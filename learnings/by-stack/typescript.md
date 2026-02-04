# TypeScript/React Learnings

Stack-specific learnings for TypeScript, React, and React Native development.

---

## React Components

### [2024-01] Always Set displayName

**Context:** Creating functional components
**Learning:** Set `Component.displayName = 'ComponentName'` for better debugging
**Rationale:** React DevTools shows `displayName` instead of anonymous function names

---

### [2024-01] Prefer Named Exports

**Context:** Exporting components and hooks
**Learning:** Use named exports over default exports
```typescript
// ✅ Preferred
export const UserCard: FC<UserCardProps> = () => { ... }

// ❌ Avoid
export default function UserCard() { ... }
```
**Rationale:** Better refactoring support, explicit imports, easier tree shaking

---

## Custom Hooks

### [2024-02] Return Objects for Complex Hooks

**Context:** Custom hooks with multiple return values
**Learning:** Return object instead of tuple when >2 values or values are often unused
```typescript
// ✅ Flexible usage
const { data, isLoading } = useApiData(url);

// ❌ Forces destructuring all values
const [data, isLoading, error, refetch] = useApiData(url);
```

---

### [2024-02] useCallback for Returned Functions

**Context:** Hooks that return functions
**Learning:** Always wrap returned functions in `useCallback` to maintain referential equality
**Consequence:** Without memoization, consumers may get infinite re-renders

---

## TypeScript Patterns

### [2024-01] Discriminated Unions for State

**Context:** Managing component state with multiple possibilities
**Learning:** Use discriminated unions over optional properties
```typescript
// ✅ Clear, type-safe
type State = 
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: User }
  | { status: 'error'; error: Error };

// ❌ Ambiguous
interface State {
  loading?: boolean;
  data?: User;
  error?: Error;
}
```

---

### [2024-01] Strict Null Checks

**Context:** Optional chaining and null handling
**Learning:** Always enable `strictNullChecks` in tsconfig.json
**Rationale:** Catches null/undefined errors at compile time

---

## Testing

### [2024-02] Testing Library Best Practices

**Context:** Writing React component tests
**Learning:** 
- Query by role/label first, testId last
- Use `userEvent` over `fireEvent` for realistic interactions
- Use `waitFor` for async assertions
```typescript
// ✅ Accessible query
screen.getByRole('button', { name: /submit/i })

// ❌ Fragile query
screen.getByTestId('submit-button')
```

---

### [2024-02] Mock at Boundaries

**Context:** Testing hooks with external dependencies
**Learning:** Mock at the service/API boundary, not internal functions
```typescript
// ✅ Mock the service
vi.mock('../../services/userService');

// ❌ Don't mock internal functions
vi.mock('../useUserState');
```

---

## Performance

### [2024-01] Avoid Inline Objects in JSX

**Context:** Passing objects as props
**Learning:** Define objects outside render or use `useMemo`
```typescript
// ❌ New object every render
<Component style={{ padding: 10 }} />

// ✅ Memoized
const style = useMemo(() => ({ padding: 10 }), []);
<Component style={style} />
```

---

### [2024-02] Lazy Loading for Large Components

**Context:** Code splitting
**Learning:** Use `React.lazy()` for route-level components
```typescript
const Dashboard = lazy(() => import('./features/dashboard/Dashboard'));
```

---

## Adding New Learnings

When a TypeScript/React-specific pattern emerges:

1. Add entry with date header
2. Include context, learning, and code examples
3. Note if it applies to React Native as well
4. Consider if it warrants a standards update
