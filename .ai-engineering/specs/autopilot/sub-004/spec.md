---
id: sub-004
parent: spec-084
title: "README and Generated Topology Documentation"
status: planned
files:
  - README.md
  - .ai-engineering/README.md
depends_on:
  - sub-001
  - sub-002
  - sub-003
  - sub-005
  - sub-006
---

# Sub-Spec 004: README and Generated Topology Documentation

## Scope
Refresh the root README and `.ai-engineering/README.md` so they accurately document the generated tree, the lazy or stateful directories created by skills, ownership rules, and the new review/verify/runbook/update behavior. This sub-spec is intentionally downstream of the runtime surfaces so the docs reflect the real final topology rather than guessing ahead of implementation.

## Exploration

### Existing Files

- `README.md` is currently stale on counts and generated topology details.
- `.ai-engineering/README.md` is also stale on ownership and generated-directory explanations.
- The documentation needs to reflect actual current source-of-truth files such as `src/ai_engineering/state/defaults.py`, `scripts/sync_command_mirrors.py`, and the real template trees instead of outdated folder counts.

### Dependencies

- This stream imports the final runbook contract from `sub-001`.
- It imports the final update-tree UX contract from `sub-002`.
- It imports the promoted shared-context layout from `sub-003`.
- It imports the final verify and review surfaces from `sub-005` and `sub-006`.

### Risks

- If docs land before runtime contracts settle, they will drift immediately.
- Folder counts and ownership language will keep regressing unless the README text is anchored in the real framework topology.
