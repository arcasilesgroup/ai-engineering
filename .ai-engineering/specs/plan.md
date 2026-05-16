---
spec: spec-137
slug: event-relevance-discipline
title: Plan — Event Relevance Discipline
pipeline: build
phases: 7
status: approved
branch: claude/merge-and-draft-spec-M5T9f
date_approved: 2026-05-16
auto_approved: true
---

# Plan — spec-137 Event Relevance Discipline

This plan decomposes spec-137 into seven phases (M1..M7) with bite-sized
tasks, TDD-first ordering, and explicit gate criteria. Each task lists
the files it touches, the expected outcome, and the verification step.
The full quality loop runs once at the end (CONSTITUTION.md §13.5
single-round fail-loud).

## Branch / PR

- Working branch: `claude/merge-and-draft-spec-M5T9f`
- Target: `main` via final PR after all phases complete and tests green.

## Quality bar

- TDD: every new test is RED before implementation; every changed test is updated in the same commit as the code it covers.
- No `# noqa`, `# nosec`, `// @ts-ignore`, or other suppression.
- No backwards-compat shim for retired emit semantics.
- Hot-path budget: pre-commit < 1 s, pre-push < 5 s.
- Each phase's verification step runs locally before moving to the next.

## Phase 1 (M2-foundation) — Schema migration + severity field

**Goal**: Bump `schemaVersion` to 2 and add `severity` as a first-class field on `FrameworkEvent`. Keep all 13 kinds in `ALLOWED_EVENT_KINDS`.

### Tasks

1. **P1.T1**: Read [tools/skill_domain/event_schema.py](tools/skill_domain/event_schema.py) end-to-end to understand current shape.
2. **P1.T2**: Add `SEVERITY_VALUES = frozenset({"S0", "S1", "S2", "S3"})` constant at module top.
3. **P1.T3**: Add `severity: Literal["S0", "S1", "S2", "S3"]` to `FrameworkEvent` TypedDict (or to the Pydantic model — whichever shape is current).
4. **P1.T4**: Bump the `schemaVersion` module-level constant `1 → 2`.
5. **P1.T5**: Add `severity` to the required-field tuple at [tools/skill_domain/event_schema.py:72](tools/skill_domain/event_schema.py:72).
6. **P1.T6**: Update the validator function to assert `severity in SEVERITY_VALUES` when present; accept events without severity ONLY if `schemaVersion == 1` (read-only historical path).
7. **P1.T7**: Update existing schema tests at [tests/unit/state/test_event_schema.py](tests/unit/state/test_event_schema.py) to include `severity` in fixtures and parametrized required-field checks. Run pytest on this file; expect green.

### Verification

```
uv run pytest tests/unit/state/test_event_schema.py -v
```

Expected: all tests green; new severity assertion fails when omitted from a v2 event.

## Phase 2 (M2-mirrors) — Collapse three frozensets

**Goal**: Make [tools/skill_domain/event_schema.py:37](tools/skill_domain/event_schema.py:37) the single source of truth for `ALLOWED_EVENT_KINDS`; assert at CI time that the two stdlib mirrors cannot drift.

### Tasks

1. **P2.T1**: Identify the three sites:
   - Authority: `tools/skill_domain/event_schema.py` (frozenset).
   - Mirror 1: `.ai-engineering/scripts/hooks/_lib/observability.py` (`_ALLOWED_KINDS`).
   - Mirror 2: `.ai-engineering/scripts/hooks/_lib/hook-common.py` (third copy in `validate_event_schema`).
2. **P2.T2**: Write the new test FIRST (RED): `tests/unit/state/test_event_kinds_single_source.py`. The test:
   - Imports `ALLOWED_EVENT_KINDS` from the authority.
   - Reads the two mirror files as text, extracts the frozenset literal, parses it.
   - Asserts membership equality.
3. **P2.T3**: Run the test — it should pass if mirrors are already aligned, or fail if drift exists. Either way, the test now locks the invariant going forward.
4. **P2.T4**: Update [tools/skill_domain/event_schema.py:37](tools/skill_domain/event_schema.py:37) — no kinds removed, no kinds added; the membership stays exactly the 13 declared kinds.

### Verification

```
uv run pytest tests/unit/state/test_event_kinds_single_source.py -v
```

Expected: green.

## Phase 3 (M3-gate) — Relevance gate helper + stdlib mirror

**Goal**: Introduce `relevance_gate(event, policy) -> bool` as the single decision point. Two implementations (package side + hook side) with parity.

### Tasks

1. **P3.T1**: Write the new test FIRST (RED): `tests/unit/state/test_event_relevance_gate.py`. Parametrize over:
   - 13 kinds × 4 severities × `failure_emission` on/off → 104 combinations.
   - Cases: kind not in allow-list → DROP; severity below floor → DROP; severity at/above floor → KEEP; failure with `failure_emission=always` → KEEP regardless of severity floor.
2. **P3.T2**: Implement `src/ai_engineering/state/relevance.py`:
   ```python
   def relevance_gate(event: FrameworkEvent, policy: AuditPolicy) -> bool:
       if event["kind"] not in policy.kind_allowlist:
           return False
       severity_rank = {"S0": 0, "S1": 1, "S2": 2, "S3": 3}
       floor = policy.severity_floor.get(event["kind"], policy.severity_floor.get("default", "S1"))
       if severity_rank[event["severity"]] > severity_rank[floor]:
           # Note: S0 is highest signal (rank 0); reject if rank is greater than floor.
           if policy.failure_emission == "always" and event.get("outcome") not in {"success", "allow"}:
               return True
           return False
       return True
   ```
3. **P3.T3**: Run the test — expect green.
4. **P3.T4**: Create the stdlib-only mirror at `.ai-engineering/scripts/hooks/_lib/relevance.py` (no third-party imports — must be importable by hook scripts that run before `uv sync`).
5. **P3.T5**: Write a parity test `tests/unit/hooks/test_relevance_gate_parity.py` that imports both modules and asserts identical behaviour on the same parametrized inputs.

### Verification

```
uv run pytest tests/unit/state/test_event_relevance_gate.py tests/unit/hooks/test_relevance_gate_parity.py -v
```

Expected: both green.

## Phase 4 (M6) — Manifest `audit_policy:` declaration

**Goal**: Surface the policy in `.ai-engineering/manifest.yml`. The installer carries the default; the relevance gate reads from it.

### Tasks

1. **P4.T1**: Write the new test FIRST: `tests/unit/test_manifest_audit_policy_default.py`. Asserts the canonical manifest carries the expected `audit_policy:` block.
2. **P4.T2**: Append to `.ai-engineering/manifest.yml` after the `telemetry:` block:
   ```yaml
   audit_policy:
     kind_allowlist:
       - skill_invoked
       - agent_dispatched
       - context_load
       - ide_hook
       - framework_error
       - framework_operation
       - git_hook
       - control_outcome
       - task_trace
       - memory_event
       - eval_run
       - retention_applied
       - policy_decision
     severity_floor:
       framework_operation: S2
       ide_hook: S2
       framework_error: S0
       default: S1
     sampling:
       policy_decision_allow: 0.10
     failure_emission: always
   ```
3. **P4.T3**: Mirror the same block into the installer template at `src/ai_engineering/templates/.ai-engineering/manifest.yml` if it exists. Confirm path.
4. **P4.T4**: Add an `AuditPolicy` Pydantic model (or TypedDict) in `src/ai_engineering/state/audit_policy.py` that parses the manifest block.
5. **P4.T5**: Add a `load_audit_policy()` helper that reads the manifest and returns an `AuditPolicy`.

### Verification

```
uv run pytest tests/unit/test_manifest_audit_policy_default.py -v
```

Expected: green.

## Phase 5 (M3-emitters) — Wire gate into writers; drop the two heartbeats

**Goal**: Activate the gate at the two canonical writers; convert `spec_verified` and `install_simulate_hook` from unconditional to change-driven.

### Tasks

1. **P5.T1**: Write the new test FIRST: `tests/unit/state/test_event_relevance_no_heartbeats.py`. The test:
   - Greps `src/ai_engineering/cli_commands/spec_cmd.py` to assert that the call site at line 230 is inside a conditional (looks for `if drift_detected or ...` near the emit).
   - Greps `src/ai_engineering/installer/user_scope_install.py` similarly.
   - Asserts no unconditional path remains.
2. **P5.T2**: Update `src/ai_engineering/state/observability.py` (`_append_framework_events_locked` at line 107) — call `relevance_gate(event, load_audit_policy())` before the write; drop silently if `False`.
3. **P5.T3**: Update `.ai-engineering/scripts/hooks/_lib/observability.py` (hook-side at line 224) — same logic with the stdlib-mirror gate.
4. **P5.T4**: Update [src/ai_engineering/cli_commands/spec_cmd.py:230](src/ai_engineering/cli_commands/spec_cmd.py:230): wrap the emit in `if drift_detected: emit_framework_event(...)`. Add `severity="S1"` (state-change) when drift detected.
5. **P5.T5**: Update [src/ai_engineering/installer/user_scope_install.py:1220](src/ai_engineering/installer/user_scope_install.py:1220): wrap in `if outcome != "success" or first_seen: emit_framework_event(...)`. Add `severity="S2"` baseline, `severity="S0"` on failure.
6. **P5.T6**: All other 28 enumerated emit sites in brief §5: add explicit `severity=` argument. Use the brief's "Conditional today?" column to choose:
   - State-change emits → `S1`.
   - Decision / policy emits → `S2`.
   - Failure / error emits → `S0`.
   - Debug / verbose emits → `S3`.

### Verification

```
uv run pytest tests/unit/state/test_event_relevance_no_heartbeats.py -v
```

Expected: green.

## Phase 6 (M5-tests + M3-finishing) — Rewrite the 18 enumerated tests

**Goal**: Update every existing test that asserts on the legacy event shape to include `severity` and the new gate behaviour. Add the telemetry-debug.log retirement test.

### Tasks

1. **P6.T1**: Update `tests/unit/state/test_event_schema.py` — DONE in P1.
2. **P6.T2**: Update `tests/unit/test_event_plane_contract.py`.
3. **P6.T3**: Update `tests/unit/hooks/test_telemetry_skill.py`.
4. **P6.T4**: Update `tests/unit/cli/test_audit_query_cli.py`.
5. **P6.T5**: Update `tests/unit/cli/test_audit_index_cli.py`.
6. **P6.T6**: Update `tests/unit/cli/test_audit_tokens_cli.py`.
7. **P6.T7**: Update `tests/unit/hooks/test_runtime_session_start.py`.
8. **P6.T8**: Update `tests/unit/hooks/test_runtime_stop_ralph.py`.
9. **P6.T9**: Update `tests/unit/hooks/test_runtime_stop_session_rollup.py`.
10. **P6.T10**: Update `tests/unit/hooks/test_runtime_subagent_stop.py`.
11. **P6.T11**: Update `tests/unit/test_mechanisms_sha_skip_when_unpinned.py`.
12. **P6.T12**: Update `tests/unit/test_doctor_service.py`.
13. **P6.T13**: Update `tests/unit/state/test_audit_index.py`, `test_audit_replay.py`, `test_audit_otel_export.py` — add severity column / projection assertions.
14. **P6.T14**: Write `tests/unit/hooks/test_telemetry_debug_log_retired.py` — asserts no call site writes to `telemetry-debug.log` and `AIENG_TELEMETRY_DEBUG` is not referenced.

### Verification

```
uv run pytest tests/unit/ -v
```

Expected: green.

## Phase 7 (M4 + M5-cleanup + M7) — Consumers + telemetry-debug retirement + CHANGELOG

**Goal**: Update consumer code paths to read severity; retire `telemetry-debug.log`; commit CHANGELOG entry.

### Tasks

1. **P7.T1**: Update [src/ai_engineering/state/audit_index.py:65](src/ai_engineering/state/audit_index.py:65) — add `severity TEXT` column to projection schema.
2. **P7.T2**: Update [src/ai_engineering/state/audit_index.py:477](src/ai_engineering/state/audit_index.py:477) — bulk-read inspects `schemaVersion`; v1 rows get severity NULL.
3. **P7.T3**: Update [src/ai_engineering/state/audit_otel_export.py:73](src/ai_engineering/state/audit_otel_export.py:73) — map S0→FATAL (21), S1→WARN (13), S2→INFO (9), S3→DEBUG (5) per OTel `SeverityNumber`.
4. **P7.T4**: Retire `telemetry-debug.log` call sites:
   - [.ai-engineering/scripts/hooks/observe.py:92](.ai-engineering/scripts/hooks/observe.py:92)
   - [.ai-engineering/scripts/hooks/instinct-extract.py:37](.ai-engineering/scripts/hooks/instinct-extract.py:37)
   - [.ai-engineering/scripts/hooks/prompt-injection-guard.py:947](.ai-engineering/scripts/hooks/prompt-injection-guard.py:947)
   - [.ai-engineering/scripts/hooks/mcp-health.py:591](.ai-engineering/scripts/hooks/mcp-health.py:591)
5. **P7.T5**: Remove `AIENG_TELEMETRY_DEBUG` references from CLAUDE.md "Runtime Layer Tunables" and any other docs.
6. **P7.T6**: Run `ai-eng audit verify` against the historical NDJSON to confirm chain integrity.
7. **P7.T7**: Add CHANGELOG entry under `## Unreleased`:
   ```markdown
   ### Breaking
   - `framework-events.ndjson` schema version bumped 1 → 2.
   - `severity` required on every event (S0..S3).
   - `spec_verified` emits only on detected drift; `install_simulate_hook` emits only on failure or first-seen mechanism.
   - `telemetry-debug.log` retired; `AIENG_TELEMETRY_DEBUG` env var removed.
   - Manifest carries new required `audit_policy:` block.
   ```

### Verification

```
uv run pytest tests/unit/ -v
uv run ai-eng audit verify
```

Expected: both green.

## Quality loop (final)

Single-round fail-loud (CONSTITUTION.md §13.5):

```
uv run pytest tests/unit/ -q
uv run python -m ai_engineering.policy.release_version_guard
uv run ai-eng check
uv run ai-eng audit verify
```

If any fail: stop, escalate the failure, fix, re-run.

## Out-of-scope reminders (D-137-06..10)

- No `AIENG_AUDIT_POLICY_PATH` env-var override.
- No CI guard for new emit sites in this PR.
- No backfill of historical decisions in `state.db decisions`.
- No per-kind sampling beyond existing 10% policy-decision sampler.
- No `outcome` enum redesign.

---

**Handoff**: this plan is the contract for `/ai-build`.
