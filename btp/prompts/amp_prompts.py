
def get_analysis_prompt(features_desc, best_rows, rest_rows):
    return [
        {"role": "system", "content": f"You are a data scientist. Analyze the patterns in this dataset.\nFeatures:\n{features_desc}"},
        {"role": "user", "content": f"""Analyze the differences between these Best examples:\n{best_rows}\n\nAnd these Rest examples:\n{rest_rows}\n\n
Output a structured analysis identifying:
1. Feature Ranking: List 3-5 most influential features.
2. Tradeoff Identification: Note any conflicting objectives.
3. Directionality: For continuous variables, which direction improves the objective?
"""}
    ]

def get_constraint_prompt(analysis):
    return [
        {"role": "user", "content": f"""Based on this analysis:\n{analysis}\n\n
Identify explicit boundaries for valid configurations. Distinguish between:
- Hard Constraints: Inviolable rules (physical/logical limits).
- Soft Constraints: Heuristic preferences.
List them clearly.
"""}
    ]

def get_generation_prompt(analysis, constraints, best_rows, features_desc, n_count=2):
    names = [line[2:].split(" (Feature):", 1)[0]
             for line in features_desc.splitlines() if line.startswith("- ") and " (Feature):" in line]
    if not names:
        raise ValueError("AMP generation requires an explicit feature schema")
    ordered_names = "\n".join(f"{index}. {name}" for index, name in enumerate(names, 1))
    return [
        {"role": "user", "content": f"""
Analysis: {analysis}
Constraints: {constraints}
Configuration Features (generate values for ONLY these):
{features_desc}

Required output schema: every "features" array must contain exactly {len(names)} values,
one for each configuration feature in this numbered order:
{ordered_names}

Task: Generate {n_count} NEW better configurations and {n_count} NEW poorer configurations.
Strictly adhere to the Hard Constraints.
The "features" list in your output MUST include values for ONLY the configuration features listed above, in the same order. Do NOT include objective/output values.
Optimize the key features identified in the Analysis to improve the Objectives.

Return only a valid JSON object with keys "better_examples" and "poorer_examples".
Each key must contain exactly {n_count} objects, each with a "features" array of exactly {len(names)} values.
Use numbers for numeric features and observed category strings for categorical features.
Do not wrap in markdown blocks, omit a feature, append an objective, or add commentary.
"""}
    ]

def get_validation_prompt(constraints, generated_examples):
    return [
        {"role": "user", "content": f"""
Constraints:
{constraints}

Generated Configuration:
{generated_examples}

Task: Verify if the configuration violates any Hard Constraints.
If VALID, output "VALID".
If INVALID, explain the violation and provide a REVISED configuration that satisfies the constraint while preserving other values.

Return JSON: {{"status": "VALID" | "INVALID", "revised_features": [...] (if invalid), "explanation": "..."}}
"""}
    ]
