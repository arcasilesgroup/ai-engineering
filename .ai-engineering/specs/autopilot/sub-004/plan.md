---
total: 22
completed: 0
---

# Plan: sub-004 Meta-Cleanup

## Plan

exports:
  - scripts/sync_mirrors (Python package: __main__, core, frontmatter, manifest_sync, claude_target, codex_target, gemini_target, copilot_target)
  - scripts/sync_command_mirrors.py (≤2KB backwards-compat shim)
  - tests.unit.skills.test_spec_path_canonical (CI guard for D-122-40)
  - tests.unit.hooks.test_canonical_events_count (CI guard for D-122-27)
  - tests.unit.hooks.test_hot_path_slo (CI guard for D-122-28)
  - tests.unit.docs.test_skill_references_exist (CI guard for D-122-31)
  - tests.integration.sync.test_sync_compat (shim-parity guard)
  - docs/cli-reference.md (refreshed with audit subcommands)
  - docs/solution-intent.md (Phase-1-affected sections refreshed)
  - CHANGELOG.md [Unreleased] entries (spec-122-a/b/c/d)
  - .gitignore (state.db*, **/.DS_Store, defensive patterns)
  - canonical docs purged of /ai-implement, ghost skills, legacy specs/ paths

imports:
  - sub-001: final manifest.yml shape, slim CONSTITUTION.md, evals/ deletion confirmed
  - sub-002: state.db* filenames for .gitignore; ai-eng audit CLI verbs (retention/rotate/compress/verify-chain/health/vacuum) for cli-reference; Engram delegation shape for solution-intent
  - sub-003: OPA wiring + Rego policy filenames for solution-intent governance section

### Wave A: Script split + shim (D-122-24)

- [ ] T-4.1: Carve `scripts/sync_mirrors/` package skeleton
  - **Files**: `scripts/sync_mirrors/__init__.py` (new), `scripts/sync_mirrors/__main__.py` (new), `scripts/sync_mirrors/core.py` (new), `scripts/sync_mirrors/frontmatter.py` (new), `scripts/sync_mirrors/manifest_sync.py` (new), `scripts/sync_mirrors/claude_target.py` (new), `scripts/sync_mirrors/codex_target.py` (new), `scripts/sync_mirrors/gemini_target.py` (new), `scripts/sync_mirrors/copilot_target.py` (new)
  - **Done**: `find scripts/sync_mirrors -name '*.py' | wc -l` ≥ 9; each module has docstring + at minimum the function stubs migrated from the monolith (no logic yet); `python -c 'import scripts.sync_mirrors'` succeeds.

- [ ] T-4.2: Migrate logic from monolith into per-IDE modules
  - **Files**: `scripts/sync_mirrors/core.py`, `scripts/sync_mirrors/frontmatter.py`, `scripts/sync_mirrors/manifest_sync.py`, `scripts/sync_mirrors/claude_target.py`, `scripts/sync_mirrors/codex_target.py`, `scripts/sync_mirrors/gemini_target.py`, `scripts/sync_mirrors/copilot_target.py`, `scripts/sync_command_mirrors.py` (original, source for migration)
  - **Done**: All ~50 top-level defs from the original `sync_command_mirrors.py` (functions like `render_gemini_md_placeholders`, `generate_copilot_instructions`, `validate_canonical`, `validate_manifest`, `_generate_surface`, `_check_or_write`, `_handle_orphans`, `_extract_frontmatter`) live in the appropriate module per concern. `ruff check scripts/sync_mirrors/` passes.

- [ ] T-4.3: Write integration test for shim parity (TDD pre-shim)
  - **Files**: `tests/integration/sync/test_sync_compat.py` (new), `tests/integration/sync/__init__.py` (new if missing)
  - **Done**: Test invokes `python scripts/sync_command_mirrors.py --check` (and any other documented argv combinations) via subprocess; captures stdout/stderr/exit code; compares to `python -m scripts.sync_mirrors --check` on a fixture skill tree. Test currently FAILS (shim does not yet exist); fail message is informative.

- [ ] T-4.4: Replace monolith with thin shim
  - **Files**: `scripts/sync_command_mirrors.py` (rewrite to ≤2 KB)
  - **Done**: `wc -c scripts/sync_command_mirrors.py` ≤ 2,000; file imports + delegates to `scripts.sync_mirrors.__main__:main`; `tests/integration/sync/test_sync_compat.py` PASSES; running the shim with no args matches the package output byte-for-byte.

### Wave B: Spec path canonicalization (D-122-40 — NEW)

- [ ] T-4.5: Write CI guard `test_spec_path_canonical.py` (TDD pre-rewrite)
  - **Files**: `tests/unit/skills/test_spec_path_canonical.py` (new)
  - **Done**: Test globs `.claude/skills/**/*.md`, `.gemini/skills/**/*.md`, `.codex/skills/**/*.md`; asserts no occurrence of bare `specs/spec.md`, `specs/plan.md`, or `specs/autopilot/` (not preceded by `.ai-engineering/`). Test currently FAILS with a list of 66 offending files (240 occurrences). Failure message names the first 5 violators with line numbers.

- [ ] T-4.6: Rewrite legacy spec paths across IDE skill trees
  - **Files**: 22 files under `.claude/skills/` (ai-brainstorm/SKILL.md, ai-brainstorm/handlers/spec-review.md, ai-mcp-sentinel/SKILL.md, ai-commit/SKILL.md, ai-autopilot/SKILL.md, ai-autopilot/handlers/phase-{decompose,deep-plan,orchestrate,implement,quality,deliver}.md, ai-dispatch/SKILL.md, ai-dispatch/handlers/deliver.md, ai-pr/SKILL.md, ai-standup/SKILL.md, ai-run/handlers/phase-item-plan.md, _shared/execution-kernel.md, ai-docs/handlers/solution-intent-{init,sync}.md, ai-start/SKILL.md, ai-plan/SKILL.md, ai-plan/handlers/design-routing.md), 22 mirrors under `.gemini/skills/`, 22 mirrors under `.codex/skills/`. Also update `.ai-engineering/contexts/spec-schema.md` if it references `specs/spec.md` legacy paths.
  - **Done**: `tests/unit/skills/test_spec_path_canonical.py` PASSES; `grep -rn 'specs/spec.md\|specs/plan.md\|specs/autopilot/' .claude/skills/ .gemini/skills/ .codex/skills/ | grep -v '\.ai-engineering/'` returns empty. Rewrite is idempotent (regex uses negative-lookbehind; running twice yields zero diff).

### Wave C: `.gitignore` hardening + .DS_Store purge (D-122-35)

- [ ] T-4.7: Update `.gitignore` with global junk + state.db patterns
  - **Files**: `.gitignore`
  - **Done**: `.gitignore` contains `**/.DS_Store`, `state.db*`, `state.db-wal`, `state.db-shm` lines (and any missing from current per master spec D-122-35). `git check-ignore docs/.DS_Store` exits 0.

- [ ] T-4.8: Purge committed `.DS_Store` from working tree
  - **Files**: `docs/.DS_Store` (delete via `git rm --cached`), any other matching files surfaced by `find . -name '.DS_Store' -not -path './.git/*'`
  - **Done**: `find . -name '.DS_Store' -not -path './.git/*'` returns empty; `git ls-files | grep .DS_Store` returns empty. NO `git filter-repo` history rewrite (per Risks: working-tree only).

### Wave D: Hook canonical event count (D-122-27)

- [ ] T-4.9: Audit `.claude/settings.json` event registrations
  - **Files**: `.claude/settings.json` (read-only audit), supporting docs (`CLAUDE.md`, `AGENTS.md`, `.ai-engineering/adr/ADR-004-*.md` if present)
  - **Done**: Drop any matcher whose `command` references a hook script that does not exist on disk (dead wiring). Output: confirmed canonical count = 11 events (UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure, Stop, PreCompact, PostCompact, SessionStart, SubagentStop, Notification, SessionEnd) OR a corrected count if dead matchers are found. Audit findings logged in commit message.

- [ ] T-4.10: Update CLAUDE.md / AGENTS.md / ADR-004 to actual count
  - **Files**: `CLAUDE.md`, `AGENTS.md`, `.ai-engineering/adr/ADR-004-*.md` (if exists; otherwise skip)
  - **Done**: All references to "8 canonical events", "10 canonical events" etc. replaced with the actual audited count from T-4.9. `grep -rn 'canonical event' CLAUDE.md AGENTS.md` returns consistent count.

- [ ] T-4.11: Write CI guard `test_canonical_events_count.py`
  - **Files**: `tests/unit/hooks/test_canonical_events_count.py` (new)
  - **Done**: Test parses `.claude/settings.json`; asserts `len(data["hooks"])` matches the documented count; asserts every matcher's `command` script exists on disk (no dead wiring regression). PASSES post-T-4.10.

### Wave E: Hot-path SLO tests (D-122-28)

- [ ] T-4.12: Write `test_hot_path_slo.py`
  - **Files**: `tests/unit/hooks/test_hot_path_slo.py` (new)
  - **Done**: Three test functions: `test_pre_commit_under_1s_p95`, `test_pre_push_under_5s_p95`, `test_hook_invocation_under_50ms`. Each: 50 iterations via `time.perf_counter`; compute p95 via `statistics.quantiles(n=20)[18]`; assert p95 < budget. CI slack: `if os.getenv("CI"): budget *= 1.2`. Test PASSES on local machine; CI run will validate on actual runner.

### Wave F: Doc drift audit + repair (D-122-31)

- [ ] T-4.13: Replace `/ai-implement` → `/ai-dispatch` in CONSTITUTION docs
  - **Files**: `CONSTITUTION.md` (line 18), `src/ai_engineering/templates/project/CONSTITUTION.md` (line 18)
  - **Done**: `grep -rn '/ai-implement' CONSTITUTION.md src/ai_engineering/templates/project/CONSTITUTION.md` returns empty; `grep -rn '/ai-implement' --include='*.md' .` returns empty (broader sweep).

- [ ] T-4.14: Cross-check skill listings in canonical docs against `.claude/skills/`
  - **Files**: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `README.md`
  - **Done**: For each canonical doc, every `/ai-*` skill reference exists in `.claude/skills/<name>/SKILL.md`. Skills present in `.claude/skills/` but absent from `AGENTS.md → Skills Available` are added (or rationale logged). `grep -oP '/ai-[a-z-]+' AGENTS.md | sort -u` matches `ls .claude/skills/ | grep ^ai-`.

- [ ] T-4.15: Verify spec references in skill bodies vs `_history.md`
  - **Files**: `.claude/skills/**/SKILL.md`, `.claude/skills/**/handlers/*.md`, `.ai-engineering/specs/_history.md`
  - **Done**: `grep -rn 'spec-1[0-9][0-9]' .claude/skills/` cross-checked against `_history.md` archive; references to specs deleted by Phase 1 (per sub-001 deletion list — e.g., `spec-117-progress`, `spec-121`) removed or rewritten to point to `_history.md` summary.

- [ ] T-4.16: Repo-wide grep for ghost skill names
  - **Files**: all `*.md` files
  - **Done**: `grep -rn '/ai-implement\|/ai-eval-gate\|/ai-eval[^a-z-]' --include='*.md' .` returns empty (after replacements). Confirmed: 0 occurrences in canonical doc set; broader sweep catches any in `docs/`, `specs/`, `.ai-engineering/`.

- [ ] T-4.17: Write CI guard `test_skill_references_exist.py`
  - **Files**: `tests/unit/docs/__init__.py` (new), `tests/unit/docs/test_skill_references_exist.py` (new)
  - **Done**: Test walks `**/*.md` (excluding `.git/`, `node_modules/`, `.venv/`); for each `/ai-<name>` regex match, assert `.claude/skills/ai-<name>/SKILL.md` exists. PASSES post-T-4.13..16.

### Wave G: Docs cleanup (D-122-25)

- [ ] T-4.18: Update `docs/cli-reference.md` with new audit subcommands
  - **Files**: `docs/cli-reference.md`
  - **Done**: New section `## Audit and observability` (or appended to existing) lists `ai-eng audit retention`, `ai-eng audit rotate`, `ai-eng audit compress`, `ai-eng audit verify-chain`, `ai-eng audit health`, `ai-eng audit vacuum` (verbs from sub-002 export per master spec D-122-22). `grep 'ai-eng audit retention' docs/cli-reference.md` matches.

- [ ] T-4.19: Refresh `docs/solution-intent.md` Phase-1-affected sections
  - **Files**: `docs/solution-intent.md`
  - **Done**: Sections referencing deleted state (memory.db → Engram delegation; custom Rego → OPA proper; `evals/` → deleted; per-IDE MCP templates → `engram setup`) rewritten. Total file size reduced or held steady (no scope creep). `grep -i 'memory.db\|custom rego\|/ai-implement' docs/solution-intent.md` returns empty (or only in historical-context paragraphs).

- [ ] T-4.20: Audit and refresh remaining docs
  - **Files**: `docs/anti-patterns.md`, `docs/ci-alpine-smoke.md`, `docs/copilot-subagents.md`, `docs/agentsview-source-contract.md`
  - **Done**: Each file read; stale references (deleted skills, deleted state files, deleted scripts) replaced or removed; alpine version in `ci-alpine-smoke.md` matches current CI image; copilot-subagents matches post-spec-120 surface. Commit message logs "no changes needed" for any file confirmed clean.

### Wave H: skill-audit.sh evaluation (D-122-26)

- [ ] T-4.21: Evaluate skill-audit.sh vs /ai-platform-audit; act on result
  - **Files**: `scripts/skill-audit.sh` (delete OR keep), `.ai-engineering/manifest.yml` (update if KEEP)
  - **Done**: Run `bash scripts/skill-audit.sh` once; capture `audit-report.json`. Run `/ai-platform-audit --all` (or read its output equivalent). Compare. **Decision branch**:
    - If `skill-audit.sh` output is a strict subset of `/ai-platform-audit` (or all entries are `eval-failed-cli-missing` because `ai-eng skill eval` does not exist): DELETE `scripts/skill-audit.sh`; commit message documents "eval CLI never landed; advisory script provides no signal".
    - If complement (provides unique signal `/ai-platform-audit` lacks): KEEP; add to `.ai-engineering/manifest.yml` `required_tools` block; document purpose in script header.
  - Branch chosen logged in commit body. `find scripts/skill-audit.sh` either returns empty OR `grep skill-audit.sh .ai-engineering/manifest.yml` matches.

### Wave I: CHANGELOG (D-122-37)

- [ ] T-4.22: Populate CHANGELOG.md `[Unreleased]` per sub-spec
  - **Files**: `CHANGELOG.md`
  - **Done**: Below the existing `## [Unreleased]` block (line 8) and below an `<!-- AUTO -->` marker (added if missing), append four `### Added/Changed/Removed (spec-122-X)` sub-blocks for X = a, b, c, d. Each block summarizes that sub-spec's actual changes (read from sub-001/002/003/004 spec.md frontmatter + `git diff --stat` against the wave commit). `grep '\[Unreleased\]' CHANGELOG.md` shows the block; `grep '(spec-122-d)' CHANGELOG.md` matches; manual edits above `<!-- AUTO -->` preserved.

### Confidence

**HIGH** for the structural moves (Waves A, B, C, F-T-4.13/16, G-T-4.18) because:
- Exact file count is known (66 files / 240 occurrences for D-122-40; 2 files for `/ai-implement`).
- Existing `tests/unit/hooks/test_hook_integrity.py` is a proven scaffold for the three new test files.
- `scripts/sync_command_mirrors.py` boundary cuts are visible from the `def`/`class` listing (per-IDE writers, frontmatter, manifest, core).
- `.gitignore` purge is mechanical (one file: `docs/.DS_Store`).

**MEDIUM** for the audit-driven decisions (T-4.9 canonical event audit, T-4.21 skill-audit eval) because:
- T-4.9 outcome depends on whether dead wirings are found at audit time. Plan supports either branch (count stays 11, or drops to 10/9/8).
- T-4.21 has a binary decision branch (delete vs keep) that resolves at run-time.

**MEDIUM** for T-4.19 solution-intent rewrite because:
- 776 LOC / 32 KB is a large surface; "Phase-1-affected sections only" requires judgement on what counts as affected. Mitigation: scope explicitly bounded to memory.db, OPA, evals/, MCP templates, per-IDE state — anything outside is deferred to spec-123.

**MEDIUM** for T-4.22 CHANGELOG because:
- It depends on sub-001/002/003 wave commits being available to extract diff stats. In autopilot Phase 6 (deliver), `/ai-pr` typically auto-generates; this task scaffolds the structure so Phase 6's auto-gen has somewhere to write.

No blockers identified. All tasks can proceed once sub-001/002/003 reach `implemented` per the DAG dependency declaration.

## Self-Report

[EMPTY — populated by Phase 4]
