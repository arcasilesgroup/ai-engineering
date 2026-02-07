# TypeScript/React Anti-Patterns

These are patterns to avoid in TypeScript/React code. When you encounter any of these in existing code, refactor them. When writing new code, never introduce them.

---

## Table of Contents

- [any Abuse](#any-abuse)
- [Prop Drilling](#prop-drilling)
- [useEffect for Derived State](#useeffect-for-derived-state)
- [Index as Key](#index-as-key)
- [Premature Optimization](#premature-optimization)
- [God Components](#god-components)
- [Nested Ternaries in JSX](#nested-ternaries-in-jsx)
- [Business Logic in Components](#business-logic-in-components)
- [Mutable State Patterns](#mutable-state-patterns)
- [Over-Abstraction](#over-abstraction)

---

## any Abuse

### The Problem

Using `any` disables TypeScript's type checking, silently introducing bugs that would otherwise be caught at compile time. It spreads virally -- one `any` infects every value that flows through it.

### Common Violations and Fixes

```typescript
// ANTI-PATTERN: any for API responses
async function fetchUser(id: string): Promise<any> {
  const res = await fetch(`/api/users/${id}`);
  return res.json();
}
const user = await fetchUser('123');
user.naem; // Typo not caught!

// FIX: Use a typed response with runtime validation
async function fetchUser(id: string): Promise<User> {
  const res = await fetch(`/api/users/${id}`);
  const data: unknown = await res.json();
  return UserSchema.parse(data);
}
const user = await fetchUser('123');
user.naem; // Compile error: Property 'naem' does not exist on type 'User'
```

```typescript
// ANTI-PATTERN: any for event handlers
const handleChange = (e: any) => {
  setName(e.target.value);
};

// FIX: Use the correct React event type
const handleChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
  setName(e.target.value);
};
```

```typescript
// ANTI-PATTERN: any to silence type errors
const items = data as any[];
items.map((item) => item.whatever);

// FIX: Use unknown and narrow, or define the type
interface DataItem {
  id: string;
  value: number;
}

function isDataItemArray(data: unknown): data is DataItem[] {
  return Array.isArray(data) && data.every(
    (item) => typeof item === 'object' && item !== null && 'id' in item && 'value' in item,
  );
}

if (!isDataItemArray(data)) {
  throw new Error('Invalid data format');
}
data.map((item) => item.value); // Fully typed
```

```typescript
// ANTI-PATTERN: any for generic catch-all
function processData(data: any): any {
  return data;
}

// FIX: Use generics
function processData<T>(data: T): T {
  return data;
}
```

### When You Inherit any From a Library

If a third-party library returns `any`, immediately narrow it at the boundary.

```typescript
// Wrap the untyped boundary
import { unsafeLibraryFunction } from 'some-lib'; // Returns any

function safeWrapper(input: string): ExpectedOutput {
  const result: unknown = unsafeLibraryFunction(input);
  return ExpectedOutputSchema.parse(result);
}
```

---

## Prop Drilling

### The Problem

Passing props through multiple intermediate components that do not use them creates tight coupling, makes refactoring painful, and clutters component signatures.

### Identifying the Smell

If a prop passes through 3 or more components without being used, it is being drilled.

```typescript
// ANTI-PATTERN: Drilling theme through 4 levels
function App() {
  const theme = useTheme();
  return <Dashboard theme={theme} />;
}

function Dashboard({ theme }: { theme: Theme }) {
  return <Sidebar theme={theme} />;  // Dashboard doesn't use theme
}

function Sidebar({ theme }: { theme: Theme }) {
  return <NavItem theme={theme} />;  // Sidebar doesn't use theme
}

function NavItem({ theme }: { theme: Theme }) {
  return <span style={{ color: theme.primary }}>Home</span>;
}
```

### Fixes

**Option 1: Context (for widely-used data)**

```typescript
// FIX: Context for theme
const ThemeContext = createContext<Theme | null>(null);

function useThemeContext(): Theme {
  const theme = useContext(ThemeContext);
  if (!theme) throw new Error('useThemeContext must be within ThemeProvider');
  return theme;
}

function NavItem(): React.ReactElement {
  const theme = useThemeContext();
  return <span style={{ color: theme.primary }}>Home</span>;
}
```

**Option 2: Component composition (restructure the tree)**

```typescript
// FIX: Composition — pass the rendered element, not the data
function Dashboard(): React.ReactElement {
  const theme = useTheme();

  return (
    <Sidebar>
      <NavItem style={{ color: theme.primary }}>Home</NavItem>
    </Sidebar>
  );
}

function Sidebar({ children }: { children: React.ReactNode }): React.ReactElement {
  return <nav>{children}</nav>;
}
```

**Option 3: Custom hook (when components need the same data)**

```typescript
// FIX: Each component fetches its own data via hook
function NavItem(): React.ReactElement {
  const theme = useTheme(); // Each consumer gets it directly
  return <span style={{ color: theme.primary }}>Home</span>;
}
```

### When Prop Drilling Is Acceptable

Prop drilling through 1-2 levels is normal and fine. Do not introduce context for a prop that only passes through one intermediate component.

---

## useEffect for Derived State

### The Problem

Using `useEffect` + `setState` to compute values that can be derived directly from existing state or props causes unnecessary re-renders, introduces timing bugs, and makes code harder to follow.

### Common Violations

```typescript
// ANTI-PATTERN: useEffect to compute derived state
function UserList({ users }: { users: User[] }) {
  const [filteredUsers, setFilteredUsers] = useState<User[]>([]);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    setFilteredUsers(users.filter((u) => u.name.includes(searchTerm)));
  }, [users, searchTerm]);
  // Problems:
  // 1. Extra render cycle (renders with stale filteredUsers, then re-renders)
  // 2. Unnecessary state (filteredUsers is fully derivable)
  // 3. Can cause infinite loops if dependencies are wrong

  return <List items={filteredUsers} />;
}

// FIX: Compute during render
function UserList({ users }: { users: User[] }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredUsers = users.filter((u) => u.name.includes(searchTerm));
  // Or use useMemo if the computation is actually expensive:
  // const filteredUsers = useMemo(
  //   () => users.filter((u) => u.name.includes(searchTerm)),
  //   [users, searchTerm],
  // );

  return <List items={filteredUsers} />;
}
```

```typescript
// ANTI-PATTERN: useEffect to transform props
function PriceDisplay({ priceInCents }: { priceInCents: number }) {
  const [formattedPrice, setFormattedPrice] = useState('');

  useEffect(() => {
    setFormattedPrice(`$${(priceInCents / 100).toFixed(2)}`);
  }, [priceInCents]);

  return <span>{formattedPrice}</span>;
}

// FIX: Compute inline
function PriceDisplay({ priceInCents }: { priceInCents: number }) {
  const formattedPrice = `$${(priceInCents / 100).toFixed(2)}`;
  return <span>{formattedPrice}</span>;
}
```

```typescript
// ANTI-PATTERN: useEffect to sync state with props
function ControlledInput({ externalValue }: { externalValue: string }) {
  const [value, setValue] = useState(externalValue);

  useEffect(() => {
    setValue(externalValue);
  }, [externalValue]);
  // This is almost always a bug. The component now has TWO sources of truth.

  return <input value={value} onChange={(e) => setValue(e.target.value)} />;
}

// FIX: Use a key to reset, or make it fully controlled
// Option A: Key-based reset
<ControlledInput key={externalValue} defaultValue={externalValue} />

// Option B: Fully controlled
function ControlledInput({ value, onChange }: {
  value: string;
  onChange: (value: string) => void;
}) {
  return <input value={value} onChange={(e) => onChange(e.target.value)} />;
}
```

### The Rule

If you can compute it from existing state or props, compute it. Do not store it in state. Use `useMemo` only if the computation is genuinely expensive.

---

## Index as Key

### The Problem

Using array index as a key breaks React's reconciliation when items are reordered, inserted, or deleted. React uses keys to determine which DOM elements to reuse, and index-based keys cause it to match the wrong items.

### When Index as Key Is Dangerous

```typescript
// ANTI-PATTERN: Index key with a reorderable list
function TodoList({ todos, onDelete }: TodoListProps) {
  return (
    <ul>
      {todos.map((todo, index) => (
        <li key={index}>  {/* BUG: items will mismatch after delete/reorder */}
          <input type="checkbox" checked={todo.done} />
          <span>{todo.text}</span>
          <button onClick={() => onDelete(index)}>Delete</button>
        </li>
      ))}
    </ul>
  );
}

// FIX: Use a stable unique identifier
function TodoList({ todos, onDelete }: TodoListProps) {
  return (
    <ul>
      {todos.map((todo) => (
        <li key={todo.id}>
          <input type="checkbox" checked={todo.done} />
          <span>{todo.text}</span>
          <button onClick={() => onDelete(todo.id)}>Delete</button>
        </li>
      ))}
    </ul>
  );
}
```

### When Index as Key Is Acceptable

Index keys are safe ONLY when ALL of these conditions are true:

1. The list is static (never reordered, filtered, or modified).
2. Items have no local state or uncontrolled inputs.
3. Items have no stable unique ID available.

```typescript
// OK: Static display-only list that never changes
function StaticBreadcrumbs({ items }: { items: string[] }) {
  return (
    <nav>
      {items.map((item, index) => (
        <span key={index}>{item}</span>
      ))}
    </nav>
  );
}
```

When in doubt, always use a unique ID.

---

## Premature Optimization

### The Problem

Wrapping everything in `React.memo`, `useMemo`, and `useCallback` without evidence of a performance problem adds complexity, increases memory usage, and can actually hurt performance (the comparison cost exceeds the render cost).

### Common Violations

```typescript
// ANTI-PATTERN: Memoizing everything
function UserCard({ user }: UserCardProps) {
  const fullName = useMemo(() => `${user.first} ${user.last}`, [user.first, user.last]);
  // String concatenation is cheaper than the useMemo overhead

  const handleClick = useCallback(() => {
    console.log(user.id);
  }, [user.id]);
  // Nobody is depending on this callback's referential identity

  return (
    <div onClick={handleClick}>
      <span>{fullName}</span>
    </div>
  );
}

export default React.memo(UserCard);
// UserCard renders cheap UI — memo comparison cost may exceed render cost

// FIX: Write it simply
function UserCard({ user }: UserCardProps) {
  const fullName = `${user.first} ${user.last}`;

  const handleClick = (): void => {
    console.log(user.id);
  };

  return (
    <div onClick={handleClick}>
      <span>{fullName}</span>
    </div>
  );
}

export { UserCard };
```

### When to Optimize

Only optimize after you have:

1. Identified a real performance problem using React DevTools Profiler.
2. Confirmed that a specific component is re-rendering unnecessarily and that the re-render cost is significant.
3. Verified that the optimization actually helps by profiling before and after.

### What to Optimize First

Before reaching for memoization:

1. Fix unnecessary re-renders caused by poor state structure (state too high in the tree).
2. Split large components so less of the tree re-renders.
3. Move state closer to where it is used.
4. Use virtualization for long lists.

---

## God Components

### The Problem

Components that exceed 300 lines, handle multiple responsibilities, or have deeply nested JSX are hard to read, test, and maintain.

### Warning Signs

- More than 5 `useState` or `useEffect` calls.
- More than 300 lines.
- Multiple unrelated pieces of state.
- Complex conditional rendering with deep nesting.
- Mixing data fetching, business logic, and presentation.

```typescript
// ANTI-PATTERN: God component (abbreviated)
function DashboardPage() {
  const [users, setUsers] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [isExporting, setIsExporting] = useState(false);
  const [filters, setFilters] = useState({});
  // ... 8 useEffect calls, 15 event handlers, 200 lines of JSX
}
```

### Fix: Decompose

```typescript
// FIX: Split into focused components and hooks
function DashboardPage() {
  return (
    <DashboardLayout>
      <DashboardHeader />
      <div className="dashboard-grid">
        <AnalyticsPanel />
        <RecentUsersPanel />
        <NotificationsPanel />
      </div>
    </DashboardLayout>
  );
}

// Each panel is self-contained with its own hook
function AnalyticsPanel() {
  const { data, isLoading } = useAnalytics();
  if (isLoading) return <AnalyticsSkeleton />;
  return <AnalyticsChart data={data} />;
}

function RecentUsersPanel() {
  const { users, isLoading } = useRecentUsers();
  const [searchTerm, setSearchTerm] = useState('');
  const filtered = users.filter((u) => u.name.includes(searchTerm));

  return (
    <div>
      <SearchInput value={searchTerm} onChange={setSearchTerm} />
      <UserList users={filtered} isLoading={isLoading} />
    </div>
  );
}
```

---

## Nested Ternaries in JSX

### The Problem

Nested ternaries are difficult to read and reason about, especially in JSX where indentation does not help.

```typescript
// ANTI-PATTERN: Nested ternaries
function StatusDisplay({ status }: { status: Status }) {
  return (
    <div>
      {status === 'loading'
        ? <Spinner />
        : status === 'error'
          ? <ErrorIcon />
          : status === 'empty'
            ? <EmptyState />
            : <DataDisplay />}
    </div>
  );
}
```

### Fixes

**Option 1: Early returns (preferred for top-level rendering)**

```typescript
function StatusDisplay({ status }: { status: Status }) {
  if (status === 'loading') return <Spinner />;
  if (status === 'error') return <ErrorIcon />;
  if (status === 'empty') return <EmptyState />;
  return <DataDisplay />;
}
```

**Option 2: Object lookup (for inline variants)**

```typescript
const STATUS_COMPONENTS: Record<Status, React.ComponentType> = {
  loading: Spinner,
  error: ErrorIcon,
  empty: EmptyState,
  success: DataDisplay,
};

function StatusDisplay({ status }: { status: Status }) {
  const Component = STATUS_COMPONENTS[status];
  return <Component />;
}
```

**Option 3: Switch in a helper (when logic is complex)**

```typescript
function getStatusContent(status: Status, data: Data | null): React.ReactElement {
  switch (status) {
    case 'loading':
      return <Spinner />;
    case 'error':
      return <ErrorIcon />;
    case 'empty':
      return <EmptyState />;
    case 'success':
      return <DataDisplay data={data!} />;
    default: {
      const _exhaustive: never = status;
      return _exhaustive;
    }
  }
}
```

A single ternary is fine: `{isLoggedIn ? <UserMenu /> : <LoginButton />}`. Never nest them.

---

## Business Logic in Components

### The Problem

Embedding business rules, data transformations, and calculations directly in component bodies makes them untestable in isolation, non-reusable, and hard to understand.

```typescript
// ANTI-PATTERN: Business logic in component
function OrderSummary({ order }: { order: Order }) {
  // Tax calculation embedded in component
  const taxRate = order.shipping.country === 'US'
    ? order.shipping.state === 'CA' ? 0.0725
    : order.shipping.state === 'NY' ? 0.08
    : 0.05
    : 0;

  const subtotal = order.items.reduce((sum, item) => {
    const discount = item.quantity >= 10 ? 0.1 : item.quantity >= 5 ? 0.05 : 0;
    return sum + item.price * item.quantity * (1 - discount);
  }, 0);

  const tax = subtotal * taxRate;
  const shipping = subtotal > 100 ? 0 : 9.99;
  const total = subtotal + tax + shipping;

  return (
    <div>
      <p>Subtotal: ${subtotal.toFixed(2)}</p>
      <p>Tax: ${tax.toFixed(2)}</p>
      <p>Shipping: ${shipping.toFixed(2)}</p>
      <p>Total: ${total.toFixed(2)}</p>
    </div>
  );
}
```

### Fix: Extract to Pure Functions or Hooks

```typescript
// FIX: Extract business logic to testable utilities
// utils/order-calculations.ts
export function calculateOrderTotals(order: Order): OrderTotals {
  const subtotal = calculateSubtotal(order.items);
  const tax = calculateTax(subtotal, order.shipping);
  const shipping = calculateShipping(subtotal);
  const total = subtotal + tax + shipping;

  return { subtotal, tax, shipping, total };
}

function calculateSubtotal(items: OrderItem[]): number {
  return items.reduce((sum, item) => {
    const discount = getVolumeDiscount(item.quantity);
    return sum + item.price * item.quantity * (1 - discount);
  }, 0);
}

function getVolumeDiscount(quantity: number): number {
  if (quantity >= 10) return 0.1;
  if (quantity >= 5) return 0.05;
  return 0;
}

function calculateTax(subtotal: number, shipping: ShippingAddress): number {
  return subtotal * getTaxRate(shipping);
}

// Component is now pure presentation
function OrderSummary({ order }: { order: Order }) {
  const { subtotal, tax, shipping, total } = calculateOrderTotals(order);

  return (
    <div>
      <p>Subtotal: ${subtotal.toFixed(2)}</p>
      <p>Tax: ${tax.toFixed(2)}</p>
      <p>Shipping: ${shipping.toFixed(2)}</p>
      <p>Total: ${total.toFixed(2)}</p>
    </div>
  );
}
```

The extracted functions can now be unit tested without rendering any components.

---

## Mutable State Patterns

### The Problem

Directly mutating state or refs that represent state bypasses React's change detection, causing the UI to become stale or behave unpredictably.

```typescript
// ANTI-PATTERN: Mutating state directly
function TodoList() {
  const [todos, setTodos] = useState<Todo[]>([]);

  const addTodo = (text: string): void => {
    todos.push({ id: crypto.randomUUID(), text, done: false }); // MUTATION!
    setTodos(todos); // Same reference — React won't re-render
  };

  const toggleTodo = (id: string): void => {
    const todo = todos.find((t) => t.id === id);
    if (todo) {
      todo.done = !todo.done; // MUTATION!
      setTodos([...todos]); // Shallow copy hides the mutation but it is still wrong
    }
  };

  return <List items={todos} />;
}

// FIX: Immutable updates
function TodoList() {
  const [todos, setTodos] = useState<Todo[]>([]);

  const addTodo = (text: string): void => {
    setTodos((prev) => [...prev, { id: crypto.randomUUID(), text, done: false }]);
  };

  const toggleTodo = (id: string): void => {
    setTodos((prev) =>
      prev.map((todo) =>
        todo.id === id ? { ...todo, done: !todo.done } : todo,
      ),
    );
  };

  return <List items={todos} />;
}
```

```typescript
// ANTI-PATTERN: Mutating objects in state
function UserForm() {
  const [user, setUser] = useState({ name: '', address: { city: '', zip: '' } });

  const updateCity = (city: string): void => {
    user.address.city = city; // MUTATION of nested object
    setUser({ ...user }); // Shallow copy does not protect nested objects
  };

  // FIX: Immutable nested update
  const updateCity = (city: string): void => {
    setUser((prev) => ({
      ...prev,
      address: { ...prev.address, city },
    }));
  };
}
```

### Rule

Never mutate state. Always create new objects and arrays. For complex nested updates, consider Immer or `useReducer`.

---

## Over-Abstraction

### The Problem

Applying DRY (Don't Repeat Yourself) too aggressively creates abstractions that are harder to understand than the duplication they eliminate. Premature abstraction couples unrelated code and makes future changes painful.

### Warning Signs

- A "generic" component with more than 8 props controlling its behavior.
- A utility function that handles 5+ different cases via flags.
- An abstraction used in only 1-2 places.
- A shared module that every consumer needs to configure differently.

```typescript
// ANTI-PATTERN: Over-abstracted "generic" component
interface GenericListProps<T> {
  items: T[];
  renderItem: (item: T) => React.ReactElement;
  renderEmpty: () => React.ReactElement;
  renderLoading: () => React.ReactElement;
  renderError: (error: Error) => React.ReactElement;
  isLoading: boolean;
  error: Error | null;
  onItemClick?: (item: T) => void;
  onItemDelete?: (item: T) => void;
  selectable?: boolean;
  selectedItems?: T[];
  onSelectionChange?: (items: T[]) => void;
  sortable?: boolean;
  sortField?: keyof T;
  sortDirection?: 'asc' | 'desc';
  onSort?: (field: keyof T) => void;
  paginated?: boolean;
  page?: number;
  pageSize?: number;
  totalItems?: number;
  onPageChange?: (page: number) => void;
  filterable?: boolean;
  filterValue?: string;
  onFilterChange?: (value: string) => void;
  virtualized?: boolean;
  itemHeight?: number;
  // ... the list goes on
}

// This component is harder to use than building each list from scratch
```

### The Fix: Prefer Composition and Duplication

```typescript
// FIX: Simple, focused components composed together
function UserList(): React.ReactElement {
  const { users, isLoading, error } = useUsers();
  const [search, setSearch] = useState('');
  const filtered = users.filter((u) => u.name.includes(search));

  if (isLoading) return <Skeleton count={5} />;
  if (error) return <ErrorDisplay error={error} />;

  return (
    <div>
      <SearchInput value={search} onChange={setSearch} />
      {filtered.length === 0 ? (
        <EmptyState message="No users found" />
      ) : (
        <ul>
          {filtered.map((user) => (
            <UserListItem key={user.id} user={user} />
          ))}
        </ul>
      )}
    </div>
  );
}
```

### The Rule of Three

Do not abstract until you have seen the same pattern in three places. When you do abstract:

1. Extract only the truly shared behavior.
2. Keep the abstraction focused on one thing.
3. Make sure every consumer uses most of the abstraction's surface area.
4. If different consumers need different 20% of the abstraction, they probably need different abstractions.

A little duplication is far cheaper than the wrong abstraction.
