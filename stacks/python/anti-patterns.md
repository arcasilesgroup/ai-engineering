# Python Anti-Patterns

These are patterns and practices that must be avoided in all Python code. Each section describes the anti-pattern, explains why it is harmful, and provides the correct alternative. When reviewing or generating code, flag any occurrence of these anti-patterns and replace them with the recommended approach.

---

## Mutable Default Arguments

A mutable default argument (list, dict, set) is shared across all calls to the function. Mutations persist between invocations, causing unpredictable behavior.

```python
# DON'T - mutable default argument
def add_item(item: str, items: list[str] = []) -> list[str]:
    items.append(item)
    return items

# First call returns ["a"], second call returns ["a", "b"] - shared list
add_item("a")  # ["a"]
add_item("b")  # ["a", "b"]  <-- unexpected

# DO - use None and create inside the function
def add_item(item: str, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    items.append(item)
    return items

# DO - for dataclasses, use field(default_factory=...)
from dataclasses import dataclass, field

@dataclass
class Config:
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
```

---

## Bare Except Clauses

A bare `except:` or overly broad `except Exception:` catches everything, including `KeyboardInterrupt`, `SystemExit`, and programming errors like `TypeError` or `AttributeError`. This hides bugs and makes debugging nearly impossible.

```python
# DON'T - bare except
try:
    process_data(data)
except:
    pass  # swallows ALL exceptions including KeyboardInterrupt

# DON'T - overly broad except with no action
try:
    process_data(data)
except Exception:
    pass  # hides every possible error

# DO - catch specific exceptions
try:
    result = parse_json(raw_input)
except json.JSONDecodeError as e:
    logger.warning("Invalid JSON input: %s", e)
    return default_value

# DO - if you must catch broadly, log and re-raise
try:
    process_data(data)
except Exception:
    logger.exception("Unexpected error processing data")
    raise
```

---

## Global State Abuse

Global mutable state creates hidden dependencies between modules, makes testing difficult, introduces race conditions in concurrent code, and makes the order of operations unpredictable.

```python
# DON'T - global mutable state
_cache = {}
_db_connection = None

def get_user(user_id: int) -> User:
    if user_id in _cache:
        return _cache[user_id]
    user = _db_connection.query(User, user_id)  # relies on global
    _cache[user_id] = user
    return user

# DO - inject dependencies, encapsulate state in a class
class UserCache:
    def __init__(self, db: Database) -> None:
        self._cache: dict[int, User] = {}
        self._db = db

    def get_user(self, user_id: int) -> User:
        if user_id not in self._cache:
            self._cache[user_id] = self._db.query(User, user_id)
        return self._cache[user_id]
```

Acceptable globals:
- Module-level constants (`MAX_RETRIES = 3`).
- Logger instances (`logger = logging.getLogger(__name__)`).
- Immutable configuration loaded once at startup.

---

## Circular Imports

Circular imports occur when module A imports from module B and module B imports from module A. This leads to `ImportError` or partially initialized modules.

```python
# DON'T - circular dependency
# user_service.py
from order_service import OrderService  # order_service imports UserService

class UserService:
    def __init__(self, order_service: OrderService) -> None:
        ...

# order_service.py
from user_service import UserService  # circular!

class OrderService:
    def __init__(self, user_service: UserService) -> None:
        ...

# DO - break the cycle with interfaces/protocols
# interfaces.py
from typing import Protocol

class UserServiceProtocol(Protocol):
    async def get_user(self, user_id: int) -> User: ...

class OrderServiceProtocol(Protocol):
    async def get_orders(self, user_id: int) -> list[Order]: ...

# user_service.py
from interfaces import OrderServiceProtocol

class UserService:
    def __init__(self, order_service: OrderServiceProtocol) -> None:
        ...

# order_service.py
from interfaces import UserServiceProtocol

class OrderService:
    def __init__(self, user_service: UserServiceProtocol) -> None:
        ...

# DO - alternatively, use TYPE_CHECKING for type-only imports
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from order_service import OrderService
```

---

## Star Imports

`from module import *` pollutes the namespace, makes it impossible to trace where a name came from, and causes silent name collisions.

```python
# DON'T
from os.path import *
from utils import *
from models import *

# DO - import specific names
from os.path import join, dirname, exists
from utils import calculate_hash, format_timestamp
from models import User, Order

# DO - import the module and use qualified names
import os.path

full_path = os.path.join(base, filename)
```

The only acceptable use of `*` imports is in `__init__.py` files to re-export a package's public API, and only when `__all__` is defined in the source module.

---

## Not Using Virtual Environments

Installing packages globally leads to version conflicts, makes builds unreproducible, and risks breaking system Python tools.

```bash
# DON'T
pip install fastapi  # installs globally

# DO
python -m venv .venv
source .venv/bin/activate
pip install fastapi

# DO - using uv for speed
uv venv
uv pip install fastapi
```

Every project must have its own virtual environment. The `.venv` directory must be in `.gitignore`.

---

## Ignoring Type Hints

Untyped code is harder to understand, harder to refactor, and misses an entire class of bugs that type checkers catch at zero runtime cost.

```python
# DON'T
def process(data, options):
    result = transform(data, options.get("format"))
    return result

# DO
def process(
    data: list[RawRecord],
    options: ProcessingOptions,
) -> list[TransformedRecord]:
    result = transform(data, options.format)
    return result
```

Run `mypy --strict` in CI. Do not merge code with type errors.

---

## Legacy String Formatting

The `%` operator and `.format()` method are harder to read and more error-prone than f-strings. F-strings are faster and more readable.

```python
# DON'T - % formatting
message = "Hello, %s. You have %d items." % (name, count)

# DON'T - .format()
message = "Hello, {}. You have {} items.".format(name, count)

# DO - f-string
message = f"Hello, {name}. You have {count} items."

# EXCEPTION: logging uses lazy formatting (not f-strings)
logger.info("User %s has %d items", name, count)  # correct
logger.info(f"User {name} has {count} items")  # wasteful - string built even if level disabled
```

---

## Not Closing Resources

Failing to close files, database connections, HTTP sessions, and other resources causes leaks that degrade performance and eventually crash the application.

```python
# DON'T - resource leak
f = open("data.txt")
content = f.read()
# f is never closed; if an exception occurs between open and close, leak is guaranteed

# DON'T - close without exception safety
f = open("data.txt")
content = f.read()
f.close()  # never reached if read() raises

# DO - context manager
with open("data.txt") as f:
    content = f.read()
# file is closed even if an exception occurs

# DO - async context manager
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        data = await response.json()
```

Every resource that implements `__enter__`/`__exit__` or `__aenter__`/`__aexit__` must be used with a `with` or `async with` statement.

---

## Monkey Patching in Production

Monkey patching (modifying classes or modules at runtime) makes code unpredictable, breaks IDE navigation, and is nearly impossible to debug.

```python
# DON'T - monkey patching
import some_library

def my_custom_method(self):
    ...

some_library.SomeClass.process = my_custom_method  # fragile, invisible

# DO - use composition or subclassing
class MyProcessor:
    def __init__(self, inner: some_library.SomeClass) -> None:
        self._inner = inner

    def process(self) -> Result:
        # Custom behavior
        preprocessed = self._preprocess()
        return self._inner.original_process(preprocessed)

# DO - use dependency injection to swap behavior
```

Monkey patching is acceptable only in test code using `unittest.mock.patch` or `monkeypatch`.

---

## Overusing Inheritance

Deep inheritance hierarchies are rigid, hard to understand, and create tight coupling. Changes to a base class ripple unpredictably through all descendants.

```python
# DON'T - deep inheritance
class Animal:
    ...

class Mammal(Animal):
    ...

class DomesticAnimal(Mammal):
    ...

class Pet(DomesticAnimal):
    ...

class Dog(Pet):
    # 5 levels deep - changes to any ancestor break this
    ...

# DO - composition over inheritance
@dataclass
class Animal:
    name: str
    movement: MovementStrategy
    diet: DietStrategy
    habitat: Habitat

# DO - use Protocols for shared behavior
class Feedable(Protocol):
    def feed(self, food: Food) -> None: ...

class Walkable(Protocol):
    def walk(self, distance: float) -> None: ...
```

Use inheritance only when there is a genuine "is-a" relationship AND shared implementation. Prefer composition and Protocols in all other cases.

---

## Magic Numbers and Strings

Unnamed numeric or string literals scattered through the code are impossible to understand, search for, or update consistently.

```python
# DON'T
if user.age >= 18:
    ...

if response.status_code == 200:
    ...

await asyncio.sleep(300)

if role == "admin":
    ...

# DO - named constants
MINIMUM_AGE = 18
CACHE_TTL_SECONDS = 300

if user.age >= MINIMUM_AGE:
    ...

if response.status_code == HTTPStatus.OK:
    ...

await asyncio.sleep(CACHE_TTL_SECONDS)

# DO - use enums for categorical values
class UserRole(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

if role == UserRole.ADMIN:
    ...
```

---

## God Modules and God Classes

A module or class that does everything is impossible to test, understand, or maintain. It violates the Single Responsibility Principle.

```python
# DON'T - god class
class UserManager:
    def create_user(self, ...) -> User: ...
    def authenticate(self, ...) -> Token: ...
    def send_email(self, ...) -> None: ...
    def generate_report(self, ...) -> Report: ...
    def process_payment(self, ...) -> Payment: ...
    def update_inventory(self, ...) -> None: ...
    def export_to_csv(self, ...) -> bytes: ...

# DO - split by responsibility
class UserService:
    def create_user(self, ...) -> User: ...

class AuthService:
    def authenticate(self, ...) -> Token: ...

class EmailService:
    def send_email(self, ...) -> None: ...

class ReportService:
    def generate_report(self, ...) -> Report: ...
```

If a class has more than 5-7 public methods or a module has more than 300 lines, it is likely doing too much.

---

## Using `type()` Instead of `isinstance()`

Direct type comparison with `type()` fails for subclasses and violates the Liskov Substitution Principle.

```python
# DON'T
if type(error) == ValueError:
    ...

# DO
if isinstance(error, ValueError):
    ...

# DO - check multiple types
if isinstance(value, (int, float)):
    ...
```

---

## Catching and Returning None Instead of Raising

Returning `None` to indicate failure forces every caller to check for `None`, which is easily forgotten. It also hides the reason for failure.

```python
# DON'T
def get_user(user_id: int) -> User | None:
    try:
        return db.query(User, user_id)
    except DatabaseError:
        return None  # caller has no idea what went wrong

# DO - let exceptions propagate or raise domain exceptions
def get_user(user_id: int) -> User:
    try:
        user = db.query(User, user_id)
    except DatabaseError as e:
        raise RepositoryError(f"Failed to fetch user {user_id}") from e
    if user is None:
        raise NotFoundError("User", user_id)
    return user
```

Returning `None` is appropriate only when "not found" is a normal, expected outcome (e.g., `dict.get()`), not when it masks an error.

---

## Premature Optimization

Optimizing code before measuring creates complexity without proven benefit.

```python
# DON'T - premature micro-optimization that hurts readability
user_ids = list({u.id for u in users})  # set comprehension for "speed"
# when the list is 10 items and this runs once per request

# DO - write clear code first
user_ids = [u.id for u in users]

# THEN - if profiling shows this is a bottleneck, optimize with a comment
# Profiled: deduplication needed, set comprehension is 3x faster for n>10000
user_ids = list({u.id for u in users})
```

---

## Using `os.system()` for Shell Commands

`os.system()` runs commands through the shell, which is vulnerable to injection attacks and provides no way to capture output or handle errors properly.

```python
# DON'T
import os
os.system(f"rm -rf {user_input}")  # shell injection vulnerability

# DON'T
os.system("ls -la /tmp")

# DO - use subprocess with list arguments
import subprocess

result = subprocess.run(
    ["ls", "-la", "/tmp"],
    capture_output=True,
    text=True,
    check=True,
)
print(result.stdout)
```

---

## Unnecessary List Comprehensions

Creating a list only to pass it to a function that accepts any iterable wastes memory.

```python
# DON'T - unnecessary list
total = sum([x.price for x in items])
any_active = any([u.is_active for u in users])
filtered = list([x for x in items if x.valid])

# DO - generator expression
total = sum(x.price for x in items)
any_active = any(u.is_active for u in users)
filtered = [x for x in items if x.valid]  # list comp is fine when you need a list
```

---

## Using `assert` for Runtime Validation

`assert` statements are stripped when Python runs with `-O` (optimize). Never use them for input validation or security checks.

```python
# DON'T - assert for validation
def withdraw(amount: Decimal) -> None:
    assert amount > 0, "Amount must be positive"  # removed with -O flag
    ...

# DO - explicit validation
def withdraw(amount: Decimal) -> None:
    if amount <= 0:
        raise ValueError(f"Amount must be positive, got {amount}")
    ...
```

`assert` is acceptable in test code and for documenting impossible states during development.

---

## Summary

| Anti-Pattern | Fix |
|---|---|
| Mutable default arguments | Use `None` and create inside function |
| Bare except | Catch specific exception types |
| Global mutable state | Inject dependencies, encapsulate in classes |
| Circular imports | Use Protocols, `TYPE_CHECKING`, or restructure |
| Star imports | Import specific names |
| No virtual environment | Always use `venv` or `uv` |
| Missing type hints | Annotate all function signatures |
| `%` / `.format()` strings | Use f-strings (except in logging) |
| Unclosed resources | Use `with` / `async with` |
| Monkey patching | Composition, DI, or subclassing |
| Deep inheritance | Composition and Protocols |
| Magic numbers | Named constants and enums |
| God classes/modules | Split by single responsibility |
| `type()` comparison | `isinstance()` |
| Swallowing errors as `None` | Raise domain exceptions |
| Premature optimization | Profile first, then optimize |
| `os.system()` | `subprocess.run()` with list args |
| Unnecessary list comprehensions | Generator expressions |
| `assert` for validation | Explicit `if` / `raise` |
