---
id: sub-001
parent: spec-084
title: "Portable Runbook Automation Contract"
status: planned
files:
  - .ai-engineering/runbooks/
  - src/ai_engineering/templates/.ai-engineering/runbooks/
  - .github/workflows/ai-eng-*.md
  - .github/workflows/ai-eng-*.lock.yml
  - .ai-engineering/manifest.yml
  - .agents/skills/board-discover/SKILL.md
  - .agents/skills/board-sync/SKILL.md
  - scripts/sync_command_mirrors.py
  - src/ai_engineering/validator/_shared.py
depends_on: []
---

# Sub-Spec 001: Portable Runbook Automation Contract

## Scope
Define the canonical portable runbook contract for ai-engineering so a single self-contained Markdown artifact can operate across Codex App Automation, Claude scheduled tasks, GitHub agentic workflows, and manual execution. Keep runbooks provider-native on GitHub Issues and Azure Boards, preserve hierarchy constraints from `manifest.yml`, and treat local `/ai-brainstorm` -> `/ai-plan` -> execution as the post-handoff path rather than something the runbooks implement directly.

## Exploration

### Existing Files

- Current `.ai-engineering/runbooks/*.md` files are mostly procedural Markdown; they are readable but not yet the self-contained executable contract the umbrella spec now requires.
- Host-specific workflow wrappers under `.github/workflows/ai-eng-*.md` currently carry executable metadata that is not yet owned canonically by the runbooks themselves.
- Generated `.github/workflows/ai-eng-*.lock.yml` files are downstream artifacts and must stay derived rather than becoming an alternate source of truth.
- `.ai-engineering/manifest.yml` already encodes the provider, state mappings, and hierarchy rules the new runbook contract must obey.
- `.agents/skills/board-discover/SKILL.md` and `.agents/skills/board-sync/SKILL.md` are already the framework abstractions for provider adaptation and lifecycle syncing.
- `scripts/sync_command_mirrors.py` and `src/ai_engineering/validator/_shared.py` are the obvious enforcement path if the runbook contract introduces mirrored or validated structure.

### Patterns and Constraints

- Keep the runbook as the canonical artifact and make host adapters derive from it.
- Runbooks remain provider-native and may enrich or create work items, but they cannot implement local code or bypass the local `/ai-brainstorm` -> `/ai-plan` path.
- Feature-level work items remain read-only; subordinate user stories and tasks must respect `manifest.yml` hierarchy rules.
- Avoid a dual-source model where the workflow wrapper and the runbook both describe the same behavior differently.

### Risks

- A split source of truth between runbooks and workflow wrappers would immediately reintroduce drift.
- Provider actions can easily overreach unless the hierarchy and writable-field guardrails are enforced centrally.
- Generated workflow artifacts can drift unless their derivation path is explicit and tested.
