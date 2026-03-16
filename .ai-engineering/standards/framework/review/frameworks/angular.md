# Angular Review Guidelines

## Update Metadata
- Rationale: Angular-specific patterns for components, services, RxJS, and performance.

## Component Patterns
- Use `OnPush` change detection strategy for performance.
- Smart/Dumb component split: containers handle data, presentational components display it.
- Use `@Input()` with `set` for input validation.
- Lazy-load route modules for bundle size optimization.

## RxJS Patterns
- Always unsubscribe — use `takeUntilDestroyed()` (Angular 16+) or `async` pipe.
- Use `switchMap` for HTTP requests triggered by user actions.
- Avoid nested subscribes — use higher-order mapping operators.

## Service Patterns
- Use `providedIn: 'root'` for singleton services.
- Use interceptors for cross-cutting HTTP concerns (auth, error handling).
- Use `inject()` function (Angular 14+) over constructor injection for simpler code.

## Security
- Use Angular's built-in sanitization — never bypass with `bypassSecurityTrust*` without review.
- Use `HttpClient` — never raw `fetch()`.

## References
- Enforcement: `standards/framework/stacks/typescript.md`
