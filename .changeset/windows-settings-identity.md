---
"ai-engineering": patch
---

On Windows, `ai-eng uninstall` (and the carrier install) sometimes refused to touch `~/.copilot/hooks/ai-eng.json`, saying it "changed while ai-eng was removing its entries, or it is a hard link with a second name". The check that the settings file is not the machine record under a second name compared file ids as JavaScript numbers; an NTFS file id is 64 bits, and past 2^53 two files created a moment apart rounded to the same id. The ids are now compared as exact bigints, so only a real hard link is refused. The checkpoint guard, which finds the checkpoint file a write really lands on by the same id, compares them the same way.
