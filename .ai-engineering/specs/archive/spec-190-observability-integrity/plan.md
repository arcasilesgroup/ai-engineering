---
spec: spec-190
title: Plan — Observability Integrity (attributable, deduplicated, fail-loud telemetry)
status: approved
execution_route:
  version: 1
  spec: spec-190
  executor: autopilot
  automation: full
  concern_count: 6
  estimated_files: 32
  reason: >-
    Six independent concerns (attribution, dedup+storm, tool-failure capture,
    honest spec-verify outcome, smoke harness, twin/manifest guard) across the
    telemetry layer. Each behavioral change touches a THREE-copy dual-writer
    (pip state/, hook _lib canonical, hook _lib template twin) with no CI parity
    guard, plus a Pydantic silent-drop trap and a byte-twin + hooks-manifest
    regen per hook edit. ≥3 concerns and >10 files → autopilot decomposes into
    sub-specs and waves; single build would serialize six loosely-coupled tracks.
  safe_next_command: "/ai-autopilot"
---

# Plan — Observability Integrity (spec-190)

## Summary

Fix the telemetry layer so the framework can see and attribute its own failures.
Six concerns, each mapped to a spec-190 decision. Grouped for parallel waves; the
tool-failure and spec-verify concerns are independent and can land first.

## Architecture (ad-hoc — extends existing layered + append-only NDJSON telemetry)

**Critical shared context — every task must respect this map.** There is no new
pattern; the risk is the multi-copy write surface.

Three parallel copies of the observability/instincts logic exist, with NO CI guard
coupling pip ↔ hook:

| Copy | Path | Twin rule | Manifest |
|------|------|-----------|----------|
| pip package | `src/ai_engineering/state/{observability,instincts}.py`, `tools/skill_domain/state_models.py`, `cli_commands/{spec_cmd,core}.py` | functional-parallel with hook `_lib` (edit both; NOT a byte copy) | none |
| hook canonical | `.ai-engineering/scripts/hooks/_lib/{observability,instincts,hook-common}.py`, `runtime-session-start.py` | byte-identical to template twin (`cp`) | sha-pinned |
| hook template | `src/ai_engineering/templates/.ai-engineering/scripts/hooks/**` | byte-identical to canonical | (installer copy) |

Hard rules (D-190-06), enforced as a gate on every hook-touching task:
1. Edit hook canonical → `cp` byte-identical to template twin.
2. Any hook byte change → `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py` (else enforce-mode self-disables the hook).
3. A pip-side edit with no matching hook `_lib` edit (or vice-versa) passes ALL current parity tests but silently diverges hot-path vs pip behavior — Phase 0 adds the missing byte-parity guard to catch template drift; pip↔hook stays a manual discipline (call it out in each task's Gate).
4. Hooks stay stdlib-only (no `ai_engineering` import on the hot path); pre-commit <1s; runtime writes use the tolerant `read_json` + atomic `_atomic_write` pattern under `contextlib.suppress` — never raise.
5. Introspection/tests use `.venv/bin/python` (bare `python3` cannot import `ai_engineering` and hits the py3.9 `datetime.UTC` trap).

## Phase 0 — Parity safety net (lands first; protects every twin edit)

- [ ] T-1 — Extend hook byte-parity guard from auto-format-only to the whole hooks subtree
  - Agent: build
  - Files: `tests/unit/test_hook_template_parity.py::test_live_hook_and_template_are_byte_equivalent` L37-53 (generalize); companion `tests/unit/test_template_parity.py::TestHookScriptParity` L34-55 (name/count only today)
  - Principles applied: §10.5 TDD (guard-first), §10.4 DRY (one parity source of truth)
  - Patch (deterministic): none — replace the single-file assertion with a walk over `.ai-engineering/scripts/hooks/**` (INCLUDE_SUFFIXES `.py/.sh/.ps1`, exclude `_lib/__init__.py`) asserting each canonical file is byte-identical to its `templates/.ai-engineering/scripts/hooks/**` twin.
  - Gate: `.venv/bin/python -m pytest tests/unit/test_hook_template_parity.py tests/unit/test_template_parity.py` → PASS (green now; fails if any later task forgets a twin `cp`)

## Phase 1 — D-190-01 Attribution: `frameworkVersion` + durable `sessionId`

- [ ] T-2 — RED: envelope must carry `frameworkVersion` (pip + hook-lib)
  - Agent: build
  - Files: `tests/unit/test_framework_observability.py`, `tests/unit/test_lib_observability.py`, `tests/unit/hooks/test_lib_observability_genai.py`
  - Principles applied: §10.5 TDD (RED before GREEN)
  - Patch (deterministic): none — assert `build_framework_event(...)` output includes a non-empty `frameworkVersion`.
  - Gate: `.venv/bin/python -m pytest tests/unit/test_framework_observability.py tests/unit/test_lib_observability.py` → FAIL

- [ ] T-3 — GREEN: add `framework_version` field to the `FrameworkEvent` model (silent-drop trap)
  - Agent: build
  - Files: `tools/skill_domain/state_models.py` :339-368 (`class FrameworkEvent`, `model_config` at :368 is `populate_by_name` only → pydantic default `extra="ignore"` DROPS unknown keys)
  - Principles applied: §10.7 Clean Code (make the schema explicit), §10.3 SOLID
  - Patch (deterministic):
    ```diff
    +    framework_version: str | None = Field(default=None, alias="frameworkVersion")
    ```
    (add beside the existing aliased fields, e.g. after `schema_version`/near :365; re-exported via `ai_engineering.state.models`)
  - Gate: `.venv/bin/python -c "from ai_engineering.state.models import FrameworkEvent; print(FrameworkEvent.model_validate({'frameworkVersion':'9.9.9'}).model_dump(by_alias=True).get('frameworkVersion'))"` → prints `9.9.9`

- [ ] T-4 — GREEN: stamp `frameworkVersion` in the pip envelope builder
  - Agent: build
  - Files: `src/ai_engineering/state/observability.py` :296-406 (`event_data` dict 389-405; returns `FrameworkEvent.model_validate` at :406); `src/ai_engineering/__init__.py` :11 (`__version__`)
  - Principles applied: §10.4 DRY (single version source), §10.5 TDD
  - Patch (deterministic): `from ai_engineering import __version__` at module top; add `"frameworkVersion": __version__,` to `event_data`.
  - Gate: T-2 pip assertions → PASS

- [ ] T-5 — GREEN: stamp `frameworkVersion` in the hook-lib envelope builder (+ twin + manifest)
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/_lib/observability.py` :304-418 (`entry` dict 394-404, plain dict — no pydantic gate) → `cp` to `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/observability.py`
  - Principles applied: §10.4 DRY, §10.8 stdlib-only hot path
  - Patch (deterministic): `entry["frameworkVersion"] = _read_framework_version()` (see T-6 reader; stdlib, no pip import).
  - Gate: `cp` twin byte-identical → `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py` → `.venv/bin/python -m pytest tests/unit/hooks/test_lib_observability_genai.py tests/unit/test_hook_template_parity.py` → PASS

- [ ] T-6 — GREEN: pinned `VERSION` written in the install/update funnel + stdlib reader
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/core.py` `_finalize_hooks_manifest` :723-776 (single funnel hit by install :238/:795 and update via `_finalize_update_hooks_manifest` :795; `__version__` imported :21); new reader helper in `.ai-engineering/scripts/hooks/_lib/observability.py` (+twin)
  - Principles applied: §10.2 YAGNI (reuse the finalize funnel — no new install step), §10.8 no pip import on hot path
  - Patch (deterministic): at top of `_finalize_hooks_manifest`, write `root/.ai-engineering/state/runtime/VERSION` (gitignored, regenerated each install/update — NOT a committed file) with `__version__`. Reader `_read_framework_version()` reads that file, fallback `"0.0.0"`, wrapped in `contextlib.suppress`.
  - Gate: `.venv/bin/python -m pytest tests/unit/ -k "finalize_hooks_manifest or version"` → PASS; manual: install writes `state/runtime/VERSION`
  - Note: `state/runtime/` is the REAL runtime dir (the `runtime-session-start.py` docstring's `.ai-engineering/runtime/` is wrong — trace_context uses `state/runtime/`). VERSION is not under `scripts/` so it is NOT manifest-hashed.

- [ ] T-7 — RED: `sessionId` resolves from a persisted pointer when env is unset
  - Agent: build
  - Files: `tests/unit/hooks/test_runtime_session_start.py`, `tests/unit/hooks/test_hook_common_lib.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — assert SessionStart writes a session pointer under `state/runtime/`, and `get_session_id()` returns it when `CLAUDE_SESSION_ID`/`ANTIGRAVITY_SESSION_ID` are absent.
  - Gate: `.venv/bin/python -m pytest tests/unit/hooks/test_runtime_session_start.py tests/unit/hooks/test_hook_common_lib.py` → FAIL

- [ ] T-8 — GREEN: persist session pointer + `get_session_id` fallback (+ twins + manifest)
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/runtime-session-start.py` (clone `_safe_init_trace_context` :83-99 pattern; `ctx.session_id` at :109; call near :112-113) and `.ai-engineering/scripts/hooks/_lib/hook-common.py` `get_session_id` :169-171 — add pointer read after the env lookups; both `cp` to template twins
  - Principles applied: §10.3 SOLID (single resolver), §10.8 stdlib-only, §10.5 TDD
  - Patch (deterministic): none — judgment (mirror `write_trace_context`/`trace_context_path` from `_lib/trace_context.py` :37,:209-215; write `state/runtime/session-pointer.json`; suppress errors).
  - Gate: `cp` both twins → `regenerate-hooks-manifest.py` → T-7 tests PASS → `tests/unit/test_hook_template_parity.py` PASS

## Phase 2 — D-190-03 Tool-failure capture (independent; can land first)

- [ ] T-9 — RED: `tool_response` failure is derived as failure (string + dict shapes)
  - Agent: build
  - Files: `tests/unit/test_lib_instincts.py::TestDeriveOutcome` L149-169; `tests/unit/test_instinct_state.py::test_append_instinct_observation`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — add cases: `data={"tool_name":"Bash","tool_response":{"is_error":True,"stderr":"boom"}}` → `failure`; `data={"tool_name":"Read","tool_response":"... error ..."}` → `failure`; assert `output_summary` includes `tool_response` text.
  - Gate: `.venv/bin/python -m pytest tests/unit/test_lib_instincts.py tests/unit/test_instinct_state.py` → FAIL

- [ ] T-10 — GREEN: read `tool_response` in `_derive_outcome` + `_build_observation_detail` (THREE copies)
  - Agent: build
  - Files: `src/ai_engineering/state/instincts.py` `_derive_outcome` :327-334 / `_build_observation_detail` :337-354 / `_ERROR_HINTS` :29; `.ai-engineering/scripts/hooks/_lib/instincts.py` :500-513/:515-532/`_ERROR_HINTS` :49 → `cp` template twin. `instinct-observe.py` already forwards `tool_response` (no change).
  - Principles applied: §10.4 DRY (identical logic in all three), §10.7 Clean Code
  - Patch (deterministic): none — contract: truthy `tool_response.get("is_error")` → failure; coerce dict via `_coerce_mapping`/`_coerce_text` and scan `_ERROR_HINTS`; the new `tool_response` branch MUST run BEFORE the `return "success" if data.get("tool_name")` fallback. Fail-open to `success` on unknown shape.
  - Gate: edit all three copies identically → `cp` twin → `regenerate-hooks-manifest.py` → T-9 tests PASS + `tests/unit/test_hook_template_parity.py` PASS

## Phase 3 — D-190-04 Honest `spec verify` outcome

- [ ] T-11 — RED: `spec verify` emits `outcome=failure` on uncorrected drift; keep emit under the `if`
  - Agent: build
  - Files: `tests/unit/test_spec_cmd.py` (signal-emission suite ~L80-250, drift assertion L227); `tests/unit/state/test_event_relevance_no_heartbeats.py` :67-72 (AST guard requires `spec_verified` emit stay inside an `if` branch — update in lockstep, do NOT unconditionalize)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — assert the emitted event's `outcome == "failure"` when drift is present and not auto-fixed, `"success"` when corrected.
  - Gate: `.venv/bin/python -m pytest tests/unit/test_spec_cmd.py tests/unit/state/test_event_relevance_no_heartbeats.py` → FAIL

- [ ] T-12 — GREEN: thread `outcome` through `_emit_signal` to the existing kwarg
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/spec_cmd.py` `_emit_signal` :52-61 (no `outcome` param today) + verify site :279-288 (`if drift_detected:` guard; `drift_detected` computed :254). `emit_framework_operation` already accepts `outcome="success"` (`observability.py` :892) — no change there.
  - Principles applied: §10.3 SOLID (thread state, don't hardcode), §10.5 TDD
  - Patch (deterministic):
    ```diff
    -def _emit_signal(root, event, detail):
    +def _emit_signal(root, event, detail, outcome="success"):
         ...
    -        emit_framework_operation(root, operation=event, component="cli.spec", source="cli", metadata=detail)
    +        emit_framework_operation(root, operation=event, component="cli.spec", source="cli", outcome=outcome, metadata=detail)
    ```
    At the verify site, pass `outcome="failure" if (drift_detected and not corrected) else "success"` (keep the call inside the `if drift_detected` block — AST guard preserved).
  - Gate: T-11 tests PASS

## Phase 4 — D-190-02 Dedup + storm alarm (largest; judgment-heavy)

- [ ] T-13 — RED: repeated identical errors coalesce + a storm control-outcome fires
  - Agent: build
  - Files: `tests/unit/state/test_observability_genai.py`, `tests/unit/test_framework_observability.py` (pip); `tests/unit/hooks/test_lib_observability_genai.py`, `tests/unit/test_lib_observability.py` (hook-lib); `tests/unit/hooks/test_runtime_session_start.py` (banner)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — assert: N identical `emit_framework_error` calls → 1 full event + a rollup carrying `detail.occurrences`; crossing threshold emits a `control_outcome` with `control="framework_error_storm"`; audit hash-chain stays continuous (no dropped `append`).
  - Gate: `.venv/bin/python -m pytest tests/unit/state/test_observability_genai.py tests/unit/test_lib_observability.py` → FAIL

- [ ] T-14 — GREEN: storm-state sidecar helper (atomic, gitignored)
  - Agent: build
  - Files: new leaf in `.ai-engineering/scripts/hooks/_lib/runtime_state.py` (reuse `runtime_dir` :146-217 + atomic pattern) OR mirror `_lib/risk_accumulator.py::_atomic_write` :328-343; `cp` template twin. Sidecar under `.ai-engineering/runtime/` (already gitignored, `.gitignore` :188).
  - Principles applied: §10.4 DRY (reuse `_atomic_write`), §10.8 stdlib-only, fail-open
  - Patch (deterministic): none — fingerprint = `hash(component, error_code, session_id, bounded_summary)`; record `first_seen/last_seen/count`; window from `AIENG_HOOK_CACHE_TTL_SEC` (`_env_int` :76-88).
  - Gate: `cp` twin → `regenerate-hooks-manifest.py` → unit test for the helper PASS

- [ ] T-15 — GREEN: coalesce in `emit_framework_error` + emit `framework_error_storm` (pip + hook-lib)
  - Agent: build
  - Files: `src/ai_engineering/state/observability.py` `emit_framework_error` :734-767 / `emit_control_outcome` shape :807-836 (pip); `.ai-engineering/scripts/hooks/_lib/observability.py` `emit_framework_error` :684-717 / `emit_control_outcome` :719 → `cp` twin
  - Principles applied: §10.4 DRY (both writers identical behavior), §13.7 SSOT (rollup keeps audit chain intact)
  - Patch (deterministic): none — on emit, bump the T-14 sidecar; emit full event on first-in-window, else a suppressed-count rollup (`detail.occurrences=N`); raise ONE `framework_error_storm` `control_outcome` past threshold. Never skip `append` entirely (chain continuity). Both copies edited identically.
  - Gate: edit pip + hook-lib → `cp` twin → `regenerate-hooks-manifest.py` → T-13 emit tests PASS + parity PASS

- [ ] T-16 — GREEN: surface active storms at SessionStart (no `doctor` needed)
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/runtime-session-start.py` additionalContext surface :102-145 (write at :142-143 under `contextlib.suppress`) → `cp` twin
  - Principles applied: §10.7 Clean Code (bounded one-line banner), fail-open
  - Patch (deterministic): none — read the storm sidecar; if an active storm exists in the last window, print one plain-text warning line; suppressed when clean.
  - Gate: `cp` twin → `regenerate-hooks-manifest.py` → T-13 banner test PASS

- [ ] T-17 — GREEN: document the storm TTL/threshold tunables
  - Agent: build
  - Files: `src/ai_engineering/templates/project/CLAUDE.md` Runtime Tunables (near :212) + canonical sync source; run `ai-eng dev sync` (or `scripts/sync_mirrors`) to propagate mirrors
  - Principles applied: §10.4 DRY (one tunables table), §10.6 SDD
  - Patch (deterministic): none — add `AIENG_ERROR_STORM_THRESHOLD` (default proposal ≥20/hr) + reuse `AIENG_HOOK_CACHE_TTL_SEC` for the window; note new env in the tunables list.
  - Gate: `.venv/bin/python -m pytest tests/unit/docs -k "tunable or claude_md"` and mirror-parity tests → PASS

## Phase 5 — D-190-05 Hook smoke completeness harness

- [ ] T-18 — GREEN: settings.json-driven per-event smoke test (covers every wired hook)
  - Agent: build
  - Files: `tests/integration/test_framework_hook_emitters.py` `_prepare_project` :52-108 (switch the hardcoded ~9-script tuple to `shutil.copytree` of the whole `hooks/` tree) + new parametrized class cloning the subprocess pattern at :135-162; enumerate from `.claude/settings.json` :45-283 (`json load → hooks.items() → matcher["hooks"] → h["command"]`, take the LAST `CLAUDE_PROJECT_DIR/...` match = the `.py`, not the `run-hook.sh` wrapper)
  - Principles applied: §10.5 TDD (structural completeness), §10.1 KISS (drive from wiring, not a hand-list)
  - Patch (deterministic): none — for each event, `subprocess.run([sys.executable, script], input=json.dumps(synthetic_envelope), check=False)`, assert `returncode == 0` and no traceback on stderr. Invoke the `.py` directly (NOT through `run-hook.sh`) to avoid manifest-integrity exits. Tolerate fail-open passthrough (e.g. `memory-session-start.py` 4s subprocess).
  - Gate: `.venv/bin/python -m pytest tests/integration/test_framework_hook_emitters.py` → PASS (now exercises `memory-session-start.py` + all `runtime-*`/`memory-*` hooks)

## Phase 6 — Integration, gates, delivery

- [ ] T-19 — Final manifest regen + staleness check
  - Agent: build
  - Files: `.ai-engineering/state/hooks-manifest.json` (regenerated), all edited hook twins
  - Principles applied: §13 Hard Rules (hook integrity)
  - Gate: `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py --check` → clean; `tests/unit/hooks/test_regen_manifest_portable.py` PASS

- [ ] T-20 — Full verification pass
  - Agent: verify
  - Files: whole changeset
  - Principles applied: §10.5 TDD, §13 (gates)
  - Gate: `.venv/bin/python -m pytest tests/unit tests/integration` green; `PYTHONPATH=tools .venv/bin/python -m spec_lint --check .ai-engineering/specs/spec.md` clean; `ai-eng doctor` no new FAIL; gitleaks/ruff/pip-audit clean; no `# noqa`/suppressions introduced (§13.2)

- [ ] T-21 — Twin/dual-writer final audit
  - Agent: verify
  - Files: pip `state/{observability,instincts}.py` vs hook `_lib/{observability,instincts}.py`
  - Principles applied: §13.7 SSOT, §10.4 DRY
  - Gate: manual diff confirms pip ↔ hook-lib behavioral parity for `emit_framework_error` dedup and `_derive_outcome` `tool_response` handling (no CI guard couples them — this is the one gap the automated parity test cannot cover); `tests/unit/test_hook_template_parity.py` (canonical↔template) PASS

## Risks & rollback

- **Dual-writer divergence** (pip vs hook-lib) — the only parity the automated guard can't
  enforce. Mitigated by T-21 manual audit + identical-edit discipline in T-10/T-15.
- **Manifest staleness self-disables hooks** if a twin `cp` or regen is skipped. Mitigated by
  T-1 byte-parity guard (green-now) + T-19 `--check` + per-task regen gates.
- **Hot-path budget**: storm sidecar I/O on the error path. Mitigated by atomic `_atomic_write`
  + `contextlib.suppress` + fail-open to raw emit; never block.
- **Rollback**: each concern is an independent sub-spec/wave; revert a concern's commits without
  touching the others. Envelope fields are additive — old readers ignore them.
