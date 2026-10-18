import json
import re
from types import SimpleNamespace
from experiments.remaining_methods import dapr_repair, run
def normalize_candidate_json(content):
    """Accept exactly one omitted closing bracket around four intact arrays."""
    if not isinstance(content, str):
        return None
    source = content.strip()
    if not re.fullmatch(r'\{\s*"candidates"\s*:\s*\[.*\}', source, re.DOTALL):
        return None
    try:
        parsed = json.loads(source[:-1] + "]}")
    except json.JSONDecodeError:
        return None
    if (set(parsed) != {"candidates"} or not isinstance(parsed["candidates"], list)
            or len(parsed["candidates"]) != 4
            or any(not isinstance(row, list) for row in parsed["candidates"])):
        return None
    return json.dumps(parsed, separators=(",", ":"))

class RepairingModelV2(dapr_repair.RepairingModel):
    def invoke(self, messages):
        prompt = messages[0]["content"]
        subspace = "reduced feature subspace" in prompt
        if subspace:
            match = re.search(r"exactly (\d+) values", prompt)
            if not match:
                raise ValueError("DAPR subspace size missing from frozen prompt")
            feature_count = int(match.group(1))
        else:
            feature_count = len(self.data.cols.x)
        current = list(messages)
        for attempt in range(self.max_repairs + 1):
            content = self.logged_model.invoke(current).content
            normalized = normalize_candidate_json(content) if subspace else None
            candidate = normalized or content
            try:
                self._validate(candidate, subspace, feature_count)
                if normalized is not None:
                    self.repair_events.append({"stage": "syntax_normalization",
                                               "feature_count": feature_count,
                                               "source_sha256": hashlib.sha256(content.encode()).hexdigest(),
                                               "rule": "insert_one_missing_outer_array_bracket"})
                return SimpleNamespace(content=candidate)
            except ValueError as error:
                self.repair_events.append({"stage": "subspace" if subspace else "final",
                                           "feature_count": feature_count,
                                           "attempt": attempt + 1,
                                           "error_type": type(error).__name__,
                                           "error": str(error)})
                if attempt == self.max_repairs:
                    raise
                current = current + [{"role": "assistant", "content": content or ""},
                                     {"role": "user", "content":
                                      self._correction(subspace, feature_count, error)}]
        raise AssertionError("Unreachable correction loop")
