---
"ai-engineering": patch
---

`ai-eng init` no longer asks before installing the global skill canon or adding ai-eng's guard hook to the settings your tools read from your home folder (Claude Code, Pi, Codex, Copilot, OpenCode). A "no" to either left a repo that called itself governed with no guards running, and `update` and `config` already wrote the same files without asking. Your own settings in those files are kept, and running `init` again never adds the hook twice. `init` still asks before creating a git repository and before overwriting an AGENTS.md that is already there.
