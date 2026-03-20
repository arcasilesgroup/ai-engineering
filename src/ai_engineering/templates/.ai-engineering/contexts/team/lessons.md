## Rules & Patterns

Persistent learning context for AI agents. Records corrections, patterns, and rules discovered during development sessions. This file is loaded by `/ai-onboard` at session start and updated by `/ai-learn` after corrections.

Unlike `decision-store.json` (formal decisions with expiry and risk acceptance), this file captures informal but important patterns that should persist across sessions.

## How to Add Lessons

When the user corrects AI behavior:
1. Identify the pattern (not just the specific fix)
2. Add a new section below with: context, the learning, and an example if applicable
3. Keep entries concise (3-5 lines max per lesson)

## Patterns

### Plan tasks must have checkboxes for progress tracking

**Context**: `/ai-plan` generates `plan.md` as the contract for `/ai-dispatch`.
**Learning**: Every task line MUST use `- [ ] T-N.N:` format, not `- T-N.N:`. Without checkboxes, `/ai-dispatch` cannot track progress and the user cannot see completion state at a glance.
**Rule**: When writing plan.md, always prefix tasks with `- [ ]`.
