---
id: "045"
slug: critics-inside-spec
status: draft
date: "2026-08-27"
ref: ""
supersedes: ""
---

# Critics inside spec

## Who this is for, and what it is worth to them

The repository owner who approves every spec, and every future author this framework
puts through the cycle. Today one decision costs up to five files — spec, challenge,
council transcript, council page, approval dossier — and two critic passes that re-read
a 75K-line tree from cold context: 044's challenge ran 70 minutes and its council passed
36 minutes without writing a byte (owner-reported session timings, 2026-08-27). After
this spec one decision is one file the gate and the person both read, and the critics
are bounded instruments: at most ten questions, one pass, counts a script checks.

## Context and problem

What is true today, measured on this tree:

- Four sidecar files sit beside `spec.md` for the specs that went through the full
  critic cycle: `challenge.md` (3,445 lines across 14 specs), `council.md` (4,290 lines
  across 14), `council.html` (216 KB across 12) and `approval.md` (15 specs, 029
  onward). `challenge.md` has no reader at all — ADR 0023 says so in its own words.
  `council.md` has exactly two: `tests/council_counts.py` counts its bullets and
  `tests/test_contracts.py` refuses its verdict fields. Neither opens a finding.
  `approval.md` has no mechanical reader either: a live call into `madr.validate`
  returns `INCOMPLETE [MADR_UNREADABLE]` for every one of the fifteen (a file
  declaring the foreign schema `urn:ai-engineering:spec-approval:1` is read as not a
  MADR, `src/ai_engineering/madr.py:218-224`), and the tree-wide validation passes
  without reading any of them — `docs/adr/` is the only home it opens. The canonical
  approval at exact digests already lives in the `docs/adr/` records that verb does
  validate.
- `ai-challenge`'s procedure is an exhaustive sweep: execute every checkable sentence
  in the spec. On 044 it returned ten `WRONG` verdicts and seven `UNPROVEN`
  (`specs/044-ponytail-audit-residual-cuts/challenge.md:244-248`); the owner named two
  of the ten load-bearing — the incomplete deletion list and the wrong register census
  — against a spec the author had already verified once. Its 70 minutes are
  owner-reported and instrumented by nothing in this tree, which the `ran:` lines of
  D-045-05 exist to change.
- `ai-council` runs three sequential fork rounds: five lenses, then the anonymous
  cross-read, then a blind chairman — plus a `council.html` page written for a person.
  The measured mechanism is the first two rounds (report 003: independent readers raise
  14 issues a session against 9; the cross-read cuts false alarms from 22% to 5.3%;
  66.5% of correct answers flip wrong when another answer enters the reader's context).
  The third round duplicates what the author does when folding findings into the spec —
  044's council corrections went into the spec digest by hand either way — and the HTML
  page duplicates the transcript the person reads once.

The harm of leaving it: wall-clock paid to re-prove what the author already verified,
token cost of files whose only reader is a counter, and one decision spread over five
files a reviewer must open one by one to reconstruct.

## Options considered

1. **Critics inside the spec (chosen).** `ai-challenge` becomes a grill: at most ten
   questions, asked one at a time, each anchored to a sentence of the spec and answered
   by executing commands in the fork — the execution discipline stays, the exhaustive
   sweep does not. The author folds the Q&A into a new `## Grill` section of the spec.
   `ai-council` runs once: five forked lenses plus the cross-read in the same pass, the
   author writes the verdict, and the machine shape (three bullet headings plus the two
   counts) moves into a `## Council` section. `challenge.md`, `council.md`,
   `council.html` and `approval.md` die for new specs; the count readers retarget the
   sections. Gives: one file per decision; independence, the cross-read and the
   command-per-finding rule survive intact; the sweep is bounded by structure, not
   prose. Costs: the per-lens transcript disappears (the lenses were anonymous anyway —
   names never existed); `tests/council_counts.py` and the contracts readers migrate in
   the same block; skill-corpus arithmetic that pins the skills' text moves in the same
   commits as the skill edits.
2. **Keep the sidecar files, cut the ceremony around them.** Delete `council.html`
   only, cap the sweep by prose guidance, keep three rounds. Gives: zero reader
   migration; the artifacts stay where the corpus tests already point. Costs: four
   files per decision remain, three of them read by nobody or by one counter; the
   70-minute sweep is bounded by an instruction a reader can ignore rather than by a
   shape; the reviewer still opens five files to follow one decision.
3. **Parallelise the critics instead of shrinking them.** Fork every lens into its own
   worktree and run the three rounds concurrently. Gives: wall-clock relief on paper
   without touching artifacts or skills. Costs: report 019 marks critic-parallel
   wall-clock `[sin fuente]` — the 14-vs-9 measurement is human readers, not agents;
   the dominant cost is each fork re-reading the tree cold, which parallelism
   multiplies rather than removes (Anthropic measured an orchestrator-with-subagents
   run at roughly 15× the tokens of a single chat — "How we built our multi-agent
   research system", 2025-06); it adds orchestration the one-writer rule and rule 11
   never asked for; and the artifact surface — the cost paid in every later session —
   does not shrink at all.

Option 2 loses: it keeps the second and third home of the same decision, the exact
failure rule 4 names. Option 3 loses: it buys an unmeasured benefit with real machinery
and leaves every file in place.

## Decision

**D-045-01 — ai-challenge becomes the grill.** At most ten questions per round, one at
a time, each naming the sentence it attacks and carrying the command that decided it,
with the verdict written beside the output (`WRONG`, `UNPROVEN`, or holds). The fork
discipline is unchanged: read only the spec and the tree, never the plan or the chat.
The two-rounds-per-digest bound is unchanged; the cap bounds round one, and round two
exists for what the cap made round one miss. An empty `## Grill` is a grill that did
not run: the section's rule is one bullet per question plus, when the round genuinely
found nothing to attack, one `**A:**` line reading `nothing checkable failed` — the
reader refuses a `## Grill` with neither. The challenger never writes the spec; it
returns the Q&A to the author, who folds it into `## Grill` and corrects the attacked
sentences in place — a spec is revised, never appended-contradictory.

**D-045-02 — ai-council runs once.** Five forked lenses (cost, reversibility, the
undecidable path, what is taken on trust, the example nobody wrote) and the anonymous
cross-read happen inside one pass; the blind-chairman round folds into the author's
verdict paragraph, because the author is the one who must answer the findings anyway.
Independence rules, the command rule and the no-authority boundary are unchanged: it
may conclude, it may not approve. No `council.html`; the transcript shape survives as
the `## Council` section's machine-readable part. The rule that a lens must have run
moves from the old skill into the section: its header names the five lenses and marks
any that returned nothing — `lenses: cost, reversibility, undecidable, trust, example`
by name, never `3 of 5`, which the no-authority tally check would refuse as arithmetic
about members (`tests/test_contracts.py:2235`). A finding the cross-read refutes and
another lens upholds stays in `### Gaps no single lens named` and is *not* also listed
under the refuted heading — one heading owns one finding, or the two counts
double-count what the counter exists to keep honest.

**D-045-03 — the spec template carries the critics, and the sidecar files die.** The
template gains `## Grill` and `## Council` (the three bullet headings plus `### The two
counts`), placed after `## Challenged once` and before `## Assumptions and unresolved
risks`. For new specs, `challenge.md`, `council.md`, `council.html` and `approval.md`
are never created; the historical sidecar files stay exactly where they are — written
records are not rewritten. `tests/council_counts.py` becomes a **dual-glob,
dual-shape** reader: it reads `specs/*/council.md` (historical, totals heading `## The
two counts`) and, beside it, any `specs/*/spec.md` that carries a `## Council` section
(new, totals heading `### The two counts`), summing both into one receipt — executed:
the old shape yields `(8, 13)` and the new yields its own counts, while a single-glob
retarget makes all 45 specs raise `Unreadable` and turns the mixed tree red on day
one). A section that is *present but empty* is a refusal, not a `(0, 0)` green: each
of the three bullet headings carries at least one entry or one explicit `none` bullet,
because `counts()` is arithmetic agreement between bullets and totals and an empty
agreement is the indistinguishable byte state every "did the critic run" question
reduces to. It fails closed on the template's own TODO prompt under those headings —
and this fail-closed is the counter's, not doctor's `MARKER`, which only fires on a
`status: shipped` spec and so could never guard a draft
(`src/ai_engineering/doctor.py:1137`; all fourteen sidecar-bearing specs and 045
itself are `draft`). The approval gate is what refuses a draft whose `## Council`
still carries the prompt: a digest cannot be signed over an un-run council. Approval
content stays canonical in `docs/adr/` MADRs, which are the records `madr.validate`
already reads; what `approval.md` uniquely carried — the summary of what the critics
changed — is what `## Grill` and `## Council` now record.

**D-045-05 — every critic run records its own minutes.** The header line of `## Grill`
and of `## Council` carries `ran: <date> — <n> min`, written by the author when the
fold lands. The 70 and 36 minutes that motivated this spec are owner-reported and
instrumented by nothing; a design that cuts a cost it cannot measure is a design whose
own claim nobody can check, and `tests/council_counts.py` — which already recomputes
what a council wrote rather than believing it — reads the line and refuses a section
without it.

**D-045-04 — three options, always, before the decision.** `ai-spec` demands exactly
three real options under `## Options considered`, positioned before `## Decision`
because a decision with no alternatives in front of it is not auditable. The critics
re-evaluate those options as part of their pass, and their effect lands by revising the
options and decision in place — with `## Grill` and `## Council` recording what moved
and why. A decision earns its own MADR, via `ai-eng decide`, exactly when it constrains
specs that do not exist yet (a boundary or a global convention); everything else stays
in this file, which is its record.

## Challenged once

Strongest realistic case: "folding the critics' output into the file under review
destroys the independence that made them worth paying for — report 003 measured 66.5%
of correct answers flipping wrong when another answer enters the reader's context."
Answer: the independence lives in the fork, not in the file boundary. Both skills keep
`context: fork`; the contamination measurement describes a reader absorbing answers,
while the grill runs the other way — questions leave the fork, and the author, who is
allowed to read everything, folds the answers in. 044 already ran the fold: its
council's corrections went into the spec and the approved digest carries them. The case
fails; proceed.

Second case: "a counts reader pointed at `spec.md` false-greens on the unfilled
template." Answer: fail closed. The template's TODO prompt under `## Council` is
exactly the anchored-marker case doctor's `MARKER` check already solves
(`src/ai_engineering/doctor.py:1147`): bullets absent, prompt present, reader refuses
with the spec named. Absence of the section reads as "has not run", the same
non-verdict `council_counts.py` gives an absent `council.md` today.

## Grill

`ran: 2026-08-27 — 5 questions, owner-side, uninstrumented before D-045-05 existed`

### Q1 — ¿Hace falta approval.md, o va dentro de spec y plan?
**A:** No hace falta como fichero: ningún código lo lee — `madr.validate` lo rechaza
como MADR y el aprobado canónico ya vive en `docs/adr/`. Lo que era útil de
approval.md (qué cambiaron los críticos) pasa a `## Grill`/`## Council`; el alcance de
lo aprobado queda en el MADR. Cambió D-045-03.

### Q2 — ¿Brainstorm/challenge/council dentro de la spec, bien representado como feature?
**A:** Sí — es exactamente este diseño: What (`## Decision` + `## Options considered`),
Why (`## Context and problem`), How (`## Examples somebody can check`), y el registro
del criticismo en las dos secciones nuevas. Cambió la estructura del template (D-045-03).

### Q3 — ¿"Options considered" siempre tres?
**A:** Sí: tres propuestas reales, ni dos ni cinco. Cambió D-045-04.

### Q4 — ¿"Options considered" va al final, después de challenge y council?
**A:** No: va antes de `## Decision`, porque sin alternativas delante la decisión no es
auditable. El instinto apunta a algo real — los críticos re-evalúan las opciones — y se
resuelve revisándolas in situ, nunca añadiendo una contradicción debajo; `## Grill` y
`## Council` registran qué movió. Cambió D-045-04; el orden del template queda intacto.


### Q5 — ¿Diagramas dentro de la spec?
**A:** No en el template: los headings ya son el esquema que los scripts leen, y un
diagrama duplicaría el orden lineal que el template impone. Un diagrama entra en una
spec concreta sólo si representa algo no lineal (p. ej. el DAG de verificación de la
spec 031). No cambió nada.

## Council

`ran: pending — the pass runs once before approval; this line appears with its minutes`
TODO: runs once on this draft before approval — five forked lenses (cost, reversibility,
the undecidable path, what is taken on trust, the example nobody wrote) and the
cross-read inside the same pass; the author writes the verdict and one first step. Every
finding and every refutation carries a command. It may conclude; it may not approve.
The shape below is what the counter reads — top-level bullets only:

### Gaps no single lens named

<!-- bullets -->

### Findings cut for carrying no command

<!-- bullets -->

### Findings the cross-read refuted, with the command that refuted them

<!-- bullets -->

### The two counts

- Gaps that appeared only after the cross-read: **N**
- Findings deleted, for carrying no command or for being refuted: **N**

Verdict: TODO — the author writes it when the pass runs.

## Assumptions and unresolved risks

Assumptions:
- Fork-based critics remain the harness pattern; nothing here changes what the harness
  provides, only what the skills do with it and what lands on disk.
- The owner's directive of 2026-08-27 is the intake contract for this spec (goal,
  constraints and acceptance named in session), and this session's grill satisfies the
  grill-once expectation for the draft.
- Historical sidecar files stay untouched; skill-corpus arithmetic that pins the
  skills' text moves in the same commits as the skill edits, which the corpus tests
  already enforce.
- D-045-01, 02 and 03 are **one coupled rollback block, not three independent
  reverts** (LensReversibility L-4): `tests/test_skill_bounds.py:34` byte-pins
  `"hand the page to the person"` and `"loopgate"` in both critic skills — a module
  `ai-challenge`/`ai-council` name as the orchestrator's instrument even though the
  `loopgate` module itself died in 044's family (a) — and `tests/test_quality_gate.py`'s
  GATE row plus `docs/tools.md:52` quote the `just council` recipe. Backing any one of
  the three decisions out re-edits all of them; the plan must land them in one commit
  family with a single `git revert`, not as separable tasks.

Unresolved risks:
- The ten-question cap may under-cover a spec with more than ten checkable sentences;
  the two-round digest bound is the reopen path — round two exists for what the cap
  made round one miss, and a digest revision reopens the count.
- The transcript's audit value is lost for future specs; the counts remain
  script-checked, the lenses were never named, and a session that needs the full lens
  output keeps it in the session record, not in `specs/`.
- Inserting two `##` headings moves every later section's **position-based number**
  (`src/ai_engineering/spec.py:813` `section()`, sold by D-031-03 as "resolve a part by
  number"). Executed: 044's `## Assumptions` is section 6, 045's is section 8. No
  `section()` call site exists in `src/` or `tests/` today, so the cost is nil by
  absence-of-callers, not by design (LensReversibility L-5). If a stored numeric
  reference is ever added, old and new corpora disagree permanently; the mitigation,
  if that day comes, is name-based resolution, and this spec records the shift so the
  next author sees the two regimes rather than rediscovering it.

## Examples somebody can check

**The grill path.** Given this spec's grill ran in session, When
`grep -c '^### Q' specs/045-critics-inside-spec/spec.md` runs, Then it prints `5`; and
`grep -c '\*\*A:\*\*' specs/045-critics-inside-spec/spec.md` prints `6` — five answers
plus the template line the undecidable example quotes. Every question carries its
answer and what it changed.

**The dead-file path.** Given the plan landed and a new spec is created with
`ai-eng spec new probe-045`, When `ls specs/*probe-045` runs, Then it prints
`spec.md` alone at spec stage — no sidecar is created; and
`grep -rn "council.html" .agents/skills/ | wc -l` prints `0`.

**The counts path.** Given the new reader, When `just council` runs after this spec's
own council fills `## Council`, Then it prints the two counts read from the section and
exits `0`; and given a spec still carrying the template's TODO prompt under
`## Council`, When the same command runs, Then it exits non-zero naming that spec.

**The history-stays-guarded path.** Given the dual-shape reader, When `just council`
runs against `specs/044-ponytail-audit-residual-cuts/council.md`, Then it still prints
`8` and `13` (executed: the old h2 shape returns `(8, 13)`), and the new h3 template
shape returns a count rather than the `Unreadable` a single-mode reader raises — so
the 4,290 historical lines keep their guard after the retarget.

**The undecidable path.** Given a grill question no tree command can decide, When the
author folds it, Then the answer line reads `**A:** UNPROVEN — <why>` and the sentence
it attacked is revised or its risk recorded under `## Assumptions and unresolved
risks`; silence is the only wrong answer.

**The approval path.** Given this spec approved, When
`ls specs/045-critics-inside-spec` runs, Then it prints `plan.md` and `spec.md` and
nothing else — the approval record is the `docs/adr/` MADR `madr.validate` reads.

## Decisions

<!-- One `**D-NNN-NN — <the decision>**` per line, each with a `**Rationale:**` under it.
     Prefix a line with `- [X]` to claim the decision earns promotion: it constrains
     specs that do not exist yet, and `ai-eng decide` promotes only marked lines.
     `ai-eng decide` does not write here: it writes a record under docs/adr/. -->

- [X] **D-045-03 — The spec template carries `## Grill` and `## Council`; the four
      sidecar files die for new specs; counters retarget the in-spec sections and fail
      closed on the template prompt.**
      **Rationale:** one decision, one file; the gate reads sections the same way it
      read files, and written history is never rewritten.
- [X] **D-045-04 — Exactly three real options, always, before `## Decision`; critics
      revise them in place and a decision earns a MADR only when it constrains future
      specs.**
      **Rationale:** three keeps the comparison honest without theatre; the position
      before the decision is what makes the recommendation auditable.
- **D-045-01 — ai-challenge becomes the grill: ≤10 command-backed questions, one at a
  time, folded into `## Grill` by the author.** **Rationale:** the sweep's value was
  the execution, not the exhaustiveness; the cap bounds cold-context cost by structure.
- **D-045-02 — ai-council runs once: five lenses + cross-read in a single pass, author
  writes the verdict, no HTML page.** **Rationale:** the measured mechanism is the
  lens/cross-read pair; the third round and the page duplicated the author's fold.
- **D-045-05 — every critic run records its own minutes in the section header.**
  **Rationale:** a cost the design claims to cut must be measurable on the artifact
  the design produces; owner-reported timings alone are the fiction rule 11 refuses.

## Accepted risks

<!-- none; unresolved risks are recorded above and none is accepted by this record -->

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
