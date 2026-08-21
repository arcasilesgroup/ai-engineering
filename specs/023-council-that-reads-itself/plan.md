# Plan: the council that reads itself — 023 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**. The approval of these two files is recorded in its own record, at the
digests named there, because an approval cannot be written inside the file it approves.

One repository writer, on `spec/023-council-substitution`. Each task is one atomic commit
changing one primary production, policy or skill file plus only the files that task names.
Rollback for every task and every repair is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the whole gate in the
same chain as the commit itself, because a receipt is keyed to the bytes being committed and
a `;` between the two ships a red gate.

## The order, and why

The record that reopens a deferral goes first, because a deferral is reopened by a record and
not by a commit that quietly disagrees with one — which is the sentence `docs/adr/0019` wrote
about itself.

The line cap goes second and not last. The rewritten skill is longer than the file it
replaces, and `contract.audit_one` refuses any `SKILL.md` over `CEILING` lines, so a cap still
standing when task 5 lands turns the whole change red for a reason that has nothing to do with
councils.

The instrument goes before the thing it measures, and the boundary goes before the skill that
writes into it. Task 5 is last because it is the only one that cannot be committed alone: the
skill's description and its `corpus.md` are both scored by `just skilleval` against a baseline
whose margin is zero, so the text, the corpus and the baseline move together or the gate is
red between them.

## What this plan is not doing, and why

- **No CI/CD task and no observability task.** Specification 023 adds nothing that gets a URL:
  no service, no endpoint, no deployment. `/ai-plan` requires both only for deployable work,
  and inventing them here would be eight boxes ticked against nothing.
- **No renaming of `ai-council`.** Twelve files name it. The method changes; the name does not,
  so none of the twelve breaks.
- **No change to `.ai/intent.md`.** This is a skill and a test, not a change of Solution Intent.
- **No move of `EP-195` in `specs/013` or `docs/requirements.toml`.** `D-023-08` says why: one
  run is not a series, and the honest move is to leave both rows and say so in the record.
- **No second file at `.ai/reports/`.** `policy/capabilities.toml:109` gives `ai-council`
  `write_roots = ['specs']`, so `council.html` lands beside the specification and no capability
  changes. Writing the HTML sibling is inside task 5, not a task of its own.

## The boundary this plan may not cross

`SKILL_FOG_CEILING`, `contract.fog` and `contract.prose` are the readability instrument and
are **not** part of this work. `MAX_AGE_CEILING` in `src/ai_engineering/readiness.py` and
`_CEILING` in `tests/pilot_register.py` are different constants with a similar name. A diff
that touches any of the five has deleted or altered a control by name collision. Task 2 proves
it did not happen rather than asserting it.

## Block A — the record and the room to write it (Tasks 1–2)

1. [ ] **A record reopens the deferral that said a council may not conclude** —
   **file** `docs/adr/` (a new record, created by `uv run ai-eng decide --supersede 0019 --spec 023`).
   **check**: `uv run python -c "import sys;from pathlib import Path;sys.exit(0 if any('0019' in p.read_text(encoding='utf-8').split('supersedes:')[1][:12] for p in Path('docs/adr').glob('*.md') if 'supersedes:' in p.read_text(encoding='utf-8')) else 1)"`
   and `uv run --with pytest python -m pytest -q tests/test_madr.py`.
   **rollback**: `git revert <commit>`.
   **done when**: a record with `status: accepted` names `0019` in its `supersedes` field, states
   that `EP-195` is not closed by it and that the two rows in `specs/013` and
   `docs/requirements.toml` stay where they are until the receipt from `D-023-05` has been read
   on more than one run, and `madr.validate` is green.

2. [ ] **The skill line cap is deleted, with its four consumers and the doctrine that states it** —
   **file** `src/ai_engineering/contract.py`, and with it `tests/test_record.py`,
   `tests/mutation.py`, `tests/stats.py`, `AGENTS.md` and `CHANGELOG.md`.
   **check**: `uv run python -c "import sys;from ai_engineering import contract;sys.exit(1 if hasattr(contract,'CEILING') else 0)"`
   and `uv run --with pytest python -m pytest -q tests/test_record.py tests/test_contracts.py`
   and `just guards`.
   **rollback**: `git revert <commit>`.
   **done when**: `contract.CEILING` and the length branch in `audit_one` are gone;
   `test_a_skill_over_the_line_cap_is_a_procedure_that_should_be_a_script` is deleted rather
   than skipped; the `"the skill cap"` row is out of `MUTANTS` and `just guards` still reports
   every remaining row killed; `tests/stats.py` no longer prints a denominator it cannot read;
   `AGENTS.md` no longer states a cap that does not exist; `CHANGELOG.md`'s `[Unreleased]`
   breaking block names `contract.CEILING` in the words somebody upgrading would search for;
   and `SKILL_FOG_CEILING`, `contract.fog`, `contract.prose`, `readiness.MAX_AGE_CEILING` and
   `tests/pilot_register._CEILING` are byte-identical to before —
   proved by `git diff HEAD~1 -- src/ai_engineering/readiness.py tests/pilot_register.py`
   printing nothing.

## Block B — the instrument, before anything it measures (Task 3)

3. [ ] **The two counts stop being a sentence a model prints and become a command the gate runs** —
   **file** `tests/council_counts.py` (new), and with it `justfile` and `tests/test_contracts.py`.
   **check**: `just council` and
   `uv run --with pytest python -m pytest -q tests/test_contracts.py -k council_counts`.
   **rollback**: `git revert <commit>`.
   **done when**: the script reads every `specs/*/council.md`, recomputes both numbers from the
   file's own structure rather than reading the totals the run wrote, refuses when the two
   disagree, writes `.ai/receipts/council-counts.json` in the schema
   `urn:ai-engineering:check-evidence:1` that `tests/skill_eval.py` already uses, exits non-zero
   when the file's shape cannot be parsed, prints `RAN council=<new>/<deleted>`, tolerates a
   repository with no `council.md` at all without inventing a pass, and `council` is a recipe
   inside `just check` before `ran`.

## Block C — the boundary and the skill (Tasks 4–5)

4. [ ] **The never-approves test starts refusing granted authority and stops refusing a conclusion** —
   **file** `tests/test_contracts.py`.
   **check**: `uv run python -c "import re,pathlib,sys;s=pathlib.Path('tests/test_contracts.py').read_text();ns={'re':re};exec(s[s.index('COUNCIL_VERDICT ='):s.index('def _verdict_fields')],ns);f=lambda x:bool(ns['COUNCIL_VERDICT'].search(x) or ns['COUNCIL_AUTHORITY'].search(x));sys.exit(0 if [f(x) for x in ('approved','PASS','Risk accepted: R-1','Recommendation: approve','Recommendation: tighten section 4','Verdict: answerable')]==[True,True,True,True,False,False] else 1)"`
   and `uv run --with pytest python -m pytest -q tests/test_contracts.py -k council`.
   **rollback**: `git revert <commit>`.
   **done when**: `verdict` and `recommendation` have left `COUNCIL_VERDICT`; `approval`,
   `decision`, `vote`, `votes`, `voted`, `score`, `scores`, `consensus`, `ranking` and `ranked`
   are still refused as fields; `COUNCIL_TALLY` is byte-identical; a new `COUNCIL_AUTHORITY`
   refuses `approved`, `approve`, `approval`, `PASS`, `FAIL`, `granted` and an accepted risk
   anywhere on a line; the existing fixture `Recommendation: approve` is still refused and
   `Recommendation: tighten section 4` is not; the test's docstring says which of the two
   directions each half holds; and the assertion about the skill's own text is left untouched
   for task 5.

5. [ ] **The council becomes three rounds, and its corpus stops refusing what it now does** —
   **file** `.agents/skills/ai-council/SKILL.md`, and with it
   `.agents/skills/ai-council/corpus.md`, `policy/pilot-register.toml` and
   `tests/test_contracts.py`.
   **check**: `just skilleval` at the moved baseline, `just cover`, and
   `uv run python -c "from ai_engineering import contract;import sys;p=__import__('pathlib').Path('.agents/skills/ai-council/SKILL.md');sys.exit(0 if not contract.audit_one(p) else 1)"`.
   **rollback**: `git revert <commit>`.
   **done when**: `SKILL.md` describes three rounds — five independent lenses, an anonymised
   cross-read that withholds each lens's own answer and asks for false positives rather than a
   ranking, and an anonymised chairman given the specification as well as both rounds; it states
   that a refutation carries a command that is executed, that a refuted finding is struck through
   and kept rather than erased, and that corroboration beats a lone refutation; it names the two
   files it writes, `council.md` and `council.html`, both under `specs/NNN-slug/`; its
   description still carries a `Not for X — use /ai-Y` clause and is still the folded
   `description: >-` form with double-quoted triggers; `context: fork` and `background: false`
   are unchanged; `corpus.md` no longer refuses "have the members vote and tell me the verdict"
   on a ground that is now false, and carries a case for the cross-read and one for the
   chairman's boundary; the `skill-routing` baseline in `policy/pilot-register.toml` names its
   new number with a sentence saying why it moved; and the assertion in `tests/test_contracts.py`
   requires the new boundary sentence instead of `No vote and no ranking`.

## Done when the plan is done

`just check` is green with its output shown, `just guards` reports every row killed,
`just council` prints two numbers read out of a file rather than asserted, and
`ai-eng spec show 023 --task <n>` refuses any task whose digests have moved.
