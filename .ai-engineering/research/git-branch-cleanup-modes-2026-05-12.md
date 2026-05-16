---
topic: Git branch cleanup canonical modes (git-trim taxonomy)
date: 2026-05-12
tier: external-evidence (Context7)
consumers: [spec-133 D-133-03, .ai-engineering/specs/spec.md]
---

# Git Branch Cleanup — 7 Canonical Modes (git-trim taxonomy)

Source: Context7 query on `/jasonmccreary/git-trim` + `/git/htmldocs` (2026-05-12).

## 7 Canonical Branch-Cleanup Modes

Together they cover 100% of git workflow cleanup scenarios:

1. **`--pruned`** — local branches whose remote-tracking ref is gone (after `git fetch --prune`). Detect via `git for-each-ref --format='%(refname:short) %(upstream:track)'` filtering `[gone]`.
2. **`--merged`** — `git branch --merged <base>` (regular merge detection).
3. **`--squashed`** — squash-merge detection via `git merge-base` + `git commit-tree`. Catches GitHub/GitLab "Squash and merge" workflow — branches that `--merged` misses entirely.
4. **`--stale`** — branches with no commits in N days (configurable via `gt.staleDays`, default 90).
5. **`--untracked`** — local branches without any remote-tracking ref.
6. **`--reset`** — all local branches NOT on remote (interactive confirm; force re-sync to remote state). Useful for forks / new workstations.
7. **`--all`** — superset (pruned + merged + squashed + stale + untracked + reset).

## Modifiers (orthogonal to modes)

- `--tracked` — also delete corresponding remote tracking branches.
- `--dry-run` — preview without deleting.
- `--force` — bypass safety checks.

## Protected Branches

- Git config key `gt.exclude` (glob patterns supported: `release/* save/*`).
- Common defaults: `main master develop staging`.
- Per-repo override via `git config gt.exclude` (no `--global`).

## Safety Rules

- Never delete current branch (HEAD).
- Always confirm interactively on `--reset` (unless `--force`).
- Refuse to operate in detached HEAD state.

`git fetch --prune` is prerequisite for `--pruned` mode to be meaningful — should be run automatically or documented.

## Application to `ai-eng cleanup branches`

Mirror the 7-mode + 3-modifier surface for full coverage. Add `--json` for structured output (CI / `/ai-cleanup` skill consumption). Protected list: `gt.exclude` config + manifest `cleanup.protected_branches` field. Audit event emission per deletion via `OutputPort` + framework event ledger.

## Sources

- [git-trim README](https://github.com/jasonmccreary/git-trim/blob/main/README.md)
- [git-trim llms.txt](https://context7.com/jasonmccreary/git-trim/llms.txt)
- [Git fetch --prune docs](https://github.com/git/htmldocs/blob/gh-pages/git-fetch.html)
- [Git remote prune docs](https://github.com/git/htmldocs/blob/gh-pages/git-remote.adoc)
