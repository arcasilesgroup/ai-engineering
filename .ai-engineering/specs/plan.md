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
