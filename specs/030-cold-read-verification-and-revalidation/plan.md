# Plan: cold-read verification, coverage rules and revalidation — 030 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**, recorded at their digests in their own record. One repository writer, on a
branch carrying the whole 030 change. Each task is one atomic commit touching one primary
production, policy or skill file plus only the files that task names. Rollback for every task
is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the whole gate in the same
chain as the commit itself. `ai-eng spec show 030 --task <n>` refuses any task whose digests
have moved.

## The order, and why

Coverage rules first (B-030-2), because both the cold-read verifier and revalidation read
from them — a verifier that derives its scope from prose is prose-backed, not data-backed,
and a revalidate that cannot name the guard's coverage cannot tell whether the fix removed
the trigger. Then the cold-read verifier (B-030-1), which applies the answer key (spec 029)
with `--recheck`. Then revalidation (B-030-3), which re-runs the coverage the first two
establish, at finding granularity. The final task proves the whole gate plus the evals
harness's coverage contract, with clean controls for each new behaviour.

Each task starts with its **red fixture** — the test that fails before the behaviour exists —
implemented in the same commit, exactly as spec 029's blocks did.

## What this plan is not doing, and why

- **No change to `.ai/intent.md`, `CONSTITUTION.md`, or the one-writer rule.** The three
  behaviours extend the *target*, not the authority model.
- **No acceptance of ADR 0025 / no history rewrite of spec 026.** The inherited
  `madr.validate` red is recorded, not fixed here; the final task asserts no new MADR
  failure.
- **No new CLI verb.** Revalidation is a `--revalidate <finding-id>` flag on the existing
  `audit`/`verify` surface; coverage is policy data; the ten verbs stay closed.
- **No third-party dependency.** The cold-read verifier and revalidator are standard-library
  deterministic readers; `claude -p` or a scanner plugin is explicitly refused (portable
  command rule).
- **No CI/CD box ticked.** Adds no service, endpoint or URL.

## The boundary this plan may not cross

The coverage rules live in `policy/coverage/*.toml`, read by the guards at run time; a
guard scanning outside its declared roots is `INCOMPLETE`, never silently widened. The
cold-read verifier has read-only filesystem access by construction and never receives the
constructor's reasoning. Revalidation marks `fixed` only when the diff removed the trigger
against the guard's coverage; a touched file that keeps the trigger is `INCOMPLETE`.

## Tasks

## Block A — coverage rules (B-030-2)

1. **Red fixture: a guard scanning outside its coverage file is refused** —
   **file** `tests/test_coverage_rules.py` (new): stage a coverage file with roots, a guard
   that reads inside them (allowed) and one that reads outside (must be `INCOMPLETE`).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_coverage_rules.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before `src/ai_engineering/` ships the reader, and
   green after — a rule escaping the declared roots is `INCOMPLETE`, never a pass.

2. **Coverage reader in the product** —
   **file** `src/ai_engineering/coverage.py` (new, stdlib-only: reads `policy/coverage/*.toml`,
   validates the declared roots are inside the repository, exposes `may_scan(path)`),
   plus the green half of `tests/test_coverage_rules.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_coverage_rules.py`
   **rollback**: `git revert <commit>`.
   **done when**: `coverage.may_scan` returns the declared roots exactly, refuses roots that
   escape the repository, and a guard outside them is refused by the fixture.

3. **Wire coverage into the evals harness reporters** —
   **file** `tests/evals/packs/ai-security/pack.toml` (add a `coverage` table with roots),
   `tests/test_evals_harness.py` (a reporter reading outside its declared roots is refused).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_evals_harness.py -k coverage`
   **rollback**: `git revert <commit>`.
   **done when**: the ai-security pack declares its roots, and the harness refuses a pack
   whose `scan.py` reads outside them (the fail-closed lane, B-029-1's clean control kept).

## Block B — cold-read verifier (B-030-1)

4. **Red fixture: cold-read verifier with write access or the constructor's reasoning is refused** —
   **file** `tests/test_cold_read.py` (new): stage a spec + answer key + delivered file; a
   verifier with read-only access (allowed) and one with write access or the builder's
   reasoning (must be refused).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_cold_read.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before the runner ships, and green after — an
   uncertain check is a fail, and a verifier that can edit what it judges is refused.

5. **`verify_cold` runner in the product** —
   **file** `src/ai_engineering/verify_cold.py` (new, stdlib-only: walks the named files
   read-only, applies the answer key with `--recheck` via `evidencing`, reports
   PASS/FAIL/`BLOCKED: U<n>`), plus the green half of `tests/test_cold_read.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_cold_read.py`
   **rollback**: `git revert <commit>`.
   **done when**: `verify_cold` returns the observed verdict from the answer key, refuses
   write access by construction, and reports `BLOCKED: U<n>` for an unknown observable.

6. **Cold-read route in the ai-verify corpus** —
   **file** `.agents/skills/ai-verify/corpus.md` (route: "verify this cold" — read-only,
   never the constructor's reasoning; refusal: "review it warm" → use `/ai-review`).
   **check**: `uv run python tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: the corpus routes the cold-read case with no fork against the answer-key
   route (spec 029), and the skill-routing baseline moves only with the measured reason.

## Block C — revalidation (B-030-3)

7. **Red fixture: a touched-but-unfixed finding is INCOMPLETE, never silently fixed** —
   **file** `tests/test_revalidate.py` (new): stage a finding, a diff that removed its
   trigger (fixed) and a diff that touched the file but kept the trigger (must be
   `INCOMPLETE`).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_revalidate.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before the revalidator ships, and green after.

8. **Revalidator in the product** —
   **file** `src/ai_engineering/revalidate.py` (new, stdlib-only: given the guard's coverage
   and the diff, marks a finding `fixed` only when the trigger is gone), wired into
   `src/ai_engineering/audit.py` as `--revalidate <finding-id>`, plus the green half of
   `tests/test_revalidate.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_revalidate.py`
   **rollback**: `git revert <commit>`.
   **done when**: `--revalidate` marks `fixed` exactly when the diff removed the trigger,
   returns `INCOMPLETE` for a touched-but-unfixed file, and writes a check-evidence receipt.

## Block E — prove the gate

9. **The full gate reads the three controls green with their clean controls** —
   **file** none (verification).
   **check**: `just check`
   **rollback**: `git revert <commit>`.
   **done when**: `just check` exits 0, the coverage/cold-read/revalidate suites pass with
   their clean controls, the evals harness's coverage contract refuses an out-of-roots
   reporter, and `tests/test_madr.py` reports exactly the same pre-existing failures as
   before this block (the ADR 0025 inherited red) — no fifth failure introduced.