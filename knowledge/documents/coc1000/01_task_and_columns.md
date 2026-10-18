---
source_id: moot_catalog_and_csv
dataset_id: coc1000
source_path: third_party/moot/optimize/process/README.md
dataset_path: data/process/coc1000.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# coc1000: task and column map

The MOOT catalog describes COC1000 as a COCOMO-like software-process model that precedes XOMO. Its short description does not fully define this export’s driver scales or objectives.

The local CSV has 1000 data rows. Its input column names are: ACAP, ARCH, DATA, DOCU, PCAP, PCON, PMAT, PREC, PVOL, RELY, RUSE, SCED, SITE, STOR, TEAM, TIME, TOOL. Its objective column names are: LOC+, AEXP-, PLEX-, RISK-, EFFORT-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
