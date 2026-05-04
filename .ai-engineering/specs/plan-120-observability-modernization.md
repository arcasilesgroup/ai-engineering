# Plan: spec-120 Observability Layer Modernization

## Pipeline: full
## Phases: 5
## Tasks: 22 (build: 17, verify: 4, guard: 1)

## Architecture

modular-monolith (additive)

spec-120 adds three new modules under `src/ai_engineering/state/` (`trace_context.py`, `audit_index.py`, `audit_replay.py`, `audit_otel_export.py`) and four new Typer subcommands under the existing `audit_app` namespace (`index`, `query`, `tokens`, `replay`, `otel-export`). Wire-format changes are strictly additive at root (`traceId`, `spanId`, `parentSpanId`) and under `detail.genai.*`. The hash chain (`prev_event_hash`) is **not** modified — the new logical-causality field (`parentSpanId`) lives alongside it without touching the canonical-JSON inputs to `compute_entry_hash`. SQLite projection is a derived artifact (gitignored, rebuildable). The OTel exporter is a pure function over the indexed tree; it ships JSON, no daemon.

### Phase A: Schema + emit plumbing
**Gate**: `traceId` / `spanId` / `parentSpanId` validated as optional at schema and validator level; `genai` block accepted under `detail.*` for `skill_invoked`, `agent_dispatched`, `task_trace`; trace-context lifecycle (read/write/push/pop) implemented in stdlib-only form mirrored on both pkg and `_lib` sides; emit helpers accept the new kwargs without breaking existing callers; the audit-chain hash on a sample event with full trace context is identical when the trace fields are stripped (proves they are additive and inert to hashing semantics from the consumer perspective; `compute_entry_hash` itself does not exclude them, so the chain naturally absorbs the new fields without code change).

- [ ] T-A1: Extend `src/ai_engineering/state/event_schema.py` `FrameworkEvent` TypedDict with optional `traceId: str`, `spanId: str`, `parentSpanId: str | None`; extend `validate_event_schema` to accept-when-present (must match `^[0-9a-f]{32}$` for `traceId`, `^[0-9a-f]{16}$` for `spanId` / `parentSpanId`) and reject malformed values fail-closed (agent: build).
- [ ] T-A2: Extend `.ai-engineering/schemas/audit-event.schema.json` — add `traceId` / `spanId` / `parentSpanId` optional root properties with regex patterns matching T-A1; add `$defs/genai_block` with `system`, `request.model`, `usage.{input_tokens,output_tokens,total_tokens,cost_usd}`, `provider` (all optional inside the block); reference the block as an optional property under `detail` for `detail_skill_invoked`, `detail_agent_dispatched`, and `detail_task_trace` discriminator branches; flip `additionalProperties: false` to `true` only on those three branches OR add `genai` to their explicit property list (prefer the explicit list to keep the surface honest) (agent: build, blocked by T-A1).
- [ ] T-A3: Implement `src/ai_engineering/state/trace_context.py` — module functions `read_trace_context(project_root) -> dict | None`, `write_trace_context(project_root, ctx)`, `push_span(project_root, span_id) -> str`, `pop_span(project_root)`, `current_trace_context(project_root) -> tuple[trace_id, parent_span_id]`, `new_span_id() -> str` (16-hex), `new_trace_id() -> str` (32-hex). State file: `.ai-engineering/state/runtime/trace-context.json` (gitignored, local-only). Tolerate corruption: on parse failure, log a `framework_error` of `error_code = trace_context_corrupted` and return a fresh trace_id with NULL parent (agent: build, blocked by T-A2).
- [ ] T-A4: Mirror a stdlib-only equivalent of `trace_context.py` into `.ai-engineering/scripts/hooks/_lib/trace_context.py` — zero imports from `ai_engineering.*`, identical wire output (UUID4 hex, sort_keys=True), so hooks can run pre-pip-install (agent: build, blocked by T-A3).
- [ ] T-A5: Extend `build_framework_event` in both `src/ai_engineering/state/observability.py` AND `.ai-engineering/scripts/hooks/_lib/observability.py` with optional kwargs `trace_id: str | None = None`, `span_id: str | None = None`, `parent_span_id: str | None = None`, `usage: dict | None = None`. Auto-generate `spanId` if omitted via `new_span_id()`. Auto-inherit `traceId` and `parentSpanId` from `current_trace_context(project_root)` if not supplied. Place `usage` (when present) under `detail.genai.usage` after re-shaping into the OTel-mirroring nested form (`{"system": ..., "request": {"model": ...}, "usage": {...}}`) (agent: build, blocked by T-A4).
- [ ] T-A6: Update `emit_skill_invoked` and `emit_agent_dispatched` in both pkg + `_lib` sides to accept and forward `usage` and trace-context kwargs; preserve all existing positional/keyword arguments (no breaking changes to existing call sites) (agent: build, blocked by T-A5).
- [ ] T-A7: Add unit tests: `tests/unit/state/test_trace_context.py` (push/pop/corruption/fresh-fallback), `tests/unit/state/test_observability_genai.py` (build_framework_event with usage round-trips through `validate_event_schema` and through `compute_entry_hash` without breaking chain on a synthetic 3-event sequence), `tests/unit/hooks/test_lib_trace_context.py` (stdlib-only mirror parity vs pkg side) — each ≥ 90 % line coverage on the new modules (agent: build, blocked by T-A6).
- [ ] T-A8: Targeted verification — run `tests/unit/state/test_audit_chain.py` and `tests/unit/test_audit_chain_verify.py` unchanged; confirm GREEN. Run `tests/unit/hooks/test_hook_integrity.py` unchanged; confirm GREEN (hooks manifest is regenerated in Phase E, not here, so this run validates that schema/validator additions do not perturb existing hook bytes) (agent: verify, blocked by T-A7).

### Phase B: SQLite projection + query CLI
**Gate**: `audit_index.py` reads the existing 27 MB NDJSON without errors and writes a SQLite database matching §4.3 of the spec; `indexed_lines.last_offset` enables incremental re-index; `ai-eng audit index` and `ai-eng audit query` and `ai-eng audit tokens` are wired under the `audit_app` Typer namespace at `cli_factory.py:334-340`; the three rollup views (`skill_token_rollup`, `agent_token_rollup`, `session_token_rollup`) return rows when `usage` blocks are present in source events.

- [ ] T-B1: Implement `src/ai_engineering/state/audit_index.py` — `build_index(project_root, rebuild=False) -> IndexResult` using stdlib `sqlite3`. Read NDJSON line-by-line tracking byte offset; if `rebuild=False` and `indexed_lines` row exists, seek to `last_offset` and resume. For each line: parse JSON, extract root + `detail.genai.*` columns per §4.3 schema, `INSERT OR REPLACE INTO events` keyed on `span_id` (or generated synthetic key when `spanId` absent — use sha256(line)[:16] so legacy events have a stable PK). Wrap inserts in a single transaction per build. Drop and recreate the indexes (`idx_events_*`) and views (`skill_token_rollup`, `agent_token_rollup`, `session_token_rollup`) only on `rebuild=True`. Always store the raw JSON in `detail_json` column for ad-hoc queries (agent: build, blocked by T-A8).
- [ ] T-B2: Add Typer subcommand `audit index` in `src/ai_engineering/cli_commands/audit_cmd.py` (`audit_index(rebuild: bool = typer.Option(False, "--rebuild"))`); register under `audit_app` in `cli_factory.py` next to the existing `verify` registration. Output: human summary (rows indexed, last_offset, elapsed_ms) plus optional `--json` mode following the existing `is_json_mode` convention from `audit_verify` (agent: build, blocked by T-B1).
- [ ] T-B3: Add Typer subcommand `audit query` (`audit_query(sql: str = typer.Argument(...), as_json: bool = typer.Option(False, "--json"))`) — open the SQLite DB read-only (`sqlite3.connect(f"file:{path}?mode=ro", uri=True)`), execute the SQL, print rows as a tabular layout (column widths from `cli_ui` helpers if available, else stdlib `str.ljust`), or as a JSON array under `--json`. Refuse non-SELECT statements with a clear error (parse the leading token after stripping whitespace and comments) (agent: build, blocked by T-B2).
- [ ] T-B4: Add Typer subcommand `audit tokens` (`audit_tokens(by: str = typer.Option("skill", "--by", help="skill|agent|session"))`) — thin wrapper that runs the matching `*_token_rollup` view and prints the result via the same tabular renderer as T-B3. Validates `by ∈ {skill, agent, session}` and exits non-zero on invalid value (agent: build, blocked by T-B3).
- [ ] T-B5: Unit tests `tests/unit/state/test_audit_index.py` covering: full build from a synthetic 50-event NDJSON; incremental rebuild after appending 5 new events advances `last_offset` and inserts only the new rows; `--rebuild` truthfully drops and recreates; legacy events without `spanId` get a deterministic synthetic PK; `genai` columns are NULL when absent and populated when present; the three rollup views aggregate correctly. Plus CLI tests `tests/unit/cli/test_audit_index_cli.py`, `test_audit_query_cli.py`, `test_audit_tokens_cli.py` covering happy path, `--json` mode, and the SELECT-only guard. ≥ 90 % line coverage on `audit_index.py` (agent: build, blocked by T-B4).
- [ ] T-B6: Add `.ai-engineering/state/audit-index.sqlite` to `.gitignore` if not already covered by `.ai-engineering/state/runtime/` patterns; verify gitignore coverage (agent: build, blocked by T-B5).

### Phase C: Replay + OTel export
**Gate**: `audit_replay.py` builds a span tree from the SQLite index and walks it depth-first with indented output; `--json` flag dumps the tree as a JSON object consumable by a future viewer; `audit_otel_export.py` produces OTLP-JSON-shaped spans (one span per event) with the §4.5 field mapping; both CLIs are registered under `audit_app`; legacy events without `traceId` are handled (skipped or grouped under a synthetic trace per session, decision documented in module docstring).

- [ ] T-C1: Implement `src/ai_engineering/state/audit_replay.py` — `build_span_tree(conn, *, session_id=None, trace_id=None) -> SpanNode`, `walk_tree(root, renderer)`, `render_text(node, depth) -> str`, `render_json(node) -> dict`. SpanNode is a dataclass with `span_id`, `parent_span_id`, `event` (the raw row dict), `children` (list). Sort children by `ts_unix_ms`. Token rollup at the end aggregates `total_tokens` and `cost_usd` over the visited subtree. Legacy events without `parent_span_id` are emitted as roots; ordering across multiple roots is by `ts_unix_ms` (agent: build, blocked by T-B6).
- [ ] T-C2: Add Typer subcommand `audit replay` (`audit_replay(session: str | None = typer.Option(None, "--session"), trace: str | None = typer.Option(None, "--trace"), as_json: bool = typer.Option(False, "--json"))`) — exactly one of `--session` / `--trace` required (validate and exit non-zero otherwise). Auto-runs `build_index(rebuild=False)` if the DB is missing or stale (mtime of NDJSON > mtime of SQLite). Print indented text by default; emit JSON dict under `--json`. Color the outcome cell red on `failure`, green on `success`, dim on `warning` using the `cli_ui` helpers if they expose color primitives, else plain text (agent: build, blocked by T-C1).
- [ ] T-C3: Implement `src/ai_engineering/state/audit_otel_export.py` — `build_otlp_spans(conn, *, trace_id) -> list[dict]` per the §4.5 mapping: `traceId` / `spanId` / `parentSpanId` pass-through; `timestamp` → `startTimeUnixNano` (ISO → unix nano); `kind` → `name`; `component` → `attributes.component`; `detail.genai.system` → `attributes."gen_ai.system"`; `detail.genai.request.model` → `attributes."gen_ai.request.model"`; `detail.genai.usage.input_tokens` → `attributes."gen_ai.usage.input_tokens"` (and matching `output_tokens`); `outcome=failure` → `status.code = "STATUS_CODE_ERROR"`; default span kind `SPAN_KIND_INTERNAL`. End-time defaults to `startTimeUnixNano` + 1 ns when no duration is recorded. Output structure follows OTel GenAI conventions snapshot v1.27.0; record the snapshot version in the module docstring (agent: build, blocked by T-C2).
- [ ] T-C4: Add Typer subcommand `audit otel-export` (`audit_otel_export(trace: str = typer.Option(..., "--trace"), out: Path | None = typer.Option(None, "--out"))`) — write the OTLP JSON to `out` if provided (Path), else stdout. Wrap the spans list in the standard `{"resourceSpans": [{"resource": {...}, "scopeSpans": [{"scope": {"name": "ai-engineering", "version": "<pkg-version>"}, "spans": [...]}]}]}` envelope (agent: build, blocked by T-C3).
- [ ] T-C5: Unit tests `tests/unit/state/test_audit_replay.py` covering: tree built from a 10-event synthetic chain with two nested children and one orphan legacy event (no parent_span_id); DFS walk visits in expected order; token rollup sums correctly; `render_json` round-trips through `json.dumps`. Plus `tests/unit/state/test_audit_otel_export.py` covering: each field-mapping row in §4.5; failure outcome flips status code; missing `genai` block leaves attributes empty; ISO→unix-nano conversion is exact for sub-second timestamps. Plus CLI tests `tests/unit/cli/test_audit_replay_cli.py` and `test_audit_otel_export_cli.py` for argument validation and stdout/file output. ≥ 90 % line coverage on both new modules (agent: build, blocked by T-C4).

### Phase D: End-to-end integration + docs
**Gate**: one integration test emits a synthetic session (5 nested events with usage), runs `index → query → replay → otel-export`, asserts each stage's output shape; AGENTS.md, CLAUDE.md, and `.ai-engineering/docs/` reference the new commands and the `genai` block; coverage on all four new modules is ≥ 90 % line.

- [ ] T-D1: Integration test `tests/integration/test_spec_120_e2e.py` — fixture creates a temp project root, emits a 5-event synthetic session via the pkg-side helpers (`emit_skill_invoked` with a `usage` block, then `emit_agent_dispatched` with `parent_span_id` linking back, then a nested `task_trace`). Then invokes the four CLI subcommands via Typer's `CliRunner` (`audit index`, `audit query "SELECT COUNT(*) FROM events"`, `audit replay --session <id> --json`, `audit otel-export --trace <id> --out spans.json`). Asserts: index reports 5 rows; query returns 5; replay JSON has the nested tree shape; OTLP JSON validates against a minimal in-test schema (resourceSpans → scopeSpans → spans → required fields per row in §4.5) (agent: build, blocked by T-C5).
- [ ] T-D2: Update `AGENTS.md` and `CLAUDE.md` — append a short "Audit observability" section under existing observability docs that lists the four new commands and points at this spec for the field-mapping reference. Update `.ai-engineering/docs/` if an observability doc exists there; create one only if a peer doc clearly belongs there per existing convention (do NOT proliferate docs) (agent: build, blocked by T-D1).
- [ ] T-D3: Coverage check — run `pytest --cov=ai_engineering.state.trace_context --cov=ai_engineering.state.audit_index --cov=ai_engineering.state.audit_replay --cov=ai_engineering.state.audit_otel_export --cov-report=term-missing` and confirm ≥ 90 % line on each. Record the result in `.ai-engineering/specs/spec-120-progress/coverage-evidence.md` (create the progress directory) (agent: verify, blocked by T-D2).

### Phase E: Wiring + manifest regen
**Gate**: `runtime-stop.py` writes a session-end token rollup event sourced from the SQLite index; dispatcher emits `agent_dispatched` and `skill_invoked` with `usage` capture when the IDE provides counts; hooks manifest regenerated with `regenerate-hooks-manifest.py`; all spec-104 / spec-110 audit-chain integrity tests still pass; spec acceptance criteria 1-8 evidenced.

- [ ] T-E1: Update `.ai-engineering/scripts/hooks/runtime-stop.py` — at session end, open the SQLite index read-only, run `SELECT * FROM session_token_rollup WHERE session_id = ?`, emit a single `framework_operation` event with `detail.operation = "session_token_rollup"` and the rollup payload (input/output/total tokens, cost_usd, started_at, ended_at). Best-effort: if the index is missing or stale, skip emission and log a `framework_error` of `error_code = session_rollup_skipped` (agent: build, blocked by T-D3).
- [ ] T-E2: Update the dispatcher emit sites for `agent_dispatched` and `skill_invoked` (search: `grep -rn "emit_agent_dispatched\|emit_skill_invoked" .ai-engineering/scripts/hooks/`) — at each call site that already has access to token counts from the IDE payload, forward them as `usage={"input_tokens": ..., "output_tokens": ...}`. Do NOT fabricate counts when absent; `usage` stays `None` and the event is emitted without a `genai` block (agent: build, blocked by T-E1).
- [ ] T-E3: Run `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py` to regenerate `.ai-engineering/state/hooks-manifest.json` for every hook script edited in T-E1 / T-E2 / T-A4 / T-A5 / T-A6. Run again with `--check` to confirm zero residual drift. Commit the regenerated manifest in the same commit as the hook edits (agent: build, blocked by T-E2).
- [ ] T-E4: Acceptance-criteria sweep against spec-120 §6: (1) `ai-eng audit index` builds SQLite from existing 27 MB NDJSON without errors; (2) `audit query "SELECT kind, COUNT(*) FROM events GROUP BY kind"` returns counts; (3) `audit tokens --by skill` returns a non-empty table when `usage` is present; (4) `audit replay --session <id>` walks parent-child order indented; (5) `audit otel-export --trace <id> --out spans.json` produces valid OTLP JSON; (6) all existing tests pass; (7) hooks manifest regenerated and committed; (8) spec-104 / spec-110 audit-chain integrity tests still pass. Record evidence in `.ai-engineering/specs/spec-120-progress/acceptance-evidence.md` (agent: verify, blocked by T-E3).
- [ ] T-E5: Governance review on the schema additions, the four new CLI subcommands, the runtime-stop emission, the hooks-manifest regen, and the audit-chain non-regression evidence; sign-off in `.ai-engineering/specs/spec-120-progress/governance-review.md` (agent: guard, blocked by T-E4).

## Wave grouping for /ai-dispatch

| Wave | Tasks (parallel within wave) | Notes |
|------|------------------------------|-------|
| W1   | T-A1                         | Schema TypedDict — single-file foundation |
| W2   | T-A2                         | JSON schema (depends on W1 contract names) |
| W3   | T-A3                         | trace_context (pkg side) |
| W4   | T-A4                         | trace_context (`_lib` mirror) — split from W3 to keep Python paths clean |
| W5   | T-A5, T-A6                   | Parallel: build_framework_event extension + emit-helper extension; both touch pkg + `_lib` symmetrically |
| W6   | T-A7                         | Unit tests for Phase A |
| W7   | T-A8                         | Verification gate for Phase A (audit-chain non-regression) |
| W8   | T-B1                         | audit_index module |
| W9   | T-B2, T-B3, T-B4             | Parallel: three independent CLI subcommands sharing the `audit_app` Typer namespace |
| W10  | T-B5, T-B6                   | Parallel: tests + gitignore (no overlap) |
| W11  | T-C1, T-C3                   | Parallel: replay module and OTel exporter module — independent; both consume `audit_index` outputs only |
| W12  | T-C2, T-C4                   | Parallel: their respective CLI subcommands |
| W13  | T-C5                         | Combined Phase C tests |
| W14  | T-D1                         | Integration test (cross-module; runs after every Phase A/B/C surface is green) |
| W15  | T-D2, T-D3                   | Parallel: docs + coverage report |
| W16  | T-E1, T-E2                   | Parallel: runtime-stop edit + dispatcher edits — different files |
| W17  | T-E3                         | Hooks manifest regen (must follow all hook edits) |
| W18  | T-E4                         | Acceptance sweep |
| W19  | T-E5                         | Governance sign-off |

Cross-wave dependencies: every wave is gated by the previous wave's last task's success. Inside a wave, tasks are independent and can dispatch in parallel.

## Risk hotspots

| Hotspot | Risk | Mitigation |
|---------|------|-----------|
| `compute_entry_hash` in `src/ai_engineering/state/audit_chain.py` | Adding root fields (`traceId`, `spanId`, `parentSpanId`) changes the canonical-JSON input to the hasher — could appear to break the chain if the new fields land mid-stream and old verifiers compare against pre-existing hashes. | The chain is forward-only by construction (`prev_event_hash` of event N is computed from event N-1 at write time). New fields are absorbed naturally because `compute_entry_hash` already excludes only `prev_event_hash` itself, not "fields it has not seen before." The risk is purely on the **mental model**, not the implementation — but T-A8 makes it explicit by re-running `tests/unit/state/test_audit_chain.py` and `tests/unit/test_audit_chain_verify.py` unchanged after Phase A. |
| Hooks manifest (`.ai-engineering/state/hooks-manifest.json`) | Editing `_lib/observability.py` (T-A5/A6) and `runtime-stop.py` (T-E1) without regenerating the manifest would trip `runtime-guard.py` integrity checks in `enforce` mode and emit `hook_integrity_violation` errors in `warn` mode. | T-E3 regenerates the manifest after all hook edits land; the `--check` flag is run to confirm zero drift. T-A8 explicitly runs `tests/unit/hooks/test_hook_integrity.py` to catch the issue before Phase E. |
| `tests/unit/state/test_audit_chain.py` and `test_audit_chain_verify.py` | These tests are sensitive to any change in event-payload semantics; a failing assertion here is a regression-blocker. | Treated as canary in T-A8 (between Phase A and Phase B). Phase B/C/D do not touch the chain at all. |
| `additionalProperties: false` in audit-event schema | The existing discriminated branches (`detail_skill_invoked`, etc.) reject unknown keys. Adding `genai` requires extending the explicit property list, not flipping the closed surface. | T-A2 explicitly chooses the explicit-property-list path so `additionalProperties: false` stays enforced. Anything outside `genai` and the existing fields still gets rejected. |
| Trace-context file corruption | A partial write or a stale lock could leave `trace-context.json` unparseable. | T-A3 spec'd the fall-back: corruption logs a `framework_error` and returns a fresh trace_id with NULL parent. Tests in T-A7 cover the corruption path. |
| SQLite index drift | Hand-edits to NDJSON or simultaneous writes during indexing could leave SQLite stale. | The index is gitignored and rebuildable; `--rebuild` flag drops and re-reads from offset 0. T-B1 wraps inserts in a single transaction per build. |
| `audit_app` Typer namespace | Currently registers only `verify`; adding four subcommands expands the surface — risk of name collision if anyone added shadowed subcommands elsewhere. | Confirmed `cli_factory.py:334-340` is the single registration site; T-B2/B3/B4/C2/C4 register adjacent to `verify` in one block. |

## Test strategy per phase

| Phase | Strategy | Coverage target |
|-------|----------|-----------------|
| A     | Unit tests on the four new pieces of behaviour: TypedDict + validator additions, trace_context module (pkg + `_lib` mirror parity), build_framework_event extensions, emit-helper extensions. Plus an explicit non-regression run of `test_audit_chain.py`, `test_audit_chain_verify.py`, `test_hook_integrity.py`. | ≥ 90 % line on `trace_context.py` (pkg + `_lib`); event_schema additions covered by `test_observability_genai.py`. |
| B     | Unit tests on `audit_index.py` (full build, incremental rebuild, `--rebuild` flag, legacy events, view aggregation). CLI tests on each Typer subcommand using `typer.testing.CliRunner`. | ≥ 90 % line on `audit_index.py`. |
| C     | Unit tests on `audit_replay.py` (tree construction, DFS walk, JSON dump, token rollup) and `audit_otel_export.py` (every field-mapping row in §4.5, failure-status flip, ISO→nano conversion). CLI tests on both subcommands. | ≥ 90 % line on `audit_replay.py` and `audit_otel_export.py`. |
| D     | One end-to-end integration test that emits a synthetic 5-event nested session via the real `emit_*` helpers and runs `index → query → replay → otel-export` through `CliRunner`, asserting each stage's output. Coverage report run as a separate verify task with results recorded. | Aggregate ≥ 90 % across the four new modules; integration assertions named `test_spec_120_e2e_full_pipeline`, `test_spec_120_e2e_otlp_shape`, `test_spec_120_e2e_replay_tree_shape`. |
| E     | Acceptance-criteria sweep against spec §6 plus governance review. Existing test suite (`pytest tests/`) must remain green; explicit re-run of audit-chain and hook-integrity tests; hooks-manifest `--check` must report zero drift. | No new coverage target — the gate is "everything still green." |

Concrete pytest names (exhaustive list referenced by tasks):
- `tests/unit/state/test_trace_context.py::test_push_pop_round_trip`
- `tests/unit/state/test_trace_context.py::test_corruption_falls_back_to_fresh_trace`
- `tests/unit/state/test_trace_context.py::test_new_span_id_is_16_hex`
- `tests/unit/state/test_trace_context.py::test_new_trace_id_is_32_hex`
- `tests/unit/hooks/test_lib_trace_context.py::test_lib_mirror_byte_for_byte_with_pkg`
- `tests/unit/state/test_observability_genai.py::test_build_event_with_usage_validates`
- `tests/unit/state/test_observability_genai.py::test_chain_unbroken_with_trace_fields`
- `tests/unit/state/test_observability_genai.py::test_emit_skill_invoked_with_usage`
- `tests/unit/state/test_audit_index.py::test_full_build_from_synthetic_ndjson`
- `tests/unit/state/test_audit_index.py::test_incremental_rebuild_advances_offset`
- `tests/unit/state/test_audit_index.py::test_rebuild_flag_drops_and_recreates`
- `tests/unit/state/test_audit_index.py::test_legacy_events_get_synthetic_pk`
- `tests/unit/state/test_audit_index.py::test_skill_token_rollup_view`
- `tests/unit/state/test_audit_index.py::test_agent_token_rollup_view`
- `tests/unit/state/test_audit_index.py::test_session_token_rollup_view`
- `tests/unit/cli/test_audit_index_cli.py::test_index_human_output`
- `tests/unit/cli/test_audit_index_cli.py::test_index_json_output`
- `tests/unit/cli/test_audit_query_cli.py::test_query_select_count`
- `tests/unit/cli/test_audit_query_cli.py::test_query_rejects_non_select`
- `tests/unit/cli/test_audit_tokens_cli.py::test_tokens_by_skill`
- `tests/unit/cli/test_audit_tokens_cli.py::test_tokens_invalid_by_exits_nonzero`
- `tests/unit/state/test_audit_replay.py::test_tree_built_from_synthetic_chain`
- `tests/unit/state/test_audit_replay.py::test_dfs_walk_order`
- `tests/unit/state/test_audit_replay.py::test_orphan_legacy_event_emitted_as_root`
- `tests/unit/state/test_audit_replay.py::test_token_rollup_sums_subtree`
- `tests/unit/state/test_audit_replay.py::test_render_json_round_trips`
- `tests/unit/state/test_audit_otel_export.py::test_field_mapping_per_spec_4_5`
- `tests/unit/state/test_audit_otel_export.py::test_failure_outcome_flips_status_error`
- `tests/unit/state/test_audit_otel_export.py::test_iso_to_unix_nano_exact`
- `tests/unit/state/test_audit_otel_export.py::test_missing_genai_leaves_attrs_empty`
- `tests/unit/cli/test_audit_replay_cli.py::test_replay_session_indented`
- `tests/unit/cli/test_audit_replay_cli.py::test_replay_json_output`
- `tests/unit/cli/test_audit_replay_cli.py::test_replay_requires_session_or_trace`
- `tests/unit/cli/test_audit_otel_export_cli.py::test_export_to_stdout`
- `tests/unit/cli/test_audit_otel_export_cli.py::test_export_to_file`
- `tests/integration/test_spec_120_e2e.py::test_spec_120_e2e_full_pipeline`
- `tests/integration/test_spec_120_e2e.py::test_spec_120_e2e_replay_tree_shape`
- `tests/integration/test_spec_120_e2e.py::test_spec_120_e2e_otlp_shape`

## Do not touch

The following files MUST NOT be modified by spec-120 — any change here regresses the audit chain or hook integrity manifest and triggers a verification gate failure:

- `src/ai_engineering/state/audit_chain.py` — `compute_entry_hash` and `verify_audit_chain` are the canonical hash-chain implementation. spec-120 is additive at the wire-format layer; the hasher must remain bit-stable.
- `tests/unit/state/test_audit_chain.py` — canary for chain integrity.
- `tests/unit/test_audit_chain_verify.py` — second canary for chain integrity.
- `tests/unit/hooks/test_hook_integrity.py` — canary for hook manifest stability.
- `.ai-engineering/state/hooks-manifest.json` — only T-E3 regenerates this via the official `regenerate-hooks-manifest.py` script; never hand-edit.
- `.ai-engineering/state/framework-events.ndjson` — never written to except via `append_framework_event`; the index reads it but does not touch it.
- `.ai-engineering/scripts/regenerate-hooks-manifest.py` — script is invoked, never modified.
- `.claude/settings.json` deny rules — read-only at the IDE layer per CLAUDE.md hot-path discipline.
- Existing `audit_verify` Typer command in `audit_cmd.py` — extend the namespace alongside it, do not replace.
- `src/ai_engineering/state/observability.py::append_framework_event` body — extend `build_framework_event` (the constructor) but leave the file-write path (single-writer lock semantics) unchanged.

## Sequencing notes

- Phase A is strictly sequential by file dependencies (TypedDict → JSON schema → pkg trace_context → `_lib` trace_context → emit constructor → emit helpers → tests → verification gate). The wave grouping above is tight on purpose.
- Phase B's three CLI subcommands (T-B2/B3/B4) are independent and can ship in one wave; they share only the `audit_app` namespace registration site, which is line-additive.
- Phase C's two new modules (`audit_replay.py` and `audit_otel_export.py`) are parallel — neither imports the other; both consume `audit_index.py` outputs only.
- Phase D's integration test is the first place all four new modules execute together; it must follow Phase C green.
- Phase E hook edits (T-E1, T-E2) are parallel because they touch different files. T-E3 (manifest regen) must follow both. T-E4 (acceptance sweep) is a verification task, not a code task.
- Hooks-manifest regen (T-E3) is the ONLY task allowed to write `.ai-engineering/state/hooks-manifest.json`. Any earlier manifest mismatch caught by `runtime-guard.py` is a defect and must be fixed by re-running T-E3, not by hand-editing.

## Exit conditions

- Four new modules under `src/ai_engineering/state/` (`trace_context.py`, `audit_index.py`, `audit_replay.py`, `audit_otel_export.py`) plus one mirror at `.ai-engineering/scripts/hooks/_lib/trace_context.py`, each with ≥ 90 % line coverage.
- Four new CLI subcommands registered under `audit_app` in `cli_factory.py`: `audit index`, `audit query`, `audit tokens`, `audit replay`, `audit otel-export` (five subcommands; `audit tokens` is a thin wrapper over `audit query`).
- `traceId` / `spanId` / `parentSpanId` are accepted at root by both validator and JSON schema; `genai` block is accepted under `detail.*` for `skill_invoked`, `agent_dispatched`, `task_trace`.
- Hash-chain tests (`test_audit_chain.py`, `test_audit_chain_verify.py`) and hook-integrity tests (`test_hook_integrity.py`) remain GREEN unchanged.
- Hooks manifest regenerated and committed in the same commit as hook edits.
- One integration test (`tests/integration/test_spec_120_e2e.py`) exercises emit → index → query → replay → otel-export end-to-end with a synthetic session.
- All eight acceptance criteria from spec-120 §6 are evidenced in `.ai-engineering/specs/spec-120-progress/acceptance-evidence.md`.
- Governance sign-off recorded in `.ai-engineering/specs/spec-120-progress/governance-review.md`.
- Non-goals from spec-120 §3 (Langfuse/Phoenix deployment, real-time export, HTML viewer, backfill of legacy events, replacing audit chain) and deferred items from §8 are NOT addressed by any task above.
