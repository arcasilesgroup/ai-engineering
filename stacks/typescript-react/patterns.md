# TypeScript/React Recommended Patterns

These patterns are the preferred approaches for common problems in TypeScript/React applications. Follow these patterns unless a project-specific override is documented.

---

## Table of Contents

- [Custom Hooks](#custom-hooks)
- [Composition Patterns](#composition-patterns)
- [Container and Presentation Split](#container-and-presentation-split)
- [Context Patterns](#context-patterns)
- [Error Handling Patterns](#error-handling-patterns)
- [Data Fetching Patterns](#data-fetching-patterns)
- [Event Handling Patterns](#event-handling-patterns)
- [Routing Patterns](#routing-patterns)

---

## Custom Hooks

### Data Fetching Hook

Wrap React Query or SWR into domain-specific hooks that encapsulate query keys, fetcher logic, and return types.

```typescript
// features/users/hooks/use-user.ts
import { useQuery } from '@tanstack/react-query';
import { usersApi } from '../api/users-api';

import type { User } from '../types';

interface UseUserOptions {
  enabled?: boolean;
}

interface UseUserReturn {
  user: User | undefined;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useUser(id: string, options: UseUserOptions = {}): UseUserReturn {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['users', 'detail', id],
    queryFn: () => usersApi.getUser(id),
    enabled: options.enabled ?? true,
  });

  return {
    user: data,
    isLoading,
    error: error as Error | null,
    refetch: async () => { await refetch(); },
  };
}
```

### Form State Hook

Encapsulate form logic in a custom hook to separate form behavior from presentation.

```typescript
// features/users/hooks/use-create-user-form.ts
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CreateUserSchema } from '../types';
import { usersApi } from '../api/users-api';

import type { z } from 'zod';
import type { UseFormReturn } from 'react-hook-form';

type CreateUserFormData = z.infer<typeof CreateUserSchema>;

interface UseCreateUserFormReturn {
  form: UseFormReturn<CreateUserFormData>;
  onSubmit: () => void;
  isSubmitting: boolean;
  submitError: Error | null;
}

export function useCreateUserForm(options?: {
  onSuccess?: () => void;
}): UseCreateUserFormReturn {
  const queryClient = useQueryClient();

  const form = useForm<CreateUserFormData>({
    resolver: zodResolver(CreateUserSchema),
    defaultValues: {
      name: '',
      email: '',
      role: 'viewer',
    },
  });

  const mutation = useMutation({
    mutationFn: usersApi.createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', 'list'] });
      form.reset();
      options?.onSuccess?.();
    },
  });

  const onSubmit = form.handleSubmit((data) => {
    mutation.mutate(data);
  });

  return {
    form,
    onSubmit,
    isSubmitting: mutation.isPending,
    submitError: mutation.error as Error | null,
  };
}
```

### Debounce Hook

Use a debounce hook for search inputs, resize handlers, and other high-frequency events.

```typescript
// shared/hooks/use-debounced-value.ts
import { useState, useEffect } from 'react';

export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delayMs);

    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debouncedValue;
}

// Usage in a search component
function SearchPage(): React.ReactElement {
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearch = useDebouncedValue(searchTerm, 300);
  const { results, isLoading } = useSearch(debouncedSearch);

  return (
    <div>
      <input
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        placeholder="Search..."
      />
      {isLoading ? <Spinner /> : <ResultsList results={results} />}
    </div>
  );
}
```

### Intersection Observer Hook

Use for lazy loading, infinite scroll, and visibility tracking.

```typescript
// shared/hooks/use-intersection-observer.ts
import { useState, useEffect, useRef } from 'react';

interface UseIntersectionObserverOptions {
  threshold?: number;
  rootMargin?: string;
  triggerOnce?: boolean;
}

interface UseIntersectionObserverReturn {
  ref: React.RefObject<HTMLElement | null>;
  isIntersecting: boolean;
  entry: IntersectionObserverEntry | null;
}

export function useIntersectionObserver(
  options: UseIntersectionObserverOptions = {},
): UseIntersectionObserverReturn {
  const { threshold = 0, rootMargin = '0px', triggerOnce = false } = options;
  const ref = useRef<HTMLElement | null>(null);
  const [isIntersecting, setIsIntersecting] = useState(false);
  const [entry, setEntry] = useState<IntersectionObserverEntry | null>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([observerEntry]) => {
        if (!observerEntry) return;
        setIsIntersecting(observerEntry.isIntersecting);
        setEntry(observerEntry);

        if (triggerOnce && observerEntry.isIntersecting) {
          observer.unobserve(element);
        }
      },
      { threshold, rootMargin },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [threshold, rootMargin, triggerOnce]);

  return { ref, isIntersecting, entry };
}

// Usage: Infinite scroll
function UserList(): React.ReactElement {
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteUserList();
  const { ref, isIntersecting } = useIntersectionObserver({ rootMargin: '200px' });

  useEffect(() => {
    if (isIntersecting && hasNextPage) {
      fetchNextPage();
    }
  }, [isIntersecting, hasNextPage, fetchNextPage]);

  return (
    <div>
      {data?.pages.flatMap((page) =>
        page.users.map((user) => <UserCard key={user.id} user={user} />),
      )}
      <div ref={ref as React.RefObject<HTMLDivElement>}>
        {isFetchingNextPage && <Spinner />}
      </div>
    </div>
  );
}
```

### Local Storage Hook

Type-safe local storage with JSON serialization and SSR safety.

```typescript
// shared/hooks/use-local-storage.ts
import { useState, useCallback, useEffect } from 'react';

export function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, (value: T | ((prev: T) => T)) => void, () => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') return initialValue;
    try {
      const item = window.localStorage.getItem(key);
      return item ? (JSON.parse(item) as T) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStoredValue((prev) => {
        const nextValue = value instanceof Function ? value(prev) : value;
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(key, JSON.stringify(nextValue));
        }
        return nextValue;
      });
    },
    [key],
  );

  const removeValue = useCallback(() => {
    setStoredValue(initialValue);
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(key);
    }
  }, [key, initialValue]);

  // Sync across tabs
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent): void => {
      if (e.key === key && e.newValue !== null) {
        setStoredValue(JSON.parse(e.newValue) as T);
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [key]);

  return [storedValue, setValue, removeValue];
}
```

### Media Query Hook

```typescript
// shared/hooks/use-media-query.ts
import { useState, useEffect } from 'react';

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    const handler = (event: MediaQueryListEvent): void => {
      setMatches(event.matches);
    };

    mediaQuery.addEventListener('change', handler);
    setMatches(mediaQuery.matches);

    return () => mediaQuery.removeEventListener('change', handler);
  }, [query]);

  return matches;
}

// Usage
function Sidebar(): React.ReactElement {
  const isMobile = useMediaQuery('(max-width: 768px)');

  if (isMobile) {
    return <MobileDrawer />;
  }

  return <DesktopSidebar />;
}
```

---

## Composition Patterns

### Compound Components

Use compound components when building complex UI widgets that share implicit state (tabs, accordions, selects, menus).

```typescript
// shared/components/Tabs/Tabs.tsx
import { createContext, useContext, useState, useCallback } from 'react';

interface TabsContextValue {
  activeTab: string;
  setActiveTab: (id: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabsContext(): TabsContextValue {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error('Tabs compound components must be used within a Tabs provider');
  }
  return context;
}

// Root component
interface TabsProps {
  defaultTab: string;
  onChange?: (tabId: string) => void;
  children: React.ReactNode;
}

export function Tabs({ defaultTab, onChange, children }: TabsProps): React.ReactElement {
  const [activeTab, setActiveTabState] = useState(defaultTab);

  const setActiveTab = useCallback(
    (id: string) => {
      setActiveTabState(id);
      onChange?.(id);
    },
    [onChange],
  );

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      <div role="tablist">{children}</div>
    </TabsContext.Provider>
  );
}

// Tab trigger
interface TabProps {
  id: string;
  children: React.ReactNode;
}

function Tab({ id, children }: TabProps): React.ReactElement {
  const { activeTab, setActiveTab } = useTabsContext();
  const isActive = activeTab === id;

  return (
    <button
      role="tab"
      aria-selected={isActive}
      aria-controls={`tabpanel-${id}`}
      onClick={() => setActiveTab(id)}
    >
      {children}
    </button>
  );
}

// Tab panel
interface TabPanelProps {
  id: string;
  children: React.ReactNode;
}

function TabPanel({ id, children }: TabPanelProps): React.ReactElement | null {
  const { activeTab } = useTabsContext();

  if (activeTab !== id) return null;

  return (
    <div role="tabpanel" id={`tabpanel-${id}`} aria-labelledby={`tab-${id}`}>
      {children}
    </div>
  );
}

// Attach sub-components
Tabs.Tab = Tab;
Tabs.Panel = TabPanel;

// Usage:
// <Tabs defaultTab="general">
//   <Tabs.Tab id="general">General</Tabs.Tab>
//   <Tabs.Tab id="security">Security</Tabs.Tab>
//   <Tabs.Panel id="general"><GeneralSettings /></Tabs.Panel>
//   <Tabs.Panel id="security"><SecuritySettings /></Tabs.Panel>
// </Tabs>
```

### Render Props

Use render props when a component needs to share behavior but the consumer controls the rendering. This pattern is less common now that hooks exist, but remains useful for components that need to inject behavior into the render tree.

```typescript
// shared/components/Virtualizer.tsx
interface VirtualizerProps<T> {
  items: T[];
  itemHeight: number;
  containerHeight: number;
  children: (item: T, index: number, style: React.CSSProperties) => React.ReactElement;
}

export function Virtualizer<T>({
  items,
  itemHeight,
  containerHeight,
  children,
}: VirtualizerProps<T>): React.ReactElement {
  const [scrollTop, setScrollTop] = useState(0);

  const startIndex = Math.floor(scrollTop / itemHeight);
  const endIndex = Math.min(
    startIndex + Math.ceil(containerHeight / itemHeight) + 1,
    items.length,
  );

  const visibleItems = items.slice(startIndex, endIndex);

  return (
    <div
      style={{ height: containerHeight, overflow: 'auto' }}
      onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
    >
      <div style={{ height: items.length * itemHeight, position: 'relative' }}>
        {visibleItems.map((item, i) => {
          const actualIndex = startIndex + i;
          const style: React.CSSProperties = {
            position: 'absolute',
            top: actualIndex * itemHeight,
            height: itemHeight,
            width: '100%',
          };
          return children(item, actualIndex, style);
        })}
      </div>
    </div>
  );
}

// Usage:
// <Virtualizer items={users} itemHeight={60} containerHeight={400}>
//   {(user, index, style) => (
//     <div key={user.id} style={style}>
//       <UserRow user={user} />
//     </div>
//   )}
// </Virtualizer>
```

### Higher-Order Components (When Appropriate)

HOCs are rarely needed in modern React. Use them only when you must wrap a component's behavior transparently, especially when working with external libraries that expect specific component shapes.

```typescript
// shared/hocs/with-error-boundary.tsx
import { ErrorBoundary } from '@/shared/components/ErrorBoundary';

interface WithErrorBoundaryOptions {
  fallback: React.ReactNode;
  onError?: (error: Error) => void;
}

export function withErrorBoundary<TProps extends object>(
  Component: React.ComponentType<TProps>,
  options: WithErrorBoundaryOptions,
): React.ComponentType<TProps> {
  function WrappedComponent(props: TProps): React.ReactElement {
    return (
      <ErrorBoundary fallback={options.fallback} onError={options.onError}>
        <Component {...props} />
      </ErrorBoundary>
    );
  }

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName ?? Component.name ?? 'Component'})`;

  return WrappedComponent;
}

// Usage:
// export const SafeAnalyticsWidget = withErrorBoundary(AnalyticsWidget, {
//   fallback: <WidgetError />,
//   onError: (error) => reportError(error),
// });
```

### Slot Pattern

Use the slot pattern for layout components that accept named sections.

```typescript
// shared/components/PageLayout.tsx
interface PageLayoutProps {
  header: React.ReactNode;
  sidebar?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export function PageLayout({
  header,
  sidebar,
  children,
  footer,
}: PageLayoutProps): React.ReactElement {
  return (
    <div className="page-layout">
      <header className="page-header">{header}</header>
      <div className="page-body">
        {sidebar && <aside className="page-sidebar">{sidebar}</aside>}
        <main className="page-content">{children}</main>
      </div>
      {footer && <footer className="page-footer">{footer}</footer>}
    </div>
  );
}

// Usage:
// <PageLayout
//   header={<Breadcrumbs items={crumbs} />}
//   sidebar={<FilterPanel filters={filters} />}
//   footer={<Pagination page={page} total={total} />}
// >
//   <UserTable users={users} />
// </PageLayout>
```

---

## Container and Presentation Split

### When to Split

Split container and presentation components when:

1. The same data presentation is used with different data sources.
2. Complex data fetching and transformation logic obscures the UI code.
3. You want to test the presentation in isolation (e.g., with Storybook).

Do NOT split dogmatically. If a component is simple and self-contained, keeping everything in one file is fine.

### Pattern

```typescript
// Container: handles data, state, side effects
// features/users/components/UserProfileContainer.tsx
export function UserProfileContainer({ userId }: { userId: string }): React.ReactElement {
  const { user, isLoading, error } = useUser(userId);
  const { updateUser, isUpdating } = useUpdateUser();
  const navigate = useNavigate();

  const handleUpdate = async (data: UpdateUserInput): Promise<void> => {
    await updateUser(userId, data);
    navigate('/users');
  };

  if (isLoading) return <UserProfileSkeleton />;
  if (error) return <ErrorDisplay error={error} retry={() => window.location.reload()} />;
  if (!user) return <NotFound resource="user" />;

  return (
    <UserProfile
      user={user}
      onUpdate={handleUpdate}
      isUpdating={isUpdating}
    />
  );
}

// Presentation: pure rendering, no side effects
// features/users/components/UserProfile.tsx
interface UserProfileProps {
  user: User;
  onUpdate: (data: UpdateUserInput) => Promise<void>;
  isUpdating: boolean;
}

export function UserProfile({ user, onUpdate, isUpdating }: UserProfileProps): React.ReactElement {
  return (
    <section className="user-profile">
      <div className="user-header">
        <img src={user.avatar} alt="" className="avatar" />
        <h1>{user.name}</h1>
        <p>{user.email}</p>
      </div>

      <UserEditForm
        defaultValues={user}
        onSubmit={onUpdate}
        isSubmitting={isUpdating}
      />
    </section>
  );
}
```

---

## Context Patterns

### Separate Contexts for Separate Concerns

Never put unrelated state in the same context. Split by domain to minimize unnecessary re-renders.

```typescript
// DO: Separate contexts
// AuthContext — user, login, logout
// ThemeContext — theme, toggleTheme
// NotificationContext — notifications, addNotification, dismissNotification

// DON'T: God context
// AppContext — user, theme, notifications, sidebar, modal, ...
```

### Context with Reducer

For contexts with complex state transitions, combine context with useReducer.

```typescript
// features/notifications/NotificationContext.tsx
interface Notification {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
}

interface NotificationState {
  notifications: Notification[];
}

type NotificationAction =
  | { type: 'ADD'; notification: Notification }
  | { type: 'DISMISS'; id: string }
  | { type: 'CLEAR_ALL' };

function notificationReducer(
  state: NotificationState,
  action: NotificationAction,
): NotificationState {
  switch (action.type) {
    case 'ADD':
      return {
        notifications: [...state.notifications, action.notification],
      };
    case 'DISMISS':
      return {
        notifications: state.notifications.filter((n) => n.id !== action.id),
      };
    case 'CLEAR_ALL':
      return { notifications: [] };
    default: {
      const _exhaustive: never = action;
      return _exhaustive;
    }
  }
}

interface NotificationContextValue {
  notifications: Notification[];
  addNotification: (type: Notification['type'], message: string) => void;
  dismissNotification: (id: string) => void;
  clearAll: () => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function useNotifications(): NotificationContextValue {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
}

export function NotificationProvider({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const [state, dispatch] = useReducer(notificationReducer, { notifications: [] });

  const addNotification = useCallback(
    (type: Notification['type'], message: string) => {
      const id = crypto.randomUUID();
      dispatch({ type: 'ADD', notification: { id, type, message } });

      // Auto-dismiss after 5 seconds
      setTimeout(() => {
        dispatch({ type: 'DISMISS', id });
      }, 5000);
    },
    [],
  );

  const dismissNotification = useCallback((id: string) => {
    dispatch({ type: 'DISMISS', id });
  }, []);

  const clearAll = useCallback(() => {
    dispatch({ type: 'CLEAR_ALL' });
  }, []);

  const value = useMemo<NotificationContextValue>(
    () => ({
      notifications: state.notifications,
      addNotification,
      dismissNotification,
      clearAll,
    }),
    [state.notifications, addNotification, dismissNotification, clearAll],
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}
```

### Split Read and Write Contexts

For high-frequency read scenarios, separate the state (read) from the dispatch (write) to prevent re-renders in components that only dispatch.

```typescript
// State context (triggers re-render on state change)
const CountStateContext = createContext<number>(0);

// Dispatch context (stable reference, no re-render)
const CountDispatchContext = createContext<React.Dispatch<CountAction>>(() => {
  throw new Error('CountDispatchContext not provided');
});

export function useCountState(): number {
  return useContext(CountStateContext);
}

export function useCountDispatch(): React.Dispatch<CountAction> {
  return useContext(CountDispatchContext);
}

export function CountProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [state, dispatch] = useReducer(countReducer, 0);

  return (
    <CountStateContext.Provider value={state}>
      <CountDispatchContext.Provider value={dispatch}>
        {children}
      </CountDispatchContext.Provider>
    </CountStateContext.Provider>
  );
}
```

### Provider Composition

Avoid deeply nested providers by composing them in a single `AppProviders` component.

```typescript
// app/providers.tsx
export function AppProviders({ children }: { children: React.ReactNode }): React.ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ThemeProvider>
          <NotificationProvider>
            {children}
          </NotificationProvider>
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

// If nesting gets deep, use a compose helper:
function composeProviders(
  ...providers: Array<React.ComponentType<{ children: React.ReactNode }>>
): React.ComponentType<{ children: React.ReactNode }> {
  return function ComposedProviders({ children }: { children: React.ReactNode }) {
    return providers.reduceRight(
      (acc, Provider) => <Provider>{acc}</Provider>,
      children,
    ) as React.ReactElement;
  };
}

export const AppProviders = composeProviders(
  QueryClientProvider as React.ComponentType<{ children: React.ReactNode }>,
  AuthProvider,
  ThemeProvider,
  NotificationProvider,
);
```

---

## Error Handling Patterns

### Result Type for Operations That Can Fail

Use a Result type for functions that have expected failure modes. Throw exceptions only for truly unexpected errors.

```typescript
// shared/types/result.ts
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

function ok<T>(value: T): Result<T, never> {
  return { ok: true, value };
}

function err<E>(error: E): Result<never, E> {
  return { ok: false, error };
}

// Usage in API layer
async function createUser(input: CreateUserInput): Promise<Result<User, ApiError>> {
  try {
    const user = await api.post<User>('/users', input);
    return ok(user);
  } catch (error) {
    if (error instanceof ApiRequestError) {
      return err({
        code: error.code,
        message: error.message,
        status: error.status,
      });
    }
    throw error; // Re-throw unexpected errors
  }
}

// Usage in component
const handleSubmit = async (data: CreateUserInput): Promise<void> => {
  const result = await createUser(data);

  if (!result.ok) {
    if (result.error.code === 'DUPLICATE_EMAIL') {
      form.setError('email', { message: 'This email is already registered' });
    } else {
      addNotification('error', result.error.message);
    }
    return;
  }

  addNotification('success', `Created user ${result.value.name}`);
  navigate('/users');
};
```

### Error Boundaries with Recovery

Provide recovery actions in error boundary fallbacks.

```typescript
// DO: Actionable error UI
function FeatureErrorFallback({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}): React.ReactElement {
  return (
    <div role="alert" className="error-panel">
      <h2>Something went wrong</h2>
      <p>{error.message}</p>
      <div className="error-actions">
        <button onClick={reset}>Try again</button>
        <button onClick={() => window.location.reload()}>Reload page</button>
      </div>
      {import.meta.env.DEV && (
        <pre className="error-stack">{error.stack}</pre>
      )}
    </div>
  );
}
```

### Async Error Handling in Effects

Always catch errors in async operations inside useEffect. Uncaught promise rejections crash the app without useful error messages.

```typescript
// DO: Handle errors in effects
useEffect(() => {
  const controller = new AbortController();

  async function loadData(): Promise<void> {
    try {
      const data = await fetchData(id, { signal: controller.signal });
      setData(data);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return; // Component unmounted, ignore
      }
      setError(error instanceof Error ? error : new Error('Unknown error'));
    }
  }

  loadData();
  return () => controller.abort();
}, [id]);

// DON'T: Unhandled promise in effect
useEffect(() => {
  fetchData(id).then(setData); // No error handling, no cleanup
}, [id]);
```

### Global Error Handler

Set up a global error handler for unhandled errors and promise rejections.

```typescript
// app/error-handler.ts
export function setupGlobalErrorHandler(): void {
  window.addEventListener('error', (event) => {
    reportError({
      type: 'unhandled_error',
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error?.stack,
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    reportError({
      type: 'unhandled_rejection',
      message: event.reason?.message ?? 'Unknown promise rejection',
      stack: event.reason?.stack,
    });
  });
}

function reportError(errorInfo: Record<string, unknown>): void {
  // Send to error tracking service (Sentry, etc.)
  console.error('[Global Error]', errorInfo);
}
```

---

## Data Fetching Patterns

### React Query Configuration

Set up React Query with sensible defaults.

```typescript
// shared/api/query-client.ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,        // 5 minutes
      gcTime: 10 * 60 * 1000,           // 10 minutes (formerly cacheTime)
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30_000),
      refetchOnWindowFocus: false,       // Enable per-query if needed
    },
    mutations: {
      retry: 0,
    },
  },
});
```

### Query Key Factory

Use a factory pattern for query keys to ensure consistency and enable targeted invalidation.

```typescript
// features/users/api/query-keys.ts
export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (filters: UserFilters) => [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, 'detail'] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
};

// Invalidation examples:
// queryClient.invalidateQueries({ queryKey: userKeys.all });        // Everything
// queryClient.invalidateQueries({ queryKey: userKeys.lists() });    // All lists
// queryClient.invalidateQueries({ queryKey: userKeys.detail(id) }); // Specific user
```

### Optimistic Updates

Apply optimistic updates for operations where the expected outcome is highly predictable (toggles, increments, simple edits).

```typescript
// features/todos/hooks/use-toggle-todo.ts
export function useToggleTodo(): {
  toggleTodo: (id: string) => void;
} {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (id: string) => todosApi.toggle(id),

    onMutate: async (id: string) => {
      // Cancel ongoing fetches
      await queryClient.cancelQueries({ queryKey: todoKeys.lists() });

      // Snapshot previous state
      const previousTodos = queryClient.getQueryData<Todo[]>(todoKeys.lists());

      // Optimistically update
      queryClient.setQueryData<Todo[]>(todoKeys.lists(), (old) =>
        old?.map((todo) =>
          todo.id === id ? { ...todo, completed: !todo.completed } : todo,
        ),
      );

      return { previousTodos };
    },

    onError: (_error, _id, context) => {
      // Roll back on error
      if (context?.previousTodos) {
        queryClient.setQueryData(todoKeys.lists(), context.previousTodos);
      }
    },

    onSettled: () => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: todoKeys.lists() });
    },
  });

  return {
    toggleTodo: (id: string) => mutation.mutate(id),
  };
}
```

### Prefetching

Prefetch data on hover or when navigation is likely.

```typescript
// Prefetch on hover
function UserLink({ userId, children }: { userId: string; children: React.ReactNode }): React.ReactElement {
  const queryClient = useQueryClient();

  const handleMouseEnter = (): void => {
    queryClient.prefetchQuery({
      queryKey: userKeys.detail(userId),
      queryFn: () => usersApi.getUser(userId),
      staleTime: 60_000,
    });
  };

  return (
    <Link to={`/users/${userId}`} onMouseEnter={handleMouseEnter}>
      {children}
    </Link>
  );
}
```

---

## Event Handling Patterns

### Type-Safe Event Handlers

Always type event parameters explicitly.

```typescript
// DO: Explicit event types
function SearchForm({ onSearch }: { onSearch: (term: string) => void }): React.ReactElement {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const term = formData.get('search') as string;
    onSearch(term);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    // Handle change
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Escape') {
      e.currentTarget.blur();
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="search" onChange={handleChange} onKeyDown={handleKeyDown} />
    </form>
  );
}
```

### Event Cleanup

Always clean up event listeners in useEffect.

```typescript
// DO: Clean up listeners
useEffect(() => {
  const handleResize = (): void => {
    setWindowWidth(window.innerWidth);
  };

  window.addEventListener('resize', handleResize);
  return () => window.removeEventListener('resize', handleResize);
}, []);

// DO: Use AbortController for multiple listeners
useEffect(() => {
  const controller = new AbortController();

  window.addEventListener('resize', handleResize, { signal: controller.signal });
  window.addEventListener('scroll', handleScroll, { signal: controller.signal });
  document.addEventListener('keydown', handleKeyDown, { signal: controller.signal });

  return () => controller.abort();
}, []);
```

### Event Delegation

For lists with many interactive items, delegate events to the parent instead of attaching handlers to each child.

```typescript
// DO: Event delegation for large lists
function UserList({ users, onSelect }: UserListProps): React.ReactElement {
  const handleClick = (e: React.MouseEvent<HTMLUListElement>): void => {
    const target = (e.target as HTMLElement).closest<HTMLLIElement>('[data-user-id]');
    if (target) {
      const userId = target.dataset.userId;
      if (userId) {
        onSelect(userId);
      }
    }
  };

  return (
    <ul onClick={handleClick}>
      {users.map((user) => (
        <li key={user.id} data-user-id={user.id}>
          {user.name}
        </li>
      ))}
    </ul>
  );
}
```

---

## Routing Patterns

### Type-Safe Route Definitions

Define routes as a constant map with typed path parameters.

```typescript
// shared/routes.ts
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  USERS: '/users',
  USER_DETAIL: '/users/:userId',
  USER_EDIT: '/users/:userId/edit',
  SETTINGS: '/settings',
  SETTINGS_SECTION: '/settings/:section',
} as const;

// Type-safe path builder
export function buildPath(
  route: typeof ROUTES.USER_DETAIL,
  params: { userId: string },
): string;
export function buildPath(
  route: typeof ROUTES.SETTINGS_SECTION,
  params: { section: string },
): string;
export function buildPath(route: string, params?: Record<string, string>): string {
  if (!params) return route;
  return Object.entries(params).reduce(
    (path, [key, value]) => path.replace(`:${key}`, value),
    route,
  );
}

// Usage:
// buildPath(ROUTES.USER_DETAIL, { userId: '123' }) => '/users/123'
```

### Route Guards

Protect routes with authentication and authorization guards.

```typescript
// shared/components/AuthGuard.tsx
interface AuthGuardProps {
  children: React.ReactNode;
  requiredRole?: UserRole;
  fallback?: React.ReactNode;
}

export function AuthGuard({
  children,
  requiredRole,
  fallback,
}: AuthGuardProps): React.ReactElement {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <PageSkeleton />;
  }

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} state={{ from: location }} replace />;
  }

  if (requiredRole && user?.role !== requiredRole) {
    if (fallback) return <>{fallback}</>;
    return <ForbiddenPage />;
  }

  return <>{children}</>;
}

// Usage in route config:
// <Route
//   path={ROUTES.SETTINGS}
//   element={
//     <AuthGuard requiredRole="admin">
//       <SettingsPage />
//     </AuthGuard>
//   }
// />
```

### Layout Routes

Use layout routes to share UI structure across pages.

```typescript
// app/routes.tsx
import { Outlet } from 'react-router-dom';

function AuthenticatedLayout(): React.ReactElement {
  return (
    <AuthGuard>
      <div className="app-layout">
        <Header />
        <div className="app-body">
          <Sidebar />
          <main className="app-content">
            <Suspense fallback={<ContentSkeleton />}>
              <Outlet />
            </Suspense>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}

function PublicLayout(): React.ReactElement {
  return (
    <div className="public-layout">
      <Suspense fallback={<PageSkeleton />}>
        <Outlet />
      </Suspense>
    </div>
  );
}

export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      { path: ROUTES.LOGIN, element: <LoginPage /> },
      { path: ROUTES.HOME, element: <LandingPage /> },
    ],
  },
  {
    element: <AuthenticatedLayout />,
    children: [
      { path: ROUTES.DASHBOARD, element: <DashboardPage /> },
      { path: ROUTES.USERS, element: <UsersPage /> },
      { path: ROUTES.USER_DETAIL, element: <UserDetailPage /> },
      { path: ROUTES.SETTINGS, element: <SettingsPage /> },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
]);
```

### Typed Route Parameters

Use typed hooks for extracting route parameters.

```typescript
// shared/hooks/use-typed-params.ts
import { useParams } from 'react-router-dom';

export function useTypedParams<T extends Record<string, string>>(): T {
  return useParams() as T;
}

// Usage
interface UserDetailParams {
  userId: string;
}

function UserDetailPage(): React.ReactElement {
  const { userId } = useTypedParams<UserDetailParams>();
  const { user, isLoading } = useUser(userId);

  // ...
}
```

### Search Params State

Sync filter/pagination state with URL search parameters for shareable URLs and browser back/forward support.

```typescript
// shared/hooks/use-search-params-state.ts
import { useSearchParams } from 'react-router-dom';
import { useMemo, useCallback } from 'react';
import { z } from 'zod';

export function useSearchParamsState<T extends z.ZodObject<z.ZodRawShape>>(
  schema: T,
  defaults: z.infer<T>,
): [z.infer<T>, (updates: Partial<z.infer<T>>) => void] {
  const [searchParams, setSearchParams] = useSearchParams();

  const state = useMemo((): z.infer<T> => {
    const raw = Object.fromEntries(searchParams.entries());
    const result = schema.safeParse({ ...defaults, ...raw });
    return result.success ? result.data : defaults;
  }, [searchParams, schema, defaults]);

  const setState = useCallback(
    (updates: Partial<z.infer<T>>) => {
      setSearchParams((prev) => {
        const current = Object.fromEntries(prev.entries());
        const next = { ...current, ...updates };
        // Remove entries that match defaults
        for (const [key, value] of Object.entries(next)) {
          if (value === defaults[key] || value === undefined || value === '') {
            delete next[key];
          }
        }
        return new URLSearchParams(next as Record<string, string>);
      });
    },
    [setSearchParams, defaults],
  );

  return [state, setState];
}

// Usage
const FiltersSchema = z.object({
  search: z.string().default(''),
  role: z.enum(['all', 'admin', 'editor', 'viewer']).default('all'),
  page: z.coerce.number().default(1),
  limit: z.coerce.number().default(20),
});

function UsersPage(): React.ReactElement {
  const [filters, setFilters] = useSearchParamsState(FiltersSchema, {
    search: '',
    role: 'all',
    page: 1,
    limit: 20,
  });

  // Changing filters updates the URL: /users?search=john&role=admin&page=2
  return (
    <div>
      <input
        value={filters.search}
        onChange={(e) => setFilters({ search: e.target.value, page: 1 })}
      />
      <UserList filters={filters} />
    </div>
  );
}
```
