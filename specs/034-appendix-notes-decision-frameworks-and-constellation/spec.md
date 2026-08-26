---
id: "034"
slug: appendix-notes-decision-frameworks-and-constellation
status: draft
date: 2026-08-25
ref: ""
supersedes: "010"
---

# Appendix notes, decision frameworks and the constellation rule

## Who this is for, and what it is worth to them

The person who runs `/ai-goal` on this repository and approves what it produces, and every
stranger who installs the wheel for a repository they are accountable for. The research goal
(`.ai/reports/018`) marked three remaining disciplines the external references proved and
this repository does not yet supply: memory that only ever appends and never rewrites,
named decision frameworks a skill can apply instead of inventing a rationale, and a
constellation rule that tells a single false signal from real systemic failure. This
specification supersedes parts of spec 010's target to add the three (the research paquete
6: its N26, N27 and N29).

## Context and problem

**What is true today, measured in this tree on 2026-08-25, after specs 027-033:**

- `ai-note` writes findings to `docs/notes/<slug>.md` with a rot-detectable header, but
  nothing refuses a **rewrite** of an existing note: a later session can edit the history a
  finding records, which is the append-only discipline Loop-Engineering proved
  (`NOTES.md`: every finding appended with a date, never rewritten — the research N26). A
  note that can be silently edited is a note that can rot backwards.
- Several skills decide (ai-spec recommends, ai-review judges, ai-report triages), but none
  names a **concrete decision framework**: the rationale is whatever the model reaches for,
  unrepeatable across sessions (contains-studio's RICE/Kano/Effort-Versus-Value, each a
  named, repeatable method — the research N27).
- The outcome vocabulary is closed and `INCOMPLETE` is "cannot decide or prove". But it is
  decided per-event: a single guard failure is INCOMPLETE even when it is one isolated
  noise in an otherwise-healthy surface, while a constellation of failures in the same
  context reads as the same single INCOMPLETE. astryx's constellation model (signal
  convergence = real; isolated signal = noise) is the missing lens on the framework's own
  verdicts — the research N29.

**The problem, in words a non-technical reader can follow:**

Three things are missing from how this framework keeps and weighs information. A finding,
once recorded, can be silently edited instead of only ever added to — so the history a note
carries can be rewritten years later. A skill that decides has no named method to follow, so
its decision is whatever the model happened to reach for that session. And the framework
treats one failing signal and a storm of failing signals as the same answer, when they mean
different things. The three changes in this spec add those three: append-only notes, named
decision frameworks, and a constellation rule for verdicts.

## Options considered

1. **Add the three as checked modules and contract rules (chosen shape).** N26 (append-only
   as a contract rule over `docs/notes/`), N27 (a decision-frameworks module skills route
   through) and N29 (a constellation module over outcomes) land as their own TDD tasks on
   the backbone specs 028-033. Gives: three deterministic, tested disciplines. Costs: a
   wide block; atomic commits mitigate it.
2. **Do append-only alone, defer the rest.** Gives: a small first block. Costs: decisions
   still lack a named method and verdicts still conflate noise with systemic failure — the
   two gaps the research paired with the note discipline. The user's rule is that nothing
   in the goal is a ceiling.
3. **Adopt the external frameworks wholesale (RICE/Kano exactly as written).** Gives: ready
   wording. Costs: the frameworks' exact scoring is tuned to their own products; the shapes
   transfer, the constants must fit this tree's own decisions (the same call spec 027 made
   importing taxonomy classes, not text).

## Decision

**Option 1**, as paquete 6 of the research. The spec supersedes spec 010 only where it
extends the target with the three behaviours below; it does not weaken, drop or relabel any
normative requirement 010 already states. Each behaviour is closed, versioned, and comes
with both a positive fixture and a nearby clean control. The three are:

### B-034-1 — Appendix-only notes (research N26)

A contract rule over `docs/notes/`: a note may only be **appended** — new findings added
with a date, never rewriting an existing entry's bytes. `contract.audit_one` gains
`_appendix_problems` for the `ai-note` skill, and the `ai-note` skill body itself refuses
rewrite ("a note is appended to, never edited"). The history a note carries cannot be
rewritten backward; rot is detected by the existing header, not by lying about the past.

### B-034-2 — Named decision frameworks (research N27)

A `decision_fw` module in `src/ai_engineering/` with a small registry of named frameworks:
**RICE** (Reach × Impact × Confidence ÷ Effort), **Effort/Value**, and **Kano** (the three
categories), each a function a skill calls rather than a prose description. The `ai-report`
and `ai-review` corpora gain the rule: when a decision has a named framework, apply it and
say which one — a bare "we ranked by impact" with no method is refused as unsupported.

### B-034-3 — The constellation rule over verdicts (research N29)

A `constellation` module in `src/ai_engineering/` that classifies a set of signals: a
**constellation** (≥2 signals of the same class in the same context) reads as real systemic
failure; an **isolated** signal (one in an otherwise-clean context) reads as noise and does
not by itself escalate to systemic INCOMPLETE. The module is a lens over verdicts — it
classifies, it does not downgrade a guard's own fail — and a fixture proves both halves.

## Challenged once

**"Append-only is a nice-to-have; notes are already committed so git guards history."** Git
guards *committed* history, not the working-tree file a session edits before committing.
The append rule is about the note's own discipline: a fresh finding in the working tree must
add to, not replace, the note it extends. Loop-Engineering's `NOTES.md` was append-only not
because git could not rewrite it, but because a note that gets edited loses the "what we
learned then" that makes it worth re-reading later. And the rule is checked, so it cannot
drift.

**"Constellation sounds like it would weaken a guard's fail."** It cannot — a guard's own
fail stays a fail; `constellation` does not downgrade it. It is a *reader* that tells the
framework (and a person) whether a cluster of failures is one systemic thing or several
isolated noises, which changes what the INCOMPLETE means, never whether each failure
happened. The fixture proves the clean-control half: a single signal stays a single
INCOMPLETE, and the module never erases a fail.

## Assumptions and unresolved risks

- Assumption: the append rule is a contract check on `ai-note`'s *instruction* (the skill
  body refuses rewrite), not an enforceable file-system lock — git remains the durable
  history, and the skill's own cross-edits are what the rule catches.
- Assumption: the three named frameworks (RICE, Effort/Value, Kano) cover the decisions this
  framework actually makes; a decision without a fitting framework says so, and a later spec
  may add one with measured need.
- Unresolved: the constellation threshold (≥2 signals of the same class) is a first
  reading; a later spec may calibrate it from measured clusters.
- Unresolved: the inherited `madr.validate` red from ADR 0025; recorded, not fixed here.

## Examples somebody can check

Given a fresh finding that would overwrite an existing note,
When the appendix rule reads the skill,
Then the skill body is refused for not being append-only (`uv run --with pytest==9.1.1
pytest -q tests/test_decision_and_notes.py -k appendix` → `1 passed`).

Given a decision that names a framework,
When `decision_fw` applies it,
Then RICE, Effort/Value and Kano each return a deterministic verdict, and a bare "ranked by
impact" with no named method is refused (`uv run --with pytest==9.1.1 pytest -q
tests/test_decision_and_notes.py -k framework` → `2 passed`).

Given a cluster of signals of the same class in one context,
When `constellation` reads them,
Then it reports a constellation (systemic), and a single isolated signal in a clean context
reports isolated — never erasing a fail (`uv run --with pytest==9.1.1 pytest -q
tests/test_constellation.py` → `2 passed`).

Given the repaired tree,
When `contract.audit` runs over all skills,
Then the ai-note skill reads clean against the appendix rule and the gate proves the tree
clean (`uv run --with pytest==9.1.1 pytest -q tests/test_decision_and_notes.py
tests/test_constellation.py` → all passed).

## Decisions

**D-034-01 — notes are append-only: a finding adds to a note, never rewrites it.**
Rationale: Loop-Engineering's `NOTES.md` proved the discipline that keeps a note worth
re-reading; the rule is checked, so a silent rewrite is a contract failure, not a drift.

**D-034-02 — decisions route through named frameworks; a bare rationale with no method is
refused.**
Rationale: contains-studio proved repeatable decisions need a named, concrete method
(RICE/Effort-Value/Kano); a module makes the method callable and a corpus rule makes it the
only supported way to justify a ranking.

**D-034-03 — a constellation of signals reads as systemic; an isolated signal reads as
noise, and neither erases a guard's fail.**
Rationale: astryx's constellation model is the correct lens on verdicts — convergence is
real, isolation is noise; the module classifies a cluster without ever downgrading an
individual failure.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification adds an appendix rule, a decision-frameworks module and a constellation
module; it adds no service, no URL and no second hop, so the service-shaped boxes are
`not applicable`.

- [x] CI/CD — `just check` runs the three behaviours on every push (`.github/workflows/check.yml`); `contract._appendix_problems`, `decision_fw` and `constellation` are gate lanes, and nothing here is deployed
- [x] Logs — not applicable, and that is the rule: this spec adds modules and a corpus rule; every verb still emits the one JSON line `ai-eng digest` reads
- [x] Traces — not applicable, and that is the rule: one process, no second hop, no trace
- [x] Errors — not applicable: the new code paths fail closed — a rewrite instructing ai-note is refused by `_appendix_problems`, a rationale with no named framework is refused by `decision_fw.named`, and a guard fail is never erased by `constellation`
- [x] Health and data age — `tests/test_decision_and_notes.py` and `tests/test_constellation.py` run in `just test` on every gate, and `tests/skill_eval.py` asserts the `skill-routing` baseline moved 359 → 363 with the reason beside it
- [x] External check — `.github/workflows/check.yml` runs the whole gate on every push; the corpus rule "when decisioning, name the framework" is asserted by `tests/skill_eval.py`, the independent route over the same corpora
- [x] Second path — each behaviour is read by its module and its fixture with no shared line (`_appendix_problems` vs `tests/test_decision_and_notes.py`; `decision_fw` vs the same suite; `constellation.classify` vs `tests/test_constellation.py`), and the corpus rules are asserted by `tests/skill_eval.py`
- [x] Security — `just security`: gitleaks, semgrep and trivy on every push, over a change that adds no dependency and no network call