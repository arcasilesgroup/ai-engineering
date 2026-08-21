---
id: "023"
slug: council-that-reads-itself
status: draft
date: 2026-08-21
ref: ""
supersedes: ""
---

# Council that reads itself

## Who this is for, and what it is worth to them

The repository owner, who signs specifications, and anybody else who will ever run
`/ai-council` on one before signing it.

Today that command hands him five lists of gaps written by five readers who never saw each
other's lists, and nothing reads across them. So the gap that no single lens's question was
shaped to see — the one every lens missed — is the one thing the council cannot find, and it
is the reason a person runs a council rather than a reader. He asked for the change on
2026-08-21 in these words: "quiero que nuestro ai-council lo sustituyamos con este", meaning
the LLM Council method, whose chairman produces a verdict and a recommendation. Told that it
contradicts a decision record accepted that morning, he answered "pero debemos hacerlo".

That exchange is the whole authority for the verdict half of this change, and it is written
here because it is not written anywhere else in the tree.

What changes for him: one page he reads and acts on, instead of five lists he cross-references
himself. What it costs him is below, in numbers, including the numbers that count against it.

## Context and problem

`/ai-council` today runs five lenses over one specification. No lens sees another's answer,
there is no vote, no ranking and no field in which the word approved could be written. A
finding that carries no runnable command is deleted before the file is written, and the count
of deletions is printed — so one of the two counts this specification proposes already ships.

Decision record `docs/adr/0019` is `status: accepted`, dated 2026-08-21 under the standing
authority reference `no-hitl-2026-08-20`. Its Decision outcome contains the sentence this
specification exists to answer: "there is still no benchmark that defines the improvement a
council shows." Specification 013 asks for the same thing in the same words at line 212 —
"A second model must find a measurable gap, not manufacture consensus, and no benchmark
defines the improvement it would show" — and records `EP-195` as `NON-GOAL` at line 194.
`docs/requirements.toml:1445` records it a third time, as `verdict = "NO-EVIDENCE"` with
`mover = "decided"`, and `tests/ledger_run.py` executes its evidence command. Three rows, one
requirement, and this specification moves all three or none.

Three separate problems sit under that.

**One: nothing reads across the lenses.** Measured on human reviewers reading a real
artifact, independent readers raise 56% more issues than readers who confer — 14 per session
against 9 — and only 30% of what the independent group found was seen by more than one of
them. That is the case for keeping them independent. The same experiment prices it: those
independent readers had a 22% false-positive rate against 5.3% for the readers who conferred,
with no significant difference in valid defects found. Reading alone buys coverage and pays
in precision, and this council has never paid the precision back.
`.ai/reports/003-council-peer-review-evidence.html` [12], committed with this specification.

**Two: nothing here is readable by the person it is for.** `specs/NNN-slug/council.md` is
five sections a person must synthesise themselves. The same experiment reports that
participants strongly preferred the method with a meeting and believed it produced higher
quality, despite the data saying it did not. The effective precision of a finding nobody
reads is zero, and nothing in this repository measures whether the council's output is read —
which means this problem has no comparator before the change or after it, and the claim to
have solved it cannot be graded.

**Three: the method the owner asked to adopt cannot land as bytes.** Its frontmatter names a
skill that is not this directory, its description carries no "Not for X — use /ai-Y" clause
and is written in a form `tests/skill_eval.py` cannot read, it brings no `corpus.md`, it is
not marked `context: fork`, and it is roughly five times the current file's length. Each of
those is a check in this repository with a command beside it in "Examples somebody can
check". The pasted file is not in the tree, so the count of checks it reds cannot be run
here and no number is claimed for it.

And the artifact behind the method is smaller than its reputation. `karpathy/llm-council` is
five commits, all made on 2025-11-22, unchanged since, with no tests and no benchmark. Its
author called the design space "under-explored", recorded that the peer ranking disagreed
with his own judgement, and a month later filed the project under "quick app demos". Read
from its source rather than its README: the anonymisation labels are never shuffled, so
"Response A" is the same model on every query; the ranking prompt names no criteria at all;
the computed aggregate ranking is never passed to the chairman; and the chairman prompt
re-attaches every model name. `.ai/reports/003` [3]. Those five readings came from the
network and are not checkable from this tree.

## Options considered

1. **Adopt the pasted file as bytes.** Costs: the checks in "Examples somebody can check",
   one accepted record contradicted silently, and a skill whose frontmatter this repository's
   own routing evaluation cannot parse — `tests/skill_eval.py` reads only the folded
   `description: >-` form and only double-quoted trigger phrases, so the skill would claim no
   situation and nothing would route to it. It produces a red gate and no working council.
   Killed.

2. **Keep the council as it is and add nothing.** Costs: `EP-195` stays open with no
   instrument in three separate rows, the precision gap above stays unpaid, and the owner's
   request is refused twice. Its one merit is that it is the only shape this repository has
   evidence for, and that evidence is doctrine rather than measurement: `COUNCIL_VERDICT` in
   `tests/test_contracts.py` is a regular expression asserting a design opinion, which is the
   thing rule 11 says must pass with a command rather than an assertion. Killed.

3. **Replace the method, and keep the ranking.** Five advisors, an anonymised peer review
   that asks which response is strongest, a chairman that ranks and then synthesises. This is
   the pasted method, adapted to the contract. Costs, measured: the one head-to-head that
   exists implements this exact shape — a class docstringed "Structure A: Independent →
   Rank → Synthesize (Karpathy Baseline)" — and it was the only deliberative structure to
   score *below* the best individual member, 70.7% against 71.7% on MMLU-Pro Math. In the
   same harness with the same models, majority vote scored +5.1pp and deliberate-then-vote
   +9.2pp. The ensemble works; ranking and then synthesising is what loses. Its author's own
   stated limits: 7-9B models, most pairwise comparisons not significant, may not generalise
   to frontier scale. `.ai/reports/003` [1]. Killed on that measurement, not on doctrine.

4. **Replace the method, and replace the ranking question with a precision question.**
   Chosen. Described below.

## Decision

Option 4. `/ai-council` becomes three rounds and two files, both of them under `specs/`.

**Round one — five lenses, independent, as today.** Each reads the specification and nothing
else. Independence is what buys the 56% coverage, and it cannot be recovered by instruction:
placing another answer in an LLM's context flips a correct answer to a wrong one at 66.5%,
against 10.3% for a plain re-ask, *without* attributing that answer to anybody — so the
damage is done by the content being present, not by social framing [7].

**Round two — anonymised cross-read, and it does not rank.** Each lens sees the other four
answers, relabelled and shuffled per run, and *not its own*: withholding a lens's own section
is what keeps self-preference out of the round that deletes things, and it costs nothing
because a lens re-reading itself was never the point. It answers two questions: *which
findings here do you believe are false positives, and what command shows it* — and *what did
all of us miss*. It is never asked which response is strongest. That is the whole of the
difference from the pasted method, and it is where the measurement points: what the cross-read
is measured to buy is precision, 22% false positives down to 5.3% with no loss of valid
defects [12], while list-wise ranking of five comparably good answers is the worst case in the
position-bias literature — consistency falls from 0.70 to 0.34 for one judge and from 0.82 to
0.67 for another when moving from pairwise to list-wise, and it is lowest precisely when the
candidates are close in quality [4].

**Round three — a chairman, anonymised, that synthesises and recommends.** It is given the
specification under review, the five round-one sections and the round-two answers, all without
lens names, and it writes new text rather than picking a winner: an aggregator that composes
beats the same model selecting one answer [5], and at equal compute that gain is +9.0pp on
hard items against +2.2pp on easy ones [6] — specification review is the hard-item regime.
It never learns which lens said what. Re-attaching names is measured as a large causal lever
on preference — self-preference runs 0.511 unlabelled against 0.82 to 0.97 labelled — and
re-attaching them is a defect in the original artifact, not part of its idea [20].

**What a refutation has to be, and what happens to what it refutes.** A refutation carries a
command, that command is executed, and its output is written down. A refutation with no
command, or one whose command does not show what it claims, is itself discarded. A finding
that survives a refutation stays whole; a finding that does not is **struck through and kept
in the file with the refuting command beside it**, never erased — a wrongly refuted real gap
that leaves nothing but an integer is unrecoverable, and this design's own risk section says
wrong refutation is the failure it fears most. Where one lens refutes and another corroborates,
the finding stays: corroboration is the standing rule this council already has, and a
refutation only removes what nothing else supports.

**What it may write and what it may not.** The chairman writes a verdict, the disagreements,
the blind spots, a recommendation and one first step. It may not write granted authority. See
`D-023-03` for exactly which words move and which do not; the change is not one word and is not
a relaxation.

**Two files, both under `specs/NNN-slug/`.** `council.md`, the transcript, and `council.html`,
the page a person reads. Not `.ai/reports/`: `policy/capabilities.toml:109` gives `ai-council`
`write_roots = ['specs']` and nothing else, and the reports directory is a flat, hand-allocated
`NNN` namespace shared with `/ai-research` where three numbers already mean something else.
Writing beside the specification needs no capability change, no manifest proof and no allocator.

**And the number `EP-195` asked for, as a script.** A script counts two things from
`council.md` and writes a receipt, and a step in `just check` reads it: findings that appeared
only after the cross-read, and findings deleted for carrying no command or for being refuted.
It is a script and not a prompt because rule 12 says so and because rule 11 refuses a number a
model asserts about its own run. A "new" finding is one that no round-one lens named and whose
absence its command demonstrates; two lenses naming one gap stays corroboration and stays two
entries, which is the rule this council already has.

`contract.CEILING` is deleted in the same change, for reasons that are its own decision below.

## Challenged once

**The strongest realistic case that this is wrong:** every heavy negative result cited above
measures *iterated* debate, and this design has one round. If one-shot cross-reading behaves
like iterated debate, then round two imports a 57-77% correct-to-wrong conformity rate [9]
and a 32.3pp oracle gap [8] into a council whose entire job is to be trusted about absence.
If it does not, roughly fifteen of those findings do not apply at all.

**Nobody has run that comparison.** No paper puts one-shot cross-reading and iterated debate
on the same benchmark, models and token budget. The research pass looked and marked it
unsourced, and it stays unsourced here.

**The decision is kept, and here is why the case does not carry it.** Round two never asks a
lens to change its answer, never shows it a rebuttal, never tells it that it was ranked and
never seeks consensus — the four mechanisms every one of those papers measures. What it asks
for is a new artifact: a refutation carrying an executed command. That is a structural answer
rather than a measured one, and it is weaker than a measurement.

**And it was run once, on this document.** Five lenses read this specification independently
and produced 28 findings. The cross-read then produced 11 gaps no lens had named, each verified
absent by a command, and refuted 3 findings, each refutation executed. One cross-read claim was
itself discarded as invented. That is `specs/023-council-that-reads-itself/council.md`, and it
is one run on one document by one model family — not a benchmark, and not offered as one. It
is the first evidence this repository has ever had on the question, and the instrument in
`D-023-05` is what turns one run into a series.

**What that run also showed:** an independent challenger executing this specification's
sentences found six of them wrong, including two about the very test `D-023-03` rewrites. Every
one is repaired in this text. That the author's own document failed its first execution is the
argument for the stage, not against it.

## Assumptions and unresolved risks

**Assumptions.**

- That a deletion carrying an executed command is a better filter than a vote. One run, above.
- That the five lenses produce genuinely different readings. Persona assignment does not
  improve accuracy — 162 roles, 2,410 questions, 9 models, no persona significantly beat the
  no-persona control [19] — but it does significantly increase the diversity of what is
  generated, and the same study finds that aggregating the best persona per question helps
  while no automatic way of picking it beats chance. Run them all and pool is the reading that
  assumption rests on.
- That shuffling labels per run helps. It is variance reduction rather than de-biasing [16],
  and it is kept because the script that writes the round-two prompt has to order them anyway.

**Unresolved risks.**

- The two counts may show no gap on later runs. Then `EP-195` stays open, all three of its rows
  stay as they are, and this change bought a readable page and nothing else — which must be
  said in the record rather than absorbed.
- Deleting `contract.CEILING` removes the only automatic thing that noticed a skill becoming a
  procedure. Rule 12 becomes a prompt again, and rule 12 itself says a judgement that always
  resolves the same way should be code. This is a known regression, accepted by the owner on
  2026-08-21, and it is not repaired here. Restoring it later is not re-adding a constant: it
  is a mutation row, a stats field, two assertions and whatever skill has grown past 80 lines
  in the meantime.
- One council run costs eleven model calls where today's costs five — five lenses, five
  cross-reads, one chairman — and round two's input is roughly four times a lens's own answer.
  No new credential and no new provider: the lenses are forks of whatever host is already
  running, and `policy/pilot-register.toml:415` records that this framework will not require an
  account to install. Wall-clock and tokens per run are not measured here and should be, after
  the first ten runs, from the receipt `D-023-05` introduces.
- The evidence base on the LLM side is five unrefereed preprints from 2025-2026 running mostly
  0.5B-14B open-weight models. The human-judgement evidence is peer-reviewed and thirty years
  old. Neither half is about this repository.
- Reverting is one `git revert` of one commit, and the receipts written before it survive it.
  Nothing here is a schema change and nothing lands outside `specs/`, `.ai/reports/`, the four
  files that read `CEILING`, and the skill's own directory.

## Examples somebody can check

**The pasted file does not route.** Given the pasted skill's frontmatter, When
`tests/skill_eval.py` reads it, Then the skill claims no situation, because `description()`
parses only the folded form and `_TRIGGER` matches only double-quoted phrases — verified by
running `uv run python -c "import sys; sys.path.insert(0,'tests'); import skill_eval;
print(repr(skill_eval.description('description: \"a b\"')))"` and reading `''`.

**Changing the description has a price.** Given the corpus as it stands, When `just skilleval`
runs, Then it prints `RAN skilleval=326` beside `baseline 326, delta +0, margin 0`, so
changing the skill's description and its `corpus.md` moves that number and the baseline at
`policy/pilot-register.toml:329` must move in the same commit with a sentence saying why.

**The cap is spent on formatting, not instructions.** Given the sixteen skills, When each is
measured as non-blank lines of `contract.prose(body)` — frontmatter, fenced blocks, tables and
block quotes removed — Then the largest is `ai-spec` at 52, whose raw `wc -l` is 80 — verified
by running `uv run python -c "from pathlib import Path; from ai_engineering import contract;
print(max((len([l for l in contract.prose(p.read_text()).splitlines() if l.strip()]),
p.parent.name) for p in Path('.agents/skills').glob('ai-*/SKILL.md')))"` and reading
`(52, 'ai-spec')`.

**The comparator for the claim this rests on.** Given `CONSTITUTION.md`, When its line 53 is
read, Then it says models never grant authority and says nothing about recommending —
verified by running `git show HEAD:CONSTITUTION.md` and reading `Models may investigate,
propose and review; they never grant authority or accept risk.` This is the comparator
`docs/adr/0014` requires, and `D-023-03` is wrong without it.

**The test is looser than the document it enforces.** Given `tests/test_contracts.py` today,
When the four things `D-023-03` says must still fail are tested against the live
`COUNCIL_VERDICT`, Then three of them pass undetected — a bare `approved`, a bare `PASS` and
`Risk accepted: R-023-01` — while `Recommendation: sign it` and `Verdict: keep` are refused,
verified by running `uv run python -c "import re,pathlib; s=pathlib.Path('tests/test_contracts.py').read_text();
ns={'re':re}; exec(s[s.index('COUNCIL_VERDICT ='):s.index('COUNCIL_TALLY =')], ns);
print([bool(ns['COUNCIL_VERDICT'].search(x)) for x in ('approved','PASS','Risk accepted: R-023-01','Recommendation: sign it','Verdict: keep')])"`
and reading `[False, False, False, True, True]`. So this decision is not a relaxation of one
word: it removes two and adds detection for four things nothing detects today.

**The denial path, after the rewrite.** Given the rewritten boundary, When `council.md`
contains `Recommendation: tighten section 4` or `Verdict: answerable`, Then the suite passes;
and When it contains `Recommendation: approve`, a bare `approved`, `PASS`, `FAIL` or an
accepted risk, Then the suite fails, because the authority words are refused anywhere on the
line and not only as a field — which is the whole of what separates the two, and the thing
this specification is most likely to have got wrong.

**The undecidable path.** Given a run where round one produces no findings at all, or where
fewer than five lenses answer, When the file is written, Then it says how many answers round
two had, the chairman says it wrote over an empty transcript, and both counts are `0`. A
council that never comes back empty is a council inventing work, and a run that cannot say
how many readers it had is a run nobody can re-derive.

**Deleting the cap moves six things.** Given the deletion of `contract.CEILING`, When
`grep -rn 'contract\.CEILING\|^CEILING = \|> CEILING\|{CEILING}' src tests AGENTS.md` runs,
Then it answers with the constant and its check in `src/ai_engineering/contract.py`, two
assertions at `tests/test_record.py:853-857`, a guards-lane row at `tests/mutation.py:92`
whose row count moves with it, `tests/stats.py:154` and `:226` where `skill_ceiling` is a
published denominator, and `AGENTS.md:91`, which states the cap as doctrine and is itself
length-capped by a test — verified by running `uv run --with pytest python -m pytest
tests/test_record.py -k line_cap -q` and reading `1 passed` today. The same grep also answers
`src/ai_engineering/readiness.py:212` and `tests/pilot_register.py:95`, which are a different
constant with a similar name and must not be touched.

## Decisions

**D-023-01 — `/ai-council` gains an anonymised cross-read round and a chairman, and keeps its
five independent lenses.**

**Rationale:** Independence is what buys coverage — 14 issues against 9, and 70% of them seen
by exactly one reader — and it cannot be restored by instruction once another answer is in
context, which flips correct answers at 66.5% with nobody attributed. The cross-read is added
for the thing independence is measured to cost, which is precision: 22% false positives
against 5.3%, with no difference in valid defects found. Run once on this document it produced
11 gaps no lens had named and refuted 3 findings.

**D-023-02 — Round two asks which findings are false positives and what all of them missed. It
never asks which response is strongest, and no lens sees its own answer.**

**Rationale:** The only head-to-head measurement of rank-then-synthesise puts it below the best
single reader, −1.0pp, in a harness where voting scored +5.1pp and deliberate-then-vote +9.2pp.
List-wise ranking of five comparably good answers is the worst case in the position-bias
literature, and comparative protocols are about four times more manipulable than absolute ones.
Withholding a lens's own section keeps the self-preference effect that `D-023-04` cites out of
the round that deletes things, where it would otherwise apply at full strength.

**D-023-03 — The chairman writes a verdict and a recommendation, and the never-approves test is
rewritten rather than relaxed.**

**Rationale:** The owner asked for a verdict twice and that is his decision to make.
`CONSTITUTION.md:53` forbids a model granting authority, not a model recommending, and the test
was stricter than the document it enforces. But it is also *looser* than that document in the
other direction, which the challenge found by executing it: a bare `approved`, a bare `PASS`, a
gate result and an accepted risk are all undetected today. So the change is: `verdict` and
`recommendation` leave the field list; `approval`, `decision`, `vote`, `votes`, `voted`,
`score`, `scores`, `consensus`, `ranking` and `ranked` stay on it; `COUNCIL_TALLY` stays
untouched; and a new pattern refuses `approved`, `approve`, `approval`, `PASS`, `FAIL`,
`granted` and an accepted risk *anywhere on the line*, which is what keeps the test's existing
fixture `Recommendation: approve` refused while letting `Recommendation: tighten section 4`
pass. Recording a decision stays with `ai-eng decide` and a named person.

**D-023-04 — The chairman never learns which lens wrote what, and is given the specification
under review as well as the two rounds.**

**Rationale:** Identity disclosure moves self-preference from 0.511 to between 0.82 and 0.97 on
the same texts, so anonymisation is a lever that works. The original artifact re-attaches names
in the one call that writes the user-facing answer, which is a defect in it rather than part of
its idea. It is given the specification because a chairman that has not read the document
cannot check a refutation's command, and the whole of round two is commands.

**D-023-05 — A script counts how many findings appeared only after the cross-read and how many
were deleted, writes a receipt, and a step in `just check` reads it.**

**Rationale:** `EP-195` asks for a measurable gap rather than a manufactured consensus, and
`docs/adr/0019` records that no benchmark defines the improvement a council shows. These two
counts are that instrument, and one half of it — the deletion count — already ships as a
sentence in the skill today, which is exactly the shape rule 12 says must become code. A number
a model prints about its own run is what rule 11 refuses, so it lands in `.ai/receipts/` beside
`skill-evaluation.json` and is read back by the gate, or it is not evidence.

**D-023-06 — `contract.CEILING` is deleted, together with its five call sites in four files and
the sentence of doctrine that states it.**

**Rationale:** Measured before deciding: across sixteen skills the largest raw file is 80 lines
and the largest prose count is 52, so the cap was being consumed by frontmatter, blank lines,
headings and fenced blocks rather than by instructions, and it was binding on exactly one file.
Readability already has a direct instrument in `SKILL_FOG_CEILING`, which bounds a rate and not
a length — so nothing bounds length afterwards, and that is the regression, recorded above. The
owner chose deletion over changing what the cap counts, on 2026-08-21, having been shown that
cost. The five sites are named in "Examples somebody can check" because the first draft of this
decision named two of them and the challenge found the other three.

**D-023-07 — The skill's `corpus.md` and its description move in the same commit, and the
`skilleval` baseline moves with them.**

**Rationale:** `.agents/skills/ai-council/corpus.md:21` refuses the case "have the members vote
and tell me the verdict" on the ground that "there is no field to disagree in", and the skill's
own description says it "has no vote, no verdict and no field in which the word approved could
be written". `D-023-03` makes both of those false. `tests/skill_eval.py` scores routing on
exactly those two texts, so a refusal that no longer holds is a routing defect and not merely a
number that moves — and the number moves too, against a baseline whose margin is zero.

**D-023-08 — `docs/adr/0019` is superseded by a new record, and the other two `EP-195` rows are
moved by that record or not at all.**

**Rationale:** A deferral is reopened by a record, not by a commit that quietly disagrees with
one — which is the sentence `0019` wrote about itself. It is superseded with
`ai-eng decide --supersede 0019`. `EP-195` is recorded in two further places, `specs/013`
line 194 as `NON-GOAL` and `docs/requirements.toml:1445` as `NO-EVIDENCE`, and the new record
names what happens to each. Until the receipt from `D-023-05` has been read on more than one
run, the honest move for both is to leave them where they are and say why in the record.

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
