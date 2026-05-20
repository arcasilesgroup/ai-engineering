# Persistence Doctrine

> Authoritative reference for **where data lives** in ai-engineering.
> Cited from [CONSTITUTION.md](../CONSTITUTION.md) §13 and
> [CLAUDE.md](../CLAUDE.md) §0. Maintained by spec-138 (Harness
> Persistence Strategy); amendments require an ADR.

## The SSOT-PD rule

**Single Source of Truth Per Datum.** Every piece of framework state
lives in exactly one canonical writable store. Every other copy is a
*derived cache* — explicitly named, with a documented rebuild command,
and rebuildable on demand. Two stores accepting writes for the same
datum is the violation we close; one store with multiple writers is
acceptable.

- One canonical store per datum.
- Caches are explicitly labelled (named, with a rebuild command).
- Caches are rebuildable on demand — never the primary witness.
- Dual-writes (silent mirrors that drift) are forbidden.

## The four tiers

The framework stores state across four tiers chosen by the *shape* of
the data, not by convenience. A datum belongs to exactly one tier, and
within that tier to exactly one canonical file.

### Tier 1 — NDJSON audit log

- **Canonical for:** framework events (every hook fire, every skill
  invocation, every gate decision). The audit chain is the
  ground-truth witness used by `/ai-explain`, `/ai-verify`, and
  external auditors.
- **File pattern:** `.ai-engineering/state/framework-events.ndjson`
  (one JSON object per line, hash-chained via `prev_event_hash`).
- **Write SLA:** O(1) append — no parsing, no schema validation on
  write. Hot path budget under 50ms p95.
- **Read pattern:** sequential replay (cold path) via
  `ai-eng audit replay` / `ai-eng audit index`. Hot consumers read
  the projection in Tier 2, never the NDJSON directly.
- **Write trigger:** every hook fire (PreToolUse, PostToolUse,
  SessionStart, SessionEnd, ...) and every policy decision via
  `src/ai_engineering/governance/decision_log.py:emit_policy_decision`.
- **Hot-path status:** yes — must stay append-only and lock-free.
  Article III preservation (formerly CONSTITUTION.md
  [Article III — Dual-Plane Security](../.ai-engineering/specs/_history-constitution-2026-05-11.md#article-iii-dual-plane-security),
  now folded into the current CONSTITUTION.md "Compliance gates"
  section at lines 85-110).

### Tier 2 — SQLite `state.db`

- **Canonical for:** cold-path lifecycle rows that need indexed
  UPDATE / DELETE / FTS semantics, plus explicitly named derived
  caches and transitional placeholders. The database is not one
  uniform replay projection; every table declares its role below.
- **File pattern:** `.ai-engineering/state/state.db` (single STRICT
  SQLite file; schema in
  [`src/ai_engineering/state/migrations/0001_initial_schema.py:27-217`](../src/ai_engineering/state/migrations/0001_initial_schema.py#L27-L217)).
- **Write SLA:** sub-second per write. Never written from the
  hot-path hooks (PreToolUse / PostToolUse / UserPromptSubmit /
  SubagentStop / Notification).
- **Read pattern:** indexed SQL via `ai-eng audit query`,
  `ai-eng decision list`, `ai-eng risk list`, `ai-eng update`, and
  installer/doctor diagnostics.
- **Write trigger:** spec approval (`/ai-brainstorm`, `/ai-plan`),
  CLI commands (`ai-eng decision backfill`, `ai-eng ownership
  import`, `ai-eng risk accept`), installer phases (cold path), and
  SessionEnd projection rebuild for the `events` table (derived
  cache; see below).
- **Hot-path status:** no — cold-path-only. The contract test
  `tests/architecture/test_no_sql_on_hot_path.py` (spec-138 M4)
  enforces that no hot-path hook imports `sqlite3`.

| Table | Role | Source of truth / primary writer | Primary consumers |
|-------|------|----------------------------------|-------------------|
| `events` | derived cache | `.ai-engineering/state/framework-events.ndjson`; rebuilt by `ai-eng audit index --rebuild` and SessionEnd incremental indexing | `ai-eng audit query`, `ai-eng audit tokens` |
| `decisions` | mixed lifecycle/cache | CLI risk/flow decisions are lifecycle rows; ADR-style `D-NNN-NN` rows are backfilled from spec markdown/CHANGELOG | `ai-eng decision list`, risk lifecycle commands, `/ai-explain` decision lookup |
| `decisions_fts` | derived cache | SQLite FTS5 triggers over `decisions` | decision search |
| `risk_acceptances` | canonical lifecycle | risk lifecycle commands and release-gate flows | release/risk gates |
| `gate_findings` | transitional placeholder | schema placeholder only in this spec | not primary; gate/risk/verify use `gate-findings.json` |
| `ownership_map` | canonical lifecycle | installer state phase, `ai-eng ownership import`, and one-time legacy `ownership-map.json` fallback migration | `ai-eng update` reads this table before file evaluation; doctor/ownership diagnostics inspect it |
| `install_steps` | canonical lifecycle | installer phase outcomes | `ai-eng doctor --check state-db`, install idempotence checks |

### Tier 3 — JSON / YAML configuration

- **Canonical for:** machine-readable configuration whose schema is
  declared in Python (Pydantic / dataclass) and consumed by the
  deterministic plane.
- **File patterns:**
  - `.ai-engineering/manifest.yml` — framework configuration
    (stacks, agents, telemetry consent, IDE targets).
  - `.ai-engineering/state/hooks-manifest.json` — pinned sha256
    digests of every hook script for `run_hook_safe` integrity
    verification.
  - `.ai-engineering/state/gate-findings.json` — primary
    gate/risk/verify artifact for this spec; emitted by gate/review
    orchestration and read by verify/risk surfaces.
  - `.ai-engineering/suppression-allowlist.yml` — Article VII
    suppression exceptions (governed by `tools/no_suppression/`).
- **Write SLA:** human-typed plus tooling-validated; no perf budget.
- **Read pattern:** Pydantic parse on bootstrap; cached in process.
- **Write trigger:** operator edit + `ai-eng <surface> regenerate`
  commands (`regenerate-hooks-manifest.py`,
  `scripts/sync_mirrors/core.py`). Never written from the hot path.
- **Hot-path status:** read-only on the hot path; writes are cold
  path only.

### Tier 4 — Markdown human-authored truth

- **Canonical for:** human-authored doctrine and narrative state.
  Reviewable in PRs, diffable across history, indexable by humans.
- **File patterns:**
  - `.ai-engineering/specs/spec.md`, `.ai-engineering/specs/plan.md`
    (active spec workflow output).
  - `.ai-engineering/specs/archive/spec-NNN-*.md` (post-merge
    archive).
  - `.ai-engineering/LESSONS.md` (self-improvement loop per
    CLAUDE.md operating mindset #7).
  - [`CONSTITUTION.md`](../CONSTITUTION.md) (project identity).
  - [`CLAUDE.md`](../CLAUDE.md) (canonical cross-IDE rulebook;
    mirrors regenerated from
    `src/ai_engineering/templates/project/CLAUDE.md` and
    `CANONICAL.md`).
  - [`CHANGELOG.md`](../CHANGELOG.md) (Keep-a-Changelog format;
    every removal / breaking change documented).
- **Write SLA:** human-typed; no machine perf budget. Mirror sync
  is the only mechanical writer.
- **Read pattern:** operator + LLM session bootstrap; CI parsers
  (decision backfill, mirror-parity gates).
- **Write trigger:** operator commits; `scripts/sync_mirrors/core.py`
  for the byte-equivalent CLAUDE.md / AGENTS.md / GEMINI.md /
  copilot-instructions.md mirrors.
- **Hot-path status:** no. Markdown is operator and reviewer
  surface, not runtime.

## Derived caches

A *derived cache* is a writable store whose content is fully
reconstructible from a Tier 1–4 source-of-truth. Caches MAY be
queried for speed; they MUST NOT be the primary witness for any
audit, gate, or compliance claim.

| Cache name                     | Source-of-truth                                                                | Rebuild command                          | Freshness contract                                                                                          |
|--------------------------------|--------------------------------------------------------------------------------|------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| `state.db.events`              | `.ai-engineering/state/framework-events.ndjson` (Tier 1)                       | `ai-eng audit index --rebuild` (cold path only — incremental at SessionEnd, full on operator demand) | Rebuilt at SessionEnd (5-second budget) via `build_index(project_root, rebuild=False)`; operators MAY re-run on demand. Drift acceptable until next rebuild. Hot-path code MUST NOT write directly — enforced by `tests/architecture/test_no_sql_on_hot_path.py`. Incremental indexing via `indexed_lines.last_offset` keeps the SessionEnd budget under 5 s; on-demand `--rebuild` truncates and re-reads from offset 0. |
| `state.db.decisions_fts`       | `state.db.decisions` (Tier 2)                                                  | SQLite FTS5 triggers (auto on INSERT)    | Triggered on every `decisions` INSERT / UPDATE; never out of sync intra-process.                            |
| `state.db.decisions` (ADR rows only) | `.ai-engineering/specs/*.md` + `CHANGELOG.md` (Tier 4)                   | `ai-eng decision backfill`               | Rebuilt on operator demand and on `/ai-brainstorm` approval (M3 follow-up). Risk/flow decision rows written by CLI remain lifecycle rows, not rebuildable from specs. |
| `state.db.install_steps`       | Installer phase outcomes (process state, not on disk)                          | Re-run `ai-eng install` (idempotent)     | Populated on install; stale after manual filesystem surgery.                                                |

`state.db.ownership_map` is not a derived cache in spec-146. It is the
canonical update-decision table; `ai-eng update` reads this table before
evaluating create/update actions. A one-time legacy `ownership-map.json`
fallback may seed the table only when SQLite has no rows.

`state.db.gate_findings` is a non-primary placeholder/transitional
table in this spec. `.ai-engineering/state/gate-findings.json` remains
the primary gate/risk/verify artifact until a later approved migration
moves every producer and consumer.

## Bounded operational caches

`.ai-engineering/cache/gate/` is a bounded performance cache for
`ai-eng gate run`, not a canonical state-plane datum and not a deletion
target for `.ai-engineering/state/` cleanup. Entries are JSON files
keyed by gate-check inputs (tool version, relevant config hashes,
arguments, and staged blob SHAs); cache hits only skip recomputation,
they do not become audit or compliance witnesses.

- **Bounds:** entries expire after the existing 24-hour freshness
  window and writes prune the directory to 256 JSON entries.
- **Inspect:** `ai-eng gate cache --status`.
- **Clear:** `ai-eng gate cache --clear --yes` for a full wipe, or
  `ai-eng gate run --force` to clear matching entries before a fresh
  run.
- **State boundary:** old `.ai-engineering/state/gate-cache/` remains
  forbidden; the live cache belongs under `.ai-engineering/cache/gate/`.

## Strict rules

1. **No silent dual-writes.** A datum lives in exactly one canonical
   tier. If a second store needs the same datum for query speed, it
   is a derived cache — named in the table above, with a rebuild
   command, and clearly marked in code as `# derived cache; rebuild
   via <command>`.
2. **The audit chain stays on NDJSON.** `framework-events.ndjson` is
   the canonical witness. `state.db.events` is a derived cache for
   indexed query convenience; gates and external audits MUST verify
   against the NDJSON (`ai-eng audit verify`) before trusting the
   projection. The **only** writer to `state.db.events` is
   `ai-eng audit index --rebuild` (which dispatches into
   `ai_engineering.state.audit_index.build_index`). The SessionEnd hook
   invokes this writer in incremental mode (`rebuild=False`); the
   migration `0003_replay_ndjson.py` is positioned as a one-shot
   bootstrap that the SessionEnd rebuild supersedes for ongoing data.
3. **The hot path never writes SQL.** Hooks registered under
   PreToolUse, PostToolUse, UserPromptSubmit, SubagentStop, and
   Notification MUST NOT import `sqlite3`. SessionEnd is the
   sole hook permitted to run the rebuild; it carries a 5-second
   budget guard. Enforced mechanically by
   `tests/architecture/test_no_sql_on_hot_path.py` (spec-138 M4).
4. **Schema authority lives in Pydantic, not DDL.** The
   `state.db` schema is declared in
   [`src/ai_engineering/state/migrations/0001_initial_schema.py`](../src/ai_engineering/state/migrations/0001_initial_schema.py).
   Every INSERT site is contract-tested
   (`tests/unit/state/test_sql_writer_schemas.py`, spec-138 M1)
   to match the canonical column list. Drift between writer and
   schema fails CI.
5. **Hard deletes — no shims.** Per CONSTITUTION.md §13.3, renamed
   / deleted / migrated stores are removed outright. No
   backwards-compatibility mirror, no dual-write fallback, no
   deprecation alias. The CHANGELOG documents every removal.

## Operator surface — what changes for you

The doctrine is enforced by a small set of operator-facing commands.
None of these run on the hot path; all are idempotent and safe to
re-run.

- `ai-eng decision list` — read active decisions from
  `state.db.decisions`. The table is empty on a fresh checkout
  until `ai-eng decision backfill` populates it from spec markdown
  (Tier 4 → derived cache rebuild). M3 follow-up will auto-invoke
  the backfill on `/ai-brainstorm` approval.
- `ai-eng decision backfill` — parse `.ai-engineering/specs/*.md`
  and `CHANGELOG.md`, extract `D-NNN-NN` records, populate
  `state.db.decisions`. Idempotent on re-run.
- `ai-eng ownership import` — parse `.github/CODEOWNERS` (or
  operator-provided `ownership-map.json`), populate
  `state.db.ownership_map`. Re-run after every CODEOWNERS edit.
- `ai-eng doctor --check state-db` — list every `state.db` table
  with row count and last-modified timestamp; flag tables that
  should be populated but are empty (decisions after backfill,
  install_steps after install). Diagnostic surface for SSOT-PD
  drift.
- **SessionEnd rebuild semantics** — at session end, the framework
  invokes `audit_index.rebuild_at_session_end()` (5-second budget)
  to refresh the `state.db.events` projection from the NDJSON
  audit log. Subsequent `ai-eng audit query` / `ai-eng audit
  tokens` reads see the updated projection. Until M3 ships, the
  decision and ownership tables stay empty unless explicitly
  rebuilt.

## Glossary

- **SSOT-PD** — *Single Source of Truth Per Datum.* The framework's
  rule that every datum lives in exactly one canonical writable
  store, with all other copies labelled as derived caches.
- **Article III** — historical CONSTITUTION.md article on Dual-Plane
  Security that established the append-only NDJSON audit chain as
  the ground-truth witness. Preserved verbatim in
  [`_history-constitution-2026-05-11.md`](../.ai-engineering/specs/_history-constitution-2026-05-11.md);
  rolled into the current CONSTITUTION.md "Compliance gates"
  section (§85-110).
- **Derived cache** — a writable store whose content is fully
  reconstructible from a Tier 1–4 source-of-truth via a named
  rebuild command. Caches are query convenience, never primary
  witness.
- **Hot path** — code reached by every operator action (every save,
  every commit, every prompt). Budgeted: pre-commit under 1
  second, pre-push under 5 seconds, hooks under 50ms p95.
- **Cold path** — code reached by deliberate operator action
  (installer phases, `ai-eng <cmd>` invocations, SessionEnd, CI
  jobs). No tight wall-clock budget; correctness over latency.
- **Tier** — one of the four canonical persistence layers (NDJSON
  audit, SQLite `state.db`, JSON/YAML config, Markdown). Each tier
  has its own write SLA and hot-path status.
- **Polyglot persistence** — the framework's design choice to use
  the right store for each shape of data (append-only chain for
  events, relational + FTS for stateful lifecycle, declarative
  config for schema-driven settings, Markdown for human-authored
  doctrine) rather than forcing every datum into a single store.
