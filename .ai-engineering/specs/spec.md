---
id: spec-072
title: "Install UX: Recursive Detection, Popularity Ordering, Git Init"
status: draft
created: 2026-03-25
refs: []
---

# spec-072: Install UX: Recursive Detection, Popularity Ordering, Git Init

## Problem

`ai-eng install` has three UX deficiencies and one correctness bug:

### 1. Shallow detection (stacks + IDEs)

`detect_stacks()` only checks root-level files (`root / filename`). `detect_ides()` only checks `.vscode/` and `.idea/` at root. In monorepos or projects with nested structure, markers in subdirectories are invisible.

**Evidence**: Running `ai-eng install` in a directory with `backend/pyproject.toml` and `frontend/package.json` detects zero stacks.

### 2. Alphabetical ordering

All selection lists use `sorted()`, producing alphabetical order. The user sees `bash` first and `typescript` last. This is counterintuitive — popular stacks should appear first.

**Evidence**: Wizard output shows `bash` at top of stacks list instead of `typescript`/`python`/`javascript`.

### 3. GitHub hardcoded as VCS default

`detect_vcs()` returns `"github"` on any detection failure. `_DEFAULT_VCS = "github"` in wizard.py. The wizard pre-selects `github` even when no remote exists and no VCS was detected.

**Evidence**: In a directory with no git remote, the VCS prompt shows `github` pre-selected.

### 4. Silent hook skip on non-git directories

When `.git/` doesn't exist, `install_hooks()` raises `FileNotFoundError`, which `HooksPhase.execute()` silences via `contextlib.suppress()`. `verify()` emits a warning but always returns `passed=True`. The install reports success with no hooks installed.

**Evidence**: `HooksPhase.execute()` at `phases/hooks.py:86-89` wraps `install_hooks()` in `contextlib.suppress(FileNotFoundError)`. No `git init` exists anywhere in the codebase. Legacy `install()` at `service.py:164` has the same `contextlib.suppress` pattern.

## Solution

Four changes to the install flow, following Approach B (single walker + git init in detect phase).

### 4.1 Recursive detection with single-pass walker

Replace per-function detection with a single recursive walker in `autodetect.py` that traverses the directory tree once, collecting both stack markers and IDE markers in a single pass.

**Exclusion set** (directories skipped entirely):

```python
_WALK_EXCLUDE: frozenset[str] = frozenset({
    "node_modules", ".venv", "venv", "vendor", ".git",
    "__pycache__", "build", "dist", ".tox", ".nox",
    ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "target",       # Rust/Java build output
    ".gradle",      # Gradle cache
    "Pods",         # iOS CocoaPods
    ".dart_tool",   # Dart cache
    ".build",       # Swift build
})
```

**Walker design**:

```python
def _walk_markers(root: Path) -> tuple[set[str], set[str]]:
    """Single-pass recursive walk. Returns (stack_names, ide_names).

    Uses os.walk(followlinks=False) to avoid symlink loops.
    JS/TS detection is per-directory: if a directory has tsconfig.json,
    "typescript" is added. If it has package.json WITHOUT tsconfig.json,
    "javascript" is added. In a monorepo with both a JS backend and a TS
    frontend in different subdirectories, BOTH "javascript" and "typescript"
    are detected. This is intentional — the project uses both stacks.

    AI provider detection is NOT included in the walker. It remains
    root-level only via detect_ai_providers(), because .claude/ and
    .github/ are project-root markers by definition.
    """
    stacks: set[str] = set()
    ides: set[str] = set()

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded directories in-place
        dirnames[:] = [d for d in dirnames if d not in _WALK_EXCLUDE]

        # Check filenames against _FILE_MARKERS
        for fname in filenames:
            if fname in _FILE_MARKERS:
                stacks.update(_FILE_MARKERS[fname])
            # Glob-equivalent: check extensions
            if fname.endswith((".csproj", ".sln")):
                stacks.add("csharp")

        # IDE markers: directory names
        dir_name = Path(dirpath).name
        if dir_name == ".vscode":
            ides.add("vscode")
        elif dir_name == ".idea":
            ides.add("jetbrains")

        # JS/TS detection per directory
        fset = set(filenames)
        if "tsconfig.json" in fset:
            stacks.add("typescript")
        elif "package.json" in fset:
            stacks.add("javascript")

    return stacks, ides
```

**Integration with existing API**:

- `detect_stacks()` and `detect_ides()` become thin wrappers that call `_walk_markers()` and return their respective results, ordered by popularity.
- `detect_all()` calls `_walk_markers()` once and distributes results to avoid double traversal.
- `detect_ai_providers()` remains unchanged — root-level only. `.claude/` and `.github/` are project-root markers by definition and should NOT be detected recursively.
- `package.json` and `tsconfig.json` remain outside `_FILE_MARKERS` to preserve the per-directory ts-overrides-js logic.

### 4.2 Popularity-based ordering

Replace `sorted()` with explicit popularity tuples based on GitHub Octoverse 2025 rankings.

**Stacks** (Octoverse 2025 contributor count order):

```python
_STACK_POPULARITY: tuple[str, ...] = (
    "typescript",   # #1 Octoverse 2025
    "python",       # #2
    "javascript",   # #3
    "java",         # #4
    "csharp",       # #5
    "go",           # #6
    "php",          # #7
    "rust",         # #8
    "ruby",         # #9
    "kotlin",       # #10
    "swift",        # #11
    "dart",         # #12
    "elixir",       # #13
    "sql",          # not ranked — utility language
    "bash",         # not ranked — utility language
    "universal",    # meta — always last
)
```

**IDEs** (market share order):

```python
_IDE_POPULARITY: tuple[str, ...] = (
    "vscode",       # ~74% market share
    "jetbrains",    # ~27%
    "cursor",       # growing, VS Code fork
    "terminal",     # niche
)
```

**AI Providers** (user adoption order):

```python
_PROVIDER_POPULARITY: tuple[str, ...] = (
    "github_copilot",  # largest installed base
    "claude_code",     # second
    "gemini",          # third
    "codex",           # newest
)
```

**VCS** (market share order):

```python
_VCS_POPULARITY: tuple[str, ...] = (
    "github",        # dominant
    "azure_devops",  # enterprise
)
```

A shared `_order_by_popularity(items, ranking)` function sorts any list according to its ranking tuple, appending unknown items at the end alphabetically.

### 4.3 VCS without default pre-selection

Three changes:

1. **`detect_vcs()` in `autodetect.py`**: Return `""` (empty string) when detection fails instead of `"github"`. Since `detect_vcs()` delegates to `detect_from_remote()` in `vcs/factory.py` (which also returns `"github"` as fallback), the wrapper translates: call `detect_from_remote()`, but if the underlying `git remote get-url origin` command fails (non-zero exit or exception), return `""` instead of trusting the fallback. `detect_from_remote()` itself is NOT modified (it's used by other consumers that expect `"github"` fallback).

2. **`_detect_vcs()` in `phases/detect.py`**: Same change — return `""` instead of `"github"` when the subprocess fails or returns non-zero.

3. **Wizard `_ask_select()`**: Make `default` parameter optional (`default: str | None = None`). When `None`, call `questionary.select()` without the `default` kwarg. Before the VCS prompt, print a styled note: `"  Detected: none"` when `detected.vcs` is empty.

**Ctrl+C / abort handling**: `WizardResult.vcs` must NEVER be empty. If `questionary.select().ask()` returns `None` (Ctrl+C), abort the install entirely via `raise SystemExit(1)`. This is different from the current behavior that falls back to `"github"` — an unselected VCS is not a recoverable state. The `_ask_select` function changes from returning `_DEFAULT_VCS` on `None` to raising `SystemExit(1)`.

**Pipeline boundary**: The empty string `""` exists ONLY in `DetectionResult.vcs` (auto-detection output). After the wizard runs, `WizardResult.vcs` is always `"github"` or `"azure_devops"`. `InstallContext.vcs_provider` receives from `WizardResult`, never from raw detection.

**`DetectPhase.execute()` overwrite guard**: `DetectPhase.execute()` currently overwrites `context.vcs_provider` with whatever `_detect_vcs()` returns (line 106 of `detect.py`). Change this to only overwrite when the detected value is non-empty:

```python
if action.rationale.startswith("VCS detected:"):
    detected_vcs = action.rationale.split(": ", 1)[1]
    if detected_vcs:  # Only overwrite if detection succeeded
        context.vcs_provider = detected_vcs
```

### 4.4 Automatic `git init` in detect phase

Add `git init` to `DetectPhase` when `.git/` does not exist. This ensures hooks can always be installed.

**Phase ordering**: VCS detection runs first (returns `""` for non-git directories), then `git init` is planned. This ordering is correct — detection informs the plan, `git init` prepares the environment for later phases.

**In `DetectPhase.plan()`**:
- Check if `context.target / ".git"` exists
- If not, add a `PlannedAction(action_type="create", destination=".git", rationale="git init — repository not initialized")`

**In `DetectPhase.execute()`**:
- When the `git init` action is present, run `subprocess.run(["git", "init"], cwd=context.target, check=True)`
- If `git` binary is not found (`FileNotFoundError`), raise `InstallerError("git is required but not installed. Install git and retry.")` — the framework fundamentally requires git
- Log to result: `result.created.append(".git")`

**In `HooksPhase.execute()`** (pipeline path):
- **Remove** `contextlib.suppress(FileNotFoundError)` — hooks must never silently fail
- If `install_hooks()` raises, let it propagate as a pipeline error

**In legacy `install()` at `service.py:164`** (legacy path):
- **Remove** `contextlib.suppress(FileNotFoundError)` from this path too
- Add the same `git init` logic before calling `install_hooks()`
- Consistency: both code paths handle missing `.git/` the same way

**In `HooksPhase.verify()`**:
- Change `passed=True` to `passed=False` when pre-commit hook is missing — missing hooks is a failure, not a warning

## Scope

### In Scope

1. Rewrite `autodetect.py`: replace shallow detection with single-pass recursive walker + exclusion set
2. Add `_WALK_EXCLUDE` constant with documented exclusion directories
3. Add popularity ordering tuples (`_STACK_POPULARITY`, `_IDE_POPULARITY`, `_PROVIDER_POPULARITY`, `_VCS_POPULARITY`) to `autodetect.py`
4. Add `_order_by_popularity()` helper function
5. Update `wizard.py`: use popularity ordering for all checkbox/select prompts
6. Update `wizard.py`: make `_ask_select` default optional, abort install on Ctrl+C, show "Detected: none" note
7. Update `detect_vcs()` in `autodetect.py`: return `""` on failure (wrapper logic, `detect_from_remote()` untouched)
8. Update `_detect_vcs()` in `phases/detect.py`: return `""` on failure instead of `"github"`
9. Add `DetectPhase.execute()` overwrite guard: only overwrite `context.vcs_provider` when detected value is non-empty
10. Add `git init` logic to `DetectPhase.plan()` and `DetectPhase.execute()` with `git`-not-installed error handling
11. Remove `contextlib.suppress(FileNotFoundError)` from `HooksPhase.execute()` (pipeline path)
12. Remove `contextlib.suppress(FileNotFoundError)` from legacy `install()` at `service.py:164`
13. Add `git init` logic to legacy `install()` path for consistency
14. Change `HooksPhase.verify()` to return `passed=False` when hooks are missing
15. Update `ui.py` `render_detection()` to handle empty VCS display
16. Unit tests for recursive walker (monorepo fixtures, exclusion verification)
17. Unit tests for popularity ordering (including unknown items appended alphabetically)
18. Unit tests for git init in detect phase (including git-not-installed scenario)
19. Integration test: install on empty directory (no .git) succeeds with hooks installed
20. Update existing tests to match new behavior (popularity ordering, recursive detection, strict hooks)

### Out of Scope

- Modifying hook scripts themselves (only the installation flow)
- Adding new VCS providers (only changing default behavior)
- Changing `detect_from_remote()` in `vcs/factory.py` (other consumers expect `"github"` fallback)
- Changing `git remote add` behavior (user's responsibility)
- Modifying the `operations.py` stack/IDE management (only detection and wizard)
- Making `detect_ai_providers()` recursive (root-level only by design)
- Doctor phase updates (spec-071 will adapt to these changes)

## Acceptance Criteria

- [ ] AC1: `ai-eng install` in a monorepo with `backend/pyproject.toml` + `frontend/tsconfig.json` detects both `python` and `typescript`
- [ ] AC2: `ai-eng install` in a project with `apps/web/.vscode/` nested directory detects `vscode`
- [ ] AC3: Stack selection shows `typescript` first, `universal` last (Octoverse order)
- [ ] AC4: IDE selection shows `vscode` first, `terminal` last
- [ ] AC5: AI provider selection shows `github_copilot` first
- [ ] AC6: VCS selection shows no pre-selection when no git remote exists, with "Detected: none" note
- [ ] AC7: VCS selection pre-selects correctly when a GitHub or Azure DevOps remote IS detected
- [ ] AC8: `ai-eng install` in an empty directory (no `.git/`) runs `git init` automatically and installs hooks
- [ ] AC9: After install on empty directory, `.git/hooks/pre-commit` exists and is executable
- [ ] AC10: `HooksPhase.verify()` returns `passed=False` when hooks are missing
- [ ] AC11: Recursive walker skips `node_modules`, `.venv`, `vendor/`, and all exclusion directories
- [ ] AC12: Walker does NOT follow symlinks (prevents infinite loops)
- [ ] AC13: Monorepo with `backend/package.json` (no tsconfig) + `frontend/tsconfig.json` detects both `javascript` AND `typescript`
- [ ] AC14: Ctrl+C during VCS select aborts install (`SystemExit(1)`), does not produce empty VCS
- [ ] AC15: `_order_by_popularity()` appends unknown items alphabetically after ranked items
- [ ] AC16: `ai-eng install` fails with clear error when `git` binary is not installed
- [ ] AC17: `detect_ai_providers()` does NOT detect `.claude/` in subdirectories (root-only)
- [ ] AC18: All existing tests updated to match new behavior and passing (zero regressions)

## Files Modified

| File | Change |
|------|--------|
| `installer/autodetect.py` | Recursive walker, popularity tuples, `_order_by_popularity()`, `detect_vcs()` returns `""` |
| `installer/wizard.py` | Popularity ordering, optional `default` in `_ask_select`, abort on Ctrl+C, "Detected: none" note |
| `installer/ui.py` | Handle empty VCS in `render_detection()` |
| `installer/phases/detect.py` | `git init` logic, `_detect_vcs()` returns `""`, VCS overwrite guard |
| `installer/phases/hooks.py` | Remove `contextlib.suppress`, `verify()` returns `passed=False` |
| `installer/service.py` | Remove `contextlib.suppress` from legacy `install()`, add `git init` for legacy path |
| `tests/unit/test_autodetect.py` | Update for recursive detection, add walker/exclusion/popularity tests |
| `tests/unit/test_wizard.py` | Update for popularity ordering, empty VCS, Ctrl+C abort |
| `tests/unit/test_detect_phase.py` | New tests for git init and git-not-installed |
| `tests/unit/test_hooks_phase.py` | Update for strict hook verification |
| `tests/integration/test_cli_install_doctor.py` | Integration test: empty dir install |

## Assumptions

- ASSUMPTION: `os.walk()` with in-place `dirnames` pruning is sufficient for performance (no need for parallel traversal)
- ASSUMPTION: `os.walk(followlinks=False)` is the default — symlinks to directories are not followed, symlinks to files are still yielded (acceptable behavior)
- ASSUMPTION: GitHub Octoverse 2025 ranking is a stable-enough reference for ordering (updated annually)
- ASSUMPTION: Running `git init` in an empty directory is always safe and has no side effects beyond creating `.git/`
- ASSUMPTION: `detect_from_remote()` in `vcs/factory.py` is used by other consumers that expect `"github"` fallback — changing it is out of scope

## Risks

| Risk | Mitigation |
|------|-----------|
| Recursive walk slow on very large repos | `_WALK_EXCLUDE` prunes heavy directories (node_modules, target, etc.). `os.walk` with pruning is O(relevant files), not O(all files) |
| `git init` unexpected by user | The framework requires git — there's no valid scenario without it. Install output shows "Initialized git repository" as feedback |
| Popularity ordering becomes stale | Tuples are explicit constants, easy to update. Annual review when Octoverse publishes |
| Removing `contextlib.suppress` causes install failures on edge cases | Desired behavior — hooks MUST be installed. `git init` in detect phase ensures `.git/` always exists before hooks phase runs |
| Empty VCS propagates to downstream code | Prevented by design: `""` exists only in `DetectionResult.vcs`. Wizard always resolves to non-empty value or aborts. `DetectPhase` overwrite guard skips empty values |
| `git` binary not installed | `DetectPhase.execute()` catches `FileNotFoundError` and raises `InstallerError` with clear message |
| JS/TS detection in different subdirectories produces both stacks | Intentional: a monorepo with JS and TS subdirs genuinely uses both stacks |

## Dependencies

- None. This spec can be implemented independently.
- spec-071 (Doctor Redesign) should be aware of the `git init` addition in detect phase when implementing `doctor/phases/detect.py`.
