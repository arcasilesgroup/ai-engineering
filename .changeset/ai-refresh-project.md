---
"ai-engineering": minor
---

`/ai-agents-md` and `/ai-config-to-project` are now one skill, `/ai-refresh-project`, run by name. It brings a governed repository back in line with its tree in five steps: `AGENTS.md` and the PRD, the `docs/` folder, stale artifacts (`ai-eng doctor --gc`), orphan branches and worktrees (`ai-eng work`), and the governance files (layer rules, config, overrides), which it proposes on a page for you to apply. The `ai-eng adapt` verb is gone: `ai-eng adapt apply` always refused, because a hash an agent writes cannot prove a person approved the change.
