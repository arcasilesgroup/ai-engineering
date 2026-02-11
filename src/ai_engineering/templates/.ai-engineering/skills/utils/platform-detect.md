# Platform Detection Utility

## Purpose

Detect repository hosting platform and readiness using deterministic local checks.

## Detection Sequence

1. Read remote URL:

```bash
git remote get-url origin
```

2. Classify provider:

- contains `github.com` -> `github`
- contains `dev.azure.com` or `visualstudio.com` -> `azure-devops`
- otherwise -> `unknown`

3. Validate provider CLI and auth:

```bash
gh --version
gh auth status

az --version
az account show
```

## Output Contract

- provider: `github` | `azure-devops` | `unknown`
- tooling: installed/configured/authenticated/operational per provider
- remediation: command suggestions for missing prerequisites

## Governance Notes

- GitHub is runtime priority in current phase.
- Azure DevOps constraints must remain represented in manifest schema.

## References

- `skills/quality/install-check.md` — uses platform detection for readiness checks.
- `standards/framework/core.md` — provider support model.
