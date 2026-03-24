# React Framework Guidelines

## Patterns to Detect

Flag these patterns in React/TypeScript code:

- **Callback parameter mismatch**: When callers pass parameters to a callback but the callback signature doesn't use them, or the callback is empty while callers appear to expect behavior. This indicates a disconnect between intent and implementation.
- **Missing ARIA on collapsibles**: Collapsible/expandable UI elements need `aria-expanded` and `aria-controls` attributes for screen reader accessibility.
- **Inconsistent sortable/collapsible state**: Components with sortable or collapsible items need consistent state management. New items should auto-expand when similar components do.
- **Unbounded in-memory structures**: Caches, lists, or maps that accumulate entries without cleanup mechanisms create potential memory leaks.
- **Orphaned producers**: When removing code that consumes a field/method, check if the producer code becomes dead code.
- **Test coverage for new parameters**: When adding new parameters or overloads to functions, verify existing tests cover the new code paths.
- **Browser API compatibility**: APIs like `crypto.randomUUID()` require secure context and may not work in all browsers. Prefer established library functions.

## React Component Architecture

**Critical Issues:**

- Components doing too much (violating single responsibility)
- Missing error boundaries for error-prone sections
- Direct DOM manipulation instead of React patterns
- Missing or incorrect key props in lists

**Split large components:**

- Container components for data/state
- Presentational components for pure rendering

## Performance & Re-rendering

**Important optimizations:**

- useMemo for expensive calculations
- useCallback for event handlers passed as props
- React.memo for components that re-render often
- Missing dependency arrays causing infinite loops
- Unnecessary state causing re-renders

## Hooks Usage & Patterns

**Critical hook violations:**

- Hooks called conditionally or in loops
- Missing dependency arrays
- Missing cleanup functions in useEffect

**Common mistakes:**

- Using useEffect for derived state (use useMemo)
- useEffect doing too much (split them)
- Creating new functions on every render
- Using useState when useRef is appropriate

## TypeScript & Props Management

**Type safety issues:**

- Props without proper TypeScript types
- Using `any` instead of proper interfaces
- Missing null/undefined checks
- Props spreading losing type safety

## Implementation Patterns

### Composition Over Inheritance

```tsx
// ✅ Compose small, focused components instead of extending base classes
interface CardProps {
  children: React.ReactNode
  variant?: 'default' | 'outlined'
}

export function Card({ children, variant = 'default' }: CardProps) {
  return <div className={`card card-${variant}`}>{children}</div>
}

export function CardHeader({ children }: { children: React.ReactNode }) {
  return <div className="card-header">{children}</div>
}

export function CardBody({ children }: { children: React.ReactNode }) {
  return <div className="card-body">{children}</div>
}

// Usage -- compose freely without inheritance chains
<Card variant="outlined">
  <CardHeader>Title</CardHeader>
  <CardBody>Content</CardBody>
</Card>
```

### Compound Components (WAI-ARIA Tabs)

```tsx
interface TabsContextValue {
  activeTab: string
  setActiveTab: (tab: string) => void
}

const TabsContext = createContext<TabsContextValue | undefined>(undefined)

export function Tabs({ children, defaultTab }: {
  children: React.ReactNode
  defaultTab: string
}) {
  const [activeTab, setActiveTab] = useState(defaultTab)

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      {children}
    </TabsContext.Provider>
  )
}

export function TabList({ children }: { children: React.ReactNode }) {
  return <div role="tablist">{children}</div>
}

export function Tab({ id, children }: { id: string; children: React.ReactNode }) {
  const context = useContext(TabsContext)
  if (!context) throw new Error('Tab must be used within Tabs')

  return (
    <button
      role="tab"
      aria-selected={context.activeTab === id}
      aria-controls={`panel-${id}`}
      id={`tab-${id}`}
      tabIndex={context.activeTab === id ? 0 : -1}
      onClick={() => context.setActiveTab(id)}
    >
      {children}
    </button>
  )
}

export function TabPanel({ id, children }: { id: string; children: React.ReactNode }) {
  const context = useContext(TabsContext)
  if (!context) throw new Error('TabPanel must be used within Tabs')
  if (context.activeTab !== id) return null

  return (
    <div role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`}>
      {children}
    </div>
  )
}

// Usage
<Tabs defaultTab="overview">
  <TabList>
    <Tab id="overview">Overview</Tab>
    <Tab id="details">Details</Tab>
  </TabList>
  <TabPanel id="overview">Overview content</TabPanel>
  <TabPanel id="details">Details content</TabPanel>
</Tabs>
```

### Custom Hooks

```tsx
// useToggle -- clean boolean state management
export function useToggle(initialValue = false): [boolean, () => void] {
  const [value, setValue] = useState(initialValue)
  const toggle = useCallback(() => setValue(v => !v), [])
  return [value, toggle]
}

// useDebounce -- with proper cleanup on unmount
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(handler) // cleanup prevents stale updates
  }, [value, delay])

  return debouncedValue
}

// Usage
const [isOpen, toggleOpen] = useToggle()
const debouncedQuery = useDebounce(searchQuery, 500)
```

### Context + useReducer

```tsx
interface State {
  items: Item[]
  selectedItem: Item | null
  loading: boolean
}

type Action =
  | { type: 'SET_ITEMS'; payload: Item[] }
  | { type: 'SELECT_ITEM'; payload: Item }
  | { type: 'SET_LOADING'; payload: boolean }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_ITEMS':
      return { ...state, items: action.payload }
    case 'SELECT_ITEM':
      return { ...state, selectedItem: action.payload }
    case 'SET_LOADING':
      return { ...state, loading: action.payload }
    default:
      return state
  }
}

const ItemContext = createContext<{
  state: State
  dispatch: Dispatch<Action>
} | undefined>(undefined)

export function ItemProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, {
    items: [],
    selectedItem: null,
    loading: false,
  })

  return (
    <ItemContext.Provider value={{ state, dispatch }}>
      {children}
    </ItemContext.Provider>
  )
}

export function useItems() {
  const context = useContext(ItemContext)
  if (!context) throw new Error('useItems must be used within ItemProvider')
  return context
}
```

### Code Splitting

```tsx
import { lazy, Suspense } from 'react'

const HeavyChart = lazy(() => import('./HeavyChart'))
const AdminPanel = lazy(() => import('./AdminPanel'))

export function Dashboard() {
  return (
    <div>
      <Suspense fallback={<ChartSkeleton />}>
        <HeavyChart data={data} />
      </Suspense>

      {isAdmin && (
        <Suspense fallback={<Spinner />}>
          <AdminPanel />
        </Suspense>
      )}
    </div>
  )
}
```

### Virtualization

```tsx
import { useVirtualizer } from '@tanstack/react-virtual'

export function VirtualList({ items }: { items: Item[] }) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100,
    overscan: 5,
  })

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map(virtualRow => (
          <div
            key={virtualRow.index}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualRow.size}px`,
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            <ItemCard item={items[virtualRow.index]} />
          </div>
        ))}
      </div>
    </div>
  )
}
```

### Error Boundary

```tsx
interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error boundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <div role="alert">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => this.setState({ hasError: false, error: null })}>
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

// Usage -- wrap error-prone sections
<ErrorBoundary fallback={<p>Chart failed to load.</p>}>
  <HeavyChart data={data} />
</ErrorBoundary>
```

### Framer Motion Animations

```tsx
import { motion, AnimatePresence } from 'framer-motion'

// List animations
export function AnimatedList({ items }: { items: Item[] }) {
  return (
    <AnimatePresence>
      {items.map(item => (
        <motion.div
          key={item.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          <ItemCard item={item} />
        </motion.div>
      ))}
    </AnimatePresence>
  )
}

// Modal animations (accessible)
export function AnimatedModal({ isOpen, onClose, children }: ModalProps) {
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return
    const handleEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handleEsc)
    contentRef.current?.focus()
    return () => document.removeEventListener('keydown', handleEsc)
  }, [isOpen, onClose])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            aria-hidden="true"
          />
          <motion.div
            ref={contentRef}
            className="modal-content"
            role="dialog"
            aria-modal="true"
            tabIndex={-1}
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
          >
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
```

### Stale Closure Trap

```tsx
// ❌ BAD: Stale closure -- count is captured at render time
function Counter() {
  const [count, setCount] = useState(0)

  useEffect(() => {
    const id = setInterval(() => {
      setCount(count + 1) // always reads the initial count value
    }, 1000)
    return () => clearInterval(id)
  }, []) // empty deps = stale closure

  return <span>{count}</span>
}

// ✅ GOOD: Functional updater reads the latest state
function Counter() {
  const [count, setCount] = useState(0)

  useEffect(() => {
    const id = setInterval(() => {
      setCount(prev => prev + 1) // always reads current state
    }, 1000)
    return () => clearInterval(id)
  }, [])

  return <span>{count}</span>
}
```

### Conditional Rendering

```tsx
// ✅ GOOD: && pattern for simple presence checks
{items.length > 0 && <ItemList items={items} />}
{error && <ErrorBanner message={error.message} />}

// ✅ GOOD: Ternary for binary toggle
{isLoading ? <Spinner /> : <DataView data={data} />}

// ❌ BAD: Nested ternaries (ternary hell)
{isLoading ? <Spinner /> : error ? <Error /> : data ? <View data={data} /> : <Empty />}

// ✅ GOOD: Early returns or a lookup instead of nested ternaries
function StatusView({ isLoading, error, data }: Props) {
  if (isLoading) return <Spinner />
  if (error) return <Error message={error.message} />
  if (!data) return <Empty />
  return <View data={data} />
}
```

## Common Anti-Patterns

**useEffect misuse:**

- Using for derived state (use useMemo)
- Missing cleanup for subscriptions/timers
- Multiple useEffects that should be combined

**Event handlers:**

- Inline arrow functions in JSX (causes re-renders)
- Missing event.preventDefault() when needed

**Forms:**

- Controlled inputs without onChange
- Missing debouncing for search inputs

## Accessibility Requirements (WCAG 2.1 AA)

**CRITICAL**: All interactive elements must be accessible to keyboard and screen reader users.

### Form Inputs

**All inputs must have accessible labels:**

```tsx
// ❌ BAD: No label
<input type="number" value={min} onChange={setMin} />

// ✅ GOOD: Visible label (preferred)
<label htmlFor="min-value">Minimum Value</label>
<input id="min-value" type="number" value={min} onChange={setMin} />

// ✅ GOOD: ARIA label (when no visible label)
<input
    type="number"
    value={min}
    onChange={setMin}
    aria-label="Minimum value for filter"
    placeholder="min"
/>

// ✅ GOOD: aria-labelledby (when label is complex)
<div id="range-label">Price Range</div>
<input
    type="number"
    aria-labelledby="range-label"
    aria-label="Minimum price"
/>
```

### Error States & Validation

**Error messages must be announced to screen readers:**

```tsx
// ✅ GOOD: Complete error handling
<input
    type="number"
    value={value}
    onChange={setValue}
    aria-label="Minimum value"
    aria-invalid={hasError}
    aria-describedby={hasError ? "min-error" : undefined}
/>
{hasError && (
    <div id="min-error" role="alert" aria-live="polite">
        Minimum must be less than maximum
    </div>
)}
```

### Buttons & Interactive Elements

**Icon-only buttons need labels:**

```tsx
// ❌ BAD: Icon button with no label
<button onClick={handleClose}>
    <IconClose />
</button>

// ✅ GOOD: aria-label for screen readers
<button onClick={handleClose} aria-label="Close dialog">
    <IconClose />
</button>

// ✅ GOOD: Hidden text + aria-label
<button onClick={handleClose}>
    <IconClose aria-hidden="true" />
    <span className="sr-only">Close dialog</span>
</button>
```

### Loading & Async States

**Announce loading states:**

```tsx
// ✅ GOOD: Loading state announced
<div aria-busy={isLoading} aria-live="polite">
    {isLoading ? "Loading data..." : <DataDisplay />}
</div>
```

### Keyboard Navigation

**Critical keyboard requirements:**

- Tab order must be logical
- All interactive elements reachable by keyboard
- Focus indicators must be visible
- Enter/Space activates buttons
- Escape closes modals/dropdowns

```tsx
// ✅ GOOD: Keyboard-accessible modal
<Modal
    isOpen={isOpen}
    onClose={handleClose}
    onEscapeKey={handleClose}  // Close on Escape
    shouldReturnFocus={true}   // Return focus when closed
    aria-modal="true"
    aria-labelledby="modal-title"
>
    <h2 id="modal-title">Confirm Action</h2>
    ...
</Modal>
```

### Common Accessibility Checklist

When reviewing components, verify:

- [ ] All form inputs have labels (visible or aria-label)
- [ ] Error messages are announced (role="alert" or aria-live)
- [ ] Invalid inputs marked (aria-invalid="true")
- [ ] Error messages linked (aria-describedby)
- [ ] Icon-only buttons have aria-label
- [ ] Loading states announced (aria-busy, aria-live)
- [ ] Modals trap focus and close on Escape
- [ ] Keyboard navigation works (all elements reachable)
- [ ] Focus indicators visible (no outline: none without replacement)
- [ ] Color contrast meets WCAG AA (4.5:1 for text)
- [ ] Tab order is logical
- [ ] ARIA roles used correctly
- [ ] Images have alt text (or aria-hidden if decorative)
- [ ] Links/buttons have descriptive text (not "click here")

### Anti-patterns

```tsx
// ❌ BAD: Removes focus indicators without replacement
button { outline: none; }

// ❌ BAD: Keyboard navigation broken
<div onClick={handleClick}>Click me</div>  // Not keyboard accessible

// ❌ BAD: Poor contrast
<span style={{ color: '#999', background: '#fff' }}>Important text</span>

// ❌ BAD: Non-descriptive link
<a href="/details">Click here</a>

// ✅ GOOD: Descriptive link
<a href="/details">View product details</a>
```
