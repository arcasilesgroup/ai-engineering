---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0038"
title: "Harvest patterns, never the external file's prose."
date: "2026-08-29"
spec: "048"
status: "accepted"
authority_role: "repository owner"
approval_ref: "54bdfa50"
approved_at: "2026-08-29T12:09:24Z"
supersedes: ""
---

# 0038. Harvest patterns, never the external file's prose.

## Context and problem statement

Spec 021 established that external skill text may enter this Apache-2.0 wheel only as
MIT prose with a NOTICE naming its author. The `handshake` skill audited in report 025
carries no license, no author, and no public origin (zero code-search hits on its
distinctive phrases, three phrases tested). Its three intake mechanisms are worth
having; copying its sentences into shipped, distributable prose would encode an
attribution debt the wheel cannot discharge, and vendoring an untraceable file into
instruction position would let an unknown author's wording steer every future spec
interview. This decision constrains every later harvest: the promotion test is whether
the source's license can be named, not whether copying is technically possible.

## Considered options

1. **Rewrite from the decisions, in this tree's voice; borrow no sentences.** The
   mechanisms are ideas — a live draft, a read-back gate, fact-versus-decision routing —
   and ideas are not copyrightable expression. Costs a rewrite and one discipline: the
   rewriter must not transplant the file's examples. This is what D-048-02/03/04 shipped
   through `references/intake.md`, with the pass/fail example pair rebuilt on a
   different domain (bread offcuts at a market, not cocoa bags to cafes).
2. **Vendor the file with a "provenance unknown" notice.** Rejected: an unknown provenance
   is not a license, and a notice does not create one; it also contradicts the CONSTITUTION's
   never-mirror rule by importing a second copy of a governed domain.
3. **Copy sentences selectively, trusting fair use.** Rejected: fair-use judgement is a
   lawyer's decision with a named client, this repository is a wheel distributed to
   strangers, and rule 12 says a decision that always comes out the same way — here,
   no — becomes a rule, not a case-by-case call.

## Decision outcome

Option 1, as a standing rule: a harvest of unlicensed or untraceable text takes
mechanisms only, rewritten in this tree's voice, with its examples rebuilt on a
different domain. After the security fork measured the shipped reference against the
external file (its line "who does what, and what happens next" reproduced one rule line verbatim,
plus shared function-word shingles), that rule line was rewritten to name the actor, the
action and the outcome, so the rule holds at the byte level, not only at the planning
level.

## Consequences

Better: the wheel carries no prose whose owner nobody can name, the anti-mirror rule
holds, and future harvests get a one-test rule (can you name the license? if not,
patterns only). Worse: harvest costs a rewrite every time instead of a paste — which is
the point, and the same asymmetry rule 12 buys everywhere else: the discipline is paid
once per mechanism, the legal debt never at all.
