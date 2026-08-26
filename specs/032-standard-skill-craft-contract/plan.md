# Plan: standard skill-craft contract — 032 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**, recorded at their digests in their own record. One repository writer, on a
branch carrying the whole 032 change. Each task is one atomic commit touching one primary
production, policy or skill file plus only the files that task names. Rollback for every task
is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the whole gate in the same
chain as the commit itself. `ai-eng spec show 032 --task <n>` refuses any task whose digests
have moved.

## The order, and why

The same order spec 027 proved: the four contract rules land first, one task each, so that
when the repair pass runs there is a script deciding what "clean" means — a repair with no
gate behind it is prose with no teeth. Each rule gets its red fixture in the same commit
(the test that fails before the rule exists and passes after). Then the repair pass brings
every shipped skill under the four rules. Then the final task proves the whole tree reads
clean through the new contract and the gate. The earliest possible failure — a rule that
cannot decide its own case — is caught in task 1 before any skill is touched.

## What this plan is not doing, and why

- **No change to `.ai/intent.md`, `CONSTITUTION.md`, or the one-writer rule.**
- **No change to the skill-smell taxonomy (spec 027).** The four existing smell rules stay
  exactly as they are; this block adds four *craft* rules beside them, each in its own
  `_*_problems` function.
- **No acceptance of ADR 0025 / no history rewrite of spec 026.** The inherited
  `madr.validate` red is recorded, not fixed here; the final task asserts no new MADR
  failure.
- **No change to `justfile`/`test_quality_gate.py`.** Those carry the repository owner's
  uncommitted work; the new craft tests are picked up by the existing `test` recipe with no
  wiring.
- **No CI/CD box ticked.** Adds no service, endpoint or URL.

## The boundary this plan may not cross

The four rules live in `contract.py` beside the spec 027 smells and never touch the corpus
or routing files. Incorrect/Correct fires only where a `## Rules` section exists — a skill
with no rules passes, and a skill whose rules are prose is refused. The load-tier bound is
500 lines of `SKILL.md` body, with long embedded scripts refused in favour of a `scripts/`
file; the repair pass keeps every body well under it.

## Tasks

## Block A — the four craft rules (Tasks 1-4)

1. **Anti-rationalization rule in `contract.audit_one`** —
   **file** `src/ai_engineering/contract.py` (add `_anti_rationalization_problems` and call
   it from `audit_one`), and `tests/test_contract_craft.py` (new, first case: a skill with
   no such section is refused, one whose table answers an excuse passes).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contract_craft.py -k anti`
   **rollback**: `git revert <commit>`.
   **done when**: `contract.audit_one` reports a skill with no anti-rationalization section,
   and passes one whose section answers an excuse with a factual counter in the same entry.

2. **Output-contract rule in `contract.audit_one`** —
   **file** `src/ai_engineering/contract.py` (add `_output_contract_problems`), and the
   `-k output` case of `tests/test_contract_craft.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contract_craft.py -k output`
   **rollback**: `git revert <commit>`.
   **done when**: a skill whose `## What it produces` names no artifact is refused, and one
   that names a path is passed.

3. **Incorrect/Correct rule in `contract.audit_one`** —
   **file** `src/ai_engineering/contract.py` (add `_incorrect_correct_problems`), and the
   `-k pairs` case of `tests/test_contract_craft.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contract_craft.py -k pairs`
   **rollback**: `git revert <commit>`.
   **done when**: a skill with a `## Rules` section stated as bare prose is refused; a skill
   with an Incorrect/Correct pair passes; a skill with no rules section passes.

4. **Load-tier rule in `contract.audit_one`** —
   **file** `src/ai_engineering/contract.py` (add `_load_tier_problems`: body > 500 lines
   refused; long inline scripts refused in favour of `scripts/`), and the `-k load` case of
   `tests/test_contract_craft.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contract_craft.py -k load`
   **rollback**: `git revert <commit>`.
   **done when**: a body over 500 lines is refused; a body under the bound with scripts in
   `scripts/` is passed.

## Block B — repair the shipped skills (Task 5)

5. **Repair every SKILL.md to the four craft rules** —
   **file** `.agents/skills/` (each shipped pair that triggers a rule: add the missing
   anti-rationalization section, the `## What it produces` artifact, an Incorrect/Correct
   pair where a rules section exists, and move any long inline script to `scripts/`).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contract_craft.py`
   **rollback**: `git revert <commit>`.
   **done when**: `tests/test_contract_craft.py` passes against the live tree — no shipped
   `SKILL.md` triggers any of the four new rules, and the corpus/routing files are untouched.

## Block C — prove the whole tree reads clean (Task 6)

6. **The gate reads the repaired tree clean** —
   **file** none (verification).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contract_craft.py && uv run --with ruff==0.16.2 ruff check src tests`
   **rollback**: `git revert <commit>`.
   **done when**: the craft contract test passes over the live tree, ruff is clean, and
   `git status --short` shows only this block's files plus the repository owner's own
   uncommitted work.

## Block E — prove the gate (Task 7)

7. **The full gate reads the four craft rules green with their clean controls** —
   **file** none (verification).
   **check**: `just check`
   **rollback**: `git revert <commit>`.
   **done when**: `just check` exits 0, `tests/test_madr.py` reports exactly the same
   pre-existing failures as before this block (the ADR 0025 inherited red) — no fifth
   failure introduced; the spec, plan and approval of 032 are committed at their exact
   digests.