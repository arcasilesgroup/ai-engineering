---
"ai-engineering": patch
---

`ai-eng update`'s plan now reads the way it acts:

- A shared settings file, such as `.cursor/hooks.json`, says "ai-eng's entries refreshed, your keys kept". It no longer says "overwritten", because it is merged by marker and your keys stay.
- Each `↳` list of paths now sits under its own heading ("already current", "yours"). Before, it sat under the row above, so the current files seemed to be the ones updated.
