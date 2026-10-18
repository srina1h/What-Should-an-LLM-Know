"""Isolated, offline-first HKMA scouting and document retrieval for the pilot."""
from functools import partial
import hashlib
import json
import re
from pathlib import Path

import numpy as np


MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
CHUNK_CHARS = 900
CHUNK_OVERLAP = 100
TOP_K = 3
_EMBEDDER = None


def _as_python(value):
    return value.item() if isinstance(value, np.generic) else value


class LocalEmbedder:
    """Use a pinned, already-cached MiniLM revision; never download at runtime."""
    def __init__(self):
        from transformers import AutoModel, AutoTokenizer
        import torch
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION, local_files_only=True)
        self.model = AutoModel.from_pretrained(MODEL_ID, revision=MODEL_REVISION, local_files_only=True)
        self.model.eval()

    def __call__(self, texts):
        out = []
        for start in range(0, len(texts), 16):
            batch = self.tokenizer(texts[start:start + 16], padding=True, truncation=True,
                                   max_length=256, return_tensors="pt")
            with self.torch.no_grad():
                hidden = self.model(**batch).last_hidden_state
                mask = batch["attention_mask"].unsqueeze(-1)
                pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1)
                pooled = self.torch.nn.functional.normalize(pooled, p=2, dim=1)
            out.extend(pooled.cpu().numpy())
        return np.asarray(out, dtype=np.float32)


def embed_texts(texts):
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = LocalEmbedder()
    return _EMBEDDER(texts)


class CorpusIndex:
    def __init__(self, corpus_root, dataset_id, embed=None):
        self.root = Path(corpus_root)
        self.dataset_id = dataset_id
        directory = self.root / dataset_id
        if not directory.is_dir():
            raise ValueError(f"Missing corpus folder: {dataset_id}")
        self.chunks = []
        for path in sorted(directory.glob("*.md")):
            raw = path.read_text()
            body = raw.split("---", 2)[-1].strip() if raw.startswith("---") else raw
            step = CHUNK_CHARS - CHUNK_OVERLAP
            for start in range(0, len(body), step):
                passage = body[start:start + CHUNK_CHARS].strip()
                if not passage: continue
                self.chunks.append({"id": f"{path.stem}:{start}",
                                    "path": f"{dataset_id}/{path.name}",
                                    "text": passage,
                                    "sha256": hashlib.sha256(passage.encode()).hexdigest()})
        if not self.chunks:
            raise ValueError(f"No indexed passages for {dataset_id}")
        self.embed = embed or embed_texts
        vectors = np.asarray(self.embed([c["text"] for c in self.chunks]), dtype=np.float32)
        if vectors.ndim != 2 or len(vectors) != len(self.chunks) or not np.isfinite(vectors).all():
            raise ValueError("Invalid document embeddings")
        self.vectors = vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)

    def retrieve(self, query, top_k=TOP_K):
        vector = np.asarray(self.embed([query]), dtype=np.float32)
        if vector.shape != (1, self.vectors.shape[1]) or not np.isfinite(vector).all():
            raise ValueError("Invalid query embedding")
        vector = vector[0] / max(float(np.linalg.norm(vector[0])), 1e-12)
        scores = self.vectors @ vector
        order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), self.chunks[i]["id"]))
        return [{**self.chunks[i], "score": float(scores[i])} for i in order[:top_k]]


def scout_rows(data, available, seed):
    """Ten distinct nearest-unobserved oracle rows: four random startup, six TPE."""
    from hyperopt import Trials, STATUS_OK, fmin, hp, tpe
    from src.utils.ezr import chebyshev
    if len(available) < 10:
        raise ValueError("Scouting needs ten available observed rows")
    cols = data.cols.x
    space = {c.txt: (hp.uniform(c.txt, c.lo, c.hi) if hasattr(c, "lo") and c.lo < c.hi
                     else hp.choice(c.txt, [c.lo]) if hasattr(c, "lo")
                     else hp.choice(c.txt, sorted(c.has, key=str))) for c in cols}
    remaining = set(available)
    row_values = {}
    for col in cols:
        if hasattr(col, "lo"):
            denom = max(col.hi - col.lo, 1e-12)
            row_values[col.txt] = np.asarray([(data.rows[ix][col.at] - col.lo) / denom
                                               for ix in available], dtype=np.float64)
        else:
            row_values[col.txt] = np.asarray([data.rows[ix][col.at] for ix in available], dtype=object)
    selected, ledger = [], []
    def objective(params):
        distances = np.zeros(len(available), dtype=np.float64)
        for col in cols:
            values = row_values[col.txt]
            if hasattr(col, "lo"):
                norm = (params[col.txt] - col.lo) / max(col.hi - col.lo, 1e-12)
                distances += (values - norm) ** 2
            else:
                distances += (values != params[col.txt]).astype(np.float64)
        order = np.argsort(distances, kind="stable")
        nearest = available[int(order[0])]
        ix = next(available[int(i)] for i in order if available[int(i)] in remaining)
        remaining.remove(ix)
        selected.append(ix)
        row = data.rows[ix]
        score = float(chebyshev(data, row))
        ledger.append({"phase": "startup" if len(selected) <= 4 else "tpe",
                       "query_features": [_as_python(params[c.txt]) for c in cols],
                       "observed_row_index": ix,
                       "observed_features": [_as_python(row[c.at]) for c in cols],
                       "chebyshev": score, "nearest_already_evaluated": nearest != ix})
        return {"loss": score, "status": STATUS_OK}
    fmin(fn=objective, space=space, algo=partial(tpe.suggest, n_startup_jobs=4),
         max_evals=10, trials=Trials(), rstate=np.random.default_rng(seed),
         show_progressbar=False, verbose=False)
    return selected, ledger


class HKMAPilot:
    def __init__(self, data, method, model, corpus_root, dataset_id, embed=None, index=None):
        if method not in ("HKMA-scout", "HKMA-rag", "HKMA-combined"):
            raise ValueError("Unknown HKMA condition")
        self.data, self.method, self.model = data, method, model
        self.index = (index or CorpusIndex(corpus_root, dataset_id, embed=embed)) if method != "HKMA-scout" else None
        self.ledger, self.retrieved, self.priors = [], [], None

    def scout(self, available, seed):
        indices, self.ledger = scout_rows(self.data, available, seed)
        return indices, self.ledger

    def generate(self, best_rows, rest_rows):
        from btp.methods.utils import parse_json_output, parse_named_warm_starts
        from btp.prompts.warm_start import warm_start_messages
        fields = [c.txt for c in self.data.cols.x]
        objectives = [c.txt for c in self.data.cols.y]
        if self.method != "HKMA-rag":
            ordered = sorted(self.ledger, key=lambda row: row["chebyshev"])
            evidence = {"best_observed": ordered[:3], "other_observed": ordered[3:]}
            prompt = [{"role": "system", "content": "In at most 120 words, state feature-specific differences between the best and other measured rows. Name features and observed numeric values or ranges supporting each pattern. If the ten rows do not support a pattern, say so. The sampled query coordinates are not measurements. Do not infer causal effects or undocumented units. Do not describe the process."},
                      {"role": "user", "content": json.dumps({"features": fields, "objectives": objectives,
                                                                "scouting_evidence": evidence}, default=str)}]
            self.priors = self.model.invoke(prompt).content
            if not isinstance(self.priors, str) or not self.priors.strip():
                raise ValueError("Empty empirical priors")
            if not any(re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", self.priors, re.I)
                       for name in fields) or not re.search(r"\d", self.priors):
                raise ValueError("Missing feature-specific empirical prior")
        if self.index is not None:
            query = ("Features: " + ", ".join(fields) + ". Objectives: " + ", ".join(objectives)
                     + (". Empirical priors: " + self.priors if self.priors else ""))
            self.retrieved = self.index.retrieve(query)
        context = []
        if self.priors:
            context.append("Empirical priors from observed scouting rows:\n" + self.priors)
        if self.retrieved:
            context.append("Retrieved documentation:\n" + "\n\n".join(
                f"Source {item['id']}: {item['text']}" for item in self.retrieved))
        prompt = warm_start_messages(self.data, best_rows, rest_rows, "\n\n".join(context))
        response = self.model.invoke(prompt).content
        if response and not response.lstrip().startswith("{"):
            return parse_named_warm_starts(response, fields)
        parsed = parse_json_output(response or "")
        if not isinstance(parsed, dict):
            raise ValueError("Invalid HKMA JSON")
        better, poorer = parsed.get("better_examples"), parsed.get("poorer_examples")
        if not isinstance(better, list) or not isinstance(poorer, list) or len(better) != 2 or len(poorer) != 2:
            raise ValueError("HKMA requires two better and two poorer examples")
        rows = []
        for item in better + poorer:
            if isinstance(item, list):
                rows.append(item)
            elif not isinstance(item, dict):
                raise ValueError("HKMA example must be a list or object")
            elif set(item) == {"features"}:
                rows.append(item["features"])
            elif set(item) == set(fields):
                rows.append([item[field] for field in fields])
            else:
                raise ValueError("HKMA example fields differ from dataset schema")
        return rows
