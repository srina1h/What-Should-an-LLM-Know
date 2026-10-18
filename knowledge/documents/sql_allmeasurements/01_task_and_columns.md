---
source_id: moot_catalog_and_csv
dataset_id: sql_allmeasurements
source_path: third_party/moot/optimize/config/README.md
dataset_path: data/config/SQL_AllMeasurements.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# SQL_AllMeasurements: task and column map

The MOOT catalog associates this configuration task with SQL (the CSV field names include SQLite options). It does not document every switch, valid combination, performance unit, or benchmark export transformation.

The local CSV has 4653 data rows. Its input column names are: operatingSystemCharacteristics, sqlite_secure_delete, chooseSQLITE_TEMP_STORE, sQLITE_TEMP_STOREzero, sQLITE_TEMP_STOREone, sQLITE_TEMP_STOREtwo, sQLITE_TEMP_STOREthree, enableFeatures, sQLITE_ENABLE_ATOMIC_WRITE, sQLITE_ENABLE_STAT2, disableFeatures, sQLITE_DISABLE_LFS, sQLITE_DISABLE_DIRSYNC, omitFeatures, sQLITE_OMIT_BETWEEN_OPTIMIZATIO0, sQLITE_OMIT_BTREECOUNT, sQLITE_OMIT_LIKE_OPTIMIZATIO0, sQLITE_OMIT_LOOKASIDE, sQLITE_OMIT_OR_OPTIMIZATIO0, sQLITE_OMIT_QUICKBALANCE, sQLITE_OMIT_SHARED_CACHE, sQLITE_OMIT_XFER_OPT, options, setAutoVacuum, autoVacuumOff, autoVacuumO0, setCacheSize, standardCacheSize, lowerCacheSize, higherCacheSize, lockingMode, exclusiveLock, normalLockingMode, pageSize, standardPageSize, lowerPageSize, higherPageSize, highestPageSize. Its objective column names are: Performance-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
