---
applyTo: "**/*.py"
---

# Python Coding Standards for Copilot

These instructions apply to all Python files in this project. Follow these standards when generating or modifying code.

## Type Hints

Type hints are required on all public functions, methods, and class attributes.

```python
from typing import Optional

def get_user(user_id: str) -> Optional[User]:
    """Fetch user by ID."""
    return users.get(user_id)

def process_items(items: list[str]) -> dict[str, int]:
    """Count occurrences of each item."""
    return {item: items.count(item) for item in set(items)}

# Python 3.10+ union syntax
def parse_input(value: str | int) -> str:
    return str(value)
```

Use generic types for complex signatures:

```python
from typing import TypeVar, Generic, Callable

T = TypeVar('T')

def first_or_default(items: list[T], default: T) -> T:
    return items[0] if items else default

Handler = Callable[[Request], Response]
```

## PEP 8 and Ruff

- Follow PEP 8 style guidelines
- Code is linted and formatted by Ruff
- Maximum line length: 120 characters (configured in pyproject.toml)
- Use 4-space indentation
- Two blank lines before top-level definitions, one blank line before methods

## Naming Conventions

| Element       | Convention         | Example                          |
|--------------|--------------------|----------------------------------|
| Modules       | snake_case         | `user_service.py`                |
| Classes       | PascalCase         | `UserService`, `ApiClient`       |
| Functions     | snake_case         | `get_user`, `process_order`      |
| Variables     | snake_case         | `user_name`, `is_active`         |
| Constants     | UPPER_SNAKE_CASE   | `MAX_RETRIES`, `API_BASE_URL`    |
| Private       | _prefix            | `_internal_method`, `_cache`     |

## Dataclasses and Pydantic

Use dataclasses for simple data structures and Pydantic for validated models.

### Dataclasses

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class User:
    id: str
    name: str
    email: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    roles: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class Point:
    x: float
    y: float
```

### Pydantic Models

```python
from pydantic import BaseModel, EmailStr, validator

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    age: int

    @validator('age')
    def age_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('age must be positive')
        return v

    class Config:
        str_strip_whitespace = True
```

## Docstrings (Google Style)

All public functions and classes must have Google-style docstrings.

```python
def calculate_discount(
    price: float,
    discount_percent: float,
    max_discount: float | None = None
) -> float:
    """Calculate discounted price.

    Args:
        price: Original price in dollars.
        discount_percent: Discount percentage (0-100).
        max_discount: Maximum discount amount (optional).

    Returns:
        Final price after discount.

    Raises:
        ValueError: If discount_percent is not between 0 and 100.

    Example:
        >>> calculate_discount(100.0, 20.0)
        80.0
    """
```

## Error Handling

### Custom Exceptions

```python
class DomainError(Exception):
    """Base exception for domain errors."""
    pass

class NotFoundError(DomainError):
    """Resource not found."""
    def __init__(self, resource: str, id: str):
        self.resource = resource
        self.id = id
        super().__init__(f"{resource} with id '{id}' not found")
```

### Rules

- Define custom exception hierarchies rooted in a `DomainError` base
- Never use bare `except:` without re-raising
- Use `with pytest.raises(ExceptionType)` in tests
- Use context managers (`with`) for resource management

## Default Arguments

Never use mutable default arguments.

```python
# CORRECT
def process(items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    return [item.upper() for item in items]

# WRONG -- mutable default shared between calls
def process(items: list[str] = []) -> list[str]:
    items.append("new")
    return items
```

## Imports

Organize imports in this order (Ruff enforces this):
1. Standard library
2. Third-party packages
3. Local application imports

Never use `from module import *`.

## Async/Await

```python
import asyncio

async def fetch_user(user_id: str) -> User:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/users/{user_id}")
        return User(**response.json())

async def fetch_all_users(user_ids: list[str]) -> list[User]:
    tasks = [fetch_user(uid) for uid in user_ids]
    return await asyncio.gather(*tasks)
```

## File Organization

```
src/
    __init__.py
    main.py
    config.py
    models/
        __init__.py
        user.py
    services/
        __init__.py
        user_service.py
    api/
        __init__.py
        routes.py
    utils/
        __init__.py
        helpers.py
```

## pytest Testing

- Test framework: pytest with pytest-mock, pytest-cov, pytest-asyncio
- Test files in `tests/` directory: `test_module_name.py`
- Naming: `test_unit_scenario_expected`
- Use fixtures in `conftest.py` for shared setup
- Use `@pytest.mark.parametrize` for data-driven tests
- Use `@pytest.mark.asyncio` for async tests
- Follow Arrange/Act/Assert pattern

```python
import pytest

class TestUserService:
    def test_get_user_returns_user_when_exists(self, user_service, sample_user):
        # Arrange
        user_service.repository.get.return_value = sample_user

        # Act
        result = user_service.get_user("123")

        # Assert
        assert result.id == "123"
        assert result.name == sample_user.name

    def test_get_user_raises_not_found_when_missing(self, user_service):
        # Arrange
        user_service.repository.get.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            user_service.get_user("invalid")
        assert "invalid" in str(exc_info.value)
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input_value,expected", [
    (100, 80),
    (50, 40),
    (0, 0),
])
def test_calculate_discount(input_value, expected):
    result = calculate_discount(input_value, discount_percent=20)
    assert result == expected
```

### Fixtures

```python
@pytest.fixture
def mock_repository():
    return Mock()

@pytest.fixture
def user_service(mock_repository):
    return UserService(repository=mock_repository)

@pytest.fixture
def sample_user():
    return User(id="123", name="John Doe", email="john@example.com")
```

## Ruff Compliance

- Run `ruff check` and `ruff format` before committing
- Do not add `# noqa` suppressions without a documented reason
- Configuration is in `pyproject.toml`

## Best Practices

- Use `pathlib.Path` instead of string paths
- Use f-strings for string formatting
- Use context managers for resource cleanup
- Prefer explicit over implicit
- Keep functions focused (Single Responsibility)
- Avoid global mutable state

## Security

- Never hardcode secrets, API keys, or credentials
- Use environment variables or secret managers
- Validate all external inputs
- Never log sensitive data (passwords, tokens, PII)
- Use `secrets` module for cryptographic randomness, not `random`
