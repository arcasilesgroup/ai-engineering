# GitHub Actions Standards

These standards govern how an AI coding assistant writes, maintains, and optimizes GitHub Actions workflows. Follow these patterns for every GitHub Actions workflow you create or modify.

---

## Workflow Structure

### Triggers

Define triggers explicitly. Never use a broad trigger like `on: push` without branch or path filters.

```yaml
name: CI

on:
  push:
    branches: [main]
    paths-ignore:
      - '*.md'
      - 'docs/**'
  pull_request:
    branches: [main]
    paths-ignore:
      - '*.md'
      - 'docs/**'
```

#### Trigger Rules

- Use `push` triggers for the main branch to run CI after merge and for deployment workflows.
- Use `pull_request` triggers for pre-merge validation.
- Use `workflow_dispatch` to allow manual execution for any workflow that might need on-demand runs.
- Use `schedule` with cron syntax for periodic tasks (dependency updates, nightly builds, stale cache cleanup).
- Use `workflow_call` for reusable workflows invoked by other workflows.
- Use `release` triggers for publish or packaging workflows tied to GitHub Releases.
- Avoid `push` triggers on all branches. Filter to specific branches.
- Use `paths` and `paths-ignore` to skip workflows when only irrelevant files change.

### Jobs and Steps

```yaml
jobs:
  build:
    name: Build and Test
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read
    steps:
      - name: Checkout repository
        uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1

      - name: Setup Node.js
        uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test
```

#### Job Rules

- Every job must have a `timeout-minutes` value.
- Every job must declare `permissions` explicitly. Never rely on the default token permissions.
- Use `runs-on: ubuntu-latest` unless the project requires a specific OS or architecture.
- Give every job and step a descriptive `name`.
- Keep steps small and focused. One step should do one thing.

---

## Reusable Workflows

Use reusable workflows to share pipeline logic across repositories. Define them with `workflow_call`.

### Defining a Reusable Workflow

```yaml
# .github/workflows/reusable-ci.yml
name: Reusable CI

on:
  workflow_call:
    inputs:
      node-version:
        description: 'Node.js version to use'
        required: false
        type: string
        default: '20'
      working-directory:
        description: 'Directory containing package.json'
        required: false
        type: string
        default: '.'
    secrets:
      NPM_TOKEN:
        description: 'NPM authentication token'
        required: false

jobs:
  ci:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read
    defaults:
      run:
        working-directory: ${{ inputs.working-directory }}
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
      - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
          cache-dependency-path: '${{ inputs.working-directory }}/package-lock.json'
      - run: npm ci
      - run: npm test
```

### Calling a Reusable Workflow

```yaml
# .github/workflows/ci.yml
name: CI
on:
  pull_request:
    branches: [main]

jobs:
  ci:
    uses: ./.github/workflows/reusable-ci.yml
    with:
      node-version: '20'
    secrets:
      NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### Composite Actions

Use composite actions for reusable sets of steps within a single job.

```yaml
# .github/actions/setup-project/action.yml
name: Setup Project
description: Install dependencies and build the project
inputs:
  node-version:
    description: 'Node.js version'
    required: false
    default: '20'
runs:
  using: composite
  steps:
    - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
      with:
        node-version: ${{ inputs.node-version }}
        cache: 'npm'
    - run: npm ci
      shell: bash
    - run: npm run build
      shell: bash
```

#### When to Use Each

- **Reusable workflows**: When you need to share entire jobs or stages across repositories.
- **Composite actions**: When you need to share a sequence of steps within a single job.

---

## Matrix Strategy

Use matrix strategies to test across multiple platforms, versions, or configurations.

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    timeout-minutes: 15
    strategy:
      fail-fast: true
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        node-version: [18, 20, 22]
        exclude:
          - os: windows-latest
            node-version: 18
        include:
          - os: ubuntu-latest
            node-version: 20
            coverage: true
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
      - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      - run: npm ci
      - run: npm test
      - name: Upload coverage
        if: matrix.coverage
        uses: actions/upload-artifact@5d5d22a31266ced268874388b861e4b58bb5c2f3 # v4.3.1
        with:
          name: coverage
          path: coverage/
```

### Matrix Rules

- Use `fail-fast: true` unless you need results from all combinations (for example, to identify platform-specific failures).
- Use `exclude` to skip invalid or unnecessary combinations.
- Use `include` to add specific combinations with extra properties.
- Keep the matrix small. Every additional dimension multiplies the number of jobs.

---

## Caching

### Dependency Caching with Setup Actions

Prefer built-in caching in setup actions over manual `actions/cache` when available.

```yaml
# Node.js: Built-in cache
- uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
  with:
    node-version: '20'
    cache: 'npm'

# Python: Built-in cache
- uses: actions/setup-python@82c7e631bb3cdc910f68e0081d67478d79c6982d # v5.1.0
  with:
    python-version: '3.12'
    cache: 'pip'

# Go: Built-in cache
- uses: actions/setup-go@cdcb36043654635271a94b9a6d1392de5bb323a7 # v5.0.1
  with:
    go-version-file: 'go.mod'
    cache: true
```

### Manual Caching

Use `actions/cache` when setup actions do not cover your use case.

```yaml
- name: Cache Playwright browsers
  uses: actions/cache@0c45773b623bea8c8e75f6c82b208c3cf94ea4f9 # v4.0.2
  id: playwright-cache
  with:
    path: ~/.cache/ms-playwright
    key: playwright-${{ runner.os }}-${{ hashFiles('package-lock.json') }}

- name: Install Playwright browsers
  if: steps.playwright-cache.outputs.cache-hit != 'true'
  run: npx playwright install --with-deps
```

### Docker Layer Caching

```yaml
- name: Build Docker image
  uses: docker/build-push-action@4a13e500e55cf31b7a5d59a38ab2040ab0f42f56 # v5.1.0
  with:
    context: .
    push: true
    tags: registry.example.com/myapp:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### Caching Rules

- Always use a hash of the lock file in the cache key.
- Include `runner.os` in the cache key when caching OS-specific artifacts.
- Use `restore-keys` for fallback cache hits when the exact key does not match.
- Monitor cache sizes. GitHub limits cache storage per repository.
- Do not cache secrets, credentials, or environment-specific configuration.

---

## Artifact Management

### Uploading Artifacts

```yaml
- name: Upload build artifacts
  uses: actions/upload-artifact@5d5d22a31266ced268874388b861e4b58bb5c2f3 # v4.3.1
  with:
    name: build-${{ github.sha }}
    path: dist/
    retention-days: 7
    if-no-files-found: error
```

### Downloading Artifacts

```yaml
- name: Download build artifacts
  uses: actions/download-artifact@c850b930e6ba138125429b7e5c93fc707a7f8427 # v4.1.4
  with:
    name: build-${{ github.sha }}
    path: dist/
```

### Artifact Rules

- Set `retention-days` to limit storage costs. Use 1-3 days for PR artifacts, 7-30 days for release artifacts.
- Set `if-no-files-found: error` to fail the step if expected artifacts are missing.
- Use unique artifact names that include the SHA or run ID to avoid collisions.
- Use artifacts to pass build outputs between jobs. Do not rebuild in downstream jobs.

---

## Environment Secrets and Variables

### Configuration Hierarchy

```yaml
# Repository-level secret
${{ secrets.API_KEY }}

# Environment-level secret (requires environment in job)
jobs:
  deploy:
    environment: production
    steps:
      - run: deploy --token ${{ secrets.DEPLOY_TOKEN }}

# Repository variable (non-sensitive)
${{ vars.APP_NAME }}
```

### Rules for Secrets

- Never echo or log secrets. GitHub masks them, but do not rely on masking alone.
- Use environment-level secrets for deployment credentials scoped to specific environments.
- Use repository-level secrets for credentials shared across all workflows.
- Rotate secrets on a regular schedule.
- Prefer OIDC authentication over stored secrets for cloud providers.
- Use `environment` protection rules (required reviewers, deployment branches) to gate access to production secrets.

---

## Concurrency Control

Prevent duplicate workflow runs from wasting resources or causing conflicts.

```yaml
# Cancel in-progress runs for the same PR
concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.ref }}
  cancel-in-progress: true
```

### Concurrency Rules

- Use concurrency groups on PR workflows to cancel outdated runs when new commits are pushed.
- Do not use `cancel-in-progress: true` on deployment workflows for the main branch. Canceling a deployment mid-run can leave the environment in a broken state.
- Group by workflow name and branch or PR number.

```yaml
# For deployment workflows: queue instead of cancel
concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: false
```

---

## Job Dependencies and Conditional Execution

### Job Dependencies

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    # ...

  test:
    runs-on: ubuntu-latest
    # ...

  build:
    needs: [lint, test]  # Runs only after both lint and test pass
    runs-on: ubuntu-latest
    # ...

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    # ...
```

### Conditional Execution

```yaml
# Run only on main branch pushes
if: github.ref == 'refs/heads/main' && github.event_name == 'push'

# Run only when specific files change
if: contains(github.event.head_commit.modified, 'src/')

# Run even if a previous job failed (for cleanup or notifications)
if: always()

# Run only if a previous job failed
if: failure()

# Skip for Dependabot PRs
if: github.actor != 'dependabot[bot]'
```

---

## Self-Hosted Runners

### When to Use Self-Hosted Runners

- When builds require specialized hardware (GPUs, ARM architecture, high memory).
- When builds need access to internal network resources.
- When GitHub-hosted runner costs are prohibitive for high-volume pipelines.
- When regulatory requirements mandate builds run on controlled infrastructure.

### Self-Hosted Runner Security

- Use ephemeral runners that are destroyed after each job.
- Never run self-hosted runners on machines that store sensitive data unrelated to CI.
- Restrict self-hosted runner access to private repositories only.
- Use runner groups to control which workflows can use which runners.
- Keep runner software and OS up to date.

```yaml
jobs:
  build:
    runs-on: [self-hosted, linux, gpu]
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
      - run: ./train-model.sh
```

---

## Release Automation

### Semantic Release

```yaml
name: Release
on:
  push:
    branches: [main]

permissions:
  contents: write
  issues: write
  pull-requests: write

jobs:
  release:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - name: Semantic Release
        run: npx semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### Changesets

```yaml
name: Release
on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
      - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - name: Create Release PR or Publish
        uses: changesets/action@aba318e9165b45b7948c60273e0b72fce0a64eb9 # v1.4.7
        with:
          publish: npm run release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

---

## PR Workflows

### Auto-Labeling

```yaml
name: Label PR
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  label:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/labeler@8558fd74291d67161a8a78ce36a881fa63b766a9 # v5.0.0
        with:
          repo-token: ${{ secrets.GITHUB_TOKEN }}
```

### Required Status Checks

Configure these checks as required in branch protection:

- Lint
- Unit tests
- Type checking
- Security scan
- Build

### Auto-Merge for Dependency Updates

```yaml
name: Auto-merge Dependabot
on:
  pull_request:

permissions:
  contents: write
  pull-requests: write

jobs:
  auto-merge:
    if: github.actor == 'dependabot[bot]'
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Enable auto-merge
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Security

### OIDC Authentication

Use OIDC to authenticate with cloud providers. Never store long-lived cloud credentials as secrets.

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      id-token: write  # Required for OIDC
      contents: read
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1

      - name: Authenticate to AWS
        uses: aws-actions/configure-aws-credentials@e3dd6a429d7300a6a4c196c26e071d42e0343502 # v4.0.2
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions
          aws-region: us-east-1

      - name: Authenticate to Azure
        uses: azure/login@6c251865b4e6290e7b78be643ea2d005bc51f69a # v2.1.1
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

### Minimal Permissions

Always set the minimum permissions each job needs. Set restrictive defaults at the workflow level and widen per job.

```yaml
# Restrictive default
permissions:
  contents: read

jobs:
  test:
    permissions:
      contents: read
    # ...

  deploy:
    permissions:
      contents: read
      id-token: write  # Only this job needs OIDC
    # ...
```

### Pinned Action Versions

- Pin every third-party action to a full commit SHA.
- Add a comment with the version tag for readability.
- Use Dependabot or Renovate to keep pinned SHAs up to date.

```yaml
# Good: SHA-pinned with version comment
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1

# Acceptable: Version-pinned for first-party (GitHub-maintained) actions
- uses: actions/checkout@v4

# Bad: Unpinned
- uses: actions/checkout@main
```

---

## Common Workflow Examples

### Full CI Workflow

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.head_ref || github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
      - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck

  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
      - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'
      - run: npm ci
      - run: npm test -- --coverage
      - uses: actions/upload-artifact@5d5d22a31266ced268874388b861e4b58bb5c2f3 # v4.3.1
        with:
          name: coverage
          path: coverage/
          retention-days: 3

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
      - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@5d5d22a31266ced268874388b861e4b58bb5c2f3 # v4.3.1
        with:
          name: build-${{ github.sha }}
          path: dist/
          retention-days: 7
```

### Deploy Workflow

```yaml
name: Deploy
on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  id-token: write

concurrency:
  group: deploy-production
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
      - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@5d5d22a31266ced268874388b861e4b58bb5c2f3 # v4.3.1
        with:
          name: build-${{ github.sha }}
          path: dist/

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    timeout-minutes: 10
    environment: staging
    steps:
      - uses: actions/download-artifact@c850b930e6ba138125429b7e5c93fc707a7f8427 # v4.1.4
        with:
          name: build-${{ github.sha }}
          path: dist/
      - name: Deploy to staging
        run: ./scripts/deploy.sh staging

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    timeout-minutes: 10
    environment: production
    steps:
      - uses: actions/download-artifact@c850b930e6ba138125429b7e5c93fc707a7f8427 # v4.1.4
        with:
          name: build-${{ github.sha }}
          path: dist/
      - name: Deploy to production
        run: ./scripts/deploy.sh production
```
