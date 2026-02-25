# Unit Testing

## Principles

- Isolated: no I/O, no network, no filesystem.
- Fast: <1s per test, entire unit suite <30s.
- Deterministic: same result every run.
- One assertion per logical concept.

## Python (pytest)

```python
import pytest

def test_calculate_total_with_tax():
    # Arrange
    items = [{"price": 100, "qty": 2}]

    # Act
    total = calculate_total(items, tax_rate=0.08)

    # Assert
    assert total == 216.0


def test_calculate_total_empty_cart():
    assert calculate_total([], tax_rate=0.08) == 0.0


@pytest.mark.parametrize("input_val,expected", [
    ([], 0),
    ([1], 1),
    ([1, 2, 3], 6),
    ([-1, 1], 0),
])
def test_sum_parametrized(input_val, expected):
    assert sum_values(input_val) == expected
```

## TypeScript/JS (Vitest)

```typescript
import { describe, it, expect, vi } from 'vitest';

describe('Calculator', () => {
  it('calculates total with tax', () => {
    const cart = new Cart([{ price: 100, qty: 2 }]);
    expect(cart.totalWithTax(0.08)).toBe(216);
  });

  it('returns 0 for empty cart', () => {
    const cart = new Cart([]);
    expect(cart.totalWithTax(0.08)).toBe(0);
  });
});
```

## Mocking

```python
# Python — mock external dependency
from unittest.mock import patch

def test_fetch_user_returns_data():
    with patch("app.client.http_get") as mock_get:
        mock_get.return_value = {"id": 1, "name": "Alice"}
        user = fetch_user(1)
    assert user.name == "Alice"
```

```typescript
// TypeScript — Vitest mock
import { vi } from 'vitest';

const mockFetch = vi.fn().mockResolvedValue({
  json: () => Promise.resolve({ id: 1, name: 'Test' }),
});
vi.stubGlobal('fetch', mockFetch);
```

## Async Testing

```python
import pytest

@pytest.mark.asyncio
async def test_async_fetch():
    result = await async_fetch_data("key")
    assert result is not None
```

```typescript
it('fetches user data', async () => {
  const user = await getUser('123');
  expect(user.name).toBe('Alice');
});
```

## Quick Reference

| Principle | Guideline |
|-----------|-----------|
| Isolation | No I/O, no shared state |
| Speed | <1s per test |
| Naming | `test_<unit>_<scenario>_<outcome>` |
| Assertions | One logical concept per test |
| Mocking | Only external dependencies |
| Parametrize | Use for input/output variations |
