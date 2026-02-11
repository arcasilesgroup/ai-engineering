# Migration

## Purpose

Structured migration skill for database schema changes, API versioning, breaking changes, and data transformations. Ensures safe, reversible migrations with rollback plans.

## Trigger

- Command: agent invokes migration skill or user requires schema/API/data migration.
- Context: breaking changes, schema evolution, API version bump, data format migration, framework updates.

## Procedure

1. **Assess impact** — determine migration scope.
   - What is changing: schema, API contract, data format, config structure.
   - Who is affected: consumers, downstream systems, installed instances.
   - Breaking vs. non-breaking: can existing consumers continue without changes?
   - Data volume: how much data needs transformation.

2. **Plan migration** — define strategy.
   - **Additive first**: add new fields/endpoints before removing old ones.
   - **Deprecation window**: mark old APIs/fields as deprecated with timeline.
   - **Version strategy**: semantic versioning, migration scripts per version bump.
   - **Rollback plan**: how to revert if migration fails.

3. **Implement migration** — build the migration.
   - Write migration script (forward and backward).
   - Framework state migrations: transform JSON schemas between versions.
   - API migrations: support old and new formats during transition.
   - Include validation: verify data integrity after migration.

4. **Test migration** — validate thoroughly.
   - Test forward migration on sample data.
   - Test backward migration (rollback).
   - Test with edge cases: empty data, max-size data, corrupt data.
   - Test on clean install vs. upgrade from previous version.

5. **Execute migration** — deploy safely.
   - Dry-run first: show what would change without applying.
   - Backup before applying.
   - Apply and validate.
   - Monitor for issues post-migration.

6. **Document** — record the migration.
   - What changed and why.
   - How to upgrade from version N to N+1.
   - Rollback procedure.
   - Known issues or limitations.

## Output Contract

- Migration script (forward + backward).
- Test results for forward and rollback paths.
- Documentation of changes and upgrade procedure.
- Validation evidence: data integrity confirmed.

## Governance Notes

- Breaking changes require explicit documentation in PR and changelog.
- Framework state schema changes must include migration scripts (per SemVer release model).
- Ownership safety: migrations must not modify team-managed or project-managed content.
- Dry-run is mandatory before apply — never auto-apply migrations.
- Rollback plan is required for all migrations. No exceptions.

## References

- `standards/framework/core.md` — update contract and ownership safety.
- `context/product/framework-contract.md` — release model (SemVer + migration scripts).
- `agents/verify-app.md` — E2E verification agent for migration testing.
