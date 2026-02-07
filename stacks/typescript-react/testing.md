# TypeScript/React Testing Standards

All TypeScript/React code MUST be tested using Vitest and React Testing Library. Follow these standards for every test file.

---

## Table of Contents

- [Test File Location and Naming](#test-file-location-and-naming)
- [Test Structure](#test-structure)
- [Component Testing](#component-testing)
- [Hook Testing](#hook-testing)
- [Async Testing Patterns](#async-testing-patterns)
- [Mock Patterns](#mock-patterns)
- [Snapshot Testing Policy](#snapshot-testing-policy)
- [Integration Test Patterns](#integration-test-patterns)
- [Accessibility Testing](#accessibility-testing)
- [Coverage Expectations](#coverage-expectations)

---

## Test File Location and Naming

### Co-locate Tests with Source

Every test file lives next to the source file it tests. Never put tests in a separate `__tests__` directory tree.

```
features/
  users/
    components/
      UserCard.tsx
      UserCard.test.tsx        # Co-located
    hooks/
      use-user.ts
      use-user.test.ts         # Co-located
    utils/
      format-user.ts
      format-user.test.ts      # Co-located
```

### Naming Convention

- Component tests: `{ComponentName}.test.tsx`
- Hook tests: `{hook-name}.test.ts` (or `.test.tsx` if rendering is needed)
- Utility tests: `{util-name}.test.ts`
- Integration tests: `{feature}.integration.test.tsx`

---

## Test Structure

### describe / it Naming

Use `describe` for the unit under test and `it` for specific behaviors. Write test names as complete sentences that describe the expected behavior.

```typescript
// DO: Descriptive test structure
describe('UserCard', () => {
  it('renders the user name and email', () => { ... });
  it('shows the admin badge when the user has admin role', () => { ... });
  it('calls onSelect with the user id when clicked', () => { ... });
  it('disables interaction when the disabled prop is true', () => { ... });
});

describe('useUser', () => {
  it('returns the user data for a valid id', async () => { ... });
  it('returns an error when the API request fails', async () => { ... });
  it('refetches when the id changes', async () => { ... });
});

// DON'T: Vague or implementation-focused names
describe('UserCard', () => {
  it('works', () => { ... });
  it('test 1', () => { ... });
  it('should render', () => { ... });
  it('calls setState', () => { ... }); // Testing implementation, not behavior
});
```

### Arrange-Act-Assert

Every test follows the Arrange-Act-Assert pattern. Separate the sections with blank lines for readability.

```typescript
it('filters users by search term', () => {
  // Arrange
  const users = [
    createUser({ name: 'Alice Johnson' }),
    createUser({ name: 'Bob Smith' }),
    createUser({ name: 'Alice Cooper' }),
  ];

  // Act
  const result = filterUsers(users, 'Alice');

  // Assert
  expect(result).toHaveLength(2);
  expect(result.map((u) => u.name)).toEqual(['Alice Johnson', 'Alice Cooper']);
});
```

### Test Factories

Use factory functions to create test data. Never hardcode test objects inline in every test.

```typescript
// test/factories/user.ts
import type { User } from '@/features/users/types';

let idCounter = 0;

export function createUser(overrides: Partial<User> = {}): User {
  idCounter += 1;
  return {
    id: `user-${idCounter}`,
    name: `Test User ${idCounter}`,
    email: `user${idCounter}@test.com`,
    role: 'viewer',
    avatar: null,
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date('2024-01-01'),
    ...overrides,
  };
}

// Usage in tests
const admin = createUser({ name: 'Admin', role: 'admin' });
const viewer = createUser({ name: 'Viewer', role: 'viewer' });
```

### Setup and Teardown

Use `beforeEach` for shared setup. Prefer creating test data inside individual tests when it makes the test more readable.

```typescript
describe('UserList', () => {
  // Shared setup for all tests in this block
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders a list of users', () => {
    // Test-specific data created inline for clarity
    const users = [createUser(), createUser(), createUser()];
    render(<UserList users={users} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
  });
});
```

---

## Component Testing

### Rendering Components

Use `render` from React Testing Library. Query elements by their accessible role, label, or text -- never by CSS class or test ID (unless no accessible alternative exists).

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserCard } from './UserCard';
import { createUser } from '@/test/factories/user';

describe('UserCard', () => {
  it('renders the user name and email', () => {
    const user = createUser({ name: 'Jane Doe', email: 'jane@example.com' });

    render(<UserCard user={user} />);

    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    expect(screen.getByText('jane@example.com')).toBeInTheDocument();
  });

  it('renders the avatar with accessible alt text', () => {
    const user = createUser({ name: 'Jane Doe', avatar: '/jane.jpg' });

    render(<UserCard user={user} />);

    const avatar = screen.getByRole('img', { name: /jane doe/i });
    expect(avatar).toHaveAttribute('src', '/jane.jpg');
  });
});
```

### Query Priority

Follow the React Testing Library query priority:

1. `getByRole` -- accessible role (button, heading, textbox, etc.)
2. `getByLabelText` -- form inputs with labels
3. `getByPlaceholderText` -- when label is not available
4. `getByText` -- visible text content
5. `getByDisplayValue` -- form element current value
6. `getByAltText` -- images
7. `getByTitle` -- title attribute
8. `getByTestId` -- last resort only

```typescript
// DO: Query by role
const submitButton = screen.getByRole('button', { name: /submit/i });
const nameInput = screen.getByRole('textbox', { name: /name/i });
const heading = screen.getByRole('heading', { level: 1 });

// DO: Query by label for form fields
const emailInput = screen.getByLabelText(/email/i);

// ACCEPTABLE: getByTestId when no semantic query works
const complexWidget = screen.getByTestId('color-picker');

// DON'T: Query by CSS class or DOM structure
const button = container.querySelector('.submit-btn'); // Never
```

### User Event Testing

Use `@testing-library/user-event` (not `fireEvent`) for user interactions. It simulates real browser behavior (focus, keydown, keyup, input, change).

```typescript
import userEvent from '@testing-library/user-event';

describe('LoginForm', () => {
  it('submits the form with email and password', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(<LoginForm onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText(/email/i), 'user@example.com');
    await user.type(screen.getByLabelText(/password/i), 'securepassword');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    expect(handleSubmit).toHaveBeenCalledWith({
      email: 'user@example.com',
      password: 'securepassword',
    });
  });

  it('shows validation errors for empty fields', async () => {
    const user = userEvent.setup();

    render(<LoginForm onSubmit={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /log in/i }));

    expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    expect(screen.getByText(/password is required/i)).toBeInTheDocument();
  });

  it('disables the submit button while submitting', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn(() => new Promise<void>((resolve) => setTimeout(resolve, 100)));

    render(<LoginForm onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText(/email/i), 'user@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    expect(screen.getByRole('button', { name: /log in/i })).toBeDisabled();
  });
});
```

### Testing Conditional Rendering

```typescript
describe('UserProfile', () => {
  it('shows the edit button for the profile owner', () => {
    const user = createUser({ id: 'user-1' });

    render(<UserProfile user={user} currentUserId="user-1" />);

    expect(screen.getByRole('button', { name: /edit profile/i })).toBeInTheDocument();
  });

  it('hides the edit button for other users', () => {
    const user = createUser({ id: 'user-1' });

    render(<UserProfile user={user} currentUserId="user-2" />);

    expect(screen.queryByRole('button', { name: /edit profile/i })).not.toBeInTheDocument();
  });
});
```

### Testing with Providers

Create a custom render function that wraps components with required providers.

```typescript
// test/utils/render.tsx
import { render, type RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialRoute?: string;
  queryClient?: QueryClient;
}

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
}

export function renderWithProviders(
  ui: React.ReactElement,
  options: CustomRenderOptions = {},
): ReturnType<typeof render> {
  const {
    initialRoute = '/',
    queryClient = createTestQueryClient(),
    ...renderOptions
  } = options;

  function Wrapper({ children }: { children: React.ReactNode }): React.ReactElement {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialRoute]}>
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}
```

---

## Hook Testing

### renderHook

Test custom hooks using `renderHook` from React Testing Library.

```typescript
import { renderHook, act } from '@testing-library/react';
import { useToggle } from './use-toggle';

describe('useToggle', () => {
  it('initializes with the provided value', () => {
    const { result } = renderHook(() => useToggle(true));

    expect(result.current[0]).toBe(true);
  });

  it('toggles the value when toggle is called', () => {
    const { result } = renderHook(() => useToggle(false));

    act(() => {
      result.current[1](); // toggle function
    });

    expect(result.current[0]).toBe(true);
  });
});
```

### Hooks with Dependencies

When a hook depends on changing props, use the `rerender` function.

```typescript
describe('useDebouncedValue', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns the initial value immediately', () => {
    const { result } = renderHook(() => useDebouncedValue('hello', 300));

    expect(result.current).toBe('hello');
  });

  it('debounces value changes', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebouncedValue(value, 300),
      { initialProps: { value: 'hello' } },
    );

    rerender({ value: 'world' });
    expect(result.current).toBe('hello'); // Not yet updated

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current).toBe('world'); // Now updated
  });
});
```

### Hooks with Context

Wrap hooks that depend on context using a provider wrapper.

```typescript
describe('useAuth', () => {
  it('returns the authenticated user', () => {
    const mockUser = createUser({ name: 'Test User' });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthContext.Provider value={{ user: mockUser, isAuthenticated: true, login: vi.fn(), logout: vi.fn() }}>
        {children}
      </AuthContext.Provider>
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('throws when used outside AuthProvider', () => {
    expect(() => {
      renderHook(() => useAuth());
    }).toThrow('useAuth must be used within an AuthProvider');
  });
});
```

---

## Async Testing Patterns

### Waiting for Elements

Use `findBy` queries (which wait) for elements that appear asynchronously. Use `waitFor` for assertions that need to wait.

```typescript
describe('UserProfile', () => {
  it('loads and displays user data', async () => {
    server.use(
      http.get('/api/users/:id', () => {
        return HttpResponse.json(createUser({ name: 'Jane Doe' }));
      }),
    );

    renderWithProviders(<UserProfile userId="user-1" />);

    // Wait for async content to appear
    expect(await screen.findByText('Jane Doe')).toBeInTheDocument();
  });

  it('shows an error message when loading fails', async () => {
    server.use(
      http.get('/api/users/:id', () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    renderWithProviders(<UserProfile userId="user-1" />);

    expect(await screen.findByText(/something went wrong/i)).toBeInTheDocument();
  });
});
```

### waitFor

Use `waitFor` when you need to assert on state changes that happen asynchronously but do not produce new DOM elements.

```typescript
it('disables the button after submission', async () => {
  const user = userEvent.setup();
  render(<SubmitForm />);

  await user.click(screen.getByRole('button', { name: /submit/i }));

  await waitFor(() => {
    expect(screen.getByRole('button', { name: /submit/i })).toBeDisabled();
  });
});
```

### waitForElementToBeRemoved

```typescript
it('removes the loading spinner after data loads', async () => {
  renderWithProviders(<UserList />);

  // Spinner should be visible initially
  expect(screen.getByRole('progressbar')).toBeInTheDocument();

  // Wait for it to disappear
  await waitForElementToBeRemoved(() => screen.queryByRole('progressbar'));

  // Now data should be visible
  expect(screen.getAllByRole('listitem').length).toBeGreaterThan(0);
});
```

### Fake Timers

Use `vi.useFakeTimers()` for testing debounce, throttle, setTimeout, and setInterval.

```typescript
describe('AutoSave', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('saves after 2 seconds of inactivity', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const onSave = vi.fn();

    render(<AutoSaveForm onSave={onSave} />);

    await user.type(screen.getByRole('textbox'), 'Hello');

    // Not saved yet
    expect(onSave).not.toHaveBeenCalled();

    // Advance past debounce period
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(onSave).toHaveBeenCalledTimes(1);
  });
});
```

---

## Mock Patterns

### vi.fn() for Callbacks

Use `vi.fn()` to create mock functions for testing callback props.

```typescript
it('calls onDelete when the delete button is clicked', async () => {
  const user = userEvent.setup();
  const onDelete = vi.fn();

  render(<UserCard user={createUser()} onDelete={onDelete} />);

  await user.click(screen.getByRole('button', { name: /delete/i }));

  expect(onDelete).toHaveBeenCalledTimes(1);
  expect(onDelete).toHaveBeenCalledWith(expect.stringMatching(/^user-/));
});
```

### vi.mock() for Modules

Mock entire modules when you need to isolate a unit from its dependencies.

```typescript
// Mock a module
vi.mock('@/shared/api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from '@/shared/api/client';

describe('usersApi', () => {
  it('fetches a user by id', async () => {
    const mockUser = createUser({ id: 'user-1' });
    vi.mocked(api.get).mockResolvedValue(mockUser);

    const result = await usersApi.getUser('user-1');

    expect(api.get).toHaveBeenCalledWith('/users/user-1');
    expect(result).toEqual(mockUser);
  });
});
```

### MSW for API Mocking

Use Mock Service Worker (MSW) for integration tests that involve API calls. MSW intercepts at the network level, so your actual fetch logic is tested.

```typescript
// test/mocks/handlers.ts
import { http, HttpResponse } from 'msw';
import { createUser } from '../factories/user';

export const handlers = [
  http.get('/api/users', () => {
    return HttpResponse.json([
      createUser({ name: 'Alice' }),
      createUser({ name: 'Bob' }),
    ]);
  }),

  http.get('/api/users/:id', ({ params }) => {
    return HttpResponse.json(createUser({ id: params.id as string }));
  }),

  http.post('/api/users', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json(createUser(body as Partial<User>), { status: 201 });
  }),

  http.delete('/api/users/:id', () => {
    return new HttpResponse(null, { status: 204 });
  }),
];

// test/mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);

// test/setup.ts (vitest setup file)
import { server } from './mocks/server';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

```typescript
// Using MSW in tests with per-test overrides
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';

describe('UserList', () => {
  it('displays users from the API', async () => {
    renderWithProviders(<UserListPage />);

    expect(await screen.findByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('shows an error when the API fails', async () => {
    // Override the default handler for this test
    server.use(
      http.get('/api/users', () => {
        return HttpResponse.json(
          { message: 'Internal Server Error' },
          { status: 500 },
        );
      }),
    );

    renderWithProviders(<UserListPage />);

    expect(await screen.findByText(/something went wrong/i)).toBeInTheDocument();
  });
});
```

### Mocking Hooks

When testing a component that uses a complex hook, mock the hook to isolate the component's rendering logic.

```typescript
vi.mock('../hooks/use-user', () => ({
  useUser: vi.fn(),
}));

import { useUser } from '../hooks/use-user';

describe('UserProfile', () => {
  it('renders user data', () => {
    vi.mocked(useUser).mockReturnValue({
      user: createUser({ name: 'Jane' }),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<UserProfile userId="user-1" />);

    expect(screen.getByText('Jane')).toBeInTheDocument();
  });

  it('shows a loading skeleton', () => {
    vi.mocked(useUser).mockReturnValue({
      user: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    render(<UserProfile userId="user-1" />);

    expect(screen.getByTestId('profile-skeleton')).toBeInTheDocument();
  });
});
```

---

## Snapshot Testing Policy

### Avoid Snapshot Tests

Do not use snapshot tests for component rendering. They are brittle, produce large diffs for trivial changes, and rarely catch real bugs.

```typescript
// DON'T: Snapshot test
it('renders correctly', () => {
  const { container } = render(<UserCard user={createUser()} />);
  expect(container).toMatchSnapshot();
});
```

### Acceptable Uses

Snapshot tests are acceptable only for:

1. **Serialized data structures** (API request bodies, configuration objects).
2. **Error messages** (to catch unintended changes in user-facing text).

```typescript
// OK: Snapshot of a serialized data structure
it('generates the correct API request body', () => {
  const body = buildCreateUserRequest({ name: 'Jane', email: 'jane@test.com' });
  expect(body).toMatchInlineSnapshot(`
    {
      "email": "jane@test.com",
      "name": "Jane",
      "role": "viewer",
    }
  `);
});
```

Prefer inline snapshots (`toMatchInlineSnapshot`) over file snapshots when using snapshots, so the expected value is visible in the test.

---

## Integration Test Patterns

### Feature-Level Integration Tests

Write integration tests that exercise a full user flow through a feature, hitting real component rendering, hooks, and (mocked) API calls.

```typescript
// features/users/UserManagement.integration.test.tsx
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { renderWithProviders } from '@/test/utils/render';
import { createUser } from '@/test/factories/user';
import { UsersPage } from './UsersPage';

describe('User Management', () => {
  it('allows creating a new user and seeing them in the list', async () => {
    const user = userEvent.setup();
    const existingUsers = [createUser({ name: 'Alice' })];
    const newUser = createUser({ name: 'Bob', email: 'bob@test.com' });

    // Setup API mocks
    server.use(
      http.get('/api/users', () => HttpResponse.json(existingUsers)),
      http.post('/api/users', () => HttpResponse.json(newUser, { status: 201 })),
    );

    renderWithProviders(<UsersPage />, { initialRoute: '/users' });

    // Wait for the list to load
    expect(await screen.findByText('Alice')).toBeInTheDocument();

    // Click "Add User" button
    await user.click(screen.getByRole('button', { name: /add user/i }));

    // Fill out the form
    await user.type(screen.getByLabelText(/name/i), 'Bob');
    await user.type(screen.getByLabelText(/email/i), 'bob@test.com');
    await user.selectOptions(screen.getByLabelText(/role/i), 'viewer');

    // Update mock to return both users after creation
    server.use(
      http.get('/api/users', () => HttpResponse.json([...existingUsers, newUser])),
    );

    // Submit the form
    await user.click(screen.getByRole('button', { name: /create/i }));

    // Verify the new user appears in the list
    expect(await screen.findByText('Bob')).toBeInTheDocument();
  });

  it('shows validation errors for invalid input', async () => {
    const user = userEvent.setup();

    server.use(
      http.get('/api/users', () => HttpResponse.json([])),
    );

    renderWithProviders(<UsersPage />, { initialRoute: '/users' });

    await user.click(await screen.findByRole('button', { name: /add user/i }));
    await user.click(screen.getByRole('button', { name: /create/i }));

    expect(await screen.findByText(/name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/email is required/i)).toBeInTheDocument();
  });
});
```

---

## Accessibility Testing

### Automated axe-core Checks

Run axe-core accessibility checks on every component test. This catches low-hanging accessibility violations (missing alt text, invalid ARIA, color contrast, etc.).

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

describe('UserCard', () => {
  it('has no accessibility violations', async () => {
    const { container } = render(<UserCard user={createUser()} />);

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});

// For components with multiple states, test each state
describe('LoginForm', () => {
  it('has no accessibility violations in default state', async () => {
    const { container } = render(<LoginForm onSubmit={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations with error state', async () => {
    const user = userEvent.setup();
    const { container } = render(<LoginForm onSubmit={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /log in/i }));

    expect(await axe(container)).toHaveNoViolations();
  });
});
```

### Manual Accessibility Assertions

In addition to automated checks, explicitly verify key accessibility features.

```typescript
it('associates form labels with inputs', () => {
  render(<LoginForm onSubmit={vi.fn()} />);

  // getByLabelText will throw if the label-input association is broken
  expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
});

it('marks invalid fields with aria-invalid', async () => {
  const user = userEvent.setup();
  render(<LoginForm onSubmit={vi.fn()} />);

  await user.click(screen.getByRole('button', { name: /log in/i }));

  expect(screen.getByLabelText(/email/i)).toHaveAttribute('aria-invalid', 'true');
});

it('announces errors with role="alert"', async () => {
  const user = userEvent.setup();
  render(<LoginForm onSubmit={vi.fn()} />);

  await user.click(screen.getByRole('button', { name: /log in/i }));

  const alerts = screen.getAllByRole('alert');
  expect(alerts.length).toBeGreaterThan(0);
});
```

---

## Coverage Expectations

### Minimum Coverage by File Type

| File Type | Line Coverage | Branch Coverage | Notes |
|-----------|:------------:|:--------------:|-------|
| Utility functions | 95% | 90% | Pure logic, easy to test exhaustively |
| Custom hooks | 90% | 85% | Test all state transitions and edge cases |
| API modules | 85% | 80% | Test success, error, and edge cases |
| Components (presentation) | 85% | 80% | Test rendering, interactions, states |
| Components (container) | 75% | 70% | Integration coverage fills gaps |
| Type files | N/A | N/A | Types have no runtime code |
| Configuration files | N/A | N/A | Not worth unit testing |

### What to Cover

1. All happy paths.
2. All error states (API failures, validation errors, empty data).
3. Edge cases (empty arrays, null values, boundary values).
4. User interactions (click, type, keyboard navigation).
5. Accessibility requirements (labels, ARIA, focus management).

### What NOT to Cover

1. Third-party library internals (React, React Query, etc.).
2. Trivial pass-through components with no logic.
3. CSS/styling details (use visual regression tools for that).
4. Implementation details (internal state names, number of re-renders).

### Enforcing Coverage

Configure Vitest to enforce minimum coverage thresholds in CI.

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      thresholds: {
        statements: 80,
        branches: 75,
        functions: 80,
        lines: 80,
      },
      exclude: [
        'node_modules/',
        'test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/types.ts',
        '**/index.ts', // Barrel exports
      ],
    },
  },
});
```
