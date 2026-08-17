---
name: ai-build
description: >-
  Executes one task of an already approved plan, red to green to refactor, as one logical
  change with a clean checkpoint and the gate run before anything is called done. Trigger
  for "implement task 3", "build this", "make the plan's next step work", "write the code
  for this spec". Not for deciding what to build — use /ai-spec, which is where an option
  is weighed and an authority recorded. Not for diagnosing a failure — use /ai-debug, which
  finds a cause at file:line. It does not widen scope, approve its own work, publish or
  deploy; when the plan stops being true it stops and says so.
license: Apache-2.0
compatibility: needs git
disable-model-invocation: true
---

# Build the task the plan already approved, and stop where the plan stops

## What it produces

Code and tests for one task, a plan whose checkboxes match reality, and a commit that
passes the gate.

## Steps

1. Read the plan and name the task you are doing. If the task is not in a plan, or the plan
   is not approved, stop here: this skill has nothing to execute.
2. Write the failing test first, and run it. A test that has never been red is a test that
   has never been shown to test anything, and the exact focal point matters — assert on the
   thing that would break, not on the shape around it.
3. Make it green with the smallest change that works. Then refactor with the test still
   green, or leave it.
4. One logical change per commit. `hooks/change_scope_guard.py` counts the files a change
   touches and denies one that has outgrown its plan — that guard is not a suggestion and
   working around it is out of scope for this skill.
5. Run the gate exactly as CI runs it and paste the output. "It should pass" is not the
   gate, and `--no-verify` is denied by `hooks/no_verify_guard.py` on the way past.
6. Update the plan's checkboxes to what actually happened, including the parts that did not.
7. When the plan stops being true — the task is bigger than written, the design does not
   survive contact, a decision is missing — stop and escalate to `/ai-spec`. Continuing on a
   plan you have privately rewritten is the failure this skill exists to prevent.

## Done when

- One task is done, its test was red first, and the gate output is in the conversation.
- The plan on disk says what happened, and nothing was quietly widened.
- Nothing was published, deployed, merged or approved by the same hands that wrote it.
