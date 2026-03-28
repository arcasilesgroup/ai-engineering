---
total: 3
completed: 3
---

# Plan: sub-004 README and Generated Topology Documentation

## Plan

- [x] T-4.1 Rewrite the root `README.md` around the actual framework surface.
  Done when: the root README reflects current counts, real platform mirrors, runbook behavior, update UX, and the generated `.ai-engineering/` topology users interact with.

- [x] T-4.2 Rewrite `.ai-engineering/README.md` as the topology and ownership guide.
  Done when: it explains framework-managed, team-managed, and stateful directories, including lazy folders and skill-created artifacts, using the final runtime contracts from the dependent streams.

- [x] T-4.3 Cross-check both READMEs against the final repository shape.
  Done when: the two documents agree on counts, ownership semantics, and generated-directory descriptions without stale or aspirational text.

## Imports

- `runbook_contract_schema` from `sub-001`
- `update_tree_preview_contract` from `sub-002`
- promoted context layout from `sub-003`
- `verify-contract-v2` from `sub-005`
- `review_skill_contract` from `sub-006`

## Exports

- updated root README contract
- updated `.ai-engineering/README.md` topology guide

## Self-Report
- Rewrote the root README around the real 2026 framework surface: provider mirrors, runbook contracts, review/verify behavior, and the tree-based update preview.
- Rewrote `.ai-engineering/README.md` as a topology guide that distinguishes seeded, generated, and lazy directories, and mirrored the same content into the install template.
- Cross-checked the documents against the live repository shape, including the GitHub Copilot skill exception for `analyze-permissions`.
