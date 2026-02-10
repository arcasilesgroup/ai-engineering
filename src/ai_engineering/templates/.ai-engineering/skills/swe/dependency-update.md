# Dependency Update

## Purpose

Structured dependency update skill: audit current dependencies, update safely, test compatibility, and validate security posture. Ensures updates don't introduce vulnerabilities or breaking changes.

## Trigger

- Command: agent invokes dependency-update skill or user requests dependency updates.
- Context: security advisory, outdated packages, version bump, vulnerability scan findings.

## Procedure

1. **Audit** — assess current dependency state.
   - Run `pip-audit` to identify known vulnerabilities.
   - Run `uv pip list --outdated` to identify available updates.
   - Categorize: security-critical, feature updates, patch updates.

2. **Plan updates** — prioritize and sequence.
   - Security vulnerabilities first (critical → high → medium).
   - One dependency at a time for major version bumps.
   - Batch minor/patch updates that are low-risk.
   - Check changelogs for breaking changes.

3. **Update** — apply changes.
   - Update `pyproject.toml` dependency specifications.
   - Run `uv sync` to resolve and lock.
   - For major version changes: review migration guide.

4. **Test** — verify compatibility.
   - Run full test suite: `pytest tests/ -v`.
   - Run type checks: `ty check src/`.
   - Run linter: `ruff check src/`.
   - Verify no regressions in functionality.

5. **Validate security** — re-audit after updates.
   - Run `pip-audit` again to confirm vulnerabilities resolved.
   - Run `semgrep` to check for new security patterns.
   - Verify no new advisories introduced by updates.

## Output Contract

- List of dependencies updated with before/after versions.
- Vulnerability resolution summary.
- Test results confirming compatibility.
- Updated `pyproject.toml` and lock file.

## Governance Notes

- Security-critical updates should not be deferred without explicit risk acceptance in `state/decision-store.json`.
- Never downgrade a dependency to resolve a conflict without documented justification.
- Pin exact versions in lockfile, use compatible ranges in `pyproject.toml`.
- `pip-audit` must pass before push (pre-push gate).

## References

- `standards/framework/stacks/python.md` — required tooling.
- `standards/framework/quality/core.md` — security gate.
- `standards/framework/core.md` — risk acceptance policy.
- `agents/security-reviewer.md` — agent that assesses dependency security.
