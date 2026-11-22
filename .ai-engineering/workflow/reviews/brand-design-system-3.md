# Review brand-design-system checkpoint 3

Goal: every templates/*.html.tpl carries both marker pairs and parity covers all eight; PRD, spec, plan and viewer drop their private token and base styles; artifact-design.md loses its CSS and script blocks; the seven HTML-writing skills say copy the template and write no CSS or script; the tests that compared the doc's block now compare every carrier to brand/.

Diff: commit 55c79f74. Verify not re-run (the caller passed the builder receipt and asked for no re-run).

Checked and clean: templateDrift no longer skips unmarked templates, and a BrandMarkerError counts as drift; the new test strips one marker and one whole pair from each of the eight templates and expects exactly that file to be named. recap, research and triage get the markers only, with bytes unchanged. PRD, spec and plan keep every placeholder and every `<pre>` (gates and evidence) byte for byte. The viewer template and the checkpoint viewer.html are byte-identical. artifact.files is derived and tested against the templates glob. All seven `Writes: *.html` skills carry the exact copy line. No `css fence is left in artifact-design.md, and no stale "copy the CSS block" wording is left in skills/. No test was weakened: the whitespace-stripped `includes` carrier check became a byte-equal templateDrift check. Outside the checkpoint's list, only the workflow JSON bookkeeping and the additive tests/brand-templates.spec.ts changed.

## F1 · MAJOR · open
**Where:** skills/ai-brainstorm/SKILL.md:289
**Critic (r1):** The new line tells the writer, without condition and in step 1 (before approval), that "The conclusions go to `.ai-engineering/PRD.html`: Copy `templates/PRD.html.tpl` and fill its sections". PRD.html is cumulative. Step 5 (line 303) says to write it only after approval, and that when the PRD already has other features the writer updates the matching one and leaves the others. An agent that follows line 289 on the second feature copies the blank template over the existing PRD and loses every earlier feature, and it does so before the gate. → Remove the PRD sentence from step 1. In step 5, say: "If `.ai-engineering/PRD.html` does not exist yet, copy `templates/PRD.html.tpl` and fill its sections; write no CSS and no script. Otherwise edit the existing page in place." The artifact-brand test only needs one copy line per skill, so brainstorm.html.tpl's line still satisfies it.

## F2 · MINOR · open
**Where:** scripts/brand.ts:839
**Critic (r1):** The new `cmdParity` branch (a refused marker prints the BrandMarkerError message and exits 1) is not covered at the CLI. tests/brand-templates.spec.ts runs `parity` only for the case where the website checkout is missing. → Add a spawnSync `parity` run on a scratch tree with one marker removed. Assert exit status 1, and assert that stderr equals the named-file message.

## F3 · MINOR · open
**Where:** brand/README.md:39
**Critic (r1):** "and every template `brand/components.css` and `brand/components.js`?" has no verb, so the reader cannot tell what is compared to what. → "…and does every template's brand region still match `brand/components.css` and `brand/components.js`?"
