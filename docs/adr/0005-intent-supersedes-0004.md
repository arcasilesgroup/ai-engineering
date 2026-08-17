---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0005"
title: "Intent supersedes the boundary of ADR 0004"
date: "2026-08-13"
spec: "010"
status: "accepted"
authority_role: "repository owner"
approval_ref: "ae523990"
approved_at: "2026-08-15T03:54:12Z"
supersedes: "0004"
---

# 0005. Intent supersedes the boundary of ADR 0004

## Context and problem statement

ADR 0004 remains correct about document moulds owned by another repository: importing one
would couple this framework to somebody else's format, duplicate policy and recreate the
sprawl this project exists to remove. Its evidence and that prohibition still matter.

The canonical `.ai/intent.md` introduced by Spec 010 is not such a mould. The framework
owns one short, closed and versioned mechanism; the user owns the record in their
repository. It states constraints, current facts, variables and intended outcomes, and it
links to governed records instead of copying their prose. No external repository supplies
its sections or can make the contract stale by changing its own document format.

ADR 0004 predates that distinction. Its refusal of an imported mould can therefore be read
as refusal of any native Intent contract. The ambiguity must be removed without editing
the evidence, costs or reasoning that led to the earlier decision.

## Considered options

1. **Keep ADR 0004 as the only decision about Intent.** This preserves history but leaves
   the broad reading unresolved and conflicts with the native Intent required by Spec 010.
2. **Rewrite or delete ADR 0004.** This makes the records appear consistent, but erases the
   observed failure that justifies the boundary and makes the new design look older than it
   is.
3. **Preserve ADR 0004 and supersede only its decision boundary.** Keep the external-mould
   prohibition and historical file intact while distinguishing it from a minimal native
   schema whose instance belongs to the user.

## Decision outcome

Recommend option 3.

If accepted, this record would replace only the ambiguous boundary: a document mould owned
by another repository still never enters this framework, while a framework-owned minimal
Intent contract and a user-owned `.ai/intent.md` instance are permitted. The earlier
evidence, the rejection of copied content and the rule against mirrors remain in force.

This MADR is `accepted`. Its authority came through a valid status transition: the
repository owner approved it, the approval is written down where `approval_ref` points, and
the record carries the role, the reference and the timestamp the schema requires together or
not at all. Accepting it approves this recommendation; it still authorizes no work and
accepts no risk, both of which have their own records.

## Consequences

Better, if accepted: the framework can govern work from a short native Intent without
importing another repository's vocabulary, templates or lifecycle. Readers can follow the
supersession edge and see both why external moulds stay out and why this Intent is different.

Worse: the boundary now takes two records to understand, and the distinction depends on the
native Intent remaining small and mechanism-owned rather than becoming a catalogue of
somebody else's content. ADR 0004 remains unchanged as historical evidence; preserving it
also preserves language that can be misread when viewed without this proposal.

Open risk: later additions could turn the minimal Intent into the kind of mould this record
excludes. Its closed schema, canonical home and relation checks reduce that risk but do not
accept it. A second risk is that the `supersedes` edge could be mistaken for approval: it is not one,
and this record's authority comes from its transition and from nothing else.
