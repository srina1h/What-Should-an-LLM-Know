"""Shared few-shot generation prompt for the LLM and HKMA pilot."""


def warm_start_messages(data, best_rows, rest_rows, context=None):
    if len(best_rows) != 2 or len(rest_rows) != 2:
        raise ValueError("Warm-start prompting requires two best and two rest rows")
    fields = [col.txt for col in data.cols.x]

    def describe(rows):
        return "\n".join("- " + ", ".join(f"{col.txt}={row[col.at]}" for col in data.cols.x)
                         for row in rows)

    user = (f"Dataset features: {', '.join(fields)}\n\n"
            f"BEST examples (these have good performance):\n{describe(best_rows)}\n\n"
            f"WORST examples (these have poor performance):\n{describe(rest_rows)}\n")
    symbolic = [f"{col.txt}: {', '.join(map(str, sorted(col.has, key=str)))}"
                for col in data.cols.x if not hasattr(col, "lo")]
    if symbolic:
        user += ("\nFor categorical features, use only these observed values exactly:\n"
                 + "\n".join(symbolic) + "\n")
    if context:
        user += f"\nAdditional domain context:\n{context}\n"
    user += ("\nGenerate 2 new examples BETTER than the best examples and 2 WORSE "
             "than the worst examples. Use the feature names and order above. "
             "Return only this format, with every feature on each line:\n"
             "BETTER:\n- feature1=value1, feature2=value2, ...\n"
             "- feature1=value1, feature2=value2, ...\n"
             "WORSE:\n- feature1=value1, feature2=value2, ...\n"
             "- feature1=value1, feature2=value2, ...")
    return [{"role": "system", "content": "You are a helpful AI that generates synthetic data examples for optimization."},
            {"role": "user", "content": user}]
