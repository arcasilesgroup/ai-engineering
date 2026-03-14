---
name: dep-check
schedule: "0 4 * * *"
environment: worktree
layer: scanner
owner: operate
requires: [uv, gh]
---

# Dependency Check

## Prompt

Audit all project dependencies for known vulnerabilities. Create a GitHub Issue for each new CVE found.

1. Run `uv run pip-audit --format json` and parse the output.
2. For each vulnerability:
   - Package name, installed version, fixed version (if available), CVE ID, severity.
   - Check if a GitHub Issue already exists (search: `[dep] <package> <CVE>`).
   - If no existing issue, create one.
3. Label: `dependency`, `security`, `needs-triage`.
4. Priority: CVSS >= 9.0 → `p1-critical`, >= 7.0 → `p2-high`, else → `p3-normal`.
5. Title format: `[dep] <package> <version>: <CVE-ID>`
6. Body: include CVE description, severity score, fixed version, upgrade command.

## Context

- Uses: security skill (deps mode).
- Reads: `pyproject.toml` for dependency list.
- Reads: `.ai-engineering/manifest.yml` for enforcement.checks.

## Safety

- Read-only mode: audit and create issues only.
- Do NOT modify `pyproject.toml` or lockfiles.
- Do NOT run `uv lock` or `uv sync`.
- Maximum 10 issues per run.
- Skip CVEs that already have open issues.
