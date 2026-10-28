# Checkpoint 16 review

## Goal

A dependency-free `bun run tokens` reports bytes/4 counts; the core skill frontmatter stays at or below 2,500 tokens, the AGENTS template at or below 1,200, and hook output stays within budget without changing ceremony behavior.

## Acceptance

- Core skill frontmatter at or under 2,500 tokens; `templates/AGENTS.md.tpl` at or under 1,200.
- Hooks print 0 lines on green and at most 3 on deny, retaining the reason and exit code.
- The ceremony contract, skills lint, and “Where to work” match stay green.

## changed_files

- `AGENTS.md`
- `FILEMAP.md`
- `package.json`
- `scripts/tokens.ts`
- `skills/.chain-bundle/ai-eng-chain.ts`
- `skills/ai-agents-md/SKILL.md`
- `skills/ai-architect/SKILL.md`
- `skills/ai-audit-code/SKILL.md`
- `skills/ai-audit-docs/SKILL.md`
- `skills/ai-brainstorm/SKILL.md`
- `skills/ai-codegraph/SKILL.md`
- `skills/ai-debug/SKILL.md`
- `skills/ai-explore/SKILL.md`
- `skills/ai-issue-report/SKILL.md`
- `skills/ai-note/SKILL.md`
- `skills/ai-read-docs/SKILL.md`
- `skills/ai-research/SKILL.md`
- `skills/ai-security/SKILL.md`
- `src/chain/dialect.ts`
- `src/floor/entry.ts`
- `src/floor/index.ts`
- `tests/floor-hooks.spec.ts`
- `templates/AGENTS.md.tpl`
- `tests/token-budget.spec.ts`

## Verify

- `bun test tests/token-budget.spec.ts`
- `bun run tokens`
- `bun test tests/ceremony-contract.spec.ts`
- `bun test tests/skills-lint.spec.ts`
- `bun test tests/agents-md-sections.spec.ts`
- `bun test tests/floor-hooks.spec.ts`
- `bun test tests/chain-deny-tool.spec.ts`
- `bun test tests/generated-payload.test.ts`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`

## Round 1 findings

- **F1 — Major:** A successful `commit-msg` with an active override still emits `active override travels in the commit: …` and returns 0. `commitMsg` adds this to `result.lines`; `floor()` writes those lines even when `result.ok` is true. This violates the zero-line green-hook acceptance, and the token-budget test does not exercise the active-override case.

**Verdict:** FAIL — major F1 remains.

## Fixer response · Round 1

ROOT CAUSE: `commitMsg` intentionally carries override metadata in `result.lines`, and the shared hook writer printed those lines for successful results.

FIX: Added an actual source-CLI regression for an active override, kept `Override-Reason` in the message, and made the shared writer suppress successful results while preserving denial output and exit codes. Updated the existing floor-hook expectation.

LESSON: Gate shared hook output on result status; keep success metadata in the commit and denial reasons visible.

FILES: `src/floor/entry.ts`, `tests/token-budget.spec.ts`, `tests/floor-hooks.spec.ts`, `LEARNINGS.md`, `.ai-engineering/workflow/checkpoints/floating-core.json`, `.ai-engineering/workflow/reviews/floating-core-16.md`

PROOF: The regression failed before the fix with 1 output line. `bun test ./tests/token-budget.spec.ts` passes: 6 tests, 37 assertions.
