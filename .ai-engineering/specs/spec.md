---
spec: spec-123
title: Phase 1 Closure — Spec Workflow Standardization + Memory Nuke + State.db Bootstrap + OPA Closure
status: approved
effort: large
---

# Spec 123 — Phase 1 Closure

## Summary

Spec-122 delivered 36 of 40 decisions across hygiene, state.db schema, OPA proper switch, and meta-cleanup, but left structural gaps: state.db was never bootstrapped (schema code shipped, no migration apply path); the legacy memory layer (~3K LOC across `scripts/memory/`, `memory_cmd.py`, and `/ai-remember` + `/ai-dream` skill surfaces) was not removed; the workspace-charter stub at `.ai-engineering/CONSTITUTION.md` still ships; OPA T-3.13/T-3.14/T-3.17/T-3.18 are partial; the autopilot phase-deliver cleanup never ran (its scaffolding lingers); progress-log directories for spec-119/120 still live under `specs/`. More fundamentally, the framework lacks a single canonical spec-workflow contract: `specs/` carries 85+ files (numbered archives, plan archives, exploration companions, progress dirs, autopilot scaffolding, dead work-plane artifacts) and there is no enforcement that every skill follows the same `spec → plan → execute → PR` flow.

This spec closes Phase 1 by collapsing `.ai-engineering/specs/` to three files (`spec.md`, `plan.md`, `_history.md`), nuking the legacy memory subsystem (Engram becomes a third-party product wired at install time, not a wrapped skill), bootstrapping `state.db` via lazy connect plus idempotent install hook with full NDJSON replay, deleting the workspace-charter stub with all 9 callers in lockstep, finishing the OPA closure tasks, fixing the autopilot phase-deliver cleanup bug, and codifying the canonical spec-workflow contract in CONSTITUTION.md.

The end-state is a smaller, single-process framework: every skill that touches `specs/` reads the same three files; everything else is git history or runtime state.

## Goals

- `specs/` directory contains exactly three files: `spec.md`, `plan.md`, `_history.md`. CI guard fails any deviation.
- All numbered archive specs (`spec-NNN-*.md`, `plan-NNN-*.md`, ~50 files), exploration companions (`spec-117-hx-NN-explore.md`, ~12 files), supporting files (`spec-117-harness-*.md` + `spec-117-orchestrator-operating-prompt.md`, 5 files), progress dirs (`spec-119-progress/`, `spec-120-progress/`), dead work-plane artifacts (`task-ledger.json`, `current-summary.md`, `history-summary.md`, `handoffs/`, `evidence/`, `context-packs/`), and autopilot scaffolding deleted from `specs/`. Total: ~85 files removed from active surface.
- Numbered specs recoverable from git history (`git log -- .ai-engineering/specs/spec-NNN-*.md`). Decisions and citations stored authoritatively in `state.db.decisions` and `_history.md`.
- Autopilot transient state relocates to `.ai-engineering/state/runtime/autopilot/` (gitignored) — never lives under `specs/`.
- CONSTITUTION.md gains a new article: "Active Spec Workflow Contract" — defines `/ai-brainstorm → /ai-plan → /ai-dispatch | /ai-autopilot → /ai-pr` as the single canonical flow, with depth scaling for spec size but identical process steps.
- Memory subsystem fully deleted: `.ai-engineering/scripts/memory/` (9 files, ~3K LOC), `src/ai_engineering/cli_commands/memory_cmd.py`, the `ai-eng memory` CLI subcommand, the `/ai-remember` skill (canonical + 3 IDE mirrors + 4 templates), the `/ai-dream` skill (same fan-out), and all `ai-eng memory ...` invocations in skill bodies + docs + CHANGELOG.
- Engram positioned as third-party product: `ai-eng install` adds an interactive prompt ("Install Engram for memory persistence? [y/N]"); on yes detects OS + IDE and runs Engram's official install path (brew on macOS, winget on Windows, direct binary on Linux); writes Engram's per-IDE configuration per its official guide. No Engram-specific Python wrapper code ships in ai-engineering.
- `state.db` exists and contains all 7 STRICT tables populated. Lazy bootstrap: first call to `state_db.connect()` creates the DB, runs all migrations, replays the full NDJSON event log into `events` table (idempotent `ON CONFLICT(span_id) DO NOTHING`), and migrates the 5 JSON state files (`decision-store.json`, `gate-findings.json`, `ownership-map.json`, `install-state.json`, `hooks-manifest.json`) into their respective tables. `ai-eng install` performs the same migration apply idempotently as belt-and-suspenders.
- `.ai-engineering/CONSTITUTION.md` workspace-charter stub deleted. All 9 callers updated in lockstep: `control_plane.py:_CONSTITUTIONAL_ALIASES` reduced to empty tuple; `file_existence.py` source-repo path list cleaned; `manifest_coherence.py` workspace-charter validation block deleted (~50-100 LOC); `standards.py` legacy-retirement family `current_surfaces` reduced to `("CONSTITUTION.md",)`; 7 test fixtures updated; 2 template files cleaned.
- OPA closure: T-3.13 wires OPA into `ai-eng risk accept`; T-3.14 integration golden tests for all three policies via `opa eval` subprocess; T-3.17 CI workflow runs `opa test --coverage` with ≥90% line coverage gate; T-3.18 `/ai-governance` skill + manifest doctor wiring updated to surface OPA decision logs.
- Sub-002 closure: T-2.8 wires sidecar offload into `runtime-guard.py` PostToolUse; T-2.10 zstd seekable compress runs on closed NDJSON months; T-2.11 retention module enforces 90-day HOT cutoff for events tier; T-2.12 `ai-eng audit` CLI gains six verbs (`retention apply`, `rotate`, `compress`, `verify-chain`, `health`, `vacuum`); T-2.22 `audit_index.py` redirects writes/reads to `state.db` with public API preserved.
- Autopilot bug fix: `phase-deliver.md` handler executes its cleanup step reliably (current behavior leaves `specs/autopilot/` after PR). Bug root-caused and fixed.
- All `/ai-implement` references purged repo-wide (CHANGELOG.md:376 + any others). CI guard `tests/unit/docs/test_skill_references_exist.py` already added in spec-122-d covers regression.
- Full unit test suite green (5020+ passing); zero new ruff issues vs baseline; gitleaks clean; OPA bundle loads + verifies; hot-path SLO p95 < 1s preserved.

## Non-Goals

- Phase 2 v2 cutover (specs 200-213 trajectory). Spec-123 closes Phase 1 only.
- Re-implementing the memory layer in any form. Engram replaces it; if user does not install Engram, the framework simply has no memory persistence.
- Migrating to Regorus / OPA-WASM. Phase 2 future-spec option.
- Cross-machine state.db sync. SQLite + WAL is single-host; multi-host scenarios are Litestream territory and not in scope.
- Rewriting solution-intent.md or solution architecture documents beyond the new "Active Spec Workflow Contract" addition.
- Touching `.ai-engineering/state/archive/` historical content. The pre-spec-122-reset backup directory remains as-is until its one-week recovery window elapses (then user may delete).
- Re-introducing `/ai-remember` or `/ai-dream` as skills. They are gone permanently.
- Adding new specs/ files. The contract is exactly three: `spec.md`, `plan.md`, `_history.md`.

## Decisions

### Theme 1 — Spec workflow standardization

**D-123-01: Single canonical spec-workflow flow.** Every skill that touches `specs/` follows the identical sequence: `/ai-brainstorm → /ai-plan → /ai-dispatch | /ai-autopilot → /ai-pr`. Depth and intensity scale with spec size (autopilot for ≥3 concerns or ≥10 files; dispatch otherwise). Process steps do not vary. **Rationale**: framework currently lacks a single source-of-truth process; each skill drifts subtly. Standardization eliminates per-skill variance, makes onboarding deterministic, and prevents the kind of structural drift that produced HX-02's 7-entry work-plane that no skill consumes.

**D-123-02: Three-file specs/ canonical structure.** `.ai-engineering/specs/` contains exactly `spec.md`, `plan.md`, `_history.md`. No subdirectories, no numbered archives, no progress dirs, no work-plane artifacts. **Rationale**: audit shows only `spec.md` (10 skill consumers), `plan.md` (7 consumers), and `_history.md` (1 consumer, `/ai-pr`) are actually read at runtime. The other 4 work-plane artifacts (task-ledger.json, current-summary.md, history-summary.md, handoffs/, evidence/) have zero skill consumers — pure dead weight from HX-02. Numbered archives are cited but never read; git history preserves them losslessly.

**D-123-03: Delete numbered archive specs from specs/.** All `spec-NNN-*.md` and `plan-NNN-*.md` files removed. ~85 files affected. Decisions stay authoritative in `state.db.decisions` (sub-002 schema) and `_history.md` (one-line per spec lifecycle). **Rationale**: numbered specs are immutable historical record; they live in git. Active surface should not duplicate. Cited paths in skill bodies migrate to either decision-store query or git-log-based recovery.

**D-123-04: Delete dead work-plane artifacts.** `task-ledger.json` (HX-02, zero consumers), `current-summary.md` (zero consumers), `history-summary.md` (zero consumers), `handoffs/` (zero consumers), `evidence/` (zero consumers), `context-packs/` (origin unclear, archive). **Rationale**: HX-02 over-engineered the work-plane with structures that no skill ever consumed. Dead code in the active surface is cognitive overhead.

**D-123-05: Autopilot transient state relocates.** `.ai-engineering/specs/autopilot/` → `.ai-engineering/state/runtime/autopilot/` (gitignored). Manifest, sub-NNN/spec.md+plan.md, integrity-report.md all move there. **Rationale**: autopilot scaffolding is per-run transient; it is runtime state, not spec content. Belongs under `state/runtime/` like other transient artifacts (checkpoint.json, tool-history, risk-score.json).

**D-123-06: CI guard enforces canonical specs/ structure.** New test `tests/unit/specs/test_canonical_structure.py` asserts `os.listdir('.ai-engineering/specs')` returns exactly `['_history.md', 'plan.md', 'spec.md']` (sorted). Any other entry fails CI. **Rationale**: prevents the kind of drift that accumulated 85 files. Mechanical enforcement keeps the active surface clean.

**D-123-07: CONSTITUTION.md adds "Active Spec Workflow Contract" article.** New article (Article XIII or next available) codifies D-123-01 + D-123-02 as a non-negotiable governance rule. **Rationale**: standards live in the constitution; CI guards enforce them; skills inherit them. Without this article the structure is convention; with it, it is governance.

### Theme 2 — Memory subsystem nuke

**D-123-08: Delete `.ai-engineering/scripts/memory/`.** All 9 files (audit.py, cli.py, dreaming.py, episodic.py, knowledge.py, repair.py, retrieval.py, semantic.py, store.py) plus `__init__.py`. ~3K LOC. **Rationale**: spec-122 made the deps removal final but left the consumer code in place; result is a CLI surface that fails at import time. Cleanup mode = full delete.

**D-123-09: Delete `src/ai_engineering/cli_commands/memory_cmd.py` + `ai-eng memory` CLI registration.** All `ai-eng memory <subcommand>` paths removed. Click/Typer command tree pruned. **Rationale**: zero consumers post-Phase-5; kept only legacy reference points.

**D-123-10: Delete `/ai-remember` + `/ai-dream` skills with full IDE fan-out.** Canonical at `.claude/skills/{ai-remember,ai-dream}/SKILL.md`, mirrors at `.gemini/skills/...`, `.codex/skills/...`, `.github/skills/...`, plus 4 template copies under `src/ai_engineering/templates/project/<ide>/skills/...`. Total ~16 files deleted. Skill registry in `manifest.yml` decremented. **Rationale**: Engram replaces the skill-level surface. Memory skills no longer exist as ai-engineering primitives.

**D-123-11: Scrub all `ai-eng memory ...` references repo-wide.** Skill bodies, README, AGENTS.md, CLAUDE.md, GEMINI.md, copilot-instructions.md, CHANGELOG.md, docs/. **Rationale**: ghost-references will confuse future contributors and AI agents. Mechanical sed/replace pass.

**D-123-12: Engram positioned as third-party product wired at install time.** `ai-eng install` adds an interactive prompt: "Install Engram for memory persistence? [y/N]". On yes: detect OS (macOS/Linux/Windows) and IDE (Claude Code / Codex / Gemini / Copilot); execute Engram's official install path (`brew install engram` / `winget install Engram` / direct binary download); run `engram setup <agent>` per detected IDE per Engram's documented setup guide. No Engram-specific Python wrapper code ships in ai-engineering — Engram is a peer product, not a dependency. **Rationale**: clean separation. ai-engineering = framework; Engram = memory product. Users opt in. The integration is a one-shot install-time wiring, not a runtime coupling.

### Theme 3 — State.db bootstrap

**D-123-13: Lazy state.db bootstrap on `state_db.connect()`.** First invocation checks if DB exists; if not, creates the file at `.ai-engineering/state/state.db`, applies all migrations (`0001_initial_schema`, `0002_seed_from_json`, `0003_replay_ndjson`), and exits with the open connection ready for use. Migration runner is idempotent (re-running yields no-op). **Rationale**: zero-config UX. Any code path that touches state.db just-works. No new commands for users to remember.

**D-123-14: `ai-eng install` runs migration apply idempotently.** Belt-and-suspenders alongside lazy bootstrap. Fresh installs get migrations applied at install time (no first-call latency); existing repos that re-run install get the same idempotent result. **Rationale**: explicit + lazy together cover both UX paths (fresh install gets DB ready before first use; existing repos auto-migrate on update).

**D-123-15: NDJSON replay populates events table during bootstrap.** Migration `0003_replay_ndjson` reads `framework-events.ndjson` (currently 7767 events post-state-reset) and inserts each into `events` table with `ON CONFLICT(span_id) DO NOTHING`. Replay completes in single `BEGIN IMMEDIATE` transaction. **Rationale**: state.db must be a true projection of the immutable NDJSON SoT. Without replay it is empty and meaningless. Idempotency handles re-runs.

**D-123-16: 5 JSON state files migrated into state.db tables.** Migration `0002_seed_from_json` reads `decision-store.json` → `decisions`, `gate-findings.json` → `gate_findings`, `ownership-map.json` → `ownership_map`, `install-state.json` → `install_steps`, `hooks-manifest.json` verifications stream → `hooks_integrity`. Source files preserved in place (read-only) until spec-124 cleanup confirms no rollback need. **Rationale**: state.db consolidates. Source files kept short-term as fallback recovery.

### Theme 4 — Workspace-charter stub deletion (T-1.2 carry-over)

**D-123-17: Delete `.ai-engineering/CONSTITUTION.md` stub with all 9 callers updated in lockstep.** Files affected: stub itself; `src/ai_engineering/state/control_plane.py` (line 20: `_CONSTITUTIONAL_ALIASES` reduced to empty tuple; lines 89, 348 callers updated); `src/ai_engineering/validator/categories/file_existence.py` (lines 20-26 source-repo path list cleaned); `src/ai_engineering/validator/categories/manifest_coherence.py` (lines ~50-58, ~196-203, ~231-243 workspace-charter validation block deleted, ~50-100 LOC); `src/ai_engineering/standards.py` (line 227 legacy-retirement family `current_surfaces` reduced); 7 test fixtures (`tests/unit/test_validator.py`, `tests/unit/test_validator_extra.py`, `tests/unit/test_constitution_skill_paths.py`, `tests/unit/test_state.py`, `tests/unit/test_lib_observability.py`, `tests/unit/test_framework_context_loads.py`, `tests/unit/config/test_manifest.py`); 2 template files (`src/ai_engineering/templates/.ai-engineering/manifest.yml`, `src/ai_engineering/templates/.ai-engineering/CONSTITUTION.md`). All updates land in single commit to avoid intermediate validator failures. **Rationale**: spec-122 sub-001 T-1.2 self-blocked because the file-boundary frontmatter excluded the test fixtures and templates. Spec-123 includes them all explicitly. Single canonical CONSTITUTION at repo root is the correct end-state.

### Theme 5 — OPA closure (sub-003 deferred items)

**D-123-18: Wire OPA into `ai-eng risk accept` (T-3.13 finish).** `src/ai_engineering/cli_commands/risk_cmd.py` (or wherever risk-accept lives) invokes `data.risk_acceptance_ttl.deny` via `opa_runner.evaluate_deny()`. Failed policy → reject the accept. **Rationale**: third governance touchpoint completes the OPA wiring trio (pre-commit + pre-push + risk-accept).

**D-123-19: Integration golden tests for all three policies (T-3.14 finish).** `tests/integration/governance/test_opa_eval.py` exercises each `.rego` policy with golden inputs producing expected allow/deny. Subprocess invocation via `opa eval --bundle` not Python eval. **Rationale**: end-to-end verification that the bundle + signature pipeline + opa_runner all wire correctly.

**D-123-20: CI workflow opa test --coverage ≥ 90% gate (T-3.17).** New step in `.github/workflows/<existing-test-workflow>.yml` runs `opa test --coverage .ai-engineering/policies/`, asserts ≥ 90% line coverage per policy. Failure blocks merge. **Rationale**: governance code deserves the same coverage rigor as application code.

**D-123-21: `/ai-governance` skill + manifest doctor wiring update (T-3.18).** `/ai-governance` SKILL.md surfaces OPA decision-log queries (last N policy_decisions from state.db.events). `ai-eng doctor` adds an OPA-health check (binary present, bundle signature verifies, policies load). **Rationale**: governance observability + health monitoring closes the loop.

### Theme 6 — Sub-002 closure (state.db ops + audit CLI)

**D-123-22: Wire sidecar offload into runtime-guard.py PostToolUse (T-2.8).** Existing `runtime-guard.py` already offloads tool outputs above `AIENG_TOOL_OFFLOAD_BYTES`. New: events ≥ 3 KB (sidecar threshold) emit a sidecar file at `.ai-engineering/state/runtime/event-sidecars/<sha256>.json` and inline event carries hash + summary. **Rationale**: cross-IDE concurrent NDJSON writes with large events corrupted the audit chain pre-spec-122; sidecar pattern is the documented mitigation.

**D-123-23: zstd seekable compress for closed NDJSON months (T-2.10).** Rotation module already detects month rollover or 256 MB. New: closed-month files run through `zstd --seekable` producing `.ndjson.zst` archives under `.ai-engineering/state/archive/ndjson/YYYY-MM/`. Original removed after compress + verify-chain. **Rationale**: audit retention requires multi-year storage; uncompressed NDJSON bloats. zstd-seekable preserves random access for verify-chain.

**D-123-24: Retention module 90-day HOT cutoff for events tier (T-2.11).** `ai-eng audit retention apply` deletes events older than 90 days from `state.db.events` (audit log retains in NDJSON archive). HOT/WARM/COLD tiering documented in spec-122-b. **Rationale**: SQLite VACUUM costs scale with table size; bounded HOT tier keeps query latency tight.

**D-123-25: ai-eng audit CLI gains 6 verbs (T-2.12).** `retention apply`, `rotate`, `compress`, `verify-chain`, `health`, `vacuum`. Each maps to a function in the existing audit module. **Rationale**: operations need scriptable handles for retention/rotation/integrity workflows.

**D-123-26: audit_index.py redirect to state.db (T-2.22).** `audit_index.py` writes go to `state.db.events` instead of `audit-index.sqlite`. `audit-index.sqlite` deprecated; deleted in same commit if no consumer remains. Public API of `audit_index` module preserved (callers see no change). **Rationale**: state.db is the single canonical projection per CQRS; duplicate audit-index file violates SoT.

### Theme 7 — Autopilot bug fix

**D-123-27: Fix autopilot phase-deliver.md cleanup execution.** Phase-deliver handler (`.claude/skills/ai-autopilot/handlers/phase-deliver.md`) currently documents the cleanup step but spec-122 autopilot run did not execute it (left `specs/autopilot/` populated post-merge). Root-cause + fix: handler should explicitly call `rm -rf .ai-engineering/specs/autopilot/` (or new gitignored path per D-123-05) AND clear `spec.md` + `plan.md` to placeholder. Verify cleanup actually ran via `ls` check before reporting Phase 6 complete. **Rationale**: autopilot must actually finish what it documents; observed behavior leaves residue. Cleanup verification gate prevents recurrence.

### Theme 8 — Documentation drift residual

**D-123-28: Scrub remaining `/ai-implement` references repo-wide.** CHANGELOG.md:376 (known) + any others surfaced by `grep -rn '/ai-implement' --include='*.md' .`. Replace with `/ai-dispatch` or remove. **Rationale**: ghost-skill references confuse contributors and AI agents.

**D-123-29: ai-eng install adds Engram interactive prompt + per-OS / per-IDE wiring.** Reference D-123-12 for full text. Implementation lands in `src/ai_engineering/installer/service.py` or wherever install pipeline lives. **Rationale**: clean third-party integration story.

## Risks

- **Numbered-spec deletion breaks active citations**. Many skill bodies cite paths like `.ai-engineering/specs/spec-118-memory-layer.md` for context. Post-deletion those paths 404. **Mitigation**: pre-deletion grep pass replaces path-citations with either decision-store queries (`state.db.decisions WHERE id = 'D-118-NN'`) or the canonical `_history.md` entry. CI guard `tests/unit/docs/test_skill_references_exist.py` (already exists from spec-122-d) catches regressions. Acceptance criterion: `grep -rn 'spec-[0-9][0-9][0-9]-' --include='*.md' .claude/.gemini/.codex/.github/` returns only `_history.md` references.
- **state.db bootstrap silent failure**. Lazy connect fails to create DB or apply migrations; downstream calls to `state_db.connect()` raise opaque errors. **Mitigation**: bootstrap logs each migration step to `framework-events.ndjson`; first-failure raises a clear `StateDbBootstrapError` with actionable message ("run `ai-eng audit init-db --rebuild` to recover"). Health check `ai-eng doctor` includes a state.db existence + integrity probe.
- **NDJSON replay performance**. 7767 events today; 84K+ in production deployments. Replay in single `BEGIN IMMEDIATE` may exceed transaction time limit. **Mitigation**: chunked replay (1000 events per transaction); progress emitted as `framework_event` records; resumable via `_migrations` ledger checkpoint.
- **Memory CLI deletion strands existing users**. Users with workflows scripted around `ai-eng memory dream` will break. **Mitigation**: deletion shipped behind a one-release deprecation warning would be ideal but spec-123 is cleanup-mode (no soft delete). Mitigation reduces to: CHANGELOG warns clearly; `ai-eng install` post-update emits a one-time notice ("Memory subsystem removed — install Engram for replacement"); README updated with migration guidance.
- **Engram install flakiness**. `brew install engram`, `winget install Engram`, or direct binary download may fail on locked-down machines. **Mitigation**: install prompt is opt-in; on failure, `ai-eng install` reports the failure path and continues without Engram (memory unavailable). User can retry later via `ai-eng install --engram`.
- **Workspace-charter stub deletion blast radius**. T-1.2 self-blocked in spec-122 sub-001 because 7 test fixtures + 2 templates were not in scope. Spec-123 explicitly enumerates them but a missed call site could fail validator at runtime. **Mitigation**: full repo grep `grep -rn '.ai-engineering/CONSTITUTION.md\|workspace_charter\|compatibility_aliases' src/ tests/` before deletion; all hits land in single commit. `ai-eng doctor` post-merge confirms validator green.
- **CI guard for canonical specs/ structure too strict**. Some legitimate workflows may need temporary subdirs (e.g., autopilot before cleanup runs). **Mitigation**: CI guard runs only at PR merge time on default branch (or via `pytest tests/unit/specs/test_canonical_structure.py` invoked explicitly), not on every push. Autopilot transient state lives outside `specs/` per D-123-05 so the guard never trips on autopilot work.
- **Single canonical workflow imposed retroactively breaks skills**. Some skills today bypass `/ai-brainstorm → /ai-plan → /ai-dispatch` (e.g., `/ai-debug`, `/ai-explain`, `/ai-research` operate in their own surface). **Mitigation**: D-123-01 applies only to skills that produce specs. Read-only skills (`/ai-explain`, `/ai-guide`, `/ai-research`, `/ai-debug`, `/ai-explain`, `/ai-standup`) are not affected. CONSTITUTION article scopes the contract to spec-producing skills only.
- **OPA install on locked-down CI runner**. Bundle build/sign/test depends on `opa` binary. **Mitigation**: spec-122-c already documented baking `opa` into CI image. Spec-123 reuses that pattern; no new install path required.
- **Phase 5 of autopilot burns context**. Spec-123 will run via `/ai-autopilot` (≥3 concerns, ≥10 files); same truncation risk as spec-122. **Mitigation**: agent prompts include explicit per-task verification (`ls`, `pytest <specific-test>`, `grep <expected-string>`) so progress is verifiable from disk even if agent narrative truncates. Autopilot bug fix (D-123-27) ensures cleanup runs reliably.

## Open Questions

- Should `_history.md` migrate to `state.db.events` (`kind='spec_lifecycle'`) and the file-system entry become a generated read-model? Doing so would mean `specs/` collapses to two files (`spec.md`, `plan.md`). Defer decision: keep `_history.md` for spec-123 to minimize blast radius; revisit in Phase 2 when `state.db` is fully load-bearing.
- Should the autopilot `phase-deliver.md` cleanup step also archive the integrity report to `state.db` (or `_history.md`) instead of leaving it under `state/runtime/autopilot/`? Open.
- Engram version pin range. Spec-122-b proposed `>=1.15.8,<1.16`. Should spec-123 widen to `>=1.15.8,<2`? Open — depends on Engram's release cadence and breaking-change posture.

## References

- doc: `.ai-engineering/specs/spec-122-framework-cleanup-phase-1.md` (master)
- doc: `.ai-engineering/specs/spec-122-a-hygiene-and-evals-removal.md`
- doc: `.ai-engineering/specs/spec-122-b-engram-and-state-unify.md`
- doc: `.ai-engineering/specs/spec-122-c-opa-proper-switch.md`
- doc: `.ai-engineering/specs/spec-122-d-meta-cleanup.md`
- doc: `.ai-engineering/specs/autopilot/integrity-report.md`
- doc: `src/ai_engineering/state/work_plane.py` (HX-02 resolver — to be simplified per D-123-04)
- doc: `src/ai_engineering/state/state_db.py` (sub-002 schema)
- doc: `src/ai_engineering/state/migrations/` (sub-002 migration runner)
- doc: `src/ai_engineering/governance/opa_runner.py` (sub-003 wrapper)
- doc: `src/ai_engineering/governance/policy_engine.py` (Phase 5 shim)
- doc: `.claude/skills/ai-autopilot/handlers/phase-deliver.md` (bug fix target)
- doc: `.claude/skills/ai-brainstorm/SKILL.md`
- doc: `.claude/skills/ai-plan/SKILL.md`
- doc: `.claude/skills/ai-dispatch/SKILL.md`
- doc: `.claude/skills/ai-pr/SKILL.md`
- doc: `CONSTITUTION.md` (target for new "Active Spec Workflow Contract" article)
- pr: arcasilesgroup/ai-engineering#505 (spec-122 delivery, predecessor)
- ext: https://github.com/Gentleman-Programming/engram (Engram product)
- ext: https://www.openpolicyagent.org/docs/v1.2/ (OPA reference)
- ext: https://sqlite.org/lang_attach.html (state.db migration patterns)
- ext: https://github.com/facebook/zstd/blob/dev/contrib/seekable_format/README.md (zstd seekable for D-123-23)
