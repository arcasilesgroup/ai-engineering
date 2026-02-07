# Python Testing Standards

All Python projects must use `pytest` as the testing framework. These standards define how tests are organized, written, and executed. Every behavioral change to the codebase must have corresponding test coverage. When generating code, always generate the tests alongside it.

---

## Test File Organization

### Directory Structure

```
project-root/
  src/
    mypackage/
      services/
        user_service.py
        order_service.py
      repositories/
        user_repository.py
      api/
        routes/
          users.py
  tests/
    __init__.py
    conftest.py                    # shared fixtures
    unit/
      __init__.py
      conftest.py                  # unit-specific fixtures
      services/
        __init__.py
        test_user_service.py
        test_order_service.py
      repositories/
        __init__.py
        test_user_repository.py
    integration/
      __init__.py
      conftest.py                  # integration-specific fixtures (DB, etc.)
      test_user_api.py
      test_order_workflow.py
    e2e/
      __init__.py
      conftest.py
      test_checkout_flow.py
```

### Naming Rules

- Test files must start with `test_` (e.g., `test_user_service.py`).
- Test functions must start with `test_` (e.g., `test_create_user_returns_user_with_id`).
- Test classes must start with `Test` (e.g., `TestUserService`). Do not inherit from `unittest.TestCase`.
- Use descriptive test names that explain the scenario and expected outcome.

```python
# DO - descriptive names
def test_create_user_returns_user_with_generated_id() -> None: ...
def test_create_user_raises_validation_error_when_email_is_empty() -> None: ...
def test_delete_user_returns_none_when_user_does_not_exist() -> None: ...

# DON'T - vague names
def test_create() -> None: ...
def test_user() -> None: ...
def test_error() -> None: ...
```

### conftest.py

- Place shared fixtures in `conftest.py` at the appropriate directory level.
- Root `conftest.py` contains fixtures used across all test types.
- Subdirectory `conftest.py` files contain fixtures specific to that test category.
- Never import from `conftest.py` directly. Pytest discovers fixtures automatically.

```python
# tests/conftest.py - shared across all tests
import pytest

@pytest.fixture
def sample_user() -> User:
    return User(
        id=1,
        name="Alice Smith",
        email="alice@example.com",
        is_active=True,
    )

@pytest.fixture
def sample_users() -> list[User]:
    return [
        User(id=1, name="Alice", email="alice@example.com", is_active=True),
        User(id=2, name="Bob", email="bob@example.com", is_active=True),
        User(id=3, name="Charlie", email="charlie@example.com", is_active=False),
    ]
```

---

## Pytest Conventions

### Use Plain assert

- Use plain `assert` statements. Pytest provides detailed introspection on failures.
- Do not use `self.assertEqual`, `self.assertTrue`, or any `unittest` assertion methods.

```python
# DO
def test_user_full_name(sample_user: User) -> None:
    assert sample_user.full_name == "Alice Smith"

def test_active_users_excludes_inactive(sample_users: list[User]) -> None:
    active = [u for u in sample_users if u.is_active]
    assert len(active) == 2
    assert all(u.is_active for u in active)

# DON'T
def test_user_full_name(self):
    self.assertEqual(self.user.full_name, "Alice Smith")
```

### Testing Exceptions

- Use `pytest.raises` as a context manager to test that exceptions are raised.
- Always check the exception message or attributes when the message matters.

```python
def test_withdraw_raises_on_negative_amount() -> None:
    account = Account(balance=Decimal("100.00"))

    with pytest.raises(ValueError, match="Amount must be positive"):
        account.withdraw(Decimal("-50.00"))

def test_get_user_raises_not_found() -> None:
    service = UserService(repo=InMemoryUserRepository())

    with pytest.raises(NotFoundError) as exc_info:
        await service.get_user(999)

    assert exc_info.value.resource == "User"
    assert exc_info.value.identifier == 999
```

### Approximate Comparisons

```python
def test_calculate_tax() -> None:
    result = calculate_tax(Decimal("99.99"))
    assert result == pytest.approx(Decimal("8.00"), abs=Decimal("0.01"))
```

### Test Structure: Arrange-Act-Assert

Every test must follow the Arrange-Act-Assert pattern, separated by blank lines.

```python
def test_place_order_creates_order_with_correct_total() -> None:
    # Arrange
    service = OrderService(
        order_repo=InMemoryOrderRepository(),
        payment_gateway=FakePaymentGateway(),
    )
    command = PlaceOrderCommand(
        customer_id=1,
        items=[
            OrderItem(product_id=10, quantity=2, unit_price=Decimal("25.00")),
            OrderItem(product_id=20, quantity=1, unit_price=Decimal("50.00")),
        ],
    )

    # Act
    order = await service.place_order(command)

    # Assert
    assert order.total == Decimal("100.00")
    assert order.status == OrderStatus.CONFIRMED
    assert len(order.items) == 2
```

---

## Fixtures

### Scope

- `function` (default): Created for each test. Use for most fixtures.
- `class`: Shared across all tests in a test class.
- `module`: Shared across all tests in a module. Use for expensive setup like database schema.
- `session`: Shared across the entire test session. Use for one-time setup like starting containers.

```python
@pytest.fixture(scope="session")
def database_engine() -> Generator[AsyncEngine, None, None]:
    """Create the database engine once for the entire test session."""
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    asyncio.run(engine.dispose())

@pytest.fixture(scope="function")
async def db_session(
    database_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh session per test, with automatic rollback."""
    async with database_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(database_engine) as session:
        async with session.begin():
            yield session
            await session.rollback()
```

### Factory Fixtures

Use factory fixtures when tests need multiple instances with varying attributes.

```python
@pytest.fixture
def make_user() -> Callable[..., User]:
    """Factory fixture for creating User instances with defaults."""
    _counter = 0

    def _make_user(
        name: str = "Test User",
        email: str | None = None,
        is_active: bool = True,
        role: UserRole = UserRole.MEMBER,
    ) -> User:
        nonlocal _counter
        _counter += 1
        return User(
            id=_counter,
            name=name,
            email=email or f"user{_counter}@example.com",
            is_active=is_active,
            role=role,
        )

    return _make_user

# Usage in tests
def test_list_active_users(make_user: Callable[..., User]) -> None:
    active = make_user(is_active=True)
    inactive = make_user(is_active=False)
    another_active = make_user(is_active=True)

    result = filter_active([active, inactive, another_active])

    assert result == [active, another_active]
```

### Async Fixtures

```python
@pytest.fixture
async def populated_db(
    db_session: AsyncSession,
    make_user: Callable[..., User],
) -> AsyncSession:
    """Seed the database with test data."""
    users = [make_user() for _ in range(5)]
    db_session.add_all([UserModel.from_domain(u) for u in users])
    await db_session.flush()
    return db_session
```

---

## Parametrized Tests

Use `@pytest.mark.parametrize` to test multiple input/output combinations without duplicating test logic.

```python
@pytest.mark.parametrize(
    ("input_email", "expected_valid"),
    [
        ("user@example.com", True),
        ("user+tag@example.com", True),
        ("user@sub.domain.com", True),
        ("", False),
        ("not-an-email", False),
        ("@example.com", False),
        ("user@", False),
        ("user@.com", False),
    ],
    ids=[
        "standard-email",
        "plus-addressing",
        "subdomain",
        "empty-string",
        "no-at-sign",
        "no-local-part",
        "no-domain",
        "dot-only-domain",
    ],
)
def test_validate_email(input_email: str, expected_valid: bool) -> None:
    result = validate_email(input_email)
    assert result == expected_valid

@pytest.mark.parametrize(
    ("quantity", "unit_price", "expected_total"),
    [
        (1, Decimal("10.00"), Decimal("10.00")),
        (5, Decimal("10.00"), Decimal("50.00")),
        (0, Decimal("10.00"), Decimal("0.00")),
        (3, Decimal("33.33"), Decimal("99.99")),
    ],
)
def test_calculate_line_total(
    quantity: int,
    unit_price: Decimal,
    expected_total: Decimal,
) -> None:
    result = calculate_line_total(quantity, unit_price)
    assert result == expected_total
```

### Parametrize with Fixtures

```python
@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.MEMBER])
async def test_authenticated_users_can_view_profile(
    role: UserRole,
    make_user: Callable[..., User],
    client: AsyncClient,
) -> None:
    user = make_user(role=role)
    response = await client.get(
        f"/users/{user.id}",
        headers=auth_headers(user),
    )
    assert response.status_code == 200
```

---

## Mocking

### When to Mock

- Mock external services (HTTP APIs, email, payment gateways).
- Mock the current time when testing time-dependent logic.
- Mock filesystem operations when testing logic that reads/writes files.
- Do NOT mock the unit under test. Mock only its dependencies.
- Do NOT mock data structures, simple functions, or value objects.

### pytest-mock (mocker fixture)

```python
async def test_user_service_sends_welcome_email(
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_email = mocker.AsyncMock(spec=EmailSender)
    mock_repo = mocker.AsyncMock(spec=UserRepository)
    mock_repo.save.return_value = User(id=1, name="Alice", email="a@b.com")

    service = UserService(user_repo=mock_repo, email_sender=mock_email)

    # Act
    await service.register_user(RegisterCommand(name="Alice", email="a@b.com"))

    # Assert
    mock_email.send_welcome.assert_awaited_once_with("a@b.com")
    mock_repo.save.assert_awaited_once()
```

### monkeypatch

Use `monkeypatch` for patching environment variables and module attributes.

```python
def test_settings_reads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("APP_DEBUG", "true")

    settings = Settings()

    assert settings.database_url == "postgresql://test:test@localhost/test"
    assert settings.debug is True

def test_function_uses_current_time(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed_now = datetime(2024, 1, 15, 12, 0, 0)
    monkeypatch.setattr("mypackage.services.datetime", lambda: fixed_now)

    result = create_timestamped_record()

    assert result.created_at == fixed_now
```

### unittest.mock.patch

Use `patch` when `monkeypatch` is not flexible enough, particularly for patching methods on classes.

```python
from unittest.mock import AsyncMock, patch

async def test_payment_service_retries_on_timeout() -> None:
    with patch(
        "mypackage.services.payment_gateway.charge",
        new_callable=AsyncMock,
        side_effect=[TimeoutError(), PaymentResult(success=True)],
    ) as mock_charge:
        result = await payment_service.charge(amount=Decimal("50.00"))

    assert result.success is True
    assert mock_charge.await_count == 2
```

### Mock Pitfalls to Avoid

```python
# DON'T - mocking the thing you're testing
def test_user_service(mocker):
    mocker.patch.object(UserService, "create_user", return_value=user)
    result = service.create_user(...)  # testing the mock, not the code

# DON'T - mocking too much (testing implementation, not behavior)
def test_create_user(mocker):
    mocker.patch("mypackage.services.uuid4", return_value="abc")
    mocker.patch("mypackage.services.datetime.now", return_value=now)
    mocker.patch("mypackage.services.hash_password", return_value="hashed")
    # Testing that specific functions are called in specific order
    # is testing implementation details, not behavior

# DO - test behavior through the public interface
async def test_create_user_persists_and_returns_user() -> None:
    repo = InMemoryUserRepository()
    service = UserService(user_repo=repo)

    user = await service.create_user(name="Alice", email="a@b.com")

    assert user.name == "Alice"
    assert await repo.get_by_id(user.id) is not None
```

---

## Async Testing

### pytest-asyncio

Configure `asyncio_mode = "auto"` in `pyproject.toml` so async test functions are detected automatically.

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

```python
# No decorator needed with asyncio_mode = "auto"
async def test_fetch_user_returns_user(
    db_session: AsyncSession,
) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    user = User(name="Alice", email="alice@example.com")
    saved = await repo.save(user)

    fetched = await repo.get_by_id(saved.id)

    assert fetched is not None
    assert fetched.name == "Alice"
```

### Async Fixtures

```python
@pytest.fixture
async def http_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

---

## Database Testing

### Transaction Rollback Strategy

Wrap each test in a transaction that rolls back after the test completes. This is faster than recreating the database for each test.

```python
@pytest.fixture
async def db_session(
    engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional session that rolls back after each test."""
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()
```

### Factory Boy for Test Data

```python
import factory
from factory.alchemy import SQLAlchemyModelFactory

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = UserModel
        sqlalchemy_session_persistence = "flush"

    name = factory.Faker("name")
    email = factory.LazyAttribute(
        lambda obj: f"{obj.name.lower().replace(' ', '.')}@example.com"
    )
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)

class OrderFactory(SQLAlchemyModelFactory):
    class Meta:
        model = OrderModel
        sqlalchemy_session_persistence = "flush"

    customer = factory.SubFactory(UserFactory)
    status = OrderStatus.PENDING
    total = factory.LazyFunction(lambda: Decimal(f"{random.uniform(10, 500):.2f}"))

# Usage
async def test_list_orders_for_customer(db_session: AsyncSession) -> None:
    UserFactory._meta.sqlalchemy_session = db_session
    OrderFactory._meta.sqlalchemy_session = db_session

    customer = UserFactory()
    OrderFactory.create_batch(3, customer=customer)
    OrderFactory.create_batch(2)  # other customer

    repo = SqlAlchemyOrderRepository(db_session)
    orders = await repo.get_by_customer(customer.id)

    assert len(orders) == 3
```

---

## API Testing

### FastAPI TestClient

```python
from httpx import AsyncClient
from fastapi.testclient import TestClient

# Synchronous (for simple tests)
def test_health_check() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# Async (preferred for async applications)
@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

async def test_create_user(client: AsyncClient) -> None:
    response = await client.post(
        "/users",
        json={"name": "Alice", "email": "alice@example.com"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"
    assert "id" in data

async def test_create_user_returns_422_for_invalid_email(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/users",
        json={"name": "Alice", "email": "not-an-email"},
    )

    assert response.status_code == 422
```

### Overriding Dependencies in Tests

```python
@pytest.fixture
def override_dependencies() -> Generator[None, None, None]:
    """Override FastAPI dependencies for testing."""
    app.dependency_overrides[get_db_session] = lambda: test_session
    app.dependency_overrides[get_current_user] = lambda: test_user
    yield
    app.dependency_overrides.clear()

async def test_protected_endpoint(
    client: AsyncClient,
    override_dependencies: None,
) -> None:
    response = await client.get("/users/me")
    assert response.status_code == 200
```

### Django Test Client

```python
from django.test import TestCase
from rest_framework.test import APIClient

class TestUserAPI(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="alice", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def test_list_users(self) -> None:
        response = self.client.get("/api/users/")
        assert response.status_code == 200
        assert len(response.data) >= 1

    def test_create_user_requires_authentication(self) -> None:
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/users/",
            {"name": "Bob", "email": "bob@example.com"},
        )
        assert response.status_code == 401
```

---

## Property-Based Testing (Hypothesis)

Use Hypothesis for testing properties that should hold for all valid inputs, rather than testing specific examples.

```python
from hypothesis import given, strategies as st, assume

@given(st.text(min_size=1, max_size=100))
def test_slugify_produces_valid_slug(text: str) -> None:
    slug = slugify(text)
    # Properties that should always hold
    assert slug == slug.lower()
    assert " " not in slug
    assert slug.replace("-", "").replace("_", "").isalnum() or slug == ""

@given(
    st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00")),
    st.integers(min_value=1, max_value=100),
)
def test_line_total_is_non_negative(price: Decimal, quantity: int) -> None:
    total = calculate_line_total(price, quantity)
    assert total >= 0

@given(st.lists(st.integers(), min_size=1))
def test_sort_preserves_length(items: list[int]) -> None:
    sorted_items = custom_sort(items)
    assert len(sorted_items) == len(items)

@given(st.lists(st.integers(), min_size=1))
def test_sort_is_idempotent(items: list[int]) -> None:
    once = custom_sort(items)
    twice = custom_sort(once)
    assert once == twice
```

### When to Use Hypothesis

- Encoding/decoding roundtrips (serialize then deserialize should return original).
- Mathematical properties (commutativity, associativity, identity).
- Data transformations where invariants must hold (length preservation, type preservation).
- Parsers and validators (valid inputs should parse, invalid should reject).

---

## Coverage

### Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
branch = true
omit = [
    "*/migrations/*",
    "*/tests/*",
    "*/__main__.py",
]

[tool.coverage.report]
fail_under = 80
show_missing = true
skip_covered = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.",
    "@overload",
    "raise NotImplementedError",
]
```

### Running with Coverage

```bash
# Run tests with coverage
pytest --cov=src --cov-report=term-missing --cov-report=html

# Fail if coverage drops below threshold
pytest --cov=src --cov-fail-under=80
```

### Coverage Rules

- Minimum 80% line coverage for the overall project.
- New code must have at least 90% coverage.
- 100% coverage on critical paths: authentication, authorization, payment processing, data validation.
- Do not write tests solely to increase coverage numbers. Every test must verify meaningful behavior.

---

## Test Markers

Define custom markers for controlling which tests run in different environments.

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests that require external services",
    "e2e: marks end-to-end tests",
]
```

```python
import pytest

@pytest.mark.slow
def test_generate_large_report() -> None:
    """Takes >10 seconds to run."""
    ...

@pytest.mark.integration
async def test_redis_cache_set_and_get() -> None:
    """Requires a running Redis instance."""
    ...

@pytest.mark.e2e
async def test_full_checkout_flow() -> None:
    """Tests the entire checkout flow against a running application."""
    ...
```

### Running by Marker

```bash
# Run only fast unit tests
pytest -m "not slow and not integration and not e2e"

# Run integration tests
pytest -m integration

# Run everything
pytest
```

---

## Testing Best Practices Summary

| Practice | Rule |
|---|---|
| Test names | Describe the scenario and expected outcome |
| Test structure | Arrange-Act-Assert with blank lines between sections |
| Assertions | Use plain `assert`, not `unittest` methods |
| Fixtures | Use factory fixtures for variable test data |
| Mocking | Mock dependencies, not the unit under test |
| Async | Use `asyncio_mode = "auto"` with pytest-asyncio |
| Database | Use transaction rollback per test for speed |
| API tests | Use `AsyncClient` for FastAPI, `APIClient` for DRF |
| Parametrize | Use for multiple input/output combinations |
| Coverage | Minimum 80% overall, 90% for new code |
| Markers | Tag slow, integration, and e2e tests |
| Hypothesis | Use for invariant and property testing |
