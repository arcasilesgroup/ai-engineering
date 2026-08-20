---
id: "022"
slug: the-anchor-nobody-could-answer-for
status: draft
date: 2026-08-20
ref: ""
supersedes: ""
---

# The anchor nobody could answer for

## Who this is for, and what it is worth to them

The repository owner, who reads a line on every single commit telling him something is
wrong and has never once been able to act on it, and anybody running this framework whose
own commits say the same. Nineteen commits were made on this branch while writing it, and
all nineteen printed `commit-msg: this commit is not anchored`. The cure that line names
requires a person at a physical keyboard running a command that lives inside the half being
deleted, and it has never been run.

When this is done, a commit says nothing unless something is actually wrong, and the record
keeps every property a reader depends on except the one nobody could ever exercise.

## Context and problem

The chain is a hash-linked record of what happened, one per repository and machine, kept
outside every clone. It works, and it is not what this specification touches.

The **anchor** is a second thing wearing a similar name: a footer written into each commit
message pointing at the chain's head, and three verdicts derived by comparing the git log
against the chain. Today `ai-eng audit verify` exits 1 and reports 22 broken links across
five runs. The only thing built that can answer for them is `ai-eng audit account`, which
needs a named person typing an exact sentence on a real terminal — `accept.py` returns no
under `--non-interactive` and never opens the device — and which has never been run.

Measured while writing this: passing all 40,933 buffered events through the sealer produces
26,270 correct, 13,011 foreign, 1,253 ordinary, 399 blocks and **zero** marked edited. The
defect that manufactured those 22 is already fixed. They are historical damage, they are not
growing, and the machinery kept open for them costs a line on every commit and about 520
lines in the tree.

The owner decided on 2026-08-20: delete it, do not run `account` first, and accept the 22.

There is a second, sharper reason to be careful here rather than quick. The word "anchor" is
used in this tree for two unrelated things. `accept._anchored_bytes`, `acceptance._anchored`,
`readiness._anchored`, `spec_transaction(anchor=)`, `uninstall.anchors` and
`decide._require_anchored_io` are a **path-safety reader**: they refuse a symbolic link, a
filesystem boundary crossing and an unbounded read. Touching any of them would delete a
security control while appearing to do the thing this specification asks for.

## Options considered

1. **Run `ai-eng audit account` once, then delete.** Cleanest record, and it costs a person
   at a keyboard for an unknown number of ranges. The owner declined it in writing, and the
   measurement above says the ranges are closed rather than accumulating.
2. **Keep the anchor and repair the 22.** Same cost as option 1 plus keeping 520 lines and a
   line on every commit for a comparison that has produced three verdicts and no finding.
3. **Delete the anchor, keep the chain, accept the 22.** What the owner decided.

## Decision

Option 3. Deleted: the `ANCHOR` pattern and `HISTORY_INCOMPLETE_PREFIX`, `_history_findings`,
`_anchor_line`, `anchor_line`, the `--anchor` and `--anchors` command surface, the commit
footer in `git-hooks/commit-msg`, the `anchor_commits` configuration key and the workflow
line `skeletons.py` generates for other people's repositories.

Kept, and the boundary is the whole of the care in this specification: `ai-eng audit verify`
and `ai-eng audit replay`, which still walk every link, still refuse a link that arrived
edited before it was sealed, and still revalidate the Solution Intent. `hooks/_emit.py` holds
no anchor code at all — its three matches are prose in docstrings. Every `_anchored` reader
listed above stays untouched.

`doctor` assertion 11 is **not** deleted. Only its last line belongs to the anchor. The
branches above it are live and independent, one of them the detector that notices another
tool has hijacked this repository's git hooks and left a check green over a repository where
none of ours run. The doctor keeps 25 assertions.

## Challenged once

The strongest case against: deleting the anchor removes the only copy of the chain's head
that lives outside the machine holding the chain, so a lost laptop loses the ability to prove
where the record ended. That is a real loss and the README advertises it.

It fails on what the copy could do. A footer in a commit message on the same machine's
branch is not an off-machine replica; it survives losing the laptop only if the branch was
pushed, in which case the push is the replica and the footer is a duplicate of a fact the
remote already holds. And the property it protects — tamper evidence — is `audit verify`'s,
which is kept in full. What is genuinely lost is the three history verdicts, and those have
produced no finding in this repository's life while producing a false alarm on every commit.

The README sentence goes with it. A promise that outlives its mechanism is the defect this
product exists to expose, and leaving it would be the worse half of this trade.

## Assumptions and unresolved risks

Assumed without proof: that no consumer repository depends on the `Ai-Eng-Anchor:` footer.
Only this tree and the template `skeletons.py` writes were searched.

Open and named: after this, `ai-eng audit verify` still exits 1 on this machine, because the
22 broken links remain in the chain and nothing here repairs them. The line on every commit
stops; the exit code does not. Anybody reading `audit verify` on this machine sees a red that
is historical, and this specification records that rather than papering over it.

## Examples somebody can check

Given a commit made after this lands, When the commit-msg hook runs, Then it says nothing
about anchoring. Checked by `git commit` and reading stderr, which prints
`commit-msg: this commit is not anchored` today and nothing after.

Given `ai-eng audit --anchor`, When it is run, Then the argument is refused as unknown rather
than producing a footer. Checked by `uv run pytest -q tests/test_mut_accept.py`.

Given a chain with a link that arrived edited before it was sealed, When `ai-eng audit verify`
runs, Then it still refuses. That is the property this specification must not break, and it is
checked by `uv run pytest -q tests/test_record.py -k verify`.

Given `ai-eng doctor`, When it runs after this lands, Then it still prints 25 assertions and
still detects a hijacked git-hooks path. Checked by `uv run pytest -q tests/test_doctor.py`.

Given `accept._anchored_bytes` and its siblings, When the tree is searched after this lands,
Then all of them are present and unmodified. Checked by
`git diff --stat HEAD~9 -- src/ai_engineering/accept.py src/ai_engineering/acceptance.py`,
which must be empty.

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
