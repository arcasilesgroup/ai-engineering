# CI/CD Pipeline Standards

These standards govern how an AI coding assistant designs, implements, and maintains CI/CD pipelines. Every pipeline decision must be grounded in these principles.

---

## Pipeline as Code

All pipeline definitions live in version control alongside application code. Never configure pipelines through a web UI alone.

- Store pipeline definitions in the repository root or a dedicated `.github/workflows/`, `.azure-pipelines/`, or `ci/` directory.
- Treat pipeline files with the same rigor as application code: peer review, linting, and testing.
- Use a linter for pipeline files. For GitHub Actions, use `actionlint`. For Azure Pipelines, use the Azure Pipelines VS Code extension or API validation.
- Include pipeline changes in pull requests so reviewers can assess deployment impact alongside code changes.
- Document non-obvious pipeline decisions with inline comments in YAML files.

```yaml
# Good: Pipeline definition is self-documenting and version controlled
# .github/workflows/ci.yml
name: CI
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
```

### Pipeline Testing

- Test pipeline logic locally before pushing when possible. Use `act` for GitHub Actions or the Azure Pipelines agent locally.
- Create a dedicated pipeline that validates other pipeline files on change.
- Use path filters so pipeline-only changes do not trigger full application builds.

---

## Fast Feedback

The primary goal of CI is to give developers fast, reliable feedback. Every decision should optimize for speed without sacrificing correctness.

### Fail Fast

- Order pipeline stages so the cheapest and most-likely-to-fail checks run first.
- Run linting and type checking before unit tests. Run unit tests before integration tests.
- Use `fail-fast: true` in matrix strategies unless you explicitly need all combinations to complete.
- Set timeouts on every job and step to prevent hung pipelines from consuming resources.

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - run: npm run lint

  test:
    needs: lint  # Only run tests if linting passes
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - run: npm test
```

### Parallelize

- Split independent work into separate jobs that run concurrently.
- Use matrix strategies for multi-platform or multi-version testing.
- Shard large test suites across multiple runners.
- Separate build, test, lint, and security scanning into parallel jobs where dependencies allow.

### Cache Aggressively

- Cache dependency installations (node_modules, pip packages, Go modules).
- Cache build artifacts between steps and between runs.
- Cache Docker layers for container builds.
- Use content-based cache keys (lock file hashes) so caches invalidate only when dependencies change.
- Set reasonable cache expiration; do not let stale caches persist indefinitely.

---

## Idempotent Pipelines

Running the same pipeline with the same inputs must produce the same outputs, regardless of how many times it runs.

- Pin all dependency versions in lock files. Never use floating version ranges in CI.
- Pin action versions to full commit SHAs, not tags.
- Pin base Docker images to digests, not mutable tags like `latest`.
- Use deterministic build tools. If a build tool supports reproducible builds, enable it.
- Avoid relying on external state that may change between runs (mutable remote resources, APIs without versioning).
- Ensure database migrations are idempotent: they can run multiple times without error.

```yaml
# Good: Pinned to SHA
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1

# Bad: Mutable tag
- uses: actions/checkout@v4
```

When full SHA pinning is impractical for readability, pin to a specific version tag and add a comment with the SHA. Use Dependabot or Renovate to keep pinned versions current.

---

## Environment Parity

Minimize differences between development, staging, and production environments.

- Use the same OS, runtime versions, and dependency versions across all environments.
- Use containers to enforce environment consistency.
- Deploy the same artifact to every environment; vary only configuration through environment variables.
- Use infrastructure as code to provision environments identically.
- Test with the same database engine and version as production. Never substitute SQLite for PostgreSQL in CI if production uses PostgreSQL.

### Environment Promotion Model

```
Build → Dev → Staging → Production
  │       │       │          │
  │       │       │          └─ Manual approval gate
  │       │       └─ Automated smoke tests
  │       └─ Automated integration tests
  └─ Unit tests, lint, security scan
```

- Every environment gets the same immutable artifact.
- Configuration differences are injected via environment variables or config files, not baked into the artifact.
- Promotion from one environment to the next requires passing the gate criteria for that stage.

---

## Immutable Artifacts

Build an artifact once and deploy it to every environment. Never rebuild for different environments.

- Tag artifacts with the Git SHA or a unique build identifier.
- Store artifacts in a registry (container registry, package registry, artifact storage).
- Never modify an artifact after it is built. If changes are needed, build a new artifact.
- Include metadata with every artifact: Git SHA, build timestamp, pipeline run ID.

```yaml
# Build once, tag with SHA
- name: Build and push Docker image
  run: |
    docker build -t myapp:${{ github.sha }} .
    docker push registry.example.com/myapp:${{ github.sha }}

# Deploy to staging using the same image
- name: Deploy to staging
  run: |
    kubectl set image deployment/myapp myapp=registry.example.com/myapp:${{ github.sha }}
```

---

## Pipeline Stages

Organize pipelines into well-defined stages with clear responsibilities.

### Standard Stage Order

1. **Build** -- Compile code, install dependencies, generate artifacts.
2. **Test** -- Run unit tests, integration tests, and contract tests.
3. **Security** -- Run SAST, dependency scanning, container scanning, secrets detection.
4. **Quality** -- Run linting, formatting checks, code coverage thresholds.
5. **Package** -- Build Docker images, create release bundles, publish packages.
6. **Deploy to Staging** -- Deploy the artifact to a staging environment.
7. **Smoke Test** -- Run a minimal test suite against the staging environment.
8. **Deploy to Production** -- Deploy the artifact to production after approval.
9. **Post-Deploy Verification** -- Run health checks and smoke tests against production.

### Stage Rules

- Every stage must have a clear pass/fail condition.
- Stages must be ordered so that cheaper checks run before expensive ones.
- A failure in any stage must block subsequent stages.
- Security and quality stages must never be skippable in the main branch pipeline.
- Deploy stages for production must require explicit approval in the pipeline configuration.

---

## Branch-Based Workflows

### Trunk-Based Development (Preferred)

Use trunk-based development for teams practicing continuous deployment.

- All developers commit to `main` (or a short-lived feature branch that merges within 1-2 days).
- Feature flags gate incomplete work in production.
- The `main` branch is always deployable.
- CI runs on every push to `main` and on every pull request targeting `main`.
- Release from `main` directly, tagging commits for release tracking.

### GitFlow (When Required)

Use GitFlow only when the project requires formal release management with long-lived release branches.

- `main` reflects production. `develop` reflects the next release.
- Feature branches branch from `develop` and merge back to `develop`.
- Release branches branch from `develop` for stabilization.
- Hotfix branches branch from `main` for urgent production fixes.
- CI runs on all branches. CD runs on `main` and release branches only.

### Branch Protection

- Require status checks to pass before merging.
- Require at least one approving review.
- Require branches to be up to date with the base branch.
- Require signed commits on protected branches when the team supports it.
- Disallow force pushes to protected branches.
- Disallow deletion of protected branches.

---

## Deployment Strategies

### Blue-Green Deployment

Maintain two identical environments. Deploy to the idle one, verify, then switch traffic.

- Use when zero-downtime is required and the application supports instant cutover.
- Ensure the database schema is compatible with both the old and new application versions during the switch.
- Keep the old environment running as an instant rollback target.

### Canary Deployment

Route a small percentage of traffic to the new version, gradually increasing as confidence grows.

- Use when you need to validate behavior under real production traffic before full rollout.
- Define metrics that trigger automatic rollback (error rate, latency, custom business metrics).
- Start with 1-5% of traffic. Increase to 10%, 25%, 50%, 100% over a defined schedule.

### Rolling Deployment

Replace instances of the old version one at a time with the new version.

- Use when the application is stateless and instances are interchangeable.
- Set `maxUnavailable` and `maxSurge` to control the pace.
- Ensure health checks gate the rollout so unhealthy instances halt the deployment.

### Feature Flags as a Deployment Strategy

- Decouple deployment from release. Deploy code to production but keep features behind flags.
- Use feature flags for gradual rollouts, A/B testing, and kill switches.
- Clean up feature flags after full rollout to avoid technical debt.

---

## Rollback Strategies

Every deployment must have a tested rollback plan.

- **Automatic rollback**: Configure deployment tooling to roll back automatically when health checks fail after deployment.
- **Manual rollback**: Ensure the team can trigger a rollback in under 5 minutes by redeploying the previous artifact.
- **Database rollback**: If a deployment includes database migrations, the migration must be backward-compatible so the previous application version still works with the new schema.
- Never roll back database migrations in production unless absolutely necessary. Design migrations to be forward-only and backward-compatible.
- Test rollback procedures regularly. A rollback plan that has never been tested is not a plan.

```yaml
# Automated rollback example (Kubernetes)
- name: Deploy with rollback
  run: |
    kubectl rollout status deployment/myapp --timeout=300s || \
    kubectl rollout undo deployment/myapp
```

---

## Pipeline Monitoring and Alerting

Treat pipeline health as a production concern.

### Metrics to Track

- **Pipeline duration**: Track trends. Investigate increases.
- **Success rate**: Alert when the failure rate for the main branch exceeds a threshold.
- **Queue time**: Monitor how long jobs wait for runners.
- **Flaky test rate**: Track tests that intermittently fail. Quarantine them.
- **Cache hit rate**: Monitor cache effectiveness.
- **Cost per pipeline run**: Track runner costs, especially for self-hosted infrastructure.

### Alerting

- Alert when a main branch pipeline fails.
- Alert when pipeline duration exceeds the 95th percentile.
- Alert when runner capacity is constrained and queue times spike.
- Send pipeline failure notifications to the team channel, not just the committer.

---

## Documentation Requirements

Every CI/CD pipeline must include documentation.

### In-Repository Documentation

- A `CONTRIBUTING.md` or similar file must describe how CI/CD works for the project.
- Document how to run the pipeline locally.
- Document environment variables and secrets the pipeline requires.
- Document the deployment process, including manual steps if any.

### Pipeline Comments

- Comment non-obvious pipeline logic inline in YAML files.
- Document why a step exists, not what it does (the YAML itself describes the what).
- Document workarounds with links to the issue they address.

```yaml
# We split test shards manually because the test framework doesn't support
# automatic sharding. See https://github.com/org/repo/issues/123
- name: Run test shard 1
  run: npm test -- --shard=1/3
```

### Runbooks

- Maintain a runbook for common pipeline failures and their resolutions.
- Include rollback procedures in the deployment runbook.
- Update runbooks when pipeline behavior changes.

---

## Pipeline Anti-Patterns to Avoid

- **Snowflake pipelines**: Every project should follow the same pipeline structure with minimal customization.
- **Manual gates everywhere**: Automate quality gates. Reserve manual approval for production deployment only.
- **Long-running pipelines**: If CI takes more than 15 minutes, investigate and optimize.
- **Ignoring flaky tests**: Quarantine or fix flaky tests immediately. Never retry-and-ignore.
- **Secrets in code**: Never hardcode secrets. Always use the platform's secret management.
- **Pipeline drift**: Keep pipeline definitions consistent across projects using templates or shared workflows.
- **No timeout**: Every job and long-running step must have a timeout.
- **Over-triggering**: Use path filters and branch filters to avoid running pipelines unnecessarily.
