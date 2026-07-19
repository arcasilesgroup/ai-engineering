---
name: ai-schema
description: "Designs schemas, plans safe migrations with rollback scripts, optimizes slow queries with index recommendations, defines data retention and GDPR right-to-erasure policies. Supports PostgreSQL, MySQL, SQLite, MongoDB. Trigger for 'add a column', 'we need a migration', 'the query is slow', 'define a retention policy', 'GDPR compliance for data'. Not for application-layer ORMs without DB schema; use /ai-code instead. Not for security audits; use /ai-security instead. Not for infrastructure provisioning — no infra skill exists."
effort: mid
argument-hint: "design|migrate|optimize|lifecycle"
tags: [database, sql, migration, schema, optimization, enterprise]
requires:
  anyBins: [psql, mysql, sqlite3, mongosh]
---


# Database Engineering

Schema design, safe migration generation, query optimization, and data lifecycle management across PostgreSQL, MySQL, SQLite, and MongoDB. Multi-ORM: SQLAlchemy, Prisma, TypeORM, Drizzle, Entity Framework, Diesel.

## Process

Step 0 (load contexts): read `.ai-engineering/manifest.yml` `providers.stacks`; load `.ai-engineering/overrides/<stack>/conventions.md` for each stack and `.ai-engineering/overrides/_shared/conventions.md`; load `.ai-engineering/team/*.md` for team conventions.

## Modes

### design -- Schema Design

1. **Analyze data model** -- entities, relationships, access patterns, data volume, growth projections.
2. **Apply normalization** -- 3NF+ by default. Document denormalization decisions with rationale.
3. **Design schema** -- tables, indexes, constraints, partitioning for large tables.
4. **Validate referential integrity** -- every FK has a matching PK, cascade rules defined.
5. **Output**: DDL script + entity relationship description.

### migrate -- Safe Migrations

1. **Assess impact** -- locking impact, backward compatibility, data volume affected.
2. **Use expand-contract** -- for breaking changes (add new, migrate data, drop old).
3. **Generate forward migration** -- with explicit transaction boundaries.
4. **Generate rollback migration** -- ALWAYS required. No migration ships without rollback.
5. **Test migration** -- verify on representative data volume.
6. **Output**: forward script, rollback script, execution plan.

### optimize -- Query Optimization

1. **Analyze execution plan** -- `EXPLAIN ANALYZE` (PostgreSQL), `EXPLAIN` (MySQL).
2. **Identify bottlenecks** -- sequential scans, missing indexes, N+1 patterns.
3. **Recommend indexes** -- composite indexes based on query patterns, partial indexes for filtered queries.
4. **Connection pool tuning** -- pool size, timeout, idle connection management.
5. **Output**: optimized query, index recommendations, before/after execution plan.

### lifecycle -- Data Lifecycle

1. **Retention policies** -- define per-table retention based on regulatory requirements.
2. **Archival strategies** -- partition-based archival, cold storage migration.
3. **GDPR compliance** -- right to erasure procedures, data anonymization.
4. **Multi-DB architecture** -- read replicas, caching layers, write distribution.
5. **Output**: lifecycle policy document, archival procedures.

## Common Mistakes

- Adding indexes without checking write impact -- indexes speed reads but slow writes.
- Running DDL without `--dry-run` first -- destructive DDL requires explicit user approval.

## Examples

### Example — safe migration with backfill

User: "we need to add a soft-delete column to users with a backfill"

```
/ai-schema migrate
```

Generates up + down migration, default-backfill strategy, lock-impact analysis, rollback script, and a dry-run preview.

## Integration

Calls: `psql` / `mysql` / `sqlite3` / `mongosh` (verification). Triggers: `/ai-security` (injection pattern review). Integrates with: ORM migration systems (Alembic, Prisma Migrate, EF Migrations). See also: `/ai-security`, `/ai-governance` (destructive DDL approval).

## References

- `.ai-engineering/manifest.yml` -- governance rules for destructive operations.

$ARGUMENTS
