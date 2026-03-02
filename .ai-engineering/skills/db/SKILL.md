---
name: db
description: "Design database schemas, plan safe migrations, optimize queries, and manage data lifecycle with rollback procedures."
version: 1.0.0
tags: [database, sql, migration, schema, optimization, data-lifecycle]
metadata:
  ai-engineering:
    scope: read-write
    token_estimate: 800
---

# Database Operations

## Purpose

Database operations skill covering schema design, migration safety, query optimization, connection pool tuning, and data lifecycle management. Ensures database changes are safe, reversible, and performance-conscious. Works across ORMs (Entity Framework, Prisma, SQLAlchemy, TypeORM, Drizzle, Diesel) and databases (PostgreSQL, SQL Server, MySQL, SQLite).

## Trigger

- Command: agent invokes database-ops skill or user requests database work.
- Context: new schema design, migration planning, query optimization, data lifecycle policy, performance tuning.

## When NOT to Use

- **Data modeling decisions** (entity relationships, normalization trade-offs) — use `data-model` for modeling procedures.
- **Security of database access** — use `sec-review` for access control review.
- **Infrastructure provisioning** (database server setup) — use `infra` for server provisioning.
- **General code review** — use `code-review` for application code.

## Procedure

1. **Detect database stack** — identify ORM, database engine, and migration tool.
   - Check project files: `schema.prisma`, `*.csproj` (EF), `alembic.ini`, `ormconfig`, `Cargo.toml` (Diesel).
   - Load `standards/framework/stacks/database.md` for enforceable patterns.
   - Load `references/database-patterns.md` for detailed guidance.

2. **Design schema** (for new features).
   - Follow naming conventions: lowercase snake_case, plural tables.
   - Define primary keys, foreign keys with ON DELETE/ON UPDATE behavior.
   - Add `created_at`, `updated_at` with database defaults.
   - Add CHECK constraints for domain invariants.
   - Index foreign keys and frequently-queried columns.

3. **Plan migration** (for schema changes).
   - Classify: additive (safe) vs breaking (requires expand-contract).
   - Assess locking impact on production tables.
   - Write forward migration + rollback migration.
   - Test migration on production-size data in staging.
   - For breaking changes: expand → migrate data → deploy code → contract.

4. **Optimize queries** (for performance issues).
   - Run `EXPLAIN` / `EXPLAIN ANALYZE` on slow queries.
   - Identify: missing indexes, N+1 patterns, full table scans, unnecessary joins.
   - Apply: targeted indexes, eager loading, keyset pagination, column projection.
   - Measure before and after with execution time and rows scanned.

5. **Configure connections** (for pool tuning).
   - Set pool size based on workload: `max_connections / app_instances`.
   - Configure idle timeout (30-60s), connection lifetime (30-60min).
   - Enable health checks (test-on-borrow).
   - Add retry logic with exponential backoff for transient failures.

6. **Design data lifecycle** (for retention/archival).
   - Define retention periods per data category.
   - Design archival strategy: archive tables, cold storage, or time-partitioning.
   - Support GDPR: data export, deletion, anonymization.
   - Document backup and restore procedures.

## Output Contract

- Schema design with DDL or ORM migration files.
- Migration plan with safety assessment and rollback procedure.
- Query optimization report with before/after execution plans.
- Connection pool configuration recommendations.
- Data lifecycle policy with retention schedules.

## Governance Notes

- Destructive DDL (DROP TABLE, DROP COLUMN) requires explicit user approval.
- Every migration must have a rollback script.
- Production data operations require backup verification before execution.
- Query optimization recommendations must include measured evidence (EXPLAIN output).

### Iteration Limits

- Max 3 attempts to resolve the same database issue. After 3 failures, escalate to user with evidence.

### Post-Action Validation

- After generating migrations, run ORM-specific validation (e.g., `prisma migrate diff`, `dotnet ef migrations script`).
- Verify SQL syntax if generating raw DDL.
- If validation fails, fix issues and re-validate (max 3 attempts).

## References

- `standards/framework/stacks/database.md` — SQL patterns, migration safety, data lifecycle.
- `standards/framework/stacks/dotnet.md` — EF Core patterns (DbContext, migrations, bulk operations, interceptors).
- `skills/db/references/database-patterns.md` — detailed database patterns.
- `skills/data-model/SKILL.md` — data modeling procedures.
- `agents/build.md` — implementation agent for complex database decisions.
