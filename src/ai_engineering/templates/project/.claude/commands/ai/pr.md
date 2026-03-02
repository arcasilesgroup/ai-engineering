Stage, commit, push, create PR with auto-complete.

Preconditions (abort if any fail):
1. Current branch is NOT `main` or `master`.
2. Working tree has staged or unstaged changes, or commits ahead of remote.
3. Active spec is read from `.ai-engineering/context/specs/_active.md`.

Read and execute `.ai-engineering/skills/pr/SKILL.md`. Follow the complete procedure, all governance notes, and the Command Contract in `.ai-engineering/manifest.yml`. Args: `--only` = create PR only (warn if unpushed).

$ARGUMENTS
