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

- Merge to `main` → `.github/workflows/version.yml` opens a **Version PR** (or
  publishes npm if versions are already bumped). npm publishing uses OIDC trusted
  publishing — no stored token.
- Binary releases (8 cross-compiled targets + SBOM + GitHub Release) stay
  tag-driven: push `v2.0.0` → `.github/workflows/release.yml`.
- Two channels, one owner each: **changesets owns npm**, **tags own binaries**.
