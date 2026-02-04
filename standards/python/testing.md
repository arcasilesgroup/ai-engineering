# Python Testing Standards

> pytest patterns and conventions.

---

## Test Framework

- **Framework:** pytest
- **Assertions:** pytest built-in / pytest-assertpy
- **Mocking:** pytest-mock / unittest.mock
- **Coverage:** pytest-cov
- **Async:** pytest-asyncio

---

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_user_service.py
│   └── test_utils.py
├── integration/
│   └── test_api.py
└── fixtures/
    └── user_fixtures.py
```

---

## Naming Conventions

### Test Files

```
test_module.py        # Test file for module.py
test_user_service.py  # Test file for user_service.py
```

### Test Functions

```python
# Pattern: test_[unit]_[scenario]_[expected]
def test_get_user_with_valid_id_returns_user():
    pass

def test_get_user_with_invalid_id_raises_not_found():
    pass

def test_calculate_discount_with_max_limit_applies_cap():
    pass
```

---

## Basic Test Pattern

```python
import pytest
from myapp.services.user_service import UserService, NotFoundError

class TestUserService:
    """Tests for UserService."""

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

---

## Fixtures

### conftest.py

```python
import pytest
from unittest.mock import Mock
from myapp.services.user_service import UserService
from myapp.models.user import User

@pytest.fixture
def mock_repository():
    """Create mock repository."""
    return Mock()

@pytest.fixture
def user_service(mock_repository):
    """Create UserService with mock dependencies."""
    return UserService(repository=mock_repository)

@pytest.fixture
def sample_user():
    """Create sample user for testing."""
    return User(
        id="123",
        name="John Doe",
        email="john@example.com"
    )

@pytest.fixture
def sample_users():
    """Create list of sample users."""
    return [
        User(id="1", name="Alice", email="alice@example.com"),
        User(id="2", name="Bob", email="bob@example.com"),
    ]
```

### Parameterized Fixtures

```python
@pytest.fixture(params=["active", "inactive", "pending"])
def user_status(request):
    """Parameterized fixture for user statuses."""
    return request.param

def test_user_status_display(user_status):
    # Test runs 3 times with different statuses
    result = format_status(user_status)
    assert result is not None
```

---

## Parametrize

```python
@pytest.mark.parametrize("input_value,expected", [
    (100, 80),      # 20% off of 100
    (50, 40),       # 20% off of 50
    (0, 0),         # 20% off of 0
])
def test_calculate_discount(input_value, expected):
    result = calculate_discount(input_value, discount_percent=20)
    assert result == expected

@pytest.mark.parametrize("invalid_input", [
    -1,
    101,
    "not a number",
])
def test_discount_with_invalid_percent_raises(invalid_input):
    with pytest.raises(ValueError):
        calculate_discount(100, discount_percent=invalid_input)
```

---

## Async Testing

```python
import pytest

@pytest.mark.asyncio
async def test_fetch_user_returns_user():
    # Arrange
    client = AsyncAPIClient()

    # Act
    user = await client.fetch_user("123")

    # Assert
    assert user.id == "123"

@pytest.mark.asyncio
async def test_fetch_users_concurrent():
    client = AsyncAPIClient()
    
    users = await client.fetch_all_users(["1", "2", "3"])
    
    assert len(users) == 3
```

---

## Mocking

### Using pytest-mock

```python
def test_send_email_calls_smtp(mocker):
    # Arrange
    mock_smtp = mocker.patch("myapp.email.smtplib.SMTP")
    service = EmailService()

    # Act
    service.send("test@example.com", "Hello")

    # Assert
    mock_smtp.return_value.send_message.assert_called_once()

def test_get_config_from_env(mocker):
    mocker.patch.dict("os.environ", {"API_KEY": "secret"})
    
    config = get_config()
    
    assert config.api_key == "secret"
```

### Using unittest.mock

```python
from unittest.mock import Mock, patch, AsyncMock

def test_with_patch():
    with patch("myapp.services.external_api") as mock_api:
        mock_api.get_data.return_value = {"key": "value"}
        
        result = process_data()
        
        assert result["key"] == "value"

@pytest.mark.asyncio
async def test_async_mock():
    mock_client = AsyncMock()
    mock_client.fetch.return_value = {"id": "123"}
    
    result = await mock_client.fetch("123")
    
    assert result["id"] == "123"
```

---

## Assertions

```python
# Equality
assert result == expected
assert result != other

# Truthiness
assert user.is_active
assert not user.is_deleted

# Membership
assert "error" in response.message
assert item in collection

# Type checking
assert isinstance(result, User)

# Approximate equality (floats)
assert result == pytest.approx(expected, rel=1e-3)

# Exception testing
with pytest.raises(ValueError, match="must be positive"):
    process(-1)
```

---

## Markers

```python
# Skip test
@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass

# Skip conditionally
@pytest.mark.skipif(sys.platform == "win32", reason="Unix only")
def test_unix_specific():
    pass

# Expected failure
@pytest.mark.xfail(reason="Known bug #123")
def test_known_issue():
    pass

# Custom marker
@pytest.mark.integration
def test_database_connection():
    pass
```

Run specific markers:
```bash
pytest -m integration
pytest -m "not slow"
```

---

## Coverage

```bash
# Run with coverage
pytest --cov=myapp --cov-report=html

# Fail if coverage below threshold
pytest --cov=myapp --cov-fail-under=80
```

---

## Best Practices

### Do

- ✅ Use fixtures for setup and teardown
- ✅ Keep tests independent
- ✅ Use parametrize for data-driven tests
- ✅ Test edge cases and error conditions
- ✅ Use meaningful assertion messages

### Don't

- ❌ Test implementation details
- ❌ Use sleep() in tests (use proper async)
- ❌ Share state between tests
- ❌ Mock too much
- ❌ Write flaky tests
