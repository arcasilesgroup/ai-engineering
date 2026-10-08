---
name: ai-test-planner
description: Plan and write the tests for a feature, bottom-up. Everything that code or the CLI can verify (pure logic, API endpoints, DB constraints, auth/role rules) is tested without a browser. UI end-to-end tests come last and cover only what the lower layers can't. Use when the user asks to plan tests, write tests, or add test coverage for a feature or checkpoint (e.g. "/ai-test-planner discount rules").
license: MIT
---

# Test planner

**If you're running as a subagent** (for example, launched by `/ai-orchestrator`), you can't launch subagents. Do the steps marked "subagent" yourself, and do only the steps and checkpoint cases you were asked for.

**Project specifics** (test file locations, commands, frameworks, how to act as a role, e2e sign-in) come from the **Project config** section of `AGENTS.md`. Read it first. If a value you need is missing there, infer it from the existing tests and config files, and say so in your report.

Rule: **push every check to the lowest layer that can prove it.** A browser test is only for things that exist only in the browser. Layers run in order, and a layer runs only once the one below it passes:

| # | Layer | Proves | Where / Run |
|---|-------|--------|-------------|
| 1 | Unit | Pure logic: calculations, date math, state rules | Project config → *Unit tests* |
| 2 | API | Endpoints, role/permission checks, status codes, DB constraints surfacing as 409/422, state transitions | Project config → *API tests* |
| 3 | CLI / static | The app type-checks, lints and builds; smoke `curl`s against the running API | Project config → *Lint*, *Build*, *Health check* (commands only, no files) |
| 4 | UI (runs last) | Rendering, navigation, form wiring, role-based visibility, and the 375px layout | Project config → *E2E tests* |

Before putting a case in layer 4, ask: *could layer 1 or 2 fail for the same bug?* If yes, move the case down. For example, "a staff user can't refund an order" is a layer 2 case, never a UI one.

## 1. Map the feature with a subagent

Send an `Explore` subagent to return a compact map of the feature:

- the pure functions involved;
- the endpoints, with their auth dependencies and permission checks;
- the tables, with their constraints (unique, check, FK, partial indexes);
- the pages, forms and client code that call the endpoints;
- the existing tests and fixtures.

If `.ai-engineering/workflow/checkpoints/<slug>.json` exists, have it include that file too, so the tests line up with the checkpoints.

## 2. Write the plan

Write `.ai-engineering/workflow/test-plans/<slug>.json`:

```json
{
  "feature": "Discount rules",
  "slug": "discount-rules",
  "order": ["unit", "api", "cli", "ui"],
  "gating": "Run layers in order. Do not run a layer until every case in the layer before it passes.",
  "layers": {
    "unit": [{ "id": "U1", "case": "percentage discount never goes below zero", "file": "<unit test path>", "checkpoint": 1 }],
    "api":  [{ "id": "A1", "case": "non-admin cannot create a discount → 403", "file": "<api test path>", "checkpoint": 2 }],
    "cli":  [{ "id": "C1", "case": "app builds", "command": "<build command>", "checkpoint": 3 }],
    "ui":   [{ "id": "E1", "case": "admin creates a discount and sees it in the list", "file": "<e2e spec path>", "checkpoint": 4, "why_ui": "Form wiring from the button to the save call, and list refresh" }]
  },
  "not_tested": ["Anything deliberately skipped, and why"]
}
```

- Every `ui` case needs a `why_ui` field saying why no lower layer can prove it.
- `checkpoint` is optional; use it only when a checkpoint file exists. When it does, also add each checkpoint's test commands to that checkpoint's `verify` array in the checkpoint JSON.
- Cover the unhappy paths as well as the happy path: wrong role, someone else's record (403/404), duplicates (409), bad input (422), and races (a conditional update that matches no row → 409).

## 3. Write the tests with parallel subagents

Layers 1 and 2 write to separate files, so launch one `general-purpose` subagent per layer **in a single message**. Give each one its slice of the plan and these conventions:

- **Unit tests:** no DB, no network, following the neighbouring unit tests. If the logic isn't pure yet, say so. Don't mock around it; the logic belongs in a pure module.
- **API tests:** use the framework's in-process test client and the role-impersonation approach from Project config → *Acting as a role in API tests*. Never mint real tokens. Run against the local DB from Project config → *DB start/reset*; skip with a clear reason if it isn't reachable. Shared fixtures go in the project's shared fixture file: create it once and reuse it after that. If a test dependency is missing, report it rather than adding it.

Once they finish, run layers 1 and 2 yourself. For failures, fix the tests; if the failure is a product bug, report it rather than changing the test to pass. Then run layer 3.

## 4. UI tests, last

Do this only after layers 1–3 pass.

- If `@playwright/test` isn't installed where Project config → *E2E tests* says, **ask before adding it**, because it's a new dependency. Under `/ai-orchestrator`, it's listed in `new_dependencies` and approved at the checkpoint review, so add it without asking.
- Load the signed-in session from `.ai-engineering/workflow/playwright/auth.json`, the same file `/ai-review-ui` uses; per-role files are `.ai-engineering/workflow/playwright/auth-<role>.json`. If it's missing, ask the user to run `! npx -y playwright codegen --save-storage=.ai-engineering/workflow/playwright/auth.json <web URL><sign-in path>` (both from Project config).
- Keep the tests few and flow-shaped: one spec per user journey, not one per assertion.
- Use role and label locators (`getByRole`, `getByLabel`), not CSS selectors.
- Write them with one `general-purpose` subagent, then run them.

## 5. Report

Reply with:
- the plan path;
- the cases per layer, e.g. `unit 6 · api 9 · cli 2 · ui 2`;
- the pass/fail result per layer;
- any product bugs the tests exposed.

Add new test files and `.ai-engineering/workflow/test-plans/` to `FILEMAP.md`.

## Lifecycle

Lane: standard, full
Writes: .ai-engineering/workflow/test-plans
Read by: ai-orchestrator, implement workers
Dies: when the feature plan is closed
Next: none
