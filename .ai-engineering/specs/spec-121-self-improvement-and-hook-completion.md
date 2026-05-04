# spec-121: Self-Improvement Loop Completion + Hook Event Coverage

**Status**: approved (autonomous)
**Owner**: ai-engineering
**Date**: 2026-05-04
**Branch**: feat/spec-120-observability-modernization (continuation)
**Predecessors**: spec-120 (observability modernization), spec-118 (memory), spec-119 (eval)

## Problem

Audit "Análisis Profundo — Harness Engineering" identified two gaps after spec-120 landed:

### F. Self-Improvement (Osmani ratchet) — execution incomplete
1. ~~`instinct-observe.py` failing every invocation~~ → fixed in spec-120 (`8e395428`).
2. **No automatic AGENTS.md update path** — `/ai-learn` writes only to `LESSONS.md`; the procedural-memory layer (AGENTS.md / CONSTITUTION.md) never gets reinforced from delivery feedback.
3. **No scheduled entropy GC** — `/ai-entropy-gc` skill exists but requires manual invocation; no cron/schedule wiring drives it weekly as the skill documentation prescribes.

### G. Hooks Schema vs Reality — coverage incomplete
- Schema (`.ai-engineering/schemas/hooks.schema.json`) declares 18 events. Only 9 are wired in `.claude/settings.json` (Stop, SubagentStop, PreCompact, PostCompact, SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure).
- **Notification** (LLM-driven user notifications) and **SessionEnd** are emitted by Claude Code natively but unwired — telemetry blind spots.
- **http** and **prompt** hook types are documented in schema but no executor exists; only `command` is supported.

## Goals

- Reinforce procedural memory: `/ai-learn` proposes AGENTS.md/CONSTITUTION.md edits when accumulated lessons cross a threshold.
- Close ratchet end-to-end: scheduled entropy GC runs weekly without manual nudge.
- Wire `Notification` and `SessionEnd` hook events so the audit chain is complete for the events Claude Code actually fires.
- Add minimal `http` adapter for `command` type hooks (POST telemetry to a backend URL) — the cross-IDE primitive for enterprise centralized audit.
- Document `prompt` type as deferred (requires LLM call inside hook — defer until ai-eval scoring pipeline lands).

## Non-Goals

- Full LLM-as-hook (`prompt` type executor). Deferred — requires sandboxed Anthropic SDK call with budget caps.
- Wiring `ToolError`, `ModelResponse`, `McpConnectionChange`, `TaskStart/Complete`, `ContextTruncation`, `RateLimitHit`, `PermissionRequest`, `SessionPause/Resume` — Claude Code does not natively emit these. Cross-IDE schema parity stays in schema; runtime wiring is Claude-only for events Claude actually fires.
- Replacing existing `runtime-stop.py` Stop logic. SessionEnd is additive.

## Acceptance Criteria

1. New hook script `runtime-notification.py` wired to `Notification` event. Emits `ide_hook` telemetry. Fail-open. Hot-path budget < 500 ms.
2. New hook script `runtime-session-end.py` wired to `SessionEnd` event. Flushes session checkpoint, emits `framework_operation` event with session summary (tools used, skills invoked, duration). Fail-open.
3. `/ai-learn` skill SKILL.md gains "AGENTS.md proposal" mode: when ≥ 5 lessons of same category accumulate, surface proposal block for human review (output to `agents-proposals.md`, never auto-mutates AGENTS.md — same constraint as `/ai-dream` D-118-04).
4. `/schedule` skill snippet documented in `/ai-entropy-gc` SKILL.md showing the exact cron line (`0 4 * * 1` weekly Monday 04:00 UTC). Add `.ai-engineering/scripts/scheduled/entropy-gc.sh` wrapper.
5. `_lib/hook_http.py` helper provides `dispatch_http_hook(url, payload, timeout)` — used by command hooks that opt into mirroring telemetry to a backend. Best-effort, fail-open. Pinned timeout 5 s.
6. `hooks-manifest.json` regenerated to include new scripts; integrity check passes.
7. Test stub at `.ai-engineering/tests/test_spec_121_hooks.py` validates new hook scripts handle empty stdin, valid event payload, and unknown event gracefully (all exit 0).
8. `ai-commit` produces a single conventional commit message referencing `spec-121`.

## Out of scope (open follow-ups)

- E2B sandboxing tier (audit §C).
- pgvector semantic memory (audit §B).
- OTel GenAI conventions on hooks (audit §E).
- Tool-call output offloading already done in spec-120 — confirmed.
- `prompt` hook type executor.

## Telemetry impact

New event kinds emitted: `framework_operation` with `operation=session_end_summary`, `operation=agents_proposal_drafted`, `operation=entropy_gc_scheduled_run`. All flow into `framework-events.ndjson` and the spec-120 SQLite projection.

## Risk and rollback

- All hooks fail-open. If `runtime-notification.py` errors, prompt continues.
- Manifest integrity in `warn` mode for dev — no regression on stale manifest.
- Scheduled entropy-gc opens **draft** PRs only; no auto-merge (existing skill rule).
- Rollback = revert single commit; deny rules and existing hooks unchanged.
