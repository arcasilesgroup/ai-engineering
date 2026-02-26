---
name: test-runner
description: "Write and run tests across languages and frameworks; use for unit, integration, E2E testing, coverage analysis, and test strategy."
version: 1.0.0
category: dev
tags: [testing, tdd, coverage, unit-test, integration-test, e2e, quality]
metadata:
  ai-engineering:
    scope: read-write
    token_estimate: 900
---

# Test Runner

## Purpose

Write and run tests across languages and frameworks. Provides operational guidance for unit, integration, E2E testing, TDD workflow, coverage analysis, and test patterns.

## Trigger

- Command: `/dev:test-runner` or agent invokes test-runner skill.
- Context: writing tests, running test suites, analyzing coverage, TDD workflow.

## When NOT to Use

- **Test design** (choosing what to test, tier selection, strategy) — use `dev:test-strategy` instead. Test-runner executes; test-strategy designs.
- **Coverage auditing** (threshold evaluation, gap analysis) — use `quality:audit-code` for metric thresholds or `quality:test-gap-analysis` for capability-to-test mapping.
- **Debugging failures** (root cause analysis) — use `dev:debug` instead. Test-runner runs tests; debug investigates failures.

## Procedure

1. **Identify framework** — select tooling per stack.

   | Language | Unit Tests | Integration | E2E |
   |----------|-----------|-------------|-----|
   | Python | pytest | pytest + httpx | Playwright |
   | TypeScript/JS | Vitest (preferred), Jest | Supertest | Playwright |
   | .NET | xUnit / NUnit | xUnit + WebApplicationFactory | Playwright |
   | Swift | XCTest | XCTest | XCUITest |

2. **Select test tier** — per `standards/framework/stacks/python.md` Test Tiers.

   | Tier | Marker | I/O | Gate | Characteristics |
   |------|--------|-----|------|-----------------|
   | Unit | `@pytest.mark.unit` | None | Pre-push | Fast (<1s), isolated, mocked, pure logic |
   | Integration | `@pytest.mark.integration` | Local | CI | Real I/O (fs, git, subprocess), moderate |
   | E2E | `@pytest.mark.e2e` | Full stack | CI (staged) | Full workflows, slower |
   | Live | `@pytest.mark.live` | External APIs | Opt-in | Requires env var |

3. **Follow TDD cycle** — Red → Green → Refactor.
   - **Red**: write one minimal failing test.
   - **Green**: write minimum code to pass.
   - **Refactor**: clean up while tests stay green.

4. **Structure tests** — AAA pattern (Arrange-Act-Assert).
   - Arrange: set up preconditions, fixtures, test data.
   - Act: execute the function/operation under test.
   - Assert: verify expected outcomes.

5. **Run tests** — use stack-appropriate commands.

   ```bash
   # Python — tiered execution
   uv run pytest tests/unit -x -n auto --dist worksteal --no-cov   # Unit (fast, parallel)
   uv run pytest tests/integration -x -n auto --dist worksteal     # Integration (parallel)
   uv run pytest tests/e2e -v                                       # E2E (sequential)
   uv run pytest tests/unit --cov=src/app --cov-fail-under=90 -n auto  # Unit with coverage

   # TypeScript/JS
   npx vitest run                                          # Single run
   npx vitest --coverage                                   # With coverage

   # .NET
   dotnet test --no-build                                  # Run tests
   ```

6. **Analyze coverage** — identify gaps, focus on behavior not lines.

## What to Test

**Always test:**
- Public API / exported functions.
- Edge cases: empty input, null, boundary values.
- Error handling: invalid input, network failures.
- Business logic: calculations, state transitions.

**Don't test:**
- Private implementation details.
- Framework internals.
- Trivial getters/setters.
- Third-party library behavior.

## Test Patterns

- **Mocking**: mock external dependencies only; test real behavior where possible.
- **Async testing**: use `pytest-asyncio` (Python), `async/await` in test bodies (JS/TS).
- **Naming**: `test_<unit>_<scenario>_<expected_outcome>`.
- **Fixtures**: shared in `conftest.py`, scoped appropriately.
- **One test file per module**, colocated in `tests/` mirror of `src/`.

## Reference Guide

Load detailed guidance on-demand:

| Topic | Reference | Load When |
|-------|-----------|-----------|
| Unit Testing | `references/unit-testing.md` | pytest, Vitest, Jest patterns |
| Integration | `references/integration-testing.md` | API testing, DB testing |
| E2E | `references/e2e-testing.md` | User flows, Playwright |
| Performance | `references/performance-testing.md` | k6, load testing |
| Security | `references/security-testing.md` | Auth, injection, headers |
| Reports | `references/test-reports.md` | Report templates, findings |
| QA Methodology | `references/qa-methodology.md` | Manual testing, shift-left |
| Automation | `references/automation-frameworks.md` | Framework patterns, scaling |
| TDD Iron Laws | `references/tdd-iron-laws.md` | TDD methodology, red-green-refactor |
| Testing Anti-Patterns | `references/testing-anti-patterns.md` | Mock issues, test quality |

## Test Pyramid Enforcement

- **Unit tests** (`tests/unit/`): Fast (<1s each), fully mocked, no subprocess/I/O. Use `pytestmark = pytest.mark.unit`.
- **Integration tests** (`tests/integration/`): Real I/O (filesystem, git, subprocess). Use `pytestmark = pytest.mark.integration`.
- **E2E tests** (`tests/e2e/`): Full install + CLI workflows. Use `pytestmark = pytest.mark.e2e`.
- Every test file MUST have a `pytestmark` module-level marker. Files without markers will run in all tiers.
- Pre-push gate runs only `unit` tier with parallel execution (target: < 60s).
- CI runs all tiers staged: unit → integration → E2E.

## Governance Notes

- Coverage target: per `standards/framework/quality/core.md` (90% overall, 100% governance-critical).
- Test tiers: per `standards/framework/stacks/python.md` Test Tiers table.
- Performance targets: per `standards/framework/quality/core.md` Test Performance Targets table.
- Gate integration: unit at pre-push, all tiers staged at CI/PR.
- Security tests validate OWASP top 10 per `standards/framework/security/owasp-top10-2025.md`.

### Iteration Limits

- Max 3 attempts to resolve the same test failure. After 3 failures, escalate to user with evidence of attempts.
- Each attempt must try a different approach — repeating the same action is not a valid retry.
