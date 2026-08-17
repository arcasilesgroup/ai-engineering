---
id: "016"
slug: the-thesis-nobody-owns
status: draft
date: 2026-08-15
ref: ""
supersedes: ""
---

# The thesis nobody owns

Draft. Nothing may be implemented from it until a human approves it at an exact digest, and
approving it approves no plan. Derived from the structural gap named in
`docs/audit-2026-08-15.md` — thirty-six requirements with no owning spec — and from the four
measurements in this document, each rerun here rather than quoted from the audit's commit.

## Context and problem

Specs 011 through 015 own the five waves of `.ai/reports/evolution-proposal/index.html`.
Nothing owns the document's own thesis: its mission, its comparative X-ray "Propuesta"
column, and its catalogue admission rules. Those are `EP-062` through `EP-097`, plus
`EP-098`, `EP-099` and `EP-102`.

**The audit's count is one too many, and this document says so first.** `EP-062..EP-097` is
thirty-six identifiers; `EP-081` belongs to spec 011. Thirty-five are unowned there.
`EP-100` and `EP-101` are already a row in spec 012's closing table, so the three admission
rules left over are `EP-098`, `EP-099` and `EP-102`. Thirty-eight in total, and the table
below carries every one.

Four of them are not "unowned prose". They are measured defects, and each was rerun for this
draft rather than taken on the audit's word.

**1. `EP-066` — the corrected mission is not in the identity file.** The proposal's mission
names nine verbs and a controls/guardrails/harnesses/traceable-evidence clause. Scanning
`CONSTITUTION.md`:

```
for w in discover specif decid review plan implement verif validat audit \
         guardrail harness traceable; do
  printf '%-12s %s\n' "$w" "$(grep -ic "$w" CONSTITUTION.md)"; done
```

`discover 2`, `specif 1`, `decid 3`, `review 4`; `plan 0`, `implement 0`, `verif 0`,
`validat 0`, `audit 0`, `guardrail 0`, `harness 0`, `traceable 0`. **Five of the nine verbs
are absent, not four** — the audit undercounted by one — and so is the whole guardrails
clause. `ai-eng doctor` assertion 4 reads that file and prints `ok`, because it checks
length and placeholders, not content.

**2. `EP-090` — the JSON envelope validates against nothing.** `ai-eng spec list --json`
emits twelve fields: `schema_version`, `command`, `operation_id`, `started_at`,
`finished_at`, `outcome`, `summary`, `changes`, `checks`, `remaining`, `next_actions`,
`error`. Validating that object against `policy/outcome-v1.schema.json`:

- four required properties are missing — `schema`, `exit_code`, `reason`, `next_action`;
- ten of the twelve emitted fields violate its `additionalProperties: false`.

`grep -rln operation_id policy/` returns nothing. The envelope is built inline in `cli.py`
and no file in `policy/` describes it. What *is* pinned is the terminal `Result` —
`outcome.py` holds the schema's SHA-256 and refuses to run if it changes — so the exact half
is guarded and the wider object beside it is not. The payload also carries
`schema_version: "1"` with no `schema` naming which contract version 1 belongs to, which is
the one field a machine consumer needs to know what it is reading.

**3. `EP-084` — no event carries a surface.** `hooks/_emit.py` declares the closed set
`("blocked", "allowed", "bypassed", "command", "error", "session")` and raises on anything
else, so the "never `hook ran`" half of the requirement holds. The event body is `ts, cls,
name, session, repo, machine, operation_id, trace_id, data`. No surface. No adapter.
`hooks/_otlp.py` keeps `ms` — latency — and no surface or adapter field either. The third
part, export result, **has landed since the audit**: commit `4e9fd0b4` made
`hooks/session.py` record `status`, `rejected` and `sent` when a collector refuses records.
That is not re-planned here.

**4. `EP-095` — no stakeholder or value section exists.** Grepping `stakeholder`,
`audience`, `value statement` and `non-technical` across `.agents/`, `src/`, `policy/` and
`tests/` returns three hits and only one instruction between them:
`.agents/skills/ai-spec/SKILL.md` asks the author to state the problem in words a
non-technical reader can follow, `tests/test_contracts.py` pins that same sentence, and the
third is the word `audience` inside a ceiling comment in `contract.py`. `spec.py`'s
template has six headings — Context and problem, Options considered, Decision, Decisions,
Accepted risks, Production-ready — and none of them names who the work is for. Nothing
checks for either.

The harm of leaving it: a wave can close green while the thesis it exists to serve is absent
from the file that states this project's identity. Four measured gaps sit in a range no
specification is responsible for, and an unowned requirement is never anybody's red line.

## Options considered

**A. Own the four measurable gaps; route the rest to the spec that already holds the
mechanism.** This document takes `EP-066`, `EP-084`, `EP-090` and `EP-095` as work with a
check each, records the requirements that cannot go red as unfalsifiable, and points the
remaining twelve at specs 011–015 without restating their contracts.

*Gives:* every requirement in the range has exactly one home, and the four with a possible
red get a command that produces it. *Costs:* one schema file, one sentence in
`CONSTITUTION.md`, one template heading and its lint, one event field. *Risks:* the
stakeholder heading becomes a box nobody has to fill; the envelope schema gets written from
`cli.py` and therefore cannot contradict it. *Rules out:* a thesis document nothing executes.

**B. Own the whole range here, restating the "Propuesta" column as obligations of this
spec.** Every row of the comparative X-ray becomes a normative line in this document.

*Gives:* one place to read the thesis end to end. *Costs:* twelve requirements acquire a
second home, and the two homes drift the first time one is edited. *Risks:* it cannot fail.
A restatement of five approved specs is prose, and `EP-300` already measured what this shape
does — one surface-id list written in four files with a single bound pair. *Rules out:*
nothing, which is the problem.

## Decision

**Option A.** The deciding reason is not scope. It is that B produces a document whose every
line is already true somewhere else, so no command can ever turn it red — and this range
exists precisely because the audit found twenty controls that read stronger than they are.

**Challenged once, honestly:** the strongest case against A is that it edits
`CONSTITUTION.md`, and `EP-071` and `EP-097` both require that file to stay short and never
become a second normative layer — a mission that grows nine verbs and a guardrails clause is
how an identity file turns into a policy document. That case is real and it changes the
shape: the addition is **one sentence inside the existing `## Mission` section**. No new
heading, no new file, and the doctrine ceiling in `tests/test_contracts.DOCTRINE_CEILING`
stays where it is. If the sentence will not fit, the ceiling moves in a commit that says
why, which is the rule `AGENTS.md` already sets.

## Normative contract

Where this section and spec 010 differ, spec 010 governs and this document is wrong.

- The mission recorded in `CONSTITUTION.md` names all nine verbs — discover, specify,
  decide, plan, implement, review, verify, validate, audit — and the controls, guardrails,
  harnesses and traceable evidence clause. A check reads that file, not a copy of it, and
  fails when a verb is missing.
- The JSON envelope validates against a schema that lives in `policy/`, on every verb that
  emits one. The schema pins the field set closed and requires the envelope to name its own
  contract. It **references** `policy/outcome-v1.schema.json` for the seven outcomes and
  does not restate them.
- The check that enforces it validates output captured from a real CLI run. A fixture the
  test constructs itself proves only that the test agrees with the test.
- Every event that has a surface records it, with the adapter that produced it. An event
  whose surface cannot be determined records `undetermined`. No default, ever: an
  attribution nobody earned is the same defect as a coverage word nobody earned.
- The six event classes stay closed and `hook ran` stays absent.
- A spec and a ship carry one short section naming who the work is for and what changes for
  them. It is checked for presence and for still holding the template's placeholder.
- No requirement in this range is reworded so that the repository passes it. A requirement
  with no possible red is recorded as unfalsifiable and left alone.

## What this closes

Thirty-eight rows. "Today" is what was measured in this tree. PROVEN rows are done and are
named so that nobody re-plans them; ROUTED rows belong to the spec named and are not
re-specified here.

| Requirement | Today | What closes it |
|---|---|---|
| EP-062 | UNFALSIFIABLE | nothing; a mission with no metric. Its recordable half is EP-066 |
| EP-063 | UNFALSIFIABLE | nothing; "where the decision changes" names no observable |
| EP-064 | UNFALSIFIABLE | nothing; `grep -ril traceab src/ hooks/ policy/ .agents/` → no hit |
| EP-065 | UNFALSIFIABLE | nothing for "one evidence per promise"; the one-home half is `ai-eng doctor` assertion 18 → `ok` |
| EP-066 | INCOMPLETE | one Mission sentence in `CONSTITUTION.md`, all nine verbs plus the guardrails clause, read by a check |
| EP-067 | PROVEN | `python -c "from ai_engineering import outcome; print(outcome.result('GREEN').outcome)"` → `INCOMPLETE` |
| EP-068 | UNFALSIFIABLE | nothing; the seven criteria are one line each in `AGENTS.md` rule 10, and no rubric exists |
| EP-069 | PROVEN | `ai-eng doctor` → exit 1, "None of these is a pass. Not evaluated is never green." |
| EP-070 | PROVEN | `grep -n supersedes policy/madr-v1.schema.json` → required; relations are typed fields |
| EP-071 | PROVEN | `git ls-files \| grep -ci soul` → `0`; `## Values` is four bullets |
| EP-072 | PROVEN | `grep -n fixed_constraints policy/intent-v1.schema.json` → required with the other three |
| EP-073 | UNFALSIFIABLE | nothing; "conditions the future" is the judgement `ai-eng decide --madr` leaves to a person |
| EP-074 | ROUTED to 012 | `ai-test` (EP-115..117) and `ai-verify` (EP-127, EP-128) |
| EP-075 | ROUTED to 011, 014 | per-surface version and proof age (011); evidence and risk links on export (014) |
| EP-076 | PARTLY RECORDED | the audience half is `## Who it is for`; the never-green half is `## Never`; the verbs half is EP-066 |
| EP-077 | ROUTED to 011 | one canonical payload, adapters per surface, wheel-installed proof |
| EP-078 | ROUTED to 012 | admission checks in `contract.audit_one`; the roadmap itself is EP-098 |
| EP-079 | PARTLY PROVEN | `ai-eng doctor` prints scope, `RUNNING n/4`, outcome, reason, next action, exit code. The JSON half is EP-090 |
| EP-080 | ROUTED to 012 | EP-270..EP-275: local draft, two scans, byte preview, private route |
| EP-082 | ROUTED to 014 | the security baseline and its PASS/FAIL/INCOMPLETE |
| EP-083 | SPLIT | v1 gates stand — `just --list` shows `check` over build, lint, typecheck, test, cover, security, counts. The evals half is unfalsifiable; see below |
| EP-084 | INCOMPLETE | surface and adapter on every event that has one, `undetermined` where it cannot be decided. The export-result third landed at `4e9fd0b4` |
| EP-085 | ROUTED to 012 | AA as the floor, AAA recorded rather than gated (D-012-05) |
| EP-086 | ROUTED to 013 | origin, branches, worktrees, draft PR, CI, merge queue |
| EP-087 | UNFALSIFIABLE | nothing; a comparative claim with no runnable legacy and no benchmark |
| EP-088 | ROUTED to 012 | one refusal fixture per existing skill (EP-103..EP-110) |
| EP-089 | PROVEN | `find .agents/skills -type d -name references` → only `ai-review/references` |
| EP-090 | INCOMPLETE | an envelope schema in `policy/`, validated against captured CLI output |
| EP-091 | ROUTED to 012 | `ai-design` and `ai-animation` as files with rendered evidence |
| EP-092 | PROVEN | `ai-eng doctor` assertion 18 → `ok  Your data is yours: every framework file has a declared home` |
| EP-093 | UNFALSIFIABLE | nothing; "stable baseline" has no definition and no owner. See below |
| EP-094 | ROUTED to 014 | SBOM in the existing release workflow (EP-049), provenance unchanged |
| EP-095 | NO CHECK | one short audience-and-value section in spec and ship, checked for presence and placeholder |
| EP-096 | ROUTED to 013 | DAG, worktree per task, checkpoints, queue; no authority-envelope subsystem |
| EP-097 | PROVEN | four value lines in `CONSTITUTION.md` and no second home: `git ls-files \| grep -ci soul` → `0` |
| EP-098 | PROVEN | `grep -c '^\[\[capabilities\]\]' policy/capabilities.toml` → `15`, exactly the eight plus the seven named |
| EP-099 | PROVEN | `ls .agents/skills` → nine, no brainstorm skill; discovery is step 1 of `ai-spec/SKILL.md` |
| EP-102 | PROVEN | nine skills against ten verbs in `ai-eng --help`; `spec` and `report` have a same-named skill and the other eight — `init`, `doctor`, `update`, `decide`, `accept`, `audit`, `exception`, `uninstall` — have none |

### What `EP-098` proves, and what it does not

`policy/capabilities.toml` holds fifteen declarations and they are exactly the roadmap the
proposal names. That is the requirement as written and it is met. It is also the whole of
it: `ai-eng doctor` assertion 23 prints `15 capabilities are declared and none is enforced`.
The declaration is proven; the enforcement is spec 012's and spec 014's, and this row is not
a claim that the fifteen skills exist.

### Nine requirements cannot be made red as written

Written here rather than quietly sharpened, because inventing a crisp version of a vague
requirement is how a wave closes on work nobody specified.

**EP-062, EP-063, EP-065, EP-087 — the thesis paragraphs.** "Without turning autonomy into
unlimited authority", "the person enters where the decision changes", "one executed evidence
per promise", "v1 already beats legacy in truth". Each names an intent and none names a
thing to count. A check written for any of them would pass on the day it was written,
because whoever writes it also chooses what it counts.

**EP-064 — the central metric.** "How many steps are traced from intent to an evidence that
can go red." This is the most tempting one in the range: it sounds countable. It is not,
until somebody states what a step is and what makes an evidence red-capable, and both of
those choices decide the answer. `grep -ril traceab` over `src/`, `hooks/`, `policy/` and
`.agents/` returns nothing, so there is no existing definition to borrow.

**EP-068 — rubrics for KISS, YAGNI, DRY, SOLID, Clean Architecture and Clean Code.** The
criteria are one line each in `AGENTS.md` rule 10 and one line each in every spec's
Engineering criteria section. The rubric is unwritten. Rule 12 turns a judgement into a
script after it has resolved the same way three times; these have not been recorded
resolving once, so no rubric ships and the judgement stays a prompt.

**EP-073 — "when the decision conditions the future".** The condition for promoting a
decision to an MADR. `ai-eng decide --madr` already leaves that call to a person, which is
the honest answer while the judgement is unrecorded.

**EP-083 and EP-093 — evals.** "Only for new probabilistic skills", "cross-model replay
advisory", "block only after a stable baseline". No threshold, no baseline definition, no
evaluation runner in this repository — spec 012 records the same absence when it refuses
EP-029. The v1 gates half of EP-083 stands on its own and is proven; the evals half has no
owner and this spec does not become one by restating it.

## Non-goals

- No new verb. The ten in `ai-eng --help` are frozen.
- No thesis document. No `docs/thesis.md`, no mission page, no second normative layer.
- No change to `policy/outcome-v1.schema.json`, to its pinned digest, or to the six event
  classes.
- No re-plan of the export-result recording. It landed at `4e9fd0b4`.
- No work that specs 011–015 own: no adapter, no capability file, no coordination, no
  scanner, no pilot instrument.
- No rubric for the seven engineering criteria, and no invented metric for EP-064.

## Engineering criteria

- **KISS** — one sentence, one schema, one field, one heading. Four changes, four checks.
- **YAGNI** — the twenty-nine requirements with no possible red get no code at all.
- **DRY** — the envelope schema references the outcome schema; it never copies the seven.
- **SOLID** — the schema describes the envelope; `cli.py` builds it; neither validates
  itself.
- **TDD** — each of the four checks is red against today's tree before its fix exists.
- **Clean Code** — an event with no determinable surface says `undetermined`, not a guess.
- **Clean Architecture** — the schema is data in `policy/`, the check is code, and `hooks/`
  keeps importing nothing but the standard library.

## Risks requiring resolution, not acceptance

- **A stakeholder heading that always passes.** A section every spec has and none fills is a
  green nobody earned, in the document whose job is to prevent them. Resolution: the check
  fails on the template's own placeholder text and on an empty body, and a red fixture
  proves both before the heading ships.
- **An envelope schema derived from `cli.py`.** A schema written by reading the emitter
  cannot contradict the emitter. Resolution: the schema is written from what a consumer
  needs — a named contract, a closed field set — and the first run is red against today's
  output, which carries no `schema` field. If the first run is green, the schema is wrong
  and is rewritten, not accepted.
- **A surface field that is guessed.** The moment a default exists, every event acquires an
  attribution and none of them is evidence. Resolution: `undetermined` is a recorded value
  with its own test, and no code path supplies a fallback surface.
- **The mission sentence turning `CONSTITUTION.md` into policy.** Resolution: one sentence
  inside `## Mission`, no new heading, the doctrine ceiling unchanged, and assertion 4 stays
  the only reader.
- **Sharpening.** The nine unfalsifiable requirements above are the standing temptation of
  this range. Resolution: they are listed in this document, they are not tasks, and any
  future check claiming to close one arrives with its own red fixture first.

## Decisions

**D-016-01 — the corrected mission goes into `CONSTITUTION.md`'s existing Mission section,
not into a new file.**
**Rationale:** EP-071 and EP-097 forbid a second normative layer, and `ai-eng doctor`
assertion 4 already reads that file. A fact recorded where no command reads it is exactly
the shape the audit counted twenty times.

**D-016-02 — the JSON envelope gets its own schema in `policy/`, which references
`outcome-v1` rather than restating it, and the check validates captured CLI output.**
**Rationale:** measured, the envelope is missing four required fields and carries ten the
outcome schema forbids, while the `Result` beside it is pinned by SHA-256 in `outcome.py`. A
second copy of the seven outcomes would reproduce EP-300 — one list in four files, one bound
pair — and a self-built fixture would only prove the test agrees with itself.

**D-016-03 — every event that has a surface records it and its adapter; an undeterminable
surface is recorded as `undetermined` and never defaulted.**
**Rationale:** the guard contract's whole shape is that an unknown value fails closed
instead of choosing one. A default surface would make every event carry an attribution and
none of them evidence.

**D-016-04 — the export-result half of EP-084 is not re-planned.**
**Rationale:** it landed at `4e9fd0b4`, after the commit the audit measured. The audit's own
sixth correction is that the report still asks for EP-257, which was done in P0. Re-planning
landed work is that mistake with a different identifier.

**D-016-05 — the stakeholder output is one heading in the spec and ship templates, with a
check for presence and for unchanged placeholder text.**
**Rationale:** EP-095 asks for a short section and explicitly no new prose skill. A heading
with no check is a heading that always passes, which is the failure this range was supposed
to close.

**D-016-06 — the twelve requirements whose mechanism belongs to specs 011–015 are routed,
not re-specified.**
**Rationale:** two homes for one requirement is EP-300's defect moved from the code into the
record, and the second home drifts the first time either is edited.

**D-016-07 — requirements with no possible red are recorded as unfalsifiable and left.**
**Rationale:** specs 012, 013, 014 and 015 each name this failure mode. A vague line
sharpened into a check the repository already passes is a green manufactured by whoever
wrote the check.

**D-016-08 — the audit's count is corrected in this document.**
**Rationale:** `EP-062..EP-097` is thirty-six identifiers of which spec 011 owns one, and
five of the nine mission verbs are absent rather than four. A specification that opens by
repeating a number it can disprove teaches its reader to trust the number over the command.

## Accepted risks

None. Every risk above stays open until it is removed or accepted by an authorised human
with complete evidence and an expiry date.

## Production-ready

Nothing gets a URL until every box is ticked by observed evidence.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
