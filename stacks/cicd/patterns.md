# CI/CD Patterns

These patterns describe reusable solutions to common CI/CD problems. An AI coding assistant should apply these patterns when building or optimizing pipelines.

---

## Matrix Builds

Use matrix builds to test across multiple dimensions: operating systems, language versions, and configurations.

### When to Use Matrix Builds

- Open source libraries that must support multiple runtime versions.
- Cross-platform applications that must work on Linux, macOS, and Windows.
- Applications that must work with multiple database versions or dependency configurations.

### Matrix Design Principles

- Keep the matrix as small as possible. Every additional dimension multiplies total jobs.
- Use `exclude` to remove invalid or unnecessary combinations.
- Use `include` to add specific combinations with additional properties (such as code coverage on one combination only).
- Use `fail-fast: true` during development to get quick feedback. Disable it in release pipelines where you need all results.

```yaml
# GitHub Actions example
strategy:
  fail-fast: true
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    node: [18, 20, 22]
    exclude:
      # Skip Windows + Node 18 (unsupported combination)
      - os: windows-latest
        node: 18
    include:
      # Collect coverage only on one combination
      - os: ubuntu-latest
        node: 20
        coverage: true
```

```yaml
# Azure Pipelines example
strategy:
  matrix:
    linux-node18:
      vmImage: 'ubuntu-latest'
      nodeVersion: '18'
    linux-node20:
      vmImage: 'ubuntu-latest'
      nodeVersion: '20'
    windows-node20:
      vmImage: 'windows-latest'
      nodeVersion: '20'
  maxParallel: 3
```

---

## Dependency Caching Strategies

Cache dependency installations to avoid downloading packages on every build.

### Cache Key Design

Every cache key must include:
1. The package manager name (to avoid collisions between tools).
2. The operating system (dependencies often differ by OS).
3. A hash of the lock file (to invalidate when dependencies change).

Provide fallback restore keys that match on the package manager and OS, allowing partial cache hits.

### Per-Ecosystem Patterns

#### Node.js (npm)

```yaml
# Cache the npm cache directory, not node_modules
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: npm-${{ runner.os }}-${{ hashFiles('package-lock.json') }}
    restore-keys: |
      npm-${{ runner.os }}-
```

#### Node.js (pnpm)

```yaml
- name: Get pnpm store directory
  id: pnpm-cache
  run: echo "STORE_PATH=$(pnpm store path)" >> $GITHUB_OUTPUT

- uses: actions/cache@v4
  with:
    path: ${{ steps.pnpm-cache.outputs.STORE_PATH }}
    key: pnpm-${{ runner.os }}-${{ hashFiles('pnpm-lock.yaml') }}
    restore-keys: |
      pnpm-${{ runner.os }}-
```

#### Python (pip)

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: pip-${{ runner.os }}-${{ hashFiles('requirements.txt', 'requirements-dev.txt') }}
    restore-keys: |
      pip-${{ runner.os }}-
```

#### Go

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/go/pkg/mod
      ~/.cache/go-build
    key: go-${{ runner.os }}-${{ hashFiles('go.sum') }}
    restore-keys: |
      go-${{ runner.os }}-
```

#### Rust

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.cargo/bin/
      ~/.cargo/registry/index/
      ~/.cargo/registry/cache/
      ~/.cargo/git/db/
      target/
    key: cargo-${{ runner.os }}-${{ hashFiles('Cargo.lock') }}
    restore-keys: |
      cargo-${{ runner.os }}-
```

#### .NET (NuGet)

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.nuget/packages
    key: nuget-${{ runner.os }}-${{ hashFiles('**/*.csproj', '**/packages.lock.json') }}
    restore-keys: |
      nuget-${{ runner.os }}-
```

---

## Docker Build Optimization

### Multi-Stage Builds

Always use multi-stage Docker builds to minimize image size and separate build-time dependencies from runtime.

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --production=false
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine AS production
WORKDIR /app
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
USER appuser
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

### Layer Caching in CI

Order Dockerfile instructions from least-frequently-changed to most-frequently-changed. Copy dependency files before source code.

```dockerfile
# Good: Dependencies cached separately from source
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# Bad: Any source change invalidates the npm ci cache
COPY . .
RUN npm ci
```

### Docker Build Caching in GitHub Actions

```yaml
- uses: docker/setup-buildx-action@v3

- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: |
      registry.example.com/myapp:${{ github.sha }}
      registry.example.com/myapp:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### Docker Build Caching in Azure Pipelines

```yaml
- task: Docker@2
  displayName: 'Build and push'
  inputs:
    containerRegistry: 'myRegistry'
    repository: 'myapp'
    command: 'buildAndPush'
    Dockerfile: '**/Dockerfile'
    tags: |
      $(Build.BuildId)
      latest
    arguments: '--cache-from=type=registry,ref=registry.example.com/myapp:cache'
```

---

## Monorepo Pipelines

### Path Filters

Run only the pipelines relevant to the changed code.

```yaml
# GitHub Actions
on:
  push:
    paths:
      - 'packages/api/**'
      - 'packages/shared/**'  # Shared dependencies
      - 'package.json'
      - 'package-lock.json'
```

```yaml
# Azure Pipelines
trigger:
  paths:
    include:
      - packages/api/**
      - packages/shared/**
```

### Affected Project Detection

For monorepos using Nx, Turborepo, or similar tools, run only affected projects.

```yaml
# Nx affected
- name: Run affected tests
  run: npx nx affected --target=test --base=origin/main --head=HEAD

# Turborepo affected
- name: Run affected builds
  run: npx turbo run build --filter='...[origin/main]'
```

### Monorepo Pipeline Patterns

- **Single pipeline with path filters**: Simple but can lead to many workflow files.
- **Dynamic pipeline generation**: Use a script to detect changed projects and trigger appropriate jobs.
- **Tool-native support**: Use Nx, Turborepo, or Bazel to handle affected detection and execution natively.

```yaml
# Dynamic job generation based on changed files
jobs:
  detect:
    runs-on: ubuntu-latest
    outputs:
      api-changed: ${{ steps.changes.outputs.api }}
      web-changed: ${{ steps.changes.outputs.web }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            api:
              - 'packages/api/**'
            web:
              - 'packages/web/**'

  test-api:
    needs: detect
    if: needs.detect.outputs.api-changed == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/api && npm test

  test-web:
    needs: detect
    if: needs.detect.outputs.web-changed == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/web && npm test
```

---

## Feature Flag Integration

### Pipeline-Based Feature Flags

Use environment variables or build arguments to toggle features in CI/CD.

```yaml
- name: Build with feature flags
  run: npm run build
  env:
    FEATURE_NEW_DASHBOARD: ${{ github.ref == 'refs/heads/main' && 'true' || 'false' }}
```

### Feature Flag Service Integration

Query a feature flag service during deployment to determine which features to activate.

```yaml
- name: Check feature flag
  id: feature-check
  run: |
    FLAG_VALUE=$(curl -s https://flags.example.com/api/flags/new-feature)
    echo "enabled=$FLAG_VALUE" >> $GITHUB_OUTPUT

- name: Deploy with feature configuration
  run: ./deploy.sh
  env:
    NEW_FEATURE_ENABLED: ${{ steps.feature-check.outputs.enabled }}
```

### Rules for Feature Flags in CI/CD

- Deploy code with feature flags disabled by default.
- Enable flags gradually through the feature flag service, not through redeployment.
- Include feature flag cleanup in the pipeline: fail the build if a flag has been fully rolled out for more than 30 days without being removed from code.

---

## Database Migration in CI/CD

### Migration Principles

- Migrations must be idempotent: running them multiple times must not cause errors.
- Migrations must be backward-compatible: the previous application version must work with the new schema.
- Never drop columns or tables in the same deployment that removes the code using them. Separate these into two deployments.

### Migration Pipeline Pattern

```yaml
jobs:
  migrate-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Run migrations
        run: npm run db:migrate
        env:
          DATABASE_URL: ${{ secrets.STAGING_DATABASE_URL }}

      - name: Verify migrations
        run: npm run db:verify
        env:
          DATABASE_URL: ${{ secrets.STAGING_DATABASE_URL }}

  deploy-staging:
    needs: migrate-staging
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Deploy application
        run: ./deploy.sh staging
```

### Two-Phase Migration Pattern

For breaking schema changes, use two deployments:

1. **Phase 1**: Add new columns/tables. Deploy code that writes to both old and new locations. Backfill data.
2. **Phase 2**: After all data is migrated, deploy code that reads and writes only to new locations. Remove old columns/tables.

---

## E2E Testing in Pipelines

### Playwright

```yaml
jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci

      - name: Cache Playwright browsers
        uses: actions/cache@v4
        id: playwright-cache
        with:
          path: ~/.cache/ms-playwright
          key: playwright-${{ runner.os }}-${{ hashFiles('package-lock.json') }}

      - name: Install Playwright browsers
        if: steps.playwright-cache.outputs.cache-hit != 'true'
        run: npx playwright install --with-deps

      - name: Install Playwright system dependencies
        if: steps.playwright-cache.outputs.cache-hit == 'true'
        run: npx playwright install-deps

      - name: Run E2E tests
        run: npx playwright test

      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7
```

### Cypress

```yaml
jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: cypress-io/github-action@v6
        with:
          build: npm run build
          start: npm start
          wait-on: 'http://localhost:3000'
          wait-on-timeout: 60

      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: cypress-screenshots
          path: cypress/screenshots/
```

### E2E Testing Rules

- Run E2E tests in a dedicated job with a generous timeout (20-30 minutes).
- Cache browser binaries to avoid downloading them on every run.
- Always upload test reports and screenshots as artifacts, even on success.
- Use `if: always()` for artifact upload steps so reports are available when tests fail.
- Run E2E tests against a deployed preview environment, not a locally started server, when possible.
- Shard E2E tests across multiple machines for large suites.

```yaml
# Playwright sharding
strategy:
  fail-fast: false
  matrix:
    shard: [1, 2, 3, 4]
steps:
  - run: npx playwright test --shard=${{ matrix.shard }}/4
```

---

## Infrastructure as Code Integration

### Terraform

```yaml
jobs:
  plan:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: '1.7.0'

      - name: Terraform Init
        run: terraform init
        working-directory: infra/

      - name: Terraform Plan
        run: terraform plan -out=tfplan
        working-directory: infra/

      - name: Upload plan
        uses: actions/upload-artifact@v4
        with:
          name: tfplan
          path: infra/tfplan

  apply:
    needs: plan
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3

      - name: Download plan
        uses: actions/download-artifact@v4
        with:
          name: tfplan
          path: infra/

      - name: Terraform Apply
        run: terraform apply -auto-approve tfplan
        working-directory: infra/
```

### Bicep (Azure)

```yaml
- task: AzureCLI@2
  displayName: 'Deploy Bicep template'
  inputs:
    azureSubscription: 'azure-production'
    scriptType: 'bash'
    scriptLocation: 'inlineScript'
    inlineScript: |
      az deployment group create \
        --resource-group myapp-rg \
        --template-file infra/main.bicep \
        --parameters infra/parameters.production.json
```

### IaC Pipeline Rules

- Always run `plan` before `apply`. Never auto-apply without review in production.
- Store Terraform state remotely (Azure Storage, S3, Terraform Cloud).
- Pin provider and module versions.
- Use separate state files per environment.
- Run IaC linting (`tflint`, `checkov`) as part of CI.

---

## Notification Patterns

### Slack Notifications

```yaml
- name: Notify Slack on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "Pipeline failed: ${{ github.workflow }} on ${{ github.ref }}",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Pipeline Failed*\nWorkflow: ${{ github.workflow }}\nBranch: ${{ github.ref_name }}\nCommit: ${{ github.sha }}\n<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Run>"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
    SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK
```

### Microsoft Teams Notifications

```yaml
# Azure Pipelines
- task: InvokeRESTAPI@1
  displayName: 'Notify Teams'
  condition: failed()
  inputs:
    connectionType: 'connectedServiceName'
    serviceConnection: 'teams-webhook'
    method: 'POST'
    body: |
      {
        "@type": "MessageCard",
        "summary": "Pipeline Failed",
        "sections": [{
          "activityTitle": "Pipeline Failed: $(Build.DefinitionName)",
          "facts": [
            { "name": "Branch", "value": "$(Build.SourceBranchName)" },
            { "name": "Build", "value": "$(Build.BuildNumber)" }
          ]
        }]
      }
```

### Notification Rules

- Notify on failure only. Do not send notifications for every successful build.
- Include a direct link to the failed pipeline run in every notification.
- Include the branch name, commit SHA, and committer in failure notifications.
- Use dedicated channels for CI/CD notifications; do not pollute general team channels.
- Send deployment notifications (success and failure) to a deployment-specific channel.

---

## Cost Optimization

### Runner Cost Reduction

- Use spot instances or preemptible VMs for self-hosted runners when builds can tolerate interruption.
- Right-size runner hardware. Do not use large runners for simple lint jobs.
- Use auto-scaling runner pools that scale to zero during off-hours.
- Monitor runner utilization and adjust pool sizes accordingly.

### Build Time Reduction

- Cache everything: dependencies, build outputs, Docker layers, test fixtures.
- Parallelize independent work across jobs.
- Use incremental builds where the build tool supports them.
- Skip unnecessary work with path filters and affected detection.
- Use shallow clones (`fetch-depth: 1`) when full history is not needed.

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 1  # Shallow clone for faster checkout
```

### Storage Cost Reduction

- Set artifact retention periods. Delete PR artifacts after 1-3 days.
- Clean up old container images from registries with lifecycle policies.
- Prune stale caches periodically.
- Use compressed artifacts to reduce storage and transfer time.

### Execution Cost Reduction

- Cancel superseded workflow runs using concurrency groups.
- Skip CI on documentation-only changes using path filters.
- Use `workflow_dispatch` for expensive workflows (performance benchmarks, full E2E suites) instead of running them on every commit.
- Run expensive tests on a schedule (nightly) rather than on every PR, with a manual trigger option for on-demand runs.
