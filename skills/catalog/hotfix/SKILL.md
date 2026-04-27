---
name: hotfix
description: Use when production is broken and a fast-track fix is needed — emergency branch from a production tag, abbreviated gates, post-fix audit-trail entry. Trigger for "prod is down", "hotfix", "emergency fix", "page just fired". Cross-links to `incident-respond`.
effort: high
tier: core
capabilities: [tool_use, structured_output]
governance:
  blocking: true
---

# /ai-hotfix

PagerDuty / DreamOps-style emergency flow. Branches from the last
released production tag, applies the minimal fix, runs fast-track gates,
ships, and records a complete audit trail for postmortem.

> Cross-link: pair with `/ai-incident-respond` for incident command,
> communications, and customer-facing status updates.

## When to use

- Production incident with active customer impact
- Severity-1 / severity-2 page from on-call
- Security disclosure requiring same-day patch
- Data corruption requiring stop-the-bleed before postmortem

## NOT for use when

- Bug exists but isn't actively causing impact → normal `/ai-debug`
  + `/ai-pr` flow
- Refactor or "while I'm here" cleanup → use the regular pipeline
- New features → reject and route through `/ai-specify`

## Process

1. **Capture incident ID** — link to PagerDuty / OpsGenie / internal
   tracker. Persist to `.ai-engineering/incidents/<id>.md`.
2. **Branch from production tag** — `git checkout -b hotfix/<id> <last-prod-tag>`,
   not from `main`. Avoids dragging in unreleased work.
3. **Apply minimal fix** — the smallest possible diff that addresses
   the symptom. Defer root cause to postmortem if necessary.
4. **Fast-track gates** (parallel, time-budgeted):
   - Lane A: focused tests (changed-files only) + ruff + gitleaks
   - Lane B: security scan on diff (semgrep, dep-audit)
   - Lane C: smoke tests in shadow environment
5. **Tag and release** — `git tag <version>+hotfix.<id>`; run
   `/ai-release-gate` in expedited mode; deploy.
6. **Cherry-pick to main** — open follow-up PR to merge the fix back
   into `main` so it survives the next release.
7. **Audit-trail entry** — append to `.ai-engineering/incidents/<id>.md`:
   timestamps, decisions, who approved, what was skipped vs default.
8. **Schedule postmortem** — run `/ai-postmortem` within 48 hours.

## Hard rules

- NEVER skip gitleaks on hotfix — secret leaks during incidents are
  common and devastating.
- NEVER include unrelated changes — single-purpose diff only.
- NEVER skip the cherry-pick to main; otherwise the hotfix regresses
  on the next release.
- Every gate skipped is logged in the audit trail with justification.
- Postmortem within 48 hours is mandatory, not optional.

## Common mistakes

- Branching from `main` (drags in unreleased changes)
- Bundling unrelated improvements ("while we're hotfixing…")
- Forgetting the cherry-pick back to main
- Skipping the audit-trail entry — postmortem becomes guesswork
- Treating root cause analysis as part of hotfix instead of postmortem
