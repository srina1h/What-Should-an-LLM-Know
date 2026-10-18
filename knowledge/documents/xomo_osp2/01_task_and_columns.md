---
source_id: moot_catalog_and_csv
dataset_id: xomo_osp2
source_path: third_party/moot/optimize/process/README.md
dataset_path: data/process/xomo_osp2.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# xomo_osp2: task and column map

The MOOT catalog describes XOMO as a COCOMO-like software-process simulation with risk, effort, defect, and duration goals. Flight, Ground, OSP, and OSP2 are scenario variants. It does not decode transformed CSV ratings or all driver units.

The local CSV has 10000 data rows. Its input column names are: DATA, AA, ACAP, AEXP, B, DOCU, ETAT, KLOC, PCAP, PCON, PMAT, PR, PREC, PVOL, RELY, RESL, RUSE, SCED, SITE, STOR, TEAM, TIME, TOOL. Its objective column names are: EFFORT-, MONTHS-, DEFECTS-, RISKS-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
