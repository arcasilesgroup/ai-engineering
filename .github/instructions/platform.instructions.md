---
applyTo: "**/*.yml,**/*.yaml,**/Dockerfile,**/*.sh,**/*.ps1"
---

# Platform & CI/CD Instructions

## Multi-Platform Support

This project supports both GitHub and Azure DevOps:

### GitHub
- CI/CD via GitHub Actions (`.github/workflows/`)
- PRs via `gh pr create`
- Issues referenced as `#123` or `Closes #123`

### Azure DevOps
- CI/CD via Azure Pipelines (`pipelines/`)
- PRs via `az repos pr create`
- Work items referenced as `AB#123`

## CI/CD Standards

- Never hardcode secrets in pipeline files -- use secret variables or Key Vault
- Always pin action/task versions (never use `@latest`)
- Use reusable templates/workflows for shared logic
- Test pipeline changes in feature branches before merging to main
- Reference `standards/cicd.md` for full conventions

## Shell Scripts

- Always use `#!/usr/bin/env bash`
- Always use `set -euo pipefail`
- Quote all variables: `"$VAR"` not `$VAR`
- Use `[[ ]]` for conditionals, not `[ ]`
- Redirect stderr appropriately
