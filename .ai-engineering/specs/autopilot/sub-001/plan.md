---
total: 3
completed: 3
---

# Plan: sub-001 Portable Runbook Automation Contract

## Plan

- [x] T-1.1 Formalize the canonical runbook contract surface across live and template runbooks.
  Done when: each runbook is the single self-contained Markdown source for metadata, provider actions, HITL boundary, and expected outputs, and the old split between procedural runbook and executable wrapper is explicitly collapsed.

- [x] T-1.2 Implement the adapter propagation path from runbooks to host-specific workflow artifacts.
  Done when: GitHub workflow wrapper surfaces derive from the runbook contract instead of inventing their own metadata, and generated `.lock.yml` artifacts remain downstream-only.

- [x] T-1.3 Enforce provider guardrails and integrity checks for the new contract.
  Done when: hierarchy rules, writable-field boundaries, and mirrored/generated integrity checks are covered through validation and regression tests.

## Exports

- `runbook_contract_schema`
- `host_adapter_rules`
- `provider_guardrails`

## Self-Report
- Promoted the three canonical runbooks to self-contained Markdown contracts with explicit provider scope, guardrails, and host-adapter references.
- Simplified the GitHub workflow Markdown files into thin host adapters that point back to the canonical runbooks.
- Added regression coverage for the provider-backed runbooks and confirmed mirror integrity with `python scripts/sync_command_mirrors.py --check`.
