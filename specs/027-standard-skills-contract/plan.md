# Plan: standard skills contract — 027 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**, recorded at their digests in their own record. One repository writer, on a
branch carrying the whole 027 change. Each task is one atomic commit touching one primary
production, policy or skill file plus only the files that task names. Rollback for every task
is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the whole gate in the same
chain as the commit itself. `ai-eng spec show 027 --task <n>` refuses any task whose digests
have moved.

## The order, and why

The standardization is a contract, not a cleanup: `contract.py` already audits each skill by
script, and the four smell rules it gains must exist before any skill is repaired, or the
the "repair" is prose with no gate behind it. So the plan adds the rules first (one task each),
then repairs the sixteen skill pairs, then a final task proves the whole tree reads clean
through the new contract. The earliest possible failure — a rule that cannot decide its own
case — is caught in task 2, before any skill is touched.
`ai-eng spec show 027 --task <n>` refuses any task whose digests have moved.

## What this plan is not doing, and why

- **No CI/CD task and no observability task.** Spec 027 adds no service, no endpoint, no URL:
  contract rules, skill text, tests. `/ai-plan` requires deployables only; inventing the
  boxes here would be ticked against nothing.
- **No change to the skill-smell taxonomy itself.** arXiv:2607.01456 is the authority and the
  contract imports its classes (portable-command, existence-check, forced-output,
  sourced-statistic). This block encodes those four, nothing broader.
- **No change to `.ai/intent.md` or `CONSTITUTION.md`.** This is a skill-contract rule set,
  not a change of Solution Intent.

## The boundary this plan may not cross

The skills ship to a downstream repo whose surface the wheel guarantees only commands the wheel
installs. The portable-command rule therefore permits `ai-eng` verbs and the output of a tool
kept as a gate's evidence; it refuses a bare `just <recipe>`, `semgrep`, `gitleaks`, `trivy`
or `git grep` as a required command. `just` stays the maintainer's local orchestrator and is
never named by a shipped skill. The repair never relocates a skill's `references/` subfolder or
adds a file that is not the skill's own.

## Tasks

## Block A — the contract rules (Tasks 1–4)

1. [x] <!--t:abf4787afc4d--> **Portable-command rule in `contract.audit_one`** —
   **file** `src/ai_engineering/contract.py` (extend `audit_one`), and a new test
   `tests/test_contract_smells.py`.
   **check**: `uv run --with pytest python -m pytest -q tests/test_contract_smells.py -k portable`
   **rollback**: `git revert <commit>`.
   **done when**: `contract.audit_one` reports a file that names a bare `just <recipe>`,
   `semgrep`, `gitleaks`, `trivy` or `git grep` as a required command, and passes a skill
   that names only an `ai-eng` verb or the output of a tool kept as evidence.

2. [x] <!--t:b96909f5c61b--> **Existence-check rule in `contract.audit_one`** —
   **file**: `src/ai_engineering/contract.py`.
   **check**: `uv run --with pytest python -m pytest -q tests/test_contract_smells.py -k existence`
   **rollback**: `git revert <commit>`.
   **done when**: a skill that references another path (`policy/`, `hooks/`,
   `ai-/references/`, `specs/`) without an existence check and a fail-closed sentence is
   reported, and one that checks is not.

3. [ ] **Forced-output rule in `contract.audit_one`** —
   **file**: `src/ai_engineering/contract.py`.
   **check**: `uv run --with pytest python -m pytest -q tests/test_contract_smells.py -k forced`
   **rollback**: `git revert <commit>`.
   **done when**: a skill whose exit says only "verify" or "the approval is the gate" is
   reported, and one that names a printed artifact or a committed file is not.

4. [ ] **Sourced-statistic rule in `contract.audit_one`** —
   **file**: `src/ai_engineering/contract.py`.
   **check**: `uv run --with pytest python -m pytest -q tests/test_contract_smells.py -k sourced`
   **rollback**: `git revert <commit>`.
   **done when**: a skill that carries a bare numeric statistic with no source reference is
   reported, and one that anchors each number is not.

## Block B — repair the sixteen skill pairs (Task 5)

5. [ ] **Repair every skill's SKILL.md and corpus.md to the four rules** —
   **file**: `.agents/skills/` (all sixteen pairs: `SKILL.md` + `corpus.md`).
   **check**: `uv run --with pytest python -m pytest -q tests/test_contract_smells.py`
   **rollback**: `git revert <commit>`.
   **done when**: `tests/test_contract_smells.py` passes against the live tree — a skill that
   names a bare repo-specific command, a cross-file reference without an existence check, a
   weak exit, or an unsourced statistic is reported, and no shipped `SKILL.md` or `corpus.md`
   triggers one.

## Block C — prove the whole tree reads clean (Task 6)

6. [ ] **The gate reads the repaired tree clean** —
   **file**: `just check` and `tests/test_contract_smells.py`.
   **check**: `uv run --with pytest python -m pytest -q tests/test_contract_smells.py && git status --porcelain -- .agents/skills | grep -q . || true`
   **rollback**: `git revert <commit>`.
   **done when**: the full contract test that exercises all four rules against the twelve
   repaired skills passes, and the doctor's skill-audit line reports no smell violation.