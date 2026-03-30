---
id: sub-003
parent: spec-090
title: "Instinct Skill Rewrite - Listening + Review"
status: planned
files: [".claude/skills/ai-instinct/SKILL.md", ".claude/skills/ai-onboard/SKILL.md", ".claude/skills/ai-commit/SKILL.md", ".claude/skills/ai-pr/SKILL.md"]
depends_on: [sub-002]
---

# Sub-Spec 003: Instinct Skill Rewrite - Listening + Review

## Scope

Implements D-090-07 (three-leg observation) and D-090-12 (call points). Rewrites /ai-instinct with two commands. Updates /ai-onboard, /ai-commit, /ai-pr integration points.

## Exploration

### Existing Files
- `ai-instinct/SKILL.md` — 106 lines. Two modes: `status` and `review`. Review is a 9-step consolidation that reads observations, normalizes into supported families, merges, regenerates context.md. Supported families: toolSequences, errorRecoveries, skillAgentPreferences.
- `ai-onboard/SKILL.md` — Lines 35-38 load instinct context: reads meta.json, reads context.md, triggers review if stale. Must change: no context.md loading, activate listening mode instead.
- `ai-commit/SKILL.md` — Best insertion point: after Step 0.5 (work item context), before Step 1 (staging). New step 0.6 calls `/ai-instinct --review`.
- `ai-pr/SKILL.md` — Best insertion point: after Step 6.5 (docs), before Step 7 (pre-push). New step 6.7 calls `/ai-instinct --review`.

### Patterns to Follow
- skill-sharpen listening mode pattern: output single line "observing...", go silent, analyze on --review.
- ai-create TDD pressure test approach: CSO-optimize description for trigger quality.

### Dependencies Map
- Sub-002 must complete first: SKILL.md references v2 families and schema.
- 4 IDE mirrors (.claude, .codex, .gemini, .github) + 4 templates = 8 copies per skill changed.
- ai-onboard/ai-commit/ai-pr each have 4 IDE copies.

### Risks
- Listening mode is behavioral — LLM compliance varies. Instruction must be concise and unambiguous.
- --review before commit/PR adds latency. Must be fast (read instincts.yml + write, no exploration).
