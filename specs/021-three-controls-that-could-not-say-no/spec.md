---
id: "021"
slug: three-controls-that-could-not-say-no
status: draft
date: 2026-08-20
ref: ""
supersedes: ""
---

# Three controls that could not say no

## Who this is for, and what it is worth to them

The repository owner, who is not at the keyboard for this work, and the next person who
adds a capability to this framework. Today the owner pays a tax on every single commit —
fifty of the last fifty commits moved an integer that bounds nothing — and the next person
who tries to add a fourteenth skill is stopped by a rule whose only reachable effect is to
stop them. Neither of those two costs buys a control. Meanwhile a third thing, the piece
that decides whether a tool call is allowed, reads its own crash as permission.

When this is done the owner commits without arithmetic, a capability is added by editing
one list that a person signs, and a dispatcher that cannot decide denies instead of
allowing.

## Context and problem

Three separate things in this tree are shaped like controls and are not.

**The line ceiling.** `contract.REPO_CEILING` is 82,400 and `contract.repo_lines()` returns
82,400. A test allows a slack of at most 400, so the constant is obliged to follow the tree
it claims to bound. `git log -G'^REPO_CEILING = '` returns fifty of the last fifty commits,
four of which do nothing else. The single row in the halt ledger — the one time the machine
stopped and asked a person — is a fixed-point collision between two sessions over this
number. Nothing in the history shows it catching a defect.

**The capability cap.** `policy/capability-manifest.schema.json` bounds the catalogue at
fifteen entries in three places. Measured against a sixteenth capability: removing the cap
alone still fails, removing the cap and the id list still fails, and only widening
`allowed_ids` passes. So the cap cannot fire today — anything that would trip it dies
earlier — and the one situation where it does fire is after somebody has correctly widened
both lists, when it answers "the manifest is invalid" without saying which rule. Its only
reachable effect is to break the correct change. This repository already withdrew it:
`docs/audit-2026-08-16.md:42` lists "EP-308 — a closed fifteen-capability list is not a check
that a sixteenth capability cannot be declared without governance" among the proofs the
audit withdrew, and it has had no owner since.

**Two fail-open paths in the guard chain.** `hooks/chain.py` dies outside every handler when
a tool name arrives as something other than text; the process exits 1, and every surface
reads 1 as "not blocking". The action passes without a guard having seen it. And
`hooks/_wrap.py` transmits a denial as exit 0 plus text on standard output: with that output
closed, a blocked call exits 120 in both protocols, which no surface reads as a denial.
The file that says a guard fails closed even when it crashes is wrong about itself.

## Options considered

1. **Repair each of the three in place.** Keep the ceiling and give it a slack that means
   something; keep the cap and make its message name the rule; wrap the dispatcher. Two
   thirds of that is repairing a control that has never fired, which is how a tree grows a
   maintenance cost for a guarantee nobody is getting.
2. **Delete the two that cannot fire, fix the one that can.** Smaller tree, and the two
   deletions are what makes the fix affordable: with zero slack against the ceiling, a
   commit that adds nine lines to `chain.py` cannot land without first moving the number it
   is supposed to respect.
3. **Delete all three and drop the guard-chain repair.** Rejected in writing: a denial read
   as permission is the exact failure this product exists to expose, and it is nine lines.

## Decision

Option 2. The ceiling and the capability cap are removed; the two fail-open paths are
closed; and one further crash — `hooks/loop_guard.py` raising on an argument made only of
whitespace, which denies a legitimate call in the guard's own name — is fixed in the same
block because it is one line and it is reachable by the model.

`allowed_ids` is **not** removed. It is the one hand-written list where adding a capability
is still a signature, and it ships inside the wheel installed on other people's machines,
which the tests do not. Deriving it from the directories on disk would mean anybody who
creates a folder decides what capabilities exist.

The line ceiling has no replacement. `TEST_RATIO_MAX` already covers the shape the ceiling's
own comment said it could not see — a suite growing while the product does not — and no
study was found that measures a defect, churn or maintainability outcome from bounding the
total lines of a repository.

## Challenged once

The strongest case against this: the ceiling did stop something. `specs/019/spec.md:190-193`
records a capability being dropped partly because "the schema would have to change", and
four commits exist whose whole content is closing the ceiling onto the tree. So both numbers
did change behaviour — they made additions expensive.

That case fails on the difference between expensive and checked. A control makes a *specific*
wrong thing expensive and says which. These two make *every* addition expensive and say
nothing about which, so the thing they deter is uncorrelated with the thing they were built
to deter. The halt ledger proves the direction: its one row is this machinery stopping
correct work, not wrong work. Expense without discrimination is friction, and friction is
what people route around — which is what 670 recorded bypasses of a since-deleted scope
guard already demonstrated in this same tree.

## Assumptions and unresolved risks

Assumed without proof: that no consumer repository outside this one reads `REPO_CEILING` or
`repo_lines`. Only this tree was searched.

Open: the two fail-open repairs are measured against the two protocols observed in Claude
Code. The other seven surfaces were not exercised, so "a denial now leaves as a denial" is
proven on one surface and asserted on the rest. That is the same gap the tree already
carries under the word PROVEN, and this block does not close it.

Open and named because it is worse than it looks: after this block, nothing binds a writer
to the files its task declared. `hooks/change_scope_guard.py` and `hooks/claim_scope_guard.py`
were deleted on 2026-08-20 for reasons that hold, and nothing replaced them. This block does
not repair that; it records it so the next one cannot pretend it is not there.

## Examples somebody can check

Given a sixteenth capability in the catalogue, When the manifest is validated, Then it is
accepted — and the same input is refused today. Checked by
`uv run pytest -q tests/test_capabilities.py` after the change, and before it by adding a row
and watching `capability.validate()` return a refusal naming `allowed_ids`.

Given a tool name that arrives as a number, When the dispatcher runs, Then it exits 2 and the
call is denied. Today it exits 1 and the surface allows it. The exact command and its output:
`echo '{"tool_name": 17, "tool_input": {}, "hook_event_name":"PreToolUse"}' | PYTHONPATH=hooks python3 hooks/chain.py PreToolUse; echo "exit=$?"`
prints `exit=2` after this block and `exit=1` before it.

Given a denial whose standard output is closed, When the guard decides, Then the process
exits 2 rather than 120, so the surface still reads a denial. Checked by
`uv run pytest -q tests/test_hooks.py -k closed_stdout`.

Given the ceiling constant deleted, When the gate runs, Then it is green and no commit needs
an arithmetic step. Checked by `just check` and by `git grep -n REPO_CEILING` returning only
`CHANGELOG.md`.

Given an argument made only of whitespace, When the loop guard reads it, Then it does not
raise and does not deny. Checked by `uv run pytest -q tests/test_hooks.py -k whitespace`.

## Decisions

<!-- ai-eng decide writes yaml blocks here -->

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
