---
name: ai-review-ui
description: Compare the live UI of the web app against its HTML prototype in .ai-engineering/workflow/prototypes/ and report the visual and behavioral gaps. Screenshots both, then two parallel reviewers (subagents, or `claude -p`) diff them, one for visuals and one for behavior. Use when the user asks to review, check, or diff the implemented UI against a prototype (e.g. "/ai-review-ui order-list", "does the settings page match the prototype?").
license: MIT
---

# Review UI against prototype

This skill runs in one of two modes. Work out which one you're in first.

- **Standalone** (a human ran `/ai-review-ui`): run steps 1–5. The output is a findings report. Don't fix anything; step 5 ends by offering fixes, and fixing happens only if the user accepts.
- **Gate** (`/ai-orchestrator` Gate 2): run steps 2–4 only, with the checkpoint's `ui.scope`. Before capturing, check that `route` in `.ai-engineering/workflow/prototypes/<name>.states.json` equals the checkpoint's `ui.route`; if not, fix the scenario file to use `ui.route`, since the capture script only reads the scenario. Return `PASS` or `FAIL` and the merged findings to the orchestrator. Never offer or apply fixes; failures go through the orchestrator's failure path. The gate passes when every in-scope, live-reproducible state is `match` and there are no `high` or `med` findings, other than ones tagged `[intentional?]`.

## 1. Resolve the pair

- **Prototype:** `.ai-engineering/workflow/prototypes/<name>.html`. Match it from the request; if more than one could fit, ask.
- **Live route:** the page that implements it (see `FILEMAP.md`, and Project config → *Pages* in `AGENTS.md`, which says where signed-in and public pages live). Public pages don't need the saved sign-in session.
- **Source files:** that route's page file, plus any components it uses (Project config → *Components*).

If the route isn't obvious from the prototype name, send an `Explore` subagent to find the page that implements it and its component files. Have it return only the paths.

## 2. Make sure the app is reachable

- Run `curl -s -o /dev/null -w '%{http_code}' <web URL>` (Project config → *Web URL*). If nothing answers, run the *Dev server* command from the repo root in the background and wait until it responds.
- Signed-in pages need a saved session. If `.ai-engineering/workflow/playwright/auth.json` is missing, stop and ask the user to run the command below, sign in, and close the window:
  ```
  ! npx -y playwright codegen --save-storage=.ai-engineering/workflow/playwright/auth.json <web URL><sign-in path>
  ```
  `.ai-engineering/workflow/playwright/` is gitignored. If the screenshots come back showing the login page, the session has expired; ask the user to run the same command again.

## 3. Capture both sides in the same state

Never compare a prototype in one state with the live page in another, like an empty form against a submitted one. Every comparison is driven by a **state scenario**, `.ai-engineering/workflow/prototypes/<name>.states.json`, which `/ai-prototype` writes next to each prototype. If it's missing, write it first from the prototype's states:

```json
{
  "route": "/discounts",
  "login": "/login",
  "now": "2026-10-01T10:00:00",
  "regions": ["page-header", "discount-list", "discount-form"],
  "states": [
    { "name": "overview", "regions": ["page-header", "discount-list"], "steps": [] },
    { "name": "empty-form", "regions": ["discount-form"], "steps": [] },
    { "name": "validation-error", "regions": ["discount-form"], "steps": [{ "click": "Save discount" }] },
    { "name": "filled", "regions": ["discount-form"], "steps": [{ "select": "Type", "value": "Percentage" }, { "fill": "Amount", "value": "15" }] },
    { "name": "saved", "regions": ["discount-form", "discount-list"], "mutates": true, "steps": [{ "select": "Type", "value": "Percentage" }, { "fill": "Amount", "value": "15" }, { "click": "Save discount" }, { "waitFor": "Discount saved" }] },
    { "name": "no-discounts", "regions": ["discount-list"], "proto_query": "state=empty", "live": false, "live_note": "needs a store with no discounts" }
  ]
}
```

- **Regions and scope:** a checkpoint often builds only part of a screen, while its prototype shows the finished screen. The prototype marks each part with `data-region="<name>"`. `regions` lists them, and each state says which regions it exercises. With `--scope page-header,balances`:
  - the script captures only the states whose regions are all in scope;
  - it fingerprints only the prototype elements inside in-scope regions, so parts that aren't built yet can't cause a MISMATCH;
  - the reviewers judge only in-scope regions.

  Region names match the checkpoint's `ui.scope`.

- **`login`** is the sign-in path from Project config (default `/login`). Landing there means the saved session expired. Without `--scope`, every state runs and the whole screen is compared (standalone mode, or the final checkpoint for a screen).

- **Steps:** `fill`/`select`/`check` target a field by its visible label. `click` targets a button by its name (add `"role"` for links or tabs). There's also `press`, `waitFor` (text) and `wait` (ms). The same steps run on both sides, so the prototype and the live page must use the same labels and button text; a step that works on only one side is a finding in itself.
- **Data states:** loading, error and empty lists are reached on the prototype with `proto_query`, and on live with `live_query` or a different role's session (`"auth": ".ai-engineering/workflow/playwright/auth-<role>.json"`). If live can't reproduce the state, set `"live": false`. That state is then reviewed on the prototype alone and never compared.
- **Mutating states** (`"mutates": true`) run on live only when the base URL is localhost. List them last.
- **Viewports:** both sides use the same viewports (default 1440×900 and 375×812), the same frozen clock (`now`), reduced motion, and no animations.

Run from the repo root:
```bash
npx -y -p playwright sh -c 'NODE_PATH="$(dirname "$(command -v playwright)")/.." node skills/ai-review-ui/capture.cjs <name> <web URL> [--scope a,b]'
```

The script writes `.ai-engineering/workflow/playwright/review/<name>/<state>-<width>-{proto,live}.png`, plus `states.json`.

Before taking each pair of screenshots, it **fingerprints the UI state on both sides**: field values by label, open dialogs, alert or status messages, and invalid fields. Each pair is marked `match`, `MISMATCH` (with the reasons) or `proto-only`.

- A **MISMATCH** means the two sides aren't in the same state, so their pixels aren't comparable. Report each mismatch as a `high` finding, e.g. "after submitting empty, the live page shows no validation", and exclude that pair from the visual review.
- `redirected to <sign-in path>` means the sign-in session has expired; see step 2.

## 4. Independent review

Hand the comparison to reviewers with fresh context, so they judge the screenshots and not your memory of building them.

**Default: two agents in parallel.** Launch `ui-visual-reviewer` and `ui-behavior-reviewer` in a single message. Their method, output format and rules are in their agent definitions (`.claude/agents/`), which also:
- give them a fixed model (visual: `opus`; behavior: `sonnet`);
- tell them to ignore `AGENTS.md`, so they judge against the prototype and `.ai-engineering/DESIGN.md` without the implementer's reasoning. Don't pass them the checkpoint's goal, tasks or implementation notes either.

Give each one only:
- the capture folder `.ai-engineering/workflow/playwright/review/<name>/`;
- the scope (`ui.scope`, or "whole screen");
- `.ai-engineering/workflow/prototypes/<name>.html`, plus `.ai-engineering/workflow/prototypes/<name>.states.json` for the behavior reviewer;
- the live source paths (the page and its components).

The visual reviewer judges sizes **proportionally** against each screenshot's own dimensions, not by eye. The behavior reviewer owns the MISMATCH findings.

**Alternative: `claude -p`.** Use this when the user asks for it, or for a fully separate process. Run both from the repo root, in parallel:
```bash
claude -p --agent ui-visual-reviewer "<inputs above>"
claude -p --agent ui-behavior-reviewer "<inputs above>"
```

## 5. Report (standalone only)

Merge the two lists and drop duplicates, meaning the same element and the same difference. Put the state mismatches from `states.json` first. Relay the findings verbatim, grouped as high, then med, then low. Add the paths to the screenshots. Offer to fix the high-severity findings.

## Lifecycle

Lane: standard, full
Writes: nothing
Read by: ai-orchestrator, humans
Dies: on completion
Next: none
