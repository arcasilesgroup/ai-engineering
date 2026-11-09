---
"ai-engineering": patch
---

`ai-eng update` now moves the lock to the installed version even when every file is already current. Before, after upgrading the binary, `ai-eng doctor` kept saying "files installed by 3.0.2 → ai-eng update", and `ai-eng update` kept answering "nothing to sync" without moving the version. The warning never went away.
