# Security reconnaissance · worktree lifecycle awareness

## Scope and baseline

This audit covers the local lifecycle record and checks added to AI Engineering,
plus Copilotline's read-only consumer. AI Engineering is a TypeScript/Bun CLI
that manages local worktrees for coding agents. Copilotline is a TypeScript CLI
that renders GitHub Copilot status JSON as a terminal statusline. The relevant
feature paths are `src/commands/worktree.ts`, `src/shared-worktree.ts`,
`skills/ai-brainstorm/SKILL.md`, `skills/ai-orchestrator/SKILL.md`,
Copilotline's `src/infrastructure/worktree-info.ts`,
`src/infrastructure/git-info.ts`, `src/application/render-status-line.ts`,
and their focused tests.

The nearest comparables are Git's local worktree commands and Copilot CLI's
custom statusline hook. Both products run locally as the invoking user. No
network service or multi-tenant server mediates the lifecycle feature.

## Prior audit runs

AI Engineering `run-1` exists. It reported open findings in receipt-ledger
integrity, denial reporting and garbage collection, deny-cache correctness,
path-policy classification, shell-command policy, symlink handling, and
self-protect's textual shell fence. This run will not re-report those issues
unless the lifecycle changes create a concrete new path to them. The present
scope is the per-worktree lifecycle record, approval transitions, local-root
matching, and Copilotline's read-only status counts.

## Actors and trust boundaries

- A developer or coding agent invokes AI Engineering commands with the local
  user's operating-system privileges. CLI slugs, states and `--force` are
  command inputs.
- AI Engineering reads repository-local configuration, Git metadata and
  lifecycle JSON, then manages branches/worktrees with Git and filesystem
  operations.
- The brainstorm/orchestrator skills use those records as local workflow
  evidence. Their approval gates are prompt-level procedures, not a separate
  authentication system.
- Copilotline receives status JSON on stdin. The caller-provided working
  directory influences Git discovery. Its inventory reader inspects the
  conventional sibling `<repo>.worktrees` directory and local lifecycle
  records; it does not write state or perform lifecycle actions.

AI Engineering stores one local record per slug under `.ai-eng-lifecycle/`.
Records describe approval-before-start, active implementation,
review-before-merge/cleanup, or unknown. A record is not cryptographic proof
that a person approved a transition. The implementation guards state changes
with live worktree/branch evidence and revision-bound review transitions.

## Input surfaces and sinks

1. AI Engineering CLI arguments reach worktree creation, lifecycle updates and
   removal. Slugs and state names are validated; Git is spawned with argv, not
   a shell string.
2. `.ai-engineering/config.toml` can override the local worktree root;
   `.ai-eng-worktrees.json` and `.ai-eng-lifecycle/<slug>.json` are local JSON
   inputs used by lifecycle commands.
3. Git's common-dir and worktree-list output determine repository roots,
   branches, registered paths and prunable status.
4. Copilotline's JSON stdin provides a `cwd`; it reaches local Git discovery.
   The reader parses lifecycle JSON and compares slug, path, branch and state
   before returning numeric counts to the statusline renderer.
5. The only feature-specific output sink is terminal text/JSON containing
   validated counts. Record contents and other worktree names are not printed.

No lifecycle-specific HTTP, database, authentication or remote Git surface was
added. Copilotline has separate existing quota/account features that may use
`gh` and GitHub; they are outside this audit's lifecycle scope. Existing
receipt-ledger, policy and self-protect findings from `run-1` remain separate
open ground and should be handled on their own feature.
