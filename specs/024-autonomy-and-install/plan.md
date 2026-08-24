---
plan: "024"
spec: "024"
---

# Plan: the autonomy and install wave — atomic execution

## How this runs

One repository writer. Each task is one atomic commit changing one primary production,
policy, documentation or workflow file, plus only its focused supporting test and fixture
files. Rollback for every task and repair is `git revert <commit>`.

Every check named below is an exact future red check: run it with `uv`, using the named
`path::node`. It is red now because the node or file is absent, and becomes green only
after that task. No broad `-k`, placeholder node or invented green result is acceptable.

Implementation follows the criteria in `AGENTS.md`: KISS, DRY, YAGNI, SOLID, TDD (red
first), BDD, Clean Code and Clean Architecture. No extra documents are created for this
work; the record is the spec, this plan, and the research report 006 that feeds both. The
deployable artefact is the wheel, so the CI/CD and observability tasks below are named and
not optional.
**Still requiring separate, explicit consent, and not covered here:** any push, tag,
release, publication, global installation, or network call. No release receipt or
publishing authority is implied by anything in this plan.

## What the spec asks for, in the order the first red check appears

The dependency is the shared-root collision fix already sitting uncommitted in the
working tree (`init.py`, `wiring.py`, `test_mut_init.py`, `test_stranger_install.py`).
The spec says it "must land in its own commit before the automations". So the plan
commits it first, then lands the four decisions, then the deployable lane, then the
record.

## Tasks

1. [x] <!--t:9e898379c07a--> **Land the shared-root collision fix as its own commit** —
   **file** `src/ai_engineering/init.py`, `src/ai_engineering/wiring.py`,
   `tests/test_mut_init.py`, `tests/test_stranger_install.py` (the four already in the
   working tree, unchanged).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_stranger_install.py::test_a_folder_this_install_never_wrote_is_named_and_skipped_and_the_rest_install tests/test_mut_init.py::test_init_can_be_run_twice_on_a_machine_it_already_set_up`
   — red at HEAD (the tests do not exist at HEAD; they are part of this working-tree
   diff), green after the commit. The check asserts two things the spec's wave depends
   on: a foreign folder in a shared skills root is *named and skipped*, not a machine
   refusal, and a second `init` on a machine it set up still reads ready.
   **rollback**: `git revert <commit>`.
   **done when**: one commit lands the name-and-skip collision behavior with both tests
   green; nothing in the diff changes any other line of `init.py`/`wiring.py`.

2. [x] <!--t:2080e8c8180a--> **D-024-03: measurable catalogue budget** —
   **file**: `src/ai_engineering/contract.py`, `tests/test_contracts.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py::test_the_catalogue_fits_the_smallest_documented_budget`
   — red now (no such test, no `CATALOG_MAX`), green after `contract.py` gains a
   `CATALOG_MAX` constant and `audit` sums every `ai-*` skill's `name + description`
   and fails over the budget, naming the catalogue budget and the culprit.
   **rollback**: `git revert <commit>`.
   **done when**: `just check` passes and the new test asserts the shipped sixteen-skill
   catalogue stays under 50 000 characters and refuses a synthetic seventeenth skill
   over the budget by naming the budget and the culprit, without touching
   `DESCRIPTION_MAX = 1000` or `SPEC_FIELDS`.

3. [x] <!--t:3a15ba446449--> **D-024-02: `init` becomes context-aware** —
   **file**: `src/ai_engineering/init.py`, `tests/test_stranger_install.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_stranger_install.py::test_bare_init_inside_a_repo_offers_the_project_step tests/test_stranger_install.py::test_bare_init_outside_a_repo_does_global_only tests/test_stranger_install.py::test_bare_init_dash_y_in_a_repo_stays_global_only`
   — red now (no such tests), green after `main` offers the project half when the
   working directory is inside a repository and a person is answering, and keeps
   global-only when `-y`, piped, non-interactive or `--no-project`.
   **rollback**: `git revert <commit>`.
   **done when**: the three behaviors the spec's examples name are pinned by tests:
   inside a repo with a person answering it asks "Set up this project too?"; outside a
   repo it does global only; `-y` inside a repo stays global-only. The interactive
   offer largely exists today via `project_step`'s ask (line 601); this task pins it and
   fixes whatever the red test finds (the likely gap is the non-interactive path, which
   must not silently take the project half).

4. [x] <!--t:2f2a47ff7a69--> **D-024-01: opt-in `--hooks-template` flag and wiring, with the template**
   **file**: `src/ai_engineering/init.py`, `src/ai_engineering/wiring.py`,
   `tests/test_stranger_install.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_stranger_install.py::test_hooks_template_writes_the_template_and_never_a_global_hooks_path tests/test_stranger_install.py::test_hooks_template_dry_run_writes_nothing`
   — red now (flag and tests absent); the write side and the dry-run side are each pinned
   by a test.
   **rollback**: `git revert <commit>`.
   **done when**: the flag exists; the template dir holds exactly the three shipped
   hooks; git init.templateDir at global scope points at it; and the safe property is
   asserted — the hooks are the existing files, which already exit 0 on a repository
   that has never set ai.managed (verified: commit-msg line 5, pre-commit line 23,
   pre-push line 20). A global core.hooksPath is never written — that refusal is pinned
   by a test, because it is the whole D-024-01 safety claim.

5. [x] <!--t:f0b0a8e0b8b6--> **D-024-01: uninstall parity** —
   **file**: `src/ai_engineering/uninstall.py`, `tests/test_stranger_install.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_stranger_install.py::test_uninstall_removes_the_hooks_template_and_global_key`
   — red now, green after `uninstall` removes the template dir and the global
   `init.templateDir` key, and only when the current global value is the one the receipt
   records (a person's own template dir is never removed).
   **rollback**: `git revert <commit>`.
   **done when**: uninstall removes both, only the receipt row drives its removal, a
   foreign template value is left alone, and `uninstall` still reports one line per row.

6. [x] <!--t:fd3c0c4f0776--> **CI/CD: the install matrix gains a templateDir row per platform** —
   **file**: `.github/workflows/install-matrix.yml`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_quality_gate.py::test_install_matrix_executes_the_hooks_template_on_every_supported_os`
   — red now (no such test); the matrix's per-platform native-controls section runs the
   template install from the installed wheel across all three runners.
   **rollback**: `git revert <commit>`.
   **done when**: the new row runs on Linux, macOS and Windows with no skip, and the
   existing test_install_matrix_executes controls still pass in the same job.

7. [x] <!--t:dc611b09bf11--> **Observability: doctor gains one assertion for the template state** —
   **file**: `src/ai_engineering/doctor.py`, `tests/test_doctor.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_doctor.py::test_doctor_asserts_the_hooks_template_is_owned_and_removable`
   — red now (no such assertion); the assertion reads the receipt rows and reports the
   template dir ok when the row and the dir match, and names a cure when they disagree.
   **rollback**: `git revert <commit>`.
   **done when**: ai-eng doctor states the template state in its output, and ai-eng
   report digest covers the new runs by the existing ALWAYS_WRITES event rule — no
   new event schema needed because every verb already records one command event per
   run.

8. [x] <!--t:694a9354e51c--> **D-024-04: English in the record** —
   **file**: `docs/tools.md` (translated), `src/ai_engineering/solution_intent.py`
   (English labels — see note), regenerated `docs/solution-intent.html`.
   **check**: `grep -rn "Guía rápida\|escribe\|solución" docs/tools.md docs/solution-intent.html`
   returns nothing, and `uv run python -m ai_engineering.solution_intent --check` passes
   — red now (the Spanish strings are there), green after the translation and
   regeneration. The test `tests/test_quality_gate.py::test_no_spanish_in_docs` pins
   the grep as a gate.
   **rollback**: `git revert <commit>`.
   **done when**: `docs/tools.md` is English, `docs/solution-intent.html` regenerates
   English from `ai-eng report intent --html`, and `just check`'s `intent-page` recipe
   (`uv run python -m ai_engineering.solution_intent --check`) is green. Reports 001-005
   under `.ai/reports/` stay as they are: preserved history, not rewritten.

## What is deliberately not being done, and why

- **The PII lane and per-stack SAST rule sets are deferred to P4 (D-024-05).** They are
  already normative there in spec 010's `### P4 — security and release evidence`. No task
  in this plan implements a scanner or a rule set; the deferral is a scheduling decision
  the spec records, not a ceremony this plan repeats.
- **The supply-chain verifier (`EP-047` / `EP-280`) is not planned.** It needs a
  published release and network access to fetch it; no local task can close it. It stays
  open, named in `policy/threat-model.toml`.
- **Reports 001-005 under `.ai/reports/` stay Spanish.** They are dated snapshots of prior
  states; the constitution's rule against rewriting history applies. The translation
  covers `docs/tools.md` and the generated page, not the archives [spec D-024-04].
- **No new CLI verb.** Every verb change costs a capability row and a will-table row; the
  four automations the wave lands all live inside the existing `init` verb, which already
  declares `git config` among its writes in `cli.py`.
- **The working-tree collision fix is committed, not re-planned.** It was written in the
  same territory the wave owns and its tests were part of it; this plan only makes it
  atomic (task 1), it does not redesign it.

## Notes that came out of planning and must not be lost

- **D-024-02 is partly true already.** `project_step` (init.py line 601) already asks
  "Set up this project too?" when the working directory is a repository and a person is
  at the keyboard. Task 3 pins the spec's three promised behaviors that are not all true
  today — the non-interactive path and the `-y` path — with tests. This is a correction
  to the spec's "Context" sentence, not to its Decision; the spec's own BDD examples are
  the exact behaviors the tests will pin.
- **The hooks already pass cleanly on a never-opted-in repo.** The template hook files
  are the shipped hooks, and pre-commit/commit-msg/pre-push all exit 0 when
  `ai.managed` is unset. Task 4's safety property is therefore inherited from existing
  code and asserted, not written new.
- **The install matrix already exercises `doctor` per platform** (the "zero to a green
  doctor" step). Task 6 extends it with the template row; it does not add a new job.

## Done when

- Every task has one file, one failing check that goes green, a rollback and a testable
  "done when" — above.
- The four automation tasks (2, 3, 4, 5) and the deployable lane (6, 7) land, each as
  its own commit.
- The CI/CD and observability tasks (6, 7) are in the plan because the wheel is the
  deployable surface; they are not optional.