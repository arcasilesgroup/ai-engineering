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
    "esModuleInterop": true
  }
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
    throw new TypeError('Invalid user data');
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
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'name' in value &&
    typeof (value as User).id === 'string' &&
    typeof (value as User).name === 'string'
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
    return 'Anonymous';
  }
  return user.name;
}

// DO: Use optional chaining
const city = user?.address?.city ?? 'Unknown';

// DON'T: Use non-null assertion without justification
const city = user!.address!.city;

// ACCEPTABLE (rare): Non-null assertion with proof
// Element is guaranteed to exist because the component only renders after mount
const root = document.getElementById('root')!;
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
  IDLE: 'idle',
  LOADING: 'loading',
  SUCCESS: 'success',
  ERROR: 'error',
} as const;

export type Status = (typeof STATUS)[keyof typeof STATUS];

// DON'T: Use enum
enum Status {
  IDLE = 'idle',
  LOADING = 'loading',
  SUCCESS = 'success',
  ERROR = 'error',
}
```

### Discriminated Unions

Use discriminated unions for state machines and variant types. Always include an exhaustive check.

```typescript
// DO: Discriminated union with exhaustive handling
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };

function renderState<T>(state: AsyncState<T>): string {
  switch (state.status) {
    case 'idle':
      return 'Ready';
    case 'loading':
      return 'Loading...';
    case 'success':
      return `Data: ${state.data}`;
    case 'error':
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

type UserRole = 'admin' | 'editor' | 'viewer';

// 2. Define the API contract
interface UserApi {
  getUser(id: string): Promise<User>;
  updateUser(id: string, data: UpdateUserInput): Promise<User>;
  deleteUser(id: string): Promise<void>;
}

// 3. Define the input type
type UpdateUserInput = Pick<User, 'name' | 'email'> & {
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
import { z } from 'zod';

export const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string().min(1).max(255),
  role: z.enum(['admin', 'editor', 'viewer']),
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
  variant: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
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
type Status = 'idle' | 'loading' | 'success' | 'error';

// DO: Type for derived types
type CreateUserInput = Omit<User, 'id' | 'createdAt'>;
type UserSummary = Pick<User, 'id' | 'name'>;

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
type UpdateUserInput = Partial<Pick<User, 'name' | 'email' | 'avatar'>>;

// Required<T> — All properties required (use to enforce completeness)
type CompleteUserProfile = Required<User>;

// Pick<T, K> — Select specific properties
type UserSummary = Pick<User, 'id' | 'name' | 'avatar'>;

// Omit<T, K> — Exclude specific properties
type CreateUserInput = Omit<User, 'id' | 'createdAt' | 'updatedAt'>;

// Record<K, V> — Typed dictionary
type UsersByRole = Record<UserRole, User[]>;

// Readonly<T> — Immutable version
type FrozenUser = Readonly<User>;

// Extract / Exclude — For union manipulation
type WritableRole = Exclude<UserRole, 'viewer'>;
type AdminRole = Extract<UserRole, 'admin' | 'superadmin'>;

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
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };

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
  variant?: 'compact' | 'full';
  onSelect?: (userId: string) => void;
}

export function UserCard({ user, variant = 'compact', onSelect }: UserCardProps): React.ReactElement {
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
const [searchTerm, setSearchTerm] = useState('');
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
  | { type: 'SET_FIELD'; field: string; value: string }
  | { type: 'SET_ERROR'; field: string; error: string }
  | { type: 'TOUCH_FIELD'; field: string }
  | { type: 'SUBMIT_START' }
  | { type: 'SUBMIT_SUCCESS' }
  | { type: 'SUBMIT_FAILURE'; errors: Record<string, string> }
  | { type: 'RESET' };

function formReducer(state: FormState, action: FormAction): FormState {
  switch (action.type) {
    case 'SET_FIELD':
      return {
        ...state,
        values: { ...state.values, [action.field]: action.value },
        errors: { ...state.errors, [action.field]: '' },
      };
    case 'SUBMIT_START':
      return { ...state, isSubmitting: true };
    case 'SUBMIT_SUCCESS':
      return { ...state, isSubmitting: false };
    case 'SUBMIT_FAILURE':
      return { ...state, isSubmitting: false, errors: action.errors };
    case 'RESET':
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
import { create } from 'zustand';

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

| Type | Convention | Example |
|------|-----------|---------|
| Component | PascalCase | `UserCard.tsx` |
| Hook | kebab-case with `use-` prefix | `use-auth.ts` |
| Utility | kebab-case | `format-date.ts` |
| Type file | kebab-case or `types.ts` | `types.ts`, `api-types.ts` |
| Test file | Same name + `.test` | `UserCard.test.tsx` |
| Style module | Same name + `.module.css` | `UserCard.module.css` |
| Constants | kebab-case | `constants.ts`, `route-paths.ts` |
| Context | PascalCase with Context suffix | `AuthContext.tsx` |

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
import { useState, useCallback, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

// 2. External libraries
import { z } from 'zod';
import { useQuery, useMutation } from '@tanstack/react-query';
import clsx from 'clsx';

// 3. Internal absolute imports
import { Button } from '@/shared/components/Button';
import { useAuth } from '@/features/auth';
import { api } from '@/shared/api/client';

// 4. Relative imports
import { UserAvatar } from './UserAvatar';
import { formatUserName } from '../utils/format';
import { USER_ROLES } from './constants';

// 5. Type-only imports
import type { User, UserRole } from '../types';
import type { ApiResponse } from '@/shared/types/api';

// 6. Side-effect imports
import './UserCard.css';
```

### Use `type` Imports

Always use `import type` for type-only imports. This ensures types are erased at compile time and prevents circular dependency issues.

```typescript
// DO: Separate type imports
import type { User, UserRole } from './types';
import { formatUser } from './utils';

// DON'T: Mix types with value imports
import { User, UserRole, formatUser } from './module';
```

---

## Barrel Exports Policy

### When to Use Barrel Exports

Use `index.ts` barrel exports at the feature boundary to define the feature's public API.

```typescript
// features/auth/index.ts
export { AuthProvider } from './components/AuthProvider';
export { AuthGuard } from './components/AuthGuard';
export { LoginForm } from './components/LoginForm';
export { useAuth } from './hooks/use-auth';
export type { AuthContextValue, LoginCredentials } from './types';
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
export * from './types';
export * from './hooks/use-auth';
export * from './utils';

// DO: Explicit, curated exports
export { useAuth } from './hooks/use-auth';
export type { AuthContextValue } from './types';
```

### Import from Barrels

When a feature has a barrel export, always import from the barrel, not from internal files.

```typescript
// DO: Import from barrel
import { useAuth, AuthGuard } from '@/features/auth';

// DON'T: Reach into feature internals
import { useAuth } from '@/features/auth/hooks/use-auth';
```

---

## Error Boundaries

### Every Feature Route Gets an Error Boundary

Wrap each top-level route or feature section with an error boundary to prevent one failing component from taking down the entire app.

```typescript
// DO: Error boundary component
import { Component } from 'react';

interface ErrorBoundaryProps {
  fallback: React.ReactNode | ((error: Error, reset: () => void) => React.ReactNode);
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
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
      if (typeof fallback === 'function') {
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
  import('./features/settings/SettingsPage').then((mod) => ({
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
    return this.request<T>('GET', path, undefined, params);
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>('POST', path, body);
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>('PUT', path, body);
  }

  async delete(path: string): Promise<void> {
    await this.request<void>('DELETE', path);
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
      'Content-Type': 'application/json',
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
    this.name = 'ApiRequestError';
  }
}

export const api = new ApiClient({
  baseUrl: import.meta.env.VITE_API_BASE_URL,
  getAuthToken: () => localStorage.getItem('token'), // Or from auth context
});
```

### React Query / SWR Integration

Use React Query (TanStack Query) for server state management. Define query and mutation functions in feature-specific API modules.

```typescript
// features/users/api/users-api.ts
import { api } from '@/shared/api/client';
import { UserSchema, UsersListSchema } from '../types';

import type { User, CreateUserInput, UpdateUserInput } from '../types';

export const usersApi = {
  getUser: async (id: string): Promise<User> => {
    const data = await api.get<unknown>(`/users/${id}`);
    return UserSchema.parse(data);
  },

  listUsers: async (params?: { page?: number; limit?: number }): Promise<User[]> => {
    const data = await api.get<unknown>('/users', params as Record<string, string>);
    return UsersListSchema.parse(data);
  },

  createUser: async (input: CreateUserInput): Promise<User> => {
    const data = await api.post<unknown>('/users', input);
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
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersApi } from '../api/users-api';

import type { User, CreateUserInput } from '../types';

export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (params: Record<string, unknown>) => [...userKeys.lists(), params] as const,
  details: () => [...userKeys.all, 'detail'] as const,
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
  const { exportToExcel } = await import('./utils/excel-export');
  await exportToExcel(data);
};

// DON'T: Static import of large library used in one place
import * as XLSX from 'xlsx';
```
