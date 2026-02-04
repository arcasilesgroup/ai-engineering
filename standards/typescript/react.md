# React Standards

> Patterns and conventions for React with TypeScript.

---

## Component Structure

### Functional Components

```typescript
// ✅ PREFERRED: Function declaration with typed props
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

### File Naming

```
components/
├── UserCard/
│   ├── index.ts              # Re-export
│   ├── UserCard.tsx          # Component
│   ├── UserCard.test.tsx     # Tests
│   ├── UserCard.module.css   # Styles
│   └── types.ts              # Local types
├── ui/
│   ├── Button.tsx
│   └── Input.tsx
└── index.ts                   # Barrel export
```

---

## Props Patterns

### Required vs Optional

```typescript
interface ButtonProps {
  // Required props
  children: React.ReactNode;
  onClick: () => void;
  
  // Optional props with defaults
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  className?: string;
}

export function Button({
  children,
  onClick,
  variant = 'primary',
  disabled = false,
  className,
}: ButtonProps) {
  // ...
}
```

### Children Typing

```typescript
// For any valid React children
interface Props {
  children: React.ReactNode;
}

// For single element only
interface Props {
  children: React.ReactElement;
}

// For render prop pattern
interface Props {
  children: (data: Data) => React.ReactNode;
}
```

---

## Hooks

### Custom Hook Pattern

```typescript
// hooks/use-user.ts
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

    return () => {
      cancelled = true;
    };
  }, [userId]);

  return { user, isLoading, error };
}
```

### Hook Naming

```typescript
// ✅ Prefix with 'use'
useUser()
useAuth()
useLocalStorage()
useFetch()

// ❌ Wrong naming
getUser()
fetchAuth()
```

---

## State Management

### React Query (Server State)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Query
export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => api.getUsers(),
  });
}

// Mutation with cache invalidation
export function useCreateUser() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (newUser: CreateUserRequest) => api.createUser(newUser),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
```

### Local State (Zustand)

```typescript
import { create } from 'zustand';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  login: (user) => set({ user, isAuthenticated: true }),
  logout: () => set({ user: null, isAuthenticated: false }),
}));
```

---

## Event Handlers

### Typing Events

```typescript
// Form events
const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
  e.preventDefault();
  // ...
};

// Input events
const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  setValue(e.target.value);
};

// Click events
const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
  // ...
};

// Keyboard events
const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
  if (e.key === 'Enter') {
    // ...
  }
};
```

---

## Performance

### Memoization

```typescript
// ✅ useMemo for expensive computations
const sortedUsers = useMemo(
  () => users.sort((a, b) => a.name.localeCompare(b.name)),
  [users]
);

// ✅ useCallback for stable function references
const handleSelect = useCallback((user: User) => {
  onSelect(user);
}, [onSelect]);

// ✅ React.memo for pure components
export const UserCard = React.memo(function UserCard({ user }: Props) {
  return <div>{user.name}</div>;
});
```

### Lazy Loading

```typescript
import { lazy, Suspense } from 'react';

const UserProfile = lazy(() => import('./UserProfile'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <UserProfile userId={userId} />
    </Suspense>
  );
}
```

---

## Error Boundaries

```typescript
import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? <div>Something went wrong</div>;
    }
    return this.props.children;
  }
}
```

---

## Best Practices

### Do

- ✅ Use functional components with hooks
- ✅ Keep components small and focused
- ✅ Co-locate related files (component, styles, tests)
- ✅ Use TypeScript strict mode
- ✅ Handle loading and error states

### Don't

- ❌ Use `any` for props or state
- ❌ Mutate state directly
- ❌ Use index as key in dynamic lists
- ❌ Over-optimize with useMemo/useCallback
- ❌ Nest components inside components
