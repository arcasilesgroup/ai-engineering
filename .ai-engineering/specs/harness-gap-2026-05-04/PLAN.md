# Harness Gap Closure — Consolidated Plan + DAG

## Sub-spec plans (compact)

### SS-01 — Memory persistence repair (P0.1)
**Root cause** (verified): `memory-stop.py` shells via `sys.executable`. Under Claude Code,
`sys.executable` from the hook process is the system `python3` (e.g. `/opt/homebrew/.../python3`)
which lacks the `typer` dep. The `memory.cli` import fails, the subprocess returns nonzero,
the hook fail-open path runs, and zero episodes get written. The CLI itself works correctly
when invoked with the project venv (`{"status":"no_events"}` for synthetic, real episode
written for a real session_id with events).

**Fix**:
- Add `_resolve_python()` in `memory-stop.py` mirroring the Copilot wrapper's logic:
  prefer `<project>/.venv/bin/python`, then `.venv/Scripts/python(.exe)`, then `uv run`,
  finally fall back to `sys.executable`.
- When fallback to `sys.executable` happens, emit `framework_operation` with
  `operation=memory_stop_python_fallback` so the gap is visible in telemetry instead of silent.
- Same fix in `memory.cli` (Popen for embed-episode) so the fire-and-forget child also
  uses the venv python.

**Tests**: `tests/integration/test_memory_episode_persistence.py`:
- Build a synthetic project_root with `framework-events.ndjson` containing 3+ events for
  one sessionId, plus a fake `.venv/bin/python` symlink to `sys.executable` (the test's
  own python which DOES have typer because pytest is in the venv).
- Run memory-stop.py via subprocess with the synthetic Stop payload.
- Assert episodes table has ≥1 row matching that sessionId.
- Second test: project without `.venv` falls back to `sys.executable`, emits the fallback
  framework_operation event.

**Files touched**: `.ai-engineering/scripts/hooks/memory-stop.py`,
`.ai-engineering/scripts/memory/cli.py`, `tests/integration/test_memory_episode_persistence.py`.

### SS-02 — Integrity default = enforce (P0.2)
**Fix**: change `_DEFAULT_MODE = "warn"` → `"enforce"` in `_lib/integrity.py:40`.

**Tests**:
- Update `tests/unit/hooks/test_hook_integrity.py` if any test relies on warn-as-default.
  (Reading the file: tests pass mode via env, no test pins default. Add new pin-test.)
- New: `tests/unit/hooks/test_integrity_default_matches_doc.py` — imports `_DEFAULT_MODE`
  via importlib, asserts `=="enforce"`. Drift test.

**Files**: `_lib/integrity.py`, new test file.

### SS-03 — Ralph reinjection enabled-by-default (P0.3)
**Fix**: line 84 of `runtime-stop.py`:
```python
# Before:
_RALPH_BLOCK_ENABLED = (os.environ.get("AIENG_RALPH_BLOCK") or "").strip() == "1"
# After:
_RALPH_BLOCK_ENABLED = (os.environ.get("AIENG_RALPH_BLOCK", "1") or "").strip() != "0"
```
Also update the docstring above to reflect new default.

**Tests**: `tests/unit/hooks/test_runtime_stop_ralph.py`:
- assert default enabled (no env var → ENABLED=True)
- assert AIENG_RALPH_BLOCK=0 → ENABLED=False (opt-out)
- assert AIENG_RALPH_DISABLED=1 still wins (existing escape)
- Smoke: invoke `_ralph_convergence_loop` against tmp project with no test failures →
  returns False (converged path); the change must not break the convergence-passes path.

**Files**: `runtime-stop.py`, new test, ADR fragment in `.ai-engineering/decisions/`.

### SS-04 — Codex injection guard matcher coverage (P1.1)
**Codex tool taxonomy**: Codex v3 hook protocol uses Bash + edit + patch + apply_patch
as the principal mutation tools (verified from `.codex/skills` references and the
codex-hook-bridge passthrough). Currently every PreToolUse hook matches only `Bash`.

**Fix**: change `"matcher": "Bash"` → `"matcher": "Bash|edit|patch|apply_patch|write"`
on all four PreToolUse hooks in `.codex/hooks.json`.

**Tests**: `tests/integration/test_codex_injection_coverage.py`:
- Parse `.codex/hooks.json`. For each PreToolUse hook in canonical list, assert matcher
  contains all of {Bash, edit, patch, apply_patch}.
- Drift test: future hooks added must explicitly opt out via comment marker, else fail.

**Files**: `.codex/hooks.json`, new test, updated `hooks-manifest.json` checksums (json
not in manifest, but verify via re-run).

### SS-05 — Memory cross-IDE parity (P1.2)
**Codex**: add `memory-stop.py` to `Stop` event in `.codex/hooks.json`. (memory-session-start
is referenced as wired but I see only `codex-hook-bridge` etc. — verify and add too.)

**Gemini**: add `memory-stop.py` to `AfterAgent`, `memory-session-start.py` to `BeforeAgent`
in `.gemini/settings.json`.

**Copilot**: create `copilot-memory-stop.{sh,ps1}` in `.ai-engineering/scripts/hooks/`
following the existing `copilot-runtime-stop.sh` pattern — uses `copilot_framework_python_script`
to launch `memory-stop.py` with venv python. Wire in `.github/hooks/hooks.json` `sessionEnd`.
Also create `copilot-memory-session-start.{sh,ps1}` for `sessionStart`.

**Tests**: `tests/integration/test_memory_cross_ide.py`:
- For each engine ID (codex, gemini, copilot), confirm the hook config wires `memory-stop`
  to the Stop-equivalent event.
- Smoke: invoke each adapter with a synthetic Stop payload, assert episodes count increments
  (uses the same fixture pattern as SS-01).

**Files**: `.codex/hooks.json` (overlap with SS-04 — serialize), `.gemini/settings.json`,
new `.ai-engineering/scripts/hooks/copilot-memory-{stop,session-start}.{sh,ps1}` (4 files),
`.github/hooks/hooks.json`, hooks-manifest re-pin, new test.

### SS-06 — Eval-gate CI workflow (P2.1)
**Discovery**: `ai-eng eval check/gate` CLI subcommand DOES NOT EXIST. The eval module is
implemented (`src/ai_engineering/eval/gate.py:mode_check/mode_enforce/mode_report`) but no
Typer wiring in `cli_factory.py`. Adding `ai-eng eval check` is a prerequisite.

**Fix**:
1. Add `eval_cmd.py` in `cli_commands/` exposing `eval check`, `eval enforce`, `eval report`
   that wraps `ai_engineering.eval.gate.mode_*` functions.
2. Register in `cli_factory.py` as `eval_app` Typer subcommand.
3. Create `.github/workflows/eval-gate.yml`:
   - On `pull_request` → `ai-eng eval check --json` (advisory comment, no fail).
   - On `push` to main → `ai-eng eval enforce --json` (failing job blocks merge).
   - Reads thresholds from manifest.yml (already structured).

**Tests**:
- `tests/unit/cli/test_eval_cmd.py` — typer.testing.CliRunner against the three subcommands.
  Stub `run_gate` to return a known GateOutcome; assert exit code mapping (CONDITIONAL=0
  in check mode, =1 in enforce mode for NO_GO, etc.).
- Workflow lint: `actionlint` if available; otherwise `python -c "import yaml; yaml.safe_load(...)"`
  smoke.

**Files**: new `cli_commands/eval_cmd.py`, `cli_factory.py` edit, new
`.github/workflows/eval-gate.yml`, new test.

### SS-07 — Embedding async worker (P2.2)
**Fix**: `embed_worker.py` daemon under `.ai-engineering/scripts/memory/`.

Implementation:
```python
# embed_worker.py
def run_once(project_root, batch_size=32):
    """Embed up to batch_size pending episodes. Returns count."""
def run_daemon(project_root, poll_interval_sec=60):
    """Loop forever: run_once + sleep. SIGTERM-safe."""
```

CLI: add `embed` subcommand to `memory.cli` with `--once` / `--daemon` flags.

Hot-path guard: at module load time, if `os.environ.get("AIENG_HOOK_RUNTIME") == "1"`,
raise `HotPathInvocationError`. (Existing convention — verify by grep.)

Cron snippet: `.ai-engineering/scripts/scheduled/memory-embed.sh` (mirror entropy-gc.sh
pattern). Recommended cadence: every 5 minutes when daemon is not running, OR daemon-mode
under launchd/systemd.

**Tests**: `tests/unit/memory/test_embed_worker.py`:
- Fixture: 10 pending episode rows in tmp memory.db.
- `run_once()` → 10 vectors written, all rows updated to `complete`.
- Empty queue → exits 0, no error.
- Hot-path guard: setting `AIENG_HOOK_RUNTIME=1` raises HotPathInvocationError.
- Mismatch dim error path: model returns wrong-size vector → row marked `failed`,
  framework_error event emitted.

**Files**: new `embed_worker.py`, edit `memory/cli.py`, new
`.ai-engineering/scripts/scheduled/memory-embed.sh`, new test.

### SS-08 — A2A artifact protocol + ACI severity (P3.1+P3.2 combined)
**P3.1 — A2A**: Create `_lib/agent_protocol.py` with:
```python
@dataclass(frozen=True)
class AgentArtifact:
    run_id: str
    agent_type: str
    inputs: dict
    outputs: dict
    citations: list[str]
    confidence: float | None
    parent_run_id: str | None
    started_at: str
    ended_at: str
    status: Literal["success", "failure", "partial"]
def write_artifact(project_root, artifact) -> Path:
    """Atomic write to .ai-engineering/state/agent-artifacts/<run-id>.json."""
def load_artifact(project_root, run_id) -> AgentArtifact:
def trace_session(project_root, session_id) -> list[AgentArtifact]:
```
CLI: `ai-eng agent inspect <run-id>` and `ai-eng agent trace <session-id>`.

**P3.2 — ACI severity**: extend `_lib/observability.py:emit_framework_error()`:
- New optional kwargs: `severity: str = "advisory"`, `recovery_hint: str | None = None`.
- Bump `FRAMEWORK_EVENT_SCHEMA_VERSION = "1.1"`.
- New ALLOWED severity set: `{"recoverable","terminal","advisory"}`.
- Backward compat: events without `severity` parse fine; CLI/audit code reads `severity`
  with `.get("severity","advisory")` default.
- SQLite projection (`audit_index.py`): add `severity TEXT` and `recovery_hint TEXT`
  columns via additive ALTER. Migration step in `build_index`: `ALTER TABLE events ADD
  COLUMN severity TEXT` wrapped in try/except for already-applied case.

**Spec doc**: write `.ai-engineering/specs/spec-122-a2a-artifact-protocol.md` (lightweight
spec stub since the implementation lives in this PR).

**Tests**:
- `tests/unit/_lib/test_agent_protocol.py` — schema validation, atomic write under
  concurrent writes (use `threading` to write same run_id from 2 threads, assert one
  wins clean), nested parent_run_id.
- `tests/unit/hooks/test_event_schema_v11.py` — old (1.0) events still parse, new (1.1)
  validates severity enum, projection has new columns.
- `tests/unit/cli/test_agent_inspect_cli.py` — CliRunner against new commands.

**Files**: new `_lib/agent_protocol.py`, edit `_lib/observability.py`, edit
`audit_index.py`, new `cli_commands/agent_cmd.py`, edit `cli_factory.py`, 3 new tests,
new spec doc.

### SS-09 — OTLP live-tail daemon (P4.1)
**Fix**: add `audit_otel_tail()` in `audit_cmd.py`:
- Tail `framework-events.ndjson` (file watch via mtime polling, stdlib only).
- Batch into OTLP/JSON envelopes (reuse `build_otlp_spans` shaping logic if applicable;
  may need a parallel `build_otlp_spans_from_events` since the existing function reads
  from SQLite).
- POST to `--collector` URL via `urllib.request` with retry (exponential backoff: 1s,2s,4s,
  max 3 attempts).
- Fail-open on collector unreachable: emit `framework_error` with summary, continue tailing.
- `--since <timestamp>` resumes from a checkpoint.

CLI registration in `cli_factory.py`.

CLAUDE.md: add Langfuse + Phoenix collector endpoint hints in the audit observability
section.

**Tests**: `tests/integration/test_otel_tail.py`:
- Spin up `http.server` thread on free port, capture POST bodies.
- Append events to fixture NDJSON.
- Run `audit_otel_tail` for ≤2s with `--since` to scope.
- Assert events arrive in order, OTLP envelope structure correct.

**Files**: edit `audit_cmd.py`, edit `cli_factory.py`, edit `state/audit_otel_export.py`
(new `build_otlp_spans_from_events` helper if needed), new integration test, edit CLAUDE.md.

---

## File-overlap matrix

|                              | SS-01 | SS-02 | SS-03 | SS-04 | SS-05 | SS-06 | SS-07 | SS-08 | SS-09 |
|------------------------------|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|
| memory-stop.py               | ✓     |       |       |       |       |       |       |       |       |
| _lib/integrity.py            |       | ✓     |       |       |       |       |       |       |       |
| runtime-stop.py              |       |       | ✓     |       |       |       |       |       |       |
| .codex/hooks.json            |       |       |       | ✓     | ✓     |       |       |       |       |
| .gemini/settings.json        |       |       |       |       | ✓     |       |       |       |       |
| .github/hooks/hooks.json     |       |       |       |       | ✓     |       |       |       |       |
| memory/cli.py                | ✓     |       |       |       |       |       | ✓     |       |       |
| _lib/observability.py        |       |       |       |       |       |       |       | ✓     |       |
| state/audit_index.py         |       |       |       |       |       |       |       | ✓     |       |
| state/audit_otel_export.py   |       |       |       |       |       |       |       |       | ✓     |
| audit_cmd.py                 |       |       |       |       |       |       |       |       | ✓     |
| cli_factory.py               |       |       |       |       |       | ✓     |       | ✓     | ✓     |
| hooks-manifest.json          | ✓     |       | ✓     |       | ✓     |       |       |       |       |

## Conflict zones (must serialize)
- `.codex/hooks.json` — SS-04 + SS-05 → serialize (Wave 2 then Wave 2.b)
- `memory/cli.py` — SS-01 + SS-07 → SS-01 first (Wave 1), SS-07 follows (Wave 3)
- `cli_factory.py` — SS-06 + SS-08 + SS-09 → serialize (sequential edits)
- `hooks-manifest.json` — touched by SS-01, SS-03, SS-05 → regenerate at end of each wave

## DAG / Wave plan

```
Wave 1 (P0 — critical fixes, parallel-safe except cli.py):
  ┌─ SS-02 (integrity default)        → independent
  ├─ SS-03 (ralph default)            → independent
  └─ SS-01 (memory persistence)       → touches memory/cli.py first

Wave 2 (P1 — cross-IDE, partial serialize):
  ┌─ SS-04 (codex matchers)           → must run before SS-05 (.codex/hooks.json)
  └─ SS-05 (memory cross-IDE)         → starts after SS-04 commits

Wave 3 (P2 — features):
  ┌─ SS-06 (eval-gate CI)             → cli_factory.py edit (sequential)
  └─ SS-07 (embed worker)             → memory/cli.py edit (after SS-01 stable)

Wave 4 (P3 — doctrine primitives):
  └─ SS-08 (A2A + ACI)                → cli_factory.py + observability + audit_index

Wave 5 (P4 — live observability):
  └─ SS-09 (OTLP tail)                → cli_factory.py + audit_cmd + otel_export

Final: regenerate-hooks-manifest.py + ruff + pytest -x + integrity report.
```

Total: 5 waves, 9 sub-specs, expected ~30-50 net source files touched + tests.
