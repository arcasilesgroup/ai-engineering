---
spec: spec-118
title: Memory Layer - Episodic, Semantic, Knowledge Objects, Dreaming, and Cross-Session Retrieval
status: approved
effort: large
---

# Spec 118 - Memory Layer

## Summary

ai-engineering exposes only one working memory tier today: **procedural** memory expressed in canonical entry-point and governance files (`AGENTS.md`, `CLAUDE.md`, `CONSTITUTION.md`, `LESSONS.md`). The instinct subsystem at `.ai-engineering/scripts/hooks/_lib/instincts.py` attempts capture and extraction but is degraded in production: `meta.json:lastExtractedAt` is the empty string, which forces re-processing of every observation on every Stop hook, and `instinct-observations.ndjson` records carry empty `timestamp` fields, defeating delta filtering. There is no semantic retrieval, no episodic store, no cross-session context injection, and no consolidation loop. Each new agent invocation enters cold.

This spec adds the four missing tiers required for compounding learning across sessions, anchored in the existing audit chain and Constitution Article V single-source-of-truth contract:

1. **Episodic memory** at the Stop hook: each session writes a structured episode (work plane, tools, skills, agents, files, outcomes, rule-based summary) sourced from `framework-events.ndjson` and `runtime/checkpoint.json`.
2. **Knowledge Objects (KO)**: hash-addressed (sha256) facts ingested from `LESSONS.md` sections, `decision-store.json`, `instincts.yml` corrections/recoveries/workflows, and spec deltas. One canonical row per fact with provenance, importance, and supersedence chain.
3. **Semantic tier**: SQLite at `.ai-engineering/state/memory.db` with the `sqlite-vec` extension, embedding episodes and KOs through `fastembed` (BAAI/bge-small-en-v1.5, 384-dim, ONNX, lazy-loaded).
4. **Dreaming loop**: manual or scheduled consolidation that applies exponential decay (`importance * 0.97^days`), clusters via HDBSCAN, marks duplicates with `superseded_by`, archives entries below the importance threshold, and writes promotion candidates to `memory-proposals.md` (mirrors the existing `instincts/proposals.md` review pattern).
5. **Cross-session retrieval**: a new `/ai-remember` skill plus a SessionStart hook that auto-injects top-K relevant prior episodes and lessons into the new session.

## Goals

- Provide compounding learning so the framework instinct ratchet works in production: every recurring mistake or recovery becomes retrievable evidence on the next session.
- Extend the audit chain with a single new event kind `memory_event` (discriminated by `detail.operation`), preserving regulated-industry tamper-evident properties while keeping `_ALLOWED_KINDS` small.
- Keep canonical paths and ownership boundaries intact: skills authored under `.claude/skills/` (canonical), hooks at `.ai-engineering/scripts/hooks/`, memory module at `.ai-engineering/scripts/memory/`, durable state at `.ai-engineering/state/memory.db` (gitignored, per-user).
- Preserve hot-path discipline: SessionStart under 1.5 s p95, Stop episode write synchronous and small, embedding work delegated to fire-and-forget subprocess.
- Preserve human authority over `LESSONS.md`: dreaming proposes, never mutates the canonical lessons file.
- Run cross-IDE: state and CLI live at canonical locations; skills propagate through `ai-eng sync-mirrors` to `.gemini/`, `.codex/`, `.github/`.
- Repair the existing instinct subsystem: backfill empty timestamps, defensively coerce empty-string `lastExtractedAt` to null, harden empty-stdin handling in observation hooks.

## Non-Goals

- LLM-generated session summaries (v1 uses a rule-based template; LLM summarization is follow-up work).
- Encryption of `memory.db` at rest (relies on host filesystem encryption such as FileVault; documented assumption).
- MMR reranking (placeholder; v1 uses `decayed_importance * cosine_similarity`).
- Distributed memory across machines or shared team memory (single-node, per-developer).
- Replacement of the existing `/ai-instinct` and `/ai-learn` skills (they remain unchanged; `/ai-remember` and `/ai-dream` are new).
- Cross-IDE bridge edits for Copilot and Gemini SessionStart synthesis (Phase 5 lands Claude only; bridge synthesis filed as follow-up work in spec-118 progress).

## Decisions

### D-118-01: One new audit event kind, discriminated by `detail.operation`

The framework will add a single new value `memory_event` to `_ALLOWED_KINDS` in `.ai-engineering/scripts/hooks/_lib/observability.py`. Sub-operations live in the `detail.operation` enum: `episode_stored`, `knowledge_object_added`, `memory_retrieved`, `dream_run`, `decay_applied`, `knowledge_object_promoted`, `knowledge_object_retired`. The audit-event JSON Schema gets a matching `$defs/detail_memory_event` and an `allOf` discriminated branch.

**Rationale**: Seven new top-level kinds would inflate `_ALLOWED_KINDS` and the discriminated union for a single subsystem. The `framework_operation` precedent at `observability.py` already shows the framework's preference for sub-typing through detail fields rather than expanding the kind enum. Keeping the surface small protects the audit chain from churn while still letting validators and consumers filter by sub-operation.

### D-118-02: Hash-addressed Knowledge Objects with provenance

Knowledge Objects are keyed by `sha256(canonical_text)`. Re-ingesting the same canonical text never duplicates; flipping a single character produces a new row. Each KO records source provenance (`source_path`, `source_anchor`), kind enum, importance, last-seen timestamp, retrieval count, and an optional `superseded_by` pointer. Archival is a soft flag, not a delete.

**Rationale**: Hash-addressing makes KOs immutable evidence and gives dreaming a deterministic identity for clustering and supersedence. Soft archival preserves audit history. Provenance lets retrieval surface citations alongside content, which is how the framework already handles decision-store entries and instinct evidence.

### D-118-03: Local embedding backend (`fastembed`) over remote APIs

The framework will embed locally with `fastembed` (default model BAAI/bge-small-en-v1.5, 384-dim, ONNX). The model is lazy-loaded inside `semantic.py`; `memory.db` can be opened, episodes written, and KOs hashed without paying the model load cost. The `fastembed` ONNX weights cache to `~/.cache/fastembed/`; an `ai-eng memory warmup` subcommand pre-downloads them.

**Rationale**: Regulated-industry adopters cannot send session content to external APIs without explicit data-handling review. Local embedding keeps inference deterministic and offline-capable. ONNX gives competitive throughput against torch-backed `sentence-transformers` while avoiding the ~2 GB torch dependency. The 384-dim default fits sqlite-vec efficiently and matches the bge-small benchmark profile.

### D-118-04: Dreaming proposes, never mutates `LESSONS.md`

The dream loop writes promotion candidates to `.ai-engineering/instincts/memory-proposals.md` for human review. `LESSONS.md` remains human-authored or human-approved. Supersedence and archival happen inside `memory.db`; nothing in the canonical lessons file changes without an explicit human commit.

**Rationale**: Human authority over canonical learning files is a governance invariant established by the existing `proposals.md` pattern. Auto-promotion would risk silently rewriting rules and would bypass the review loop that earlier specs (115, 116) protected.

### D-118-05: HDBSCAN early-exit on small corpora

When the active KO count is below 30, dreaming skips clustering, applies decay only, and emits `dream_run` with `clusters_found = 0` and outcome `noop_small_corpus`. This avoids HDBSCAN flagging almost everything as noise on bootstrapping repos.

**Rationale**: HDBSCAN with `min_cluster_size = 3` is unstable below ~50 points; on a fresh install we would either hide all entries or invent spurious clusters. Early-exit keeps the audit signal honest and avoids confusing first-run users.

### D-118-06: Refuse-to-start on embedding-model dimension mismatch

If `vector_map.embedding_model` records a model whose dimension does not match the active embedder, the memory CLI exits with a clear error directing the user to run `ai-eng memory repair --rebuild-vectors`. The framework does not silently re-embed in the background.

**Rationale**: vec0 cannot mix dimensions in one virtual table. Silent re-embedding can spend minutes on first call and may be undesired (downgrade vs upgrade). An explicit migration command keeps the operator in control and the audit chain truthful.

### D-118-07: Stop hook latency is bounded by fire-and-forget embedding

The Stop hook writes the episode synchronously (cheap SQLite insert under ~10 ms) and dispatches embedding to a detached `subprocess.Popen` that writes back to `memory.db` and emits its own `memory_event`. The latest session is queryable for keyword filters immediately and for semantic search after the child finishes (typically under 2 s post-Stop).

**Rationale**: The CLAUDE.md hot-path budget caps Stop work. Loading the ONNX model on the hook thread would push p95 well past the budget. The fire-and-forget pattern keeps the user-visible Stop fast while still completing semantic indexing in seconds.

### D-118-08: SessionStart auto-injection lands Claude-first

Phase 5 wires `SessionStart` only in `.claude/settings.json`. Codex and Gemini bridges synthesize an equivalent event via a sentinel file at `.ai-engineering/state/runtime/session-bootstrap-${session_id}.flag` written on the first `PreToolUse`. Copilot synthesis is filed as follow-up.

**Rationale**: Claude has a native `SessionStart` event; Codex and Gemini do not. Synthesizing a once-per-session sentinel keeps memory injection optional and decoupled from the bridge code. Landing Claude first keeps spec-118 deliverable while the cross-IDE work proceeds in parallel.

### D-118-09: Repair pass over runtime-only code change for the timestamp regression

The empty-timestamp problem in `instinct-observations.ndjson` is a data-on-disk regression, not a current code path defect: `_iso_now()` returns valid ISO timestamps. The fix is `memory/repair.py --backfill-timestamps` operating on the on-disk records, plus a defensive coerce in `_lib/instincts.py::_load_meta` to map empty-string `lastExtractedAt` to null. The regression's likely origin (the `.repair-backup` file) is investigated and noted in the repair log.

**Rationale**: Editing runtime code to handle inconsistent on-disk state would mask the underlying regression. Repair-then-coerce makes the data healthy and adds a safety net without burying the bug.

### D-118-10: Skill ownership boundary for `/ai-remember` and `/ai-dream`

The new skills are authored canonically at `.claude/skills/ai-remember/SKILL.md` and `.claude/skills/ai-dream/SKILL.md`. They invoke the framework CLI through `ai-eng memory remember` and `ai-eng memory dream`; they do not import the memory package directly. Mirrors propagate through `ai-eng sync-mirrors`.

**Rationale**: Article V SSOT requires one canonical location. Calling through the CLI keeps the skill body small and shell-portable across IDE surfaces and avoids embedding Python imports inside skill markdown.

## Footprint (`uv sync --extra memory`)

Indicative on-disk costs (Python 3.12, macOS arm64). Adopters in regulated
industries should verify before approving the extra:

| Component | Approx size | Notes |
|---|---|---|
| `fastembed` site-packages | 30 MB | Pulls onnxruntime + tokenizers |
| `sqlite-vec` site-packages | 6 MB | Compiled extension + Python shim |
| `hdbscan` + `numpy` site-packages | 65 MB | numpy is the dominant cost |
| `BAAI/bge-small-en-v1.5` ONNX cache | 130 MB | `~/.cache/huggingface` after first warmup |
| `memory.db` per project (steady-state) | 5–50 MB | grows with episodes + KOs; archived rows compacted by `/ai-dream` |

Total marginal install cost: **~230 MB site-packages + ~130 MB model cache**.

The hook hot path stays stdlib-only — `memory-stop.py` and
`memory-session-start.py` shell out to a subprocess for any fastembed work,
so a project that does not run `uv sync --extra memory` still gets full
hook integrity, just no semantic retrieval.

## Evidence to Keep

The full memory stack (episodic + semantic + dreaming) is justified only if
adopters actually retrieve relevant prior context. After 30 days of real use
the following metrics gate the **semantic** and **dreaming** tiers; if they
miss, drop those tiers and keep only Phase 1 (episodic + keyword search):

1. `ai-eng memory status` shows ≥ 100 episodes AND ≥ 30 knowledge objects
   ingested from `LESSONS.md` / `decision-store.json` / instincts.
2. At least 3 documented sessions where keyword/recency search over
   `framework-events.ndjson` would have **missed** an obviously relevant
   prior episode that semantic retrieval surfaced.
3. Dreaming has produced at least 1 promotion proposal that a human
   accepted into `LESSONS.md` or `instincts.yml`.

If any condition fails after 30 days, follow the Removal Procedure below.

## Removal Procedure

If the memory hypothesis fails to clear the evidence bar:

**Cheap to remove (clean delete):**
- `.ai-engineering/scripts/memory/` (10 modules)
- `.ai-engineering/scripts/hooks/memory-stop.py`, `memory-session-start.py`
- `.claude/skills/ai-remember/`, `.claude/skills/ai-dream/` (× 4 mirrors)
- `memory.db` (gitignored; per-project)
- `[memory]` extra in `pyproject.toml`
- Wire-up in `.claude/settings.json` (PostToolUseFailure + SessionStart)
- This spec, `decision-store.json` D-118-* entries, and references in
  spec-116 / spec-117

**Sticky to remove (legacy support window):**
- `memory_event` in `audit-event.schema.json` `_ALLOWED_KINDS` cannot be
  removed cleanly once events are emitted to `framework-events.ndjson` —
  external NDJSON validators would reject historical lines. Treat the
  kind as **legacy-only**: keep schema acceptance, emit nothing new.
- Any human-curated lesson promoted via `instincts/memory-proposals.md`
  loses its lineage marker. Strip the marker on retire.

Document the migration plan in a new spec (e.g. `spec-118-retirement.md`)
and bump the framework minor version. Do not remove silently.

## Risks

- **Latency drift on cold first run**: even with lazy fastembed, the first `/ai-remember` after a fresh install pays the ONNX download cost. **Mitigation**: `ai-eng memory warmup` documented in `/ai-start` flow; a slow-warmup test asserts < 5 s after warmup.
- **Audit schema validation regressions**: extending `audit-event.schema.json` with `additionalProperties: false` means any drift in emitted detail fields fails validation. **Mitigation**: emission helper in `memory/audit.py` is the only writer; schema validation runs in CI on a sampled NDJSON tail.
- **HDBSCAN nondeterminism in tests**: HDBSCAN ordering can vary across builds. **Mitigation**: test embeddings are seeded by `np.random.RandomState(hash(text))`; assertions check cluster membership sets, not labels.
- **Hook-manifest drift**: adding new hooks without regenerating `hooks-manifest.json` will trigger the integrity check in enforce mode. **Mitigation**: each phase that touches hooks ends with `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py` and a CI guard that runs `--check`.
- **Cross-IDE skill parity**: until `ai-eng sync-mirrors` runs, `/ai-remember` exists only under `.claude/`. **Mitigation**: Phase 4 includes the mirror sync; the gate fails until mirrors are present in `.gemini/skills/ai-remember/SKILL.md` and equivalents.
- **Embedding model upgrade lock-in**: `vector_map.embedding_model` makes upgrades explicit but disruptive. **Mitigation**: `ai-eng memory repair --rebuild-vectors` is documented; the refuse-to-start error names the exact command.
- **`memory.db` size growth**: long-running repos will accumulate episodes and KOs. **Mitigation**: dreaming archives by importance; `ai-eng memory status` reports row counts and DB size; future spec can add archival pruning.
- **Instinct subsystem compatibility**: existing `instinct-extract.py` runs before `memory-stop.py` in the Stop chain. **Mitigation**: Phase 2 gate verifies extracted instinct counts before and after are unchanged.
- **Subprocess fire-and-forget orphan**: detached embedding processes that crash silently can leave KOs unembedded. **Mitigation**: `ai-eng memory status` reports rows missing vectors; `ai-eng memory repair --rebuild-vectors` re-embeds them; an audit `memory_event/episode_stored` records `embedding_status = pending|complete|failed`.

## References

- doc: AGENTS.md
- doc: CLAUDE.md
- doc: CONSTITUTION.md
- doc: .ai-engineering/manifest.yml
- doc: .ai-engineering/LESSONS.md
- doc: .ai-engineering/instincts/instincts.yml
- doc: .ai-engineering/instincts/meta.json
- doc: .ai-engineering/instincts/proposals.md
- doc: .ai-engineering/state/decision-store.json
- doc: .ai-engineering/state/framework-events.ndjson
- doc: .ai-engineering/state/instinct-observations.ndjson
- doc: .ai-engineering/state/hooks-manifest.json
- doc: .ai-engineering/state/runtime/checkpoint.json
- doc: .ai-engineering/scripts/hooks/_lib/observability.py
- doc: .ai-engineering/scripts/hooks/_lib/instincts.py
- doc: .ai-engineering/scripts/hooks/_lib/hook_context.py
- doc: .ai-engineering/scripts/hooks/instinct-observe.py
- doc: .ai-engineering/scripts/hooks/instinct-extract.py
- doc: .ai-engineering/scripts/hooks/runtime-stop.py
- doc: .ai-engineering/scripts/hooks/copilot-adapter.py
- doc: .ai-engineering/scripts/regenerate-hooks-manifest.py
- doc: .ai-engineering/schemas/audit-event.schema.json
- doc: .ai-engineering/schemas/manifest.schema.json
- doc: .claude/settings.json
- doc: .claude/skills/ai-instinct/SKILL.md
- doc: .claude/skills/ai-learn/SKILL.md
- doc: .claude/skills/ai-start/SKILL.md
- doc: .claude/skills/ai-plan/SKILL.md
- doc: .claude/skills/ai-dispatch/SKILL.md
- doc: .ai-engineering/specs/spec-115-cross-ide-entry-point-governance-and-engineering-principles-standard.md
- doc: .ai-engineering/specs/spec-116-framework-knowledge-consolidation-canonical-placement-and-governance-cleanup.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-context-pack.md
- doc: pyproject.toml
- doc: src/ai_engineering/cli_factory.py
- doc: src/ai_engineering/cli_commands/sync.py
- ext: https://github.com/asg017/sqlite-vec
- ext: https://github.com/qdrant/fastembed
- ext: https://github.com/scikit-learn-contrib/hdbscan
