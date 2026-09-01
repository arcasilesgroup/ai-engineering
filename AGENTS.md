# AGENTS.md — governed by {ai} Engineering

Guidance for AI coding agents working in this repository. Human teammates should be able to follow every line too. Only rules an agent CANNOT deduce from the code live here; if a rule becomes obvious from reading the code, delete it from this file.

## Project overview
`ai-engineering` is a governance floor for AI coding agents: a single Bun-compiled binary (`ai-eng`) that plants governance (`init`), enforces guards through hooks (`chain`), and proves completeness with receipts (`spec run`). The binary IS the payload — every skill and template travels inside it (regenerate with `bun scripts/gen-assets.ts`). Product spec: `docs/blueprint.html` (v17, §-numbered).

## Security
- Never bypass a git hook or a check: no `--no-verify`, no `-n` on commit, no `HUSKY=0`.
- Never silence a linter: no `noqa`, `@ts-ignore`, `eslint-disable`, `nosec`.
- No secrets, no personal data, no machine-specific absolute paths in any file.

## Code style
- KISS, YAGNI, DRY, SOLID, TDD, Clean Code.
- Explain it so someone who doesn't code can follow along.

## Build and test commands
- `bun install` — install dependencies.
- `bun run build` — compile the binary (`dist/ai-eng`, bytecode + sourcemap).
- `bun test` — full suite (adversarial + gates + arch).
- `bun test tests/skills.spec.ts` — skill canon gates only.
- `bun run lint` / `bun run typecheck` — oxlint / tsgolint.
- `bun scripts/gen-assets.ts` — regenerate `src/assets.ts` after touching `skills/` or `templates/`. ALWAYS run this after adding/renaming/deleting payload files, or the build breaks.
- `bun link` — expose the local `ai-eng` for testing in other repos.

## Architecture layers
- `src/cli.ts` — dispatch only: flags → verb → command module. Logic lives in `src/{chain,floor,guards,spec,wrap,surfaces}/`, never in `cli.ts`.
- `src/commands/*.ts` — thin parsers; the logic lives below them.
- `skills/` is the SOURCE of the global canon — flat `ai-*` folders, one `SKILL.md` each, references under `references/`. The arch-test reads `.ai-engineering/arch.rules.json`.

## Workflow
- Green gate before "done": show the output of the check that proves it.
- A decision that always comes out the same is code, not a prompt.
- Skills follow the canon contract (enforced by `tests/skills.spec.ts`): one `SKILL.md` per folder, folded `>-` frontmatter with `name` = folder name, English only, no corpus.md, no machine paths, no token-limit statements, upstream attribution preserved.
- Status convention in every task list: 🟢 done (with proof pasted) · 🟡 pending (name it) · 🔴 blocked on user.

## Pull requests
- Run lint and the full test suite before committing; the commit must pass everything it will face in CI.
- Add or update tests for the code you change, even if nobody asked.
- After moving files or changing imports, re-run lint and typecheck.
- Title format: `<area>: <imperative summary>` (e.g. `chain: cache verdicts per tool_use_id`).

## Session hygiene (context economy)
`/clear` between tasks · `/compact` before stopping, not after · batch prompting · check `/usage` when the context inflates.

## Anti-drift
This list contains only what the agent CANNOT deduce from the project.
