---
"ai-engineering": patch
---

`/ai-orchestrator` now resumes one builder for tests, implementation, and verify, then one reviewer reads the diff. A blocker gets one fix. A second failure stops. A passed checkpoint is one commit and the end of the turn.
