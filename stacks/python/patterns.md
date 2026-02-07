# Python Design Patterns

These are the recommended design patterns for Python projects. When structuring code, apply these patterns to achieve separation of concerns, testability, and maintainability. Each pattern includes a concrete implementation and guidance on when to use it.

---

## Dependency Injection

### When to Use

- When a class or function depends on an external resource (database, API, cache, filesystem).
- When you need to swap implementations for testing.
- When you want to decouple high-level business logic from low-level infrastructure.

### Manual Constructor Injection

The simplest and most Pythonic approach. Pass dependencies as constructor arguments.

```python
class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        email_sender: EmailSender,
        event_bus: EventBus,
    ) -> None:
        self._user_repo = user_repo
        self._email_sender = email_sender
        self._event_bus = event_bus

    async def register_user(self, command: RegisterUser) -> User:
        user = User(name=command.name, email=command.email)
        await self._user_repo.save(user)
        await self._email_sender.send_welcome(user.email)
        await self._event_bus.publish(UserRegistered(user_id=user.id))
        return user
```

### Composition Root

Wire all dependencies in a single place at the application boundary.

```python
# composition.py - the only place where concrete classes are instantiated
def create_user_service(session: AsyncSession) -> UserService:
    return UserService(
        user_repo=SqlAlchemyUserRepository(session),
        email_sender=SmtpEmailSender(settings.smtp_config),
        event_bus=RedisEventBus(settings.redis_url),
    )

# For testing, swap implementations
def create_test_user_service() -> UserService:
    return UserService(
        user_repo=InMemoryUserRepository(),
        email_sender=FakeEmailSender(),
        event_bus=InMemoryEventBus(),
    )
```

### FastAPI Depends

FastAPI's built-in dependency injection system.

```python
from fastapi import Depends

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

async def get_user_repo(
    session: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    return SqlAlchemyUserRepository(session)

async def get_user_service(
    repo: UserRepository = Depends(get_user_repo),
) -> UserService:
    return UserService(user_repo=repo)

@router.post("/users")
async def create_user(
    payload: CreateUserRequest,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.register_user(payload)
```

### When NOT to Use

- For simple scripts or small utilities where passing arguments directly is sufficient.
- When a dependency has exactly one implementation and no tests need to swap it.

---

## Repository Pattern

### When to Use

- When you need to abstract database access behind a clean interface.
- When business logic should not depend on the specific ORM or database.
- When you want to test business logic without a real database.

### Interface Definition

```python
from typing import Protocol, TypeVar

T = TypeVar("T")

class Repository(Protocol[T]):
    async def get_by_id(self, id: int) -> T | None: ...
    async def get_all(self, *, offset: int = 0, limit: int = 100) -> list[T]: ...
    async def save(self, entity: T) -> T: ...
    async def delete(self, id: int) -> None: ...

class UserRepository(Protocol):
    async def get_by_id(self, id: int) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_all(self, *, offset: int = 0, limit: int = 100) -> list[User]: ...
    async def save(self, user: User) -> User: ...
    async def delete(self, id: int) -> None: ...
    async def count(self, *, active_only: bool = False) -> int: ...
```

### SQLAlchemy Implementation

```python
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: int) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == id)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get_all(
        self, *, offset: int = 0, limit: int = 100
    ) -> list[User]:
        result = await self._session.execute(
            select(UserModel)
            .order_by(UserModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [self._to_domain(row) for row in result.scalars().all()]

    async def save(self, user: User) -> User:
        model = self._to_model(user)
        self._session.add(model)
        await self._session.flush()
        return self._to_domain(model)

    async def delete(self, id: int) -> None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self._session.delete(model)

    async def count(self, *, active_only: bool = False) -> int:
        query = select(func.count(UserModel.id))
        if active_only:
            query = query.where(UserModel.is_active.is_(True))
        result = await self._session.execute(query)
        return result.scalar_one()

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            name=model.name,
            email=model.email,
            is_active=model.is_active,
        )

    @staticmethod
    def _to_model(user: User) -> UserModel:
        return UserModel(
            id=user.id,
            name=user.name,
            email=user.email,
            is_active=user.is_active,
        )
```

### In-Memory Implementation (for Tests)

```python
class InMemoryUserRepository:
    def __init__(self) -> None:
        self._store: dict[int, User] = {}
        self._next_id = 1

    async def get_by_id(self, id: int) -> User | None:
        return self._store.get(id)

    async def get_by_email(self, email: str) -> User | None:
        return next(
            (u for u in self._store.values() if u.email == email),
            None,
        )

    async def get_all(
        self, *, offset: int = 0, limit: int = 100
    ) -> list[User]:
        users = sorted(self._store.values(), key=lambda u: u.id)
        return users[offset : offset + limit]

    async def save(self, user: User) -> User:
        if user.id is None:
            user = User(id=self._next_id, **user.__dict__)
            self._next_id += 1
        self._store[user.id] = user
        return user

    async def delete(self, id: int) -> None:
        self._store.pop(id, None)

    async def count(self, *, active_only: bool = False) -> int:
        if active_only:
            return sum(1 for u in self._store.values() if u.is_active)
        return len(self._store)
```

---

## Service Layer Pattern

### When to Use

- When business logic is too complex for a route handler.
- When the same business operation is triggered from multiple entry points (API, CLI, background job).
- When you need to coordinate multiple repositories or external services in a single operation.

### Implementation

```python
class OrderService:
    def __init__(
        self,
        order_repo: OrderRepository,
        product_repo: ProductRepository,
        payment_gateway: PaymentGateway,
        inventory_service: InventoryService,
        notification_service: NotificationService,
    ) -> None:
        self._order_repo = order_repo
        self._product_repo = product_repo
        self._payment_gateway = payment_gateway
        self._inventory = inventory_service
        self._notifications = notification_service

    async def place_order(self, command: PlaceOrderCommand) -> Order:
        """Place a new order, charge payment, and reserve inventory.

        Args:
            command: The order placement command with items and payment info.

        Returns:
            The created order with confirmed status.

        Raises:
            InsufficientStockError: If any item is out of stock.
            PaymentFailedError: If the payment charge fails.
        """
        # Validate stock availability
        for item in command.items:
            product = await self._product_repo.get_by_id(item.product_id)
            if product is None:
                raise NotFoundError("Product", item.product_id)
            if not await self._inventory.check_availability(
                product.id, item.quantity
            ):
                raise InsufficientStockError(product.id, item.quantity)

        # Calculate total
        total = await self._calculate_total(command.items)

        # Charge payment
        payment_result = await self._payment_gateway.charge(
            amount=total,
            payment_method=command.payment_method,
        )
        if not payment_result.success:
            raise PaymentFailedError(payment_result.error_message)

        # Create order
        order = Order(
            customer_id=command.customer_id,
            items=command.items,
            total=total,
            payment_id=payment_result.payment_id,
            status=OrderStatus.CONFIRMED,
        )
        order = await self._order_repo.save(order)

        # Reserve inventory
        for item in command.items:
            await self._inventory.reserve(item.product_id, item.quantity)

        # Notify customer
        await self._notifications.send_order_confirmation(order)

        return order

    async def cancel_order(self, order_id: int) -> Order:
        order = await self._order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order", order_id)
        if order.status not in (OrderStatus.CONFIRMED, OrderStatus.PENDING):
            raise InvalidOperationError(
                f"Cannot cancel order in status {order.status}"
            )

        # Refund payment
        await self._payment_gateway.refund(order.payment_id)

        # Release inventory
        for item in order.items:
            await self._inventory.release(item.product_id, item.quantity)

        order.status = OrderStatus.CANCELLED
        return await self._order_repo.save(order)
```

### Rules for Service Layer

- Services orchestrate; they do not contain persistence logic (that belongs in repositories).
- Services do not know about HTTP, request objects, or response formats.
- Services raise domain exceptions, not HTTP exceptions.
- Each public method on a service represents one business use case.
- Keep services stateless. All state lives in the repository or database.

---

## Decorator Patterns

### Retry Decorator

```python
import asyncio
import functools
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry an async function with exponential backoff."""
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exc: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        wait = delay * (backoff_factor ** attempt)
                        logger.warning(
                            "Attempt %d/%d for %s failed: %s. Retrying in %.1fs",
                            attempt + 1, max_attempts, func.__name__, e, wait,
                        )
                        await asyncio.sleep(wait)
            raise last_exc  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator

# Usage
@async_retry(max_attempts=3, exceptions=(ConnectionError, TimeoutError))
async def fetch_external_data(url: str) -> dict[str, Any]:
    ...
```

### Cache Decorator

```python
from functools import lru_cache
from datetime import datetime, timedelta

def timed_cache(seconds: int = 300) -> Callable:
    """Cache function results with a TTL."""
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        cache: dict[tuple, tuple[R, datetime]] = {}

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = (args, tuple(sorted(kwargs.items())))
            if key in cache:
                result, timestamp = cache[key]
                if datetime.now() - timestamp < timedelta(seconds=seconds):
                    return result
            result = func(*args, **kwargs)
            cache[key] = (result, datetime.now())
            return result
        return wrapper
    return decorator

# For simple cases, use stdlib lru_cache
@lru_cache(maxsize=128)
def get_country_code(country_name: str) -> str:
    ...
```

### Authorization Decorator (FastAPI)

```python
from functools import wraps

def require_role(*roles: str) -> Callable:
    """Require the current user to have one of the specified roles."""
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Extract current_user from kwargs (set by Depends)
            current_user = kwargs.get("current_user")
            if current_user is None:
                raise HTTPException(status_code=401, detail="Not authenticated")
            if current_user.role not in roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, **kwargs)
        return wrapper  # type: ignore[return-value]
    return decorator

# Usage
@router.delete("/users/{user_id}")
@require_role("admin")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> None:
    await service.delete_user(user_id)
```

### Timing Decorator

```python
def async_timing(func: Callable[P, R]) -> Callable[P, R]:
    """Log execution time of an async function."""
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        try:
            return await func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            logger.info(
                "%s completed in %.3fs",
                func.__name__,
                elapsed,
            )
    return wrapper  # type: ignore[return-value]
```

---

## Factory Pattern

### When to Use

- When object creation logic is complex or conditional.
- When the caller should not need to know which concrete class to instantiate.
- When creation logic needs to be centralized for consistency.

### Simple Factory Function

```python
def create_notification_sender(
    channel: NotificationChannel,
    config: Settings,
) -> NotificationSender:
    """Create the appropriate notification sender for the channel."""
    match channel:
        case NotificationChannel.EMAIL:
            return EmailSender(
                smtp_host=config.smtp_host,
                smtp_port=config.smtp_port,
                from_address=config.from_email,
            )
        case NotificationChannel.SMS:
            return SmsSender(
                api_key=config.twilio_api_key,
                from_number=config.twilio_from_number,
            )
        case NotificationChannel.SLACK:
            return SlackSender(
                webhook_url=config.slack_webhook_url,
            )
        case _:
            raise ValueError(f"Unsupported notification channel: {channel}")
```

### Abstract Factory

```python
class StorageFactory(Protocol):
    def create_file_storage(self) -> FileStorage: ...
    def create_metadata_store(self) -> MetadataStore: ...

class LocalStorageFactory:
    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path

    def create_file_storage(self) -> FileStorage:
        return LocalFileStorage(self._base_path)

    def create_metadata_store(self) -> MetadataStore:
        return SqliteMetadataStore(self._base_path / "metadata.db")

class CloudStorageFactory:
    def __init__(self, config: CloudConfig) -> None:
        self._config = config

    def create_file_storage(self) -> FileStorage:
        return S3FileStorage(self._config.bucket_name)

    def create_metadata_store(self) -> MetadataStore:
        return DynamoMetadataStore(self._config.table_name)
```

---

## Strategy Pattern

### When to Use

- When you have multiple algorithms for the same task and need to switch between them.
- When you want to avoid long conditional chains for selecting behavior.
- When algorithms should be interchangeable at runtime.

### Implementation with Protocol

```python
from typing import Protocol

class PricingStrategy(Protocol):
    def calculate(self, base_price: Decimal, quantity: int) -> Decimal: ...

class StandardPricing:
    def calculate(self, base_price: Decimal, quantity: int) -> Decimal:
        return base_price * quantity

class BulkPricing:
    def __init__(self, threshold: int, discount: Decimal) -> None:
        self._threshold = threshold
        self._discount = discount

    def calculate(self, base_price: Decimal, quantity: int) -> Decimal:
        total = base_price * quantity
        if quantity >= self._threshold:
            total *= (1 - self._discount)
        return total

class SeasonalPricing:
    def __init__(self, multiplier: Decimal) -> None:
        self._multiplier = multiplier

    def calculate(self, base_price: Decimal, quantity: int) -> Decimal:
        return base_price * self._multiplier * quantity

# Usage
class OrderCalculator:
    def __init__(self, pricing: PricingStrategy) -> None:
        self._pricing = pricing

    def calculate_line_total(
        self, product: Product, quantity: int
    ) -> Decimal:
        return self._pricing.calculate(product.price, quantity)

# Swap strategies based on context
if is_holiday_season():
    pricing = SeasonalPricing(multiplier=Decimal("1.15"))
elif order.total_quantity > 100:
    pricing = BulkPricing(threshold=100, discount=Decimal("0.1"))
else:
    pricing = StandardPricing()

calculator = OrderCalculator(pricing)
```

### Strategy with Callable

For simple strategies, a plain function is sufficient.

```python
type SortKey = Callable[[Product], Any]

def sort_by_price(product: Product) -> Decimal:
    return product.price

def sort_by_rating(product: Product) -> float:
    return -product.average_rating  # negative for descending

def sort_by_popularity(product: Product) -> int:
    return -product.purchase_count

SORT_STRATEGIES: dict[str, SortKey] = {
    "price": sort_by_price,
    "rating": sort_by_rating,
    "popularity": sort_by_popularity,
}

def get_sorted_products(
    products: list[Product],
    sort_by: str = "price",
) -> list[Product]:
    key_func = SORT_STRATEGIES.get(sort_by)
    if key_func is None:
        raise ValueError(f"Unknown sort key: {sort_by}")
    return sorted(products, key=key_func)
```

---

## Observer Pattern (Event-Driven)

### When to Use

- When an action in one part of the system should trigger reactions in other parts without tight coupling.
- For audit logging, notifications, cache invalidation, and analytics.
- When you need to add new reactions without modifying the emitting code.

### Implementation

```python
from collections.abc import Callable, Awaitable
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class UserCreatedEvent:
    user_id: int
    email: str

@dataclass(frozen=True)
class OrderPlacedEvent:
    order_id: int
    customer_id: int
    total: Decimal

type Event = UserCreatedEvent | OrderPlacedEvent
type EventHandler = Callable[[Any], Awaitable[None]]

class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = {}

    def subscribe(
        self,
        event_type: type,
        handler: EventHandler,
    ) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: Event) -> None:
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Handler %s failed for event %s",
                    handler.__name__,
                    type(event).__name__,
                )

# Registration
bus = EventBus()

async def send_welcome_email(event: UserCreatedEvent) -> None:
    await email_service.send_welcome(event.email)

async def log_user_creation(event: UserCreatedEvent) -> None:
    audit_logger.info("User created: %d", event.user_id)

async def sync_to_crm(event: UserCreatedEvent) -> None:
    await crm_client.create_contact(event.email)

bus.subscribe(UserCreatedEvent, send_welcome_email)
bus.subscribe(UserCreatedEvent, log_user_creation)
bus.subscribe(UserCreatedEvent, sync_to_crm)

# Publishing (in the service layer)
await bus.publish(UserCreatedEvent(user_id=42, email="alice@example.com"))
```

### Decorator-Based Registration

```python
class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = {}

    def on(self, event_type: type) -> Callable[[EventHandler], EventHandler]:
        """Decorator to register an event handler."""
        def decorator(handler: EventHandler) -> EventHandler:
            self._handlers.setdefault(event_type, []).append(handler)
            return handler
        return decorator

bus = EventBus()

@bus.on(UserCreatedEvent)
async def send_welcome_email(event: UserCreatedEvent) -> None:
    await email_service.send_welcome(event.email)

@bus.on(UserCreatedEvent)
async def log_user_creation(event: UserCreatedEvent) -> None:
    audit_logger.info("User created: %d", event.user_id)
```

---

## Protocol-Based Interfaces

### When to Use

- Always prefer Protocols over ABCs for defining interfaces, unless you need shared concrete method implementations.
- Protocols enable structural typing: any class that has the right methods matches the Protocol, without needing to inherit from it.

### Defining Clean Interfaces

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Serializable(Protocol):
    def to_dict(self) -> dict[str, Any]: ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self: ...

@runtime_checkable
class Cacheable(Protocol):
    @property
    def cache_key(self) -> str: ...

    @property
    def cache_ttl(self) -> int: ...

class HasTimestamps(Protocol):
    @property
    def created_at(self) -> datetime: ...

    @property
    def updated_at(self) -> datetime: ...
```

### Composing Protocols

```python
class Persistable(Serializable, HasTimestamps, Protocol):
    """A domain entity that can be serialized and has timestamps."""
    @property
    def id(self) -> int | None: ...

# Any class matching all three protocols satisfies Persistable
class User:
    def __init__(self, id: int | None, name: str) -> None:
        self._id = id
        self.name = name
        self._created_at = datetime.now()
        self._updated_at = datetime.now()

    @property
    def id(self) -> int | None:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def to_dict(self) -> dict[str, Any]:
        return {"id": self._id, "name": self.name}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(id=data.get("id"), name=data["name"])
```

---

## Command Pattern (CQRS-Like)

### When to Use

- When you want to separate read operations from write operations.
- When commands (writes) need validation, authorization, and auditing.
- When queries (reads) need different optimization strategies than writes.

### Command and Handler

```python
from dataclasses import dataclass
from typing import Protocol

# Commands are immutable data objects
@dataclass(frozen=True)
class CreateOrderCommand:
    customer_id: int
    items: list[OrderItem]
    payment_method: str

@dataclass(frozen=True)
class CancelOrderCommand:
    order_id: int
    reason: str

# Handler protocol
class CommandHandler(Protocol[T]):
    async def handle(self, command: T) -> Any: ...

# Concrete handlers
class CreateOrderHandler:
    def __init__(
        self,
        order_repo: OrderRepository,
        payment_gateway: PaymentGateway,
    ) -> None:
        self._order_repo = order_repo
        self._payment = payment_gateway

    async def handle(self, command: CreateOrderCommand) -> Order:
        # Validate
        if not command.items:
            raise ValidationError("items", "Order must have at least one item")

        # Execute
        order = Order.create(
            customer_id=command.customer_id,
            items=command.items,
        )
        await self._payment.charge(order.total, command.payment_method)
        return await self._order_repo.save(order)

# Command bus / dispatcher
class CommandBus:
    def __init__(self) -> None:
        self._handlers: dict[type, Any] = {}

    def register(self, command_type: type, handler: Any) -> None:
        self._handlers[command_type] = handler

    async def dispatch(self, command: Any) -> Any:
        handler = self._handlers.get(type(command))
        if handler is None:
            raise ValueError(f"No handler for {type(command).__name__}")
        return await handler.handle(command)

# Usage
bus = CommandBus()
bus.register(CreateOrderCommand, create_order_handler)
bus.register(CancelOrderCommand, cancel_order_handler)

result = await bus.dispatch(
    CreateOrderCommand(
        customer_id=1,
        items=[OrderItem(product_id=10, quantity=2)],
        payment_method="card_xxx",
    )
)
```

### Query Side

```python
@dataclass(frozen=True)
class GetOrderQuery:
    order_id: int

@dataclass(frozen=True)
class ListOrdersQuery:
    customer_id: int
    status: OrderStatus | None = None
    limit: int = 20
    offset: int = 0

class GetOrderHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetOrderQuery) -> OrderReadModel | None:
        """Queries can use optimized read paths, bypassing the domain model."""
        result = await self._session.execute(
            select(OrderModel)
            .options(selectinload(OrderModel.items))
            .where(OrderModel.id == query.order_id)
        )
        row = result.scalar_one_or_none()
        return OrderReadModel.from_orm(row) if row else None
```

---

## Context Managers for Resource Management

### When to Use

- For any resource that must be cleaned up: database connections, file handles, locks, temporary files, HTTP sessions.
- When cleanup must happen even if an exception occurs.

### Synchronous Context Manager

```python
from contextlib import contextmanager
from collections.abc import Generator

@contextmanager
def managed_transaction(session: Session) -> Generator[Session, None, None]:
    """Wrap a database session in a transaction with automatic rollback."""
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Usage
with managed_transaction(session) as txn:
    txn.add(new_user)
    txn.add(new_profile)
# Committed on success, rolled back on exception, closed always
```

### Async Context Manager

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

@asynccontextmanager
async def http_client() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Create and clean up an aiohttp session."""
    session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        headers={"User-Agent": "myapp/1.0"},
    )
    try:
        yield session
    finally:
        await session.close()

# Usage
async with http_client() as client:
    response = await client.get("https://api.example.com/data")
    data = await response.json()
```

### Class-Based Context Manager

```python
class DistributedLock:
    """A distributed lock using Redis."""

    def __init__(self, redis: Redis, key: str, ttl: int = 30) -> None:
        self._redis = redis
        self._key = f"lock:{key}"
        self._ttl = ttl
        self._token: str | None = None

    async def __aenter__(self) -> Self:
        self._token = str(uuid.uuid4())
        acquired = await self._redis.set(
            self._key, self._token, nx=True, ex=self._ttl
        )
        if not acquired:
            raise LockAcquisitionError(f"Could not acquire lock: {self._key}")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        # Only release if we still own the lock
        current = await self._redis.get(self._key)
        if current == self._token:
            await self._redis.delete(self._key)

# Usage
async with DistributedLock(redis, "order-processing-42"):
    await process_order(42)
```

---

## Pattern Selection Guide

| Situation | Pattern |
|---|---|
| Class needs external resources | Dependency Injection |
| Database access needs abstraction | Repository |
| Complex business operation spanning multiple services | Service Layer |
| Cross-cutting concern (logging, retry, auth) | Decorator |
| Object creation is conditional or complex | Factory |
| Multiple algorithms for the same operation | Strategy |
| Actions should trigger decoupled reactions | Observer / Event Bus |
| Need interface without requiring inheritance | Protocol |
| Separate reads from writes with different optimization | Command / CQRS |
| Resource cleanup must be guaranteed | Context Manager |
