---
name: ai-review
description: >-
  Judges a diff the way a staff engineer would: does it do what it claims, is it correct at
  its boundaries, is it safe, is it tested, and is there a smaller version of it. Never
  claims the result of a mechanical gate — those ran in CI and it says so. Trigger for
  "review this", "any issues with this", "is this merge-ready", "look over my PR", "what
  would you change". Not for running the gates — that is just check in CI. Not for finding
  why something is broken — use /ai-debug. Not for landing the work — use /ai-ship.
license: Apache-2.0
compatibility: needs git
context: fork
background: false
disable-model-invocation: true
---

# Judge the diff

## What it produces

Findings, each one at `file:line`, each with the smallest change that would resolve it.

## Steps

1. Read the spec and the plan first. Half of all real findings are "this is not what was
   agreed", and you cannot see those from the diff alone.
2. Read the diff whole before commenting on any part of it. A finding about a line that the
   next hunk deletes wastes the author's afternoon. If it does not fit in one pass, say so
   in the first line of the report, review it in named parts, and list the parts you have
   not read. A truncated pass reads exactly like a complete one, which is the failure this
   framework exists to cure, arriving as a confident report about the half that fit.
3. Work the checklists in `references/`, one lens at a time: correctness, security,
   performance, testing, compatibility. Each is a separate pass; mixing them is how the
   security one gets skipped.
4. Never report what a tool already reports. Formatting, lint, secrets, dependency
   vulnerabilities — those ran in CI, and repeating them buries the findings only a person
   could have made. If the gate did not run, say that instead of standing in for it.
5. For each finding: what breaks, the inputs that break it, and the smallest fix. A finding
   without a failing scenario is an opinion, and it should be labelled as one.
6. Before you call anything blocking, try to kill it, and default to dismissing: re-read
   the file around the line, not the hunk, and look for the guard, caller, framework
   behaviour or config that makes the scenario impossible. Dismiss it too when the bug is
   real and the fix you would propose is wrong, or worse than the code. A real bug you are
   unsure of still blocks; a theoretical one you are certain of does not. Say what you
   tried to kill and what lived.
7. Say what is good, once, briefly, and only where it is load-bearing. Then rank findings
   by what you would actually block on.

## Done when

- Every finding has a location, a failure scenario and a smallest fix.
- Nothing in the report claims a gate result that this skill did not see.
- The blocking findings are separated from the ones you would merge without.

## What this is not

Not a rewrite. If your finding is "I would have built it differently", it is a comment, not
a blocker, and it says so.
