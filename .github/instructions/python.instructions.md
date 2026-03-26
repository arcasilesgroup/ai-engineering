---
applyTo: "**/*.py"
---

# Python Instructions

Generated from `.ai-engineering/contexts/languages/python.md`.

## Idiomatic Python

**Import organization:**

- Python imports should be at the top of the file unless there's a circular reference issue
- Group imports: standard library, third-party, local (separated by blank lines)
- Use absolute imports over relative imports for clarity
- Avoid wildcard imports (`from module import *`)

**Circular reference handling:**

- If imports must be delayed, add a comment explaining why
- Consider refactoring to remove circular dependencies
- Use `TYPE_CHECKING` for type-only imports:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import User
```

**Code style:**

- Follow PEP 8 conventions
- Use descriptive variable names
- Prefer list/dict comprehensions over loops when clear
- Use context managers (`with` statements) for resources
- Prefer f-strings over `.format()` or `%` formatting

## Django ORM Patterns

**N+1 Query Issues:**

- Use `select_related()` for ForeignKey/OneToOne
- Use `prefetch_related()` for ManyToMany/reverse ForeignKey
- Check for queries in loops

**Query Optimization:**

- Use `only()` or `defer()` to limit fields
- Use `annotate()` for aggregations instead of Python loops
- Avoid filtering in Python - filter in the database
- Use `.count()` not `len(queryset)`
- Use `bulk_create`/`bulk_update` for batch operations
- **Foreign keys have indexes** - Django creates indexes for ForeignKey fields automatically

**Common mistakes:**

- Accessing related objects without prefetch
- Using `len()` instead of `.count()`
- Multiple queries where one with joins would work

## Bulk Operations & Signals

- **`bulk_update()` and `bulk_create()` don't trigger signals** (`post_save`, `pre_save`, etc.)
- If signals update caches, manually refresh after bulk operations or use individual `save()` calls
- Wrap bulk operations in `@transaction.atomic` for atomicity
- For large datasets, process in batches to limit memory usage:

```python
# Good - batched bulk update
BATCH_SIZE = 1000
for i in range(0, len(objects), BATCH_SIZE):
    batch = objects[i:i + BATCH_SIZE]
    Model.objects.bulk_update(batch, ["field"])
```

## Async/Await Patterns

**Critical issues:**

- Mixing sync and async code incorrectly
- Not using `async_to_sync` or `sync_to_async` when needed
- Missing `await` keywords
- Blocking operations in async functions

**Django async support:**

- Use async views for I/O-bound operations
- Check ORM operations are async-safe
- Use `asgiref.sync` utilities for mixed code

## Type Hints

**Type safety:**

- Add type hints to all function signatures
- Use `Optional[]` for nullable values
- Avoid `Any` type - be specific
- Use `TypedDict` for structured dicts, not `dict[str, Any]`

**Common patterns:**

```python
from typing import Optional, List
from django.http import HttpRequest, HttpResponse

def view(request: HttpRequest, user_id: Optional[int] = None) -> HttpResponse:
    ...
```

## Dictionary Access Patterns

**Direct access vs `.get()` for required fields:**

- Use `dict["key"]` for fields that must be present (primary keys, identifiers, required schema fields). This fails fast with a clear `KeyError` if the data is unexpectedly malformed, rather than silently propagating `None` downstream where it causes confusing errors.
- Use `dict.get("key")` only for genuinely optional fields where absence is a valid state.
- When building lookup dicts from lists (e.g., `{item["id"]: item for item in items}`), use direct access for the key field -- if the field is missing, the data is corrupt and you want to know immediately.

```python
# Good - fails fast if "id" is missing
flags_by_id = {flag["id"]: flag for flag in flags}

# Bad - silently maps None as a key, causing subtle bugs later
flags_by_id = {flag.get("id"): flag for flag in flags}
```

## Error Handling

**Django-specific:**

- Use `get_object_or_404()` for user-facing views
- Handle `DoesNotExist` exceptions appropriately
- Don't catch broad exceptions without logging

**Transaction management:**

- Use `@transaction.atomic` for multi-step operations
- Handle `IntegrityError` for unique constraint violations
- Be aware of transaction rollback behavior

## Security Patterns

**Django security:**

- Always validate and sanitize user input
- Use Django forms for validation
- Check CSRF protection is active
- Verify permissions before data access
- Use parameterized queries (ORM handles this)
- Avoid raw SQL unless necessary

**Authentication:**

- Use Django auth decorators (`@login_required`)
- Check permissions with `user.has_perm()`
- Don't roll custom authentication

## Timing and Duration Measurement

- Use `time.monotonic()` for measuring durations, not `time.time()`
- `monotonic()` is immune to system clock changes (NTP, DST, manual adjustments)
- `time.time()` can jump backward or forward unexpectedly

```python
# Good
start = time.monotonic()
do_work()
elapsed = time.monotonic() - start

# Bad - can give negative durations if clock adjusts
start = time.time()
do_work()
elapsed = time.time() - start
```

## Common Anti-Patterns

**ORM misuse:**

- Multiple saves in a loop (use `bulk_create` or `bulk_update`)
- Loading entire querysets to count (use `.count()`)
- Filtering querysets multiple times (chain filters)

**View patterns:**

- Business logic in views (move to models/services)
- Missing input validation
- Mixing template rendering and API responses

## Testing Patterns

**Django testing:**

- Use `TestCase` for database tests
- Use `TransactionTestCase` when testing transactions
- Mock external services
- Use `override_settings` for config changes
- Factory patterns over fixtures

## Performance

**Common bottlenecks:**

- Missing database indexes
- Serializing large querysets without pagination
- Template rendering with complex queries
- Missing cache for expensive operations

## Quality Checklist

Before committing Python code:

1. `ruff check` and `ruff format`
2. `mypy` (if configured)
3. `pytest` for tests
