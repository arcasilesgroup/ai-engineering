# Review · git-worktree-flow #7 — the smallest piece of each outside habit

## Goal
The smallest text additions: `skills/ai-audit-code/SKILL.md` gains the `file:line` citation discipline, a "Looks bad but is fine" section and the anti-false-positive plus verify-before-deleting guardrails; `skills/ai-security/SKILL.md` gains "no severity without an attack path" and the split between the hunter, the proof-of-concept and the validator. Nothing else from the three attachments is imported.

## Acceptance
1. `ai-audit-code` cites `file:line` and carries a "Looks bad but is fine" section.
2. `ai-security` states that no severity is given without an attack path and separates the hunter/PoC from the validator.
3. No other content from the three attachments is imported; the embedded assets are in sync.

## changed_files
- `skills/ai-audit-code/SKILL.md`
- `skills/ai-security/SKILL.md`
- `src/assets.ts` (regenerated)

## Verify commands
- `rg -q 'Looks bad but is fine' skills/ai-audit-code/SKILL.md`
- `rg -q 'file:line' skills/ai-audit-code/SKILL.md`
- `rg -q 'attack path' skills/ai-security/SKILL.md`
- `bun test tests/skills.spec.ts`
- `bun test tests/embed-canon.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun run build`

## Context the reviewer should know
This is the last checkpoint, and the only one whose source is outside the repository: three skills a colleague passed in were reviewed during the design and only their best habits were kept. Attack the additions on two axes the gates cannot: whether a rule added here contradicts a rule the same file already states, and whether anything crept in beyond what the plan named. A skill that grows a second, softer version of a rule it already enforces is worse than one that grew nothing.
