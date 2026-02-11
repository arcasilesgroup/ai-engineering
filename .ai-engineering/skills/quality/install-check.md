# Install Readiness Validation

## Purpose

Validate that ai-engineering is operational after install/update.

## Required Checks

### Structure

- `.ai-engineering/` exists.
- required state files exist:
  - `install-manifest.json`
  - `ownership-map.json`
  - `sources.lock.json`
  - `decision-store.json`
  - `audit-log.ndjson`

### Hooks

- `pre-commit`, `commit-msg`, and `pre-push` exist and are executable.
- hooks are framework-managed and integrity-verified.

### Tooling

- `gitleaks`, `semgrep`, `pip-audit`, `ruff`, `ty`, and test runner are available.
- `gh` and `az` status are evaluated and reported.

### Provider and Auth

- remote provider is detected from git remote URL.
- provider CLI authentication status is reported.

## Output Requirements

- machine-readable JSON summary for automation,
- concise human-readable remediation steps,
- no bypass recommendations.

## References

- `skills/utils/platform-detect.md` — provider and tooling detection.
- `standards/framework/core.md` — enforcement requirements.
- `agents/verify-app.md` — verification agent that uses readiness checks.
