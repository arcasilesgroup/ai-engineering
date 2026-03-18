# Cross-Cutting Standard: API Design

## Scope

Applies to all stacks exposing HTTP APIs, GraphQL endpoints, or gRPC services.

## Principles

1. **Contract-first**: define the API contract (OpenAPI, GraphQL schema, protobuf) before implementation.
2. **Versioning**: API version in URL path (`/v1/`) or header. Never break existing consumers.
3. **Consistency**: uniform naming, error format, pagination, and filtering across all endpoints.
4. **Idempotency**: unsafe operations (POST, PUT, DELETE) support idempotency keys when appropriate.
5. **Security by default**: authentication required unless explicitly public. Authorize every request.

## REST Patterns

- **Resource naming**: plural nouns (`/users`, `/orders`). No verbs in URLs.
- **HTTP methods**: GET (read), POST (create), PUT (full update), PATCH (partial update), DELETE (remove).
- **Status codes**: 200 (OK), 201 (created), 204 (no content), 400 (bad request), 401 (unauthorized), 403 (forbidden), 404 (not found), 409 (conflict), 422 (validation), 500 (server error).
- **Error format**: `{ "error": { "code": "VALIDATION_FAILED", "message": "...", "details": [...] } }`.
- **Pagination**: cursor-based preferred. Include `next_cursor`, `has_more`. Offset-based acceptable for small datasets.
- **Filtering**: query parameters (`?status=active&sort=-created_at`).

## GraphQL Patterns

- **Schema-first**: define `.graphql` schema files. Generate resolvers.
- **Pagination**: Relay connection spec (`edges`, `nodes`, `pageInfo`).
- **Error handling**: use `errors` array in response. Custom error extensions for codes.
- **N+1 prevention**: DataLoader pattern for batch loading.

## gRPC Patterns

- **Proto-first**: define `.proto` files. Generate client/server code.
- **Streaming**: use server streaming for large datasets, bidirectional for real-time.
- **Error codes**: use standard gRPC status codes.

## Anti-patterns

- Breaking changes without versioning.
- Inconsistent naming across endpoints (mixing camelCase and snake_case).
- Returning 200 for errors with error body.
- No rate limiting on public endpoints.
- Exposing internal IDs or implementation details in API responses.

## Update Contract

This file is framework-managed and may be updated by framework releases.
