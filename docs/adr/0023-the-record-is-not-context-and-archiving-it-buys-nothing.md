---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0023"
title: "The record is not context, and archiving it buys nothing"
date: "2026-08-21"
spec: "023"
status: "proposed"
supersedes: ""
---

# 0023. The record is not context, and archiving it buys nothing

## Context and problem statement

Wave 3 of the subtraction plan archives eight shipped specifications: out of the tree, kept
only in git history. Measured today, the eight oldest shipped specifications are **4,115
lines** across their `spec.md` and `plan.md`.

The plan gave one reason for wanting them gone, and it was stated as a fact about cost:
*"ése es contexto que el agente carga en cada sesión — lo que de verdad estás pagando"*.

This was escalated to the owner rather than done, on the grounds that `CONSTITUTION.md`
forbids it. That escalation was wrong, and the reason it was wrong matters more than the
outcome.

## Considered options

1. **Archive them, having first amended the Constitution.** This was the shape the escalation
   proposed. It amends a rule that never applied in order to permit work whose benefit was
   never measured.
2. **Archive them, the Constitution having been misread.** Correct on the rule and still
   wrong, because it acts on an unmeasured premise.
3. **Withdraw the constitutional objection and refuse the work on measurement.**

## Decision outcome

Option 3, in two independent halves. Either half alone settles it, and both are stated
because both are true.

**The constitutional objection is withdrawn.** `CONSTITUTION.md` says: *"Never touch a user's
`AGENTS.md`, `CONSTITUTION.md` or `specs/` after writing them once"*. The governing words are
*a user's*. It binds what this product does inside somebody else's repository — the whole
point of a framework that writes files into a tree it does not own — and says nothing about
what this repository does with its own record. No test in this tree reads it the other way.
Claiming it did was a misreading, and a misreading that blocks work is not a safe error: it
spends an owner's attention on a permission he was never being asked for.

**The archive is refused on measurement.** Both of its benefits are zero:

- *It is not per-session context.* `grep -rn 'specs/' hooks/*.py` returns nothing. No hook
  loads the record; `AGENTS.md` names the directory and does not read it. The 4,115 lines are
  not paid for in any session, so the saving the plan priced does not exist.
- *Tree size is no longer a control.* `specs/021` deleted `contract.REPO_CEILING` on the
  finding that a ceiling obliged to follow the tree it bounds cannot refuse anything.
  `git grep -n REPO_CEILING -- src tests hooks justfile` returns nothing.

And the cost is not zero. `tests/test_record.py` asserts `target.is_file()` for every file an
approval record names, over all eleven rows. Moving a specification out of the tree turns
that red for every record that approves one, and the repair for that would be teaching the
approval reader to follow files into an archive — machinery built to serve a saving that
measures zero.

## Consequences

The tree keeps 4,115 lines it does not need in order to run, and that is the honest state:
they are a record, records are read by people rather than loaded by machines, and this one
is the evidence that the work happened.

This decision is reversed by one command producing a different answer. If
`grep -rn 'specs/' hooks/*.py` ever prints a line, the premise it rests on is gone and the
archive becomes worth pricing again.

What this does not settle is whether eight shipped specifications should be *shorter*. That
is a different question from whether they should be elsewhere, nobody has measured it, and
nothing here forecloses it.
