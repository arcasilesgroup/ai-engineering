# Delivery and Platform Patterns

On-demand reference for CI/CD generation, deployment, and platform operations.

## GitHub Actions

### Workflow Structure

- Trigger on `push` (main) and `pull_request` for CI.
- Use `workflow_dispatch` for manual deployment triggers.
- Reusable workflows in `.github/workflows/` with `workflow_call`.
- Composite actions in `.github/actions/<name>/action.yml` for shared steps.
- Matrix strategy for multi-stack, multi-OS testing.

### Secrets and Variables

- Secrets: `${{ secrets.NAME }}` — never logged, masked in output.
- Variables: `${{ vars.NAME }}` — visible in logs, for non-sensitive config.
- Environment-scoped secrets for deployment targets.
- Use OIDC for cloud authentication (GitHub → Azure, AWS, GCP).

### Caching

- `actions/cache` for `node_modules`, `.venv`, `~/.cargo`, `~/.nuget`.
- Key on lockfile hash: `hashFiles('**/package-lock.json')`.
- Restore keys for partial cache hits.

### Required Checks

- Branch protection: require status checks (CI workflow) before merge.
- Require up-to-date branches before merging.
- Require PR reviews (minimum 1).

## Azure Pipelines

### Pipeline Structure

- `azure-pipelines.yml` at repo root or `pipelines/` directory.
- Stages: `Build` → `Test` → `Security` → `Deploy` with environment approvals.
- Templates in `pipelines/templates/` for reusable steps.
- Variable groups for environment-specific config.

### Templates

```yaml
# pipelines/templates/build.yml
parameters:
  - name: stack
    type: string
steps:
  - script: echo "Building ${{ parameters.stack }}"
```

### Environments

- Dev: auto-deploy on PR merge.
- Staging: auto-deploy, manual approval gate for production.
- Production: require approval from designated approvers.

### Service Connections

- Use workload identity federation (not client secrets).
- Scope to specific resource group and subscription.
- Rotate credentials on schedule.

## Railway

### Configuration

- `railway.toml`: `[build]` and `[deploy]` sections.
- `nixpacks.toml` for custom build configuration.
- Health checks: `healthcheckPath = "/health"`, `healthcheckTimeout = 5`.
- Volumes for persistent data (databases, file storage).

### Deployment

- Auto-deploy from connected Git branch.
- Preview environments for PRs.
- Environment variables via Railway CLI or dashboard.
- `railway up` for manual deployments.

## Cloudflare Workers/Pages

### Workers

- `wrangler.toml`: name, compatibility date, bindings (KV, D1, R2, Queues).
- Module syntax: `export default { async fetch(request, env, ctx) {} }`.
- Deploy: `wrangler deploy` or Git-connected auto-deploy.
- Local dev: `wrangler dev` with hot reload.

### Pages

- Connect to Git repo for automatic build and deploy.
- `_headers` and `_redirects` files for routing rules.
- Functions in `functions/` directory for server-side logic.
- Build configuration in dashboard or `wrangler.toml`.

### Bindings

- KV: key-value storage. `env.MY_KV.get(key)`, `env.MY_KV.put(key, value)`.
- D1: SQL database. `env.MY_DB.prepare(sql).bind(params).run()`.
- R2: object storage. S3-compatible API.
- Queues: async message processing.

## Vercel

### Configuration

- `vercel.json`: rewrites, redirects, headers, environment variables.
- Framework auto-detection (Next.js, Astro, SvelteKit, etc.).
- Preview deployments for every PR.
- Production deploys from main branch.

### Environment Variables

- Set in Vercel dashboard (Development, Preview, Production scopes).
- Reference via `process.env.NAME` at build time.
- Use Vercel CLI: `vercel env add NAME`.

## Netlify

### Configuration

- `netlify.toml`: `[build]` command and publish directory, `[[redirects]]`, `[[headers]]`.
- Netlify Functions in `netlify/functions/` directory.
- Deploy previews for PRs.
- Edge Functions for server-side logic at CDN edge.

### Build Settings

```toml
[build]
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "20"
```

## Infrastructure Change Safety

- **Plan before apply**: always preview changes before applying.
- **Blue-green or canary**: for zero-downtime deployments.
- **Rollback strategy**: maintain ability to revert to previous deployment.
- **Health checks**: verify service health after deployment.
- **Monitoring**: alerting on error rate, latency, and resource usage post-deploy.
