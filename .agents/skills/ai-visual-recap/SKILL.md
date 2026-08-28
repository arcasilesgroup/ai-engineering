---
name: ai-visual-recap
description: >-
  Turns a finished work unit — a branch, a commit range, a PR, the tasks of one plan —
  into the record a reviewer reads before the raw diff: one page whose file-tree and diff
  excerpts come from git itself, whose narrative says what changed and why, and whose link
  opens in the browser beside the digest of the spec it recaps. Trigger for "recap this
  PR", "show me what this branch changed", "the build is done, what did it do". Not for
  planning work not yet done — use /ai-visual-plan. Not for judging whether the change is
  correct — use /ai-review, which attacks the diff; a recap only ever shows what is there.
license: Apache-2.0
compatibility: needs git; needs the ai-eng CLI on PATH
disable-model-invocation: true
---

# Recap the work unit as one page

## What it produces

`.ai/reports/NNN-recap-<slug>.html` — a committed record of one range's change, printed in
chat as a `file://` link beside the spec digest it carries.

## Steps

1. Read `policy/visual-pages.md` first; it owns the budgets and the editorial bar. If
   that path is absent, refuse to author the page and restore the file — a recap written
   against remembered budgets is the drift the file exists to prevent.
2. Scope the whole work unit, not the last fix: the implementation, the follow-ups, the
   tests and the record changes this thread made. Separate them from unrelated dirty
   files that existed before; if the boundary is genuinely unclear, say the assumption
   in one line and proceed.
3. Pick the base the range starts from — the approval commit for a build, the merge base
   for a PR — and run the command that derives the page from real bytes:

   ```bash
   ai-eng report recap --spec <NNN> --base <ref> --summary "<1-3 paragraphs>"
   ```

   The file-tree and every excerpt come from `git diff` over that range; the renderer
   refuses an excerpt that is not a real hunk. The summary is yours, and every claim in
   it names a file the diff touches.
4. Show the link the command prints. A recap nobody clicks is a file.
5. Skip the page for a change that reviews faster as a plain diff — a small, single-file
   or obvious one. A recap is review overhead; say "one file, plain diff is enough" and
   stop.
6. UI changes need the visual named. When the range changed rendered UI, the summary
   names the components the diff touched and the before/after wireframes live on the
   plan's view page, where blocks are authored — the recap is derived from bytes and
   invents none.
7. Never re-read the whole diff twice: the budgets are the cost ceiling as much as the
   shape rule, and a recap that dumps is a recap the reviewer scrolls past.

## Done when

- `ai-eng report recap` exited 0, the page matches the reports-home shape `doctor`
  checks, and its `file://` link is in the reply.
- The page's file list equals `git diff --name-status` over the same range.

## What this is not

- "The agent that built it can vouch for it, so the narrative can come from memory" — a
  recap block invented from conversation instead of the diff is the failure this page
  exists to prevent; the command refuses the fabricated hunk, and the reviewer's job
  starts where the tool's does.
- "Every change deserves a recap" — under the tab floor the change is small, and the
  honest output is the plain diff plus one sentence saying why no page.
