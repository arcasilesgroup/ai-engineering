# Framework Node.js Backend Stack Standards

## Update Metadata

- Rationale: establish Node.js backend patterns for non-framework services (Express, Fastify, raw Node).
- Expected gain: consistent Node.js backend quality, async patterns, and operational standards.
- Potential impact: Node.js backend projects get enforceable patterns distinct from frontend or NestJS.

## Stack Scope

- Primary language: TypeScript (strict mode).
- Runtime: Node.js (LTS).
- Frameworks: Express, Fastify, Hono, or raw Node.js HTTP module.
- Base standard: extends `standards/framework/stacks/typescript.md` — all TS rules apply.
- Supporting formats: Markdown, YAML, JSON.
- Distribution: Docker container, cloud function, or platform deployment.

## Required Tooling

- Inherits all tooling from `typescript.md`.
- Process management: `pm2` or container orchestration (Docker, Kubernetes).
- API documentation: OpenAPI/Swagger (generated or hand-authored).
- Database client: Prisma, Drizzle, or Knex per project convention.

## Minimum Gate Set

- Pre-commit: inherits from `typescript.md`.
- Pre-push: inherits from `typescript.md`.

## Quality Baseline

- Inherits all quality rules from `typescript.md`.
- Graceful shutdown: handle `SIGTERM`/`SIGINT` with connection draining.
- Health checks: `/health` and `/ready` endpoints for load balancer probes.
- Structured logging: JSON-format logs with correlation IDs.
- Rate limiting: configured on public-facing endpoints.

## Code Patterns

- **Async/await**: all I/O operations use async/await. No callback patterns.
- **Stream processing**: use Node.js streams for large data (file uploads, ETL). Pipe with backpressure handling.
- **Worker threads**: CPU-intensive tasks offloaded to worker threads, not the event loop.
- **Environment configuration**: validated at startup with `zod`. Fail fast on missing required config.
- **Middleware pattern**: Express/Fastify middleware for cross-cutting concerns (auth, logging, error handling, CORS).
- **Error handling**: centralized error handler middleware. Typed error classes with HTTP status codes.
- **Database**: connection pooling, prepared statements, transaction wrappers.
- **Caching**: Redis or in-memory with TTL. Cache-aside pattern for read-heavy endpoints.
- **Small focused functions**: <50 lines, single responsibility.
- **Project layout**: `src/routes/`, `src/services/`, `src/middleware/`, `src/lib/`, `src/config/`.

## Testing Patterns

- Inherits patterns from `typescript.md`.
- API tests: supertest for Express/Fastify endpoint testing.
- Database tests: test containers or in-memory SQLite.
- Stream tests: mock readable/writable streams.
- Load tests: k6 or autocannon for performance baselines.

## Performance

_Stack-specific performance patterns will be added as the standard evolves. Refer to `review/performance/SKILL.md` for general performance review procedures._

## Security

_Stack-specific security patterns will be added as the standard evolves. Refer to `review/security/SKILL.md` for general security review procedures._

## Update Contract

This file is framework-managed and may be updated by framework releases.
