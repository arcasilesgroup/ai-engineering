# Plan: spec-125 state/ Canonical Hardening

## Pipeline: full
## Phases: 4
## Tasks: 78 (build: 61, verify: 14, guard: 3)

## Architecture

**Pattern**: CQRS / Event Sourcing (extension of spec-122-b state-plane consolidation).

**Justification**: state plane already separates write model (`framework-events.ndjson` immutable append-only audit log per Article III) from read model (`state.db` SQLite projection rebuilt via migrations `0001_initial_schema.py`, `0002_seed_from_json.py`, `0003_replay_ndjson.py`). Spec-125 completes the projection migration: the last two JSON fallbacks (`install-state.json`, `framework-capabilities.json`) become projection tables (`install_state`, `tool_capabilities`) populated by new ordered migrations `0004` and `0005`. JSON fallback readers refactor to query state.db. Pattern criteria match: (a) immutable history of state changes, (b) multiple read-projections from same write source, (c) deterministic rebuild via migration replay, (d) hash-chained audit ledger (`framework-events.ndjson`). No new pattern; spec-125 finalizes the pattern's adoption across all state artifacts.

## Design

Routing decision: `skipped`. Rationale: infrastructure refactor with zero UI surface change. No design-intent.md needed.

## Phase 1 — Theme A: JSON Fallback Migration (Wave 1)

**Gate**: `install-state.json` + `framework-capabilities.json` deleted from disk + codebase. state.db has populated `install_state` + `tool_capabilities` tables. All 14 source readers + 14 test fixtures refactored. `pytest tests/unit/state/ tests/integration/state/ -v` passes. `_warn_on_deprecated_fallbacks()` extended to detect both files.

- [ ] T-1.1: Add `install-state.json` and `framework-capabilities.json` to `_DEPRECATED_JSON_FALLBACKS` tuple at `src/ai_engineering/state/state_db.py:56-60` (agent: build)
- [ ] T-1.2: Write failing tests for `install_state` table contract: schema columns, idempotent ingestion, round-trip read/write — `tests/unit/state/test_install_state_table.py` (TDD RED) (agent: build)
- [ ] T-1.3: Create migration `src/ai_engineering/state/migrations/0004_migrate_install_state.py` — CREATE TABLE `install_state` + INSERT FROM JSON via `_runner.py` interface (`run(conn)` function) — must pass T-1.2 (agent: build)
- [ ] T-1.4: Refactor `src/ai_engineering/cli_commands/setup.py:195,202,295,308,386,397` — replace JSON read/write with state.db queries (agent: build)
- [ ] T-1.5: Refactor `src/ai_engineering/cli_commands/core.py:375` — state.db read (agent: build)
- [ ] T-1.6: Refactor `src/ai_engineering/cli_commands/guide.py:24` — state.db read (agent: build)
- [ ] T-1.7: Refactor `src/ai_engineering/detector/readiness.py:313` — state.db read (agent: build)
- [ ] T-1.8: Refactor `src/ai_engineering/doctor/phases/detect.py:3,51,57` — state.db read (agent: build)
- [ ] T-1.9a: Update install-state e2e tests — `tests/e2e/test_install_clean.py:64,77,82`, `tests/e2e/test_install_existing.py:78`, `tests/e2e/test_install_pipeline.py:74` (agent: build)
- [ ] T-1.9b: Update install-state integration tests — `tests/integration/state/test_db_migration.py:78`, `tests/integration/test_cli_command_modules.py:25,27,174`, `tests/integration/test_doctor_fix_go_stack.py:35,63`, `tests/integration/test_doctor_fix_node_stack.py:75`, `tests/integration/test_doctor_integration.py:153` (agent: build)
- [ ] T-1.9c: Update install-state unit tests — `tests/unit/state/test_install_state.py:431,444,447`, `tests/unit/state/test_migration.py:29` (agent: build)
- [ ] T-1.10: Write failing tests for `tool_capabilities` table contract — `tests/unit/state/test_tool_capabilities_table.py` (TDD RED) (agent: build)
- [ ] T-1.11: Create migration `src/ai_engineering/state/migrations/0005_migrate_framework_capabilities.py` — CREATE TABLE `tool_capabilities` + INSERT FROM JSON — must pass T-1.10 (agent: build)
- [ ] T-1.12: Refactor `src/ai_engineering/installer/phases/state.py:30` (`write_framework_capabilities` writer) — state.db (agent: build)
- [ ] T-1.13: Refactor `src/ai_engineering/installer/service.py:68,100,464,466` — state.db (agent: build)
- [ ] T-1.14: Refactor `src/ai_engineering/state/agentsview.py:12,14,57,59,66` — state.db (agent: build)
- [ ] T-1.15: Refactor `src/ai_engineering/state/context_packs.py:37` (`DERIVED_CAPABILITY_PLANE` constant) — state.db (agent: build)
- [ ] T-1.16: Refactor `src/ai_engineering/state/control_plane.py:115,171` — state.db (agent: build)
- [ ] T-1.17: Refactor `src/ai_engineering/state/observability.py:29,79,968,1002-1005` (`FRAMEWORK_CAPABILITIES_REL`, `build_framework_capabilities`) — state.db (agent: build)
- [ ] T-1.18: Refactor `src/ai_engineering/state/repository.py:137-143` (`load_framework_capabilities`, `save_framework_capabilities`) — state.db (agent: build)
- [ ] T-1.19: Refactor `src/ai_engineering/validator/categories/manifest_coherence.py:340` — state.db (agent: build)
- [ ] T-1.20a: Update framework-capabilities e2e + integration tests — `tests/e2e/test_install_clean.py:67`, `tests/integration/test_installer_integration.py:301` (agent: build)
- [ ] T-1.20b: Update framework-capabilities unit tests — `tests/unit/test_context_packs.py:39,80`, `tests/unit/test_installer.py:138,153`, `tests/unit/test_runtime_repositories.py:70,86`, `tests/unit/test_state_plane_contract.py:43`, `tests/unit/test_state.py:109` (agent: build)
- [ ] T-1.21: Delete `.ai-engineering/state/install-state.json` + `.ai-engineering/state/framework-capabilities.json` from disk (agent: build)
- [ ] T-1.22: Run `pytest tests/unit/state/ tests/integration/state/ tests/integration/test_installer*.py tests/integration/test_doctor*.py tests/integration/test_cli_command_modules.py tests/e2e/ -v` — must pass (agent: verify)
- [ ] T-1.23: Run `ai-eng doctor` on clean checkout — confirm no probe regression (agent: verify)
- [ ] T-1.24: Verify `_warn_on_deprecated_fallbacks()` triggers `framework_error` event when test recreates JSON files temporarily — `tests/unit/state/test_state_db_fallback_warning.py` extended assertion (agent: build)

## Phase 2 — Theme B: Subdir Relocation (Wave 2)

**Gate**: `runtime/` lives at `.ai-engineering/runtime/`, `gate-cache/` lives at `.ai-engineering/cache/gate/`. All hook scripts use central `RUNTIME_DIR` + `CACHE_DIR` constants. Cross-IDE wrappers (Copilot bash + ps1, Codex, Gemini) translate paths. Template mirrors updated. `.gitignore` updated. Hook integration tests pass. Acceptance grep: `grep -rn "state/runtime\|state/gate-cache" --include="*.py" --include="*.sh" --include="*.ps1" .` returns zero matches outside specs/.

- [ ] T-2.1: Write failing test for `RUNTIME_DIR` + `CACHE_DIR` constant resolution — `tests/unit/hooks/test_hook_context_paths.py` asserts `RUNTIME_DIR == project_root / ".ai-engineering" / "runtime"` and `CACHE_DIR == project_root / ".ai-engineering" / "cache"` (TDD RED — must fail before T-2.2) (agent: build)
- [ ] T-2.2: Add `RUNTIME_DIR` + `CACHE_DIR` path constants to `.ai-engineering/scripts/hooks/_lib/hook_context.py` (single source of truth) — must make T-2.1 pass (TDD GREEN, blocked by T-2.1, DO NOT modify test from T-2.1) (agent: build)
- [ ] T-2.3: Refactor `runtime-guard.py:9` (tool-outputs path) — use RUNTIME_DIR (agent: build)
- [ ] T-2.4: Refactor `runtime-progressive-disclosure.py:118` (`_SKILL_INDEX_REL`) — use RUNTIME_DIR (agent: build)
- [ ] T-2.5: Refactor `runtime-session-start.py:11` (trace-context.json) — use RUNTIME_DIR (agent: build)
- [ ] T-2.6: Refactor `runtime-stop.py` + `runtime-compact.py` — checkpoint.json + ralph-resume.json paths use RUNTIME_DIR (agent: build)
- [ ] T-2.7: Refactor `_lib/hook-common.py:225` (event-sidecars path) — use RUNTIME_DIR (agent: build)
- [ ] T-2.8: Refactor `_lib/risk_accumulator.py:28` (docstring + risk-score.json path) — use RUNTIME_DIR (agent: build)
- [ ] T-2.9: Refactor cross-IDE Copilot wrappers `.github/copilot-runtime-{guard,stop,progressive-disclosure}.sh` — translate `state/runtime/` → `runtime/` (agent: build)
- [ ] T-2.10: Refactor cross-IDE Copilot PowerShell wrappers `.github/copilot-runtime-{guard,stop,progressive-disclosure}.ps1` (agent: build)
- [ ] T-2.11: Update Codex hook references in `.codex/hooks/` (agent: build)
- [ ] T-2.12: Update Gemini hook references in `.gemini/hooks/` (agent: build)
- [ ] T-2.13: Refactor `src/ai_engineering/cli_commands/gate.py:486` (primary `cache_dir` assignment) — `.ai-engineering/cache/gate/` (agent: build)
- [ ] T-2.14: Refactor `src/ai_engineering/cli_commands/gate.py:667` (second `cache_dir` for status/clear) (agent: build)
- [ ] T-2.15: Refactor `src/ai_engineering/cli_commands/gate.py` lines 12 (docstring), 301, 350, 355, 497, 691, 819 — gate-cache references (agent: build)
- [ ] T-2.16: Update `.gitignore` — add `.ai-engineering/runtime/`, `.ai-engineering/cache/`; remove obsolete entries (lines 167-170, 175, 180, 183-186, 189-194 — see spec D-125-06) (agent: build)
- [ ] T-2.17a: Update template mirrors `src/ai_engineering/templates/project/.claude/` — replace stale `state/runtime/`, `state/gate-cache/` references (agent: build)
- [ ] T-2.17b: Update template mirrors `src/ai_engineering/templates/project/.github/` — same path sweep (agent: build)
- [ ] T-2.17c: Update template mirrors `src/ai_engineering/templates/project/.gemini/` — same path sweep (agent: build)
- [ ] T-2.17d: Update template mirrors `src/ai_engineering/templates/project/.codex/` — same path sweep (agent: build)
- [ ] T-2.18: Run hook integration tests `pytest tests/integration/hooks/ -v` — must pass (agent: verify)
- [ ] T-2.19: Run cross-IDE wrapper tests in CI matrix (Linux + macOS + Windows for Copilot ps1) — agent: verify
- [ ] T-2.20: Acceptance grep — `grep -rn "\.ai-engineering/state/runtime\|\.ai-engineering/state/gate-cache" --include="*.py" --include="*.sh" --include="*.ps1" --include="*.md" --include="*.yml" .` returns zero matches outside `_history.md` and `.ai-engineering/specs/` (agent: verify)

## Phase 3 — Theme C: Subdir + Code Deletion (Wave 3)

**Gate**: `state/archive/`, `state/audit-archive/` deleted from filesystem. `rotation.py` removed from codebase. `test_compress.py` removed. `audit_cmd.py` rotation imports removed. No functional code references rotation or audit-archive. `pytest tests/unit/state/ tests/unit/audit/` passes.

- [ ] T-3.1: Verify `framework-events.ndjson` hash-chain integrity before any deletion — `ai-eng audit replay --session=all` integrity check (agent: verify)
- [ ] T-3.2: `git rm -r .ai-engineering/state/archive/delivery-logs/spec-117/` (197 tracked files) (agent: build)
- [ ] T-3.3: `rm -rf .ai-engineering/state/archive/pre-spec-122-reset-20260505/` (78MB untracked snapshot) (agent: build)
- [ ] T-3.4: `rmdir .ai-engineering/state/archive/pre-state-db/` + `rmdir .ai-engineering/state/archive/` (now empty) (agent: build)
- [ ] T-3.5: `rmdir .ai-engineering/state/audit-archive/` (empty) (agent: build)
- [ ] T-3.6: Delete `src/ai_engineering/state/rotation.py` (455 lines) (agent: build)
- [ ] T-3.7: Delete `tests/unit/state/test_compress.py` (imports rotation.py) (agent: build)
- [ ] T-3.8: Refactor `src/ai_engineering/cli_commands/audit_cmd.py:662,689,720` — remove lazy imports of `rotate_now`, `compress_closed_month`, `verify_archive_chain`; remove or stub the `audit rotate` / `audit compress` subcommands (agent: build)
- [ ] T-3.9: Update `tests/unit/state/test_retention.py` if affected by rotation.py removal (agent: build)
- [ ] T-3.10: Acceptance grep — `grep -rn "from ai_engineering\.state\.rotation\|import rotation\|audit-archive\|rotate_now\|compress_closed_month\|compress_month\|verify_archive_chain" src/ tests/` returns zero matches (agent: verify)
- [ ] T-3.11: Run `pytest tests/unit/state/ tests/unit/audit/ tests/integration/audit/ -v` — must pass (agent: verify)

## Phase 4 — Theme D: Test Guard + Optional Elimination + Doc Sweep (Wave 4)

**Gate**: `test_state_canonical.py` rewritten with binary contract (REQUIRED_FILES=4, REQUIRED_DIRS=`("locks",)`, FORBIDDEN_FILES expanded, FORBIDDEN_DIRS=`("archive","audit-archive","gate-cache","runtime")`, no ALLOWED_OPTIONAL_FILES). `_LEGACY_IDE_KEY_MAP` removed from both shim sites. AGENTS.md, CLAUDE.md, README.md, CHANGELOG.md, CONSTITUTION.md, all `.claude/.gemini/.github/.codex/` agent + skill docs scrubbed of stale paths. `pytest tests/ -x` passes. `ruff check`, `ruff format --check`, `gitleaks protect --staged`, `ai-eng doctor` all clean.

- [ ] T-4.1: Rewrite `tests/unit/specs/test_state_canonical.py` — new constants: `REQUIRED_FILES = ("framework-events.ndjson","hooks-manifest.json","instinct-observations.ndjson","state.db")`, `REQUIRED_DIRS = ("locks",)`, `SQLITE_WAL_SIBLINGS = frozenset({"state.db-shm","state.db-wal"})` (with explanatory comment), `FORBIDDEN_FILES = ("decision-store.json","gate-findings.json","ownership-map.json","install-state.json","framework-capabilities.json",".DS_Store")`, `FORBIDDEN_DIRS = ("archive","audit-archive","gate-cache","runtime")`. Remove `ALLOWED_OPTIONAL_FILES` entirely (agent: build)
- [ ] T-4.2: Add new tests: `test_forbidden_dirs_absent`, `test_locks_dir_pattern` (validates `*.lock` regex over locks/ contents), update `test_no_unexpected_top_level` to use REQUIRED ∪ SQLITE_WAL_SIBLINGS (agent: build)
- [ ] T-4.3: Delete `_LEGACY_IDE_KEY_MAP` constant + `_migrate_legacy_ide_keys` function from `src/ai_engineering/config/loader.py:67,94-100,113-114,149-150` (agent: build)
- [ ] T-4.4: Delete `claude_code` entry from `_PROVIDER_ALIASES` in `src/ai_engineering/cli_commands/core.py:1147-1149` (agent: build)
- [ ] T-4.5: Update test fixtures `tests/unit/state/test_install_state.py:425-447` — replace `claude_code` with `claude-code` (agent: build)
- [ ] T-4.6: Update test fixture `tests/unit/state/test_migration.py:29` — replace `claude_code` (agent: build)
- [ ] T-4.7: Update `tests/integration/test_gate_cross_ide.py:102,124,649,674` — remove `claude_code` regex alternation (agent: build)
- [ ] T-4.8: Sweep `AGENTS.md` lines 15, 59, 71-72 — replace decision-store.json + framework-capabilities.json refs with `state.db.decisions` + `state.db.tool_capabilities`; document SQLITE_WAL_SIBLINGS as state.db footnote (agent: build)
- [ ] T-4.9: Sweep `CLAUDE.md` Hooks Configuration section — update `state/runtime/`, `state/gate-cache/` path references (agent: build)
- [ ] T-4.10: Sweep `CONSTITUTION.md` — verify Article III references only `framework-events.ndjson` (no other state/ paths) (agent: build)
- [ ] T-4.11: Sweep `README.md` + `CHANGELOG.md` — state path refs (agent: build)
- [ ] T-4.12: Sweep `.github/copilot-instructions.md` (agent: build)
- [ ] T-4.13: Sweep `.codex/AGENTS.md` (agent: build)
- [ ] T-4.14: Sweep `.gemini/GEMINI.md` (agent: build)
- [ ] T-4.15: Sweep `.claude/agents/` files containing stale paths: `ai-autopilot.md`, `ai-guard.md`, `ai-build.md`, `ai-guide.md`, `verifier-governance.md`, `verifier-architecture.md`, `verify-deterministic.md` (agent: build)
- [ ] T-4.16: Sweep `.claude/skills/ai-verify/handlers/verify.md`, `.claude/skills/ai-security/SKILL.md` (agent: build)
- [ ] T-4.17: Sweep `.gemini/` mirror set (agents + skills, ~20 files) (agent: build)
- [ ] T-4.18: Sweep `.github/` mirror set (agents + skills, ~20 files) (agent: build)
- [ ] T-4.19: Sweep `.codex/` mirror set (agent: build)
- [ ] T-4.20: Sweep `src/ai_engineering/templates/project/` mirrors that propagate to new installs (agent: build)
- [ ] T-4.21: Acceptance grep — `grep -rn "decision-store\.json\|ownership-map\.json\|install-state\.json\|framework-capabilities\.json\|state/runtime\|state/gate-cache\|state/archive\|state/audit-archive" --include="*.md" --include="*.yml" --include="*.json" .` returns zero matches outside `_history.md` and `.ai-engineering/specs/spec-125*` (agent: verify)
- [ ] T-4.22: Run full test suite — `pytest tests/ -x` exit 0 (agent: verify)
- [ ] T-4.23: Run `ruff check . && ruff format --check` — exit 0 (agent: verify)
- [ ] T-4.24: Run `gitleaks protect --staged --no-banner` — exit 0 (agent: verify)
- [ ] T-4.25: Run `ai-eng doctor` on clean checkout — all probes green (agent: verify)
- [ ] T-4.26: Run `pytest tests/unit/specs/test_state_canonical.py -v` — 5+ tests pass (binary contract enforced) (agent: guard)
- [ ] T-4.27: Verify final `state/` listing matches spec D-125-09 surface — guard advisory check (agent: guard)
- [ ] T-4.28: Final governance check — confirm no new `ALLOWED_OPTIONAL_FILES` resurrected (agent: guard)

## Risks Forwarded from Spec

- **R-125-01** (migration corruption): mitigated by transactional migrations + T-1.22 verification
- **R-125-02** (hook refactor breakage): mitigated by T-2.1 central path constant + T-2.18 integration tests
- **R-125-03** (`.DS_Store` macOS): mitigated by `.gitignore` + T-4.1 FORBIDDEN
- **R-125-04** (relocation external tooling): mitigated by T-2.20 + T-4.21 acceptance grep
- **R-125-05** (spec-124 wave 6 conflict): pre-flight check before plan execution — confirm spec-124 complete or stack on top
- **R-125-06** (audit chain integrity): T-3.1 hash-chain verification before deletion
- **R-125-07** (cross-IDE wrapper coverage): T-2.9..T-2.12 explicit refactor + T-2.20 grep
- **R-125-08** (agentsview/engram external readers): R-125-04 grep also catches; engram opt-in unaffected

## Pre-Execution Checks

1. Confirm spec-124 wave 6 status — if pending, complete first OR stack spec-125 on `feat/spec-122-framework-cleanup-phase-1` HEAD with explicit branch decision
2. New branch: `feat/spec-125-state-canonical-hardening` recommended (clean separation)
3. Backup `state.db` before T-1.3 first migration run
4. Verify clean working tree (no untracked files except expected `state/runtime/` outputs)

## References

- spec: `.ai-engineering/specs/spec.md`
- predecessor: spec-124 (commit `1cb3cb0d` — wave 5 deferred install-state + framework-capabilities)
- migration runner: `src/ai_engineering/state/migrations/_runner.py`
- canonical guard: `tests/unit/specs/test_state_canonical.py`
- architecture pattern: `.ai-engineering/contexts/architecture-patterns.md` (CQRS / Event Sourcing)
