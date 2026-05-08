---
total: 14
completed: 0
---

# Plan: sub-001 M0 — Foundations + spec lifecycle + voice updates

## Pipeline: standard
## Phases: 5
## Tasks: 14 (build: 10, verify: 3, guard: 1)

## Architecture

**Pattern**: Hexagonal (inherited from umbrella spec-127 D-127-09).

**Justification**: Layers concrete and small.
- **Domain** (pure): `LifecycleState` enum
  (`DRAFT`/`APPROVED`/`IN_PROGRESS`/`SHIPPED`/`ABANDONED`/`ARCHIVED`),
  `SpecRecord` dataclass, `Transition` validator. Zero I/O.
- **Infrastructure**: filesystem readers/writers (JSON sidecar, `_history.md`
  markdown projection, NDJSON event append). All wrap `artifact_lock`.
- **Application** (CLI): `start_new`, `mark_shipped`, `archive`, `sweep`,
  `status` — each composes domain transition + infra write under one lock.

Atomic ops <500ms (no LLM, stdlib + filesystem). Layer isolation informally
enforced in M0 (single file). M5 `tests/architecture/test_layer_isolation.py`
covers it once `tools/skill_domain` / `skill_infra` exist.

## Design

Skipped — pure tooling + doc rewrites.

## Phase classification: standard

1 new script (~250 LOC). 2 new test files. 1 history-table migration. 3
SKILL.md edits (≤10 lines each). 2 root governance doc rewrites. Total: ≤5
Python files, ≤3 doc edits, 14 tasks.

### Phase 0: Pre-flight

**Gate**: lifecycle script absent (greenfield); locking primitive importable;
brief §15 + §18 read.

- [ ] T-0.1: Confirm `spec_lifecycle.py` does not exist; record `_history.md`
  column count (5) for migration test fixture (agent: verify)
- [ ] T-0.2: `/ai-guard` advisory check — confirm no constitutional drift
  (TDD-first respected; no LLM in hot path) (agent: guard)

### Phase 1: RED — failing tests for spec lifecycle

**Gate**: `pytest tests/unit/specs/test_spec_lifecycle.py` runs and FAILS
at every assertion.

- [ ] T-1.1: Write `tests/unit/specs/test_spec_lifecycle.py` with five test
  classes — `TestStartNew`, `TestMarkShipped`, `TestArchive`, `TestSweep`,
  `TestStatus`. Each covers: happy path, idempotency, FSM illegal-transition
  rejection, atomic write under `artifact_lock`, NDJSON event emission, perf
  assertion (<500ms via `time.monotonic`). Use `tmp_path` fixture (agent: build)

### Phase 2: GREEN — spec_lifecycle.py implementation

**Gate**: T-1.1 tests pass; `python spec_lifecycle.py status` <500ms; NDJSON
event chain valid.

- [ ] T-2.1: Implement domain layer — `LifecycleState` enum, `SpecRecord`
  dataclass, `LEGAL_TRANSITIONS` dict, pure `transition(state, action) -> state`
  validator. **DO NOT modify test files from T-1.1.** (agent: build)
- [ ] T-2.2: Implement infra layer — `_load_state()` / `_write_state()`
  (atomic via tempfile + os.replace, `artifact_lock` guarded), 7-column
  markdown projection writer reading any N ∈ {5,6,7}-col legacy row, NDJSON
  appender. **DO NOT modify test files from T-1.1.** (agent: build)
- [ ] T-2.3: Implement application API — `start_new`, `mark_shipped`,
  `archive`, `sweep` (DRAFT > 14d → ABANDONED; SHIPPED + next brainstorm →
  ARCHIVED), `status`. CLI dispatch via `argparse`. **DO NOT modify test files
  from T-1.1.** (agent: build)
- [ ] T-2.4: Verify pytest green; perf <500ms passes on cold cache (agent: verify)

### Phase 3: Wire-in to skills + history migration

**Gate**: three SKILL.md files reference `spec_lifecycle.py` fail-open;
`_history.md` shows 7-col header; legacy rows preserved verbatim.

- [ ] T-3.1: Edit `ai-brainstorm/SKILL.md` — insert step 1.0 (before evidence
  sweep): `python spec_lifecycle.py start_new <slug> <title>` (fail-open).
  Update `## Integration` calls list (agent: build)
- [ ] T-3.2: Edit `ai-pr/SKILL.md` — replace step 11's manual row append with
  `mark_shipped <spec-id> <pr> <branch>` post-merge (fail-open). Remove obsolete
  manual-row instructions (agent: build)
- [ ] T-3.3: Edit `ai-cleanup/SKILL.md` — add Phase 3 "Spec sweep (`--specs`)"
  invoking `sweep()`; extend frontmatter `argument-hint`; extend Quick Reference
  (agent: build)
- [ ] T-3.4: Migrate `.ai-engineering/specs/_history.md` to 7-column layout via
  `spec_lifecycle.py migrate-history` (one-shot CLI subcommand from T-2.3);
  preserve free-form retro sections below `---`; verify diff is column-only
  (agent: build)

### Phase 4: RED→GREEN — root governance docs voice rewrite

**Gate**: `pytest tests/unit/docs/test_canonical_docs_consistency.py` green;
AGENTS.md ≤80 lines; CLAUDE.md governance hooks section present.

- [ ] T-4.1: Write `tests/unit/docs/test_canonical_docs_consistency.py` —
  AGENTS.md ≤80 lines; skill count text matches `manifest.yml` length (target
  46 post-M3, parameterized); agent count matches manifest (target 23
  post-rename); verbatim seven-step chain `/ai-brainstorm → /ai-plan →
  /ai-build → /ai-verify → /ai-review → /ai-commit → /ai-pr` in both AGENTS.md
  and CLAUDE.md; legacy names from D-127-04 absent; CLAUDE.md "Governance
  hooks" section enumerates `skill_lint`, `test_layer_isolation`, eval gate,
  hot-path budgets. Tests must FAIL before T-4.2/T-4.3 (agent: build)
- [ ] T-4.2: Rewrite `AGENTS.md` to ≤80 lines per brief §18.2 — Boris+Karpathy
  voice, two-file state pattern (`plan.md` + `LESSONS.md`), seven-step chain
  verbatim, "Skills (46)" + "Agents (23)" headings. **DO NOT modify test files
  from T-4.1.** (agent: build)
- [ ] T-4.3: Reorder + edit `CLAUDE.md` — order: hot-path → Step 0 → tooling.
  Add "Governance hooks" section. Convert openers to imperative-bold. Preserve
  Claude-Code-specific specifics. **DO NOT modify test files from T-4.1.**
  (agent: build)
- [ ] T-4.4: Verify pytest green (agent: verify)

## Phase Dependency Graph

```
P0 ──→ P1 ──→ P2 ──→ P3 ──→ P4
              └────────────→ P4 (T-4.1 RED can start once P2 done)
```

## TDD Pairing

- **T-1.1 → T-2.1/T-2.2/T-2.3** (lifecycle implementation under one RED)
- **T-4.1 → T-4.2/T-4.3** (docs rewrite under one RED)

Each GREEN task carries **"DO NOT modify test files from T-X.Y"**.

## Hot-path budget

All `spec_lifecycle.py` atomic ops <500ms. No LLM. Stdlib only. Reuses
`artifact_lock` from `.ai-engineering/scripts/hooks/_lib/locking.py`.

## Done conditions

- [ ] `spec_lifecycle.py` ships idempotent `start_new`, `mark_shipped`,
  `archive`, `sweep`, `status`; tests green; <500ms per op
- [ ] `/ai-brainstorm` calls `start_new` (fail-open)
- [ ] `/ai-pr` calls `mark_shipped` post-merge (fail-open)
- [ ] `/ai-cleanup --specs` calls `sweep()` (fail-open)
- [ ] `_history.md` 7-column header `(ID, Title, Status, Created, Shipped, PR,
  Branch)`; legacy rows preserved
- [ ] `AGENTS.md` ≤80 lines; canonical seven-step chain verbatim
- [ ] `CLAUDE.md` reordered; Governance hooks section present
- [ ] `tests/unit/docs/test_canonical_docs_consistency.py` green

## Self-Report
[EMPTY -- populated by Phase 4]
