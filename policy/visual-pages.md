# How to author a visual page

The block vocabulary `ai-eng report view|recap` renders, and the editorial bar the blocks
must meet. This file is the authoring reference for the skills; the renderer never reads
it, and every budget it names lives in `contract.py`, not here.

Derived from Builder.io's visual-plan and visual-recap skills — MIT License,
Copyright (c) 2026 Builder.io — upstream `BuilderIO/skills` (`skills/visual-plan`,
`skills/visual-recap`, themselves mirrored from `BuilderIO/agent-native` by
`scripts/sync-agent-native-skills.mjs`). What was taken is the editorial craft: the block
taxonomy, the diff→block mapping and the grounding rules. What was left is the mechanism:
the hosted Plan MCP, the `@agent-native/core` npm CLI and the hosted renderer. The audit
of that trade is `.ai/reports/021-skills-integration-roadmap.html`.

## The grammar

A block is a fenced `visual` segment inside ordinary Markdown:

````markdown
```visual
{"block": "diagram", "title": "The flow", "steps": [{"label": "spec", "note": "…"}, "plan"]}
```
````

A plain reader sees a fenced JSON note. The renderer lifts the blocks out, renders the
prose around them, and appends each surface in document order. An unknown block name is
never dropped: it appears in a visible warning section on the page. A malformed JSON body
warns and the rest of the document still renders.

Blocks are invisible to the plan's machinery — the task parser, the approval digest and
the intent counter all stop at fences — so a numbered line or a bold field inside a block
is content, never structure. That wall is `spec.fence_records`, and it predates the
grammar for a reason: grill round 1 of spec 046 executed that a fence-blind parser turns
a fenced `**check**:` into the command a tick would execute.

## The blocks

| block | payload | use it for |
|---|---|---|
| `diagram` | `steps: [{label, note} \| string]` | a sequence the reader must follow before the prose |
| `file-tree` | `entries: [{path, change, children?}]` | the footprint of a change or a proposed layout |
| `decision-table` | `headers?, rows: [{col: value}]` | comparing options; one row per option, no prose in cells |
| `open-questions` | `questions: [{title, options: [{label, detail?}], recommendation?}]` | the decisions the reader must actually make |
| `checklist` | `items: [{label, done} \| string]` | what is claimed done, at a glance |
| `wireframe-before-after` | `before/after: {html, caption?}` | a UI change; markup is filtered to shape and inline style |
| `diff` | `path, text, summary?` | one key change; `text` must be a real hunk range |
| `narrative` | `text` | 1–3 paragraphs of outcome, nothing else |

## The editorial bar (harvested, kept because it is the product)

- **Outcome first.** The page leads with what changed and why in one to three paragraphs,
  not with a disclaimer, a provenance note or a count of files. A block that only says the
  page exists is boilerplate; boilerplate is what the upstream skill forbids and what this
  file forbids again.
- **Grounded, not reconstructed.** A `diff` excerpt is a range from `git diff` and a
  `file-tree` entry is a line from `git diff --name-status`. A block invented from
  conversation — plausible paths, remembered hunks — is the failure the recap exists to
  prevent. When the renderer cannot find a hunk, the page is refused, not padded.
- **Lean is not thin.** For any change worth a page: the tree, the outcome narrative, and
  the key changes. The count of key-change excerpts and their line budget are named by
  `contract.RECAP_TABS_MIN`, `contract.RECAP_TABS_MAX` and
  `contract.RECAP_EXCERPT_LINES_MAX`; the page title budget by `contract.PAGE_TITLE_MAX`.
  Under the floor the change reviews faster as a plain diff — say so and skip the page.
- **UI impact needs a wireframe.** If the diff changed rendered UI, prose and hunks are
  not a substitute for showing it: `before` and `after` must be comparable — same screen,
  same density, the change the only difference. A caption that says what to look at beats
  a caption that describes the mockup.
- **Real content, never lorem.** A wireframe filled with `Acme Inc` and a plausible row
  teaches the reviewer the layout works; `TODO` boxes teach nothing and hide the density
  problem until implementation.
- **The question block is the last block.** One `open-questions` per page, at the bottom,
  every question with a recommendation. A page that asks without recommending pushes the
  work back to the reader.
- **Secrets never cross.** The recap redacts key-shaped values before they reach the page;
  an author who notices a secret in a hunk fixes the hunk, not the redactor.

## What a page is not

Not an approval. The ADR at the canonical digests of `spec.md` and `plan.md` is the gate
(D-046-01); a view prints those digests so a stale page is identifiable from its header,
and a recap records bytes already approved. Not a second source of truth: the Markdown is
the record, the page is a reading of it, and the fix for an ugly page is this file or the
renderer, never a hand-edited artifact.
