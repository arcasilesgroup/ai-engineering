---
spec: spec-133
title: spec-133 — Surface Primitive Re-architecture (CLI UX + Cross-IDE)
pipeline: autopilot
phases: 6
sub-specs: 14
status: in-progress
---

# Plan — spec-133 Surface Primitive Re-architecture

This plan is the aggregate index for spec-133's autopilot run. The
per-sub-spec deep plans live under
`.ai-engineering/runtime/autopilot/sub-NNN/plan.md` per spec-131
D-131-13. See `.ai-engineering/runtime/autopilot/manifest.md` for the
14-sub-spec DAG and wave assignment.

## Branch / PR

- branch: `spec-128/context-overrides-refactor` (NO new branch — D-133 constraint)
- pr: `arcasilesgroup/ai-engineering#509` (NO new PR — D-133 constraint)

## Quality bar

Per D-133-26: every new CLI verb / deterministic primitive ships
production-grade — idempotent, exit-coded per category (0/1/2/78),
audit events via OutputPort, `--json` structured output universal,
`--dry-run` where state-changing, refuse detached HEAD, never delete
current branch, TDD per mode (RED-first).

## Outcomes (updated per-wave)

See `.ai-engineering/runtime/autopilot/manifest.md` for the live DAG.
Integrity Report appears at the end of the run.


## Tasks

- [x] sub-001 Surface domain primitive + 10 tests (D-133-15)
- [x] sub-002 Manifest schema + wizard collapse + 12 tests (D-133-16/17/18)
- [x] sub-003 ScriptsPhase + 9 root scripts + 8 tests (D-133-21)
- [x] sub-004 Surface Axiom (§16) + parity test + 4 tests (D-133-04)
- [x] sub-005 cli_ui.skill_ref helper + 8 tests (D-133-22)
- [x] sub-006 OpenCode Surface (bridge + target) + 4 tests (D-133-06)
- [x] sub-007 Cursor Surface (bridge + target) + 5 tests (D-133-06/07)
- [x] sub-008 Antigravity mirror-only Surface + docs + 1 test (D-133-06)
- [x] sub-009 ai-eng cleanup 7-mode CLI + 8 tests (D-133-03)
- [x] sub-010 guide DELETE + ai-explore + applies_to_surfaces (D-133-02/09/19)
- [x] sub-011 B16 greenfield (middleware + recovery contract) + 10 tests (D-133-23/24/25)
- [ ] sub-012 Hex zero-whitelist + 4 ports + 6 in-band fixes (D-133-20)
- [x] sub-013 HARD DELETE 4 orphan dirs + handlers consolidation (D-133-10/13)
- [x] sub-014 12 stacks + _shared/sql.md + 17 tests (D-133-12)
- [x] Final quality loop: unit tests 5462 passing
- [ ] Final quality loop: integration tests
- [ ] CHANGELOG update
- [ ] PR #509 update
