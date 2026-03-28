---
runbook: weekly-health
purpose: provider-side framework health reporting
host_adapters:
  github_workflow: ai-eng-weekly-health
provider_scope:
  github: issues
  azure_devops: work_items
feature_policy: read-only
hierarchy_policy: may create user stories under features and tasks under user stories
outputs:
  local_files: none
  provider_updates: issue_or_work_item_report, comments, writable fields
handoff:
  lifecycle: ready
  local_execution: manual only
---

# Runbook: Weekly Health

## Purpose

Run framework health checks, summarize the result in the external provider, and
leave a durable health report for later intake or follow-up. This runbook is
provider-native and reporting-only.

## Host Adapter

- GitHub workflow adapter: `.github/workflows/ai-eng-weekly-health.md`

## Provider Actions

- create or update a weekly health report item
- close or supersede older reports when policy allows
- comment the changes made by the runbook
- never write local spec or plan files

## Guardrails

- do not mutate feature-level records
- report partial results instead of failing the whole runbook
- local implementation and remediation remain separate follow-up work

## Procedure

1. Run framework health checks such as `ai-eng doctor --json`.
2. Run content-integrity validation such as `ai-eng validate --json`.
3. Gather relevant delivery metrics if available.
4. Summarize PASS/WARN/FAIL by category.
5. Create or update the provider-native report item with the findings, recommendations, and any writable metadata fields supported by the configured provider.
6. Close or supersede older weekly reports when the host policy allows it.

## Output

- provider-native weekly health report
- console summary for the run
