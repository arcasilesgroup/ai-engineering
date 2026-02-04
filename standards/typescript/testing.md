# TypeScript Testing Standards

> Jest and Vitest testing patterns.

---

## Test Framework

- **Framework:** Jest or Vitest
- **React Testing:** React Testing Library
- **Mocking:** jest.mock / vi.mock
- **Coverage:** Built-in coverage

---

## Test File Structure

```
src/
├── components/
│   └── UserCard/
│       ├── UserCard.tsx
│       └── UserCard.test.tsx    # Co-located test
├── hooks/
│   └── use-user.ts
│   └── use-user.test.ts
└── __tests__/                   # Integration tests
    └── user-flow.test.tsx
```

---

## Naming Conventions

### Test Files

```
component.test.tsx    # Component tests
hook.test.ts          # Hook tests
util.test.ts          # Utility tests
service.test.ts       # Service tests
```

### Test Names

```typescript
describe('UserCard', () => {
  it('renders user name', () => { });
  it('calls onSelect when clicked', () => { });
  it('displays loading state while fetching', () => { });
  it('shows error message when fetch fails', () => { });
});
```

---

## Component Testing

### Basic Pattern

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { UserCard } from './UserCard';

describe('UserCard', () => {
  const mockUser = {
    id: '1',
    name: 'John Doe',
    email: 'john@example.com',
  };

  it('renders user name', () => {
    render(<UserCard user={mockUser} />);
    
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('calls onSelect when clicked', () => {
    const onSelect = jest.fn();
    render(<UserCard user={mockUser} onSelect={onSelect} />);
    
    fireEvent.click(screen.getByRole('button'));
    
    expect(onSelect).toHaveBeenCalledWith(mockUser);
  });
});
```

### Async Testing

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { UserList } from './UserList';

describe('UserList', () => {
  it('displays users after loading', async () => {
    render(<UserList />);
    
    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });
    
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });
});
```

---

## Hook Testing

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { useUser } from './use-user';

describe('useUser', () => {
  it('fetches user data', async () => {
    const { result } = renderHook(() => useUser('1'));
    
    expect(result.current.isLoading).toBe(true);
    
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    
    expect(result.current.user).toEqual({
      id: '1',
      name: 'John Doe',
    });
  });

  it('handles fetch error', async () => {
    // Mock API to return error
    jest.spyOn(api, 'getUser').mockRejectedValue(new Error('Not found'));
    
    const { result } = renderHook(() => useUser('invalid'));
    
    await waitFor(() => {
      expect(result.current.error).toBe('Not found');
    });
  });
});
```

---

## Mocking

### Module Mocking

```typescript
// Mock entire module
jest.mock('@/services/api', () => ({
  getUser: jest.fn(),
  getUsers: jest.fn(),
}));

// In test
import { getUser } from '@/services/api';

const mockGetUser = getUser as jest.MockedFunction<typeof getUser>;

beforeEach(() => {
  mockGetUser.mockResolvedValue({ id: '1', name: 'John' });
});
```

### Vitest Mocking

```typescript
import { vi } from 'vitest';

vi.mock('@/services/api', () => ({
  getUser: vi.fn(),
}));
```

### MSW (Mock Service Worker)

```typescript
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/users/:id', (req, res, ctx) => {
    return res(ctx.json({ id: req.params.id, name: 'John' }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

---

## Test Utilities

### Custom Render

```typescript
// test-utils.tsx
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient;
}

export function renderWithProviders(
  ui: React.ReactElement,
  options: CustomRenderOptions = {}
) {
  const { queryClient = createTestQueryClient(), ...renderOptions } = options;

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}
```

---

## Assertions

### Common Patterns

```typescript
// Element presence
expect(screen.getByText('Hello')).toBeInTheDocument();
expect(screen.queryByText('Loading')).not.toBeInTheDocument();

// Element state
expect(button).toBeDisabled();
expect(input).toHaveValue('test');
expect(checkbox).toBeChecked();

// Function calls
expect(mockFn).toHaveBeenCalled();
expect(mockFn).toHaveBeenCalledWith(expectedArg);
expect(mockFn).toHaveBeenCalledTimes(1);

// Async assertions
await expect(promise).resolves.toEqual(expected);
await expect(promise).rejects.toThrow('error');
```

---

## Best Practices

### Do

- ✅ Test behavior, not implementation
- ✅ Use `screen` queries (getByRole, getByText)
- ✅ Prefer `userEvent` over `fireEvent`
- ✅ Test accessibility (getByRole)
- ✅ Clean up mocks in afterEach

### Don't

- ❌ Test implementation details
- ❌ Snapshot test everything
- ❌ Test third-party libraries
- ❌ Mock too much
- ❌ Write brittle selectors (getByTestId abuse)
