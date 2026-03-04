---
name: db
description: "Database engineering: schema design, data modeling, safe migrations, query optimization, data lifecycle. Absorbs data-model skill."
metadata:
  version: 2.0.0
  tags: [database, sql, migration, schema, optimization, data-lifecycle, data-model]
  ai-engineering:
    scope: read-write
    token_estimate: 900
---

# Database

## Purpose

Database engineering skill covering schema design, data modeling, migration safety, query optimization, connection pool tuning, and data lifecycle management. Consolidates db and data-model skills. Works across ORMs (Entity Framework, Prisma, SQLAlchemy, TypeORM, Drizzle, Diesel) and databases (PostgreSQL, SQL Server, MySQL, SQLite).

## Trigger

- Command: `/ai:db`
- Context: schema design, data modeling, migration planning, query optimization, data lifecycle.

## Procedure

1. **Analyze data model** -- entities, relationships, access patterns, data volume, growth projections. Apply normalization rules (3NF+), document denormalization decisions with rationale.

2. **Design schema** -- create or modify tables, indexes, constraints. Validate referential integrity. Consider partitioning for large tables.

3. **Plan migration** -- assess locking impact, backward compatibility, rollback procedure. Use expand-contract pattern for breaking changes. Rollback scripts are ALWAYS required alongside forward migrations.

4. **Optimize queries** -- analyze execution plans (`EXPLAIN ANALYZE`), recommend indexes, fix N+1 patterns. Connection pool configuration and tuning.

5. **Design lifecycle** -- retention policies, archival strategies, GDPR compliance. Multi-database architecture considerations (read replicas, caching layers).

## When NOT to Use

- **Infrastructure provisioning** (cloud database instances) -- use `infra`.
- **CI/CD pipeline setup** -- use `cicd`.
