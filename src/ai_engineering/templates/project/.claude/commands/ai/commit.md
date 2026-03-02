Stage, lint, secret-detect, commit, and push.

Preconditions (abort if any fail):
1. Current branch is NOT `main` or `master`.
2. Working tree has staged or unstaged changes.
3. Active spec is read from `.ai-engineering/context/specs/_active.md`.

Read and execute `.ai-engineering/skills/commit/SKILL.md`. Follow the complete procedure, all governance notes, and the Command Contract in `.ai-engineering/manifest.yml`. Args: `--only` = stage + commit only.

$ARGUMENTS
