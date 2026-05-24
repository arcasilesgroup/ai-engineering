## spec-118 — Memory Layer (Episodic, Semantic, Knowledge Objects, Dreaming, Cross-Session Retrieval)

**Branch**: `feat/knowledge-placement-governance-cleanup`. **Phases**: 5. **Status**: done (commit `62fa73bc`).

**Scope**: added the four missing memory tiers anchored in the existing audit chain and Constitution Article V SSOT — episodic memory at the Stop hook, hash-addressed Knowledge Objects, semantic tier on `sqlite-vec` + `fastembed`, dreaming consolidation loop, cross-session retrieval. Repaired the existing instinct subsystem's empty-timestamp regression as a side-effect.

**Key landings**:
- One new audit kind `memory_event` with seven discriminated sub-operations (D-118-01).
- Two canonical skills `/ai-remember` and `/ai-dream` (skill count 49 → 51).
- Two canonical hooks `memory-stop.py` and `memory-session-start.py` wired into `.claude/settings.json` and recorded in `hooks-manifest.json`.
- New module `.ai-engineering/scripts/memory/` with `store`, `episodic`, `knowledge`, `semantic`, `retrieval`, `dreaming`, `repair`, `audit`, `cli` submodules.
- Optional dependency extra `memory = ["sqlite-vec", "fastembed", "hdbscan", "numpy"]` in `pyproject.toml`.
- Manual-only promotion path: dreaming proposes; `LESSONS.md` is never auto-mutated.

**Lessons learned**:
1. **One audit kind sub-typed via `detail.operation` keeps the surface small** without sacrificing query power. The same pattern lands again under spec-119 D-119-01.
2. **Stdlib-only at import time + lazy heavy deps** (fastembed via subprocess) keeps the hook hot path under budget while the embedding work runs fire-and-forget.
3. **Refuse-to-start on dimension mismatch** (vector_map.embedding_dim vs active embedder) is the right default; silent re-embedding would silently corrupt the corpus.

**Follow-up gaps surfaced and repaired by spec-119**:
- `memory_event` was missing from `src/ai_engineering/state/event_schema.py::ALLOWED_EVENT_KINDS` and from the install-template hook copies. spec-119 Phase 1 added it as a parity repair.
