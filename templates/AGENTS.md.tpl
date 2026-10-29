# AGENTS.md — governed by {ai} Engineering ({{version}})

Guidance for AI coding agents working in this repository. Human teammates should be able to follow every line too. Only rules an agent CANNOT deduce from the code live here; if a rule becomes obvious from reading the code, delete it from this file.

## Security
- Never bypass hooks or checks (`--no-verify`, `-n`, `HUSKY=0`).
- Never suppress lint (`noqa`, `@ts-ignore`, `eslint-disable`, `nosec`).
- Never write secrets, personal data, or machine-specific absolute paths.

## Code style
- KISS, YAGNI, DRY, SOLID, TDD, Clean Code.
- Explain with enough context for a non-coder.
- **Readable code** (Boswell & Foucher): make code quick to understand.
  - Use purpose-naming; avoid generic names (`data`, `temp`, `helper`).
  - Prefix booleans (`is`, `has`, `can`, `should`) and limits (`max`, `min`).
  - Prefer positive conditions and early returns over deep nesting.
  - Comments explain why, not what; clarify surprises, skip the obvious.
  - Give each function one job. Reconsider requirements, use stdlib, prune.

## Build and test commands
{{commands}}

## Project config
- Domain: n/a
- Roles: n/a
- Paths: n/a
- Commands: n/a
- URLs: n/a
- Sign-in: n/a
- Do not touch: n/a
- Context: n/a

## Architecture rules
Lines the critic treats as blockers. Fill in project-specific rules here; leave empty when none apply yet.

## Shared helpers
- codegraph — use for call chains and blast-radius before editing across modules.

## Where to work
- Work in the open checkout. Use a worktree only when requested or another feature is active; pause if work may overlap.
- Prefer host worktree support; otherwise run `ai-eng worktree new <branch>` and use its reported path. The person chooses or approves the branch.
- Resume in the feature checkout. Never stash, reset, overwrite, or remove foreign work; preserve uncertainty and ask.
- After review, offer a PR, local merge, or keeping the branch. Prefer PR with a forge remote, otherwise local merge; `ai-eng worktree merge <slug>` handles it.

## Git workflow
See **Where to work** for checkout, worktree, and integration choices. `.ai-engineering/recap.html` is optional and never required for merge.

## Workflow
- Show the passing check before saying "done"; deterministic decisions belong in code.
- Never pass by deleting/skipping tests, weakening assertions, or loosening types; report a faulty test, do not weaken it.
- Stay in scope; report unrelated issues as "noticed, not fixed".
- If todos exist, mark each 🟢 done with proof, 🟡 pending with its next action, or 🔴 blocked with the exact question. Otherwise state status inline.

## Unattended runs
- Do not stop to ask. State a careful assumption and continue with reachable work.
- Run the full suite once before editing; record existing failures, and own new ones.
- Use non-interactive commands, `CI=true`, and `/dev/null` stdin when unsure; timeout network commands.
- Run long-lived processes in the background with a timeout.

## Lifecycle
- Follow each skill's `## Lifecycle` and its `Next:` handoff.
- Lanes: light (no contract), standard (`ai-brainstorm` → `ai-orchestrator`), full (triggered nodes).
- Record spoken approval in the artifact and follow its next step. Never ask for a command or approve yourself.

## Architecture layers
You may edit `src/**` freely; the arch-test reads `.ai-engineering/arch.rules.json` — propose layer changes there via PR, never by editing the test in silence.

## Voice
- Follow `ai-write`'s `references/voice.md` (shipped in the binary and skill canon).
- Lead with the action; number multi-step actions, one per step.
- State the finished step before the next. End with a next action under two minutes.
- Closing reports lead with blockers, then work and proof.

## Session hygiene (context economy)
`/clear` between tasks · `/compact` before stopping · batch prompts · check `/usage` as context grows.

## Pull requests
- Before committing, run lint and the full suite; the commit must pass CI checks.
- Add or update tests for changed behavior. After moves/import changes, rerun lint and typecheck.
- Title: `<area>: <imperative summary>` (e.g. `chain: cache verdicts per tool_use_id`).
- Commit subject ≤50 chars; explain why in the body when not obvious.

## Anti-drift
This list contains only what the agent CANNOT deduce from the project.
