---
source_id: postgres_wal
dataset_id: postgresql
source_url: https://www.postgresql.org/docs/16/runtime-config-wal.html
source_kind: official_product_documentation
source_status: public_html_checked
---

# PostgreSQL write-ahead-log settings

The PostgreSQL 16 manual describes `fsync` as a durability mechanism: disabling
it can make a database unrecoverable after a crash. `synchronous_commit`
controls when a commit is acknowledged relative to WAL flushing; disabling
the wait can lose recent acknowledged transactions after a crash without
necessarily corrupting the database. `full_page_writes` writes full page
images after checkpoints to protect recovery from partial page writes.
These are setting semantics and tradeoffs, **not** a claim that the benchmark
ran PostgreSQL 16 or that any switch value is safe for production use.
