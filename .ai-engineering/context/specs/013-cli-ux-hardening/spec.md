---
id: "013"
slug: "cli-ux-hardening"
status: "in-progress"
created: "2026-02-11"
---

# Spec 013 — CLI UX Hardening: Verify-App Findings Remediation

## Problem

The verify-app agent ran a full E2E verification and identified 5 non-blocking findings that degrade the CLI user experience:

- **F1**: Raw Python tracebacks on invalid paths (e.g. `ai-eng install /nonexistent` shows `FileNotFoundError` stack trace instead of a clean error message).
- **F2**: Arbitrary stack names accepted without validation (e.g. `ai-eng stack add bogus` silently succeeds instead of rejecting unknown stacks).
- **F3**: `ai-eng` not on PATH after install — user must activate the venv manually (informational, accepted behavior).
- **F4**: `ai-eng install` does not auto-install git hooks — requires separate `ai-eng doctor --fix-hooks` step.
- **F5**: `uv pip install -e .` emits a noisy `typer[all]` extras warning due to unnecessary `[all]` extra in dependency spec.

Four findings require code fixes (F1, F2, F4, F5). One is document-only (F3, accepted as expected behavior).

## Solution

- **F1**: Add a centralized error handler in `cli_factory.py` that catches `FileNotFoundError` and `NotADirectoryError`, emitting a clean user-facing error message instead of a raw traceback.
- **F2**: Add `get_available_stacks()` helper in `installer/operations.py` and validation in `stack_ide.py` that rejects unknown stack/IDE names with the list of valid options.
- **F4**: Add `install_hooks()` call at the end of the `install()` function in `installer/service.py` so hooks are installed automatically during `ai-eng install`.
- **F5**: Remove the `[all]` extra from the `typer` dependency in `pyproject.toml` to eliminate the warning.
- **F3**: Accepted as expected behavior — no code change required.

## Scope

### In Scope

- F1: Centralized error handler in `cli_factory.py` for path-related errors.
- F2: Stack/IDE name validation with `get_available_stacks()` helper.
- F4: Auto-install hooks during `ai-eng install`.
- F5: Remove `[all]` extra from `typer` dependency.
- Tests for all code changes.

### Out of Scope

- F3: PATH behavior after install (accepted, no code change).
- New CLI commands or subcommands.
- Changes to the governance content system.
- Changes to the framework contract or standards.

## Acceptance Criteria

1. `ai-eng install /nonexistent` produces a clean error message with no traceback.
2. `ai-eng stack add bogus` is rejected with a list of valid stack names.
3. `ai-eng install <test-dir>` auto-installs git hooks (verifiable via `ls .git/hooks/pre-commit`).
4. `uv pip install -e .` completes with no `typer[all]` warning.
5. All existing tests pass.
6. Content integrity 6/6 passes.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D013-001 | F3 accepted as expected behavior | PATH setup is OS/shell-specific; venv activation is the standard Python workflow |
| D013-002 | Centralized handler in cli_factory.py, not per-command | Single point of maintenance; consistent UX across all commands |
| D013-003 | No new files — reuse existing modules | Minimizes file count; follows existing patterns |
