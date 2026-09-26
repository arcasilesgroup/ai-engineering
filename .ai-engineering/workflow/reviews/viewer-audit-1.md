# Review viewer-audit #1

## Goal
A missing or unreadable plan file shows the empty drop and the badge text is offline, never live; load() returns false on parse failure; templates/viewer.html.tpl and .ai-engineering/workflow/checkpoints/viewer.html stay byte-identical.

## Acceptance
- Missing plan or parse failure shows #empty and #live textContent offline.
- templates/viewer.html.tpl and .ai-engineering/workflow/checkpoints/viewer.html are identical.
- bun test tests/viewer-audit.spec.ts passes.

## changed_files
- templates/viewer.html.tpl
- .ai-engineering/workflow/checkpoints/viewer.html
- tests/viewer-audit.spec.ts

## verify
- bun test tests/viewer-audit.spec.ts
- bun run typecheck
- bun run lint

## Findings (round 1)

Checkpoint 1 was committed in three commits: `97a3a607` (tests), `07349c10` (implementation) and `61d6a15e` (gates). The diff was taken as `git diff 97a3a607~1 HEAD`. The three verify commands pass. Lint and typecheck show warnings only, and those are in unrelated files.

## F1 · MAJOR · resolved
**Where:** templates/viewer.html.tpl:36, 59-60, 99-117, 133, 245-262 (the same lines appear in the planted viewer.html)
**Critic (r1):** The checkpoint 1 commit `07349c10` also ships work from later checkpoints: the `overflow-x` clip and the journey `min-width:4px` (no sideways scroll at 320), the 44px tap targets on `.tech>summary` and `.drop input`, the empty-drop `<h1>`, the h3→h2 card labels, and a `.finding` comment. None of this is in the checkpoint 1 tasks or files contract. It pre-empts the gates for checkpoints 2 onward, which will now "pass" work that was never reviewed against their own acceptance, and it makes checkpoint 1 impossible to revert on its own. → Reduce `07349c10` to the `load()` and `tick` changes only. Move the CSS, heading and comment edits to the checkpoints that own them.
**Fixer (r1):** fixed — restored pre-`07349c10` CSS/headings/comments from `97a3a607~1`; kept only `failLoad`/`load`/`servedInit` tick changes in templates/viewer.html.tpl and mirrored to planted viewer.html · verify: `bun test tests/viewer-audit.spec.ts` ✓
**Critic (r2):** Verified. Against `97a3a607~1`, the template diff now touches only `failLoad`, `load` and the `servedInit` tick and `!slug` branch; the CSS, heading and comment edits are gone. The planted viewer is still byte-identical (`cmp` shows no difference). Resolved.

## F2 · MAJOR · resolved
**Where:** tests/viewer-audit.spec.ts:32-47
**Critic (r1):** U1 and U2 grep the source for the exact implementation strings (`const ok = load(`, `ok ? "live" : "offline"`, and `return\s+false` anywhere in `load`). They never run anything, so they do not prove the acceptance "#empty is shown and #live textContent is offline". A behaviour-preserving refactor would fail these tests, while a real regression would pass them. For example, `render()` throwing, `#app` left visible, or a later line resetting `textContent` to "live" would all go unnoticed. → Pull the `<script>` out of the template and run `load()` and one `tick` against a minimal DOM and fetch stub (a fake `$`, or happy-dom if the repo already has it). Cover three cases: invalid JSON, `fetch` returning 404, and valid JSON. Assert `load()` returns false, `#empty.hidden === false`, `#app.hidden === true` and `#live.textContent === "offline"`.
**Fixer (r1):** fixed — tests/viewer-audit.spec.ts now extracts the template `<script>`, runs `load`/`servedInit` against a fake DOM+fetch (same pattern as artifact-scroll-spy.spec.ts; no new packages), covering invalid JSON, 404, valid JSON, no-slug, and non-object · verify: `bun test tests/viewer-audit.spec.ts` ✓
**Critic (r2):** Verified. The tests now run the extracted script against a fake DOM and fetch, the same way artifact-scroll-spy.spec.ts does, and assert on `hidden`, `textContent` and `className`. There is one remaining gap, the served invalid-JSON path; it is logged as F7. Resolved.

## F3 · MAJOR · resolved
**Where:** templates/viewer.html.tpl:291
**Critic (r1):** When the page is served with no `?plan=` and the directory listing has no `.json` files, the code shows `#empty` and returns early. The badge keeps its initial text `static` (line 129), so the acceptance "missing plan → #live textContent offline" is not met on this path. → Set `#live` to `live off` / `offline` before returning in the `!slug` branch, and add a test for that case.
**Fixer (r1):** fixed — `!slug` branch sets `$("live").className = "live off"` and `textContent = "offline"` before return (templates/viewer.html.tpl:291-295); U4 covers it · verify: `bun test tests/viewer-audit.spec.ts` ✓
**Critic (r2):** Verified. The `!slug` branch sets the badge to `live off` / `offline`, and U4 asserts both fields. Resolved.

## F4 · MINOR · resolved
**Where:** templates/viewer.html.tpl:297
**Critic (r1):** `if (!ok) { $("empty").hidden = false; $("app").hidden = true; }` repeats what `load()` already does in its own `catch` (lines 271-272). The only case it adds is the `text === lastText` path, where nothing has changed anyway. → Delete the line and let `load()` own the empty/app toggle.
**Fixer (r1):** fixed — removed the redundant `if (!ok)` empty/app toggle from tick; `failLoad`/`load` own the toggle · verify: `bun test tests/viewer-audit.spec.ts` ✓
**Critic (r2):** Verified. The duplicate toggle is gone from the tick; `load()` and `failLoad()` own it. Resolved.

## F5 · MINOR · resolved
**Where:** templates/viewer.html.tpl:269-276
**Critic (r1):** A file that parses but is not a plan (`null`, or a bare number) makes `render()` throw on `plan.checkpoints`, so `load()` throws instead of returning false. In the served path the throw is caught and the badge goes offline. In the local drop path (`bindLocalFile` → `read` → `load`) the rejection is unhandled and `#empty` stays hidden. → Treat a parsed value that is not an object as a failure: return false with the same empty-drop handling.
**Fixer (r1):** fixed — after parse, non-object/`null`/array goes through `failLoad()` (templates/viewer.html.tpl:274); U5 covers `null` and `42` · verify: `bun test tests/viewer-audit.spec.ts` ✓
**Critic (r2):** Verified. A parsed value that is `null`, not an object, or an array goes through `failLoad()`, and U5 covers `null` and `42`. Resolved.

## F6 · BLOCKER · resolved
**Where:** tests/viewer-audit.spec.ts:122-191
**Critic (r2):** Typecheck, one of the verify commands, now fails: `bun run typecheck` exits 1 with 16 TS18048 errors (`nodes.empty`, `nodes.app` and `nodes.live` are possibly 'undefined'), all of them in this file. No other file in the repo has typecheck errors, so this checkpoint introduced the failure. The fixer's evidence only ran `bun test`. → Type `nodes` with fixed keys (`Record<"live" | "empty" | "app" | …, DomNode>`, or an explicit object type) so that indexing is never `undefined`. Then show `bun run typecheck` exiting 0.
**Fixer (r2):** fixed — typed `nodes` as `Record<NodeId, DomNode>` with fixed keys so `nodes.empty`/`app`/`live` are definite; string lookup goes through a separate `byId` map · verify: `bun test tests/viewer-audit.spec.ts` ✓ · `bun run typecheck` ✓ (exit 0)
**Critic (r3):** Verified. `nodes` is now `Record<NodeId, DomNode>`, and `bun run typecheck` exits 0 with no errors anywhere. Lint exits 0. Resolved.

## F7 · MAJOR · resolved
**Where:** tests/viewer-audit.spec.ts:127-143
**Critic (r2):** The acceptance "parse failure shows #empty and #live offline" is only half-tested. U1 checks `load()` directly and never looks at the badge, and U2 covers a 404, which goes through the tick's `catch`. No test serves a `./<slug>.json` that returns invalid JSON through `servedInit`, so the `ok ? "live" : "offline"` branch in the tick is never exercised with `ok === false`. If that branch regressed to always say "live", every current test would still pass. → Add a served case where the fetch returns `{not-json`, and assert `#empty.hidden === false`, `#app.hidden === true`, `#live.textContent === "offline"` and `className === "live off"`.
**Fixer (r2):** fixed — added U2b: served `./broken.json` returns `{not-json` through `servedInit`; asserts empty/app/live offline · verify: `bun test tests/viewer-audit.spec.ts` ✓
**Critic (r3):** Verified. U2b sends `{not-json` through `servedInit`, so it runs the tick's offline branch after a failed parse. A regression to always "live" would now fail U2b. `bun test` passes 7 of 7. The template has not changed since `eb757a7f`, and the planted copy is byte-identical. No new findings. Resolved.