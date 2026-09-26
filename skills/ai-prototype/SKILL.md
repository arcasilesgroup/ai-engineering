---
name: ai-prototype
description: Build a single-file, clickable HTML prototype of a UI screen or flow, following the design directions given in the request. Use when the user asks to prototype, mock up, or sketch a UI (e.g. "/ai-prototype order list, dense, neutral palette", "mock up the settings page").
license: MIT
---

# Prototype

Build a static HTML prototype of the UI the user asked for. It's for looking at and clicking through, not production code.

**If you're running as a subagent** (for example, launched by `/ai-orchestrator`), you can't launch subagents. Do the steps marked "subagent" yourself, skip `open`, and return only the file path and your assumptions.

## 1. Gather the design directions

Use these sources, highest priority first:

1. **The request itself:** layout, tone, palette, density, references, anything the user said about the look.
2. **Project design sources, if they exist:** `.ai-engineering/DESIGN.md`, and the global styles/tokens file named in the **Project config** section of `AGENTS.md` (colors, fonts, radii). Use them so the prototype looks like the real app.
3. **Domain:** Project config → *Domain* and *Roles*, plus `.ai-engineering/PRD.html`. Make the fake data realistic for that domain: real-looking names, entities, dates, amounts and statuses. Role-dependent UI follows the roles listed there.

If the request doesn't say which screen or flow it wants, ask one short question. Missing style directions are not a reason to ask: fall back to the project tokens, and if there are none, use a clean, neutral, dense app UI.

**Gather sources 2 and 3 with an `Explore` subagent**, not by reading the files yourself. Ask it to return a compact brief with:

- **Design tokens:** the colors, fonts, radii and spacing from `.ai-engineering/DESIGN.md` and the global styles file, as exact values.
- **What the matching page has today:** if a live page already exists for this screen, list its sections, components and copy (Project config → *Pages* and *Components*).
- **Data fields:** the fields the API really returns for this screen (Project config → *Shared types* and *API routes*), so the fake data has the right shape.

The brief keeps the raw file dumps out of your context.

## 2. Build

- **Output:** one file, `.ai-engineering/workflow/prototypes/NNN-<kebab-name>.html`. `NNN` is the next free three-digit number in that folder (`001`, `002`, …), so several prototypes sort. Not in the app source, not at the repo root, not in another folder. Put all CSS and JS inline. Allowed external resources: Tailwind via `<script src="https://cdn.tailwindcss.com"></script>` and Google Fonts. Nothing else.
- **Scope:** only the screens or states the user asked for. For a flow, put the steps in one file and switch between them with JS. Don't use extra pages.
- **Interactivity:** make the key interactions work: tabs, modals, form validation messages, filters over the fake data, and status changes. Use plain JS and no framework.
- **States:** show the empty, loading, and error states wherever the UI would really have them. Each **data state** must be reachable through a `?state=<name>` URL parameter (e.g. `?state=empty`, `?state=error`), so review tools can open it directly. A visible switcher in the corner is optional.
- **Labels are a contract:** use the exact field labels and button text the real page should have. `/ai-review-ui` drives the prototype and the live page with the same steps by label, so if the text differs, the comparison fails.
- **Regions:** wrap each part of the screen in an element with `data-region="<name>"` (e.g. `page-header`, `summary`, `edit-form`). Under `/ai-orchestrator`, use the region names from the checkpoints' `ui.scope`.
- **State scenario:** also write `.ai-engineering/workflow/prototypes/NNN-<kebab-name>.states.json` with the same number and name as the HTML. It lists every state the prototype shows and how to reach it. Include the `regions` list, and give each state the `regions` it exercises. Include the default, filled, validation-error and submitted states for forms, open dialogs, applied filters, and the `?state=` data states. The format is in `ai-review-ui` step 3. It lives in `.ai-engineering/workflow/prototypes/` beside its HTML.
- **Responsive:** the layout must work from 375px up to desktop width, with no horizontal scroll.
- **Accessibility basics:** semantic elements, labels on inputs, visible focus, and sufficient contrast.
- Declare colors, radii, and fonts once as CSS variables in `:root`, so a direction change means a one-place edit.

## 3. Self-check with a subagent

Screenshot the prototype at desktop and mobile widths:

```bash
OUT=.ai-engineering/workflow/playwright/prototype/<kebab-name>; mkdir -p $OUT
for vp in 1440,900 375,812; do
  npx -y playwright screenshot --full-page --viewport-size=$vp --wait-for-timeout=1000 \
    "file://$PWD/.ai-engineering/workflow/prototypes/<kebab-name>.html" $OUT/${vp%,*}.png
done
```

Then give a `general-purpose` subagent the screenshots, the HTML, the design directions from step 1, and `.ai-engineering/DESIGN.md`. Ask it to list, most severe first, where the prototype breaks the directions. It should check:

- horizontal scroll or broken layout at 375px;
- colors, fonts or spacing that don't match the tokens;
- interactions or states from the request that are missing;
- accessibility basics.

Apply its fixes in one pass. Don't loop on its feedback.

## 4. Deliver

- Run `open .ai-engineering/workflow/prototypes/<kebab-name>.html` to show it in the browser.
- Reply with the file path, one line naming which design directions were applied, and any assumption you made where the directions were silent.
- Iterate on feedback by editing the same file. Only create a new file (`-v2`) if the user wants to compare versions.
- On a standalone run, don't commit the prototype unless the user asks. Under `/ai-orchestrator`, it's committed along with the plan. Add `.ai-engineering/workflow/prototypes/` to `FILEMAP.md` the first time the directory is created.

## Lifecycle

Lane: standard, full
Writes: .ai-engineering/workflow/prototypes/
Read by: ai-review-ui, humans
Dies: when the feature plan is closed
Next: none
