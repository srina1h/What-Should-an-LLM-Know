import json
from experiments.remaining_methods import run
from experiments.remaining_methods.amp_generation_repair import parse_amp_rows
def with_fresh_amp_generation_repair(data, method, model, generate):
    if method not in ("AMP-2", "AMP-3"):
        raise ValueError("Fresh AMP correction is only defined for AMP-2/3")
    fields = [column.txt for column in data.cols.x]
    domains = []
    for column in data.cols.x:
        if hasattr(column, "lo"):
            domains.append(f"{column.txt}: numeric, observed {column.lo} to {column.hi}")
        else:
            domains.append(f"{column.txt}: one of {', '.join(map(str, sorted(column.has, key=str)))}")

    def corrected(best, rest):
        try:
            rows = generate(best, rest)
            run.validate_rows(data, rows)
            return rows
        except ValueError as initial_error:
            if model.calls != run.METHOD_CALLS[method]:
                raise
            prompt_path = model.directory / f"call_{model.calls:02d}.prompt.json"
            response_path = model.directory / f"call_{model.calls:02d}.response.json"
            if not prompt_path.exists() or not response_path.exists():
                raise
            original = json.loads(response_path.read_text())["message"].get("content")
            # Some completed reasoning responses have null content. Their
            # prompt and raw response are still logged; permit a fresh counted
            # generation rather than accepting or fabricating feature rows.
            messages = json.loads(prompt_path.read_text())["messages"]
            original_seed = model.seed
            last_error = initial_error
            for correction in (1, 2):
                model.seed = original_seed + correction * 1_000_003
                event = model.directory / f"amp_repair_{correction:02d}.json"
                run.write_new(event, {"correction": correction,
                    "previous_error_type": type(last_error).__name__,
                    "previous_error_message": str(last_error),
                    "original_prompt_sha256": run.sha(prompt_path),
                    "original_response_sha256": run.sha(response_path),
                    "model_seed": model.seed,
                    "protocol": "fresh_seed_clean_prompt_no_previous_invalid_reply"})
                instruction = (
                    "Generate a fresh answer to the original task. Return only one strict JSON object "
                    "with exactly two better_examples and two poorer_examples. Each example has only "
                    f"a features array of exactly {len(fields)} values in this order: "
                    + ", ".join(fields) + ".\n"
                    + "Feature domains:\n" + "\n".join(domains)
                    + "\nEvery numeric value must be a JSON number written in digits, never a word. "
                    "Do not add an objective, extra field, markdown, or commentary."
                )
                try:
                    response = model.invoke(messages + [{"role": "user", "content": instruction}]).content
                    repaired = parse_amp_rows(response or "")
                    run.validate_rows(data, repaired)
                    return repaired
                except (ValueError, json.JSONDecodeError) as error:
                    last_error = error
                finally:
                    model.seed = original_seed
            raise ValueError("Both counted AMP corrections failed validation") from last_error
    return corrected
