---
spec: spec-190
title: "Observability Integrity: attributable, deduplicated, fail-loud framework telemetry"
status: approved
effort: large
summary: "Make framework telemetry trustworthy and attributable: stamp sessionId + framework_version on every event, dedup error storms via a runtime sidecar, capture real tool failures, report spec-verify pass/fail honestly, and smoke-run every wired hook in CI."
---

# Observability Integrity

## Summary

The framework's own telemetry cannot currently see or attribute its own failures. A
fleet analysis of 234k framework events across 18 repos (claude.ai artifact 216ac1f9)
was crippled by five gaps in the measurement layer, each ground-truthed against current
`main` on 2026-07-19: (1) events carry no `framework_version` and only ~1.3% of hot-path
`ide_hook` events carry a `sessionId`, so 53% of errors cannot be tied to any session and
version forensics requires cross-referencing git tags to manifests; (2) error/integrity
events emit once per hook invocation with no coalescing, so ~10 real incidents produced
18,400 events and one hook crash ran 6 days unnoticed; (3) 100% of 25,900 `tool_complete`
observations record `success` because the outcome deriver never reads the host result
envelope, making real tool failures invisible; (4) `ai-eng spec verify` records
`outcome=success` even when drift is detected and nothing was remediated (1,611/1,611
drift verifications logged as success — a rubber stamp); (5) no test enumerates the hooks
wired in `settings.json` and executes each, so a crashing hook can ship undetected. This
spec fixes the measurement layer so everything measured on top of it becomes trustworthy.

## Goals

- Every framework event envelope carries `frameworkVersion`, sourced without importing the
  pip package on the stdlib hook path.
- Hot-path `ide_hook` events carry `sessionId` at ≥95% coverage (verifiable by sampling the
  NDJSON), via a SessionStart-persisted session pointer rather than an env var.
- Repeated identical error/integrity events coalesce to one full event plus a bounded rollup
  carrying an occurrence count, keyed by a `(component, error_code, session, summary)`
  fingerprint held in a gitignored runtime sidecar.
- A `framework_error_storm` control-outcome is emitted and surfaced at SessionStart when one
  fingerprint recurs past a per-window threshold — visible without running `doctor`.
- `tool_complete` observations reflect real failure: `error_flag`/`outcome` are derived from
  `tool_response.is_error` and error-hint text, verifiable by a failing-tool fixture.
- `ai-eng spec verify` reports `outcome=failure` when drift is detected and left uncorrected,
  and `success` only when clean or remediated.
- A CI smoke test derives the hook list from `.claude/settings.json` and subprocess-executes
  each wired hook against a synthetic per-event payload, asserting no crash — covering every
  registered hook including `memory-session-start.py`.
- All changes hold the framework's own invariants: byte-twin parity, regenerated
  hooks-manifest, additive-only envelope fields, stdlib-only hot path, pre-commit <1s.

## Non-Goals

- Reopening the six telemetry findings already fixed in current `main`: `agent_kind` crash
  (spec-131 sub-004), hooks-manifest re-pin on update/install (spec-142/159/179),
  verify-after-build gating (§13.5 / D-167), `no_ai_prefix` routing (ships as
  runtime-progressive-disclosure, spec-116), runtime-stop end-of-turn latency (spec-139 M6),
  auto-format over-budget (spec-139 M5.T4).
- Read-side injection scanning of `tool_response` for Read/WebFetch/WebSearch/MCP — deferred
  to a separate guard-coverage spec (B2).
- Replacing the cumulative session risk accumulator with decay/per-command scoring, wiring
  the dead `allowlist.domains`, or tightening the TLD member-access residual — B2.
- Running `ruff --fix` before consuming a ralph retry — deferred to a loop-efficiency spec (B3).
- Removing the intentional dual-phase `instinct-observe` PreToolUse registration — its
  write-amplification is already batched (spec-139 M5.T2); spawn-cost review is out of scope.
- Consolidating the low-usage skill long-tail — a product-strategy decision already underway
  in spec-187/189.
- Changing the `spec verify` `drift_detected` formula — it is already correct; the deck's
  "completed==total still flags drift" counter-claim did not reproduce.
- Cross-session or cross-repo error aggregation, and any external/real-time alerting
  infrastructure — dedup and storm detection are per-session, files-only.

## Decisions

### D-190-01 — Attribution: stamp `sessionId` + `frameworkVersion` on every envelope

Add `frameworkVersion` to all three envelope builders (`state/observability.py`, the
`_lib/observability.py` twin, and the inline dicts in `hook-common.py`). Source it from
`ai_engineering.__version__` on the package path and from a pinned `VERSION` file — written
by the install/update finalize path — on the stdlib hook path. Resolve `sessionId` from a
session pointer the SessionStart hook persists under `.ai-engineering/runtime/`, falling back
from the (usually unset) `CLAUDE_SESSION_ID` env var.

**Rationale**: Attribution is the base of every downstream analysis; today 53% of errors are
session-orphaned and exposure-by-version needs git forensics. The env-var path is exactly why
`sessionId` coverage is ~1.3% — a persisted pointer removes that dependency. A pinned `VERSION`
file avoids importing the pip package on the hot path (the stdlib-only contract) and survives
editable installs because the same finalize path that re-pins hooks-manifest writes it.

### D-190-02 — Dedup + storm alarm via a gitignored runtime sidecar

Coalesce error/integrity emission in `emit_framework_error` (both twins). Compute a
fingerprint = hash(component, error_code, session_id, bounded_summary); keep a gitignored
sidecar under `.ai-engineering/runtime/` recording first_seen/last_seen/count per fingerprint.
Emit the full event on first occurrence and a bounded rollup (`detail.occurrences=N`) per
window (reuse `AIENG_HOOK_CACHE_TTL_SEC`); suppress the intermediate duplicates. Raise one
`framework_error_storm` control-outcome when a fingerprint crosses a per-hour threshold, and
surface active storms at SessionStart.

**Rationale**: The fresh-process-per-hook model means an in-process buffer collapses almost
nothing across separate tool calls — only a persisted sidecar makes dedup real (operator
decision). The deck's core failure was that nobody ran `doctor`, so the alarm must fire on a
surface the operator already sees (SessionStart), not a report they must pull. `occurrences`
is an additive `detail` field — no schema break.

### D-190-03 — Capture real tool failures from `tool_response`

Teach `_derive_outcome` (instincts.py) to read the Claude Code result envelope: treat a truthy
`tool_response.is_error` as failure and include the coerced `tool_response` text in the
`_ERROR_HINTS` scan, mirroring the same source into `_build_observation_detail`'s tool-output
chain. Fail-open to `success` when the shape is unrecognized.

**Rationale**: 25,900/25,900 `tool_complete` events say `success` purely because the deriver
reads result keys the host never populates while ignoring `tool_response.is_error` — a blind
spot, not an absence of failures. Fail-open on unknown shapes avoids inventing false failures
across engines.

### D-190-04 — Honest `spec verify` outcome

Thread an `outcome` into the `spec verify` emit (`spec_cmd.py`): add an `outcome` parameter to
`_emit_signal` forwarding to `emit_framework_operation`'s existing `outcome` kwarg, set to
`success` when not drifted or corrected, else `failure`. Leave the `drift_detected` formula
untouched.

**Rationale**: `outcome` currently records "the command ran", not "the verification passed",
so 1,611/1,611 drift-detected runs read as success — the signal is a rubber stamp that any
health dashboard would misread. The formula itself already compares frontmatter to body
correctly; only the outcome semantics are wrong.

### D-190-05 — Completeness smoke harness driven from `settings.json`

Add one parametrized CI test that reads `.claude/settings.json`, resolves each wired hook
command, and subprocess-runs it against a minimal valid per-event stdin envelope, asserting no
traceback and no exit-2 crash. Reuse the `_prepare_project` harness from
`tests/integration/test_framework_hook_emitters.py` but drive the list from `settings.json`
instead of a hardcoded tuple.

**Rationale**: The `agent_kind` crash ran 6 weeks because the only settings-wide check
(`test_no_dead_wirings`) verifies a file exists, not that it runs; at least one wired hook
(`memory-session-start.py`) has zero execution coverage. Driving from `settings.json` closes
the completeness gap structurally rather than per-hook. CI-only keeps the hot path clean —
prevention belongs in CI, not every SessionStart.

### D-190-06 — Hold the framework's own invariants

Every edit under `.ai-engineering/scripts/**` is copied byte-identical to
`src/ai_engineering/templates/.ai-engineering/scripts/**`; any hook byte change regenerates
`.ai-engineering/state/hooks-manifest.json`; all new envelope fields are additive; hooks stay
stdlib-only on the hot path with pre-commit under 1s.

**Rationale**: This spec touches the governance plane itself — byte-twin parity, manifest
integrity, and the hot-path budget are the invariants that keep installs from breaking (the
exact class of pain the telemetry deck measured). A fix to the observability layer must not
regress the layer's own guarantees.

## Risks

- **Sidecar contention / hot-path budget.** The dedup sidecar adds file I/O to the error path.
  *Mitigation:* bounded atomic write / short-lived lock, `AIENG_HOOK_CACHE_TTL_SEC` window,
  fail-open to raw emit on lock timeout — never block the hook.
- **`tool_response` shape varies by engine/host.** *Mitigation:* defensive `get()` + coercion;
  fail-open to `success` on unknown shapes so no false failures are invented.
- **`VERSION` file goes stale on editable installs.** *Mitigation:* install/update writes it in
  the same finalize path that re-pins hooks-manifest; `doctor` adds a staleness check.
- **SessionStart storm surface adds startup noise.** *Mitigation:* surface only fingerprints
  above threshold in the last window, one bounded line, suppressed when clean.
- **Byte-twin / manifest drift** if a canonical edit is not mirrored. *Mitigation:* parity copy
  + `regenerate-hooks-manifest.py` are explicit steps in the delivery checklist.
- **Additive fields ignored by old readers.** *Mitigation:* fields are optional and additive;
  existing NDJSON readers already tolerate unknown keys.

## References

- doc: claude.ai artifact 216ac1f9 — fleet telemetry analysis (234k framework events, 18 repos, 28 may–19 jul 2026)
- doc: 16-agent ground-truth verification of every finding against `main` (2026-07-19); 6 findings dead/already-fixed, excluded under Non-Goals

## Open Questions

- Storm threshold N and window: reuse `AIENG_HOOK_CACHE_TTL_SEC` for the window and pick a
  per-hour N at plan time (default proposal: alarm at ≥20 same-fingerprint events/hour).
- Whether `doctor` should also report the pinned `VERSION` freshness check in v1 or defer it.
