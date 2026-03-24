## Retry with Exponential Backoff

Retry transient failures with increasing delays. Apply jitter to avoid thundering herd.

```python
# GOOD: exponential backoff with jitter
import random
import time

def retry_with_backoff(fn, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            return fn()
        except TransientError:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
            time.sleep(delay)
```

```typescript
// GOOD: generic retry with exponential backoff
async function retry<T>(fn: () => Promise<T>, maxRetries = 3): Promise<T> {
  let lastError: Error;
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      if (i < maxRetries - 1) {
        const delay = Math.pow(2, i) * 1000 + Math.random() * 500;
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  throw lastError!;
}
```

```go
// GOOD: retry with context cancellation support
func RetryWithBackoff(ctx context.Context, fn func() error, maxRetries int) error {
    for i := 0; i < maxRetries; i++ {
        if err := fn(); err == nil {
            return nil
        }
        if i < maxRetries-1 {
            delay := time.Duration(1<<uint(i)) * time.Second
            select {
            case <-time.After(delay):
            case <-ctx.Done():
                return ctx.Err()
            }
        }
    }
    return fmt.Errorf("exhausted %d retries", maxRetries)
}
```

**Rules:**

- Only retry on transient errors (network timeouts, 429, 503) -- never on 400/401/403/404
- Cap maximum delay (e.g. 30 seconds) to avoid infinite waits
- Add jitter to prevent synchronized retries across instances
- Log each retry attempt with attempt number and delay

## Structured Logging

Emit machine-parseable JSON logs with consistent fields for aggregation and alerting.

```python
# GOOD: structured log entry
import json
import logging
from datetime import datetime, timezone

class StructuredLogger:
    def __init__(self, service: str):
        self.service = service

    def log(self, level: str, message: str, **context):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "service": self.service,
            "message": message,
            **context,
        }
        print(json.dumps(entry))

    def info(self, message: str, **ctx):
        self.log("info", message, **ctx)

    def error(self, message: str, error: Exception | None = None, **ctx):
        if error:
            ctx["error"] = str(error)
            ctx["error_type"] = type(error).__name__
        self.log("error", message, **ctx)
```

```typescript
// GOOD: structured logging with request context
interface LogContext {
  requestId?: string;
  userId?: string;
  method?: string;
  path?: string;
  durationMs?: number;
  [key: string]: unknown;
}

function log(level: "info" | "warn" | "error", message: string, context?: LogContext) {
  const entry = {
    timestamp: new Date().toISOString(),
    level,
    message,
    ...context,
  };
  console.log(JSON.stringify(entry));
}
```

**Rules:**

- Always include `timestamp`, `level`, `service`, `message`
- Add `requestId` for request tracing across services
- Add `durationMs` for performance tracking on operations
- Never log secrets, tokens, passwords, or PII
- Use `warn` for recoverable issues, `error` for failures requiring attention

## Centralized Error Class

Define a base error class that carries HTTP status, error code, and operational flag. All service-layer errors inherit from it.

```python
# GOOD: centralized API error hierarchy
class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500, code: str = "internal_error", operational: bool = True):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.operational = operational

class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} '{identifier}' not found", status_code=404, code="not_found")

class ValidationError(AppError):
    def __init__(self, details: list[dict]):
        super().__init__("Validation failed", status_code=422, code="validation_error")
        self.details = details
```

```typescript
// GOOD: centralized error class with status and code
class AppError extends Error {
  constructor(
    message: string,
    public statusCode: number = 500,
    public code: string = "internal_error",
    public operational: boolean = true,
  ) {
    super(message);
    Object.setPrototypeOf(this, AppError.prototype);
  }
}

// GOOD: error handler distinguishes known vs unknown errors
function handleError(error: unknown): { status: number; body: object } {
  if (error instanceof AppError) {
    return { status: error.statusCode, body: { error: { code: error.code, message: error.message } } };
  }
  // Unknown error -- log and return generic 500
  console.error("Unexpected error:", error);
  return { status: 500, body: { error: { code: "internal_error", message: "Internal server error" } } };
}
```

**Rules:**

- All expected errors throw `AppError` subclasses with appropriate status codes
- Unknown errors are caught at the boundary, logged, and returned as 500
- Never expose stack traces, SQL errors, or internal details to clients
- Use `operational` flag to distinguish programmer errors (crash) from expected failures (handle)

## Role-Based Access Control (RBAC)

Use a higher-order function (HOF) or decorator pattern to enforce permissions at the handler boundary.

```python
# GOOD: RBAC decorator
from functools import wraps

ROLE_PERMISSIONS = {
    "admin": {"read", "write", "delete", "admin"},
    "editor": {"read", "write", "delete"},
    "viewer": {"read"},
}

def require_permission(permission: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if permission not in ROLE_PERMISSIONS.get(user.role, set()):
                raise AppError("Insufficient permissions", status_code=403, code="forbidden")
            return fn(request, *args, **kwargs)
        return wrapper
    return decorator

@require_permission("delete")
def delete_resource(request, resource_id):
    # Only users with 'delete' permission reach here
    pass
```

```typescript
// GOOD: RBAC higher-order function
type Permission = "read" | "write" | "delete" | "admin";

const rolePermissions: Record<string, Permission[]> = {
  admin: ["read", "write", "delete", "admin"],
  editor: ["read", "write", "delete"],
  viewer: ["read"],
};

function requirePermission(permission: Permission) {
  return (handler: (req: Request, user: User) => Promise<Response>) => {
    return async (req: Request) => {
      const user = await authenticate(req);
      if (!rolePermissions[user.role]?.includes(permission)) {
        return new Response(JSON.stringify({ error: { code: "forbidden" } }), { status: 403 });
      }
      return handler(req, user);
    };
  };
}
```

## Cache-Aside Pattern

Check cache first. On miss, fetch from source, populate cache, return.

```python
# GOOD: cache-aside with TTL
def get_resource(resource_id: str) -> dict:
    cache_key = f"resource:{resource_id}"

    # 1. Check cache
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 2. Cache miss -- fetch from source
    resource = db.find_by_id(resource_id)
    if resource is None:
        raise NotFoundError("Resource", resource_id)

    # 3. Populate cache with TTL
    cache.set(cache_key, resource, ttl=300)
    return resource

def update_resource(resource_id: str, data: dict) -> dict:
    resource = db.update(resource_id, data)
    # Invalidate cache on write
    cache.delete(f"resource:{resource_id}")
    return resource
```

```typescript
// GOOD: cache-aside with invalidation
async function getResource(id: string): Promise<Resource> {
  const cacheKey = `resource:${id}`;
  const cached = await cache.get(cacheKey);
  if (cached) return JSON.parse(cached);

  const resource = await db.findById(id);
  if (!resource) throw new AppError("Not found", 404, "not_found");

  await cache.set(cacheKey, JSON.stringify(resource), { ex: 300 });
  return resource;
}
```

**Rules:**

- Always invalidate or update cache on writes to the underlying data
- Set appropriate TTLs -- short for frequently changing data, longer for stable data
- Handle cache failures gracefully -- fall through to the data source
- Include relevant identifiers in cache keys to avoid collisions

## Background Job Queue

Offload long-running work to a queue so request handlers return immediately.

```python
# GOOD: simple in-process job queue (for single-instance apps)
import asyncio
from collections import deque
from typing import Callable, Awaitable

class JobQueue:
    def __init__(self):
        self._queue: deque[Callable[[], Awaitable[None]]] = deque()
        self._processing = False

    async def enqueue(self, job: Callable[[], Awaitable[None]]):
        self._queue.append(job)
        if not self._processing:
            asyncio.create_task(self._process())

    async def _process(self):
        self._processing = True
        while self._queue:
            job = self._queue.popleft()
            try:
                await job()
            except Exception as e:
                logger.error("Job failed", error=e)
        self._processing = False
```

```typescript
// GOOD: typed job queue with error isolation
class JobQueue<T> {
  private queue: T[] = [];
  private processing = false;

  async add(job: T): Promise<void> {
    this.queue.push(job);
    if (!this.processing) this.process();
  }

  private async process(): Promise<void> {
    this.processing = true;
    while (this.queue.length > 0) {
      const job = this.queue.shift()!;
      try {
        await this.execute(job);
      } catch (error) {
        log("error", "Job failed", { error: String(error) });
      }
    }
    this.processing = false;
  }

  private async execute(job: T): Promise<void> {
    // Override in subclass or pass executor to constructor
  }
}
```

**Rules:**

- Return `202 Accepted` from the API when enqueueing work
- Isolate job failures -- one failed job must not block the queue
- Add dead-letter handling for jobs that fail repeatedly
- For multi-instance deployments, use a distributed queue (database-backed, message broker)

## Rate Limiting Tiers

Apply different rate limits based on authentication level.

| Tier | Limit | Window | Identifier |
|------|-------|--------|------------|
| Anonymous | 30/min | Per IP | `X-Forwarded-For` or socket address |
| Authenticated | 100/min | Per user | User ID from token |
| Premium | 1000/min | Per API key | API key |
| Internal | 10000/min | Per service | Service identity |

**Response headers:**

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
Retry-After: 60          # only on 429
```

**Rules:**

- Always return rate limit headers so clients can self-throttle
- Use sliding window counters, not fixed windows (avoids burst at window boundaries)
- Rate-limit authentication endpoints aggressively to prevent brute force
- Return `429 Too Many Requests` with `Retry-After` header

## Common Anti-Patterns

**Retry logic:**

- Retrying on non-transient errors (400, 401, 404) -- wastes resources and never succeeds
- No maximum delay cap -- exponential backoff without a ceiling can delay minutes
- No jitter -- all instances retry at the same time after an outage

**Error handling:**

- Catching all exceptions and returning 200 with an error body
- Logging errors without context (no request ID, no user ID, no operation name)
- Exposing stack traces or database errors to clients

**Caching:**

- Cache without TTL -- stale data indefinitely
- No invalidation on writes -- cache and database drift apart
- Caching errors -- a transient failure gets cached and served repeatedly

**Authorization:**

- Checking authentication but not authorization (who you are != what you can do)
- Permissions checked inside business logic instead of at the handler boundary
- Hard-coded role checks scattered through the codebase instead of a centralized RBAC map

**Background jobs:**

- Blocking the request handler while processing -- defeats the purpose
- No error isolation -- one failed job crashes the queue processor
- No observability -- jobs fail silently with no logging or alerting
