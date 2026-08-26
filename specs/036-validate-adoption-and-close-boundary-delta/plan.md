# Plan: validate adoption and close the boundary delta — 036 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**, recorded at their digests in their own record. One repository writer, on a
branch carrying the whole 036 change. Each task is one atomic commit; rollback for every task
is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the gate in the same
chain as the commit itself. `ai-eng spec show 036 --task <n>` refuses any task whose digests
have moved.

## The order, and why

Proof objects first, per the council: the fixtures (`tests/test_036_boundary.py`,
`tests/test_036_validation.py`) land red before their module; then the
`decision_boundary.py` module turns them green; then the corpus/description routes land on
the two parse surfaces the harness actually admits (refusal in each `SKILL.md` description
— the `_REFUSAL` surface — and one quoted boundary case in each `corpus.md` — the `cases()`
surface), with the `skill_eval` baseline move argued in the same commit; then the gate. The
spec's example commands are the acceptance tests; R0 of this plan is complete when those
commands print their stated counts.

## What this plan is not doing, and why

- **No change to specs 028-034 modules.** Every row of the validation table stays as it is;
  this plan never edits `evidence.py`, `verify_cold.py`, `contract.py`, `cost.py`,
  `capability.py`, `trim.py` or `decision_fw.py`. It only *asserts* them (B-036-3).
- **No change to 035's frozen bytes.** 035's spec and plan stay at their approval digests;
  the supersede note already landed on 035's `approval.md` (commit 90286a0d).
- **No new skill.** The boundary rule rides the existing three skills' descriptions and
  corpora; the skill set is unchanged.
- **No content-level `skill_eval` assertion machinery.** Per the council (F5.3), the harness
  carries the rules generically and never checks content; this plan adds parseable rows and
  the baseline move, nothing more.
- **No acceptance of ADR 0025** — the inherited `madr.validate` red stays; the final gate
  asserts no new MADR failure.
- **No CI/CD box ticked.** Adds no service, endpoint or URL.

## The boundary this plan may not cross

`decision_boundary.classify` returns a `Classified` (`verdict` + indexed `reason`): in-scope
decisions classify to Always/Ask-first/Never; out-of-declaration decisions classify to
`None` with `reason = U1..` and report `CANNOT DECIDE`; undeclared or malformed declarations
classify to `None` with `reason = U0`. It never coerces `None` into a class, never widens a
declared boundary, and reads declarations from the `capability.py` manifest surface — it
does not define a second permission model. The corpus rule lands only on the two parse
surfaces (`_REFUSAL` in SKILL.md descriptions, quoted cases with a destination in
corpus.md); a refusal in the wrong surface is the fixture's red half.

## Tasks

1. **Red fixtures: boundary and validation** —
   **file** `tests/test_036_boundary.py` (new) + `tests/test_036_validation.py` (new).
   `test_036_boundary.py` covers in-declaration (Always/Ask-first/Never, deterministic),
   out-of-declaration (`None`, `U1`, `CANNOT DECIDE`, blocks), and undeclared/malformed
   (`None`, `U0`). `test_036_validation.py` asserts every validation-table row: module
   exists, contract symbol exists, provenance marker in the docstring first line where the
   row names one (spec 029 / spec 030 / spec 033 / spec 034 / capability-era).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_036_boundary.py tests/test_036_validation.py`
   **rollback**: `git revert <commit>`.
   **done when**: both files run and fail for the right reason (no module, missing symbols)
   — the plan will turn real reds green.

2. **Decision-boundary module** —
   **file** `src/ai_engineering/decision_boundary.py` (new, stdlib-only: `Classified`
   (frozen dataclass: `verdict` + `reason`), `classify(decision, declarations)` returning
   Always/Ask-first/Never or `None` with `U0`/`U1..`, reading declarations from the
   `capability.py` manifest surface), plus the green half of `tests/test_036_boundary.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_036_boundary.py`
   **rollback**: `git revert <commit>`.
   **done when**: in-declaration classifies deterministically, out-of-declaration returns
   `None`/`U1` and blocks, undeclared/malformed returns `None`/`U0`, and a parallel test
   proves `capability.preflight` still behaves (no second model).

3. **Validation freshness green** —
   **file** `tests/test_036_validation.py` (green half, no production change).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_036_validation.py`
   **rollback**: `git revert <commit>`.
   **done when**: every table row's module exists with its symbol and provenance marker;
   deleting a module fails the check (the red half is proven by task 1's run).

4. **Corpus and description routes for the boundary rule** —
   **file** `.agents/skills/ai-spec/SKILL.md`, `.agents/skills/ai-review/SKILL.md`,
   `.agents/skills/ai-verify/SKILL.md` (each gains a `Not for … — …` refusal clause naming
   the decision-boundary rule in its description) and each skill's `corpus.md` (one quoted
   boundary situation with its destination). The `skill_eval` baseline move is argued in
   this same commit.
   **check**: `uv run python tests/skill_eval.py && uv run --with pytest==9.1.1 pytest -q tests/test_036_boundary.py tests/test_036_validation.py`
   **rollback**: `git revert <commit>`.
   **done when**: the refusal is read by `_REFUSAL` from the descriptions, the quoted cases
   are read by the routing lane, the baseline moves with its reason, and a fixture proves a
   refusal written only in `corpus.md` is not counted (the red half).

5. **035 supersede receipt and plan trace** —
   **file** none beyond records (verification): `ai-eng spec list` shows 036 `supersedes:
   035`; 035's approval.md carries the note and its digests are unchanged.
   **check**: `git diff 90286a0d -- specs/035-adoption-of-reference-patterns/spec.md specs/035-adoption-of-reference-patterns/plan.md` (empty)
   **rollback**: `git revert <commit>`.
   **done when**: 035's frozen bytes are bit-identical, the supersede chain reads
   036 → 035 by value.

6. **The gate** —
   **file** none (verification).
   **check**: `just check`
   **rollback**: `git revert <commit>`.
   **done when**: `just check` exits 0, the boundary and validation suites pass with their
   clean controls, `tests/skill_eval.py` runs at the new baseline, `tests/test_madr.py`
   reports exactly the same pre-existing failures as before this block (the ADR 0025
   inherited red) — no new failure — and the spec, plan and approval of 036 are committed
   at their exact digests.