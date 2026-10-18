---
source_id: moot_catalog_and_csv
dataset_id: auto93
source_path: third_party/moot/optimize/misc/README.md
dataset_path: data/misc/auto93.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# auto93: task and column map

The MOOT catalog describes auto93 as a car-performance task included for debugging methods. It is not a software-engineering configuration task.

The local CSV has 398 data rows. Its input column names are: Clndrs, Volume, Model, origin. Its objective column names are: Lbs-, Acc+, Mpg+. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
