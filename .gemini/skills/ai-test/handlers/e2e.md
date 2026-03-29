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
