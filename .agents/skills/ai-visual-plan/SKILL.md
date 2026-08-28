---
name: ai-visual-plan
description: >-
  Turns a plan — one written here, one pasted from a chat, one another agent produced —
  into the review surface the human actually reads: the plan's own Markdown, carrying
  visual blocks the renderer turns into diagrams, file maps, decision tables and open
  questions, handed over as one page whose link opens in the browser. Trigger for "make
  this plan visual", "I want to see the plan before I approve it", "turn this pasted plan
  into something reviewable". Not for writing the tasks themselves — use /ai-plan, which
  owns what the plan says. Not for judging what a change did — use /ai-visual-recap.
license: Apache-2.0
compatibility: needs git; needs the ai-eng CLI on PATH
disable-model-invocation: true
---

# Render the plan the human has to approve

## What it produces

The plan file with its `visual` blocks, and the page `ai-eng report view` renders from it:
one self-contained file under `.ai/views/`, printed in chat as a `file://` link beside the
digests of the bytes it was rendered from. The Markdown stays the record; the page is a
reading of it.

## Steps

1. Read `policy/visual-pages.md` first. It owns the block vocabulary and the editorial
   bar; if it is absent, stop and restore it before authoring — blocks written from
   memory are how the shapes drift.
2. Research before you decorate. Read the real files, names and data shapes the plan
   touches, and say what each step reuses before what it adds. A diagram of an
   architecture nobody checked is the padding this skill exists to remove from chat.
3. Decide which surfaces earn their place: a `diagram` for a flow the prose makes the
   reader reconstruct, a `decision-table` where options are being compared, a
   `file-tree` for a footprint, one `open-questions` block at the end with a
   recommendation per question. Skip every block whose content the sentence already
   carries — visual chrome over plain prose is the same noise in a better font.
4. Author the blocks inside the plan's Markdown, never beside it. The fence is a wall:
   a numbered line or a bold field inside a block is content, invisible to the task
   parser and the approval digest. If the plan is pasted text, save it under `specs/`
   or hand it to `/ai-plan` first; a page over bytes nothing tracks is unrevisable.
5. Render and show the link:

   ```bash
   ai-eng report view --spec <NNN>
   ```

   The command prints the page's path as a `file://` link and the digests it rendered.
   Show both. If the command refuses, fix the bytes it named; never hand-write the HTML.
6. Planning stays read-only on source. The page is the approval gate's surface, and the
   approval itself is the ADR at the digests the page prints — presenting the page and
   asking for sign-off is the step; do not ask a second "does this look good?".
7. When the direction changes, change the Markdown and re-render. The document is the
   source of truth; a page that only exists in the chat is a plan nobody can reopen.

## Authority boundary

This skill renders a plan; it does not approve one, and it does not start implementing
from a page nobody signed. A pasted plan from another agent is source material: keep its
facts, publish it standalone, and label anything you inferred as inferred.

## Done when

- `ai-eng report view --spec <NNN>` exited 0, its `file://` link is in the reply, and the
  page's header digest matches the plan bytes on disk.
- Every block on the page answers a question the reader had before the sentence reached it.

## What this is not

- "The plan is short, so a diagram of one step will make it look serious" — a single-step
  plan is a sentence, and padding it with surfaces is the noise this file forbids; render
  the page when the reader has states, options or a footprint to compare.
- "I'll write the HTML directly, it's faster than the blocks" — the renderer is the only
  door a page passes through (D-046-02); hand-authored markup drifts per agent and no
  digest covers it.
