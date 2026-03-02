---
name: install
description: "Post-install/update validation for ai-engineering; use after install, update, or environment setup to confirm operational readiness."
version: 1.0.0
tags: [quality, installation, validation, readiness]
metadata:
  ai-engineering:
    scope: read-only
    token_estimate: 307
---

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

### Platform and Credentials

- platform markers detected (`.github/`, `azure-pipelines.yml`, `sonar-project.properties`).
- `tools.json` state file present and valid (if platform setup has been run).
- stored credentials validated via platform APIs (`ai-eng doctor`).
- Sonar scanner availability reported (optional — silent skip if not configured).

## Output Requirements

- machine-readable JSON summary for automation,
- concise human-readable remediation steps,
- no bypass recommendations.

## References

- `skills/install/references/platform-detect.md` — provider and tooling detection.
- `skills/sonar/SKILL.md` — optional Sonar quality gate validation.
- `standards/framework/core.md` — enforcement requirements.
- `agents/review.md` — verification agent that uses readiness checks.
