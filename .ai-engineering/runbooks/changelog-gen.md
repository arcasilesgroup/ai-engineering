---
name: changelog-gen
schedule: "0 16 * * 5"
environment: worktree
layer: reporting
requires: [gh, git]
---

# Changelog Generator

## Prompt

Generate a CHANGELOG.md update from the git log since the last release. Create a PR.

1. Find the last release tag: `git describe --tags --abbrev=0`.
2. Get commits since that tag: `git log <tag>..HEAD --format="%s" --no-merges`.
3. Classify each commit into changelog categories:
   - `feat:` or `spec-NNN:` with feature content → **Added**
   - `fix:` or `bug:` → **Fixed**
   - `refactor:` → **Changed**
   - `perf:` → **Performance**
   - `security:` or `dep:` → **Security**
   - `docs:` → skip (not user-facing)
   - `chore:` or `ci:` → skip (not user-facing)
4. Generate changelog section in Keep a Changelog format.
5. Prepend to CHANGELOG.md (after the header, before the first version entry).
6. Use benefit-first language: "Users can now..." instead of "Added support for...".
7. Create a PR:
   - Branch: `chore/changelog-update-<date>`
   - Title: `chore: Update CHANGELOG.md`
   - Labels: `auto-generated`, `documentation`
   - Enable auto-merge.

## Context

- Uses: changelog skill.
- Reads: git log, CHANGELOG.md.

## Safety

- Only modifies CHANGELOG.md — no other files.
- Branch must be `chore/changelog-update-*`.
- If no user-facing changes found, skip (do not create empty changelog entry).
- Do NOT modify existing changelog entries.
- Do NOT change version numbers or create releases.
