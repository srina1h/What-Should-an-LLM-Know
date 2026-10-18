---
source_id: moot_catalog_and_csv
dataset_id: ss_n
source_path: third_party/moot/optimize/config/README.md
dataset_path: data/config/SS-N.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# SS-N: task and column map

The MOOT catalog identifies this as a software-configuration task. It does not identify the specific software system for this SS variant or define all settings and performance units.

The local CSV has 53662 data rows. Its input column names are: No_mbtree, No_asm, No_cabac, No_scenecut, Aq_strength, Bframes, Qcomp, Qp, Ref, Rc_lookahead, B_bias, Threads, Keyint, Crf, Scenecut, Seek, Ipratio. Its objective column names are: PSNR-, Energy-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
