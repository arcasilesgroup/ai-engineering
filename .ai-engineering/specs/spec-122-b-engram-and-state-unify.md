---
spec: spec-122-b
title: Framework Cleanup Phase 1-B — Engram Delegation + Unified state.db
status: approved
effort: large
---

# Spec 122-b — Engram Delegation + Unified state.db

> Sub-spec of [spec-122 master](./spec-122-framework-cleanup-phase-1.md).
> Implements decisions D-122-05, D-122-06, D-122-16..23, D-122-30,
> D-122-34, D-122-38. **Depends on spec-122-a** (manifest.yml cleanup
> and CONSTITUTION dedupe must land first so state.db migrations and
> Engram setup target the cleaned surfaces).

## Summary

Replaces the framework's self-hosted episodic + semantic memory layer
(`memory.db` + `sqlite-vec` + `fastembed` + `hdbscan`, ~3K LOC across
`scripts/memory/`) with delegation to Engram (external CLI + MCP server,
`/opt/homebrew/bin/engram` v1.15.8+). `engram setup <agent>` becomes the
canonical wiring path per IDE; ai-engineering ships zero per-IDE MCP
templates. The framework's persistence surface is consolidated into a
single `state.db` SQLite database with seven STRICT tables (`events`,
`decisions`, `risk_acceptances`, `gate_findings`, `hooks_integrity`,
`ownership_map`, `install_steps`) plus a `_migrations` ledger. The
NDJSON `framework-events.ndjson` is preserved as immutable Article-III
source-of-truth and remains the rebuildable origin for the SQLite
projection (CQRS read-model split).

The schema is grounded in 35+ verified citations (sqlite.org docs, Greg
Young CQRS, Martin Fowler event sourcing, Crosby/Wallach tamper-evident
logging, Datasette / Litestream practitioner consensus, NIST SP 800-92
+ SOX / SEC 17a-4 retention ceilings, Facebook seekable-zstd contrib).
Retention is tiered (90d HOT in SQLite, 24mo WARM NDJSON plaintext, 7y
COLD zstd seekable archives). Cross-IDE concurrent NDJSON writes are
guarded by POSIX `O_APPEND` ≤ 4 KB atomicity + sidecar overflow at 3 KB.
Schema migrations are gated by `PRAGMA user_version` + a `_migrations`
table whose entries are sha256-protected by
`AIENG_HOOK_INTEGRITY_MODE=enforce` (default).

This sub-spec carries the highest blast radius of Phase 1: it touches
the audit infrastructure, deletes a memory layer used by `/ai-remember`
and `/ai-dream`, and restructures the dependency tree.

## Goals

- `state.db` SQLite database created with seven STRICT tables + a
  `_migrations` ledger; all PRAGMAs (D-122-16) set on connection open.
- Each table earns its place by a named consumer (events: audit CLI;
  decisions: /ai-plan + /ai-explain; risk_acceptances: /ai-release-gate;
  gate_findings: /ai-pr; hooks_integrity: /ai-security; ownership_map:
  /ai-governance; install_steps: ai-eng install).
- `events` table populated by replaying 84,679 existing NDJSON entries
  (idempotent via `ON CONFLICT(span_id) DO NOTHING`).
- Five JSON state files migrated: `decision-store.json` →
  `decisions`; `gate-findings.json` → `gate_findings`;
  `ownership-map.json` → `ownership_map`; `install-state.json` →
  `install_steps`; `hooks-manifest.json` verifications stream →
  `hooks_integrity`.
- Migration runner under `src/ai_engineering/state/migrations/`
  with `apply(conn)` + `BODY_SHA256` per file, gated by
  `_migrations.sha256` integrity check on every app startup.
- Transactional outbox: every projection mutation commits in a single
  `BEGIN IMMEDIATE` alongside the NDJSON event emit.
- NDJSON rotation monthly OR at 256 MB; closed months compressed to
  zstd seekable format; hash chain spans rotations via Crosby/Wallach
  pattern (`prev_month_head_hash` in first record).
- Cross-IDE concurrent write safety: `runtime-guard.py` rejects events
  ≥ 3 KB and offloads to `state/runtime/event-sidecars/<sha256>.json`;
  inline event carries hash + summary.
- `ai-eng audit` CLI extended with `retention apply`, `rotate`,
  `compress`, `verify-chain`, `health`, `vacuum`,
  `query --include-archived`.
- Engram delegation wired: `ai-eng install` invokes `engram setup
  <agent>` per detected IDE (Claude Code, Codex, Gemini CLI, GitHub
  Copilot, OpenCode); zero per-IDE MCP server config templates shipped
  inside ai-engineering.
- `/ai-remember` and `/ai-dream` skills reduced to thin wrappers over
  `engram search --project` and `engram save` respectively.
- `pyproject.toml` cleaned: `sqlite-vec`, `fastembed`, `hdbscan`
  removed; `[project.optional-dependencies.memory]` extra removed;
  `uv.lock` regenerated; `--extra memory` install path dropped from
  `ai-eng install` and CI workflows.
- `memory.db`, `scripts/memory/`, `instinct-observations.ndjson.repair-backup`
  deleted; `instinct-observations.ndjson` archived read-only (Engram
  becomes new observation target via `/ai-instinct --review` writing
  to `engram save`).

## Non-Goals

- Authoring scenario packs to revive `evals/` (deleted in spec-122-a).
- OPA proper migration (sub-spec c).
- sync_command_mirrors.py refactor (sub-spec d).
- SQLCipher encryption-at-rest for `state.db` (banking compliance is
  satisfied by host filesystem encryption per FIPS 140-3 storage
  requirements; SQLCipher is follow-up if regulators require app-layer
  key management).
- Cross-machine memory sync (Engram's responsibility, not
  ai-engineering's).
- Migration tooling beyond `PRAGMA user_version` + `_migrations`
  (Alembic explicitly rejected — adds 15+ MB of SQLAlchemy for a
  pattern that fits in 50 LOC of stdlib `sqlite3`).

## Decisions

This sub-spec **imports** the following master decisions verbatim:

| ID | Decision title |
|---|---|
| D-122-05 | Memory delegated to Engram external dependency |
| D-122-06 | Unified state.db SQLite alongside immutable NDJSON SoT |
| D-122-16 | SQLite PRAGMA configuration at connection open |
| D-122-17 | Schema migration strategy — `PRAGMA user_version` + `_migrations` |
| D-122-18 | Transactional outbox for projection mutations |
| D-122-19 | Retention + tiered storage policy |
| D-122-20 | NDJSON rotation + zstd seekable compression |
| D-122-21 | Single-table until 5M rows; ATTACH-shard partition only on trigger |
| D-122-22 | Housekeeping cadence + new `ai-eng audit` CLI surface |
| D-122-23 | Cross-IDE concurrent NDJSON write safety |
| D-122-30 | `AIENG_HOOK_INTEGRITY_MODE=enforce` applies to state.db migrations |
| D-122-34 | pyproject.toml + uv.lock cleanup post-Engram delegation |
| D-122-38 | Engram MCP setup delegated 100% (no per-IDE template) |

## Acceptance Criteria

- `sqlite3 .ai-engineering/state/state.db '.schema'` shows 7 tables +
  `_migrations` + `decisions_fts` virtual table, all `STRICT`.
- `sqlite3 .ai-engineering/state/state.db 'PRAGMA journal_mode'`
  returns `wal`.
- `sqlite3 .ai-engineering/state/state.db 'PRAGMA foreign_keys'`
  returns `1`.
- `sqlite3 .ai-engineering/state/state.db 'SELECT count(*) FROM events'`
  ≥ 84,679 (matches NDJSON line count).
- `find .ai-engineering/state -name 'memory.db'` returns empty.
- `find .ai-engineering/scripts/memory` returns empty.
- `grep -E '(sqlite-vec|fastembed|hdbscan)' pyproject.toml` returns
  empty.
- `uv sync` from clean state succeeds with the trimmed lockfile.
- `engram --version` returns ≥ `1.15.8`.
- `cat ~/.claude/settings.json` (or per-IDE equivalent) contains an
  `engram` MCP server entry written by `engram setup`.
- `/ai-remember "test query"` returns Engram results without invoking
  any in-process embedding code.
- `ai-eng audit verify-chain --full` passes (hash chain valid across
  all NDJSON months).
- `ai-eng audit health` reports `freelist_count / page_count` < 50%
  bloat.
- `ai-eng audit query "SELECT count(*) FROM events WHERE outcome='failure'"`
  returns sub-millisecond latency on partial-indexed query.
- `tests/integration/state/test_db_migration.py` round-trips every
  migrated JSON file and asserts equivalence.
- `tests/integration/memory/test_engram_subprocess.py` verifies
  `/ai-remember` and `/ai-dream` shell out correctly + handle failure
  modes (binary missing, timeout, malformed JSON).

## Risks

- **Engram availability across user platforms**: Engram is Mac/Linux
  homebrew today. Windows users in regulated enterprises may not have
  homebrew. **Mitigation**: prefer `winget install Engram`; fallback
  to direct binary download from Engram releases when winget
  unavailable; document in CLAUDE.md install section.
- **state.db migration corruption mid-stream**: replaying 84k NDJSON
  entries could fail. **Mitigation**: replay is idempotent (`ON
  CONFLICT(span_id) DO NOTHING`); `ai-eng audit index --rebuild --from
  <date>` re-runs deterministically; NDJSON is durable SoT.
- **Engram MCP setup divergence across versions**: `engram setup` may
  produce different outputs as Engram updates. **Mitigation**: pin
  Engram minor version in `required_tools.baseline.engram = ">=1.15.8,<1.16"`;
  CI runs a settings-file diff smoke test on every Engram bump.
- **`/ai-remember` regression after delegation**: thin-wrapper output
  shape may differ from current spec-118 retrieval format.
  **Mitigation**: integration test golden-file compares output shape
  to documented contract; release notes flag any breaking changes.
- **Cross-IDE concurrent NDJSON write race on non-POSIX FS**: NFS,
  HDFS, SMB do not guarantee `O_APPEND` atomicity. **Mitigation**:
  `ai-eng doctor` warns when repo is on a non-POSIX FS; documentation
  marks NFS / HDFS / SMB as unsupported.
- **Migration body sha256 drift after manual edit**: editing a
  migration file after it was applied triggers
  `migration_integrity_violation`. **Mitigation**: documented in
  migration-runner README; `ai-eng audit migration-rebase` provides
  controlled re-recording when an edit is intentional.
- **Subprocess overhead vs in-process embedding**: Engram CLI
  invocation adds ~50 ms vs 5 ms in-process. **Mitigation**: SessionStart
  bootstrap already pre-warms results via
  `engram context`; per-skill latency budget unchanged.

## References

- doc: spec-122-framework-cleanup-phase-1.md (master)
- doc: spec-122-a-hygiene-and-evals-removal.md (dependency)
- doc: .ai-engineering/state/framework-events.ndjson
- doc: .ai-engineering/state/audit-index.sqlite (deprecated post-merge)
- doc: .ai-engineering/state/memory.db (deleted)
- doc: .ai-engineering/state/decision-store.json (migrated)
- doc: .ai-engineering/state/ownership-map.json (migrated)
- doc: .ai-engineering/state/gate-findings.json (migrated)
- doc: .ai-engineering/state/install-state.json (migrated)
- doc: .ai-engineering/state/hooks-manifest.json (migrated)
- doc: src/ai_engineering/state/audit_index.py
- doc: src/ai_engineering/state/audit_chain.py
- doc: pyproject.toml
- doc: uv.lock
- ext: https://github.com/Gentleman-Programming/engram
- ext: https://sqlite.org/stricttables.html
- ext: https://sqlite.org/wal.html
- ext: https://sqlite.org/foreignkeys.html
- ext: https://sqlite.org/json1.html
- ext: https://sqlite.org/fts5.html
- ext: https://sqlite.org/lang_attach.html
- ext: https://sqlite.org/lang_vacuum.html
- ext: https://sqlite.org/limits.html
- ext: https://sqlite.org/autoinc.html
- ext: https://sqlite.org/backup.html
- ext: https://martinfowler.com/eaaDev/EventSourcing.html
- ext: https://cqrs.files.wordpress.com/2010/11/cqrs_documents.pdf
- ext: https://microservices.io/patterns/data/transactional-outbox.html
- ext: https://learn.microsoft.com/azure/architecture/patterns/event-sourcing
- ext: https://csrc.nist.gov/pubs/sp/800/92/final
- ext: https://static.usenix.org/event/sec09/tech/full_papers/crosby.pdf
- ext: https://github.com/facebook/zstd/blob/dev/contrib/seekable_format/README.md
- ext: https://pubs.opengroup.org/onlinepubs/9699919799/functions/write.html
- ext: https://nullprogram.com/blog/2016/08/03/
- ext: https://simonwillison.net/2024/Aug/22/optimizing-datasette/
- ext: https://fly.io/blog/all-in-on-sqlite-litestream/
- ext: https://use-the-index-luke.com/no-offset
