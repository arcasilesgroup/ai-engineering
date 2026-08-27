# Council — 038 design accessibility guard

A five-lens read of `spec.md`, then a cross-read, then a chairman. The lenses never see
each other in round one; in round two each sees the four others relabelled and not its own.
Every finding and every refutation carries a command that was run; its output is written
down below it. Nothing here grants anything.

## Round one — five lenses, each alone

### Cost

What does this change cost, and is the cost claim measurable at the moment of signing?

- **Finding A1 — the advertised cost is a promise over objects that do not exist.** Option
  1 prices the change as "one rule, one reference, one fixture", but none of the three is
  in the tree: no `_accessibility_problems` lane, no `references/accessibility.md`, no
  `tests/test_038_accessibility.py`. The only presently measurable cost is what a reader
  pays to verify any of the spec's own receipts — one failed run. The hidden cost the
  price omits is that the fixture must invent a representation for "a designed surface"
  and "a verify pass", which nothing in the framework defines (C1).
  Command: `test -f tests/test_038_accessibility.py; echo $?`
    ```
    1
    ```

- **Finding A2 — the CI/CD box is ticked while nothing names the fixture anywhere.** The
  Production-ready section asserts "[x] CI/CD — `just check` runs
  `tests/test_038_accessibility.py` on every push (`.github/workflows/check.yml`)", but
  neither the workflow nor the justfile mentions the fixture; the box is already ticked
  today over wiring that does not exist.
  Command: `grep -c 'test_038' .github/workflows/check.yml justfile`
    ```
    .github/workflows/check.yml:0
    justfile:0
    ```

- **Finding A3 — the lane's "on every push" promise cannot land as a green claim while
  the inherited red is open.** The gate is already red in `tests/test_madr.py` on ADR 0025
  (documented `.ai/reports/014`; the spec itself records "the inherited `madr.validate` red
  from ADR 0025 stays open"), so whatever the new fixture runs, the gate this box claims to
  run green is not green.  [struck in round two — R1]
  Command: `grep -n 'madr.validate\|ADR 0025\|stays open' specs/038-design-accessibility-guard/spec.md`
    ```
    117:- Unresolved: the inherited `madr.validate` red from ADR 0025 stays open; this spec does
    ```

### Reversibility

What is hard to un-write?

- **Finding B1 — the spec's premise mis-describes committed content, and the floor it
  claims to add is already written into the very skill it governs.** ai-design's
  `SKILL.md` — committed in `f0a7f888`/`df9f69d8` (the "repair all shipped SKILL.md to the
  standard-craft contract" pass), both predating this draft — already carries step 5
  "Accessibility is evidence … WCAG 2.2 AA is the release floor and the only level anything
  blocks on", and verify (step 4) already measures "contrast over the real background".
  Un-writing this floor is not additive: it means re-editing a just-settled skill or
  shipping a lane redundant with its prose — the guard-that-never-fires class this
  repository names in `docs/adr/0014`.
  Command: `git log --oneline -3 -- .agents/skills/ai-design/SKILL.md`
    ```
    c7e2ee17 test(contract): adapt the pins and fixtures the craft rules touch
    df9f69d8 fix(skills): repair all shipped SKILL.md to the standard-craft contract
    f0a7f888 feat(skills): ten requirements that were specified, claimed closed, and never written
    ```

- **Finding B2 — the floor re-owns the one item two committed places delegate elsewhere.**
  B-038-1 requires `prefers-reduced-motion` respect inside ai-design's verify route, but
  the committed skill's step 7 says exactly the opposite: reduced motion "is judged by
  `/ai-review`'s motion lens, and this skill does not own that detail". The review lens's
  own pinned checklist repeats the delegation ("Motion respects the reduced-motion
  preference, which is judged by the motion lens beside"). Reversing or reconciling this
  split is a conflict with committed text, not an additive rule.
  Command: `sed -n '47,51p' .agents/skills/ai-design/SKILL.md`
    ```
    6. A scanner is a filter, not a verdict. Axe output and a contrast ratio together do not
       declare conformance; they narrow what a person still has to look at.
    7. Motion belongs to the diff that carries it. Curves, duration, gestures, interruptibility,
       reduced motion and the performance budget are judged by `/ai-review`'s motion lens, and
       this skill does not own that detail.
    ```

### The undecidable path

Which claim cannot be decided from the spec as written?

- **Finding C1 — what will `_accessibility_problems` read: a designed surface or the
  skill?** B-038-1 says both. "A designed surface passes only when it names the a11y
  basics and they hold" reads a *surface*; "the rule lives as a contract lane …
  over the ai-design skill" reads a *skill document*. The lanes in `contract.py` read
  only `SKILL.md`/`corpus.md` text — there is no "designed surface" or "verify pass"
  artifact anywhere in the framework — so the rule's input is unpinned until an
  implementer invents a representation.  [strong form struck in round two — R3]
  Command: `sed -n '132,136p' src/ai_engineering/contract.py`
    ```
    def audit(root: Path) -> list[str]:
        skills = sorted(root.glob("ai-*/SKILL.md"))
        if not skills:
            return [f"no skills found under {root}"]
        problems = [problem for skill in skills for problem in audit_one(skill)]
    ```

- **Finding C2 — "the same shape as `_incorrect_correct_problems`" is documented to
  scope out the one skill it must refuse.** That lane's contract states "a skill with no
  rules section passes", and ai-design has no `## Rules` section. A faithfully-shaped
  `_accessibility_problems` would return `[]` for ai-design — the refused-at-audit
  guarantee cannot be decided until the new lane either copies the scope-out (a no-op) or
  diverges from it (unspecified).
  Command: `sed -n '465,468p' src/ai_engineering/contract.py`
    ```
    def _incorrect_correct_problems(folder: Path, name: str) -> list[str]:
        body = (folder / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        if not _RULES.search(body):
            return []  # no rules section: scoped out
    ```

- **Finding C3 — the floor's items are never levelled, under an "AA" banner that does
  not fit them.** "contrast ≥ WCAG AA" is 1.4.3 (AA); "keyboard-reachable" is 2.1.1 (A);
  "visible focus" is 2.4.7 (AA); "prefers-reduced-motion respected" corresponds to 2.3.3
  (AAA) — or to nothing at all as a pure media-query respect — and is already delegated by
  two committed places. The reference that would pin per-item levels does not exist, so
  what "passes only when it names the a11y basics" means is undecidable.
  Command: `grep -n 'AA\|reduced-motion\|keyboard' specs/038-design-accessibility-guard/spec.md`
    ```
    53:   closed rule on ai-design's corpus/verify: contrast ≥ WCAG AA, everything reachable by
    54:   keyboard, visible focus, `prefers-reduced-motion` respected; a designed surface that
    73:   names the a11y basics and they hold — contrast ≥ WCAG AA on text, every interactive
    74:   element keyboard-reachable with visible focus, `prefers-reduced-motion` respected. A
    ```

### Taken on trust

What is asserted that a reader is asked to take without checking?

- **Finding D1 — "nothing in the framework says it" is false against this tree, twice.**
  The problem section's "no WCAG floor: no contrast check … no reduced-motion respect …
  nothing in the framework says it" is contradicted by (a) ai-design's own committed step
  5 ("WCAG 2.2 AA is the release floor") and step 4 ("contrast over the real background"),
  and (b) the review lens's `ai-review/references/frontend.md`, whose definition-of-done
  checklist — "Written out because 'accessible' is a word and this is a list" — carries
  "Motion respects the reduced-motion preference", pinned verbatim in the contract tests
  under EP-248. What is genuinely absent is narrower: no *checked refusing* lane at the
  design/verify stage, no `not-covered` honesty exit, no keyboard/focus naming inside
  ai-design itself.
  Command: `grep -n 'Motion respects' tests/test_contracts.py`
    ```
    1294:    ("EP-248", "ai-review/references/frontend.md", "Motion respects the reduced-motion preference"),
    ```

- **Finding D2 — one half of the citation checks out, the other names nothing.** The
  bullet "The research's AL-Design and claude-agents rows name the a11y discipline" — the
  claude-agents file exists (verified: `the claude-agents repo/design/
  accessibility-auditor.md` is present), but the AL-Design report has zero a11y or
  accessibility mentions; its D-01..D-15 adoption table has no accessibility row.
  Command: `grep -ci 'a11y\|accessib' .ai/research/reports/17-AL-Design/report.md`
    ```
    0
    ```

- **Finding D3 — "spec 037 roadmap table rows 6/16 recorded this" overreaches its
  table.** Rows 6 and 16 are real ("al-design-system", "AL-Design / a11y", both P2 and
  both pointing at spec 038), but neither names `apple-design`, `hallmark`,
  `high-end-visual-design` or `emil-design-eng`; those four appear nowhere in the
  repository except in spec 038 itself. A reader who follows the citation for the insumo
  list lands on a table that does not contain it.
  Command: `grep -c 'apple-design\|hallmark\|high-end-visual-design\|emil' specs/037-model-router-and-intake-validation/spec.md`
    ```
    0
    ```

- **Finding D4 — a bullet labelled "measured in this tree on 2026-08-26" cites a file
  that is not in this tree.** The path `the claude-agents repo/design/
  accessibility-auditor.md` is outside the repository; git tracks nothing under
  `claude-agents`, so a stranger fork cannot reproduce the measurement the label claims.
  Command: `git ls-files | grep -c claude-agents`
    ```
    0
    ```

### The example nobody wrote

Which example is asserted but not written?

- **Finding E1 — all four Examples are unwritten promises.** Every "Then" in "Examples
  somebody can check" is backed by `tests/test_038_accessibility.py`, which does not
  exist; run against the current tree, `-k floor`, `-k not_covered`, `-k honest` and
  `-k reference` all exit 4.
  Command: `uv run --with pytest==9.1.1 pytest -q tests/test_038_accessibility.py -k floor`
    ```
    no tests ran in 0.00s
    ERROR: file or directory not found: tests/test_038_accessibility.py

    === exit: 4
    ```

- **Finding E2 — the reference example is doubly unwritten: no file and no
  directory.** `references/accessibility.md` does not exist, and ai-design has no
  `references/` directory at all; B-038-2's path ("`references/accessibility.md` beside
  ai-design") is ambiguous between a top-level `references/` — which the wheel does not
  guarantee — and `ai-design/references/`, the namespace `contract.py`'s `_EXIST_ROOTS`
  recognises as the skill's own. The worked pattern lives at `ai-review/references/`.
  Command: `test -f .agents/skills/ai-design/references/accessibility.md; echo $?`
    ```
    1
    ```

- **Finding E3 — no example exercises the audit-refusal half.** "…so a design skill
  that omits the floor is refused at audit" (line 78) is the actual mechanism of B-038-1,
  yet all four examples exercise a fixture over invented surfaces; none shows a lane
  refusing a skill.
  Command: `grep -n 'audit' specs/038-design-accessibility-guard/spec.md`
    ```
    37:- `contract.py`'s audit lanes prove the pattern: a checked rule (`_incorrect_correct_
    78:floor is refused at audit.
    105:lane is one function in the existing audit, and the fixture proves both halves (floor
    ```

- **Finding E4 — no code or test in this tree mentions the reduced-motion item, so
  nothing can exercise it.** The newest check in the floor has no fixture case and no
  implementation anywhere in `src/` or `tests/`.  [struck in round two — R2]
  Command: `grep -rn 'prefers-reduced-motion\|reduced-motion' src/ tests/ | wc -l`
    ```
    5
    ```

## Round two — the cross-read, relabelled, and none sees its own

Each lens sees the other four answers, shuffled, and is asked two things: which finding is
a false alarm (and what command shows it), and what did all of us miss. Rankings were not
taken. Refutations carry commands that were run.

### What the cross-read struck through

- ~~**R1 — A3: the lane cannot land while the inherited madr red keeps the gate red, so
  the CI/CD promise is undeliverable.**~~ Refuted by running the actual audit: the contract
  lanes are independent of the `tests/test_madr.py` history reproduction, and
  `contract.audit` over this tree is clean. The inherited red constrains the *gate*, not
  the lane; the box promises wiring, not a green gate; the spec itself names the red as
  unresolved without authorising its repair.
  Command: `uv run python -c "from pathlib import Path; from ai_engineering.contract import audit; print('\n'.join(audit(Path('.agents/skills'))) or 'CLEAN')"`
    ```
    CLEAN
    ```

- ~~**R2 — E4: no code or test mentions the reduced-motion item, so it cannot be
  exercised.**~~ Refuted by the contract tests themselves: the item is pinned verbatim at
  `tests/test_contracts.py:1294` as EP-248 over `ai-review/references/frontend.md`
  ("Motion respects the reduced-motion preference"). The item's testability exists — under
  the review lens, not under any design-route fixture. The core of E4 survives only as
  "no *design-verify* fixture touches it", which C3 and B2 already carry.
  Command: `grep -n 'Motion respects' tests/test_contracts.py`
    ```
    1294:    ("EP-248", "ai-review/references/frontend.md", "Motion respects the reduced-motion preference"),
    ```

- ~~**R3 — C1's strong form: the verify route produces no artifact, so the floor has
  nothing to write its verdict into.**~~ Refuted by the skill's own output contract:
  "## What it produces" names "an accessibility record where every line names the command
  or the observation that satisfied it", and "Done when" demands "every accessibility line
  names a command or a person and a date". The verdict has a committed home; what is
  undecidable is only whether the lane reads that record or the skill text (C1 stands in
  that weaker, still-open form).
  Command: `grep -n 'accessibility' .agents/skills/ai-design/SKILL.md`
    ```
    21:Tokens, components and their states, a mobile-first implementation, and an accessibility
    55:   proves nothing about alt text, contrast, trademark, copyright or accessibility has not
    76:- Every accessibility line names a command or a person and a date; nothing is ticked by a
    ```

### What the cross-read caught that no single lens named

The misses, written down so the count can be recomputed rather than believed
(listed under their own heading below).

## Round three — the chairman wrote this

Nobody here knows which lens said what. This is new text, not a ranking.

**What the lenses agree on.** The a11y need is real and roadmap-recorded: rows 6 and 16 of
the 037 roadmap both name spec 038 as their P2 home. The chosen shape — one contract lane,
one reference, one fixture; no new agent, no dependency, no network call — is the smallest
machine-checked form this framework lands disciplines in, and it matches the house pattern
(checked rule refusing omission, fixture proving both halves, honest exit instead of a
bare pass). Everybody's commands collide on the same two centre facts: the example receipts
are currently unverifiable, and at least part of the problem section mis-measures the
committed tree.

**Where they clash.** Whether "nothing in the framework says it" is a fair description of
a tree in which ai-design's own step 5 names "WCAG 2.2 AA" as "the release floor", verify
already measures "contrast over the real background", and the review lens's frontend
reference pins a thirteen-item checklist ending in "Motion respects the reduced-motion
preference" — versus the narrower reading that what is missing is only the *checked,
refusing* floor at the design stage. Whether the lane, "the same shape as
`_incorrect_correct_problems`", would ever fire on the one skill it governs. And whether
reduced-motion belongs in this floor at all, when two committed places delegate it to
`/ai-review`'s motion lens.

**Blind spots the cross-read caught.** Only by reading the findings together did these
surface: the refusal has no object — the only audited design skill already complies
(audit is CLEAN), and the insumo skills that actually produce surfaces are never audited,
so enforcement rests entirely on a fixture over an invented surface. The new reference
would be a *second* a11y checklist beside the EP-248-pinned one the spec never cites. The
same honesty exists in two spellings (`NOT COVERED` in the verifier machinery, `not-covered`
with a hyphen and a reason here) and nothing binds them. Roadmap row 6's own condition —
"P2 — solo si producimos UI" — is unmet in this tree, and the spec never engages it. And
C2's trap was nearly walked into twice: the shape the spec copies is the one lane in the
contract documented to scope its target out.

**Verdict.** The direction is coherent and the shape is minimal, but the spec is written
over a mis-measurement and over artifacts that do not exist. The true gap is smaller and
more specific than the problem section claims: the framework already says the floor in
prose (ai-design step 5, contrast in verify, the review lens's pinned frontend checklist);
what does not exist is a checked, refusing rule at the design/verify stage, a `not-covered`
honesty exit on the design surface, keyboard/focus naming inside ai-design itself, and the
reference. Signed as "measured in this tree", the central premise and all four example
receipts fail; signed as a direction to land the checked floor, it is right and small.
Nothing here grants anything.

**Recommendation.** Re-measure the problem section against the committed ai-design skill
and the EP-248-pinned frontend checklist before signing the "nothing in the framework says
it" claim. Pin what the lane reads (skill text or the accessibility record) and when it
fires (the `## Rules` scope-out has to be resolved explicitly). Put the reference inside
`ai-design/references/` and have it name the existing ai-review checklist rather than
reinvent it — or say it supersedes it. Level every check (contrast AA, keyboard A,
focus-visible AA, and reduced-motion's AAA/2.3.3 status plus its `/ai-review` delegation).
Land `tests/test_038_accessibility.py` with exactly the four `-k` cases and one case that
actually refuses a skill at audit. Engage row 6's "solo si producimos UI" condition
instead of treating both rows as unconditional.

**One first step.** Write `references/accessibility.md` beside ai-design naming the
existing `ai-review/references/frontend.md` checklist and the per-item levels, together
with `tests/test_038_accessibility.py` carrying the four `-k` cases — and correct the
problem section's "nothing in the framework says it" to the measured truth (prose floor
exists; no checked rule).

The three sections below are the only ones a script reads. Their bullet counts must equal
the two totals stated at the bottom; the counts were recomputed rather than believed.

### Gaps no single lens named

- **M1 — the refused-at-audit side has no object, now or soon.** The audit globs only
  `ai-*/SKILL.md`; the framework's one design gateway already names the floor (its audit
  result today is CLEAN), and the insumo skills the reference will name are not in the
  tree and never audited. "A design skill that omits the floor is refused at audit" is a
  rule whose only audited target already complies — a guard that never fires — and whose
  real enforcement surface is a fixture over a surface representation nothing defines.
  Command: `uv run python -c "from pathlib import Path; from ai_engineering.contract import audit; print('\n'.join(audit(Path('.agents/skills'))) or 'CLEAN')"`
    ```
    CLEAN
    ```

- **M2 — one honesty, two spellings, and nothing binds them.** The framework's verifier
  honesty is `NOT COVERED` (`≠ PASS`, spec 035 B-035-2; 036's own council already noted
  the phrase names a task, not a symbol over `Verdict` PASS/FAIL/BLOCKED), while 038
  writes `not-covered <reason>` with a hyphen and a reason, claiming "the same honesty".
  The two live side by side in the tree with no shared definition; a fixture asserting one
  says nothing about the other.
  Command: `grep -rn 'not-covered\|NOT COVERED' specs/035-adoption-of-reference-patterns/spec.md specs/038-design-accessibility-guard/spec.md`
    ```
    specs/035-adoption-of-reference-patterns/spec.md:38:    and `NOT COVERED ≠ PASS` rules
    specs/035-adoption-of-reference-patterns/spec.md:112:  no capability to repair what it finds ("report, don't fix"); `NOT COVERED` is reported,
    specs/035-adoption-of-reference-patterns/spec.md:235:  `1 passed`), and a lane that could not run reports `NOT COVERED`, never `PASS`
    specs/038-design-accessibility-guard/spec.md:47:keyboard, focus, reduced-motion) or is explicitly marked `not-covered` with why — the same
    specs/038-design-accessibility-guard/spec.md:55:   fails reports `INCOMPLETE: not-covered <reason>`, never a bare pass. Plus
    ```

- **M3 — the reference is a second checklist, and the spec never cites the first.** The
  spec names "the ai-review references are the worked pattern" while remaining silent that
  `ai-review/references/frontend.md` already carries the concrete a11y definition of done
  ("Written out because 'accessible' is a word and this is a list"), pinned item by item
  under EP-248. `references/accessibility.md` as specced would duplicate that list — two
  checklists, one contract-test-pinned and one not, is the drift this repository refuses.
  Command: `grep -c 'frontend' specs/038-design-accessibility-guard/spec.md`
    ```
    0
    ```

- **M4 — both roadmap rows route to spec 038, but row 6 is conditional and the condition
  is unmet.** Row 6 ("al-design-system") is "P2 — solo si producimos UI (spec 038)":
  adoption is gated on this tree producing UI. Spec 038 treats both rows as unconditional
  adoption of the guard, while nothing in the tree produces a UI surface for the guard to
  govern.
  Command: `sed -n '192,205p' specs/037-model-router-and-intake-validation/spec.md`
    ```
    | 6 | al-design-system | P2 — solo si producimos UI (spec 038) | spec candidata |
    | 16 | AL-Design / a11y | P2 — guard de a11y en diseño (spec 038) | spec candidata |
    ```

### Findings cut for carrying no command

- **Cut1 — the reference is a standing maintenance cost nobody prices: every WCAG
  revision and every new design row the roadmap adopts extends it forever, and no command
  measures reference drift or its token growth against spec 033's economy.** A
  reading-level claim with no runnable demonstration, so it was cut in round one rather
  than written as a finding.
- **Cut2 — ai-design's verify bound ("at most two automatic rounds: a third means the
  design is wrong, not the measurement") caps how often the a11y outcome may be re-checked,
  a cap tuned for visual verification, not conformance re-runs.** The tension is real but
  nothing in the tree demonstrates it, so it was cut.

### Findings the cross-read refuted, with the command that refuted them

- ~~**R1 — A3: the lane cannot land while the inherited madr red keeps the gate red, so the
  CI/CD promise is undeliverable.**~~ — refuted by
  `uv run python -c "from pathlib import Path; from ai_engineering.contract import audit; print('\n'.join(audit(Path('.agents/skills'))) or 'CLEAN')"`.
    ```
    CLEAN
    ```

- ~~**R2 — E4: no code or test mentions the reduced-motion item, so nothing can exercise
  it.**~~ — refuted by
  `grep -n 'Motion respects' tests/test_contracts.py`.
    ```
    1294:    ("EP-248", "ai-review/references/frontend.md", "Motion respects the reduced-motion preference"),
    ```

- ~~**R3 — C1's strong form: the verify route produces no artifact, so the floor has
  nothing to write its verdict into.**~~ — refuted by
  `grep -n 'accessibility' .agents/skills/ai-design/SKILL.md`, which prints the
  accessibility record in "## What it produces" and its "Done when" clause.
    ```
    21:Tokens, components and their states, a mobile-first implementation, and an accessibility
    55:   proves nothing about alt text, contrast, trademark, copyright or accessibility has not
    76:- Every accessibility line names a command or a person and a date; nothing is ticked by a
    ```

## The two counts

- Gaps that appeared only after the cross-read: **4**
- Findings deleted, for carrying no command or for being refuted: **5**