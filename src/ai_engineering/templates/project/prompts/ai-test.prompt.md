---
name: ai-test
version: 2.0.0
description: "Testing strategy, execution, and TDD — plan test suites, write and run tests, analyze coverage gaps, or drive implementation test-first with RED-GREEN-REFACTOR. Multi-stack: Python, TypeScript, .NET, React, Next.js, Node, NestJS, Rust, Go, Java."
argument-hint: "plan|run|gap|tdd"
mode: agent
tags: [testing, tdd, coverage, unit, integration, e2e, multi-stack]
requires:
  anyBins:
  - pytest
  - vitest
  - jest
  - dotnet
  - cargo
  - go
---


# Test

## Purpose

Unified testing skill for all 20 supported stacks. Tests are first-class production code — the executable specification of what the system does and the safety net that makes confident refactoring possible.

**Core principle**: Tests exist to give you confidence to change code. Maximum confidence per minute of developer time — not maximum coverage.

Write tests that:
- **Fail for the right reasons** — when behavior changes, not when implementation details shift
- **Explain the system** — reading test names tells you what the system does
- **Run fast** — unit tests in milliseconds, full suite under a minute
- **Are independent** — every test runs alone, in any order, same result

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"test"}'` at skill start. Fail-open.

## Modes

### Mode: `plan`
Design test strategy: identify what to test, assign test categories (unit/integration/e2e), define coverage targets, map critical paths.

### Mode: `run`
Write and execute tests following stack standards. Detect framework from project files. Follow existing conventions (directory structure, naming, fixtures). Run with stack-appropriate command.

### Mode: `gap`
Analyze coverage gaps: map untested critical paths, identify missing edge cases, check branch coverage vs line coverage. Produce gap report with prioritized recommendations.

### Mode: `tdd`
Drive implementation test-first using RED-GREEN-REFACTOR. See TDD Cycle below.

## TDD Cycle

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

This is the Iron Law. Violating the letter of the rules IS violating the spirit.

### RED — Write Failing Test

1. Write ONE minimal test showing what SHOULD happen
2. Clear name: `test_<unit>_<scenario>_<expected_outcome>`
3. Real assertions (no mock-testing-mocks)
4. Run test — confirm it FAILS for the expected reason (missing feature, not typo)

If test passes immediately → you're testing existing behavior. Fix the test.
If test errors (syntax/import) → fix the error, re-run until it fails correctly.

### GREEN — Minimal Code

1. Write the simplest code to make the test pass
2. No extras, no features-ahead, no "while I'm here" improvements (YAGNI)
3. Run test — confirm it PASSES
4. Run ALL tests — confirm nothing else broke

If test still fails → fix your code, not the test.

### REFACTOR — Clean Up (after GREEN only)

- Remove duplication, improve names, extract helpers
- Tests MUST stay green throughout
- Do NOT add behavior during refactor

### Implementation Contract

After RED phase, produce:

```markdown
## Test Files
- [exact paths to test files written]

## Verification
- Command: [exact test command]
- Result: FAIL (expected)
- Failure reason: [1-2 lines tied to missing behavior]

## Constraints
- DO NOT modify these test files during GREEN phase
- Implement in: [paths or modules]
- Completion gate: [exact command] passes
```

### When Stuck

| Problem | Solution |
|---------|----------|
| Don't know how to test | Write the API you wish existed. Write the assertion first. |
| Test too complicated | Design too complicated. Simplify the interface. |
| Must mock everything | Code too coupled. Use dependency injection. |
| Test setup is huge | Extract helpers. Still complex? Simplify the design. |

## AAA Pattern (Non-Negotiable)

Every test has exactly three sections, visually separated:

```
# Arrange — set up inputs and dependencies
# Act — call the function/method under test
# Assert — verify the outcome
```

Name pattern: `test_<unit>_<scenario>_<expected_outcome>`

Good: `test_parse_email_rejects_missing_at_symbol`
Bad: `test_parse_email`, `test_1`, `test_process`

## Fakes Over Mocks

Mocks (`MagicMock`, `jest.fn()`) test implementation details. Prefer fakes: in-memory implementations of the same interface your production code uses.

**Fake design**:
- Implement the same Protocol/interface as production code
- Add test helpers as separate methods (`assert_published()`, `get_saved()`)
- Make behavior configurable (`fake.set_decline("insufficient funds")`)
- Keep simple enough that fakes don't need their own tests

**When mocks ARE appropriate** (3 cases only):
1. Verifying something was NOT called
2. Simulating transient errors for retry logic (`side_effect=ConnectionError()`)
3. Third-party libraries you can't easily fake — but wrap them in your own adapter first

## Test Categories

### Unit Tests
Fast, no I/O, no network, no database. Test pure logic in isolation. Use fakes for dependencies.

### Integration Tests
Cross boundaries: your code with a real database, HTTP API, or filesystem. Use test containers for real infrastructure. Transactional isolation (rollback after each test).

### E2E Tests
Full system through public API. Use sparingly — only critical business flows. Real infrastructure, realistic data, mark as slow.

## Stack-Specific Testing

### Python
- **Runner**: `pytest` via `uv run pytest`
- **Coverage**: `pytest-cov` (branch=true, target 80%)
- **Fixtures**: factory functions (`make_user()`) over fixtures. `conftest.py` for infrastructure only.
- **Async**: `asyncio_mode = "auto"`, never `asyncio.sleep()` for sync — use `asyncio.Event`
- **CLI**: `typer.testing.CliRunner`
- **Parametrize**: `@pytest.mark.parametrize` with `ids=` for readable output

### TypeScript
- **Runner**: `vitest` (preferred) or `jest`
- **Coverage**: `c8` or `istanbul` (branch coverage enabled)
- **Fixtures**: factory functions, `beforeEach` for infrastructure cleanup
- **Async**: `async/await` in tests, `vi.useFakeTimers()` for time control
- **DOM**: `@testing-library` for component tests, `jsdom` environment

### .NET
- **Runner**: `dotnet test` with `xUnit`
- **Coverage**: `coverlet` (target 80%)
- **Fixtures**: `IClassFixture<T>` for shared state, `WebApplicationFactory<T>` for API tests
- **DI**: Override services in test setup, use in-memory DB for EF Core tests
- **Async**: `async Task` test methods, `CancellationToken` testing

### React
- **Runner**: `vitest` + `@testing-library/react`
- **Coverage**: Component render + hook behavior + user interaction
- **Fixtures**: `render()` helpers, mock providers for context
- **Patterns**: Test user behavior not implementation. Query by role/label, not test-id.
- **Hooks**: `renderHook()` from `@testing-library/react`

### Next.js
- **Runner**: `vitest` with `next/jest` config
- **Server Components**: Test as pure functions (no React rendering)
- **API Routes**: Test handler functions directly with mocked `NextRequest`
- **Middleware**: Test with `NextResponse` assertions
- **E2E**: Playwright for full browser tests

### Node / NestJS
- **Runner**: `vitest` or `jest`
- **API**: `supertest` for HTTP assertions
- **NestJS**: `Test.createTestingModule()` for DI container testing
- **Middleware**: Test as pure functions with mock req/res
- **Streams**: Test with `Readable.from()` and collect with `for await`

### Rust
- **Runner**: `cargo test`
- **Coverage**: `cargo tarpaulin` or `cargo llvm-cov`
- **Fixtures**: Builder pattern for test data, `#[test]` attribute
- **Async**: `#[tokio::test]` for async tests
- **Property**: `proptest` crate for property-based testing

### Go
- **Runner**: `go test ./...`
- **Coverage**: `go test -cover` (target 80%)
- **Fixtures**: Table-driven tests, `testing.T` helpers
- **Mocks**: Interface-based fakes, `gomock` for generated mocks
- **HTTP**: `httptest.NewServer()` for integration tests

### Java / Kotlin
- **Runner**: JUnit 5 (`@Test`, `@ParameterizedTest`)
- **Coverage**: JaCoCo (branch coverage, target 80%)
- **Mocks**: Mockito for stubs, prefer manual fakes for repositories
- **Spring**: `@SpringBootTest` + `@MockBean` for integration
- **Async**: `CompletableFuture` assertions, `Awaitility` for async waiting

## Coverage Strategy

Coverage is a guide, not a goal. 100% with bad assertions is worse than 70% with meaningful tests.

- **80-90%** for core domain logic — where bugs cost the most
- **50-70%** for adapters — integration tests cover critical paths
- **Don't chase** glue code, config, wiring, CLI boilerplate
- **Branch coverage > line coverage** — enable `branch = true`
- **Quality gate**: 80% minimum (SonarCloud)

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests-after pass immediately, proving nothing. |
| "Tests-after achieve same goals" | Tests-after: "what does this do?" Tests-first: "what SHOULD this do?" |
| "Already manually tested" | Ad-hoc is not systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is debt. |
| "Keep as reference, write tests first" | You'll adapt it. That's testing-after. Delete means delete. |
| "Need to explore first" | Fine. Throw away exploration code, start fresh with TDD. |
| "Test is hard = skip it" | Hard to test = hard to use. Listen to the test. Simplify design. |
| "TDD will slow me down" | TDD is faster than debugging in production. |
| "This is different because..." | It's not. Delete code. Start over with TDD. |

## Flaky Test Diagnostic

When a test is flaky, check these 6 categories in order:

1. **Time dependency** — `datetime.now()`, `Date.now()` without injection. Fix: inject a clock.
2. **Order dependency** — shared mutable state between tests. Fix: isolate via fixtures.
3. **Async race** — `sleep()` for synchronization. Fix: use events/barriers/wait_for.
4. **External service** — real HTTP calls, rate limits. Fix: fakes or mocks at boundary.
5. **Resource exhaustion** — unclosed connections, file handles. Fix: context managers, cleanup.
6. **Float precision** — exact float comparison. Fix: `pytest.approx`, `Decimal`, `toBeCloseTo`.

## Verification Checklist

Before marking test work complete:

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing (TDD mode)
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass, output pristine (no errors, warnings)
- [ ] Tests use real code (mocks only for the 3 legitimate cases)
- [ ] Edge cases and error paths covered
- [ ] Test names describe behavior (`test_X_when_Y_then_Z`)
- [ ] AAA pattern in every test

## Governance Notes

- Read stack-specific standards from `standards/framework/stacks/<stack>.md` for quality thresholds.
- Quality gate: coverage 80%, zero blocker/critical findings (source: `standards/framework/quality/core.md`).
- For TDD mode, follow the Implementation Contract pattern from `.github/agents/build.agent.md` TDD Protocol.
- Tests that validate the REAL project (canary tests) should read from `.ai-engineering/` directly, not from `tmp_path` fixtures.

## References

- `.github/agents/build.agent.md` — TDD Protocol (RED-GREEN-REFACTOR with Implementation Contract)
- `standards/framework/quality/core.md` — coverage targets, quality gates
- Stack-specific standards in `standards/framework/stacks/`
