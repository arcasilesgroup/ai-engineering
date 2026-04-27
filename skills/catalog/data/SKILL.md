---
name: data
description: Use when working with database schemas, migrations, retention, GDPR right-to-erasure, or data lineage — schema design, safe migration generation, classification, lineage tracing. Trigger for "design this schema", "generate a migration", "purge user data", "where does this data flow".
effort: max
tier: core
capabilities: [tool_use, structured_output]
governance:
  blocking: true
---

# /ai-data

Schema, migration, retention, and lineage authority. Covers PostgreSQL,
MySQL, SQLite, and MongoDB. Enforces GDPR Article 17 (right to erasure)
and SOC2 retention controls.

## When to use

- New schema or schema change — design + review
- Generating a migration (forward + reverse)
- GDPR data subject request — erasure / export / rectification
- Data classification — PII, PHI, financial, public
- Lineage tracing — "where does field X come from / flow to"
- Retention policy enforcement — TTL purges

## Process

### Schema design

1. Read existing schema; confirm domain model alignment.
2. Apply normalization to 3NF unless OLAP/analytics requires denorm.
3. Add indices based on query patterns (not speculation).
4. Mark every column with classification: `public`, `internal`,
   `confidential`, `pii`, `phi`, `financial`.

### Migration generation

1. Generate forward + reverse migrations as a pair.
2. Use safe patterns: `ADD COLUMN NULL` then backfill then `SET NOT NULL`;
   never lock tables in hot paths.
3. Run on shadow database first; capture timing.
4. Emit `migration.proposed` event with risk score (table size, lock
   duration, downtime estimate).

### GDPR right-to-erasure

1. Locate every store containing the subject (use lineage map).
2. Delete primary records; cascade or anonymize foreign references.
3. Purge derived data: caches, search indices, OLAP cubes, backups
   (per backup retention SLA).
4. Emit `gdpr.erasure.completed` with subject hash + scope manifest.

### Lineage tracking

- Maintain `.ai-engineering/data/lineage.yaml` mapping source → table
  → field → consumers.
- Auto-update on migration application (CI check verifies consistency).

## Hard rules

- NEVER drop a column in the same migration that introduces it (split
  add and remove across two releases).
- NEVER execute destructive DDL (`DROP TABLE`, `TRUNCATE`) without
  explicit user approval AND a backup verification step.
- NEVER store PII/PHI without classification tag and retention TTL.
- Reverse migrations are mandatory — a forward without reverse is
  rejected by the gate.
- Backups are immutable and encrypted; access is audit-logged.

## Common mistakes

- Treating migrations as code-only; they are operations with locks
- Skipping reverse migration ("we'll never need to roll back")
- Forgetting derived stores when purging (search index keeps PII)
- Cross-environment drift — staging schema diverges from prod
- Missing classification tags on new columns
