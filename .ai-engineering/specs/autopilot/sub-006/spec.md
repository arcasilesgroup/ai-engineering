---
id: sub-006
parent: spec-084
title: "Review Architecture Refresh and Adversarial Validation"
status: planned
files:
  - .agents/skills/review/SKILL.md
  - .agents/skills/review/handlers/review.md
  - .agents/skills/review/handlers/find.md
  - .agents/skills/review/handlers/learn.md
  - .agents/agents/ai-review.md
  - .claude/skills/ai-review/SKILL.md
  - .claude/skills/ai-review/handlers/review.md
  - .claude/skills/ai-review/handlers/find.md
  - .claude/skills/ai-review/handlers/learn.md
  - .claude/agents/ai-review.md
  - .github/skills/ai-review/SKILL.md
  - .github/skills/ai-review/handlers/review.md
  - .github/skills/ai-review/handlers/find.md
  - .github/skills/ai-review/handlers/learn.md
  - .github/agents/review.agent.md
  - src/ai_engineering/templates/project/.agents/skills/review/
  - src/ai_engineering/templates/project/.claude/skills/ai-review/
  - src/ai_engineering/templates/project/.github/skills/ai-review/
  - scripts/sync_command_mirrors.py
  - src/ai_engineering/validator/categories/mirror_sync.py
  - tests/unit/test_sync_mirrors.py
  - tests/unit/test_template_skill_parity.py
  - tests/unit/test_agent_schema_validation.py
depends_on: []
---

# Sub-Spec 006: Review Architecture Refresh and Adversarial Validation

## Scope
Refresh `review` so the skill becomes canonical, the agent becomes a thinner wrapper, and the architecture follows the useful structural patterns from `review-code`: explicit specialist Markdown prompts, one primary review handler, backend alongside frontend, `normal` and `--full` profiles, and a `finding-validator` stage that evaluates all findings in both profiles. Remove `find` and `learn` from the review surface entirely and propagate the new contract across all mirrors and runtime surfaces.

## Exploration

### Existing Files

- The current canonical review skill still mixes `review`, `find`, and `learn`, so the surface is broader than the approved direction.
- The current review agent overlaps substantially with the skill and adds ambiguity about which contract is canonical.
- Existing mirror and template propagation already runs through `.claude` as canonical source and `scripts/sync_command_mirrors.py`, so the final design has to land across all mirrors and template copies together.
- The current handler tree includes `find` and `learn` files that now need to be removed or rewritten so stale surfaces do not survive.
- `review-code` provides the inspiration pattern: detailed specialist Markdown prompts, context-explorer structure, and a finding validator that challenges findings instead of only emitting them.

### Patterns and Constraints

- Keep a single primary review handler.
- Make the skill canonical and the agent thin.
- Narrow `review` to review only; `find` and `learn` leave the surface entirely.
- `normal` runs the full specialist roster through three fixed macro-agents.
- `--full` runs one specialist per agent.
- `finding-validator` runs in both profiles and validates all findings.

### Risks

- Stale `find` and `learn` references can survive in mirrors and templates if not removed in one pass.
- A richer specialist architecture can drift quickly unless sync and parity tests are updated alongside it.
- If the agent keeps extra promises, the skill-vs-agent confusion will remain even after prompt cleanup.
