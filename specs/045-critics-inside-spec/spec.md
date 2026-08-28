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
council transcript, council page, approval dossier — and two critic passes whose cost
is not shared the way the slogan says: the challenge re-reads the whole 129,740-line
tracked tree from cold context (73,054 of those lines are `src`+`tests` — the number
earlier drafts quoted for "the tree" was that subset), and the council pays five forked
lenses over the spec file, twice. 044's challenge ran 70 minutes and its council passed
36 minutes without writing a byte (owner-reported session timings, 2026-08-27,
instrumented by nothing in this tree). After this spec one decision is one file the
gate and the person both read, and the critics are bounded instruments: at most ten
questions per round, one pass, and a gate that counts both.

## Context and problem

What is true today, measured on this tree:

- Four sidecar files sit beside `spec.md` for the specs that went through the full
  critic cycle: `challenge.md` (3,445 lines across 14 specs), `council.md` (4,290
  lines across 14), `council.html` (203,492 raw bytes across 12) and `approval.md`
  (15 files, specs 029–042 plus 044; 043 has none). The *semantic* readers split as
  ADR 0023 says: nothing opens a `challenge.md` finding, and `council.md` is read by
  `tests/council_counts.py` (bullet-vs-total arithmetic) and `tests/test_contracts.py`
  (the no-authority refusal) — neither opens a finding. Mechanically there is a third
  surface: `sm`, consumed by `just map` inside `just check`, scans all four kinds into
  the reference graph, and `policy/skill-map-accepted.toml` carries 95 entries naming
  them (81 with a sidecar as source node) — the death of the convention goes
  inert-pairs, not red, which is priced below rather than wished away.
- `approval.md` has no validating reader: a live call to `madr.validate` returns
  `INCOMPLETE [MADR_UNREADABLE]` for each of the fifteen (executed), and the tree-wide
  validation PASSes with all fifteen parsed-but-skipped — its candidate set is
  `docs/adr/*` plus `specs/*/spec.md` (`src/ai_engineering/madr.py:417-419,474-499`),
  never the dossiers. And the sentence an earlier draft carried — that the canonical
  approval "already lives in `docs/adr/`" — is false since ADR 0026 (spec 027), the
  last digest-approval record: `grep -rn -E 'specification[s]? 0(29|3[0-9]|4[0-4])'
  docs/adr/` prints nothing. For specs 029–044 the dossier is the *only* place the
  approval lives. Restoring the approval to `docs/adr/` is therefore a cost this
  design takes on, not a saving, and the fifteen dossiers stay where they are.
- `ai-challenge`'s procedure is an exhaustive sweep: execute every checkable sentence
  in the spec. On 044 it returned ten `WRONG` verdicts and seven `UNPROVEN`
  (`specs/044-ponytail-audit-residual-cuts/challenge.md:244-248`) over 28 fenced
  command blocks; the owner named two of the ten load-bearing — the incomplete
  deletion list and the wrong register census — against a spec the author had already
  verified once. The minutes tracked commands executed, not sentences listed: a cap
  on questions must be honest that a multi-command answer still costs.
- `ai-council` runs three sequential fork rounds: five lenses, then the anonymous
  cross-read, then a blind chairman — plus a `council.html` page written for a
  person. The measured mechanism is the first two rounds (report 003: independent
  readers raise 14 issues a session against 9; the cross-read cuts false alarms from
  22% to 5.3%; 66.5% of correct answers flip wrong when another answer enters the
  reader's context). The third round duplicates what the author does when folding
  findings into the spec — 044's council corrections went into the spec digest by
  hand either way — and the HTML page duplicates the transcript the person reads once.

The harm of leaving it: wall-clock paid to re-prove what the author already verified,
token cost of files whose only semantic reader is a counter, and one decision spread
over five files a reviewer must open one by one to reconstruct.

## Options considered

1. **Critics inside the spec (chosen).** `ai-challenge` becomes a grill: at most ten
   questions per round, asked one at a time, each anchored to a sentence of the spec
   and answered by executing commands in the fork — the execution discipline stays,
   the exhaustive sweep does not. The author folds the Q&A into a new `## Grill`
   section of the spec. `ai-council` runs once: five forked lenses plus the cross-read
   in the same pass, the author writes the verdict, and the machine shape (three
   bullet headings plus the two counts) moves into a `## Council` section.
   `challenge.md`, `council.md`, `council.html` and `approval.md` die for new specs;
   the `just council` step becomes a critic step reading the sections. Gives: one file
   per decision; independence, the cross-read and the command-per-finding rule
   survive; a full-cycle decision pays ~550 sidecar lines plus ~17 KB of HTML plus a
   ~90-line dossier today and replaces them with two ≤40-line sections (per-spec
   averages of the 14-spec corpus). Costs, priced on the tree, not on hope:
   `tests/council_counts.py`, two `test_contracts.py` readers, 114 sidecar references
   across 11 live files, 95 accepted-pair rows that go inert, 3 verbatim pins of "at
   least two real options" in the contracts test plus 3 in `ai-spec/SKILL.md` plus 2
   in the shipped template, and the `docs/tools.md` rows the comparator test pins to
   the justfile — all in one commit family.
2. **Keep the sidecar files, cut the ceremony around them.** Delete `council.html`
   only, cap the sweep by prose guidance, keep three rounds. Gives: zero reader
   migration; the artifacts stay where the corpus tests already point. Costs: four
   files per decision remain, three of them read by nobody or by one counter; the
   70-minute sweep is bounded by an instruction a reader can ignore rather than by a
   shape; the reviewer still opens five files to follow one decision; and the
   approval record never returns to the one home a command validates.
3. **Parallelise the critics instead of shrinking them.** Fork every lens into its own
   worktree and run the three rounds concurrently. Gives: wall-clock relief on paper
   without touching artifacts or skills. Costs: report 019 marks critic-parallel
   wall-clock `[sin fuente]` — the 14-vs-9 measurement is human readers, not agents;
   the challenge's cost is the cold tree re-read (129,740 tracked lines), which
   parallel forks multiply rather than remove, and Anthropic measured an
   orchestrator-with-subagents run at roughly 15× the tokens of a single chat
   ("How we built our multi-agent research system", 2025-06); it adds orchestration
   the one-writer rule and rule 11 never asked for; and the artifact surface — the
   cost paid in every later session — does not shrink at all.

Option 2 loses: it keeps the second and third home of the same decision, the exact
failure rule 4 names, and leaves the approval in a file no command reads. Option 3
loses: it buys an unmeasured benefit with real machinery and leaves every file in
place.

## Decision

**D-045-01 — ai-challenge becomes the grill.** At most ten questions per round, one
at a time, each a `### Q` entry naming the sentence it attacks, carrying the command
that decided it and its verdict beside the output (`WRONG`, `UNPROVEN`, or holds).
The fork discipline is unchanged: read only the specification and the tree, never the
plan or the chat. The two-rounds-per-digest bound is unchanged and made visible: a
round continues the `### Q` numbering and announces itself in the section's `ran:`
line; because every fold moves the digest, the bound is enforced by the round tag and
its ceiling ("hand the page to the person"), not by digest arithmetic. An empty
`## Grill` is a grill that did not run: the section holds at least one `### Q` entry
with its `**A:**` line, or the literal line `nothing checkable failed` — the critic
step (D-045-03) refuses a section with neither. The challenger never writes the spec;
it returns the Q&A to the author, who folds it into `## Grill` and corrects the
attacked sentences in place — a spec is revised, never appended-contradictory.

**D-045-02 — ai-council runs once.** Five forked lenses (cost, reversibility, the
undecidable path, what is taken on trust, the example nobody wrote) and the anonymous
cross-read happen inside one pass; the blind-chairman round folds into the author's
verdict paragraph, because the author is the one who must answer the findings anyway.
Independence rules, the command rule and the no-authority boundary are unchanged: it
may conclude, it may not approve. No `council.html`; the transcript shape survives as
the `## Council` section's machine-readable part. The rule that every lens ran moves
from the old skill into the section: its header names the five lenses by name —
`lenses: cost, reversibility, undecidable, trust, example` — never a `3 of 5` tally,
which the no-authority rule refuses as arithmetic about members
(`tests/test_contracts.py:2235`). A finding the cross-read refutes and another lens
upholds stays in `### Gaps no single lens named` and is *not* also listed under the
refuted heading — one heading owns one finding, or the two counts double-count what
the counter exists to keep honest.

**D-045-03 — the spec template carries the critics; the sidecar convention dies
forward, and the counters become an explicit critic step.** The template gains
`## Grill` and `## Council` (the three bullet headings plus `### The two counts`),
placed after `## Challenged once` and before `## Assumptions and unresolved risks`.
For new specs, `challenge.md`, `council.md`, `council.html` and `approval.md` are
never created; the historical files stay exactly where they are — written records are
not rewritten, which also means the fifteen dossiers are not deleted, only unlearned.
`tests/council_counts.py` becomes the critic reader and keeps the recipe name
`council`, so `just check` stays sixteen steps:

- **dual glob**: `specs/*/council.md` (historical, totals heading `## The two
  counts`) plus every `specs/*/spec.md` that carries a `## Council` section (new,
  `### The two counts`), summed into one receipt. Executed: the old shape yields
  `(8, 13)`; a single-glob switch to `spec.md` makes all 45 specs raise `Unreadable`;
  the two heading levels cannot share one mode, so the reader switches on the file it
  is in.
- **emptiness is a refusal, not a `(0, 0)`**: each of the three bullet headings
  carries at least one dash-bullet or a literal `none` line, and the totals count
  only dash-bullets. Executed: a present-but-empty section with `**0**/**0**` agrees
  with itself under `counts()` — an unfilled draft and a clean pass are the same
  bytes; the `none` line is what makes "ran and found nothing" distinguishable from
  "did not run".
- **prompt refusal bites declared rounds, and only them**: enforcement is
  conditional on a declared `ran: round` line — a section still holding the
  template's prompt and no `ran:` line reads as "has not run", the same green
  absence `council_counts.py` gives a missing `council.md` today, so drafting a spec
  never reddens the gate. A section that *declares* a round and still carries prompt
  prose is the false green: executed, `counts()` passes it today (zeros filled,
  prompt kept, exit 0), because the only today-refusal is `**N**` failing the digit
  regex. The step adds the explicit check — any prompt line or HTML comment under a
  declared critic heading refuses the spec — with a planted fixture, the way the
  four planted refusals prove the totals rule.
- **no-authority, scoped**: `test_a_council_reviews_and_never_approves` keeps its
  file-wide rule over historical `council.md` files and gains a section-scoped pass
  over new `## Council` bodies. A whole-file port of the regexes refuses ordinary
  spec prose — executed over all 45 files it catches `specs/036…/spec.md`'s register
  row and this draft's own challenge answer — and the constitution forbids rewriting
  036. Scoping decides it without weakening the rule or touching history.

Approval goes back to `docs/adr/`: the digest-approval ADR series, which stopped at
0026, resumes for specs approved from here, and `madr.validate` — which only ever
opens `docs/adr/*` and `specs/*/spec.md` — finally reads the approval record it was
always supposed to gate. What `approval.md` uniquely carried, the summary of what the
critics changed, is what `## Grill` and `## Council` now record.

**D-045-04 — three options, always, before the decision.** `ai-spec` is amended — it
says "at least two" in three places today, the contracts test pins that sentence
verbatim three more, and the shipped template carries it twice; all of it moves in
the same family: exactly three real options under `## Options considered`, positioned
before `## Decision`, because a decision with no alternatives in front of it is not
auditable. The rule binds new specs; the existing corpus already splits 36/9 (counted
today), and the nine join the tree's established frozen-list convention for written
history rather than being rewritten. The critics re-evaluate the options as part of
their pass, and their effect lands by revising the options and decision in place —
`## Grill` and `## Council` record what moved and why. A decision earns its own MADR,
via `ai-eng decide`, exactly when it constrains specs that do not exist yet (a
boundary or a global convention); everything else stays in this file, which is its
record.

**D-045-05 — every critic round records itself.** Each critic section opens with one
line per round: ``ran: round <n>, <ISO date> — <n> min``, strict grammar, and the
critic step refuses a section whose line is missing or malformed. Executed against
this draft before the rule existed: both of its earlier `ran:` lines failed the
declared form, which is why the rule ships as a regex with a planted fixture and not
as a sentence. The minutes are **self-reported**: nothing in this tree starts a clock
a critic fork writes to (executed: no duration parse in `tests/council_counts.py`),
so the line makes each round's cost visible on the artifact that carries the claim —
visible, not audited. Report 019 marked this same gap `[sin fuente]`; an instrument
that times forks is the day the number needs to be true.

## Challenged once

Strongest realistic case: "folding the critics' output into the file under review
destroys the independence that made them worth paying for — report 003 measured 66.5%
of correct answers flipping wrong when another answer enters the reader's context."
Answer: the independence lives in the fork, not in the file boundary. Both skills keep
`context: fork`; the contamination measurement describes a reader absorbing answers,
while the grill runs the other way — questions leave the fork, and the author, who is
allowed to read everything, folds the answers in. 044 already ran the fold: its
council's corrections went into the spec and the approved digest carries them. The
residual truth the cost lens named stays as a risk: future lenses will read earlier
rounds inside the document under review; the reopened measurement is recorded below.

Second case: "a counts reader pointed at `spec.md` false-greens on the unfilled
template." Answer: it would, and the grill executed exactly that — prompt prose kept,
zeros filled, exit 0. That is why the prompt refusal is a *new* rule with a planted
fixture (D-045-03) rather than a property inherited from `counts()`, and why the
emptiness state is reserved by an explicit `none` line. A missing `## Council` still
reads as "has not run", the same non-verdict `council_counts.py` gives an absent
`council.md` today; doctor's `MARKER` cannot guard a draft because it fires only on
`status: shipped` specs (`src/ai_engineering/doctor.py:1137`), and every sidecar
spec, this one included, is draft.

## Grill

`ran: round 1, 2026-08-27 — 0 min` — owner intake, no fork ran: the five questions
came from the owner's own message; the minutes line is honest about it.

### Q1 — ¿Hace falta approval.md, o va dentro de spec y plan?
**A:** Como *convención nueva*, no: su contenido se parte — el resumen de qué movieron
los críticos va a `## Grill`/`## Council`, y el registro de autoridad vuelve a
`docs/adr/` (ver Q8: la serie lleva vacía desde la ADR 0026, así que hoy el dossier
es load-bearing y devolverlo es un coste de este diseño, no un ahorro). Cambió
D-045-03.

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

`ran: round 2, 2026-08-28 — 67 min` — one forked challenger, specification and tree
only, cold context. Seven findings `WRONG`, three hold; each answer names what it
moved in this file.

### Q6 — ¿Qué mecanismo rechaza hoy el prompt de plantilla bajo `## Council`?
**A:** Ninguno. Ejecutado: `tests/council_counts.py` no menciona TODO ni MARKER, y una
`## Council` con el prompt intacto y los totales rellenados a `**0**` devuelve
`(0, 0)` con exit 0; el `MARKER` de doctor solo corre en specs `shipped` y todas las
del corpus son `draft`. La cadena fail-closed que D-045-03 afirmaba no existía.
Cambió D-045-03: el rechazo del prompt es regla nueva con fixture, no heredada.

### Q7 — ¿Es exacto el comportamiento de `madr.validate` citado?
**A:** El resultado, sí — los quince dossiers devuelven `INCOMPLETE [MADR_UNREADABLE]`
al validarlos en solitario (re-ejecutado). La explicación estaba invertida: el árbol
completo PASSa parseando y *saltándose* los quince; su set de candidatos es
`docs/adr/*` más `specs/*/spec.md`, nunca los sidecars. Corregido en Context.

### Q8 — ¿Vive ya el aprobado canónico en `docs/adr/`?
**A:** No. El último registro a digests es la ADR 0026 (spec 027); para 029–044 no hay
ninguno. El dossier es, hoy, la única prueba de esos quince aprobados. Matarlo sin
devolver la serie a `docs/adr/` borraría el registro; por eso D-045-03 lo convierte en
coste asumido (la serie retoma) en vez de ahorro reclamado.

### Q9 — ¿"exactly three options" describe el estado actual?
**A:** No, es un cambio redactado en presente. `at least two` vive en tres frases de
`ai-spec/SKILL.md`, tres literales de `test_contracts.py` y dos del template
embarcado. D-045-04 ahora dice "`ai-spec` is amended" y el coste entra en la opción 1.

### Q10 — ¿"the tree" son 75K líneas?
**A:** No: 129.740 tracked; 73.054 son `src`+`tests`, el subconjunto que la cifra
anterior medía. Corregido en el encabezado.

### Q11 — ¿Dos lectores, o tres?
**A:** Dos semánticos, tres mecánicos: `sm` (consumido por `just map` dentro del gate)
escanea las cuatro clases y `policy/skill-map-accepted.toml` guarda 95 filas que las
nombran. Su muerte es inerte, no roja. Añadido a Context y a los costes de la opción 1.

### Q12 — ¿Cumple esta spec su propia línea `ran:`?
**A:** No la cumplía: una sin minutos, otra en `pending`. D-045-05 exige ahora
gramática estricta con fixture, y este fichero demuestra las dos primeras líneas
correctas; el diseño admite que el número es auto-reportado — visible, no auditado.

### Q13 — ¿Baten los conteos del corpus tras la revisión?
**A:** Sí: 14/3.445 challenge, 14/4.290 council, 12/203.492 bytes council.html, 15
approval (029–042 y 044; 043 sin uno). Las cuatro cifras de Context se re-derivan.

### Q14 — ¿Siguen valiendo los ejemplos que contaban líneas de este fichero?
**A:** No tras el pliegue: la ronda 2 y el council cambiaron todos los conteos que un
ejemplo citaba, otra vez. Los ejemplos se reescribieron para contar sobre el template
y sobre fixtures plantados — artefactos que la gate puede exigir — en lugar de sobre
este borrador.

### Q15 — ¿Es cierto que las dos formas del contador no comparten modo?
**A:** Sí, ejecutado: `counts()` sobre `specs/044…/council.md` devuelve `(8, 13)`;
sobre la forma nueva h3 levanta `Unreadable`; un glob único a `spec.md` levanta error
en las 45. De ahí la cláusula dual de D-045-03.

## Council

`ran: round 1, 2026-08-28 — 81 min` — `lenses: cost, reversibility, undecidable, trust, example`
— five forked reads, each on this specification and the tree alone, then the anonymous
cross-read. It concludes; it grants nothing.

### Gaps no single lens named

- A **draft that is its own first false green** — found only when the cross-read put
  three lenses' findings side by side: the timing gap (trust), the absent-refusal gap
  (example) and the `ran:` violation (cost) are one defect seen thrice, and every
  refusal-shaped rule this spec adds must ship with its own failing fixture in the
  same commit, or the next author inherits the same self-violation. Before this fold
  `grep -c 'ran: round' specs/045-critics-inside-spec/spec.md` printed `0`.
- **The approval series died at ADR 0026** — trust read the validator's skip and cost
  read the reader list; neither noticed the home had been empty for fifteen specs.
  `grep -rn -E 'specification[s]? 0(29|3[0-9]|4[0-4])' docs/adr/` prints nothing, so
  D-045-03's approval clause is a restoration, not a duplication, and no single lens
  framed it that way.
- **No-authority over whole spec files is a false-positive machine** — found
  independently by cost and example, who each ported `tests/test_contracts.py`'s
  regexes over all 45 specs: two refuse today (036's register row; this draft's own
  challenge answer), and 036 is written history nobody may rewrite. The scoped
  section-body pass — which no single lens proposed — is what decides it.

### Findings cut for carrying no command

- whether a ten-question grill is faster than the 70-minute sweep: nothing in this
  tree times a fork; the instrument that could does not exist yet.
- whether the 15× token figure holds here: external, unverifiable from this tree.
- whether the fold contaminates the lens pass through the 66.5% channel: structural
  reading, unmeasurable without an experiment nobody has run.
- the wrong corpus counts as their own finding: accuracy, already folded into the
  evidence corrections.
- whether the independence thesis survives the fold: a benefit claim, not a cost.
- whether session records survive to be read: outside the tree by definition.
- whether the ten-question cap under-covers: the spec names its own reopen path.
- whether a mixed receipt breaks `RAN council=` readers: the theatre test cannot
  parse today's shape either; no observable outcome changes.
- whether round two reuses the cap: no artifact exists for the question to bite on.

### Findings the cross-read refuted, with the command that refuted them

- "`spec.md` grows +232% per decision (17,329 → 57,538 bytes)" — the projection pasted
  044's exhaustive transcript into the file, which is the exact behaviour the
  ten-question cap exists to prevent; `wc -c specs/044-ponytail-audit-residual-cuts/
  spec.md specs/044-ponytail-audit-residual-cuts/challenge.md` shows where the bytes
  came from. The reader-side half survives as a risk below.
- "the retarget silently un-guards the historical councils" — refuted by the dual-glob
  clause: executed, the fourteen `council.md` files still count today
  (`RAN council=59/66`) and a glob that reads both shapes keeps them; what fails is
  only a single-glob switch, which D-045-03 forbids.
- "the h3 refusal is an artifact of the not-yet-retargeted counter" — half true, and
  the probe shows the split: `counts()` raises on the heading match (a glob problem)
  and on totals-vs-bullets (an emptiness problem); the two are separate rules in
  D-045-03 precisely because the refutation found them conflated.

### The two counts

- Gaps that appeared only after the cross-read: **3**
- Findings deleted, for carrying no command or for being refuted: **12**

Verdict: the mechanism is sound and the draft was not. Every load-bearing claim the
first version made about readers, approvals and fail-closed chains was answered by a
command, and four answers said the opposite of the sentence. Recommendation: ship the
rules only where a fixture refuses them — empty grill, `ran:` grammar, prompt, option
count, scoped no-authority — and keep this section as the first specimen of the shape.
One first step: write the five refusal fixtures *before* the template ships the
headings, so the first spec the new tool makes cannot pass a gate its own printed
rules do not enforce.

## Assumptions and unresolved risks

Assumptions:
- Fork-based critics remain the harness pattern; nothing here changes what the harness
  provides, only what the skills do with it and what lands on disk.
- The owner's directive of 2026-08-27 is the intake contract for this spec (goal,
  constraints and acceptance named in session), and the session's grill round one
  satisfies the grill-once expectation for the draft.
- D-045-01, 02, 03 and 05 form **one coupled rollback block**: the two critic skills'
  pinned strings (`tests/test_skill_bounds.py` — `"two rounds"`, `"digest"`, `"hand
  the page to the person"`, `"loopgate"`, which names an instrument whose module died
  in 044 and must be named by the new text or the bounds test moves in the same
  commit), `docs/tools.md`, and the skill-map accepted pairs. The plan reverts the
  block task by task in reverse order (per-task `git revert`); what none of the
  reverts yields is independence — each revert re-edits the others' pins. D-045-04
  shares the template commit with D-045-03's headings, so its "independently
  reversible" first reading was wrong: it was reverted *alone in prose* (pins, skill
  sentences), never *alone in a commit*. Found by the block review.

Unresolved risks:
- The ten-question cap may under-cover a spec with more checkable sentences than
  questions; minutes scale with commands-per-answer, and the cap bounds questions, so
  the `ran:` line is visibility, not a ceiling on the real cost. The two-round digest
  bound is the reopen path: a revision reopens the count.
- Future lens passes read earlier critic rounds inside the document under review —
  the same channel report 003 measured at 66.5%. Structural; unmeasured. Reopen the
  file boundary if a future council's findings anchor on the spec's own Grill text
  rather than its claims.
- The transcript's per-fork audit value is gone for new specs; the counts stay
  script-checked, the lenses were never named, and a session that needs the raw lens
  text keeps it in the session record, not in `specs/`.
- Inserting two `##` headings moves every later section's position-based number
  (`src/ai_engineering/spec.py` `section()`, the scheme spec 031 promotes). Executed:
  044's assumptions are section 6, this file's are section 8. No `section()` caller
  exists in `src/` or `tests/` today — cost nil by absence of callers, not by design.
  If a numeric reference is ever stored, old and new corpora disagree permanently;
  the mitigation is name-based resolution, and this section is the record.
- Self-reported minutes verify nothing (D-045-05); the day the number must be true,
  the instrument that times forks is its own change.

## Examples somebody can check

**The empty-grill path.** Given the built critic step, and a spec whose `## Grill`
holds neither a `### Q` with its `**A:**` nor the line `nothing checkable failed`,
When `just council` runs, Then it exits non-zero naming that spec — the planted
fixture in `tests/test_contracts.py` is the proof. (The first draft of this example
claimed no code read `### Q` at all; the reader shipped in the same block, so the
baseline moved — corrected at the review fold, which moved the spec's digest with
it. `grep -rn '### Q' tests | wc -l` prints non-zero today by design.)

**The ran-line path.** Given a `## Council` whose header reads ``ran: pending — …``,
When `just council` runs, Then it exits non-zero naming that spec; and given the
strict form on this file's three headers, it counts them — `grep -cE 'ran: round
[0-9]+, [0-9]{4}-[0-9]{2}-[0-9]{2} — [0-9]+ min'
specs/045-critics-inside-spec/spec.md` prints `3`.

**The prompt path.** Given the built rule, When `just council` runs over a spec whose
`## Council` carries a `ran: round` declaration, prompt prose, and zeros filled, Then
it exits non-zero naming that spec — the state that returns `(0, 0)` and exit 0 today
(executed in grill round two); a draft with prompt and no `ran:` line reads "has not
run" and stays green.

**The options path.** Given a fresh scaffold from `ai-eng spec new probe-045`, When
`sed -n '/^## Options considered/,/^## Decision/p' specs/*probe-045/spec.md | grep
-cE '^[0-9]+\. '` runs, Then it prints `3`.

**The dead-file path.** Given the plan landed and a new spec is created with
`ai-eng spec new probe-045`, When `ls specs/*probe-045` runs, Then it prints
`spec.md` alone at spec stage — no sidecar is created; and
`grep -rn "council.html" .agents/skills/ | wc -l` prints `0`.

**The counts path.** Given the dual-glob reader, When `just council` runs, Then it
still counts the fourteen historical files — `specs/044-ponytail-audit-residual-cuts/
council.md` yields `(8, 13)` — and adds the `## Council` sections of newer specs, one
`RAN council=` line over both regimes.

**The no-authority path.** Given the scoped pass, When
`uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py::test_a_council_reviews_and_never_approves`
runs over this tree, Then it exits `0` — 036's register row and this draft's prose
are outside the section scope — and a `## Council` body writing that the specification
is approved still refuses.

**The undecidable path.** Given a grill question no tree command can decide, When the
author folds it, Then the answer line reads `**A:** UNPROVEN — <why>` and the sentence
it attacked is revised or its risk recorded under `## Assumptions and unresolved
risks`; silence is the only wrong answer.

**The approval path.** Given this spec approved, When
`ls specs/045-critics-inside-spec` runs, Then it prints `plan.md` and `spec.md` and
nothing else, and the next record in `docs/adr/` is this spec's digest approval — the
series continuing, which `madr.validate` reads and the old dossier never was.

## Decisions

<!-- One `**D-NNN-NN — <the decision>**` per line, each with a `**Rationale:**` under it.
     Prefix a line with `- [X]` to claim the decision earns promotion: it constrains
     specs that do not exist yet, and `ai-eng decide` promotes only marked lines.
     `ai-eng decide` does not write here: it writes a record under docs/adr/. -->

- [X] **D-045-03 — The template carries Grill and Council; the sidecar convention dies forward; the critic step reads both shapes, refuses emptiness, prompt and malformed ran: lines with fixtures, scopes no-authority to section bodies, and returns the approval record to docs/adr/.**
      **Rationale:** one decision, one file; the gate reads sections the way it read
      files, and written history is never rewritten.
- [X] **D-045-04 — Exactly three real options, always, before Decision; new specs only, history frozen; critics revise them in place; a decision earns a MADR only when it constrains future specs.**
      **Rationale:** three keeps the comparison honest without theatre; the position
      before the decision is what makes the recommendation auditable.
- **D-045-01 — ai-challenge becomes the grill: ≤10 command-backed `### Q` entries per
  round, an empty section refused, folded into `## Grill` by the author.**
  **Rationale:** the sweep's value was the execution, not the exhaustiveness; the cap
  bounds cold-context cost by structure.
- **D-045-02 — ai-council runs once: five named lenses + cross-read in a single pass,
  author writes the verdict, no HTML page, one heading owns one finding.**
  **Rationale:** the measured mechanism is the lens/cross-read pair; the third round
  and the page duplicated the author's fold.
- **D-045-05 — every critic round records `ran: round <n>, <date> — <n> min`, refused
  when malformed; minutes self-reported and visible, not audited.**
  **Rationale:** a cost the design claims to cut must be visible on the artifact the
  design produces; owner-reported timings alone are the fiction rule 11 refuses.

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
