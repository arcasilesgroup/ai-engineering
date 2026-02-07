# Coding Standards

## Universal Standards

# Universal Coding Standards

These standards apply to every technology stack. They define the baseline expectations for all code written or modified by AI assistants and human engineers alike. When a stack-specific standard conflicts with a universal one, the stack-specific standard takes precedence.

---

## Code Quality Principles

### Readability Is Non-Negotiable

Code is read far more often than it is written. Optimize for the reader, not the writer.

- Write code that a competent engineer unfamiliar with the project can understand within 60 seconds of reading a function.
- Avoid clever tricks, obscure operators, and implicit behavior. Explicit is better than implicit.
- Use vertical whitespace deliberately to separate logical blocks within a function.
- Keep related code close together. If two pieces of logic are always modified together, they belong near each other.

### Simplicity Over Abstraction

- Do not introduce an abstraction until a pattern has repeated at least three times (Rule of Three).
- Prefer flat code over deeply nested code. If a function has more than 3 levels of nesting, refactor it.
- Prefer composition over inheritance in all cases unless the language idiom strongly favors inheritance.
- When choosing between a simple solution that is slightly repetitive and a clever solution that is DRY but hard to follow, choose the simple solution.
- Avoid "clever" code that relies on operator precedence, short-circuit tricks, or language-specific quirks for core logic. Save cleverness for performance-critical hot paths where the trade-off is justified and documented.

```
// DON'T — clever but opaque
const name = user?.profile?.name || (config.defaults && config.defaults[role]) || "Unknown";

// DO — clear and traceable
let name = "Unknown";
if (user?.profile?.name) {
  name = user.profile.name;
} else if (config.defaults?.[role]) {
  name = config.defaults[role];
}
```

### DRY — But Not at the Cost of Clarity

- Extract repeated logic into named functions or constants when the same logic appears 3+ times.
- Do NOT extract code into a shared utility just because two pieces of code happen to look similar. They must share the same reason to change.
- Duplication is far cheaper than the wrong abstraction. If extracting creates coupling between unrelated modules, keep the duplication.
- When you do extract, name the shared function after _what it does_, not _where it is used_. `formatCurrency` is reusable; `formatPriceForCheckoutPage` is not.

### SOLID Principles

- **Single Responsibility**: Every module, class, or function should have one reason to change. If you cannot describe what it does in one sentence without using "and," split it.
- **Open/Closed**: Design modules so new behavior can be added without modifying existing code. Use interfaces, plugins, or configuration — not conditional branches.
- **Liskov Substitution**: Subtypes must be usable wherever their parent type is expected without breaking behavior.
- **Interface Segregation**: Do not force consumers to depend on methods they do not use. Prefer small, focused interfaces over large, general ones.
- **Dependency Inversion**: High-level modules should depend on abstractions, not on low-level implementation details. Inject dependencies rather than instantiating them directly.

---

## Naming Conventions

### General Rules

- Names must be descriptive and unambiguous. A reader should understand the purpose without reading the implementation.
- Do not abbreviate unless the abbreviation is universally understood within the domain (e.g., `url`, `id`, `http`, `db`).
- Avoid single-letter variable names except for loop counters (`i`, `j`, `k`) and lambda/closure parameters where the context makes the meaning obvious.
- Boolean variables and functions must read as a yes/no question: `isActive`, `hasPermission`, `canRetry`, `shouldValidate`.

### Variables

- Use `camelCase` for variables and function parameters (unless the language convention differs, e.g., `snake_case` in Python/Ruby).
- Constants use `UPPER_SNAKE_CASE`.
- Avoid generic names like `data`, `info`, `temp`, `result`, `value`, `item` unless narrowly scoped (under 5 lines).

```
// DON'T
const d = getUsers();
const temp = processData(d);

// DO
const activeUsers = getActiveUsers();
const enrichedProfiles = enrichUserProfiles(activeUsers);
```

### Functions and Methods

- Name functions with a verb that describes the action: `fetchUser`, `calculateTotal`, `validateEmail`, `sendNotification`.
- Functions that return booleans start with `is`, `has`, `can`, `should`, or `was`.
- Event handler functions use `on` or `handle` prefix: `onSubmit`, `handleClick`, `onUserCreated`.
- Avoid vague verbs: `process`, `handle`, `manage`, `do`. Be specific about what the function does.

```
// DON'T
function handleData(input) { ... }

// DO
function parseCSVToUserRecords(csvContent) { ... }
```

### Classes, Types, and Interfaces

- Classes and types use `PascalCase`.
- Interfaces should describe a capability or contract, not just mirror a class name. Prefer `Serializable`, `Cacheable`, `UserRepository` over `IUser`.
- Do not prefix interfaces with `I` unless the language convention mandates it (e.g., C# does, TypeScript does not).
- Enums use `PascalCase` for the type and `UPPER_SNAKE_CASE` for values.

### Files and Directories

- File names must match the primary export or class they contain.
- Use `kebab-case` for file names unless the language convention differs (e.g., `PascalCase` for React components, `snake_case` for Python modules).
- Group files by feature or domain, not by technical role (e.g., prefer `users/controller.ts` over `controllers/user-controller.ts`).
- Index files (`index.ts`, `__init__.py`) should only re-export. They must contain zero business logic.

---

## Code Organization

### File Size

- A single file should not exceed 300 lines of code (excluding imports and comments). If it does, find a natural boundary to split.
- If a file contains more than one public class or more than 5 public functions, it is doing too much.

### Function Length

- A function should fit on one screen (~40 lines). If it does not, extract sub-operations into well-named helper functions.
- A function should do one thing. If the function name requires "and" to describe it, split it.
- Aim for functions with 3 or fewer parameters. If a function takes more than 4 parameters, group them into a configuration object or struct.

### Complexity

- Cyclomatic complexity per function should not exceed 10. Refactor complex conditionals into guard clauses, early returns, or lookup tables.
- Avoid deeply nested callbacks. Use async/await, promises, or equivalent language patterns.
- Replace complex `if/else if/else if` chains with strategy patterns, maps, or switch statements.

```
// DON'T
function getDiscount(userType) {
  if (userType === 'premium') {
    return 0.2;
  } else if (userType === 'member') {
    return 0.1;
  } else if (userType === 'trial') {
    return 0.05;
  } else {
    return 0;
  }
}

// DO
const DISCOUNT_BY_USER_TYPE = {
  premium: 0.2,
  member: 0.1,
  trial: 0.05,
};

function getDiscount(userType) {
  return DISCOUNT_BY_USER_TYPE[userType] ?? 0;
}
```

### Module Boundaries

- Each module should have a clear public API and hide its implementation details. Consumers should interact with the module through its public interface, not reach into its internals.
- Avoid god modules — if a module is imported by more than half the codebase, it is likely doing too much. Split it by responsibility.
- Keep coupling low between modules. A change in module A should rarely require changes in module B. If it does, the boundary is in the wrong place.

### Imports and Dependencies

- Sort imports in a consistent order: standard library, external packages, internal modules, relative imports.
- Separate import groups with a blank line for visual clarity.
- Never import an entire module when you only use one function. Use named/selective imports.
- Avoid circular dependencies. If module A imports from B and B imports from A, extract the shared logic into a third module C.

```
// DON'T — unorganized imports
import { validateEmail } from './utils';
import express from 'express';
import { UserService } from '../services/user';
import fs from 'fs';
import { logger } from './logger';
import cors from 'cors';

// DO — grouped and ordered
import fs from 'fs';

import cors from 'cors';
import express from 'express';

import { UserService } from '../services/user';

import { logger } from './logger';
import { validateEmail } from './utils';
```

---

## Error Handling

### Principles

- Never swallow errors silently. Every catch/except block must either handle the error meaningfully, re-throw it, or log it with sufficient context.
- Use typed/specific errors over generic ones. Catch the narrowest exception type possible.
- Fail fast: validate inputs at the boundary and reject invalid data immediately rather than letting it propagate deep into the system.
- Distinguish between expected errors (validation failures, not-found) and unexpected errors (null pointers, connection timeouts). Handle them differently.

### Patterns

- Use guard clauses and early returns to handle error cases first, keeping the happy path un-indented.
- Return result types (e.g., `Result<T, E>`, `Either`) rather than throwing exceptions in contexts where errors are expected and frequent.
- Always include context in error messages: what operation failed, what input caused it, and what the caller should do about it.

```
// DON'T
throw new Error("Failed");

// DO
throw new ValidationError(
  `Failed to parse date from field "startDate": received "${rawValue}". Expected ISO 8601 format (YYYY-MM-DD).`
);
```

- Never use exceptions for control flow. Exceptions are for exceptional circumstances, not for branching logic.
- Clean up resources in `finally` blocks, `defer` statements, or language-equivalent constructs. Never rely on the happy path for cleanup.

### Error Hierarchy

- Define a project-level error hierarchy. At minimum, distinguish between:
  - **Operational errors**: Expected problems that the system can handle (network timeout, invalid input, resource not found). These are part of normal operation.
  - **Programmer errors**: Bugs in the code (null dereference, type error, assertion failure). These indicate code that needs fixing.
- Operational errors should be caught and handled gracefully (retry, fallback, user message). Programmer errors should crash loudly and be fixed immediately.
- Use custom error classes that carry structured context (error code, HTTP status, user-facing message, internal details) rather than passing strings around.

```
// DON'T — generic error with no context
catch (err) {
  console.log(err);
  return res.status(500).send("Error");
}

// DO — structured error handling
catch (err) {
  if (err instanceof NotFoundError) {
    return res.status(404).json({ error: { code: "NOT_FOUND", message: err.userMessage } });
  }
  logger.error({ err, requestId: req.id, operation: "fetchUser" });
  return res.status(500).json({ error: { code: "INTERNAL_ERROR", message: "An unexpected error occurred." } });
}
```

---

## Documentation

### When to Document

- **Public APIs**: Every public function, method, class, or module must have a doc comment explaining what it does, its parameters, its return value, and any exceptions it throws.
- **Why, not what**: Document the reasoning behind non-obvious decisions. If the code is clear about _what_ it does, a comment explaining _what_ is redundant. Explain _why_.
- **Workarounds and hacks**: If code works around a bug, references an external issue, or uses a non-obvious approach, leave a comment with a link or explanation.
- **Configuration**: Document all configuration options, their valid values, defaults, and effects.
- **Complex algorithms**: If a function implements a non-trivial algorithm, link to the source (paper, RFC, design doc) and summarize the approach.

### When NOT to Document

- Do not add comments that restate what the code already says. `// increment counter` above `counter++` is noise.
- Do not use comments as a substitute for good naming. If you need a comment to explain what a variable is, rename the variable.
- Do not leave commented-out code in the codebase. Delete it. Version control exists for a reason.
- Do not write TODO comments without an associated ticket or issue number. `// TODO: fix this` is not actionable. `// TODO(PROJ-1234): handle pagination` is.

### Documentation Formats

- Use the documentation format standard for your language: JSDoc for JavaScript/TypeScript, docstrings for Python, GoDoc for Go, Javadoc for Java, `///` for Rust.
- Include parameter types and descriptions, return types, and thrown exceptions in doc comments.
- For REST APIs, maintain an OpenAPI/Swagger specification. Keep it in sync with the implementation — automated generation is preferred.

```
/**
 * Calculates the shipping cost for an order based on destination and weight.
 *
 * @param destination - ISO 3166-1 alpha-2 country code (e.g., "US", "DE").
 * @param weightKg - Total weight of the order in kilograms. Must be positive.
 * @returns The shipping cost in USD cents.
 * @throws {InvalidDestinationError} If the country code is not supported.
 * @throws {WeightLimitExceededError} If weightKg exceeds 30.
 */
function calculateShippingCost(destination: string, weightKg: number): number {
  // ...
}
```

---

## Performance Awareness

- Do not optimize prematurely. Write clear, correct code first. Optimize only when profiling identifies a bottleneck.
- Be aware of algorithmic complexity. A nested loop over a large dataset (O(n^2)) is a red flag — consider whether a hash map, index, or different data structure would help.
- Avoid unnecessary allocations in hot paths: reuse buffers, avoid string concatenation in loops, prefer streaming over loading entire datasets into memory.
- Know the cost of your abstractions. ORMs, serialization frameworks, and middleware have overhead. In performance-critical paths, consider dropping down a level.
- Cache expensive computations, but always define a cache invalidation strategy. Unbounded caches are memory leaks.
- Prefer lazy evaluation and pagination when dealing with large collections. Never load an entire table into memory unless you are certain the table is small.

---

## Dependency Management

- Add a dependency only when the alternative is writing and maintaining significant code yourself. A 10-line utility function does not need a package.
- Before adding a dependency, evaluate: maintenance activity, open issue count, license compatibility, download/usage numbers, and transitive dependency count.
- Pin dependency versions explicitly in lock files. Never rely on floating ranges (e.g., `^1.0.0`) in production deployments.
- Audit dependencies regularly for known vulnerabilities. Integrate automated tools (Dependabot, Snyk, Renovate) into CI.
- Separate production dependencies from development dependencies. Test frameworks, linters, and build tools do not belong in the production bundle.
- When wrapping a third-party dependency, do so behind an internal interface. This allows replacement without rewriting consumers.

---

## Code Review Readiness

Before submitting code for review (or before an AI assistant considers a task complete), verify:

1. **It compiles and passes all tests.** Never submit code that has known failures.
2. **It includes tests.** Every behavioral change must have corresponding test coverage.
3. **It handles edge cases.** Empty inputs, null values, boundary conditions, and concurrent access have been considered.
4. **It follows the project style.** Formatting matches the project configuration. No linter warnings or errors.
5. **It has no debug artifacts.** Remove `console.log`, `print()`, `debugger`, commented-out code, and hard-coded test values.
6. **It is scoped correctly.** A single PR addresses a single concern. Do not mix refactoring with feature work. Do not mix formatting changes with logic changes.
7. **It is self-describing.** The PR description explains what changed and why. If context is needed, it links to the relevant issue or design document.
8. **It does not introduce tech debt without acknowledgment.** If a shortcut was taken, document it with a TODO and a ticket number.

---

## Summary Checklist

| Principle      | Check                                                           |
| -------------- | --------------------------------------------------------------- |
| Readable       | Can a new team member understand this in under 60 seconds?      |
| Simple         | Is the simplest possible approach used?                         |
| Named well     | Do names convey intent without needing comments?                |
| Sized right    | Are files under 300 lines, functions under 40?                  |
| Errors handled | Are all error paths covered with context?                       |
| Documented     | Are public APIs documented and non-obvious decisions explained? |
| Performant     | Are there any O(n^2) or worse operations on large datasets?     |
| Dependencies   | Is every dependency justified and pinned?                       |
| Review-ready   | Tests pass, no debug artifacts, single concern?                 |

## TypeScript/React Standards

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
const user = await fetchUser("123");
user.naem; // Typo not caught!

// FIX: Use a typed response with runtime validation
async function fetchUser(id: string): Promise<User> {
  const res = await fetch(`/api/users/${id}`);
  const data: unknown = await res.json();
  return UserSchema.parse(data);
}
const user = await fetchUser("123");
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
  return (
    Array.isArray(data) &&
    data.every(
      (item) =>
        typeof item === "object" &&
        item !== null &&
        "id" in item &&
        "value" in item,
    )
  );
}

if (!isDataItemArray(data)) {
  throw new Error("Invalid data format");
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
import { unsafeLibraryFunction } from "some-lib"; // Returns any

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
  const [searchTerm, setSearchTerm] = useState("");
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
  const [user, setUser] = useState({
    name: "",
    address: { city: "", zip: "" },
  });

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
  sortDirection?: "asc" | "desc";
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
import { useQuery } from "@tanstack/react-query";
import { usersApi } from "../api/users-api";

import type { User } from "../types";

interface UseUserOptions {
  enabled?: boolean;
}

interface UseUserReturn {
  user: User | undefined;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useUser(
  id: string,
  options: UseUserOptions = {},
): UseUserReturn {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["users", "detail", id],
    queryFn: () => usersApi.getUser(id),
    enabled: options.enabled ?? true,
  });

  return {
    user: data,
    isLoading,
    error: error as Error | null,
    refetch: async () => {
      await refetch();
    },
  };
}
```

### Form State Hook

Encapsulate form logic in a custom hook to separate form behavior from presentation.

```typescript
// features/users/hooks/use-create-user-form.ts
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CreateUserSchema } from "../types";
import { usersApi } from "../api/users-api";

import type { z } from "zod";
import type { UseFormReturn } from "react-hook-form";

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
      name: "",
      email: "",
      role: "viewer",
    },
  });

  const mutation = useMutation({
    mutationFn: usersApi.createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users", "list"] });
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
import { useState, useCallback, useEffect } from "react";

export function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, (value: T | ((prev: T) => T)) => void, () => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === "undefined") return initialValue;
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
        if (typeof window !== "undefined") {
          window.localStorage.setItem(key, JSON.stringify(nextValue));
        }
        return nextValue;
      });
    },
    [key],
  );

  const removeValue = useCallback(() => {
    setStoredValue(initialValue);
    if (typeof window !== "undefined") {
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

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
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
type Result<T, E = Error> = { ok: true; value: T } | { ok: false; error: E };

function ok<T>(value: T): Result<T, never> {
  return { ok: true, value };
}

function err<E>(error: E): Result<never, E> {
  return { ok: false, error };
}

// Usage in API layer
async function createUser(
  input: CreateUserInput,
): Promise<Result<User, ApiError>> {
  try {
    const user = await api.post<User>("/users", input);
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
    if (result.error.code === "DUPLICATE_EMAIL") {
      form.setError("email", { message: "This email is already registered" });
    } else {
      addNotification("error", result.error.message);
    }
    return;
  }

  addNotification("success", `Created user ${result.value.name}`);
  navigate("/users");
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
      if (error instanceof DOMException && error.name === "AbortError") {
        return; // Component unmounted, ignore
      }
      setError(error instanceof Error ? error : new Error("Unknown error"));
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
  window.addEventListener("error", (event) => {
    reportError({
      type: "unhandled_error",
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error?.stack,
    });
  });

  window.addEventListener("unhandledrejection", (event) => {
    reportError({
      type: "unhandled_rejection",
      message: event.reason?.message ?? "Unknown promise rejection",
      stack: event.reason?.stack,
    });
  });
}

function reportError(errorInfo: Record<string, unknown>): void {
  // Send to error tracking service (Sentry, etc.)
  console.error("[Global Error]", errorInfo);
}
```

---

## Data Fetching Patterns

### React Query Configuration

Set up React Query with sensible defaults.

```typescript
// shared/api/query-client.ts
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30_000),
      refetchOnWindowFocus: false, // Enable per-query if needed
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
  all: ["users"] as const,
  lists: () => [...userKeys.all, "list"] as const,
  list: (filters: UserFilters) => [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, "detail"] as const,
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

  window.addEventListener("resize", handleResize);
  return () => window.removeEventListener("resize", handleResize);
}, []);

// DO: Use AbortController for multiple listeners
useEffect(() => {
  const controller = new AbortController();

  window.addEventListener("resize", handleResize, {
    signal: controller.signal,
  });
  window.addEventListener("scroll", handleScroll, {
    signal: controller.signal,
  });
  document.addEventListener("keydown", handleKeyDown, {
    signal: controller.signal,
  });

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
  HOME: "/",
  LOGIN: "/login",
  DASHBOARD: "/dashboard",
  USERS: "/users",
  USER_DETAIL: "/users/:userId",
  USER_EDIT: "/users/:userId/edit",
  SETTINGS: "/settings",
  SETTINGS_SECTION: "/settings/:section",
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
export function buildPath(
  route: string,
  params?: Record<string, string>,
): string {
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
import { useParams } from "react-router-dom";

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

# TypeScript/React Frontend Security Standards

Every TypeScript/React application MUST follow these security practices. Frontend security is a mandatory layer of defense, not optional hardening.

---

## Table of Contents

- [XSS Prevention](#xss-prevention)
- [CSRF Protection](#csrf-protection)
- [Secure Cookie Handling](#secure-cookie-handling)
- [Token Storage](#token-storage)
- [Input Validation](#input-validation)
- [Dependency Security](#dependency-security)
- [Environment Variables](#environment-variables)
- [Content Security Policy](#content-security-policy)
- [Sensitive Data in Client Bundle](#sensitive-data-in-client-bundle)

---

## XSS Prevention

### Never Use dangerouslySetInnerHTML

Do not use `dangerouslySetInnerHTML` unless you have sanitized the input with a trusted library. React escapes content by default -- `dangerouslySetInnerHTML` bypasses that protection.

```typescript
// DON'T: Unsanitized HTML injection
function Comment({ body }: { body: string }): React.ReactElement {
  return <div dangerouslySetInnerHTML={{ __html: body }} />;
  // If body contains <script>alert('xss')</script>, it will execute
}

// DO: Sanitize if you must render HTML
import DOMPurify from 'dompurify';

function Comment({ body }: { body: string }): React.ReactElement {
  const sanitized = DOMPurify.sanitize(body, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
    ALLOWED_ATTR: ['href', 'target', 'rel'],
  });

  return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
}

// BEST: Use a markdown renderer instead of raw HTML
import ReactMarkdown from 'react-markdown';

function Comment({ body }: { body: string }): React.ReactElement {
  return <ReactMarkdown>{body}</ReactMarkdown>;
}
```

### Sanitize User Input in URLs

User-provided URLs can contain `javascript:` protocol injections.

```typescript
// DON'T: Unsanitized user URL
function UserLink({ url }: { url: string }): React.ReactElement {
  return <a href={url}>Visit</a>;
  // If url is "javascript:alert('xss')", clicking triggers script execution
}

// DO: Validate URL protocol
function sanitizeUrl(url: string): string {
  try {
    const parsed = new URL(url);
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
      return parsed.href;
    }
  } catch {
    // Invalid URL
  }
  return '#';
}

function UserLink({ url }: { url: string }): React.ReactElement {
  return (
    <a href={sanitizeUrl(url)} target="_blank" rel="noopener noreferrer">
      Visit
    </a>
  );
}
```

### External Links

All external links MUST include `rel="noopener noreferrer"` when using `target="_blank"`.

```typescript
// DO: Safe external link
<a href={externalUrl} target="_blank" rel="noopener noreferrer">
  External Site
</a>
```

### Do Not Construct HTML Strings

Never build HTML strings through concatenation or template literals. Always use React's JSX, which auto-escapes.

```typescript
// DON'T: HTML string construction
const html = `<div class="user">${userName}</div>`;
element.innerHTML = html; // XSS if userName contains <script>

// DO: Use JSX
return <div className="user">{userName}</div>; // React escapes userName
```

---

## CSRF Protection

### Token-Based Requests

For any state-changing request (POST, PUT, DELETE), include a CSRF token in the request headers. Coordinate with your backend on the token delivery mechanism.

```typescript
// shared/api/client.ts
async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  // Include CSRF token for state-changing requests
  if (method !== "GET" && method !== "HEAD") {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken;
    }
  }

  const response = await fetch(url, {
    method,
    headers,
    body: JSON.stringify(body),
    credentials: "same-origin",
  });
  return response.json() as Promise<T>;
}

function getCsrfToken(): string | null {
  // Read from meta tag (set by server-rendered page)
  return (
    document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')
      ?.content ?? null
  );
}
```

### SameSite Cookies

Ensure your backend sets cookies with `SameSite=Strict` or `SameSite=Lax`. The frontend cannot set this, but should verify it is configured correctly during security reviews.

---

## Secure Cookie Handling

### Cookie Attributes

When the frontend needs to set cookies (rare -- prefer letting the backend handle auth cookies), always set security attributes.

```typescript
// DO: Set secure cookie attributes
function setCookie(name: string, value: string, days: number): void {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = [
    `${encodeURIComponent(name)}=${encodeURIComponent(value)}`,
    `expires=${expires}`,
    "path=/",
    "Secure", // Only sent over HTTPS
    "SameSite=Strict", // Not sent with cross-site requests
    // Note: HttpOnly cannot be set from JavaScript (server only)
  ].join("; ");
}
```

### Do Not Read Auth Cookies in JavaScript

Authentication cookies MUST be `HttpOnly` (set by the server, invisible to JavaScript). If your code reads auth tokens from `document.cookie`, the architecture is wrong.

---

## Token Storage

### Never Store Auth Tokens in localStorage

`localStorage` is accessible to any JavaScript running on the page, including XSS payloads and third-party scripts. Auth tokens stored in `localStorage` can be stolen.

```typescript
// DON'T: Store tokens in localStorage
localStorage.setItem("authToken", token);
const token = localStorage.getItem("authToken");

// DON'T: Store tokens in sessionStorage (same vulnerability)
sessionStorage.setItem("authToken", token);
```

### Preferred Token Storage

Use one of these approaches, in order of preference:

1. **HttpOnly, Secure, SameSite cookies** (set by the server). The frontend never sees or touches the token. The browser automatically includes it in requests.

2. **In-memory only** (for SPAs with short-lived sessions). Store the token in a JavaScript variable or React state/context. The token is lost on page refresh, which is acceptable if your backend supports silent refresh via a refresh token in an HttpOnly cookie.

```typescript
// DO: In-memory token storage
// shared/auth/token-store.ts
let accessToken: string | null = null;

export function setAccessToken(token: string): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function clearAccessToken(): void {
  accessToken = null;
}
```

3. **Refresh token in HttpOnly cookie + access token in memory**. The backend sets a long-lived refresh token as an HttpOnly cookie. The frontend stores the short-lived access token in memory and uses the refresh token cookie to get a new access token when it expires.

### What IS Safe to Store in localStorage

- User preferences (theme, language, sidebar state).
- Non-sensitive UI state.
- Cache keys and non-sensitive cache data.

---

## Input Validation

### Validate on Both Client and Server

Client-side validation is for user experience. Server-side validation is for security. Never trust client-only validation.

```typescript
// DO: Client-side validation for UX
const CreateUserSchema = z.object({
  name: z.string().min(1, "Name is required").max(255, "Name too long"),
  email: z.string().email("Invalid email"),
  role: z.enum(["admin", "editor", "viewer"]),
});

// The server MUST also validate this data independently.
// A malicious client can bypass all frontend validation.
```

### Sanitize Before Display

Even if data comes from your own API, sanitize it before rendering if it was originally user-provided. A compromised API or database can serve XSS payloads.

```typescript
// DO: Treat all user-generated content as untrusted
function UserBio({ bio }: { bio: string }): React.ReactElement {
  // React JSX auto-escapes, so this is safe:
  return <p>{bio}</p>;

  // But if you must render HTML:
  // return <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(bio) }} />;
}
```

### Validate URL Parameters

URL parameters and search params are user input. Validate them before using them in API calls or rendering.

```typescript
// DO: Validate route params
function UserProfilePage(): React.ReactElement {
  const { userId } = useParams<{ userId: string }>();

  // Validate the param format before using it
  const validId = z.string().uuid().safeParse(userId);
  if (!validId.success) {
    return <NotFound />;
  }

  const { user } = useUser(validId.data);
  // ...
}
```

---

## Dependency Security

### npm Audit

Run `npm audit` (or `pnpm audit`) in CI on every build. Fail the build on critical or high severity vulnerabilities.

```yaml
# CI pipeline step
- name: Security audit
  run: pnpm audit --audit-level=high
```

### Lock File Integrity

Always commit your lock file (`package-lock.json`, `pnpm-lock.yaml`). Use `--frozen-lockfile` in CI to ensure reproducible builds.

```yaml
# CI pipeline step
- name: Install dependencies
  run: pnpm install --frozen-lockfile
```

### Minimize Dependencies

Before adding a dependency:

1. Check the package's download count, maintenance status, and known vulnerabilities.
2. Assess whether you can implement the needed functionality in-house (especially for small utilities).
3. Prefer well-known, actively maintained packages with a security policy.
4. Pin exact versions for critical dependencies.

### Renovate / Dependabot

Configure automated dependency updates. Review each update before merging, especially for packages that handle:

- Authentication and authorization
- Cryptography
- HTML sanitization
- URL parsing

---

## Environment Variables

### Client-Side Exposure

Environment variables prefixed with `VITE_` (Vite) or `NEXT_PUBLIC_` (Next.js) are embedded in the client bundle and visible to anyone who views the page source.

```typescript
// These are PUBLIC — anyone can see them:
const apiUrl = import.meta.env.VITE_API_URL; // OK: Public API endpoint
const analyticsId = import.meta.env.VITE_ANALYTICS_ID; // OK: Public tracking ID

// These MUST NEVER be in client-side env vars:
// VITE_DATABASE_URL        — exposes database credentials
// VITE_API_SECRET_KEY      — exposes server secrets
// VITE_STRIPE_SECRET_KEY   — exposes payment secrets
// NEXT_PUBLIC_JWT_SECRET   — exposes token signing key
```

### Rules

1. Never put API secrets, database credentials, or signing keys in `VITE_` or `NEXT_PUBLIC_` variables.
2. Do not hardcode secrets in source code.
3. Use server-side environment variables for secrets, and proxy requests through your backend.
4. Document all required environment variables in a `.env.example` file (without actual values).

```bash
# .env.example
VITE_API_URL=https://api.example.com
VITE_ANALYTICS_ID=UA-XXXXXXXXX
# Server-side only (not prefixed with VITE_):
# DATABASE_URL=postgresql://...
# JWT_SECRET=...
```

### Never Commit .env Files

Add `.env*` (except `.env.example`) to `.gitignore`. Verify this is in place in every project.

```gitignore
# .gitignore
.env
.env.local
.env.development
.env.production
```

---

## Content Security Policy

### Configure CSP Headers

Set Content Security Policy headers on your server or CDN to restrict what resources the browser is allowed to load.

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self';
  connect-src 'self' https://api.yourapp.com;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
```

### Frontend Implications

1. Do not use inline `<script>` tags. Bundle all JavaScript.
2. Do not use `eval()`, `new Function()`, or `setTimeout` with string arguments.
3. Do not load scripts from third-party CDNs unless they are explicitly allowlisted in the CSP.
4. Prefer `'self'` for all resource types and add specific origins only when needed.

```typescript
// DON'T: eval or Function constructor
eval(userInput);
const fn = new Function("return " + userInput);
setTimeout('alert("hello")', 0); // String argument = eval

// DO: Use proper functions
const fn = (input: string): number => parseInt(input, 10);
setTimeout(() => {
  alert("hello");
}, 0); // Function argument = safe
```

### CSP Nonce for Inline Scripts

If you must use inline scripts (e.g., for analytics), use a nonce-based CSP. The server generates a random nonce per request and includes it in both the CSP header and the script tag.

```html
<!-- Server sets header: Content-Security-Policy: script-src 'nonce-abc123' -->
<script nonce="abc123">
  // Analytics initialization
</script>
```

---

## Sensitive Data in Client Bundle

### What Must Never Be in the Bundle

1. API secret keys or private keys.
2. Database connection strings.
3. Encryption keys or JWT signing secrets.
4. Internal service URLs that should not be public.
5. User PII that the current user should not see (other users' emails, etc.).
6. Admin-only configuration.

### How to Verify

1. Build the production bundle: `pnpm build`.
2. Search the output for known secret patterns:

```bash
# Check for leaked secrets in the bundle
grep -r "sk_live\|sk_test\|PRIVATE_KEY\|-----BEGIN" dist/
grep -r "password\|secret\|token" dist/assets/*.js
```

3. Use a bundle analyzer to inspect all included code:

```bash
npx vite-bundle-visualizer
```

### Source Maps

Never deploy source maps to production. They expose your original source code to anyone who opens DevTools.

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    sourcemap: false, // Never true in production
  },
});
```

If you need source maps for error tracking (e.g., Sentry), upload them to the error tracking service and do not serve them publicly.

### Logging

Never log sensitive data (tokens, passwords, PII) to the browser console in production.

```typescript
// DO: Strip debug logs in production
if (import.meta.env.DEV) {
  console.log("Debug info:", data);
}

// DON'T: Log sensitive data
console.log("User token:", token);
console.log("API response:", { ...response, password: user.password });
```

Configure your build tool to strip `console.log` statements from production builds:

```typescript
// vite.config.ts
export default defineConfig({
  esbuild: {
    drop: import.meta.env.PROD ? ["console", "debugger"] : [],
  },
});
```

# TypeScript/React Coding Standards

These standards are mandatory for all TypeScript/React code in this project. Follow every rule unless a specific override is documented in the project's `.ai-engineering/config.yml`.

---

## Table of Contents

- [TypeScript Configuration and Strict Mode](#typescript-configuration-and-strict-mode)
- [Type-First Development](#type-first-development)
- [Interface vs Type Decisions](#interface-vs-type-decisions)
- [Generics Usage and Constraints](#generics-usage-and-constraints)
- [Utility Types](#utility-types)
- [React Component Patterns](#react-component-patterns)
- [Props Typing](#props-typing)
- [Hooks Rules](#hooks-rules)
- [State Management Patterns](#state-management-patterns)
- [File and Folder Organization](#file-and-folder-organization)
- [Import Ordering](#import-ordering)
- [Barrel Exports Policy](#barrel-exports-policy)
- [Error Boundaries](#error-boundaries)
- [Suspense and Lazy Loading](#suspense-and-lazy-loading)
- [Form Handling Patterns](#form-handling-patterns)
- [API Integration Patterns](#api-integration-patterns)
- [Styling Approach](#styling-approach)
- [Accessibility Requirements](#accessibility-requirements)
- [Performance Patterns](#performance-patterns)

---

## TypeScript Configuration and Strict Mode

### Required tsconfig.json Settings

Every project MUST enable the following compiler options. Do not weaken these settings.

```jsonc
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "exactOptionalPropertyTypes": true,
    "forceConsistentCasingInFileNames": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "moduleResolution": "bundler",
    "module": "ESNext",
    "target": "ES2022",
    "jsx": "react-jsx",
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "esModuleInterop": true,
  },
}
```

### No `any` Policy

Never use `any`. The only acceptable exceptions are:

1. Third-party library type definitions that genuinely require it (and even then, wrap the boundary).
2. Type assertion escape hatches that are immediately narrowed and commented with a justification.

```typescript
// DO: Use unknown and narrow
function parseResponse(data: unknown): User {
  if (!isUser(data)) {
    throw new TypeError("Invalid user data");
  }
  return data;
}

// DON'T: Use any
function parseResponse(data: any): User {
  return data;
}
```

When you encounter `any` in existing code, replace it with `unknown` and add a type guard, or replace it with a proper generic.

```typescript
// DO: Use a type guard to narrow unknown
function isUser(value: unknown): value is User {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    "name" in value &&
    typeof (value as User).id === "string" &&
    typeof (value as User).name === "string"
  );
}

// DON'T: Skip validation
function isUser(value: any): value is User {
  return value.id && value.name;
}
```

### Strict Null Checks

All values that can be `null` or `undefined` MUST be explicitly typed and handled. Never use the non-null assertion operator (`!`) unless you can prove the value exists and add a comment explaining why.

```typescript
// DO: Handle nullable values explicitly
function getUserName(user: User | null): string {
  if (!user) {
    return "Anonymous";
  }
  return user.name;
}

// DO: Use optional chaining
const city = user?.address?.city ?? "Unknown";

// DON'T: Use non-null assertion without justification
const city = user!.address!.city;

// ACCEPTABLE (rare): Non-null assertion with proof
// Element is guaranteed to exist because the component only renders after mount
const root = document.getElementById("root")!;
```

### Explicit Return Types

All exported functions and all functions longer than a single expression MUST have explicit return types. Internal single-expression arrow functions may rely on inference.

```typescript
// DO: Explicit return type on exported function
export function calculateTotal(items: CartItem[]): number {
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

// DO: Explicit return type on multi-line function
function formatUser(user: User): FormattedUser {
  const fullName = `${user.firstName} ${user.lastName}`;
  return {
    fullName,
    email: user.email.toLowerCase(),
    initials: `${user.firstName[0]}${user.lastName[0]}`,
  };
}

// OK: Inference on simple inline callback
const names = users.map((u) => u.name);

// DO: Explicit return type on React components
export function UserCard({ user }: UserCardProps): React.ReactElement {
  return <div>{user.name}</div>;
}
```

### Const Assertions and Enums

Prefer `as const` objects over TypeScript enums. Enums have runtime behavior that can cause unexpected bundle size and tree-shaking issues.

```typescript
// DO: Use const object + type derivation
export const STATUS = {
  IDLE: "idle",
  LOADING: "loading",
  SUCCESS: "success",
  ERROR: "error",
} as const;

export type Status = (typeof STATUS)[keyof typeof STATUS];

// DON'T: Use enum
enum Status {
  IDLE = "idle",
  LOADING = "loading",
  SUCCESS = "success",
  ERROR = "error",
}
```

### Discriminated Unions

Use discriminated unions for state machines and variant types. Always include an exhaustive check.

```typescript
// DO: Discriminated union with exhaustive handling
type AsyncState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: Error };

function renderState<T>(state: AsyncState<T>): string {
  switch (state.status) {
    case "idle":
      return "Ready";
    case "loading":
      return "Loading...";
    case "success":
      return `Data: ${state.data}`;
    case "error":
      return `Error: ${state.error.message}`;
    default: {
      const _exhaustive: never = state;
      return _exhaustive;
    }
  }
}
```

---

## Type-First Development

### Define Types Before Implementation

Always define the shape of your data and interfaces before writing implementation code. This applies to:

1. API response and request types
2. Component props
3. State shapes
4. Hook return types
5. Utility function signatures

```typescript
// DO: Define types first, then implement

// 1. Define the data shape
interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  createdAt: Date;
}

type UserRole = "admin" | "editor" | "viewer";

// 2. Define the API contract
interface UserApi {
  getUser(id: string): Promise<User>;
  updateUser(id: string, data: UpdateUserInput): Promise<User>;
  deleteUser(id: string): Promise<void>;
}

// 3. Define the input type
type UpdateUserInput = Pick<User, "name" | "email"> & {
  role?: UserRole;
};

// 4. Now implement
async function getUser(id: string): Promise<User> {
  const response = await api.get<User>(`/users/${id}`);
  return response.data;
}
```

### Co-locate Types with Their Domain

Types that are specific to a feature belong in that feature's directory. Shared types go in a `types/` directory at the appropriate level.

```
src/
  features/
    users/
      types.ts          # User-specific types
      api.ts            # Uses types from ./types.ts
      components/
        UserCard.tsx     # Props interface in the component file
  types/
    api.ts              # Shared API types (e.g., PaginatedResponse<T>)
    common.ts           # Truly shared types (e.g., Nullable<T>)
```

### Zod for Runtime Validation

Use Zod schemas for runtime validation at system boundaries (API responses, form data, URL params). Derive TypeScript types from Zod schemas to keep them in sync.

```typescript
// DO: Single source of truth with Zod
import { z } from "zod";

export const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string().min(1).max(255),
  role: z.enum(["admin", "editor", "viewer"]),
  createdAt: z.coerce.date(),
});

export type User = z.infer<typeof UserSchema>;

// Use at system boundary
function parseApiResponse(data: unknown): User {
  return UserSchema.parse(data);
}
```

---

## Interface vs Type Decisions

### When to Use `interface`

Use `interface` for:

1. Object shapes that define a public API contract (component props, service interfaces, data models).
2. Anything that might be extended or implemented by a class (rare in React).
3. Declaration merging scenarios (module augmentation).

```typescript
// DO: Interface for component props (public API)
interface ButtonProps {
  variant: "primary" | "secondary" | "danger";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

// DO: Interface for service contracts
interface AuthService {
  login(credentials: LoginCredentials): Promise<AuthToken>;
  logout(): Promise<void>;
  refreshToken(): Promise<AuthToken>;
}

// DO: Interface for data models
interface User {
  id: string;
  email: string;
  name: string;
  createdAt: Date;
}
```

### When to Use `type`

Use `type` for:

1. Unions and intersections.
2. Mapped types and conditional types.
3. Utility type derivations (Pick, Omit, etc.).
4. Function signatures.
5. Tuple types.
6. Primitive aliases with semantic meaning.

```typescript
// DO: Type for union
type Status = "idle" | "loading" | "success" | "error";

// DO: Type for derived types
type CreateUserInput = Omit<User, "id" | "createdAt">;
type UserSummary = Pick<User, "id" | "name">;

// DO: Type for function signatures
type EventHandler<T = void> = (event: T) => void;
type AsyncOperation<T> = () => Promise<T>;

// DO: Type for tuples
type Coordinate = [x: number, y: number];
type UseStateReturn<T> = [T, React.Dispatch<React.SetStateAction<T>>];

// DO: Type for intersections
type ButtonProps = BaseProps & AriaProps & { onClick: () => void };

// DO: Semantic primitive alias
type UserId = string;
type Milliseconds = number;
```

### Consistency Rule

Within a single file, be consistent. If a file primarily defines object shapes, use `interface` throughout. If it primarily defines unions and derived types, use `type` throughout. Do not alternate randomly.

---

## Generics Usage and Constraints

### Use Generics for Reusable Abstractions

Generics should be used when a function, component, or type needs to work with multiple types while preserving type safety.

```typescript
// DO: Generic data fetching hook
function useQuery<TData, TError = Error>(
  key: string,
  fetcher: () => Promise<TData>,
): UseQueryResult<TData, TError> {
  // ...
}

// DO: Generic list component
interface ListProps<TItem> {
  items: TItem[];
  renderItem: (item: TItem, index: number) => React.ReactElement;
  keyExtractor: (item: TItem) => string;
}

function List<TItem>({ items, renderItem, keyExtractor }: ListProps<TItem>): React.ReactElement {
  return (
    <ul>
      {items.map((item, index) => (
        <li key={keyExtractor(item)}>{renderItem(item, index)}</li>
      ))}
    </ul>
  );
}
```

### Constrain Generics

Always constrain generics to the minimum required shape. Never use an unconstrained generic when you need specific properties.

```typescript
// DO: Constrain to what you need
function getProperty<T extends Record<string, unknown>, K extends keyof T>(
  obj: T,
  key: K,
): T[K] {
  return obj[key];
}

// DO: Constrain with interface
interface HasId {
  id: string;
}

function findById<T extends HasId>(items: T[], id: string): T | undefined {
  return items.find((item) => item.id === id);
}

// DON'T: Unconstrained generic when you need properties
function getProperty<T>(obj: T, key: string): unknown {
  return (obj as Record<string, unknown>)[key];
}
```

### Generic Naming Conventions

Use descriptive names for generics when the meaning is not obvious from context. Single-letter names are acceptable only in well-known patterns.

```typescript
// OK: Single letter for well-known patterns
function identity<T>(value: T): T { return value; }
function map<T, U>(items: T[], fn: (item: T) => U): U[] { ... }

// DO: Descriptive names for domain-specific generics
function useQuery<TData, TError = Error>(...): ...
function createStore<TState, TActions>(...): ...
interface Repository<TEntity extends HasId> { ... }

// DON'T: Single letter when meaning is unclear
function process<A, B, C>(a: A, b: B): C { ... }
```

---

## Utility Types

### Standard Utility Types and When to Use Them

Use TypeScript's built-in utility types to derive types rather than duplicating definitions.

```typescript
interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  avatar: string | null;
  createdAt: Date;
  updatedAt: Date;
}

// Partial<T> — All properties optional (use for patch/update inputs)
type UpdateUserInput = Partial<Pick<User, "name" | "email" | "avatar">>;

// Required<T> — All properties required (use to enforce completeness)
type CompleteUserProfile = Required<User>;

// Pick<T, K> — Select specific properties
type UserSummary = Pick<User, "id" | "name" | "avatar">;

// Omit<T, K> — Exclude specific properties
type CreateUserInput = Omit<User, "id" | "createdAt" | "updatedAt">;

// Record<K, V> — Typed dictionary
type UsersByRole = Record<UserRole, User[]>;

// Readonly<T> — Immutable version
type FrozenUser = Readonly<User>;

// Extract / Exclude — For union manipulation
type WritableRole = Exclude<UserRole, "viewer">;
type AdminRole = Extract<UserRole, "admin" | "superadmin">;

// ReturnType<T> — Derive return type from function
type QueryResult = ReturnType<typeof useUserQuery>;

// Parameters<T> — Derive parameter types
type FetchParams = Parameters<typeof fetchUser>;
```

### Custom Utility Types

Define project-level utility types for recurring patterns.

```typescript
// Nullable — Explicitly nullable
type Nullable<T> = T | null;

// AsyncState — Standard async state shape
type AsyncState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: Error };

// DeepPartial — Recursive partial
type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

// StrictOmit — Omit that enforces valid keys
type StrictOmit<T, K extends keyof T> = Omit<T, K>;

// ValueOf — Extract value types from an object
type ValueOf<T> = T[keyof T];
```

---

## React Component Patterns

### Functional Components Only

Never use class components. All components MUST be functional components. There are no exceptions.

```typescript
// DO: Functional component with explicit return type
export function UserProfile({ user, onEdit }: UserProfileProps): React.ReactElement {
  return (
    <div className="user-profile">
      <h2>{user.name}</h2>
      <p>{user.email}</p>
      <button onClick={onEdit}>Edit</button>
    </div>
  );
}

// DON'T: Class component
class UserProfile extends React.Component<UserProfileProps> {
  render() {
    return <div>{this.props.user.name}</div>;
  }
}
```

### Component Declaration Style

Use named function declarations for top-level components. Use arrow functions for inline callbacks and small helpers within a component file.

```typescript
// DO: Named function declaration for components
export function UserCard({ user }: UserCardProps): React.ReactElement {
  // Local helper as arrow function is fine
  const getInitials = (name: string): string => {
    return name.split(' ').map((n) => n[0]).join('');
  };

  return <div>{getInitials(user.name)}</div>;
}

// DON'T: Arrow function for top-level component export
export const UserCard = ({ user }: UserCardProps): React.ReactElement => {
  return <div>{user.name}</div>;
};
```

The reason: named function declarations hoist, produce better stack traces, and are easier to find in profiler output.

### Do Not Use `React.FC`

Never use `React.FC` or `React.FunctionComponent`. These types add implicit `children` prop (in older React types), have issues with generics, and provide no benefit over explicit typing.

```typescript
// DO: Explicit props typing
function UserCard({ user }: UserCardProps): React.ReactElement {
  return <div>{user.name}</div>;
}

// DON'T: React.FC
const UserCard: React.FC<UserCardProps> = ({ user }) => {
  return <div>{user.name}</div>;
};
```

### Component Size Limits

A single component file MUST NOT exceed 300 lines. If a component approaches this limit, extract sub-components, custom hooks, or utility functions into separate files.

### Single Responsibility

Each component should do one thing. If a component handles data fetching, state management, and rendering complex UI, split it.

```typescript
// DO: Split responsibilities
// UserProfilePage.tsx — orchestrates data and layout
export function UserProfilePage(): React.ReactElement {
  const { user, isLoading, error } = useUser();

  if (isLoading) return <UserProfileSkeleton />;
  if (error) return <ErrorDisplay error={error} />;
  if (!user) return <NotFound />;

  return <UserProfile user={user} />;
}

// UserProfile.tsx — pure presentation
export function UserProfile({ user }: UserProfileProps): React.ReactElement {
  return (
    <section className="user-profile">
      <UserAvatar user={user} />
      <UserDetails user={user} />
      <UserActions userId={user.id} />
    </section>
  );
}
```

### Conditional Rendering

Use early returns for loading/error states. Use logical AND (`&&`) for simple conditionals. Never use nested ternaries.

```typescript
// DO: Early returns for loading and error states
export function UserList({ users, isLoading, error }: UserListProps): React.ReactElement {
  if (isLoading) {
    return <Skeleton count={5} />;
  }

  if (error) {
    return <ErrorMessage error={error} />;
  }

  if (users.length === 0) {
    return <EmptyState message="No users found" />;
  }

  return (
    <ul>
      {users.map((user) => (
        <UserListItem key={user.id} user={user} />
      ))}
    </ul>
  );
}

// DO: Simple conditional with &&
{isAdmin && <AdminPanel />}

// DO: Simple binary with ternary
{isLoggedIn ? <UserMenu /> : <LoginButton />}

// DON'T: Nested ternaries
{isLoading ? <Spinner /> : error ? <Error /> : data ? <Content /> : <Empty />}
```

---

## Props Typing

### Interface for Props

Always use `interface` for component props. Name the interface `{ComponentName}Props`.

```typescript
interface UserCardProps {
  user: User;
  variant?: "compact" | "full";
  onSelect?: (userId: string) => void;
}

export function UserCard({
  user,
  variant = "compact",
  onSelect,
}: UserCardProps): React.ReactElement {
  // ...
}
```

### Destructure Props in Parameters

Always destructure props in the function parameter. Never access `props.x` inside the component body.

```typescript
// DO: Destructure in params
function UserCard({ user, variant = 'compact', onSelect }: UserCardProps): React.ReactElement {
  return <div onClick={() => onSelect?.(user.id)}>{user.name}</div>;
}

// DON'T: Access props object
function UserCard(props: UserCardProps): React.ReactElement {
  return <div onClick={() => props.onSelect?.(props.user.id)}>{props.user.name}</div>;
}
```

### Default Values

Set default values using destructuring defaults, not `defaultProps`.

```typescript
// DO: Destructuring defaults
function Button({
  variant = 'primary',
  size = 'md',
  disabled = false,
  children,
}: ButtonProps): React.ReactElement {
  return <button className={`btn-${variant} btn-${size}`} disabled={disabled}>{children}</button>;
}

// DON'T: defaultProps (deprecated)
Button.defaultProps = {
  variant: 'primary',
  size: 'md',
};
```

### Children Typing

Explicitly type `children` when a component accepts them. Use `React.ReactNode` for general content.

```typescript
interface CardProps {
  title: string;
  children: React.ReactNode;
}

// For components that require specific children (e.g., render props):
interface DataTableProps<T> {
  data: T[];
  children: (item: T) => React.ReactElement;
}
```

### Extending HTML Elements

When wrapping a native HTML element, extend its props and use `ComponentPropsWithoutRef` or `ComponentPropsWithRef`.

```typescript
// DO: Extend native button props
interface ButtonProps extends React.ComponentPropsWithoutRef<'button'> {
  variant: 'primary' | 'secondary' | 'danger';
  isLoading?: boolean;
}

export function Button({
  variant,
  isLoading = false,
  disabled,
  children,
  ...rest
}: ButtonProps): React.ReactElement {
  return (
    <button
      className={`btn btn-${variant}`}
      disabled={disabled || isLoading}
      {...rest}
    >
      {isLoading ? <Spinner /> : children}
    </button>
  );
}

// DO: With ref forwarding
interface InputProps extends React.ComponentPropsWithRef<'input'> {
  label: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  function Input({ label, error, ...rest }, ref) {
    return (
      <div>
        <label>{label}</label>
        <input ref={ref} aria-invalid={!!error} {...rest} />
        {error && <span role="alert">{error}</span>}
      </div>
    );
  },
);
```

### Polymorphic `as` Prop

When building polymorphic components, type the `as` prop correctly.

```typescript
type PolymorphicProps<TElement extends React.ElementType, TProps = object> = TProps &
  Omit<React.ComponentPropsWithoutRef<TElement>, keyof TProps> & {
    as?: TElement;
  };

interface TextOwnProps {
  size?: 'sm' | 'md' | 'lg';
  weight?: 'normal' | 'bold';
}

type TextProps<TElement extends React.ElementType = 'span'> = PolymorphicProps<TElement, TextOwnProps>;

export function Text<TElement extends React.ElementType = 'span'>({
  as,
  size = 'md',
  weight = 'normal',
  ...rest
}: TextProps<TElement>): React.ReactElement {
  const Component = as ?? 'span';
  return <Component className={`text-${size} font-${weight}`} {...rest} />;
}

// Usage:
// <Text>inline text</Text>
// <Text as="p">paragraph</Text>
// <Text as="h1" size="lg">heading</Text>
```

---

## Hooks Rules

### Rules of Hooks (Enforced)

1. Only call hooks at the top level of a component or custom hook.
2. Never call hooks inside conditions, loops, or nested functions.
3. Never call hooks after an early return.

```typescript
// DO: All hooks at the top
function UserProfile({ userId }: { userId: string }): React.ReactElement {
  const [isEditing, setIsEditing] = useState(false);
  const { user, isLoading } = useUser(userId);
  const theme = useTheme();

  if (isLoading) return <Skeleton />;
  // ...
}

// DON'T: Hooks after early return
function UserProfile({ userId }: { userId: string }): React.ReactElement {
  const { user, isLoading } = useUser(userId);
  if (isLoading) return <Skeleton />;

  const theme = useTheme(); // VIOLATION: hook after early return
  // ...
}

// DON'T: Hooks inside conditions
function UserProfile({ userId }: { userId: string }): React.ReactElement {
  if (userId) {
    const { user } = useUser(userId); // VIOLATION: hook inside condition
  }
  // ...
}
```

### Custom Hook Extraction

Extract a custom hook when:

1. Two or more components share the same stateful logic.
2. A component's hook logic exceeds 15 lines.
3. Hook logic is independently testable.
4. The logic involves complex state + effect coordination.

Custom hooks MUST:

- Start with `use`.
- Have an explicit return type.
- Live in a dedicated file named `use-{name}.ts`.

```typescript
// DO: Extract complex hook logic
// use-debounced-value.ts
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
```

### Dependency Arrays

Always provide complete dependency arrays. Never suppress the `react-hooks/exhaustive-deps` ESLint rule without a comment explaining why.

```typescript
// DO: Complete dependency array
useEffect(() => {
  const controller = new AbortController();
  fetchUser(userId, { signal: controller.signal }).then(setUser);
  return () => controller.abort();
}, [userId]);

// DO: Use useCallback for stable function refs in deps
const handleSubmit = useCallback(
  (data: FormData) => {
    submitForm(data, userId);
  },
  [userId],
);

// DON'T: Missing dependencies
useEffect(() => {
  fetchUser(userId).then(setUser);
}, []); // Missing userId

// DON'T: Suppress without explanation
// eslint-disable-next-line react-hooks/exhaustive-deps
useEffect(() => { ... }, []);
```

### Hook Return Types

For hooks that return multiple values, prefer returning an object over a tuple (unless the hook mimics `useState`).

```typescript
// DO: Object return for complex hooks
interface UseUserReturn {
  user: User | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useUser(id: string): UseUserReturn {
  // ...
}

// OK: Tuple return for simple state-like hooks
export function useToggle(initial: boolean = false): [boolean, () => void] {
  const [value, setValue] = useState(initial);
  const toggle = useCallback(() => setValue((v) => !v), []);
  return [value, toggle];
}
```

---

## State Management Patterns

### useState

Use `useState` for:

- Simple, independent pieces of state (boolean flags, form field values, UI toggles).
- State that does not require complex update logic.
- State that is local to a single component.

```typescript
// DO: Simple independent states
const [isOpen, setIsOpen] = useState(false);
const [searchTerm, setSearchTerm] = useState("");
const [selectedId, setSelectedId] = useState<string | null>(null);

// DO: Lazy initialization for expensive computations
const [data, setData] = useState<ProcessedData>(() => {
  return expensiveComputation(rawData);
});
```

### useReducer

Use `useReducer` when:

- State has multiple sub-values that change together.
- Next state depends on previous state in complex ways.
- State transitions follow well-defined rules.
- You need to pass dispatch down instead of multiple callbacks.

```typescript
// DO: Reducer for complex coordinated state
interface FormState {
  values: Record<string, string>;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
  isSubmitting: boolean;
}

type FormAction =
  | { type: "SET_FIELD"; field: string; value: string }
  | { type: "SET_ERROR"; field: string; error: string }
  | { type: "TOUCH_FIELD"; field: string }
  | { type: "SUBMIT_START" }
  | { type: "SUBMIT_SUCCESS" }
  | { type: "SUBMIT_FAILURE"; errors: Record<string, string> }
  | { type: "RESET" };

function formReducer(state: FormState, action: FormAction): FormState {
  switch (action.type) {
    case "SET_FIELD":
      return {
        ...state,
        values: { ...state.values, [action.field]: action.value },
        errors: { ...state.errors, [action.field]: "" },
      };
    case "SUBMIT_START":
      return { ...state, isSubmitting: true };
    case "SUBMIT_SUCCESS":
      return { ...state, isSubmitting: false };
    case "SUBMIT_FAILURE":
      return { ...state, isSubmitting: false, errors: action.errors };
    case "RESET":
      return initialFormState;
    default: {
      const _exhaustive: never = action;
      return _exhaustive;
    }
  }
}
```

### Context

Use React Context for:

- Theme or locale that many components need.
- Authenticated user data.
- Feature flags.
- Avoiding prop drilling through 3+ levels for widely-used data.

Do NOT use Context for:

- High-frequency updates (use a state library or signals instead).
- Data that only a few components need (pass as props).
- Server-state caching (use React Query / SWR).

```typescript
// DO: Typed context with null check
interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function AuthProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  // ... state management logic
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
```

### When to Use External State Libraries

Use Zustand, Jotai, or similar lightweight libraries when:

- Global state changes frequently and causes unnecessary re-renders with Context.
- You need state that persists across navigations.
- You need computed/derived state with subscription granularity.
- Multiple independent stores are cleaner than a single Context tree.

```typescript
// DO: Zustand for global UI state
import { create } from "zustand";

interface SidebarStore {
  isOpen: boolean;
  toggle: () => void;
  open: () => void;
  close: () => void;
}

export const useSidebarStore = create<SidebarStore>((set) => ({
  isOpen: false,
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
}));
```

---

## File and Folder Organization

### Feature-Based Structure

Organize by feature, not by file type. Each feature is a self-contained module.

```
src/
  features/
    auth/
      components/
        LoginForm.tsx
        LoginForm.test.tsx
        SignupForm.tsx
        AuthGuard.tsx
      hooks/
        use-auth.ts
        use-auth.test.ts
        use-login-form.ts
      api/
        auth-api.ts
        auth-api.test.ts
      types.ts
      constants.ts
      index.ts              # Barrel export of public API
    users/
      components/
        UserList.tsx
        UserCard.tsx
        UserProfile.tsx
      hooks/
        use-user.ts
        use-user-list.ts
      api/
        users-api.ts
      types.ts
      index.ts
  shared/
    components/
      Button/
        Button.tsx
        Button.test.tsx
        Button.module.css
        index.ts
      Input/
      Modal/
    hooks/
      use-debounce.ts
      use-media-query.ts
      use-local-storage.ts
    utils/
      format.ts
      validation.ts
    types/
      api.ts
      common.ts
  app/
    layout.tsx
    routes.tsx
    providers.tsx
```

### File Naming Conventions

| Type         | Convention                     | Example                          |
| ------------ | ------------------------------ | -------------------------------- |
| Component    | PascalCase                     | `UserCard.tsx`                   |
| Hook         | kebab-case with `use-` prefix  | `use-auth.ts`                    |
| Utility      | kebab-case                     | `format-date.ts`                 |
| Type file    | kebab-case or `types.ts`       | `types.ts`, `api-types.ts`       |
| Test file    | Same name + `.test`            | `UserCard.test.tsx`              |
| Style module | Same name + `.module.css`      | `UserCard.module.css`            |
| Constants    | kebab-case                     | `constants.ts`, `route-paths.ts` |
| Context      | PascalCase with Context suffix | `AuthContext.tsx`                |

### One Component Per File

Each file exports one primary component. Small helper components used only by that component may live in the same file, but must be unexported.

```typescript
// UserCard.tsx
// OK: Private helper in same file
function UserAvatar({ src, name }: { src: string; name: string }): React.ReactElement {
  return <img src={src} alt={name} className="avatar" />;
}

// Primary export
export function UserCard({ user }: UserCardProps): React.ReactElement {
  return (
    <div>
      <UserAvatar src={user.avatar} name={user.name} />
      <span>{user.name}</span>
    </div>
  );
}
```

---

## Import Ordering

### Required Order

Imports MUST follow this order, separated by blank lines:

1. React and React-related packages
2. External libraries (npm packages)
3. Internal absolute imports (aliases like `@/`)
4. Relative imports (parent → sibling → children)
5. Type-only imports
6. Side-effect imports (CSS, polyfills)

```typescript
// 1. React
import { useState, useCallback, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";

// 2. External libraries
import { z } from "zod";
import { useQuery, useMutation } from "@tanstack/react-query";
import clsx from "clsx";

// 3. Internal absolute imports
import { Button } from "@/shared/components/Button";
import { useAuth } from "@/features/auth";
import { api } from "@/shared/api/client";

// 4. Relative imports
import { UserAvatar } from "./UserAvatar";
import { formatUserName } from "../utils/format";
import { USER_ROLES } from "./constants";

// 5. Type-only imports
import type { User, UserRole } from "../types";
import type { ApiResponse } from "@/shared/types/api";

// 6. Side-effect imports
import "./UserCard.css";
```

### Use `type` Imports

Always use `import type` for type-only imports. This ensures types are erased at compile time and prevents circular dependency issues.

```typescript
// DO: Separate type imports
import type { User, UserRole } from "./types";
import { formatUser } from "./utils";

// DON'T: Mix types with value imports
import { User, UserRole, formatUser } from "./module";
```

---

## Barrel Exports Policy

### When to Use Barrel Exports

Use `index.ts` barrel exports at the feature boundary to define the feature's public API.

```typescript
// features/auth/index.ts
export { AuthProvider } from "./components/AuthProvider";
export { AuthGuard } from "./components/AuthGuard";
export { LoginForm } from "./components/LoginForm";
export { useAuth } from "./hooks/use-auth";
export type { AuthContextValue, LoginCredentials } from "./types";
```

### When NOT to Use Barrel Exports

1. Do NOT create barrels inside `components/`, `hooks/`, or `utils/` subdirectories within a feature. Import directly.
2. Do NOT re-export everything. Only export what other features need.
3. Do NOT create deeply nested barrel chains (barrel importing from barrel importing from barrel).
4. Do NOT use barrels for the `shared/` directory if the project uses tree-shaking-unfriendly bundler configurations.

```typescript
// DON'T: Barrel inside components subfolder
// features/auth/components/index.ts <-- unnecessary

// DON'T: Re-export everything
export * from "./types";
export * from "./hooks/use-auth";
export * from "./utils";

// DO: Explicit, curated exports
export { useAuth } from "./hooks/use-auth";
export type { AuthContextValue } from "./types";
```

### Import from Barrels

When a feature has a barrel export, always import from the barrel, not from internal files.

```typescript
// DO: Import from barrel
import { useAuth, AuthGuard } from "@/features/auth";

// DON'T: Reach into feature internals
import { useAuth } from "@/features/auth/hooks/use-auth";
```

---

## Error Boundaries

### Every Feature Route Gets an Error Boundary

Wrap each top-level route or feature section with an error boundary to prevent one failing component from taking down the entire app.

```typescript
// DO: Error boundary component
import { Component } from "react";

interface ErrorBoundaryProps {
  fallback:
    | React.ReactNode
    | ((error: Error, reset: () => void) => React.ReactNode);
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    this.props.onError?.(error, errorInfo);
  }

  private reset = (): void => {
    this.setState({ error: null });
  };

  render(): React.ReactNode {
    if (this.state.error) {
      const { fallback } = this.props;
      if (typeof fallback === "function") {
        return fallback(this.state.error, this.reset);
      }
      return fallback;
    }
    return this.props.children;
  }
}
```

Note: Error boundaries are the one exception to the "no class components" rule, because React does not yet provide a hook-based error boundary API.

### Usage Pattern

```typescript
// DO: Wrap route-level components
function App(): React.ReactElement {
  return (
    <ErrorBoundary fallback={(error, reset) => <ErrorPage error={error} onRetry={reset} />}>
      <Suspense fallback={<AppSkeleton />}>
        <RouterProvider router={router} />
      </Suspense>
    </ErrorBoundary>
  );
}

// DO: Wrap individual features for isolation
function DashboardPage(): React.ReactElement {
  return (
    <div className="dashboard">
      <ErrorBoundary fallback={<WidgetError />}>
        <AnalyticsWidget />
      </ErrorBoundary>
      <ErrorBoundary fallback={<WidgetError />}>
        <RecentActivityWidget />
      </ErrorBoundary>
    </div>
  );
}
```

---

## Suspense and Lazy Loading

### Route-Level Code Splitting

Lazy-load route components. Never lazy-load small shared components.

```typescript
import { lazy, Suspense } from 'react';

// DO: Lazy load route-level components
const Dashboard = lazy(() => import('./features/dashboard/DashboardPage'));
const Settings = lazy(() => import('./features/settings/SettingsPage'));
const UserProfile = lazy(() => import('./features/users/UserProfilePage'));

function AppRoutes(): React.ReactElement {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/users/:id" element={<UserProfile />} />
      </Routes>
    </Suspense>
  );
}

// DON'T: Lazy load small components
const Button = lazy(() => import('./shared/components/Button')); // Unnecessary
```

### Named Exports with Lazy Loading

When a module uses named exports, wrap the import:

```typescript
// Module exports: export function SettingsPage() { ... }
const Settings = lazy(() =>
  import("./features/settings/SettingsPage").then((mod) => ({
    default: mod.SettingsPage,
  })),
);
```

### Suspense Boundaries

Place Suspense boundaries at meaningful UI boundaries, not at every lazy component.

```typescript
// DO: Suspense at layout boundary
function AppLayout({ children }: { children: React.ReactNode }): React.ReactElement {
  return (
    <div className="app-layout">
      <Header />
      <Sidebar />
      <main>
        <Suspense fallback={<ContentSkeleton />}>
          {children}
        </Suspense>
      </main>
    </div>
  );
}
```

---

## Form Handling Patterns

### Use a Form Library

Use React Hook Form (preferred) or Formik for all forms with more than two fields. Do not hand-roll form state management for complex forms.

```typescript
// DO: React Hook Form with Zod validation
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const CreateUserSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255),
  email: z.string().email('Invalid email address'),
  role: z.enum(['admin', 'editor', 'viewer']),
});

type CreateUserFormData = z.infer<typeof CreateUserSchema>;

export function CreateUserForm({ onSubmit }: CreateUserFormProps): React.ReactElement {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateUserFormData>({
    resolver: zodResolver(CreateUserSchema),
    defaultValues: {
      name: '',
      email: '',
      role: 'viewer',
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <div>
        <label htmlFor="name">Name</label>
        <input id="name" {...register('name')} aria-invalid={!!errors.name} />
        {errors.name && <span role="alert">{errors.name.message}</span>}
      </div>

      <div>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" {...register('email')} aria-invalid={!!errors.email} />
        {errors.email && <span role="alert">{errors.email.message}</span>}
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Creating...' : 'Create User'}
      </button>
    </form>
  );
}
```

### Simple Forms

For forms with one or two fields (search, single toggle), `useState` is acceptable.

```typescript
// OK: Simple search form
function SearchBar({ onSearch }: { onSearch: (term: string) => void }): React.ReactElement {
  const [term, setTerm] = useState('');

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    onSearch(term);
  };

  return (
    <form onSubmit={handleSubmit} role="search">
      <label htmlFor="search" className="sr-only">Search</label>
      <input
        id="search"
        type="search"
        value={term}
        onChange={(e) => setTerm(e.target.value)}
        placeholder="Search..."
      />
      <button type="submit">Search</button>
    </form>
  );
}
```

### Controlled vs Uncontrolled

Prefer uncontrolled inputs with React Hook Form for performance. Use controlled inputs only when you need to react to every keystroke (search-as-you-type, character counters).

---

## API Integration Patterns

### Typed API Client

Create a typed API client layer. Never call `fetch` directly from components.

```typescript
// shared/api/client.ts
interface ApiConfig {
  baseUrl: string;
  getAuthToken: () => string | null;
}

interface ApiError {
  status: number;
  message: string;
  code: string;
}

class ApiClient {
  constructor(private readonly config: ApiConfig) {}

  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    return this.request<T>("GET", path, undefined, params);
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>("POST", path, body);
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>("PUT", path, body);
  }

  async delete(path: string): Promise<void> {
    await this.request<void>("DELETE", path);
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    params?: Record<string, string>,
  ): Promise<T> {
    const url = new URL(path, this.config.baseUrl);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.set(key, value);
      });
    }

    const token = this.config.getAuthToken();
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    const response = await fetch(url.toString(), {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new ApiRequestError(error.message, response.status, error.code);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }
}

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export const api = new ApiClient({
  baseUrl: import.meta.env.VITE_API_BASE_URL,
  getAuthToken: () => localStorage.getItem("token"), // Or from auth context
});
```

### React Query / SWR Integration

Use React Query (TanStack Query) for server state management. Define query and mutation functions in feature-specific API modules.

```typescript
// features/users/api/users-api.ts
import { api } from "@/shared/api/client";
import { UserSchema, UsersListSchema } from "../types";

import type { User, CreateUserInput, UpdateUserInput } from "../types";

export const usersApi = {
  getUser: async (id: string): Promise<User> => {
    const data = await api.get<unknown>(`/users/${id}`);
    return UserSchema.parse(data);
  },

  listUsers: async (params?: {
    page?: number;
    limit?: number;
  }): Promise<User[]> => {
    const data = await api.get<unknown>(
      "/users",
      params as Record<string, string>,
    );
    return UsersListSchema.parse(data);
  },

  createUser: async (input: CreateUserInput): Promise<User> => {
    const data = await api.post<unknown>("/users", input);
    return UserSchema.parse(data);
  },

  updateUser: async (id: string, input: UpdateUserInput): Promise<User> => {
    const data = await api.put<unknown>(`/users/${id}`, input);
    return UserSchema.parse(data);
  },

  deleteUser: async (id: string): Promise<void> => {
    await api.delete(`/users/${id}`);
  },
};

// features/users/hooks/use-user.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { usersApi } from "../api/users-api";

import type { User, CreateUserInput } from "../types";

export const userKeys = {
  all: ["users"] as const,
  lists: () => [...userKeys.all, "list"] as const,
  list: (params: Record<string, unknown>) =>
    [...userKeys.lists(), params] as const,
  details: () => [...userKeys.all, "detail"] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
};

export function useUser(id: string): {
  user: User | undefined;
  isLoading: boolean;
  error: Error | null;
} {
  const { data, isLoading, error } = useQuery({
    queryKey: userKeys.detail(id),
    queryFn: () => usersApi.getUser(id),
  });

  return { user: data, isLoading, error };
}

export function useCreateUser(): {
  createUser: (input: CreateUserInput) => Promise<User>;
  isCreating: boolean;
} {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: usersApi.createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
  });

  return {
    createUser: mutation.mutateAsync,
    isCreating: mutation.isPending,
  };
}
```

---

## Styling Approach

### Choose One Approach Per Project

Each project MUST use exactly one primary styling approach. Document the choice in the project's configuration. The supported approaches are:

1. **Tailwind CSS** (preferred for new projects)
2. **CSS Modules**
3. **styled-components / Emotion** (only for existing projects)

### Tailwind CSS Conventions

When using Tailwind:

```typescript
// DO: Use clsx/cn for conditional classes
import { clsx } from 'clsx';

interface ButtonProps {
  variant: 'primary' | 'secondary';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  children: React.ReactNode;
}

const variantStyles = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
} as const;

const sizeStyles = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
} as const;

export function Button({ variant, size, disabled, children }: ButtonProps): React.ReactElement {
  return (
    <button
      className={clsx(
        'rounded font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
        variantStyles[variant],
        sizeStyles[size],
        disabled && 'opacity-50 cursor-not-allowed',
      )}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

// DON'T: Inline long class strings without organization
<button className="bg-blue-600 text-white hover:bg-blue-700 px-4 py-2 rounded font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed text-base">
  Click me
</button>
```

### CSS Modules Conventions

When using CSS Modules:

```typescript
// UserCard.module.css
.card {
  display: flex;
  align-items: center;
  padding: 1rem;
  border-radius: 0.5rem;
}

.card--compact {
  padding: 0.5rem;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

// UserCard.tsx
import styles from './UserCard.module.css';
import clsx from 'clsx';

export function UserCard({ user, compact }: UserCardProps): React.ReactElement {
  return (
    <div className={clsx(styles.card, compact && styles['card--compact'])}>
      <img className={styles.avatar} src={user.avatar} alt="" />
      <span>{user.name}</span>
    </div>
  );
}
```

### No Inline Styles

Never use the `style` prop for static styling. Inline styles are acceptable only for truly dynamic values (e.g., calculated positions, user-defined colors).

```typescript
// OK: Dynamic value that cannot be known at build time
<div style={{ transform: `translateX(${offset}px)` }} />
<div style={{ backgroundColor: user.themeColor }} />

// DON'T: Static styling via style prop
<div style={{ display: 'flex', gap: '1rem', padding: '16px' }} />
```

---

## Accessibility Requirements

### Semantic HTML First

Always use the correct semantic HTML element before reaching for ARIA attributes.

```typescript
// DO: Semantic HTML
<nav aria-label="Main navigation">
  <ul>
    <li><a href="/dashboard">Dashboard</a></li>
    <li><a href="/settings">Settings</a></li>
  </ul>
</nav>

<main>
  <article>
    <h1>Page Title</h1>
    <p>Content...</p>
  </article>
</main>

<button onClick={handleClick}>Submit</button>

// DON'T: Div soup with ARIA band-aids
<div role="navigation">
  <div role="list">
    <div role="listitem"><div role="link" onClick={...}>Dashboard</div></div>
  </div>
</div>

<div onClick={handleClick} role="button" tabIndex={0}>Submit</div>
```

### Required ARIA Patterns

```typescript
// Form inputs MUST have labels
<label htmlFor="email">Email</label>
<input id="email" type="email" aria-describedby="email-hint" />
<p id="email-hint">We will never share your email.</p>

// Error messages MUST use role="alert"
{error && <p role="alert" className="error">{error}</p>}

// Modals MUST trap focus and have aria-modal
<dialog open aria-modal="true" aria-labelledby="modal-title">
  <h2 id="modal-title">Confirm Delete</h2>
  <p>Are you sure?</p>
  <button onClick={onCancel}>Cancel</button>
  <button onClick={onConfirm}>Delete</button>
</dialog>

// Images MUST have alt text (empty string for decorative images)
<img src={user.avatar} alt={`${user.name}'s profile photo`} />
<img src="/decorative-divider.svg" alt="" />

// Loading states MUST be announced
<div aria-live="polite" aria-busy={isLoading}>
  {isLoading ? 'Loading...' : content}
</div>

// Icons used as buttons MUST have accessible labels
<button aria-label="Close dialog" onClick={onClose}>
  <CloseIcon aria-hidden="true" />
</button>
```

### Keyboard Navigation

All interactive elements MUST be keyboard accessible:

1. All clickable elements must be focusable (`<button>`, `<a>`, or `tabIndex={0}`).
2. Custom components must handle `Enter` and `Space` for activation.
3. Dropdown menus must support arrow keys.
4. Modals must trap focus.
5. Escape must close overlays.

```typescript
// DO: Keyboard-accessible custom component
function Dropdown({ items, onSelect }: DropdownProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const handleKeyDown = (e: React.KeyboardEvent): void => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveIndex((prev) => Math.min(prev + 1, items.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveIndex((prev) => Math.max(prev - 1, 0));
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        if (activeIndex >= 0) {
          onSelect(items[activeIndex]);
          setIsOpen(false);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        break;
    }
  };

  return (
    <div onKeyDown={handleKeyDown}>
      <button
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)}
      >
        Select an item
      </button>
      {isOpen && (
        <ul role="listbox">
          {items.map((item, index) => (
            <li
              key={item.id}
              role="option"
              aria-selected={index === activeIndex}
              onClick={() => onSelect(item)}
            >
              {item.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

### Color Contrast

All text MUST meet WCAG 2.1 AA contrast requirements:

- Normal text: 4.5:1 minimum contrast ratio.
- Large text (18px+ bold or 24px+): 3:1 minimum.
- UI components and graphics: 3:1 minimum.

### Skip Navigation

Every page MUST have a "Skip to main content" link as the first focusable element.

```typescript
// DO: Skip navigation link
function AppLayout({ children }: { children: React.ReactNode }): React.ReactElement {
  return (
    <>
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4">
        Skip to main content
      </a>
      <Header />
      <main id="main-content" tabIndex={-1}>
        {children}
      </main>
      <Footer />
    </>
  );
}
```

---

## Performance Patterns

### useMemo

Use `useMemo` only when:

1. Computing a value is genuinely expensive (sorting/filtering large lists, complex transformations).
2. The computed value is passed as a prop to a memoized child component and would cause unnecessary re-renders.

```typescript
// DO: Expensive computation
const sortedUsers = useMemo(() => {
  return [...users].sort((a, b) => a.name.localeCompare(b.name));
}, [users]);

// DO: Object passed to memoized child
const chartConfig = useMemo(() => ({
  labels: data.map((d) => d.label),
  values: data.map((d) => d.value),
  colors: generateColors(data.length),
}), [data]);

return <MemoizedChart config={chartConfig} />;

// DON'T: Simple derivation (just compute it)
const fullName = useMemo(() => `${user.first} ${user.last}`, [user.first, user.last]);
// Instead:
const fullName = `${user.first} ${user.last}`;
```

### useCallback

Use `useCallback` only when:

1. Passing a callback to a memoized child component (`React.memo`).
2. The callback is a dependency of another hook's dependency array.
3. The callback is used in a `useEffect` dependency array.

```typescript
// DO: Callback passed to memoized child
const handleSelect = useCallback((id: string) => {
  setSelectedId(id);
}, []);

return <MemoizedList items={items} onSelect={handleSelect} />;

// DO: Callback used as effect dependency
const fetchData = useCallback(async () => {
  const data = await api.get(`/items/${category}`);
  setItems(data);
}, [category]);

useEffect(() => {
  fetchData();
}, [fetchData]);

// DON'T: Unnecessary useCallback
const handleClick = useCallback(() => {
  setCount((c) => c + 1);
}, []);
// Just use a plain function if the child is not memoized:
const handleClick = (): void => {
  setCount((c) => c + 1);
};
```

### React.memo

Use `React.memo` only for components that:

1. Render often with the same props.
2. Perform non-trivial rendering (large trees, complex calculations).
3. Have been profiled and confirmed to cause performance issues.

```typescript
// DO: Memo a list item that re-renders frequently
export const UserListItem = React.memo(function UserListItem({
  user,
  onSelect,
}: UserListItemProps): React.ReactElement {
  return (
    <li onClick={() => onSelect(user.id)}>
      <img src={user.avatar} alt="" />
      <span>{user.name}</span>
      <span>{user.email}</span>
    </li>
  );
});

// DO: Custom comparison when needed
export const ExpensiveChart = React.memo(
  function ExpensiveChart({ data, config }: ChartProps): React.ReactElement {
    // expensive rendering
  },
  (prevProps, nextProps) => {
    return (
      prevProps.data === nextProps.data &&
      prevProps.config.type === nextProps.config.type
    );
  },
);

// DON'T: Memo everything by default
export const SimpleText = React.memo(function SimpleText({ text }: { text: string }) {
  return <span>{text}</span>; // Too cheap to memo
});
```

### Virtualization

For lists longer than 50 items, use virtualization (react-window or @tanstack/react-virtual).

```typescript
// DO: Virtualize long lists
import { useVirtualizer } from '@tanstack/react-virtual';

function VirtualizedList({ items }: { items: User[] }): React.ReactElement {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,
  });

  return (
    <div ref={parentRef} style={{ height: '400px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              transform: `translateY(${virtualItem.start}px)`,
              height: `${virtualItem.size}px`,
              width: '100%',
            }}
          >
            <UserListItem user={items[virtualItem.index]!} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Image Optimization

1. Always provide `width` and `height` attributes (or use aspect-ratio CSS) to prevent layout shift.
2. Use `loading="lazy"` for images below the fold.
3. Use modern formats (WebP, AVIF) with fallbacks.
4. Use responsive `srcSet` for varying viewport sizes.

```typescript
// DO: Optimized image
<img
  src="/images/hero.webp"
  alt="Dashboard overview"
  width={1200}
  height={630}
  loading="lazy"
  decoding="async"
/>
```

### Bundle Size Awareness

1. Check import cost before adding a dependency.
2. Use dynamic imports for large libraries used in few places.
3. Prefer lighter alternatives (date-fns over moment, clsx over classnames).
4. Use bundle analyzer regularly to track growth.

```typescript
// DO: Dynamic import for large, rarely-used library
const handleExport = async (): Promise<void> => {
  const { exportToExcel } = await import("./utils/excel-export");
  await exportToExcel(data);
};

// DON'T: Static import of large library used in one place
import * as XLSX from "xlsx";
```

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
it("filters users by search term", () => {
  // Arrange
  const users = [
    createUser({ name: "Alice Johnson" }),
    createUser({ name: "Bob Smith" }),
    createUser({ name: "Alice Cooper" }),
  ];

  // Act
  const result = filterUsers(users, "Alice");

  // Assert
  expect(result).toHaveLength(2);
  expect(result.map((u) => u.name)).toEqual(["Alice Johnson", "Alice Cooper"]);
});
```

### Test Factories

Use factory functions to create test data. Never hardcode test objects inline in every test.

```typescript
// test/factories/user.ts
import type { User } from "@/features/users/types";

let idCounter = 0;

export function createUser(overrides: Partial<User> = {}): User {
  idCounter += 1;
  return {
    id: `user-${idCounter}`,
    name: `Test User ${idCounter}`,
    email: `user${idCounter}@test.com`,
    role: "viewer",
    avatar: null,
    createdAt: new Date("2024-01-01"),
    updatedAt: new Date("2024-01-01"),
    ...overrides,
  };
}

// Usage in tests
const admin = createUser({ name: "Admin", role: "admin" });
const viewer = createUser({ name: "Viewer", role: "viewer" });
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
const submitButton = screen.getByRole("button", { name: /submit/i });
const nameInput = screen.getByRole("textbox", { name: /name/i });
const heading = screen.getByRole("heading", { level: 1 });

// DO: Query by label for form fields
const emailInput = screen.getByLabelText(/email/i);

// ACCEPTABLE: getByTestId when no semantic query works
const complexWidget = screen.getByTestId("color-picker");

// DON'T: Query by CSS class or DOM structure
const button = container.querySelector(".submit-btn"); // Never
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
import { renderHook, act } from "@testing-library/react";
import { useToggle } from "./use-toggle";

describe("useToggle", () => {
  it("initializes with the provided value", () => {
    const { result } = renderHook(() => useToggle(true));

    expect(result.current[0]).toBe(true);
  });

  it("toggles the value when toggle is called", () => {
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
describe("useDebouncedValue", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns the initial value immediately", () => {
    const { result } = renderHook(() => useDebouncedValue("hello", 300));

    expect(result.current).toBe("hello");
  });

  it("debounces value changes", () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebouncedValue(value, 300),
      { initialProps: { value: "hello" } },
    );

    rerender({ value: "world" });
    expect(result.current).toBe("hello"); // Not yet updated

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current).toBe("world"); // Now updated
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
vi.mock("@/shared/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from "@/shared/api/client";

describe("usersApi", () => {
  it("fetches a user by id", async () => {
    const mockUser = createUser({ id: "user-1" });
    vi.mocked(api.get).mockResolvedValue(mockUser);

    const result = await usersApi.getUser("user-1");

    expect(api.get).toHaveBeenCalledWith("/users/user-1");
    expect(result).toEqual(mockUser);
  });
});
```

### MSW for API Mocking

Use Mock Service Worker (MSW) for integration tests that involve API calls. MSW intercepts at the network level, so your actual fetch logic is tested.

```typescript
// test/mocks/handlers.ts
import { http, HttpResponse } from "msw";
import { createUser } from "../factories/user";

export const handlers = [
  http.get("/api/users", () => {
    return HttpResponse.json([
      createUser({ name: "Alice" }),
      createUser({ name: "Bob" }),
    ]);
  }),

  http.get("/api/users/:id", ({ params }) => {
    return HttpResponse.json(createUser({ id: params.id as string }));
  }),

  http.post("/api/users", async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json(createUser(body as Partial<User>), {
      status: 201,
    });
  }),

  http.delete("/api/users/:id", () => {
    return new HttpResponse(null, { status: 204 });
  }),
];

// test/mocks/server.ts
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);

// test/setup.ts (vitest setup file)
import { server } from "./mocks/server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
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
it("generates the correct API request body", () => {
  const body = buildCreateUserRequest({ name: "Jane", email: "jane@test.com" });
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

| File Type                 | Line Coverage | Branch Coverage | Notes                                     |
| ------------------------- | :-----------: | :-------------: | ----------------------------------------- |
| Utility functions         |      95%      |       90%       | Pure logic, easy to test exhaustively     |
| Custom hooks              |      90%      |       85%       | Test all state transitions and edge cases |
| API modules               |      85%      |       80%       | Test success, error, and edge cases       |
| Components (presentation) |      85%      |       80%       | Test rendering, interactions, states      |
| Components (container)    |      75%      |       70%       | Integration coverage fills gaps           |
| Type files                |      N/A      |       N/A       | Types have no runtime code                |
| Configuration files       |      N/A      |       N/A       | Not worth unit testing                    |

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
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      thresholds: {
        statements: 80,
        branches: 75,
        functions: 80,
        lines: 80,
      },
      exclude: [
        "node_modules/",
        "test/",
        "**/*.d.ts",
        "**/*.config.*",
        "**/types.ts",
        "**/index.ts", // Barrel exports
      ],
    },
  },
});
```
