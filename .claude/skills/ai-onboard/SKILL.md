---
name: ai-onboard
description: "Use at session start to detect available skills, load active context, refresh bounded instinct context when needed, and enforce skill usage discipline for the current session."
effort: medium
argument-hint: ""
---


# Onboard

## Purpose

Framework bootstrap and enforcement. Detect available skills, load active project context, refresh instinct context only when needed, and install the session rule that skills are mandatory when they apply.

## Trigger

- Auto-triggered via session-start hooks when available
- Manual: `/ai-onboard`
- Context: beginning of any non-trivial session

## Procedure

1. **Detect skills**
   - Scan the active platform skill directory and build a capability map.

2. **Load active project context**
   - Read `.ai-engineering/specs/spec.md`
   - Read `.ai-engineering/specs/plan.md`
   - Read `.ai-engineering/state/decision-store.json`
   - Read `.ai-engineering/contexts/team/lessons.md`
   - Read `.ai-engineering/manifest.yml`
   - Read `.ai-engineering/contexts/project-identity.md` if present

3. **Refresh instinct context when needed**
   - Inspect `.ai-engineering/instincts/meta.json`
   - Inspect `.ai-engineering/instincts/context.md`
   - If refresh is pending, the context is stale, or enough new observations accumulated, run `/ai-instinct review`
   - Otherwise, load the existing bounded instinct context as-is

4. **Present quick status**
   - Report the active spec
   - Report plan progress if a plan exists
   - Report loaded skills count
   - Report decision count or notable active risks
   - Report instinct status: fresh, stale, or refreshed
   - Report board configuration if present

5. **Enforce skill discipline**
   - Install this rule for the session:

     > If a skill applies to the current task, you MUST use it. No shortcuts.

## Board Status Examples

- `Board: GitHub Projects v2 #4, 5 states mapped`
- `Board: GitHub Labels (status: labels), 5 states mapped`
- `Board: Azure DevOps (Agile), 5 states mapped`
- `Board: not configured (run /ai-board-discover)`

## Red Flags Table

Rationalization patterns agents use to skip skills. Every one of these is wrong.

| # | Rationalization | Why it is wrong | Correct action |
|---|----------------|-----------------|----------------|
| 1 | "This is too simple for planning" | Simple tasks still need scope definition | Use `/ai-plan` |
| 2 | "I'll just make a quick fix" | Quick fixes skip root cause analysis | Use `/ai-debug` |
| 3 | "Tests aren't needed for this change" | Every behavioral change needs verification | Use `/ai-test` |
| 4 | "I already know the answer" | Confidence without verification causes regressions | Use the matching skill and then verify |
| 5 | "The user is in a hurry" | Process skipping creates rework | Follow the process faster, do not skip it |
| 6 | "This is just a config change" | Config changes affect runtime behavior | Use `/ai-test` to verify |
| 7 | "I'll add tests later" | Later rarely happens | Follow TDD or add coverage immediately |
| 8 | "The existing tests probably cover this" | Assumption without proof is not engineering | Run the tests and check the result |
| 9 | "This doesn't need a spec" | Non-trivial work still needs scope | Use `/ai-brainstorm` |
| 10 | "I'll clean up the commit message later" | Commit messages are permanent documentation | Use `/ai-commit` |
| 11 | "Security scanning would slow us down" | A leak costs more than a scan | Use `/ai-security` or `/ai-verify` |
| 12 | "This refactor is obvious" | Obvious refactors still need guardrails | Use the matching workflow skill |

## Detection Rules

When the user's request matches these patterns, enforce the corresponding skill:

| User intent pattern | Required skill |
|-------------------|----------------|
| "implement", "build", "add feature" | `/ai-brainstorm` then `/ai-plan` then `/ai-dispatch` |
| "fix", "bug", "broken", "not working" | `/ai-debug` |
| "test", "coverage", "verify" | `/ai-test` or `/ai-verify` |
| "refactor", "restructure", "move" | `/ai-brainstorm` then `/ai-plan` |
| "explain", "how does", "what is" | `/ai-explain` |
| "commit", "push", "save" | `/ai-commit` |
| "PR", "pull request", "review" | `/ai-pr` or `/ai-review` |
| "deploy", "release", "publish" | `/ai-release` |
| "conflict", "merge conflict" | `/ai-resolve-conflicts` |
| "incident", "outage", "postmortem" | `/ai-postmortem` |

## Quick Reference

```text
/ai-onboard
```

No arguments. Reads project state, refreshes instinct context when warranted, and configures the session.

## Boundaries

- `onboard` does not execute product work
- `onboard` should stay light; it loads context and refreshes instinct context only when the gate says it is worth doing
- `onboard` may update `.ai-engineering/instincts/{instincts.yml,context.md,meta.json}` as an explicit exception to the usual read-only bootstrap rule
- If no active spec exists, report it but do not block the session

$ARGUMENTS
