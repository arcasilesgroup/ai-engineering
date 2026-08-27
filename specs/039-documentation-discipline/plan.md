# Plan: documentation discipline — 039 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and
this exact `plan.md`**, recorded at their digests in their own record. One repository
writer, on a branch carrying the whole 039 change. Each task is one atomic commit; rollback
for every task is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the gate in the same
chain as the commit itself. `ai-eng spec show 039 --task <n>` refuses any task whose
digests have moved.

## The order, and why

Proof objects first: the fixture (`tests/test_039_documentation.py`) lands red before its
deliverables. Then the reference (B-039-1) turns it green, then the three differentiated
corpus routes + the `skill_eval` baseline move (B-039-2), then the gate. The spec's example
commands are the acceptance tests; each `--tick` seals its box.

## What this plan is not doing, and why

- **No new skill.** The discipline is a reference beside `ai-report` + three corpus routes.
- **No port of the technical-writer agent.** It stays an insumo in claude-agents (D-039-01).
- **No hard STE100 parser.** The mechanical craft lanes already hold over our own docs; a
  parser over user repos violates ownership. A light prose check is deferred to measured
  need (recorded in the spec).
- **No acceptance of ADR 0025** — the inherited `madr.validate` red stays; the final gate
  asserts no new MADR failure.
- **No CI/CD box ticked.** Adds no service, endpoint or URL.

## The boundary this plan may not cross

The reference is the single source of the discipline, reached only through the three corpus
routes (never always-loaded). The three routes are phrased differently per surface so the
routing harness sees three distinct cases, not one fork. The refusal targets a doc that
hands an agent a vague completion bound or restates the environment; it never edits a user
repo. Each commit is atomic with its fixture.

## Tasks

1. [ ] **Red fixture: reference + routes + bare-bound denial** —
   **file** `tests/test_039_documentation.py` (new): three cases — `reference`
   (the reference names context pointers, the two loads, leading words, pruning and the
   STE100 one-idea-one-sentence rule), `bare_bound` (a doc handing an agent "understanding
   reached" is refused by the route), `no_fork` (the three routes differ from each other).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_039_documentation.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture runs and fails for the right reason (no reference, no routes).

2. [ ] **The documentation-writer reference (B-039-1)** —
   **file** `.agents/skills/ai-report/.agents/skills/ai-report/references/documentation-writer.md` (new: the
   writing-for-agents levers and the STE100 controlled-language rules, as the single source
   of the discipline), plus the `reference` case green.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_039_documentation.py -k reference`
   **rollback**: `git revert <commit>`.
   **done when**: the reference names every lever the fixture asserts and the route-pointed
   material exists.

3. [ ] **The three differentiated corpus routes (B-039-2)** —
   **file** `.agents/skills/ai-spec/corpus.md` + `.agents/skills/ai-plan/corpus.md` +
   `.agents/skills/ai-report/corpus.md` (each gains its own quoted route naming the
   discipline and a `Not for … — …` refusal for a vague bound or an environment restatement;
   phrased differently per surface), plus the `bare_bound` and `no_fork` cases green and the
   `skill_eval` baseline move argued in this same commit.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_039_documentation.py && uv run python tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: the three routes parse as three distinct cases, the denial is refused, and
   the baseline moves with its reason (or stays, with the reason stated).

4. [ ] **The gate** —
   **file** none (verification).
   **check**: `just check`
   **rollback**: `git revert <commit>`.
   **done when**: `just check` exits 0 with the 039 suite green, `tests/test_madr.py`
   reporting exactly the same pre-existing failures as before this block (the ADR 0025
   inherited red) — no new failure — and the spec, plan and approval of 039 are committed
   at their exact digests.