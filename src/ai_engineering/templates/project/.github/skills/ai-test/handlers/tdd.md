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
3. Write the simplest code that makes the test pass, following `.ai-engineering/contexts/operational-principles.md`
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
