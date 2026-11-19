---
"ai-engineering": patch
---

The CLI now speaks one visual language. Every file row names what happened to it in a fixed column (`installed`, `updated`, `removed`, `unchanged`), while the mark and the colour keep saying how it went. `init`, `doctor`, `config`, `update` and `uninstall` open with the same `verb · folder · ai-eng version` title and close on one next command. `doctor`, `work` and the registry check in `update` show what they are doing while they work. The new-version notice no longer waits on the network at the end of a command: it reads the cache and refreshes it in the background, in blue when a newer ai-eng exists and in yellow when this repo is behind its binary. `--help` gives every verb one line, and `work` colours each lane by the decision it needs.
