"""spec-118 Memory Layer.

Modules:
    store     - SQLite + sqlite-vec connection and schema bootstrap
    episodic  - per-session episode writer
    knowledge - hash-addressed knowledge object writer / ingest
    semantic  - lazy fastembed loader and vec0 upsert
    retrieval - top-K search with rerank
    dreaming  - decay, HDBSCAN cluster, supersedence, proposals
    repair    - data-hygiene utilities for legacy state
    audit     - thin emit wrapper for `memory_event` audit records
    cli       - Typer subcommands wired into `ai-eng memory ...`

Hooks at `.ai-engineering/scripts/hooks/memory-{session-start,stop}.py`
remain stdlib-only and shell into this CLI through subprocess so the
fastembed model never loads on the hook critical path.
"""

__all__ = [
    "audit",
    "cli",
    "dreaming",
    "episodic",
    "knowledge",
    "repair",
    "retrieval",
    "semantic",
    "store",
]
