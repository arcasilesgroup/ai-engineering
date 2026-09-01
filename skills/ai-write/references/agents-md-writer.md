# AGENTS.md writer — the agent-guidance discipline

Loaded when writing or reviewing AGENTS.md (or its importers: CLAUDE.md,
.codex, .cursorrules). Sources: agents.md convention (agents.md), this repo's
own AGENTS.md practice, documentation-writer.md for the writing levers.

## The contract

AGENTS.md is guidance for AI coding agents working in the repository — written
so human teammates can follow every line too. Two filters decide what belongs:

1. **Non-deducibility** — only rules an agent CANNOT infer from the code live
   here. If reading the code teaches the rule, delete the line (anti-drift).
2. **Context economy** — this file is loaded on every turn; every line pays
   rent every session. One source of truth per meaning; the environment
   (formatters, hooks, CI) is a source of truth too — do not restate it.

## Structure (in this order when applicable)

1. **Header** — name + governance mark; one paragraph of scope.
2. **Project overview** — what the product is, where the spec lives, how the
   build works (the payload mechanism if any).
3. **Security** — the never-cross lines: hook bypass, linter silencing,
   secrets policy.
4. **Code style** — only the non-obvious: the rule set name, the explanation
   standard.
5. **Build and test commands** — the exact commands, including the ones whose
   omission breaks silently (asset regeneration, codegen steps).
6. **Architecture layers** — where logic lives and where it must not live.
7. **Workflow** — the green gate, the status convention, the canon contracts
   enforced by tests.
8. **Pull requests** — pre-commit obligations, title format, CI parity.
9. **Anti-drift** — close with the one-line scope reminder: this list contains
   only what cannot be deduced from the project.

## Writing rules

- **Command table over prose** — commands as fenced `code`, exact flags.
- **Enforcement points named** — every "always/never" names the mechanism that
  enforces it (a test, a hook, CI); unenforced rules rot.
- **Status convention** — one shared task-status vocabulary so agent output and
  human review agree (e.g. 🟢 done with proof · 🟡 pending · 🔴 blocked).
- **Keep it under the context ceiling** — ~80 lines; overflow goes to
  references behind pointers, not into the always-loaded file.
- English only; no machine paths; no token-limit statements.
