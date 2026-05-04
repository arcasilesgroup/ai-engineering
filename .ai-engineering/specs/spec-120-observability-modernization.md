# Spec 120 — Observability Layer Modernization

**Status**: Draft → Approved (autonomous)
**Owner**: framework
**Date**: 2026-05-04
**Predecessors**: spec-082 (canonical observability), spec-110/112 (audit chain + schema), spec-116 (runtime), spec-118 (memory), spec-119 (eval)
**Branch**: feat/spec-120-observability-modernization (cut from current feat/knowledge-placement-governance-cleanup)

---

## 1. Problem

The framework writes NDJSON events to `.ai-engineering/state/framework-events.ndjson`
and hash-chains them (`prev_event_hash`) for tamper-evident audit. That covers
**audit** but not **debugging**.

Five concrete gaps surfaced from the harness-engineering deep analysis:

1. **No OTel GenAI semantic conventions** — events use ad-hoc `kind` and
   `detail` fields with no portable mapping to `gen_ai.system`,
   `gen_ai.request.model`, `gen_ai.usage.input_tokens`,
   `gen_ai.usage.output_tokens`, etc. Cannot ship traces to any standard
   observability backend (Langfuse, Phoenix, Logfire, OTel collector).
2. **No SQL over traces** — debugging today is `grep` over a 27 MB NDJSON
   file. No `WHERE`, `GROUP BY`, `JOIN`, time filters. Token spend and
   failure rate per skill cannot be answered without writing throwaway
   Python.
3. **No session replay** — when something goes wrong mid-session, there
   is no way to walk back through tool calls, prompts, and outcomes in
   order. Nothing renders the chain as a sequence of steps.
4. **No nested causality** — events have one parent pointer:
   `prev_event_hash` (linear list across the whole stream). They do not
   carry a *logical* parent (e.g. "this `task_trace` was caused by that
   `agent_dispatched`"). Failure-attribution requires reconstructing the
   tree manually from `correlationId` and timestamps.
5. **No token attribution** — schema reserves `tokens_in`, `tokens_out`,
   `estimated_cost_usd` (per `audit-event.schema.json` `tokenFields`),
   but the emit helpers don't surface them and no roll-up exists per
   turn / skill / agent / session.

## 2. Goals (in scope)

- Add OTel GenAI conventions to `framework-events.ndjson` as an optional
  `genai` block in `detail` plus root-level `traceId` / `spanId` /
  `parentSpanId`. Ship a small adapter that exports a session as
  OTel-compatible JSON spans.
- Build a SQLite projection of the NDJSON stream (`ai_engineering audit
  index`) and a query CLI (`ai_engineering audit query "SELECT ..."`).
  Idempotent and re-runnable; SQLite is rebuilt from NDJSON on demand.
- Implement a terminal-based session replay (`ai_engineering audit
  replay --session <id>`) that walks the event tree in order. HTML is
  out of scope (Q3 in the broader roadmap); we ship a JSON dump that a
  future UI can consume.
- Add `parentSpanId` (logical) alongside `prev_event_hash` (chain).
  Span tree per `traceId`. Emit helpers accept `parent_span_id`.
- Add `usage` block (input/output/total tokens, cost USD, model,
  provider) to skill_invoked / agent_dispatched / task_trace events.
  Roll-ups via the SQLite projection.

## 3. Non-goals

- Self-hosted Langfuse / Phoenix / Logfire deployment. We emit
  OTel-compatible JSON; deployment is the user's choice.
- Real-time streaming export. Batch-only export of a session.
- HTML / web UI (`ai_engineering audit replay --html`). Out of scope —
  text replay + JSON dump is enough for v1.
- Backfilling 27 MB of historical events with `traceId` / `parentSpanId`
  (additive forward-only; existing events keep working).
- Replacing the existing audit chain. `prev_event_hash` stays as the
  tamper-evident chain; `parentSpanId` is additive logical causality.

## 4. Architecture

### 4.1 Event schema additions (additive, backward compatible)

Optional fields at the root of every event:

```jsonc
{
  "traceId": "<32-hex>",         // root identifier per logical run
  "spanId":  "<16-hex>",         // unique per event
  "parentSpanId": "<16-hex>"     // logical parent (null at root)
}
```

Optional `genai` block under `detail` for events that involve an LLM
call (skill_invoked, agent_dispatched, task_trace):

```jsonc
"detail": {
  "...existing fields...": "...",
  "genai": {
    "system":            "anthropic",       // gen_ai.system
    "request": {
      "model":  "claude-sonnet-4-5"         // gen_ai.request.model
    },
    "usage": {
      "input_tokens":  1234,                // gen_ai.usage.input_tokens
      "output_tokens": 567,                 // gen_ai.usage.output_tokens
      "total_tokens":  1801,
      "cost_usd":      0.0143
    }
  }
}
```

Schema names mirror OTel GenAI semantic conventions but stay in nested
JSON (NDJSON) — the OTel exporter (§4.5) flattens them to dotted keys
on export.

### 4.2 Hash chain stays linear; causality goes parallel

- `prev_event_hash` (existing) — per-line linear chain across the entire
  NDJSON file. Tamper-evident audit. Unchanged.
- `parentSpanId` (new) — points to the `spanId` of the logical parent.
  Forms a per-`traceId` tree. Used for replay and failure attribution.

These are two independent integrity layers and serve different
purposes. We do **not** introduce `parent_event_hash` as a new
sibling — `prev_event_hash` already exists and re-using the term would
collide. Instead we use OTel's standard `parentSpanId`.

### 4.3 SQLite projection

A new module `src/ai_engineering/state/audit_index.py` reads
`framework-events.ndjson` and rebuilds (or incrementally updates) a
SQLite database at `.ai-engineering/state/audit-index.sqlite`.

Tables:

```sql
CREATE TABLE events (
  span_id            TEXT PRIMARY KEY,
  trace_id           TEXT,
  parent_span_id     TEXT,
  correlation_id     TEXT NOT NULL,
  session_id         TEXT,
  timestamp          TEXT NOT NULL,
  ts_unix_ms         INTEGER NOT NULL,
  engine             TEXT NOT NULL,
  kind               TEXT NOT NULL,
  component          TEXT NOT NULL,
  outcome            TEXT NOT NULL,
  source             TEXT,
  prev_event_hash    TEXT,
  -- gen_ai surface (NULL when event has no LLM call)
  genai_system       TEXT,
  genai_model        TEXT,
  input_tokens       INTEGER,
  output_tokens      INTEGER,
  total_tokens       INTEGER,
  cost_usd           REAL,
  -- raw blob for ad-hoc detail queries
  detail_json        TEXT NOT NULL
);

CREATE INDEX idx_events_trace      ON events(trace_id);
CREATE INDEX idx_events_session    ON events(session_id);
CREATE INDEX idx_events_kind       ON events(kind);
CREATE INDEX idx_events_component  ON events(component);
CREATE INDEX idx_events_ts         ON events(ts_unix_ms);

CREATE TABLE indexed_lines (
  -- byte offset of the last NDJSON line indexed; used for incremental
  -- re-indexing without re-parsing the whole file
  last_offset INTEGER PRIMARY KEY,
  last_hash   TEXT,
  indexed_at  TEXT
);

CREATE VIEW skill_token_rollup AS
  SELECT json_extract(detail_json, '$.skill') AS skill,
         COUNT(*)              AS invocations,
         SUM(input_tokens)     AS input_tokens,
         SUM(output_tokens)    AS output_tokens,
         SUM(total_tokens)     AS total_tokens,
         SUM(cost_usd)         AS cost_usd
    FROM events
   WHERE kind = 'skill_invoked'
   GROUP BY skill;

CREATE VIEW agent_token_rollup AS
  SELECT json_extract(detail_json, '$.agent') AS agent,
         COUNT(*)              AS dispatches,
         SUM(input_tokens)     AS input_tokens,
         SUM(output_tokens)    AS output_tokens,
         SUM(total_tokens)     AS total_tokens,
         SUM(cost_usd)         AS cost_usd
    FROM events
   WHERE kind = 'agent_dispatched'
   GROUP BY agent;

CREATE VIEW session_token_rollup AS
  SELECT session_id,
         MIN(timestamp)        AS started_at,
         MAX(timestamp)        AS ended_at,
         COUNT(*)              AS events,
         SUM(input_tokens)     AS input_tokens,
         SUM(output_tokens)    AS output_tokens,
         SUM(total_tokens)     AS total_tokens,
         SUM(cost_usd)         AS cost_usd
    FROM events
   WHERE session_id IS NOT NULL
   GROUP BY session_id;
```

The index is a **derived artifact** — gitignored, rebuildable from
NDJSON. Never the source of truth.

### 4.4 Replay

`ai_engineering audit replay --session <id>` (or `--trace <id>`):

1. Load events from SQLite index (auto-build if stale).
2. Build span tree from `parentSpanId`.
3. Walk depth-first, indented by depth, colorized by outcome.
4. Show: `timestamp · kind · component · outcome · summary`.
5. Token rollup at the end.
6. `--json` flag emits a JSON dump of the tree (consumable by future
   HTML viewer; out of scope for v1).

### 4.5 OTel export

`ai_engineering audit otel-export --trace <id> [--out path.json]`:

Translates the tree into OTel JSON spans format. One span per event.
Field mapping:

| NDJSON                          | OTel                              |
|---------------------------------|-----------------------------------|
| `traceId`                       | `traceId` (32-hex)                |
| `spanId`                        | `spanId` (16-hex)                 |
| `parentSpanId`                  | `parentSpanId`                    |
| `timestamp`                     | `startTimeUnixNano`               |
| `kind`                          | `name`                            |
| `component`                     | `attributes["component"]`         |
| `detail.genai.system`           | `attributes["gen_ai.system"]`     |
| `detail.genai.request.model`    | `attributes["gen_ai.request.model"]` |
| `detail.genai.usage.input_tokens`  | `attributes["gen_ai.usage.input_tokens"]`  |
| `detail.genai.usage.output_tokens` | `attributes["gen_ai.usage.output_tokens"]` |
| `outcome=failure`               | `status.code = ERROR`             |

This produces an OTLP/JSON file the user can pipe to any OTel
collector — Langfuse, Phoenix, Logfire, Tempo, Honeycomb, etc.

### 4.6 Hook layer plumbing

`_lib/observability.py` (hook-side) and
`src/ai_engineering/state/observability.py` (pkg-side) gain:

- `build_framework_event(..., trace_id=..., span_id=...,
  parent_span_id=..., usage=...)` — additive kwargs, optional.
- A new helper `current_trace_context(project_root) -> (trace_id,
  parent_span_id)` that looks up the active context from
  `.ai-engineering/state/runtime/trace-context.json` (written by the
  `SessionStart` hook, updated by each emit).
- `emit_skill_invoked(...)` and `emit_agent_dispatched(...)` accept
  `usage: dict | None` and parent span; they auto-generate `spanId`
  and inherit `traceId` from current context if not supplied.

### 4.7 Trace context lifecycle

- **Session start**: `runtime-stop.py` writes `trace-context.json`
  with a fresh `traceId`. Wait — that's stop. We add a small
  `SessionStart`-equivalent that runs first; if absent (Codex,
  Gemini), the first emit auto-creates the file.
- **Per emit**: `spanId` = uuid4 hex (16 chars). `parentSpanId` =
  whatever was current. Push current `spanId` onto a stack inside
  `trace-context.json` for nested calls (e.g. agent_dispatched → child
  skill_invoked).
- **Session end**: pop / clear.

The trace-context file is local-only (under `runtime/`, gitignored)
and tolerant of corruption (best-effort fall back to a fresh
`traceId`).

## 5. Detailed task breakdown

### Phase A — Schema + emit plumbing

- **A1**: Add `traceId`, `spanId`, `parentSpanId` to event_schema
  (TypedDict + validator). Optional, additive.
- **A2**: Update `audit-event.schema.json` to allow optional
  `traceId` / `spanId` / `parentSpanId` at root and `genai` block under
  `detail.*`.
- **A3**: Extend `build_framework_event` (both pkg + `_lib`) to accept
  `trace_id`, `span_id`, `parent_span_id`, `usage`. Auto-generate
  `spanId` if missing.
- **A4**: Implement `trace_context.py` (read/write
  `runtime/trace-context.json`, push/pop span stack).
- **A5**: Wire `emit_skill_invoked` and `emit_agent_dispatched` to
  consume trace context + `usage`.

### Phase B — SQLite projection

- **B1**: `audit_index.py` — read NDJSON, write SQLite. Schema as in
  §4.3. Idempotent + incremental (`indexed_lines.last_offset`).
- **B2**: CLI `ai_engineering audit index` (force / incremental).
- **B3**: CLI `ai_engineering audit query "SELECT ..."` — read-only
  SQLite, print rows tabular or `--json`.
- **B4**: Token rollup CLI shorthand: `ai_engineering audit tokens
  --by skill|agent|session`.

### Phase C — Replay + OTel export

- **C1**: `audit_replay.py` — span tree builder + DFS walk +
  text/JSON renderer.
- **C2**: CLI `ai_engineering audit replay --session <id>` /
  `--trace <id>` / `--json`.
- **C3**: `audit_otel_export.py` — OTLP JSON spans builder.
- **C4**: CLI `ai_engineering audit otel-export --trace <id>`.

### Phase D — Tests + docs

- **D1**: Unit tests for trace-context, audit_index, audit_replay,
  audit_otel_export (≥ 90 % line coverage; all new modules).
- **D2**: Integration test: emit a synthetic session, run index,
  query, replay, otel-export. Assert end-to-end.
- **D3**: Update `AGENTS.md`, `CLAUDE.md`, and `.ai-engineering/docs/`
  with the new CLI commands and `genai` field.

### Phase E — Wiring

- **E1**: Update `runtime-stop.py` to write a session-end token
  rollup event sourced from the SQLite index.
- **E2**: Add `agent_dispatched` and `skill_invoked` `usage` capture
  at the dispatcher (best-effort — only when the IDE provides token
  counts; otherwise the field is absent).
- **E3**: Hooks manifest regen (`regenerate-hooks-manifest.py`).

## 6. Acceptance criteria

1. `ai_engineering audit index` builds a SQLite database from the
   existing 27 MB NDJSON without errors.
2. `ai_engineering audit query "SELECT kind, COUNT(*) FROM events
   GROUP BY kind"` returns counts.
3. `ai_engineering audit tokens --by skill` returns a non-empty table
   after a session that invoked at least one skill with `usage`.
4. `ai_engineering audit replay --session <id>` walks events in
   parent-child order and prints them indented.
5. `ai_engineering audit otel-export --trace <id> --out spans.json`
   produces valid OTLP JSON (smoke-validated against the OTel
   schema — fields present, types correct).
6. All existing tests pass (no regression in audit chain or hook
   paths).
7. Hooks manifest is regenerated and committed.
8. Spec-104 / spec-110 audit-chain integrity tests still pass —
   `prev_event_hash` is unaffected.

## 7. Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Existing 27 MB NDJSON has no `traceId` / `spanId` — index would write NULLs | Index treats them as nullable; queries on legacy events still work, just with NULL trace info. Forward-only enrichment. |
| Trace-context file corruption mid-session loses parent linkage | Best-effort fall back: missing context yields a fresh `traceId` and `parentSpanId = NULL`. Logged as `framework_error` with `error_code = trace_context_corrupted`. |
| SQLite projection drifts from NDJSON if hand-edited | Index is rebuildable; `--rebuild` flag drops the table and re-reads from offset 0. |
| OTel field naming changes upstream | We document the snapshot of the spec we mirror (OTel GenAI v1.27.0). Migration is a future spec. |
| Token attribution needs IDE cooperation | Documented as best-effort; missing `usage` is not an error. The schema reserves the slot today (per `audit-event.schema.json` `tokenFields`); we just plumb through what we have. |

## 8. Out of scope (deferred to future specs)

- Real-time streaming OTel exporter daemon.
- HTML session replay viewer.
- Cross-session analytics (`ai_engineering audit cohort ...`).
- Cost-optimization recommender.
- Automatic OTel collector deployment.
- Backfill of `traceId` / `spanId` into existing NDJSON.

## 9. Approval

Approved autonomously per user instruction (2026-05-04 22:xx, "tienes
todo el poder y permisos … hasta el final"). Spec → /ai-plan → /ai-dispatch
→ /ai-commit → summary.
