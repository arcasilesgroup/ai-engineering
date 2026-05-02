# WORKSPACE CHARTER

This file is a compatibility alias retained for legacy installs.
Root `CONSTITUTION.md` is the sole constitutional authority and the only Step 0
input for the project. This workspace charter documents `.ai-engineering/`
boundaries and local customization surfaces without superseding the root
constitution.

## Purpose

- Preserve the legacy `.ai-engineering/CONSTITUTION.md` path while migration
	completes.
- Record workspace-local boundaries for `.ai-engineering/**`, IDE mirrors, and
	other compatibility surfaces.
- Keep hard rules, constitutional constraints, and Step 0 behavior in root
	`CONSTITUTION.md` only.

## Workspace Boundaries

### Framework-managed surfaces

- [List framework-managed files and directories]

### Team-managed surfaces

- `.ai-engineering/contexts/team/**` -- team conventions and lessons
- `.ai-engineering/manifest.yml` operator-authored configuration fields
- Root `CONSTITUTION.md` -- the only constitutional document

### Coordination-required changes

- [What changes require team notification or review]

## Compatibility Notes

- Legacy tooling may still read `.ai-engineering/CONSTITUTION.md` as a fallback
	when root `CONSTITUTION.md` is absent.
- New writers must update `CONSTITUTION.md`; this file is subordinate workspace
	policy, not peer authority.
- Any conflict between this file and root `CONSTITUTION.md` is resolved in favor
	of the root constitution.

## Governance

This workspace charter is subordinate to root `CONSTITUTION.md`. It is not a
second constitution and it is not loaded at Step 0.

**Amendment process**: Changes to this charter require team review and must
remain consistent with root `CONSTITUTION.md`.

**Ownership**: TEAM_MANAGED compatibility artifact. The framework preserves this
path during the migration window unless a replacement spec removes it.

**Version**: 1.0.0 | **Ratified**: [YYYY-MM-DD] | **Last Amended**: [YYYY-MM-DD]
