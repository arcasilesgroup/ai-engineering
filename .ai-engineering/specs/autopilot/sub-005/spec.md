---
id: sub-005
parent: spec-084
title: "Verify Specialist Fan-Out"
status: planned
files:
  - .agents/skills/verify/SKILL.md
  - .agents/skills/verify/handlers/verify.md
  - .agents/agents/ai-verify.md
  - .claude/skills/ai-verify/SKILL.md
  - .claude/skills/ai-verify/handlers/verify.md
  - .claude/agents/ai-verify.md
  - .github/skills/ai-verify/SKILL.md
  - .github/skills/ai-verify/handlers/verify.md
  - .github/agents/verify.agent.md
  - src/ai_engineering/templates/project/.agents/skills/verify/
  - src/ai_engineering/templates/project/.claude/skills/ai-verify/
  - src/ai_engineering/templates/project/.github/skills/ai-verify/
  - src/ai_engineering/verify/service.py
  - src/ai_engineering/verify/scoring.py
  - src/ai_engineering/cli_commands/verify_cmd.py
  - src/ai_engineering/validator/_shared.py
  - src/ai_engineering/validator/categories/mirror_sync.py
  - tests/unit/test_verify_service.py
  - tests/unit/test_verify_scoring.py
  - tests/unit/test_validator.py
depends_on: []
---

# Sub-Spec 005: Verify Specialist Fan-Out

## Scope
Redesign `verify` into a specialist fan-out surface with `normal` and `--full` profiles, fixed macro-agent grouping in `normal`, original specialist attribution in the output, and evidence-first aggregation without a separate adversarial validator stage. Propagate the resulting contract across mirrors, runtime code, and docs without leaving stale or aspirational verify surfaces behind.

## Exploration

### Existing Files

- Current verify skill files already mention seven specialist modes, but they do not define the new implicit `normal` profile, the explicit `--full` profile, or the fixed two-macro-agent grouping.
- Current verify agent files duplicate and over-promise behavior that the runtime does not implement.
- `src/ai_engineering/verify/service.py` currently supports `quality`, `security`, `governance`, and `platform`, but not the final specialist fan-out contract.
- `src/ai_engineering/verify/scoring.py` has no specialist attribution model yet, so grouped execution cannot report back by original specialist lens.
- `src/ai_engineering/cli_commands/verify_cmd.py` exposes modes directly from the service and currently has no `--full` surface or grouped-specialist rendering.
- Template and mirror surfaces exist under `.agents`, `.claude`, `.github`, and `src/ai_engineering/templates/project/**`; they all need to converge together.

### Patterns and Constraints

- The skill stays canonical and the agent becomes a thin wrapper.
- `normal` must cover the full specialist roster through two fixed macro-agents.
- `--full` must run one specialist per agent.
- Output stays attributed by original specialist in both profiles.
- There is no separate `finding-validator` stage in verify.

### Risks

- Updating prompts without extending runtime code would leave verify aspirational.
- Adding profile support can break callers and tests that currently assume a smaller mode map.
- Mirror validation will likely fail unless all live and template files move in one pass.
