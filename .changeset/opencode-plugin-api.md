---
"ai-engineering": patch
---

opencode: the carrier follows the host's plugin API and stays out of its plugin scan. OpenCode imports every file in `~/.config/opencode/plugins` as a plugin ENTRY, so the chain bundle 3.0.x wrote beside the entry was refused as an invalid plugin and took the provider config hook down with it (`Plugin export is not a function`, then `undefined is not an object (evaluating 'R.config')`). The bundle now lives in `~/.config/opencode/ai-eng/`, imported from there. The entry is written for the installed major: 2.x gets the default `{ id, setup }` definition and gates tool calls by wrapping `tool.execute` (deny = throw, rewrite = args mutation); 1.x gets the `"tool.execute.before"`/`"tool.execute.after"` hooks. `update` retires a scanned bundle a recorded install left behind, and OpenCode's lowercase tool names (`shell`, `read`, `write`, …) now reach the guards under their canonical names instead of being skipped.
