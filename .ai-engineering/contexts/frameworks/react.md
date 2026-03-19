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
