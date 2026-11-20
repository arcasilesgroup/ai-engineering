---
"ai-engineering": patch
---

The `config.toml` that `ai-eng init` writes now tells the truth about itself: the surface list names `copilot-cli` (the id `ai-eng config` accepts), the `[gc]` comment names the folders `doctor --gc` really collects and documents `older_than` and `keep_runs`, and the new-version opt-out reads `[notices] enabled = false`, the key ai-eng reads. The old `notices = false` line, uncommented, landed inside `[gc]` and turned nothing off.
