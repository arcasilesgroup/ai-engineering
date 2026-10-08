---
name: verify-feature
description: >-
  Verify that a feature as built actually matches what was asked for — catching
  requirements that were quietly dropped, built differently than specified, or built
  without being asked for. Use this whenever you are partway through or wrapping up a
  feature and about to call it done, and whenever the user says "does this match the
  PRD/spec", "did we drift", "is this what I asked for", "check this against the
  requirements", "verify the feature", "did you build everything", or reviews work
  before a commit or PR. Also reach for it unprompted at the midpoint of any
  multi-step feature, before more code gets stacked on a wrong foundation. This
  answers "did we build the right thing" — it is not the code-quality gate (lint /
  typecheck / tests) and not `security-review`.
---

# Verify feature against requirements

Code review asks "is this code correct and safe?" This asks a different question that
review reliably misses: **is this the thing we agreed to build?** A dropped requirement
compiles. A near-miss substitution passes lint. An unasked-for feature has no failing
test. Nothing in the normal toolchain notices, which is why drift is usually found by a
human weeks later.

Your output is a verdict per requirement, backed by evidence, plus a list of gaps. You do
not fix anything until the user picks what to fix.

## 1. Establish the contract, and write it down before reading the code

First settle **which** feature you're verifying, since the answer scopes everything else.
Usually it's obvious from the conversation. When invoked cold, infer it from the branch
name and the diff against the base branch — a branch called `feat/mobile-channel-ui`
touching the channel views names its own subject. If the diff spans two unrelated
features, say so and ask which one rather than blending them into one confusing report.

You cannot measure drift without a fixed thing to measure against. Find the contract in
this order:

1. **A written spec this project already keeps.** Look for the project's own
   convention before assuming there isn't one: a PRD or spec directory
   (`docs/features/`, `docs/specs/`, `docs/rfcs/`, `adr/`), a `design.md`, or a
   location named in `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, or `AGENTS.md`.
   If a document exists for this feature, it *is* the contract. Prefer it over
   conversation memory even when the two disagree — disagreement is itself a
   finding, handled in §5.
2. **A file or ticket the user points you at** — a spec, an issue body
   (`gh issue view`, `glab issue view`), a linked design doc.
3. **The conversation** — the user's own earlier messages. The most common case,
   since most branches have no written spec.

If the contract comes from the conversation rather than a file, **write the requirement
list out and show it to the user before you look at a single line of the
implementation.** This ordering is the most important step in the skill, and it is worth
the extra round trip. Read the code first and you will unconsciously reconstruct
requirements that the code happens to satisfy — you will look at a `channels` filter and
remember the ask as "filter posts", when it was "filter posts *and* persist the choice
per user". Freezing the list first makes that failure impossible instead of merely
discouraged. It also gives the user a cheap chance to say "no, that's not what I meant"
before you spend effort verifying the wrong contract.

Scan the whole session for requirements, not just the opening message. Requirements
arrive as corrections ("no, moderators too"), as constraints ("don't touch the webhook"),
and as offhand asides that were never restated. A mid-session correction *supersedes* the
original — record the latest version and note that it changed.

## 2. Decompose into falsifiable claims

Turn the contract into atomic statements that can each be shown true or false by pointing
at code. Vague requirements are where drift hides, so sharpen them:

- Not "admins can manage products" → "an `owner`/`admin` can create, edit, publish, and
  delete a product from `/admin/store`, and each write re-checks role server-side."
- Not "it should be fast" → ask the user what number they meant, or mark it
  `UNVERIFIABLE` with the reason. Never quietly score a vague requirement as met.

Cover the categories the requirement touches. If the contract is a written spec, its
section headings are a ready-made checklist; otherwise work through the ones that apply
to this system. The project's own invariants count as requirements even when unstated:

- **Behavior and flow**, including the states people forget — empty, loading, error,
  offline, unauthenticated, permission-denied, and partial-failure
- **Data model and migrations** — new fields, backfills, and backwards compatibility
  with what is currently deployed
- **Access control** — who can reach it, and where that is enforced server-side
- **Side effects** — anything the feature triggers elsewhere: payments, emails,
  webhooks, jobs, cache invalidation, analytics
- **Interface conformance** — which design surface or style guide governs the UI
- **Anything the contract explicitly deferred** — a non-goal is a requirement

Also list the **non-goals** as claims to check in reverse: "there is no cart", "physical
products are not supported". These are the requirements most often violated by accident.

## 3. Verify each claim by tracing, not by pattern-matching

A claim is met when you can name the file and line that satisfies it *and* show the code
is actually reachable. The gap between "code exists" and "feature works" is where most
false verification happens, so hunt specifically for:

- **Orphans.** A server action nobody imports, a route nothing links to, a column nothing
  writes, an admin form that never renders. Trace from the real entry point — a sidebar
  item, a route file, a form's submit handler — to the effect. This is the single most
  common way a feature looks finished and isn't.
- **Stubs and happy paths.** A handler that returns early, a `TODO`, a success branch
  with no error branch, a state the spec named (empty list, expired session, failed
  payment) that has no code.
- **Near-miss substitutions.** The most dangerous category, because it reads as done. The
  spec said a per-item discount percentage; the build accepts a pasted external price ID.
  Both are "pricing". Only one is the requirement. When something in the code is
  *adjacent* to the requirement, assume divergence until you've shown they're equivalent.
- **Claims the spec makes about itself.** A good spec names specifics — which auth
  helper each path uses, which caches get invalidated, which tables the writes touch,
  what the permission model is. Those are checkable promises, so verify them as
  written rather than treating them as narration. Two that fail quietly and are worth
  checking every time: a **missing cache invalidation** after a write, which serves
  stale data with no error anywhere; and a **write to a resource whose access control
  lives in application code rather than in the datastore**, where a missing
  server-side check is a real authorization hole even though every test passes.

Read the actual diff (`git diff <base>...HEAD`, `git status` — resolve `<base>` to the
first of `origin/main`, `origin/master`, `main`, `master` that exists) so you know what this change
touched, but don't stop there — a requirement can be unmet because of code that *wasn't*
written, and that never appears in a diff.

## 4. Report

A status table, then the deltas, then the things needing a decision. If this project
already has a verification-report idiom of its own, match that instead — a report that
looks like the ones around it gets read.

```markdown
## Verification: <feature> — <checkpoint | final>
Contract: <path to PRD, or "reconstructed from conversation (frozen above)">

| # | Requirement | Verdict | Evidence |
|---|---|---|---|
| 1 | Admin can delete a record; role re-checked server-side | MET | `src/admin/actions.ts:88` (`requireAdmin`) |
| 2 | Per-item discount percentage | DIVERGED | build takes a fixed external price ID instead — `src/api/pricing.ts:41` |
| 3 | Category filter on the listing page | MISSING | no `category` field; no filter in `src/views/list.ts` |

### Gaps to close
1. …  (ordered by what breaks worst, not by requirement number)

### Needs your decision
- <where build and contract disagree and the build might be the better answer>

### Couldn't verify statically
- <claim> — would need <running the app / a test / your confirmation>
```

Verdicts, and why each is separate:

| Verdict | Meaning |
|---|---|
| `MET` | Built, evidence found, path traced to a real effect |
| `PARTIAL` | Built but incomplete — happy path only, or an alternate state the spec named is missing |
| `DIVERGED` | Built differently than specified. Not automatically wrong; needs a decision |
| `MISSING` | Specified, believed done, absent |
| `PENDING` | Not built yet, and that's expected at this point in the work |
| `UNASKED` | In the code, not in the contract — scope creep, or something the spec deferred |
| `UNVERIFIABLE` | Can't confirm by reading. Say what would confirm it |

`PENDING` vs `MISSING` is what makes a mid-implementation checkpoint usable. Halfway
through a feature most requirements legitimately aren't built, and reporting those as
failures makes the whole report noise the user learns to skip. At a checkpoint, only call
something `MISSING` if the work so far implies it was supposed to be done — otherwise
it's `PENDING`, and the useful signal is the small set of things already built *wrong*,
because those are what later code will be stacked on.

Be honest about the limits of reading code. `UNVERIFIABLE` with a clear "here's what
would settle it" is worth more than a confident `MET` that turns out false — an inflated
pass rate trains the user to stop trusting the report, which costs more than the gap you
were papering over. Note also that this skill deliberately doesn't run the app, so
anything that depends on runtime behavior belongs in that section.

## 5. Fix only what the user approves

Present the report and stop. Then, for what they pick, keep one distinction in front of
you: **drift can mean the code is wrong, or it can mean the contract is stale.**

If the user changed their mind mid-session, or the build found a better answer, then the
code is right and the *spec* is the thing to update. Blindly "fixing" code back to a
superseded requirement destroys good work and is worse than not checking at all. So for
every `DIVERGED` item, ask which way it resolves before touching anything. `MISSING` and
`PARTIAL` are usually genuine code gaps; `UNASKED` resolves either by removing the code
or by adding it to the spec — the user's call, since they may have asked for it in a
channel you can't see.

When a resolution updates the spec, respect whatever lifecycle this project has for
its docs. A common one: the spec is living until the feature ships, and afterwards the
durable facts graduate to the places people actually read — the agent-rules file, a
gotchas or learnings doc, the schema reference — rather than staying buried in a spec
nobody opens again. Follow the project's convention if it has one; do not invent a new
document if it does not.

After fixing, re-verify the items you changed. A fix that introduces a new gap is common
enough that closing the loop is worth it.

## When there is no written spec at all

Don't refuse to work — reconstruct from the conversation per §1 and proceed. But if the
feature is substantial and the project keeps specs somewhere, offer to write the frozen
requirement list there in the project's existing format. That turns a one-off
verification into a contract the next session can verify against, which is the whole
point.

If the project keeps no specs, offer once and drop it. Adding a lone document to a repo
with no convention for it usually means it goes stale unread, and a stale contract is
worse than none — it makes the next verification confidently wrong.
