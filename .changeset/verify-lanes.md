---
"ai-engineering": minor
---

The twelve verification skills `ai-verify` routes to (verify-feature, spec-extract, feature-verify, second-opinion, review-router, code-audit, security-audit, a11y-audit, perf-audit, design-check, build-check and full-review) now live inside `ai-verify` as files in `skills/ai-verify/lanes/`, with their scripts in `skills/ai-verify/scripts/`. None of them changed; they no longer appear as twelve separate skills in your agent's list, and `ai-eng update` removes the old folders. The lanes now read their shared conventions from `ai-verify/references/review/CONVENTIONS.md`, which ships with the skill, instead of a `.claude/review/CONVENTIONS.md` that no project had.
