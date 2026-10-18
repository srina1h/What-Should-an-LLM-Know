---
source_id: moot_health_data_readme
dataset_id: life_expectancy
source_path: third_party/moot/optimize/health_data/README.md
source_url: https://github.com/timm/moot/blob/main/optimize/health_data/README.md
source_kind: repository_documentation
source_status: locally_available
---

# MOOT Life Expectancy task

MOOT describes 2,938 country-year records from 2000 to 2015, with 20 input
features and two development-related outcomes. The inputs cover country and
year, mortality, disease and immunization indicators, body-mass and thinness
measures, expenditure, GDP, and population. In this frozen CSV,
`Life_expectancy` is an input feature, while
`Income_composition_of_resources+` and `Schooling+` are the two objectives
to maximize. The `+` directions come from the benchmark headers.

The short MOOT description does not establish the source, exact units, or
preprocessing of every field. Country-year attributes are observations, not
independent policy controls. Do not infer causal effects or numeric constraints
from this note.
