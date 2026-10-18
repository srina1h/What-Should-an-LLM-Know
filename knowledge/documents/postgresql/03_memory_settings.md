---
source_id: postgres_resources
dataset_id: postgresql
source_url: https://www.postgresql.org/docs/16/runtime-config-resource.html
source_kind: official_product_documentation
source_status: public_html_checked
---

# PostgreSQL memory-setting roles

The PostgreSQL 16 manual describes `shared_buffers` as memory for the server's
shared buffer cache. `temp_buffers` limits per-session buffers used for
temporary tables. `work_mem` is a base limit for a query operation such as a
sort or hash before temporary disk files are used; multiple operations and
sessions can each consume memory. Bare values in PostgreSQL's configuration
have parameter-specific implied units. The manual's units and recommendations
must **not** be imposed on the benchmark's `SharedBuffers`, `TempBuffers`, or
`WorkMem` numbers without an export mapping.
