---
source_id: moot_catalog_and_csv
dataset_id: ss_j
source_path: third_party/moot/optimize/config/README.md
dataset_path: data/config/SS-J.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# SS-J: task and column map

The MOOT catalog identifies this as a software-configuration task. It does not identify the specific software system for this SS variant or define all settings and performance units.

The local CSV has 3840 data rows. Its input column names are: Spouts, Max_spout, Sorters, Emit_freq, Chunk_size, Message_size. Its objective column names are: Throughput+, Latency-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
