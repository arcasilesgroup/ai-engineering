---
name: daily-triage
schedule: "0 8 * * *"
environment: worktree
layer: triage
requires: [gh]
---

# Daily Triage

## Prompt

Classify and prioritize all issues labeled `needs-triage`. Apply priority labels and assign to the appropriate milestone.

1. Fetch issues: `gh issue list --label needs-triage --state open --json number,title,labels,body --limit 50`.
2. For each issue, classify using this priority hierarchy:
   - Security findings → `p1-critical`
   - Bug reports → `p2-high`
   - Feature requests → `p3-normal`
   - Performance issues → `p3-normal` (unless in hot path → `p2-high`)
   - Test coverage gaps → `p3-normal`
   - Architecture improvements → `p3-normal`
   - DX improvements → `p3-normal`
3. Apply the priority label.
4. Remove the `needs-triage` label.
5. If the issue body contains "agent-ready" or the task is automatable, add label `agent-ready`.
6. Size each issue: examine scope, count affected files, estimate effort → add size label.
7. Report: list of triaged issues with assigned priority.

## Context

- Uses: work-item skill (triage mode).
- Reads: `.ai-engineering/manifest.yml` for priority hierarchy.

## Safety

- Only modifies labels — never modifies issue title or body.
- Do NOT close issues.
- Do NOT auto-assign to humans.
- Maximum 50 issues per run.
- If unsure about priority, default to `p3-normal` and add `needs-review`.
