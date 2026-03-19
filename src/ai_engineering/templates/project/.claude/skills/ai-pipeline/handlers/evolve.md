# Handler: evolve

Add advanced patterns to existing CI/CD pipelines.

## Process

1. **Read existing pipeline** -- parse current workflow files.
2. **Assess maturity** -- identify which patterns are already applied.
3. **Recommend patterns** -- based on project needs:

## Available Patterns

### CI Result Gate (GitHub Actions)
Single aggregator job replacing 20+ Branch Protection checks. Handles conditional jobs (docs-only PRs, Dependabot, fork contributions) without blocking merge.

### Path-Based Conditional Execution
Use `dorny/paths-filter` to skip expensive jobs on docs-only changes. Define `change-scope` job with output filtering.

### Matrix Strategy
Multi-OS, multi-version testing with `fail-fast: false`. Combine OS and language version dimensions.

### SonarCloud Integration
Add Sonar analysis after test jobs. Configure coverage report paths per stack.

### Merge Queue
Enable `merge_group` event trigger alongside `pull_request`. Batches PRs, runs CI on merged result.

### Reusable Workflows
Extract shared logic into `workflow_call` workflows. Cross-repo with `secrets: inherit`. Max 4 nesting levels.

### Composite Actions
Bundle multi-step logic into `.github/actions/<name>/action.yml`. Require `shell: bash` for composite steps.

### Caching Strategies
Stack-specific cache paths and key patterns: `<tool>-<os>-<lockfile-hash>`. Always provide `restore-keys`.

### Environment Protection & Deployment
GitHub Environments with approval reviewers. Build-once-deploy-many with artifact promotion.

### Azure Pipelines: Template Composition
Central template repository with `resources.repositories`. Manager pattern: build-manager, deploy-manager, security-manager, artifact-manager.

### Azure Pipelines: Deployment Strategies
Rolling (VM batches), Canary (incremental traffic), Blue-Green (slot swap). Each with health checks and rollback.

## Output

- Updated workflow files with new patterns.
- Validation report (`actionlint`).
- Migration notes for any breaking changes.
