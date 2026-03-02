# Automation Frameworks

## Advanced Framework Patterns

### Screenplay Pattern

```typescript
export class Actor {
  constructor(private page: Page) {}
  attemptsTo(...tasks: Task[]) {
    return Promise.all(tasks.map(t => t.performAs(this)));
  }
}

class Login implements Task {
  constructor(private email: string, private password: string) {}
  async performAs(actor: Actor) {
    await actor.page.getByLabel('Email').fill(this.email);
    await actor.page.getByLabel('Password').fill(this.password);
    await actor.page.getByRole('button', { name: 'Login' }).click();
  }
}

await new Actor(page).attemptsTo(new Login('user@test.com', 'pass'));
```

### Keyword-Driven Testing

```typescript
const keywords = {
  NAVIGATE: (page, url) => page.goto(url),
  CLICK: (page, selector) => page.click(selector),
  TYPE: (page, selector, text) => page.fill(selector, text),
  VERIFY: (page, selector) => expect(page.locator(selector)).toBeVisible(),
};

const steps = [
  { keyword: 'NAVIGATE', args: ['/login'] },
  { keyword: 'TYPE', args: ['#email', 'user@test.com'] },
  { keyword: 'CLICK', args: ['#submit'] },
];

for (const step of steps) await keywords[step.keyword](page, ...step.args);
```

## Maintenance Strategies

### Self-Healing Locators

```typescript
async function findElement(page: Page, strategies: string[]): Promise<Locator> {
  for (const selector of strategies) {
    const el = page.locator(selector);
    if (await el.count() > 0) return el;
  }
  throw new Error(`Not found: ${strategies.join(', ')}`);
}

const submit = await findElement(page, [
  '[data-testid="submit"]',     // Best: stable test ID
  'button:has-text("Submit")',  // Good: semantic
  'button.primary',             // Fallback: CSS
]);
```

### Error Recovery & Smart Retry

```typescript
async function retryWithBackoff<T>(fn: () => Promise<T>, retries = 3): Promise<T> {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (e) {
      if (i === retries - 1) throw e;
      await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i)));
    }
  }
}
```

## Scaling Strategies

### Parallel & Distributed Execution

```typescript
// playwright.config.ts
export default defineConfig({
  workers: process.env.CI ? 8 : 4,
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  shard: process.env.SHARD ? {
    current: parseInt(process.env.SHARD_INDEX),
    total: parseInt(process.env.SHARD_TOTAL),
  } : undefined,
});
```

## CI/CD Integration

```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test --shard=${{ matrix.shard }}/4
```

## Test Data Factories

```typescript
export class UserFactory {
  static create(overrides?: Partial<User>): User {
    return {
      id: faker.string.uuid(),
      email: faker.internet.email(),
      name: faker.person.fullName(),
      role: 'user',
      ...overrides,
    };
  }
  static createMany(count: number) {
    return Array.from({ length: count }, () => this.create());
  }
}
```

## Selection Criteria

**Automate**: Repetitive, stable UI, critical paths, data-driven, positive ROI.
**Don't automate**: Exploratory, changing UI, one-time, usability, negative ROI.

## Quick Reference

| Pattern | Best For | Complexity |
|---------|----------|-----------|
| Page Object | Reusable components | Medium |
| Screenplay | Complex workflows | High |
| Keyword-Driven | Non-tech testers | Low |
| Model-Based | State machines | High |

| Scaling | Use Case |
|---------|----------|
| Parallel | Reduce time |
| Distributed | Large suites |
| Cloud | Cross-browser |
| Resource Reuse | Speed |
