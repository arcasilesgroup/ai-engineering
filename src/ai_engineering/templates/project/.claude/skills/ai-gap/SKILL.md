---
name: ai-gap
description: "Gap detection — spec vs code gaps, wiring gaps, feature gaps, framework self-audit. Includes correctness mode. Runs in isolated context."
argument-hint: "all|feature|wiring|framework|correctness"
---

Read and execute the skill defined in `.ai-engineering/skills/gap/SKILL.md`.

Use context:fork for isolated execution when performing heavy analysis.

Modes: `all` (default), `feature`, `wiring`, `framework` (self-audit), `correctness` (verify code does what PR/spec claims).

$ARGUMENTS
