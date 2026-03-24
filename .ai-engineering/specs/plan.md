# Plan: spec-064 Install Flow Redesign

## Pipeline: standard
## Phases: 4
## Tasks: 11 (build: 9, verify: 2)

---

### Phase 1: Auto-Detection Module (TDD)
**Gate**: All autodetect unit tests pass. `detect_all()` returns correct `DetectionResult` for repos with markers and empty repos.

- [x] T-1.1: Write failing tests for `detect_stacks()` (agent: build)
  - Create `tests/unit/installer/test_autodetect.py`
  - Test all 13 stack markers (python, javascript, typescript, go, rust, csharp, java, ruby, dart, elixir, swift, php, kotlin)
  - Test empty directory returns `[]`
  - Test multi-stack (pyproject.toml + tsconfig.json → `["python", "typescript"]`)
  - Test javascript vs typescript disambiguation (package.json alone → javascript, with tsconfig.json → typescript)
  - Use `tmp_path` fixtures, `pytest.mark.unit`
  - **Done when**: Tests exist and FAIL (RED)

- [x] T-1.2: Implement `detect_stacks()` to pass tests (agent: build, blocked by T-1.1)
  - Create `src/ai_engineering/installer/autodetect.py`
  - Define `_STACK_MARKERS: dict[str, list[str]]` mapping marker files to stack names
  - Special-case: typescript vs javascript (tsconfig.json presence)
  - Special-case: `*.csproj`, `*.sln` use glob (root-level only)
  - Define `DetectionResult` dataclass with `stacks`, `providers`, `ides`, `vcs` fields
  - **Done when**: T-1.1 tests pass (GREEN)
  - **Constraint**: DO NOT modify test files from T-1.1

- [x] T-1.3: Write failing tests for `detect_ai_providers()`, `detect_ides()`, `detect_vcs()`, `detect_all()` (agent: build)
  - Add tests to `test_autodetect.py`
  - AI providers: `.claude/` → claude_code, `.github/copilot-instructions.md` → github_copilot, `.github/prompts/` → github_copilot, `.agents/` → NOT detected, empty → `[]`
  - IDEs: `.vscode/` → vscode, `.idea/` → jetbrains, both → both, neither → `[]`
  - VCS: mock `detect_from_remote()` → returns "github" or "azure_devops"
  - `detect_all()`: returns `DetectionResult` aggregating all functions
  - **Done when**: Tests exist and FAIL (RED)

- [x] T-1.4: Implement remaining autodetect functions (agent: build, blocked by T-1.3)
  - `detect_ai_providers(root)` — check directory/file existence
  - `detect_ides(root)` — check `.vscode/`, `.idea/`
  - `detect_vcs(root)` — delegate to `detect_from_remote()`, fallback "github" on failure
  - `detect_all(root)` — call all four, return `DetectionResult`
  - **Done when**: All T-1.3 tests pass (GREEN)
  - **Constraint**: DO NOT modify test files from T-1.3

### Phase 2: Wizard Module (TDD)
**Gate**: Wizard tests pass. `questionary` is importable. `run_wizard()` returns correct `WizardResult` for all scenarios.

- [x] T-2.1: Add `questionary` dependency and write wizard tests (agent: build)
  - Add `"questionary>=2.0,<3.0"` to `pyproject.toml` `[project] dependencies`
  - Run `uv sync` to install
  - Create `tests/unit/installer/test_wizard.py`
  - Test: detected items are preselected, non-detected are available
  - Test: empty detection → nothing preselected
  - Test: `WizardResult` dataclass has `stacks`, `providers`, `ides`, `vcs` fields
  - Test: partial resolution (some categories resolved by flags) → wizard skips those
  - Mock `questionary.checkbox()` and `questionary.select()` returns
  - **Done when**: Tests exist, `questionary` imports, tests FAIL (RED)

- [x] T-2.2: Implement `wizard.py` (agent: build, blocked by T-2.1)
  - Create `src/ai_engineering/installer/wizard.py`
  - `WizardResult` dataclass with `stacks`, `providers`, `ides`, `vcs` fields
  - `run_wizard(detected: DetectionResult, resolved: dict | None = None) -> WizardResult`
    - `resolved` keys = categories already provided via CLI flags (skip in wizard)
    - Unresolved categories: `questionary.checkbox()` with detected items as defaults
    - VCS: `questionary.select()` with detected value as default
    - Use `get_available_stacks()`, `get_available_ides()` from `installer/operations.py` for option lists
    - Use `_VALID_AI_PROVIDERS` from `installer/operations.py` for provider options
  - **Done when**: T-2.1 tests pass (GREEN)
  - **Constraint**: DO NOT modify test files from T-2.1

### Phase 3: CLI Integration
**Gate**: `ai-eng install` runs with new detect→wizard flow. Old prompts removed. Flags work. `--non-interactive` works. `--dry-run` works.

- [x] T-3.1: Replace prompt functions in `core.py` (agent: build, blocked by T-1.4, T-2.2)
  - Remove `_prompt_stacks()` function
  - Remove `_prompt_ides()` function
  - Remove `_prompt_external_cicd_docs()` function
  - Remove `_write_cicd_standards_url()` function
  - Remove CI/CD URL prompt call and manifest write from `install_cmd`
  - Simplify `_resolve_ai_providers()`: keep flag-resolution, remove `typer.prompt()` path
  - Simplify `_resolve_vcs_provider()`: keep flag + autodetect paths, remove `typer.prompt()` path
  - New flow in `install_cmd`:
    1. Auto-detect: `detected = detect_all(root)`
    2. Build resolved dict from CLI flags
    3. All categories resolved OR `--non-interactive` → skip wizard
    4. Otherwise → `run_wizard(detected, resolved)`
    5. Merge results → `install_with_pipeline()`
  - Show detection summary before wizard if anything detected
  - `--non-interactive`: uses detection + defaults for undetected categories (no wizard)
  - **Done when**: `ai-eng install` works with new flow, no old prompts remain

- [x] T-3.2: Update CLI-level install tests (agent: build, blocked by T-3.1)
  - Update tests that mock `typer.prompt` → mock `questionary` instead
  - Verify `--non-interactive` uses detection + defaults
  - Verify partial flags (e.g. `--stack python` only) → wizard for remaining
  - Verify full flags → no wizard
  - Verify `--dry-run` → no wizard
  - **Done when**: All install tests pass

### Phase 4: Verification
**Gate**: Full test suite passes. Lint clean. No regressions.

- [x] T-4.1: Full verification suite (agent: verify, blocked by T-3.2)
  - `pytest tests/ -x --tb=short` — all pass
  - `ruff check src/ tests/` — lint clean
  - `ruff format --check src/ tests/` — format clean
  - Verify `test_pipeline.py` passes WITHOUT modification (AC26)
  - **Done when**: All gates green

- [x] T-4.2: Smoke test in clean directory (agent: build, blocked by T-4.1)
  - `mktemp -d` → `cd` → `git init` → `ai-eng install`
  - Verify: "no markers found" message or detection summary
  - Verify: checkbox wizard appears
  - Verify: install completes
  - `ai-eng install --stack python --provider claude_code --ide terminal --vcs github` in another temp dir → no wizard, success
  - **Done when**: Both flows produce valid installations

---

## Agent Assignments Summary

| Agent | Tasks | Purpose |
|-------|-------|---------|
| build | 9 | TDD tests, autodetect module, wizard module, CLI integration |
| verify | 2 | Full test suite, lint, smoke test validation |

## Dependencies

```
T-1.1 → T-1.2 ──┐
T-1.3 → T-1.4 ──┤
                 ├→ T-3.1 → T-3.2 → T-4.1 → T-4.2
T-2.1 → T-2.2 ──┘
```

Phase 1 TDD pairs (T-1.1→T-1.2 and T-1.3→T-1.4) can run in parallel with Phase 2 (T-2.1→T-2.2).
Phase 3 requires all three pairs complete.
Phase 4 is final verification.

## Files Modified

| File | Phase | Action |
|------|-------|--------|
| `src/ai_engineering/installer/autodetect.py` | 1 | create |
| `tests/unit/installer/test_autodetect.py` | 1 | create |
| `pyproject.toml` | 2 | modify (add questionary) |
| `src/ai_engineering/installer/wizard.py` | 2 | create |
| `tests/unit/installer/test_wizard.py` | 2 | create |
| `src/ai_engineering/cli_commands/core.py` | 3 | modify (replace prompts) |
| `tests/unit/installer/test_pipeline.py` | 3 | verify unchanged |
