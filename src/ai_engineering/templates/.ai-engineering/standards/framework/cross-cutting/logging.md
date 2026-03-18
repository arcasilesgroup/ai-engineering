# Cross-Cutting Standard: Logging

## Scope

Applies to all stacks. Stack standards may extend with framework-specific logging libraries.

## Principles

1. **Structured logging**: JSON format in production for machine parsing. Human-readable in development.
2. **Consistent levels**: ERROR (action needed), WARN (potential issue), INFO (business events), DEBUG (troubleshooting).
3. **Context propagation**: include correlation IDs, request IDs, user identifiers across log entries.
4. **No sensitive data**: never log passwords, tokens, PII, or secrets. Redact at the logging boundary.
5. **Performance-aware**: avoid expensive string formatting for disabled log levels.

## Patterns

- **Structured fields**: use key-value pairs, not string interpolation (`logger.info("order.created", order_id=id)` not `logger.info(f"Order {id} created")`).
- **Correlation IDs**: generate at system entry point, propagate through all service calls.
- **Request logging**: log at request start (method, path) and end (status, duration).
- **Error logging**: include exception type, message, and stack trace. Add business context.
- **Audit logging**: security-relevant events (auth, access control, data mutations) at INFO or above.

## Anti-patterns

- Logging at the wrong level (using ERROR for expected conditions).
- Including full request/response bodies (data leak risk, volume).
- Missing correlation IDs in distributed systems.
- Inconsistent timestamp formats across services.

## Update Contract

This file is framework-managed and may be updated by framework releases.
