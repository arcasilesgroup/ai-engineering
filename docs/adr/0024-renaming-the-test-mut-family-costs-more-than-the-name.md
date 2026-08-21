---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0024"
title: "Renaming the test_mut family costs more than the name is worth"
date: "2026-08-21"
spec: "023"
status: "accepted"
authority_role: "repository owner"
approval_ref: "spec-023-2026-08-21"
approved_at: "2026-08-21T12:00:00Z"
supersedes: ""
---

# 0024. Renaming the test_mut family costs more than the name is worth

## Context and problem statement

The subtraction plan asked for twenty-three `tests/test_mut_*.py` files to be deleted. That
was refused: they are ordinary tests of ordinary modules and deleting them deletes coverage
nothing else provides. `specs/023` proposed the middle course in D-023-06 — rename them, so
the prefix stops claiming membership in an apparatus that was removed — and the owner
approved it.

Executing it produced a measurement that was not taken before the decision was written.

`grep -rn test_mut_` outside the files themselves returns **51 references**:

| where | references | executable |
|---|---|---|
| `specs/*/spec.md`, `specs/*/plan.md` | 40 | 7 |
| `docs/requirements.toml` | 13 | 13 |
| `tests/test_contracts.py`, `src/ai_engineering/spec.py` | 3 | 3 |

The thirteen in `docs/requirements.toml` are `evidence = "pytest tests/test_mut_wiring.py -k
router"` and its siblings, and `tests/ledger_run.py` executes them. Those are repairable in
the same commit, because that file is not signed.

The forty inside `specs/` are not repairable. Editing a signed specification voids the
approval that covers it, which is the constraint D-023-02 had just finished working around
by moving the unsigned document instead of the signed one. Seven of those forty are runnable
commands. Renaming would break all seven, in documents that cannot be corrected — which is
the exact defect this same run repaired one commit earlier, seven times over.

## Considered options

1. **Rename, repair the thirteen, leave the forty stale.** Trades one naming smell for seven
   evidence commands that exit 4 inside approved documents. Worse on its own terms.
2. **Rename, and edit the specifications too.** Voids the approvals on six specifications to
   fix a prefix. Not the agent's to do, and not worth doing if it were.
3. **Keep the name.**

## Decision outcome

Option 3. D-023-06 is overturned by a measurement taken after it was approved.

The benefit being bought was that `test_mut_` claims an apparatus that no longer exists.
That claim is weaker than it looked when D-023-06 was written. `mut` names tests written to
kill deliberate defects, and this repository still generates deliberate defects — the
generated half of `tests/mutation.py` produces them on every run of the `guards` lane. What
was deleted was mutmut and `just mutate`, one instrument, not the practice. So the prefix is
imprecise rather than false, and the price of precision is seven broken commands in signed
documents and forty stale paths in the record.

Nothing about the earlier refusal to delete changes. The twenty-three files are 9,786 lines
of tests that assert one decision at a time, in modules whose sibling suites exercise them
through whole objects and reach only the paths a plausible input happens to take. They stay.

## Consequences

A reader meeting `tests/test_mut_acceptance.py` has to open it to learn what it is. Its first
line says so — *"Every refusal `_validate_field` and `validate_record` can make, one at a
time"* — and every file in the family opens the same way, which is the cheapest form this
information can take.

This is the second decision in this run overturned by measuring it during execution rather
than before, after D-023-04's constitutional objection. Both were caught by doing the work
rather than by reviewing the plan, which is an argument for short tasks and against long
planning, and it is worth saying out loud that a plan approved in one reading is a plan whose
premises were checked once.

Reversing this needs the forty references gone or the specifications unsigned. Neither is
likely, so the honest reading is that this name is now permanent.
