---
name: ai-test
description: Use when writing tests, enforcing TDD (RED-GREEN-REFACTOR), analyzing coverage gaps, or planning test strategy. Supports Python, TypeScript, .NET, Rust, Go.
effort: high
argument-hint: "plan|run|gap|tdd [target]"
mode: agent
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

### Mode: tdd (RED-GREEN-REFACTOR)

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

**Phase RED -- Write Failing Test**

1. Write ONE test showing what SHOULD happen
2. Name: `test_<unit>_<scenario>_<expected_outcome>`
3. AAA pattern: Arrange, Act, Assert (visually separated)
4. Run test -- confirm FAIL for the expected reason (missing feature, not syntax error)
5. Produce Implementation Contract:

```markdown
## Implementation Contract
- Test files: [exact paths]
- Verification: [exact command]
- Failure reason: [why it fails -- tied to missing behavior]
- Constraint: DO NOT modify these test files during GREEN
```

6. STOP. Do not implement.

**Phase GREEN -- Minimal Code**

1. Read the Implementation Contract
2. DO NOT modify test files (they are immutable)
3. Write the simplest code to make the test pass (YAGNI)
4. Run test -- confirm PASS
5. Run ALL tests -- confirm no regressions

If the test still fails: fix your code, not the test.

**Phase REFACTOR -- Clean Up (after GREEN only)**

- Remove duplication, improve names, extract helpers
- Tests MUST stay green throughout
- Do NOT add behavior during refactor

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

If tests are wrong, escalate to the user. NEVER weaken, skip, or modify tests to make implementation easier. "Tests are wrong" means the requirement changed -- not that passing them is hard.

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

$ARGUMENTS

---

# Handler: E2E Testing -- Playwright

## Purpose

End-to-end testing patterns using Playwright. Covers Page Object Model architecture, configuration, flaky test quarantine, CI/CD integration, artifact management, and domain-specific patterns for financial and Web3 applications.

## Activation

Dispatched when the test skill detects E2E scope: Playwright config present, `*.spec.ts` files in diff, or user requests browser-level tests.

## Procedure

### Step 1 -- Page Object Model (POM)

Every page under test gets a POM class. Structure:

```typescript
import { Page, Locator } from '@playwright/test'

export class ItemsPage {
  readonly page: Page
  readonly searchInput: Locator
  readonly itemCards: Locator
  readonly createButton: Locator

  constructor(page: Page) {
    this.page = page
    this.searchInput = page.locator('[data-testid="search-input"]')
    this.itemCards = page.locator('[data-testid="item-card"]')
    this.createButton = page.locator('[data-testid="create-btn"]')
  }

  async goto() {
    await this.page.goto('/items')
    await this.page.waitForLoadState('networkidle')
  }

  async search(query: string) {
    await this.searchInput.fill(query)
    await this.page.waitForResponse(resp => resp.url().includes('/api/search'))
    await this.page.waitForLoadState('networkidle')
  }

  async getItemCount() {
    return await this.itemCards.count()
  }
}
```

Rules:
- All Locator fields are `readonly`
- Use `data-testid` selectors exclusively (never CSS classes)
- Encapsulate all page interactions as methods
- Constructor wires all locators; methods compose actions

### Step 2 -- Playwright Configuration

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'playwright-results.xml' }],
    ['json', { outputFile: 'playwright-results.json' }]
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10000,
    navigationTimeout: 30000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
})
```

Key settings:
- `fullyParallel: true` -- tests run in parallel across workers
- `forbidOnly` blocks `.only` from reaching CI
- `retries: 2` in CI, `0` locally -- surfaces flaky tests early
- 4 projects: chromium, firefox, webkit, mobile-chrome
- `webServer` auto-starts the dev server; reuses existing locally

### Step 3 -- Flaky Test Quarantine

**Identification**:
```bash
npx playwright test tests/suspect.spec.ts --repeat-each=10
npx playwright test tests/suspect.spec.ts --retries=3
```

A test that fails in any of 10 repetitions is flaky. Quarantine immediately.

**Quarantine markers**:
```typescript
// Hard quarantine -- test is disabled
test('complex flow', async ({ page }) => {
  test.fixme(true, 'Flaky -- Issue #123')
})

// Conditional skip -- flaky only in CI
test('animation-dependent', async ({ page }) => {
  test.skip(process.env.CI === 'true', 'Flaky in CI -- Issue #456')
})
```

Every quarantined test MUST reference a tracking issue. Quarantine without a ticket is tech debt.

### Step 4 -- Root Cause Fixes for Flakiness

**Race conditions -- use auto-wait locators**:
```typescript
// BAD: assumes element is ready
await page.click('[data-testid="button"]')

// GOOD: auto-wait locator
await page.locator('[data-testid="button"]').click()
```

**Network timing -- wait for responses, not timeouts**:
```typescript
// BAD: arbitrary timeout
await page.waitForTimeout(5000)

// GOOD: wait for specific API response
await page.waitForResponse(resp => resp.url().includes('/api/data'))
```

**Animation timing -- wait for visible then networkidle**:
```typescript
// BAD: click during animation
await page.click('[data-testid="menu-item"]')

// GOOD: wait for stability
await page.locator('[data-testid="menu-item"]').waitFor({ state: 'visible' })
await page.waitForLoadState('networkidle')
await page.locator('[data-testid="menu-item"]').click()
```

### Step 5 -- Artifact Management

**Screenshots** (on-failure automatic, on-demand for debugging):
```typescript
await page.screenshot({ path: 'artifacts/after-login.png' })
await page.screenshot({ path: 'artifacts/full-page.png', fullPage: true })
await page.locator('[data-testid="chart"]').screenshot({ path: 'artifacts/chart.png' })
```

**Traces** (automatic on first retry via config, manual for deep debugging):
```typescript
await browser.startTracing(page, {
  path: 'artifacts/trace.json',
  screenshots: true,
  snapshots: true,
})
// ... test actions ...
await browser.stopTracing()
```

**Video**: configured via `video: 'retain-on-failure'` -- only kept for failed tests to save disk.

### Step 6 -- CI/CD Integration (GitHub Actions)

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test
        env:
          BASE_URL: ${{ vars.STAGING_URL }}
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: |
            playwright-report/
            artifacts/
          retention-days: 30
```

`if: always()` ensures artifacts upload even on failure -- critical for debugging.

### Step 7 -- Domain-Specific Patterns

**Web3 / Wallet testing**:
```typescript
test('wallet connection', async ({ page, context }) => {
  await context.addInitScript(() => {
    window.ethereum = {
      isMetaMask: true,
      request: async ({ method }) => {
        if (method === 'eth_requestAccounts')
          return ['0x1234567890123456789012345678901234567890']
        if (method === 'eth_chainId') return '0x1'
      }
    }
  })
  await page.goto('/')
  await page.locator('[data-testid="connect-wallet"]').click()
  await expect(page.locator('[data-testid="wallet-address"]')).toContainText('0x1234')
})
```

**Financial / critical flow testing**:
```typescript
test('trade execution', async ({ page }) => {
  test.skip(process.env.NODE_ENV === 'production', 'Skip on production')

  await page.goto('/markets/test-market')
  await page.locator('[data-testid="trade-amount"]').fill('1.0')
  await page.locator('[data-testid="confirm-trade"]').click()
  await page.waitForResponse(
    resp => resp.url().includes('/api/trade') && resp.status() === 200,
    { timeout: 30000 }
  )
  await expect(page.locator('[data-testid="trade-success"]')).toBeVisible()
})
```

Financial tests MUST skip on production environments. Use extended timeouts for blockchain responses.

## Output Format

```
tests/
  e2e/
    auth/
      login.spec.ts
      register.spec.ts
    features/
      search.spec.ts
      create.spec.ts
    api/
      endpoints.spec.ts
  fixtures/
    auth.ts
    data.ts
  pages/
    LoginPage.ts
    ItemsPage.ts
playwright.config.ts
```

## Quality Gate

- All `data-testid` selectors verified against component source
- Zero `waitForTimeout` calls -- use `waitForResponse` or `waitFor` instead
- Every quarantined test references a tracking issue
- POM classes have no direct assertions (assertions stay in spec files)
- CI config uploads artifacts on failure
- Financial/production-sensitive tests have environment guards

---

# Handler: TDD Workflow

## Purpose

Structured test-driven development ceremony. Extends the parent ai-test skill's RED-GREEN-REFACTOR protocol with user journey mapping, mock/fake strategy aligned with AE doctrine, coverage configuration, and continuous testing workflow.

## Activation

Dispatched when the test skill is invoked in `tdd` mode, or when building new features, fixing bugs, or refactoring code where TDD is the appropriate discipline.

## Procedure

### Step 1 -- Write User Journeys

Map every feature to user stories before writing any code or tests.

```
As a [role], I want to [action], so that [benefit]
```

Example:
```
As a user, I want to search for markets semantically,
so that I can find relevant markets even without exact keywords.
```

Each journey becomes one or more test cases. No journey, no test, no code.

### Step 2 -- Generate Test Cases

For each user journey, derive test cases covering happy path, edge cases, error paths, and boundary conditions.

```typescript
describe('Semantic Search', () => {
  it('returns relevant results for valid query', async () => {
    // Happy path
  })

  it('handles empty query gracefully', async () => {
    // Edge case
  })

  it('falls back to substring search when service unavailable', async () => {
    // Fallback behavior
  })

  it('sorts results by similarity score', async () => {
    // Ordering
  })

  it('rejects query exceeding max length', async () => {
    // Boundary
  })
})
```

Naming convention: `test_<unit>_<scenario>_<expected_outcome>` (Python) or descriptive `it('should...')` (TypeScript). AAA pattern is mandatory.

### Step 3 -- RED Phase (Write Failing Tests)

1. Write ONE test showing what SHOULD happen
2. Use the AAA pattern: Arrange, Act, Assert (visually separated with comments)
3. Run the test -- confirm it FAILS for the expected reason (missing feature, not syntax error)
4. Produce the Implementation Contract:

```markdown
## Implementation Contract
- Test files: [exact paths]
- Verification: [exact command]
- Failure reason: [why it fails -- tied to missing behavior]
- Constraint: DO NOT modify these test files during GREEN
```

5. STOP. Do not implement.

### Step 4 -- Implement (Minimal Code)

1. Read the Implementation Contract
2. DO NOT modify test files (they are immutable in this phase)
3. Write the simplest code that makes the test pass (YAGNI)
4. If the test still fails: fix your code, not the test

### Step 5 -- GREEN Phase (Confirm Pass)

1. Run the specific test -- confirm PASS
2. Run ALL tests -- confirm no regressions
3. If any test fails, return to Step 4

### Step 6 -- Refactor

With all tests green:
- Remove duplication
- Improve names and readability
- Extract helpers and shared fixtures
- DO NOT add new behavior during refactor
- Tests MUST stay green throughout

### Step 7 -- Verify Coverage

Run the coverage tool and confirm the threshold is met.

```bash
# Python
uv run pytest --cov --cov-branch --cov-fail-under=80

# TypeScript (Jest)
npx jest --coverage

# TypeScript (Vitest)
npx vitest run --coverage
```

Coverage threshold configuration (Jest example):
```json
{
  "jest": {
    "coverageThreshold": {
      "global": {
        "branches": 80,
        "functions": 80,
        "lines": 80,
        "statements": 80
      }
    }
  }
}
```

## Mock and Fake Strategy

**AE doctrine: fakes over mocks.** Fakes implement the same interface as the real dependency, giving you behavior-level confidence. Mocks verify call patterns, which couples tests to implementation.

**Fakes for internal interfaces** (preferred):
```python
# Real interface
class UserRepository(Protocol):
    def get(self, user_id: str) -> User | None: ...

# Fake for tests
class FakeUserRepository:
    def __init__(self, users: dict[str, User] | None = None):
        self._users = users or {}

    def get(self, user_id: str) -> User | None:
        return self._users.get(user_id)
```

**Mocks acceptable ONLY for third-party services** (wrap in your own adapter first):

Supabase:
```typescript
jest.mock('@/lib/supabase', () => ({
  supabase: {
    from: jest.fn(() => ({
      select: jest.fn(() => ({
        eq: jest.fn(() => Promise.resolve({
          data: [{ id: 1, name: 'Test Item' }],
          error: null
        }))
      }))
    }))
  }
}))
```

Redis:
```typescript
jest.mock('@/lib/redis', () => ({
  searchByVector: jest.fn(() => Promise.resolve([
    { slug: 'test-item', similarity_score: 0.95 }
  ])),
  checkHealth: jest.fn(() => Promise.resolve({ connected: true }))
}))
```

OpenAI:
```typescript
jest.mock('@/lib/openai', () => ({
  generateEmbedding: jest.fn(() => Promise.resolve(
    new Array(1536).fill(0.1)
  ))
}))
```

**When mocks are acceptable** (from AE ai-test rules):
1. Verifying something was NOT called
2. Simulating transient errors for retry logic
3. Third-party libraries (but wrap in your own adapter first)

### Watch Mode Workflow

During development, keep tests running continuously:

```bash
# Python
uv run pytest-watch

# TypeScript (Jest)
npx jest --watch

# TypeScript (Vitest)
npx vitest
```

Tests re-run automatically on file changes. Fix failures immediately -- never let red tests accumulate.

### Pre-Commit Verification

Before every commit, run the full suite:

```bash
# Combined check
npm test && npm run lint

# Or via pre-commit hook
pytest && ruff check && ruff format --check
```

## Output Format

Each TDD cycle produces:
1. User journey (As a...)
2. Test cases (failing)
3. Implementation Contract
4. Implementation (minimal)
5. Green confirmation (all tests pass)
6. Refactored code
7. Coverage report showing >= 80%

## Quality Gate

- Tests written BEFORE implementation (no exceptions)
- Implementation Contract produced at RED phase
- Test files untouched during GREEN phase
- No `sleep()` or `waitForTimeout()` for synchronization
- Fakes used for internal interfaces; mocks only for third-party
- Coverage >= 80% on branches, functions, lines, statements
- All tests independent (no shared mutable state between tests)
- Descriptive names: `test_<unit>_<scenario>_<expected>` or `it('should...')`
- Zero skipped or disabled tests without a tracking issue
