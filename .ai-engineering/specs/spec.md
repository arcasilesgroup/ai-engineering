---
spec: spec-122
title: Framework Cleanup Phase 1 — Hygiene + State Unification + Engram Delegation + OPA Switch + Meta-Cleanup
status: approved
effort: large
active_buffer: true
canonical_path: .ai-engineering/specs/spec-122-framework-cleanup-phase-1.md
---

# Active Spec Buffer

This file is the resolver-canonical active-spec buffer (per
`src/ai_engineering/state/work_plane.py:resolve_active_work_plane`).
The full spec content lives in the immutable archive at:

- Master: `.ai-engineering/specs/spec-122-framework-cleanup-phase-1.md`
- Sub-spec A: `.ai-engineering/specs/spec-122-a-hygiene-and-evals-removal.md`
- Sub-spec B: `.ai-engineering/specs/spec-122-b-engram-and-state-unify.md`
- Sub-spec C: `.ai-engineering/specs/spec-122-c-opa-proper-switch.md`
- Sub-spec D: `.ai-engineering/specs/spec-122-d-meta-cleanup.md`

All 5 are approved (master + 4 sub-specs). Autopilot orchestrates delivery via
`.ai-engineering/specs/autopilot/manifest.md`.

## Summary

Framework cleanup Phase 1 (40 decisions). Touches:
- Config hygiene (CONSTITUTION dedupe, semgrep expansion, gitleaks tightening, manifest orphan removal)
- Evals subsystem deletion (false-signal `enforcement: blocking`)
- Memory delegation to Engram (delete ~3K LOC, 4 deps, custom memory layer)
- State unification (5 JSON + 1 SQLite → single `state.db` with 7 STRICT tables)
- OPA proper swap-in (deletes custom mini-Rego interpreter, wires real CNCF binary)
- Meta-cleanup (script split, doc drift, hot-path SLO tests, spec-path canonicalization)

## DAG Reference

```
sub-001 (spec-122-a) ──┬──> sub-002 (spec-122-b) ──┐
                       │                             ├──> sub-004 (spec-122-d)
                       └──> sub-003 (spec-122-c) ──┘
```

Wave 1: sub-001 (no deps).
Wave 2: sub-002 + sub-003 (parallel, both depend on sub-001).
Wave 3: sub-004 (depends on all three).

## Status

- Phase 0 Validate: complete (all sub-specs approved, state reset, scaffolding ready)
- Phase 1 Decompose: complete (user pre-decomposed; manifest written)
- Phase 2 Deep Plan: pending
- Phase 3 Orchestrate: pending
- Phase 4 Implement: pending
- Phase 5 Quality: pending
- Phase 6 Deliver: pending
