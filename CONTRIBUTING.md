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
- Match the existing architecture: `src/cli.ts` dispatches to command entry
  points; implementation lives in `src/{chain,floor,guards,git,surfaces,workflow,wrap}/`.
  The source and its tests define behavior. `docs/blueprint.html` records design
  context; update the user-facing docs and tests when behavior changes.
- When a feature needs synchronization, use native `git rebase <detected base>`
  from the selected feature checkout after its implementation checkpoints and
  behavior and review gates pass (a UI gate may be `n/a`). The CLI does not run
  rebases. Resolve conflicts in that checkout or abort with `git rebase --abort`.
  If the base moves during the rebase, synchronize again and rerun affected gates.
- Run `ai-eng worktree merge <slug>` only after human app review. The checkpoint
  must be `ready-to-merge`, have every planned gate complete, and record the
  approved review against the exact `reviewed_base` and `reviewed_feature` commit
  IDs. The command creates a normal hook-running merge in a temporary detached
  worktree. It publishes to the detected local base only if that ref still equals
  `reviewed_base`, then refreshes any matching base checkout and verifies the
  exact merge parents and ancestry. The feature worktree and branch remain in
  place after publication; remove them later with `ai-eng worktree rm <slug>`.
- A conflicting merge stays in the temporary detached worktree, not the
  feature. The command attempts to abort and remove that temporary transaction
  and returns an error; the reviewed feature remains available. If temporary
  cleanup cannot be verified, follow the path and state in the error. A refusal
  or pre-publication hook failure also leaves the feature available. If the base
  moved before publication and no matching merge was already published,
  synchronize again, rerun affected gates, and obtain renewed app review. If a
  commit hook fails, fix its reported cause before retrying; rerun affected
  checks and review if the feature or reviewed refs change. After publication,
  refresh or verification failures preserve the feature worktree; resolve the
  obstruction and retry `ai-eng worktree merge <slug>`, which recognizes its
  already-published reviewed merge. Before removing a feature, use
  `ai-eng worktree list` to confirm its exact path and branch, then run
  `ai-eng worktree rm <slug>` when the checkout is safe to remove. A successful
  removal deletes the checkpoint with the worktree; no separate completion
  record or declaration manifest remains.

## Commit and PR conventions

- Conventional Commits; commit messages must carry the `Receipt-Id` trailer
  when the git hooks require it (the hook enforces this).
- PR title: `<area>: <imperative summary>` (e.g. `chain: cache verdicts per tool_use_id`).
- Local flow: create a feature worktree with `ai-eng worktree new <branch>`,
  synchronize with native `git rebase <detected base>` when needed, publish the
  reviewed merge with `ai-eng worktree merge <slug>`, then remove the worktree
  explicitly when it is no longer needed.
- When the user requests a PR, `ai-pr` pushes and verifies the current branch
  from the current checkout or selected worktree before opening it. It does not
  create or switch branches, and it uses the selected base without assuming local `main`.
- CI runs build, lint, typecheck, the full test suite, gitleaks, semgrep,
  trivy and `bun audit`. SonarCloud and Snyk jobs run when their tokens are
  configured. Your commit must pass the jobs it will face there.

## Changesets and releases

- `bun run changeset` → pick bump (patch: fixes · minor: new verbs/flags/skills ·
  major: breaking CLI surface) + one-sentence summary.
- Merge to `main` → `.github/workflows/version.yml` opens a Version PR that bumps
  `package.json` and `CHANGELOG.md`; it does not publish.
- Dispatch `.github/workflows/release.yml` with a channel: `integration` ships a
  candidate (GitHub prerelease + npm `next`), `production` ships the real one
  (GitHub release marked latest + npm `latest`). It gates the dispatched SHA (lint,
  typecheck, full suite, build), builds the 8 binaries, packs one npm tarball —
  smoke-tested and described by a runtime-only CycloneDX SBOM — and publishes that
  exact tarball, checked against its digest, under OIDC trusted publishing.

## Reporting bugs and security issues

- Bugs: GitHub Issues with repro steps and `ai-eng doctor` output.
- Vulnerabilities: **never** a public issue — follow [SECURITY.md](SECURITY.md).
