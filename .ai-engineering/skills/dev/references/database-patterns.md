# Database Patterns

On-demand reference for database design, migrations, and operations. See also `standards/framework/stacks/database.md` for enforceable rules.

## Entity Modeling

- Name tables in plural lowercase snake_case (`users`, `order_items`).
- Primary keys: UUID/ULID for distributed, auto-increment for simple.
- Declare foreign keys with explicit `ON DELETE`/`ON UPDATE`.
- Add `created_at` and `updated_at` (UTC, database defaults) on all tables.
- Soft delete with `deleted_at` timestamp + partial index on non-deleted rows.
- Domain invariants as CHECK constraints (e.g., `CHECK (quantity > 0)`).

## Index Strategy

- Index all foreign keys.
- Index columns used in `WHERE`, `JOIN`, `ORDER BY` frequently.
- Composite indexes: most selective column first.
- Partial indexes for filtered queries (e.g., `WHERE deleted_at IS NULL`).
- Covering indexes for read-heavy queries (include columns in index).
- Monitor: identify slow queries → EXPLAIN → add targeted index.

## Transaction Boundaries

- Keep transactions short — no user interaction within a transaction.
- Use optimistic locking (version column) for concurrent updates.
- Idempotent operations: use `INSERT ... ON CONFLICT` or `MERGE`.
- Explicit isolation levels: `READ COMMITTED` default, `SERIALIZABLE` for critical.
- Retry transient failures with exponential backoff and jitter.

## Migration Safety

### Forward-Only Migrations

- Additive: add column, add table, add index.
- Avoid: rename column, drop column, change column type (in single migration).
- Expand-contract pattern for breaking changes:
  1. Expand: add new column/table.
  2. Migrate: backfill data with script.
  3. Deploy: code reads from new, writes to both.
  4. Contract: remove old column/table (separate migration).

### Locking Considerations

- PostgreSQL: `CREATE INDEX CONCURRENTLY` avoids table lock.
- MySQL: `pt-online-schema-change` for large ALTER TABLE.
- SQL Server: `ONLINE = ON` for index operations.
- Test migration duration on production-size data in staging.

### Rollback

- Every migration has a down script.
- Test rollback in staging before production.
- For data-destructive changes: backup before migration, verify before cleanup.

## Connection Management

- Pool size: tune based on workload (`max_connections / app_instances`).
- Idle timeout: release idle connections after 30-60 seconds.
- Connection lifetime: rotate connections every 30-60 minutes.
- Health checks: validate connections before use.
- Connection string: from environment variable or secrets manager, never hardcoded.

## Query Optimization

- Always run `EXPLAIN` / `EXPLAIN ANALYZE` for new queries.
- Prevent N+1: use JOINs or ORM eager loading.
- Keyset pagination for large datasets (not `OFFSET`).
- Project specific columns only (no `SELECT *` in app code).
- Parameterized queries always (prevent SQL injection).
- Batch operations: batch `INSERT`, `UPDATE`, `DELETE`.

## Data Lifecycle

- Define retention periods per data category.
- Archive cold data: move to archive tables or cold storage.
- GDPR/privacy: support export and deletion requests.
- Anonymization: replace PII with tokens when audit trail required.
- Automated daily backups with point-in-time recovery.
- Test restore procedures quarterly.

## ORM Quick Reference

| ORM | Migration | Eager Load | Query Builder |
|-----|-----------|------------|--------------|
| Entity Framework | `Add-Migration` / `Update-Database` | `.Include()` | LINQ |
| Prisma | `prisma migrate dev` | `include:` | Prisma Client |
| SQLAlchemy | `alembic revision --autogenerate` | `joinedload()` | `select()` 2.0 style |
| TypeORM | `migration:generate` | `relations:` / `leftJoinAndSelect` | QueryBuilder |
| Drizzle | `drizzle-kit push` | `with:` | Type-safe SQL |
| Diesel | `diesel migration run` | `belonging_to` | DSL macros |
