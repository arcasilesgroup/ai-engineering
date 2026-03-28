---
runbook: daily-triage
purpose: provider-side issue triage and hygiene
host_adapters:
  github_workflow: ai-eng-daily-triage
provider_scope:
  github: issues
  azure_devops: work_items
feature_policy: read-only
hierarchy_policy: may create user stories under features and tasks under user stories
outputs:
  local_files: none
  provider_updates: labels, comments, state, writable fields
handoff:
  lifecycle: ready
  local_execution: manual only
---

# Runbook: Daily Triage

## Purpose

Automated issue hygiene in the external work-item provider. This runbook triages
existing backlog items, enriches writable fields, and leaves the board in a
better ready-for-intake state. It does not implement code and it does not write
local `spec.md` or `plan.md`.

## Host Adapter

- GitHub workflow adapter: `.github/workflows/ai-eng-daily-triage.md`

## Provider Actions

- read open issues or work items with their metadata
- add or remove writable labels and fields
- add comments describing what changed on the card
- close only items allowed by provider policy
- never mutate feature-level records

## Guardrails

- features are read-only
- provider actions stop at backlog preparation; local implementation remains manual
- populate relevant writable provider fields when available
- if creating follow-up work, respect manifest hierarchy rules

## Procedure

1. List open issues or work items with title, labels, assignees, updated date, and relevant writable fields.
2. Detect stale or under-specified items.
3. Apply backlog hygiene updates:
   - mark stale items
   - flag missing priority or triage metadata
   - add comments documenting the changes
4. If the provider supports richer fields discovered by board configuration, populate the relevant writable fields rather than relying on labels only.
5. Close only abandoned items that satisfy the provider-side policy.
6. Emit a concise provider-native summary and leave the backlog ready for human or local intake.

## Output

- provider-side updates only
- console summary with counts and notable exceptions
