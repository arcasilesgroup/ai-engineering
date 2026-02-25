# Integration Testing

## Principles

- Test real interactions between components.
- Use local I/O (filesystem, database, git) — no external services.
- Slower than unit tests but validate actual behavior.
- Clean up after each test (tmp_path, test databases).

## API Testing (Python — httpx)

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_user():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/users/", json={
            "email": "test@example.com",
            "name": "Test"
        })
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_invalid_email_returns_422():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/users/", json={
            "email": "invalid",
            "name": "Test"
        })
    assert response.status_code == 422
```

## API Testing (TypeScript — Supertest)

```typescript
import request from 'supertest';
import { app } from '../app';

describe('POST /api/users', () => {
  it('creates user with valid data', async () => {
    const response = await request(app)
      .post('/api/users')
      .send({ email: 'test@test.com', name: 'Test' })
      .expect(201);

    expect(response.body).toMatchObject({
      email: 'test@test.com',
      name: 'Test',
    });
  });

  it('returns 401 without auth token', async () => {
    await request(app)
      .get('/api/users/me')
      .expect(401);
  });
});
```

## Authenticated Requests

```typescript
describe('Protected endpoints', () => {
  let authToken: string;

  beforeAll(async () => {
    const response = await request(app)
      .post('/api/auth/login')
      .send({ email: 'test@test.com', password: 'password' });
    authToken = response.body.token;
  });

  it('accesses protected route', async () => {
    await request(app)
      .get('/api/users/me')
      .set('Authorization', `Bearer ${authToken}`)
      .expect(200);
  });
});
```

## Database Testing

```typescript
import { db } from '../database';

describe('UserRepository', () => {
  beforeEach(async () => {
    await db.query('DELETE FROM users');
  });

  afterAll(async () => {
    await db.end();
  });

  it('creates and retrieves user', async () => {
    const user = await userRepo.create({ email: 'test@test.com', name: 'Test' });
    const found = await userRepo.findById(user.id);
    expect(found).toEqual(user);
  });
});
```

## Filesystem / Git Integration (Python)

```python
import subprocess

@pytest.mark.integration
def test_install_creates_hooks(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    install_framework(tmp_path)
    assert (tmp_path / ".git" / "hooks" / "pre-commit").exists()
```

## Quick Reference

| Aspect | Guideline |
|--------|-----------|
| Scope | Component interactions, real I/O |
| Speed | <10s per test |
| Cleanup | `tmp_path`, test DB rollback |
| Marker | `@pytest.mark.integration` |
| Gate | Pre-push |
