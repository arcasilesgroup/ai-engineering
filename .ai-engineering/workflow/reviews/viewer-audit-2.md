# Review viewer-audit #2

## Goal
Empty drop title is an h1 Open a feature plan; file input min-height 44px; long paths wrap; in-card section labels are h2 with the same visual style; page title stays h1; empty section has data-region empty-drop; planted viewer stays identical to the template.

## Acceptance
- Empty drop shows one h1 Open a feature plan; file input CSS min-height is 44px; paths wrap without sideways scroll.
- Card section labels are h2; no h1-to-h3 skip in the card body.
- Planted viewer remains identical to the template.

## changed_files
- templates/viewer.html.tpl
- .ai-engineering/workflow/checkpoints/viewer.html
- tests/viewer-audit.spec.ts
- .ai-engineering/workflow/prototypes/viewer-audit.states.json

## verify
- bun test tests/viewer-audit.spec.ts
- bun run typecheck
- bun run lint

## Round 1 (critic)
Reviewed range c7be4528^..HEAD (changes are committed). Verify: 13 tests pass, typecheck exit 0, lint exit 0; template and planted viewer byte-identical.

## F1 · BLOCKER · resolved
**Where:** templates/viewer.html.tpl:316-319 (mirrored in .ai-engineering/workflow/checkpoints/viewer.html)
**Critic (r1):** The picker's `innerHTML` and `onchange` are now rebuilt on every 3-second tick while the plan loads. Before this change they were set once at init. Rewriting the options of a `<select>` the user has open closes the dropdown and resets keyboard highlight every 3 s, so choosing a feature can fail mid-interaction. → Build the options only when `ensurePicker()` creates the element (or only when the file list changes); on later ticks leave an existing picker untouched.
**Fixer (r1):** fixed — `ensurePicker(files, slug)` builds options/onchange only on create; tick calls it without rewriting · templates/viewer.html.tpl:265-274,316 · verify: bun test tests/viewer-audit.spec.ts ✓ · bun run typecheck ✓
**Critic (r2):** Verified in f822f49a. `ensurePicker` fills the options and handler only when it creates the element, and later ticks return the existing node untouched. U12 proves it with a marker. The template and planted viewer are still byte-identical. Resolved.

## F2 · MAJOR · resolved
**Where:** tests/viewer-audit.spec.ts:36-66 and 277-298
**Critic (r1):** The new picker lifecycle (`ensurePicker`/`removePicker`: absent on the empty drop, present after a good load with more than one plan, removed after a later parse or fetch failure) has no test at all. The fake DOM even dropped the `picker` node instead of asserting it. This repeats LEARNINGS L7 (an acceptance branch through the tick never executed). → Add servedInit cases with a fetch stub listing two plans: good plan means one `#picker` with the slug selected; broken plan on a later tick means no `#picker`; a second good tick does not recreate or rebuild it (covers F1).
**Fixer (r1):** fixed — harness gains createElement/appendChild/remove + tickAgain; U10–U12 cover create/select, remove on broken tick, untouched on second good tick · tests/viewer-audit.spec.ts · verify: bun test tests/viewer-audit.spec.ts ✓
**Critic (r2):** Verified. U10 checks that the picker is created with the slug selected, U11 that a broken tick removes it, and U12 that a second good tick leaves it alone. All three run `servedInit` and the registered tick through the real template code. 16 tests pass. Resolved.

## F3 · MAJOR · resolved
**Where:** tests/viewer-audit.spec.ts:277-293 and 318-321 (U4, U5, U6, U8)
**Critic (r1):** Four of the six checkpoint-2 tests regex the template source instead of running it. That repeats LEARNINGS L2 ("assert behaviour, not source text"). U4 passes even if nothing unhides `#empty`, and U8 would still pass if the region ended up on another element after a render. → Drive U4 and U8 through the fake DOM (for example, failed `load()` or `servedInit` with no slug, then assert the empty section's h1 text and `data-region`). Keep the CSS regexes for U5 and U6 only, since no browser layout exists here, and say so in the test name.
**Fixer (r1):** fixed — U4 asserts h1 via failed load unhiding `#empty`; U8 asserts `data-region` after no-slug servedInit; U5/U6 renamed as CSS-source-only · tests/viewer-audit.spec.ts · verify: bun test tests/viewer-audit.spec.ts ✓
**Critic (r2):** Upheld. The rewritten U4 and U8 now assert values the test fixture injects itself. At tests/viewer-audit.spec.ts:83-91, the fake `#empty` is hard-coded with `<h1>Open a feature plan</h1>` and `data-region="empty-drop"`. If the template's heading or region were deleted tomorrow, both tests would stay green, so the check is circular. The first version at least read the template. → Build the fake `#empty` from the template: take the `<section id="empty">…</section>` markup from `templateHtml()` and set the node's innerHTML and attributes from it, not from literals. Then the behavior assertion (failed load unhides `#empty`) and the content assertion both depend on the shipped file. The U5/U6 renames are accepted.
**Fixer (r2):** fixed — `emptySectionFromTemplate` seeds `#empty` attrs/innerHTML from the shipped section; U13/U8 assert against that · tests/viewer-audit.spec.ts · verify: bun test tests/viewer-audit.spec.ts ✓ · bun run typecheck ✓
**Critic (r3):** Verified in 357314ae. The fake `#empty` now takes its attributes, children and starting `hidden` state from the template's own `<section id="empty">`, with no literals left. Deleting the template's h1 or `data-region` would now fail U13 or U8, and U13 still checks that a failed load unhides the section. Resolved.

## F4 · MINOR · resolved
**Where:** tests/viewer-audit.spec.ts:63
**Critic (r1):** The fake `#live` still starts as `static`, but the template now ships `offline`. The fixture no longer matches the page, so a test could pass on a state that cannot exist. → Start the fixture at `offline`, like the template.
**Fixer (r1):** fixed — fixture `#live` starts as `offline` · tests/viewer-audit.spec.ts harness · verify: bun test tests/viewer-audit.spec.ts ✓
**Critic (r2):** Verified. The fixture's `#live` now starts as `offline`, matching the template. Resolved.

## F5 · MINOR · resolved
**Where:** tests/viewer-audit.spec.ts:326
**Critic (r2):** Two tests are named "U4": the checkpoint-1 test at line 256 and the checkpoint-2 test at line 326. A failure report naming U4 is ambiguous. → Renumber the checkpoint-2 test to the next free ID (U13).
**Fixer (r2):** fixed — checkpoint-2 empty-h1 case renamed U13 · tests/viewer-audit.spec.ts · verify: bun test tests/viewer-audit.spec.ts ✓
**Critic (r3):** Verified. The checkpoint-2 empty-title test is now U13, and only one test is named U4. Resolved.

## Round 2 (critic)
Verify: 16 tests pass, typecheck exit 0, lint exit 0; template and planted viewer byte-identical.

## F6 · MINOR · open (r3)
**Where:** tests/viewer-audit.spec.ts:354 and 359
**Critic (r3):** The same duplicate-ID problem as F5 still exists for U5 and U6: the checkpoint-1 tests at lines 298 and 308 already use those names. I missed this in round 1. → Renumber the checkpoint-2 CSS tests to U14 and U15.

## Round 3 (critic)
Verify: 16 tests pass, typecheck exit 0, lint exit 0; template and planted viewer byte-identical. Only a MINOR finding is open, so checkpoint 2 passes review.
