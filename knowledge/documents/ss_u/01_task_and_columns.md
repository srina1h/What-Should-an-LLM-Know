---
source_id: moot_catalog_and_csv
dataset_id: ss_u
source_path: third_party/moot/optimize/config/README.md
dataset_path: data/config/SS-U.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# SS-U: task and column map

The MOOT catalog identifies this as a software-configuration task. It does not identify the specific software system for this SS variant or define all settings and performance units.

The local CSV has 4608 data rows. Its input column names are: no_asm, no_8x8dct, no_cabac, no_deblock, no_fast_pskip, no_mbtree, no_mixed_refs, no_weightb, rc_lookahead, rc_lookahead_20, rc_lookahead_40, rc_lookahead_60, ref, ref_1, ref_5, ref_9, core, core1, core2, core3, core4. Its objective column names are: Benchmark-iperf-, Benchmark-cpu-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
