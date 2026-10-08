# Contributing to ai-engineering

Thanks for helping build ai-engineering. This document covers the rules
that are NOT deducible from the code; everything else, the code and
[AGENTS.md](AGENTS.md) teach.

## Ground rules

- **Never bypass a git hook or a check**: no `--no-verify`, no `-n` on commit,
  no `HUSKY=0`.
- **Never silence a linter**: no `noqa`, `@ts-ignore`, `eslint-disable`, `nosec`.
- **No secrets, no personal data, no machine-specific absolute paths** in any file.
- **Green gate before "done"**: show the output of the check that proves it.
- Every PR that changes user-visible behavior (CLI, guards, skills, templates)
  ships with a [changeset](.changeset/README.md). Docs-only and test-only PRs
  do not need one.

## Setup

```bash
bun install          # dependencies
bun run build        # compile dist/ai-eng (skills/templates embedded)
bun test             # unit + adversarial + gates + arch
bun run lint         # oxlint
bun run typecheck    # oxlint --type-aware --type-check
```

The binary is the payload: `skills/` and `templates/` travel inside it. If you
touch either, run `bun scripts/gen-assets.ts` — the build breaks without it.

To test the CLI against real repos: `bun link`, then run `ai-eng` anywhere.

## How to work

- Add or update tests for the code you change, even if nobody asked.
- After moving files or changing imports, re-run lint and typecheck.
- Match the existing architecture: `src/cli.ts` dispatches only — logic lives
  in `src/{chain,floor,guards,spec,wrap,surfaces}/`; `src/commands/*.ts` are
  thin parsers.
- Product spec is `docs/blueprint.html` (v17): §-references in code and docs
  point at it. A behavior change without a blueprint section is a spec change —
  propose it in an issue first.
- Rebase a feature with `ai-eng worktree rebase <slug>` after its implementation
  checkpoint is approved, each checkpoint has passed, and behavior and review
  gates have passed (a UI gate may be `n/a`). The command requires the managed
  feature worktree to be clean. It rebases only onto local
  `refs/heads/main`; it does not fetch or sync a remote or sibling branch. A
  conflict stays active in that feature worktree for the agent to resolve or
  abort with `git rebase --abort`. If local `main` moves during the rebase, the
  rewritten feature stays in place; rerun synchronization and affected gates.
- Run `ai-eng worktree merge <slug>` only after human app review. The primary
  checkout must be clean and on local `main`; the command resolves it even when
  invoked inside a feature worktree. The checkpoint must be `ready-to-merge`,
  have every planned gate complete, and record the approved review against the
  exact `reviewed_main` and `reviewed_feature` commit IDs. The command creates a
  normal hook-running merge in a temporary detached worktree. It publishes to
  local `refs/heads/main` only if that ref still equals `reviewed_main`, then
  refreshes the primary checkout, verifies the exact merge parents and
  ancestry, and safely removes only the approved feature worktree and branch.
- A conflicting merge stays in the temporary detached worktree, not the
  feature. The command attempts to abort and remove that temporary transaction
  and returns an error; the reviewed feature remains available. If temporary
  cleanup cannot be verified, follow the path and state in the error. A refusal
  or pre-publication hook failure also leaves the feature available. If `main`
  moved before publication and no matching merge was already published,
  synchronize again, rerun affected gates, and obtain renewed app review. If a
  commit hook fails, fix its reported cause before retrying; rerun affected
  checks and review if the feature or reviewed refs change. After publication,
  refresh or verification failures preserve the feature worktree; resolve the
  obstruction and retry `ai-eng worktree merge <slug>`, which recognizes its
  already-published reviewed merge. If removal cannot be verified, inspect
  `git worktree list`, the feature path, and `refs/heads/feat/<slug>` before
  retrying; do not assume the worktree remains or claim the close succeeded. A
  successful close removes the checkpoint with the worktree, so the worktree
  leaves Git's active inventory; no separate complete lifecycle record or
  declaration manifest remains.

## Commit and PR conventions

- Conventional Commits; commit messages must carry the `Receipt-Id` trailer
  when the git hooks require it (the hook enforces this).
- PR title: `<area>: <imperative summary>` (e.g. `chain: cache verdicts per tool_use_id`).
- Local flow: create a feature worktree with `ai-eng worktree new <slug>`, sync
  it with `ai-eng worktree rebase <slug>`, and close it with
  `ai-eng worktree merge <slug>`. A session never pushes.
- The pull request against `origin/main` is your decision. It is cut from the local `main`, never from a worktree.
- CI runs build, lint, typecheck, the full test suite, gitleaks, semgrep,
  trivy, `bun audit`, SonarCloud and Snyk — your commit must pass everything
  it will face there.

## Changesets and releases

- `bun run changeset` → pick bump (patch: fixes · minor: new verbs/flags/skills ·
  major: breaking CLI surface) + one-sentence summary.
- Merge to `main` → `.github/workflows/version.yml` opens a Version PR that bumps
  `package.json` and `CHANGELOG.md`; it does not publish.
- Dispatch `.github/workflows/release.yml` with a channel: `integration` ships a
  candidate (GitHub prerelease + npm `next`), `production` ships the real one
  (GitHub release marked latest + npm `latest`). It builds the 8 binaries + SBOM +
  GitHub Release and publishes npm under OIDC trusted publishing.

## Reporting bugs and security issues

- Bugs: GitHub Issues with repro steps and `ai-eng doctor` output.
- Vulnerabilities: **never** a public issue — follow [SECURITY.md](SECURITY.md).
