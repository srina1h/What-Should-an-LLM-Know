---
source_id: sklearn_forest
dataset_id: health_closed_issues
source_url: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html
source_kind: official_library_documentation
source_status: public_html_checked
---

# RandomForestRegressor parameter meanings

The scikit-learn reference defines `n_estimators` as the forest's tree count,
`min_samples_leaf` as the minimum training samples permitted in a leaf,
`min_impurity_decrease` as the minimum split improvement, and `max_depth` as a
tree-depth limit. `criterion` selects the split-quality rule. These are useful
semantic descriptions for the similarly named benchmark fields. The current
online library version need not be the version used to create the study data;
do not transfer library defaults or categorical code mappings into the CSV.
