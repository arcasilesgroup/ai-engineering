# Plan — close the list, move the ceiling once, then push

Ordered so that no commit leaves the gate red for the next one. The ceiling raise is its own
commit and comes before every task that adds a line, which is all of them but the first.

## 1. The two verbs that crashed instead of reporting

- **file** `src/ai_engineering/audit.py`, `src/ai_engineering/spec.py`,
  `src/ai_engineering/doctor.py`, `tests/test_record.py`, `tests/test_doctor.py` ·
  **check** `pytest tests/test_record.py tests/test_doctor.py`, and both strict xfail markers
  gone · **rollback** `git revert` · **done when** `audit.read` carries an unparseable line as
  an event-shaped marker instead of raising, `verify` names that link, `doctor.chain_intact`
  reads through the same function so it can no longer walk a cut chain and call it intact, and
  `spec.next_number` ignores a folder under `specs/` whose first chunk is not a number.
- **cost** net zero. The two guards are shorter than the xfail markers they retire.

## 2. The ceiling

- **file** `src/ai_engineering/contract.py` · **check**
  `pytest tests/test_contracts.py::test_the_line_ceiling_holds` · **rollback** `git revert`
  · **done when** `REPO_CEILING` reads 16,991 and the commit message carries the arithmetic
  in the decision block of the spec. Raising it is the operator's call and the number is
  measured, not estimated: `contract.repo_lines` over the staged tree.

## 3. The prose that had gone false

- **file** `README.md`, `AGENTS.md`, `CONSTITUTION.md`, `CHANGELOG.md`,
  `src/ai_engineering/init.py`, `tests/test_mut_init.py` · **check**
  `pytest tests/test_contracts.py tests/test_mut_init.py` · **rollback** `git revert` ·
  **done when** the README stops saying `init` prints a file it writes, "eight guards" is
  "five guards" in both files, the constitution names the suite instead of a §11 that does
  not exist, `## Unreleased` is `## 1.0.0 — 2026-08-10`, and no sentence anywhere describes
  `docs/tools.md` as something it is not.

## 4. The guard count, pinned

- **file** `tests/test_contracts.py` · **check**
  `pytest tests/test_contracts.py::test_the_counts_this_repository_states_about_itself_are_the_counts_it_has`
  · **rollback** `git revert` · **done when** `COUNTED` carries three guard rows and the left
  side is derived from `chain.TABLE` minus `chain.TELEMETRY` — the table the dispatcher
  actually executes, so a guard module with no row cannot satisfy it.

## 5. `doctor --fix` stops typing a person's answer

- **file** `src/ai_engineering/doctor.py`, `tests/test_doctor.py` · **check**
  `pytest tests/test_doctor.py` · **rollback** `git revert` · **done when** `unattended()`
  decides which cures `--fix` may run, assertion 12's cure is printed and not run, and the
  panel's "fixable now" count is the same set `--fix` executes.

## 6. `just changed` stops dropping half the suite in silence

- **file** `justfile` · **check** `just changed` after touching `tests/test_install.py`
  lists `uninstall.py` and `update.py` · **rollback** `git revert` · **done when** the
  modules come from the file's own imports rather than from its name, and a suite that names
  none of ours says so on stderr instead of vanishing into "nothing you touched has mutants".

## 7. The buffer stamp

- **file** `hooks/_emit.py`, `src/ai_engineering/audit.py`, `tests/test_hooks.py` ·
  **check** `pytest tests/test_hooks.py`, the third strict xfail gone · **rollback**
  `git revert`, and delete `~/.ai-engineering/buffer.key` · **done when** an edited buffer
  line is sealed as the error that says so with what it claimed kept beside it, and
  `ai-eng audit verify` names that link and exits 1. Its bound is R-009-01.

## 8. The Unicode fold

- **file** `hooks/injection_guard.py`, `policy/iocs.yml`, `tests/test_contracts.py` ·
  **check** `pytest tests/test_contracts.py -k "catalogue or precision"` · **rollback**
  `git revert` · **done when** text is NFKD-folded to ASCII before it is matched and the
  recall measurement R-001-04 asked for is an equality assertion over twelve variants, not a
  printout. No catalogue entry is broadened; the follow-up forbids it and it would make a
  precise guard a false-positive machine.

## 9. Backups stop landing in the user's first commit

- **file** `src/ai_engineering/init.py`, `tests/test_mut_init.py`, `tests/test_install.py` ·
  **check** `pytest tests/test_install.py -k backup` · **rollback** `git revert` ·
  **done when** `init.backup` writes under `.ai/backups/`, which the managed `.ai/.gitignore`
  already covers, and nothing matching `*.bak-*` is left at the repository root. This closes
  R-005-16 by taking the first of the two ways out its follow-up named.

## 10. The install matrix exercises what four risk acceptances said it did not

- **file** `.github/workflows/install-matrix.yml` · **check** the workflow parses, and the
  first CI run on this branch · **rollback** `git revert` · **done when** the matrix
  pre-creates the skills root so `wiring.link` copies rather than symlinks on every platform,
  asserts the closing report and the gitleaks notice, runs `ai-eng doctor --fix` against a
  settings file it deleted, and asserts after `uninstall` that the copies and the guard entry
  are gone rather than only that `specs/` survived.

## 11. The payload dialects, end to end

- **file** `tests/adversarial/run.py` · **check** `python tests/adversarial/run.py`, 14 of
  14 · **rollback** `git revert` · **done when** one attack goes through the real spawned
  dispatcher as snake_case, as camelCase and as the bare `tool`/`input` spelling, and all
  three are denied. This closes R-003-03's first half; the second half is a surface flipping
  to proven, which no test can do.

## 12. The record

- **file** `specs/003`, `specs/004`, `specs/005`, `specs/008`, `specs/009`, `docs/adr/0004`
  · **check** `ai-eng doctor` assertion 19 green with spec 004 shipped, and
  `ai-eng decide --list` naming 0004 · **rollback** `git revert` · **done when** the refusal
  is an ADR, spec 004 is shipped with eight boxes that each name a command or say why the
  box does not apply, R-008-01 states the gap that is real instead of one the tree
  contradicts, and R-003-03 and R-005-16 are closed with the check that closed them.
- **cost** zero counted lines. `specs/` and `docs/adr/` are outside `repo_lines`.

## 13. Push, and read the first CI

- **check** the run on `origin/v1`: `check`, `install-smoke` and every leg of the matrix
  · **rollback** nothing to roll back; a red run is the output rule 6 asks for either way ·
  **done when** the branch is on `origin` and the result has been read rather than assumed.
  This is the step that turns the rest of this plan from a prediction into an observation,
  and R-009-02 is open until it has run. Completed at `bece5b4a`: install run 31415890269
  and check run 31415890187 both read `success`, and R-009-02 is closed at those runs.

## 13a. Treat the receipt as evidence, never authority

- **files** `src/ai_engineering/init.py`, `src/ai_engineering/uninstall.py`,
  `tests/test_install.py`, `src/ai_engineering/contract.py` · **check**
  `pytest tests/test_install.py -k 'tampered_receipt or control_data'` and
  `just mutate src/ai_engineering/init.py src/ai_engineering/uninstall.py` · **rollback**
  `git revert` · **done when** every destination used for deletion is reconstructed from
  the surface table, the installer's finite project set or the selected repository; a
  second valid row cannot smuggle a forged kept row into the unwire loop; and the prior
  hooks path reaches `git config` only after a printable length bound and an explicit
  option terminator. This is the real trust-boundary defect behind five findings from the
  first Sonar run; the three content-written-to-a-trusted-path findings are call-shape
  false positives and are removed in the next change rather than hidden.
- **cost** 158 counted lines: 68 product, 84 tests and the six-line ceiling record;
  17,588 to 17,746, with no slack.

## 13b. Separate document content from its trusted destination

- **files** `src/ai_engineering/wiring.py`, `src/ai_engineering/accept.py`,
  `src/ai_engineering/decide.py`, `src/ai_engineering/contract.py` · **check**
  `pytest tests/test_mut_wiring.py tests/test_mut_spec.py` and the next Sonar job ·
  **rollback** `git revert` · **done when** the three flows no longer hand document content
  to a path method: each trusted path is opened first and the existing bytes are written to
  its handle, with no suppression and no behaviour change.
- **cost** eight counted lines: three product and the five-line ceiling record; 17,746 to
  17,754, with no slack.

## 13c. Read the assigned Quality Gate through SonarCloud's current API

- **files** `tests/quality_gate.py`, `tests/test_quality_gate.py`,
  `src/ai_engineering/contract.py` · **check** `pytest tests/test_quality_gate.py` and the
  next Sonar job · **rollback** `git revert` · **done when** the reader sends both project
  and organization to `get_by_project`, takes the returned gate id to `show`, and compares
  the conditions from that second response. HTTP 400 remains undecided and red; it is not
  converted into a pass.
- **cost** 56 counted lines: 24 script, 27 test and the five-line ceiling record; 17,754 to
  17,810, with no slack.

## 14. Make it `main`

- **check** `git merge-base main v1` exits 1, so this is a replacement and not a merge; the
  old history stays reachable by tag · **rollback** the tag · **done when** the operator has
  authorised it, after a green run and not before. It is the one step here that no
  `git revert` undoes.

## What this plan is not doing

- Writing `run.py --live-claude`. The reason is in the spec's decisions and under R-003-05.
- Flipping any surface from UNPROVEN to proven. A surface flips when a denial executes there
  and not when a test spawns a dispatcher.
- Adding `extractions/*` to this repository's Actions allowlist. That is the other way to
  make `check` start and it is the operator's to make, not a commit's. Getting `just` from
  PyPI needs nobody's settings and works in every fork.
