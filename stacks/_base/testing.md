# Universal Testing Standards

These testing standards apply to every technology stack. Untested code is unfinished code. Every behavioral change must have corresponding tests, and those tests must be reliable, fast, and meaningful. AI assistants must generate tests alongside implementation code — never defer testing to "later."

---

## Test Pyramid

Follow the test pyramid. The majority of tests should be fast, isolated unit tests. Integration and end-to-end tests fill the gaps that unit tests cannot cover.

```
        /  E2E  \          ~5-10% of tests
       /----------\
      / Integration \       ~15-25% of tests
     /----------------\
    /    Unit Tests     \   ~65-80% of tests
   /____________________\
```

### Unit Tests

- Test a single function, method, or class in isolation.
- Execute in milliseconds. The entire unit test suite should complete in under 60 seconds for most projects.
- Mock or stub all external dependencies (databases, APIs, file systems, clocks).
- Should comprise the largest portion of the test suite.
- Every public function with non-trivial logic must have unit tests.

### Integration Tests

- Test the interaction between two or more components (e.g., service + database, API + middleware + handler).
- Use real (or containerized) dependencies where practical (e.g., a real PostgreSQL instance via Docker).
- Execute in seconds, not minutes. Optimize test setup with shared fixtures or transactions that roll back.
- Focus on boundary behavior: serialization, query correctness, message handling, and configuration.

### End-to-End (E2E) Tests

- Test critical user workflows from the outside (e.g., browser automation, API call sequences).
- Cover only the most important paths: signup, login, core business flow, payment, checkout.
- Accept that E2E tests are slower and more brittle. Keep the count low and the value high.
- Run E2E tests in CI but not on every commit — trigger on PR creation and before deploy.
- Never duplicate coverage that unit or integration tests already provide.

---

## Test Naming Conventions

Test names must describe three things: **what** is being tested, **under what conditions**, and **what the expected outcome** is.

### Format

```
<unitUnderTest>_<scenario>_<expectedBehavior>
```

Or, when using a describe/it framework:

```
describe('<UnitUnderTest>')
  describe('when <condition>')
    it('should <expected behavior>')
```

### Examples

```
// Good — clear what, when, expected
calculateDiscount_whenUserIsPremiumMember_returnstwentyPercent()
calculateDiscount_whenCartIsEmpty_returnsZero()
calculateDiscount_whenCouponIsExpired_throwsExpiredCouponError()

// Good — describe/it style
describe('calculateDiscount')
  describe('when user is a premium member')
    it('should return 20% discount')
  describe('when the cart is empty')
    it('should return zero')
  describe('when the coupon is expired')
    it('should throw an ExpiredCouponError')
```

```
// DON'T — vague, tells you nothing when it fails
test('discount works')
test('test1')
test('should work correctly')
testCalculateDiscount()
```

### Rules

- Test names must read as a specification. When a test fails, the name alone should tell you what broke.
- Do not use "test" or "spec" as a prefix in the test name — the framework already knows it is a test.
- Group related tests using `describe` blocks or equivalent grouping constructs.
- Use consistent naming across the project. Pick one convention and enforce it.

---

## AAA Pattern (Arrange, Act, Assert)

Every test must follow the Arrange-Act-Assert pattern. This makes tests predictable, readable, and easy to debug.

### Structure

```
// Arrange — set up the preconditions and inputs
const user = createUser({ type: 'premium', joinedAt: '2024-01-01' });
const cart = createCart({ items: [{ id: 'SKU-1', price: 100 }] });

// Act — execute the behavior being tested
const discount = calculateDiscount(user, cart);

// Assert — verify the outcome
expect(discount).toBe(20);
```

### Rules

- **One Act per test.** Each test should exercise exactly one behavior. If you have multiple Act sections, split into multiple tests.
- **Separate the three sections visually.** Use blank lines or comments to delineate Arrange, Act, and Assert.
- **Keep Arrange minimal.** If setup is complex, extract it into helper functions or fixtures. The test body should be focused on the behavior, not the setup.
- **Assert one logical concept per test.** Multiple assertions are fine if they all verify the same logical outcome (e.g., checking both the status code and body of a response). Do not test unrelated behaviors in the same test.
- **Avoid logic in tests.** No `if`, `for`, or `switch` in test bodies. Tests should be linear, deterministic sequences.

```
// DON'T — logic in tests, multiple behaviors
test('user operations', () => {
  const user = createUser();
  if (user.type === 'premium') {
    expect(calculateDiscount(user)).toBe(20);
  }
  expect(user.save()).toBeTruthy();
  expect(sendWelcomeEmail(user)).toHaveBeenCalled();
});

// DO — one behavior per test, no logic
test('calculateDiscount_whenPremiumUser_returns20', () => {
  const user = createUser({ type: 'premium' });

  const discount = calculateDiscount(user);

  expect(discount).toBe(20);
});
```

---

## Test Isolation

### Rules

- **No shared mutable state between tests.** Every test must set up its own state and tear it down after. If tests share state, they become order-dependent and flaky.
- **No test order dependencies.** Every test must pass when run alone, in any order, or in parallel.
- **Reset state between tests.** Use `beforeEach`/`setUp` hooks to reset databases, clear caches, restore mocks, and reset singletons.
- **No network calls in unit tests.** Mock all HTTP, database, and file system interactions. Unit tests must work without any external services running.
- **Use isolated database transactions for integration tests.** Wrap each test in a transaction and roll back after, or use a fresh database/schema per test suite.
- **Freeze time in tests that depend on dates or timestamps.** Use a clock mock or time-travel library. Never use `Date.now()` or `time.time()` directly in the code under test — inject a clock dependency.

```
// DON'T — tests share mutable state
let counter = 0;

test('increment', () => {
  counter++;
  expect(counter).toBe(1);
});

test('double', () => {
  counter *= 2;
  expect(counter).toBe(2); // Fails if 'increment' didn't run first
});

// DO — each test owns its state
test('increment_fromZero_returnsOne', () => {
  let counter = 0;
  counter++;
  expect(counter).toBe(1);
});

test('double_fromOne_returnsTwo', () => {
  let counter = 1;
  counter *= 2;
  expect(counter).toBe(2);
});
```

---

## Mocking Guidelines

### What to Mock

- **External services**: HTTP APIs, third-party SDKs, email providers, payment gateways.
- **Infrastructure**: Databases, file systems, message queues, caches (in unit tests).
- **Non-deterministic inputs**: Current time, random number generators, UUIDs.
- **Slow operations**: Network calls, disk I/O, expensive computations (only when they make tests unacceptably slow).

### What NOT to Mock

- **The unit under test.** Never mock the thing you are testing. This produces tests that verify your mocking framework, not your code.
- **Simple value objects.** Do not mock data classes, DTOs, or plain objects. Construct real instances.
- **Internal collaborators within the same module** (in most cases). If `ServiceA` calls a private helper function, test through the public interface rather than mocking the helper.
- **Language standard library.** Do not mock `Array.map`, `string.split`, or equivalent. Mock the boundaries, not the language.

### Mocking Best Practices

- Prefer fakes (lightweight implementations) over mocks (verification-based stubs) when the dependency has complex behavior.
- Verify interactions only when the interaction itself is the behavior you are testing (e.g., "when a user signs up, an email is sent" — verify the email service was called).
- Do not over-specify mock expectations. Assert on the inputs that matter and ignore the rest. Brittle mocks break on every refactor.
- Clean up mocks after each test. Leaked mocks corrupt subsequent tests.

```
// DON'T — mocking internal implementation details
jest.spyOn(userService, '_hashPassword');
userService.createUser(userData);
expect(userService._hashPassword).toHaveBeenCalled();

// DO — testing through the public interface
const user = await userService.createUser(userData);
const isPasswordValid = await verifyPassword('plaintext', user.passwordHash);
expect(isPasswordValid).toBe(true);
```

---

## Coverage Targets

### Minimum Thresholds

| Category | Target |
|---|---|
| Overall line coverage | 80% minimum |
| Overall branch coverage | 75% minimum |
| Critical business logic | 100% line and branch coverage |
| Utility/helper functions | 90% minimum |
| Generated code, type definitions | Exclude from coverage |

### What Counts as Critical

- Authentication and authorization logic.
- Payment processing and financial calculations.
- Data validation and sanitization.
- Encryption and security-related code.
- Core business rules and domain logic.

### Coverage Rules

- **Coverage is a floor, not a ceiling.** Meeting 80% does not mean you stop writing tests. It means you have not written enough tests if you are below 80%.
- **Coverage does not equal quality.** A test that executes a line without asserting anything adds coverage but no value. Every test must assert meaningful behavior.
- **Do not write tests solely to increase coverage numbers.** If a line of code is genuinely not worth testing (e.g., a trivial getter), exclude it explicitly and document why.
- **Track coverage trends.** Coverage should increase or stay stable over time. A PR that decreases coverage must justify the decrease.
- **Enforce coverage in CI.** Fail the build if coverage drops below the threshold.

---

## Test Data Management

### Principles

- **Never use production data in tests.** Not even anonymized production data unless a formal anonymization process has been applied and verified.
- **Use factories or builders to create test data.** These provide sensible defaults and allow tests to override only the fields relevant to the scenario.
- **Keep test data minimal.** Only include the fields and records necessary for the specific test. Do not create a "god fixture" with everything.
- **Make test data deterministic.** No random values in test data unless you are specifically testing randomized behavior (and then use a seeded random generator).

### Patterns

```
// DON'T — verbose, repetitive, includes irrelevant fields
test('discount for premium user', () => {
  const user = {
    id: '123',
    firstName: 'John',
    lastName: 'Doe',
    email: 'john@example.com',
    phone: '+1234567890',
    address: '123 Main St',
    city: 'Springfield',
    state: 'IL',
    zip: '62701',
    type: 'premium',
    createdAt: '2024-01-01',
    updatedAt: '2024-01-15',
  };
  expect(calculateDiscount(user)).toBe(20);
});

// DO — factory with defaults, override only what matters
test('discount for premium user', () => {
  const user = createUser({ type: 'premium' });

  const discount = calculateDiscount(user);

  expect(discount).toBe(20);
});
```

### Fixtures

- Store shared fixtures in a dedicated `fixtures/` or `__fixtures__/` directory.
- Name fixture files after the entity they represent: `users.json`, `products.json`.
- Keep fixtures small and focused. Prefer factories for complex or variable test data.
- Version fixtures alongside the tests that use them. If the schema changes, update the fixtures.

### Database Test Data

- Use migrations to set up the test database schema. Never manually create tables in test setup.
- Seed only the data required for the test suite. Use transactions to isolate test data.
- Clean up test data after each test or test suite. Prefer rollback over delete for performance.

---

## Flaky Test Policy

A flaky test is a test that sometimes passes and sometimes fails without any code change. Flaky tests destroy confidence in the test suite and train engineers to ignore failures.

### Rules

- **A flaky test must be fixed or deleted within 5 business days of identification.** There is no "skip and come back to it later."
- **Never add `skip`, `xit`, `@Disabled`, or equivalent annotations without a linked ticket and a deadline.** Indefinitely skipped tests are dead code.
- **If a test is skipped, it must include a comment** with the ticket number and the reason: `// SKIP: PROJ-789 — flaky due to race condition in event bus. Fix ETA: 2026-02-14`.
- **Quarantine flaky tests** by moving them to a separate test suite that runs but does not block CI. This keeps the main suite reliable while preserving visibility.
- **Track flaky test frequency.** If a test fails intermittently more than once per week, it is flaky and must be addressed.

### Common Causes and Fixes

| Cause | Fix |
|---|---|
| Shared mutable state | Isolate state per test (see Test Isolation) |
| Timing/race conditions | Use deterministic waits, event-driven assertions, or retries with backoff |
| Network dependencies in unit tests | Mock all external calls |
| Clock sensitivity | Freeze time with a clock mock |
| Order dependency | Ensure each test is independently runnable |
| Resource exhaustion | Clean up handles, connections, and files in teardown |

---

## Performance Testing

### When to Performance Test

- Before launching a new service or feature that will serve production traffic.
- When changing a critical path (database queries, API endpoints, data pipelines) that handles significant volume.
- When introducing a new dependency that sits in the hot path.
- Before and after major refactors to ensure no regressions.

### Types

| Type | Purpose | When |
|---|---|---|
| Load testing | Verify system handles expected traffic | Pre-launch, major changes |
| Stress testing | Find the breaking point | Pre-launch, capacity planning |
| Soak testing | Detect memory leaks and degradation over time | Pre-launch, after architecture changes |
| Benchmark testing | Compare performance of specific operations | During development, optimization |

### Rules

- Define performance budgets (response time, throughput, error rate) before testing. "Fast" is not a requirement — "p99 under 200ms at 1000 RPS" is.
- Run performance tests against a production-like environment. Never performance test against local development machines and draw production conclusions.
- Store performance test results for historical comparison. Track trends over time.
- Performance tests must be reproducible. Document the test configuration, data set, and environment.
- Do not block CI with performance tests on every commit. Run them on a schedule (nightly) or on demand before releases.

---

## Accessibility Testing

### Requirements

- All user-facing web applications must meet WCAG 2.1 Level AA compliance at minimum.
- Accessibility is not a post-launch activity. Test for accessibility during development, not after.
- Automated accessibility checks must be part of CI for any project with a UI.

### Automated Checks

- Integrate an accessibility linter or scanner into the build pipeline (axe-core, pa11y, Lighthouse CI).
- Test for: missing alt text, insufficient color contrast, missing form labels, keyboard navigation, ARIA attribute correctness, heading hierarchy, focus management.
- Set thresholds: zero critical violations, zero serious violations. Fail the build on regressions.

### Manual Checks

Automated tools catch approximately 30-50% of accessibility issues. Manual testing is required for:

- Keyboard-only navigation: every interactive element must be reachable and operable without a mouse.
- Screen reader testing: verify that content is announced in a logical order and interactive elements have clear labels.
- Focus management: after modal open/close, route changes, and dynamic content updates, focus must move to a logical location.
- Zoom and reflow: content must remain usable at 200% zoom without horizontal scrolling.

### Testing Checklist

| Check | Method |
|---|---|
| All images have meaningful alt text (or empty alt for decorative) | Automated + manual review |
| Color contrast meets 4.5:1 for normal text, 3:1 for large text | Automated |
| All form inputs have associated labels | Automated |
| All interactive elements are keyboard accessible | Manual |
| Focus order follows visual/logical order | Manual |
| ARIA roles and properties are used correctly | Automated + manual |
| Page has a single `h1` and logical heading hierarchy | Automated |
| Error messages are associated with their form fields | Automated + manual |
| Dynamic content changes are announced to screen readers | Manual |
| No content relies solely on color to convey meaning | Manual |

---

## Summary Checklist

| Area | Check |
|---|---|
| Pyramid | Is the test distribution roughly 70/20/10 (unit/integration/e2e)? |
| Naming | Do test names describe what, when, and expected outcome? |
| Structure | Does every test follow Arrange-Act-Assert? |
| Isolation | Can every test run independently in any order? |
| Mocking | Are only external boundaries mocked, not internal implementation? |
| Coverage | Is overall coverage above 80% and critical paths at 100%? |
| Test data | Are factories used, and is production data excluded? |
| Flaky tests | Are all flaky tests tracked with tickets and deadlines? |
| Performance | Are performance budgets defined and tested for critical paths? |
| Accessibility | Are automated a11y checks in CI and manual checks scheduled? |
