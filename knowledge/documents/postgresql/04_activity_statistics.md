---
source_id: postgres_statistics
dataset_id: postgresql
source_url: https://www.postgresql.org/docs/16/runtime-config-statistics.html
source_kind: official_product_documentation
source_status: public_html_checked
---

# PostgreSQL activity and count tracking

In the PostgreSQL 16 manual, `track_activities` enables monitoring of commands
currently being run. `track_counts` enables cumulative database-activity
statistics used by features such as autovacuum. These descriptions identify
the roles of the benchmark's similarly named switches. They do not establish
the effect on the benchmark workload or the performance of a particular
configuration.
