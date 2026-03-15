# Cross-Cutting Standard: Testing

## Scope

Applies to all stacks. Stack standards may extend with framework-specific testing tools and patterns.

## Principles

1. **Test pyramid**: many unit tests, fewer integration tests, minimal E2E tests.
2. **Fast feedback**: unit tests run in seconds, integration tests in minutes, E2E tests in low minutes.
3. **Deterministic**: no flaky tests. Tests pass or fail consistently. Random ordering safe.
4. **Independent**: tests don't depend on execution order or shared mutable state.
5. **Meaningful coverage**: test behavior, not implementation. Coverage is a safety net, not a goal.

## Test Tiers

| Tier | I/O | Speed | Gate | Purpose |
|------|-----|-------|------|---------|
| Unit | None | <1s each | Pre-commit | Pure logic, data transformations |
| Integration | Local (filesystem, DB) | <10s each | Pre-push | Component interaction, I/O |
| E2E | Full stack | <60s each | PR gate | User flows, system behavior |
| Live | External APIs | Varies | Opt-in | Third-party integration verification |

## Patterns

- **AAA**: Arrange-Act-Assert. One logical assertion per test.
- **Test naming**: `test_<unit>_<scenario>_<expected>` or BDD `should_<behavior>_when_<condition>`.
- **Test data**: factories/fixtures over hardcoded data. No production data in tests.
- **Isolation**: each test sets up and tears down its own state. Use transactions or tmp directories.
- **Regression tests**: every bug fix includes a test that would have caught the bug.
- **Snapshot tests**: for UI components and serialization formats. Update snapshots intentionally.

## Quality Thresholds

Per `standards/framework/quality/core.md`:
- 80% overall line coverage.
- 100% coverage for governance-critical paths.
- Zero uncovered public API functions.

## Anti-patterns

- Testing implementation details (private methods, internal state).
- Tests that pass when the feature is broken (false positives).
- Shared mutable state between tests.
- Sleeping in tests instead of polling/waiting.
- Mock-heavy tests that don't test real behavior.

## Update Contract

This file is framework-managed and may be updated by framework releases.
