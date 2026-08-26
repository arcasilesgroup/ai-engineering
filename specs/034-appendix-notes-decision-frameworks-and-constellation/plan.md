# Plan: appendix notes, decision frameworks and constellation — 034 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**, recorded at their digests in their own record. One repository writer, on a
branch carrying the whole 034 change. Each task is one atomic commit touching one primary
production, policy or skill file plus only the files that task names. Rollback for every task
is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the whole gate in the same
chain as the commit itself. `ai-eng spec show 034 --task <n>` refuses any task whose digests
have moved.

## The order, and why

The three behaviours are independent modules plus one contract rule and corpus routes; they
land appendix first (it is a checked rule over ai-note, the smallest), then the two modules
(decision frameworks and constellation). The repair task brings the touched skills under the
rules, and the gate proves the tree clean. Each task starts with its red fixture exactly as
specs 028-033 did.

## What this plan is not doing, and why

- **No change to `.ai/intent.md`, `CONSTITUTION.md`, or the one-writer rule.**
- **No new skill.** The three behaviours are modules, one contract rule and corpus routes;
  the fifteen-skill target is unchanged.
- **No acceptance of ADR 0025 / no history rewrite of spec 026.**
- **No change to `justfile`/`test_quality_gate.py`** (the repository owner's uncommitted
  work sits there); the new suites join the existing `test` recipe.
- **No CI/CD box ticked.**

## The boundary this plan may not cross

`_appendix_problems` is a contract check on ai-note's *instruction* (the skill body refuses
rewrite), never a file-system lock — git remains the history. `decision_fw` names the three
frameworks only; a decision without one says so and is refused, never silently given a
method. `constellation` classifies a cluster (≥2 same-class signals → systemic; one →
isolated) and never downgrades a guard's own fail. The repo owner's uncommitted work in
`justfile`/`test_quality_gate.py` is never touched.

## Tasks

## Block A — appendix notes (B-034-1)

1. **Red fixture: ai-note that would overwrite an existing note is refused** —
   **file** `tests/test_decision_and_notes.py` (new, first case): a skill body saying
   "edit the note" / "rewrite the note" is refused; "append to the note" passes.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_decision_and_notes.py -k appendix`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before `contract.py` ships `_appendix_problems`, and
   green after — a rewrite instruction is refused, an append instruction passes.

2. **Appendix rule in contract + repair ai-note skill** —
   **file** `src/ai_engineering/contract.py` (add `_appendix_problems` and call it from
   `audit_one`), `.agents/skills/ai-note/SKILL.md` (state "a note is appended to, never
   edited"), plus the green half of the `-k appendix` fixture.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_decision_and_notes.py -k appendix`
   **rollback**: `git revert <commit>`.
   **done when**: the appendix rule refuses a rewrite instruction, the ai-note skill reads
   clean against it, and `contract.audit` reports no appendix problem on the tree.

## Block B — decision frameworks (B-034-2)

3. **Red fixture: a decision with no named framework is refused; named ones return a verdict** —
   **file** `tests/test_decision_and_notes.py` (append the `-k framework` cases): RICE,
   Effort/Value and Kano each return a deterministic verdict; a bare "ranked by impact"
   with no method is refused.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_decision_and_notes.py -k framework`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before `decision_fw.py` ships, and green after.

4. **Decision-framework module + corpus routes** —
   **file** `src/ai_engineering/decision_fw.py` (new, stdlib-only: `rice(reach, impact,
   confidence, effort)`, `effort_value(value, effort)`, `kano(category)`), and the
   `ai-report`/`ai-review` corpus rule "when decisioning, name the framework"; plus the
   green half of the `-k framework` fixture.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_decision_and_notes.py -k framework`
   **rollback**: `git revert <commit>`.
   **done when**: the three frameworks return deterministic verdicts, the corpus routes the
   named-framework rule, and `uv run python tests/skill_eval.py` moves the baseline only
   with the measured reason.

## Block C — constellation (B-034-3)

5. **Red fixture: a cluster reads systemic, an isolated signal reads noise** —
   **file** `tests/test_constellation.py` (new): ≥2 same-class signals in one context →
   systemic; a single signal in a clean context → isolated; a guard fail is never erased.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_constellation.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before `constellation.py` ships, and green after.

6. **Constellation module** —
   **file** `src/ai_engineering/constellation.py` (new, stdlib-only:
   `classify(signals)` → `systemic` | `isolated`; a single signal stays `isolated` without
   erasing the fail), plus the green half of `tests/test_constellation.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_constellation.py`
   **rollback**: `git revert <commit>`.
   **done when**: `classify` reports systemic for a cluster and isolated for a lone signal,
   and the clean control proves an individual fail is never downgraded.

## Block E — prove the gate (Task 7)

7. **The full gate reads the three behaviours green with their clean controls** —
   **file** none (verification).
   **check**: `just check`
   **rollback**: `git revert <commit>`.
   **done when**: `just check` exits 0, the appendix/framework/constellation suites pass
   with their clean controls, `tests/test_madr.py` reports exactly the same pre-existing
   failures as before this block (the ADR 0025 inherited red) — no fifth failure
   introduced; the spec, plan and approval of 034 are committed at their exact digests.