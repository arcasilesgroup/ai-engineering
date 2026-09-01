# AGENTS.md — governed by {ai} Engineering ({{version}})

Guidance for AI coding agents working in this repository. Human teammates should be able to follow every line too. Only rules an agent CANNOT deduce from the code live here; if a rule becomes obvious from reading the code, delete it from this file.

## Security
- Never bypass a git hook or a check: no `--no-verify`, no `-n` on commit, no `HUSKY=0`.
- Never silence a linter: no `noqa`, `@ts-ignore`, `eslint-disable`, `nosec`.
- No secrets, no personal data, no machine-specific absolute paths in any file.

## Code style
- KISS, YAGNI, DRY, SOLID, TDD, Clean Code.
- Explain it so someone who doesn't code can follow along.

## Build and test commands
{{commands}}

## Workflow
- Green gate before "done": show the output of the check that proves it.
- A decision that always comes out the same is code, not a prompt.
- Status convention in every task list: 🟢 done (with proof pasted) · 🟡 pending (name it) · 🔴 blocked on user.

## Architecture layers
You may edit `src/**` freely; the arch-test reads `.ai-engineering/arch.rules.json` — propose layer changes there via PR, never by editing the test in silence.

## Session hygiene (context economy)
`/clear` between tasks · `/compact` before stopping, not after · batch prompting · check `/usage` when the context inflates.

## Pull requests
- Run lint and the full test suite before committing; the commit must pass everything it will face in CI.
- Add or update tests for the code you change, even if nobody asked.
- After moving files or changing imports, re-run lint and typecheck.
- Title format: `<area>: <imperative summary>` (e.g. `chain: cache verdicts per tool_use_id`).
- Commit messages: subject ≤ 50 chars; body explains WHY when it is not obvious.

## Anti-drift
This list contains only what the agent CANNOT deduce from the project.
