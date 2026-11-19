---
"ai-engineering": patch
---

The generated CI workflow no longer fails while installing ai-eng: it verified the release's provenance against the tag, but releases are built from main, so the check never passed.
