# Autopilot Manifest: spec-084

## Split Strategy
Hybrid by-domain split: one sub-spec per major runtime/documentation surface, keeping implementation concerns isolated while preserving the shared ownership migration dependency.

## Sub-Specs

| # | Title | Status | Depends On | Files (best guess) |
|---|-------|--------|------------|---------------------|
| sub-001 | Portable Runbook Automation Contract | completed | None | `.ai-engineering/runbooks/`, `.github/workflows/`, `.ai-engineering/manifest.yml` |
| sub-002 | Update Tree UX | completed | sub-003 | `src/ai_engineering/updater/service.py`, `src/ai_engineering/cli_commands/core.py`, `tests/` |
| sub-003 | Shared Context Promotion and Ownership Migration | completed | None | `.ai-engineering/contexts/**`, `src/ai_engineering/state/defaults.py`, installer/update logic |
| sub-004 | README and Generated Topology Documentation | completed | sub-001, sub-002, sub-003, sub-005, sub-006 | `README.md`, `.ai-engineering/README.md` |
| sub-005 | Verify Specialist Fan-Out | completed | None | `.agents/skills/verify/**`, `.agents/agents/ai-verify.md`, `src/ai_engineering/verify/**` |
| sub-006 | Review Architecture Refresh and Adversarial Validation | completed | None | `.agents/skills/review/**`, `.agents/agents/ai-review.md`, mirror skill/agent surfaces |

## Outcome

- All 6 sub-specs landed in the main workspace and were reconciled through `python scripts/sync_command_mirrors.py`.
- Documentation, mirrors, ownership changes, runtime changes, and regression tests now agree on the same final surface.

## Totals
- Sub-specs: 6
- Dependency chain depth: 2

## Coverage Traceability

| Parent Concern | Sub-Spec(s) |
|----------------|-------------|
| Portable runbooks and MAS+HITL provider orchestration | sub-001 |
| `ai-eng update` preview tree UX | sub-002 |
| Promotion of framework-shared guidance out of team space | sub-003 |
| README and generated topology docs refresh | sub-004 |
| `verify` architecture and fan-out redesign | sub-005 |
| `review` architecture, specialist prompts, and validator flow | sub-006 |

## Execution Waves

- Wave 1: `sub-001`, `sub-003`, `sub-005`, `sub-006`
- Wave 2: `sub-002`
  - waits for `sub-003` because the preview has to reflect the final ownership and promoted context surface
- Wave 3: `sub-004`
  - waits for all runtime streams so the READMEs describe the actual final topology and command surfaces

## Exports and Imports

| Sub-Spec | Exports | Imports |
|----------|---------|---------|
| `sub-001` | `runbook_contract_schema`, `host_adapter_rules`, `provider_guardrails` | None |
| `sub-002` | `update_tree_preview_contract`, `cli_tree_renderer`, `update_preview_regression_net` | final ownership/path surface from `sub-003` |
| `sub-003` | `.ai-engineering/contexts/cli-ux.md`, `.ai-engineering/contexts/mcp-integrations.md` | None |
| `sub-004` | updated root README, updated `.ai-engineering/README.md` | outputs from `sub-001`, `sub-002`, `sub-003`, `sub-005`, `sub-006` |
| `sub-005` | `verify-contract-v2`, `verify-runtime-v2`, `verify-mirror-coverage` | umbrella verify decisions and current runtime envelope |
| `sub-006` | `review_skill_contract`, `review_specialist_prompt_architecture`, `review_output_contract`, `review_mirror_propagation_requirements` | sync/template patterns and `review-code` references |
