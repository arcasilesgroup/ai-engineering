# WORKSPACE CHARTER

This file is a compatibility alias retained during control-plane normalization.
Root `CONSTITUTION.md` is the sole constitutional authority and the only Step 0
input for this repository. This workspace charter documents workspace-local
boundaries and customization surfaces under `.ai-engineering/` without
superseding the root constitution.

## Purpose

- Preserve the legacy `.ai-engineering/CONSTITUTION.md` path while migration
	completes.
- Document workspace-local boundaries for `.ai-engineering/**`, IDE mirror
	surfaces, and coordination-sensitive control-plane changes.
- Keep hard rules, constitutional principles, and agent boot order anchored only
	in root `CONSTITUTION.md`.

## Workspace Boundaries

### Framework-managed surfaces

- `.claude/skills/**`, `.claude/agents/**` -- canonical skill and agent
	definitions
- `.ai-engineering/**` -- manifest, state, contexts, specs, and runbooks managed
	by governed framework flows
- `.github/agents/**`, `.github/skills/**`, `.github/hooks/**` -- GitHub Copilot
	mirrors
- `.codex/**`, `.gemini/**` -- other IDE mirrors
- Hook scripts -- hash-verified, never modified directly

### Team-managed surfaces

- `.ai-engineering/contexts/team/**` -- team conventions and lessons
- `.ai-engineering/manifest.yml` operator-authored configuration fields
- Root `CONSTITUTION.md` -- the only constitutional document

### Coordination-required changes

- Gate thresholds -- require risk acceptance in `state/decision-store.json`
- Manifest schema -- affects all IDEs and downstream mirrors
- Skill and agent contracts -- consumed by multiple IDE providers
- PyPI package interface -- public API for `ai-eng`

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
remain consistent with root `CONSTITUTION.md`. No automated process may promote
this file back to constitutional authority.

**Ownership**: TEAM_MANAGED compatibility artifact. The framework preserves this
path during the migration window unless a replacement spec removes it.

**Version**: 1.0.0 | **Ratified**: 2026-03-29 | **Last Amended**: 2026-04-30
