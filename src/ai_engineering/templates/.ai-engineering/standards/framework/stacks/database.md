# Framework Database Cross-Cutting Standard

## Update Metadata

- Rationale: establish SQL, data modeling, and migration safety patterns across all stacks.
- Expected gain: consistent database design, migration safety, and query optimization patterns.
- Potential impact: any project with database components gets enforceable data management patterns.

## Standard Type

Cross-cutting standard. Applies alongside a primary stack standard. Does not define its own enforcement gates.

## Scope

- Relational databases: SQL Server, PostgreSQL, MySQL/MariaDB, SQLite.
- ORMs and query builders: Entity Framework, Prisma, Drizzle, TypeORM, SQLAlchemy, Diesel.
- Schema versioning and migration safety.
- Query optimization and indexing.
- Connection management and pooling.
- Data lifecycle: retention, archival, deletion.

## Schema Design Patterns

- **Naming**: lowercase snake_case for tables and columns. Plural table names (`users`, `orders`).
- **Primary keys**: prefer UUID or ULID for distributed systems. Auto-increment for simple apps.
- **Foreign keys**: always declare with explicit ON DELETE/ON UPDATE behavior.
- **Indexes**: index all foreign keys. Index columns used in WHERE, JOIN, ORDER BY. Composite indexes in selectivity order.
- **Constraints**: NOT NULL by default. Add CHECK constraints for domain rules. Unique constraints on business keys.
- **Timestamps**: `created_at` and `updated_at` on all tables. UTC timezone. Database-level defaults.
- **Soft delete**: use `deleted_at` timestamp if business requires recoverability. Add partial index on non-deleted rows.

## Migration Safety

- **Forward-only**: migrations must be additive and non-destructive in production.
- **Backward compatibility**: new column → deploy code → backfill → remove old column. Never rename/drop columns in a single migration.
- **Expand-contract pattern**: for breaking schema changes. Expand (add new), migrate data, contract (remove old).
- **Testing**: run migrations against a copy of production schema. Verify both up and down migrations.
- **Rollback**: every migration must have a rollback script. Test rollback in staging.
- **Locking**: avoid long-running ALTER TABLE in production (use pt-online-schema-change for MySQL, CREATE INDEX CONCURRENTLY for PostgreSQL).
- **Sequencing**: migrations numbered sequentially with timestamps. Never reorder or modify committed migrations.

## Query Optimization

- **EXPLAIN before deploy**: review query plans for any new or modified query.
- **N+1 prevention**: use JOINs or eager loading. ORM-specific: `Include()` (EF), `include:` (Prisma), `joinedLoad` (SQLAlchemy).
- **Pagination**: keyset pagination (WHERE id > last_id) over OFFSET for large tables.
- **Projections**: SELECT only needed columns. Avoid `SELECT *` in application code.
- **Parameterized queries**: always use parameterized queries. Never concatenate user input into SQL.
- **Batch operations**: batch INSERTs and UPDATEs. Avoid row-by-row processing.

## Connection Management

- **Connection pooling**: mandatory for production. Configure pool size based on workload.
- **Pool settings**: min connections, max connections, idle timeout, connection lifetime.
- **Health checks**: validate connections before use (test-on-borrow).
- **Retry logic**: retry transient failures with exponential backoff and jitter.
- **Transaction scope**: keep transactions short. No user interaction within transactions.

## Data Lifecycle

- **Retention policy**: define retention periods per data category (user data, logs, analytics).
- **Archival**: move cold data to archive tables or cold storage. Maintain queryability if needed.
- **Deletion**: hard delete only after retention period. Cascade deletes documented and tested.
- **GDPR/privacy**: support data export and deletion requests. Anonymize rather than delete when audit trail required.
- **Backups**: automated daily backups with point-in-time recovery. Test restore procedures quarterly.

## ORM-Specific Patterns

### Entity Framework (.NET)

- Code-first with migrations. `Add-Migration`, `Update-Database`.
- Use `IQueryable` for composable queries. Materialize with `ToListAsync()` at boundary.
- Configure relationships in `OnModelCreating` using fluent API.

### Prisma (TypeScript)

- `schema.prisma` as single source of truth. `prisma migrate dev` for development.
- Use `prisma generate` to update client after schema changes.
- Relations: use `@relation` with explicit foreign key fields.

### SQLAlchemy (Python)

- Declarative models with `MappedAsDataclass` (2.0+ style).
- Alembic for migrations. `alembic revision --autogenerate`.
- Use `select()` construct for queries (2.0 style), not legacy `session.query()`.

## Update Contract

This file is framework-managed and may be updated by framework releases.
