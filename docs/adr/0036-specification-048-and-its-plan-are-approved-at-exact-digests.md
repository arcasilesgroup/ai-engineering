---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0036"
title: "Specification 048 and its plan are approved at exact digests"
date: "2026-08-29"
spec: "048"
status: "accepted"
authority_role: "repository owner"
approval_ref: "54bdfa50"
approved_at: "2026-08-29T11:18:33Z"
supersedes: ""
---

# 0036. Specification 048 and its plan are approved at exact digests

## Context and problem statement

`specs/048-handshake-intake-mechanisms/spec.md` decides that three mechanisms from an
external interview skill (`~/Downloads/handshake/SKILL.md`, audited in
`.ai/reports/025-handshake-skill-harvest.html`) fold into `ai-spec` step 0 rather than
arrive as a 21st skill: a live crash-recovery draft under `.ai/`, a plain-words
read-back the owner confirms before anything is scaffolded, and fact-versus-decision
routing inside intake itself. The mechanism detail lives in a new
`.agents/skills/ai-spec/references/intake.md`; step 0 carries a self-sufficient pointer and the clauses it
must enforce, with an unattended-goal branch that records an unconfirmed read-back
instead of waiting for one (D-048-04, forced by the council's deadlock finding against
`/ai-goal`'s no-wait rule). Harvest is by pattern only: the source file has no license
and no locatable author, so no prose of it is copied (D-048-03).

The draft was walked by the first half under the shape spec 045 consolidated. The grill
ran one round of ten questions; three load-bearing claims were WRONG and folded in
place: the fog arithmetic does not force material out of the skill file (fog is an
average — the inline experiment scores 9.92 green), `ai-verify` does not run the
references convention it was cited for, and the "three pins, four files" edit surface
is two stored pins in one file. A fourth fold corrected the endorsed report number
(9.17 was a raw-body measure; the gate's method gives 8.50) and named the dangling
`validate_intake` pointer in the goal template, whose module shipped in `fae2ac65` and
died orphaned in `14eaaeb1`. The council ran once (five lenses plus cross-read): seven
gaps survived into the fold, the worst being the headless deadlock and an invented
`## Decisions still open` heading that the closed twelve-section template cannot
produce; three findings were deleted, and the two counts this record's spec carries are
the recompute's, not the pass's — `tests/council_counts.py` refused the inflated
total until the bullets matched.

## Considered options

1. **Approve the specification and its plan at their exact bytes.** The same binding
   every digest approval carries, so a digest move refuses instead of sliding.
2. **Approve the direction and leave the plan open.** Rejected: an unbound plan is an
   unmeasured promise — the exact shape the 024 fidelity audit found in specs 035-040.
3. **Let the build approve its own bytes.** Rejected: authority is a dated artifact a
   validator opens, not a sentence in a transcript.

## Decision outcome

Approved at these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/048-handshake-intake-mechanisms/spec.md` | `9211b8f96b1c245a7a2b35d2f328b10673f5c973b95aefb0984f393334001b8c` |
| `specs/048-handshake-intake-mechanisms/plan.md` | `0faae11f48866e1b6b42c878494fb04eff56c37a35efed9bcc058e085bcdc67b` |

The plan row above names the raw SHA-256 of the plan's bytes at signing, which is not
the canonical number `--tick` verifies — an all-`[ ]` plan canonicalises below its raw
sha; 0037 carries the canonical digest execution checks against. This record's first
form claimed the opposite in this sentence; the /ai-review fork caught it and this
record was corrected rather than rewritten silently. The repository owner
approved in conversation on 2026-08-29 ("termina con el lo que hemos hecho y lo que
queda, vamos" as an `/ai-goal` invocation, whose frontmatter makes the invocation the
standing approval) and directed this plan's execution in the same message. The
approval digest was taken after the spec's final fold-in edit (the routable-fact
example regaining its When/Then); the bytes above are the bytes that ship.

The plan's four tasks are the exact authorised work: the skill body with both stored
pins and the new reference in one commit; the goal template's dead-pointer fix; the
critics' verdicts recorded in the spec; and the derived page plus changelog at the
shipped bytes. Nothing past task 4 is opened by this record; each task commit runs its
named check in the same chain. The two decisions marked `[X]` — harvest-by-pattern-only
and the unattended read-back branch — go up as MADRs by `ai-eng decide`.

## Consequences

The record that opened execution for 048. Its plan row names raw bytes that were never
the canonical number `--tick` verifies, and the checks then narrowed to the single
command the tick can execute; 0037 supersedes this record with the canonical digest. The specification
row still names the bytes that are there, and both survive as the account of the
critics' rounds. An approval that moves is not an approval that lied; it is an
approval whose correction is on the record.
