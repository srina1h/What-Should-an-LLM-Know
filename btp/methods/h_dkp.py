import os
from btp.methods.base import BaseStrategy
from src.language import load_model
from btp.methods.utils import parse_json_output

class H_DKP_Strategy(BaseStrategy):
    """
    Human-in-the-Loop Domain Knowledge Prompting (H-DKP) Strategy.
    Uses human-verified constraints (Markdown) to guide generation.
    """
    def __init__(self, data, args):
        super().__init__(data, args)
        self.constraints = self._load_constraints()
        self.model = getattr(args, 'pipeline', None)
        if self.model is None:
            self.model = load_model(args, name=args.llm).get_pipeline()

    def _load_constraints(self):
        """Loads domain knowledge from Markdown file (supplied by the replicating researcher)."""
        explicit = getattr(self.args, 'hdkp_knowledge_file', None)
        if explicit is not None:
            with open(explicit, 'r') as f:
                text = f.read()
            if not text.strip():
                raise ValueError("Explicit H-DKP knowledge file is empty")
            return text
        raise ValueError("H-DKP requires independently reviewed rules via hdkp_knowledge_file")

    def generate_examples(self, best_rows, rest_rows):
        feature_order = [col.txt for col in self.data.cols.x]
        best_features = [[row[col.at] for col in self.data.cols.x] for row in best_rows]
        rest_features = [[row[col.at] for col in self.data.cols.x] for row in rest_rows]
        features_desc = []
        for c in self.data.cols.x:
            if hasattr(c, 'lo'):
                features_desc.append(f"- {c.txt}: {c.lo} to {c.hi}")
            else:
                vals = list(c.has.keys()) if c.has else []
                features_desc.append(f"- {c.txt}: {vals}")
        features_desc = "\n".join(features_desc)
        prompt = [
            {"role": "system", "content": f"""You are a domain expert.
Dataset Features:
{features_desc}

Feature order for every generated row: {feature_order}
Do not include outcome columns in generated rows.
Use categorical labels exactly as listed. Do not substitute aliases or alternate spellings.

Domain Knowledge (Expert Verified):
{self.constraints}

Use these constraints to ensure generated examples are realistic and valid.
"""},
            {"role": "user", "content": f"""
Given Best Examples (features only):
{best_features}

Given Rest Examples (features only):
{rest_features}

Generate 2 NEW better examples and 2 NEW poorer examples.
Follow the domain constraints strictly.

Return only a JSON object with keys "better_examples" and "poorer_examples".
Each key must contain exactly two objects of the form
{{"features": [values in the feature order above]}}.
Each features array must have exactly {len(feature_order)} values. Do not add outcome values.
"""}
        ]
        
        response = self.model.invoke(prompt).content
        data = parse_json_output(response)
        if not isinstance(data, dict) or set(data) != {"better_examples", "poorer_examples"}:
            raise ValueError("H-DKP requires a JSON object with better_examples and poorer_examples")
        generated = []
        for group in ("better_examples", "poorer_examples"):
            items = data[group]
            if not isinstance(items, list) or len(items) != 2:
                raise ValueError("H-DKP requires exactly two examples per group")
            for item in items:
                if (not isinstance(item, dict) or set(item) != {"features"}
                        or not isinstance(item["features"], list)
                        or len(item["features"]) != len(feature_order)):
                    raise ValueError("H-DKP requires wrapped, feature-only rows matching the schema")
                generated.append(item["features"])
        return generated
