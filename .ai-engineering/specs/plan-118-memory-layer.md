# Plan: spec-118 Memory Layer

## Pipeline: full
## Phases: 5
## Tasks: 34 (build: 29, verify: 3, guard: 2)

## Architecture

modular-monolith

spec-118 adds a new bounded module `memory/` to the existing single-deployable framework. The memory module owns durable state at `.ai-engineering/state/memory.db`, exposes a Typer CLI surface (`ai-eng memory ...`), and is invoked by stdlib-only hooks through subprocess. No new deployable, no new runtime boundary, no schema split. Internal seams: `store` (SQLite + sqlite-vec), `episodic` and `knowledge` (writers), `semantic` (embedding), `retrieval` (read), `dreaming` (consolidation), `repair` (data hygiene), `audit` (event emission), `cli` (entry points). External seams that must not regress: `_lib/observability.py` audit chain, `_lib/instincts.py` extraction, hooks-manifest integrity, audit-event schema, manifest skill registry. Mirrors propagate via `ai-eng sync-mirrors` after canonical landings.

### Phase 1: Foundation - Audit Schema, Deps, Repair, Store
**Gate**: One audit kind `memory_event` is registered, `pyproject.toml` carries the required deps, the `memory/store.py` schema bootstraps idempotently with `PRAGMA user_version = 1`, and `ai-eng memory repair --backfill-timestamps` heals existing `instinct-observations.ndjson` records without data loss on a working copy.
- [ ] T-1.1: Add `sqlite-vec`, `fastembed`, `hdbscan`, `numpy` to `pyproject.toml` and register pytest markers `memory` and `memory_slow` (agent: build).
- [ ] T-1.2: Extend `_ALLOWED_KINDS` in `.ai-engineering/scripts/hooks/_lib/observability.py:24` with `memory_event` and confirm hash-chain emission stays unchanged for existing kinds (agent: build, blocked by T-1.1).
- [ ] T-1.3: Add `$defs/detail_memory_event` and the matching discriminated `allOf` branch to `.ai-engineering/schemas/audit-event.schema.json` covering operations `episode_stored`, `knowledge_object_added`, `memory_retrieved`, `dream_run`, `decay_applied`, `knowledge_object_promoted`, `knowledge_object_retired` (agent: build, blocked by T-1.2).
- [ ] T-1.4: Harden empty-stdin handling in `.ai-engineering/scripts/hooks/instinct-observe.py` and `.ai-engineering/scripts/hooks/copilot-adapter.py:46`; defensively coerce empty-string `lastExtractedAt` to null inside `_lib/instincts.py::_load_meta` (agent: build, blocked by T-1.3).
- [ ] T-1.5: Implement `.ai-engineering/scripts/memory/repair.py` with `backfill_timestamps()` that reads the on-disk NDJSON, fills missing timestamps from the available evidence (line position relative to file mtime when no better source exists), and rewrites the file atomically; expose it through `ai-eng memory repair --backfill-timestamps` (agent: build, blocked by T-1.4).
- [ ] T-1.6: Implement `.ai-engineering/scripts/memory/store.py` with `bootstrap()` covering the `episodes`, `knowledge_objects`, `vector_map`, and `retrieval_log` tables, the indices listed in the spec, and the deferred `memory_vectors` virtual-table creation gated on the sqlite-vec extension load (agent: build, blocked by T-1.5).
- [ ] T-1.7: Implement `.ai-engineering/scripts/memory/audit.py` as the single emitter for `memory_event` records; route through `_lib/observability.py::append_framework_event` and validate detail shape against `audit-event.schema.json` in tests (agent: build, blocked by T-1.6).
- [ ] T-1.8: Run a governance review on the audit-event extension, hook-manifest impact, ownership boundary between `memory/`, `hooks/`, and `_lib/`, and the repair script's data-handling semantics before any writers ship (agent: guard, blocked by T-1.7).

### Phase 2: Writers - Episodic, Knowledge Objects, Stop Hook
**Gate**: A real Stop event produces a valid episode row plus a `memory_event/episode_stored` audit entry, the `knowledge_objects` table populates from `LESSONS.md`, `decision-store.json`, and `instincts.yml` without duplication, and `instinct-extract.py` extraction counts before and after Phase 2 are unchanged.
- [ ] T-2.1: Implement `.ai-engineering/scripts/memory/episodic.py` with `write_episode()` that reads `framework-events.ndjson` and `runtime/checkpoint.json`, computes a rule-based summary, and writes one row to `episodes`; emit `memory_event/episode_stored` (agent: build, blocked by T-1.8).
- [ ] T-2.2: Implement `.ai-engineering/scripts/memory/knowledge.py` with `ingest_lessons()`, `ingest_decisions()`, `ingest_instincts()`, and `ingest_all()` that hash canonical content with sha256 and upsert idempotently, recording provenance and metadata (agent: build, blocked by T-2.1).
- [ ] T-2.3: Implement `.ai-engineering/scripts/memory/cli.py` with subcommands `ingest`, `repair`, and `status`; wire the CLI into `src/ai_engineering/cli_factory.py` so `ai-eng memory ...` is reachable (agent: build, blocked by T-2.2).
- [ ] T-2.4: Implement `.ai-engineering/scripts/hooks/memory-stop.py` (stdlib-only) that locates the project root, reads the existing checkpoint, and shells to `python3 -m ai_engineering.memory.cli stop ...`; wire it into `.claude/settings.json` Stop block after `runtime-stop.py` (agent: build, blocked by T-2.3).
- [ ] T-2.5: Regenerate `.ai-engineering/state/hooks-manifest.json` via `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py` and confirm `--check` is clean (agent: build, blocked by T-2.4).
- [ ] T-2.6: Add unit coverage in `tests/unit/memory/` for store schema idempotency, episodic write round-trip, knowledge-object hashing and dedup, and audit-event emission against the JSON Schema (agent: build, blocked by T-2.5).
- [ ] T-2.7: Run targeted verification: full Phase 1 plus Phase 2 unit suites, schema validation on a sampled tail of `framework-events.ndjson`, and a comparison of pre-/post-extract instinct counts (agent: verify, blocked by T-2.6).

### Phase 3: Semantic Tier and Retrieval
**Gate**: `ai-eng memory remember "<seeded query>"` returns deterministic top-K results in CI with the stub embedder, cold-start time after `ai-eng memory warmup` stays under 5 s, and refuse-to-start fires correctly on a synthetic dimension mismatch.
- [ ] T-3.1: Implement `.ai-engineering/scripts/memory/semantic.py` with lazy `_get_embedder()` (no fastembed import at module level), `embed_batch()`, `upsert_vector()`, and a refuse-to-start check that compares `vector_map.embedding_model`/dim against the active embedder (agent: build, blocked by T-2.7).
- [ ] T-3.2: Extend `memory-stop.py` to dispatch fire-and-forget embedding through `subprocess.Popen` after the synchronous episode write; record `embedding_status` in the emitted `episode_stored` event (agent: build, blocked by T-3.1).
- [ ] T-3.3: Implement `.ai-engineering/scripts/memory/retrieval.py` with `search()` that runs sqlite-vec cosine search, joins through `vector_map`, applies `decayed_importance * cosine_similarity` rerank, and supports `kind`, `since`, and `top_k` filters; log to `retrieval_log` and emit `memory_event/memory_retrieved` (agent: build, blocked by T-3.2).
- [ ] T-3.4: Extend `cli.py` with subcommands `remember` and `warmup`; warmup pre-downloads ONNX weights and writes a status line for `/ai-start` (agent: build, blocked by T-3.3).
- [ ] T-3.5: Add unit coverage in `tests/unit/memory/` using a deterministic embedder fixture (`np.random.RandomState(hash(text)).rand(384)` normalized): semantic upsert and join, retrieval rerank math, kind/since filters, refuse-to-start on dim mismatch (agent: build, blocked by T-3.4).
- [ ] T-3.6: Run targeted verification including a `memory_slow` opt-in pass that loads the real fastembed model on a developer machine and asserts cold-start latency budget (agent: verify, blocked by T-3.5).

### Phase 4: Dreaming, Skills, Mirror Sync
**Gate**: `ai-eng memory dream --dry-run` reports non-empty supersedence and proposal candidates on a seeded corpus, `ai-eng memory dream` writes `.ai-engineering/instincts/memory-proposals.md` and never mutates `LESSONS.md`, the manifest skill count moves from 49 to 51, and `ai-eng sync-mirrors` propagates `/ai-remember` and `/ai-dream` to `.gemini/`, `.codex/`, `.github/` without diff drift.
- [ ] T-4.1: Implement `.ai-engineering/scripts/memory/dreaming.py` with `apply_decay()` (`importance * 0.97^days_since_last_seen`), `cluster_with_hdbscan()` honoring the small-corpus early-exit at < 30 KOs, `mark_supersedence()`, `archive_below_threshold()`, and `propose_promotions()` that writes to `memory-proposals.md` (agent: build, blocked by T-3.6).
- [ ] T-4.2: Extend `cli.py` with `dream [--dry-run] [--decay-only] [--min-cluster-size=N] [--decay-base=R]`; emit one `memory_event/dream_run` per call with `clusters_found`, `promoted_count`, `retired_count`, and `decay_factor` (agent: build, blocked by T-4.1).
- [ ] T-4.3: Author canonical skill `.claude/skills/ai-remember/SKILL.md` with frontmatter (effort: low, model: sonnet, tools: Bash); the body invokes `ai-eng memory remember "$ARGS" --json` and renders a compact bulleted result with provenance (agent: build, blocked by T-4.2).
- [ ] T-4.4: Author canonical skill `.claude/skills/ai-dream/SKILL.md` with frontmatter (effort: medium, model: sonnet, tools: Bash, Read); the body runs `--dry-run` first, asks for explicit human approval, then runs without `--dry-run` and prints the proposals path (agent: build, blocked by T-4.3).
- [ ] T-4.5: Update `.ai-engineering/manifest.yml` to register `ai-remember` and `ai-dream` (skill count 49 -> 51) and bump any totals or metadata that the manifest schema validates (agent: build, blocked by T-4.4).
- [ ] T-4.6: Run `uv run ai-eng sync-mirrors` and confirm canonical-to-mirror parity for the new skills under `.gemini/`, `.codex/`, and `.github/` surfaces (agent: build, blocked by T-4.5).
- [ ] T-4.7: Add unit coverage in `tests/unit/memory/` for decay arithmetic (`0.97**30 ~ 0.401`), HDBSCAN early-exit with `clusters_found = 0`, supersedence assignment, archival flip, and the proposal markdown rendering (agent: build, blocked by T-4.6).
- [ ] T-4.8: Run a governance review on the manifest delta, sync-mirrors output, and the proposals-only authority boundary over `LESSONS.md` (agent: guard, blocked by T-4.7).

### Phase 5: Cross-Session Injection and End-to-End Proof
**Gate**: A new Claude session presents a relevant prior episode in the welcome banner, the SessionStart hook stays under 1.5 s p95, the integration suite passes end-to-end, and `uv run ai-eng validate -c cross-reference` plus `-c file-existence` are green.
- [ ] T-5.1: Implement `.ai-engineering/scripts/hooks/memory-session-start.py` (stdlib-only) that reads `runtime/checkpoint.json` and the active work-plane pointer to derive a recovery-context query, shells to `ai-eng memory remember --top-k 5 --json`, and writes a banner block to stdout for IDE injection (agent: build, blocked by T-4.8).
- [ ] T-5.2: Wire `SessionStart` in `.claude/settings.json` ahead of any other startup hooks; document the Codex/Gemini sentinel synthesis path (`runtime/session-bootstrap-${session_id}.flag`) without changing the bridge code in this spec (agent: build, blocked by T-5.1).
- [ ] T-5.3: Regenerate `.ai-engineering/state/hooks-manifest.json` and confirm `--check` is clean (agent: build, blocked by T-5.2).
- [ ] T-5.4: Add `tests/integration/memory/test_session_lifecycle.py` and `tests/integration/memory/test_cli_remember.py` covering Stop -> SessionStart round-trip with stubbed stdin and a CLI `remember` round-trip against a seeded `memory.db` (agent: build, blocked by T-5.3).
- [ ] T-5.5: Run the focused end-to-end proof for spec-118: full memory unit and integration suites, `python3 -m jsonschema` validation against the audit-event schema, `uv run ai-eng validate -c cross-reference`, and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.4).

## Sequencing Notes

- Each phase ends with the existing instinct subsystem in a working state. Rollback at any phase keeps earlier phases functional because no later phase has a hard dependency on a future one.
- Hook-manifest regeneration is required at the end of any phase that adds or modifies a hook script (T-2.5, T-5.3) to prevent integrity-check failures in enforce mode.
- The manifest skill-count update (T-4.5) must precede `ai-eng sync-mirrors` (T-4.6) so mirrors render with the correct skill registry.
- Audit-schema changes (T-1.3) and emitter (T-1.7) ship in the same phase as the kind addition (T-1.2) so schema validation never sees an unrecognized kind in the wild.
- The repair pass (T-1.5) executes before any episode or knowledge-object write to keep observation timestamps trustworthy when episodic summarization derives from them.
- Phase 5 lands Claude only; cross-IDE bridge synthesis is documented and filed as follow-up work, not part of this plan's gates.

## Exit Conditions

- One canonical memory module exists at `.ai-engineering/scripts/memory/` with `store`, `episodic`, `knowledge`, `semantic`, `retrieval`, `dreaming`, `repair`, `audit`, `cli` submodules.
- One audit kind `memory_event` is registered with seven discriminated sub-operations, schema-validated.
- Two canonical skills `/ai-remember` and `/ai-dream` are registered in `manifest.yml`, mirrored across enabled IDE surfaces.
- Two canonical hooks `memory-stop.py` and `memory-session-start.py` are wired into `.claude/settings.json` and recorded in `hooks-manifest.json`.
- The instinct subsystem timestamp regression is repaired on disk and defensively guarded in code.
- `LESSONS.md` is never mutated by the framework; promotion candidates land in `memory-proposals.md` for human review.
- The full memory unit and integration suites pass; audit-event schema validation passes; `uv run ai-eng validate -c cross-reference` and `-c file-existence` pass.
