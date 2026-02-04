# Python Standards

> Consolidated Python standards: PEP 8 compliance, type hints, data modeling, async patterns, error handling, and testing.

---

## 1. Code Style and PEP 8

### Core Rules

- Maximum line length: **88 characters** (Black formatter default)
- Use 4 spaces for indentation (never tabs)
- Two blank lines between top-level definitions
- One blank line between methods in a class
- Imports organized: stdlib, third-party, local (enforced by Ruff `isort`)

```python
# GOOD: Organized imports
import os
from datetime import datetime
from pathlib import Path

import httpx
from pydantic import BaseModel

from app.models import User
from app.services.auth import AuthService
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `user_service.py`, `auth_utils.py` |
| Packages | snake_case | `data_access`, `api_clients` |
| Classes | PascalCase | `UserService`, `HttpClient` |
| Functions | snake_case | `get_user`, `calculate_total` |
| Variables | snake_case | `user_name`, `total_count` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| Private | _prefix | `_internal_method`, `_cache` |
| Type variables | PascalCase | `T`, `ResponseT`, `ItemType` |
| Protocols | PascalCase, suffix -able/-Protocol | `Serializable`, `Repository` |

---

## 2. Type Hints

### Always Use Type Hints

```python
# GOOD: Fully typed function
def get_user_by_email(email: str, include_inactive: bool = False) -> User | None:
    """Retrieve a user by email address."""
    query = select(User).where(User.email == email)
    if not include_inactive:
        query = query.where(User.is_active.is_(True))
    return session.execute(query).scalar_one_or_none()

# GOOD: Complex types
from collections.abc import Sequence, Mapping

def process_items(
    items: Sequence[Item],
    config: Mapping[str, str],
    callback: Callable[[Item], bool] | None = None,
) -> list[ProcessedItem]:
    ...

# BAD: Missing type hints
def get_user_by_email(email, include_inactive=False):
    ...
```

### Generic Types

```python
from typing import TypeVar, Generic

T = TypeVar("T")

class Repository(Generic[T]):
    def __init__(self, model_class: type[T]) -> None:
        self._model_class = model_class

    async def get_by_id(self, entity_id: str) -> T | None:
        ...

    async def list_all(self, limit: int = 100) -> list[T]:
        ...
```

---

## 3. Data Modeling

### Pydantic for API/External Data

```python
from pydantic import BaseModel, Field, field_validator

class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(ge=0, le=150)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name must not be blank")
        return v.strip()

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

### Dataclasses for Internal Domain Objects

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Money:
    amount: int  # Store as cents
    currency: str = "USD"

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)

@dataclass
class OrderLine:
    product_id: str
    quantity: int
    unit_price: Money
    metadata: dict[str, str] = field(default_factory=dict)
```

### Model Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|-------------|---------|-----------------|
| Plain dicts for structured data | No validation, no IDE support | Use Pydantic or dataclass |
| Mutable default arguments | Shared state between calls | Use `field(default_factory=...)` |
| Mixing API and domain models | Coupling layers | Separate request/response/domain |
| Optional everywhere | Unclear contracts | Only use Optional when truly nullable |

---

## 4. Async/Await Patterns

```python
import asyncio
import httpx

# GOOD: Async with proper resource management
async def fetch_user_data(user_ids: list[str]) -> list[UserData]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [_fetch_single_user(client, uid) for uid in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    return [r for r in results if isinstance(r, UserData)]

async def _fetch_single_user(client: httpx.AsyncClient, user_id: str) -> UserData:
    response = await client.get(f"/api/users/{user_id}")
    response.raise_for_status()
    return UserData.model_validate(response.json())

# GOOD: Async context manager
class DatabaseSession:
    async def __aenter__(self) -> "DatabaseSession":
        self._connection = await create_connection()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._connection.close()
```

---

## 5. Error Handling

### Custom Exceptions

```python
class AppError(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code

class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

class ValidationError(AppError):
    """Raised when input validation fails."""

class ExternalServiceError(AppError):
    """Raised when an external service call fails."""
```

### Result-Like Pattern

```python
from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar("T")

@dataclass(frozen=True)
class Success(Generic[T]):
    value: T

@dataclass(frozen=True)
class Failure:
    error: str
    code: str | None = None

type Result[T] = Success[T] | Failure

# Usage
def parse_age(value: str) -> Result[int]:
    try:
        age = int(value)
        if age < 0 or age > 150:
            return Failure("Age must be between 0 and 150", code="INVALID_AGE")
        return Success(age)
    except ValueError:
        return Failure(f"Cannot parse '{value}' as integer", code="PARSE_ERROR")

# Consuming results
match parse_age(raw_input):
    case Success(value=age):
        print(f"Valid age: {age}")
    case Failure(error=msg):
        print(f"Error: {msg}")
```

### Error Handling Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|-------------|---------|-----------------|
| Bare `except:` | Catches SystemExit, KeyboardInterrupt | Catch specific exceptions |
| `except Exception: pass` | Silently swallows errors | Log and re-raise or handle |
| Returning `None` on error | Caller must guess what happened | Use Result pattern or raise |
| Raising generic `Exception` | Uncatchable without catching all | Define custom exceptions |
| String error codes | Typo-prone, no IDE support | Use enums or typed constants |

---

## 6. Testing with pytest

### Test Structure

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.services.user_service import UserService

class TestUserService:
    """Tests for UserService."""

    @pytest.fixture
    def user_repository(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def service(self, user_repository: AsyncMock) -> UserService:
        return UserService(repository=user_repository)

    async def test_get_user_returns_user_when_found(
        self, service: UserService, user_repository: AsyncMock
    ) -> None:
        # Arrange
        expected_user = User(id="1", name="Alice", email="alice@test.com")
        user_repository.get_by_id.return_value = expected_user

        # Act
        result = await service.get_user("1")

        # Assert
        assert result == expected_user
        user_repository.get_by_id.assert_awaited_once_with("1")

    async def test_get_user_raises_not_found_when_missing(
        self, service: UserService, user_repository: AsyncMock
    ) -> None:
        user_repository.get_by_id.return_value = None

        with pytest.raises(NotFoundError, match="User 1 not found"):
            await service.get_user("1")
```

### Parametrize

```python
@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        ("alice@example.com", True),
        ("bob@test.co.uk", True),
        ("invalid-email", False),
        ("@no-local.com", False),
        ("no-domain@", False),
    ],
    ids=["valid_simple", "valid_subdomain", "missing_at", "missing_local", "missing_domain"],
)
def test_is_valid_email(input_value: str, expected: bool) -> None:
    assert is_valid_email(input_value) is expected
```

### Fixtures with Yield (Setup/Teardown)

```python
@pytest.fixture
async def database() -> AsyncGenerator[Database, None]:
    db = await Database.connect("sqlite+aiosqlite:///:memory:")
    await db.run_migrations()
    yield db
    await db.disconnect()
```

---

## 7. Ruff Configuration

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "S",    # flake8-bandit (security)
    "A",    # flake8-builtins
    "C4",   # flake8-comprehensions
    "DTZ",  # flake8-datetimez
    "RUF",  # Ruff-specific rules
]
ignore = ["E501"]  # Line length handled by formatter

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"]  # Allow assert in tests

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

---

## 8. Virtual Environments and Dependencies

### Always Use Virtual Environments

```bash
# Create with uv (recommended)
uv venv .venv
source .venv/bin/activate

# Or with standard venv
python -m venv .venv
source .venv/bin/activate
```

### Dependency Management with pyproject.toml

```toml
[project]
name = "my-service"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110.0",
    "pydantic>=2.6.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.3.0",
    "mypy>=1.9",
]
```

### Dependency Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|-------------|---------|-----------------|
| No pinned versions | Non-reproducible builds | Pin with `uv.lock` or `pip-compile` |
| Global pip install | Conflicts between projects | Always use virtual environments |
| `requirements.txt` only | No dev/prod separation | Use `pyproject.toml` with groups |
| Ignoring `mypy` errors | Hidden type bugs | Run `mypy --strict` in CI |

---

## 9. Project Structure

```
src/
  app/
    __init__.py
    main.py               # Application entry point
    config.py              # Settings (Pydantic BaseSettings)
    models/                # Domain models
    services/              # Business logic
    repositories/          # Data access
    api/                   # Route handlers
      routes/
      dependencies.py
    exceptions.py          # Custom exceptions
tests/
  conftest.py              # Shared fixtures
  test_services/
  test_repositories/
  test_api/
pyproject.toml
```
