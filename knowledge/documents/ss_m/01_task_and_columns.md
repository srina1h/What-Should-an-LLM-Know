---
source_id: moot_catalog_and_csv
dataset_id: ss_m
source_path: third_party/moot/optimize/config/README.md
dataset_path: data/config/SS-M.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# SS-M: task and column map

The MOOT catalog identifies this as a software-configuration task. It does not identify the specific software system for this SS variant or define all settings and performance units.

The local CSV has 864 data rows. Its input column names are: compressed_script, encryption, crypt_aes, crypt_blowfish, transaction_control, txc_mvlocks, txc_mvcc, txc_locks, table_type, memory_tables, cached_tables, small_cache, large_cache, logging, detailed_logging, no_write_delay, small_log. Its objective column names are: Benchmark-energy-, Benchmark-time-, Benchmark-cpu-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
