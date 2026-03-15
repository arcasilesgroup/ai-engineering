# Cross-Cutting Standard: Error Handling

## Scope

Applies to all stacks. Stack standards may extend or specialize these patterns.

## Principles

1. **Fail fast, fail loud**: detect errors early and surface them immediately.
2. **Typed errors**: use language-native error types (exceptions, Result types, error enums). Avoid stringly-typed errors.
3. **No swallowed errors**: every `catch`/`except`/`rescue` must log, re-raise, or handle meaningfully.
4. **User-facing vs internal**: separate user-facing error messages (clear, actionable) from internal error details (stack traces, context).
5. **Error boundaries**: define clear error handling boundaries at system edges (HTTP handlers, CLI entry points, queue consumers).

## Patterns

- **Custom error hierarchies**: define domain-specific error types. Don't throw generic exceptions.
- **Error context**: include enough context to diagnose without reproducing (input values, state, caller chain).
- **Retry policy**: transient errors (network, lock contention) may retry. Permanent errors (validation, auth) must not.
- **Circuit breaker**: for external service calls, implement circuit breaker to avoid cascade failures.
- **Error codes**: stable identifiers for programmatic handling. Human-readable messages for display.

## Anti-patterns

- Empty catch blocks.
- Catching base exception types (e.g., `catch (Exception e)`) without re-throwing.
- Using exceptions for control flow.
- Logging and re-throwing the same error (double-logging).
- Returning `null`/`None` to signal errors when a Result type or exception is appropriate.

## Update Contract

This file is framework-managed and may be updated by framework releases.
