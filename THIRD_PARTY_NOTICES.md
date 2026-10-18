# Source attribution

The authors of the study are Srinath Srinivasan and Tim Menzies.

- `src/utils/ezr.py`, the retained warm-start and clustering implementations,
  prompts, and API-wrapper classes derive from the repository's `lazy_llm`
  infrastructure. Its MIT notice is in `licenses/lazy-llm-LICENSE`.
- The tabular task files derive from the repository's MOOT
  inputs. The MOOT MIT notice is in `licenses/MOOT-LICENSE.md`. Individual source
  datasets retain their source terms and provenance.
- `btp/` contains the study's knowledge-construction strategies and prompts.
- `experiments/remaining_methods/` contains extracted study evaluator, retrieval,
  and bounded-correction code.
- `stats/scott_knott.py` is the study's validated grouping implementation.

Upstream license notices are retained in `licenses/`. Individual source datasets retain their source terms.
