# Changesets

This repo uses [changesets](https://github.com/changesets/changesets) to version
the `ai-engineering` npm package and generate CHANGELOG.md entries.

## When you need a changeset

Every PR that changes user-visible behavior (CLI, guards, skills, templates) ships
with one changeset file. Docs-only or test-only PRs do not need one.

## How to add one

```bash
bun run changeset
```

Pick the bump type:

- **patch** — bug fixes, guard tweaks, doc corrections.
- **minor** — new verbs, new flags, new skills in the canon.
- **major** — breaking changes to the CLI surface, hook contract, or file layout.

Write the summary in one sentence; the version PR merges it into CHANGELOG.md.

## Release flow

- Merge to `main` → `.github/workflows/version.yml` opens a **Version PR** that
  bumps `package.json` and `CHANGELOG.md`. It does not publish.
- Dispatch `.github/workflows/release.yml` with a channel: **integration** ships a
  candidate (GitHub prerelease + npm `next`), **production** ships the real one
  (GitHub release marked latest + npm `latest`). It builds the 8 cross-compiled
  targets + SBOM + GitHub Release and publishes npm under OIDC trusted
  publishing — no stored token.
- **changesets owns the version arithmetic**, **`release.yml` owns the
  deployment** — the only publisher, of npm and of the binaries alike.
