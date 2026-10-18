import random
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import mutual_info_classif
from sklearn.preprocessing import MinMaxScaler
from scipy.stats import spearmanr

from btp.methods.base import BaseStrategy
from src.language import load_model
from btp.methods.utils import parse_json_output, parse_named_warm_starts
from src.utils.ezr import chebyshev


class DAPR_Strategy(BaseStrategy):
    """
    Dimension-Aware Progressive Refinement (DAPR) Strategy.

    Implements Algorithm 2 from the paper:
      1. Ensemble feature importance (Spearman + Mutual Info + Random Forest),
         normalised and averaged, over the few-shot samples only.
      2. Progressive subspace expansion:
         - Start with top-k features; at each step project 4 random samples
           onto the current subspace, prompt the LLM to generate candidate
           configurations restricted to those features, nearest-neighbour them
           into D, evaluate with Chebyshev, and track the best.
         - Expand by s features, anchoring newly-added features to values from
           the current best configuration (median fallback).
      3. Final full-dimensional warm-start generation seeded with 4 random
         samples and anchored to the best configuration found during refinement.
    """

    def __init__(self, data, args):
        super().__init__(data, args)
        self.model = getattr(args, "pipeline", None)
        if self.model is None:
            self.model = load_model(args, name=args.llm).get_pipeline()
        # Algorithm 2 parameters: initial size k and step s. Expose via args so
        # ablations are possible; fall back to paper-friendly defaults.
        n_feats = len(self.data.cols.x)
        k_raw = getattr(args, "dapr_k", None)
        s_raw = getattr(args, "dapr_s", None)
        c_raw = getattr(args, "dapr_candidates", None)
        self.k = int(k_raw) if k_raw else max(1, n_feats // 2)
        self.s = int(s_raw) if s_raw else 2
        self.n_candidates = int(c_raw) if c_raw else 4
        self.k = max(1, min(self.k, max(1, n_feats)))
        self.s = max(1, self.s)
        self.n_candidates = max(1, self.n_candidates)
        self.intermediate_evaluations = []
        self.intermediate_stage_errors = []
        self._row_index_by_id = {id(row): index for index, row in enumerate(data.rows)}

    # ------------------------------------------------------------------
    # §6.3.1 Feature Importance Ranking
    # ------------------------------------------------------------------
    def _calculate_feature_importance(self, best_rows, rest_rows):
        """Ensemble feature importance over the few-shot samples only.

        Spearman |corr|, mutual information, and Random Forest importances are
        each MinMax-normalised and averaged; features are returned sorted by
        descending final score.
        """
        feature_cols = list(self.data.cols.x)
        feature_names = [c.txt for c in feature_cols]

        X_data, y_data = [], []
        for r in best_rows:
            X_data.append([r[c.at] for c in feature_cols])
            y_data.append(1)
        for r in rest_rows:
            X_data.append([r[c.at] for c in feature_cols])
            y_data.append(0)

        df = pd.DataFrame(X_data, columns=feature_names)
        # Factorize every non-numeric column.  Check via `is_numeric_dtype` rather
        # than `dtype == 'object'` because pandas >= 2 returns dtypes like `str`
        # or `StringDtype()` for pure-string columns, which the legacy `object`
        # comparison misses — and `.astype(float)` below would then blow up on
        # categorical feature values (e.g. `'absolute_error'` on HPO datasets).
        for col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                df[col], _ = pd.factorize(df[col])

        try:
            X = df.values.astype(float)
        except Exception:
            # Final safety net: factorize every column (irrespective of dtype)
            # and retry.  Ensures we never crash on quirky mixed-type inputs.
            for col in df.columns:
                df[col], _ = pd.factorize(df[col])
            X = df.values.astype(float)
        y = np.array(y_data)

        if len(set(y)) < 2 or X.shape[0] < 2:
            return feature_cols

        rf = RandomForestClassifier(n_estimators=10, random_state=42)
        rf.fit(X, y)
        rf_imp = rf.feature_importances_

        mi_imp = mutual_info_classif(X, y, discrete_features="auto", random_state=42)

        spearman_imp = []
        for i in range(X.shape[1]):
            with np.errstate(invalid="ignore"):
                res = spearmanr(X[:, i], y)
            corr = res[0] if hasattr(res, "__getitem__") else res
            try:
                corr = float(corr)
            except (TypeError, ValueError):
                corr = 0.0
            spearman_imp.append(abs(corr) if not np.isnan(corr) else 0.0)
        spearman_imp = np.array(spearman_imp)

        def _safe_norm(arr):
            arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
            rng = arr.max() - arr.min()
            if rng <= 0:
                return np.zeros_like(arr)
            return MinMaxScaler().fit_transform(arr.reshape(-1, 1)).flatten()

        norm_rf = _safe_norm(rf_imp)
        norm_mi = _safe_norm(mi_imp)
        norm_sp = _safe_norm(spearman_imp)

        final_score = (norm_rf + norm_mi + norm_sp) / 3.0
        final_score = np.nan_to_num(final_score, nan=0.0)

        ranked = sorted(
            zip(feature_cols, final_score), key=lambda p: p[1], reverse=True
        )
        return [c for c, _ in ranked]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _median_for(self, col):
        """Median (NUM) or mode (SYM) fallback anchor for a column."""
        vals = [r[col.at] for r in self.data.rows if r[col.at] != "?"]
        if not vals:
            return 0
        if hasattr(col, "lo"):
            try:
                return float(np.median([float(v) for v in vals]))
            except Exception:
                return vals[len(vals) // 2]
        vc = {}
        for v in vals:
            vc[v] = vc.get(v, 0) + 1
        return max(vc, key=vc.get)

    def _project_rows(self, rows, cols):
        """Return rows projected onto `cols` as plain lists (paper line 3/19)."""
        return [[r[c.at] for c in cols] for r in rows]

    def _format_cols(self, cols):
        lines = []
        for c in cols:
            if hasattr(c, "lo"):
                lines.append(f"- {c.txt}: numeric in [{c.lo}, {c.hi}]")
            else:
                vals = list(c.has.keys()) if getattr(c, "has", None) else []
                desc = vals if len(vals) < 10 else "categorical (many values)"
                lines.append(f"- {c.txt}: {desc}")
        return "\n".join(lines)

    def _find_nearest_in_D(self, partial_config, active_cols):
        """Nearest neighbour of a subspace config in the full dataset D.

        Distance is computed on `active_cols` only (the only coords available
        for `partial_config`); the returned row is the full row from D so its
        Chebyshev over the y-columns can be evaluated (paper lines 6-7).
        """
        best_dist = float("inf")
        nn_row = None
        for row in self.data.rows:
            d = 0.0
            for idx, col in enumerate(active_cols):
                v1 = partial_config[idx]
                v2 = row[col.at]
                if hasattr(col, "lo"):
                    try:
                        v1f = float(v1)
                        v2f = float(v2)
                        rng = (col.hi - col.lo) or 1e-30
                        nv1 = (v1f - col.lo) / rng
                        nv2 = (v2f - col.lo) / rng
                        d += (nv1 - nv2) ** 2
                    except Exception:
                        d += 1.0
                else:
                    d += 0.0 if str(v1) == str(v2) else 1.0
            d = d ** 0.5
            if d < best_dist:
                best_dist = d
                nn_row = row
        return nn_row

    # ------------------------------------------------------------------
    # §6.3.2 Progressive Expansion (Algorithm 2)
    # ------------------------------------------------------------------
    def _prompt_subspace(self, current_cols, anchored, fs_rows_projected):
        """Build the per-iteration LLM prompt (Algorithm 2, lines 3-5)."""
        col_desc = self._format_cols(current_cols)
        feature_order = [c.txt for c in current_cols]

        fs_block_lines = []
        for i, proj in enumerate(fs_rows_projected):
            pairs = ", ".join(
                f"{name}={val}" for name, val in zip(feature_order, proj)
            )
            fs_block_lines.append(f"  [{i+1}] {pairs}")
        fs_block = "\n".join(fs_block_lines) if fs_block_lines else "  (none)"

        if anchored:
            anchor_pairs = ", ".join(
                f"{name}={val}" for name, val in anchored.items()
            )
            anchor_instr = (
                f"\nAnchored features (must keep these values fixed): {anchor_pairs}\n"
                f"You may only vary the non-anchored features listed above."
            )
        else:
            anchor_instr = ""

        content = f"""You are optimising a configuration on a reduced feature subspace.

Feature subspace (feature order matters — your output must match this order exactly):
{col_desc}

Few-shot samples projected onto this subspace:
{fs_block}
{anchor_instr}

Generate {self.n_candidates} candidate configurations that you expect to score
well on the underlying objectives.  Return STRICT JSON of the form:

{{"candidates": [[val_1, val_2, ...], ...]}}

Each inner list must have exactly {len(current_cols)} values in the feature
order given above.  Do not include any other keys or commentary.
"""
        return [{"role": "user", "content": content}]

    def _prompt_final(self, best_row, fs_rows_full):
        """Final full-space prompt (Algorithm 2, lines 18-20)."""
        feature_cols = list(self.data.cols.x)
        col_desc = self._format_cols(feature_cols)
        feature_order = [c.txt for c in feature_cols]

        fs_block_lines = []
        for i, proj in enumerate(fs_rows_full):
            pairs = ", ".join(
                f"{name}={val}" for name, val in zip(feature_order, proj)
            )
            fs_block_lines.append(f"  [{i+1}] {pairs}")
        fs_block = "\n".join(fs_block_lines) if fs_block_lines else "  (none)"

        best_proj = [best_row[c.at] for c in feature_cols]
        best_pairs = ", ".join(
            f"{name}={val}" for name, val in zip(feature_order, best_proj)
        )

        content = f"""You are producing warm-start examples in the FULL feature space.

Features (output order):
{col_desc}

Few-shot samples (full space):
{fs_block}

Best configuration found during progressive refinement (use as anchor):
  {best_pairs}

Produce exactly four warm-start examples anchored around the best configuration:
two BETTER rows and two WORSE rows. Return only this named-field format:

BETTER:
- {', '.join(f'{name}=value' for name in feature_order)}
- {', '.join(f'{name}=value' for name in feature_order)}
WORSE:
- {', '.join(f'{name}=value' for name in feature_order)}
- {', '.join(f'{name}=value' for name in feature_order)}

Use every feature name exactly once in every row. No table or commentary.
"""
        return [{"role": "user", "content": content}]

    # ------------------------------------------------------------------
    def generate_examples(self, best_rows, rest_rows):
        self.intermediate_evaluations.clear()
        self.intermediate_stage_errors.clear()
        ranked_cols = self._calculate_feature_importance(best_rows, rest_rows)
        n = len(ranked_cols)
        if n == 0:
            return []

        # line 1: X_cur <- {f_1..f_k}; best <- null
        current_cols = ranked_cols[: self.k]
        # Seed best with the best few-shot row so Chebyshev comparisons are
        # always well-defined (equivalent to `best <- null` with a sentinel).
        current_best_row = best_rows[0] if best_rows else self.data.rows[0]
        current_best_cheb = chebyshev(self.data, current_best_row)

        # line 2: while |X_cur| < n  (we also execute the body once when k == n,
        # which is handled by running the loop at least once via a do/while).
        while True:
            # line 3: project 4 random samples onto X_cur
            if len(self.data.rows) >= self.n_candidates:
                fs_rows = random.sample(self.data.rows, self.n_candidates)
            else:
                fs_rows = list(self.data.rows)
            fs_projected = self._project_rows(fs_rows, current_cols)

            # Anchored features = those already chosen that are *not* the
            # initial k; for the first iteration this is empty.  We pin the
            # anchored values to the current best configuration.
            anchored = {}
            if len(current_cols) > self.k:
                for c in current_cols[self.k :]:
                    anchored[c.txt] = current_best_row[c.at]

            # lines 4-5: LLM generates candidates on X_cur
            try:
                prompt = self._prompt_subspace(current_cols, anchored, fs_projected)
                response = self.model.invoke(prompt).content
                parsed = parse_json_output(response)
                candidates = parsed.get("candidates", []) or []

                # lines 6-8: map each candidate to its NN in D and evaluate
                # Chebyshev on the recovered full row.
                # lines 9-12: track the best configuration seen so far.
                for cand in candidates:
                    if not isinstance(cand, list):
                        continue
                    if len(cand) != len(current_cols):
                        continue
                    nn = self._find_nearest_in_D(cand, current_cols)
                    if nn is None:
                        continue
                    cheb = chebyshev(self.data, nn)
                    self.intermediate_evaluations.append({
                        "active_features": len(current_cols),
                        "candidate": cand,
                        "observed_row_index": self._row_index_by_id[id(nn)],
                        "chebyshev": cheb,
                    })
                    if cheb < current_best_cheb:
                        current_best_row = nn
                        current_best_cheb = cheb
            except Exception as error:
                # Paper's outer loop is tolerant to a bad LLM response in any
                # single iteration — just skip and keep expanding.
                self.intermediate_stage_errors.append({
                    "active_features": len(current_cols),
                    "error_type": type(error).__name__,
                })

            # Termination: all features included.
            if len(current_cols) >= n:
                break

            # lines 13-14: expand by s next most-important features.
            d_size = len(current_cols)
            x_new = ranked_cols[d_size : min(d_size + self.s, n)]
            current_cols = current_cols + x_new

            # lines 15-17: anchor newly-added features to values from `best`,
            # using median/mode fallback when the best row has a missing value.
            for c in x_new:
                v = current_best_row[c.at] if current_best_row is not None else "?"
                if v == "?" or v is None:
                    # Fallback written into a copy of the best row so future
                    # iterations see a concrete anchor.
                    anchor_val = self._median_for(c)
                    try:
                        mutable = list(current_best_row)
                        mutable[c.at] = anchor_val
                        current_best_row = mutable
                    except Exception:
                        pass

        # lines 18-20: final warm-start generation in the full space, seeded
        # with 4 random full-space samples and anchored to best.
        full_cols = list(self.data.cols.x)
        if len(self.data.rows) >= self.n_candidates:
            fs_full_rows = random.sample(self.data.rows, self.n_candidates)
        else:
            fs_full_rows = list(self.data.rows)
        fs_full_projected = self._project_rows(fs_full_rows, full_cols)

        final_prompt = self._prompt_final(current_best_row, fs_full_projected)
        final_res = self.model.invoke(final_prompt).content
        if not isinstance(final_res, str) or not final_res.strip():
            raise ValueError("DAPR final generation returned no content")
        return parse_named_warm_starts(final_res, [c.txt for c in full_cols])
