---
spec: "037"
approach: "mixed"
---

# Plan — PR Workflow Hardening

## Architecture

### New Files

| File | Purpose |
|---|---|
| `.ai-engineering/context/specs/037-pr-workflow-hardening/spec.md` | Define problem, scope, acceptance criteria |
| `.ai-engineering/context/specs/037-pr-workflow-hardening/plan.md` | Define implementation architecture and phases |
| `.ai-engineering/context/specs/037-pr-workflow-hardening/tasks.md` | Track phased execution and progress |

### Modified Files

| File | Purpose |
|---|---|
| `src/ai_engineering/commands/workflows.py` | Enforce deterministic PR create-or-update flow |
| `src/ai_engineering/vcs/pr_description.py` | Harden PR body generation/update contract |
| `.ai-engineering/skills/pr/SKILL.md` | Clarify upsert and payload handling rules |
| `.github/prompts/ai-pr.prompt.md` | Keep prompt behavior aligned with canonical PR contract |
| `.github/prompts/pr.prompt.md` | Remove semantic drift with PR prompt surface |
| `tests/integration/test_command_workflows.py` | Add PR create/update regression coverage |
| `tests/unit/test_vcs_providers.py` | Validate provider-level PR upsert behavior |

### Mirror Copies

| Canonical | Mirror |
|---|---|
| `.ai-engineering/skills/pr/SKILL.md` | `src/ai_engineering/templates/.ai-engineering/skills/pr/SKILL.md` |
| `.github/prompts/ai-pr.prompt.md` | `src/ai_engineering/templates/project/prompts/ai-pr.prompt.md` |
| `.github/prompts/pr.prompt.md` | `src/ai_engineering/templates/project/prompts/pr.prompt.md` |

## File Structure

- `.ai-engineering/context/specs/037-pr-workflow-hardening/`
  - `spec.md`
  - `plan.md`
  - `tasks.md`

## Session Map

### Phase 0 — Scaffold and Activate [S]
- Create spec directory and core lifecycle docs.
- Activate `_active.md` and link product contract.

### Phase 1 — Contract Parity Baseline [M]
- Build a parity matrix: skill vs manifest vs workflow implementation.
- Identify authoritative PR behavior and drift points.

### Phase 2 — Deterministic PR Upsert Path [L]
- Implement existing-PR detection by head branch.
- Route create vs append-update through one deterministic command path.

### Phase 3 — Body Reliability Hardening [M]
- Enforce file-based body payload handling.
- Preserve structured body sections in both create and update paths.

### Phase 4 — Validation and Governance Closure [L]
- Add regression tests for create/update/automerge behavior.
- Run lint, type, tests, and governance validation.
- Prepare closure artifacts (`done.md`) when AC are met.

## Patterns

- Contract-first: skill/manifest/workflow parity before behavior changes.
- Deterministic branching: explicit create-path and update-path decisions.
- Append-only updates: never overwrite existing PR body content.
- Mirror parity: keep canonical and template mirrors synchronized.
- Safety-first validation: pass security, quality, and governance gates before PR.
