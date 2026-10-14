# Checkpoint 5 · Collect a complete read-only Azure backlog

Goal: The selected Azure backlog level yields a complete inventory of nonterminal work items using process-aware state categories, bounded batch reads and a provable completion condition; otherwise collection fails closed.

Acceptance:
- The synthetic inventory contains every and only nonterminal item for the selected backlog level; parent/child context never adds inventory rows.
- Every request uses an allowlisted method/route, explicit organization/project scope, and batches of at most 200 IDs.
- Missing/unknown work-item state categories, incomplete/error reads, or an unknown/reached `workItemCountLimit` fail without a report.
- Only Azure DevOps Services routes are supported; no tenant/auth query or remote write is performed.

Changed files:
- `skills/ai-triage/references/azure-devops.md`
- `skills/ai-triage/scripts/collect-azure.mjs`
- `skills/ai-triage/scripts/collect-azure.d.mts`
- `tests/triage-azure.unit.spec.ts`
- `tests/triage-azure.integration.spec.ts`

Verify:
- `bun test tests/triage-azure.unit.spec.ts`
- `bun test tests/triage-azure.integration.spec.ts`
- `bun test tests/triage-routing.unit.spec.ts`
- `bun test tests/triage-routing.integration.spec.ts`
- `bun run typecheck`
- `bun run lint`

## Round 1 review

VERDICT: PASS

Findings: none. The collector constrains method/route pairs and carries explicit scope on every request; completeness, state classification, exact batch IDs, and hierarchy-as-context are handled fail-closed. The adapter boundary does not implement or invoke `az devops invoke`; the reference explicitly blocks guessing route mappings. Tests use synthetic data only.
