## Core Principles

**KISS (Keep It Simple, Stupid):**
Choose the simplest solution that works. Avoid over-engineering and premature optimization. Easy to understand beats clever every time.

**DRY (Don't Repeat Yourself):**
Extract common logic into functions or modules. If you copy-paste, you create two places to update and two places for bugs to hide. But do not over-abstract -- wait until the third occurrence before extracting a shared utility.

**YAGNI (You Aren't Gonna Need It):**
Don't build features before they are needed. Avoid speculative generality. Start simple, refactor when the real requirement arrives. Code that was never needed is the cheapest code to maintain.

**Readability First:**
Code is read far more than it is written. Optimize for the next reader, who may be you in six months. Self-documenting code preferred over comments that restate what the code does.

## Naming

**Functions -- verb-noun pattern:**

```python
# GOOD: verb-noun, describes action and target
def fetch_user_profile(user_id: str) -> Profile: ...
def calculate_similarity(vec_a: list, vec_b: list) -> float: ...
def is_valid_email(email: str) -> bool: ...

# BAD: noun-only, ambiguous
def user(id): ...
def similarity(a, b): ...
def email(e): ...
```

```typescript
// GOOD: verb-noun pattern
async function fetchMarketData(marketId: string): Promise<Market> { }
function calculateSimilarity(a: number[], b: number[]): number { }
function isValidEmail(email: string): boolean { }

// BAD: unclear or noun-only
async function market(id: string) { }
function similarity(a, b) { }
function email(e) { }
```

```go
// GOOD: exported verb-noun
func FetchUserProfile(userID string) (*Profile, error) { }
func IsValidEmail(email string) bool { }

// BAD: ambiguous
func User(id string) { }
func Email(e string) { }
```

**Boolean prefixes -- `is`, `has`, `should`, `can`:**

```
// GOOD: intention is clear from the name
isAuthenticated, hasPermission, shouldRetry, canDelete

// BAD: ambiguous -- is this a boolean or a noun?
authenticated, permission, retry, delete
```

**Variables -- descriptive, no single letters:**

```
// GOOD: what the value represents
totalRevenue, searchQuery, maxRetries, userCount

// BAD: cryptic abbreviations
x, q, n, tmp, data2
```

**Constants -- UPPER_SNAKE_CASE:**

```
MAX_RETRIES = 3
DEBOUNCE_DELAY_MS = 500
DEFAULT_PAGE_SIZE = 20
```

## Comments

**Explain WHY, not WHAT.** The code already says what it does. Comments should explain non-obvious decisions, constraints, and trade-offs.

```python
# GOOD: explains WHY
# Use exponential backoff to avoid overwhelming the API during outages
delay = min(1000 * (2 ** retry_count), 30000)

# Deliberately using mutation here for performance with 10K+ element arrays
items.append(new_item)

# BAD: restates what the code does
# Increment counter by 1
count += 1

# Set name to user's name
name = user.name
```

**JSDoc / docstring standard for public APIs:**

```typescript
/**
 * Searches markets using semantic similarity.
 *
 * @param query - Natural language search query
 * @param limit - Maximum number of results (default: 10)
 * @returns Array of markets sorted by similarity score
 * @throws {Error} If embedding API fails or database is unavailable
 *
 * @example
 * ```typescript
 * const results = await searchMarkets("election", 5);
 * console.log(results[0].name);
 * ```
 */
export async function searchMarkets(query: string, limit: number = 10): Promise<Market[]> { }
```

```python
def search_markets(query: str, limit: int = 10) -> list[Market]:
    """Search markets using semantic similarity.

    Args:
        query: Natural language search query.
        limit: Maximum number of results. Defaults to 10.

    Returns:
        List of markets sorted by similarity score.

    Raises:
        ConnectionError: If embedding API fails.

    Example:
        >>> results = search_markets("election", 5)
        >>> results[0].name
        'US Presidential Election'
    """
```

**Required documentation tags:** `@param` (or `Args:`), `@returns` (or `Returns:`), `@throws` (or `Raises:`), `@example` (or `Example:`).

## Testing

**AAA pattern (Arrange / Act / Assert) with labeled comments:**

```typescript
test("returns empty array when no markets match query", () => {
  // Arrange
  const markets: Market[] = [];
  const query = "nonexistent";

  // Act
  const results = filterMarkets(markets, query);

  // Assert
  expect(results).toEqual([]);
});
```

```python
def test_returns_empty_list_when_no_markets_match():
    # Arrange
    markets = []
    query = "nonexistent"

    # Act
    results = filter_markets(markets, query)

    # Assert
    assert results == []
```

**Descriptive test names -- describe the scenario and expected outcome:**

```
// GOOD: reads like a specification
"returns empty array when no markets match query"
"throws error when API key is missing"
"falls back to substring search when vector DB is unavailable"
"creates user with valid data and returns 201"

// BAD: vague, tells you nothing when it fails
"works"
"test search"
"handles error"
```

**One assertion per behavior.** Multiple assertions are fine when they verify the same behavior from different angles. Separate tests for separate behaviors.

## Code Smells

**Long functions (>50 lines) -- split by responsibility:**

```python
# BAD: one function doing everything
def process_market_data(raw_data):
    # ... 100 lines of validation, transformation, persistence, notification ...

# GOOD: split into focused functions
def process_market_data(raw_data):
    validated = validate_market_data(raw_data)
    transformed = transform_market_data(validated)
    saved = persist_market_data(transformed)
    notify_subscribers(saved)
    return saved
```

**Deep nesting (>3 levels) -- use early returns:**

```typescript
// BAD: 5+ levels of nesting
if (user) {
  if (user.isAdmin) {
    if (market) {
      if (market.isActive) {
        if (hasPermission) {
          // Do something
        }
      }
    }
  }
}

// GOOD: early returns flatten the logic
if (!user) return;
if (!user.isAdmin) return;
if (!market) return;
if (!market.isActive) return;
if (!hasPermission) return;

// Do something
```

**Magic numbers -- use named constants:**

```typescript
// BAD: what do these numbers mean?
if (retryCount > 3) { }
setTimeout(callback, 500);

// GOOD: intent is clear
const MAX_RETRIES = 3;
const DEBOUNCE_DELAY_MS = 500;

if (retryCount > MAX_RETRIES) { }
setTimeout(callback, DEBOUNCE_DELAY_MS);
```

**God classes / god functions:** If a module or function has more than one reason to change, it is doing too much. Split along responsibility boundaries.

**Primitive obsession:** Passing raw strings/numbers when a domain type would prevent misuse (e.g., `userId: string` vs `UserId` type).

## Common Anti-Patterns

**Naming:**

- Single-letter variables outside of trivial loop indices (`for i in range(n)` is fine; `x = get_user()` is not)
- Boolean variables without `is/has/should/can` prefix -- ambiguous when read in conditionals
- Functions named with nouns instead of verbs -- indistinguishable from data

**Comments:**

- Comments that restate the code -- become stale when the code changes
- Commented-out code left in the file -- use version control instead
- TODO comments without a tracking issue -- they live forever

**Testing:**

- Tests with no assertions (pass without verifying anything)
- Test names that say "test1", "test2" -- useless when a test fails
- Skipped tests left in the suite indefinitely -- either fix or delete them
- Testing implementation details instead of behavior -- brittle on refactor

**Structure:**

- Functions over 50 lines -- hard to understand, hard to test, hard to reuse
- Nesting deeper than 3 levels -- flatten with early returns or extract helper functions
- Magic numbers and strings scattered through logic -- change one, miss another
- Copy-paste code that drifts apart over time -- extract and share
