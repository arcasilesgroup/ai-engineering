---
name: code
version: 2.1.0
description: 'Write code across all supported stacks following standards: implement
  features, write tests, validate. Includes CLI design (agent-first, JSON + Rich dual-output).'
tags: [implementation, code, multi-stack, features, cli]
---

# Build

## Purpose

Core implementation skill for writing code across all 20 supported stacks. Implements features, writes tests, and validates against stack standards. The primary "write code" skill invoked by the build agent. Also covers CLI design: agent-first commands with JSON envelope output (`--json`) and Rich human UX, dual-mode routing, and progress indicators (see `cli_output.py`, `cli_envelope.py`, `cli_ui.py`).

## Trigger

- Command: `/ai:build`
- Context: implementation tasks requiring code changes across any stack.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"build"}'` at skill start. Fail-open -- skip if ai-eng unavailable.

## Procedure

### 1. Read Context

Understand the full change scope before writing a single line.

- **Check `_active.md`** -- read `context/specs/_active.md` to identify the current spec. If no active spec exists and the work is non-trivial, invoke `create-spec` first.
- **Read the spec chain** -- open `spec.md` (the WHAT), `plan.md` (the HOW), and `tasks.md` (the DO) for the active spec. Identify which phase and task number this build addresses.
- **Read `decision-store.json`** -- check for prior decisions that constrain the implementation. Reusing a rejected approach wastes a full cycle.
- **Identify affected modules** -- from the plan's Architecture section, determine which files will be created or modified. Map each file to its owning module.
- **Load session checkpoint** -- run `ai-eng checkpoint load` to recover any prior session state. This prevents duplicate work and ensures continuity.
- **Confirm scope with the user** -- if the task is ambiguous or touches more than 5 files, summarize your understanding and ask for confirmation before proceeding.

WHY: Building without context produces code that solves the wrong problem. Reading the spec chain first ensures alignment with the stated goal.

### 2. Detect Stack

Identify the technology stack from project files, then load the matching standard.

| Project file | Stack | Standard to load |
|---|---|---|
| `pyproject.toml`, `setup.py` | Python | `stacks/python.md` |
| `*.csproj`, `*.sln` | .NET | `stacks/dotnet.md` |
| `next.config.*` | Next.js | `stacks/typescript.md` |
| `package.json` + `tsconfig.json` | TypeScript | `stacks/typescript.md` |
| `Cargo.toml` | Rust | `stacks/rust.md` |
| `*.tf` | Terraform | `stacks/infrastructure.md` |
| `Dockerfile`, `compose.yml` | Containers | `stacks/infrastructure.md` |
| `.github/workflows/*.yml` | GitHub Actions | `stacks/cicd.md` |
| `azure-pipelines.yml` | Azure Pipelines | `stacks/cicd.md` |
| `*.sql`, `migrations/` | Database | `stacks/database.md` |

- For polyglot projects, load ALL applicable standards. A repo with `pyproject.toml` and `*.tf` requires both Python and infrastructure standards.
- If no recognized project file exists, ask the user to confirm the stack before proceeding.
- Read `quality/core.md` in every case -- quality baselines apply to all stacks.

WHY: Each stack has its own idioms, tooling, and quality gates. Loading the wrong standard produces code that passes locally but fails in CI.

### 3. Design

Propose the approach before writing code. Building without a design creates rework.

- **State the approach in 2-3 sentences** -- what pattern you will use, where the new code lives, and how it integrates with existing modules.
- **Identify trade-offs** -- name at least one alternative you considered and why you rejected it. Example: "Could use inheritance here, but composition keeps the dependency graph flatter."
- **Check for breaking changes** -- if modifying a public API, CLI interface, or shared utility, flag the downstream impact.
- **Decide commit granularity** -- one logical change per commit. If the task requires both a new module and updates to existing callers, plan two commits.

When to ask the user:
- The task has multiple valid approaches with different trade-offs.
- The change touches a public interface or contract.
- The design requires a new dependency.

When to proceed without asking:
- The approach is unambiguous (fix a typo, add a test, implement a spec-defined function).
- The spec already prescribes the design in its Architecture section.

WHY: Design-first prevents the sunk-cost trap. Ten minutes of design saves an hour of rework.

### 4. Implement

Write code that is correct, readable, and maintainable.

**Principles:**
- **Single Responsibility** -- each function/class does one thing. If you need "and" to describe it, split it.
- **Open/Closed** -- extend behavior through composition or configuration, not by modifying working code.
- **DRY** -- extract shared logic into named functions. Duplicated lines on changed code must stay at or below 3%.
- **Explicit over implicit** -- prefer named constants over magic numbers, explicit parameters over hidden defaults, typed returns over Any.
- **Small functions** -- keep cyclomatic complexity at or below 10 and cognitive complexity at or below 15 per function.

**Structure:**
- Place new files according to the project's existing directory conventions. Do not invent new top-level directories without spec justification.
- Match the existing code style: naming conventions, import ordering, docstring format.
- Add type annotations (Python: full type hints; TypeScript: strict mode; .NET: nullable reference types enabled).
- Write docstrings or XML-doc comments for all public functions. Internal helpers get a one-line comment explaining WHY, not WHAT.

**Commit discipline:**
- One logical change per commit. "Add X" and "Fix Y" are separate commits.
- Commit message format: `spec-NNN: Phase X.Y -- <description>`.
- Never commit generated files, build artifacts, or secrets.

WHY: Clean code is not a luxury -- it is the only code that survives contact with the next developer (human or agent).

### 5. Test

Write tests that prove the new behavior works and protect against regression.

- **Coverage target**: 80% on new and changed code (aligned with `quality/core.md`). Governance-critical paths require 100%.
- **Test pyramid**: favor unit tests (~50%), then integration tests (~45%), then E2E (~5%).

When to write **unit tests**:
- Pure functions, data transformations, validators, parsers.
- Any function with branching logic (if/match/switch).
- Error handling paths -- verify exceptions are raised with correct messages.

When to write **integration tests**:
- Multi-module interactions (service calls repository, CLI invokes service).
- File I/O, database queries, HTTP calls (use fixtures/mocks for external services).
- Configuration loading and environment detection.

When to write **E2E tests**:
- User-facing workflows that span the full stack.
- Only when the spec explicitly requires it -- E2E tests are expensive to maintain.

**Test structure:**
- Name tests descriptively: `test_<function>_<scenario>_<expected>`.
- Use Arrange/Act/Assert (AAA) pattern.
- Each test asserts one behavior. Multiple assertions are acceptable only when verifying a single logical outcome.
- Never write tests that assert implementation details (e.g., "function was called 3 times"). Assert observable behavior.

WHY: Tests are the executable specification. They prove the code works today and catch regressions tomorrow.

### 6. Validate

Run the full validation pipeline after every file change. Fix failures before proceeding.

| Stack | Lint / Format | Build / Type Check | Security | Tests |
|---|---|---|---|---|
| Python | `ruff check` + `ruff format --check` | `ty check` | `gitleaks protect --staged` | `pytest` |
| .NET | `dotnet format --verify-no-changes` | `dotnet build --no-restore` | `gitleaks protect --staged` | `dotnet test` |
| TypeScript | `eslint .` + `prettier --check .` | `tsc --noEmit` | `gitleaks protect --staged` | `jest` or `vitest` |
| Rust | `cargo fmt -- --check` | `cargo check` + `cargo clippy` | `gitleaks protect --staged` | `cargo test` |
| Terraform | `terraform fmt -check` | `terraform validate` | `gitleaks protect --staged` + `tfsec` | `terraform plan` |
| YAML | `yamllint .` | schema validation | `gitleaks protect --staged` | N/A |

**Error handling:**
- If a linter reports fixable errors, apply the auto-fix (`ruff check --fix`, `dotnet format`) and re-run.
- If a type checker fails, read the full error, fix the source, and re-validate. Do not add type-ignore comments.
- If security scanning finds a secret, remove it immediately -- do not commit and fix later.
- Maximum 3 validation-fix cycles per file. After 3 failures on the same issue, escalate to the user with the full error output.

WHY: Validation after every change catches errors at the lowest cost. A lint failure caught in-editor costs seconds; the same failure caught in CI costs minutes plus context-switch overhead.

### 7. Document

Record what was built and why.

- **Commit message** -- follow the `spec-NNN: Phase X.Y -- <description>` format. The description explains the WHY, not the WHAT. "Add retry logic to handle transient network failures" not "Add retry logic".
- **Code comments** -- add comments only for non-obvious logic: workarounds, performance optimizations, business rules. Do not comment obvious code.
- **Spec task update** -- mark completed tasks `[x]` in `tasks.md`. Update the frontmatter counters (`completed`, `last_session`, `next_session`). Run `ai-eng spec verify` to auto-correct counters.
- **Decision recording** -- if any decision was made during implementation (pattern choice, dependency selection, scope adjustment), record it with `ai-eng decision record`. This dual-writes to `decision-store.json` and `audit-log.ndjson`.

WHY: Code without context is a puzzle. Documentation turns implementation decisions into institutional knowledge.

## Holistic Analysis

Before modifying any file, analyze its place in the dependency graph.

- **Upstream dependencies** -- what does this file import? Will those APIs change in this spec?
- **Downstream consumers** -- what imports this file? Changing a function signature here breaks callers there.
- **Shared utilities** -- if modifying a utility used across modules, grep for all call sites and verify compatibility.
- **Configuration coupling** -- check if the file reads from config files, environment variables, or CLI flags. Changes to expected config keys require coordinated updates.
- **Test dependencies** -- identify tests that exercise the file being modified. Run them before and after to confirm behavior preservation.

Use `git log --oneline -- <file>` to understand the file's change history. Recent changes indicate active development -- coordinate to avoid conflicts.

WHY: Files do not exist in isolation. A change to one file ripples through its dependents. Holistic analysis prevents the "fix one thing, break three others" pattern.

## Post-Edit Validation

The complete pipeline that runs after every file change, in order.

1. **Format** -- run the stack formatter. Fix formatting before anything else because formatting changes obscure real diffs.
2. **Lint** -- run the stack linter with auto-fix enabled. Review each auto-fix to ensure it did not change behavior.
3. **Type check** -- run the stack type checker. Type errors indicate logic errors, not noise.
4. **Unit tests** -- run tests scoped to the changed module. Use `pytest <module>` or the stack equivalent.
5. **Security scan** -- run `gitleaks protect --staged` on staged changes. Zero leaks required.
6. **Full test suite** -- before committing, run the full test suite to catch cross-module regressions.

If any step fails, fix the issue and restart from step 1. Do not skip ahead -- a format fix can resolve a lint error, a lint fix can resolve a type error.

Maximum 3 full pipeline iterations. After 3 failures, surface the problem to the user with complete error output and attempted fixes.

## When NOT to Use

- **Bug fixes** -- use `debug` for systematic diagnosis.
- **Restructuring** -- use `refactor` for structural changes.
- **Reducing complexity** -- use `code-simplifier`.

## Examples

### Example 1: Adding a new CLI command

User says: "Add a `status` command to the CLI that shows the active spec and health score."

1. **Read context** -- check `_active.md` for the spec, read `plan.md` to find the planned file structure. Load `decision-store.json` for any CLI design decisions.
2. **Detect stack** -- `pyproject.toml` present, load `stacks/python.md`. Also load `quality/core.md`.
3. **Design** -- propose: "Add `src/ai_eng/commands/status.py` with a `status()` function registered in the CLI group. Reads active spec from `_active.md` and health score from `state/health-history.json`. Returns JSON for agent consumption, Rich table for human consumption." Confirm with user because this adds a new public command.
4. **Implement** -- create the command module, add the Click/Typer command function, wire it into the CLI group entry point. Follow existing command patterns in the codebase.
5. **Test** -- write unit tests for the status data gathering (mock file reads), integration test for the CLI invocation (`invoke(['status'])` returns expected output).
6. **Validate** -- `ruff check` + `ruff format --check` + `ty check` + `pytest tests/commands/test_status.py` + `gitleaks protect --staged`.
7. **Document** -- commit with `spec-NNN: Phase X.Y -- add status command for active spec and health score`. Update `tasks.md`.

### Example 2: Fixing a bug in existing code

User says: "The `spec verify` command miscounts completed tasks when a task line contains a sub-list."

1. **Read context** -- check the active spec. Read the relevant task in `tasks.md`. Understand the expected behavior from `spec.md`.
2. **Detect stack** -- Python. Load `stacks/python.md`.
3. **Design** -- "The parser regex matches `- [x]` at any indent level. Fix: anchor the pattern to only match top-level task checkboxes (lines starting with `- [x]` at the expected indent, not sub-list items)." Straightforward fix -- proceed without asking.
4. **Implement** -- modify the regex in the task counter module. Keep the fix minimal: change the pattern, not the parser architecture.
5. **Test** -- add a regression test with a task file containing sub-lists. Verify the count matches expected. Run existing tests to confirm no regressions.
6. **Validate** -- full pipeline: format, lint, type check, scoped tests, security scan, full suite.
7. **Document** -- commit with `spec-NNN: Phase X.Y -- fix task counter to ignore sub-list checkboxes`. Record the fix rationale if the pattern was non-obvious.

## Output Contract

- Code changes that implement the requested feature or fix.
- Tests covering new and changed behavior (80%+ coverage on changed code).
- All validation gates passing (lint, format, type check, security, tests).
- Updated `tasks.md` with completed task checkboxes and frontmatter counters.
- Decisions recorded in `decision-store.json` if any were made.

## Governance Notes

- Never skip validation steps. Gate failure means "fix", not "ignore".
- Record all non-trivial decisions in `decision-store.json` using `ai-eng decision record`.
- Do not add suppression comments (`# noqa`, `# type: ignore`, `// nolint`, `# pragma: no cover`) to bypass quality gates. Fix the root cause or refactor the code.
- If the build touches governance-critical paths (hooks, gates, install, CLI core), escalate to `ai:verify` for security review.

### Iteration Limits

- Max 3 attempts to resolve the same validation failure. After 3 failures, escalate to the user with evidence of all attempts.
- Each attempt must try a different approach. Repeating the same action is not a valid retry.

## References

- `standards/framework/quality/core.md` -- coverage, complexity, duplication thresholds.
- `standards/framework/stacks/python.md` -- Python-specific patterns and tooling.
- `standards/framework/stacks/dotnet.md` -- .NET-specific patterns and tooling.
- `.agents/agents/ai-build.md` -- the agent that invokes this skill.
- `.agents/skills/debug/SKILL.md` -- systematic bug diagnosis (use instead for root-cause investigation).
- `.agents/skills/refactor/SKILL.md` -- structural changes (use instead for move/rename/split).
- `.agents/skills/simplify/SKILL.md` -- complexity reduction (use instead for guard clauses, early returns).
