---
source_id: nisneak_reproduction
dataset_id: health_closed_issues
source_url: https://github.com/zxcv123456qwe/niSneak
source_kind: author_reproduction_repository
source_status: public_source_files_checked
---

# Project-health study reproduction materials

The authors' reproduction repository identifies closed issues as one of three
project-health targets and provides separate issue data and optimization
notebooks. Its health-data README says its binary files are processed versions
of original data, with 16 binary columns representing one original numerical
column. This is useful provenance context for the study, not a decoder for the
frozen `Health-ClosedIssues0001.csv` hyperparameter table.

The authors' [Hyperopt issues notebook](https://github.com/zxcv123456qwe/niSneak/blob/main/baselines/hyperopt/Hyperopt%20Issues.ipynb)
uses random-forest regression with named `squared_error` and `absolute_error`
criterion choices. It computes an accuracy-like quantity from prediction MAE
relative to a baseline MAE. The notebook is a related implementation, but no
producer script or row-level mapping to the frozen MOOT table was found in this
bounded check. Do not identify the MOOT table's `ACC+` with that notebook's
quantity or infer the original training subset from the table's row count.

The frozen MOOT table itself spells its criterion labels as
`squared_error`, `absolute_error`, and `poisson`; this is a schema observation,
not evidence that the notebook produced those rows. No benchmark outcomes or
preferred hyperparameter settings are included here.
