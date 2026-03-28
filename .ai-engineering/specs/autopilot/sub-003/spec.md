---
id: sub-003
parent: spec-084
title: "Shared Context Promotion and Ownership Migration"
status: planned
files:
  - .ai-engineering/contexts/
  - src/ai_engineering/templates/.ai-engineering/contexts/
  - src/ai_engineering/state/defaults.py
  - src/ai_engineering/installer/phases/governance.py
  - src/ai_engineering/updater/service.py
  - src/ai_engineering/state/observability.py
  - src/ai_engineering/validator/_shared.py
  - src/ai_engineering/templates/project/AGENTS.md
  - src/ai_engineering/templates/project/CLAUDE.md
  - src/ai_engineering/templates/project/copilot-instructions.md
  - tests/unit/test_state.py
  - tests/unit/installer/test_phases.py
  - tests/integration/test_updater.py
  - tests/unit/test_framework_context_loads.py
  - tests/unit/test_validator.py
depends_on: []
---

# Sub-Spec 003: Shared Context Promotion and Ownership Migration

## Scope
Identify framework-shared guidance that currently lives in team-owned paths and define the framework-managed home for the subset that genuinely improves ai-engineering for downstream users. Align loader references, installer/update ownership rules, and propagation boundaries without weakening the promise that `contexts/team/**` remains user-owned.

## Exploration

### Existing Files

- `.ai-engineering/contexts/team/cli.md` and `.ai-engineering/contexts/team/mcp-integrations.md` currently contain reusable framework guidance, but they only reach the repo because Step 0 blanket-loads `contexts/team/*.md`.
- `.ai-engineering/contexts/team/README.md` and `.ai-engineering/contexts/team/lessons.md` are genuinely team-local and should stay team-managed.
- `src/ai_engineering/templates/.ai-engineering/contexts/team/README.md` and `src/ai_engineering/templates/.ai-engineering/contexts/team/lessons.md` prove the governance template currently seeds only team-local context there.
- `.ai-engineering/contexts/gather-activity-data.md` and `.ai-engineering/contexts/evidence-protocol.md` show the desired framework-managed pattern: root `contexts/*.md` with explicit skill references.
- `src/ai_engineering/state/defaults.py`, `src/ai_engineering/installer/phases/governance.py`, `src/ai_engineering/updater/service.py`, and `src/ai_engineering/validator/_shared.py` already encode the framework-managed vs team-managed ownership boundary.
- `src/ai_engineering/state/observability.py` and `tests/unit/test_framework_context_loads.py` lock current context-load telemetry, so moving shared files out of `team/` changes the declared contract and its tests.

### Promotion Targets

- Promote reusable CLI guidance into `.ai-engineering/contexts/cli-ux.md`.
- Promote reusable MCP guidance into `.ai-engineering/contexts/mcp-integrations.md`.
- Keep `contexts/team/lessons.md` and `contexts/team/README.md` as the only seeded team-owned context artifacts.

### Risks

- Promoting files without updating the loader contract would make them portable but inert.
- Leaving duplicate copies in `team/` and root `contexts/` would create immediate ambiguity.
- Installer and updater tests currently lock a two-file team seed invariant that must not be accidentally expanded.
