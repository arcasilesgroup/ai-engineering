---
name: pr-review
schedule: "0 */4 * * *"
environment: worktree
layer: reporting
owner: operate
requires: [gh]
---

# PR Review

## Prompt

Review open PRs that have been waiting for review for more than 4 hours. Classify findings into blockers (comment on PR) and improvements (create issues for the executor pipeline).

### Phase 1 — Fetch + Filter

1. Fetch open PRs: `gh pr list --state open --json number,title,createdAt,reviewDecision,labels,additions,deletions,changedFiles,headRefName --limit 20`.
2. Filter: PRs without any review and created > 4 hours ago.
3. Skip PRs labeled `skip-ai-review` or already labeled `ai-reviewed`.

### Phase 2 — Analyze

4. For each qualifying PR (max 5 per run):
   - Read the diff: `gh pr diff <number>`.
   - Analyze for:
     - **Security**: hardcoded secrets, injection risks, unsafe patterns.
     - **Breaking changes**: API signature changes, removed exports, behavioral changes.
     - **Quality**: complexity, duplication, naming conventions.
     - **Testing**: are new/changed functions covered by tests?
     - **Standards compliance**: does it follow `.ai-engineering/standards/`?

### Phase 3 — Classify Findings

5. Classify each finding into one of two categories:

   | Category | Criteria | Action |
   |----------|----------|--------|
   | **Blocker** | Security risk, breaking change, data loss, gate violation | Comment on PR (blocks merge) |
   | **Improvement** | Quality uplift, missing tests, naming, refactor opportunity, standards drift | Create GitHub Issue (feeds executor) |

### Phase 4 — Act on Blockers

6. If blockers found:
   - Post a review comment on the PR with blockers organized by severity.
   - Format: `## 🚫 Blockers` → list each with file:line, description, suggested fix.
   - Add label `has-blockers` to the PR.

### Phase 5 — Create Issues for Improvements

7. For each improvement finding:
   - Check if a GitHub Issue already exists (search by title pattern to avoid duplicates).
   - If no existing issue, create one:
     - Title: `[pr-review] <category>: <brief description> in <file>` .
     - Body: include PR reference (`#<pr-number>`), file:line, description, suggested approach, and link to diff context.
     - Labels: `agent-ready`, `needs-triage`, and priority label:
       - Missing test coverage → `p2-high`.
       - Standards drift → `p3-normal`.
       - Refactor opportunity → `p3-normal`.
     - This creates a traceable work item that the **executor runbook** picks up → spec → implement → PR.
   - Maximum 3 issues per PR (avoid noise — pick the highest-impact improvements).

### Phase 6 — Summary

8. Post a summary review comment on the PR:
   - Blockers count (if any).
   - Improvement issues created (with issue number links).
   - If no findings: "Automated review: no issues found."
9. Add label `ai-reviewed` to the PR.

## Feedback Loop

This runbook feeds directly into the executor pipeline:

```
pr-review → creates issues (agent-ready)
     ↓
daily-triage → prioritizes
     ↓
executor → picks issue → spec → build → PR → auto-merge
```

Comments alone are ephemeral — they vanish when the PR merges. Issues persist in the backlog, get prioritized, and become traceable specs with full execution context.

## Context

- Uses: quality skill (review mode), security skill (static mode).
- Reads: `.ai-engineering/standards/` for code standards.
- Creates: GitHub Issues that feed into `executor` and `daily-triage` runbooks.
- References: `skills/work-item/SKILL.md` for issue definition standard.

## Safety

- Analysis + comments + issue creation. Never approve or request changes.
- Do NOT modify PR code or push to PR branches.
- Do NOT merge PRs.
- Maximum 5 reviews per run.
- Maximum 3 improvement issues per PR (throttle to avoid noise).
- Skip PRs labeled `skip-ai-review`.
- Skip PRs already labeled `ai-reviewed`.
- Do NOT create duplicate issues — always search first.
