---
"ai-engineering": patch
---

`ai-eng init` no longer writes an empty `.ai-engineering/arch.rules.json` that nothing outside ai-engineering read. Layer rules now belong to your language's own tool (dependency-cruiser, import-linter, or depguard in golangci-lint), and `/ai-config-to-project` proposes them from your code's real imports and your stack's guidelines for you to review and apply. `ai-eng doctor` recognises those tools, no longer warns about a repo with no code yet, and points a repo with code and no rules at the skill. `ai-eng update` removes the old empty file and keeps one you edited.
