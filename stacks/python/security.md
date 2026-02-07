# Python Security Standards

These standards define the security practices that must be followed in all Python projects. Security is not optional. Every code change must be evaluated against these rules. When generating or modifying code, apply these practices by default without being asked.

---

## SQL Injection Prevention

Never construct SQL queries by concatenating or formatting user input into query strings. Always use parameterized queries or an ORM.

```python
# DON'T - string formatting in SQL
async def get_user(user_id: str) -> User:
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection
    return await db.execute(query)

# DON'T - string concatenation
query = "SELECT * FROM users WHERE name = '" + name + "'"

# DO - parameterized query
async def get_user(user_id: int) -> User:
    query = text("SELECT * FROM users WHERE id = :user_id")
    result = await session.execute(query, {"user_id": user_id})
    return result.scalar_one_or_none()

# DO - ORM (SQLAlchemy)
async def get_user(user_id: int) -> User | None:
    result = await session.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    return result.scalar_one_or_none()

# DO - Django ORM
user = await User.objects.filter(id=user_id).afirst()
```

Even with an ORM, never pass raw user input into `extra()`, `raw()`, or `RawSQL()` without parameterization.

---

## Command Injection Prevention

Never pass user input to a shell. Never use `os.system()`, `os.popen()`, or `subprocess.run(..., shell=True)` with user-controlled data.

```python
# DON'T - shell=True with user input
import subprocess
subprocess.run(f"convert {user_filename} output.png", shell=True)  # injection

# DON'T - os.system
import os
os.system(f"rm {filepath}")  # injection + dangerous

# DO - subprocess with list arguments (no shell)
import subprocess
import shlex

subprocess.run(
    ["convert", user_filename, "output.png"],
    capture_output=True,
    check=True,
    timeout=30,
)

# DO - validate and sanitize the input first
from pathlib import Path

def safe_convert(filename: str) -> None:
    path = Path(filename)
    if not path.suffix in (".jpg", ".png", ".gif"):
        raise ValueError(f"Unsupported file type: {path.suffix}")
    if ".." in path.parts:
        raise ValueError("Path traversal detected")

    subprocess.run(
        ["convert", str(path), "output.png"],
        capture_output=True,
        check=True,
        timeout=30,
    )
```

---

## Deserialization Safety

Never deserialize untrusted data with `pickle`, `marshal`, `shelve`, or `yaml.load()` (without `SafeLoader`). These formats allow arbitrary code execution.

```python
# DON'T - pickle with untrusted data
import pickle
data = pickle.loads(request.body)  # arbitrary code execution

# DON'T - yaml.load without SafeLoader
import yaml
config = yaml.load(user_input)  # arbitrary code execution

# DO - use JSON for untrusted data
import json
data = json.loads(request.body)

# DO - use Pydantic for validation
from pydantic import BaseModel

class UserInput(BaseModel):
    name: str
    email: str

validated = UserInput.model_validate_json(request.body)

# DO - yaml with SafeLoader
import yaml
config = yaml.safe_load(config_file.read())

# DO - if you must use pickle, only for trusted internal data
# and document why pickle is necessary (e.g., caching ML models)
```

---

## Path Traversal Prevention

Never construct file paths by directly concatenating user input. Attackers can use `../` sequences to access files outside the intended directory.

```python
# DON'T - direct path concatenation
def serve_file(filename: str) -> bytes:
    path = f"/uploads/{filename}"  # "../../../etc/passwd" breaks out
    with open(path, "rb") as f:
        return f.read()

# DO - resolve and validate the path
from pathlib import Path

UPLOAD_DIR = Path("/uploads").resolve()

def serve_file(filename: str) -> bytes:
    # Resolve the full path and verify it's inside the allowed directory
    requested = (UPLOAD_DIR / filename).resolve()

    if not requested.is_relative_to(UPLOAD_DIR):
        raise PermissionError("Access denied: path traversal detected")

    if not requested.is_file():
        raise FileNotFoundError(f"File not found: {filename}")

    with open(requested, "rb") as f:
        return f.read()

# DO - for FastAPI static files
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory="/uploads"), name="uploads")
```

---

## SSRF Prevention

Server-Side Request Forgery (SSRF) occurs when an application makes HTTP requests to URLs controlled by the user, allowing access to internal services.

```python
# DON'T - fetch arbitrary URLs
async def fetch_url(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:  # SSRF
            return await response.json()

# DO - validate and restrict URLs
import ipaddress
from urllib.parse import urlparse

ALLOWED_HOSTS = {"api.example.com", "cdn.example.com"}

def validate_url(url: str) -> str:
    """Validate that a URL is safe to fetch."""
    parsed = urlparse(url)

    # Require HTTPS
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS URLs are allowed")

    # Block private/internal IPs
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback or ip.is_reserved:
            raise ValueError("Internal IP addresses are not allowed")
    except ValueError:
        pass  # hostname is not an IP, check against allowlist

    # Allowlist check
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Host not allowed: {parsed.hostname}")

    return url

async def fetch_url(url: str) -> dict:
    safe_url = validate_url(url)
    async with aiohttp.ClientSession() as session:
        async with session.get(safe_url) as response:
            return await response.json()
```

---

## Secret Management

Never hardcode secrets, API keys, passwords, or tokens in source code. Never commit them to version control.

```python
# DON'T
STRIPE_KEY = "sk_live_abc123xyz"  # hardcoded secret
DATABASE_URL = "postgresql://admin:password@prod-db:5432/app"

# DON'T - even in "config" files that get committed
config = {
    "api_key": "abc123",
    "db_password": "supersecret",
}

# DO - environment variables via pydantic-settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    stripe_api_key: str  # loaded from STRIPE_API_KEY env var
    database_url: str    # loaded from DATABASE_URL env var
    jwt_secret: str      # loaded from JWT_SECRET env var

settings = Settings()  # raises ValidationError if vars are missing

# DO - use a secrets manager for production
# AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager, etc.
```

### .gitignore Requirements

Every project must include these in `.gitignore`:

```
.env
.env.*
*.pem
*.key
secrets.yaml
secrets.json
credentials.json
```

### Secret Rotation

- All secrets must have a rotation strategy.
- JWT secrets must be rotatable without downtime (support multiple valid secrets during rotation).
- Database credentials should use short-lived tokens where possible.

---

## Dependency Security

### Audit Dependencies

Run dependency audits regularly and in CI.

```bash
# pip-audit (recommended)
pip-audit --strict --fix

# safety
safety check

# pip itself
pip check
```

### Dependabot / Renovate

Configure automated dependency updates in your repository. Review and merge security patches promptly (within 24 hours for critical vulnerabilities).

### Pin Dependencies

- Pin exact versions in lock files (`requirements.txt`, `poetry.lock`, `uv.lock`).
- Use version ranges in `pyproject.toml` but generate a lock file for reproducible builds.
- Review dependency changelogs before upgrading.

```toml
# pyproject.toml - ranges for compatibility
[project]
dependencies = [
    "fastapi>=0.109.0,<1.0.0",
    "pydantic>=2.5.0,<3.0.0",
]

# Lock file pins exact versions for deployment
# uv.lock, poetry.lock, or requirements.txt with hashes
```

### Minimize Dependencies

- Before adding a dependency, evaluate whether a 10-line utility function would suffice.
- Audit transitive dependencies. A single package can pull in dozens of others.
- Prefer well-maintained packages from reputable organizations.

---

## Input Validation

Validate all external input at the boundary. Never trust data from users, APIs, files, or message queues.

```python
# DO - Pydantic validation for API input
from pydantic import BaseModel, Field, field_validator

class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(max_length=320)
    age: int = Field(ge=0, le=200)
    bio: str = Field(default="", max_length=5000)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()

# DO - validate at the boundary, trust internally
@router.post("/users")
async def create_user(
    payload: CreateUserRequest,  # validated by Pydantic before handler runs
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.create_user(payload)  # service receives validated data
```

### Sanitization

- Strip leading/trailing whitespace from string inputs.
- Normalize Unicode to prevent homograph attacks.
- Enforce maximum lengths on all string inputs to prevent abuse.
- Reject or escape HTML in text fields that are not supposed to contain HTML.

---

## Authentication

### JWT Best Practices

```python
import jwt
from datetime import datetime, timedelta, timezone

def create_access_token(
    user_id: int,
    roles: list[str],
    secret: str,
    expires_in: timedelta = timedelta(minutes=30),
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "roles": roles,
        "iat": now,
        "exp": now + expires_in,
        "jti": str(uuid.uuid4()),  # unique token ID for revocation
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def verify_access_token(token: str, secret: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],  # always specify allowed algorithms
            options={
                "require": ["sub", "exp", "iat"],
                "verify_exp": True,
            },
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {e}")
```

### Rules

- Use short-lived access tokens (15-30 minutes) and long-lived refresh tokens.
- Always specify allowed algorithms in `jwt.decode()` to prevent algorithm confusion attacks.
- Include `exp` (expiration), `iat` (issued at), and `jti` (unique ID) claims.
- Store refresh tokens securely (HTTP-only cookies or encrypted storage).
- Implement token revocation for logout and security incidents.

### OAuth2 in FastAPI

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    payload = verify_access_token(token, settings.jwt_secret)
    user = await session.get(UserModel, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user

def require_role(*roles: str) -> Callable:
    async def dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return Depends(dependency)

# Usage
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = require_role("admin"),
) -> None:
    ...
```

---

## CORS Configuration

Never use `allow_origins=["*"]` in production. Explicitly list allowed origins.

```python
# DON'T - overly permissive
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allows any website to make requests
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DO - explicit allowlist
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.example.com",
        "https://admin.example.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# DO - load from configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # from environment/config
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

## Rate Limiting

Apply rate limiting to all public-facing endpoints to prevent abuse, brute force attacks, and denial of service.

```python
# Using slowapi with FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, payload: LoginRequest) -> TokenResponse:
    ...

@router.post("/auth/reset-password")
@limiter.limit("3/hour")
async def reset_password(request: Request, payload: ResetRequest) -> None:
    ...

@router.get("/users")
@limiter.limit("100/minute")
async def list_users(request: Request) -> list[UserResponse]:
    ...
```

### Rate Limit Guidelines

| Endpoint Type | Recommended Limit |
|---|---|
| Login / Authentication | 5 per minute |
| Password reset | 3 per hour |
| Public API read | 100 per minute |
| Public API write | 20 per minute |
| Webhooks | 1000 per minute |
| File upload | 10 per hour |

---

## File Upload Security

```python
from pathlib import Path
import hashlib
import magic  # python-magic

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "application/pdf",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
UPLOAD_DIR = Path("/app/uploads").resolve()

async def upload_file(file: UploadFile) -> str:
    """Securely handle a file upload."""
    # 1. Check file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE} bytes.",
        )

    # 2. Validate MIME type by reading file contents (not trusting headers)
    detected_type = magic.from_buffer(contents, mime=True)
    if detected_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed: {detected_type}",
        )

    # 3. Generate a safe filename (never use the original filename)
    file_hash = hashlib.sha256(contents).hexdigest()
    extension = Path(file.filename).suffix.lower() if file.filename else ""
    if extension not in (".jpg", ".jpeg", ".png", ".gif", ".pdf"):
        extension = ""
    safe_name = f"{file_hash}{extension}"

    # 4. Write to a controlled directory
    dest = (UPLOAD_DIR / safe_name).resolve()
    if not dest.is_relative_to(UPLOAD_DIR):
        raise PermissionError("Invalid upload path")

    dest.write_bytes(contents)
    return safe_name
```

### File Upload Rules

- Never use the original filename for storage. Generate a safe name (hash or UUID).
- Validate MIME type by reading file content (`python-magic`), not by trusting the `Content-Type` header or file extension.
- Enforce maximum file size at both the application and web server level.
- Store uploads outside the web root.
- Scan uploaded files for malware if the application handles documents from untrusted users.
- Set restrictive permissions on the upload directory.

---

## Security Checklist

| Area | Check |
|---|---|
| SQL | All queries use parameterized queries or ORM? |
| Commands | No `os.system()` or `shell=True` with user input? |
| Deserialization | No `pickle`/`yaml.load()` on untrusted data? |
| Path traversal | All file paths validated with `.resolve()` and boundary check? |
| SSRF | All outbound URLs validated against allowlist? |
| Secrets | No hardcoded secrets? All loaded from environment/vault? |
| Dependencies | `pip-audit` runs in CI? Dependabot enabled? |
| Input validation | All external input validated with Pydantic? |
| Authentication | JWTs use short TTL, explicit algorithms, revocation? |
| CORS | Origins explicitly allowlisted (no `*` in production)? |
| Rate limiting | All public endpoints rate limited? |
| File uploads | MIME validated, filename generated, size limited? |
