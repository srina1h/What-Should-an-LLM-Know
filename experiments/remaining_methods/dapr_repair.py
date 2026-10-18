import json
import re
from types import SimpleNamespace
from experiments.remaining_methods import run
from btp.methods.utils import parse_json_output, parse_named_warm_starts
MAX_REPAIRS_PER_STAGE = 2

class RepairingModel:
    """Keep every response, and ask the same model to correct invalid output."""

    def __init__(self, logged_model, data, max_repairs=MAX_REPAIRS_PER_STAGE):
        self.logged_model = logged_model
        self.data = data
        self.max_repairs = max_repairs
        self.repair_events = []

    def _validate(self, content, subspace, feature_count):
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Empty DAPR model response")
        if subspace:
            parsed = parse_json_output(content)
            candidates = parsed.get("candidates") if isinstance(parsed, dict) else None
            if not isinstance(candidates, list) or len(candidates) != 4:
                raise ValueError("Expected four candidates in strict JSON")
            if any(not isinstance(row, list) or len(row) != feature_count for row in candidates):
                raise ValueError(f"Each candidate must have exactly {feature_count} values")
        else:
            rows = parse_named_warm_starts(content, [c.txt for c in self.data.cols.x])
            run.validate_rows(self.data, rows)

    def _correction(self, subspace, feature_count, error):
        if subspace:
            return (f"Your preceding response failed validation: {error}. Regenerate all four "
                    f"candidates as STRICT valid JSON with only the key 'candidates'. Each of "
                    f"the four arrays must contain exactly {feature_count} values in the feature "
                    "order and allowed domains in the original prompt. Use JSON numbers for "
                    "numeric fields, quoted strings for symbolic fields, and no words in place "
                    "of numbers. Do not add commentary, placeholders, or trailing commas.")
        fields = [c.txt for c in self.data.cols.x]
        allowed = [f"{c.txt}: {', '.join(map(str, sorted(c.has, key=str)))}"
                   for c in self.data.cols.x if not hasattr(c, "lo")]
        return (f"Your preceding response failed validation: {error}. Regenerate ALL four "
                "complete configurations: exactly two BETTER and two WORSE, with one named "
                "value for every feature in this order: " + ", ".join(fields) + ". "
                "Use only these observed categorical values for each respective field:\n"
                + ("\n".join(allowed) if allowed else "No categorical fields.")
                + "\nReturn only BETTER: and WORSE: headings and two '- name=value, ...' rows "
                "under each. Do not omit a feature or add commentary.")

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
            try:
                self._validate(content, subspace, feature_count)
                return SimpleNamespace(content=content)
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
