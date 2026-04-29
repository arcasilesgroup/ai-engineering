# Plan: spec-114 Telemetry Foundation Completion

## Pipeline: full
## Phases: 4
## Tasks: 35 (build: 28, verify: 5, guard: 2)

## Architecture

**Layered + Ports/Adapters (continuation of spec-112)**.

- `_lib/copilot-common.{sh,ps1}` is the shared port for Copilot adapters
  (parallel structure to `_lib/hook-common.py`).
- `manifest.yml.hot_path_slos` is the configuration port for SLO targets;
  `ai-eng doctor --check hot-path` is the verification adapter.
- `ai-eng maintenance reset-events` is a one-shot CLI command (subcommand
  under existing `maintenance` group); persistent state lives in NDJSON.
- CI cross-OS matrix is a workflow-as-config artifact; no runtime code.

No new bounded contexts. Continues spec-112's hexagonal hook-port pattern.

---

## Phase 1: Copilot DRY (T-2.9..T-2.14)

**Gate**: `_lib/copilot-common.sh` and `_lib/copilot-common.ps1` exist
in canonical and template; 12 Copilot hook pairs in
`.ai-engineering/scripts/hooks/copilot-*.{sh,ps1}` are refactored to
source/import the lib; functional tests still pass; line count drops
≥30% across the Copilot adapter surface.

- [ ] T-1.1: Write failing test
  `tests/unit/_lib/test_copilot_common_sh.py::test_lib_exports_required_functions`
  asserting `_lib/copilot-common.sh` defines functions `read_stdin_payload`,
  `emit_event`, `should_fail_open`, `log_to_stderr` (agent: build)
- [ ] T-1.2: Write failing test
  `tests/unit/_lib/test_copilot_common_ps1.py::test_lib_exports_required_functions`
  asserting `_lib/copilot-common.ps1` defines the same functions
  (PowerShell `Get-Command` introspection) (agent: build, blocked by T-1.1)
- [ ] T-1.3: Create `.ai-engineering/scripts/hooks/_lib/copilot-common.sh`
  with the 4 required functions; sealed (no external deps beyond Bash
  builtins + `jq`) (agent: build, blocked by T-1.2)
- [ ] T-1.4: Create `.ai-engineering/scripts/hooks/_lib/copilot-common.ps1`
  with the same 4 functions; sealed (no external deps beyond `Get-Content`,
  `ConvertFrom-Json`, `ConvertTo-Json`) (agent: build, blocked by T-1.3)
- [ ] T-1.5: Mirror both libs to
  `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/`
  (byte-equivalent) (agent: build, blocked by T-1.4)
- [ ] T-1.6: Refactor `copilot-skill.sh` + `copilot-skill.ps1` to
  source/import the shared lib; verify tests in
  `tests/integration/test_copilot_*` pass (agent: build, blocked by T-1.5)
- [ ] T-1.7: Refactor remaining 11 Copilot hook pairs:
  `copilot-injection-guard`, `copilot-auto-format`, `copilot-mcp-health`,
  `copilot-instinct-observe`, `copilot-instinct-extract`,
  `copilot-session-start`, `copilot-session-end`, `copilot-deny`,
  `copilot-error`, `copilot-agent`, `copilot-strategic-compact` (agent:
  build, blocked by T-1.6)
- [ ] T-1.8: Mirror all refactored adapters to template; verify
  `test_template_parity` passes (agent: build, blocked by T-1.7)
- [ ] T-1.9: Phase 1 verification — gitleaks + ruff + pytest unit/integration
  on `tests/unit/_lib/`, `tests/integration/test_copilot_*` (agent: verify,
  blocked by T-1.8)
- [ ] T-1.10: Compute LOC reduction across `copilot-*.{sh,ps1}` baseline
  vs post-refactor; confirm ≥30% drop; record in commit message (agent:
  verify, blocked by T-1.9)

---

## Phase 2: Hot-Path SLO + CI Matrix (T-3.1..T-3.10)

**Gate**: `manifest.yml` defines `hot_path_slos`; every Python hook
emits `duration_ms` in its event detail; `ai-eng doctor --check hot-path`
reports p95 vs budget; SLO violations emit `kind: hot_path_violation`;
`.github/workflows/test-hooks-matrix.yml` runs hook tests on
ubuntu/macos/windows.

- [ ] T-2.1: Write failing test
  `tests/unit/config/test_manifest.py::TestHotPathSlos::test_defaults_present`
  asserting `manifest.hot_path_slos.pre_commit_p95_ms == 1000` (agent: build)
- [ ] T-2.2: Add `HotPathSlosConfig` pydantic model to
  `src/ai_engineering/config/models.py`; load from `manifest.yml`;
  add to `ManifestConfig` schema (agent: build, blocked by T-2.1)
- [ ] T-2.3: Update `manifest.yml` (canonical + template) to include
  `hot_path_slos` block per D-114-02 (agent: build, blocked by T-2.2)
- [ ] T-2.4: Write failing test
  `tests/unit/_lib/test_hook_common.py::test_emit_event_records_duration_ms`
  asserting `emit_event` injects `detail.duration_ms` when invoked via
  `run_hook_safe` wrapper (agent: build, blocked by T-2.3)
- [ ] T-2.5: Extend `_lib/hook-common.py::run_hook_safe` to capture
  `time.perf_counter()` start/end and inject `duration_ms` (rounded to
  ms) into the emitted event detail before `emit_event` (agent: build,
  blocked by T-2.4)
- [ ] T-2.6: Mirror updated `hook-common.py` to template; byte-equiv
  test verifies parity (agent: build, blocked by T-2.5)
- [ ] T-2.7: Write failing test
  `tests/unit/cli/test_doctor_hot_path.py::test_doctor_check_hot_path_reads_ndjson`
  asserting `ai-eng doctor --check hot-path` reads last 100 events per
  hook, computes p95, compares against SLO budget (agent: build, blocked
  by T-2.6)
- [ ] T-2.8: Implement `--check hot-path` subcommand in
  `src/ai_engineering/cli_commands/doctor.py`; emits structured table
  (hook | p95_ms | budget_ms | status); SLO violations also emit
  `hot_path_violation` event with `bug_tag: infra:slow-hook` (agent:
  build, blocked by T-2.7)
- [ ] T-2.9: Write failing test
  `tests/integration/test_ci_workflows.py::test_test_hooks_matrix_workflow_present`
  asserting `.github/workflows/test-hooks-matrix.yml` exists, runs on
  ubuntu/macos/windows, executes `pytest tests/unit/_lib tests/unit/hooks
  tests/integration/test_codex_hooks.py tests/integration/test_gemini_hooks.py
  tests/integration/test_copilot_*` (agent: build, blocked by T-2.8)
- [ ] T-2.10: Create `.github/workflows/test-hooks-matrix.yml` with
  matrix strategy; SHA-pin all actions per spec-110 Article VI; uses
  same Python+uv setup as ci-check.yml (agent: build, blocked by T-2.9)

---

## Phase 3: NDJSON Reset + Hash-Chain Finalize (T-4.1..T-4.7)

**Gate**: `ai-eng maintenance reset-events` archives NDJSON to
`.legacy-<ISO>.gz` and writes fresh empty file with seed event;
refuses to run unless spec-110 commits are in `git log origin/main`
AND no legacy `prev_event_hash` reads in last 24 h. Hash-chain
root migration warning is removed from `audit_chain.py` once spec-110
30-day window has elapsed (or before, manually triggered by reset).

- [ ] T-3.1: Write failing test
  `tests/integration/test_maintenance_reset.py::test_reset_archives_and_creates_fresh_ndjson`
  asserting reset moves current `framework-events.ndjson` to
  `.legacy-<ISO>.gz`, writes fresh empty file with one seed event
  matching D-114-06 schema (agent: build)
- [ ] T-3.2: Write failing test
  `tests/integration/test_maintenance_reset.py::test_reset_refuses_without_spec_110_in_main`
  asserting reset exits non-zero with clear message when spec-110
  commits are not yet in `git log origin/main` (agent: build, blocked
  by T-3.1)
- [ ] T-3.3: Write failing test
  `tests/integration/test_maintenance_reset.py::test_reset_refuses_with_recent_legacy_reads`
  asserting reset refuses if any `legacy hash location detected` warning
  was logged in the last 24 h (agent: build, blocked by T-3.2)
- [ ] T-3.4: Implement `ai-eng maintenance reset-events` subcommand in
  `src/ai_engineering/cli_commands/maintenance.py`: gzip archive (per
  D-114-05 naming), seed event (per D-114-06 schema), gate checks (R-1
  + R-8 mitigations); flag `--print-eligible-date` returns earliest
  date `/skill-sharpen × 49` may run (now + 14 days) (agent: build,
  blocked by T-3.3)
- [ ] T-3.5: Wire reset command into existing `maintenance` Typer
  subgroup; add `--help` documentation; emit
  `framework_operation.maintenance.reset-events` event on completion
  (agent: build, blocked by T-3.4)
- [ ] T-3.6: Audit `src/ai_engineering/state/audit_chain.py` for the
  spec-110 30-day legacy-read warning; add an explicit comment block
  documenting the 2026-05-29 sunset date so spec-115 can simplify the
  reader (agent: build, blocked by T-3.5)
- [ ] T-3.7: Phase 3 verification — pytest on
  `tests/integration/test_maintenance_reset.py`,
  `tests/unit/state/test_audit_chain.py`; gitleaks; ruff
  (agent: verify, blocked by T-3.6)

---

## Phase 4: Clean Code Audit + Final Gates (T-4.9..T-4.17)

**Gate**: every function in `src/ai_engineering/` and
`.ai-engineering/scripts/hooks/` has a body ≤50 LOC OR is annotated
with `# audit:exempt:<reason>`; final gates pass (gitleaks, pip-audit,
ruff format+check, ty check excluding templates, full pytest, semgrep,
governance check); spec-114 closure report committed to run-state.

- [ ] T-4.1: Audit script — `python scripts/audit_function_size.py`
  scans `src/ai_engineering/` + `.ai-engineering/scripts/hooks/`
  (excluding `templates/`) and reports functions >50 LOC; output JSON
  with file, function, LOC count, has-exempt-comment status (agent:
  build)
- [ ] T-4.2: Run audit; identify offenders; for each: refactor (extract
  helper) OR annotate with `# audit:exempt:<reason>` if refactor would
  obscure intent (agent: build, blocked by T-4.1)
- [ ] T-4.3: Audit obvious comments — find single-line comments that
  restate code (e.g., `# return result`) and remove them (agent: build,
  blocked by T-4.2)
- [ ] T-4.4: Naming consistency pass — module-level helpers prefixed
  `_`; exported callables use `snake_case`; classes use `PascalCase`;
  fix any drift (agent: build, blocked by T-4.3)
- [ ] T-4.5: Run full pytest suite; assert 0 regressions vs pre-spec-114
  baseline (agent: verify, blocked by T-4.4)
- [ ] T-4.6: Run final gates — `gitleaks`, `pip-audit`, `ruff format
  --check`, `ruff check`, `ty check --exclude templates/**`, `semgrep`
  (agent: verify, blocked by T-4.5)
- [ ] T-4.7: Run governance check — `ai-eng verify --full` (or
  equivalent); confirm no NG-1..NG-10 violations introduced (agent: guard,
  blocked by T-4.6)
- [ ] T-4.8: Update `runs/spec-110-111-112-2026-04-29/items/spec-112/report.md`
  status: PARTIAL → COMPLETE with cross-link to spec-114 commits (agent:
  build, blocked by T-4.7)
- [ ] T-4.9: Write `runs/spec-110-111-112-2026-04-29/items/spec-114/report.md`
  closure report (Verdict / Goals coverage / Commits / Tests / Wins);
  copy spec.md + plan.md into `items/spec-114/` for run-state
  completeness (agent: build, blocked by T-4.8)
- [ ] T-4.10: Final pre-dispatch governance check — confirm no Identity
  Broker, Input Guard ML, OTel exporter, marketplace, regulated profiles,
  TrueFoundry, TS rewrite, Hexagonal, skill/agent deletion (agent:
  guard, blocked by T-4.9)

---

## Notes

- Phase order is sequential because each phase produces artifacts the
  next consumes (Copilot lib → hot-path SLO instrument → reset gate
  reads NDJSON → audit reads refactored code).
- Bundling tasks within a phase via `ai-build` agent dispatch is
  encouraged; the agent runs RED→GREEN cycles per task batch.
- Hot-path SLO violations are advisory through 2026-05-31 (R-3 / R-4
  mitigation period); blocking thereafter.
- spec-115 (`/skill-sharpen × 49`) starts 14 days after Phase 3 reset
  lands in `main`.
