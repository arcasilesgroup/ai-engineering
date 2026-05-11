---
spec: spec-128
title: Context Layout Refactor — Stack-Based Overrides
pipeline: full
status: awaiting-approval
---

# Plan — spec-128 Context Layout Refactor

## Pipeline

`full` — affects >5 files, touches production telemetry and router, requires test-first changes, and propagates across 4 IDE mirrors.

## Design Routing

`--skip-design` — structural refactor, no UX/UI surface change, no new user-facing flows. Filesystem layout + code paths only.

## Architecture

**Pattern**: Hexagonal Architecture (ports and adapters).

**Justification**: The skill execution core (e.g., `ai-build`, `ai-review`) defines a port — "give me project-specific guidance for the active stack". Today the adapter side has two implementations (per-language and per-framework) plus an autogen mirror (Copilot instructions). The refactor consolidates the adapter side into a single `overrides/<stack>/` adapter slot per stack, removing the redundant lang/framework split and the autogen mirror. The router (`tools/skill_app/deterministic_router.py`) is the port boundary; replacing two adapter lookups with one stack lookup is the core invariant change. This is canonical hexagonal cleanup: the core is unchanged, only the adapter wiring is collapsed.

## Phases

### Phase 1 — Audit & Baseline (read-only) — STATUS: DONE

| Task | Agent | Concern | Done condition | Status |
|---|---|---|---|---|
| **T-001**: Full-repo grep audit. Write classification to `.ai-engineering/runtime/spec-128-audit.md`. | ai-explore | discovery | 32 canonical refs + 27 mirror propagations classified. | ✅ DONE |
| **T-002**: Stack list (Q1). | ai-explore | decision | D-128-09 = bare-language: `python, typescript, go, rust, swift, csharp, kotlin` (Option A; user adjudication). | ✅ DONE |
| **T-003**: `overrides/_shared/` policy (Q2). | ai-explore | decision | D-128-10 = YES (cross-cutting refs in compliance-trace, observability `shared-framework`, execution-kernel `team:`). | ✅ DONE |
| **T-004**: Classify adapter content. | ai-explore | discovery | Audit complete; project-specific deltas preserved per stack in T-026. | ✅ DONE |
| **T-005**: Manifest `providers.stacks` schema (Q4). | ai-explore | decision | D-128-11 = bare-language tokens (composite breaks router). | ✅ DONE |
| **T-006**: Telemetry verification per AM-04 + baseline. | ai-eval | measurement | Telemetry: ZERO language/framework declared loads (88 events all other classes). Hypothesis preserved with caveat (telemetry necessary-not-sufficient). T-031 eval delta is canonical safety gate. Baseline `/ai-eval` deferred — Phase 7 T-031 will produce both pre and post via existing eval gate. | ✅ DONE |

**Phase 1 gate**: ✅ audit.md complete; D-128-09, D-128-10, D-128-11 locked; AM-04 verification done.

### Phase 2 — TDD RED (failing tests)

| Task | Agent | Concern | Done condition |
|---|---|---|---|
| **T-007**: Write failing test in `tests/unit/router/test_deterministic_router.py` asserting stack-based resolution returns `overrides/<stack>/conventions.md` for a given stack. | ai-build (test) | router contract | Test fails with expected error referencing the missing stack-resolve path. DO NOT touch router source. |
| **T-008**: Write failing test in `tests/unit/test_framework_context_loads.py` asserting telemetry emits `context_class == "stack"` (no `language`, no `framework`). | ai-build (test) | telemetry contract | Test fails on current taxonomy; assertion references new `stack` class. |
| **T-009**: Write failing test in `tests/adapters/test_adapter_scaffolding.py` (renamed → `tests/overrides/test_overrides_scaffolding.py`) asserting `overrides/<stack>/` shape (`conventions.md` required; `security_floor.md`, `examples/` optional). | ai-build (test) | overrides shape | Test fails because `overrides/` does not exist yet. |
| **T-010**: Add failing test asserting `scripts/sync_mirrors/core.py` does NOT generate `instructions/<lang>.instructions.md` after refactor (Surface 6 gone). | ai-build (test) | sync mirror contract | Test fails because Surface 6 still runs in current code. |

**Phase 2 gate**: 4 RED tests all fail with expected messages; no production code touched.

### Phase 3 — TDD GREEN (production code)

| Task | Agent | Concern | Done condition |
|---|---|---|---|
| **T-011**: Refactor `tools/skill_app/deterministic_router.py` to resolve by stack. Constraint: DO NOT modify test files from T-007. | ai-build (code) | router | T-007 GREEN; no other router tests regress. |
| **T-012**: Refactor telemetry — `emit_declared_context_loads` (and any helper in `tools/skill_app/.../observability`) to emit `context_class == "stack"`. Update enum / type union. Constraint: DO NOT modify test files from T-008. | ai-build (code) | telemetry | T-008 GREEN; existing telemetry consumers updated. |
| **T-013**: Refactor `scripts/sync_mirrors/core.py` — remove Surface 6 entirely (instructions/<lang> generator, helper functions, GITHUB_INSTRUCTIONS const if unused). Keep Surface 8 (copilot-instructions.md). Constraint: DO NOT modify test files from T-010. | ai-build (code) | sync mirror | T-010 GREEN; Surface 8 still works. |
| **T-014**: Refactor `tools/skill_domain/standards.py` — remove the 3 explicit refs (lines 241-243). | ai-build (code) | standards | refs gone; standards tests pass. |
| **T-015**: Update manifest schema — `manifest.yml` `providers.stacks` accepts new stack tokens; update validators in `tools/skill_*` and `tools/installer` if any. | ai-build (code) | manifest | Manifest validator accepts new stacks; rejects deprecated `language` / `framework` tokens with clear error. |

**Phase 3 gate**: T-007, T-008, T-010 GREEN; T-014/T-015 introduce no regressions; full test suite re-run shows only expected failures (filesystem ones from Phase 4 still pending).

### Phase 4 — IDE mirror updates (was Phase 6 — INVERTED per AM-01)

**Why first**: per ai-guard concern #1, mirror refs must point at `overrides/` BEFORE filesystem nuke. Otherwise `.claude/skills/ai-review/handlers/lang-*.md` silently degrade.

**Article V compliance (AM-05)**: T-024/T-025 edit only `.claude/`; T-026 propagates.

| Task | Agent | Concern | Done condition |
|---|---|---|---|
| **T-016**: Update `.claude/skills/ai-review/handlers/lang-*.md` (handlers per audit refs B1–B6: python, typescript, go, rust, kotlin, java) — `contexts/languages/<x>.md` → `overrides/<x>/conventions.md`. | ai-build (refs) | mirror | grep finds zero stale refs in `.claude/skills/ai-review/handlers/`. |
| **T-017**: Update remaining `.claude/` refs (audit A1–A6, B7, D7): `skills/ai-security/SKILL.md`, `skills/ai-code/handlers/compliance-trace.md`, `skills/_shared/execution-kernel.md`, `skills/ai-build/SKILL.md`, **`agents/ai-build.md` lines 33–36** (AM-03), `.ai-engineering/contexts/stack-context.md`. | ai-build (refs) | mirror | grep clean across `.claude/` + `.ai-engineering/contexts/stack-context.md`. |
| **T-018**: Run `scripts/sync_mirrors/core.py` to propagate `.claude/` → `.codex/`, `.gemini/`, `.github/`. | ai-build (sync) | mirror | Sync exit 0. |
| **T-019**: Verify mirror parity test (or assert by hash for shared surfaces). | ai-verify | mirror | All 4 IDEs symmetric. |

**Phase 4 gate**: 4 IDE mirrors symmetric; grep finds refs only to `overrides/` (not yet existing — that's expected, GREEN after Phase 5).

### Phase 5 — Filesystem nuke (was Phase 4 — INVERTED per AM-01)

| Task | Agent | Concern | Done condition |
|---|---|---|---|
| **T-020**: `rm -rf .ai-engineering/contexts/frameworks/` (15 files). | ai-build (fs) | delete | Dir absent. |
| **T-021**: `rm -rf .ai-engineering/contexts/languages/` (14 files). | ai-build (fs) | delete | Dir absent. |
| **T-022**: Delete `.github/instructions/*.instructions.md` (17 files). | ai-build (fs) | delete | Glob empty. |
| **T-023**: Delete `src/ai_engineering/templates/project/.github/instructions/` (template mirror). | ai-build (fs) | delete | Dir absent. |
| **T-024**: `git mv .ai-engineering/adapters/ .ai-engineering/overrides/`. | ai-build (fs) | rename | Path renamed; git history preserved. |

**Phase 5 gate**: filesystem matches target; full-repo grep for `contexts/frameworks`, `contexts/languages`, `\.github/instructions/`, `\.ai-engineering/adapters/` returns zero hits in production code (test fixtures using tmp_path are exempt).

### Phase 6 — Restructure overrides

| Task | Agent | Concern | Done condition |
|---|---|---|---|
| **T-025**: With D-128-09 = bare-language (Option A), the 7 stack dirs already exist post-rename (`overrides/{python,typescript,go,rust,swift,csharp,kotlin}/`). Verify post-rename layout; update source-pin headers (audit ref F1) so they no longer reference deleted `contexts/languages/<x>.md`. | ai-build (fs) | scaffolding | 7 stack dirs intact; conventions.md headers updated. |
| **T-026**: For deltas classified as `project-specific` in T-004 audit, retain in `overrides/<stack>/conventions.md`. Slim training-redundant sections per the slim-first hypothesis. | ai-build (fs) | content | conventions.md slim; project-specific deltas preserved. |
| **T-027**: Create `overrides/_shared/` (D-128-10 = yes) with cross-cutting files migrated from `contexts/team/` and shared concerns. | ai-build (fs) | shared | Dir exists; refs from compliance-trace, execution-kernel resolve. |

**Phase 6 gate**: T-009 GREEN (overrides scaffolding test); overrides tree matches design.

### Phase 7 — Verification

| Task | Agent | Concern | Done condition |
|---|---|---|---|
| **T-028**: Regenerate `hooks-manifest.json` (`python3 .ai-engineering/scripts/regenerate-hooks-manifest.py`); run with `--check` to gate. | ai-build (regenerate) | hooks integrity | `--check` exit 0. |
| **T-029**: Run full test suite (`pytest`). Allow only expected new tests; no regressions. | ai-verify | tests | pytest exit 0. |
| **T-030**: Run hot-path budget tests (`tests/perf/test_skill_lint_budget.py`). | ai-verify | perf | All budgets met (pre-commit ≤1s, pre-push ≤5s, /ai-commit ≤1.5s, /ai-pr ≤8s, /ai-verify PASS ≤1s). |
| **T-031**: Run `/ai-eval` post-refactor; diff vs T-006 baseline. Abort + rollback if regression > eval-gate threshold. | ai-eval | regression | Eval delta within threshold; report saved. |
| **T-032**: Run `/ai-verify`. | ai-verify | governance | Verify report PASS. |
| **T-033**: Run `/ai-review`. | ai-review | code review | Review report PASS or only NIT findings. |

**Phase 7 gate**: all green, eval within threshold, hot-paths met, hooks manifest clean.

### Phase 8 — Ship

| Task | Agent | Concern | Done condition |
|---|---|---|---|
| **T-034**: `/ai-commit` — governed commit pipeline. | (commit pipeline) | commit | Commit lands on protected-branch-derived feature branch. |
| **T-035**: `/ai-pr` — open PR with summary referencing spec-128, decisions D-128-01..11, eval delta, hot-path metrics. | (pr pipeline) | ship | PR URL returned. |

**Phase 8 gate**: PR open; CI green.

## Task Count

35 tasks across 8 phases. Avg 2-5 min per task. Total wall-clock estimate: 4-8 hours focused, single operator, no rework.

## Dependencies (critical path)

```
T-001 → T-002, T-003, T-004, T-005, T-006
T-006 (baseline) → T-031 (compare)
T-007 → T-011    (RED → GREEN router)
T-008 → T-012    (RED → GREEN telemetry)
T-009 → T-021    (RED → GREEN overrides shape)
T-010 → T-013    (RED → GREEN sync mirror)
T-011..T-015 → T-016..T-020 (code green before fs nuke)
T-016..T-020 → T-021..T-023 (delete then create)
T-021..T-023 → T-024..T-027 (overrides exist before mirror updates)
T-024..T-027 → T-028..T-033 (mirrors clean before final verify)
T-028..T-033 → T-034 → T-035
```

## TDD Pairs

| RED | GREEN |
|---|---|
| T-007 | T-011 |
| T-008 | T-012 |
| T-009 | T-021 (overrides scaffolding) |
| T-010 | T-013 |

GREEN tasks are constrained: **must not modify test files from paired RED task**.

## Open Questions Resolution

- Q1 → resolved by T-002 (D-128-09).
- Q2 → resolved by T-003 (D-128-10).
- Q3 → resolved by T-004 (audit table).
- Q4 → resolved by T-005 (D-128-11).

All resolutions land in audit.md before Phase 2 begins; spec-128 decisions list is appended in T-002, T-003, T-005.

## No-execution protocol

This file (`plan.md`) is the contract for `/ai-build`. `/ai-plan` writes it and stops. `/ai-build` executes only after explicit user approval.

## Approval requested

User must approve this plan before `/ai-build` runs. Specifically:

1. Confirm pipeline = `full` (vs. splitting into multiple smaller specs).
2. Confirm architecture pattern = hexagonal (vs. ad-hoc).
3. Confirm task decomposition (35 tasks, 8 phases).
4. Confirm TDD pairings.
5. Confirm Phase 4 destructive ops authorized (rm -rf on 46 files; rename `adapters/`).

Run `/ai-build` to execute.
