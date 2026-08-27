---
id: "038"
slug: design-accessibility-guard
status: draft
date: 2026-08-26
ref: ""
supersedes: ""
---

# Design accessibility honesty floor

## Who this is for, and what it is worth to them

The repository owner (roadmap row 16) and the stranger whose framework produces a web UI,
a dashboard or a component. Today `ai-design` already carries most of the accessibility
floor: its verify route measures contrast over the real background, its step 5 names
`WCAG 2.2 AA` as the release floor, the `ai-review` motion lens respects reduced-motion
(EP-248-pinned 13-item checklist), and `contract.audit` reports this tree CLEAN. The one
discipline **missing** is honesty at the edge: a designed surface that **cannot** meet the
floor — a deliberately low-contrast editorial look, a canvas game, a chart with complex
keyboard needs — has no explicit `not-covered` exit, so it either stalls or passes
silently. This spec adds that floor as a checked rule inside ai-design's verify route (not
a new agent), plus the keyboard/focus item the floor does not yet name.

## Context and problem

**What is true today, measured in this tree on 2026-08-26:**

- ai-design `SKILL.md` step 5: `WCAG 2.2 AA is the release floor`; verify step 7 measures
  `contrast over the real background`; `ai-review/references/frontend.md` carries the
  EP-248-pinned 13-item a11y checklist ending in `Motion respects the reduced-motion
  preference` (`tests/test_contracts.py:1294`). So the contrast/motion floor **exists**.
- The floor does **not** name keyboard reachability or visible focus, and — the real gap —
  nothing gives a surface that deliberately cannot meet the floor an honest exit:
  `INCOMPLETE: a11y not-covered <reason>`, the same honesty the framework demands of
  verifiers (`NOT COVERED ≠ PASS`).
- The roadmap's design rows (apple-design, hallmark, high-end-visual-design,
  emil-design-eng in `~/.claude/skills`) and any future design skills are *insumos* the
  design skill may load, never skills of the framework itself (spec 037 roadmap rows 6/16,
  recorded as the insumo doctrine); no design skill other than ai-design is audited.

**The problem, in words a non-technical reader can follow:**

The accessibility floor is there and most of it is enforced. What is missing is the edge:
when a design *intentionally* cannot meet a check (a deliberately artistic low-contrast
page, an interactive canvas), the framework today has no way to say "this is not covered,
and here is why" — so the choice is stall or a silent pass. This spec adds that honest
exit plus the keyboard/focus check the floor has not yet named.

## Options considered

1. **Honesty-floor rule + keyboard/focus item + one reference (chosen shape).** A closed
   rule on ai-design's verify: a surface passes only when it names the a11y basics — then
   contrast/motion that the existing steps already verify, **plus keyboard reachability and
   visible focus** — or it exits `INCOMPLETE: a11y not-covered <reason>`, never a bare pass.
   `references/accessibility.md` names the checks and the `not-covered` rule. Gives: the
   missing edge and the missing item, checked; no new agent; no style imposition. Costs:
   one rule, one reference, one fixture.
2. **A full standalone `ai-accessibility` skill.** Gives: a dedicated auditor. Costs: a new
   skill (the fifteen-skill target is deliberate), a second consumer, and — as the council
   showed — its audit would find this tree already CLEAN. Rejected on evidence.
3. **Prompt-only guidance.** Gives: zero code. Costs: exactly the gap — the "checked, or it
   rots" failure the framework refuses.

## Decision

**Option 1.** Spec 038 adds two behaviours:

### B-038-1 — Accessibility honesty floor in ai-design's verify route

ai-design's verify route gains a closed rule: a designed surface passes only when it
either (a) names the a11y basics — contrast ≥ WCAG AA, keyboard reachability, visible
focus, reduced-motion respected — and the existing verify steps confirm them, or (b)
exits `INCOMPLETE: a11y not-covered <reason>` when it deliberately cannot. A surface that
says neither is refused: a silent pass is never the answer. The rule is a contract lane
`_accessibility_problems` over the ai-design skill, in the shape of the other audit lanes;
a design that omits the floor is refused at audit.

### B-038-2 — The keyboard/focus item and the accessibility reference

The floor gains the two checks it does not yet name — keyboard reachability and visible
focus — and `references/accessibility.md` beside ai-design carries them plus the
`not-covered` rule and the concrete checks (contrast ratios, keyboard, focus,
reduced-motion, landmarks). The reference is loaded only when a verify pass runs (context
economy, spec 033); the roadmap's design skills plug into it as insumos the design skill
may load, never as framework skills.

## Challenged once

**"A blanket a11y rule in a design skill re-owns what ai-design and the motion lens
already delegate; it is redundant."** The delegation is *verified* for contrast and motion,
but it is not *complete*: keyboard and focus are absent from every step, and — the load-
bearing half — there is no honest `not-covered` exit for a surface that deliberately
cannot comply. This rule is the completion of the floor, not its duplication: (a)/(b) are
the two legal exits, and a surface claiming neither is refused. The fixture proves the
three states.

**"'INCOMPLETE: a11y not-covered' is a second spelling of the verifier's `NOT COVERED`; it
will drift."** The two are the same discipline at two surfaces — the cold verifier's
`NOT COVERED` for lanes that did not run, the design verify's `not-covered` for a surface
that cannot meet the floor. The reference names both, and D-038-02 binds the spelling;
a later spec may unify them into one constant if a second surface needs it.

## Assumptions and unresolved risks

- Assumption: WCAG AA + keyboard + focus + reduced-motion is the right first floor; later
  measured need may add landmarks, screen-reader labels or more — rule/config growth, not
  a new architecture.
- Assumption: the reference laden only on verify keeps the context economy; a design that
  never reaches verify never pays its tokens.
- Unresolved: whether the `not-covered` spelling and the verifier's `NOT COVERED` should
  become one shared constant; this spec records the two as the same discipline and binds
  the spelling, and unifies only when a second surface needs it.
- Unresolved: the inherited `madr.validate` red from ADR 0025 stays open; this spec does
  not authorise rewriting that history.

## Examples somebody can check

- **Success, floor holds:** Given a designed surface whose verify pass names contrast ≥ AA,
  keyboard reachability, visible focus and reduced-motion, When `_accessibility_problems`
  reads it, Then it returns no problems (`uv run --with pytest==9.1.1 pytest -q
  tests/test_038_accessibility.py -k floor` → `1 passed`).
- **Denial, silent pass:** Given a surface whose verify pass omits the a11y basics and
  names no `not-covered`, When the rule reads it, Then it is refused (`-k silent` →
  `1 passed`).
- **Honest exit:** Given a surface that deliberately cannot meet a check and says
  `not-covered: <reason>`, When the rule reads it, Then it passes with the reason recorded
  (`-k honest` → `1 passed`).
- **Reference loads:** Given `references/accessibility.md`, When a verify pass needs it,
  Then it names the checks and the `not-covered` rule (`-k reference` → `1 passed`).

## Decisions

**D-038-01 — the accessibility floor is completed, not invented: ai-design already verifies
contrast and motion, so this spec adds keyboard, visible focus and the honest
`not-covered` exit.**
Rationale: the council proved the premise "nothing says it" false (WCAG 2.2 AA + contrast
are already the release floor); the real gap is the edge and the two missing checks. A
rule that repeats what already holds would be a no-op; one that completes it is the delta.

**D-038-02 — a designed surface either names the basics (confirmed by the existing verify
steps) or exits `INCOMPLETE: a11y not-covered <reason>`; a silent pass is refused, and the
same-spelling discipline binds the verifier's `NOT COVERED`.**
Rationale: the honesty rule is the framework's own (`NOT COVERED ≠ PASS`); the design
floor gets the same shape, so an intentionally non-compliant surface is a recorded,
reasoned exit, never a silent one.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification adds one contract lane, one reference and one fixture; no service, no URL,
no second hop — the service-shaped boxes are `not applicable`.

- [x] CI/CD — `just check` runs `tests/test_038_accessibility.py` on every push (`.github/workflows/check.yml`); nothing deployed
- [x] Logs — not applicable: every verb still emits the one JSON line `ai-eng report digest` reads
- [x] Traces — not applicable: one process, no second hop
- [x] Errors — not applicable: the new path fails closed (silent pass refused; `not-covered` with reason is the honest exit)
- [x] Health and data age — the 038 fixture runs in the gate's pytest half (`just cover`'s `not fast_enough` collection) on every push
- [x] External check — `.github/workflows/check.yml` runs the whole gate on every push; the floor is additionally asserted by its fixture, the independent route
- [x] Second path — the lane is read by its fixture and the reference by the same fixture, with no shared line
- [x] Security — `just security`: gitleaks, semgrep, trivy on every push, over a change that adds no dependency and no network call