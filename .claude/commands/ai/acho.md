Alias: default = commit flow, `pr` = PR flow.

Preconditions (abort if any fail):
1. Current branch is NOT `main` or `master`.
2. Working tree has staged or unstaged changes.
3. Active spec is read from `.ai-engineering/context/specs/_active.md`.

Read and execute `.ai-engineering/skills/commit/SKILL.md` (default) or `.ai-engineering/skills/pr/SKILL.md` (if arg is `pr`). Follow the complete procedure, all governance notes, and the Command Contract in `.ai-engineering/manifest.yml`.

$ARGUMENTS
