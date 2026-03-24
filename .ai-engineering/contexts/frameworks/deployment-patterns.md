# Deployment Patterns

Cross-cutting deployment, containerization, health check, and production readiness patterns. Stack-agnostic unless noted.

## Deployment Strategies

### Rolling

Replaces instances incrementally. Zero downtime but mixed versions coexist during rollout.

```text
Time 0:  [v1] [v1] [v1] [v1]
Time 1:  [v2] [v1] [v1] [v1]   <- 1 replaced
Time 2:  [v2] [v2] [v1] [v1]   <- 2 replaced
Time 3:  [v2] [v2] [v2] [v1]   <- 3 replaced
Time 4:  [v2] [v2] [v2] [v2]   <- complete
```

- Use when: backward-compatible changes, stateless services.
- Avoid when: schema migrations that break v1, strict version consistency required.
- Rollback: reverse the rolling update to previous image tag.

### Blue-Green

Two identical environments. Switch traffic atomically via load balancer.

```text
              LB
             /  \
    [Blue v1]    [Green v2]    <- Green receives traffic after validation
         |            |
      (idle)      (active)

Rollback: point LB back to Blue
```

- Use when: zero-downtime required, need instant rollback.
- Cost: 2x infrastructure during deployment window.
- Validate Green thoroughly before switching. Run smoke tests against Green URL.

### Canary

Route a small percentage of traffic to the new version. Promote or rollback based on metrics.

```text
Traffic split:
  95% --> [v1] [v1] [v1] [v1]
   5% --> [v2]                    <- canary pod

Monitor: error rate, latency p99, saturation
  Pass  --> promote to 25% --> 50% --> 100%
  Fail  --> rollback canary, 100% stays on v1
```

- Use when: high-risk changes, performance-sensitive services.
- Requires: metric collection, traffic splitting (Istio, Flagger, ALB weighted targets).
- Key metrics to watch: error rate delta, latency p99 delta, CPU/memory anomalies.

## Docker Multi-Stage Patterns

### Key Rules

- Pin specific image tags. Never use `latest` in production.
- Run as non-root user. Use `uid 1001` by convention.
- Include `HEALTHCHECK` instruction.
- Add `.dockerignore` to exclude `node_modules/`, `.git/`, `__pycache__/`, `.env`, test fixtures.

### Node.js

```dockerfile
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --production

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
RUN addgroup -g 1001 app && adduser -u 1001 -G app -s /bin/sh -D app
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json ./
USER 1001
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "dist/main.js"]
```

### Go

```dockerfile
FROM golang:1.23-alpine AS build
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /server ./cmd/server

FROM gcr.io/distroless/static:nonroot
COPY --from=build /server /server
USER 1001
EXPOSE 8080
ENTRYPOINT ["/server"]
```

### Python

```dockerfile
FROM python:3.13-slim AS build
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev --frozen

FROM python:3.13-slim
RUN groupadd -g 1001 app && useradd -u 1001 -g app -s /bin/bash app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY src/ ./src/
ENV PATH="/app/.venv/bin:$PATH"
USER 1001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## CI/CD Pipeline (GitHub Actions)

Standard three-job pipeline: test, build, deploy.

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: <stack-install>
      - name: Lint
        run: <stack-lint>
      - name: Test
        run: <stack-test>
      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t $IMAGE:${{ github.sha }} .
      - name: Push to registry
        run: docker push $IMAGE:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Deploy
        run: <deploy-command> --image $IMAGE:${{ github.sha }}
```

Rules: test must pass before build. Build must pass before deploy. Deploy only from main. Use `environment:` for approval gates.

## Health Check Patterns

### Simple Health

Returns 200 when the process is alive and can serve requests.

```json
GET /health
200 OK
{ "status": "healthy" }
```

Use for: liveness probes, load balancer registration.

### Detailed Health

Checks each dependency individually. Returns 200 when all pass, 503 when any critical dependency fails.

```json
GET /health/detailed
200 OK
{
  "status": "healthy",
  "checks": {
    "database": { "status": "healthy", "latency_ms": 4 },
    "redis": { "status": "healthy", "latency_ms": 1 },
    "external_api": { "status": "degraded", "latency_ms": 850 }
  },
  "version": "1.4.2",
  "uptime_seconds": 86400
}
```

Rules:
- Never expose secrets or internal IPs in health responses.
- Distinguish `healthy`, `degraded`, `unhealthy`.
- Set timeouts on dependency checks (3s max per check).
- Return 503 only when the service cannot fulfill its core function.

## Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 30
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/detailed
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /health
    port: 8080
  periodSeconds: 5
  failureThreshold: 30
```

- **Liveness** (30s period): is the process alive? Restart if failed 3 times.
- **Readiness** (10s period): can it accept traffic? Remove from service if unhealthy.
- **Startup** (5s period, 30 failures = 150s budget): is it done initializing? Protects slow-starting apps.

Do not use the same probe for liveness and readiness. Liveness should be cheap; readiness checks dependencies.

## Environment Configuration

Follow Twelve-Factor App methodology (factor III: config).

```text
Rules:
1. Store config in environment variables, not files.
2. Never commit secrets. Use vault or CI/CD secret injection.
3. Validate all required config at startup. Fail fast with clear message.
4. Use a schema to define expected variables, types, and defaults.
5. Separate config by concern: database, auth, feature flags, observability.
```

Startup validation pattern:

```python
REQUIRED = ["DATABASE_URL", "JWT_SECRET", "REDIS_URL"]
missing = [v for v in REQUIRED if not os.environ.get(v)]
if missing:
    raise SystemExit(f"Missing required env vars: {', '.join(missing)}")
```

## Rollback Commands

Quick reference for common rollback operations.

```bash
# Kubernetes: rollback to previous deployment
kubectl rollout undo deployment/<name> -n <namespace>

# Kubernetes: rollback to specific revision
kubectl rollout undo deployment/<name> --to-revision=<N>

# Vercel: promote previous deployment
vercel rollback <deployment-url>

# Railway: rollback to previous deployment
railway rollback

# Prisma: rollback last migration
prisma migrate resolve --rolled-back <migration-name>

# Database: point-in-time recovery (PostgreSQL)
# Restore from backup to specific timestamp -- platform-specific command
```

Always verify rollback succeeded: check health endpoints, review error rates, confirm expected version.

## Production Readiness Checklist

### Application

- [ ] Health endpoints implemented (`/health` and `/health/detailed`)
- [ ] Graceful shutdown handles SIGTERM (drain connections, finish in-flight)
- [ ] Structured logging with correlation IDs
- [ ] Request validation at API boundary
- [ ] Error responses do not leak internals (stack traces, SQL, file paths)
- [ ] Rate limiting on public endpoints
- [ ] Timeouts configured for all outbound calls

### Infrastructure

- [ ] Container runs as non-root (uid 1001)
- [ ] Resource limits set (CPU, memory)
- [ ] Horizontal pod autoscaler configured
- [ ] Persistent storage uses managed volumes, not local disk
- [ ] DNS and TLS configured and tested
- [ ] Multi-AZ or multi-region for critical services

### Monitoring

- [ ] Application metrics exported (request rate, error rate, latency)
- [ ] Alerting rules for error rate spike, latency p99, pod restarts
- [ ] Dashboard with RED metrics (Rate, Errors, Duration)
- [ ] Log aggregation with search and retention policy
- [ ] Distributed tracing for multi-service calls

### Security

- [ ] Secrets injected via vault or CI/CD, never in image or env files
- [ ] Network policies restrict pod-to-pod traffic
- [ ] Container image scanned for CVEs
- [ ] HTTPS enforced, HSTS headers set
- [ ] Authentication and authorization on all endpoints

### Operations

- [ ] Runbook documented for common failure scenarios
- [ ] Rollback procedure tested and documented
- [ ] Backup and restore procedure verified
- [ ] On-call rotation and escalation path defined
- [ ] Load test completed at 2x expected peak
