---
source_id: moot_catalog_and_csv
dataset_id: healthcloseisses12mths0001_hard
source_path: third_party/moot/optimize/hpo/README.md
dataset_path: data/hpo/healthCloseIsses12mths0001-hard.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# healthCloseIsses12mths0001-hard: task and column map

The MOOT catalog describes this family as random-forest hyperparameter configurations for predicting open-source project activity over 12 months. This file concerns closed issues. The catalog does not define the exported ACC+ formula or every hyperparameter coding.

The local CSV has 10000 data rows. Its input column names are: N_estimators, criterion, Min_sample_leaves, Min_impurity_decrease, Max_depth. Its objective column names are: PRED40+, MRE-, ACC+. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
