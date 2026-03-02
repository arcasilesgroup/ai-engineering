# Testing Anti-Patterns

## Core Principle

> **"Test what the code does, not what the mocks do."**

When tests verify mock behavior instead of actual functionality, they provide false confidence while catching zero real bugs.

## The Five Anti-Patterns

### Anti-Pattern 1: Testing Mock Behavior

```typescript
// BAD: Testing the mock, not the behavior
it('should call the API', () => {
  const mockApi = jest.fn().mockResolvedValue({ data: 'test' });
  const service = new UserService(mockApi);
  service.getUser(1);
  expect(mockApi).toHaveBeenCalledWith(1); // Testing mock, not result
});

// GOOD: Testing actual behavior
it('should return user data from API', async () => {
  const mockApi = jest.fn().mockResolvedValue({ id: 1, name: 'Alice' });
  const service = new UserService(mockApi);
  const user = await service.getUser(1);
  expect(user.name).toBe('Alice'); // Testing actual output
});
```

### Anti-Pattern 2: Test-Only Methods in Production

```typescript
// BAD: Production code polluted with test concerns
class UserCache {
  _resetForTesting(): void { this.cache.clear(); }
}

// GOOD: Fresh instances per test
function createFreshCache(): UserCache {
  return new UserCache();
}
```

### Anti-Pattern 3: Mocking Without Understanding

```typescript
// BAD: Mocking everything
jest.mock('./inventory');
jest.mock('./payment');
jest.mock('./shipping');
jest.mock('./notifications');
const result = await processOrder(order);
expect(result.success).toBe(true); // What did we actually test?

// GOOD: Strategic mocking
const inventory = new InventoryService(testDb);  // Real
const payment = mockPaymentGateway();              // Mock external only
const processor = new OrderProcessor(inventory, payment);
const result = await processor.process(order);
expect(await inventory.getStock(order.itemId)).toBe(originalStock - 1);
```

### Anti-Pattern 4: Incomplete Mocks

```typescript
// BAD: Missing downstream fields
const mockUserApi = jest.fn().mockResolvedValue({ id: 1, name: 'Test' });
// Production crashes when accessing user.email

// GOOD: Complete mock or use factory
const mockUserApi = jest.fn().mockResolvedValue(
  createMockUser({ name: 'Test' }) // Factory fills defaults
);
```

### Anti-Pattern 5: Integration Tests as Afterthought

```typescript
// BAD: "We'll add tests later"
// Day 1: Write 500 lines. Day 3: Ship without tests. Day 30: Production bug.

// GOOD: Tests are part of implementation (TDD)
it('should reject duplicate usernames', async () => {
  await createUser({ username: 'alice' });
  await expect(createUser({ username: 'alice' })).rejects.toThrow('Username already exists');
});
```

## Detection Checklist

| Warning Sign | Anti-Pattern |
|-------------|--------------|
| `expect(mock).toHaveBeenCalled()` without output test | Testing mock behavior |
| Methods starting with `_` or `ForTesting` in production | Test-only methods |
| Every dependency is mocked | Mocking without understanding |
| Mocks return `{ success: true }` only | Incomplete mocks |
| Test files added weeks after feature ships | Tests as afterthought |

## Quick Reference

| Anti-Pattern | Fix |
|-------------|-----|
| Testing mocks | Assert on actual output |
| Test-only methods | Use fresh instances |
| Over-mocking | Test with real deps first |
| Incomplete mocks | Use factories, match reality |
| Tests as afterthought | TDD from the start |

---

*Content adapted from [obra/superpowers](https://github.com/obra/superpowers) by Jesse Vincent (@obra), MIT License.*
