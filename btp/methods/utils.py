import json
import re


def parse_named_warm_starts(response, feature_order):
    """Read two BETTER and two WORSE named rows without guessing missing fields."""
    groups = {"BETTER": [], "WORSE": []}
    section = None
    for raw in response.splitlines():
        line = raw.strip()
        if not line or line.startswith("```"):
            continue
        heading = line.strip("*").rstrip(":").upper()
        if heading in groups:
            section = heading
            continue
        if not line.startswith("- ") or section is None:
            continue
        pairs = {}
        parts = line[2:].split(",")
        if parts[-1].strip() == "":
            parts.pop()  # Harmless trailing delimiter after a complete row.
        for part in parts:
            if "=" not in part:
                raise ValueError("Warm-start field lacks a value")
            name, value = (x.strip() for x in part.split("=", 1))
            if name in pairs:
                raise ValueError("Duplicate warm-start field")
            try:
                pairs[name] = float(value)
            except ValueError:
                pairs[name] = value
        if set(pairs) != set(feature_order):
            raise ValueError("Generated feature names differ from schema")
        groups[section].append([pairs[name] for name in feature_order])
    if len(groups["BETTER"]) != 2 or len(groups["WORSE"]) != 2:
        raise ValueError("Expected two BETTER and two WORSE configurations")
    return groups["BETTER"] + groups["WORSE"]

def parse_json_output(response):
    try:
        # Find JSON block
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(response)
    except:
        return {}

def parse_plain_text_output(response):
    # simplistic parse for list of features
    # expected format:
    # BETTER:
    # - feature1=v1, feature2=v2
    data = {'better_examples': [], 'poorer_examples': []}
    lines = response.split('\n')
    mode = None
    for line in lines:
        if "BETTER" in line: mode = 'better_examples'
        elif "WORSE" in line or "POORER" in line: mode = 'poorer_examples'
        elif line.strip().startswith("-") and mode:
            parts = line.replace("-", "", 1).split(",")
            feats = []
            for p in parts:
                if "=" in p:
                    try:
                        feats.append(float(p.split("=")[1].strip()))
                    except:
                        feats.append(p.split("=")[1].strip())
            if feats:
                data[mode].append({"features": feats})
    return data

def markdown_to_rows(markdown):
    # standard markdown table parser
    lines = markdown.strip().split('\n')
    rows = []
    for line in lines:
        if "|" in line and "---" not in line and "Best" not in line and "Rest" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts:
                try:
                    rows.append([float(x) for x in parts[:-1]])
                except:
                    pass
    # simple split best and rest
    mid = len(rows) // 2
    return rows[:mid], rows[mid:]
