---
source_id: moot_catalog_and_csv
dataset_id: ss_r
source_path: third_party/moot/optimize/config/README.md
dataset_path: data/config/SS-R.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# SS-R: task and column map

The MOOT catalog identifies this as a software-configuration task. It does not identify the specific software system for this SS variant or define all settings and performance units.

The local CSV has 3008 data rows. Its input column names are: twoPass, quality, bestQuality, goodQuality, rtQuality, constantBitrate, autoAltRef, noAltRef, allowResize, columnTiling, rowTiling, Threads, ArnrMaxFrames, ArnrStrength. Its objective column names are: Performance-, Cpu-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
