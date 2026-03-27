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

### /ai-pr MUST clear spec.md and plan.md after PR creation

**Context**: PR #190 (spec-056) merged into main with spec.md and plan.md still containing full spec content. Steps 8.5-8.8 of `/ai-pr` SKILL.md were completely skipped. `_history.md` also missing the spec-056 entry.
**Learning**: The spec cleanup in step 8 is not optional — it's the mechanism that resets the spec lifecycle for the next feature. Stale spec files cause the next `/ai-brainstorm` to see outdated content and the next `/ai-pr` to generate PR descriptions from wrong data.
**Rule**: During `/ai-pr`, after generating the PR body from spec content, ALWAYS execute ALL of step 8:
1. Add entry to `_history.md`
2. Clear spec.md to `# No active spec\n\nRun /ai-brainstorm to start a new spec.\n`
3. Clear plan.md to `# No active plan\n\nRun /ai-plan after brainstorm approval.\n`
4. `git add` the cleared files before committing
Never skip these steps. Verify by reading the files after clearing.

### Existing PR updates must reconcile branch spec history

**Context**: On long-lived branches, updating the current PR body can hide the fact that `_history.md` is still missing entries for earlier completed specs on the same branch.
**Learning**: When a PR spans multiple specs, audit `git log origin/main..HEAD` and `_history.md` together. Do not assume the active `spec.md` is the only history entry that needs to be recorded.
**Rule**: Before closing a PR-update task, verify `_history.md` includes every completed spec represented in the branch commits, not just the latest one.
