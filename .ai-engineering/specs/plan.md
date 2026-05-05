# Plan: spec-122 Framework Cleanup Phase 1

## Pipeline: autopilot
## Phases: 5
## Tasks: 78 across 4 sub-specs (sub-001/18, sub-002/22, sub-003/16, sub-004/22)

## Architecture

autopilot — orchestrated multi-sub-spec delivery. Per-sub-spec plans
live under `.ai-engineering/specs/autopilot/sub-NNN/plan.md`; this
root plan is a thin pointer that satisfies the validator's
`Plan: <spec-id>` heading contract while the canonical task ledger
is maintained inside each sub-spec.

### Active sub-specs

| Sub-spec | Title                                 | Status   | Wave |
|----------|---------------------------------------|----------|------|
| sub-001  | Hygiene + Config + Delete Evals       | complete | 1    |
| sub-002  | Engram Delegation + Unified state.db  | partial  | 2    |
| sub-003  | OPA Proper Switch + Governance Wiring | partial  | 2    |
| sub-004  | Meta-Cleanup (Docs + Scripts + Drift) | complete | 3    |

### Phase 1: Wave 1 (sub-001)

**Gate**: hygiene baseline complete; orphan markers, deletes, manifest
references all verified clean. Commit `7ce3c3ef`.

### Phase 2: Wave 2 (sub-002 + sub-003 in parallel)

**Gate**: state.db migration runner + 7 STRICT tables land; OPA proper
binary wired into governance and audit chain. Commit `3351dcef`.

### Phase 3: Wave 3 (sub-004)

**Gate**: docs + scripts + drift cleanup complete; cross-IDE mirrors
byte-identical. Commit `a65e2702`.

### Phase 4: Quality Convergence (Phase 5 in autopilot)

**Gate**: all known follow-up debts cleared in a single pass —
- T-3.16 legacy `policy_engine.py` retired in favour of OPA shim.
- T-2.20 dead memory deps removed from `pyproject.toml` + `uv.lock`.
- 33+ residual unit-test failures from waves 1+2 cleanup converged.
- T-3.15 hot-path SLO best-effort tightening.

### Phase 5: Wrap-up

**Gate**: PR opened with quality report; merge gated by branch
protection + reviewer sign-off.

## Quality Rounds

(populated by the convergence phase)

## See Also

- Per-sub-spec plans: `.ai-engineering/specs/autopilot/sub-NNN/plan.md`
- Autopilot manifest: `.ai-engineering/specs/autopilot/manifest.md`
- Source spec: `.ai-engineering/specs/spec-122-framework-cleanup-phase-1.md`
