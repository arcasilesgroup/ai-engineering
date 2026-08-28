# Corpus: ai-visual-plan

Turns a plan's Markdown into the review surface a human reads before approving: visual
blocks rendered by `ai-eng report view` into one self-contained page, handed over as a
`file://` link beside the digests it rendered. The Markdown stays the record.

## Routes here

- "make this plan visual so I can review it" — the plain trigger: a plan that exists as prose and needs a page to be approved from.
- "here is a plan Codex wrote, turn it into something I can sign off on" — a pasted plan is source material; save it under `specs/` first, then render it standalone.
- "I want to see the file map and the open questions before I approve" — the surfaces this skill composes, and the recommendation-per-question rule it enforces.
- "the spec and plan are done, how do I show them to the reviewer" — use `/ai-visual-plan` for the gate page; the ADR at the digests is still the approval.
- "add a diagram to the plan" — one `diagram` block for a flow the prose makes the reader reconstruct; skip it if the sentence already carries it.
- "what did this change once it was built" — use `/ai-visual-recap`, because that reads a diff backwards; this reads a plan forwards.
- "decide which option wins and put it in the plan" — use `/ai-spec`, because choosing is the spec's job; this skill renders the choice, it does not make it.

## Refuses

- "write the tasks for me" — use `/ai-plan`, which owns what the plan says; this skill only changes how it reads.
- "just hand me the HTML, I'll paste it into the plan" — refused: the renderer is the only door a page passes through, and hand-authored markup carries no digest.
- "the plan is one line, make it look substantial" — a single-step plan is a sentence; padding it with surfaces is the noise the skill exists to remove.
- "approve this and start building" — presenting the page and asking for sign-off is the step; approval is the human's ADR at the digests, never the agent's.
- "the diagram looks wrong, let me edit the rendered page" — fix the Markdown or `policy/visual-pages.md` and re-render; if that guidance file is missing, restore it before authoring, and never hand-edit a page that carries no digest.
