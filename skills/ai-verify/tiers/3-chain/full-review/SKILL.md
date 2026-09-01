---
name: full-review
description: Run every review skill at once — build-check, then design-check, code-audit, security-audit, a11y-audit and perf-audit fanned out across parallel agents — and merge them into one deduplicated, severity-ranked report. Use when asked for a full/complete review, to review everything before shipping or merging, or to run all the checks.
---

# Full review

Orchestrate all six review skills and merge their output into one report the user
can act on top-down. You are the coordinator: you spawn the agents, then reconcile
what they return. You do not perform the reviews yourself.

## 1. Resolve scope once, up front

Determine the scope per `.claude/review/CONVENTIONS.md` **before** spawning
anything, and pass the identical scope string to every agent. Agents that each
resolve their own scope will drift apart, and their findings then cannot be
compared or deduplicated.

Detect the stack once here too (per `CONVENTIONS.md` §1) and pass it down with
the scope. Five agents independently re-deriving the stack is wasted work, and in
a monorepo they can legitimately land on different answers — which silently
produces five reviews of different things.

Also check now whether a design document exists (`design.md`, `docs/design.md`,
`DESIGN.md`, or the project's own spec convention). If none does, **do not spawn
the design-check agent** — it would halt immediately by design. Note its absence
in the final report instead.

Likewise, if the UI lanes do not apply — a library, a CLI, a backend service with
no interface — skip `a11y-audit` and say so rather than spawning an agent to
report that there is no UI.

## 2. Build check first, on its own

Run `build-check` yourself, synchronously, before the fan-out. It is fast,
objective, and decisive:

- **If it FAILS on a compile or type error:** stop. Report the failure and ask
  whether to fix it first or review anyway. Reasoning-based review of code that
  does not compile is largely wasted — the file is about to change, and half the
  findings will evaporate with the fix.
- **If it fails only on lint:** carry on with the fan-out; fold the lint findings
  into the merged report.
- **If it passes:** carry on, and pass any size/timing output it produced along to
  the perf agent so that lane starts from a measurement instead of a guess.

## 3. Fan out the reasoning reviews

Spawn one `general-purpose` agent per remaining skill, **all in a single message**
so they run concurrently:

| Agent | Skill | Lane |
|---|---|---|
| design | `design-check` | conformance to `design.md` (skip if no spec) |
| code | `code-audit` | correctness, concurrency, types, error handling, contracts |
| security | `security-audit` | exploitable vulnerabilities |
| a11y | `a11y-audit` | WCAG 2.2 AA (skip if there is no UI) |
| perf | `perf-audit` | payload size, data access, caching, compute cost |

Give each agent this prompt shape:

> Invoke the `<name>` skill via the Skill tool and complete the review it
> describes. Scope: `<the exact scope string resolved in step 1>`.
> Stack (already detected, do not re-derive): `<the stack string from step 1>`.
> Follow `.claude/review/CONVENTIONS.md` exactly — especially the false-positive
> gate and the installed-version rule.
> Stay strictly in your lane: `<lane>`. If you notice something outside it, note
> it in one line under "Cross-lane observations" and do not investigate — another
> agent owns it.
> Write your full report to `.claude/reviews/<name>-<stamp>.md` as the conventions
> specify. Return **only**: the verdict, a one-line summary per finding with
> severity and `file:line`, and the report path. Do not return the full report
> text.

The last instruction is what keeps this affordable: full reports live on disk, and
you read the files you need rather than absorbing five reviews through agent
return values.

Agents run in the background and notify you on completion. Wait for all of them.
Do not run any review yourself in the meantime, and never predict or fabricate a
pending agent's findings — if the user asks before results land, say it is still
running.

If an agent fails or returns nothing, say so explicitly in the merged report and
mark that lane `NOT COVERED`. Never let a silent failure read as a clean pass.

## 4. Merge

Read the report files, then reconcile:

**Deduplicate.** The same `file:line` will surface in more than one report — that
is expected, and the lanes overlap by design. Keep the version from the skill that
owns the issue (an unlabeled button is a11y's, not code-audit's) and merge the
others' detail into it. Two lanes independently flagging one line is a **confidence
signal**: mark it corroborated and raise it, rather than listing it twice.

**Re-rank globally.** Each agent ranked within its own lane, so a "Critical" from
perf and a "Critical" from security are not the same thing. Rank the combined set
by real-world consequence: exploitable > data loss > broken for all users >
broken for some users > degraded > maintainability. Security and correctness
issues generally outrank equal-severity findings from other lanes.

**Reconcile conflicts.** Lanes can legitimately disagree — most often
`design-check` reporting the code as conformant while `a11y-audit` reports the
same element as inaccessible, because the spec itself mandated something that
fails WCAG. Do not suppress either. Report both and name the conflict: the code
matches the design, and the design has an accessibility defect. That conflict is
one of the more valuable things this review produces, and it only exists because
the lanes are separate.

**Do not re-litigate.** You did not read the code; the agents did. Trust their
verified findings. The exception is a finding that contradicts another agent's
evidence — read that file yourself and adjudicate.

## 5. Report

Write the merged report to `.claude/reviews/full-review-<stamp>.md` and give the
user a short summary in chat with the top items and the path.

```markdown
# Full review — <scope>

**Verdict:** PASS | PASS WITH NOTES | FAIL
**Stack:** <the stack detected in step 1>
**Ran:** <date> · Scope: <scope>

| Lane | Verdict | C | H | M | L | Report |
|------|---------|---|---|---|---|--------|
| Build | ✅ PASS | | | | | `build-check-<stamp>.md` |
| Design | ⏭️ SKIPPED — no `design.md` | | | | | — |
| Code | ❌ FAIL | 0 | 2 | 3 | 1 | `code-audit-<stamp>.md` |
| Security | ✅ PASS | 0 | 0 | 0 | 2 | `security-audit-<stamp>.md` |
| A11y | ❌ FAIL | 1 | 1 | 0 | 4 | `a11y-audit-<stamp>.md` |
| Perf | ⚠️ NOTES | 0 | 0 | 2 | 1 | `perf-audit-<stamp>.md` |

## Fix before merge
1. **[CRITICAL] <claim>** — `<path>:12` (a11y) — <one line> — <fix>
2. **[HIGH] <claim>** — `<path>:44` (code, corroborated by security) — <one line>

## Worth fixing soon
...

## Notes and polish
<collapsed one-liners>

## Conflicts and judgment calls
- <where lanes disagreed and what you concluded>

## Coverage gaps
- <lanes not run, files not reached, anything needing the app running>
```

The **Fix before merge** list is the point of the whole exercise — keep it to
things that genuinely block, ordered so the top item is the one to do first. If
that list is empty, say so plainly at the top; do not bury a clean result under
process.

## Cost

This spawns up to five agents that each read a good deal of code. For a small
change, `code-audit` alone is usually the right call, and a targeted single skill
beats the full sweep. Use this before a merge, a release, or on a branch that has
accumulated real work.
