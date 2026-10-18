---
source_id: moot_catalog_and_csv
dataset_id: pom3a
source_path: third_party/moot/optimize/process/README.md
dataset_path: data/process/pom3a.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# pom3a: task and column map

The MOOT catalog describes POM3 as an agile-project simulation balancing completion, idle time, and cost. Scenarios A through D vary in complexity. The catalog does not prove that every input is a directly controllable staffing decision.

The local CSV has 500 data rows. Its input column names are: Culture, Criticality, Criticality Modifier, Initial Known, Inter-Dependency, Dynamism, Size, Plan, Team Size. Its objective column names are: Cost-, Score-, Idle-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
