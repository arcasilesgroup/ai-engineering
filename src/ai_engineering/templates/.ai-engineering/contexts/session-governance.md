# Session Governance

Shared reference for session-level governance rules. Loaded by `/ai-onboard` during Step 2 (Load active project context) to enforce skill discipline throughout the session.

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
| "deploy", "release", "publish" | `/ai-release-gate` |
| "conflict", "merge conflict" | `/ai-resolve-conflicts` |
| "incident", "outage", "postmortem" | `/ai-postmortem` |
