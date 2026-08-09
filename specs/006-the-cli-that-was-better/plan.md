---
id: "006"
slug: the-cli-that-was-better
---

# Plan — the renderer before the glyphs, so nothing is unheld for a commit

## What landed — measured, 2026-08-09

| | predicted | landed |
|---|---|---|
| 1. the two dependencies, and the wall that keeps them out of the guards | +22 | +139 |
| 2. the renderer, with nothing rendering through it yet | +120 | +409 |
| 3. doctor stops printing nine headings for six families | +18 | +52 |
| 4. messaging leaves stdout | +40 | +22 |
| 5a. the install screens are drawn | +55 | +36 |
| 5b. the diagnosis screens are drawn | +45 | +35 |
| 6. the picker | +50 | +94 |
| 7. the banner, the help and the version | +25 | +12 |
| 7b. the tests the mutation floor asked for | — | +176 |
| 8. this table and the ceiling comment | — | +13 |
| **total** | **+375** | **+978** |

`REPO_CEILING` closes at **13,664**, which is 12,686 plus that total, with no slack.

Task 7b was not in the plan and the mutation floor is what put it there. `just mutate`
came out at 86% against 89% — the renderer added 517 mutants and 162 of the survivors
were in `ui.py`. Almost all of them were style names, invisible on the undecorated path
this whole suite drives on purpose, so every element could have lost its colour entirely
with the build green. That is the one thing this spec exists to deliver. 162 down to 66.

The estimate was out by a factor of two rather than spec 005's factor of ten, and the two
places it was wrong are worth naming. Task 1 predicted 22 and landed 139 because `uv.lock`
is a counted file and seven packages arrived in it — the two named and five behind them.
Task 2 predicted 120 and landed 409 because the prediction counted the module and not its
suite, which is exactly the mistake spec 005 closed on and evidently not one that is
learned once. Tasks 4, 5a, 5b and 7 all came in under, for the same reason in each case:
routing an existing string through a renderer deletes the f-string that built it.

Two things happened that were not in the table above and are in the commits.

`Table.grid` was the first survey and was reverted inside the same commit: rich pads the
final column to its own width, so every row ended in invisible whitespace. The widths sit
in one function instead, which was the only thing the table was buying.

`usage()` stopped returning a string in task 7 and one call site was still interpolating
it, which would have printed `None` at anybody who mistyped a verb. The test asserting
stdout is empty on a typo is what caught it.

## The base this was measured from

Committed `HEAD` measures **12,686** against a `REPO_CEILING` of **12,686**: spec 005 closed
it at the count that landed, so the headroom is exactly zero again. This worktree measures
31 lines over, and none of it is this work — it is the operator's in-flight TypeScript lane
and it is named the same way spec 005 named it.

Every figure below is a prediction, marked as one. The closing task replaces the table with
the count that landed, and spec 005's estimate was out by nearly a factor of ten for one
reason — it counted product lines and not the tests that hold them — so these figures carry
the test line with them and are larger than they look.

One ordering is a constraint rather than a preference. **Task 2 lands before any glyph
changes.** The suite holds roughly a hundred exact indented strings, and a renderer that
owns the indent invalidates all of them in one commit; the plain-render mode goes in while
those assertions still describe the current output, so each later commit breaks exactly the
lines it meant to.

One task, one commit.

## 1. The two dependencies, and the wall that keeps them out of the guards

- **file** `pyproject.toml`, `tests/test_contracts.py` · **check** `uv build` succeeds and
  the wheel's metadata names both; a new test walks every file under `hooks/` and fails on
  any import that is not in `sys.stdlib_module_names`, which passes today and is what makes
  the dependency safe to add · **rollback** revert both · **done when** `rich` and
  `questionary` are declared with the same bounds the previous version used, and the rule
  that guards import nothing outside the standard library is an exit code instead of a
  paragraph in `AGENTS.md`. The test is the point of this task; the two lines in
  `pyproject.toml` are the cheap half. **+22.**

## 2. The renderer, with nothing rendering through it yet

- **file** `src/ai_engineering/ui.py`, `tests/test_ui.py`, `tests/conftest.py` · **check**
  a new suite drives every element twice — once with colour forced on and once with
  `NO_COLOR` set — and asserts the styled form carries the escape sequence and the plain
  form is byte-identical to what `init` and `doctor` print today; the existing suites are
  untouched and still green · **rollback** delete the module and the fixture · **done when**
  `ui` owns a stderr console for messaging, a stdout console for data, a theme of named
  styles, and five renderers: a section, a step line, a survey row, a panel and a picker.
  The fixture in `conftest.py` forces the plain path for the whole suite, so no existing
  assertion changes in this commit and every later one changes only what it means to.
  **+120.**

## 3. doctor stops printing nine headers for six families

- **file** `src/ai_engineering/doctor.py`, `tests/test_doctor.py` · **check** a test asserts
  each family name appears exactly once in the output and that the families come in a
  declared order; today `The wiring` appears four times · **rollback** revert · **done when**
  the registry is grouped by family before it is printed. The assertion numbers do not move —
  they are cited in prose across this repository and in the spec files — so the rows inside a
  family are still in numeric order and only the sections are reordered. **+18.**

## 4. Messaging leaves stdout

- **file** `src/ai_engineering/init.py`, `src/ai_engineering/doctor.py`,
  `tests/test_mut_init.py`, `tests/test_doctor.py` · **check** `ai-eng doctor > out.txt`
  leaves the twenty-one assertion lines and the coverage table in the file and every question,
  survey row and panel on the terminal; `ai-eng init -y 2>/dev/null` prints nothing at all ·
  **rollback** revert · **done when** the split is the one the previous version used. This is
  the task that touches the most test lines, because `capsys.readouterr().out` becomes `.err`
  wherever the line was chrome, and the tests say which is which by choosing a stream.
  **+40.**

## 5. The screens are drawn rather than concatenated

- **file** `src/ai_engineering/init.py`, `tests/test_mut_init.py` · **check** the survey, the
  checklist, the step lines and the closing report all come from `ui`, and the whole-screen
  assertions spec 005 added are re-pinned against the new rendering rather than loosened ·
  **rollback** revert · **done when** no f-string in `init.py` contains a tick, an indent or a
  column width. Those two whole-screen assertions are the reason the mutation floor holds at
  89%; loosening them to survive a repaint would trade a gate for a coat of paint, which is
  the exchange this whole product refuses. **+55.**
- **file** `src/ai_engineering/doctor.py`, `tests/test_doctor.py` · **check** the same, for
  the assertion lines, the three states and the coverage table; the coverage table becomes a
  real table and the test compares cells rather than counting spaces · **rollback** revert ·
  **done when** `ok`, `FAIL` and `?` are named styles and the coverage states keep their exact
  words, because `UNPROVEN`, `INERT` and `ADVISES` are vocabulary rather than decoration.
  **+45.**

## 6. The picker

- **file** `src/ai_engineering/ui.py`, `src/ai_engineering/init.py`,
  `tests/test_mut_init.py` · **check** at a terminal, the surface question and the overwrite
  question are checkboxes with the found rows pre-ticked and nothing else; with `-y`, with
  `--harness`, with `--overwrite` and with no terminal, no picker is constructed at all and
  the existing parser answers, which every test written for spec 005 already proves ·
  **rollback** revert the two call sites; the module keeps the renderer · **done when**
  pressing Ctrl-C at either question writes nothing and exits 130, which is the one behaviour
  a widget can get wrong that a typed prompt cannot. **+50.**

## 7. The banner, the help and the version

- **file** `src/ai_engineering/cli.py`, `src/ai_engineering/init.py`, `tests/test_cli.py` ·
  **check** `ai-eng --help` renders the ten verbs as a table with the verb in the brand style,
  and `ai-eng --version` still prints one plain line that a script can read · **rollback**
  revert · **done when** the banner constant lives in `ui` with the rest of the brand and
  `init` stops carrying its own copy. `--version` staying plain is in the check because it is
  the one line here that another program parses. **+25.**

## 8. The close

- **file** `src/ai_engineering/contract.py`, `specs/006-the-cli-that-was-better/plan.md` ·
  **check** `just check` green, `just mutate` at or above 89%, `python tests/adversarial/run.py`
  green, and `contract.repo_lines` equal to the constant · **rollback** revert · **done when**
  the ceiling reads the number that landed and this table is replaced by the measured one.
  Two things this task may not do: leave slack, and pad the suite to reach the mutation floor.
  The floor is the binding gate again — every branch tasks 2, 3, 5 and 6 add is a mutant, and
  a renderer is almost entirely branches over styles and widths.

## The mandatory task classes

This deploys nothing and gives nothing a URL, so the observability task is absent by fact.
The CI/CD task is **not** absent: task 1 adds the first runtime dependencies this wheel has
ever had, and the security lane that scans them — `trivy`, `pip-audit`, `snyk` — must be seen
to fail on a planted advisory before the dependencies are trusted, or the mitigation named in
the accepted risk is itself an unproven claim. That belongs in task 1's commit and its check
is a deliberate red build.

## What this plan is not doing

**No progress bars, spinners or live regions.** None of the ten verbs streams anything slow
enough, and a spinner over an operation that takes 40 ms is a lie about the work.

**No `--json`.** A machine-readable doctor is a schema, a version and a compatibility
promise; it is a different spec and it is not what was asked for.

**Not copying `cli_ui.py`.** It is 613 lines written against `typer`, `pydantic` and thirty
verbs, and it imports a type from a module this tree does not have.

**Not changing a single verdict.** No exit code, no assertion outcome, no file written and no
question asked differently — the three questions stay three. This spec repaints and adds one
input control.
