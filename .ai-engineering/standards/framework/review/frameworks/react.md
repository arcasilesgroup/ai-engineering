# React Review Guidelines

## Update Metadata
- Rationale: React-specific patterns for components, hooks, state, performance, and accessibility.

## Component Patterns
- Single Responsibility: one component, one concern.
- Prefer function components with hooks over class components.
- Use `React.memo()` only when measured — premature memoization adds complexity.
- Use error boundaries for graceful failure handling.

## Hooks
- Follow Rules of Hooks: only at top level, only in React functions.
- Dependency arrays must be complete — no missing deps.
- Use `useCallback` for event handlers passed to child components.
- Custom hooks for reusable logic — prefix with `use`.

## Accessibility (WCAG 2.1 AA)
- All interactive elements must have accessible names (`aria-label`, visible text).
- Form inputs MUST have associated `<label>` elements.
- Use semantic HTML: `<button>` not `<div onClick>`.
- Keyboard navigation: all actions reachable via Tab + Enter/Space.
- Error messages announced: use `role="alert"` or `aria-live="polite"`.
- Focus management: trap focus in modals, restore on close.
- Color contrast: minimum 4.5:1 for normal text.

## State Management
- Local state first (`useState`), lift when needed, context for truly global.
- Avoid prop drilling beyond 2 levels — use context or composition.

## References
- Enforcement: `standards/framework/stacks/react.md`
