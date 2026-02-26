---
description: "Create pull request with governance checks and auto-complete"
mode: "agent"
---

> Model tier: fast — deterministic workflow. Recommended models: Haiku (Claude) or GPT-5.3-Codex (OpenAI).

Before executing, verify these preconditions:

1. Current branch is NOT `main` or `master` (abort with warning if so).
2. Working tree has staged or unstaged changes, or commits ahead of remote (abort if nothing to push/PR).
3. Active spec is read from `.ai-engineering/context/specs/_active.md`.

Read and execute the skill defined in `.ai-engineering/skills/workflows/pr/SKILL.md`.

Follow the complete procedure. Do not skip steps. Apply all governance notes.
