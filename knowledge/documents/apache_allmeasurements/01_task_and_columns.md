---
source_id: moot_catalog_and_csv
dataset_id: apache_allmeasurements
source_path: third_party/moot/optimize/config/README.md
dataset_path: data/config/Apache_AllMeasurements.csv
source_kind: repository_documentation_and_csv_header
source_status: locally_available
---

# Apache_AllMeasurements: task and column map

The MOOT catalog associates this configuration task with Apache. It does not document every switch, valid combination, performance unit, or benchmark export transformation.

The local CSV has 192 data rows. Its input column names are: base, hostnameLookups, keepAlive, enableSendfile, followSymLinks, accessLog, extendedStatus, inMemory, handle. Its objective column names are: Performance-. In the repository convention, a trailing + means maximize and a trailing - means minimize. These names and directions come from the CSV header and do not establish feature semantics or measurement units. Do not infer causal effects or undocumented constraints from this note.
