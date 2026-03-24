---
id: spec-064
title: "Install Flow Redesign: Auto-Detection + Wizard UX"
status: draft
created: 2026-03-24
refs: []
---

# spec-064: Install Flow Redesign

## Problem

`ai-eng install` has a broken user experience:

1. **Hostile prompts**: Four sequential free-text prompts ask for "AI assistants", "Technology stacks", "IDE integrations", and "External CI/CD standards URL". Users don't know what values are valid. The labels don't match how users think about their setup.

2. **No auto-detection for stacks or providers**: VCS provider is auto-detected from git remote, but technology stacks and AI providers require manual input. In a Python repo with `.claude/` already present, the user still has to type "python" and "claude" manually.

3. **Empty repo = blind guessing**: When running in a folder with no code, the user faces four prompts with no guidance. Default values (python, claude, terminal, github) are silently applied if the user just presses Enter, but there's no indication these ARE the defaults being chosen.

4. **CI/CD URL prompt on every install**: The "External CI/CD standards URL" prompt appears even in empty repos where it makes no sense. This is a post-install configuration concern.

5. **Bug (fixed)**: `NameError: name '_copy_tree' is not defined` in `ide_config.py` — already resolved in current branch (replaced with `copy_tree_for_mode`).

## Solution

Replace the four free-text prompts with a two-phase flow:

```
Phase 1: AUTO-DETECT    — scan repo for stack markers, AI provider configs, VCS, IDEs
Phase 2: WIZARD         — questionary checkbox UI for user to confirm/modify selections
```

### Flow A: Repo with detectable content
```
$ ai-eng install
Scanning project...
  Detected: Python (pyproject.toml), Claude Code (.claude/), GitHub (remote)

? Select technology stacks:  (Use arrow keys and space to toggle)
  ● python       (detected)
  ○ typescript
  ○ go
  ...

? Select AI providers:
  ● claude_code       (detected)
  ○ github_copilot
  ○ gemini
  ○ codex

? Select VCS provider:
  ● github       (detected)
  ○ azure_devops

Installing governance framework...
  ✓ Detection
  ✓ Governance framework    42 files
  ✓ IDE configuration       12 files
  ...
```

### Flow B: Empty repo (nothing detected)
```
$ ai-eng install
Scanning project... no markers found.

? Select technology stacks:  (Use arrow keys and space to toggle)
  ○ python
  ○ typescript
  ○ go
  ...
```

Nothing preselected — user chooses explicitly.

## Scope

### In Scope

**A) Auto-Detection Module**

1. Create `src/ai_engineering/installer/autodetect.py` with pure functions:
   - `detect_stacks(root: Path) -> list[str]` — scan for file markers
   - `detect_ai_providers(root: Path) -> list[str]` — scan for config directories
   - `detect_ides(root: Path) -> list[str]` — scan for IDE workspace markers
   - `detect_vcs(root: Path) -> str` — delegate to existing `detect_from_remote()` in `vcs/factory.py`
   - `detect_all(root: Path) -> DetectionResult` — aggregate all detection into a single result

2. Stack detection markers:
   | Marker file | Stack |
   |-------------|-------|
   | `pyproject.toml`, `setup.py`, `setup.cfg`, `Pipfile` | python |
   | `package.json` (without `tsconfig.json`) | javascript |
   | `tsconfig.json` OR (`package.json` + `tsconfig.json`) | typescript |
   | `go.mod` | go |
   | `Cargo.toml` | rust |
   | `*.csproj`, `*.sln` | csharp |
   | `pom.xml`, `build.gradle`, `build.gradle.kts` | java |
   | `Gemfile` | ruby |
   | `pubspec.yaml` | dart |
   | `mix.exs` | elixir |
   | `Package.swift` | swift |
   | `composer.json` | php |
   | `build.gradle.kts` (Kotlin DSL) | kotlin |

3. AI provider detection markers:
   | Marker | Provider |
   |--------|----------|
   | `.claude/` directory | claude_code |
   | `.github/copilot-instructions.md` OR `.github/prompts/` directory | github_copilot |

   gemini and codex are NOT auto-detected (they share `.agents/` directory — ambiguous).

4. IDE detection markers (own logic, NOT delegated to `detect_ide_families()` which is SonarLint-specific):
   | Marker | IDE |
   |--------|-----|
   | `.vscode/` directory | vscode |
   | `.idea/` directory | jetbrains |
   | No markers detected | terminal (not preselected — user chooses) |

   Note: `detect_ide_families()` in `platforms/sonarlint.py` returns `IDEFamily` enum values for SonarLint config. The install pipeline uses different string values (`terminal`, `vscode`, `jetbrains`, `cursor`). These are separate concerns — autodetect writes its own IDE detection.

**B) Wizard Module**

5. Create `src/ai_engineering/installer/wizard.py` using `questionary`:
   - `run_wizard(detected: DetectionResult) -> WizardResult` — full interactive flow
   - Each category uses `questionary.checkbox()` with detected items preselected
   - VCS uses `questionary.select()` (single choice)
   - Non-interactive mode (`--non-interactive`) skips wizard, uses detection + defaults

6. Add `questionary` as dependency in `pyproject.toml`.

**C) CLI Integration**

7. Replace the four prompt functions in `core.py:install_cmd`:
   - Remove `_prompt_stacks()`, `_prompt_ides()`, `_resolve_ai_providers()` interactive paths
   - Remove `_prompt_external_cicd_docs()` entirely
   - Remove `_write_cicd_standards_url()` from install flow
   - New flow: `autodetect(root)` → `wizard(detected)` → `install_with_pipeline()`

8. Preserve CLI flags (`--stack`, `--provider`, `--ide`, `--vcs`) as overrides that skip both detection and wizard for that category. When SOME flags are provided, the wizard prompts ONLY for the unresolved categories.

**D) CI/CD URL Removal**

9. Remove CI/CD standards URL prompt from install flow. Users who need this can edit `.ai-engineering/manifest.yml` directly (`cicd.standards_url` field). A dedicated `ai-eng config set` command is out of scope for this spec.

**E) Tests**

10. Unit tests for `autodetect.py`: test each marker detection in isolation with tmp_path fixtures.
11. Unit tests for `wizard.py`: mock questionary prompts, verify result mapping.
12. Update existing install CLI tests to work with new flow (pipeline-level tests should be unaffected).

### Out of Scope

- Changes to the 6-phase install pipeline (detect, governance, ide_config, hooks, state, tools)
- Changes to template resolution or file copying logic
- New stack support (only detect what already exists in `contexts/languages/`)
- Auto-detection for gemini/codex providers
- Changes to `ai-eng update` or `ai-eng doctor`
- Rich TUI beyond questionary checkboxes (no full-screen dashboard)

## Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | `questionary` for wizard UI | Supports native checkboxes, is lightweight (~200KB), prompt_toolkit is already a transitive dependency. Better UX than free-text or Rich prompts. |
| D2 | Separate autodetect module (pure functions) | Testable without mocking UI. DetectPhase runs inside the pipeline spinner — wizard must run BEFORE the pipeline. Clean separation. |
| D3 | Only auto-detect claude_code and github_copilot | These have unique filesystem markers. gemini and codex share `.agents/` — ambiguous detection would confuse users more than help. |
| D4 | Empty repo = nothing preselected | Forces explicit choice. Silent defaults (python, claude, terminal) caused the original confusion. If the user wants python, they check the box. |
| D5 | Remove CI/CD URL from install | This is a configuration concern, not an installation concern. Clutters the first-run experience. Users edit manifest.yml directly if needed. |
| D6 | CLI flags override detection + wizard | `--stack python --provider claude_code` should work in CI/CD without any interactive prompts. Flags are the non-interactive escape hatch. |
| D7 | VCS uses select() not checkbox() | Single choice — a project has one VCS provider. Radio button semantics. |
| D8 | Own IDE detection, not `detect_ide_families()` | `detect_ide_families()` returns SonarLint `IDEFamily` enum — different concept from install IDE selections (`terminal`, `vscode`, `jetbrains`, `cursor`). Autodetect needs its own simple marker scan. |
| D9 | VCS detection via `detect_from_remote()` | `_detect_vcs()` in detect.py is a private function that takes `InstallContext`. `detect_from_remote()` in `vcs/factory.py` takes `Path` and is already used by `core.py`. Cleaner API for autodetect. |

## Acceptance Criteria

### Auto-Detection
- [ ] AC1: `detect_stacks()` returns `["python"]` when `pyproject.toml` exists in root
- [ ] AC2: `detect_stacks()` returns `["python", "typescript"]` when both `pyproject.toml` and `tsconfig.json` exist
- [ ] AC2b: `detect_stacks()` returns `["javascript"]` when `package.json` exists without `tsconfig.json`
- [ ] AC3: `detect_stacks()` returns `[]` in an empty directory
- [ ] AC4: `detect_ai_providers()` returns `["claude_code"]` when `.claude/` directory exists
- [ ] AC5: `detect_ai_providers()` returns `["claude_code", "github_copilot"]` when both `.claude/` and `.github/copilot-instructions.md` exist
- [ ] AC6: `detect_ai_providers()` does NOT detect gemini/codex from `.agents/` directory
- [ ] AC7: `detect_vcs()` delegates to `detect_from_remote()` from `vcs/factory.py` and returns `"github"` when no remote exists
- [ ] AC8: `detect_ides()` returns `["vscode"]` when `.vscode/` exists, `["jetbrains"]` when `.idea/` exists, `[]` when neither

### Wizard UX
- [ ] AC9: Wizard shows checkboxes with detected items preselected (marked with `●`)
- [ ] AC10: Wizard shows all valid options including non-detected ones (unmarked with `○`)
- [ ] AC11: Empty repo → wizard shows all options with nothing preselected
- [ ] AC12: VCS selection uses radio buttons (single select), not checkboxes
- [ ] AC13: Wizard returns a `WizardResult` dataclass with all selections

### CLI Integration
- [ ] AC14: `ai-eng install` in a Python+Claude repo shows detection summary then wizard with preselections
- [ ] AC15: `ai-eng install` in an empty repo skips detection summary and goes straight to wizard
- [ ] AC16: `ai-eng install --stack python --provider claude_code --ide terminal --vcs github` skips wizard entirely
- [ ] AC16b: `ai-eng install --stack python` (no other flags) → wizard prompts ONLY for providers, IDEs, and VCS (stacks resolved from flag)
- [ ] AC17: `ai-eng install --non-interactive` skips wizard, uses detection results + defaults for undetected categories
- [ ] AC18: No "External CI/CD standards URL" prompt during install
- [ ] AC19: `--dry-run` mode works without wizard (uses flags or defaults)

### Backwards Compatibility
- [ ] AC20: CLI flags (`--stack`, `--provider`, `--ide`, `--vcs`) continue to work as before
- [ ] AC21: `--non-interactive` mode produces same results as before (uses defaults)
- [ ] AC22: Install pipeline (6 phases) is unchanged — only the input gathering changes

### Tests
- [ ] AC23: Unit tests for each stack marker detection (12 stacks × marker files)
- [ ] AC24: Unit tests for AI provider detection (claude_code, github_copilot, negative cases)
- [ ] AC25: Unit tests for wizard with mocked questionary (detected preselection, empty preselection)
- [ ] AC26: Existing pipeline-level tests (`test_pipeline.py`) pass without modification. CLI-level tests may need updates for the new wizard flow.

## Files Changed

| Action | Path | Notes |
|--------|------|-------|
| create | `src/ai_engineering/installer/autodetect.py` | Pure detection functions |
| create | `src/ai_engineering/installer/wizard.py` | questionary-based wizard |
| modify | `src/ai_engineering/cli_commands/core.py` | Replace prompts with detect→wizard flow |
| modify | `pyproject.toml` | Add `questionary` dependency |
| create | `tests/unit/installer/test_autodetect.py` | Detection unit tests |
| create | `tests/unit/installer/test_wizard.py` | Wizard unit tests |
| modify | `tests/unit/installer/test_pipeline.py` | Update if needed for new flow |

## Risks

| Risk | Mitigation |
|------|-----------|
| `questionary` doesn't render in all terminals (dumb terminals, CI) | `--non-interactive` flag bypasses wizard entirely. Detection + defaults used. |
| Stack detection false positives (e.g., pyproject.toml in a non-Python project) | Wizard lets user deselect. Detection is suggestion, not mandate. |
| Breaking change for scripts that pipe input to `ai-eng install` | CLI flags (`--stack`, `--provider`) remain the stable API for automation. |

## Dependencies

- `questionary` PyPI package (MIT license, actively maintained)
- Existing `detect_from_remote()` in `vcs/factory.py` (VCS detection)
- Existing `contexts/languages/*.md` files (define available stacks)
