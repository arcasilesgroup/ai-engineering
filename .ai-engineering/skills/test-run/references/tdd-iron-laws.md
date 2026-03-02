# TDD Iron Laws

## The Fundamental Principle

> **NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.**

This is non-negotiable. If you wrote production code before writing a failing test, delete it and start over.

## The Three Iron Laws

### Iron Law 1: The Fundamental Rule

> "You shall not write any production code unless it is to make a failing test pass."

Every line of production code must have a corresponding test that:
1. Was written first.
2. Was observed to fail.
3. Now passes because of that code.

### Iron Law 2: Proof Through Observation

> "If you didn't watch the test fail, you don't know if it tests the right thing."

Mandatory verification steps:
- Write the test.
- Run it and **observe the failure**.
- Verify the failure message is meaningful.
- Only then implement the fix.

### Iron Law 3: The Final Rule

> "Production code exists -> A test exists that failed first. Otherwise -> It's not TDD."

## The RED-GREEN-REFACTOR Cycle

### RED: Write One Minimal Failing Test

```typescript
it('should return 0 for empty array', () => {
  expect(sum([])).toBe(0);
});
// Run: FAIL - sum is not defined
```

### GREEN: Implement Simplest Passing Code

```typescript
function sum(numbers: number[]): number {
  return 0;
}
// Run: PASS
```

### REFACTOR: Improve While Keeping Tests Green

```typescript
function sum(numbers: number[]): number {
  return numbers.reduce((acc, n) => acc + n, 0);
}
// Run: PASS (still)
```

## Common Rationalizations to Reject

| Rationalization | Why It's Wrong |
|-----------------|----------------|
| "I can manually test this quickly" | Manual testing doesn't prevent regression |
| "I'll write tests after to save time" | You'll skip edge cases and test implementation |
| "This is too simple to need a test" | Simple code changes; tests document expectations |
| "I've already written the code" | Sunk cost fallacy; delete it |
| "We're in a hurry" | Technical debt costs more than TDD |

## Practical Application

### Starting a New Feature

```typescript
// 1. RED
it('should reject empty email', () => {
  expect(validateEmail('')).toBe(false);
});

// 2. GREEN
function validateEmail(email: string): boolean {
  return email.length > 0;
}

// 3. RED (next test)
it('should reject email without @', () => {
  expect(validateEmail('invalid')).toBe(false);
});

// 4. GREEN
function validateEmail(email: string): boolean {
  return email.length > 0 && email.includes('@');
}
```

### Fixing a Bug

```typescript
// 1. RED: test that exposes the bug
it('should handle negative numbers in sum', () => {
  expect(sum([-1, -2, -3])).toBe(-6);
});
// FAIL - got 0 instead of -6

// 2. GREEN: fix the bug
function sum(numbers: number[]): number {
  return numbers.reduce((acc, n) => acc + n, 0);
}
// PASS — bug fixed AND protected against regression
```

## Verification Checklist

- [ ] Every production function has corresponding tests.
- [ ] Each test was written before its implementation.
- [ ] Each test was observed to fail first.
- [ ] Tests verify behavior, not implementation.
- [ ] Refactoring kept all tests green.

---

*Content adapted from [obra/superpowers](https://github.com/obra/superpowers) by Jesse Vincent (@obra), MIT License.*
