---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0031"
title: "Specification 046 and its plan are approved at exact digests"
date: "2026-08-28"
spec: "046"
status: "accepted"
authority_role: "repository owner"
approval_ref: "c783601c"
approved_at: "2026-08-28T13:11:32Z"
supersedes: ""
---

# 0031. Specification 046 and its plan are approved at exact digests

## Context and problem statement

`specs/046-visual-html-records/spec.md` decides that the cycle's review surfaces —
research, spec, plan and the post-build recap — reach the human as self-contained HTML
pages generated in this repository, never through a hosted plan surface. The skills author
fenced `visual` blocks inside the existing Markdown; `ai-eng report view|recap` renders
them through repo-owned templates; every page is handed over as a clickable link beside the
canonical digests it rendered. The visual PR review is a CI recap job that links a
published page — artifact-degraded until the owner decides GitHub Pages. The doctrine
ceiling moves 150 → 180 by the owner's explicit authorization so the four always-on rules
and the link duty join the twelve.

The draft was walked by the first half under the shape spec 045 consolidated. The grill ran
one round of eight questions, six `WRONG` — among them the executed check-injection (a
fenced `**check**:` span rewrites the command `--tick` executes on an approved plan), the
raw-vs-canonical digest error, the dead doctor claim about ignored files, and the plan's
own unparseable field format. The council ran once (five lenses + cross-read) with two
gaps no single lens named — the fence-blind readers and the unclaimed `will` banner — and
`just council` recomputes both counts (2 / 6). Every finding is folded into the Decision
in place; fence-awareness became the plan's precondition task 3, not a risk note.

## Considered options

1. **Approve the specification and its plan at their exact bytes.** The same binding every
   digest approval carries, so a digest move refuses instead of sliding.
2. **Approve the direction and leave the plan open.** Rejected: an unbound plan is an
   unmeasured promise.
3. **Let the build approve its own bytes.** Rejected: authority is a dated artifact a
   validator opens, not a sentence in a transcript.

## Decision outcome

Approved at these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/046-visual-html-records/spec.md` | `b7e60a1af2fe834e336d92fc6b6ea0ef577b22819216a91d9a311a855e2cd779` |
| `specs/046-visual-html-records/plan.md` | `5bbaa617c857ff1cfae5af21fab5d69e56b56a4ef6678d33e418f2446a0d7848` |

The plan digest is the canonical value — the tick column masked — which is the number the
envelope prints and every later `--tick` verifies against. The raw bytes hash
`6bb56b2f…`; the difference is the masking `approval_bytes` performs, not drift.

The plan's fourteen tasks are the exact authorised work: the doctrine room and four
always-on rules, the budget constants, fence-awareness with three refusal tests before any
block is authored, the pages module, the two report subcommands, the shipped gitignore pin,
the banner and capability manifest, the attributed guidance file, the two new skills, the
six cycle-verb edits, the PR-review job degrading to artifacts, and the end-to-end smoke
with the changelog. Tasks 1–3 are the coupled precondition family; nothing past task 14 is
opened by this record; each task commit runs its named check in the same chain.

## Consequences

The gate's answer to "what did the human approve?" stays one file and two numbers, and the
pages now print those numbers, so a stale view is identifiable from the page itself. The
cost this record approves knowingly: the fenced grammar is uglier in the terminal than a
clean plan — bought for the single-digest property, with the named sidecar retreat if it
proves worse; GitHub Pages publication of recap pages waits on the owner's privacy
decision, so the PR job ships as artifact-link only; and whether every build must carry a
recap stays a prompt until three receipts say it is code (rule 12).
