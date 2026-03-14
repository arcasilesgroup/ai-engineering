---
name: scheduled-scan
schedule: "0 2 * * *"
environment: worktree
layer: scanner
owner: operate
requires: [uv, ruff, ty, gitleaks, semgrep]
---

# Scheduled Scan

## Prompt

Run the full quality and security gate for the repository. Execute each check in order. For every finding, create a GitHub Issue with the appropriate label.

1. Run `ai-eng gate all` and capture output.
2. Run `uv run ruff check src/ tests/` — for each error, note file:line and rule.
3. Run `uv run ty check src/` — for each type error, note file:line.
4. Run `gitleaks detect --source .` — for each leak, note file:line.
5. Run `semgrep scan --config auto src/` — for each finding, note rule, severity, file:line.
6. Run `uv run pip-audit` — for each vulnerability, note package, version, CVE.

For each finding:
- Check if a GitHub Issue already exists for this finding (search by title pattern).
- If no existing issue, create one using the Issue Definition Standard from `.ai-engineering/skills/work-item/SKILL.md`.
- Label: `scan-finding`, `needs-triage`, and severity label (`p1-critical` for high/critical, `p2-high` for medium, `p3-normal` for low/info).
- Title format: `[scan] <tool>: <brief description> in <file>`

Do NOT fix any findings. Only detect and report.

## Context

- Uses: scan agent (7 modes), quality skill, security skill.
- Reads: `.ai-engineering/manifest.yml` for enforcement checks.
- Reads: `.ai-engineering/standards/framework/quality/core.md` for thresholds.

## Safety

- Read-only mode: detect and create issues only.
- Do NOT modify source code.
- Do NOT push commits.
- Maximum 20 issues per run (throttle to avoid spam).
- Skip findings that already have open issues.
