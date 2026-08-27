---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0026"
title: "Specification 027 and its plan are approved at exact digests"
date: "2026-08-25"
spec: "027"
status: "accepted"
authority_role: "repository owner"
approval_ref: "ae523990"
approved_at: "2026-08-25T09:40:45Z"
supersedes: ""
---

# 0026. Specification 027 and its plan are approved at exact digests

## Context and problem statement

`specs/027-standard-skills-contract/spec.md` decides to standardise the sixteen shipped
skill pairs against the skill-smell taxonomy of arXiv:2607.01456. The corpus already meets
the SKILL.md shape; what is missing is a checked contract. The specification turns four
measured smell classes (portable-command, existence-check, forced-output, sourced-statistic)
into rules `contract.audit_one` refuses, applied to both `SKILL.md` and `corpus.md`, and
repairs the sixteen pairs until the audit is green.

The draft was walked by the first half of the cycle. The challenge executed its claims and
found the statistics count was an undercount (≥11 in `ai-council`, not 6), that
`ai-challenge` belongs to the forced-artifact set rather than the weak one, and that the fog
ceiling is enforced by the test suite, not by `contract.audit`. The council (5 lenses +
cross-read, `RAN council=16/8`) confirmed and added two gaps folded into the spec: the repair
surface includes `corpus.md` (which ships the same smells while no rule reads it), and `just`
is the maintainer's local orchestrator, never named by a shipped skill, with the portable
verb being `ai-eng`. The plan is ordered so the contract rules land before any skill is
repaired, so a rule failure is caught early.

## Considered options

1. **Approve the specification and its plan at their exact bytes.** The same binding the
   earlier approval records carry, so a digest move refuses instead of sliding.
2. **Approve the direction and leave the plan open.** Rejected: an unbound plan is an
   unmeasured promise, and this record exists to make the promise checkable.

## Decision outcome

Approved at these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/027-standard-skills-contract/spec.md` | `c006c8c61ba580b641a48924812b94a2317fd27c990e0bcd0be82d7b7c1556f8` |
| `specs/027-standard-skills-contract/plan.md` | `396d398e9fcf9fc64302df27c15e141f541aedac32b245ab5ed82771d6294544` |

The recommendation stands: the standard skills contract is enforced by the script, and a
shipped skill names only portable commands. The plan's six tasks (four contract rules, one
repair of the sixteen pairs, one tree-wide proof) are authorized as the exact work this
record approves; nothing past task 6 is opened, and each task commit runs the gate in the
same chain as the commit.

Everything `0016` recorded about authority still holds and is not restated by reference. This
is the owner's approval of the spec and its plan, not a standing autonomous grant and not an
acceptance of any existing skill smell — those are repaired in the block, not accepted.

## Consequences

The contract's first honest finding is that the corpus held four unruled smell classes. This
approval does not repair them by itself: it authorises a sequenced plan where the rules land
first, the sixteen pairs are repaired second, and a test proves the whole tree reads clean
third. A reader who asks "does the corpus read clean?" gets a checked answer; a reader who
finds a skill that reintroduces a bare repo-specific command or an un-checked reference sees
a red audit. The risk that a contract rule is read as the whole of quality is the risk of
this block, and the plan's task 6 is written to refuse that reading.