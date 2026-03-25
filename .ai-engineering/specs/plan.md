# Plan: spec-066 Relocate scripts/hooks/ into .ai-engineering/

## Pipeline: standard
## Phases: 5
## Tasks: 10 (build: 8, verify: 2)

---

### Phase 1: File Moves
**Gate**: Template and dogfooding hooks exist at new paths. Old paths don't exist.

- [x]T-1.1: Move template source (agent: build)
  - `git mv src/ai_engineering/templates/project/scripts/hooks/ src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/`
  - Verify `src/ai_engineering/templates/project/scripts/` is empty, remove it
  - Verify `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/` contains all 34+ files + `_lib/`
  - **Done when**: Template source at new path, old `scripts/` dir gone (AC3, AC5)

- [x]T-1.2: Move dogfooding copy (agent: build)
  - `git mv scripts/hooks/ .ai-engineering/scripts/hooks/`
  - Remove empty `scripts/` directory
  - **Done when**: Dogfooding at `.ai-engineering/scripts/hooks/`, old `scripts/` gone (AC4)

### Phase 2: Installer + Updater Code (parallel tasks)
**Gate**: `_COMMON_TREE_MAPS` points to new path. Hooks phase verifies new path. Migration function exists in updater.

- [x]T-2.1: Update installer templates.py and phases/hooks.py (agent: build, blocked by T-1.1)
  - `templates.py` line 76: `("scripts/hooks", "scripts/hooks")` → `(".ai-engineering/scripts/hooks", ".ai-engineering/scripts/hooks")`
  - `phases/hooks.py` line 98: `context.target / "scripts/hooks"` → `context.target / ".ai-engineering" / "scripts" / "hooks"`
  - `phases/hooks.py` line 100: `"scripts/hooks/ empty or missing"` → `".ai-engineering/scripts/hooks/ empty or missing"`
  - **Done when**: Installer deploys to and verifies new path (AC10, AC11)

- [x]T-2.2: Add migration function to updater/service.py (agent: build, blocked by T-1.1)
  - Add `_migrate_hooks_dir(target: Path)` near existing `_migrate_legacy_dirs()` (~line 360)
  - Logic: if `target / "scripts" / "hooks"` exists and is dir → `shutil.copytree` to `target / ".ai-engineering" / "scripts" / "hooks"`, then `shutil.rmtree` old, then remove empty `scripts/` dir if empty
  - Must be idempotent: if new path already exists, skip silently
  - Call from `update()` before `_evaluate_project_files()`
  - Update `_evaluate_project_files()` lines ~203-217: tree map paths are read from `_COMMON_TREE_MAPS` which is already updated by T-2.1, no extra changes needed here (verify this)
  - **Done when**: `ai-eng update` migrates old hooks to new path (AC12, AC13, AC14)

### Phase 3: Path References (all tasks parallel, blocked by T-1.1 + T-1.2)
**Gate**: All settings.json, hooks.json, shell, and PowerShell references point to `.ai-engineering/scripts/hooks/`.

- [x]T-3.1: Update Claude Code settings.json (template + dogfooding) (agent: build, blocked by T-1.1)
  - Template: `src/ai_engineering/templates/project/.claude/settings.json` — replace all `scripts/hooks/` → `.ai-engineering/scripts/hooks/` (~10 occurrences)
  - Dogfooding: `.claude/settings.json` — same replacement (~10 occurrences)
  - Use `replace_all` for efficiency
  - **Done when**: All settings.json hook paths updated (AC6)

- [x]T-3.2: Update GitHub Copilot hooks.json (template + dogfooding) (agent: build, blocked by T-1.1)
  - Template: `src/ai_engineering/templates/project/github_templates/hooks/hooks.json` — replace `scripts/hooks/` → `.ai-engineering/scripts/hooks/` (3 entries)
  - Dogfooding: `.github/hooks/hooks.json` — replace `./scripts/hooks/` → `./.ai-engineering/scripts/hooks/` (12 entries)
  - **Done when**: All hooks.json paths updated (AC7)

- [x]T-3.3: Fix shell script dirname navigation (agent: build, blocked by T-1.1)
  - 3 telemetry scripts: replace `$(dirname "$0")/../..` → `$(dirname "$0")/../../..`
    - `.ai-engineering/scripts/hooks/telemetry-skill.sh` (line ~33)
    - `.ai-engineering/scripts/hooks/telemetry-session.sh` (line ~17)
    - `.ai-engineering/scripts/hooks/telemetry-agent.sh` (line ~61)
  - 5 copilot scripts: replace `"$SCRIPT_DIR/../.."` → `"$SCRIPT_DIR/../../.."`
    - `.ai-engineering/scripts/hooks/copilot-skill.sh` (line ~13)
    - `.ai-engineering/scripts/hooks/copilot-session-start.sh` (line ~13)
    - `.ai-engineering/scripts/hooks/copilot-session-end.sh` (line ~13)
    - `.ai-engineering/scripts/hooks/copilot-error.sh` (line ~13)
    - `.ai-engineering/scripts/hooks/copilot-agent.sh` (line ~13)
  - Also update same lines in template copies at `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/`
  - **Done when**: All 8 scripts navigate 3 levels up (AC8)

- [x]T-3.4: Fix PowerShell script path navigation (agent: build, blocked by T-1.1)
  - 2 scripts: add one `Split-Path -Parent` level
    - `.ai-engineering/scripts/hooks/telemetry-session.ps1` (line ~10)
    - `.ai-engineering/scripts/hooks/telemetry-skill.ps1` (line ~18)
  - Also update template copies
  - **Done when**: 2 PowerShell scripts navigate 3 levels up (AC9)

### Phase 4: Tests + Policy
**Gate**: All tests pass with new paths.

- [x]T-4.1: Update test paths and policy scope (agent: build, blocked by T-3.3)
  - `tests/unit/test_template_parity.py` line 15: `"scripts" / "hooks"` → `".ai-engineering" / "scripts" / "hooks"`
  - `tests/unit/test_template_parity.py` line 16: `"project" / "scripts" / "hooks"` → `"project" / ".ai-engineering" / "scripts" / "hooks"`
  - `tests/unit/test_strategic_compact.py` line 16: `"scripts" / "hooks"` → `".ai-engineering" / "scripts" / "hooks"`
  - `tests/integration/test_strategic_compact_integration.py` line 15: same change
  - `tests/integration/test_telemetry_canary.py` lines 34,35,47,48: `"scripts/hooks/..."` → `".ai-engineering/scripts/hooks/..."`
  - `tests/integration/test_telemetry_canary.py` line 106: `"scripts" / "hooks"` → `".ai-engineering" / "scripts" / "hooks"`
  - `src/ai_engineering/policy/test_scope.py` line 405: `"scripts/hooks/**"` → `".ai-engineering/scripts/hooks/**"`
  - **Done when**: All test/policy paths point to new location (AC15-AC17)

### Phase 5: Verification
**Gate**: Full test suite passes. Hooks fire. CHANGELOG untouched.

- [x]T-5.1: Run full test suite + lint (agent: verify, blocked by T-4.1)
  - `uv run pytest tests/ -x --tb=short` — all pass
  - `uv run ruff check src/ tests/` — lint clean
  - Verify `test_template_parity.py` passes (AC15)
  - Verify `test_strategic_compact.py` passes (AC16)
  - Verify `test_telemetry_canary.py` passes (AC17)
  - Verify CHANGELOG.md has NO changes to `scripts/hooks` references (AC20)
  - **Done when**: All gates green, zero regressions (AC18)

- [x]T-5.2: Smoke test install + update (agent: build, blocked by T-5.1)
  - Create temp dir, `git init`, `ai-eng install --stack python --provider claude_code --ide terminal --vcs github`
  - Verify `.ai-engineering/scripts/hooks/` exists with hooks
  - Verify `scripts/hooks/` does NOT exist at project root
  - Verify `.claude/settings.json` references `.ai-engineering/scripts/hooks/`
  - **Done when**: Clean install deploys hooks at new path (AC1, AC2, AC10)

---

## Agent Assignments Summary

| Agent | Tasks | Purpose |
|-------|-------|---------|
| build | 8 | File moves, code changes, path updates, smoke test |
| verify | 2 | Full test suite, lint, CHANGELOG check |

## Dependencies

```
T-1.1 ─┬→ T-2.1 ──────────────────┐
        ├→ T-2.2                    │
        ├→ T-3.1                    │
        ├→ T-3.2                    ├→ T-4.1 → T-5.1 → T-5.2
        ├→ T-3.3                    │
        └→ T-3.4                    │
T-1.2 ──────────────────────────────┘
```

Phase 1 tasks are sequential (T-1.1 then T-1.2).
Phase 2 and Phase 3 tasks are ALL parallel (6 independent tasks, all blocked by Phase 1).
Phase 4 depends on all of Phase 2+3.
Phase 5 is final verification.

## Files Modified

| File | Phase | Action |
|------|-------|--------|
| `src/ai_engineering/templates/project/scripts/hooks/` | 1 | move to `project/.ai-engineering/scripts/hooks/` |
| `scripts/hooks/` | 1 | move to `.ai-engineering/scripts/hooks/` |
| `src/ai_engineering/installer/templates.py` | 2 | tuple update |
| `src/ai_engineering/installer/phases/hooks.py` | 2 | verification path |
| `src/ai_engineering/updater/service.py` | 2 | migration function |
| `src/ai_engineering/templates/project/.claude/settings.json` | 3 | 10 hook paths |
| `.claude/settings.json` | 3 | 10 hook paths |
| `src/ai_engineering/templates/project/github_templates/hooks/hooks.json` | 3 | 3 script paths |
| `.github/hooks/hooks.json` | 3 | 12 script paths |
| 8 shell scripts (template + dogfooding) | 3 | dirname 2→3 levels |
| 2 PowerShell scripts (template + dogfooding) | 3 | Split-Path 2→3 levels |
| 4 test files | 4 | path constants |
| `src/ai_engineering/policy/test_scope.py` | 4 | scope glob |
