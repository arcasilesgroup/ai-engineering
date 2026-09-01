---
name: ai-debug
description: >-
  Finds the root cause of broken behaviour and names it at file:line, then writes the check
  that fails for that reason before changing anything. Also resolves merge and rebase
  conflicts by intent rather than by taking a side. Trigger for "it's not working", "this
  used to work", "I'm getting an error", "CI is failing", "why is X happening", "I have
  conflicts", "the rebase failed". Not for adding test coverage to working code — use
  /ai-verify. Not for exploring an unfamiliar area — use /ai-explore. Not for designing the
  fix — once the cause is named, use /ai-plan. Not for reporting the fault to outsiders —
  use /ai-issue-report.
license: Apache-2.0
---

# ai-debug — find the cause, not the symptom

## What it produces

A named cause at `file:line`, a check that fails because of it, and only then a fix.

## Steps

1. Reproduce it. If you cannot reproduce it, say so plainly and stop guessing: the next
   useful thing is a way to reproduce it, not a change.
2. Read the failing output in full. The first error is usually the real one and the rest
   are its consequences; the last error is the one people paste.
3. Name a cause you can point at. `file:line`, and one sentence on why that line produces
   this symptom. "Probably a race" is not a cause. If two causes are plausible, say which
   observation would tell them apart, then go and make that observation.
4. Before the fix, write the check that fails for this reason. A fix with no failing check
   before it is a change with an opinion attached.
5. Fix the cause, at the place all the callers go through. Patching the one path the report
   named leaves every sibling caller broken, and the shared fix is usually the smaller diff.
6. Run the check. Then run the suite. Then say what you changed and why it fixes the cause
   you named, not the symptom that was reported.
7. If you are two attempts in and it is still not fixed, stop and say so. That is a rule,
   not a suggestion: the third attempt is where the guessing starts.

## Conflicts

Read both sides for intent before touching either. Lock files and generated files are
regenerated, never merged by hand. Migrations are ordered, not combined. If two people
meant different things, that is a conversation, not a resolution.

## What this is not

- "I know what the bug is even though I cannot reproduce it" — a cause you cannot
  reproduce is a guess: the next useful thing is a way to reproduce it, not a change.

## Done when

- The cause is named at `file:line` and a person could disagree with it.
- A check exists that fails without the fix and passes with it.
- You said what you changed, in a sentence somebody could act on.

## The ai-engineering seam

1. The failing check you write in step 4 is a gate candidate: if the milestone's
   `.ai-engineering/spec.html` exists, add it there (`G<n>: <what holds>` + `CHECK:`) so
   `ai-eng spec run` proves the fix forever, not just today.
2. Long-running reproduction (a dev server, a watcher, a REPL) belongs to a supervised
   process, never a fire-and-forget shell call: name it, drive it over stdin, and stop it
   when the diagnosis ends.
3. Grounding duty (§11.6): every file:line you name was opened in this session. Never cite
   from memory — /ai-explore and /ai-read-docs are the lenses for that.
4. The verdict on WHY it broke belongs to the `decide` tier of the model pin
   (`.ai-engineering/config.toml`); mechanical checks (does it fail, does it pass) belong
   to `verify`.

## Routing

In scope: broken behaviour with a reproducible symptom, failing CI, merge/rebase conflicts.
Not for: no diagnosis yet but the fault must reach outsiders (/ai-issue-report), the fix
needs a design (/ai-plan), the fix needs proof it satisfies the ask (/ai-verify), a
recurring pitfall worth remembering (/ai-note).

Source: ai-engineering v1 (own), Apache-2.0.
