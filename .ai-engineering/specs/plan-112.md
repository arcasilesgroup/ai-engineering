# Plan: spec-112 Telemetry Foundation

## Pipeline: full
## Phases: 4
## Tasks: 59 (build: 48, verify: 9, guard: 2)

## Architecture

**Ports and Adapters**.

Justification: spec-112 has a genuine ports-and-adapters shape — the **port** is the unified telemetry contract (`FrameworkEvent` TypedDict + `emit_event()` interface in `_lib/hook-common.py`); the **adapters** are per-IDE bridges that translate vendor-specific hook contracts into the unified schema:
- Claude Code adapter: existing `.py` hooks call `_lib/hook-common.emit_event()` directly (no bridge needed).
- Codex CLI adapter: `codex-hook-bridge.py` translates Codex JSON contract (`developers.openai.com/codex/hooks`) → `emit_event()`.
- Gemini CLI adapter: `gemini-hook-bridge.py` translates Gemini stdin/stdout JSON contract (`geminicli.com/docs/hooks/`) → `emit_event()` and returns Gemini-required JSON response.
- Copilot adapter: `_lib/copilot-common.{sh,ps1}` shared lib normalizes shell/PS arguments → emit_event-equivalent.

Pattern fits the spec criteria from `architecture-patterns.md`: "swapping infrastructure must not touch business logic" — adding a 5th IDE in the future requires a new adapter, no change to the unified schema. Tests can substitute fast in-memory adapters for the real bridges. The `_lib/hook-common.py` port is sealed (stdlib only, no inward dependencies on `src/ai_engineering/`) — strict dependency inversion. Layered would also work but obscures the symmetric multi-IDE intent; Hexagonal/Clean Architecture would be over-engineering for a flat module surface.

## Design

Skipped — no UI surface. Telemetry foundation is hooks + libraries + CI matrix.

---

### Phase 1 — Telemetry Bug Fix + Unified Schema (Port)

**Gate**: `telemetry-skill.py` correctly extracts skill name from prompt body via regex (no longer hardcodes `"ai-engineering"`). `_lib/hook-common.py` exposes `FrameworkEvent` TypedDict, `emit_event(event_dict) -> None`, `read_stdin_json()`, `compute_event_hash(prev_hash, current_dict) -> str`, `validate_event_schema(dict) -> bool`. Existing Python hooks (`telemetry-skill.py`, `prompt-injection-guard.py`, `instinct-observe.py`, `instinct-extract.py`, `observe.py`, `mcp-health.py`, `strategic-compact.py`, `auto-format.py`) refactored to import from `_lib/hook-common.py` and emit unified-schema events. Tests `test_telemetry_skill.py::test_skill_name_extraction`, `test_event_schema.py::test_validate_minimal_event`, `test_hook_common_lib.py` pass.

- [ ] T-1.1: Write failing test `tests/unit/hooks/test_telemetry_skill.py::test_skill_name_extraction` with 12 fixtures: 10 valid prompts (`/ai-brainstorm topic`, `/ai-plan`, `/ai-research --depth=deep query`, etc. → expected `detail.skill` value) + 2 edge cases (empty prompt, prompt without `/ai-` prefix → emit `kind: skill_invoked_malformed` with `detail.skill: null`) (agent: build)
- [ ] T-1.2: Fix `telemetry-skill.py` — replace hardcoded `detail.skill = "ai-engineering"` with regex extraction `re.match(r'^/ai-([a-zA-Z0-9_-]+)', payload.get('prompt', ''))`; emit `skill_invoked_malformed` for edge cases (agent: build, blocked by T-1.1)
- [ ] T-1.3: GREEN — verify `test_skill_name_extraction` passes all 12 fixtures (agent: build, blocked by T-1.2)
- [ ] T-1.4: Write failing tests `tests/unit/state/test_event_schema.py::test_validate_minimal_event`, `test_reject_missing_required_field`, `test_engine_value_must_be_in_enum` (agent: build)
- [ ] T-1.5: Create `src/ai_engineering/state/event_schema.py` with `FrameworkEvent` TypedDict (kind, engine, timestamp, prev_event_hash, component, outcome, correlationId, sessionId, schemaVersion, project, source, detail) + validator `validate_event_schema(dict) -> bool` that returns False on missing required field or invalid engine value; eventos malformados se loguean a stderr y NO se escriben (agent: build, blocked by T-1.4)
- [ ] T-1.6: GREEN — verify event schema tests pass (agent: build, blocked by T-1.5)
- [ ] T-1.7: Write failing tests `tests/unit/hooks/test_hook_common_lib.py` covering 6 functions: `emit_event` (writes valid line to NDJSON; rejects invalid), `read_stdin_json` (parses valid JSON; raises on malformed), `compute_event_hash` (canonical sorted-keys SHA-256), `get_correlation_id` (UUID4 generated or read from env), `get_session_id` (read or null), `validate_event_schema` (delegates to event_schema.py) — 3 cases per function (agent: build)
- [ ] T-1.8: Create `.ai-engineering/scripts/hooks/_lib/hook-common.py` (sealed: stdlib-only — `pathlib`, `json`, `hashlib`, `time`, `uuid`, `os`, `sys`, `logging`) implementing the 6 functions (agent: build, blocked by T-1.7)
- [ ] T-1.9: GREEN — verify all 18 hook-common tests pass (agent: build, blocked by T-1.8)
- [ ] T-1.10: Refactor existing Python hooks to import from `_lib/hook-common.py` instead of inline event emission; each hook reduces from ~80-150 LOC to ~30-60 LOC + import (8 hooks: `telemetry-skill.py`, `prompt-injection-guard.py`, `instinct-observe.py`, `instinct-extract.py`, `observe.py`, `mcp-health.py`, `strategic-compact.py`, `auto-format.py`) (agent: build, blocked by T-1.9)
- [ ] T-1.11: Update writers in `src/ai_engineering/state/observability.py` and `src/ai_engineering/state/service.py` to use `prev_event_hash` at root of event JSON (alignment with spec-110 D-110-03) (agent: build, blocked by T-1.10)
- [ ] T-1.12: Verify Phase 1 — run all unit hook tests; LOC reduction check (8 hooks combined ≥40% reduction); manual smoke of `/ai-brainstorm` invocation captures correct `detail.skill = "ai-brainstorm"` (agent: verify, blocked by T-1.11)

---

### Phase 2 — IDE Adapters (Codex + Gemini + Copilot)

**Gate**: `.codex/hooks.json` configured with `PreToolUse`, `UserPromptSubmit`, `Stop` events emitting via `codex-hook-bridge.py` to unified NDJSON. `.gemini/settings.json` configured with `BeforeTool`, `AfterTool`, `BeforeAgent`, `AfterAgent`, `SessionStart`, `SessionEnd` events via `gemini-hook-bridge.py` returning valid stdout JSON. `_lib/copilot-common.{sh,ps1}` extracted from 12 pairs of Copilot adapters; each `copilot-*.{sh,ps1}` reduces to ~10-25 LOC. All 4 IDEs emit events to the same `framework-events.ndjson` with `engine` field correctly identifying the source. Tests `test_codex_hooks.py`, `test_gemini_hooks.py`, `test_copilot_hooks_emit_unified.py`, `test_copilot_lib_shared.py` pass.

- [ ] T-2.1: Write failing test `tests/integration/test_codex_hooks.py::test_codex_hook_emits_unified_event` — fixture stdin JSON conforming to Codex contract (`{event: "PreToolUse", tool_name: "Bash", ...}`); validates emitted NDJSON event has `engine: "codex"` and unified schema (agent: build)
- [ ] T-2.2: Create `.ai-engineering/scripts/hooks/codex-hook-bridge.py` — reads stdin JSON, normalizes to `FrameworkEvent` schema (e.g., Codex `PreToolUse` → `kind: ide_hook`; `UserPromptSubmit` matching `/ai-` → `kind: skill_invoked`), delegates to `_lib/hook-common.emit_event()`, returns stdout per Codex contract requirement (or empty if not required) (agent: build, blocked by T-2.1)
- [ ] T-2.3: Configure `.codex/hooks.json` to register the bridge as handler for `PreToolUse`, `UserPromptSubmit`, `Stop` events (agent: build, blocked by T-2.2)
- [ ] T-2.4: GREEN — verify `test_codex_hook_emits_unified_event` passes (agent: build, blocked by T-2.3)
- [ ] T-2.5: Write failing test `tests/integration/test_gemini_hooks.py::test_gemini_hook_returns_valid_json_response` — fixture stdin JSON per Gemini contract (`{eventType: "BeforeTool", toolName: "Bash"}`); validates emitted NDJSON event has `engine: "gemini"` AND that script returns stdout JSON conforming to Gemini contract (no plain text, only JSON object) (agent: build)
- [ ] T-2.6: Create `.ai-engineering/scripts/hooks/gemini-hook-bridge.py` — reads stdin JSON, normalizes to `FrameworkEvent`, delegates to `_lib/hook-common.emit_event()`, writes stdout JSON response per Gemini contract (`{action: "continue"}` or equivalent) (agent: build, blocked by T-2.5)
- [ ] T-2.7: Configure `.gemini/settings.json` to register the bridge as handler for `BeforeTool`, `AfterTool`, `BeforeAgent`, `AfterAgent`, `SessionStart`, `SessionEnd` events (agent: build, blocked by T-2.6)
- [ ] T-2.8: GREEN — verify `test_gemini_hook_returns_valid_json_response` passes (agent: build, blocked by T-2.7)
- [ ] T-2.9: Write failing test `tests/integration/test_copilot_hooks_emit_unified.py::test_copilot_sh_and_ps1_produce_identical_events` — same input fixture into `copilot-skill.sh` and `copilot-skill.ps1`; validates both emit NDJSON events identical modulo `engine` field (both should have `engine: "copilot"`) (agent: build)
- [ ] T-2.10: Write failing test `tests/unit/hooks/test_copilot_lib_shared.py::test_loc_reduction_at_least_40_percent` (LOC count of 12 pairs before vs after refactor, target: ≥40% aggregate reduction) (agent: build)
- [ ] T-2.11: Create `.ai-engineering/scripts/hooks/_lib/copilot-common.sh` exposing functions: `emit_event()` (NDJSON append + hash chain), `read_input_json()` (stdin parse), `setup_env()` (resolve project root, NDJSON path), `compute_duration()` (timer wrap), `validate_schema()` (basic shape check). Use POSIX-ish bash subset for cross-OS bash compatibility (agent: build, blocked by T-2.10)
- [ ] T-2.12: Create `.ai-engineering/scripts/hooks/_lib/copilot-common.ps1` mirroring functions for PowerShell Core + Windows PowerShell compatibility (agent: build, blocked by T-2.11)
- [ ] T-2.13: Refactor 12 pairs of `copilot-*.{sh,ps1}` to source/import the lib and reduce to ~10-25 LOC each: `copilot-skill`, `copilot-injection-guard`, `copilot-auto-format`, `copilot-mcp-health`, `copilot-instinct-extract`, `copilot-instinct-observe`, `copilot-strategic-compact`, `copilot-session-start`, `copilot-session-end`, `copilot-deny`, `copilot-error`, `copilot-agent` (agent: build, blocked by T-2.12)
- [ ] T-2.14: GREEN — verify `test_copilot_sh_and_ps1_produce_identical_events` and LOC reduction tests pass (agent: build, blocked by T-2.13)

---

### Phase 3 — Cross-Platform CI Matrix + Hot-Path Instrumentation

**Gate**: `.github/workflows/test-hooks-matrix.yml` runs `pytest tests/integration/test_hooks_e2e.py` on `ubuntu-latest`, `macos-latest`, `windows-latest`. All 8 Python hooks use `pathlib.Path` and universal newline I/O. Each hook emits `detail.duration_ms`. SLO targets configurable in `.ai-engineering/manifest.yml`; violations emit `kind: hot_path_violation` (non-blocking, skipped in CI). `ai-eng doctor --check hot-path` reports p50/p95/p99. Tests `test_hooks_e2e.py`, `test_path_portability.py`, `test_line_endings.py`, `test_duration_ms_present.py`, `test_hot_path_slo.py`, `test_doctor_hot_path.py`, `test_slo_skip_in_ci.py`, `test_doctor_telemetry_coverage.py` pass.

- [ ] T-3.1: Write failing tests `tests/unit/hooks/test_path_portability.py::test_hooks_use_pathlib` (AST scan of 8 Python hooks; fail if `os.path.join` or string concat with separators detected) and `tests/unit/hooks/test_line_endings.py::test_ndjson_uses_lf_only` (validates NDJSON written with `\n` literal) (agent: build)
- [ ] T-3.2: Audit 8 Python hooks; replace any `os.path.join`/string-concat with `pathlib.Path`; ensure `open(..., newline='')` for stdin reads and explicit `\n` for NDJSON writes (agent: build, blocked by T-3.1)
- [ ] T-3.3: GREEN — verify portability tests pass (agent: build, blocked by T-3.2)
- [ ] T-3.4: Create `.github/workflows/test-hooks-matrix.yml` — matrix `os: [ubuntu-latest, macos-latest, windows-latest]`, runs `pytest tests/integration/test_hooks_e2e.py`; uses SHA-pinned actions per spec-110 G-3 (agent: build, blocked by T-3.3)
- [ ] T-3.5: Write `tests/integration/test_hooks_e2e.py` — for each hook: spawn it with stdin JSON fixture, capture stdout/stderr, validate NDJSON output written to a temp file matches expected structure; for shell/PS pairs: validate paridad output (agent: build, blocked by T-3.4)
- [ ] T-3.6: Trigger CI matrix run (commit + push); verify all 3 matrix cells pass (agent: verify, blocked by T-3.5)
- [ ] T-3.7: Write failing tests `tests/integration/test_duration_ms_present.py::test_all_hooks_emit_duration` (executes each of 8 Python hooks + 24 Copilot scripts + 2 bridges; validates `detail.duration_ms` present and >0) (agent: build)
- [ ] T-3.8: Add timer wrap to `_lib/hook-common.py emit_event` — capture start time at module-level, compute duration on emit; bridges and Copilot lib emit `detail.duration_ms` similarly (agent: build, blocked by T-3.7)
- [ ] T-3.9: GREEN — verify `test_all_hooks_emit_duration` passes (agent: build, blocked by T-3.8)
- [ ] T-3.10: Write failing tests `tests/integration/test_hot_path_slo.py::test_emits_violation_when_exceeds_target` (fixture hook with sleep 1500ms; validates `kind: hot_path_violation` emitted with detail `{hook_name, duration_ms: 1500, slo_target_ms: 1000, slo_dimension: "pre_tool_use"}`) and `tests/unit/hooks/test_slo_skip_in_ci.py::test_no_violation_when_CI_env_true` (agent: build)
- [ ] T-3.11: Add `[telemetry.slo]` section to `.ai-engineering/manifest.yml` with defaults: `pre_tool_use_p95_ms = 1000`, `pre_commit_gate_p95_ms = 1000`, `skill_invocation_overhead_p95_ms = 200`, `enabled = true` (agent: build, blocked by T-3.10)
- [ ] T-3.12: Implement violation detection in `_lib/hook-common.py emit_event` — read SLO from manifest, compare duration_ms; if exceeds AND `os.environ.get("CI") != "true"`, emit additional `hot_path_violation` event (non-blocking, hook completes normally) (agent: build, blocked by T-3.11)
- [ ] T-3.13: GREEN — verify SLO and CI-skip tests pass (agent: build, blocked by T-3.12)
- [ ] T-3.14: Write failing tests `tests/integration/test_doctor_hot_path.py::test_reports_p95_violations` and `tests/integration/test_doctor_telemetry_coverage.py::test_reports_per_engine_breakdown` (agent: build)
- [ ] T-3.15: Add `ai-eng doctor --check hot-path` and `--check telemetry-coverage` subcommands in `src/ai_engineering/doctor/phases/` (or appropriate location); compute p50/p95/p99 from NDJSON stream, group by hook, compare to SLO; for telemetry-coverage, group by engine and report counts + missing emitters (agent: build, blocked by T-3.14)
- [ ] T-3.16: GREEN — verify both doctor tests pass (agent: build, blocked by T-3.15)

---

### Phase 4 — NDJSON Reset + Clean Code Audit + Final Gates

**Gate**: spec-110 confirmed merged before T-4.4 executes (R-7 mitigation). `ai-eng state reset-events --confirm` archives legacy NDJSON to `.legacy-<YYYY-MM-DD>.gz` and creates new NDJSON with `kind: state_reset` marker event. `docs/telemetry-reset-2026-04.md` documents the reset. Functions >30 LOC in modified files are refactored. Naming conventions enforced. Obvious comments removed. 0 secrets, 0 vulns, 0 lint errors. Coverage ≥80% on new modules. Pre-dispatch governance check confirms no NG-1..NG-11 violations.

- [ ] T-4.1: Write failing tests `tests/integration/test_state_reset.py::test_reset_archives_and_creates_empty_with_marker_event` (executes `ai-eng state reset-events --confirm` in isolated temp; validates `.legacy-<date>.gz` exists, new NDJSON has 1 line of `kind: state_reset` event) and `test_reset_refuses_without_confirm` (without `--confirm`, command exits non-zero with message) (agent: build)
- [ ] T-4.2: Implement `ai-eng state reset-events --confirm` command in `src/ai_engineering/cli_commands/state.py` (or new file): preflight checks (T1+T2+T3 tests passing — assert via subprocess `pytest -k 'telemetry_skill or event_schema or hook_common'`); gzip archive; create new file with state_reset marker event (agent: build, blocked by T-4.1)
- [ ] T-4.3: Add gate in `state reset-events`: read CHANGELOG.md / git log to confirm spec-110 merged before allowing reset; fail explicitly with message "spec-110 must be merged first (R-7 mitigation)" if unmerged (agent: build, blocked by T-4.2)
- [ ] T-4.4: GREEN — verify reset tests pass (agent: build, blocked by T-4.3)
- [ ] T-4.5: Write `docs/telemetry-reset-2026-04.md` — sections: (a) Why we reset (the 5 fallos), (b) How to query legacy archive (`gunzip -c .legacy-...gz | python3 -c '...'` example), (c) Baseline expectations post-reset (24h volume, distribution by `engine`) (agent: build, blocked by T-4.4)
- [ ] T-4.6: Write failing test `tests/integration/test_audit_chain_post_reset.py::test_no_legacy_detail_hash_in_new_events` (validates that all events written post-reset use `prev_event_hash` at root, none in `detail`) (agent: build)
- [ ] T-4.7: Verify dual-read fallback removal — when reset is invoked, the legacy `detail.prev_event_hash` fallback in `audit_chain.read_event` is no longer triggered for new events (agent: build, blocked by T-4.6)
- [ ] T-4.8: GREEN — verify `test_no_legacy_detail_hash_in_new_events` passes (agent: build, blocked by T-4.7)
- [ ] T-4.9: Audit functions >30 LOC in files modified by Phases 1-3 (`_lib/hook-common.py`, `_lib/copilot-common.{sh,ps1}`, 8 Python hooks, bridges, audit_chain extensions, observability/service updates, doctor checks, cli_commands/state.py). Refactor each oversized function into sub-functions with single responsibility. Verify with `ruff check --select PLR0915` — 0 violations on modified files (agent: verify, blocked by T-4.8)
- [ ] T-4.10: Audit naming conventions in modified files — snake_case for Python functions, no `_temp`/`_old`/`_new`/`_TODO` legacy markers. Verify with `ruff check --select N802,N803,N806` — 0 violations on modified files (agent: verify, blocked by T-4.9)
- [ ] T-4.11: Manual review of comments in modified files — remove obvious comments (e.g., `# increment counter` before `counter += 1`); preserve docstrings; convert TODO comments with TTL >30 days to GitHub issues or remove (agent: verify, blocked by T-4.10)
- [ ] T-4.12: Run `gitleaks protect --staged --no-banner` on all changed files — 0 findings (agent: verify, blocked by T-4.11)
- [ ] T-4.13: Run `pip-audit` — 0 high/critical vulns (agent: verify, blocked by T-4.12)
- [ ] T-4.14: Run `ruff format` + `ruff check` on all changed files — 0 errors (agent: verify, blocked by T-4.13)
- [ ] T-4.15: Run `pytest --cov=src/ai_engineering/state.event_schema --cov=.ai-engineering.scripts.hooks._lib.hook-common --cov=src/ai_engineering/cli_commands.state` (or paths as adjusted) — verify ≥80% coverage on new/modified code (agent: verify, blocked by T-4.14)
- [ ] T-4.16: Pre-dispatch governance check #1 — confirm no skill/agent deletion (NG-1, NG-3), no `/skill-sharpen` invocation (NG-2 — defer to spec-113), no Clean Architecture restructure (NG-4), no Hexagonal beyond ports-and-adapters for telemetry (NG-5 — note: ports-and-adapters here is for telemetry pipeline, not architectural rewrite), no OTel exporter (NG-6), no new skills except fix of `telemetry-skill.py` (NG-7), no migration to SQLite (NG-8), no real-time dashboard (NG-9), no skill content modifications (NG-11) (agent: guard, blocked by T-4.15)
- [ ] T-4.17: Pre-dispatch governance check #2 — verify spec-110 dependency (D-110-03 hash-chain root migration) is consolidated post-reset; spec-111 dependency (Tier 0 local depends on clean NDJSON) is now ready for spec-111 implementation (agent: guard, blocked by T-4.16)

---

## Risk Mitigation Notes

- **R-1 Codex/Gemini contract changes**: T-2.2 + T-2.6 implement bridges with explicit version expectation in docstring; T-3.5 e2e tests use fixtures derived from docs URL; if contract breaks in CI, test fails loudly.
- **R-2 Reset loses historical context**: T-4.2 archives gzipped legacy; T-4.5 documents how to query archive offline.
- **R-3 DRY pass breaks live hooks**: per-archivo commits with tests verde; optional `AI_ENG_USE_LEGACY_HOOKS=true` env var preserves old behavior for 30 days post-merge (preserved in `.legacy/` if implementer chooses to add).
- **R-4 SLO false positives on slow hardware**: T-3.11 makes SLO configurable in manifest.yml; user can relax targets locally.
- **R-5 Clean code audit touches merged code from other specs**: T-4.9 + T-4.10 strict scope to files modified by T1-T6 only.
- **R-6 Codex/Gemini auth/permission gaps**: T-3.15 implements `ai-eng doctor --check telemetry-coverage` to surface gaps; documentation in T-4.5 includes setup steps.
- **R-7 Schema migration race condition with spec-110**: T-4.3 explicit gate in reset command — refuses to run if spec-110 unmerged.
- **R-8 cross-OS bash/PS compatibility**: T-2.11 uses POSIX-ish bash subset; T-2.12 PS Core + Windows PS compatible; T-3.6 CI matrix catches divergence.
- **R-9 Circular imports in `_lib/hook-common.py`**: T-1.8 explicitly seals lib (stdlib-only, no `src/ai_engineering/` imports).

## Self-Review Notes

Reviewed once. No additional iteration needed:
- Each task is bite-sized and single-concern.
- TDD pairing applied throughout: tests written BEFORE implementation per phase.
- Phase gates clearly verifiable.
- Dependencies explicit and acyclic.
- Architecture pattern (Ports and Adapters) genuinely fits the multi-IDE telemetry challenge — not over-engineered.
- Sequential ordering of T1 (fix bug) → T3 (multi-IDE) → T4 (reset) is critical and explicit.
- Spec-110 dependency (R-7) gated in T-4.3.
- Spec-111 dependency note (Tier 0 needs clean NDJSON) verified in T-4.17.
- spec-113 (skill-sharpen ×49) deferred per D-112-06 — not in this plan; LESSONS.md note added in T-4.5 documentation.
- Strict scope adherence — clean code audit (T7) limited to files modified by T1-T6 (NG list verified in T-4.16/17).
