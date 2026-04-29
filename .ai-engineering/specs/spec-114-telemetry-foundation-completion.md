---
spec: spec-114
title: Telemetry Foundation Completion — Copilot DRY + Hot-Path SLO + NDJSON Reset + Clean Code
status: approved
effort: large
refs:
  - .ai-engineering/specs/spec-112-telemetry-foundation.md
  - .ai-engineering/runs/spec-110-111-112-2026-04-29/items/spec-112/report.md
  - .ai-engineering/specs/spec-110-governance-v3-harvest.md
---

## Summary

spec-112 closed PARTIAL on 2026-04-29 with Phase 1+2 (telemetry-skill fix,
unified `FrameworkEvent` schema, sealed `_lib/hook-common.py`,
Codex/Gemini hook bridges). Phase 2 cleanup (Copilot DRY), Phase 3
(hot-path SLO + CI cross-OS matrix), Phase 4 (NDJSON reset + clean code
audit + final gates) were deferred to this spec. spec-114 closes the
telemetry foundation entirely so spec-115 (`/skill-sharpen × 49`) can run
on ≥14 days of clean post-reset data.

## Goals

- G-1: Copilot adapters share `_lib/copilot-common.{sh,ps1}` instead of
  duplicating fail-open boilerplate; 12 hook pairs refactored; line
  count drops by ≥30% across the Copilot adapter surface.
- G-2: Hot-path SLO instrumentation — every Python hook records
  `duration_ms` in its emitted event; SLO config in `manifest.yml`
  (`hot_path_slos`) drives `ai-eng doctor --check hot-path` reporting.
- G-3: SLO violation events emit `kind: hot_path_violation` with the
  hook name, observed p95, configured budget, and a `bug_tag:
  infra:slow-hook` label.
- G-4: CI cross-OS matrix — new `.github/workflows/test-hooks-matrix.yml`
  runs the hook unit + integration tests across `ubuntu-latest`,
  `macos-latest`, `windows-latest` per push + PR.
- G-5: NDJSON reset command — `ai-eng maintenance reset-events`
  archives the current `framework-events.ndjson` to
  `.legacy-<YYYY-MM-DDTHH-MM-SS>.gz` and writes a fresh empty file with
  a single `framework_operation` seed event.
- G-6: Reset is gated on spec-110 merged into `main` (hash-chain root
  migration finalized); refuses to run if the legacy `detail.prev_event_hash`
  read path still emits warnings within the last 24 h of events.
- G-7: Clean code audit — every function in `src/ai_engineering/` and
  `.ai-engineering/scripts/hooks/` is ≤50 LOC, named per project
  convention; obvious comments removed; deviations recorded with a
  rationale.
- G-8: Final pre-release gates pass — `gitleaks`, `pip-audit`, `ruff
  check`, `ruff format --check`, `ty check` (with templates excluded),
  full pytest, semgrep, governance check, and the dual-plane policy
  engine evaluation.
- G-9: spec-114 closes the entire spec-112 deferred backlog (T-2.9..T-2.14,
  T-3.1..T-3.16, T-4.1..T-4.7, T-4.9..T-4.17); the report under
  `runs/.../items/spec-112/` is updated to `COMPLETE` with cross-link
  to spec-114 commits.

## Non-Goals

- NG-1: No new Python hooks beyond what spec-112 defined.
- NG-2: No re-architecture of the audit-chain (that lives in spec-110).
- NG-3: No `/skill-sharpen × 49` execution (deferred to spec-115 after
  ≥14 days of clean post-reset data — the data quality gate cannot be
  short-circuited).
- NG-4: No telemetry export to OpenTelemetry / OTLP (defer to a future
  spec when external observability is needed).
- NG-5: No marketplace / plugin tier infrastructure.
- NG-6: No backwards-compatible NDJSON migration tooling — the reset
  is a clean break (the archived `.legacy-*.gz` is the historical
  record).
- NG-7: No multi-region or multi-tenant audit-chain support.
- NG-8: No skill or agent deletion (preserve the full surface).
- NG-9: No relaxation of the 1 s pre-commit / 5 s pre-push hot-path
  budgets.
- NG-10: No bypassing of the spec-110-merged gate for the reset command;
  the gate is a hard precondition.

## Decisions

- **D-114-01** — Copilot DRY extraction lives in
  `.ai-engineering/scripts/hooks/_lib/copilot-common.sh` and
  `.ai-engineering/scripts/hooks/_lib/copilot-common.ps1`. Each adapter
  pair sources/imports the lib via a 1-line preamble. Functions exposed:
  `read_stdin_payload`, `emit_event`, `should_fail_open`, `log_to_stderr`.
- **D-114-02** — Hot-path SLO config schema in `manifest.yml`:
  ```yaml
  hot_path_slos:
    pre_commit_p95_ms: 1000
    pre_push_p95_ms: 5000
    skill_invocation_overhead_p95_ms: 200
    rolling_window_events: 100
  ```
  Defaults are spec-112 D-112-08 budgets. `ai-eng doctor --check
  hot-path` reads the last `rolling_window_events` per hook, computes
  p95, compares against budget, reports PASS/FAIL.
- **D-114-03** — Hot-path violations are advisory in the PR pipeline
  (warn but don't block) and blocking in pre-release gates. This avoids
  flaky CI from a transient slow run while preserving the SLO signal.
- **D-114-04** — CI cross-OS matrix runs only the *hook* tests
  (`tests/integration/test_codex_hooks.py`, `tests/integration/test_gemini_hooks.py`,
  `tests/unit/_lib/`, `tests/unit/hooks/`). Full-suite cross-OS is
  defer-able and CI-cost expensive; targeted matrix gives 95% of the
  cross-platform signal.
- **D-114-05** — NDJSON reset archive name uses ISO 8601 with `T` and
  `-` only (no `:` for cross-OS filesystem safety). Format:
  `framework-events.ndjson.legacy-2026-04-29T15-23-04.gz`.
- **D-114-06** — Reset seed event structure:
  ```json
  {"kind":"framework_operation","engine":"ai_engineering",
   "timestamp":"<ISO>","component":"maintenance.reset-events",
   "outcome":"success","correlationId":"<uuid>","schemaVersion":"1.0.0",
   "project":"<root>","detail":{"reset_reason":"spec-114 G-5",
   "previous_archive":"<path>"}}
  ```
- **D-114-07** — Clean code audit threshold: function bodies ≤50 LOC
  (excluding docstring + decorators). Functions exceeding the threshold
  are either refactored (extract helper) or annotated with a
  `# audit:exempt:<reason>` comment that survives ruff (rationale in
  the comment, no suppression).
- **D-114-08** — Final gates run via existing `ai-eng gate` and
  `ai-eng verify` commands; spec-114 does not introduce new gate
  infrastructure, only ensures the existing gates pass on the new code.

## Risks

- **R-1** — NDJSON reset triggered before spec-110 merges → hash-chain
  data lost mid-migration. **Mitigation**: hard gate in `reset-events`
  reads `git log origin/main` for spec-110 commits; refuses if absent.
- **R-2** — Copilot DRY refactor breaks existing hook contracts.
  **Mitigation**: byte-equivalent test (`test_copilot_adapter_byte_equivalent`)
  before refactor; functional tests preserved; rollback plan = revert
  the `_lib/copilot-common.*` files (single commit unit).
- **R-3** — Hot-path SLO measurement adds latency to the hot path
  (paradox). **Mitigation**: `time.perf_counter()` calls only — under
  100 ns each, dwarfed by hook work; SLO reporting reads from NDJSON
  asynchronously in `doctor`, not in-band.
- **R-4** — Cross-OS CI matrix exposes Windows-specific breakage we did
  not catch locally. **Mitigation**: scope reduced to hook tests only
  (D-114-04); failures are advisory for first 7 days, blocking after;
  spec-114 ships `windows_unsupported_reason` field for hooks legitimately
  Linux/macOS-only (none expected, but escape hatch present).
- **R-5** — Clean code audit refactor introduces regressions.
  **Mitigation**: refactor only behind passing tests (TDD-light: assert
  current behavior in tests first, then extract); each refactor is its
  own commit for cherry-pick rollback.
- **R-6** — Final gates fail on the merged surface (spec-110+111+112+114).
  **Mitigation**: gates run after each phase, not only at end; failures
  rolled back same-phase before next phase begins.
- **R-7** — spec-115 (sharpen) starts before 14 days of clean data
  accumulate post-reset. **Mitigation**: spec-115 entry condition
  documented; `ai-eng maintenance reset-events --print-eligible-date`
  prints the earliest date sharpen can run.
- **R-8** — Reset breaks downstream tooling that reads NDJSON expecting
  legacy `detail.prev_event_hash` location. **Mitigation**: the
  spec-110 dual-read warning logs already flag legacy reads; spec-114
  reset gate refuses if any legacy reads happened in the last 24 h.
- **R-9** — Auto-format / ruff sweeps over hooks lib trigger ty-check
  diagnostics. **Mitigation**: `--exclude templates/**` already
  configured; canonical hooks live outside `src/` so ty does not see
  them; tests cover the runtime contract.

## References

- spec-112-telemetry-foundation.md — original spec; deferred section in §
  "Final Delivery State" is the source of truth for spec-114 scope.
- runs/spec-110-111-112-2026-04-29/items/spec-112/report.md — partial
  delivery report enumerating exact deferred tasks.
- spec-110-governance-v3-harvest.md — D-110-03 hash-chain root migration
  (precondition R-1 / G-6).
- spec-111-ai-research-skill.md — citation/persistence patterns reused
  for the reset seed event structure (D-114-06).
- v3 ADR-0009 (`clear-framework-evals.md`) — informs hot-path SLO
  measurement methodology.
