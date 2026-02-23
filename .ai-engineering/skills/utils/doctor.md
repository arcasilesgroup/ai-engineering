---
name: doctor
version: 1.0.0
category: utils
tags: [diagnostics, environment, health-check, readiness]
---

# Environment Doctor

## Purpose

Unified environment diagnostics that validates all prerequisites for governed operations. Checks binary availability, git hook installation, git state, governance health, and stack detection. Produces a categorized PASS/WARN/FAIL report.

## Trigger

- Command: agent invokes doctor skill or user requests environment check.
- Context: new session setup, troubleshooting gate failures, post-install verification, CI environment validation.

## When NOT to Use

- **Post-install validation of ai-engineering package** — use `quality:install-check` instead. Doctor checks the development environment; install-check validates the installed package.
- **Full release readiness** — use `quality:release-gate` instead.
- **Governance content integrity** — use `govern:integrity-check` instead. Doctor checks tool presence; integrity-check validates content correctness.

## Procedure

### Category 1: Required Binaries

1. **Check common tooling** — verify these binaries are in PATH:
   - `git` — version control.
   - `gitleaks` — secret detection.
   - `semgrep` — SAST scanning.

2. **Check stack-specific tooling** — detect active stacks from `install-manifest.json` and verify:
   - Python: `uv`, `ruff`, `ty`, `pip-audit`.
   - .NET: `dotnet`.
   - Next.js: `node`, `npm`.

3. **Check VCS CLI** — verify provider tools:
   - `gh` (GitHub) — check `gh auth status`.
   - `az` (Azure DevOps) — check if configured (when enabled).

4. **Report per binary**: PASS (found + version) | FAIL (not found) | WARN (found but not authenticated).

### Category 2: Git Hooks

5. **Verify hook installation** — check `.git/hooks/` for:
   - `pre-commit` — exists and is executable.
   - `commit-msg` — exists and is executable.
   - `pre-push` — exists and is executable.

6. **Verify hook content** — confirm hooks call the ai-engineering gate runner (not empty stubs).

7. **Report per hook**: PASS (installed + functional) | FAIL (missing or empty).

### Category 3: Git State

8. **Check current branch** — report branch name and whether it is a protected branch (main/master).
9. **Check remote** — verify `origin` remote exists and is reachable.
10. **Check working tree** — clean or dirty (list modified files if dirty).

### Category 4: Governance Health

11. **Check active spec** — read `context/specs/_active.md`, report active spec or "none".
12. **Check decision store** — verify `state/decision-store.json` exists and is valid JSON.
13. **Check audit log** — verify `state/audit-log.ndjson` exists.

### Category 5: Stack Detection

14. **Detect active stacks** — check for stack indicators:
    - Python: `pyproject.toml` or `setup.py` present.
    - .NET: `*.csproj` or `*.sln` present.
    - Next.js: `next.config.*` or `package.json` with next dependency present.
15. **Cross-reference with manifest** — compare detected stacks against `install-manifest.json`.

### Summary

16. **Aggregate results** — produce summary table:

```
Category            Status
──────────────────  ──────
Required Binaries   PASS (8/8)
Git Hooks           PASS (3/3)
Git State           WARN (dirty working tree)
Governance Health   PASS (3/3)
Stack Detection     PASS (Python detected)
──────────────────  ──────
Overall             PASS (with warnings)
```

## Output Contract

- Per-category PASS/WARN/FAIL status with details.
- Summary table with overall verdict.
- Remediation commands for any FAIL items (e.g., `brew install gitleaks`, `uv tool install ruff`).

## Governance Notes

- Doctor is read-only — it does not install, configure, or modify anything.
- FAIL in Required Binaries or Git Hooks means governed operations will fail.
- WARN items do not block operations but indicate suboptimal state.
- This skill complements but does not replace `quality:install-check` (which validates package installation, not environment).

## References

- `standards/framework/core.md` — required tooling and enforcement rules.
- `manifest.yml` — tooling baseline and enforcement checks.
- `skills/quality/install-check.md` — package installation validation.
- `skills/utils/platform-detect.md` — VCS provider detection.
