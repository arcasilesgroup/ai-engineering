# NestJS Review Guidelines

## Update Metadata
- Rationale: NestJS-specific patterns for modules, DI, guards, and validation.

## Module Patterns
- One module per domain feature.
- Use `forRoot()` / `forFeature()` pattern for configurable modules.
- Lazy-load non-critical modules.

## Dependency Injection
- Use constructor injection with typed tokens.
- Use `@Injectable({ scope: Scope.REQUEST })` only when needed — default singleton is more performant.
- Custom providers for complex factory logic.

## Validation & Guards
- Use `class-validator` with `ValidationPipe` globally.
- Use guards for authentication, interceptors for logging/transformation.
- Use `@UseFilters()` for exception handling.

## Security
- Use `@nestjs/throttler` for rate limiting.
- Helmet middleware for HTTP security headers.
- CORS configuration: explicit origins, no wildcard in production.

## References
- Enforcement: `standards/framework/stacks/nestjs.md`
