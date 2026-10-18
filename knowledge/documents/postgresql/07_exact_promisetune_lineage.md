---
source_id: promisetune_postgresql_data
dataset_id: postgresql
source_url: https://github.com/ideas-labo/PromiseTune/blob/main/Data/PostgreSQL.csv
source_kind: primary_dataset_repository
source_status: source_rows_verified_against_local_moot
---

# PostgreSQL table lineage

The PromiseTune authors publish a PostgreSQL configuration table. Its 19,008
data rows match the bundled MOOT `optimize/systems/PostgreSQL.csv` data rows
exactly and in the same order. The MOOT copy changes only the header spelling:
the source uses lower-camel-case memory names and `$<performance`, while MOOT
uses capitalized memory names and `Performance-`.

This establishes row provenance for the frozen MOOT PostgreSQL table. The
source header names `sharedBuffers`, `tempBuffers`, and `workMem`, but does not
state their units. The row match also does not establish a PostgreSQL server
version, workload, hardware setup, or whether the numeric 0/1 switches are
recoverable deployment settings. Official PostgreSQL documentation explains
what these settings mean in a running server; it does not decode this table's
numeric memory fields. No data rows, outcomes, or favored settings are copied
into this retrieval note.
