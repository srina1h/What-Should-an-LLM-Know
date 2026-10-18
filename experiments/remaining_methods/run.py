"""Study evaluator and generation helpers; extracted without algorithm changes."""
import fcntl
import hashlib
import json
import math
from pathlib import Path
import random
import re
import time
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[2]
MODEL = "openrouter/openai/gpt-oss-120b"
METHOD_CALLS = {"AMP-2": 2, "AMP-3": 3, "AMP-4": 7, "H-DKP": 1, "LLM": 1, "exploit": 0, "HKMA-scout": 2, "HKMA-rag": 1, "HKMA-combined": 2}
REPAIRABLE_METHODS = {"LLM", "HKMA-scout", "HKMA-rag", "HKMA-combined"}
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_new(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(obj, stream, indent=2, allow_nan=False)
        stream.write("\n")

def validate_rows(data, rows):
    if not isinstance(rows, list) or len(rows) != 4:
        raise ValueError("Expected exactly four generated configurations; no fallback or repair")
    expanded = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != len(data.cols.x):
            raise ValueError("Generated feature count differs from schema")
        full = ["?"] * len(data.cols.names)
        for col, value in zip(data.cols.x, row):
            if hasattr(col, "lo"):
                if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                    raise ValueError(f"Non-finite/non-numeric feature: {col.txt}")
            elif value not in col.has:
                raise ValueError(f"Unknown symbolic feature: {col.txt}")
            # Numeric extrapolation is allowed, as in the original warm-start
            # method. Do not round, clamp or invent domain constraints.
            full[col.at] = value
        expanded.append(full)
    return expanded

def optimize(data, generate, budget, seed, policy, scout=None):
    """Observed-row accounting; d2h search and Chebyshev primary reporting.

    Preserve the historical top-two/bottom-two warm handoff. The equal-oracle
    policy charges discarded evaluated rows too; legacy policy exposes them.
    generate=None supplies the local exploit comparator under the same budget.
    """
    from src.utils.ezr import clone, d2h, chebyshev, dists, loglikes, the
    if policy not in ("equal-oracle", "legacy-20-plus-warm"):
        raise ValueError("Unknown budget policy")
    if budget < 8 or len(data.rows) < budget + 6:
        raise ValueError("Need budget >= 8 and at least budget+6 observed rows")
    random.seed(seed)
    the.Last, the.label, the.GuessFaster = budget, 4, True
    rank = lambda indices: sorted(indices, key=lambda ix: d2h(data, data.rows[ix]))
    pool = list(range(len(data.rows)))
    random.shuffle(pool)
    done, todo = rank(pool[:4]), pool[4:]
    initial = list(done)
    evaluated = list(done)
    scout_ledger = []
    scout_indices = []
    if scout is not None:
        if policy != "equal-oracle":
            raise ValueError("HKMA scouting requires equal-oracle budget")
        scout_indices, scout_ledger = scout(list(todo), seed)
        if len(scout_indices) != 10 or len(set(scout_indices)) != 10 or not set(scout_indices) <= set(todo):
            raise ValueError("Scouting must return ten distinct unevaluated rows")
        evaluated.extend(scout_indices)
        chosen = set(scout_indices)
        todo = [ix for ix in todo if ix not in chosen]
        done = rank(done + scout_indices)
    synth = []
    if generate is not None:
        synth = generate([data.rows[ix] for ix in done[:2]], [data.rows[ix] for ix in done[-2:]])
        rows = validate_rows(data, synth)
        neighbors = []
        for row in rows:
            random.shuffle(todo)
            nearest, *todo = sorted(todo, key=lambda ix: dists(data, row, data.rows[ix]))
            neighbors.append(nearest)
            evaluated.append(nearest)
        combined = rank(done + neighbors)
        done = [combined[0], combined[1], combined[-1], combined[-2]]
    handoff = list(done)
    iterations = budget - (len(evaluated) if policy == "equal-oracle" else 4)
    for _ in range(iterations):
        cut = int(0.5 + len(done) ** the.N)
        best = clone(data, [data.rows[ix] for ix in done[:cut]])
        rest = clone(data, [data.rows[ix] for ix in done[cut:]])
        random.shuffle(todo)
        key = lambda ix: loglikes(best, data.rows[ix], len(done), 2) - loglikes(rest, data.rows[ix], len(done), 2)
        top, *todo = sorted(todo[:the.any], key=key, reverse=True) + todo[the.any:]
        evaluated.append(top)
        done = rank(done + [top])
    selected = data.rows[done[0]]
    return {"selected_row": selected, "selected_row_index": done[0],
            "chebyshev": chebyshev(data, selected), "d2h": d2h(data, selected),
            "initial_row_indices": initial, "handoff_row_indices": handoff,
            "evaluated_row_indices": evaluated, "oracle_evaluations": len(evaluated),
            "smo_evaluations": iterations, "synth_rows": synth,
            "scout_evaluations": len(scout_indices), "scout_row_indices": scout_indices,
            "scout_ledger": scout_ledger}

class LoggedModel:
    def __init__(self, directory, seed, max_calls, reasoning_effort=None,
                 transport_retries=0, request_budget=None):
        self.directory, self.seed, self.max_calls = directory, seed, max_calls
        self.reasoning_effort = reasoning_effort
        self.transport_retries, self.request_budget = transport_retries, request_budget
        self.calls = 0

    def reserve_request(self):
        if self.request_budget is None:
            return
        path, limit = self.request_budget
        with Path(path).open("r+") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                count = int(stream.read().strip())
                if count >= limit:
                    raise RuntimeError("Frozen provider-request budget exhausted")
                stream.seek(0)
                stream.write(str(count + 1) + "\n")
                stream.truncate()
                stream.flush()
                os.fsync(stream.fileno())
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def invoke(self, messages, response_format=None):
        if self.calls >= self.max_calls:
            raise ValueError("Prospective model-call cap reached")
        self.calls += 1
        settings = dict(model=MODEL, temperature=0.7, top_p=1.0, max_tokens=4000,
                        seed=self.seed, num_retries=0, timeout=180, caching=False)
        if self.reasoning_effort is not None:
            settings["reasoning_effort"] = self.reasoning_effort
            # The local LiteLLM model map may omit this OpenRouter parameter;
            # keep the frozen provider request instead of silently dropping it.
            settings["allowed_openai_params"] = ["reasoning_effort"]
        if response_format is not None:
            settings["response_format"] = response_format
        prefix = self.directory / f"call_{self.calls:02d}"
        write_new(prefix.with_suffix(".prompt.json"), {"messages": messages, "settings": settings})
        # Import only after explicit execution. No API keys are written.
        from litellm import completion
        for transport_attempt in range(self.transport_retries + 1):
            self.reserve_request()
            start = time.monotonic()
            try:
                response = completion(messages=messages, **settings)
                break
            except Exception as error:
                retryable = (type(error).__name__ == "Timeout" or
                             (type(error).__name__ == "APIError" and
                              "connection reset by peer" in str(error).lower()))
                if not retryable:
                    raise
                write_new(self.directory / f"call_{self.calls:02d}.transport_{transport_attempt + 1:02d}.json",
                          {"error_type": type(error).__name__,
                           "elapsed_seconds": time.monotonic() - start,
                           "retry_number": transport_attempt + 1,
                           "retry_limit": self.transport_retries})
                if transport_attempt >= self.transport_retries:
                    raise
                time.sleep(min(2 ** (transport_attempt + 1), 8))
        message = response.choices[0].message
        write_new(prefix.with_suffix(".response.json"), {
            "id": response.id, "model": response.model,
            "message": message.model_dump(), "usage": response.usage.model_dump() if response.usage else None,
            "finish_reason": response.choices[0].finish_reason,
            "elapsed_seconds": time.monotonic() - start,
        })
        return SimpleNamespace(content=message.content)

def make_generator(data, method, model, dataset, knowledge=None):
    args = SimpleNamespace(llm=MODEL, pipeline=model, amp_mode=method, dataset=str(dataset),
                           hdkp_knowledge_file=knowledge)
    if method.startswith("AMP-"):
        from btp.methods.amp import AMP_Strategy
        return AMP_Strategy(data, args).generate_examples
    if method == "H-DKP":
        from btp.methods.h_dkp import H_DKP_Strategy
        return H_DKP_Strategy(data, args).generate_examples
    if method == "LLM":
        from btp.prompts.warm_start import warm_start_messages
        from btp.methods.utils import parse_named_warm_starts
        def generate(best, rest):
            response = model.invoke(warm_start_messages(data, best, rest)).content
            return parse_named_warm_starts(response or "", [c.txt for c in data.cols.x])
        return generate
    if method == "exploit": return None
    raise ValueError(f"Unsupported method: {method}")

def with_one_generation_repair(data, method, model, generate):
    """Allow one logged correction of an invalid final generation, never priors.

    The original response and failure reason remain on disk. The correction is
    an extra model call under a prospective protocol, not a local coercion.
    """
    from btp.methods.utils import parse_named_warm_starts
    if method not in REPAIRABLE_METHODS:
        raise ValueError(f"Generation repair is unsupported for {method}")
    fields = [col.txt for col in data.cols.x]
    allowed = [f"{col.txt}: {', '.join(map(str, sorted(col.has, key=str)))}"
               for col in data.cols.x if not hasattr(col, "lo")]

    def corrected(best, rest):
        rows = None
        try:
            rows = generate(best, rest)
            validate_rows(data, rows)
            return rows
        except ValueError as error:
            # A failed prior-extraction stage or provider call is not a
            # generated response and must not trigger a correction call.
            if model.calls != METHOD_CALLS[method]:
                raise
            number = model.calls
            prompt_path = model.directory / f"call_{number:02d}.prompt.json"
            response_path = model.directory / f"call_{number:02d}.response.json"
            if not prompt_path.exists() or not response_path.exists():
                raise
            original = json.loads(response_path.read_text())["message"].get("content")
            if original is None:
                original = ""
            if not isinstance(original, str):
                raise
            messages = json.loads(prompt_path.read_text())["messages"]
            invalid = []
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, (list, tuple)):
                        invalid.extend(f"{col.txt}={value!r}"
                                       for col, value in zip(data.cols.x, row)
                                       if not hasattr(col, "lo") and value not in col.has)
            write_new(model.directory / "generation_repair.json", {
                "initial_error_type": type(error).__name__,
                "initial_error_message": str(error),
                "invalid_categorical_values": sorted(set(invalid)),
                "original_prompt_sha256": sha(prompt_path),
                "original_response_sha256": sha(response_path),
                "max_correction_calls": 1,
            })
            instruction = ("Your previous four generated configurations failed exact validation: "
                           + str(error) + ". "
                           + ("Invalid values: " + ", ".join(sorted(set(invalid))) + ". " if invalid else "")
                           + "Regenerate ALL four rows, with exactly two BETTER and two WORSE. "
                           + "Include each feature exactly once, in this order: " + ", ".join(fields) + ". "
                           + "Use only these categorical values for their respective fields:\n"
                           + ("\n".join(allowed) if allowed else "No categorical features.")
                           + "\nReturn only BETTER: and WORSE: headings and two '- name=value, ...' rows under each. "
                           + "Do not invent a value, omit a field, or add commentary.")
            response = model.invoke(messages + [{"role": "assistant", "content": original},
                                                {"role": "user", "content": instruction}]).content
            repaired = parse_named_warm_starts(response or "", fields)
            validate_rows(data, repaired)
            return repaired
    return corrected
