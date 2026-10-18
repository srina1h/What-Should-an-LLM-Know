# What Should an LLM Know?

Reproduction code for *What Should an LLM Know? Knowledge-Guided Warm Starts for Software Optimization* 

Includes the 49 benchmark datasets and eight expert-study datasets. Three datasets are shared, so there are **54 unique CSV files**. Every method uses the same included version of its dataset. Dataset paths and hashes are in `manifest.json`.

## Setup

Use Python 3.11 or 3.12 on Linux or macOS.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python verify_package.py
```

For analysis of existing trial results only, install `requirements-analysis.txt` instead.

## Run experiments

Print a plan without making API calls:

```sh
python rerun.py --cohort automated
python rerun.py --cohort expert
```

Set `OPENROUTER_API_KEY` in your environment, then run the benchmark. The retrieval variants need the embedding model downloaded once:

```sh
python prepare_retrieval.py --download
python rerun.py --cohort automated --output results/fresh --execute --allow-paid
```

To run the comparison methods on the eight expert-study datasets:

```sh
python rerun.py --cohort expert --output results/fresh --execute --allow-paid
```

The default is 20 repeats. Successful trials are skipped on continuation. `--retry-failed` permits a new attempt after a failure; `--repair-invalid` enables bounded output corrections. Corrections and retries are included in recorded costs. Results are written to `results/fresh/trials.jsonl`.

## Expert replication

An external JSON file maps dataset IDs to one or two rule files per selected dataset. For example:

```json
{"auto93": [{"expert_id": "reviewer1", "path": "/private/rules/auto93.md"}]}
```

Run H-DKP on the selected datasets using that file:

```sh
python rerun.py --cohort expert --datasets auto93 --methods H-DKP \
  --expert-rules /private/expert-rules.json --output results/fresh --execute --allow-paid
```

## RQ analyses

Each script prints results and writes CSV and LaTeX tables. Use a new output directory for each analysis.

```sh
python rq1.py --trials results/fresh/trials.jsonl --output tables/rq1
python rq2.py --trials results/fresh/trials.jsonl --output tables/rq2
python rq3.py --trials results/fresh/trials.jsonl --output tables/rq3
python rq4.py --trials results/fresh/trials.jsonl --output tables/rq4
```

- **RQ1, Tables 3–5:** overall best-group counts, mean scores, and the DAPR-excluded comparison.
- **RQ2, Table 6:** results by low, medium, and high dimensionality.
- **RQ3, Tables 1 and 7:** expert-cohort description and comparisons using independently collected expert trials.
- **RQ4, Tables 2 and 8:** AMP stage definitions and measured calls, tokens, API charges, wall time, and labeling cost.

Run tests with `python -m unittest discover -s tests -v`.
