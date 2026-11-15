# What Should an LLM Know?

Replication code for *What Should an LLM Know? Knowledge-Guided Warm Starts for Software Optimization*

Includes 49 benchmark datasets and eight expert-study datasets. Three datasets are shared, giving **54 unique CSV files**. Every method uses the same included dataset version; paths and hashes are in `manifest.json`.

## Research questions

| RQ | Question | Comparison |
| --- | --- | --- |
| RQ1 | With only 24 labels, can domain knowledge help an LLM propose better initial configurations? | Ten automated methods on 49 datasets; overall best-group counts and mean Chebyshev distance. |
| RQ2 | Does increasing the number of configuration parameters change which kinds of knowledge help? | The same ten-method groups, summarized by dimensionality. |
| RQ3 | Does human review of the LLM's domain rules help? | H-DKP plus the ten automated methods on eight expert-study datasets; independent pools for the two POM3a tracks. |
| RQ4 | What does checked knowledge cost? | Online labels, inference costs and offline expert preparation; separate eleven-method SynthCore-28 sensitivity comparison on 49 datasets. |

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

The default is 20 independent repeats. Successful repeats are skipped on continuation; `--retry-failed` makes a new attempt after a failure. Results go to `results/current/trials.jsonl`.

Without `--execute`, every command only prints a plan.

## RQ analyses

Use a new output directory for each analysis:

```sh
python rq1.py --trials results/current/trials.jsonl --output tables/rq1
python rq2.py --trials results/current/trials.jsonl --output tables/rq2
python rq3.py --trials results/current/trials.jsonl --output tables/rq3
python rq4.py --trials results/current/trials.jsonl --output tables/rq4
python rq4.py --trials results/current/trials.jsonl --cohort expert --output tables/rq4_expert
```
