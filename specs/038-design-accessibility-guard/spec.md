---
id: "038"
slug: design-accessibility-guard
status: draft
date: 2026-08-26
ref: ""
supersedes: ""
---

# Design accessibility guard

## Who this is for, and what it is worth to them

The repository owner (roadmap row 16: "AL-Design a11y — P2 — guard de a11y en diseño") and
the stranger whose framework produces a web UI, a dashboard or a component. Today
`ai-design` (the framework's design gateway) has four routes — shape, build, imagery,
verify — with no accessibility floor: a design can be "verified against the rendered
thing" while every interactive element fails contrast or keyboard navigation, and nothing
in the framework says it. This spec adds the missing floor as a checked rule inside
ai-design's verify route (not a new agent, per the owner's "no sea agente sino que esté
dentro de ai-engineering"), plus a reference the design skills can load, so every design
the framework produces is accessible or explicitly marked not-covered.

## Context and problem

**What is true today, measured in this tree on 2026-08-26:**

- `ai-design` routes creating/extending/redesigning a web, mobile, native or CLI
  experience and "verifies the rendered result rather than the declared CSS", but its
  verify route has no WCAG floor: no contrast check, no keyboard check, no focus-visible
  check, no reduced-motion respect.
- The research's AL-Design and claude-agents rows (`.ai/research/reports/17-AL-Design/
  report.md`, `/Users/soydachi/repos/claude-agents/design/accessibility-auditor.md`)
  name the a11y discipline; `ai-design` itself (`.agents/skills/ai-design/SKILL.md`)
  imposes **no style and never requires generated imagery** — the right shape to carry a
  floor without imposing a look.
- `contract.py`'s audit lanes prove the pattern: a checked rule (`_incorrect_correct_
  problems`, `_anti_rationalization_problems`) refuses a skill that omits a discipline.
  ai-design has no such lane for a11y.

**The problem, in words a non-technical reader can follow:**

A framework that designs interfaces should never hand back an interface a person who
cannot use a mouse, or who needs the screen-reader, cannot use. Today the design skill can
call a design "verified" while failing the most basic checks. This spec adds one checked
floor: every design the framework produces either meets the accessibility basics (contrast,
keyboard, focus, reduced-motion) or is explicitly marked `not-covered` with why — the same
honesty the framework already demands of verifiers (`NOT COVERED ≠ PASS`).

## Options considered

1. **An a11y floor inside ai-design's verify route + a reference (chosen shape).** A
   closed rule on ai-design's corpus/verify: contrast ≥ WCAG AA, everything reachable by
   keyboard, visible focus, `prefers-reduced-motion` respected; a designed surface that
   fails reports `INCOMPLETE: not-covered <reason>`, never a bare pass. Plus
   `references/accessibility.md` naming the checks the design skills load. Gives: the
   floor where design is verified, no new agent, no style imposition. Costs: one rule, one
   reference, one fixture.
2. **A standalone `ai-accessibility` skill.** Gives: a dedicated auditor. Costs: a new
   skill (the framework's fifteen-skill target is deliberate; the owner asked "no sea
   agente"), a second consumer, and the same isolation the verify route already provides.
   Rejected on the owner's own framing.
3. **Prompt-only guidance (no rule).** Gives: zero code. Costs: exactly the gap — a hint
   in prose is the "checked, or it rots" failure the framework refuses everywhere else.

## Decision

**Option 1.** Spec 038 adds two behaviours:

### B-038-1 — Accessibility floor in ai-design's verify route

ai-design's verify route gains a closed rule: a designed surface passes only when it
names the a11y basics and they hold — contrast ≥ WCAG AA on text, every interactive
element keyboard-reachable with visible focus, `prefers-reduced-motion` respected. A
surface that cannot be verified reports `INCOMPLETE: a11y not-covered <reason>`, never a
bare pass. The rule lives as a contract lane `_accessibility_problems` over the ai-design
skill, the same shape as `_incorrect_correct_problems`, so a design skill that omits the
floor is refused at audit.

### B-038-2 — The accessibility reference

`references/accessibility.md` beside ai-design (the skill anatomy allows references,
templates, scripts; the ai-review references are the worked pattern): the concrete checks
(contrast ratios, keyboard/focus, reduced-motion, landmarks), the `not-covered` honesty
rule, and where the design skills it advertises (`apple-design`, `hallmark`,
`high-end-visual-design`, `emil-design-eng`, and the other design skills in the roadmap's
design rows) plug in — as *insumos* the design skill may load, never as skills of the
framework itself (spec 037 roadmap table rows 6/16 recorded this). The reference is loaded
only when a verify pass runs, keeping the context economy (spec 033).

## Challenged once

**"A WCAG rule in a design skill is the style-imposition the skill explicitly refuses
('imposes no style')."** The refusal is about *style* — fonts, palettes, layout taste — not
about *accessibility*, which is a functional floor: contrast, keyboard reachability and
reduced-motion are not a look, they are whether people with disabilities can use the
thing. The rule checks the floor and marks `not-covered`; it never says a surface must look
a certain way. The clean control: an "editorial" design with low-contrast text styled
*deliberately* still fails the floor unless it says why (and a `not-covered` with a reason
is the honest exit, never a silent pass).

**"Another contract lane grows contract.py; is a11y really the framework's problem?"**
The framework's mission includes governed work on regulated companies; an interface the
framework produces that fails basic a11y is a compliance risk it handed the stranger. The
lane is one function in the existing audit, and the fixture proves both halves (floor
holds / not-covered with reason). This is the smallest checked form of the discipline.

## Assumptions and unresolved risks

- Assumption: contrast ≥ WCAG AA and the keyboard/focus/reduced-motion set is the right
  first floor; a later measured need may add landmarks, screen-reader labels or more —
  config/rule growth, not a new architecture.
- Assumption: `references/accessibility.md` loaded only on verify keeps the context
  economy; a design that never reaches verify never pays the reference's tokens.
- Unresolved: ai-design is the design gateway today; whether a11y also needs a lane on
  other producing surfaces (marketing, docs) is a later measured need, not this spec.
- Unresolved: the inherited `madr.validate` red from ADR 0025 stays open; this spec does
  not authorise rewriting that history.

## Examples somebody can check

- **Success, floor holds:** Given a designed surface whose verify pass names contrast ≥ AA,
  keyboard reachability, visible focus and reduced-motion, When `_accessibility_problems`
  reads it, Then it returns no problems (`uv run --with pytest==9.1.1 pytest -q
  tests/test_038_accessibility.py -k floor` → `1 passed`).
- **Denial, silent pass:** Given a designed surface whose verify pass omits the a11y basics,
  When the rule reads it, Then it is refused with `INCOMPLETE: a11y not-covered <reason>`,
  never a bare pass (`-k not_covered` → `1 passed`).
- **Honest exit:** Given a surface that deliberately cannot meet a check, When it says
  `not-covered: <reason>`, Then the rule accepts it with the reason recorded (`-k honest`
  → `1 passed`).
- **Reference loads:** Given `references/accessibility.md`, When a verify pass needs it,
  Then it names the concrete checks and the `not-covered` rule (`-k reference` →
  `1 passed`).

## Decisions

**D-038-01 — accessibility is a functional floor in ai-design's verify route, never a
style imposition.**
Rationale: the skill's "imposes no style" refusal covers look, not disability; the floor
(contrast/keyboard/focus/reduced-motion) is checked by a contract lane exactly like the
other disciplines, and a surface that cannot meet it exits honestly with `not-covered`.

**D-038-02 — the a11y discipline ships as one reference beside ai-design, laden only on
verify; the design skills of the roadmap stay insumos, not framework skills.**
Rationale: skill anatomy allows references (the ai-review pattern), context economy says
load on demand, and the roadmap already records the design rows as insumos the design
skill may use — not as fifteen more skills.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification adds one contract lane, one reference and one fixture; no service, no URL,
no second hop — the service-shaped boxes are `not applicable`.

- [x] CI/CD — `just check` runs `tests/test_038_accessibility.py` on every push (`.github/workflows/check.yml`); nothing deployed
- [x] Logs — not applicable: every verb still emits the one JSON line `ai-eng report digest` reads
- [x] Traces — not applicable: one process, no second hop
- [x] Errors — not applicable: the new path fails closed (a silent pass is refused; `not-covered` with reason is the honest exit)
- [x] Health and data age — the 038 fixture runs in the gate's pytest half (`just cover`'s `not fast_enough` collection) on every push
- [x] External check — `.github/workflows/check.yml` runs the whole gate on every push; the floor is additionally asserted by its fixture, the independent route
- [x] Second path — the lane is read by its fixture and the reference by the same fixture, with no shared line
- [x] Security — `just security`: gitleaks, semgrep, trivy on every push, over a change that adds no dependency and no network call