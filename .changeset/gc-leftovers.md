---
"ai-engineering": patch
---

`ai-eng doctor --gc` now also clears what piled up unseen: verdict-cache files in `.ai-engineering/cache/verdicts/` untouched for a week, receipt-retention markers from earlier days, and the files under `.ai-engineering/workflow/` (checkpoints, feature pages, test plans) that git already holds and that are older than `[gc] older_than`. As in the other folders, a file cited by DECISIONS.md, NOTICE or the layer rules stays, and a file git does not hold is never deleted.
