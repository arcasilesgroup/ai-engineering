# Review brand-design-system checkpoint 1

Goal: `bun scripts/brand.ts gen` rewrites only the marked brand region of templates/brainstorm.html.tpl from brand/components.css and brand/components.js, reproduces today's bytes exactly, and a test fails on any hand edit inside the region.

Acceptance:
- Running gen twice leaves templates/brainstorm.html.tpl byte-identical to the committed file.
- A one-byte edit inside the brainstorm brand region makes templateDrift() name that file. An edit outside the markers survives gen byte for byte.
- A template with a missing, doubled or reversed marker is refused with a message naming the file and the marker, and is not rewritten.
- tests/artifact-layout.spec.ts, tests/artifact-scroll-spy.spec.ts and tests/artifact-brand.spec.ts pass unchanged.

changed_files:
- brand/components.css
- brand/components.js
- scripts/brand.ts
- templates/brainstorm.html.tpl
- brand/README.md
- FILEMAP.md

verify:
- mkdir -p /private/tmp/t-runs && TMPDIR=/private/tmp/t-runs bun test tests/brand-templates.spec.ts tests/artifact-layout.spec.ts tests/artifact-scroll-spy.spec.ts tests/artifact-brand.spec.ts tests/brand-check.spec.ts
- mkdir -p /private/tmp/t-runs/web && AI_ENGINEERING_WEB_DIR=/private/tmp/t-runs/web bun scripts/brand.ts gen && shasum templates/*.html.tpl > /private/tmp/t-runs/tpl.sha && AI_ENGINEERING_WEB_DIR=/private/tmp/t-runs/web bun scripts/brand.ts gen && shasum -c /private/tmp/t-runs/tpl.sha
- bun run typecheck
- bun run lint

## F1 · BLOCKER · resolved
**Where:** scripts/brand.ts:674
**Critic (r1):** Each pair is checked on its own, so a nested pair never trips `reversed`: both ends sit after their own begins, and each marker occurs once. The two spans still overlap. `spliceBrandRegions` then applies the later span first and reuses the earlier span's indexes on the already shortened string. A nested fixture `<style>/* brand:begin */AAA<!-- brand:js:begin -->BBB/* brand:end */CCC<!-- brand:js:end -->DDD` comes back as `<style>/* brand:begin */CSSript>\njs</script><!-- brand:js:end -->DDD`: the CSS end marker and the bytes between the pairs are gone, and the script tag is torn. `rewriteBrandTemplate` (scripts/brand.ts:722) writes that result because it differs from the input, and `renderArtifacts` does not throw, so `cmdGen` reaches the write. The next `gen` then throws `missing marker /* brand:end */` and leaves the damaged file on disk. The task says an out-of-order pair throws a named error and bytes outside the markers stay. After both spans are known, if `style.start < script.end && script.start < style.end`, throw `BrandMarkerError` naming the file and the marker that opens inside the other span, before any slice. Keep the existing missing, doubled, and reversed messages. Do not edit tests/brand-templates.spec.ts.

**Fixer (r1):** fixed — `spliceBrandRegions` throws `BrandMarkerError` before any slice when the spans overlap, naming the marker that opens inside the other, so `gen` never writes (scripts/brand.ts:672). The README lists nested with the other refusals (brand/README.md:67). · verify: `mkdir -p /private/tmp/t-runs && TMPDIR=/private/tmp/t-runs bun test tests/brand-templates.spec.ts tests/artifact-layout.spec.ts tests/artifact-scroll-spy.spec.ts tests/artifact-brand.spec.ts tests/brand-check.spec.ts` ✓

**Critic (r2):** The original fixture throws `templates/nested.html.tpl: nested marker <!-- brand:js:begin -->` before any slice, and the opposite containment names `/* brand:begin */`. A scratch `rewriteBrandTemplate` of that fixture throws and leaves the bytes unchanged. The committed brainstorm template still splices to itself, and a reversed pair still reports `reversed`. The cited test command passed, 33. resolved.

## F2 · MINOR · resolved
**Where:** scripts/brand.ts:836
**Critic (r1):** `drifted` now counts template region mismatches, but the summary still says those files do not match `brand/tokens.json`. A one-byte edit inside the brainstorm region prints a correct `DRIFT templates/brainstorm.html.tpl` line and then `1 generated file(s) do not match brand/tokens.json`. The template is checked against `brand/components.css` and `brand/components.js`, not the token file. The success line at scripts/brand.ts:839 makes the same claim when the template is the extra artifact. Say which files disagree with the token outputs and which disagree with the component sources. The per-file line can stay.

**Fixer (r1):** fixed — the mismatch and success summaries name token drift against `brand/tokens.json` apart from template drift against `brand/components.css` and `brand/components.js` (scripts/brand.ts:824, scripts/brand.ts:833). The parity row says the same (brand/README.md:39). · verify: `bun run typecheck` ✓ · `bun run lint` ✓

**Critic (r2):** `parityMismatchSummary` and `parityAgreementSummary` split the two counts. A live `parity` against a missing website checkout prints `3 generated file(s) do not match brand/tokens.json` and a separate `ok    templates/brainstorm.html.tpl` line. README line 39 matches. typecheck and lint exit 0. resolved.

## F3 · BLOCKER · resolved
**Where:** scripts/brand.ts:672
**Critic (r2):** The new check uses a strict `<` on the interiors only, so a begin marker that ends exactly where the other interior ends is inside that interior and still spliced. `/* brand:begin */AAA<!-- brand:js:begin -->/* brand:end */BBB<!-- brand:js:end -->` returns `/* brand:begin */CSS<script>\njs\n</script><!-- brand:js:end -->`, and `rewriteBrandTemplate` writes it: `/* brand:end */` is gone. The other flush, `<!-- brand:js:begin -->AAA/* brand:begin */<!-- brand:js:end -->BBB/* brand:end */`, drops `<!-- brand:js:end -->`. The next `gen` throws missing that marker and leaves the damage. Refuse when either opening marker's bytes intersect the other interior (the touching endpoint, `<=`, is enough: the committed brainstorm template keeps both marker lengths between its interiors, so it still splices). Name the marker that sits inside. Do not slice. Do not edit tests/brand-templates.spec.ts.

**Fixer (r2):** fixed — a begin marker that ends on the other interior's edge now counts as nested (`<=`), and the throw still names the marker that sits inside, before any slice (scripts/brand.ts:673). · verify: `mkdir -p /private/tmp/t-runs && TMPDIR=/private/tmp/t-runs bun test tests/brand-templates.spec.ts tests/artifact-layout.spec.ts tests/artifact-scroll-spy.spec.ts tests/artifact-brand.spec.ts tests/brand-check.spec.ts` ✓ · `bun run typecheck` ✓ · `bun run lint` ✓

**Critic (r3):** Both flush fixtures throw before a slice: the script begin names `<!-- brand:js:begin -->`, the style begin names `/* brand:begin */`. A scratch `rewriteBrandTemplate` of the first throws and leaves the bytes unchanged. The earlier nested fixtures, a reversed pair, and a pair separated by a gap still behave as before. The committed brainstorm template still splices to itself. `cmdGen` returns on `BrandMarkerError` before the write loop. The cited test command passed, 33. resolved.
