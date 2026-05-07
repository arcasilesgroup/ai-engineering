---
spec: spec-125
title: state/ Canonical Hardening — Eliminate Optional Category, Relocate Cache/Runtime, Migrate JSON Fallbacks
status: approved
effort: medium
---

# Spec 125 — state/ Canonical Hardening

## Summary

Spec-124 wave 5 deleted 3 of 5 migrated JSON fallbacks (`decision-store.json`, `gate-findings.json`, `ownership-map.json`) and instated CI guard `tests/unit/specs/test_state_canonical.py`. Two files were deferred as a "safety valve" to spec-125: `install-state.json` and `framework-capabilities.json`. Additionally, the canonical contract was left with an `ALLOWED_OPTIONAL_FILES` category that violates the binary "está o no está" governance principle (every artifact must be canonical or absent — no middle ground).

A deeper audit also revealed that several subdirs under `state/` have no business there: `gate-cache/` is a regenerable cache, `runtime/` is session-scoped ephemeral hook state, `archive/` holds legacy snapshots and historical delivery logs already preserved by git, and `audit-archive/` is empty (NDJSON rotation is dormant per Article III's single immutable append-only contract). Only `locks/` has a legitimate reason to live under `state/` — POSIX file-lock coordination for concurrent NDJSON writes (CI + local), which SQLite WAL does not cover.

This spec finalizes spec-122-b's state-plane consolidation by: (1) migrating `install-state.json` and `framework-capabilities.json` to state.db tables with hard cutover (no shim), (2) relocating `runtime/` and `gate-cache/` outside `state/` to sibling `.ai-engineering/runtime/` and `.ai-engineering/cache/` paths, (3) deleting `archive/` and `audit-archive/` along with `rotation.py` dead code, (4) hardening the test guard to forbid the relocated subdirs and validate `locks/` content via pattern, (5) eliminating the `ALLOWED_OPTIONAL_FILES` category entirely (`state.db-shm`/`state.db-wal` reframed as inevitable SQLite siblings, `.DS_Store` moved to FORBIDDEN). Final canonical surface: 4 files + 2 SQLite siblings + 1 dir.

## Goals

- `install-state.json` data migrated to state.db `install_state` table; JSON file deleted from disk and codebase; readers refactored: `src/ai_engineering/install/` (writers), `src/ai_engineering/cli/doctor.py`, `src/ai_engineering/cli/cmd_install.py`, `tests/unit/state/test_install_state.py` (renamed assertions).
- `framework-capabilities.json` data migrated to state.db `tool_capabilities` table; JSON file deleted; readers refactored: `src/ai_engineering/governance/validator/manifest_coherence.py`, `src/ai_engineering/cli/capability_intro.py`, `tests/unit/governance/test_manifest_coherence.py`.
- `gate-cache/` relocated to `.ai-engineering/cache/gate/`; `gate.py` cache_dir refactored; `.gitignore` updated.
- `runtime/` relocated to `.ai-engineering/runtime/`; all hook writers (`runtime-guard.py`, `runtime-stop.py`, `trace_context.py`, `risk_accumulator.py`, `sidecar.py`) and readers refactored; `.gitignore` updated.
- `archive/` deleted entirely (`pre-spec-122-reset-20260505/` + `pre-state-db/` + tracked `delivery-logs/spec-117/`); historical contents recoverable via `git log --diff-filter=D`.
- `audit-archive/` deleted; `rotation.py` removed from codebase (dead code per Article III single-file append-only).
- `tests/unit/specs/test_state_canonical.py` rewritten with binary contract: REQUIRED_FILES = 4, REQUIRED_DIRS = `["locks"]`, FORBIDDEN_FILES expanded, FORBIDDEN_DIRS = `["archive", "audit-archive", "gate-cache", "runtime"]`, locks/ pattern validation (`*.lock`).
- `ALLOWED_OPTIONAL_FILES` category eliminated from test guard; `state.db-shm` + `state.db-wal` reframed as documented inevitable SQLite siblings (not a separate category).
- `.DS_Store` moved from tolerated to FORBIDDEN; `.gitignore` retains line 1-2 OS exclusion but test guard fails if present in `state/`.
- Spec-124 D-124-01 manifest read shim for old IDE keys (`claude_code` → `claude-code`) removed (was deferred to spec-125 per spec-124 spec.md).
- Verification on clean checkout (fresh `git clone` + `ai-eng install` + delete `state/` + recreate via fresh install): `pytest tests/ -x` exit 0, `ruff check .` exit 0, `ruff format --check` exit 0, `gitleaks protect --staged --no-banner` exit 0, `ai-eng doctor` exit 0 with all probes green, `pytest tests/unit/specs/test_state_canonical.py -v` 5/5 pass.
- Documentation paths updated to reflect new layout: `AGENTS.md` (canonical state surface table), `CLAUDE.md` (state path references in observability section), `.github/copilot-instructions.md`, `.codex/AGENTS.md`, `.gemini/GEMINI.md`, `README.md`, `CONSTITUTION.md` (Article III mentions `framework-events.ndjson` path — verify still correct).
- Final canonical state/ surface (after waves 1-4):
  ```
  .ai-engineering/state/
  ├── state.db                        (+ state.db-shm, state.db-wal SQLite siblings)
  ├── framework-events.ndjson         (Article III immutable SoT)
  ├── instinct-observations.ndjson    (instinct learning log)
  ├── hooks-manifest.json             (hooks integrity manifest)
  └── locks/                          (POSIX locks for NDJSON concurrent writes)
  ```

## Non-Goals

- NDJSON rotation reactivation — Article III mandates single immutable append-only file; if size becomes problematic in the future, that requires its own spec.
- `framework-events.ndjson` itself — remains canonical Article III SoT, untouched by this spec.
- `instinct-observations.ndjson` — remains canonical, untouched.
- `hooks-manifest.json` — remains canonical, untouched (regenerated by `regenerate-hooks-manifest.py`).
- Schema design for state.db beyond the 2 new tables (`install_state`, `tool_capabilities`); existing tables stay as-is.
- Cross-IDE behavior changes; Codex/Gemini/Copilot hooks get path updates only (`.codex/hooks/`, `.gemini/hooks/`, `.github/copilot-runtime-*.{sh,ps1}` wrappers translate `state/runtime/` → `runtime/`), no functional changes.
- New caching infrastructure under `.ai-engineering/cache/` beyond relocating `gate-cache/`; subdir is created with single child `gate/`. Future caches added by separate specs.
- Migration tool / CLI for users on old installs — hard cutover, no rollback path. Users on stale checkouts re-run `ai-eng install`.
- New gate caching strategy — only relocates existing cache, does not redesign.
- Performance benchmarks — out of scope; relocation is path change only.

## Decisions

### Theme A — JSON Fallback Migration (Hard Cutover)

**D-125-01: Hard cutover migration for install-state.json + framework-capabilities.json**

Spec-124 wave 5 already established the "one shim period" precedent: spec-124 was the shim release. Spec-125 is the hard cutover. No parallel-write shim, no fallback reader period.

| File | New table | Migration script | Cutover |
|------|-----------|------------------|---------|
| `install-state.json` | `install_state` | New `0004_migrate_install_state.py` | Wave 1: ingest + delete JSON same commit |
| `framework-capabilities.json` | `tool_capabilities` | New `0005_migrate_capabilities.py` | Wave 1: ingest + delete JSON same commit |

**Rationale**: Hard cutover honors the binary canonical contract (no optional category). Spec-124 already provided one release of grace. Repeating shim pattern would re-create the same "deferred" debt. If migration fails in CI, revert the wave commit — that is the rollback path.

**D-125-02: Reader/writer refactor before JSON deletion**

Migrations run in two ordered steps inside Wave 1:
1. Schema migration creates tables + ingestion populates from JSON (JSON intact).
2. All readers + writers refactored to state.db; verification suite passes; JSON deleted in same commit.

**Rationale**: Prevents broken intermediate state. If schema/migration is buggy, step 2 reveals it before deletion. Atomic per-file transition.

**D-125-03: Deprecation warning hook in `state_db.py`**

Existing `_warn_on_deprecated_fallbacks()` (added spec-124 wave 5) extends to detect `install-state.json` + `framework-capabilities.json` reappearance and logs WARN via `framework_error` event. Reappearance = regression.

**Rationale**: Defense in depth. Test guard fails the build, but runtime warning catches edge-case writers that might recreate the JSON outside the test path.

### Theme B — Subdir Relocation

**D-125-04: `runtime/` relocates to `.ai-engineering/runtime/` (sibling of state/)**

| Old path | New path |
|----------|----------|
| `.ai-engineering/state/runtime/checkpoint.json` | `.ai-engineering/runtime/checkpoint.json` |
| `.ai-engineering/state/runtime/ralph-resume.json` | `.ai-engineering/runtime/ralph-resume.json` |
| `.ai-engineering/state/runtime/risk-score.json` | `.ai-engineering/runtime/risk-score.json` |
| `.ai-engineering/state/runtime/skills-index.json` | `.ai-engineering/runtime/skills-index.json` |
| `.ai-engineering/state/runtime/tool-history.ndjson` | `.ai-engineering/runtime/tool-history.ndjson` |
| `.ai-engineering/state/runtime/tool-outputs/` | `.ai-engineering/runtime/tool-outputs/` |
| `.ai-engineering/state/runtime/trace-context.json` | `.ai-engineering/runtime/trace-context.json` |
| `.ai-engineering/state/runtime/autopilot/` | `.ai-engineering/runtime/autopilot/` |
| `.ai-engineering/state/runtime/event-sidecars/` | `.ai-engineering/runtime/event-sidecars/` |

Producers refactored: `runtime-guard.py`, `runtime-stop.py`, `runtime-compact.py`, `runtime-progressive-disclosure.py`, `_lib/trace_context.py`, `_lib/risk_accumulator.py`, `_lib/sidecar.py`, `_lib/runtime_state.py`, `_lib/convergence.py`, `_lib/hook_context.py` (path constants).

**Rationale**: Runtime hook state is session-scoped ephemeral data, semantically distinct from canonical persistent state. Putting it under `state/` conflated two lifecycle classes. Sibling path makes the distinction explicit in the directory layout. `.ai-engineering/runtime/` keeps it project-local (no XDG complications in CI), gitignored as a single block.

**D-125-05: `gate-cache/` relocates to `.ai-engineering/cache/gate/`**

| Old path | New path |
|----------|----------|
| `.ai-engineering/state/gate-cache/<hash>.json` | `.ai-engineering/cache/gate/<hash>.json` |

Producer refactored: `src/ai_engineering/governance/gate.py` (lines 486, 667, 902 — `cache_dir` parameter default).

**Rationale**: `gate-cache/` is a regenerable cache; gate findings are persisted to state.db. The cache only accelerates re-runs. Cache != state. Relocating to `.ai-engineering/cache/` aligns with the binary contract: state/ holds source-of-truth artifacts only.

**D-125-06: New `.gitignore` patterns + cleanup of obsolete patterns**

Add:
```
.ai-engineering/runtime/
.ai-engineering/cache/
```

Remove (obsolete after this spec):
```
.ai-engineering/state/runtime/
.ai-engineering/state/gate-cache/
.ai-engineering/state/audit-archive/
.ai-engineering/state/audit-index.sqlite*
.ai-engineering/state/memory.db*
.ai-engineering/state/memory/
.ai-engineering/state/*-report.json
.ai-engineering/state/strategic-compact.json
.ai-engineering/state/watch-residuals.json
.ai-engineering/state/decision-store.json
.ai-engineering/state/ownership-map.json
.ai-engineering/state/gate-findings.json
.ai-engineering/state/*.repair-backup
```

**Rationale**: Obsolete entries reference files that no longer exist or are forbidden by the test guard. Stale gitignore entries hide regressions (a regenerated `decision-store.json` would silently exist instead of being caught). New entries cover relocated subdirs.

### Theme C — Subdir Deletion

**D-125-07: Delete `archive/` entirely**

Three contents handled:
1. `pre-spec-122-reset-20260505/` (78MB, untracked) — `rm -rf` (untracked, no git impact).
2. `pre-state-db/` (empty) — `rmdir`.
3. `delivery-logs/spec-117/` (824K, 197 tracked files) — `git rm -r`.

**Rationale**: Pre-state.db snapshots are redundant given state.db is canonical and `framework-events.ndjson` hash-chain proves event lineage. Delivery-logs spec-117 are historical artifacts recoverable via `git log --diff-filter=D --all -- .ai-engineering/state/archive/delivery-logs/spec-117/`. Per spec-123 cleanup precedent, "scratch + historical = recoverable via git, not preserved on disk".

**D-125-08: Delete `audit-archive/` + remove `rotation.py`**

Subdir deletion: `rmdir` (currently empty).
Code deletion: remove `src/ai_engineering/audit/rotation.py` + any imports/tests referencing it.

**Rationale**: NDJSON rotation is dead code. Article III mandates `framework-events.ndjson` as single immutable append-only file. Rotation contradicts the contract. If size becomes a problem at scale, a future spec can design the right rotation strategy (compressed archive + hash-chain continuation). Carrying dormant code violates the spec-104 simplification principle.

### Theme D — Test Guard + Optional Category Elimination

**D-125-09: Rewrite `test_state_canonical.py` with binary contract**

```python
REQUIRED_FILES = (
    "framework-events.ndjson",
    "hooks-manifest.json",
    "instinct-observations.ndjson",
    "state.db",
)

REQUIRED_DIRS = ("locks",)

# SQLite WAL artifacts: documented as inevitable side-effects of state.db,
# allowed without being in a separate "optional" category.
SQLITE_WAL_SIBLINGS = frozenset({"state.db-shm", "state.db-wal"})

FORBIDDEN_FILES = (
    "decision-store.json",
    "ownership-map.json",
    "install-state.json",
    "framework-capabilities.json",
    ".DS_Store",
)

# Documented transient artifacts (third category alongside SQLITE_WAL_SIBLINGS).
# Same posture: load-bearing infrastructure, regenerable, path-pinned.
DOCUMENTED_TRANSIENT_FILES = frozenset({"gate-findings.json"})

FORBIDDEN_DIRS = (
    "archive",
    "audit-archive",
    "gate-cache",
    "runtime",
)
```

New tests:
- `test_required_files_present`
- `test_required_dirs_present`
- `test_forbidden_files_absent`
- `test_forbidden_dirs_absent` (NEW)
- `test_locks_dir_pattern` — validates `locks/` contents match `*.lock` regex (NEW)
- `test_no_unexpected_top_level` — any file not in REQUIRED ∪ SQLITE_WAL_SIBLINGS = fail

`ALLOWED_OPTIONAL_FILES` frozenset removed entirely.

**Rationale**: Binary contract per user governance directive: every artifact is canonical, documented-transient, or forbidden. `state.db-shm`/`state.db-wal` are SQLite-managed inevitable siblings (cannot be prevented when state.db is in use), documented in three surfaces: (a) test docstring (frozenset constant `SQLITE_WAL_SIBLINGS` with comment), (b) `AGENTS.md` canonical state surface table (footnote on state.db), (c) `CLAUDE.md` Hooks Configuration section. `.DS_Store` is OS junk and moves to FORBIDDEN; gitignore line 1-2 prevents tracking, test prevents disk presence. Pattern validation on locks/ prevents non-lock cruft accumulating without requiring an allowlist-update for every new lock.

**Clarification (Wave 4a redo, Option C):** `gate-findings.json` is reframed as `DOCUMENTED_TRANSIENT` (third category alongside `SQLITE_WAL_SIBLINGS`), not FORBIDDEN. Same posture as the SQLite WAL siblings: load-bearing infrastructure, regenerated by `ai-commit` after every gate run, gitignored, consumed by `risk` subcommands. Its path is pinned by 14+ tests + `risk_cmd.py` UX. Honors "está o no está" — the file IS canonical-transient (documented + inevitable + regenerable). See `tests/unit/specs/test_state_canonical.py` constant `DOCUMENTED_TRANSIENT_FILES`.

**D-125-10: Remove spec-124 D-124-01 IDE-rename shim**

Spec-124 added a manifest read shim translating `claude_code` → `claude-code`, etc., flagged for removal in spec-125. This spec removes it.

**Rationale**: Single-release courtesy expired. spec-124 was the courtesy release. Stale checkouts re-run `ai-eng install`.

**D-125-11: Sweep stale state/ path references in canonical docs**

Spec-124 wave 5 deleted `decision-store.json` + others but did NOT update `AGENTS.md`. Lines 15, 59, 71 of AGENTS.md still reference deleted/about-to-be-deleted files. Spec-125 owns the doc cleanup that spec-124 missed plus the new path updates.

Concrete edits required:
- `AGENTS.md` line 15: remove `decision-store.json` reference; replace Step 0 instruction with `state.db` query.
- `AGENTS.md` line 59: remove `framework-capabilities.json` reference; replace with state.db `tool_capabilities` table.
- `AGENTS.md` line 71-72: rewrite "Decisions" + "Audit chain" rows; Decisions = `state.db.decisions`, Audit chain = `framework-events.ndjson` (unchanged).
- `CLAUDE.md` Hooks Configuration section: any `state/runtime/`, `state/gate-cache/` path references → new locations.
- `.github/copilot-instructions.md`, `.codex/AGENTS.md`, `.gemini/GEMINI.md`: same path sweep.
- `CONSTITUTION.md` Article III: verify `framework-events.ndjson` path reference is the only state/ reference (other refs out of scope).
- `README.md`: any state/ path refs.

Acceptance: `grep -rn "decision-store\.json\|ownership-map\.json\|install-state\.json\|framework-capabilities\.json\|state/runtime\|state/gate-cache\|state/archive\|state/audit-archive" --include="*.md" --include="*.yml" .` returns zero matches outside `_history.md` and `.ai-engineering/specs/`.

**Rationale**: Documentation drift is a governance smell. Stale refs in canonical docs (AGENTS.md is loaded at every session start) silently misdirect the agent. Closing this gap during spec-125 prevents the drift from compounding.

## Risks

**R-125-01: Migration script bug corrupts state.db**

Mitigation: Each migration runs inside a transaction (`BEGIN ... COMMIT`); failure auto-rollbacks. Migrations are idempotent (re-runnable). CI runs migrations on a clean state.db before merge. Wave 1 verification suite validates row counts match JSON before deletion.

**R-125-02: Hook path refactor breaks runtime observability**

Mitigation: All hook scripts have integration tests (`tests/integration/hooks/`); refactor PR runs the full hook test suite. Path constant centralized in `_lib/hook_context.py:RUNTIME_DIR` so a single refactor point covers all hooks. Cross-IDE wrappers (Copilot bash + PowerShell) tested in CI matrix.

**R-125-03: Test guard regression on macOS due to .DS_Store**

Mitigation: `.DS_Store` was previously tolerated. Hardening to FORBIDDEN means a developer with `.DS_Store` in their checkout will fail CI. Mitigation: `.gitignore` already excludes (line 1-2), and the test guard runs in CI on Linux runners where `.DS_Store` is never created. Local devs see the failure only if they manually copy state/ files via Finder.

**R-125-04: Relocated paths break external tooling expecting old paths**

Mitigation: Deep grep for `state/runtime/`, `state/gate-cache/`, `state/archive/`, `state/audit-archive/` references across codebase + .github/ + docs. Update all hits in the same wave. External users (downstream installs of ai-engineering) have no API contract on these paths — internal layout.

**R-125-05: spec-124 wave 6 not yet shipped — branch conflict**

Mitigation: Verify spec-124 status before opening spec-125 branch. If wave 6 incomplete, ship it first or stack spec-125 on top of `feat/spec-122-framework-cleanup-phase-1` HEAD. Coordinate with current branch maintainer.

**R-125-06: 78MB `pre-spec-122-reset-20260505/` deletion drops audit chain integrity reference**

Mitigation: Verify `framework-events.ndjson` hash-chain is intact before deletion (`ai-eng audit replay --session=all` integrity check). The pre-spec-122 snapshot contains a previous audit-index.sqlite + framework-events.ndjson — any historical query needs were satisfied at spec-122 cutover. Integrity proof now lives in the current `framework-events.ndjson` hash-chain itself, not the snapshot.

**R-125-07: Cross-IDE hook scripts reference `state/runtime/` paths beyond inventory**

Mitigation: Pre-refactor exhaustive grep across all IDE surfaces: `.claude/`, `.codex/`, `.gemini/`, `.github/`, `.ai-engineering/scripts/hooks/`, `_lib/`. Build path-reference inventory before W2 starts. Acceptance criterion for W2: `grep -r "state/runtime\|state/gate-cache\|state/archive\|state/audit-archive" .` returns zero matches outside `.ai-engineering/specs/spec-125*.md` and historical `_history.md` entries. Cross-IDE wrappers (`copilot-runtime-{guard,stop,progressive-disclosure}.{sh,ps1}`) tested in CI matrix.

**R-125-08: External tooling (`agentsview` companion, `engram` memory layer) reads `state/runtime/`**

Mitigation: `agentsview` is a separately installed companion — verify its session-discovery path config; if hardcoded, file an issue or PR upstream (out of this spec's scope, but document the breakage). Engram is opt-in and stores in its own location (`~/.engram/` or per docs), no overlap. Confirmed via grep before W2.

## References

- pr: TBD
- doc: .ai-engineering/specs/spec-124-spec.md (predecessor — D-124-01 shim removal, D-124-12 state cleanup deferral)
- doc: tests/unit/specs/test_state_canonical.py (current contract to be rewritten)
- doc: CONSTITUTION.md (Article III — immutable append-only audit log)
- doc: AGENTS.md (canonical state surface declaration)
- doc: src/ai_engineering/state/state_db.py (`_warn_on_deprecated_fallbacks()` — extension point for D-125-03)

## Open Questions

None — all decisions resolved during interrogation. Wave breakdown defers to `/ai-plan`:
- W1: Theme A (migrations + JSON deletion)
- W2: Theme B (relocations: runtime/ + gate-cache/)
- W3: Theme C (deletions: archive/ + audit-archive/ + rotation.py)
- W4: Theme D (test guard hardening + .gitignore + IDE shim removal)
