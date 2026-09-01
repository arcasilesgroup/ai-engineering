# Contributing to ai-engineering

Thanks for helping build the governance floor. This document covers the rules
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
bun run typecheck    # tsgolint
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

## Commit and PR conventions

- Conventional Commits; commit messages must carry the `Receipt-Id` trailer
  when the git floor requires it (the hook enforces this).
- PR title: `<area>: <imperative summary>` (e.g. `chain: cache verdicts per tool_use_id`).
- CI runs build, lint, typecheck, the full test suite, and gitleaks — your
  commit must pass everything it will face there.

## Changesets and releases

- `bun run changeset` → pick bump (patch: fixes · minor: new verbs/flags/skills ·
  major: breaking CLI surface) + one-sentence summary.
- Merge to `main` → the version workflow opens a Version PR (or publishes npm).
- Tag `v*` → the release workflow builds the 8 binaries + SBOM + GitHub Release.

## Reporting bugs and security issues

- Bugs: GitHub Issues with repro steps and `ai-eng doctor` output.
- Vulnerabilities: **never** a public issue — follow [SECURITY.md](SECURITY.md).
