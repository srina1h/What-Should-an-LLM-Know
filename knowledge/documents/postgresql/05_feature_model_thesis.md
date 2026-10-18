---
source_id: feature_model
dataset_id: postgresql
source_url: https://www.se.cs.uni-saarland.de/theses/NiklasWernerMA.pdf
source_kind: primary_research_thesis
source_status: public_pdf_checked
---

# Werner's PostgreSQL feature model

Werner's 2019 thesis documents a PostgreSQL feature model with an abstract
root node, boolean switches, and three numeric memory options. Its own case
study specifies a finite 864-configuration space and uses PolePosition 0.6.0
for workload measurement. It describes numeric units within **that thesis's**
feature model. The MOOT PostgreSQL CSV has a different row count, so the
thesis's discrete choices and units cannot yet be treated as an established
decoder for the benchmark export. The root feature is a structural marker in
the source model, not ordinary memory or durability tuning.
