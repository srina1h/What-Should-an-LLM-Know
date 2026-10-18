---
source_id: moot_catalog_and_csv
dataset_id: wine_quality
source_path: third_party/moot/optimize/misc/README.md
dataset_path: data/misc/Wine_quality.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# Wine_quality: task and column map

The MOOT catalog describes Wine Quality as a non-software debugging task. The catalog does not establish that the benchmark columns are controllable interventions.

The local CSV has 1599 data rows. Its input column names are: Fixedacidity, Volatileacidity, Citricacid, Residualsugar, CL, FreeSO2, TotalS02, Density, PH, Sulphates. Its objective column names are: Alcohol-, Quality+. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
