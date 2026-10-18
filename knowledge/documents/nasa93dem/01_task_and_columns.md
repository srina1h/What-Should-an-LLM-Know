---
source_id: moot_catalog_and_csv
dataset_id: nasa93dem
source_path: third_party/moot/optimize/process/README.md
dataset_path: data/process/nasa93dem.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# nasa93dem: task and column map

The MOOT catalog describes nasa93dem as a COCOMO-like model derived from NASA project data. The catalog does not map every encoded column to a measured unit.

The local CSV has 93 data rows. Its input column names are: prec, flex, resl, team, pmat, rely, data, cplx, ruse, docu, time, stor, pvol, acap, pcap, pcon, apex, plex, ltex, tool, site, sced. Its objective column names are: Kloc+, Effort-, Defects-, Months-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
