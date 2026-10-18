import json
from experiments.remaining_methods import run
from btp.methods.utils import parse_json_output
def parse_amp_rows(content):
    parsed = json.loads(content)
    if not isinstance(parsed, dict) or set(parsed) != {"better_examples", "poorer_examples"}:
        raise ValueError("AMP correction must contain exactly the two example groups")
    groups = []
    for key in ("better_examples", "poorer_examples"):
        examples = parsed[key]
        if not isinstance(examples, list) or len(examples) != 2:
            raise ValueError(f"AMP correction needs two {key}")
        for example in examples:
            if not isinstance(example, dict) or set(example) != {"features"}:
                raise ValueError("AMP correction needs a features array in every example")
            groups.append(example["features"])
    return groups

def with_one_amp_generation_repair(data, method, model, generate):
    if method not in ("AMP-2", "AMP-3"):
        raise ValueError("AMP correction is only defined for AMP-2/3")
    fields = [column.txt for column in data.cols.x]
    allowed = [f"{column.txt}: {', '.join(map(str, sorted(column.has, key=str)))}"
               for column in data.cols.x if not hasattr(column, "lo")]

    def corrected(best, rest):
        rows = None
        try:
            rows = generate(best, rest)
            run.validate_rows(data, rows)
            return rows
        except ValueError as error:
            if model.calls != run.METHOD_CALLS[method]:
                raise
            prompt_path = model.directory / f"call_{model.calls:02d}.prompt.json"
            response_path = model.directory / f"call_{model.calls:02d}.response.json"
            if not prompt_path.exists() or not response_path.exists():
                raise
            original = json.loads(response_path.read_text())["message"].get("content")
            if not isinstance(original, str):
                raise
            messages = json.loads(prompt_path.read_text())["messages"]
            run.write_new(model.directory / "amp_generation_repair.json", {
                "initial_error_type": type(error).__name__,
                "initial_error_message": str(error),
                "original_prompt_sha256": run.sha(prompt_path),
                "original_response_sha256": run.sha(response_path),
                "max_correction_calls": 1,
            })
            instruction = (
                f"Your generated configurations failed validation: {error}. "
                "Regenerate ALL four configurations as one strict JSON object with exactly "
                "two better_examples and two poorer_examples; each example has only a features array. "
                f"Every array must have exactly {len(fields)} values, in this feature order: "
                + ", ".join(fields) + ". "
                + "Allowed categorical values by feature:\n"
                + ("\n".join(allowed) if allowed else "No categorical features.")
                + "\nUse JSON numbers for numeric features. Do not add objective values, extra fields, "
                "markdown, or commentary."
            )
            response = model.invoke(messages + [{"role": "assistant", "content": original},
                                                {"role": "user", "content": instruction}]).content
            repaired = parse_amp_rows(response or "")
            run.validate_rows(data, repaired)
            return repaired
    return corrected
