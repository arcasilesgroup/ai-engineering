# Python Coding Standards

These standards define how Python code must be written and maintained. They apply to all Python projects and override the universal base standards where specified. When generating or modifying Python code, follow every rule in this document unless the project's own configuration explicitly overrides it.

---

## PEP 8 Compliance

### Indentation

- Use 4 spaces per indentation level. Never use tabs.
- Continuation lines must align with the opening delimiter or use a hanging indent with 4 additional spaces.

```python
# DO - aligned with opening delimiter
result = some_function(arg_one, arg_two,
                       arg_three, arg_four)

# DO - hanging indent
result = some_function(
    arg_one, arg_two,
    arg_three, arg_four,
)

# DON'T - no indentation on continuation
result = some_function(arg_one, arg_two,
arg_three, arg_four)
```

### Line Length

- Maximum line length is 88 characters (Black formatter default). This overrides PEP 8's 79-character recommendation.
- URLs in comments and docstrings may exceed this limit rather than being broken across lines.
- Use implicit line continuation inside parentheses, brackets, and braces rather than backslash continuation.

```python
# DO - implicit continuation
users = [
    user for user in all_users
    if user.is_active and user.has_permission("read")
]

# DON'T - backslash continuation
users = [user for user in all_users \
    if user.is_active and user.has_permission("read")]
```

### Blank Lines

- Two blank lines before and after top-level function and class definitions.
- One blank line between methods inside a class.
- Use single blank lines sparingly within functions to separate logical sections.
- No blank line after a `def` line or after a `class` line before the docstring.

### Naming Conventions

| Entity | Convention | Example |
|---|---|---|
| Modules | `snake_case` | `user_service.py` |
| Packages | `snake_case` (short, no underscores preferred) | `mypackage` |
| Classes | `PascalCase` | `UserRepository` |
| Functions | `snake_case` | `get_active_users` |
| Methods | `snake_case` | `calculate_total` |
| Variables | `snake_case` | `user_count` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Type variables | `PascalCase` (short) | `T`, `KT`, `VT` |
| Type aliases | `PascalCase` | `UserId`, `JsonDict` |
| Private | `_leading_underscore` | `_internal_cache` |
| Name-mangled | `__double_leading` | `__secret` (avoid unless necessary) |
| Dunder | `__name__` | Reserved for Python, never invent new ones |

```python
# DO
class PaymentProcessor:
    MAX_RETRIES = 3

    def __init__(self, gateway: PaymentGateway) -> None:
        self._gateway = gateway
        self._retry_count = 0

    def process_payment(self, amount: Decimal) -> PaymentResult:
        ...

# DON'T
class paymentProcessor:
    maxRetries = 3

    def __init__(self, Gateway):
        self.Gateway = Gateway
        self.retryCount = 0

    def ProcessPayment(self, Amount):
        ...
```

### Trailing Commas

- Always use trailing commas in multi-line structures (function arguments, lists, dicts, tuples, imports). This produces cleaner diffs.

```python
# DO
users = [
    "alice",
    "bob",
    "charlie",
]

def create_user(
    name: str,
    email: str,
    role: UserRole = UserRole.MEMBER,
) -> User:
    ...

# DON'T
users = [
    "alice",
    "bob",
    "charlie"
]
```

### Whitespace

- No whitespace immediately inside parentheses, brackets, or braces.
- One space around assignment, comparison, and binary operators.
- No space before a colon in slices; no space before the opening parenthesis of a function call.
- No trailing whitespace on any line.

```python
# DO
result = items[1:3]
value = mapping["key"]
func(arg1, arg2)

# DON'T
result = items[ 1 : 3 ]
value = mapping ["key"]
func (arg1 , arg2)
```

---

## Type Hints

### When to Annotate

- Annotate every function signature: all parameters and return types.
- Annotate class attributes and instance variables in `__init__`.
- Annotate variables where the type is not obvious from the assignment.
- Do not annotate variables where the type is obvious (e.g., `name = "Alice"` does not need `: str`).

```python
# DO - annotate function signatures
def fetch_users(
    session: AsyncSession,
    *,
    active_only: bool = True,
    limit: int = 100,
) -> list[User]:
    ...

# DO - annotate when type is non-obvious
raw_data: dict[str, Any] = json.loads(response.text)
user_ids: set[int] = set()

# DON'T - annotate when type is obvious
name: str = "Alice"  # unnecessary
count: int = 0  # unnecessary
```

### Modern Type Hint Syntax (Python 3.11+)

- Use built-in generics: `list[int]`, `dict[str, Any]`, `set[str]`, `tuple[int, ...]` instead of importing from `typing`.
- Use `X | None` instead of `Optional[X]`.
- Use `X | Y` instead of `Union[X, Y]`.
- Use `type` statement for type aliases (Python 3.12+) or `TypeAlias` annotation (Python 3.11).

```python
# DO - modern syntax
def find_user(user_id: int) -> User | None:
    ...

def parse_input(value: str | int | float) -> str:
    ...

type UserId = int
type JsonDict = dict[str, Any]

# DON'T - legacy syntax
from typing import Optional, Union, List, Dict

def find_user(user_id: int) -> Optional[User]:
    ...

def parse_input(value: Union[str, int, float]) -> str:
    ...
```

### Self Type

- Use `Self` from `typing` for methods that return the instance or the class itself.

```python
from typing import Self

class Builder:
    def with_name(self, name: str) -> Self:
        self._name = name
        return self

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> Self:
        instance = cls()
        instance._name = config["name"]
        return instance
```

### TypedDict

- Use `TypedDict` for dictionaries with a known, fixed set of string keys where each key has a specific value type.
- Prefer dataclasses or Pydantic models over `TypedDict` for most use cases.

```python
from typing import TypedDict, NotRequired

class UserPayload(TypedDict):
    name: str
    email: str
    age: NotRequired[int]
```

### Callable Types

- Use `collections.abc.Callable` for callable type hints.
- Use `ParamSpec` and `TypeVar` for decorator type hints to preserve signatures.

```python
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def retry(max_attempts: int) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            ...
        return wrapper
    return decorator
```

### Generics

- Use `TypeVar` for generic functions and classes.
- Use `Protocol` for structural typing constraints.

```python
from typing import TypeVar

T = TypeVar("T")

def first(items: list[T]) -> T | None:
    return items[0] if items else None
```

---

## Modern Python Features (3.11+)

### Structural Pattern Matching (match/case)

- Use `match`/`case` for complex conditional dispatch, especially when matching against structure.
- Prefer `match`/`case` over long `if`/`elif`/`else` chains when checking against types, shapes, or enum values.
- Always include a wildcard `case _` as the final branch.

```python
# DO
match command:
    case {"action": "create", "payload": payload}:
        return create_resource(payload)
    case {"action": "delete", "id": resource_id}:
        return delete_resource(resource_id)
    case {"action": action}:
        raise UnsupportedActionError(action)
    case _:
        raise MalformedCommandError(command)

# DO - matching against types
match event:
    case UserCreatedEvent(user_id=uid):
        await notify_admin(uid)
    case OrderPlacedEvent(order_id=oid, total=total) if total > 1000:
        await flag_large_order(oid)
    case _:
        logger.debug("Unhandled event: %s", type(event).__name__)
```

### StrEnum

- Use `StrEnum` for string enumerations that need to serialize as strings.

```python
from enum import StrEnum

class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

# This works directly in string contexts
status = OrderStatus.PENDING
assert status == "pending"
assert f"Status: {status}" == "Status: pending"
```

### Exception Groups and except*

- Use `ExceptionGroup` and `except*` when handling multiple concurrent failures (e.g., from `asyncio.TaskGroup`).

```python
async def fetch_all(urls: list[str]) -> list[Response]:
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch(url)) for url in urls]
    except* ConnectionError as eg:
        logger.error("Connection failures: %d", len(eg.exceptions))
        raise
    except* TimeoutError as eg:
        logger.warning("Timeouts: %d", len(eg.exceptions))
        raise
    return [task.result() for task in tasks]
```

### Tomllib

- Use the built-in `tomllib` module (Python 3.11+) for reading TOML files. Do not install `toml` or `tomli` as separate packages.

```python
import tomllib
from pathlib import Path

config = tomllib.loads(Path("pyproject.toml").read_text())
```

---

## Dataclasses and Pydantic Models

### When to Use Dataclasses

- Use `dataclasses` for internal data structures that do not require validation, serialization, or parsing from external input.
- Use dataclasses for value objects, DTOs between internal layers, configuration records, and domain entities.

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError(f"Amount cannot be negative: {self.amount}")

@dataclass(slots=True)
class UserProfile:
    user_id: int
    username: str
    email: str
    roles: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
```

- Prefer `frozen=True` for immutable data structures.
- Always use `slots=True` for memory efficiency and attribute access speed.
- Use `field(default_factory=...)` for mutable defaults.

### When to Use Pydantic

- Use Pydantic models for data that crosses a trust boundary: API request/response bodies, configuration from files or environment, database query results, and any external input.
- Use Pydantic v2 (`BaseModel` from `pydantic`). Do not use Pydantic v1 API.

```python
from pydantic import BaseModel, Field, field_validator, ConfigDict

class CreateUserRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=r"^[\w.+-]+@[\w-]+\.[\w.]+$")
    age: int = Field(ge=0, le=200)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name must not be blank")
        return v.strip()

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    is_active: bool
```

### Choosing Between Them

| Criterion | Dataclass | Pydantic |
|---|---|---|
| External input (API, file, env) | No | Yes |
| Internal data transfer | Yes | Acceptable |
| Needs validation | Simple (`__post_init__`) | Complex |
| Needs JSON serialization | Manual | Built-in |
| Performance-critical internal | Yes | No (overhead) |
| ORM integration | Yes (with care) | Yes (`from_attributes`) |

---

## Async/Await Patterns

### General Rules

- Use `async`/`await` for I/O-bound operations: HTTP calls, database queries, file I/O, message queues.
- Do not use `async` for CPU-bound work. Use `concurrent.futures.ProcessPoolExecutor` and `asyncio.loop.run_in_executor` instead.
- Never call `asyncio.run()` inside an already-running event loop. Structure your application so the entry point calls `asyncio.run()` once.
- Never use `time.sleep()` in async code. Use `await asyncio.sleep()`.

```python
# DO
async def fetch_user_data(user_id: int) -> UserData:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/users/{user_id}") as response:
            response.raise_for_status()
            data = await response.json()
            return UserData(**data)

# DON'T - blocking call in async context
async def fetch_user_data(user_id: int) -> UserData:
    response = requests.get(f"{API_URL}/users/{user_id}")  # blocks the event loop
    return UserData(**response.json())
```

### Async Context Managers

- Use `async with` for resources that require async setup and teardown.
- Implement `__aenter__` and `__aexit__` or use `@asynccontextmanager`.

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

### Async Generators

- Use `async for` to consume async generators.
- Use `AsyncGenerator` type hint from `collections.abc`.

```python
from collections.abc import AsyncGenerator

async def stream_events(
    topic: str,
) -> AsyncGenerator[Event, None]:
    async with connect_to_broker(topic) as consumer:
        async for message in consumer:
            yield Event.from_message(message)

# Consuming
async for event in stream_events("orders"):
    await process_event(event)
```

### Task Groups (Python 3.11+)

- Use `asyncio.TaskGroup` for concurrent task execution instead of `asyncio.gather()`.
- `TaskGroup` provides better error handling and automatic cancellation.

```python
# DO - TaskGroup
async def fetch_all_profiles(user_ids: list[int]) -> list[UserProfile]:
    async with asyncio.TaskGroup() as tg:
        tasks = [
            tg.create_task(fetch_profile(uid))
            for uid in user_ids
        ]
    return [task.result() for task in tasks]

# ACCEPTABLE - gather with return_exceptions
results = await asyncio.gather(*coros, return_exceptions=True)
errors = [r for r in results if isinstance(r, Exception)]
```

### Semaphores for Rate Limiting

```python
semaphore = asyncio.Semaphore(10)

async def rate_limited_fetch(url: str) -> Response:
    async with semaphore:
        return await fetch(url)
```

---

## FastAPI Conventions

### Application Structure

```
src/
  app/
    __init__.py
    main.py              # FastAPI app creation, lifespan
    config.py            # Settings via pydantic-settings
    dependencies.py      # Shared Depends() callables
    routers/
      __init__.py
      users.py
      orders.py
    models/
      __init__.py
      user.py            # SQLAlchemy models
      order.py
    schemas/
      __init__.py
      user.py            # Pydantic request/response models
      order.py
    services/
      __init__.py
      user_service.py
      order_service.py
    repositories/
      __init__.py
      user_repository.py
```

### Routers

- One router per resource/domain area.
- Use `APIRouter` with a prefix and tags.
- Keep route handlers thin: validate input, call a service, return a response.

```python
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=list[UserResponse])
async def list_users(
    service: UserService = Depends(get_user_service),
    pagination: PaginationParams = Depends(),
) -> list[UserResponse]:
    return await service.list_users(
        offset=pagination.offset,
        limit=pagination.limit,
    )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return user

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.create_user(payload)
```

### Dependencies

- Use `Depends()` for dependency injection. Create reusable dependency functions.
- Use `yield` dependencies for resources that need cleanup (database sessions, HTTP clients).

```python
from collections.abc import AsyncGenerator
from fastapi import Depends

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

async def get_user_service(
    session: AsyncSession = Depends(get_db_session),
) -> UserService:
    return UserService(UserRepository(session))

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    user = await authenticate(token, session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
```

### Lifespan Events

- Use the `lifespan` async context manager pattern (not the deprecated `@app.on_event`).

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    await init_db()
    await warm_caches()
    yield
    # Shutdown
    await close_db_pool()
    await flush_metrics()

app = FastAPI(lifespan=lifespan)
```

### Middleware

- Use ASGI middleware for cross-cutting concerns (logging, timing, correlation IDs).
- Order matters: middleware executes in the order it is added (outermost first).

```python
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Error Responses

- Use structured error responses with consistent format.
- Register exception handlers for custom exception types.

```python
from fastapi import Request
from fastapi.responses import JSONResponse

class AppError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        },
    )
```

---

## Django Conventions

### Models

- One model per concept. Keep models focused.
- Use `Meta` class for ordering, constraints, indexes, and verbose names.
- Define `__str__` on every model.
- Use custom managers and querysets for reusable query logic.

```python
from django.db import models

class UserManager(models.Manager):
    def active(self) -> models.QuerySet["User"]:
        return self.filter(is_active=True)

    def with_recent_orders(self) -> models.QuerySet["User"]:
        return self.prefetch_related(
            models.Prefetch(
                "orders",
                queryset=Order.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=30)
                ),
            )
        )

class User(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["is_active", "-created_at"]),
        ]

    def __str__(self) -> str:
        return self.email
```

### Views

- Prefer class-based views (CBVs) for standard CRUD operations.
- Prefer function-based views (FBVs) for simple, one-off endpoints.
- Use Django REST Framework (DRF) for API views.
- Keep views thin: validate, delegate to service, return response.

```python
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

class UserListCreateView(generics.ListCreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> models.QuerySet[User]:
        return User.objects.active()

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def reset_password(request: Request) -> Response:
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    send_reset_email(serializer.validated_data["email"])
    return Response({"status": "ok"})
```

### Serializers (DRF)

- Use `ModelSerializer` for straightforward model serialization.
- Use explicit `Serializer` for complex or non-model payloads.
- Validate at the serializer level, not in the view.

```python
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value.lower()
```

### Signals

- Use signals sparingly. They create implicit coupling and make code harder to trace.
- Never use signals for critical business logic. Use explicit service calls instead.
- Acceptable uses: audit logging, cache invalidation, denormalization.

```python
# ACCEPTABLE - audit logging
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def log_user_creation(sender: type, instance: User, created: bool, **kwargs: Any) -> None:
    if created:
        audit_logger.info("User created: %s", instance.email)

# DON'T - business logic in signals
@receiver(post_save, sender=Order)
def process_order(sender, instance, created, **kwargs):
    if created:
        charge_payment(instance)  # This belongs in a service
        send_confirmation_email(instance)  # This too
```

---

## Module Organization

### Source Layout

- Use the `src` layout for all packages intended to be distributed or deployed.
- The `src` layout prevents accidental imports from the working directory.

```
project-root/
  pyproject.toml
  src/
    mypackage/
      __init__.py
      main.py
      config.py
      domain/
        __init__.py
        models.py
        services.py
      infrastructure/
        __init__.py
        database.py
        cache.py
      api/
        __init__.py
        routes.py
        schemas.py
  tests/
    __init__.py
    conftest.py
    test_services.py
    test_routes.py
```

### `__init__.py`

- `__init__.py` files must only contain imports that define the package's public API.
- Never put business logic, function definitions, or class definitions in `__init__.py`.
- Use `__all__` to define the public API explicitly.

```python
# src/mypackage/domain/__init__.py
from mypackage.domain.models import User, Order
from mypackage.domain.services import UserService, OrderService

__all__ = ["User", "Order", "UserService", "OrderService"]
```

### Import Style

- Use absolute imports from the package root for cross-module imports.
- Use relative imports only within the same sub-package when the module is tightly coupled.
- Never use relative imports that traverse upward more than one level (`from ...foo import bar`).

```python
# DO - absolute imports
from mypackage.domain.models import User
from mypackage.infrastructure.database import get_session

# ACCEPTABLE - relative import within same sub-package
from .models import User
from .services import UserService

# DON'T - deep relative imports
from ...infrastructure.database import get_session
```

---

## Import Ordering

Imports must be ordered in three groups separated by a blank line:

1. Standard library imports
2. Third-party imports
3. Local application imports

Within each group, sort alphabetically. Use `isort` with the `black` profile.

```python
# DO
import asyncio
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from mypackage.config import settings
from mypackage.domain.models import User
from mypackage.services.user_service import UserService
```

### isort Configuration

```toml
# pyproject.toml
[tool.isort]
profile = "black"
known_first_party = ["mypackage"]
known_third_party = ["fastapi", "pydantic", "sqlalchemy"]
```

---

## Exception Handling

### Catch Specific Exceptions

- Never use bare `except:`. At minimum, catch `Exception`.
- Catch the most specific exception type possible.
- Order except blocks from most specific to most general.

```python
# DO
try:
    user = await repository.get(user_id)
except RecordNotFoundError:
    raise HTTPException(status_code=404, detail="User not found")
except DatabaseConnectionError as e:
    logger.error("Database unreachable: %s", e)
    raise HTTPException(status_code=503, detail="Service unavailable")

# DON'T
try:
    user = await repository.get(user_id)
except:
    return None  # swallows all errors silently
```

### Custom Exception Hierarchy

- Define a base exception for your application.
- Derive domain-specific exceptions from it.
- Include contextual information in exception attributes.

```python
class AppError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code

class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(
            f"{resource} with id '{identifier}' not found",
            code="NOT_FOUND",
        )
        self.resource = resource
        self.identifier = identifier

class ValidationError(AppError):
    """Raised when input validation fails."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(
            f"Validation failed for '{field}': {message}",
            code="VALIDATION_ERROR",
        )
        self.field = field
```

### Re-raising Exceptions

- Use bare `raise` to re-raise the current exception, preserving the original traceback.
- Use `raise NewError(...) from original` to chain exceptions.

```python
# DO - preserve traceback
try:
    result = parse_config(raw)
except toml.TOMLDecodeError:
    logger.error("Config file is malformed")
    raise

# DO - chain exceptions
try:
    data = json.loads(raw)
except json.JSONDecodeError as e:
    raise ConfigError(f"Invalid JSON in config: {e}") from e

# DON'T - lose traceback
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    raise ConfigError("Invalid config")  # original traceback lost
```

### Context Managers for Cleanup

- Always use `with` / `async with` for resources that must be cleaned up.
- Implement `__enter__`/`__exit__` or use `@contextmanager` for custom context managers.

```python
from contextlib import contextmanager
from collections.abc import Generator

@contextmanager
def temporary_directory() -> Generator[Path, None, None]:
    path = Path(tempfile.mkdtemp())
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)

# Usage
with temporary_directory() as tmp:
    write_files(tmp)
    process(tmp)
# Directory is cleaned up even if an exception occurs
```

---

## Logging

### Use the logging Module

- Never use `print()` for operational output. Use the `logging` module.
- Create loggers per module using `__name__`.
- Configure logging once at the application entry point.

```python
import logging

logger = logging.getLogger(__name__)

def process_order(order_id: int) -> None:
    logger.info("Processing order %d", order_id)
    try:
        result = charge_payment(order_id)
        logger.debug("Payment result: %s", result)
    except PaymentError:
        logger.exception("Payment failed for order %d", order_id)
        raise
```

### Log Levels

| Level | Use For |
|---|---|
| `DEBUG` | Detailed diagnostic information. Only visible in development. |
| `INFO` | Confirmation that things are working as expected. Key business events. |
| `WARNING` | Something unexpected happened but the application can continue. |
| `ERROR` | A function failed to perform its task. Requires attention. |
| `CRITICAL` | The application cannot continue. Immediate action required. |

### Structured Logging

- Use `structlog` or `python-json-logger` for production environments.
- Include correlation IDs, request IDs, and contextual metadata.

```python
import structlog

logger = structlog.get_logger()

async def process_order(order_id: int, user_id: int) -> None:
    log = logger.bind(order_id=order_id, user_id=user_id)
    log.info("processing_order")
    try:
        result = await charge_payment(order_id)
        log.info("payment_charged", amount=result.amount)
    except PaymentError as e:
        log.error("payment_failed", error=str(e))
        raise
```

### Logging Best Practices

- Use lazy formatting (`logger.info("User %s", user_id)`) not f-strings (`logger.info(f"User {user_id}")`). Lazy formatting avoids string construction when the log level is disabled.
- Use `logger.exception()` inside `except` blocks to automatically include the traceback.
- Never log sensitive data: passwords, tokens, PII, credit card numbers.
- Log at function boundaries: entry (with key parameters) and exit (with outcome).

---

## Docstrings

### Style

- Use Google style docstrings as the default.
- Every public module, class, function, and method must have a docstring.
- Private functions need docstrings only when the behavior is non-obvious.

```python
def calculate_shipping_cost(
    weight_kg: float,
    destination: str,
    *,
    express: bool = False,
) -> Decimal:
    """Calculate the shipping cost for a package.

    Uses the standard rate table for domestic shipments and the
    international surcharge table for foreign destinations.

    Args:
        weight_kg: Package weight in kilograms. Must be positive.
        destination: ISO 3166-1 alpha-2 country code.
        express: If True, applies express delivery surcharge.

    Returns:
        The total shipping cost in USD.

    Raises:
        ValueError: If weight_kg is not positive.
        UnsupportedDestinationError: If destination is not serviceable.

    Example:
        >>> calculate_shipping_cost(2.5, "US")
        Decimal('12.50')
        >>> calculate_shipping_cost(2.5, "US", express=True)
        Decimal('25.00')
    """
```

### Class Docstrings

```python
class OrderProcessor:
    """Processes customer orders through the fulfillment pipeline.

    Coordinates payment charging, inventory reservation, and
    shipment scheduling. Uses the configured payment gateway and
    warehouse API.

    Attributes:
        gateway: The payment gateway instance.
        warehouse: The warehouse management client.
        max_retries: Maximum retry attempts for transient failures.

    Example:
        >>> processor = OrderProcessor(gateway, warehouse)
        >>> result = await processor.process(order)
    """
```

### Module Docstrings

- Every module should have a docstring at the top explaining its purpose.

```python
"""User authentication and authorization services.

This module provides JWT-based authentication, role-based access
control, and session management for the application's API layer.

Typical usage:
    from mypackage.auth import authenticate, require_role

    user = await authenticate(token)
    require_role(user, "admin")
"""
```

---

## Generators and Iterators

### Use Generators for Lazy Evaluation

- Use generators when processing large datasets that should not be loaded entirely into memory.
- Prefer generator expressions over list comprehensions when the result is iterated only once.

```python
# DO - generator for large datasets
def read_large_csv(path: Path) -> Generator[dict[str, str], None, None]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row

# DO - generator expression (lazy)
total = sum(order.total for order in orders)

# DON'T - list comprehension when only iterating once (wastes memory)
total = sum([order.total for order in orders])
```

### itertools for Complex Iteration

```python
import itertools

# Batch processing
def batched(iterable: Iterable[T], n: int) -> Generator[tuple[T, ...], None, None]:
    """Batch an iterable into tuples of size n (use itertools.batched in 3.12+)."""
    it = iter(iterable)
    while batch := tuple(itertools.islice(it, n)):
        yield batch

# Usage
for batch in batched(all_records, 100):
    await bulk_insert(batch)
```

---

## Decorators

### Function Decorators

- Always use `@functools.wraps` to preserve the wrapped function's metadata.
- Use `ParamSpec` and `TypeVar` for type-safe decorators.

```python
import functools
import time
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def timing(func: Callable[P, R]) -> Callable[P, R]:
    """Log the execution time of a function."""
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info("%s took %.3fs", func.__name__, elapsed)
        return result
    return wrapper
```

### Decorator Factories

```python
def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry a function on failure with exponential backoff."""
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exception: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    sleep_time = delay * (2 ** attempt)
                    logger.warning(
                        "Attempt %d/%d for %s failed: %s. Retrying in %.1fs",
                        attempt + 1, max_attempts, func.__name__, e, sleep_time,
                    )
                    time.sleep(sleep_time)
            raise last_exception  # type: ignore[misc]
        return wrapper
    return decorator

# Usage
@retry(max_attempts=3, delay=0.5, exceptions=(ConnectionError, TimeoutError))
def fetch_data(url: str) -> dict[str, Any]:
    ...
```

---

## Protocols and ABCs

### Prefer Protocols (Structural Typing)

- Use `Protocol` for interface definitions. This allows structural subtyping (duck typing with type safety).
- Do not require classes to explicitly inherit from the Protocol.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Repository(Protocol[T]):
    async def get(self, id: int) -> T | None: ...
    async def save(self, entity: T) -> T: ...
    async def delete(self, id: int) -> None: ...

class UserRepository:
    """Implements Repository[User] structurally -- no inheritance needed."""

    async def get(self, id: int) -> User | None:
        ...

    async def save(self, entity: User) -> User:
        ...

    async def delete(self, id: int) -> None:
        ...

# This works because UserRepository structurally matches Repository[User]
def get_service(repo: Repository[User]) -> UserService:
    return UserService(repo)
```

### Use ABCs When

- The interface needs to enforce implementation (abstract methods that must be overridden).
- You need to share concrete method implementations across subclasses.
- The hierarchy is well-defined and unlikely to change.

```python
from abc import ABC, abstractmethod

class NotificationSender(ABC):
    @abstractmethod
    async def send(self, recipient: str, message: str) -> None:
        """Send a notification to the recipient."""

    def format_message(self, template: str, **kwargs: str) -> str:
        """Shared formatting logic."""
        return template.format(**kwargs)

class EmailSender(NotificationSender):
    async def send(self, recipient: str, message: str) -> None:
        await self._smtp_client.send(to=recipient, body=message)

class SmsSender(NotificationSender):
    async def send(self, recipient: str, message: str) -> None:
        await self._sms_client.send(phone=recipient, text=message)
```

---

## Dependency Injection

### Manual Injection

- Pass dependencies as constructor parameters or function arguments.
- This is the simplest and most Pythonic approach for small applications.

```python
class OrderService:
    def __init__(
        self,
        order_repo: OrderRepository,
        payment_gateway: PaymentGateway,
        notifier: NotificationSender,
    ) -> None:
        self._order_repo = order_repo
        self._payment_gateway = payment_gateway
        self._notifier = notifier

    async def place_order(self, order: Order) -> OrderResult:
        ...

# Composition root
def create_order_service(session: AsyncSession) -> OrderService:
    return OrderService(
        order_repo=SqlAlchemyOrderRepository(session),
        payment_gateway=StripeGateway(settings.stripe_key),
        notifier=EmailSender(settings.smtp_config),
    )
```

### FastAPI Depends

- In FastAPI, use `Depends()` for automatic dependency injection (see FastAPI section above).

---

## Configuration Management

### pydantic-settings

- Use `pydantic-settings` for environment-based configuration.
- Define all configuration in a single `Settings` class.
- Never read `os.environ` directly in business logic.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        case_sensitive=False,
    )

    # Database
    database_url: str
    database_pool_size: int = 10
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # External APIs
    stripe_api_key: str
    stripe_webhook_secret: str

    # Application
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]

settings = Settings()
```

### Environment Variables

- Use `.env` files for local development only. Never commit them.
- Use explicit environment variables in production (set by the deployment platform).
- Prefix all environment variables with the application name to avoid collisions.

```bash
# .env (local development only - never commit)
APP_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mydb
APP_JWT_SECRET=dev-secret-do-not-use-in-production
APP_STRIPE_API_KEY=sk_test_...
```

---

## API Design

### RESTful Conventions

| Action | Method | Path | Status |
|---|---|---|---|
| List | `GET` | `/resources` | 200 |
| Create | `POST` | `/resources` | 201 |
| Get | `GET` | `/resources/{id}` | 200 |
| Full update | `PUT` | `/resources/{id}` | 200 |
| Partial update | `PATCH` | `/resources/{id}` | 200 |
| Delete | `DELETE` | `/resources/{id}` | 204 |

### Pagination

- Use cursor-based pagination for large datasets. Use offset-based only for small, stable datasets.
- Always include pagination metadata in responses.

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    has_more: bool
    next_cursor: str | None = None

class PaginationParams(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
```

### Filtering and Sorting

```python
@router.get("/orders", response_model=PaginatedResponse[OrderResponse])
async def list_orders(
    status: OrderStatus | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    sort_by: str = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    pagination: PaginationParams = Depends(),
    service: OrderService = Depends(get_order_service),
) -> PaginatedResponse[OrderResponse]:
    ...
```

### Error Response Format

- Use a consistent error response format across all endpoints.

```python
class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None

class ErrorResponse(BaseModel):
    error: ErrorDetail

# Example response:
# {
#     "error": {
#         "code": "VALIDATION_ERROR",
#         "message": "Email format is invalid",
#         "field": "email"
#     }
# }
```

---

## Package Management

### pyproject.toml

- Use `pyproject.toml` as the single source of truth for project metadata, dependencies, and tool configuration.
- Do not use `setup.py` or `setup.cfg` for new projects.

```toml
[project]
name = "mypackage"
version = "1.0.0"
description = "My application"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "pydantic>=2.5.0",
    "sqlalchemy>=2.0.0",
    "uvicorn>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "mypy>=1.8.0",
    "ruff>=0.2.0",
]

[tool.ruff]
target-version = "py311"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "A", "SIM", "TCH"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### Virtual Environments

- Always use a virtual environment. Never install packages globally.
- Use `venv` (standard library), `uv`, or `poetry` for environment management.
- Add the virtual environment directory to `.gitignore`.

```bash
# Using uv (recommended for speed)
uv venv
uv pip install -e ".[dev]"

# Using standard venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Linting and Formatting

- Use `ruff` for both linting and formatting. It replaces `flake8`, `isort`, `pyupgrade`, and `black`.
- Use `mypy` in strict mode for type checking.
- Run all checks in CI. Block merges on failures.

```bash
# Format
ruff format .

# Lint and auto-fix
ruff check --fix .

# Type check
mypy src/
```

---

## Summary Checklist

| Standard | Check |
|---|---|
| PEP 8 | Does the code follow naming, spacing, and line length conventions? |
| Type hints | Are all function signatures annotated? Are modern syntax forms used? |
| Modern Python | Are 3.11+ features used where appropriate? |
| Data models | Is Pydantic used for external data and dataclasses for internal? |
| Async | Are I/O operations async? Are blocking calls avoided in async context? |
| Framework | Do FastAPI/Django patterns follow the conventions above? |
| Imports | Are imports ordered (stdlib, third-party, local) and absolute? |
| Exceptions | Are specific exceptions caught? Is context included in error messages? |
| Logging | Is `logging` used (not `print`)? Are log levels appropriate? |
| Docstrings | Do public APIs have Google-style docstrings? |
| Config | Is configuration managed via pydantic-settings? |
| Packaging | Is `pyproject.toml` the single source of truth? |
