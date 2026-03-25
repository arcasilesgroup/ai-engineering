---
id: spec-067
title: "Auto-optimize brainstorm input via ai-prompt preprocessing"
status: draft
created: 2026-03-25
refs: []
---

# spec-067: Auto-optimize brainstorm input via ai-prompt preprocessing

## Problem

When users invoke `/ai-brainstorm`, they often provide vague or underspecified input ("mejorar el flujo de instalación", "optimizar la seguridad"). The brainstorm skill's interrogation phase compensates by asking clarifying questions, but a clearer starting input would reduce the number of questions needed and produce sharper specs.

`/ai-prompt` already has proven techniques for improving text clarity and specificity, but the user must remember to invoke it manually before brainstorm. Nobody does this.

## Solution

Add a preprocessing step (step 1.5) to `/ai-brainstorm` that automatically evaluates the user's input and, if it's vague or underspecified, optimizes it for clarity and specificity before the interrogation begins. The optimized input is shown as a before/after comparison but continues automatically without requiring user confirmation.

## Scope

### In Scope

**A) New handler: `prompt-enhance.md`**

1. Create `.claude/skills/ai-brainstorm/handlers/prompt-enhance.md` with:
   - Input quality evaluation criteria (detect vague terms, missing specificity, ambiguous scope)
   - Optimization logic applying ai-prompt techniques #1 (Be Explicit Over Implicit) and #5 (Positive Framing)
   - Skip logic: if input already meets quality threshold, output "Input ya optimo" and continue
   - Before/after display format

**B) Update SKILL.md process**

2. Add step 1.5 "Enhance input" between "Load context" and "Interrogate" in `.claude/skills/ai-brainstorm/SKILL.md`
3. Update Quick Reference table with the new step
4. Add handler reference to Integration section

**C) Mirror sync**

5. After brainstorm SKILL.md changes, mirrors in `.github/prompts/` and `.agents/skills/` will need sync via existing `sync_command_mirrors.py`

### Out of Scope

- Changes to `/ai-prompt` skill itself
- Generic preprocessing mechanism for other skills (future spec)
- Codebase-aware optimization (brainstorm's existing step 1 handles that)
- User confirmation gate on the optimized input (decided: auto-continue)

## Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Handler in brainstorm, not in ai-prompt | Avoids cross-skill dependency. No precedent for cross-skill handlers. Easy to extract later. |
| D2 | Visible before/after, auto-continue | Transparency without friction. User sees what changed but isn't blocked. |
| D3 | Skip when input already specific | Avoids unnecessary latency. Evaluated by detecting vague markers in both languages: ES ("mejorar", "optimizar", "arreglar", "limpiar") and EN ("improve", "optimize", "fix", "clean up"), plus absence of measurable criteria. |
| D4 | Only techniques #1 and #5 from ai-prompt | Clarity and positive framing cover the main problem (vague input). CSO, Cialdini, etc. are irrelevant for user input preprocessing. |
| D5 | No codebase context in optimization | Brainstorm already explores the codebase in step 1. Duplicating that in the preprocessor adds latency for zero value. Pure linguistic transformation. |
| D6 | Brainstorm-only for now, generic later | Validates the concept with minimal risk. If successful, extract to shared pattern in a future spec. |

## Acceptance Criteria

### Handler
- [ ] AC1: `handlers/prompt-enhance.md` exists in `.claude/skills/ai-brainstorm/`
- [ ] AC2: Handler defines quality evaluation criteria (vague term detection)
- [ ] AC3: Handler applies techniques #1 (explicit > implicit) and #5 (positive framing)
- [ ] AC4: Handler skips optimization when input is already specific, showing "Input ya optimo, continuando..."
- [ ] AC5: Handler displays before/after comparison when optimization occurs

### SKILL.md Integration
- [ ] AC6: Step 1.5 "Enhance input" exists between "Load context" and "Interrogate"
- [ ] AC7: Quick Reference table includes the new step with gate "Input quality checked"
- [ ] AC8: Integration section lists `handlers/prompt-enhance.md` in "Calls"

### Behavior
- [ ] AC9: Vague input ("mejorar la seguridad") gets optimized with specific terms
- [ ] AC10: Specific input ("add rate limiting to /api/v2/users endpoint returning HTTP 429 after 100 req/min") passes through unchanged
- [ ] AC11: No user confirmation required — auto-continues after showing before/after
- [ ] AC12: No codebase reading happens during the optimization step

### Mirrors
- [ ] AC13: `.github/prompts/ai-brainstorm.prompt.md` reflects the new step after sync
- [ ] AC14: `.agents/skills/brainstorm/SKILL.md` reflects the new step after sync
- [ ] AC15: `.agents/skills/brainstorm/handlers/prompt-enhance.md` exists after sync

## Files Changed

| Action | Path | Notes |
|--------|------|-------|
| create | `.claude/skills/ai-brainstorm/handlers/prompt-enhance.md` | New handler with evaluation + optimization logic |
| modify | `.claude/skills/ai-brainstorm/SKILL.md` | Add step 1.5, update table and integration |
| sync | `.github/prompts/ai-brainstorm.prompt.md` | Mirror sync via script |
| sync | `.agents/skills/brainstorm/SKILL.md` | Mirror sync via script |
| sync | `.agents/skills/brainstorm/handlers/prompt-enhance.md` | Handler mirror sync |

## Risks

| Risk | Mitigation |
|------|-----------|
| Optimization distorts user intent | Before/after display (AC5) lets user catch distortions. Interrogation phase (step 2) further validates requirements. |
| Adds latency to every brainstorm invocation | Skip logic (AC4) avoids optimization when unnecessary. No codebase reading (AC12) keeps it fast. |
| "Already specific" heuristic has false positives/negatives | Conservative approach: only flag clearly vague markers. When in doubt, optimize — the cost of unnecessary optimization is low. |
| Vague markers are language-dependent | D3 updated to include both ES and EN markers. The brainstorm skill already challenges both ("improve", "optimize", "clean up" in Questioning Rules). |
| Optimization tightens intentionally exploratory inputs | Handler must preserve breadth of exploratory inputs. The optimization is linguistic cleanup, not scope-narrowing. Only add specificity to genuinely ambiguous terms, not to inputs that are broad by design. |
