# Checkpoint 1 · Replace the GitHub-only skill with ai-triage

Goal: The branch PRD records the approved scope, one shared Markdown skill preserves the existing GitHub procedure, the retired skill and directory are removed, and Azure targets stop before any remote read.

Acceptance:
- The PRD contains the approved single-skill replacement and GitHub-preservation decisions without changing unrelated product scope.
- Only `ai-triage` is the public skill name; `skills/ai-github-triage/` is gone, no alias or GitHub runtime helper exists, and an Azure target fails closed before reading.
- The shared entry point and GitHub provider reference remain Markdown instructions and preserve the existing GitHub report contract.

Changed files:
- `.ai-engineering/PRD.html`
- `skills/ai-github-triage/SKILL.md`
- `skills/ai-triage/SKILL.md`
- `skills/ai-triage/references/github.md`

Verify:
- `bun test tests/skills.spec.ts`

## Adversarial review — round 1

**VERDICT: PASS**
No findings.
Rationale: the GitHub procedure and report contract remain intact in the Markdown reference; shared routing explicitly stops Azure before remote reads; PRD changes are limited to the approved triage scope.
