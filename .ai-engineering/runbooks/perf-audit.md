---
runbook: perf-audit
purpose: provider-side performance and complexity reporting
host_adapters:
  github_workflow: ai-eng-perf-audit
provider_scope:
  github: issues
  azure_devops: work_items
feature_policy: read-only
hierarchy_policy: may create user stories under features and tasks under user stories
outputs:
  local_files: generated_artifacts_only
  provider_updates: comments, writable fields, optional follow-up work items
handoff:
  lifecycle: ready
  local_execution: manual only
---

# Runbook: Performance Audit

## Purpose

Collect performance-adjacent evidence such as duplication and complexity
signals, store the machine artifacts, and surface the result in the external
provider without directly implementing changes.

## Host Adapter

- GitHub workflow adapter: `.github/workflows/ai-eng-perf-audit.md`

## Provider Actions

- comment or create provider-native follow-up work when thresholds are exceeded
- enrich writable provider fields if available
- never mutate feature-level records

## Guardrails

- analysis and reporting only
- generated artifacts are allowed; source-code changes are not
- any new provider-native work must respect hierarchy policy

## Procedure

1. Run duplication analysis.
2. Run complexity analysis.
3. Persist machine-readable reports as artifacts.
4. Compare current findings with previous runs when data exists.
5. If thresholds are exceeded, create or update provider-native follow-up work within the allowed hierarchy.
6. Emit a concise summary with top offenders and next recommended actions.

## Output

- artifact reports for trend analysis
- provider-native summary or follow-up work when warranted
