# E2E Testing

## Principles

- Test critical user paths end-to-end.
- Validate full stack behavior (UI, API, DB).
- Slower but highest confidence.
- Focus on user journeys, not line coverage.

## Critical User Paths

Prioritize testing:
1. User registration and login.
2. Core product/service workflow.
3. Payment/checkout flow.
4. Settings and profile management.

## Playwright (TypeScript)

```typescript
import { test, expect } from '@playwright/test';

test.describe('User Registration Flow', () => {
  test('complete registration', async ({ page }) => {
    await page.goto('/register');
    await page.getByLabel('Email').fill('new@example.com');
    await page.getByLabel('Password').fill('SecurePass123!');
    await page.getByLabel('Confirm Password').fill('SecurePass123!');
    await page.getByRole('button', { name: 'Register' }).click();

    await expect(page).toHaveURL(/dashboard/);
    await expect(page.getByText('Welcome')).toBeVisible();
  });

  test('shows validation errors', async ({ page }) => {
    await page.goto('/register');
    await page.getByLabel('Email').fill('invalid');
    await page.getByRole('button', { name: 'Register' }).click();
    await expect(page.getByText('Invalid email')).toBeVisible();
  });
});
```

## Test Data Management

```typescript
export const testUsers = {
  standard: { email: 'standard@test.com', password: 'TestPass123!' },
  admin: { email: 'admin@test.com', password: 'AdminPass123!' },
};

test.beforeEach(async ({ page }) => {
  await page.request.post('/api/test/seed');
});

test.afterEach(async ({ page }) => {
  await page.request.post('/api/test/cleanup');
});
```

## Cross-Browser Testing

```typescript
// playwright.config.ts
export default defineConfig({
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
    { name: 'mobile-safari', use: { ...devices['iPhone 13'] } },
  ],
});
```

## Quick Reference

| Priority | Test Coverage |
|----------|--------------|
| **P0** | Registration, login, core feature |
| **P1** | Payment, settings, common flows |
| **P2** | Edge cases, admin features |
| **P3** | Rare scenarios |

| Pattern | When to Use |
|---------|-------------|
| Happy path | Critical user journeys |
| Error handling | Form validation, API errors |
| Edge cases | Empty states, max limits |
| Cross-browser | Before major releases |
