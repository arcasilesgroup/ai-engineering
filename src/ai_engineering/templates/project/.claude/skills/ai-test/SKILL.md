---
name: ai-test
description: "Use when working with tests: writing new tests, enforcing TDD (RED-GREEN-REFACTOR), analyzing coverage gaps, or defining test strategy. Trigger for 'add tests for', 'write a test', 'I need 80% coverage', 'test this', 'am I testing enough', 'plan my test approach'. For failing tests where the fix is not obvious, use /ai-debug instead. Supports Python, TypeScript, .NET, Rust, Go."
effort: high
argument-hint: "plan|run|gap|tdd [target]"
---


# Test

## Purpose

TDD enforcement and testing skill. Tests are executable specifications -- they define what the system does before the system does it. Maximum confidence per minute of developer time.

## When to Use

- `tdd`: driving new features test-first (RED-GREEN-REFACTOR)
- `run`: writing and executing tests for existing code
- `gap`: analyzing coverage gaps and missing edge cases
- `plan`: designing test strategy before writing tests

## Process

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

### Mode: tdd (RED-GREEN-REFACTOR)

For TDD mode, follow `handlers/tdd.md` for the full RED-GREEN-REFACTOR flow.

### Mode: run

1. Detect test framework from project files
2. Follow existing conventions (directory structure, naming, fixtures)
3. Write tests using AAA pattern with descriptive names
4. Run with stack-appropriate command
5. Report results: pass/fail count, coverage delta

### Mode: gap

1. Run coverage tool with branch coverage enabled
2. Identify untested critical paths (business logic > glue code)
3. Check for missing edge cases: null, empty, boundary, error paths
4. Produce gap report with prioritized recommendations

### Mode: plan

1. Map the testing surface (modules, public APIs, critical paths)
2. Assign test categories: unit, integration, e2e
3. Define coverage targets per module
4. Identify infrastructure needs (test containers, fixtures, fakes)

## Stack Commands

| Stack | Runner | Coverage | Async |
|-------|--------|----------|-------|
| Python | `uv run pytest` | `pytest-cov` (branch=true) | `asyncio_mode = "auto"` |
| TypeScript | `vitest` or `jest` | `c8` / `istanbul` | `async/await` |
| .NET | `dotnet test` + xUnit | `coverlet` | `async Task` |
| Rust | `cargo test` | `cargo tarpaulin` | `#[tokio::test]` |
| Go | `go test ./...` | `go test -cover` | goroutine tests |

## Testing Rules

**Fakes over mocks**. Mocks test implementation details. Fakes implement the same interface.

Mocks are acceptable ONLY for:
1. Verifying something was NOT called
2. Simulating transient errors for retry logic
3. Third-party libraries (but wrap in your own adapter first)

**AAA pattern** (non-negotiable):

```python
# Arrange -- set up inputs and dependencies
# Act -- call the function under test
# Assert -- verify the outcome
```

**Name pattern**: `test_<unit>_<scenario>_<expected_outcome>`
- Good: `test_parse_email_rejects_missing_at_symbol`
- Bad: `test_parse_email`, `test_1`, `test_it_works`

## Anti-Patterns (Reject These)

| Anti-Pattern | Why It Fails |
|-------------|-------------|
| Testing the mock | Proves the mock works, not the code |
| No-op test (assert True) | Tests nothing, inflates coverage |
| Testing implementation | Breaks on refactor, proves nothing about behavior |
| Huge test setup | Design is too coupled -- simplify the interface |
| sleep() for sync | Flaky -- use events, barriers, wait_for |
| Exact float comparison | Flaky -- use approx/closeTo |

## Iron Law

If tests are wrong, escalate to the user. NEVER weaken, skip, or modify tests to make implementation easier -- tests are the contract; bending them hides bugs. "Tests are wrong" means the requirement changed -- not that passing them is hard.

## Common Mistakes

- Writing tests after implementation (tests-after prove what IS, not what SHOULD be)
- Testing private methods (test the public API)
- 100% coverage with meaningless assertions
- Skipping edge cases (null, empty, boundary, concurrent access)
- Not running ALL tests after changes

## Handlers

| Handler | File | Activation |
|---------|------|-----------|
| E2E Testing | `handlers/e2e.md` | Activated when `*.spec.ts`, `playwright.config.ts`, or `e2e/` directory detected |
| TDD Mode | `handlers/tdd.md` | Activated when `mode=tdd` |

## Integration

- **Called by**: `/ai-dispatch` (build tasks), `ai-build agent` (TDD mode), user directly
- **Calls**: stack-specific test runners
- **Transitions to**: `ai-build` (GREEN phase), `/ai-verify` (coverage validation)
- **See also**: `/ai-debug` (diagnose failing tests), `/ai-verify` (coverage + acceptance gate)

$ARGUMENTS
