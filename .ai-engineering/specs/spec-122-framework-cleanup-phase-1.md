---
spec: spec-122
title: Framework Cleanup Phase 1 — Hygiene + State Unification + Engram Delegation + OPA Switch + Meta-Cleanup
status: approved
effort: large
---

# Spec 122 — Framework Cleanup Phase 1 (master)

> **Approved 2026-05-05.** Master umbrella spec covering 40 decisions
> across four sub-specs (a/b/c/d). See D-122-32 for the split structure
> and dependency chain. Sub-specs `spec-122-a`, `spec-122-b`, `spec-122-c`,
> `spec-122-d` are the implementation targets; this master is the canonical
> decision source they import from. Use `/ai-autopilot` for end-to-end
> autonomous delivery.

## Summary

`ai-engineering` source repo (`/Users/soydachi/repos/ai-engineering/`) accumulated
duplicated governance files, orphaned manifest sections, dead schemas, an empty
`runs/` artifact directory, a self-hosted memory layer that duplicates Engram, a
heterogeneous mix of 11 state stores (NDJSON + SQLite + 8 JSON files), and a
custom mini-Rego interpreter wired to nothing in the hot path. The framework
also ships with a skeleton evaluation gate that trivially passes `GO` because no
scenario packs exist, and a `.semgrep.yml` that misses prompt-injection, weak
crypto, and SSRF coverage. This spec consolidates the source-of-truth surfaces,
delegates memory to Engram (industry pattern 2025-26 — Cline, AgentMemory,
OMEGA, mcp-memory-service), unifies state into a single SQLite database
alongside an immutable NDJSON audit log, switches policy enforcement to OPA
proper with bundle signing and OTLP-native decision logs, deletes the false
`evals/` signal, and produces a smaller, more honest framework footprint
suitable for banking/finance/healthcare regulated adopters.

The cleanup is Phase 1 of a planned two-phase trajectory. Phase 2 — the v2
cutover already drafted in specs 200-213 — is explicitly out of scope for this
spec; Phase 1 establishes the foundation those specs assume.

## Goals

- Single canonical `CONSTITUTION.md` at repo root; `.ai-engineering/CONSTITUTION.md`
  stub deleted with all references repointed.
- IDE instruction overlay files (`CLAUDE.md`, `GEMINI.md`,
  `.github/copilot-instructions.md`) reduced to pure delta against `AGENTS.md`
  (cross-IDE SSOT). Targets: GEMINI.md ≤50 LOC delta, copilot-instructions.md
  ≤30 LOC delta.
- `.semgrep.yml` Tier-1 expansion (framework source coverage): pin community
  rulesets by version, add prompt-injection patterns, bash hooks coverage,
  weak-crypto detection, urllib/httpx/aiohttp SSRF rules.
- `.gitleaks.toml` allowlist tightened (drop wildcard
  `.ai-engineering/state/.*\.json$` that masks checkpoint/risk-score secrets).
- `iocs.json` aliases deduplicated (~40 LOC reduction); `last_updated` bumped
  to 2026-05; new incidents reviewed and appended.
- Memory layer delegated to Engram external dependency
  (`/opt/homebrew/bin/engram` v1.15.8+). `memory.db`, `scripts/memory/`,
  `sqlite-vec`, `fastembed`, `hdbscan` deleted (~3K LOC + 4 deps removed).
  `ai-eng install` invokes `engram setup <agent>` per detected IDE.
  `/ai-remember` and `/ai-dream` skills become thin wrappers over `engram
  search` / `engram save`.
- State unified into single `state.db` (SQLite, WAL, STRICT tables) with N
  minimum-necessary tables (final count and shape pending deep-DB research —
  see Section "Open Questions"). NDJSON `framework-events.ndjson` preserved
  immutable as Article III source-of-truth; SQLite is rebuildable projection.
- `manifest.yml` orphan sections removed: `tooling:` (subset of
  `required_tools`), `artifact_feeds:` (no consumer), `cicd.standards_url: null`
  (placeholder), `contexts.precedence:` (no resolver). Tooling section merged
  with `required_tools.baseline`.
- `evals/` subsystem deleted entirely: directory, `/ai-eval-gate` skill,
  `/ai-eval` skill, `ai-evaluator` agent, `manifest.yml evaluation:` block,
  `/ai-pr` step 9b, `/ai-release-gate` 9th dimension, `src/ai_engineering/eval/`
  module. Re-add path documented (post-spec-119-v2 if business case emerges).
- Policy enforcement switched from custom mini-Rego interpreter to OPA proper
  (CNCF-graduated, ~50 MB binary). Three `.rego` files migrated to OPA Rego v1
  syntax. Bundle built and signed with `opa build` + `opa sign` (JWT). Three
  hooks wired: pre-commit invokes `commit_conventional`, pre-push invokes
  `branch_protection`, `/ai-risk-accept` invokes `risk_acceptance_ttl`.
  Decision logs export to OTLP collector (already wired via `ai-eng audit
  otel-tail`). `opa test --coverage` runs in CI.
- `runs/consolidate-2026-04-29/` empty directory deleted.
- Schemas `manifest.schema.json` and `skill-frontmatter.schema.json` deleted (no
  runtime callers; `manifest_coherence.py` validates structurally via Pydantic).
- `spec-117-progress/` (197 delivery-log files) relocated to
  `state/archive/delivery-logs/spec-117/`. Empty gitkeep scaffolds (`v2/adr/`,
  `harness-gap-2026-05-04/`, `evidence/spec-116/`, `handoffs/`) deleted.
- `spec-121-self-improvement-and-hook-completion.md` frontmatter migrated from
  bold-prose form to canonical YAML schema.
- One-off install helper `wire-memory-hooks.py` deleted after idempotency
  verification.
- State directory minor cleanup: `instinct-observations.ndjson.repair-backup`
  deleted, `spec-116-t31-audit-classification.json` and `spec-116-t41-audit-findings.json`
  archived to `state/archive/`, `gate-cache/` (149 files) gains a 7-day
  retention policy, `strategic-compact.json` (44 B counter) deleted unless a
  consumer is positively identified.
- `scripts/sync_command_mirrors.py` (82 KB monolith) split into focused
  modules under `scripts/sync_mirrors/` per IDE target; backwards-compat
  shim preserves all CI / skill invocation paths.
- `docs/` folder cleanup pass: drop `.DS_Store`, audit `solution-intent.md`
  (32 KB) for post-cleanup currency, refresh `cli-reference.md` with new
  `ai-eng audit` subcommands, audit `agentsview-source-contract.md` /
  `anti-patterns.md` / `ci-alpine-smoke.md` / `copilot-subagents.md` for
  staleness.
- Repo-wide markdown drift audit: replace `/ai-implement` (skill no longer
  exists; current is `/ai-dispatch`) in `CONSTITUTION.md` and the project
  template. Cross-check skill listings in `AGENTS.md`, `CLAUDE.md`,
  `GEMINI.md`, `.github/copilot-instructions.md`, `README.md` against the
  actual `.claude/skills/` directory. Add CI guard
  (`tests/unit/docs/test_skill_references_exist.py`) to prevent future
  drift.
- Hook canonical event count alignment: `.claude/settings.json` registers
  11 events; CLAUDE.md and ADR-004 reference 8-10 depending on revision.
  Audit, drop dead wirings, update docs to actual count, and add CI guard
  `tests/unit/hooks/test_canonical_events_count.py`.
- `scripts/skill-audit.sh` evaluation: run once, compare output to
  `/ai-platform-audit --all`; if subset → DELETE the .sh; if complement →
  KEEP and document.
- Hot-path SLO test coverage: explicit timing tests for pre-commit < 1 s
  p95 and pre-push < 5 s p95 (CLAUDE.md commitment becomes CI-enforced).
- Phase 1 test coverage: state.db migration round-trip tests, OPA wiring
  tests with `opa test --coverage` ≥ 90%, Engram delegation tests, hook
  integrity extended to migrations.
- `AIENG_HOOK_INTEGRITY_MODE=enforce` default applies to the new state.db
  migration runner: migration body sha256 recorded in `_migrations.sha256`,
  verified on each app startup, mismatch refuses start with
  `migration_integrity_violation` framework error.

## Non-Goals

- v2 cutover specs 200-213 (separate Phase 2 effort, deferred).
- Multi-language `.semgrep.yml` Tier-2 templates for consumer projects (.NET,
  React, Go, Rust). Phase 1 covers framework source only; Tier-2 deferred to a
  dedicated spec.
- Authoring eval scenario packs to revive the gate. Decision is to **delete**
  the gate, not populate it.
- Migrating to Regorus (Rust mini-OPA) instead of OPA proper. Decision favors
  full OPA for OTLP-native decision logging, bundle signing, and CNCF
  ecosystem; Regorus is a documented future-spec option for confidential-
  computing builds.
- Replacing the `/ai-instinct` skill or the observation→review→promotion
  pipeline. The pipeline keeps working exactly as today (passive
  PostToolUse capture into `instinct-observations.ndjson`, manual
  `/ai-instinct --review` consolidation). Phase 1 only changes the
  **persistence target**: consolidated patterns land in the unified
  `state.db` (read by `/ai-explain`, `/ai-governance`, dashboards) rather
  than scattered JSON files. The user-visible behaviour of `/ai-instinct`
  is unchanged.
- Encryption-at-rest for `state.db` (SQLCipher). Banking-compliance angle is
  satisfied by host filesystem encryption (FileVault, dm-crypt); SQLCipher is
  follow-up work if regulators require app-level key management.
- Hot-loading skill discovery rewrites or skill-count rationalization (49 → N).
  Phase 1 keeps the skill surface intact; cleanup is structural, not capability-
  focused.

## Decisions

### D-122-01: Single CONSTITUTION at repo root, stub deleted

`/Users/soydachi/repos/ai-engineering/CONSTITUTION.md` (187 LOC) is the
authoritative governance contract. `.ai-engineering/CONSTITUTION.md` (65 LOC,
stub fallback) is deleted; all references in `observability.py:161-165`,
skills, and agents are repointed to the root path.

**Rationale**: Article V requires SSOT. Two CONSTITUTION files create drift
risk; the fallback resolution path in `observability.py` is dead code once the
stub is gone. Root placement matches the convention used by every IDE that
reads governance from the repo top-level (Claude Code, Codex, Gemini CLI,
GitHub Copilot).

### D-122-02: AGENTS.md as cross-IDE SSOT; per-IDE files become pure delta

`AGENTS.md` (73 LOC) at repo root remains the single canonical surface that
lists skills, agents, hard rules, and source-of-truth tables. `CLAUDE.md`
(217 LOC, already 0% duplication) stays unchanged. `GEMINI.md` (133 LOC, 40%
duplication today) is restructured to ≤50 LOC delta covering only
`.gemini/settings.json` wiring and Gemini-native hook conventions.
`.github/copilot-instructions.md` (60 LOC, 30% duplication today) is
restructured to ≤30 LOC covering only `.github/hooks/hooks.json` and Copilot
event mapping. No `CODEX.md` is created — Codex reads `AGENTS.md` natively.

**Rationale**: Every IDE that supports `AGENTS.md` (Codex, claude-agent-sdk)
should not need an overlay. IDEs whose native config shape differs (Claude
Code's `.claude/settings.json`, Gemini's `.gemini/settings.json`, Copilot's
`.github/hooks/hooks.json`) need only the wiring delta — never a re-listing
of skills or rules. Today's 40% / 30% duplication is drift waiting to happen.

### D-122-03: `.semgrep.yml` Tier-1 expansion with version-pinned community packs

`.semgrep.yml` extends from in-house Python-only rules (9 rules, last updated
2026-03-15) to include version-pinned community packs (`p/python`, `p/bash`,
`p/owasp-top-ten`, `p/security-audit`) plus custom prompt-injection patterns,
weak-crypto rules (md5, sha1, `random` for secrets), and SSRF coverage for
`urllib`, `httpx`, `aiohttp` in addition to `requests`.

**Rationale**: Framework hosts copilot bash hooks
(`copilot-runtime-{guard,stop,progressive-disclosure}.sh`) that have zero
Semgrep coverage today. Banking-compliance posture demands at least OWASP
Top-10 coverage with version-pinned rulesets; an unpinned `extends:` is a
supply-chain attack vector. Multi-language Tier-2 (consumer-template
expansion) is deferred to a separate spec to keep Phase 1 scope manageable.

### D-122-04: `iocs.json` aliases deduplicated

The schema duplicates four categories (`suspicious_network` ≡
`malicious_domains`, `dangerous_commands` ≡ `shell_patterns`) by storing the
full payload twice. The cleanup keeps the canonical spec-107 names
(`malicious_domains`, `shell_patterns`) as the storage keys, exposes the
upstream alias names (`suspicious_network`, `dangerous_commands`) via a
`spec107_aliases:` map that points to the canonical key, and updates
`prompt-injection-guard.py` to dereference the alias map at load. Net
reduction ~40 LOC; `IOCS_ATTRIBUTION.md` documents the alias contract.

**Rationale**: 40 LOC of literal duplication is drift bait. Ratifying the
alias as a one-level pointer preserves backward compatibility (callers using
the upstream names continue to work) while collapsing the maintenance
surface.

### D-122-05: Memory delegated to Engram external dependency

`memory.db` (`.ai-engineering/state/memory.db`, 1.8 MB), `scripts/memory/`
(store.py, semantic.py, retrieval.py, cli.py), and Python deps `sqlite-vec`,
`fastembed`, `hdbscan` are all deleted from the framework. Engram
(`/opt/homebrew/bin/engram` v1.15.8+, MIT-licensed external binary) becomes
the single memory provider. `ai-eng install` invokes `engram setup
claude-code|codex|gemini-cli|copilot` per detected IDE, which writes the
correct MCP server configuration into the IDE-native settings file. Skills
`/ai-remember` and `/ai-dream` are reduced to thin wrappers that shell out to
`engram search --project` and `engram save` respectively.

**Rationale**: Industry pattern 2025-26 (Cline Memory Bank, AgentMemory,
OMEGA, mcp-memory-service) delegates persistent memory to dedicated MCP
servers. Self-hosting an episodic + semantic + dreaming layer was
spec-118's bet; Engram now provides the same primitives with cross-project
scope, conflict detection, supersedence, and an officially supported MCP
profile. Maintaining a parallel sqlite-vec + fastembed stack inside the
framework duplicates Engram and raises the prereq weight (~150 MB models).
Delegating reduces installer complexity (`brew install engram` + a single
`engram setup` invocation per IDE) while removing ~3000 LOC and four Python
dependencies from the framework.

### D-122-06: Unified state.db SQLite alongside immutable NDJSON SoT

Eight JSON state files (`decision-store.json`, `gate-findings.json`,
`ownership-map.json`, `install-state.json`, `hooks-manifest.json`
verifications, `framework-capabilities.json` cache, plus `audit-index.sqlite`
itself) consolidate into a single `state.db` SQLite database (extension `.db`
following the GitHub CLI / Datasette / Litestream convention). The exact
table set, columns, indexes, and PRAGMA configuration are produced by a
deep-DB research pass (CI180-grade) and captured in a sub-decision before
this spec moves to `approved`. `framework-events.ndjson` is preserved
unchanged as the immutable Article III source-of-truth audit chain;
`state.db.events` is a rebuildable read-side projection.

**Rationale**: Heterogeneous JSON-and-NDJSON-and-SQLite state is a
maintenance liability: separate file formats, no joins, no transactions,
inconsistent schema discipline. Event Sourcing + CQRS (Greg Young, Martin
Fowler) advocates for an append-only event log as system-of-record plus a
mutable projection for queries; this is exactly the shape we want. SQLite
single-file durability, WAL mode, STRICT tables, and the `audit-index.sqlite`
projection already in production (spec-120, 79k rows, sub-millisecond
queries) prove the approach scales. The deep-DB research pass ensures
column-level decisions are defensible to a DBA reviewer rather than
improvised.

**Final table set** (CI180 deep-DB review applied; column choices defended
against EAV, soft-delete, UUID-PK, and BLOB-payload anti-patterns). Seven
tables, all `STRICT`. The `events` table is the rebuildable CQRS read-model
projection of the immutable NDJSON; the other six are mutable projections
that emit a corresponding event into NDJSON on every mutation
(transactional-outbox pattern, [Richardson, microservices.io]).

**Dropped vs early baseline** with rationale:

- `policy_violations` — covered by `events.kind='policy_decision'`. Adding
  a parallel table would duplicate without new fact.
- `instincts_evaluated` — Engram (D-122-05) owns observation consolidation.
- `skill_evolution` — derivable as a SQL view over `events.kind='skill_evolved'`.
- `capabilities_snapshot` — generated artifact (filesystem cache); JSON
  blob is appropriate, table is over-engineering.
- `governance_yaml_state` — `manifest.yml` is git-tracked SoT; snapshotting
  it inside the DB duplicates without query benefit.

```sql
-- ============================================================
-- 1. events — CQRS read-model projection of framework-events.ndjson
--    Immutable; rebuildable from NDJSON line 0; never UPDATE/DELETE.
-- ============================================================
CREATE TABLE events (
  seq             INTEGER PRIMARY KEY,                           -- ROWID alias; NO AUTOINCREMENT (rebuildable from NDJSON; monotonic-never-reused not required)
  span_id         TEXT NOT NULL UNIQUE,                          -- OTel span correlation (UUID-style; UNIQUE not PK)
  trace_id        TEXT,                                          -- cross-session traces
  parent_span_id  TEXT,                                          -- span-tree depth-first walk
  correlation_id  TEXT NOT NULL,                                 -- skill→agent→tool chain
  session_id      TEXT,                                          -- NULL for framework-level events
  timestamp       TEXT NOT NULL,                                 -- ISO-8601 (display, preserves tz)
  ts_unix_ms      INTEGER GENERATED ALWAYS AS (
                    CAST((julianday(timestamp) - 2440587.5) * 86400000 AS INTEGER)
                  ) STORED,                                      -- 8B int vs 24B ISO; range scans
  archive_month   TEXT GENERATED ALWAYS AS (
                    strftime('%Y-%m', timestamp)
                  ) STORED,                                      -- 'YYYY-MM' partition key for retention pruning
  source_file     TEXT,                                          -- NDJSON file of origin (rebuild provenance)
  engine          TEXT NOT NULL,                                 -- claude-code|codex|gemini|copilot
  kind            TEXT NOT NULL,                                 -- skill_invoked|agent_dispatched|...
  component       TEXT NOT NULL,                                 -- skill/agent/hook name
  outcome         TEXT NOT NULL CHECK (outcome IN ('success','failure','blocked','skipped','observed')),
  prev_event_hash TEXT,                                          -- Article-III chain validation
  genai_system    TEXT,                                          -- OTel GenAI export
  genai_model     TEXT,
  input_tokens    INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
  output_tokens   INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
  total_tokens    INTEGER CHECK (total_tokens IS NULL OR total_tokens >= 0),
  cost_usd        REAL    CHECK (cost_usd IS NULL OR cost_usd >= 0),
  detail_json     TEXT NOT NULL CHECK (json_valid(detail_json))  -- TEXT (not BLOB) so json_extract works
) STRICT;
CREATE INDEX idx_events_ts            ON events(ts_unix_ms);
CREATE INDEX idx_events_ts_session    ON events(ts_unix_ms, session_id);             -- covering index for session+range hot path
CREATE INDEX idx_events_session       ON events(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_events_kind          ON events(kind);
CREATE INDEX idx_events_component     ON events(component);
CREATE INDEX idx_events_trace         ON events(trace_id) WHERE trace_id IS NOT NULL;
CREATE INDEX idx_events_failure       ON events(component, ts_unix_ms) WHERE outcome='failure';
CREATE INDEX idx_events_archive_month ON events(archive_month);                       -- retention pruning
-- Retention: 90 days HOT in SQLite. NDJSON keeps 24-month warm + 7-year cold zstd archive (Article III).
-- Vacuum incremental nightly. Drop AUTOINCREMENT per sqlite.org/autoinc.html (CPU+IO overhead unjustified).

-- ============================================================
-- 2. decisions — D-NNN-NN architectural rulings (replaces decision-store.json)
--    Adjacency-list supersede graph (chains ≤3, recursive CTE handles depth).
-- ============================================================
CREATE TABLE decisions (
  id             TEXT PRIMARY KEY,                              -- 'D-051-04'
  title          TEXT NOT NULL,
  body           TEXT NOT NULL,                                 -- markdown rationale, ≤16 KB
  category       TEXT NOT NULL CHECK (category IN ('architecture','governance','security','process','operations')),
  criticality    TEXT NOT NULL CHECK (criticality IN ('low','medium','high','critical')),
  status         TEXT NOT NULL CHECK (status IN ('proposed','active','superseded','retired')),
  spec_id        TEXT,                                          -- 'spec-051'; NULL for ad-hoc
  source         TEXT NOT NULL,                                 -- skill/agent/human author
  superseded_by  TEXT REFERENCES decisions(id) ON DELETE RESTRICT,
  superseded_at  TEXT,
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL,
  CHECK ((status='superseded') = (superseded_by IS NOT NULL))   -- biconditional state machine
) STRICT;
CREATE INDEX idx_decisions_status ON decisions(status) WHERE status='active';
CREATE INDEX idx_decisions_spec   ON decisions(spec_id) WHERE spec_id IS NOT NULL;
-- FTS5 over body for /ai-explain history (contentless external-content):
CREATE VIRTUAL TABLE decisions_fts USING fts5(
  title, body,
  content='decisions', content_rowid='rowid', tokenize='porter'
);
-- (FTS sync triggers omitted — standard external-content pattern)

-- ============================================================
-- 3. risk_acceptances — TTL-bound CVE / finding risk approvals (spec-110)
--    finding_hash NOT a hard FK: acceptance can predate the finding row.
-- ============================================================
CREATE TABLE risk_acceptances (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  finding_hash  TEXT NOT NULL,                                  -- sha256(tool|file|line|rule|excerpt)
  cve_id        TEXT NOT NULL,
  package       TEXT NOT NULL,
  reason        TEXT NOT NULL,
  decision_id   TEXT NOT NULL REFERENCES decisions(id) ON DELETE RESTRICT,
  approved_by   TEXT NOT NULL,
  expires_at    INTEGER NOT NULL,                               -- unix ms; no eternal acceptances
  created_at    INTEGER NOT NULL,
  CHECK (expires_at > created_at)
) STRICT;
CREATE INDEX idx_risk_active ON risk_acceptances(finding_hash, expires_at);
-- Expire policy: poll-based via `ai-eng audit index --expire-acceptances`.
--                Triggers cannot fire on time. On expiry: INSERT events(kind='risk_acceptance_expired') THEN DELETE.

-- ============================================================
-- 4. gate_findings — release-gate verdicts per tool (spec-119)
--    Hash-keyed. ON DELETE RESTRICT — accepted findings never silently disappear.
-- ============================================================
CREATE TABLE gate_findings (
  finding_hash  TEXT PRIMARY KEY,                               -- sha256(tool|file|line|rule|excerpt)
  session_id    TEXT NOT NULL,
  produced_by   TEXT NOT NULL,                                  -- 'ai-commit', 'ai-verify'
  produced_at   INTEGER NOT NULL,
  branch        TEXT,
  commit_sha    TEXT,
  tool          TEXT NOT NULL,                                  -- gitleaks|pip-audit|pytest|ruff|semgrep|ty
  severity      TEXT NOT NULL CHECK (severity IN ('info','low','medium','high','critical')),
  status        TEXT NOT NULL CHECK (status IN ('open','accepted','fixed','suppressed')),
  rule_id       TEXT,
  file_path     TEXT,
  line_no       INTEGER,
  excerpt       TEXT,
  expires_at    INTEGER                                         -- attached when acceptance bound
) STRICT;
CREATE INDEX idx_gate_session ON gate_findings(session_id);
CREATE INDEX idx_gate_open    ON gate_findings(tool, severity) WHERE status='open';
-- Retention: 90d rolling for status='fixed'; forever for 'accepted' (compliance).

-- ============================================================
-- 5. hooks_integrity — sha256 tamper trail (spec-120 hot-path)
--    LOG ONLY MISMATCHES. Successful runs already covered by events.
-- ============================================================
CREATE TABLE hooks_integrity (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  hook_path   TEXT NOT NULL,
  expected    TEXT NOT NULL,                                    -- sha256 from manifest
  actual      TEXT NOT NULL,
  outcome     TEXT NOT NULL CHECK (outcome IN ('mismatch','missing_in_manifest','manifest_unreadable')),
  ts_unix_ms  INTEGER NOT NULL,
  session_id  TEXT,
  pid         INTEGER
) STRICT;
CREATE INDEX idx_hooks_recent ON hooks_integrity(ts_unix_ms DESC);
-- App-layer (no trigger): mismatches auto-emit events(kind='framework_error',
-- detail.error_code='hook_integrity_violation') via existing _lib/audit.py.

-- ============================================================
-- 6. ownership_map — Article V file→agent boundaries
--    Glob (not regex). Longest-prefix-match wins (existing convention).
-- ============================================================
CREATE TABLE ownership_map (
  pattern          TEXT PRIMARY KEY,
  owner            TEXT NOT NULL CHECK (owner IN ('framework-managed','team-managed','shared')),
  framework_update TEXT NOT NULL CHECK (framework_update IN ('allow','deny','append-only')),
  updated_at       INTEGER NOT NULL,
  updated_by       TEXT NOT NULL,
  CHECK (length(pattern) > 0 AND pattern NOT LIKE '%//%')
) STRICT;
-- History tracked via events(kind='ownership_changed'); no in-table version column.

-- ============================================================
-- 7. install_steps — idempotent installer step tracking
--    Bounded retries; UPSERT, never DELETE (preserve operational history).
-- ============================================================
CREATE TABLE install_steps (
  step_id       TEXT PRIMARY KEY,                               -- 'gh', 'uv', 'hook_hash:pre-commit'
  status        TEXT NOT NULL CHECK (status IN ('pending','done','failed','skipped')),
  retries       INTEGER NOT NULL DEFAULT 0 CHECK (retries >= 0),
  last_error    TEXT,
  detail_json   TEXT NOT NULL CHECK (json_valid(detail_json)),  -- arbitrary per-tool state
  updated_at    INTEGER NOT NULL
) STRICT;

-- ============================================================
-- _migrations — schema evolution ledger (gated by PRAGMA user_version)
-- ============================================================
CREATE TABLE _migrations (
  version     INTEGER PRIMARY KEY,
  applied_at  TEXT NOT NULL,
  sha256      TEXT NOT NULL                                     -- hash of migration body
) STRICT;
```

**Column-design defenses** (consumer-grounded; not improvised):

- `events.seq` vs `ts_unix_ms` vs `prev_event_hash` are three independent
  concerns: insertion order (replay), wall-clock (range queries), and chain
  validation (Article III). Collapsing them is the kind of improvisation the
  research expressly rejected.
- `ts_unix_ms` is a `STORED GENERATED` column from ISO `timestamp` because
  indexed range scans on a 24-byte ISO string are 4× slower than on an 8-byte
  integer; `STORED` (not `VIRTUAL`) so the index does not re-evaluate the
  julianday cast on every read.
- `detail_json` is `TEXT` (not BLOB+zstd): JSON1 `json_extract()` over 84k
  rows costs ~2 ms and the storage saving (~60% if compressed) is dwarfed by
  the cost of full JSON deserialization on every query.
- FTS5 over `decisions.body` is contentless external-content
  (`content='decisions', content_rowid='rowid'`) so the body lives once and
  is indexed twice; Porter tokenizer for English-language rationales.
- `risk_acceptances.finding_hash` is intentionally NOT a hard foreign key
  because acceptances can be filed before the next gate run produces the
  matching finding row; cross-table integrity is enforced at app layer in
  `verify/service.py`.
- All FK constraints use `ON DELETE RESTRICT`, not `CASCADE`. Deleting a
  decision must not silently delete the risk acceptances that cite it; this
  is a regulated-industry posture. CASCADE is appropriate for B2C apps, not
  audit DBs.
- The `(status='superseded') = (superseded_by IS NOT NULL)` biconditional
  CHECK encodes the supersedence state machine without triggers (which
  cannot DEFER and produce opaque error messages).
- INTEGER PK AUTOINCREMENT is preferred over UUID PK because btree depth on
  84k UUID PKs is ~3 vs ~2 on integer PKs (~30% read penalty for no
  semantic gain); UUID-style `span_id` is exposed as a UNIQUE index instead.

**Rationale**: A column-by-column defense with consumer references and
citation grounding (sqlite.org STRICT/WAL/JSON1/FTS5/partial-index docs,
Greg Young CQRS, Fowler, Richardson outbox, NIST FIPS 140-3) replaces the
"improvisada" sketch. Every table earns its place via a named consumer
process; every column earns its place via a named query pattern.

### D-122-07: `manifest.yml` orphan sections removed

`tooling:` (line 334, flat list) is removed — its content is a subset of
`required_tools.baseline`. `artifact_feeds:` (no live consumer), `cicd.standards_url: null`
(placeholder), `contexts.precedence:` (no runtime resolver) are also removed.
The `prereqs:` and `required_tools:` sections are repositioned adjacent to
each other (the lint workaround that separated them via `python_env:` is
removed). Schema validation against `manifest.schema.json` is dropped because
the schema file itself is being deleted (see D-122-12); structural
validation continues via the Pydantic models in `manifest_coherence.py`.

**Rationale**: Orphans accumulate when sections are added speculatively and
never wired. Each section deleted has zero greppable runtime caller. The
Pydantic models are the de-facto contract; the JSON Schema duplicates them
without enforcement teeth. Reducing manifest.yml from 457 to ~395 LOC tightens
the cognitive surface for every skill that reads it.

### D-122-08: `evals/` subsystem deleted

The evaluation gate (spec-119) is removed wholesale: `.ai-engineering/evals/`,
`.claude/skills/ai-eval-gate/`, `.claude/skills/ai-eval/`,
`.claude/agents/ai-evaluator.md`, `manifest.yml evaluation:` block, the step
9b call from `/ai-pr`, the 9th dimension from `/ai-release-gate` (returning
to 8 dimensions), and `src/ai_engineering/eval/` module. The deletion is
documented with a re-add path in `_history.md`: a future spec-119-v2 may
recreate the gate from scratch when a real business case (post-deployment
prompt drift, reviewer regression, regulator request) is produced.

**Rationale**: An eval gate with zero scenario packs is a false-signal:
`enforcement: blocking` trivially passes `GO` on every PR, giving operators
the impression of coverage that does not exist. Authoring scenario packs is
non-trivial work that has been deferred for two months without a champion.
Deleting the gate is honest; mothballing keeps dead code visible. The
re-add path remains because the underlying capability (deterministic
regression detection over LLM tasks) has long-term value once a
pack-authoring discipline is established.

### D-122-09: OPA proper switched in; custom mini-Rego deprecated

`src/ai_engineering/governance/policy_engine.py` (~400 LOC custom mini-Rego
interpreter) is deprecated. `opa` (CNCF-graduated, ~50 MB Go binary) becomes
a `required_tools.baseline` prereq installed via `brew install opa` (mac/linux
homebrew) or direct download (Windows, container CI). The three policies
(`branch_protection.rego`, `commit_conventional.rego`, `risk_acceptance_ttl.rego`)
are migrated from the custom-subset syntax to OPA Rego v1 (full builtins,
including crypto). `opa test --coverage` is added to the CI pipeline. The
policy directory is built into a signed bundle via `opa build` + `opa sign`
producing `.signatures.json` (JWT, RSA-256). Three hooks invoke `opa eval`:
`pre-commit` calls `data.commit_conventional.deny`, `pre-push` calls
`data.branch_protection.deny`, and `/ai-risk-accept` calls
`data.risk_acceptance_ttl.deny`. Decision logs are emitted to the existing
OTLP collector (already wired via `ai-eng audit otel-tail`).

**Rationale**: Custom mini-Rego inherits maintenance cost without inheriting
ecosystem benefits. OPA proper is the industry standard
(Netflix/Atlassian/Capital One adoption, CNCF graduation 2021), provides
native OTLP decision logging, bundle signing for tamper-evident policy
distribution, and a `opa test` framework that the custom interpreter does not
match. The 50 MB binary footprint is acceptable for a framework targeting
banking/finance/healthcare desktops where OPA is often already present in
the toolchain. Lighter alternatives exist (Regorus 1.9-6.3 MB Rust impl,
OPA-WASM compiled to KB-scale modules) and are documented as future-spec
options for edge / confidential-computing builds; the Phase 1 default is
full OPA.

### D-122-10: Phase 1 split — superseded by D-122-32 (four-spec split)

This decision was originally drafted as a three-spec split (A, B, C). It
is **superseded by D-122-32**, which expands to a four-spec split (A, B,
C, D) once the meta-cleanup wave (sync_command_mirrors split, docs drift
audit, hook event count alignment, test coverage gates, hot-path SLO
tests) entered scope. See D-122-32 for the canonical split.

**Rationale**: Three sub-specs underestimated total Phase 1 scope. Adding
a fourth meta-cleanup track keeps each sub-spec under ~5-7 days and
respects the convention that one spec → one focused theme.

### D-122-11: Empty `runs/consolidate-2026-04-29/` deleted

The directory `.ai-engineering/runs/consolidate-2026-04-29/` is empty (zero
files) and has zero greppable references in `src/`, `scripts/`, or any
skill/agent. It is deleted with no replacement.

**Rationale**: Empty directories signal abandoned migrations. Keeping them
adds zero value and pollutes `ls` output for new contributors trying to
orient.

### D-122-12: Unused JSON schemas deleted

`.ai-engineering/schemas/manifest.schema.json` is deleted because the
`manifest_coherence.py` Pydantic models are the de-facto contract;
maintaining a parallel JSON Schema duplicates without enforcement.
`.ai-engineering/schemas/skill-frontmatter.schema.json` is deleted because
zero code or documentation references it. The four remaining schemas
(`audit-event`, `decision-store`, `hooks`, `lint-violation`) are kept as
contract documentation and are scheduled for runtime validation wiring in
the v2 cutover (deferred).

**Rationale**: Schemas without validators are documentation, not contracts;
two of the six are not even documentation because nothing references them.
Pydantic provides the runtime enforcement for `manifest.yml`, making the
parallel JSON Schema redundant and a drift hazard.

### D-122-13: `spec-117-progress/` relocated and gitkeep scaffolds removed

The directory `.ai-engineering/specs/spec-117-progress/` (197 build/verify/
explore log files, 72% of the entire `specs/` tree by file count) is
relocated to `.ai-engineering/state/archive/delivery-logs/spec-117/`. Empty
gitkeep scaffolds (`v2/adr/`, `harness-gap-2026-05-04/`,
`evidence/spec-116/`, `handoffs/`) are deleted. The `specs/` directory now
contains only authored specs (`spec-NNN-<slug>.md` and the active
`spec.md`/`plan.md` slots). `_history.md` is updated to record the
spec-117-progress relocation.

**Rationale**: Mixing authored specs with auto-generated delivery logs makes
the `specs/` directory unsearchable: 274 files where 197 are noise. Logs
belong under `state/archive/`, which has explicit retention and archival
semantics; specs belong under `specs/`, which reflects authored intent.

### D-122-14: One-off install helper `wire-memory-hooks.py` deleted

`.ai-engineering/scripts/wire-memory-hooks.py` (a spec-118 one-shot helper)
is removed after running `--check` to confirm idempotency on a fresh
install. The script's behaviour (writing memory hook entries into
`.claude/settings.json`) is now obsoleted by the Engram delegation in
D-122-05; even if it were not, leaving a one-shot script in the repo
invites accidental re-execution.

**Rationale**: Dead code accumulates. One-shot helpers must be deleted
once the migration they automated has run.

### D-122-16: SQLite PRAGMA configuration at connection open

`state.db` connections set the following pragmas on open (in
`src/ai_engineering/state/connection.py`):

| Pragma | Value | Why |
|---|---|---|
| `journal_mode` | `WAL` | Concurrent reader/writer; writers do not block readers; required for `audit-index` rebuild to coexist with `ai-eng audit query` from a parallel shell. |
| `synchronous` | `NORMAL` | WAL-safe; ~3× faster than FULL; durable on OS crash (only WAL-checkpoint fsync, not every commit). |
| `foreign_keys` | `ON` | Off by default (legacy); we depend on FK semantics (`risk_acceptances → decisions`, `decisions.superseded_by`). |
| `busy_timeout` | `10000` | 10-second blocking beats `SQLITE_BUSY` surfacing to skill code. |
| `cache_size` | `-65536` | 64 MB page cache (negative = KB). |
| `temp_store` | `MEMORY` | Temp tables in RAM, not disk. |
| `mmap_size` | `268435456` | 256 MB memory-mapped I/O — appropriate for read-mostly workload (events queries far outnumber writes). |
| `auto_vacuum` | `INCREMENTAL` | Set at `CREATE` only (cannot be retrofitted without `VACUUM`); reclaim on demand via `PRAGMA incremental_vacuum`. |

Daily maintenance via a new `ai-eng audit index --vacuum` flag invokes
`incremental_vacuum(N)`. Quarterly `ANALYZE` refreshes `sqlite_stat1`.

**Rationale**: Default SQLite pragmas are tuned for embedded devices; an
audit projection on a developer laptop benefits from WAL + larger cache +
mmap. Each pragma is documented at sqlite.org with measured tradeoffs;
this table is the canonical reference for any future maintainer who asks
"why these values, not the defaults".

### D-122-17: Schema migration strategy — `PRAGMA user_version` + `_migrations` table

Schema evolution does NOT use Alembic (would drag SQLAlchemy in for a
pure-stdlib project). Instead:

- A `_migrations` table records every applied version with its timestamp
  and the sha256 of the migration body for tamper detection.
- `PRAGMA user_version` is the monotonic version pointer.
- Each migration lives at
  `src/ai_engineering/state/migrations/NNNN_<slug>.py` and exposes an
  `apply(conn)` function plus a constant `BODY_SHA256`.
- The migration runner wraps each migration in
  `BEGIN IMMEDIATE; <DDL>; PRAGMA user_version=N; INSERT INTO _migrations
  VALUES (...); COMMIT;` — failure rolls back to the prior version.

SQLite `ALTER TABLE` limitations (no arbitrary type or constraint changes)
are handled via the canonical pattern: `CREATE new; INSERT INTO new SELECT
... FROM old; DROP old; ALTER RENAME new TO old`. This is documented at
sqlite.org/lang_altertable.html and is the only stable path for SQLite
schema evolution.

**Rationale**: Hand-rolled migrations gated by `user_version` are the
practitioner consensus (Willison's `sqlite-utils`, Litestream, Datasette
ecosystem). Alembic and SQLAlchemy add 15+ MB of dependencies to support a
pattern that fits in 50 LOC of stdlib `sqlite3`. The `_migrations` table
provides an in-DB audit trail that complements `user_version` — the latter
is just an integer; the former records who, when, and the migration body
hash.

### D-122-18: Transactional outbox for projection mutations

Mutations to `decisions`, `risk_acceptances`, `gate_findings`,
`ownership_map`, `install_steps`, and `hooks_integrity` MUST be wrapped in
a single `BEGIN IMMEDIATE` that also writes the corresponding event into
`framework-events.ndjson` (via an in-DB `_outbox` queue or via
`emit_event()` immediately preceded by a successful row write). The
projection update and the event MUST commit atomically; the existing
race window in `decisions_cmd.py:179` (file-write THEN emit-event) is
closed.

**Rationale**: Without atomic projection-plus-event, a process crash
between the two writes leaves the projection ahead of the audit log
(silent state divergence) or behind it (event references a row that does
not exist). Chris Richardson's transactional outbox pattern
(microservices.io) is the canonical solution and translates cleanly to
SQLite + NDJSON via a small `_outbox` table flushed by the writer thread.

### D-122-19: Retention + tiered storage policy

`events` table is the **HOT** tier (90 days online in `state.db`).
`framework-events.ndjson` files keep 24 months as **WARM** tier
(plaintext, append-only, current month + 23 previous months).
Older months become **COLD** tier (zstd seekable-format compressed,
retained 7 years to satisfy SEC 17a-4, SOX, HIPAA, GLBA ceilings —
NIST SP 800-92 declines a single floor and defers to sectoral
regulation).

| Tier | Storage | Retention | Reasoning |
|---|---|---|---|
| HOT | `state.db.events` | 90 days | Sub-millisecond indexed queries; small enough to stay nimble. Rebuildable from NDJSON via `ai-eng audit index --rebuild --from <date>`. |
| WARM | `state/audit-archive/YYYY/YYYY-MM.ndjson` | 24 months | Plaintext, append-only, hash-chain intact. Read-on-demand for replay. |
| COLD | `state/audit-archive/YYYY/YYYY-MM.ndjson.zst` | up to 7 years | zstd seekable-format frame structure (Facebook contrib) supports random access without full decompression. ~10× compression on JSON. |

`hash-chain.json` manifest at archive root tracks `{month →
head_hash, line_count, sha256}` so cross-month integrity verification
works after rotation.

**Rationale**: Without explicit retention tiers, "indexes will hold"
becomes "the dev's laptop chokes on a 10 GB DB in 18 months." NIST
800-92 + sectoral ceilings give defensible numbers; tiering keeps
the hot path fast and the cold path cheap. NDJSON stays the
constitutional Article III source of truth — compression is
deterministic-reproducible (zstd byte-exact), so chain validation
still passes after decompression.

### D-122-20: NDJSON rotation + zstd seekable compression

`framework-events.ndjson` rotates **monthly OR at 256 MB**, whichever
fires first. The rotation flow:

1. Quiesce writers via advisory lock (`flock` on
   `state/locks/audit-rotation.lock`).
2. Compute final `head_hash` of closing month → write to
   `state/audit-archive/YYYY/YYYY-MM.manifest.json`.
3. Open new month file `state/audit-archive/YYYY/YYYY-MM.ndjson`;
   first event records `prev_month_head_hash` (Crosby/Wallach
   tamper-evident logging pattern, USENIX Security '09).
4. Update root `hash-chain.json`.
5. Background: zstd seekable-compress the just-closed month
   (`*.ndjson` → `*.ndjson.zst`); preserve plaintext for 24 months
   as WARM tier; only delete plaintext past WARM cutoff.

The active append-target NDJSON is **never** compressed (zstd writes
require buffering; line-by-line append cannot maintain
frame-aligned structure in the live file).

**Rationale**: Rotation gives a clean partition for retention. Hash
chain spans rotations via Crosby/Wallach's "first record carries
prev-file-terminal-hash" pattern, preserving Article III's
tamper-evident invariant. Seekable-zstd ([Facebook contrib]) gives
random access into compressed cold archives, so 7-year archives
stay queryable for compliance review without bulk decompression.

### D-122-21: Single-table until 5M rows; ATTACH-shard partition only on trigger

`state.db.events` stays a single monolithic table until ANY of:

- `events` row count > 5,000,000
- `state.db` file size > 2 GB
- p95 indexed query latency > 50 ms locally

When triggered, future months land in attached read-only shards
`state/archive/events-YYYY-MM.db` exposed via:

```sql
CREATE VIEW events AS
  SELECT * FROM main.events
  UNION ALL SELECT * FROM events_2027_01.events
  UNION ALL SELECT * FROM events_2026_12.events
  -- ...
;
```

Cap attached shards at 9 (default SQLite limit 10; reserve 1 slot
for ad-hoc ATTACH). When the cap is reached, oldest plaintext
shards close and only their zstd cold counterparts remain reachable
via on-demand re-ATTACH for compliance queries.

**Rationale**: Datasette (Willison) and Litestream (Ben Johnson)
practitioner consensus: SQLite holds millions of rows on developer
hardware with correct indexes. Pre-emptive partitioning **breaks
atomic cross-shard transactions in WAL mode**
(sqlite.org/lang_attach.html: "Transactions involving multiple
attached databases are atomic, assuming that the main database is
not ':memory:' and the journal_mode is not WAL"). We use WAL —
so ATTACH-shards must be read-only after rotation. Trigger-based
partitioning ensures we pay the cost only when measurably needed.

### D-122-22: Housekeeping cadence + new `ai-eng audit` CLI surface

Daemon-free schedule (cron / launchd / scheduler hook of choice):

| Cadence | Command | Purpose |
|---|---|---|
| Hourly | `PRAGMA optimize;` (auto on connection open) | Statistics refresh per sqlite.org/lang_analyze.html. |
| Nightly | `PRAGMA incremental_vacuum(5000);` | Reclaim ≤20 MB free pages. |
| Nightly | `PRAGMA wal_checkpoint(TRUNCATE);` | Bound WAL growth. |
| Weekly | `ai-eng audit health` | `freelist_count / page_count` ratio + WAL size; alert if bloat > 50 MB. |
| Monthly | `ai-eng audit rotate` | Close current NDJSON, open next month, update hash chain. |
| Monthly | `ai-eng audit compress --month <YYYY-MM>` | zstd seekable on closed plaintext file. |
| Monthly | `ai-eng audit retention apply` | DELETE FROM events WHERE archive_month <= cutoff. |
| Yearly | `ai-eng audit verify-chain --full` | Walk all months end-to-end; Crosby/Wallach validation. |

New CLI surface (extends existing `ai-eng audit` group introduced by
spec-120):

```
ai-eng audit retention apply [--keep-days N]
ai-eng audit rotate
ai-eng audit compress --month YYYY-MM
ai-eng audit verify-chain [--full]
ai-eng audit health
ai-eng audit vacuum [--full|--incremental N]
ai-eng audit query --include-archived
```

**Rationale**: Without explicit cadence, "operational discipline"
degrades to "vacuum when somebody notices the disk is full." Each
command + cadence is sourced from sqlite.org primary docs (PRAGMA
optimize quote: "perhaps once per day"; incremental_vacuum freelist
budget; WAL truncate on idle). Yearly chain verification provides
the audit-trail evidence regulators expect.

### D-122-23: Cross-IDE concurrent NDJSON write safety

Multiple agents (Claude Code + Codex + Gemini CLI + GitHub Copilot)
running in the same repo append concurrently to
`framework-events.ndjson`. POSIX `write(2)` (pubs.opengroup.org)
guarantees atomicity for `O_APPEND` writes ≤ `PIPE_BUF` (Linux
4 KB; POSIX minimum 512 B). The framework enforces:

- Every event payload serialized < 3 KB (safety margin under 4 KB).
- `runtime-guard.py` rejects events ≥ 3 KB and offloads the heavy
  payload to a content-addressed sidecar at
  `state/runtime/event-sidecars/<sha256>.json`; the inline event
  carries only the hash + summary.
- All hooks open NDJSON via `open(path, 'ab')` (Python equivalent
  of `O_APPEND`); never via `O_CREAT|O_TRUNC` mode.
- Non-POSIX filesystems (NFS, HDFS, SMB) are explicitly
  unsupported — hash-chain integrity cannot be guaranteed.

**Rationale**: Without size budget enforcement, two large events
arriving simultaneously can interleave bytes (a kernel `write()`
above PIPE_BUF is no longer atomic per POSIX). 3 KB cap with
sidecar overflow keeps inline events safe. The unsupported-FS
clause is honest engineering: NFS append semantics are
implementation-defined and break the chain. Wellons
(nullprogram.com/blog/2016/08/03/) documents this pitfall.

### D-122-24: `scripts/sync_command_mirrors.py` split + audit

The current `scripts/sync_command_mirrors.py` is 82 KB / ~50
functions/classes — single-file monolith propagating skills + agents
across `.claude/`, `.codex/`, `.gemini/`, `.github/`. The script is
referenced by 3+ skills (ai-skill-evolve, ai-pipeline) and CI. Phase 1
splits it into focused modules:

```
scripts/sync_mirrors/
├── __main__.py             # CLI entry (delegates from existing path for backwards compat)
├── core.py                 # Skill/agent discovery + canonical paths
├── claude_target.py        # .claude/ writer
├── codex_target.py         # .codex/ writer
├── gemini_target.py        # .gemini/ writer
├── copilot_target.py       # .github/ writer (bash + powershell adapters)
├── frontmatter.py          # YAML frontmatter parsing/validation
└── manifest_sync.py        # `framework-capabilities.json` regeneration
```

Backwards compat: `scripts/sync_command_mirrors.py` becomes a thin
shim that imports + delegates to `scripts/sync_mirrors/__main__.py`,
so existing CI references keep working.

**Rationale**: 82 KB single-file is unmaintainable. New IDE targets
(OpenCode, Cursor) become trivial additions if each lives in its own
file. Test coverage per-target becomes possible (today the file is too
big to test in isolation). Backwards compat shim preserves all
external invocation paths.

### D-122-25: `docs/` folder cleanup pass

Audit + cleanup `/Users/soydachi/repos/ai-engineering/docs/`:

| File | Size | Action | Reason |
|---|---|---|---|
| `.DS_Store` | 6 KB | DELETE | macOS junk, must be in `.gitignore` |
| `solution-intent.md` | 32.6 KB | AUDIT + REFRESH | ~32 KB post-cleanup likely contains references to deleted state (memory.db, evals/, custom Rego) |
| `design.pen` | 503 KB | KEEP | Pencil .pen design file; access via Pencil MCP |
| `agentsview-source-contract.md` | 1 KB | AUDIT | External tool contract; may be stale post-spec-120 |
| `anti-patterns.md` | 4.4 KB | AUDIT | Generic anti-patterns guide; verify alignment with current decisions |
| `ci-alpine-smoke.md` | 3.4 KB | AUDIT | CI smoke test docs; verify current alpine version |
| `cli-reference.md` | 5 KB | AUDIT + UPDATE | Add new `ai-eng audit retention/rotate/compress/verify-chain/health` subcommands from D-122-22 |
| `copilot-subagents.md` | 7 KB | AUDIT | Pre-spec-120; verify still accurate |
| `event-assets/` | dir | KEEP | Slide presentation assets |
| `presentations/` | dir | KEEP | Talk decks |

`.gitignore` audit: ensure `.DS_Store` ignored globally.

**Rationale**: Documentation rots in lockstep with code changes
unless explicit cleanup happens. Phase 1 touches state.db,
governance.db (deferred), evals/, memory.db, OPA — every docs file
referencing these needs verification. `.DS_Store` slipping into git
history is a recurring annoyance that a single `.gitignore` audit
prevents.

### D-122-26: `scripts/skill-audit.sh` evaluation

`scripts/skill-audit.sh` (82 LOC) is a spec-106 D-106-04 advisory
audit script. Spec-106 was the framework-knowledge-consolidation
wave — its consolidation work shipped. The script's continued
relevance depends on whether it surfaces drift the modern
`/ai-platform-audit` skill does not already cover.

Phase 1 action: run `skill-audit.sh` once on the repo, compare its
output to `/ai-platform-audit --all`. If subset → DELETE the .sh
script. If complement → KEEP and document in `manifest.yml
required_tools` so it survives audit.

**Rationale**: A two-year-old advisory shell script easily becomes
dead code as the Python skill ecosystem evolves. Either it provides
unique signal (in which case keep + integrate) or it duplicates (in
which case delete). Decision deferred to action time because
running both is a one-minute test.

### D-122-27: Hook canonical events count alignment

`.claude/settings.json` registers 11 hook events: Notification,
PostCompact, PostToolUse, PostToolUseFailure, PreCompact,
PreToolUse, SessionEnd, SessionStart, Stop, SubagentStop,
UserPromptSubmit. CLAUDE.md and ADR-004 reference "~10 canonical
events" / "8 canonical events" depending on revision. Phase 1
reconciles the count + documentation:

- Audit each event for active hook script registration.
- Drop events with NO registered hook (dead wiring).
- Update CLAUDE.md, AGENTS.md, ADR-004 to the actual count after
  audit.
- Add a CI check `tests/unit/hooks/test_canonical_events_count.py`
  that asserts `len(settings_json.hooks)` matches the documented
  count and FAILS on drift.

**Rationale**: 11 vs 8 vs 10 documentation drift is exactly the
kind of staleness that erodes operator trust. Drift-detection in
CI prevents future divergence. Cross-IDE event mapping (Codex,
Gemini, Copilot) follows the same audit.

### D-122-28: Hot-path SLO test coverage

CLAUDE.md asserts pre-commit < 1 s p95 and pre-push < 5 s p95
(framework-source critical path). Phase 1 adds explicit timing
tests:

```python
# tests/unit/hooks/test_hot_path_slo.py
def test_pre_commit_under_1s_p95(): ...
def test_pre_push_under_5s_p95(): ...
def test_hook_invocation_under_50ms(): ...  # individual hook budget
```

These tests run in CI on every PR; failure surfaces budget
violations before merge instead of as user-visible slowdowns.

**Rationale**: SLOs without enforcement are aspirations. Hot-path
discipline is a documented framework-quality contract; CI tests
make it real.

### D-122-29: Phase 1 test coverage for new artifacts

Each Phase 1 sub-track delivers test coverage:

- **State.db migration tests**: round-trip from each existing JSON
  file → state.db → query → assert equivalence. Tests live in
  `tests/integration/state/test_db_migration.py`. Coverage gate:
  every CREATE TABLE statement has at least one INSERT + SELECT
  round-trip test.
- **OPA wiring tests**: `tests/integration/governance/test_opa_eval.py`
  invokes `opa eval --bundle policies/ --input <fixture>` for each
  of the 3 policies, asserts allow/deny on golden inputs. Coverage
  via `opa test --coverage` ≥ 90% line coverage on each .rego.
- **Engram delegation tests**:
  `tests/integration/memory/test_engram_subprocess.py` mocks
  `engram` CLI to verify `/ai-remember` and `/ai-dream` shells out
  correctly + handles failure modes (binary missing, timeout, malformed
  JSON output).
- **Hook integrity tests** (existing) extended to cover state.db
  migration migration-runner integrity.

**Rationale**: Phase 1 deletes ~3K LOC and rewrites governance +
memory + state. Without parallel test coverage, regression
detection becomes manual + fragile. Each sub-spec PR includes
matching test coverage as a merge gate.

### D-122-30: `AIENG_HOOK_INTEGRITY_MODE=enforce` applies to state.db migrations

Existing CLAUDE.md documents the integrity-mode flip from `warn` →
`enforce` per spec-120 follow-up. Phase 1 confirms the same default
applies to the **new state.db migration runner**:

- Migration body sha256 is recorded in `_migrations.sha256` at
  apply time.
- On subsequent app startup, the runner verifies the recorded
  sha256 matches the current source. Mismatch (someone edited a
  migration after applying it) emits `framework_error` with
  `error_code='migration_integrity_violation'` and refuses the
  app start.
- `AIENG_HOOK_INTEGRITY_MODE=enforce|warn|off` extends to govern
  this check; default = `enforce` (matches hook integrity policy).

**Rationale**: Migration tampering is a tamper-evident-audit
concern. The same enforce-by-default discipline that protects
hook scripts must protect schema migrations — both are
constitutional surfaces. Reusing the existing env var keeps the
operational model coherent.

### D-122-31: Documentation drift audit + repair pass

A repo-wide audit fixes stale references discovered during
brainstorm + audit waves:

- `CONSTITUTION.md` references `/ai-implement` (skill does not
  exist; current skill is `/ai-dispatch`). Replace.
- `src/ai_engineering/templates/project/CONSTITUTION.md` same
  stale reference. Replace.
- Skill list in `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
  `.github/copilot-instructions.md`, `README.md` cross-checked
  against actual `.claude/skills/` directory listing. Drift is
  fixed.
- Decision references in skill bodies (`spec-118`, `spec-119`,
  etc.) verified vs `_history.md` (specs deleted by Phase 1
  removed from skill instructions).
- ADR references (`ADR-004 hook events`, etc.) cross-checked to
  current numbering.
- Manifest references (`work_items`, `evaluation`, etc.) cross-
  checked to manifest.yml after Phase 1 edits.
- Solution-intent doc (`docs/solution-intent.md` 32 KB)
  rewritten to reflect post-Phase-1 framework state.
- Repo-wide grep for skill names that no longer exist
  (`/ai-implement`, `/ai-eval-gate`, `/ai-eval`, removed by
  Phase 1) replaces or removes references.

A new CI check `tests/unit/docs/test_skill_references_exist.py`
asserts every `/ai-*` reference in markdown files corresponds to a
skill in `.claude/skills/`; drift fails the build.

**Rationale**: User-flagged `/ai-implement` reference exemplifies
silent doc drift that erodes user trust ("the docs lie, what else
is wrong?"). A repo-wide audit + CI guard turns this into a
one-time cost with permanent prevention.

### D-122-32: Phase 1 split — A/B/C/D parallel tracks (revised from D-122-10)

Supersedes D-122-10's three-spec split. Phase 1 now divides into
**four** sub-specs reflecting the meta-cleanup additions:

- **spec-122-a — hygiene + config + delete evals**:
  D-122-01..04, D-122-07, D-122-08, D-122-11..14, D-122-15,
  D-122-33 (no CODEX.md), D-122-39 (telemetry audit).
  Governance docs slim, no-CODEX.md confirmation, .semgrep tier-1,
  gitleaks tighten, iocs dedupe, manifest orphan removal, evals
  deletion, schemas drop, spec-117-progress relocate, spec-121
  frontmatter fix, wire-memory-hooks delete, runs/ + state/ minor
  cleanup, telemetry consent verify.
  Effort ~5 days, low risk, no behavior change.
- **spec-122-b — engram + state.db**: D-122-05, D-122-06,
  D-122-16..23, D-122-30, D-122-34 (pyproject + uv.lock cleanup),
  D-122-38 (no per-IDE MCP template).
  Engram delegation (100% via `engram setup`), memory.db delete,
  pyproject deps purge + uv lock regen, state.db unified schema,
  PRAGMA, migrations, outbox, retention tiers, NDJSON rotation+zstd,
  partition trigger, housekeeping cadence, cross-IDE write safety,
  migration integrity. Effort ~7 days, medium risk (touches memory
  + audit infra + dependency tree).
- **spec-122-c — OPA proper switch + governance wiring**:
  D-122-09, D-122-29 (governance test slice), D-122-36
  (pre-commit shell wrapper update). OPA binary prereq, 3 .rego v1
  migration, hook wiring (pre-commit, pre-push, risk-accept),
  bundle signing, opa test --coverage, .git/hooks/pre-commit shell
  wrapper updated. Effort ~5 days, medium-high risk (governance
  hot path).
- **spec-122-d — meta-cleanup (docs + scripts + drift)**:
  D-122-24..28, D-122-31, D-122-29 doc-test slice, D-122-35
  (.gitignore audit + global junk patterns), D-122-37 (CHANGELOG
  per sub-spec). sync_command_mirrors split, docs/ audit + refresh,
  skill-audit.sh evaluation, hook event count alignment, hot-path
  SLO tests, /ai-implement and other stale skill references
  repair, solution-intent rewrite, .gitignore global junk patterns,
  CHANGELOG entries scaffolded. Effort ~3-4 days, low-medium risk
  (mostly docs + script split, low blast radius).

Dependency chain: A → B (state schema needed before D's docs about
state) → C → D (D references final state + final OPA). B and C
may proceed in parallel after A merges.

**Rationale**: Three sub-specs underestimated the scope when
meta-cleanup (docs drift + scripts split + tests) entered scope.
Four sub-specs give each domain isolated review + clean rollback
points. Effort total still ~20 days; no scope cut, just
organization.

### D-122-33: No `CODEX.md` overlay; Codex reads `AGENTS.md` natively

`.codex/` directory exists with `agents/`, `skills/`, `config.toml`,
`hooks.json` — but no `CODEX.md` file at repo root. Codex reads
`AGENTS.md` natively. Phase 1 explicitly **does not create a
`CODEX.md`**; documentation referencing Codex points to `AGENTS.md` +
`.codex/config.toml`.

**Rationale**: Adding an overlay where the IDE already supports the
SSOT convention is duplication-by-default. The convention from D-122-02
(IDEs supporting `AGENTS.md` natively need no overlay) applies here:
Codex is the model citizen of the cross-IDE pattern.

### D-122-34: pyproject.toml + uv.lock cleanup post-Engram delegation

D-122-05 deletes `sqlite-vec`, `fastembed`, `hdbscan` deps. Phase 1
explicitly:

- Removes the affected entries from `pyproject.toml` `[project]
  dependencies` AND from any `[project.optional-dependencies.memory]`
  extra.
- Regenerates `uv.lock` via `uv lock --upgrade-package <none>` (full
  refresh).
- Updates `[tool.uv]` workspace section if applicable.
- Drops the `--extra memory` invocation path from
  `ai-eng install` and from CI workflows (`.github/workflows/*.yml`).
- Verifies `uv sync` from clean state succeeds with the trimmed lockfile.

**Rationale**: Deleting deps without lockfile regen is half-work. Stale
lockfile entries cause cryptic install failures for new operators. The
`--extra memory` invocation path is now dead — removing it prevents the
"why doesn't this work?" trap.

### D-122-35: `.gitignore` audit + global junk patterns

Phase 1 audits `/Users/soydachi/repos/ai-engineering/.gitignore` (2.7 KB)
and adds the following global patterns:

```
# OS junk
.DS_Store
**/.DS_Store
Thumbs.db
desktop.ini

# Editor junk
*.swp
*.swo
*~

# Python
__pycache__/
*.py[cod]
.ruff_cache/
.pytest_cache/
.mypy_cache/

# State (must already be present, verify)
.ai-engineering/state/runtime/
.ai-engineering/state/memory.db
.ai-engineering/state/audit-index.sqlite*
.ai-engineering/state/state.db*
.ai-engineering/state/state.db-wal
.ai-engineering/state/state.db-shm
```

Also: scan + delete pre-existing `.DS_Store` files (e.g.
`.codex/.DS_Store` 6 KB, `docs/.DS_Store` 6 KB) committed to history if
present.

**Rationale**: `.DS_Store` slipping into git is a recurring annoyance.
Global ignore + one-time purge prevents future drift. SQLite WAL/SHM
files MUST be ignored (per-developer ephemeral; never committed).

### D-122-36: Pre-commit gate updated for OPA wiring (D-122-09)

The framework's pre-commit gate lives at
`.ai-engineering/scripts/hooks/` + `.git/hooks/pre-commit` shell
wrapper installed by `scripts/install.sh`. Phase 1 (specifically
spec-122-c) updates this wrapper to invoke:

```bash
# After existing ruff + gitleaks + format check:
opa eval --bundle .ai-engineering/policies/ \
  --input <(git diff --cached --name-only | jq -R -s 'split("\n")[:-1]') \
  'data.commit_conventional.deny'
```

If `opa` binary missing → fail-open with `framework_error` event +
clear message ("install opa via `ai-eng install`"). Hot-path budget
preserved: OPA evaluation < 10 ms typical for a structured-input
policy.

**Rationale**: Without explicit pre-commit wiring, OPA migration is
half-work. The shell wrapper at `.git/hooks/pre-commit` is the
canonical local-execution surface; spec-122-c deliverables include the
update.

### D-122-37: CHANGELOG.md entry per sub-spec delivery

`/Users/soydachi/repos/ai-engineering/CHANGELOG.md` (116 KB) tracks all
framework releases. Each Phase 1 sub-spec PR appends an entry under
the Unreleased / next-version section:

```markdown
## [Unreleased]

### Added (spec-122-b)
- `state.db` unified SQLite projection with 7 STRICT tables (events,
  decisions, risk_acceptances, gate_findings, hooks_integrity,
  ownership_map, install_steps).
- `ai-eng audit retention/rotate/compress/verify-chain/health/vacuum`
  CLI commands.
- Engram external delegation via `engram setup <agent>` per IDE.

### Removed (spec-122-b)
- `memory.db` (1.8 MB) and `scripts/memory/` self-hosted memory layer.
- `sqlite-vec`, `fastembed`, `hdbscan` Python dependencies.
- `--extra memory` install path.

### Changed (spec-122-b)
- ...
```

`/ai-pr` skill auto-generates the changelog block from spec frontmatter
+ git diff stat per sub-spec; manual edit as needed.

**Rationale**: Without per-sub-spec changelog discipline, downstream
consumers cannot tell what shipped when. Banking-compliance posture
requires release notes traceable to spec IDs. Auto-generation
prevents the "I'll update CHANGELOG later" trap.

### D-122-38: Engram MCP setup delegated 100% (no per-IDE template)

D-122-05 invokes `engram setup <agent>` per detected IDE. Phase 1
explicitly **does NOT** ship a per-IDE MCP server template inside
`src/ai_engineering/templates/project/`:

- No `.claude/settings.json` MCP block template.
- No `.codex/config.toml` MCP block template.
- No `.gemini/settings.json` MCP block template.
- No `.github/copilot-instructions.md` MCP block template.

`engram setup` is the SSOT for Engram MCP wiring shape. If Engram
adds new IDEs (OpenCode, Cursor, JetBrains AI), ai-engineering picks
them up automatically when it next runs `engram setup`.

**Rationale**: Templating MCP server config inside ai-engineering
duplicates Engram's own setup logic. When Engram updates the MCP shape
(arg names, profile defaults), our templates drift. Single source of
truth — `engram setup` — eliminates the drift surface.

### D-122-39: Telemetry section audit (`manifest.yml telemetry:`)

Current state: `telemetry: { consent: strict-opt-in, default: disabled }`.
Phase 1 verifies:

- The `consent: strict-opt-in` value matches the CONSTITUTION.md +
  Article-X privacy posture (no telemetry without explicit user
  approval at install time).
- Hooks check `manifest.yml.telemetry.default == 'enabled'` (or
  per-user override flag) before emitting events outside the
  framework-events.ndjson chain.
- The OTLP export path (`ai-eng audit otel-export`) honors the
  consent flag — refuses to export if `default: disabled` AND no
  explicit per-export override.
- Documentation in CLAUDE.md / AGENTS.md / README.md states the
  consent posture so users know defaults BEFORE install.

**Rationale**: Telemetry without explicit consent is a banking /
healthcare deal-breaker. The framework's posture (strict-opt-in,
default disabled) is correct; Phase 1 only verifies the wiring
matches the manifest claim and that documentation is consistent.

### D-122-40: Spec path canonicalization — kill `specs/spec.md` doc drift

Canonical active-spec path is `.ai-engineering/specs/spec.md` (matches
resolver default in `src/ai_engineering/state/work_plane.py:240`).
Numbered archive `.ai-engineering/specs/spec-NNN-name.md` lives in
the same directory. Skill markdown references rewritten across all
four IDE skill trees (Claude / Gemini / Codex / agents). CI guard
prevents regression.

**Rationale**: HX-02 (spec-117) introduced `resolve_active_work_plane()`
returning `.ai-engineering/specs/` as default `specs_dir` but skill
markdown was never updated. Result: ai-autopilot, ai-brainstorm,
ai-mcp-sentinel, ai-commit, and several handlers document
`specs/spec.md` while runtime resolves to `.ai-engineering/specs/spec.md`.
Caused user-visible failure during `/ai-autopilot spec-122` Step 0
("no spec" reported because skill expected `specs/spec.md` while
spec lived at `.ai-engineering/specs/spec-122-*.md`). Mechanical
doc-only fix; runtime is correct, documentation is stale.

**Implementation owner**: spec-122-d (meta-cleanup wave; no behavior
change, pure documentation drift).

### D-122-15: Minor `state/` cleanup

The following are removed or relocated:

- `state/instinct-observations.ndjson.repair-backup` (14 KB) deleted — one-off
  artifact from a parse-error fix, no live consumer.
- `state/spec-116-t31-audit-classification.json` (30 KB) and
  `state/spec-116-t41-audit-findings.json` (20 KB) moved to
  `state/archive/spec-116/` — historical analysis with no live reader.
- `state/gate-cache/` (149 JSON blobs) gains a 7-day rolling retention policy
  enforced by a new `ai-eng cache prune` subcommand invoked from a daily
  cron-style hook entry (or, if Phase 2 lands first, via the v2 cron
  framework).
- `state/strategic-compact.json` (44 B, single-counter file with unclear
  consumer) is deleted. If `grep` surfaces a writer during implementation,
  the writer is removed in the same commit (the file's purpose is not
  worth preserving — counter state can be reconstructed from the audit
  log if any process actually needs it).

**Rationale**: `state/` is for live operational data; historical artifacts
and unbounded caches drift toward filesystem clutter. Per-file justification
(consumer present? bounded growth?) is the cleanup heuristic.

## Risks

- **Engram dependency availability across user platforms**: Engram is
  Mac/Linux homebrew today. Windows users in regulated enterprises may not
  have homebrew; direct binary install or chocolatey fallback paths must be
  documented. **Mitigation**: spec-122-b adds a Windows install path test
  and falls back to a documented manual download from Engram releases when
  homebrew is unavailable.
- **state.db migration corruption**: replaying 84k NDJSON entries into the
  events table on first install could fail mid-stream, leaving partial
  state. **Mitigation**: replay is idempotent (`ON CONFLICT(hash) DO
  NOTHING`); a `--rebuild-events` flag in `ai-eng audit index` re-runs from
  line 0 deterministically; `state.db` is regenerable from NDJSON without
  data loss.
- **OPA binary footprint on container CI**: 50 MB binary inflates Docker
  layers and CI cold-start time. **Mitigation**: `opa` is cached in the CI
  image at build time (Dockerfile RUN step); no per-job download. Future
  spec may switch to OPA-WASM for a KB-scale runtime if the cold-start
  cost is measurably bad.
- **OPA Rego v1 migration syntax drift**: the three custom mini-Rego files
  may use idioms not supported in v1 (or vice versa). **Mitigation**:
  `opa test` runs after each migration; coverage flag asserts ≥90% line
  coverage; hand-review of each `.rego` against
  https://www.openpolicyagent.org/docs/v1.2/policy-language/ before merge.
- **Engram MCP setup divergence across IDE versions**: `engram setup` may
  produce different outputs as Engram updates. **Mitigation**: pin Engram
  minor version in `required_tools.baseline.engram = ">=1.15.8,<1.16"`;
  CI runs a settings-file diff smoke test on every Engram bump.
- **GEMINI.md / copilot-instructions.md slim-down breaking IDE behaviour**:
  removing duplicated content may strand a Gemini-only or Copilot-only
  pattern that wasn't in AGENTS.md. **Mitigation**: line-by-line audit
  before deletion; any non-duplicated content gets pulled up into AGENTS.md
  with an `[IDE: gemini|copilot]` annotation; behavioural smoke test
  invokes a known skill in each IDE post-merge.
- **evals deletion regret**: a future regulatory inquiry may ask
  "show me your eval coverage". **Mitigation**: `_history.md` records the
  delete + re-add path; spec-119-v2 stub created in `specs/_proposed/` with
  acceptance criteria for re-introduction.
- **`manifest.yml` orphan-section deletion breaking unknown consumer**: a
  greppable-zero section may still be loaded reflectively. **Mitigation**:
  remove section, run full test suite + `ai-eng doctor` + `ai-eng audit
  index` end-to-end; if anything fails, the section is restored and the
  reflective reader is documented.
- **OPA bundle signing key management**: introducing JWT-signed bundles
  introduces a key-rotation surface area. **Mitigation**: Phase 1 uses a
  single dev-machine signing key documented in the spec-122-c plan;
  production rotation strategy deferred to a follow-up
  governance/key-management spec.
- **Spec split coordination**: spec-122-a, b, c landing as separate PRs
  could create temporal inconsistency (e.g., A merges manifest cleanup
  before B migrates state, and a manifest field B needs is gone).
  **Mitigation**: dependency order is enforced (A → B → C); shared
  manifest sections are flagged in each sub-spec's "depends on" frontmatter;
  CI smoke test runs on each merge to catch breakage before B/C diverge.

## Open Questions

- **D-122-06 final shape**: ✅ resolved. Schema integrated above with seven
  STRICT tables, partial indexes, FTS5 over `decisions.body`, generated
  `ts_unix_ms` STORED column, biconditional CHECK on supersede state
  machine, and 18 sqlite.org / Greg Young / Fowler / Richardson / NIST
  citations.
- **D-122-10 scope split A/B/C**: pending user ratification in the
  `/ai-brainstorm` interrogation. Working assumption is C (three parallel
  sub-specs).
- **D-122-15 `strategic-compact.json`**: ✅ resolved. Delete unconditionally;
  remove writer in same commit if surfaced.
- **D-122-09 Windows OPA install path**: ✅ resolved. Order of preference:
  `winget install OpenPolicyAgent.OPA` → fallback to direct download from
  https://github.com/open-policy-agent/opa/releases (version-pinned in
  `required_tools.baseline.opa.version`). Chocolatey path dropped.
- **D-122-05 Engram scope clarification**: ✅ resolved. ai-engineering's
  responsibility is limited to: (1) install Engram as a host-level
  prereq (mac/linux/windows), (2) invoke `engram setup <agent>` per
  detected IDE so Engram becomes available globally to Claude Code,
  Codex, OpenCode, GitHub Copilot, Gemini CLI. MCP profile selection
  (`agent` vs `admin,agent` vs `all`), tool granularity, and Engram
  internals are out of scope — Engram owns its own UX. ai-engineering's
  follow-up is to optimize its skills and agents to use Engram
  effectively (separate spec, post-Phase-1).
- **D-122-06 events table growth governance**: ✅ resolved by D-122-19
  (retention tiers), D-122-20 (NDJSON rotation + zstd), D-122-21
  (single-table-until-5M trigger), D-122-22 (housekeeping cadence + new
  CLI surface), D-122-23 (cross-IDE concurrent write safety). Background
  research returned 20 verified citations grounding each decision.

## References

- doc: AGENTS.md
- doc: CLAUDE.md
- doc: GEMINI.md
- doc: CONSTITUTION.md
- doc: .github/copilot-instructions.md
- doc: .ai-engineering/CONSTITUTION.md
- doc: .ai-engineering/manifest.yml
- doc: .ai-engineering/contexts/spec-schema.md
- doc: .ai-engineering/references/iocs.json
- doc: .ai-engineering/references/IOCS_ATTRIBUTION.md
- doc: .ai-engineering/state/framework-events.ndjson
- doc: .ai-engineering/state/audit-index.sqlite
- doc: .ai-engineering/state/memory.db
- doc: .ai-engineering/state/decision-store.json
- doc: .ai-engineering/state/ownership-map.json
- doc: .ai-engineering/state/gate-findings.json
- doc: .ai-engineering/state/install-state.json
- doc: .ai-engineering/state/hooks-manifest.json
- doc: .ai-engineering/state/instinct-observations.ndjson
- doc: .ai-engineering/state/instinct-observations.ndjson.repair-backup
- doc: .ai-engineering/state/spec-116-t31-audit-classification.json
- doc: .ai-engineering/state/spec-116-t41-audit-findings.json
- doc: .ai-engineering/state/strategic-compact.json
- doc: .ai-engineering/state/gate-cache/
- doc: .ai-engineering/runs/consolidate-2026-04-29/
- doc: .ai-engineering/schemas/audit-event.schema.json
- doc: .ai-engineering/schemas/decision-store.schema.json
- doc: .ai-engineering/schemas/hooks.schema.json
- doc: .ai-engineering/schemas/lint-violation.schema.json
- doc: .ai-engineering/schemas/manifest.schema.json
- doc: .ai-engineering/schemas/skill-frontmatter.schema.json
- doc: .ai-engineering/scripts/hooks/prompt-injection-guard.py
- doc: .ai-engineering/scripts/wire-memory-hooks.py
- doc: .ai-engineering/scripts/regenerate-hooks-manifest.py
- doc: .ai-engineering/policies/branch_protection.rego
- doc: .ai-engineering/policies/commit_conventional.rego
- doc: .ai-engineering/policies/risk_acceptance_ttl.rego
- doc: .ai-engineering/evals/baseline.json
- doc: .ai-engineering/specs/spec-117-progress/
- doc: .ai-engineering/specs/spec-118-memory-layer.md
- doc: .ai-engineering/specs/spec-119-evaluation-layer.md
- doc: .ai-engineering/specs/spec-120-observability-modernization.md
- doc: .ai-engineering/specs/spec-121-self-improvement-and-hook-completion.md
- doc: .semgrep.yml
- doc: .gitleaks.toml
- doc: .gitleaksignore
- doc: src/ai_engineering/governance/policy_engine.py
- doc: src/ai_engineering/eval/
- doc: scripts/sync_command_mirrors.py
- ext: https://www.openpolicyagent.org/docs/v1.2/
- ext: https://github.com/open-policy-agent/opa
- ext: https://github.com/microsoft/regorus
- ext: https://github.com/Gentleman-Programming/engram
- ext: https://martinfowler.com/eaaDev/EventSourcing.html
- ext: https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing
- ext: https://sqlite.org/whentouse.html
- ext: https://sqlite.org/wal.html
- ext: https://sqlite.org/stricttables.html
- ext: https://sqlite.org/gencol.html
- ext: https://sqlite.org/partialindex.html
- ext: https://sqlite.org/json1.html
- ext: https://sqlite.org/fts5.html
- ext: https://sqlite.org/foreignkeys.html
- ext: https://sqlite.org/lang_altertable.html
- ext: https://sqlite.org/pragma.html#pragma_auto_vacuum
- ext: https://sqlite.org/lockingv3.html
- ext: https://cqrs.files.wordpress.com/2010/11/cqrs_documents.pdf
- ext: https://microservices.io/patterns/data/transactional-outbox.html
- ext: https://litestream.io/
- ext: https://sqlite-utils.datasette.io/
- ext: https://simonwillison.net/2021/Mar/28/sqlite-utils/
- ext: https://csrc.nist.gov/publications/detail/fips/140/3/final
- ext: https://www.zetetic.net/sqlcipher/
- ext: https://sqlite.org/limits.html
- ext: https://sqlite.org/autoinc.html
- ext: https://sqlite.org/backup.html
- ext: https://simonwillison.net/2024/Aug/22/optimizing-datasette/
- ext: https://fly.io/blog/all-in-on-sqlite-litestream/
- ext: https://use-the-index-luke.com/no-offset
- ext: https://github.com/facebook/zstd/blob/dev/contrib/seekable_format/README.md
- ext: https://logdy.dev/blog/post/part-1-log-file-compression-with-gzip-and-zstandard-benchmark
- ext: https://pubs.opengroup.org/onlinepubs/9699919799/functions/write.html
- ext: https://nullprogram.com/blog/2016/08/03/
- ext: https://csrc.nist.gov/pubs/sp/800/92/final
- ext: https://static.usenix.org/event/sec09/tech/full_papers/crosby.pdf
- ext: https://blogs.gnome.org/jnelson/2015/01/06/sqlite-vacuum-and-auto_vacuum/
- ext: https://www.sqliteforum.com/p/database-partitioning-for-large-sqlite
- ext: https://semgrep.dev/explore
- ext: https://github.com/gitleaks/gitleaks
