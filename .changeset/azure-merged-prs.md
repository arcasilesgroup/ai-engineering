---
"ai-engineering": patch
---

`ai-eng work` now asks Azure DevOps for merged pull requests when the repository's `origin` is an Azure DevOps remote (`dev.azure.com`, `ssh.dev.azure.com` or `*.visualstudio.com`), through `az repos pr list`. A completed PR whose last source commit is the branch tip counts as landed, the same way a merged GitHub PR does through `gh`. Without `az`, or signed out, the board says so and still proves landings from git alone.
