# API Design Standards

> RESTful API design conventions, versioning, error responses, pagination, and security.

---

## 1. URL Structure

### Pattern: `/api/v{version}/{resource}`

```
GET    /api/v1/users          # List users
GET    /api/v1/users/{id}     # Get single user
POST   /api/v1/users          # Create user
PUT    /api/v1/users/{id}     # Replace user
PATCH  /api/v1/users/{id}     # Partial update
DELETE /api/v1/users/{id}     # Delete user
```

### Rules

- Use **plural nouns** for resources: `/users`, not `/user`.
- Use **kebab-case** for multi-word resources: `/order-items`, not `/orderItems`.
- Use **path parameters** for identity: `/users/{id}`.
- Use **query parameters** for filtering: `/users?status=active&role=admin`.
- Maximum URL depth: 3 levels (e.g., `/users/{id}/orders`).
- Never use verbs in URLs: `/users`, not `/getUsers`.

---

## 2. HTTP Methods

| Method | Purpose | Idempotent | Response Code |
|--------|---------|------------|---------------|
| GET | Read resource(s) | Yes | 200 OK |
| POST | Create resource | No | 201 Created |
| PUT | Replace resource | Yes | 200 OK / 204 No Content |
| PATCH | Partial update | No | 200 OK |
| DELETE | Remove resource | Yes | 204 No Content |

---

## 3. Response Codes

### Success

| Code | When to Use |
|------|-------------|
| 200 OK | Successful GET, PUT, PATCH |
| 201 Created | Successful POST (include Location header) |
| 204 No Content | Successful DELETE or PUT with no body |

### Client Errors

| Code | When to Use |
|------|-------------|
| 400 Bad Request | Invalid input, validation failure |
| 401 Unauthorized | Missing or invalid authentication |
| 403 Forbidden | Authenticated but not authorized |
| 404 Not Found | Resource doesn't exist |
| 409 Conflict | Duplicate resource, version conflict |
| 422 Unprocessable Entity | Semantically invalid request |
| 429 Too Many Requests | Rate limit exceeded |

### Server Errors

| Code | When to Use |
|------|-------------|
| 500 Internal Server Error | Unexpected server error |
| 502 Bad Gateway | Upstream service failure |
| 503 Service Unavailable | Service temporarily unavailable |

---

## 4. Error Response Format (RFC 7807)

All error responses use the Problem Details format:

```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation Error",
  "status": 400,
  "detail": "One or more validation errors occurred.",
  "instance": "/api/v1/users",
  "errors": {
    "email": ["Email address is not valid."],
    "name": ["Name is required.", "Name must be between 2 and 100 characters."]
  },
  "traceId": "00-abc123-def456-01"
}
```

### Rules

- Always include `type`, `title`, `status`, and `detail`.
- Include `traceId` for correlation with logs.
- Include `errors` dictionary for validation failures.
- Never expose stack traces, internal paths, or implementation details.

---

## 5. Versioning

### Strategy: URL Path Versioning

```
/api/v1/users    # Version 1
/api/v2/users    # Version 2
```

### Rules

- Start with `v1`.
- Only increment major version for breaking changes.
- Support previous version for at least 6 months after deprecation.
- Use `Sunset` header to communicate deprecation: `Sunset: Sat, 01 Jan 2026 00:00:00 GMT`.

### Breaking Changes (require version bump)

- Removing a field from response
- Changing a field type
- Removing an endpoint
- Changing authentication requirements

### Non-Breaking Changes (no version bump)

- Adding a new field to response
- Adding a new endpoint
- Adding optional query parameters
- Adding new enum values (if client handles unknown)

---

## 6. Pagination

### Pattern: Offset-Based

```
GET /api/v1/users?page=1&pageSize=20
```

### Response Format

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "totalCount": 150,
    "totalPages": 8,
    "hasNextPage": true,
    "hasPreviousPage": false
  }
}
```

### Rules

- Default `pageSize`: 20. Maximum `pageSize`: 100.
- Always include pagination metadata in list responses.
- For large datasets, consider cursor-based pagination.

---

## 7. Filtering and Sorting

### Filtering

```
GET /api/v1/users?status=active&role=admin&createdAfter=2024-01-01
```

- Use query parameters for filtering.
- Support multiple values: `?status=active,inactive`.
- Date format: ISO 8601 (`2024-01-15T10:30:00Z`).

### Sorting

```
GET /api/v1/users?sort=name:asc,createdAt:desc
```

- Format: `field:direction` (asc/desc).
- Default sort: `createdAt:desc`.
- Support multiple sort fields with comma separation.

---

## 8. Request/Response Conventions

### Rules

- Use **camelCase** for JSON property names.
- Use **ISO 8601** for dates: `2024-01-15T10:30:00Z`.
- Use **string** for IDs (not integers) to avoid overflow and enable prefixed IDs.
- Include `createdAt` and `updatedAt` timestamps on all resources.
- Never include sensitive data (passwords, tokens) in responses.

---

## 9. Authentication and Authorization

### Headers

```
Authorization: Bearer <jwt-token>
X-Request-Id: <correlation-id>
```

### Rules

- Use Bearer tokens (JWT or opaque) for API authentication.
- Include `[Authorize]` attribute on all endpoints by default. Use `[AllowAnonymous]` explicitly.
- Return 401 for missing/invalid token. Return 403 for insufficient permissions.
- Never include tokens or credentials in URL query parameters.
- Set appropriate CORS headers for browser clients.

---

## 10. Rate Limiting

Include rate limit headers in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
Retry-After: 60
```

| Tier | Rate | Window |
|------|------|--------|
| Standard | 100 requests | per minute |
| Authenticated | 1000 requests | per minute |
| Admin | 5000 requests | per minute |
