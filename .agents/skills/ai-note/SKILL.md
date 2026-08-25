---
name: ai-note
description: >-
  Saves a finding that took real time to reach — a non-obvious behaviour, an integration
  trap, a workaround and the reason it is needed — as committed markdown, stamped with the
  commit and the file patterns it describes so that it can be detected as stale later.
  Searches those notes too. Trigger for "save this", "note that", "remember this", "we
  worked this out the hard way", "do we have notes on", "what did we find about". Not for
  project decisions — use /ai-spec, which is where a decision has its context. Not for
  documentation somebody reads to learn the system — that belongs in the repository's docs.
license: Apache-2.0
compatibility: needs git
disable-model-invocation: true
---

# Save what it cost you to find out

## What it produces

`docs/notes/<slug>.md`, committed, with a header that lets rot be detected.

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
6. Searching: `git grep` over `docs/notes/` is the whole query engine, and it is enough at
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
