---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0029"
title: "The template carries Grill and Council; the sidecar convention dies forward; the critic step reads both shapes, refuses emptiness, prompt and malformed ran: lines with fixtures, scopes no-authority to section bodies, and returns the approval record to docs/adr/."
date: "2026-08-28"
spec: "045"
status: "proposed"
supersedes: ""
---

# 0029. The template carries Grill and Council; the sidecar convention dies forward; the critic step reads both shapes, refuses emptiness, prompt and malformed ran: lines with fixtures, scopes no-authority to section bodies, and returns the approval record to docs/adr/.

## Context and problem statement

A full spec cycle wrote up to five files beside the decision: `spec.md`,
`challenge.md`, `council.md`, `council.html` and `approval.md`. Measured: 3,445 lines
of challenge, 4,290 of council, 203 KB of HTML and a dossier — of which the only
mechanical readers were one counting script and one no-authority test, and neither
opens a finding. 044's cycle spent 70 minutes of challenge and 36+ minutes of council
to produce corrections that went into `spec.md` by hand anyway, and a reviewer had to
open five files to reconstruct one decision.

## Considered options

1. **Critics inside the spec**: the grill folds into `## Grill`, the single-pass
   council into `## Council`, the critic step (`just council`) reads both file shapes,
   and the approval returns to `docs/adr/`.
2. **Keep the sidecars, cut the ceremony** (drop the HTML, cap the sweep): zero
   migration, five files per decision forever, and an approval no command validates.
3. **Parallelise the critics** without shrinking them: wall-clock relief on paper,
   costs multiplied cold-context, artifact surface untouched.

## Decision outcome

Chosen option: **1**, because the independence and the cross-read that the measured
evidence supports live in the forks, not in the file boundary — and option 2 keeps a
second and third home of one decision, which is the failure rule 4 names, while
option 3 buys an unmeasured benefit with machinery rule 11 never asked for.

## Consequences

Better: one decision, one file; the gate counts sections the way it counted files;
the approval lives where `madr.validate` finally reads it. Worse: 114 references to
the retired classes migrate in one family; the lens pass will read earlier critic
rounds inside the document (66.5% channel, reopened if it shows); the `ran:` minutes
are visible, not audited. Written history is not rewritten — the historical sidecars
and the fifteen dossiers stay exactly where they are.
