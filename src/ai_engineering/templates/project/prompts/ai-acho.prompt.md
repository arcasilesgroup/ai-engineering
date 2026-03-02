---
description: "Alias: default = commit flow, `pr` = PR flow."
mode: "agent"
---

Before executing, verify these preconditions:

1. Current branch is NOT `main` or `master` (abort with warning if so).
2. Working tree has staged or unstaged changes (abort if nothing to commit).
3. Active spec is read from `.ai-engineering/context/specs/_active.md`.

`/ai:acho` is an alias. Read and execute `.ai-engineering/skills/commit/SKILL.md` for default flow, or `.ai-engineering/skills/pr/SKILL.md` if argument is `pr`.

Follow the complete procedure. Do not skip steps. Apply all governance notes.
