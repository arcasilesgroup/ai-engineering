# Getting started

Install `{ai} engineering` and get a governed repository in under a minute.

<div align="center">
  <img src="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/diagrams/install.png" alt="Install in seconds: pip install ai-engineering, ai-eng install . adds governance to your repo, ai-eng doctor reports [PASS], then open your IDE and type /ai-start. What you get: 54 skills and 9 agents, a governed workflow, automatic checks, and versioned local files." width="820">
</div>

## 1 — Install the CLI

```bash
pip install ai-engineering
# or, with uv:
uv tool install ai-engineering
```

Verify it:

```bash
ai-eng version
```

## 2 — Add governance to a repository

```bash
cd your-project
ai-eng install .
ai-eng doctor
```

`ai-eng doctor` reports `[PASS]` once hooks, mirrors, the manifest, and required tools are in place. Warnings are advisory and non-blocking.

## 3 — Start a session

Open your editor and type:

```text
/ai-start
```

`/ai-start` loads project context and shows you recent activity and the commands available.

## 4 — Ship something the governed way

Drive the intent; approve each step. The gates handle the rest.

```text
/ai-brainstorm → /ai-plan → /ai-build → /ai-pr
```

- `/ai-brainstorm` interrogates the idea and produces an approved spec.
- `/ai-plan` turns the spec into a patch-ready plan.
- `/ai-build` (or `/ai-autopilot` for larger work) implements it under TDD and quality gates.
- `/ai-pr` verifies, reviews, and opens the pull request.

`/ai-commit` stays available for WIP checkpoints; it is not part of the chain.

## Keeping current

```bash
ai-eng update     # in each governed repo, refresh the installed framework files
ai-eng doctor
```

Next: [the architecture](../architecture/index.md).
