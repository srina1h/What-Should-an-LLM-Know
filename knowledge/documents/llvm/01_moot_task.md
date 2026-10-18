---
source_id: moot_systems_readme
dataset_id: llvm
source_path: third_party/moot/optimize/systems/README.md
source_url: https://github.com/timm/moot/blob/main/optimize/systems/README.md
source_kind: repository_documentation
source_status: locally_available
---

# MOOT LLVM task

MOOT attributes its LLVM configuration table to PromiseTune and identifies
1,025 rows, ten inputs, and one performance outcome. The frozen CSV names ten
LLVM pass-selection fields: `gvn`, `instcombine`, `inline`,
`jump_threading`, `simplifycfg`, `sccp`, `print_used_types`, `ipsccp`,
`iv_users`, and `licm`. Its `PERF-` header says lower recorded performance
values are preferred.

The catalog entry does not establish what execution was timed, the workload
or hardware, or the order in which selected passes ran. Treating each 0/1
field as an unselected/selected indicator is a study assumption, not an
independently verified description of the original harness.
