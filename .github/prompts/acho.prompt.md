---
description: "Fast-path alias for /commit and /pr workflows with full governance enforcement."
mode: "agent"
---

Before executing, verify these preconditions:

1. Current branch is NOT `main` or `master` (abort with warning if so).
2. Working tree has staged or unstaged changes (abort if nothing to commit).
3. Active spec is read from `.ai-engineering/context/specs/_active.md`.

Read and execute the skill defined in `.ai-engineering/skills/commit/SKILL.md`.

Follow the complete procedure. Do not skip steps. Apply all governance notes.
