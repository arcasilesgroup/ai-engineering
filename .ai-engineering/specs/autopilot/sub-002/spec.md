---
id: sub-002
parent: spec-122
title: "Engram Delegation + Unified state.db"
status: planning
files:
  - .ai-engineering/state/state.db
  - .ai-engineering/state/memory.db
  - .ai-engineering/state/decision-store.json
  - .ai-engineering/state/gate-findings.json
  - .ai-engineering/state/ownership-map.json
  - .ai-engineering/state/install-state.json
  - .ai-engineering/state/hooks-manifest.json
  - .ai-engineering/state/framework-events.ndjson
  - .ai-engineering/state/instinct-observations.ndjson
  - .ai-engineering/state/audit-index.sqlite
  - .ai-engineering/scripts/memory/__init__.py
  - .ai-engineering/scripts/memory/store.py
  - .ai-engineering/scripts/memory/cli.py
  - .ai-engineering/scripts/memory/episodic.py
  - .ai-engineering/scripts/memory/knowledge.py
  - .ai-engineering/scripts/memory/semantic.py
  - .ai-engineering/scripts/memory/retrieval.py
  - .ai-engineering/scripts/memory/dreaming.py
  - .ai-engineering/scripts/memory/audit.py
  - .ai-engineering/scripts/memory/repair.py
  - .ai-engineering/scripts/hooks/runtime-guard.py
  - src/ai_engineering/state/connection.py
  - src/ai_engineering/state/migrations/__init__.py
  - src/ai_engineering/state/migrations/_runner.py
  - src/ai_engineering/state/migrations/0001_initial_schema.py
  - src/ai_engineering/state/migrations/0002_seed_from_json.py
  - src/ai_engineering/state/migrations/0003_replay_ndjson.py
  - src/ai_engineering/state/state_db.py
  - src/ai_engineering/state/outbox.py
  - src/ai_engineering/state/rotation.py
  - src/ai_engineering/state/sidecar.py
  - src/ai_engineering/state/retention.py
  - src/ai_engineering/state/audit_index.py
  - src/ai_engineering/state/audit_chain.py
  - src/ai_engineering/state/audit.py
  - src/ai_engineering/state/repository.py
  - src/ai_engineering/state/service.py
  - src/ai_engineering/cli_commands/audit_cmd.py
  - src/ai_engineering/cli_commands/memory_cmd.py
  - src/ai_engineering/cli_factory.py
  - src/ai_engineering/installer/service.py
  - src/ai_engineering/installer/tools.py
  - pyproject.toml
  - uv.lock
  - .claude/skills/ai-remember/SKILL.md
  - .claude/skills/ai-dream/SKILL.md
  - .claude/skills/ai-instinct/SKILL.md
  - src/ai_engineering/templates/project/.claude/skills/ai-remember/SKILL.md
  - src/ai_engineering/templates/project/.claude/skills/ai-dream/SKILL.md
  - src/ai_engineering/templates/project/.gemini/skills/ai-remember/SKILL.md
  - src/ai_engineering/templates/project/.gemini/skills/ai-dream/SKILL.md
  - .gitignore
  - tests/integration/state/test_db_migration.py
  - tests/integration/state/test_outbox_atomic.py
  - tests/integration/state/test_rotation_chain.py
  - tests/integration/state/test_retention.py
  - tests/integration/memory/test_engram_subprocess.py
  - tests/unit/state/test_connection_pragmas.py
  - tests/unit/state/test_migration_integrity.py
  - tests/unit/state/test_sidecar_overflow.py
depends_on: [sub-001]
source_spec: .ai-engineering/specs/spec-122-b-engram-and-state-unify.md
---

# Sub-Spec 002: Engram Delegation + Unified state.db

## Scope

Replace self-hosted memory layer (`memory.db` + `sqlite-vec` + `fastembed` +
`hdbscan`, ~3K LOC across `scripts/memory/`) with delegation to Engram external
CLI (`/opt/homebrew/bin/engram` v1.15.8+). Consolidate framework persistence into
single `state.db` SQLite with 7 STRICT tables (`events`, `decisions`,
`risk_acceptances`, `gate_findings`, `hooks_integrity`, `ownership_map`,
`install_steps`) + `_migrations` ledger. Preserve NDJSON `framework-events.ndjson`
as immutable Article-III SoT (CQRS read-model split). Replay NDJSON entries
into projection. Migrate 5 JSON state files. Wire Engram via `engram setup <agent>`
per detected IDE. Reduce `/ai-remember` and `/ai-dream` to thin wrappers.

## Source

Full spec: `.ai-engineering/specs/spec-122-b-engram-and-state-unify.md`.

Decisions imported: D-122-05, D-122-06, D-122-16..23, D-122-30, D-122-34, D-122-38.

## Exploration

### Existing Files

**State files (current persistence surface)**:

- `.ai-engineering/state/decision-store.json` (55 B) — `{"active_decisions":[],"superseded":[],"version":"v1"}`. Empty dev state today; production deployments will hold N rows. Migration target → `decisions` table.
- `.ai-engineering/state/gate-findings.json` (59 B) — `{"schema":"ai-engineering/gate-findings/v1","findings":[]}`. Migration target → `gate_findings` table.
- `.ai-engineering/state/ownership-map.json` (5.5 KB) — `{"paths":[...], "schemaVersion":"1.0", "updateMetadata":{...}}`. ~33 path patterns. Migration target → `ownership_map` table.
- `.ai-engineering/state/install-state.json` (2.7 KB) — schema_version 2.0; nested tooling{} with installed/authenticated/integrity_verified flags + hook_hash:* sha256 fingerprints. Migration target → `install_steps` table (one row per top-level tooling key).
- `.ai-engineering/state/hooks-manifest.json` (8.6 KB) — 68 hooks with sha256 fingerprints. **NOT migrated wholesale** — manifest is read-only contract; only mismatches are projected into `hooks_integrity` table from runtime verifications.
- `.ai-engineering/state/framework-events.ndjson` (75.3 KB, 173 lines current; spec assumes 84,679 in mature deployments) — **PRESERVED unchanged** as immutable Article III SoT. Source of truth for the events projection.
- `.ai-engineering/state/instinct-observations.ndjson` (36.8 KB) — observation stream for `/ai-instinct`. **Archived read-only post-migration**; new observations go to `engram save` via `/ai-instinct --review`.
- `.ai-engineering/state/audit-index.sqlite` — DELETE post-merge; superseded by `state.db.events`. (Currently absent in repo — only archived copy in `archive/pre-spec-122-reset-20260505/`.)
- `.ai-engineering/state/memory.db` — DELETE; superseded by Engram. (Currently absent in repo — only archived copy.)
- `.ai-engineering/state/state.db` — **NEW**, single unified projection.

**Memory layer to delete (~2,568 LOC)**:

- `.ai-engineering/scripts/memory/__init__.py` (29 LOC)
- `.ai-engineering/scripts/memory/store.py` (227 LOC) — schema bootstrap + `connect()` context manager + sqlite-vec extension load
- `.ai-engineering/scripts/memory/cli.py` (470 LOC) — Typer CLI surface (`status`, `ingest`, `remember`, `dream`, `repair`, `warmup`)
- `.ai-engineering/scripts/memory/episodic.py` (313 LOC) — episode ingestion
- `.ai-engineering/scripts/memory/knowledge.py` (268 LOC) — knowledge object hashing/upsert
- `.ai-engineering/scripts/memory/semantic.py` (232 LOC) — fastembed wrapper
- `.ai-engineering/scripts/memory/retrieval.py` (311 LOC) — top-K query
- `.ai-engineering/scripts/memory/dreaming.py` (306 LOC) — HDBSCAN consolidation
- `.ai-engineering/scripts/memory/audit.py` (232 LOC) — memory_event emitter
- `.ai-engineering/scripts/memory/repair.py` (180 LOC) — vector rebuild

**Consumer code to refactor**:

- `src/ai_engineering/state/audit_index.py` (613 LOC) — current SQLite projection of NDJSON. **Will be deprecated/folded into the unified `state.db.events` schema** in spec-122-b. Schema in this file (single `events` table + `indexed_lines` checkpoint + 3 rollup views) is functionally identical to the new design but lacks STRICT tables and the GENERATED `archive_month` column.
- `src/ai_engineering/state/audit_chain.py` (~250 LOC) — hash-chain verifier. **Preserved unchanged**; new code consumes existing API (`verify_audit_chain`, `compute_event_hash`).
- `src/ai_engineering/state/audit.py` — `emit_*` event-emission API. **Preserved**; new code wires into existing emission contract.
- `src/ai_engineering/state/service.py` — `load_install_state()` reads/writes `install-state.json`. **Refactored** to read/write `state.db.install_steps` after migration.
- `src/ai_engineering/state/repository.py` — generic JSON I/O wrapper. **Preserved**; sub-002 adds parallel `state_db.py` for SQLite I/O.
- `src/ai_engineering/cli_commands/audit_cmd.py` — current `audit verify | index | query | tokens | replay | otel-export` Typer commands. **Extended** with `retention apply`, `rotate`, `compress`, `verify-chain`, `health`, `vacuum`, plus `query --include-archived`.
- `src/ai_engineering/cli_commands/memory_cmd.py` (60 LOC) — shim that re-exports the canonical `memory.cli` Typer app from `.ai-engineering/scripts/memory/`. **Replaced** by a stub Typer app that prints "memory layer delegated to Engram; use `engram --help`" and exits 0; or unregistered from `cli_factory.py` outright.
- `.ai-engineering/scripts/hooks/runtime-guard.py` — extended to enforce 3 KB event ceiling + sidecar offload at `state/runtime/event-sidecars/<sha256>.json`.

**Skills to thin-wrap**:

- `.claude/skills/ai-remember/SKILL.md` (~90 LOC) — currently `uv run ai-eng memory remember "<query>"`; rewrite to call `engram search --project "<query>"` directly.
- `.claude/skills/ai-dream/SKILL.md` (~80 LOC) — currently `uv run ai-eng memory dream`; rewrite to call `engram save` (or follow Engram's consolidation surface; spec defers to Engram CLI evolution).
- `.claude/skills/ai-instinct/SKILL.md` — `--review` mode currently appends to `instincts.yml`; updated to also `engram save` enriched observations.
- Mirror copies in `src/ai_engineering/templates/project/.{claude,gemini}/skills/ai-{remember,dream}/SKILL.md` MUST be updated in lockstep (scripts/sync_command_mirrors.py is sub-spec d's responsibility but the source SKILL.md is sub-002's).

**Dependency surface**:

- `pyproject.toml` (164 LOC) — has `[project.optional-dependencies.memory]` extra with `sqlite-vec>=0.1,<0.2`, `fastembed>=0.3,<0.5`, `hdbscan>=0.8,<1.0`, `numpy>=1.26,<3.0`. Pytest markers `memory` + `memory_slow` registered. **All four removed**; extra deleted; markers deleted; `--extra memory` paths in CI removed.
- `uv.lock` — regenerated post-deletion via `uv lock` from clean state.

**Installer surface**:

- `src/ai_engineering/installer/service.py` + `tools.py` — handle tooling discovery + install-state persistence. Phase 0 hint: no `install.sh` exists at repo root; install flows go through `ai-eng install` CLI command (`src/ai_engineering/cli_commands/core.py:install_cmd`). New code adds an "engram setup per IDE" step to the install pipeline.

**Tests touched**:

- `tests/unit/memory/` — entire directory (test_store, test_retrieval, test_knowledge, test_semantic, test_repair) DELETE.
- `tests/integration/memory/test_session_lifecycle.py` — DELETE (memory layer gone).
- New: `tests/integration/memory/test_engram_subprocess.py` — mocks `engram` CLI for `/ai-remember` + `/ai-dream` shell-out behavior.
- New: `tests/integration/state/test_db_migration.py` — JSON file ↔ state.db round-trip.
- New: `tests/integration/state/test_outbox_atomic.py` — projection mutation + NDJSON emit single-tx invariant.
- New: `tests/integration/state/test_rotation_chain.py` — monthly rotation hash chain integrity (Crosby/Wallach).
- New: `tests/integration/state/test_retention.py` — 90d HOT cutoff enforcement.
- New: `tests/unit/state/test_connection_pragmas.py` — verifies all 9 PRAGMAs are set on connection open.
- New: `tests/unit/state/test_migration_integrity.py` — `_migrations.sha256` mismatch refuses startup under `enforce` mode.
- New: `tests/unit/state/test_sidecar_overflow.py` — 3 KB+ events offload; inline event carries hash + summary only.

### Patterns to Follow

**Primary exemplar — `src/ai_engineering/state/audit_index.py`**: this file is the closest analog to what `state.db` machinery must look like. It already implements:

- Stdlib-only sqlite3 connection management with `journal_mode=WAL` PRAGMA.
- `IF NOT EXISTS` schema bootstrap (acceptable for additive evolution; will be replaced by migration runner pattern in this sub-spec).
- Idempotent NDJSON-line ingestion with `indexed_lines.last_offset` checkpoint.
- `BEGIN`/`COMMIT` transaction boundaries around batch inserts.
- Read-only URI mode (`?mode=ro`) for query callers.
- Frozen dataclass result type (`IndexResult`) returned by writer, used by CLI.

The new `state_db.py` adopts the same single-module ergonomic, replacing `IF NOT EXISTS` schema with migration-runner-driven evolution and adding the seven new tables alongside `events`. The migration runner pattern follows the spec's documented stdlib-50-LOC contract — no Alembic.

**Migration-runner pattern** (D-122-17): Each migration at `src/ai_engineering/state/migrations/NNNN_<slug>.py` exposes:

```python
BODY_SHA256 = "..."  # sha256 of this file's content modulo this constant

def apply(conn: sqlite3.Connection) -> None:
    """Execute DDL/DML inside an existing BEGIN IMMEDIATE block."""
```

The runner walks `migrations/` in order, `BEGIN IMMEDIATE`s, runs `apply(conn)`, sets `PRAGMA user_version=N`, INSERTs `_migrations(version, applied_at, sha256)`, COMMITs. Failure rolls back. On startup, the runner verifies every recorded `sha256` matches the on-disk file (`AIENG_HOOK_INTEGRITY_MODE=enforce` default per D-122-30).

**Transactional outbox pattern** (D-122-18): Mutations to projection tables are wrapped via a context manager defined in `state_db.py`:

```python
@contextmanager
def projection_write(conn) -> Iterator[OutboxRecorder]:
    conn.execute("BEGIN IMMEDIATE")
    recorder = OutboxRecorder()
    try:
        yield recorder
        for event_dict in recorder.queued:
            emit_event_unbuffered(event_dict)  # NDJSON append
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
```

Callers do `with projection_write(conn) as ob: cur.execute(UPDATE ...); ob.queue(event_dict)`. The single COMMIT spans both the SQL row mutation and the NDJSON emit (post-yield) — eliminating the race window currently present in `decisions_cmd.py:179`.

**NDJSON rotation + hash chain** (D-122-20): Rotation logic in `src/ai_engineering/state/rotation.py`:

1. Acquire `flock` on `state/locks/audit-rotation.lock` (existing locking infra in `state/locking.py`).
2. Read final `prev_event_hash` of closing month → write to `state/audit-archive/YYYY/YYYY-MM.manifest.json`.
3. Open new month file `state/audit-archive/YYYY/YYYY-MM.ndjson`; write a synthetic anchor event whose `prev_event_hash` references the closed month head.
4. Update root `state/audit-archive/hash-chain.json`.
5. Schedule background zstd seekable compress of just-closed month.

Hash chain uses the existing `audit_chain.compute_event_hash()` API.

**Sidecar offload pattern** (D-122-23): Event payloads ≥ 3 KB are written to `state/runtime/event-sidecars/<sha256>.json` (content-addressed, deterministic), and the inline NDJSON event carries only `{"sidecar_sha256": "...", "summary": "..."}`. The 3 KB ceiling is enforced in `runtime-guard.py` PostToolUse hook (which already implements `AIENG_TOOL_OFFLOAD_BYTES` for tool outputs — same pattern, different threshold + path).

**Engram delegation pattern** (D-122-05, D-122-38): `/ai-remember` skill body becomes:

```
1. Run: engram search --project "<query>" --top-k 10 --json
2. Parse JSON. Render compact bulleted list.
3. On binary missing: fail clean with install hint.
```

No per-IDE MCP template ships. `ai-eng install` calls `subprocess.run(["engram", "setup", agent])` per detected IDE in `installer/service.py`. Engram writes its own MCP block into the IDE-native settings file.

### Dependencies Map

**Inbound (this sub-spec consumes)**:

- From sub-001 (Hygiene): clean `pyproject.toml` (no orphan markers post-evals delete), clean `manifest.yml`, Constitution dedupe complete, `wire-memory-hooks.py` already deleted (D-122-14).
- Stdlib only for `state_db.py` core: `sqlite3`, `json`, `hashlib`, `pathlib`, `time`, `datetime`, `contextlib`, `dataclasses`. **No new third-party deps**.
- Existing framework infra: `state/audit_chain.compute_event_hash`, `state/locking.artifact_lock`, `state/io.read_json_model`, `state/audit.emit_*`.

**Outbound (this sub-spec exposes)**:

- `state_db.connect()` → `sqlite3.Connection` with all 9 PRAGMAs set.
- `state_db.projection_write(conn)` → context manager for atomic projection+event mutations.
- `migrations.run_pending(conn)` → applies all migrations gated by `_migrations.sha256` integrity check.
- `rotation.rotate_now()` → CLI entry for `ai-eng audit rotate`.
- `retention.apply(keep_days)` → CLI entry for `ai-eng audit retention apply`.
- `sidecar.maybe_offload(event_dict, ceiling_bytes)` → 3 KB sidecar dispatcher used by hooks.
- New audit CLI subcommands: `retention apply`, `rotate`, `compress`, `verify-chain`, `health`, `vacuum`, `query --include-archived`.
- Updated `ai-eng install` engram-setup step.

**Sub-spec d (meta-cleanup, depends on this)**: consumes the new audit CLI surface for `docs/cli-reference.md` updates (D-122-25), CHANGELOG entries (D-122-37), and template-skill mirror updates via `scripts/sync_command_mirrors.py`.

**External dependency**: Engram CLI (`/opt/homebrew/bin/engram` v1.15.8+, MIT, brew on mac/linux, winget/binary on Windows). Pinned in `manifest.yml required_tools.baseline.engram = ">=1.15.8,<1.16"` (sub-001 surface).

### Risks

1. **NDJSON entry count mismatch — spec claims 84,679 events, repo has 173.** Spec language treats 84k as exemplar production scale, not a rebuild target. Mitigation: replay logic is data-volume-agnostic (`ON CONFLICT(span_id) DO NOTHING` + checkpoint); migration succeeds with N events for any N. Acceptance criterion `count >= 84679` re-stated as `count == wc -l framework-events.ndjson` in plan.md — verifiable on every machine.

2. **memory.db absent in current repo state — listed in `files:` for completeness.** Repo currently has only `archive/pre-spec-122-reset-20260505/memory.db`. Mitigation: deletion is no-op when target absent (`Path.unlink(missing_ok=True)`); plan accommodates both fresh-deploy and active-deploy paths.

3. **No `install.sh` at repo root.** Master spec references `scripts/install.sh` but it does not exist; `ai-eng install` CLI is the actual installer entry point (`src/ai_engineering/cli_commands/core.py:install_cmd`). Mitigation: engram-setup wiring lands in `installer/service.py` (the actual installer pipeline), not `scripts/install.sh`. `files:` updated accordingly.

4. **STRICT table compatibility with existing `audit_index.py` consumers.** The current `events` schema (`audit_index.py` line 55) is non-STRICT and lacks GENERATED columns. Mitigation: 0001_initial_schema.py creates STRICT schema in `state.db` (new file); 0003_replay_ndjson.py reads NDJSON line-by-line into STRICT table; old `audit-index.sqlite` deprecated (already gitignored, .ai-engineering/state/audit-index.sqlite). Existing `audit_index.py` is rewired to point at `state.db` post-migration but its public API (`build_index`, `open_index_readonly`, `IndexResult`) is preserved for backward compat with the audit CLI.

5. **`_outbox` table vs in-process emit_event — spec is ambiguous between two patterns.** The spec section D-122-18 mentions both "via an in-DB `_outbox` queue or via `emit_event()` immediately preceded by a successful row write". Mitigation: chose in-process post-yield emit (simpler; no separate flusher thread; documented in plan T-2.5). The "in-DB outbox queue" alternative is reserved for future scale where async flush is needed.

6. **Migration runner sha256 — locking discipline for source edits.** Editing a migration file after it was applied violates the integrity check. Mitigation: documented in `migrations/__init__.py` docstring + plan.md adds `ai-eng audit migration-rebase` (controlled re-record path) as future work, not this sub-spec.

7. **Engram subprocess overhead vs in-process embedding.** Engram CLI invocation adds ~50 ms per call vs ~5 ms in-process. Mitigation: SessionStart bootstrap pre-warms via `engram context`; per-skill latency budget unchanged. Test coverage in `test_engram_subprocess.py` asserts subprocess call count + smoke-test latency.

8. **Cross-IDE concurrent NDJSON write race on non-POSIX FS.** NFS, HDFS, SMB do not guarantee `O_APPEND` atomicity for writes ≤ PIPE_BUF. Mitigation: `ai-eng doctor` warns when repo is on a non-POSIX FS; documentation marks NFS / HDFS / SMB as unsupported. (Implementation deferred to sub-spec d's docs pass; sub-002 only enforces 3 KB ceiling.)

9. **Migration ordering — JSON files depend on `events` table existing first.** Replay (0003) must run AFTER seed (0002) only if seed events reference `events` rows. Mitigation: 0002_seed_from_json operates on dimension tables (`decisions`, `gate_findings`, `ownership_map`, `install_steps`) which have no FK to `events`; ordering is `0001 initial schema → 0002 seed dimension tables → 0003 replay events from NDJSON`. Each migration is independently runnable.

10. **Memory CLI deletion breaks pytest markers.** `pyproject.toml` registers `memory` and `memory_slow` markers; pytest will warn on unknown markers if collected with `-m memory`. Mitigation: marker registrations removed in same change; CI workflow `--extra memory` paths removed; verified by `tests/unit/state/test_no_memory_marker_referenced.py` (added if needed).

## Acceptance

See source spec. Summary:
- `state.db` exists with 7 STRICT tables + `_migrations`
- `events` table populated with rows from NDJSON replay (≥ wc -l framework-events.ndjson)
- 5 JSON files migrated round-trip
- Migration runner with sha256 integrity check
- Transactional outbox (`BEGIN IMMEDIATE` for projection + NDJSON emit)
- NDJSON rotation monthly OR 256MB; closed months → zstd seekable; hash chain spans rotations
- Cross-IDE concurrent write safety (events ≥ 3KB → sidecar)
- `ai-eng audit retention/rotate/compress/verify-chain/health/vacuum` subcommands
- Engram delegation: `ai-eng install` invokes `engram setup <agent>` per IDE
- `/ai-remember` + `/ai-dream` reduced to thin wrappers
- `pyproject.toml` cleaned (sqlite-vec, fastembed, hdbscan removed; memory extra dropped)
- `memory.db` + `scripts/memory/` deleted
