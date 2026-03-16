---
name: ai-gap
description: "Detect spec-vs-code gaps, wiring gaps, and correctness gaps: unimplemented features, dead specs, disconnected implementations, PR-vs-code mismatches."
argument-hint: "all|feature|wiring|coverage|correctness"
---

Read and execute the skill defined in `.ai-engineering/skills/gap/SKILL.md`.

Use context:fork for isolated execution when performing heavy analysis.

Modes: `all` (default), `feature`, `wiring`, `framework` (self-audit), `correctness` (verify code does what PR/spec claims).

$ARGUMENTS
