# TypeScript / React Standards

> Consolidated TypeScript and React standards: strict typing, component patterns, hooks, state management, styling, and testing.

---

## 1. TypeScript Configuration

### Strict Mode

Always enable strict mode in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "exactOptionalPropertyTypes": true
  }
}
```

### Avoid `any`, Use `unknown`

```typescript
// GOOD: Use unknown for truly unknown data
function parseApiResponse(data: unknown): User {
  if (!isUser(data)) {
    throw new Error("Invalid user data");
  }
  return data;
}

// GOOD: Type guard for runtime validation
function isUser(data: unknown): data is User {
  return (
    typeof data === "object" &&
    data !== null &&
    "id" in data &&
    "name" in data
  );
}

// BAD: Using any disables type checking
function parseApiResponse(data: any): User {
  return data; // No safety at all
}
```

### Explicit Return Types

Always declare return types on exported functions and public methods:

```typescript
// GOOD: Explicit return type
export function calculateTotal(items: CartItem[]): number {
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

// GOOD: Explicit return type on async functions
export async function fetchUser(id: string): Promise<User> {
  const response = await api.get(`/users/${id}`);
  return response.data;
}

// BAD: Missing return type on exported function
export function calculateTotal(items: CartItem[]) {
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}
```

### Interface vs Type

| Use | When |
|-----|------|
| `interface` | Object shapes, class contracts, extendable APIs |
| `type` | Unions, intersections, mapped types, primitives |

```typescript
// GOOD: Interface for object shapes (extendable)
interface User {
  id: string;
  name: string;
  email: string;
}

interface AdminUser extends User {
  permissions: Permission[];
}

// GOOD: Type for unions and computed types
type Status = "active" | "inactive" | "pending";
type UserOrAdmin = User | AdminUser;
type Readonly<T> = { readonly [K in keyof T]: T[K] };
```

---

## 2. React Component Patterns

### Functional Components with Props Typing

```typescript
// GOOD: Props interface with explicit typing
interface UserCardProps {
  user: User;
  onSelect: (userId: string) => void;
  variant?: "compact" | "full";
}

export function UserCard({ user, onSelect, variant = "full" }: UserCardProps): React.ReactElement {
  return (
    <div className={styles[variant]} onClick={() => onSelect(user.id)}>
      <h3>{user.name}</h3>
      {variant === "full" && <p>{user.email}</p>}
    </div>
  );
}
```

### Children Props

```typescript
// GOOD: Explicit children typing
interface LayoutProps {
  children: React.ReactNode;
  sidebar?: React.ReactNode;
}

export function Layout({ children, sidebar }: LayoutProps): React.ReactElement {
  return (
    <div className={styles.layout}>
      {sidebar && <aside>{sidebar}</aside>}
      <main>{children}</main>
    </div>
  );
}
```

### Component Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|-------------|---------|-----------------|
| `React.FC<Props>` | Implicit children, poor generic support | Typed function with explicit return |
| Props spreading `{...props}` | Unclear API surface | Destructure and pass explicitly |
| Inline object literals in JSX | Creates new reference each render | Extract to variable or `useMemo` |
| Business logic in components | Hard to test, violates SRP | Extract to custom hooks or utilities |
| Nested component definitions | Re-creates on every render | Define at module level |

---

## 3. Hooks Patterns

### Custom Hooks

```typescript
// GOOD: Custom hook with clear interface
interface UseUserReturn {
  user: User | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useUser(userId: string): UseUserReturn {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => fetchUser(userId),
    enabled: Boolean(userId),
  });

  return { user: data ?? null, isLoading, error, refetch };
}
```

### useEffect Cleanup

```typescript
// GOOD: Proper cleanup to avoid memory leaks
export function useWebSocket(url: string): WebSocketState {
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    const ws = new WebSocket(url);

    ws.onmessage = (event: MessageEvent) => {
      setMessages((prev) => [...prev, JSON.parse(event.data)]);
    };

    // Cleanup: close connection on unmount or URL change
    return () => {
      ws.close();
    };
  }, [url]);

  return { messages };
}

// GOOD: AbortController for fetch cleanup
useEffect(() => {
  const controller = new AbortController();

  fetchData(controller.signal).then(setData).catch((err) => {
    if (!controller.signal.aborted) setError(err);
  });

  return () => controller.abort();
}, [dependency]);
```

### Hooks Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|-------------|---------|-----------------|
| Missing dependency array | Runs on every render | Include all dependencies |
| Object/array in dependency array | Infinite re-renders | Use `useMemo` or primitives |
| Missing cleanup in useEffect | Memory leaks | Always return cleanup function |
| setState in useEffect without guard | Infinite loops | Add conditional or use ref |
| Calling hooks conditionally | Violates rules of hooks | Always call at top level |

---

## 4. State Management

### React Query (TanStack Query) for Server State

```typescript
// GOOD: Query with proper configuration
export function useUsers(filters: UserFilters): UseQueryResult<User[]> {
  return useQuery({
    queryKey: ["users", filters],
    queryFn: () => api.getUsers(filters),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

// GOOD: Mutation with optimistic update
export function useUpdateUser(): UseMutationResult<User, Error, UpdateUserInput> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.updateUser,
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(["user", updatedUser.id], updatedUser);
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });
}
```

### Zustand for Client State

```typescript
// GOOD: Typed Zustand store with actions
interface AppStore {
  theme: "light" | "dark";
  sidebarOpen: boolean;
  toggleTheme: () => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useAppStore = create<AppStore>((set) => ({
  theme: "light",
  sidebarOpen: true,
  toggleTheme: () => set((state) => ({ theme: state.theme === "light" ? "dark" : "light" })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
```

---

## 5. Styling

### CSS Modules

```typescript
// GOOD: CSS Modules with typed imports
import styles from "./user-card.module.css";

export function UserCard({ user }: UserCardProps): React.ReactElement {
  return <div className={styles.container}>{user.name}</div>;
}
```

### Tailwind CSS

```typescript
// GOOD: Tailwind with conditional classes via clsx
import { clsx } from "clsx";

export function Button({ variant, children, disabled }: ButtonProps): React.ReactElement {
  return (
    <button
      className={clsx(
        "rounded px-4 py-2 font-medium transition-colors",
        variant === "primary" && "bg-blue-600 text-white hover:bg-blue-700",
        variant === "secondary" && "bg-gray-200 text-gray-800 hover:bg-gray-300",
        disabled && "cursor-not-allowed opacity-50"
      )}
      disabled={disabled}
    >
      {children}
    </button>
  );
}
```

---

## 6. Testing with Vitest

### Test Structure

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { UserCard } from "./user-card";

describe("UserCard", () => {
  const mockUser: User = { id: "1", name: "Alice", email: "alice@example.com" };

  it("renders user name", () => {
    render(<UserCard user={mockUser} onSelect={vi.fn()} />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
  });

  it("calls onSelect with user ID when clicked", () => {
    const onSelect = vi.fn();
    render(<UserCard user={mockUser} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("Alice"));

    expect(onSelect).toHaveBeenCalledWith("1");
  });

  it("hides email in compact variant", () => {
    render(<UserCard user={mockUser} onSelect={vi.fn()} variant="compact" />);
    expect(screen.queryByText("alice@example.com")).not.toBeInTheDocument();
  });
});
```

### Testing Custom Hooks

```typescript
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

describe("useUser", () => {
  it("returns user data after loading", async () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useUser("1"), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toEqual(expect.objectContaining({ id: "1" }));
  });
});
```

---

## 7. ESLint Configuration

```json
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/strict-type-checked",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended"
  ],
  "rules": {
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/explicit-function-return-type": ["error", {
      "allowExpressions": true,
      "allowTypedFunctionExpressions": true
    }],
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
    "react/react-in-jsx-scope": "off",
    "react-hooks/exhaustive-deps": "error",
    "no-console": ["warn", { "allow": ["warn", "error"] }]
  }
}
```

---

## 8. Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Components | PascalCase | `UserCard`, `NavigationMenu` |
| Component files | kebab-case | `user-card.tsx`, `navigation-menu.tsx` |
| Hooks | camelCase with `use` prefix | `useUser`, `useLocalStorage` |
| Hook files | kebab-case | `use-user.ts`, `use-local-storage.ts` |
| Utilities | camelCase | `formatDate`, `calculateTotal` |
| Utility files | kebab-case | `format-date.ts`, `calculate-total.ts` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES`, `API_BASE_URL` |
| Types/Interfaces | PascalCase | `UserProfile`, `ApiResponse` |
| Enums | PascalCase (name + members) | `Status.Active`, `Role.Admin` |
| Test files | kebab-case with `.test` | `user-card.test.tsx` |
| CSS Modules | kebab-case with `.module` | `user-card.module.css` |

---

## 9. Project Structure

```
src/
  components/          # Shared/reusable components
    user-card/
      user-card.tsx
      user-card.test.tsx
      user-card.module.css
  features/            # Feature-based modules
    auth/
      components/
      hooks/
      services/
      types.ts
  hooks/               # Shared custom hooks
  services/            # API layer
  utils/               # Pure utility functions
  types/               # Shared type definitions
```
