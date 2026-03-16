# Django Review Guidelines

## Update Metadata
- Rationale: Django-specific patterns for ORM, views, security, and async.

## ORM Patterns
- Use `select_related()` for ForeignKey joins (single query instead of N+1).
- Use `prefetch_related()` for ManyToMany and reverse ForeignKey.
- **Fallback N+1**: Cache miss in loop triggers individual DB fetches — batch the lookup.
- Use `F()` expressions for atomic updates instead of read-modify-write.
- Use `Q()` objects for complex query filters.

## View Patterns
- Class-based views for CRUD, function-based for simple endpoints.
- Use `get_object_or_404()` instead of manual try/except.
- Always set `login_required` or permission classes on views.

## Security
- CSRF protection enabled by default — never disable globally.
- Use ORM queries — never raw SQL with string formatting.
- Validate file uploads: check content type, size limits, file extension.

## Async Support
- Use `async def` views with Django 4.1+ for I/O-bound operations.
- Wrap sync ORM calls with `sync_to_async()`.

## References
- Enforcement: `standards/framework/stacks/python.md`
