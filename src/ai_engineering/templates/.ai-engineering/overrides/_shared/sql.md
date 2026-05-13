<!-- source: SQL cross-cutting v1 (spec-133 D-133-12) -->

# SQL — Cross-Cutting Conventions

SQL never lives standalone. It coexists with a host stack
(python/java/ruby/php/...). The conventions below apply regardless of host.

## Querying

- **Parameterise everything.** No string-interpolation of user input.
- **Use CTEs** for non-trivial joins; named subqueries beat nested anonymous selects.
- **EXPLAIN PLAN** any join over >100k rows before merging.
- Indexed lookups: prefer single-column where possible; multi-column
  indexes pay off only for the leading-prefix pattern.

## Migrations

- Migrations are **immutable** once shipped. Never edit a deployed migration.
- **Backward-compatible** by default: add column nullable -> backfill -> add
  NOT NULL constraint -> drop old column (4 migrations, not 1).
- **No downtime**: zero-downtime migrations only. Lock-acquiring DDL
  (ADD CONSTRAINT, CREATE INDEX) MUST use `CONCURRENTLY` (Postgres) /
  `ONLINE` (MySQL 8+) variants.

## Security floor

- No `GRANT ALL` to application roles. Granular GRANTs per table.
- Connection pools: bounded; never trust client-supplied pool sizing.
- Audit logs on schema changes (DDL); not optional for regulated industries.

## Tooling

- **sqlfluff** for lint + format. Project config in `.sqlfluff`.
- **pg_dump / mysqldump** for backup orchestration; never ad-hoc shell pipes.
