---
title: Event Relevance Discipline
status: draft
audience: framework dev
branch: spec-128/context-overrides-refactor
length_estimate: ~860 lines
authoring_style: diagnostic-first, citation-dense
principles_required: "§10.1 KISS, §10.2 YAGNI, §10.5 TDD, §10.6 SDD, §10.7 Clean Code"
delivery_mode: brief → /ai-brainstorm
mantra: "lo que escribamos, donde sea, debe ser relevante"
date_drafted: 2026-05-16
volume_snapshot_date: 2026-05-15
source_skill: ai-spec-draft
---

# Event Relevance Discipline

> Mantra: **lo que escribamos, donde sea, debe ser relevante.**
> When 92% of the audit tail is two unconditional emit sites, signal stops
> being signal. This brief frames the problem; `/ai-brainstorm` picks the
> mechanism.

## 1. Vision

Today the framework audit tail is dominated by polling-style heartbeats: `ai-eng spec verify` writes a `spec_verified` row on every invocation, and `install_simulate_hook` writes one row per tool per synthetic install — together 92% of a typical day's events. Neither row encodes a state change; both are emit-on-call instead of emit-on-change. A reader scrolling the tail learns almost nothing about what actually happened, and every consumer pays the cost of filtering before any signal surfaces. This brief proposes a single discipline applied uniformly across every event and log sink we write — `framework-events.ndjson`, `state.db` event-like tables, `observation-events.ndjson`, `lock-failures.ndjson`, runtime sidecars, `telemetry-debug.log` — namely that **every emit must justify itself**. The justification mechanism is left open for the spec phase: it could be a kind whitelist in the manifest (Prometheus / OTel-semconv style), a severity-tier vocabulary with read-time filter (OTel `SeverityNumber` / RFC 5424 style), a per-emit programmatic hook (Sentry `before_send` style), a per-emit justification linter (Falco rules-registry style), or a wide-event single-source-of-truth that emits fewer kinds with denser context (Honeycomb / Observability 2.0 style). What is fixed is the precondition: relevance is asserted at the writer boundary, not deferred to a reader. Anything that does not survive the relevance test does not get written, anywhere.

## 2. Scope Boundary

### In scope

- `.ai-engineering/state/framework-events.ndjson` — the canonical append-only audit chain.
- All event-like tables in `.ai-engineering/state/state.db`: `events`, `decisions`, `gate_findings`, `risk_acceptances`, `hooks_integrity`, `install_state`, `install_steps`, `ownership_map`, `tool_capabilities`.
- `.ai-engineering/state/observation-events.ndjson` (instincts sliding window, distinct schema today).
- `.ai-engineering/state/lock-failures.ndjson` (sidecar breadcrumb, NOT in hash chain today).
- `.ai-engineering/state/telemetry-debug.log` (plain-text debug log, gated by `AIENG_TELEMETRY_DEBUG=1`).
- `.ai-engineering/runtime/event-sidecars/<sha256>.json` (oversized event offload).
- The two canonical writers: [src/ai_engineering/state/observability.py:107](src/ai_engineering/state/observability.py:107) (package side) and [.ai-engineering/scripts/hooks/_lib/observability.py:224](.ai-engineering/scripts/hooks/_lib/observability.py:224) (hook-side stdlib mirror).
- The three `ALLOWED_EVENT_KINDS` frozensets that must stay in sync: [tools/skill_domain/event_schema.py:37](tools/skill_domain/event_schema.py:37), [.ai-engineering/scripts/hooks/_lib/observability.py:24](.ai-engineering/scripts/hooks/_lib/observability.py:24), [.ai-engineering/scripts/hooks/_lib/hook-common.py:54](.ai-engineering/scripts/hooks/_lib/hook-common.py:54).
- Manifest knobs in [.ai-engineering/manifest.yml:98](.ai-engineering/manifest.yml:98) (`telemetry.consent`, `telemetry.default`) and any new relevance-policy fields.
- All consumers: `ai-eng audit index`, `audit query`, `audit tokens`, `audit replay`, `audit otel-export`, plus the instinct extractor.
- All tests that lock the contract (enumerated in §5).

### Out of scope

- IDE-extras content (mirror-only payload).
- Hook integrity manifest (`hooks-manifest.json`) — separate concern (spec-122 sub-d).
- Memory layer / Engram cross-session observation (external third-party add-on per `docs/integrations/engram.md`).
- Retention TTL policy mechanics (already covered by [src/ai_engineering/state/retention.py:122](src/ai_engineering/state/retention.py:122) emitting `retention_applied` only when non-zero rows pruned).
- The OPA bundle or policy authoring — relevance policy is one config concern, OPA is another.
- The `decision-store.json` → `state.db decisions` migration (already shipped per recent commit).

## 3. Diagnostic Snapshot

Numbers below come from a read-only survey of the current state on 2026-05-15 (a single working day).

### Volume

- **Total NDJSON lines**: 1,335 across a span of approximately 8 hours 30 minutes (2026-05-15T14:17:10Z → 2026-05-15T22:47:02Z). That is ~157 events/hour during an active day.
- **Declared event kinds** in the schema: 11 — `skill_invoked`, `agent_dispatched`, `context_load`, `ide_hook`, `framework_error`, `framework_operation`, `git_hook`, `control_outcome`, `task_trace`, `memory_event`, `eval_run`, `retention_applied`, `policy_decision` ([tools/skill_domain/event_schema.py:37](tools/skill_domain/event_schema.py:37)).
- **Kinds actually emitted on the snapshot day**: 3 of 11 — `framework_operation` (1,264 / 95%), `git_hook` (61 / 4.5%), `policy_decision` (10 / 0.7%).

### The top two emitters dominate

The two emit sites below account for 1,230 of 1,335 rows — **92.1% of the entire log**:

| Rank | Count | Emit site | Trigger | What changes between rows |
| ---: | ---: | --- | --- | --- |
| 1 | 848 | [src/ai_engineering/cli_commands/spec_cmd.py:230](src/ai_engineering/cli_commands/spec_cmd.py:230) (`framework_operation / spec_verified`) | Every `ai-eng spec verify` (called from pre-commit hook) | Two counter values (checkbox totals) and a `drift_detected` bool |
| 2 | 382 | [src/ai_engineering/installer/user_scope_install.py:1220](src/ai_engineering/installer/user_scope_install.py:1220) (`framework_operation / install_simulate_hook`) | One row per tool per synthetic install run | Per-tool mechanism outcome |

Both are unconditional, polling-style emissions. `spec_verified` fires whether or not drift is detected. `install_simulate_hook` fires whether or not the mechanism outcome is interesting. Neither emit-site honours an "emit only on state change" or "emit only on signal-worthy outcome" guard.

### No first-class relevance signal in the schema

The `FrameworkEvent` model declares 8 required fields ([tools/skill_domain/event_schema.py:72](tools/skill_domain/event_schema.py:72)): `kind`, `engine`, `timestamp`, `component`, `outcome`, `correlationId`, `schemaVersion`, `project`. There is **no** `severity`, `signal_tier`, `importance`, `priority`, or relevance hint field. The only quality discriminator is `outcome` (`success` / `failure` / `degraded` / `warn` / `allow` / `blocked`), which collapses "this worked normally and is uninteresting" and "this worked normally and matters for the audit story" into the same bucket (`success`).

### Three frozensets drift surface

`ALLOWED_EVENT_KINDS` is declared in three places that must agree:

1. [tools/skill_domain/event_schema.py:37](tools/skill_domain/event_schema.py:37) — Pydantic-side authoritative list.
2. [.ai-engineering/scripts/hooks/_lib/observability.py:24](.ai-engineering/scripts/hooks/_lib/observability.py:24) — `_ALLOWED_KINDS` for the stdlib mirror used by hook scripts.
3. [.ai-engineering/scripts/hooks/_lib/hook-common.py:54](.ai-engineering/scripts/hooks/_lib/hook-common.py:54) — third copy in `validate_event_schema`.

Any kind added or removed must be edited in all three or validation fails inconsistently. No test today asserts the three frozensets agree.

### Manifest has no relevance knob

[.ai-engineering/manifest.yml:98](.ai-engineering/manifest.yml:98) declares only `telemetry.consent: strict-opt-in` and `telemetry.default: disabled`. No `audited_kinds`, `signal_tier`, `relevance_policy`, or sampling configuration exists. The only runtime tunable affecting volume is `AIENG_EVENT_SIDECAR_BYTES` ([.ai-engineering/scripts/hooks/_lib/audit.py:15](.ai-engineering/scripts/hooks/_lib/audit.py:15), default 3072), which only affects whether an oversized event is offloaded — it does not gate emission. The policy-decision sampler is hardcoded at ~10% allow-sampling ([src/ai_engineering/governance/decision_log.py:56](src/ai_engineering/governance/decision_log.py:56)).

### Other sinks each carry their own emit discipline (or lack of it)

- **`observation-events.ndjson`** — Written by [.ai-engineering/scripts/hooks/_lib/instincts.py:822](.ai-engineering/scripts/hooks/_lib/instincts.py:822) on every `PreToolUse` / `PostToolUse`. Different schema (`tool_start` / `tool_complete` kinds). Self-pruned sliding window. Not in audit chain.
- **`lock-failures.ndjson`** — Written by [.ai-engineering/scripts/hooks/_lib/locked_append.py:73](.ai-engineering/scripts/hooks/_lib/locked_append.py:73) on lock exhaustion. Yet another schema (`schema_version`, `event_id`, `timestamp`, `engine`, `kind`). Explicitly NOT in the hash chain ([locked_append.py:114](.ai-engineering/scripts/hooks/_lib/locked_append.py:114)). No reader exists.
- **`telemetry-debug.log`** — Plain-text, written only when `AIENG_TELEMETRY_DEBUG=1`. Sites: [.ai-engineering/scripts/hooks/observe.py:92](.ai-engineering/scripts/hooks/observe.py:92), [.ai-engineering/scripts/hooks/instinct-extract.py:37](.ai-engineering/scripts/hooks/instinct-extract.py:37), [.ai-engineering/scripts/hooks/prompt-injection-guard.py:947](.ai-engineering/scripts/hooks/prompt-injection-guard.py:947), [.ai-engineering/scripts/hooks/mcp-health.py:591](.ai-engineering/scripts/hooks/mcp-health.py:591). No reader.
- **`state.db decisions` table** — Empty (0 rows) at the time of this survey. No prior signal-discipline decision has been recorded.
- **`runtime/event-sidecars/`** — Per-event JSON files for payloads > 3 KiB, written by [src/ai_engineering/state/sidecar.py](src/ai_engineering/state/sidecar.py) and [.ai-engineering/scripts/hooks/_lib/audit.py](.ai-engineering/scripts/hooks/_lib/audit.py) (`maybe_offload_event`). Not in hash chain.

### Consumer assumptions

Every consumer assumes the current kind set and column shape:

- `ai-eng audit index` ([src/ai_engineering/cli_commands/audit_cmd.py:48](src/ai_engineering/cli_commands/audit_cmd.py:48), [src/ai_engineering/state/audit_index.py:477](src/ai_engineering/state/audit_index.py:477)) — bulk-reads NDJSON, projects into SQLite, hardcodes 19 columns including `genai_*` extracts.
- `ai-eng audit tokens` ([src/ai_engineering/state/audit_index.py:106](src/ai_engineering/state/audit_index.py:106)) — three rollup views: `skill_token_rollup` (kind=`skill_invoked`), `agent_token_rollup` (kind=`agent_dispatched`), `session_token_rollup` (all kinds with `session_id`).
- `ai-eng audit replay` ([src/ai_engineering/state/audit_replay.py:68](src/ai_engineering/state/audit_replay.py:68)) — span-tree walk over `span_id`, `trace_id`, `parent_span_id`.
- `ai-eng audit otel-export` ([src/ai_engineering/state/audit_otel_export.py:73](src/ai_engineering/state/audit_otel_export.py:73)) — OTLP/JSON envelope; assumes subset of columns including `genai_system`, `genai_model`, `input_tokens`, `output_tokens`.
- Instinct extractor ([.ai-engineering/scripts/hooks/_lib/instincts.py:648](.ai-engineering/scripts/hooks/_lib/instincts.py:648)) — reads `framework-events.ndjson` directly, filters `kind == "skill_invoked"`.

Any kind removed silently breaks the rollups that depend on it.

## 4. Architecture

The brief proposes a structural intervention at the writer boundary: a **relevance contract** that every emit site asserts before a row is written, applied uniformly across every sink.

```
                    ┌────────────────────────────────────────┐
                    │   Caller (skill / agent / hook / CLI)  │
                    └──────────────────┬─────────────────────┘
                                       │  emit_*(payload + relevance_claim)
                                       v
                    ┌────────────────────────────────────────┐
                    │           Relevance Contract           │
                    │  - asserts caller's claim is admissible│
                    │  - mechanism TBD by /ai-brainstorm:    │
                    │      * kind whitelist (manifest)       │
                    │      * severity tier (S0..S3 or RFC)   │
                    │      * per-emit justification          │
                    │      * before_send programmatic hook   │
                    │      * sampler with deterministic rate │
                    └──────────────────┬─────────────────────┘
                                       │  admitted? yes → write; no → drop
                                       v
        ┌────────────────────────────────────────────────────────────┐
        │  Canonical writers (must share the contract)               │
        │   - src/ai_engineering/state/observability.py:107          │
        │   - .ai-engineering/scripts/hooks/_lib/observability.py:224│
        └──────────────────┬─────────────────────────────────────────┘
                           │  shape-validated + chained
                           v
        ┌────────────────────────────────────────────────────────────┐
        │  Sinks (each sink keeps its own shape but the contract is  │
        │  enforced at the writer, not the sink)                     │
        │   - framework-events.ndjson  (hash-chained)                │
        │   - state.db events table   (projection of NDJSON)         │
        │   - state.db decisions/gate_findings/... (event-like)      │
        │   - observation-events.ndjson  (instinct layer)            │
        │   - lock-failures.ndjson  (breadcrumb-only today)          │
        │   - runtime/event-sidecars/<sha256>.json                   │
        │   - telemetry-debug.log  (gated debug-only)                │
        └────────────────────────────────────────────────────────────┘
```

The contract surface lives in three files today and must collapse to a single source of truth so the three frozenset drift goes away:

- `tools/skill_domain/event_schema.py` (authoritative).
- `.ai-engineering/scripts/hooks/_lib/observability.py` (stdlib mirror — re-imports authoritative).
- `.ai-engineering/scripts/hooks/_lib/hook-common.py` (validation mirror — re-imports authoritative).

The mechanism (whitelist / severity / justification / sampler / hybrid) is the central Open Decision (§9). What is fixed in the architecture is the **location** of enforcement: at the writer boundary, not at the consumer. Read-time filtering remains available for analytics, but it is never the place where noise is gated.

## 5. Evidence Catalog

### Emit sites that need a relevance claim

| File:line | Kind | Trigger | Conditional today? |
| --- | --- | --- | --- |
| [src/ai_engineering/cli_commands/spec_cmd.py:230](src/ai_engineering/cli_commands/spec_cmd.py:230) | `framework_operation / spec_verified` | every `ai-eng spec verify` | unconditional |
| [src/ai_engineering/cli_commands/spec_cmd.py:37](src/ai_engineering/cli_commands/spec_cmd.py:37) | `framework_operation / spec_activated` | `ai-eng spec start` | on-success only |
| [src/ai_engineering/installer/user_scope_install.py:1220](src/ai_engineering/installer/user_scope_install.py:1220) | `framework_operation / install_simulate_hook` | per tool, per synthetic install | unconditional |
| [src/ai_engineering/installer/mechanisms/__init__.py:295](src/ai_engineering/installer/mechanisms/__init__.py:295) | `framework_operation / sha_pin_skipped` | per tool+mechanism when unpinned | deduped via `_SHA_PIN_SKIPPED_AUDIT_SEEN` set |
| [src/ai_engineering/installer/phases/state.py:154](src/ai_engineering/installer/phases/state.py:154) | `framework_operation / install-state-phase` | end of phase | unconditional |
| [src/ai_engineering/state/migrations/_runner.py:159](src/ai_engineering/state/migrations/_runner.py:159) | `framework_operation / migration_integrity_check` | only on integrity violation | failure-only (high signal) |
| [src/ai_engineering/governance/decision_log.py:235](src/ai_engineering/governance/decision_log.py:235) | `policy_decision` | 100% blocked, ~10% allow | sampled |
| [src/ai_engineering/policy/checks/_accept_lookup.py:144](src/ai_engineering/policy/checks/_accept_lookup.py:144) | `control_outcome / risk-acceptance` | per lookup | unconditional |
| [src/ai_engineering/doctor/service.py:388](src/ai_engineering/doctor/service.py:388) | `framework_operation / doctor` | every `ai-eng doctor` | unconditional |
| [src/ai_engineering/state/retention.py:122](src/ai_engineering/state/retention.py:122) | `retention_applied` | only when rows pruned | change-driven (good shape) |
| [.ai-engineering/scripts/hooks/telemetry-skill.py:29](.ai-engineering/scripts/hooks/telemetry-skill.py:29) | `ide_hook / user-prompt-submit` | empty prompt or no `/ai-` prefix | warn-only |
| [.ai-engineering/scripts/hooks/telemetry-skill.py:56](.ai-engineering/scripts/hooks/telemetry-skill.py:56) | `skill_invoked` | `/ai-<name>` found | on-detection |
| [.ai-engineering/scripts/hooks/telemetry-skill.py:65](.ai-engineering/scripts/hooks/telemetry-skill.py:65) | `context_load` (multiple) | per declared context | per-load |
| [.ai-engineering/scripts/hooks/observe.py:76](.ai-engineering/scripts/hooks/observe.py:76) | `ide_hook / post-tool-use` | `tool_name == "Agent"` non-agent-id branch | conditional |
| [.ai-engineering/scripts/hooks/observe.py:47](.ai-engineering/scripts/hooks/observe.py:47) | `agent_dispatched` | `tool_name == "Agent"` with `subagent_type` | on-dispatch |
| [.ai-engineering/scripts/hooks/runtime-session-start.py:101](.ai-engineering/scripts/hooks/runtime-session-start.py:101) | `framework_operation / session_started` | every SessionStart | unconditional |
| [.ai-engineering/scripts/hooks/runtime-session-end.py:74](.ai-engineering/scripts/hooks/runtime-session-end.py:74) | `framework_operation / session_end_summary` | every SessionEnd | unconditional |
| [.ai-engineering/scripts/hooks/runtime-notification.py:58](.ai-engineering/scripts/hooks/runtime-notification.py:58) | `framework_operation / ide_notification` | every IDE notification | unconditional |
| [.ai-engineering/scripts/hooks/runtime-subagent-stop.py:93](.ai-engineering/scripts/hooks/runtime-subagent-stop.py:93) | `framework_operation / subagent_stop` | every SubagentStop | unconditional |
| [.ai-engineering/scripts/hooks/runtime-stop.py:327](.ai-engineering/scripts/hooks/runtime-stop.py:327) | `framework_error / ralph_convergence_error` | convergence check throws | error-only |
| [.ai-engineering/scripts/hooks/runtime-stop.py:344](.ai-engineering/scripts/hooks/runtime-stop.py:344) | `framework_operation / ralph_converged` | converged | state-change |
| [.ai-engineering/scripts/hooks/runtime-stop.py:359](.ai-engineering/scripts/hooks/runtime-stop.py:359) | `framework_error / ralph_max_retries_exceeded` | retry ceiling hit | error-only |
| [.ai-engineering/scripts/hooks/runtime-stop.py:382](.ai-engineering/scripts/hooks/runtime-stop.py:382) | `framework_operation / ralph_reinject` | reinjection triggered | state-change |
| [.ai-engineering/scripts/hooks/runtime-stop.py:563](.ai-engineering/scripts/hooks/runtime-stop.py:563) | `framework_operation / session_token_rollup` | every Stop with session data | unconditional |
| [.ai-engineering/scripts/hooks/instinct-extract.py:25](.ai-engineering/scripts/hooks/instinct-extract.py:25) | `framework_operation / instinct-extract` | only when new patterns extracted | change-driven |
| [.ai-engineering/scripts/hooks/mcp-health.py:259](.ai-engineering/scripts/hooks/mcp-health.py:259) | `control_outcome` | per-server MCP health | per-check |
| [.ai-engineering/scripts/hooks/mcp-health.py:418](.ai-engineering/scripts/hooks/mcp-health.py:418) | `control_outcome` | aggregate MCP health | per-run |
| [.ai-engineering/scripts/hooks/prompt-injection-guard.py:107](.ai-engineering/scripts/hooks/prompt-injection-guard.py:107) | `framework_operation` | script integrity OK | per-prompt |
| [.ai-engineering/scripts/hooks/prompt-injection-guard.py:734](.ai-engineering/scripts/hooks/prompt-injection-guard.py:734) | `control_outcome` | per-pattern match | per-pattern |

### Schema authority and frozenset drift surface

| File:line | Concern |
| --- | --- |
| [tools/skill_domain/event_schema.py:37](tools/skill_domain/event_schema.py:37) | Authoritative `ALLOWED_EVENT_KINDS` |
| [tools/skill_domain/event_schema.py:72](tools/skill_domain/event_schema.py:72) | Required-field tuple (8 fields, no severity) |
| [tools/skill_domain/event_schema.py:84](tools/skill_domain/event_schema.py:84) | `FrameworkEvent` TypedDict |
| [.ai-engineering/scripts/hooks/_lib/observability.py:24](.ai-engineering/scripts/hooks/_lib/observability.py:24) | Mirror frozenset #1 |
| [.ai-engineering/scripts/hooks/_lib/hook-common.py:54](.ai-engineering/scripts/hooks/_lib/hook-common.py:54) | Mirror frozenset #2 |
| [src/ai_engineering/state/observability.py:107](src/ai_engineering/state/observability.py:107) | Package-side writer (`_append_framework_events_locked`) |
| [.ai-engineering/scripts/hooks/_lib/observability.py:224](.ai-engineering/scripts/hooks/_lib/observability.py:224) | Hook-side writer (stdlib mirror) |

### Sinks (each will be touched)

| File:line | Sink | Schema relation |
| --- | --- | --- |
| `.ai-engineering/state/framework-events.ndjson` | NDJSON hash-chained log | canonical `FrameworkEvent` |
| `.ai-engineering/state/state.db` (`events` table) | SQLite projection | 19 columns ([src/ai_engineering/state/audit_index.py:65](src/ai_engineering/state/audit_index.py:65)) |
| `.ai-engineering/state/state.db` (`decisions` table) | event-like state | Pydantic `DecisionStore` (today empty) |
| `.ai-engineering/state/observation-events.ndjson` | instinct sliding window | distinct schema ([instincts.py:39](.ai-engineering/scripts/hooks/_lib/instincts.py:39)) |
| `.ai-engineering/state/lock-failures.ndjson` | lock-failure breadcrumb | distinct schema ([locked_append.py:73](.ai-engineering/scripts/hooks/_lib/locked_append.py:73)) |
| `.ai-engineering/state/telemetry-debug.log` | plain-text debug | none — opt-in only |
| `.ai-engineering/runtime/event-sidecars/<sha256>.json` | oversized payload offload | sha-256-keyed JSON |

### Tests that lock the current contract (require updates under §3 hard migration)

| File:line | What it locks |
| --- | --- |
| [tests/unit/state/test_event_schema.py:17](tests/unit/state/test_event_schema.py:17) | Minimal event fixture; required-field parametrize |
| [tests/unit/state/test_event_schema.py:37](tests/unit/state/test_event_schema.py:37) | All 8 required keys |
| [tests/unit/test_event_plane_contract.py:35](tests/unit/test_event_plane_contract.py:35) | Rejects malformed `skill_invoked_malformed` |
| [tests/unit/test_event_plane_contract.py:52](tests/unit/test_event_plane_contract.py:52) | `agent_dispatched` / `skill_invoked` normalization |
| [tests/unit/hooks/test_telemetry_skill.py:92](tests/unit/hooks/test_telemetry_skill.py:92) | `kind == "skill_invoked"` |
| [tests/unit/hooks/test_telemetry_skill.py:115](tests/unit/hooks/test_telemetry_skill.py:115) | `kind == "ide_hook"` |
| [tests/unit/cli/test_audit_query_cli.py:126](tests/unit/cli/test_audit_query_cli.py:126) | `parsed[0]["kind"] == "skill_invoked"` |
| [tests/unit/cli/test_audit_index_cli.py:48](tests/unit/cli/test_audit_index_cli.py:48) | Fixture with `kind == "skill_invoked"` |
| [tests/unit/cli/test_audit_tokens_cli.py:39](tests/unit/cli/test_audit_tokens_cli.py:39) | Fixtures with `skill_invoked` + `agent_dispatched` |
| [tests/unit/hooks/test_runtime_session_start.py:93](tests/unit/hooks/test_runtime_session_start.py:93) | `detail.operation == "session_started"` |
| [tests/unit/hooks/test_runtime_stop_ralph.py:115](tests/unit/hooks/test_runtime_stop_ralph.py:115) | `detail.operation == "ralph_converged"` |
| [tests/unit/hooks/test_runtime_stop_ralph.py:153](tests/unit/hooks/test_runtime_stop_ralph.py:153) | `detail.operation == "ralph_reinject"` |
| [tests/unit/hooks/test_runtime_stop_session_rollup.py:182](tests/unit/hooks/test_runtime_stop_session_rollup.py:182) | `detail.operation == "session_token_rollup"` |
| [tests/unit/hooks/test_runtime_subagent_stop.py:93](tests/unit/hooks/test_runtime_subagent_stop.py:93) | `detail.operation == "subagent_stop"` |
| [tests/unit/test_mechanisms_sha_skip_when_unpinned.py:125](tests/unit/test_mechanisms_sha_skip_when_unpinned.py:125) | `detail.operation == "sha_pin_skipped"` |
| [tests/unit/test_doctor_service.py:400](tests/unit/test_doctor_service.py:400) | `operation == "doctor"`, `component == "doctor"` |
| [tests/unit/state/test_audit_index.py](tests/unit/state/test_audit_index.py) | 19-column `events` table |
| [tests/unit/state/test_audit_replay.py](tests/unit/state/test_audit_replay.py) | `_EVENT_COLUMNS` span tree |
| [tests/unit/state/test_audit_otel_export.py](tests/unit/state/test_audit_otel_export.py) | OTLP shape subset |

### Manifest / config

| File:line | Concern |
| --- | --- |
| [.ai-engineering/manifest.yml:98](.ai-engineering/manifest.yml:98) | `telemetry.consent: strict-opt-in`, `telemetry.default: disabled` |
| [.ai-engineering/scripts/hooks/_lib/audit.py:15](.ai-engineering/scripts/hooks/_lib/audit.py:15) | `AIENG_EVENT_SIDECAR_BYTES` env (default 3072) |
| [src/ai_engineering/governance/decision_log.py:56](src/ai_engineering/governance/decision_log.py:56) | Hardcoded 10% allow-sample |

## 6. Roadmap

The spec phase will sequence these milestones; the brief proposes the ordering, gates, and dependencies.

### M1 — Mechanism decision (`/ai-brainstorm`)

- Pick the relevance mechanism from the option-space in §9.
- Persist the choice as a decision row in `.ai-engineering/state/state.db decisions`.
- Acceptance gate: decision row exists; spec.md cites it.

### M2 — Schema migration

- Update [tools/skill_domain/event_schema.py:37](tools/skill_domain/event_schema.py:37) — `ALLOWED_EVENT_KINDS` re-derived from the chosen mechanism; add `severity` / `signal_tier` / `relevance_claim` field if the mechanism requires it; bump `schemaVersion`.
- Collapse the three `ALLOWED_EVENT_KINDS` frozensets to a single source of truth (import-only mirror).
- Add a CI test that asserts the three sites import from the same authority.
- Acceptance gate: schema test green; CI lint catches drift.

### M3 — Emitter updates

- Audit every emit site enumerated in §5. For each: (a) keep if its relevance claim is admissible under the new contract, (b) drop if it is polling-style and carries no state change, (c) refactor to emit-on-change otherwise.
- Special attention to `spec_verified` (848 rows/day) and `install_simulate_hook` (382 rows/day): both must become change-driven or be retired.
- Centralise the two canonical writers behind a single relevance-enforcing gate.
- Acceptance gate: a one-hour live session emits < 15 rows; a full pre-commit + pre-push pipeline emits < 5 rows.

### M4 — Consumer updates

- Update `ai-eng audit index`, `query`, `tokens`, `replay`, `otel-export` to the new schema. Token rollup views regenerate without dropped-kind regressions.
- Update the instinct extractor ([.ai-engineering/scripts/hooks/_lib/instincts.py:648](.ai-engineering/scripts/hooks/_lib/instincts.py:648)) to the new kind set.
- Acceptance gate: all consumers exercise the new schema in tests; replay produces the same span tree shape for historical events.

### M5 — Test updates

- Rewrite the 18 enumerated tests in §5 to assert against the new kind / operation set.
- Add a new test that asserts no emit site exists for the retired heartbeat operations.
- Acceptance gate: `pytest tests/unit/state tests/unit/hooks tests/unit/cli` green.

### M6 — Manifest schema

- If the mechanism is whitelist-driven or tier-driven, surface the policy in [.ai-engineering/manifest.yml:98](.ai-engineering/manifest.yml:98) under a new `audit_policy:` key.
- Document the policy shape in `docs/principles.md` or a new `docs/event-relevance.md`.
- Acceptance gate: manifest schema test green; installer carries policy default.

### M7 — Audit chain integrity verification

- Run `ai-eng audit verify` against the historical NDJSON and the post-migration NDJSON.
- Confirm `prev_event_hash` chain unbroken at the migration cut.
- Acceptance gate: chain verifies; CHANGELOG entry committed.

## 7. Definition of Done

Measurable acceptance criteria for the entire migration:

- **Volume target**: framework-events.ndjson contains ≤ 150 lines after a typical working day (down from 1,335 — a ~89% reduction). Numeric target itself is OD-013.
- **No polling emitters**: zero unconditional emit sites remain. Every emit is either change-driven, failure-driven, sampled with a configured rate, or carries an explicit per-emit relevance claim.
- **Single source of truth for kinds**: only one authoritative `ALLOWED_EVENT_KINDS` exists; the other two sites are import-only.
- **Mechanism documented**: relevance mechanism is captured in the manifest (if config-driven) and in `docs/event-relevance.md`.
- **Schema migration clean**: `schemaVersion` bumped; all events post-migration carry the new shape.
- **Audit chain integrity preserved**: `ai-eng audit verify` green; `prev_event_hash` chain unbroken.
- **Consumers updated**: `audit index`, `query`, `tokens`, `replay`, `otel-export` all green against the new schema.
- **Tests green**: the 18 enumerated tests rewritten; new tests added for the relevance contract; `pytest` green.
- **CHANGELOG entry**: documents the breakage explicitly per CONSTITUTION.md §3.
- **Hot-path budget preserved**: pre-commit < 1s, pre-push < 5s (CLAUDE.md "Hot-Path Discipline"). The new relevance gate cannot regress these budgets.

## 8. Quality Stamps

Principles applied (every claim in the spec phase must cite at least one):

- **§10.1 KISS** — Fewer kinds, fewer rows, one contract surface, one writer pair.
- **§10.2 YAGNI** — Don't emit if no consumer needs it. Two emit sites (`spec_verified`, `install_simulate_hook`) together produce 92% of the log and serve no documented consumer.
- **§10.5 TDD** — Every consumer assertion (token rollups, span tree, OTLP export) stays green after the migration; new tests for the relevance contract precede emitter changes.
- **§10.6 SDD** — This brief precedes the spec. Spec precedes plan. Plan precedes build.
- **§10.7 Clean Code** — Relevance is a first-class precondition for emission, not an afterthought.

Contracts honoured:

- **CONSTITUTION.md §3** — Hard rename / hard migration. No backwards-compat shim for retired kinds. CHANGELOG documents the breakage.
- **CONSTITUTION.md §13.5** — Single-round fail-loud quality loop. The migration ships in a single PR with all consumers and tests updated.
- **CLAUDE.md Hot-Path Discipline** — Pre-commit < 1s, pre-push < 5s.
- **CLAUDE.md §13 Hard Rules** — No suppression (`# noqa`, `# nosec`, etc.). No backwards-compat shims.

## 9. Open Decisions

The spec phase must resolve these. The brief enumerates options drawn from external prior art (§12) and from the codebase.

### OD-001: Relevance mechanism — central choice

The mechanism is the single largest decision. Options (any combination is admissible):

| ID | Pattern | Where filter happens | Prior art |
| --- | --- | --- | --- |
| OD-001-a | Emitter-side allow-list registry | emit time | Prometheus naming, OTel-semconv |
| OD-001-b | Per-emit justification linter / CI gate | emit time + CI | Falco rules-registry |
| OD-001-c | Severity-tier vocabulary with read-time filter | read time | OTel `SeverityNumber`, RFC 5424 |
| OD-001-d | Tail-sampling at consumer | consumer | OTel tail sampling |
| OD-001-e | Wide-event single-source-of-truth (fewer kinds, denser context) | emit time | Honeycomb, Observability 2.0 |
| OD-001-f | Policy-driven quota / retention with TTL | pipeline | Datadog Observability Pipelines |
| OD-001-g | Programmatic `before_send` hook | emit time | Sentry SDK |
| OD-001-h | Default-deny payload, opt-in expand | emit time | Claude Code `OTEL_LOG_TOOL_CONTENT` |

### OD-002: Severity vocabulary (if OD-001-c chosen or hybrid)

- RFC 5424 (8 levels: Emergency..Debug)?
- OTel `SeverityNumber` (24 levels: TRACE1..FATAL4)?
- Custom S0..S3 (Anthropic-friendly compactness)?

### OD-003: Where the relevance policy lives

- `.ai-engineering/manifest.yml` under a new `audit_policy:` key?
- A separate `.ai-engineering/audit-policy.yml` file?
- In-code as an immutable constant in `tools/skill_domain/event_schema.py`?

### OD-004: Failure-emission asymmetry

When the normal-success row is filtered, must the failure row always emit? Concrete example: should `spec_verified` with `drift_detected=true` always emit even if normal `spec_verified` is dropped? This is a "fail-open emission" policy decision.

### OD-005: Unifying observation-events.ndjson with framework-events.ndjson

Today the instinct layer maintains its own schema and sliding window ([.ai-engineering/scripts/hooks/_lib/instincts.py:822](.ai-engineering/scripts/hooks/_lib/instincts.py:822)). Should the relevance contract unify the two streams (one canonical writer, one schema, two sinks via filtering) or preserve the bifurcation?

### OD-006: Lock-failure sidecar shape

`lock-failures.ndjson` uses yet a third schema ([.ai-engineering/scripts/hooks/_lib/locked_append.py:73](.ai-engineering/scripts/hooks/_lib/locked_append.py:73)) and is not in the hash chain. Bring it under the relevance contract? Or accept that lock failures are an exceptional path with its own discipline?

### OD-007: Telemetry-debug.log fate

[.ai-engineering/state/telemetry-debug.log](.ai-engineering/state/telemetry-debug.log) has no reader anywhere in the codebase. Retire entirely or rationalise into the new contract?

### OD-008: Sampling rate for retained-but-rare kinds

If sampling lands (OD-001-d), what rate per kind? The policy-decision sampler is hardcoded at 10% allow-sample today ([src/ai_engineering/governance/decision_log.py:56](src/ai_engineering/governance/decision_log.py:56)). Per-kind configurable? Manifest-driven?

### OD-009: Historical event readability

Audit chain pre-migration uses the old shape. `audit index` must keep reading historical events. Options: dual-shape reader (forward-compat), one-time rewrite of historical NDJSON, or schema-version-aware reader.

### OD-010: Numeric volume target

§7 names ≤ 150 lines/day as a placeholder. Is the right target ≤ 50? ≤ 200? Per-session rather than per-day? Per-component budgets?

### OD-011: CI guard for new emit sites

Should a new emit site be rejected by CI unless its relevance claim is registered in the policy file? Concretely: a pre-commit hook that greps for new `emit_framework_event(` calls in a diff and requires a paired policy entry.

### OD-012: Decision row promotion

`state.db decisions` table is empty today. Should this migration also bootstrap the table with the relevant historical decisions (D-110-03 audit chain, D-122-23 hook integrity, D-127-10 framework events) so future relevance audits have a queryable record?

### OD-013: Manifest-driven runtime override

Should operators be able to override the policy at runtime via `AIENG_AUDIT_POLICY_PATH` (env var), or is the manifest the only knob?

## 10. Migration

Per CONSTITUTION.md §3 — hard rename, hard migration.

### Strategy

- **One PR carries the whole migration**: schema, emitters, consumers, tests, manifest, docs, CHANGELOG. No coexistence window. No deprecation shim.
- **Historical readability via reader, not writer**: `ai-eng audit index` is updated to handle both pre-migration and post-migration event shapes when projecting NDJSON into SQLite. The writer only emits the new shape. (Or — OD-009 alternative — one-time rewrite of historical NDJSON.)
- **Three frozensets collapse to one**: [tools/skill_domain/event_schema.py:37](tools/skill_domain/event_schema.py:37) becomes the sole authority. The other two sites import directly. A new test asserts they cannot drift.
- **Retired kinds**: any kind that no longer survives the relevance contract is removed from `ALLOWED_EVENT_KINDS`. Tests that assert against retired kinds are rewritten in the same commit. CHANGELOG enumerates retired kinds explicitly.
- **`schemaVersion` bump**: the canonical schema version is incremented so `audit index` can distinguish pre/post-migration events.
- **Hash chain preserved**: the migration does NOT alter historical NDJSON lines. The chain remains verifiable end-to-end.

### Cut-over

1. Land the schema change first (one commit).
2. Update emitters (one commit per logical group: CLI, installer, hooks, governance).
3. Update consumers (one commit).
4. Update tests (one commit).
5. Update manifest + docs + CHANGELOG (one commit).
6. Run `ai-eng audit verify` and `pytest` green at the end of every commit.

If the spec phase chooses a single-PR delivery instead of staged commits, all five concerns ship together. The choice is part of `/ai-plan`, not this brief.

### What does NOT get a shim

- No `compat_emit_framework_event(...)` that translates old kinds to new.
- No "deprecated kind" warning that still writes a row.
- No environment variable that re-enables retired kinds.
- No silent fallback if the relevance policy file is missing — fail loud at startup.

## 11. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| R1 | Over-aggressive trimming loses debugging insight (a kind we retire turns out to matter) | Medium | High | Two-week observation window with full-fidelity logging in a parallel debug sink (out of hash chain) before final cut; OD-004 fail-open emission for failures. |
| R2 | Audit chain integrity breaks during migration cut | Low | Critical | M7 verification gate; chain is append-only — migration only changes what is written after the cut, not what was written before. |
| R3 | Three-frozenset drift persists if collapse isn't done atomically | Medium | Medium | M2 ships the collapse in a single commit; CI test asserts the three sites are import-only. |
| R4 | Consumer regression in `audit replay` / `otel-export` (silent drop of rollup rows for retired kinds) | High | Medium | M4 consumer tests run against both pre- and post-migration fixtures; rollup view regeneration is part of acceptance. |
| R5 | In-flight NDJSON has mixed-shape rows during migration commits | Low | Low | Reader handles both shapes (OD-009-a); writer only emits the new shape after the schema commit; chain remains verifiable. |
| R6 | Anthropic SDK / Claude Code conventions evolve, our policy drifts | Medium | Low | Policy lives in manifest, not code; revisions are config-only; brief explicitly tracks Anthropic-side conventions in §12. |
| R7 | Hot-path budget regresses if relevance gate is heavy | Low | High | Relevance gate is pure-Python dict lookup (whitelist) or simple int comparison (tier); CI hot-path benchmark enforces < 1s pre-commit, < 5s pre-push (CLAUDE.md). |
| R8 | Test rewrites miss an assertion that locks a retired kind | Medium | Medium | M5 exhaustive grep for retired kind strings; full test suite gate before merge. |
| R9 | Operators bypass the policy via env var or local-only override | Low | Medium | If runtime override exists (OD-013), it is logged as a separate `policy_decision` event so the override itself is auditable. |
| R10 | Future-self adds a polling emitter that violates the contract | High | Medium | OD-011 CI guard rejects new `emit_*` calls without a paired policy entry. |

## 12. References

### External — signal vs noise discipline

- Google SRE Book, Ch. 6 "Monitoring Distributed Systems" — symptom vs cause; "maximum signal, minimum noise"; alerts must be actionable. https://sre.google/sre-book/monitoring-distributed-systems/ (2016).
- OpenTelemetry "Sampling" concept docs — head vs tail sampling. https://opentelemetry.io/docs/concepts/sampling/ (current).
- Honeycomb, "What Is Observability Engineering?" — wide events with arbitrary cardinality, filter at read time. https://www.honeycomb.io/resources/getting-started/what-is-observability-engineering (current).
- AWS Well-Architected, OPS04-BP01 "Implement application telemetry" — telemetry must be designed for an investigative use case. https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_telemetry_application_telemetry.html (current).

### External — whitelist / blacklist at the emitter

- OpenTelemetry Semantic Conventions, "Naming" — namespaced authoritative registry; custom keys must use reverse-domain prefix. https://opentelemetry.io/docs/specs/semconv/general/naming/ (semconv 1.41.0).
- Prometheus "Metric and label naming" — high-cardinality data "belongs in logs and traces, not metrics". https://prometheus.io/docs/practices/naming/ (current).
- Falco "Default Rules" — 93 named rules + explicit exception allow-lists. https://falco.org/docs/reference/rules/default-rules/ (Falco 0.x).
- Sentry SDK `before_send` / `beforeSend` — last-chance programmatic suppression. https://docs.sentry.io/platforms/python/configuration/filtering/ (current).

### External — severity / signal tier

- OpenTelemetry Logs Data Model — `SeverityNumber`; 24 levels TRACE..FATAL; filter at emit, pipeline, or read. https://opentelemetry.io/docs/specs/otel/logs/data-model/ (spec v1.53.0).
- RFC 5424 (The Syslog Protocol), §6.2.1 — eight severities 0-7. https://www.rfc-editor.org/rfc/rfc5424 (2009).
- Dash0, "Log Levels Explained: A Better Strategy with OpenTelemetry" — critique of inconsistent log levels; OTel `SeverityNumber` as the fix. https://www.dash0.com/knowledge/log-levels (2025).
- Uber `zap` / Go `log/slog` — leveled structured loggers; `IncreaseLevel` and atomic level config for emit-time filter. https://pkg.go.dev/go.uber.org/zap (current).

### External — Anthropic-side conventions

- Claude Code "Monitoring usage" docs — tool input/output content NOT logged by default; opt-in via `OTEL_LOG_TOOL_CONTENT=1`, truncated at 60 KB/span. Default-deny posture on verbose payloads. https://docs.anthropic.com/en/docs/claude-code/monitoring-usage (current).
- Anthropic Engineering, "Equipping agents for the real world with Agent Skills" — describes Skills as dynamically loaded folders; no explicit telemetry guidance for skill events. https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills (2025).
- GitHub issue anthropics/claude-code#35319 — community proposal for `Skill:<name>` namespacing in session telemetry; feature request, not shipped convention. https://github.com/anthropics/claude-code/issues/35319 (2025).
- No public Anthropic guidance found on heartbeat suppression, signal-tier vocabulary, or "what counts as a justified emit" inside a skill. `[unsourced]`.

### External — "less but signal-rich"

- Charity Majors, "There Is Only One Key Difference Between Observability 1.0 and 2.0" — 1.0 = many sources of truth, pre-aggregated; 2.0 = one wide-event source, derive at read time. https://charity.wtf/2024/11/19/there-is-only-one-key-difference-between-observability-1-0-and-2-0/ (Nov 2024).
- Datadog Observability Pipelines, "Strategies for Reducing Log Volume" — drop, sample, quota, archive at the pipeline. https://docs.datadoghq.com/observability_pipelines/guide/strategies_for_reducing_log_volume/ (current).
- OpenTelemetry blog, "AI Agent Observability — Evolving Standards and Best Practices" — standardised agent telemetry shape to avoid "hundreds of events per interaction". https://opentelemetry.io/blog/2025/ai-agent-observability/ (2025).
- Cindy Sridharan, "Monitoring and Observability" — non-actionable telemetry is noise by definition. https://copyconstruct.medium.com/monitoring-and-observability-8417d1952e1c (2017).

### Internal — repository

- [CONSTITUTION.md](CONSTITUTION.md) §3 (hard migration, no backwards-compat shim), §13.5 (single-round fail-loud).
- [CLAUDE.md](CLAUDE.md) — Hot-Path Discipline, Hard Rules §13.
- [docs/principles.md](docs/principles.md) — §10.1 KISS, §10.2 YAGNI, §10.5 TDD, §10.6 SDD, §10.7 Clean Code anchors.
- Prior specs that shaped the audit pipeline: spec-107 (event plane), spec-110 (hash chain — D-110-03 root-stamping), spec-112 (audit index), spec-118 (replay), spec-119 (OTLP export), spec-120 (audit observability), spec-122 (hooks integrity — D-122-23, D-122-27), spec-123 (consent), spec-126 (sidecars), spec-127 (framework events — D-127-10, D-127-11), spec-131 (canonical chain — D-131-07, D-131-08).

## 13. Glossary

- **Audit chain** — Append-only NDJSON sequence with `prev_event_hash` linkage; tamper-evident.
- **Emit site** — Code location that writes to an event sink. Today there are ~30 active emit sites enumerated in §5.
- **Hash chain** — `prev_event_hash` field on each event, computed over the canonical-form bytes of the previous event. Detects tampering.
- **Heartbeat** — Unconditional periodic emission that carries no new state-change information. `spec_verified` and `install_simulate_hook` are today's heartbeats.
- **Hot path** — Code path executed on every interactive operation. Pre-commit (< 1s budget) and pre-push (< 5s budget) per CLAUDE.md.
- **Kind** — Top-level discriminator string on a framework event. 11 declared, 3 actively emitted in the snapshot.
- **Outcome** — Current-state quality hint on each event (`success` / `failure` / `degraded` / `warn` / `allow` / `blocked`). Not a relevance signal.
- **Polling-style emission** — Emit-per-poll rather than emit-per-state-change. The dominant anti-pattern today.
- **Relevance** — Proposed first-class precondition for emission. Mechanism TBD (OD-001).
- **Relevance claim** — The caller's assertion that an emission is justified. Shape depends on the mechanism (kind whitelist membership, severity tier, justification string, etc.).
- **Severity tier** — Proposed signal grade. Vocabulary is OD-002.
- **Sidecar** — Auxiliary file for an oversized payload. `runtime/event-sidecars/<sha256>.json`.
- **Signal** — An emission whose absence would change a reader's behavior.
- **Signal density** — Information per row. Inversely proportional to heartbeat-share.
- **Sink** — Destination file or table that receives an emission. Enumerated in §2 and §5.
- **State-change emission** — Emit-only-when-something-changes. `retention_applied`, `instinct-extract`, `migration_integrity_check` are today's good shapes.
- **Wide event** — Honeycomb / Observability 2.0 pattern: fewer kinds, each carrying dense context, filter at read time.

## 14. Acceptance

Checklist mirroring §7 — every box must be ticked before the spec phase declares the migration complete.

- [ ] Relevance mechanism chosen and persisted in `state.db decisions` (M1).
- [ ] `schemaVersion` bumped; `ALLOWED_EVENT_KINDS` re-derived; the three frozensets collapse to a single import-only source (M2).
- [ ] CI test asserts the three frozenset sites cannot drift (M2).
- [ ] Every emit site enumerated in §5 has been audited: kept, dropped, or refactored to emit-on-change (M3).
- [ ] `spec_verified` and `install_simulate_hook` no longer fire unconditionally (M3).
- [ ] `ai-eng audit index`, `query`, `tokens`, `replay`, `otel-export` all green against the new schema (M4).
- [ ] Instinct extractor updated to the new kind set (M4).
- [ ] The 18 enumerated tests rewritten; new tests added for the relevance contract (M5).
- [ ] Manifest carries the new `audit_policy:` key (if config-driven) (M6).
- [ ] `docs/event-relevance.md` (or equivalent) documents the contract (M6).
- [ ] `ai-eng audit verify` green; `prev_event_hash` chain unbroken (M7).
- [ ] CHANGELOG entry committed, documenting retired kinds and the new shape (M7).
- [ ] After a typical working-day session, framework-events.ndjson contains ≤ 150 lines (volume target — exact number is OD-013).
- [ ] Pre-commit < 1s, pre-push < 5s benchmarks pass (hot-path budget preserved).
- [ ] No `# noqa`, `# nosec`, or other suppression added during the migration (CONSTITUTION.md §13.2).
- [ ] No backwards-compat shim for retired kinds (CONSTITUTION.md §3).

---

**Handoff**: this brief is the contract for `/ai-brainstorm`. Resolve OD-001..OD-013, write the approved spec to `.ai-engineering/specs/spec.md`, and record the mechanism decision in `state.db decisions`. The build phase consumes the spec; this brief does not propose code.
