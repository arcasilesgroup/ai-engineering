# Persistence Doctrine

> Authoritative reference for **where data lives** in ai-engineering.
> Cited from [CONSTITUTION.md](../CONSTITUTION.md) §13 and
> [CLAUDE.md](../CLAUDE.md) §0. Files-only since spec-148 (the embedded
> SQLite `state.db` was removed); amendments require an ADR.

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

## The three tiers

The framework stores state across three tiers chosen by the *shape* of
the data, not by convenience. A datum belongs to exactly one tier, and
within that tier to exactly one canonical file. There is **no database**:
spec-148 removed the embedded SQLite `state.db` so the obvious reading of
every store is a plain file on disk.

### Tier 1 — NDJSON audit log

- **Canonical for:** framework events (every hook fire, every skill
  invocation, every gate decision). The audit chain is the
  ground-truth witness used by `/ai-explain`, `/ai-verify`, and
  external auditors.
- **File pattern:** `.ai-engineering/state/framework-events.ndjson`
  (one JSON object per line, hash-chained via `prev_event_hash`).
- **Write SLA:** O(1) append — no parsing, no schema validation on
  write. Hot path budget under 50ms p95.
- **Read pattern:** sequential scan (cold path). `ai-eng audit tokens`
  (skill/agent/session rollups), `ai-eng audit replay` (span tree), and
  `ai-eng audit verify` (chain integrity) all read the NDJSON directly —
  there is no SQLite projection in between.
- **Write trigger:** every hook fire (PreToolUse, PostToolUse,
  SessionStart, SessionEnd, ...) and every policy decision via
  `src/ai_engineering/governance/decision_log.py:emit_policy_decision`.
- **Hot-path status:** yes — must stay append-only and lock-free.

### Tier 2 — JSON / YAML records + configuration

- **Canonical for:** mutable structured records and machine-readable
  configuration whose schema is declared in Python (Pydantic) and
  consumed by the deterministic plane. Small datasets read whole, with
  `mtime` caching — the scale at which a file beats a database.
- **Canonical record files (per-install state, written via the durable
  repository; gitignored):**
  - `.ai-engineering/state/decision-store.json` — governance decisions
    **and** risk acceptances (risk acceptances are decision records). Carries
    the optional per-entry SHA-256 hash chain verified by `ai-eng audit verify`.
  - `.ai-engineering/state/ownership-map.json` — the update-decision
    ownership map (`ai-eng update` reads it before evaluating create/update).
  - `.ai-engineering/state/install-state.json` — the writable install state
    (`InstallState` model dump: vcs/tooling/platforms/readiness + hook hashes).
  - `.ai-engineering/state/framework-capabilities.json` — the skill/agent
    capability catalog (a derived cache; see below).
- **Configuration files:**
  - `.ai-engineering/manifest.yml` — framework configuration
    (stacks, surfaces, telemetry consent).
  - `.ai-engineering/state/hooks-manifest.json` — pinned sha256
    digests of every hook script for `run_hook_safe` integrity
    verification.
  - `.ai-engineering/state/gate-findings.json` — primary
    gate/risk/verify artifact; emitted by gate/review orchestration and
    read by verify/risk surfaces.
  - `.ai-engineering/suppression-allowlist.yml` — Article VII
    suppression exceptions (governed by `tools/no_suppression/`).
- **Write SLA:** sub-second; tooling-validated. Never written from the
  hot-path hooks.
- **Read pattern:** Pydantic parse on read; small enough to read whole.
- **Write trigger:** spec approval (`/ai-brainstorm`, `/ai-plan`), CLI
  commands (`ai-eng decision`, `ai-eng risk`, `ai-eng ownership import`),
  installer phases, and operator config edits.
- **Hot-path status:** read-only on the hot path; writes are cold path.

### Tier 3 — Markdown human-authored truth

- **Canonical for:** human-authored doctrine and narrative state.
  Reviewable in PRs, diffable across history, indexable by humans.
- **File patterns:**
  - `.ai-engineering/specs/spec.md`, `.ai-engineering/specs/plan.md`
    (active spec workflow output).
  - `.ai-engineering/specs/archive/spec-NNN-*.md` (post-merge archive).
  - `.ai-engineering/LESSONS.md` (self-improvement loop per
    CLAUDE.md operating mindset #7).
  - [`CONSTITUTION.md`](../CONSTITUTION.md) (project identity).
  - [`CLAUDE.md`](../CLAUDE.md) (canonical cross-IDE rulebook;
    mirrors regenerated from
    `src/ai_engineering/templates/project/CANONICAL.md`).
  - [`CHANGELOG.md`](../CHANGELOG.md) (Keep-a-Changelog format;
    every removal / breaking change documented).
- **Write SLA:** human-typed; no machine perf budget. Mirror sync
  is the only mechanical writer.
- **Read pattern:** operator + LLM session bootstrap; CI parsers
  (decision backfill, mirror-parity gates).
- **Write trigger:** operator commits; `scripts/sync_mirrors/core.py`
  for the byte-equivalent CLAUDE.md / AGENTS.md /
  copilot-instructions.md mirrors.
- **Hot-path status:** no. Markdown is operator and reviewer surface.

## Derived caches

A *derived cache* is a writable store whose content is fully
reconstructible from a Tier 1–3 source-of-truth. Caches MAY be queried
for speed; they MUST NOT be the primary witness for any audit, gate, or
compliance claim.

| Cache name | Source-of-truth | Rebuild command | Freshness contract |
|------------|-----------------|-----------------|--------------------|
| `framework-capabilities.json` | The manifest + the on-disk skill/agent surface | `write_framework_capabilities()` (run by `ai-eng install`/`update`) | Rebuilt on demand from the manifest + disk; never authoritative on its own. |
| `decision-store.json` (ADR `D-NNN-NN` rows) | `.ai-engineering/specs/*.md` + `CHANGELOG.md` (Tier 3) | `ai-eng decision backfill` | Backfilled on operator demand and on `/ai-brainstorm` approval. Risk/flow decision rows written by `ai-eng risk`/`decision record` are lifecycle data, not rebuildable from specs. |

`ownership-map.json` is the canonical update-decision store, not a
derived cache: `ai-eng update` reads it before evaluating create/update
actions. `gate-findings.json` is the primary gate/risk/verify artifact.

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
  `ai-eng gate run --force` to clear matching entries before a fresh run.
- **State boundary:** old `.ai-engineering/state/gate-cache/` remains
  forbidden; the live cache belongs under `.ai-engineering/cache/gate/`.

## Strict rules

1. **No silent dual-writes.** A datum lives in exactly one canonical
   tier. If a second store needs the same datum for query speed, it
   is a derived cache — named in the table above, with a rebuild
   command, and clearly marked in code as `# derived cache; rebuild
   via <command>`.
2. **The audit chain stays on NDJSON.** `framework-events.ndjson` is
   the canonical witness; `ai-eng audit tokens`/`replay`/`verify` read
   it directly. Gates and external audits verify against the NDJSON
   (`ai-eng audit verify`).
3. **No SQLite anywhere (spec-148 files-only).** The embedded `state.db`
   was removed; no `src/` module nor hook may import `sqlite3` (except the
   one-shot legacy export migration in `ai-eng update`). Enforced
   mechanically by `tests/architecture/test_no_sqlite.py`.
4. **Schema authority lives in Pydantic.** The state models
   (`tools/skill_domain/state_models.py`) define each file's shape; the
   JSON file homes are written via the durable repository
   (`src/ai_engineering/state/repository.py`) and validated on read.
5. **Hard deletes — no shims.** Per CONSTITUTION.md §13.3, renamed
   / deleted / migrated stores are removed outright. No
   backwards-compatibility mirror, no dual-write fallback, no
   deprecation alias. The CHANGELOG documents every removal.

## Migration (pre-spec-148 installs)

`ai-eng update` runs a one-shot `export → verify → delete` migration: if
a legacy `state.db` is present, it ingests `install_state`, `decisions`,
and `ownership_map` into their file homes, verifies the export, then
deletes `state.db` (+ WAL/SHM). No backup — the fail-loud verify gate is
the safety net (`state.db` is never deleted unless every export verifies).
Idempotent; a no-op once `state.db` is gone.

## Operator surface — what changes for you

None of these run on the hot path; all are idempotent and safe to re-run.

- `ai-eng decision list` — read active decisions from
  `decision-store.json`. Empty on a fresh checkout until
  `ai-eng decision backfill` populates it from spec markdown.
- `ai-eng decision backfill` — parse `.ai-engineering/specs/*.md`
  and `CHANGELOG.md`, extract `D-NNN-NN` records, write
  `decision-store.json`. Idempotent.
- `ai-eng ownership import` — parse `.github/CODEOWNERS`, write
  `ownership-map.json`. Re-run after every CODEOWNERS edit.
- `ai-eng audit verify | tokens | replay` — verify the hash chain and
  report token usage / span trees over `framework-events.ndjson`.

## Glossary

- **SSOT-PD** — *Single Source of Truth Per Datum.* Every datum lives in
  exactly one canonical writable store; all other copies are labelled
  derived caches.
- **Derived cache** — a writable store whose content is fully
  reconstructible from a Tier 1–3 source-of-truth via a named rebuild
  command. Query convenience, never primary witness.
- **Hot path** — code reached by every operator action (every save,
  every commit, every prompt). Budgeted: pre-commit under 1 second,
  pre-push under 5 seconds, hooks under 50ms p95.
- **Cold path** — code reached by deliberate operator action (installer
  phases, `ai-eng <cmd>` invocations, SessionEnd, CI jobs). Correctness
  over latency.
- **Tier** — one of the three canonical persistence layers (NDJSON
  audit, JSON/YAML records+config, Markdown). Each tier has its own
  write SLA and hot-path status.
- **Files-only** — the framework's design choice (spec-148) to store
  every datum as a plain file (append-only chain for events, JSON/YAML
  for records and config, Markdown for human-authored doctrine) rather
  than an embedded database — the right shape for a kilobyte-scale,
  single-writer, cross-OS developer tool.
