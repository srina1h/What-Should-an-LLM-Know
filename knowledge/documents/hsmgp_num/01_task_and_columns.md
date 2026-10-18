---
source_id: moot_catalog_and_csv
dataset_id: hsmgp_num
source_path: third_party/moot/optimize/config/README.md
dataset_path: data/misc/HSMGP_num.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# HSMGP_num: task and column map

The MOOT catalog associates this configuration task with HSMGP. It does not document every switch, valid combination, performance unit, or benchmark export transformation.

The local CSV has 3456 data rows. Its input column names are: smoother_JAC, smoother_GSAC, smoother_GSACBE, smoother, cGS_IP_CG, cGS_RED_AMG, cGS_IP_AMG, smoother_GS, cGS, smoother_GSRB, smoother_GSRBAC, Pre, Post, NumCore. Its objective column names are: AverageTimePerIteration-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
