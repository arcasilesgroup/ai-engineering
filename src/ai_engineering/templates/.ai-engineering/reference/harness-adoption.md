# Harness Adoption Guide

This guide covers runtime contracts that already exist in the framework. Root README and getting-started docs should link or summarize this material only after the commands and artifacts are real.

## Adopted Contracts

| Contract | Runtime truth | Adoption guidance |
| --- | --- | --- |
| Task ledger | `.ai-engineering/specs/task-ledger.json` records durable task status, scopes, handoffs, and evidence. | Add or update ledger entries when a slice closes; keep summaries concise and point at build or verify packets. |
| Current summary | `.ai-engineering/specs/current-summary.md` records the latest completed slice and next queue. | Update after verification, not before. |
| Mirror generation | `ai-eng sync-mirrors` owns IDE mirror projections from canonical Claude sources. | Edit canonical sources, then regenerate mirrors; do not hand-edit generated mirror files. |
| Runtime hooks | Hook helper assets are classified as runtime-native or stdlib mirrors. | Preserve stdlib-only helpers when installed hooks must run without package imports. |
| Context packs | Context packs and handoff compacts carry durable references instead of pasted residue. | Add references to canonical artifacts and avoid duplicating large evidence bodies. |
| Verify taxonomy | `ai_engineering.verify.taxonomy` maps check names to stable verification families. | Add stable IDs and standards bindings when a new check family becomes canonical. |
| Legacy retirement | `ai_engineering.standards` serializes deletion families with owner, parity proof, and rollback. | Do not delete a family until its manifest entry is READY and deletion is explicitly allowed. |

## Migration Path

1. Identify the implemented runtime contract that replaces the old surface.
2. Record the replacement owner and parity proof in the retirement manifest.
3. Keep compatibility readers or docs in place until focused tests and structural validation pass.
4. Retire one family at a time with a rollback path.

## Root Documentation Boundary

Root docs are adoption summaries. They should not introduce new framework contracts. When runtime behavior changes, update the framework context first, verify it, then update root docs as a trailing user-facing explanation.