---
id: "032"
slug: standard-skill-craft-contract
status: draft
date: 2026-08-25
ref: ""
supersedes: "010"
---

# The standard skill-craft contract

## Who this is for, and what it is worth to them

The person who runs `/ai-goal` on this repository and approves what it produces, and every
stranger who installs the wheel for a repository they are accountable for. The research goal
(`.ai/reports/018`) marked four authoring disciplines the external references proved
load-bearing and this repository does not yet check: anti-rationalization tables that answer
the agent's excuses, output contracts that fix what a skill must produce, Incorrect/Correct
rule pairs that remove interpretation, and load tiers that keep a skill's body small and its
scripts out of context. This specification supersedes parts of spec 010's target to add the
four as **checked contract rules** in `contract.audit_one`, exactly the way spec 027 added
its four smell rules — one rule per task, then a repair pass over the shipped skills, then a
test proving the tree reads clean.

## Context and problem

**What is true today, measured in this tree on 2026-08-25, after specs 027-031:**

- `contract.audit_one` already refuses four smell classes (spec 027): portable-command,
  existence-check, forced-output, sourced-statistic. The skill pairs were repaired and the
  gate proves the tree reads clean.
- The corpus/eval harness (`skill_eval.py`, `pilot-register.toml` baseline 355) proves the
  skills route; the evals harness (spec 029) scores review skills against planted defects;
  the contract skims (spec 030) bound coverage. What none of them checks is the **authoring
  shape** the research flagged: an agent's excuses for skipping a step, a skill whose output
  is prose rather than a named artifact, a rule stated as prose instead of a
  Incorrect/Correct pair, and a body that grows beyond what a surface loads.
- The four external references the research measured:
  - **anti-rationalization** (agent-skills) — every skill carries a table of the excuses an
    agent makes to skip work, each with a factual counter. "It's simple" is answered with
    "then it is fast to prove".
  - **output contracts** (headstart, okf) — a skill names the exact shape of what it
    produces; prose "verify" is not an output.
  - **Incorrect/Correct** (AL-Design, shadcn rules) — a rule is a pair of code blocks, one
    forbidden and one correct; interpretation is a source of drift.
  - **load tiers** (graph-engineering, agent-skills anatomy, make-claude) — a skill's
    `name`+`description` load always (~100 words), its body loads on trigger (≤500 lines),
    references load on demand, and its scripts are executed, never read into context.

**The problem, in words a non-technical reader can follow:**

A skill that cannot answer the agent's excuses gets skipped mid-step. A skill whose output
is not a named artifact cannot be verified. A rule without the forbidden-and-correct pair
leaves room to interpret. And a skill that grows too large costs the surface that loads it.
The four changes in this spec make all four shapes checked contract rules — a script decides
whether a skill meets them, so the discipline is enforced rather than requested.

## Options considered

1. **Add the four as checked rules in `contract.audit_one`, then repair the shipped skills
   (chosen shape).** Each rule is its own TDD task with a red fixture first; the repair pass
   brings every shipped pair under the new contract; a final test proves the whole tree
   reads clean. Gives: the exact pattern spec 027 proved — rules the script refuses, a
   repair that makes the tree green, and a gate that catches reintroduction. Costs: a
   repair pass over the shipped skills. Rules out: weakening any of the four.
2. **Document the four as guidance in the authoring skill, no script.** Gives: a small
   change. Costs: spec 027's measured lesson — prose guidance is skipped; the contract
   smells reappeared until a rule refused them. The user's rule is that nothing in the goal
   is a ceiling, and a discipline nobody checks is a discipline that drifts.
3. **Adopt the four wholesale from the external references.** Gives: ready wording. Costs:
   the references' exact tables are tuned to their own stacks; the shapes transfer, the
   wording must fit this tree's vocabulary (the same decision spec 027 made importing the
   taxonomy classes, not the text).

## Decision

**Option 1**, as paquete 4 of the research. The spec supersedes spec 010 only where it
extends the target with the four checked rules below; it does not weaken, drop or relabel
any normative requirement 010 already states. Each rule is closed, versioned, and comes
with both a positive fixture and a nearby clean control. The four are:

### B-032-1 — Anti-rationalization table (research N5)

Every shipped `SKILL.md` must carry an **anti-rationalization table**: a `## What this is
not`-style section (or an explicit `## Anti-rationalizations` table) that names at least
one excuse the agent could make to skip the skill's work and answers it with a factual
counter in the same entry. `contract.audit_one` gains `_anti_rationalization_problems`:
a skill with no such section, or a section whose entries lack the counter, is refused.

### B-032-2 — Output contract (research N6)

Every shipped `SKILL.md` must carry a **`## What it produces`** section that names the
exact artifact(s) it outputs — a path, a file, a record, a verdict — not a "verify"
instruction or prose. `contract.audit_one` gains `_output_contract_problems`: a skill whose
exit names no artifact is refused (this sharpens spec 027's forced-output rule from "no
weak exit" to "the exit names its shape").

### B-032-3 — Incorrect/Correct rule pairs (research N9)

A skill that gives rules (style, composition, security, API use) must state each rule as a
pair: a `## Rules` section whose entries are `Incorrect`/`Correct` code blocks.
`contract.audit_one` gains `_incorrect_correct_problems`: a skill whose body carries a rules
section with a bare prescription and no pair is refused; a skill with no rules section
passes (the rule applies where rules exist).

### B-032-4 — Load tiers (research N11)

A shipped `SKILL.md` must keep its body within the load budget the surfaces give it: ≤500
lines, with scripts that would inflate it moved to a `scripts/` subfolder that is executed
and never read into context. `contract.audit_one` gains `_load_tier_problems`: a body over
500 lines is refused, and an inline `python3 - <<` / long embedded script body is refused
in favour of a `scripts/` file.

## Challenged once

**"Most shipped skills have no rules section, so Incorrect/Correct will either refuse
nothing or force fake pairs."** The rule is scoped exactly to avoid that: it fires only
where a `## Rules` section exists — a skill with no rules passes, a skill with rules stated
as bare prose is refused. The repair pass adds a rules section only to the skills that
actually give rules (the review lenses, the design skill); the others stay untouched. The
test proves both halves: a fake pair is as refused as a missing one.

**"500 lines is a ceiling that will be spent like a budget."** Spec 027 already refuses the
four smell classes and spec 026 bounds the catalogue; 500 is not a budget to spend but a
floor the surfaces genuinely enforce — the research measured that bodies over ~500 lines are
read partially or skipped (graph-engineering's tier model). The repair pass keeps every
body well under it; the rule catches the growth, it does not invite it.

## Assumptions and unresolved risks

- Assumption: every shipped skill can name its output artifact and carry at least one
  anti-rationalization entry without inventing either. If a skill cannot, its row reports
  the gap (the pilot-register's honest shape) rather than inventing one.
- Assumption: the load-tier bound matches what the installed surfaces actually read
  (`name`+`description` in the catalogue, body on trigger, references on demand).
- Unresolved: the inherited `madr.validate` red from ADR 0025; recorded, not fixed here.
- Unresolved: a skill whose rules are best shown as prose (an interview discipline) — the
  Incorrect/Correct rule passes it, and a later spec may widen the rule with measured need.

## Examples somebody can check

Given a skill with no anti-rationalization section,
When `contract.audit_one` reads it,
Then it is refused for missing the table; a skill whose table answers an excuse is passed
(`uv run --with pytest==9.1.1 pytest -q tests/test_contract_craft.py` → `1 passed`).

Given a skill whose exit names no artifact,
When the output-contract rule reads it,
Then it is refused; a skill whose `## What it produces` names a path is passed
(`uv run --with pytest==9.1.1 pytest -q tests/test_contract_craft.py -k output` → `1 passed`).

Given a skill with a rules section stated as bare prose,
When the Incorrect/Correct rule reads it,
Then it is refused; a skill with an Incorrect/Correct pair passes, and a skill with no
rules section also passes (`uv run --with pytest==9.1.1 pytest -q
tests/test_contract_craft.py -k pairs` → `1 passed`).

Given a skill body over 500 lines,
When the load-tier rule reads it,
Then it is refused; a body under the bound with scripts in `scripts/` is passed
(`uv run --with pytest==9.1.1 pytest -q tests/test_contract_craft.py -k load` → `1 passed`).

Given the repaired tree,
When `contract.audit` runs over all skills,
Then no shipped SKILL.md triggers any of the four new rules, and the gate proves the tree
reads clean (`uv run --with pytest==9.1.1 pytest -q tests/test_contract_craft.py` → all
passed).

## Decisions

**D-032-01 — anti-rationalization is a checked rule: a skill must name at least one excuse
and answer it factually in the same entry.**
Rationale: agent-skills proved the table is a practical counter to skipped steps; the
contract rule is what makes the table exist (spec 027's measured lesson: prose guidance is
skipped).

**D-032-02 — an output contract is a checked rule: `## What it produces` names the exact
artifact, and a prose exit is refused.**
Rationale: headstart/okf both proved that naming the output is what makes a skill's result
verifiable; this sharpens spec 027's forced-output rule from "no weak exit" to "the exit
names its shape".

**D-032-03 — Incorrect/Correct pairs are a checked rule where rules exist.**
Rationale: AL-Design's shadcn rules proved the pair removes interpretation; the rule fires
only where a `## Rules` section exists, so it never forces fake pairs.

**D-032-04 — load tiers are a checked rule: body ≤500 lines, scripts in `scripts/` executed
never read.**
Rationale: graph-engineering and make-claude both measured that bodies over ~500 lines are
read partially and inline scripts burn context; the bound is a floor the surfaces enforce,
not a budget to spend.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI