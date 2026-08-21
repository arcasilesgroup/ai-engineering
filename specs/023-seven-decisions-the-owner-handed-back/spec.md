---
id: "023"
slug: seven-decisions-the-owner-handed-back
status: draft
date: 2026-08-21
ref: ""
supersedes: ""
---

# Seven decisions the owner handed back

## Who this is for, and what it is worth to them

The repository owner, who merged pull request #681 and then changed how this repository is
worked: the person approves a specification, and everything after that approval is the
agent's to decide and to build. Seven questions were waiting for him in a brief. Under the
new rule six of them stop being his, one of them is only his, and this document is the one
thing he signs.

It is worth this to him: the seven stop being a queue. When this is approved, the work runs
to the end without another interruption, and every decision taken along the way is written
here where he can overturn it by reverting one commit.

## Context and problem

Pull request #681 merged on 2026-08-21 as `461435fb`. It executed the subtraction plan and
refused three of that plan's deletions on measurement, each with its own record. Seven items
were left open in a brief written for the owner, and the brief's own framing was that none of
them were the agent's to take.

The owner's instruction on 2026-08-21 changes that framing: *"de aquí, todos deberías de poder
decidir tú. La persona/equipo solo interviene en la aprobación del spec. Pero a partir de ahí,
debería de ser la llm que pueda implementar con el goal."*

That is a wider grant than `docs/adr/0016`, and a permission that is not written is not a
permission, so it is written here and carried into a record.

Two of the seven were blocked for a reason the new rule dissolves. Both needed a fresh
approval of bytes somebody had already signed, and re-signing an approval is exactly the act
the agent may not perform. Naming them inside the specification the owner approves is how one
signature reaches them without the agent ever forging one.

Two more turn out to have been misread the first time, and this document corrects both rather
than carrying the misreading forward.

## Options considered

**Take the six and leave the two re-approvals waiting.** Rejected: it leaves a gate carrying a
hand-written waiver list, which is the shape of green nobody earned that this product exists
to refuse.

**Ask the owner the seven questions again, one at a time.** Rejected: it is what he just told
this repository to stop doing.

**Write one specification that carries all seven, and have him approve that.** Chosen. It uses
the mechanism the repository already has, it puts a person's signature on the only act that
needs one, and it leaves every other decision written and reversible.

## Decision

**D-023-01 — The two stale approvals are re-signed at today's bytes.**
`docs/adr/0013` approved four files on 2026-08-17 and two of them have moved since. Approving
this specification approves those two at the digests below, and `docs/adr/0021` records it.

| file | digest today |
| --- | --- |
| `specs/016-the-thesis-nobody-owns/spec.md` | `c91dbc80d5026aa6f4802d683dab12a2f18c2677fab932a30c8f05b5e01df0bb` |
| `specs/018-controls-a-reviewer-proved-were-not-controls/plan.md` | `104d506522edaaafd6795030661f6717e9b18c2bfb22ebb6ff42e8ee4c753323` |

**Rationale**: both changes are repairs, and restoring the signed bytes would undo them. The
016 change is one line — a reference to `docs/audit-2026-08-15.md` corrected to the file that
exists, `docs/audit-2026-08-16.md`. The 018 change marks task T-11 done and records the run
that finished it. Restoring would put a wrong filename back and would re-assert "not done"
about work that was done. The waiver list in `tests/test_record.py` goes away in the same
commit, because a waiver that outlives its reason is the control lying.

**D-023-02 — The task-8 evidence command is repaired by renaming the test, not the plan.**
`specs/022`'s plan gives `pytest -q tests/test_contracts.py -k anchored` as task 8's check.
The test that landed is `test_the_path_safety_readers_survive_every_deletion_called_anchor`,
which that selector does not match: pytest exits 5 with everything deselected. The test is
renamed so the selector matches it.

**Rationale**: the plan is approved at a digest by `docs/adr/0017` and editing one word in it
voids that approval; renaming a test costs no signature and no meaning. Of the two files that
disagree, the cheaper one to move is the one nobody signed. This is the general rule and not a
trick for this case: when a signed document and an unsigned one contradict each other, and
either could be corrected, the unsigned one moves.

**D-023-03 — `docs/adr/0019` stands. The council ships without the yardstick its deferral asked
for.**

**Rationale**: the owner merged #681 with 0019 in it, which is the reading the brief asked
for. The design answers the deferral's actual fear by construction — lenses cannot see each
other, there is no vote, no ranking, and no field in which the word approved can be written —
and no yardstick is being claimed that does not exist.

**D-023-04 — The eight shipped specifications are not archived. Wave 3 is refused on
measurement, and the constitutional objection that blocked it is withdrawn as a misreading.**

**Rationale**: the objection was that `CONSTITUTION.md` says "Never touch a user's `AGENTS.md`,
`CONSTITUTION.md` or `specs/` after writing them once". Read again, the governing words are *a
user's*: it binds what this product does inside somebody else's repository, not what this
repository does to its own record. No test in this tree reads it the other way. So the
Constitution never blocked this and saying it did was wrong.

What blocks it is the measurement. Wave 3's stated benefit was that those 4,084 lines are
context the agent loads every session. They are not: no hook reads `specs/`, and `AGENTS.md`
only names the directory. The second benefit was tree size, and the line ceiling was deleted
by `specs/021` on the finding that it could not be a control and be met at the same time. So
the saving is zero on both counts. The cost is not zero: `tests/test_record.py` asserts
`target.is_file()` for all eleven approved digests, and moving a specification out of the tree
turns that red for every record that names one.

**D-023-05 — The three records written under standing authority stand: `0018`, `0019`, `0020`.**

**Rationale**: the owner read the pull request and merged it. That is the review the brief said
was the only thing checking the scope, and it happened.

**D-023-06 — The `test_mut_*` family is renamed, not deleted.**
Twenty-three files, 9,786 lines. The generated mutation lane derives its surface from
`chain.TABLE` and mutates `hooks/` only; most of this family tests modules that surface never
touches, so the prefix claims membership in an apparatus that no longer exists.

**Rationale**: the plan asked for the deletion on the grounds that the family no longer earns
its name. It does not earn its name, and it does earn its lines: these are ordinary tests of
ordinary modules, and deleting them deletes coverage that nothing else provides. Renaming
removes the false claim at no cost, which is what the plan was actually buying.

**D-023-07 — Windows keeps the wheel lane and stays out of the suite lane. `requires-python` is
kept at `>=3.11` and the test that made it a lie is repaired.**

**Rationale**: on Windows the wheel installs and all ten verbs answer; what fails is 183 tests
carrying POSIX assumptions, and a permanently red lane teaches everybody to ignore it. The
number is written into the workflow beside the disabled arm, so it is a finding rather than an
exemption. Separately, `pyproject.toml` declares `>=3.11` while a test asserts argparse's usage
wrapping, which changed in 3.14 — that is one brittle test, not an incompatible package, so the
test stops asserting the wrapping and the declaration stops being false.

**D-023-08 — The nine surviving generated mutants are closed with tests.**

**Rationale**: the lane passes at 90.9% against a floor of 90, which is one survivor of margin.
The floor only rises, so the margin is the whole safety of the lane, and the nine are named by
file and line.

## Challenged once

*The strongest case against this document is that it is one signature buying eight decisions,
which is the shape of a blanket approval.* It is, and the mitigation is that every decision is
written out with the measurement that produced it, and each lands in its own commit, so
overturning one costs one revert and does not disturb the others. A blanket approval is one
that cannot be taken apart afterwards; this one can.

*The second is D-023-04, where the agent both withdraws its own objection and then refuses the
work anyway.* Both halves are stated because both are true, and the second does not depend on
the first: if the measurement is wrong — if something does load `specs/` per session — the
refusal falls, and the command that would show it is given below.

## Assumptions and unresolved risks

- It is assumed that the owner's instruction covers approving `specs/016` and `specs/018` at
  today's bytes by approving this document, because this document names them and their
  digests. If he means it more narrowly, the two lines are here to strike out.
- Renaming twenty-three test files may trip a gate that pins a test path by name. Unknown
  until run; the plan sequences it so the failure is visible before anything depends on it.
- The 183 Windows failures are measured once, on one runner. Four classes are named; the tail
  is not.

## Examples somebody can check

Given the approval reader, When it runs after this lands, Then the newest record wins for each
file and no waiver list is left in the test. Checked by
`uv run pytest -q tests/test_record.py -k approval`, which passes with
`grep -c 'known = {' tests/test_record.py` returning 0.

Given task 8 of specification 022, When its own evidence command is run, Then it selects the
test that proves it rather than deselecting everything. Checked by
`uv run pytest -q tests/test_contracts.py -k anchored`, which exits 5 today and 0 after.

Given the twenty-three renamed test files, When the suite is collected before and after, Then
the number of collected tests is identical. Checked by
`uv run pytest -q tests/ --collect-only | tail -1` on both sides of the commit.

Given a session started in this repository, When every hook is read, Then none of them loads
`specs/`. Checked by `grep -rn 'specs/' hooks/*.py`, which prints nothing — this is the
measurement D-023-04 rests on, and the command that overturns it if it ever prints something.

Given the generated mutation lane, When it runs after this lands, Then its score clears the
floor by more than one survivor. Checked by `python tests/mutation.py`, which prints the score
and the floor on one line.

Given Python 3.14, When the suite runs, Then the test that pinned argparse's wrapping passes.
Checked by `uv run --python 3.14 pytest -q tests/` against
`grep -n 'requires-python' pyproject.toml`, which claims `>=3.11`.

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
