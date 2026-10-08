# Security reconnaissance · worktree lifecycle awareness

## Scope and baseline

This audit covers the local lifecycle workflow added to AI Engineering and its
read-only consumer in Copilotline. AI Engineering is a TypeScript/Bun CLI used
by developers and coding agents to manage local worktrees. Copilotline is a
TypeScript CLI that renders Copilot stdin JSON into a terminal statusline.
Relevant paths are AI Engineering `src/commands/worktree.ts`,
`src/shared-worktree.ts`, `skills/ai-brainstorm/SKILL.md`,
`skills/ai-orchestrator/SKILL.md`, and Copilotline
`src/infrastructure/worktree-info.ts`, `src/infrastructure/git-info.ts`,
`src/application/render-status-line.ts`.

The nearest comparables are Git's local worktree commands and Copilot CLI's
custom statusline hook. Both applications run locally as the invoking OS user;
the lifecycle feature adds no network service or multi-tenant boundary.

## Prior runs

AI Engineering `run-1` contains open findings about receipt-ledger integrity,
denial reporting and garbage collection, deny-cache correctness, policy path
classification under `0467`, shell-command policy, symlink policy, and
self-protect's textual shell fence. Those findings are outside the changed
lifecycle paths; do not repeat them unless this feature creates a concrete new
exploit path. `run-2` currently contains only an architecture draft and no
findings ledger, so there are no additional prior findings to skip.

## Actors and trust boundaries

- Developers or coding agents invoke AI Engineering commands with the local
  user's filesystem and Git privileges. CLI inputs include worktree slugs,
  lifecycle states and an explicit `--force` removal option.
- AI Engineering reads repository configuration, Git metadata and local JSON
  records; it creates/removes worktrees and writes per-slug lifecycle records
  under `.ai-eng-lifecycle/`.
- Brainstorm/orchestrator skills interpret those records as local evidence for
  workflow decisions. Spoken approval rules are procedural prompts, not a
  separate authentication system.
- Copilotline receives status JSON on stdin; caller-provided `cwd` influences
  local Git discovery. It scans the conventional sibling
  `<repo>.worktrees` root and lifecycle JSON, then renders numeric counts.

Records represent approval-before-start, active implementation,
review-before-merge/cleanup, or unknown. They are local state, not
cryptographic proof of who approved a transition. AI Engineering validates
slugs, paths, branches, state transitions and review revisions. Git subprocesses
use argv rather than shell strings. Copilotline validates record structure and
requires slug, live path and `feat/<slug>` branch agreement before counting.

## Input surfaces and sinks

1. AI Engineering CLI positionals and `--force` reach worktree creation,
   lifecycle updates and removal.
2. `.ai-engineering/config.toml` can override the AI Engineering worktree root;
   `.ai-eng-worktrees.json` and `.ai-eng-lifecycle/<slug>.json` are local JSON
   inputs consumed by the manager and reader.
3. Git common-dir, worktree-list and status output affect root, branch, path
   and prunable decisions.
4. Copilotline JSON stdin supplies `cwd`; it reaches local Git discovery.
   Lifecycle JSON is parsed and transformed into numeric state counts.
5. The feature-specific output sink is terminal text or normalized JSON. It
   contains static labels and validated counts, not record contents or names.

The lifecycle implementation adds no HTTP, database, authentication or remote
Git surface. Copilotline's separate quota/account feature may use GitHub and
`gh`; that path is outside this audit.
