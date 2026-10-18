---
source_id: moot_catalog_and_csv
dataset_id: x264_allmeasurements
source_path: third_party/moot/optimize/config/README.md
dataset_path: data/config/X264_AllMeasurements.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# X264_AllMeasurements: task and column map

The MOOT catalog associates this configuration task with x264. It does not document every switch, valid combination, performance unit, or benchmark export transformation.

The local CSV has 1152 data rows. Its input column names are: no_asm, no_8x8dct, no_cabac, no_deblock, no_fast_pskip, no_mbtree, no_mixed_refs, no_weightb, rc_lookahead, rc_lookahead_20, rc_lookahead_40, rc_lookahead_60, ref, ref_1, ref_5, ref_9. Its objective column names are: Performance-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
