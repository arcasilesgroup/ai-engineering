---
name: ai-test
description: "Writes tests, enforces TDD (RED-GREEN-REFACTOR), analyzes coverage gaps, defines test strategy across Python, TypeScript, .NET, Rust, Go. Trigger for 'add tests for', 'write a test', 'I need 80 percent coverage', 'plan my test approach', 'TDD this'. Not for failing tests where the fix is unclear; use /ai-debug instead. Not for AI reliability over time; use /ai-reliability-eval instead."
effort: mid
argument-hint: "plan|run|gap|tdd [target]"
---

# Test

Writes tests and enforces TDD (RED-GREEN-REFACTOR), analyzes coverage gaps, and defines test strategy across Python, TypeScript, .NET, Rust, and Go. Use it to add or plan tests; for failing tests where the fix is unclear use /ai-debug, and for AI reliability over time use /ai-reliability-eval.

## Purpose

TDD enforcement and testing. Tests are executable specifications — they define what the system does before the system does it. Maximum confidence per minute of developer time.

## Workflow

Principles applied: §10.5 TDD (tests are executable specifications; RED-GREEN-REFACTOR drives new code).

Step 0 — load contexts: read `.ai-engineering/manifest.yml` `providers.stacks`; load `.ai-engineering/overrides/<stack>/conventions.md` per stack + `.ai-engineering/overrides/_shared/conventions.md`; load `.ai-engineering/team/*.md`.

| Mode | Steps |
| --- | --- |
| `tdd` | Follow `handlers/tdd.md` for the full RED-GREEN-REFACTOR flow. |
| `run` | 1. detect framework from project files. 2. follow existing conventions (dirs, naming, fixtures). 3. write tests AAA-style with descriptive names. 4. run with the stack command. 5. report pass/fail count + coverage delta. |
| `gap` | 1. run coverage with branch coverage on. 2. identify untested critical paths (business logic > glue). 3. check missing edge cases: null, empty, boundary, error. 4. produce a prioritized gap report. |
| `plan` | 1. map the testing surface (modules, public APIs, critical paths). 2. assign categories: unit, integration, e2e. 3. set coverage targets per module. 4. identify infra needs (containers, fixtures, fakes). |

## Stack Commands

| Stack | Runner | Coverage | Async |
|-------|--------|----------|-------|
| Python | `uv run pytest` | `pytest-cov` (branch=true) | `asyncio_mode = "auto"` |
| TypeScript | `vitest` or `jest` | `c8` / `istanbul` | `async/await` |
| .NET | `dotnet test` + xUnit | `coverlet` | `async Task` |
| Rust | `cargo test` | `cargo tarpaulin` | `#[tokio::test]` |
| Go | `go test ./...` | `go test -cover` | goroutine tests |

## Testing Rules

- **Fakes over mocks** — mocks test implementation details; fakes implement the same interface. Mocks are acceptable ONLY for: (1) verifying something was NOT called, (2) simulating transient errors for retry logic, (3) third-party libraries (wrap in your own adapter first).
- **AAA pattern** (non-negotiable) — Arrange (inputs + deps), Act (call the unit), Assert (verify the outcome).
- **Name pattern** — `test_<unit>_<scenario>_<expected_outcome>`. Good: `test_parse_email_rejects_missing_at_symbol`. Bad: `test_parse_email`, `test_1`, `test_it_works`.

## Anti-Patterns (Reject These)

| Anti-Pattern | Why It Fails |
|-------------|-------------|
| Testing the mock | Proves the mock works, not the code |
| No-op test (assert True) | Tests nothing, inflates coverage |
| Testing implementation | Breaks on refactor, proves nothing about behavior |
| Huge test setup | Design is too coupled — simplify the interface |
| sleep() for sync | Flaky — use events, barriers, wait_for |
| Exact float comparison | Flaky — use approx/closeTo |

## Iron Law

If tests are wrong, escalate to the user. NEVER weaken, skip, or modify tests to make implementation easier — tests are the contract; bending them hides bugs. "Tests are wrong" means the requirement changed, not that passing them is hard.

## Common Mistakes

- Writing tests after implementation (tests-after prove what IS, not what SHOULD be).
- Testing private methods (test the public API).
- Not running ALL tests after changes.

## Handlers

| Handler | File | Activation |
|---------|------|-----------|
| E2E Testing | `handlers/e2e.md` | `*.spec.ts`, `playwright.config.ts`, or `e2e/` detected |
| TDD Mode | `handlers/tdd.md` | `mode=tdd` |

## Examples

### Example — TDD a new feature

User: "I'm building a JWT validator. Walk me through TDD."

```
/ai-test tdd jwt-validator
```

RED: writes failing tests for valid token, expired token, malformed signature; confirms FAIL for the expected reason. GREEN: hands off to `ai-build` for minimal implementation. REFACTOR: stays green.

## Integration

Called by: `/ai-build` (build + TDD tasks), user directly. Calls: stack-specific test runners. See also: `/ai-debug`, `/ai-verify`, `/ai-reliability-eval`.

$ARGUMENTS
