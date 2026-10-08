---
name: spec-extract
description: >-
  Turn an unwritten agreement into a checkable spec — pull the requirements out of this
  conversation, a ticket, a pasted thread, or a design discussion, and write them to the
  project's spec file as numbered, falsifiable claims. Use before starting a feature, when
  the user says "write this up", "turn this into a spec", "make a design doc", "what did we
  agree", "capture the requirements", or "create design.md"; when a review skill halts
  because no spec exists; and at the point a conversation has produced enough decisions
  that the next session would lose them. This produces the contract that `design-check`
  and `verify-feature` measure against — it does not verify anything itself.
---

# Extract a spec from what was actually agreed

`design-check` halts without a spec. `verify-feature` falls back to reconstructing one
from conversation memory, which is the weakest contract it supports. Both problems are the
same problem: the agreement exists, but only in a chat log that nobody will re-read and
that the next session cannot see.

Your job is to move it out of the conversation and into a file, without inventing
anything. The single failure mode of this skill is a confident spec containing
requirements nobody ever asked for — that is worse than no spec, because every downstream
verification then measures against fiction and reports it as fact.

## 1. Do not read the implementation first

If code already exists for this work, **do not read it before you have drafted the
requirement list.** You will reconstruct requirements that the code happens to satisfy,
and produce a spec that is guaranteed to pass its own check. This is the same ordering
rule as `verify-feature` §1 and it matters more here, because the artifact persists.

There is one legitimate exception, and it must be labeled. When the goal is explicitly to
document something already built — a legacy subsystem, an inherited codebase — you are
writing a **descriptive** spec, not a prescriptive one. Say so in the header, because a
descriptive spec cannot detect drift that already happened; it canonizes it.

## 2. Gather sources in order of authority

1. **The user's own messages in this session** — the most common source, and the one that
   disappears when the session ends. Read the *whole* session, not the opening ask.
2. **A ticket or issue** — `gh issue view`, `glab issue view`, a linked doc, a pasted
   thread. Quote it rather than paraphrase where the wording is load-bearing.
3. **Existing partial docs** — a half-written `design.md`, an ADR, a README section, a
   TODO list. These are prior agreements; do not silently overwrite them.
4. **Project invariants that constrain this work** — `CLAUDE.md`, `AGENTS.md`,
   `CONTRIBUTING.md`, the schema, the auth convention. These are requirements even though
   nobody restated them for this feature.

Requirements do not arrive as requirements. Scan specifically for the three shapes people
never label:

- **Corrections** — "no, moderators too". A correction *supersedes* the original. Record
  the latest version and note that it changed, so the earlier form does not resurface in
  someone's memory as an unmet requirement.
- **Constraints** — "don't touch the webhook", "has to work on the free tier". These
  become non-goals or explicit boundaries, and they are the requirements most often
  violated by accident.
- **Offhand asides** — a number mentioned once, an edge case named in passing, a name for
  something. If it was said once and never contradicted, it is in.

## 3. Write each requirement as a falsifiable claim with a stable ID

The output has to be checkable by an agent that will never see this conversation, so every
requirement is a statement that can be shown true or false by pointing at code.

- Not "admins can manage products" → "an `owner` or `admin` can create, edit, publish and
  delete a product from `/admin/store`, and each write re-checks role server-side."
- Not "it should be fast" → get the number, or record it under **Open questions** with the
  reason it is unspecified. Never let a vague requirement into the numbered list; it will
  be scored as met by whatever exists.

**Give every requirement a stable ID (`R1`, `R2`, …).** This is not cosmetic.
`design-check` produces a requirement-by-requirement traceability table, and stable IDs are
what let two reviews weeks apart be compared, and what lets a fix reference the thing it
closes. IDs are append-only: when a requirement is dropped, mark it `WITHDRAWN` in place
rather than renumbering the ones after it.

Cover the categories the work touches — the ones people forget are where drift hides:

- **Behavior**, including empty, loading, error, offline, unauthenticated,
  permission-denied and partial-failure states
- **Data model and migrations** — new fields, backfills, compatibility with what is
  currently deployed
- **Access control** — who can reach it, and where it is enforced server-side
- **Side effects** — payments, emails, webhooks, jobs, cache invalidation, analytics
- **Interface conformance** — which design surface or style guide governs the UI
- **Non-goals** — what this deliberately does not do

## 4. Mark provenance on every line, and never launder an assumption

Each requirement carries one of three provenance tags. This is the core of the skill.

| Tag | Meaning |
|---|---|
| `stated` | The user or the ticket said this, more or less in these words |
| `implied` | Follows necessarily from something stated — the empty state of a list they asked for, the migration a new column needs |
| `assumed` | You supplied it. Nobody said it. It is probably right and it is still yours |

`implied` is a real category and worth keeping — a spec that omits the error state because
nobody spoke it aloud is a spec that will pass while the feature breaks. But the tag makes
the reach visible.

`assumed` items get surfaced explicitly: **list them back to the user before you write the
file** and ask them to confirm, correct or delete each one. This is the round trip that
makes the whole artifact trustworthy. An assumption that survives review becomes `stated`;
one the user rejects is deleted, not softened.

If you find yourself unable to tag something, that is the tell that you are writing a
requirement out of your own sense of how the feature should work. Move it to **Open
questions**.

## 5. Write it where the project already keeps specs

Find the convention before inventing one: a spec directory (`docs/features/`,
`docs/specs/`, `docs/rfcs/`, `adr/`), an existing `design.md` or `DESIGN.md`, or a location
named in `README.md`, `CONTRIBUTING.md`, `CLAUDE.md` or `AGENTS.md`. Match the existing
format and naming — a document that looks like its neighbours gets read.

If the project has no convention at all, default to `design.md` at the repo root, because
that is the first path `design-check` and `full-review` look for, and say that you chose
it. If the project keeps no docs and the user does not want one, output the spec into the
conversation instead and stop — do not add an orphan file to a repo with nowhere for it to
live. A stale contract is worse than none: it makes the next verification confidently
wrong.

Never overwrite an existing spec. Read it, merge, and mark what changed.

## 6. Output shape

```markdown
# <Feature> — design

**Status:** draft | agreed | shipped
**Type:** prescriptive (written before the build) | descriptive (documents existing behavior)
**Sources:** <session <date> · issue #NN · docs/rfcs/0004.md>
**Last updated:** <date>

## Goal
<two or three sentences: the user-visible outcome and who it is for>

## Requirements

| ID | Requirement | Provenance | Notes |
|---|---|---|---|
| R1 | An `owner`/`admin` can delete a product from `/admin/store`; role re-checked server-side | stated | |
| R2 | Deleting a product invalidates the storefront listing cache | implied | R1 has no effect for readers otherwise |
| R3 | Deletion is soft — row retained with `deleted_at` | assumed | **confirm:** hard delete may be intended |
| R4 | ~~Bulk delete~~ | stated | WITHDRAWN 2026-07-14 — descoped mid-session |

## Non-goals
- No cart. Explicitly out of scope for this feature.
- Physical products are not supported.

## Constraints
- Do not modify the Stripe webhook handler.

## Open questions
- What is the acceptable latency for the listing page? "Fast" was the only bar given.
```

Requirements go in one flat numbered table, not nested by theme. Nesting reads better and
verifies worse — a traceability table needs one row per checkable claim.

## 7. Hand off

When the file is written, say what it unlocks, in one line each:

- `design-check` now has something to check against, and `full-review` will stop skipping
  that lane.
- `verify-feature` will prefer this file over conversation memory — including over *your*
  memory, which is the point.

Then offer, once, to run one of them. Do not run a review automatically: the spec is a
proposal until the user has read it, and verifying against an unreviewed spec produces
confident results about the wrong contract.

## Keeping it alive

A spec is living until the feature ships. Afterwards, the durable facts — the permission
model, the schema, the invariant everyone needs to know — are worth graduating to the
places people actually read: the agent-rules file, a gotchas doc, the schema reference.
Follow the project's own lifecycle for that if it has one. Do not leave the only copy of a
load-bearing invariant in a spec nobody opens again.
