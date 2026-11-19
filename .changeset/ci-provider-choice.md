---
"ai-engineering": minor
---

`ai-eng init` now asks where the project's CI runs: GitHub Actions, Azure Pipelines, or none. The origin remote preselects the answer, and `--ci github-actions|azure-pipelines|none` skips the question. Azure Pipelines projects receive `.azure-pipelines/ai-eng-check.yml`, which verifies the governor's provenance without a GitHub token, and init names the two portal steps (create the pipeline, add the Build validation branch policy). The choice is stored as `[ci].provider` in `.ai-engineering/config.toml`. `ai-eng config` now changes it too: run it with no flags and pick "CI provider", or pass `--ci <provider>`; it rewrites only that key, writes the new gate and removes the old one. Repositories governed before this release have no `[ci]` block and keep their GitHub workflow.
