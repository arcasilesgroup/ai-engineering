# API Design Patterns

On-demand reference for API design, contract evolution, and integration.

## Contract-First Design

- Define API contract before implementation using OpenAPI 3.1 (REST) or GraphQL SDL.
- Schema drives: server stubs, client SDKs, documentation, and test mocks.
- Contract changes require review — treat API schema as a public interface.
- Store OpenAPI spec in repo: `api/openapi.yaml` or `docs/api/`.

## REST Conventions

### URL Structure

- Resources as nouns, plural: `/users`, `/orders`, `/order-items`.
- Hierarchical: `/users/{id}/orders` for parent-child relationships.
- Actions as verbs only when CRUD doesn't fit: `/orders/{id}/cancel`.
- Version in URL (`/v1/users`) or header (`Accept: application/vnd.api+json;version=1`).

### HTTP Methods

| Method | Semantics | Idempotent | Response |
|--------|-----------|------------|----------|
| GET | Read | Yes | 200 with resource |
| POST | Create | No | 201 with Location header |
| PUT | Full replace | Yes | 200 or 204 |
| PATCH | Partial update | No | 200 with updated resource |
| DELETE | Remove | Yes | 204 |

### Pagination

- Keyset (cursor): `?after=<cursor>&limit=20` — preferred for large datasets.
- Offset: `?page=1&size=20` — acceptable for small, static datasets.
- Response: include `nextCursor`, `hasMore`, `totalCount` (when feasible).

### Filtering and Sorting

- Filter: `?status=active&type=premium`.
- Sort: `?sort=created_at:desc,name:asc`.
- Search: `?q=search+term` for full-text search.

## Error Model

### Consistent Structure

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": [
      { "field": "email", "issue": "Invalid email format" }
    ],
    "requestId": "req-abc123"
  }
}
```

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 400 | Bad Request | Invalid input, validation failure |
| 401 | Unauthorized | Missing or invalid credentials |
| 403 | Forbidden | Valid credentials, insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate, version conflict |
| 422 | Unprocessable | Semantically invalid request |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Error | Server fault (log details, return generic message) |

## Versioning Strategy

- **Additive changes**: add new fields, endpoints — no version bump needed.
- **Breaking changes**: remove fields, change types, rename — require new version.
- **Sunset process**: announce deprecation → 6-month migration window → remove.
- **Version header**: `API-Version: 2024-01-15` (date-based) for incremental changes.

## Authentication and Authorization

- **API keys**: for server-to-server, scoped per service.
- **OAuth 2.0 / OIDC**: for user-facing APIs. Use PKCE for public clients.
- **JWT**: short-lived access tokens (15 min), long-lived refresh tokens (7 days).
- **RBAC**: role-based access control at endpoint level.
- **Least privilege**: default deny, explicit allow.

## Rate Limiting

- Return `429 Too Many Requests` with `Retry-After` header.
- Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- Sliding window or token bucket algorithm.
- Different limits per tier (free, pro, enterprise).

## GraphQL Patterns

- **Schema-first**: define SDL, generate resolvers.
- **Pagination**: Relay connection spec (`edges`, `nodes`, `pageInfo`).
- **Complexity limiting**: query depth limit (max 10), field cost analysis.
- **DataLoader**: batch and cache database reads to prevent N+1.
- **Subscriptions**: WebSocket for real-time updates.

## Idempotency

- POST with `Idempotency-Key` header for safe retries.
- Server stores key → response mapping for deduplication.
- Key TTL: 24 hours minimum.
- PUT and DELETE are naturally idempotent.

## Security Headers

- `Content-Type: application/json` — always set explicitly.
- `X-Content-Type-Options: nosniff`.
- `X-Request-Id` — for tracing and debugging.
- CORS: explicit allowed origins, methods, headers. No wildcards in production.
