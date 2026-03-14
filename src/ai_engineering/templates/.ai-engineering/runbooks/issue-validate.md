---
name: issue-validate
schedule: "0 10 * * 3"
environment: worktree
layer: scanner
owner: operate
requires: [gh]
---

# Issue Validator

## Prompt

Scan all open GitHub Issues and verify they comply with the Issue Definition Standard. Create a comment on non-compliant issues.

1. Fetch all open issues: `gh issue list --state open --json number,title,labels,body --limit 100`.
2. For each issue, verify:
   - Title follows pattern: `[type] Brief summary`.
   - Body contains: Description, Priority, Size, Acceptance Criteria.
   - Has at least one priority label (`p1-critical`, `p2-high`, or `p3-normal`).
   - If referencing a spec, the spec URL is clickeable.
3. For non-compliant issues:
   - Add label `incomplete`.
   - Post a comment listing missing fields with a template to fill in.
   - Do NOT close the issue.
4. For compliant issues that had `incomplete` label:
   - Remove the `incomplete` label.
5. Report: count of compliant, non-compliant, and newly fixed.

## Context

- Uses: work-item skill (Issue Definition Standard section).
- Reads: `.ai-engineering/manifest.yml` for issue_standard configuration.

## Safety

- Only adds labels and comments — never modifies issue title or body.
- Do NOT close issues.
- Do NOT assign issues.
- Maximum 20 comments per run.
- Skip issues labeled `exempt-from-standard`.
