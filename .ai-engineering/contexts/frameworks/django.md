## Django ORM & Database Patterns

**Critical performance issues:**

- N+1 queries - use `select_related()` for ForeignKey, `prefetch_related()` for ManyToMany
- Loading full querysets when only counting - use `.count()` not `len()`
- Filtering in Python instead of database - chain filters in queryset
- Missing database indexes on frequently queried fields

**N+1 Query Detection - Common Disguises:**

N+1 queries in "fallback" or "conditional" paths are just as serious as obvious ones. Watch for:

- **Cache miss fallbacks**: `if id not in cache: Model.objects.filter(id=id).first()` inside a loop
- **Conditional queries**: `if not preloaded: fetch_from_db()` where the condition triggers frequently
- **"Safety net" queries**: Fallback queries with warning logs that suggest "this shouldn't happen" - if it can happen, it will happen at scale
- **Two-phase loading**: Pre-loading with one method, then iterating with a different method that returns additional IDs not in the pre-load

When you see a query inside a loop with an `if` guard, ask: "What conditions cause this query to execute, and how often do those conditions occur?" If the answer is "depends on data" or "edge cases", treat it as a likely N+1.

**Optimization patterns:**

- Use `only()` or `defer()` to limit loaded fields
- Use `annotate()` for aggregations instead of Python loops
- Bulk operations: `bulk_create()`, `bulk_update()` over loops
- Use `values()` or `values_list()` for simple data extraction

**Query organization:**

- Complex queries belong in model managers/querysets
- Avoid raw SQL unless necessary for performance
- Use `F()` expressions for field comparisons
- Use `Q()` objects for complex query logic

## Views & URL Patterns

**Class-Based Views (CBVs):**

- Use generic views (ListView, DetailView, etc.) when possible
- Override get_queryset() for filtering, not get()
- Use mixins for reusable behavior
- Keep business logic in models/services, not views

**Function-Based Views (FBVs):**

- Simpler than CBVs for straightforward cases
- Use decorators for common patterns (@login_required, @require_http_methods)
- Keep views thin - delegate to models/services

**Anti-patterns:**

- Business logic in views - move to models or service layer
- Missing input validation - use forms/serializers
- Mixing HTML rendering and API responses in same view

## Forms & Validation

**Form best practices:**

- Always use Django forms for user input
- Define validation in clean_field() methods
- Use ModelForm when working with models
- Custom validation in clean() for cross-field checks

**Security:**

- Never trust user input - validate everything
- Use form validation, not manual checks
- CSRF protection enabled by default - don't disable
- Use form.is_valid() before accessing cleaned_data

## Middleware & Request/Response

**Middleware patterns:**

- Keep middleware focused and fast
- Avoid expensive operations in middleware
- Order matters - authentication before authorization
- Use process_exception for centralized error handling

**Request handling:**

- Access request.user for authentication
- Use request.META for headers (X-Forwarded-For, etc.)
- Don't store mutable state in middleware

## Security Best Practices

**Critical checks:**

- Always use parameterized queries (ORM does this)
- Validate and sanitize user input with forms
- Use Django's auth decorators (@login_required)
- Check permissions with user.has_perm()
- CSRF protection active on state-changing requests
- Never use mark_safe() on user input

**Common vulnerabilities:**

- SQL injection - avoid raw SQL with user input
- XSS - auto-escape templates, careful with mark_safe
- Mass assignment - use fields/exclude in ModelForm

## Async Django Patterns

**When to use async:**

- I/O-bound operations (external APIs, file operations)
- WebSocket connections
- Long-polling endpoints

**Critical issues:**

- Mixing sync and async incorrectly
- ORM operations in async views without sync_to_async
- Missing await keywords
- Blocking operations in async functions

**Utilities:**

- Use `sync_to_async` for ORM in async views
- Use `async_to_sync` for async code in sync contexts

## Testing Patterns

**Django test structure:**

- Use TestCase for database tests
- Use TransactionTestCase for transaction testing
- Use SimpleTestCase for non-database tests
- Mock external services with unittest.mock

**Best practices:**

- Use setUpTestData for shared test data
- Override settings with override_settings
- Use Client for view testing
- Factory patterns over fixtures for flexibility

**Anti-patterns:**

- Tests depending on execution order
- Fixtures that get stale and unmaintained
- Not cleaning up after tests

## Migration Best Practices

**Safe migration patterns:**

- Separate data and schema migrations
- Test migrations on production-like data
- Reversible migrations when possible
- Avoid circular dependencies

**Dangerous patterns:**

- Renaming fields without data migration
- Removing fields with data
- Not squashing old migrations periodically

## Signal Usage

**When to use signals:**

- Cross-app communication
- Extending third-party app behavior
- Audit logging

**Anti-patterns:**

- Using signals when direct calls are clearer
- Complex business logic in signal handlers
- Signals modifying sender (causes confusion)
- Missing signal receiver cleanup

## Admin Customization

**Good practices:**

- Customize list_display for useful admin views
- Use list_filter for common queries
- Add search_fields for searchability
- Use readonly_fields for computed values

**Performance:**

- Override get_queryset for select_related/prefetch_related
- Use list_select_related for foreign keys
- Limit list_per_page for large tables

## Caching Strategies

**Cache patterns:**

- Use cache_page for entire views
- Use cached_property for expensive model properties
- Template fragment caching for partial caching
- Low-level cache API for custom caching

**Cache keys:**

- Include relevant parameters in cache keys
- Version cache keys when schema changes
- Set appropriate timeouts

## Settings & Configuration

**Best practices:**

- Use environment variables for secrets
- Separate settings by environment (dev/staging/prod)
- Use django-environ or similar for config
- Never commit secrets to version control

**Security settings:**

- DEBUG = False in production
- ALLOWED_HOSTS configured properly
- SECRET_KEY unique and secret
- SECURE_SSL_REDIRECT in production

## Common Anti-Patterns

**ORM misuse:**

- Multiple saves in loop (use bulk operations)
- Not using transactions for multi-step operations
- Accessing related objects without prefetch

**View patterns:**

- God views doing too much
- Direct model access in templates
- Missing error handling

**General:**

- Circular imports between apps
- Tight coupling between apps
- Not following Django app structure
