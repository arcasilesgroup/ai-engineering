# Python Coding Standards

> Python conventions following PEP 8 and modern best practices.

---

## Style Guide

Follow [PEP 8](https://peps.python.org/pep-0008/) with these additional guidelines.

---

## Type Hints

### Basic Types

```python
from typing import Optional, List, Dict, Tuple, Union

def get_user(user_id: str) -> Optional[User]:
    """Fetch user by ID."""
    return users.get(user_id)

def process_items(items: List[str]) -> Dict[str, int]:
    """Count occurrences of each item."""
    return {item: items.count(item) for item in set(items)}

# Python 3.10+ union syntax
def parse_input(value: str | int) -> str:
    return str(value)
```

### Complex Types

```python
from typing import Callable, TypeVar, Generic

T = TypeVar('T')

# Generic function
def first_or_default(items: List[T], default: T) -> T:
    return items[0] if items else default

# Callable type
Handler = Callable[[Request], Response]

def register_handler(path: str, handler: Handler) -> None:
    pass
```

---

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `user_service.py` |
| Classes | PascalCase | `UserService`, `ApiClient` |
| Functions | snake_case | `get_user`, `process_order` |
| Variables | snake_case | `user_name`, `is_active` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES`, `API_BASE_URL` |
| Private | _prefix | `_internal_method`, `_cache` |

---

## Function Patterns

### Docstrings (Google Style)

```python
def calculate_discount(
    price: float,
    discount_percent: float,
    max_discount: Optional[float] = None
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
    if not 0 <= discount_percent <= 100:
        raise ValueError("discount_percent must be between 0 and 100")

    discount = price * (discount_percent / 100)
    if max_discount is not None:
        discount = min(discount, max_discount)

    return price - discount
```

### Default Arguments

```python
# ✅ GOOD: Immutable defaults
def process(items: Optional[List[str]] = None) -> List[str]:
    if items is None:
        items = []
    return [item.upper() for item in items]

# ❌ BAD: Mutable default (shared between calls!)
def process(items: List[str] = []) -> List[str]:
    items.append("new")  # Mutates default!
    return items
```

---

## Classes

### Dataclasses

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

@dataclass
class User:
    id: str
    name: str
    email: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    roles: List[str] = field(default_factory=list)

@dataclass(frozen=True)  # Immutable
class Point:
    x: float
    y: float
```

### Pydantic Models (for validation)

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

---

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

class ValidationError(DomainError):
    """Validation failed."""
    def __init__(self, errors: Dict[str, str]):
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")
```

### Result Pattern (Optional)

```python
from dataclasses import dataclass
from typing import TypeVar, Generic, Union

T = TypeVar('T')

@dataclass
class Success(Generic[T]):
    value: T

@dataclass  
class Failure:
    error: str

Result = Union[Success[T], Failure]

def get_user(user_id: str) -> Result[User]:
    user = users.get(user_id)
    if user is None:
        return Failure(f"User {user_id} not found")
    return Success(user)

# Usage
result = get_user("123")
match result:
    case Success(user):
        print(f"Found: {user.name}")
    case Failure(error):
        print(f"Error: {error}")
```

---

## Async/Await

```python
import asyncio
from typing import List

async def fetch_user(user_id: str) -> User:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/users/{user_id}")
        return User(**response.json())

async def fetch_all_users(user_ids: List[str]) -> List[User]:
    tasks = [fetch_user(uid) for uid in user_ids]
    return await asyncio.gather(*tasks)
```

---

## File Organization

```
src/
├── __init__.py
├── main.py
├── config.py
├── models/
│   ├── __init__.py
│   └── user.py
├── services/
│   ├── __init__.py
│   └── user_service.py
├── api/
│   ├── __init__.py
│   └── routes.py
└── utils/
    ├── __init__.py
    └── helpers.py
```

---

## Best Practices

### Do

- ✅ Use type hints for all public functions
- ✅ Use dataclasses or Pydantic for data structures
- ✅ Use context managers (`with`) for resources
- ✅ Use `pathlib.Path` instead of string paths
- ✅ Use f-strings for formatting

### Don't

- ❌ Use mutable default arguments
- ❌ Use `from module import *`
- ❌ Catch bare `except:` without re-raising
- ❌ Use global variables
- ❌ Mix tabs and spaces
