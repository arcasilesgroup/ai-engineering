---
name: ai-note
description: >-
  Saves a finding that took real time to reach — a non-obvious behaviour, an integration
  trap, a workaround and the reason it is needed — as committed markdown, stamped with the
  commit and the file patterns it describes so that it can be detected as stale later.
  Searches those notes too. Trigger for "save this", "note that", "remember this", "we
  worked this out the hard way", "do we have notes on", "what did we find about". Not for
  project decisions — use /ai-plan, which is where a decision has its context. Not for
  documentation somebody reads to learn the system — use /ai-write, which is where a
  document gets written against the tree.
license: Apache-2.0
---

# ai-note — save what it cost you to find out

## What it produces

A block in the repository's `DECISIONS.md`, committed, with a header that lets rot be
detected — or, when the finding belongs in the docs, prose handed to ai-write. This skill
creates no file of its own. A note is appended to with a fresh date, never rewritten — the
history a finding records cannot be silently edited.

## Steps

1. The bar is thirty minutes. If it took less than that to work out, it will take less than
   that again, and a note about it is noise that hides the ones that matter.
2. Write the header first — it is what makes the note checkable later:

   ```yaml
   found: 2026-08-08
   commit: 4f2a91c
   describes: ["src/ai_engineering/wiring.py", "policy/surfaces.toml"]
   still_true_when: "the settings writers still merge rather than replace"
   ```
3. Write the note in three parts and no more: what you expected, what actually happened,
   and what to do about it. The middle one is the value; the first one is why anybody will
   believe you.
4. Point at the evidence. The command you ran, its output, the line in the vendor's source.
   A note whose claim cannot be re-checked becomes folklore within a quarter.
5. If the note is a workaround, say what would remove the need for it, and where that fix
   would live — upstream, in our code, or in a decision somebody has to make.
6. Searching: `git grep` over `DECISIONS.md` is the whole query engine, and it is enough at
   this size. Read the header of anything you find and check `still_true_when` before you
   act on it.
7. When a note is no longer true, delete it in a commit that says why. A wrong note is
   worse than no note, because it is trusted.
8. Persistence beyond this repository is not this skill's work and not this framework's.
   The note is committed markdown in the user's own repository, which is where it can be
   reviewed, dated and deleted; whatever memory system the host provides keeps its own copy
   on its own terms. A learning store inside the framework would be a second source of
   truth for something git already versions, and the second one is always the stale one.

## What this is not

- "It was quick but painful, so it deserves a note" — the bar is thirty minutes: a note about something that took less is noise that hides the ones that matter.

## Done when

- The header names a commit and the files the note describes.
- Somebody who was not here could re-run your evidence and reach the same conclusion.
- It reads like a warning to a colleague, not like documentation.

## Routing

In scope — routes here:

- "save this" — the shortest form of the trigger, and the thirty-minute bar decides
  whether it is worth a note at all.
- "write down what we learned, that cost us the whole afternoon" — exactly the bar: a
  finding that will cost the same again if nobody writes it down.
- "note that the settings writer merges instead of replacing, we lost an hour to that" — a
  non-obvious behaviour, written as what you expected, what happened, and what to do
  about it.
- "remember this workaround and why we still need it" — a workaround also records what
  would remove the need for it and where that fix would live.
- "do we have notes on the plugin loader" — searching the notes is part of this skill, and
  `git grep` over `DECISIONS.md` is the whole query engine.
- "what did we find about the hook timeout last time" — the same search, and the answer
  starts by checking the note's `still_true_when` before anybody acts on it.
- "the log is huge, keep the note small" — quote the head and the tail, mark the elided
  middle, and never drop a failure line.
- "turn this session into a skill" — the session has a generalisable process: write the
  contract-clean SKILL.md skeleton naming the steps, never the chat; the craft gate judges
  it.

Not for:

- "and turn that into a section of the handbook" — use /ai-write, because the note stays a
  finding and the handbook gets a document written against the tree.
- "write down the decision and the options we turned down" — use /ai-plan, because a
  decision needs its evidence, its two real options and its authority, and a note is a
  finding, not a decision.
- "onboard me on this module" — use /ai-explore, because that is a tour read out of the
  repository for somebody who has just arrived, not a warning saved from a lost afternoon.
- "check whether the vendor fixed this in the new release" — use /ai-research, because
  that answer is outside this repository and has to come back cited; a note only records
  what we already found here.
- "this is failing again, work out why" — use /ai-debug, because a symptom needs a cause
  at `file:line` and a check that fails for it, not a note.
- "open the PR with this note in it and close the ticket" — not here: the pull request and
  the closing keyword are not this skill's work; it writes and commits the note and
  nothing else.
- "look over the diff that came out of this investigation" — use /ai-verify, because
  judging a change is a separate pass from recording what we learned making it.

## The ai-engineering seam

1. Writes a block in `DECISIONS.md` or hands the prose to ai-write — it does NOT create a
   file of its own: the method travels intact, but the output lives where somebody will
   re-read it, not in a notes folder nobody opens twice. A finding with no home in
   DECISIONS/docs is a finding nobody re-reads.

Source: ai-engineering v1 (own), Apache-2.0.
