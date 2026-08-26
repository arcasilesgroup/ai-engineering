# Plan: context economy and skill authoring — 033 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**, recorded at their digests in their own record. One repository writer, on a
branch carrying the whole 033 change. Each task is one atomic commit touching one primary
production, policy or skill file plus only the files that task names. Rollback for every task
is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the whole gate in the same
chain as the commit itself. `ai-eng spec show 033 --task <n>` refuses any task whose digests
have moved.

## The order, and why

Tools before rules: the trimmer (B-033-1) and the extractor (B-033-2) are modules with
tests; the dispatcher shape (B-033-3) is a contract rule over skills; the installed-version
rule (B-033-4) is a module plus corpus routes. Then the corpus routes and any skill repair,
then the gate. Each task starts with its red fixture, exactly as specs 028-032 did.

## What this plan is not doing, and why

- **No change to `.ai/intent.md`, `CONSTITUTION.md`, or the one-writer rule.**
- **No new skill.** The four behaviours are modules, one contract rule and corpus routes;
  the fifteen-skill target is unchanged.
- **No acceptance of ADR 0025 / no history rewrite of spec 026.** The inherited
  `madr.validate` red is recorded, not fixed here; the final task asserts no new MADR
  failure.
- **No change to `justfile`/`test_quality_gate.py`** — those carry the repository owner's
  uncommitted work; the new suites are picked up by the existing `test` recipe with no
  wiring.
- **No CI/CD box ticked.** Adds no service, endpoint or URL.

## The boundary this plan may not cross

The trimmer never elides a failure marker and is deterministic. `skillify` emits a skeleton
that passes `contract.audit_one` (including the spec 032 craft rules) and names steps, never
chat. The dispatcher craft rule fires only when branches are present *and* the body is over
the tier bound it should have split — a clean dispatcher passes, and no skill is forced to
invent branches. `verify_against_installed` reads the installed distribution via
`importlib.metadata`; an unresolvable package is `unverified`, never a guess.

## Tasks

## Block A — modules (Tasks 1-4)

1. **Red fixture: trimmer keeps failure lines and marks the elision** —
   **file** `tests/test_trim.py` (new): a 200-line output with a failure marker in the
   middle; the marker survives, head/tail kept, the middle marked.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_trim.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before `src/ai_engineering/` ships the trimmer, and
   green after — deterministic, failure line never elided.

2. **Trimmer module** —
   **file** `src/ai_engineering/trim.py` (new, stdlib-only: `trim_output(text,
   max_lines=80)`, keeps head and tail, marks `… N lines elided …`, never elides a line
   containing a failure marker), plus the green half of `tests/test_trim.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_trim.py`
   **rollback**: `git revert <commit>`.
   **done when**: `trim_output` is deterministic, keeps failure lines, and marks elision.

3. **Red fixture: skillify emits a contract-clean skeleton, never chat** —
   **file** `tests/test_skillify.py` (new): a transcript of a costly one-off procedure; the
   skeleton passes `contract.audit_one` and names steps, not the chat.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_skillify.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before `skillify.py` ships, and green after.

4. **Skillify module** —
   **file** `src/ai_engineering/skillify.py` (new, stdlib-only: `extract(transcript)` →
   a SKILL.md skeleton with name/description/craft sections/Procedure derived from the
   generalisable steps, corrections as Rules; a transcript with no generalisable steps
   emits None), plus the green half of `tests/test_skillify.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_skillify.py`
   **rollback**: `git revert <commit>`.
   **done when**: `extract` produces a contract-clean skeleton from a real transcript and
   None from a chat with no process.

## Block B — rules and routes (Tasks 5-6)

5. **Dispatcher craft rule + installed-version module** —
   **file** `src/ai_engineering/contract.py` (add `_dispatcher_problems`: branches present
   and body over the tier bound → refused for not splitting into examples/references),
   `src/ai_engineering/versions.py` (new: `verify_against_installed(package, claim)` via
   `importlib.metadata` → match/mismatch/unverified), and `tests/test_dispatcher_craft.py`
   + `tests/test_versions.py` (both new, red-then-green).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_dispatcher_craft.py tests/test_versions.py`
   **rollback**: `git revert <commit>`.
   **done when**: the dispatcher rule refuses a branch-bloated body and passes a clean
   dispatcher; `verify_against_installed` returns match/mismatch/unverified correctly.

6. **Corpus routes for trim, skillify and installed-version** —
   **file** `.agents/skills/ai-note/corpus.md` (routes: "keep the note small — trim the
   log", "turn this session into a skill"), `.agents/skills/ai-review/corpus.md` and
   `.agents/skills/ai-security/corpus.md` (rule: a finding contradicting the installed
   version is dropped or unverified), plus `uv run python tests/skill_eval.py`.
   **check**: `uv run python tests/skill_eval.py && uv run --with pytest==9.1.1 pytest -q tests/test_dispatcher_craft.py tests/test_versions.py`
   **rollback**: `git revert <commit>`.
   **done when**: the corpus routes the trim/skillify/installed-version cases with no fork,
   and the skill-routing baseline moves only with the measured reason.

## Block C — prove the gate (Task 7)

7. **The full gate reads the four behaviours green with their clean controls** —
   **file** none (verification).
   **check**: `just check`
   **rollback**: `git revert <commit>`.
   **done when**: `just check` exits 0, the trim/skillify/dispatcher/versions suites pass
   with their clean controls, `tests/test_madr.py` reports exactly the same pre-existing
   failures as before this block (the ADR 0025 inherited red) — no fifth failure
   introduced; the spec, plan and approval of 033 are committed at their exact digests.