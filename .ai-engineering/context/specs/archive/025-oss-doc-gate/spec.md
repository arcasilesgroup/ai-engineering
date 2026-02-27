---
id: "025"
slug: "oss-doc-gate"
status: "in-progress"
created: "2026-02-27"
---

# Spec 025 — OSS Documentation Gate

## Problem

Documentation updates (CHANGELOG, README, external docs portal) are never enforced in commit/PR workflows. Changes ship without updating user-facing docs, leading to stale documentation for OSS GitHub users.

## Solution

Add a mandatory documentation gate to `/commit`, `/pr`, and `/acho` workflows that:
1. Classifies changes as user-visible vs internal-only.
2. Always updates **CHANGELOG.md** for user-visible changes (creates if missing).
3. Always updates **README.md** for new features/breaking changes (creates if missing).
4. Asks about **external documentation portal** — if provided, clones the docs repo, updates pages, and creates a PR with auto-complete.

## Scope

### In Scope

- Documentation gate step added to `/commit`, `/pr`, `/acho` procedures.
- CHANGELOG.md auto-update using `skills/docs/changelog/SKILL.md`.
- README.md auto-update using `skills/docs/writer/SKILL.md` for OSS GitHub users.
- External docs portal support: clone, update, PR with auto-complete.
- PR checklist expanded with changelog/docs/external docs items.
- Standards updated: `core.md` non-negotiables, `quality/core.md` gate table.
- Template mirrors synced.
- Decision recorded in `decision-store.json`.

### Out of Scope

- Model tier system (removed — no `model_tier` metadata).
- Automated generation from scratch (AI follows existing doc skill procedures).
- Changes to agent roster or skill-to-agent conversions.

## Acceptance Criteria

1. `/commit` procedure includes documentation gate step (step 5) between secret detection and commit.
2. `/pr` procedure includes documentation gate step and expanded PR checklist.
3. `/acho` references documentation gate inheritance.
4. Documentation gate always updates CHANGELOG.md for user-visible changes.
5. Documentation gate updates README.md for new features/breaking changes.
6. Documentation gate asks about external docs portal and handles clone + PR workflow.
7. Internal-only changes skip the gate silently.
8. `core.md` non-negotiables include documentation update mandate for OSS GitHub users.
9. `integrity-check` passes all 7 categories after completion.
10. Template mirrors byte-identical with canonical files.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D025-001 | Mandatory documentation gate in /commit, /pr, /acho for OSS GitHub users. Always updates CHANGELOG.md + README.md for user-visible changes. External docs portal support with clone + PR. | Changelog and writer skills exist but are never enforced. OSS users need up-to-date docs. External portal support prevents docs drift across repos. |
