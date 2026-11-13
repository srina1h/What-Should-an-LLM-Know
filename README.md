# What Should an LLM Know?

Replication code for *What Should an LLM Know? Knowledge-Guided Warm Starts for Software Optimization*, aligned with the November 13, 2026 draft.

Includes 49 benchmark datasets and eight expert-study datasets. Three datasets are shared, giving **54 unique CSV files**. Every method uses the same included dataset version; paths and hashes are in `manifest.json`.

## Research questions

| RQ | Question | Comparison |
| --- | --- | --- |
| RQ1 | With only 24 labels, can domain knowledge help an LLM propose better initial configurations? | Ten automated methods on 49 datasets; overall best-group counts and mean Chebyshev distance. |
| RQ2 | Does increasing the number of configuration parameters change which kinds of knowledge help? | The same ten-method groups, summarized by dimensionality. |
| RQ3 | Does human review of the LLM's domain rules help? | H-DKP plus the ten automated methods on eight expert-study datasets; independent pools for the two POM3a tracks. |
| RQ4 | What does checked knowledge cost? | Online labels, inference costs and offline expert preparation; separate eleven-method SynthCore-28 sensitivity comparison on 49 datasets. |

The primary methods are **Random, EZR, RRP, BS-LLM, AMP-2, AMP-3, AMP-4, HKMA-scout, HKMA-rag and HKMA-combined**. DAPR and full, fifteen-session SynthCore are retained for explicit legacy experiments and excluded from the current paper's statistical comparisons and default runs.

All RQ performance tables use **Chebyshev distance** of the returned configuration (lower is better). Search and final selection retain native d2h ranking; the external audit does not select a different winner. Scott–Knott groups are recomputed within each comparison scope using 512 bootstrap resamples, p < 0.05, |Cliff's delta| >= 0.147 and base seed 20261016. Counts include every member of the best group, rather than only a unique winner.

Dimensionality: low p < 6 (15 datasets), medium 6 <= p <= 11 (17), high p > 11 (17).

## Setup

Use Python 3.11 or 3.12 on Linux or macOS.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For analysis of existing current-protocol trials, `requirements-analysis.txt` suffices. Planning verifies all dataset hashes without calling a model:

```sh
python rerun.py --cohort automated
python rerun.py --cohort expert
```

## Run experiments

Set `OPENROUTER_API_KEY` in your environment. Retrieval methods require the embedding model to be downloaded once:

```sh
python prepare_retrieval.py --download
python rerun.py --cohort automated --output results/current --execute --allow-paid
python rerun.py --cohort expert --output results/current --execute --allow-paid
```

Run the additional sensitivity baseline in the same output directory:

```sh
python rerun.py --cohort automated --methods SynthCore-28 \
  --output results/current --execute --allow-paid
```

The default is 20 independent repeats. Successful repeats are skipped on continuation; `--retry-failed` makes a new, recorded attempt after a failure. `--repair-invalid` enables the retained bounded AMP-2/3 and HKMA correction helpers (and legacy DAPR corrections); extra calls and retries remain in the cost ledger. Results go to `results/current/trials.jsonl`.

Without `--execute`, every command only prints a plan. Model, decoding settings and the retrieval model revision are in `manifest.json`.

## Online evaluation budgets

| Method | Seeds | Scouting | Generated mappings | Sequential search | Nominal requests |
| --- | ---: | ---: | ---: | ---: | ---: |
| Random | 0 | 0 | 0 | 24 | 24 |
| EZR | 4 | 0 | 0 | 20 | 24 |
| BS-LLM, AMP-2/3/4, HKMA-rag, H-DKP | 4 | 0 | 4 | 16 | 24 |
| HKMA-scout, HKMA-combined | 4 | 10 | 4 | 6 | 24 |
| RRP | — | — | — | — | Depends on recursive partitioning |
| SynthCore-28 | 16 representatives | 0 | 12 | 0 | 28 |

Random samples without replacement. All current single-session methods use the same schema-aware optimizer: feature-only candidates map to nearest rows in the full observed table, and **all observed seeds, scouted rows and candidate matches** remain available to SMO. Repeated mappings consume requests but do not create new distinct labels. Intended better/poorer polarity does not replace measured outcomes.

`oracle_evaluations` records evaluation requests, `labeling_cost` records distinct observed-row tuples, and `nominal_labeling_budget` records the designed schedule. RRP exposes its native evaluation counter; distinct labels are unavailable rather than inferred from that counter.

SynthCore-28 restricts the authors' pinned Diversity ensemble (commit `eaec7012a1928c36e73ffcf7ec894c5e3e28bfe3`) to its first three sessions. It preserves initial partitioning, prompts, candidate parsing, retention and d2h selection, with no downstream SMO. The pinned source file is unchanged. The audit records actual representative counts and parsed candidates, which can differ from the nominal 16 + 3 x 4 schedule. Neither 28 requests nor the draft's observed mean of 26.31 distinct labels is imposed as a measured result.

## Expert replication and offline preparation

Supply independently reviewed, frozen rules through an external JSON mapping. One or two tracks can be supplied per dataset; the two POM3a tracks must remain separate. This package runs online optimization from frozen rules; experts collect and review those rules before execution.

```json
{
  "auto93": [{
    "expert_id": "reviewer1",
    "path": "/private/rules/auto93.md",
    "preparation": {
      "expert_contacts": 9,
      "generation_exchanges": 7,
      "distinct_labels": null
    }
  }]
}
```

`preparation` is optional. Its fields are `expert_contacts`, `generation_exchanges`, `nominal_benchmark_accesses`, `distinct_labels`, `llm_calls`, `total_tokens`, `api_cost_usd` and `calendar_days`. Missing values remain unknown. Generation exchanges exclude the first claim-review contact; nominal accesses are estimated as six per generation exchange (four seed accesses plus two expected-better mappings). Reusing seeds or matched rows means this estimate is an upper bound on distinct labels, not evidence of six new configurations per exchange.

The draft reports 36 generation exchanges and 216 nominal offline accesses across nine tracks, ranging from 6 to 48 per track. These one-time preparation costs remain separate from each 24-request online trial. Only qualitative expert-confirmed rules enter the frozen knowledge; offline configurations and scores must not be included in rule files. Do not put participant identities, consent records, or private correspondence in this public package.

```sh
python rerun.py --cohort expert --datasets auto93 --methods H-DKP \
  --expert-rules /private/expert-rules.json \
  --output results/current --execute --allow-paid
```

For a complete RQ3 study, provide rules for all eight expert datasets and run H-DKP for every selected track. Each rule file's hash and optional preparation metadata are recorded with its trials. RQ4 counts offline preparation once per frozen rule set, not once per repeat.

## RQ analyses

Use a new output directory for each analysis:

```sh
python rq1.py --trials results/current/trials.jsonl --output tables/rq1
python rq2.py --trials results/current/trials.jsonl --output tables/rq2
python rq3.py --trials results/current/trials.jsonl --output tables/rq3
python rq4.py --trials results/current/trials.jsonl --output tables/rq4
python rq4.py --trials results/current/trials.jsonl --cohort expert --output tables/rq4_expert
```

Each script writes CSV evidence and LaTeX tables:

| Analysis | Main output stems |
| --- | --- |
| RQ1 | `primary_low_label`, `membership` |
| RQ2 | `primary_low_label`, `dimensionality`, `membership` |
| RQ3 | `expert_low_label`, `expert_median_comparison`, `expert_cohort`, `membership` |
| RQ4 automated | `synthcore28_sensitivity`, `amp_design`, `operational_cost`, `labeling_cost_by_dataset` |
| RQ4 expert | `operational_cost`, `labeling_cost_by_dataset`, `offline_preparation` when supplied |

RQ1–3 require complete successful repeats in the selected scope. RQ4 writes observed costs even with incomplete coverage, but produces the sensitivity comparison only when all eleven methods have complete results. `coverage.csv` and `metadata.json` record missing evidence, ignored out-of-scope methods, protocol identity and statistical settings. The expert median table compares H-DKP with both BS-LLM and EZR using Chebyshev distance.

The current protocol is `paper-2026-11-13`. Earlier logs used different budgets, positional candidate handling or discarded observations and must be rerun; changing their method names or adding a protocol tag does not make them comparable. Fresh results may differ from the draft, and API generations and charges can vary. No published score or best-group count is hardcoded.

Run offline verification:

```sh
python -m unittest discover -s tests -v
```

Upstream license notices are retained in `licenses/`. Implementation changes and draft discrepancies are documented in `docs/paper-alignment.md`.
