---
applyTo: "**/*.{ts,tsx}"
---

# TypeScript Coding Standards for Copilot

These instructions apply to all TypeScript and TSX files in this project. Follow these standards when generating or modifying code.

## Strict Mode

- `strict: true` must be enabled in tsconfig.json
- Never disable strict checks with `// @ts-ignore` or `// @ts-expect-error` without a documented reason
- Enable `strictNullChecks`, `noImplicitAny`, `noImplicitReturns`

## No `any`

Never use `any`. Use `unknown` with type guards instead.

```typescript
// WRONG
function process(data: any) { }

// CORRECT
function process(data: unknown): User | null {
  if (isUser(data)) {
    return data;
  }
  return null;
}

function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'name' in value
  );
}
```

## Explicit Return Types

All exported functions must have explicit return types.

```typescript
// CORRECT
export async function fetchUser(id: string): Promise<User | null> {
  const response = await api.get(`/users/${id}`);
  return response.data;
}

// Inferred types are acceptable for local/private functions
const transform = (data: RawData) => ({
  id: data.userId,
  name: data.fullName,
});
```

## Interfaces and Types

- Use `interface` for object shapes (extensible via declaration merging)
- Use `type` for unions, intersections, and mapped types
- Prefer union types over enums for tree-shakeability

```typescript
// Interface for object shapes
interface User {
  id: string;
  name: string;
  email: string;
}

// Type for unions
type Status = 'active' | 'inactive' | 'pending';
type UserWithRole = User & { role: string };

// Type for function signatures
type UserHandler = (user: User) => Promise<void>;
```

## React Component Patterns

### Functional Components with Typed Props

```typescript
interface UserCardProps {
  user: User;
  onSelect?: (user: User) => void;
  className?: string;
}

export function UserCard({ user, onSelect, className }: UserCardProps) {
  const handleClick = () => {
    onSelect?.(user);
  };

  return (
    <div className={className} onClick={handleClick}>
      <h3>{user.name}</h3>
      <p>{user.email}</p>
    </div>
  );
}
```

### Rules

- Always use functional components with hooks
- Define a dedicated props interface for every component
- Use `React.ReactNode` for children typing
- Destructure props in the function signature
- Do not nest component definitions inside other components
- Co-locate component, styles, tests, and types in a directory

## Hooks Patterns

- All custom hooks must be prefixed with `use`
- Return typed objects from hooks
- Handle cleanup in `useEffect` return functions
- Use `useMemo` and `useCallback` only when there is a measurable performance need

```typescript
export function useUser(userId: string) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function fetchUser() {
      try {
        setIsLoading(true);
        const data = await api.getUser(userId);
        if (!cancelled) {
          setUser(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }
    fetchUser();
    return () => { cancelled = true; };
  }, [userId]);

  return { user, isLoading, error };
}
```

## Naming Conventions

| Element       | Convention         | Example                              |
|--------------|--------------------|--------------------------------------|
| Files         | kebab-case         | `user-service.ts`, `use-auth.ts`     |
| Components    | PascalCase         | `UserProfile.tsx`                    |
| Interfaces    | PascalCase         | `UserResponse`, `ApiConfig`          |
| Types         | PascalCase         | `UserId`, `Status`                   |
| Functions     | camelCase          | `getUser`, `handleSubmit`            |
| Variables     | camelCase          | `userName`, `isLoading`              |
| Constants     | UPPER_SNAKE_CASE   | `API_BASE_URL`, `MAX_RETRIES`        |

## Imports

Organize imports in this order:
1. External libraries
2. Internal modules (absolute imports with `@/`)
3. Relative imports
4. Styles

Use `import type` for type-only imports:

```typescript
import type { User, UserResponse } from './types';
import { fetchUser } from './api';
```

## Null Handling

- Use optional chaining: `user?.profile?.name`
- Use nullish coalescing: `value ?? defaultValue`
- Avoid non-null assertions (`!`) unless you have certainty
- Use strict null checks throughout

## Error Handling

Use a Result pattern similar to .NET:

```typescript
interface Result<T> {
  success: boolean;
  data?: T;
  error?: string;
}

async function fetchData(): Promise<Result<Data>> {
  try {
    const response = await api.get('/data');
    return { success: true, data: response.data };
  } catch (error) {
    if (error instanceof ApiError) {
      return { success: false, error: error.message };
    }
    return { success: false, error: 'Unknown error occurred' };
  }
}
```

## Vitest Testing

- Test framework: Vitest with React Testing Library
- Test files co-located with source: `Component.test.tsx`, `hook.test.ts`
- Use `describe` for grouping, `it` for individual tests
- Test behavior, not implementation details
- Use `screen` queries (`getByRole`, `getByText`) over `getByTestId`
- Prefer `userEvent` over `fireEvent`
- Clean up mocks in `afterEach`

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserCard } from './UserCard';

describe('UserCard', () => {
  const mockUser = { id: '1', name: 'John Doe', email: 'john@example.com' };

  it('renders user name', () => {
    render(<UserCard user={mockUser} />);
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('calls onSelect when clicked', async () => {
    const onSelect = vi.fn();
    render(<UserCard user={mockUser} onSelect={onSelect} />);

    await userEvent.click(screen.getByRole('button'));

    expect(onSelect).toHaveBeenCalledWith(mockUser);
  });
});
```

## ESLint Compliance

- Follow project ESLint configuration
- Do not suppress rules without documented justification
- Do not mix default and named exports in the same file
- Avoid `// @ts-ignore` -- fix the type instead

## Security

- Never hardcode secrets, API keys, or tokens
- Validate all external inputs
- Sanitize data before rendering to prevent XSS
- Use environment variables for configuration
- Never log sensitive data
