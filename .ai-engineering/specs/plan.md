# Plan: spec-123 Phase 1 Closure

## Pipeline: full
## Phases: 8
## Tasks: 58 (build: 40, verify: 15, guard: 3)

## Architecture

**Modular Monolith + CQRS with Transactional Outbox + Sidecar (Engram)**

Per `.ai-engineering/contexts/architecture-patterns.md`:

- **Modular Monolith** — single Python project (`src/ai_engineering/`) with clean module boundaries (`state/`, `governance/`, `installer/`, `policy/`, `validator/`, `cli_commands/`, `hooks/`). Spec-123 reinforces module boundaries.
- **CQRS with Transactional Outbox** — NDJSON `framework-events.ndjson` is immutable command-side write log (Article III SoT); `state.db` is rebuildable read-model projection.
- **Sidecar (Engram)** — Engram runs as separate process (CLI binary) installed by `ai-eng install` per OS/IDE. Framework does not embed Engram code.

Single architecture statement: ai-engineering is a modular monolith Python framework whose state plane follows CQRS+outbox over NDJSON-projects-into-SQLite topology, with Engram bolted on as optional sidecar.

## Design

No UI work. Routing skipped.

---

### Phase 1 — Workspace-charter stub deletion (T-1.2 carry-over)

**Gate**: pytest validator + state + constitution_skill_paths green; ai-eng doctor 0; grep negative for workspace-charter refs.

- [x] T-1.1: Pre-deletion grep for workspace-charter callers (agent: verify)
- [x] T-1.2: Update control_plane.py `_CONSTITUTIONAL_ALIASES` to empty tuple + callers (agent: build)
- [x] T-1.3: Delete workspace-charter validation block in manifest_coherence.py (agent: build)
- [x] T-1.4: Update file_existence.py `_SOURCE_REPO_CONTROL_PLANE_PATHS` (agent: build)
- [x] T-1.5: Update standards.py legacy-retirement family `current_surfaces` (agent: build)
- [x] T-1.6: Update 7 test fixtures in lockstep (agent: build)
- [x] T-1.7: Delete .ai-engineering/CONSTITUTION.md stub + 2 template stubs (agent: build)
- [x] T-1.8: Phase 1 verification — pytest + ai-eng doctor + grep negative (agent: verify)

---

### Phase 2 — Memory subsystem nuke

**Gate**: zero ghost references; framework imports clean; skill registry counts updated.

- [x] T-2.1: Pre-deletion grep for ai-eng memory references repo-wide (agent: verify)
- [x] T-2.2: Delete .ai-engineering/scripts/memory/ (9 files) (agent: build)
- [x] T-2.3: Delete src/ai_engineering/cli_commands/memory_cmd.py + CLI registration (agent: build)
- [x] T-2.4: Delete /ai-remember + /ai-dream skills (16 files: canonical + 3 mirrors + 4 templates) (agent: build)
- [x] T-2.5: Scrub ai-eng memory references in skill bodies + docs (agent: build)
- [x] T-2.6: Decrement manifest.yml skills.total (51 to 49) (agent: build)
- [x] T-2.7: Phase 2 verification — import smoke + skill registry validation (agent: verify)

---

### Phase 3 — State.db bootstrap + sub-002 closure

**Gate**: state.db exists with 7 tables populated; NDJSON replay populates events table; 5 JSON files migrated; sidecar wired; 6 audit CLI verbs callable; audit_index redirected.

- [x] T-3.1: TDD-RED — failing test for lazy state_db.connect() bootstrap (agent: build)
- [x] T-3.2: TDD-GREEN — implement lazy bootstrap in state_db.py (agent: build)
- [x] T-3.3: Wire migration apply into ai-eng install pipeline (idempotent) (agent: build)
- [x] T-3.4: Verify NDJSON replay populates events table (agent: verify)
- [x] T-3.5: Verify 5 JSON files migrated to respective tables (agent: verify)
- [x] T-3.6: Wire sidecar offload into runtime-guard.py for events 3KB+ (T-2.8) (agent: build)
- [x] T-3.7: TDD-RED+GREEN — zstd seekable compress for closed NDJSON months (T-2.10) (agent: build)
- [x] T-3.8: TDD-RED+GREEN — retention module 90d HOT cutoff (T-2.11) (agent: build)
- [x] T-3.9: Implement 6 audit CLI verbs (retention apply, rotate, compress, verify-chain, health, vacuum) (T-2.12) (agent: build)
- [x] T-3.10: Implement audit_index.py redirect to state.db (T-2.22) (agent: build)
- [x] T-3.11: Phase 3 verification — full state.db smoke + integration test (agent: verify)

---

### Phase 4 — OPA closure (parallel-ok with Phase 5)

**Gate**: 4 OPA closure tasks done; CI workflow with 90% coverage gate; doctor includes opa-health.

- [x] T-4.1: Wire OPA into ai-eng risk accept (T-3.13) (agent: build)
- [x] T-4.2: Integration golden tests for 3 policies via opa eval subprocess (T-3.14) (agent: build)
- [x] T-4.3: CI workflow opa test --coverage 90% gate (T-3.17) (agent: build)
- [x] T-4.4: /ai-governance skill update + ai-eng doctor opa-health (T-3.18) (agent: build)

---

### Phase 5 — Engram third-party integration (parallel-ok with Phase 4)

**Gate**: install prompt callable; OS+IDE detection works; engram setup invocation tested with mocked subprocess.

- [x] T-5.1: TDD-RED — failing test for ai-eng install Engram prompt (agent: build)
- [x] T-5.2: TDD-GREEN — implement _install_engram() with OS+IDE detection (agent: build)
- [x] T-5.3: Add interactive prompt to install pipeline (agent: build)
- [x] T-5.4: README + CLAUDE.md + AGENTS.md update for Engram install flow (agent: build)
- [x] T-5.5: Phase 5 verification — install prompt tests + dry-run (agent: verify)

---

### Phase 6 — specs/ canonical structure migration

**Gate**: specs/ contains exactly {spec.md, plan.md, _history.md}; CI guard test passes; no broken skill citations.

- [x] T-6.1: Migrate cited paths in skill bodies (decision-store query OR git-log fallback) (agent: build)
- [x] T-6.2: Delete all numbered archive specs (~50 files) (agent: build)
- [x] T-6.3: Delete all numbered plan archives (~16 files) (agent: build)
- [x] T-6.4: Delete spec-117 supporting + exploration companions (~17 files) (agent: build)
- [x] T-6.5: Delete progress dirs (spec-119-progress, spec-120-progress) (agent: build)
- [x] T-6.6: Delete dead work-plane artifacts (task-ledger.json, current-summary.md, history-summary.md, handoffs/, evidence/, context-packs/) (agent: build)
- [x] T-6.7: Move autopilot transient state to .ai-engineering/state/runtime/autopilot/ gitignored (agent: build)
- [x] T-6.8: Update HX-02 work_plane.py resolver to drop dead artifacts (agent: build)
- [x] T-6.9: New CI guard tests/unit/specs/test_canonical_structure.py (agent: build)

---

### Phase 7 — CONSTITUTION article + autopilot bug fix + doc drift

**Gate**: CONSTITUTION article landed; autopilot phase-deliver verified; ai-implement scrub clean.

- [x] T-7.1: Add Article XIII "Active Spec Workflow Contract" to CONSTITUTION.md (agent: build)
- [x] T-7.2: Fix autopilot phase-deliver.md cleanup execution + verification gate (D-123-27) (agent: build)
- [x] T-7.3: Scrub remaining ai-implement references repo-wide (D-123-28) (agent: build)
- [x] T-7.4: New CI guard tests/unit/specs/test_active_workflow_compliance.py (agent: build)

---

### Phase 8 — Quality convergence + final verification

**Gate**: all checks green; ready for /ai-pr.

- [x] T-8.1: Full unit test suite (agent: verify)
- [x] T-8.2: Integration tests (state, governance, sync, memory) (agent: verify)
- [x] T-8.3: ruff format + lint baseline preserved (agent: verify)
- [x] T-8.4: gitleaks (agent: verify)
- [x] T-8.5: Hot-path SLO p95 < 1s (agent: verify)
- [x] T-8.6: ai-eng spec verify --all + ai-eng doctor (agent: verify)
- [x] T-8.7: ai-eng audit health + verify-chain (agent: verify)
- [x] T-8.8: governance pre-pr review (agent: guard)
- [x] T-8.9: spec compliance pre-pr (agent: guard)
- [x] T-8.10: spec-folder compliance check (3 files only) (agent: guard)

---

### Phase 9 — Deliver via /ai-pr (out of /ai-plan scope)

User invokes /ai-pr after Phase 8 gate.

---

## Counts breakdown

| Phase | Tasks | build | verify | guard |
|-------|-------|-------|--------|-------|
| 1 Workspace-charter | 8 | 6 | 2 | 0 |
| 2 Memory nuke | 7 | 5 | 2 | 0 |
| 3 State.db bootstrap | 11 | 9 | 2 | 0 |
| 4 OPA closure | 4 | 4 | 0 | 0 |
| 5 Engram integration | 5 | 4 | 1 | 0 |
| 6 Specs/ canonical | 9 | 8 | 1 | 0 |
| 7 CONSTITUTION + autopilot fix + drift | 4 | 4 | 0 | 0 |
| 8 Quality convergence | 10 | 0 | 7 | 3 |
| **Total** | **58** | **40** | **15** | **3** |

## Critical path

```
Phase 1 paralelo Phase 2
        |
   Phase 3 (state.db)
        |
Phase 4 paralelo Phase 5
        |
   Phase 6 (specs/ canonical - most blast)
        |
Phase 7 (CONSTITUTION + autopilot fix + drift)
        |
Phase 8 (quality convergence)
        |
Phase 9 (/ai-pr)
```

## Estimated effort

5-7 hours agent-execution-time. Wall-clock varies with autopilot truncation.

## Recommended execution path

`/ai-autopilot spec-123` matches autopilot threshold. Spec-122 lessons applied:
- Per-task verification gates in agent prompts (ls, pytest specific, grep expected) survive truncation
- Smaller waves: P1+P2 wave-1; P3 wave-2; P4+P5 wave-3; P6 wave-4; P7 wave-5; P8 wave-6
- Phase 6 isolated wave because most-disruptive single phase
- D-123-27 fixes autopilot phase-deliver bug during Phase 7

Alternative: /ai-dispatch with manual checkpointing per phase.

## STOP — Hard gate

/ai-plan is planning-only. No implementation. User runs /ai-dispatch or /ai-autopilot to execute.
