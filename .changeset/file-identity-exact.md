---
"ai-engineering": patch
---

Every check that a file is still the one ai-eng read before writing or removing it — project files, machine settings, the machine record and its lock, skill links in the canon — now reads file ids as exact bigints and compares times in nanoseconds. On Windows an NTFS file id passes 2^53, where a JavaScript number drops its low bits, so a file swapped in a moment later could have passed for the one that was judged.
