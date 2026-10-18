---
source_id: moot_catalog_and_csv
dataset_id: ss_x
source_path: third_party/moot/optimize/config/README.md
dataset_path: data/config/SS-X.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# SS-X: task and column map

The MOOT catalog identifies this as a software-configuration task. It does not identify the specific software system for this SS variant or define all settings and performance units.

The local CSV has 86058 data rows. Its input column names are: opt_useAddressPrecalc, opt_vectorize, simd_avoidUnaligned, data_alignFieldPointers, opt_unroll_interleave, opt_unroll, no_explorationId, explorationId, poly_tileSize_x, poly_tileSize_y, poly_tileSize_z. Its objective column names are: Compile-performance-, Fixed-compile-cpu-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
