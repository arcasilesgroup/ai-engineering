---
id: "007"
slug: the-install-a-stranger-can-follow
---

# Plan — the cure before the colour, so no screen is redrawn twice

Six screens, in the order that puts the mechanism before the presentation of it. The
banner first because it is self-contained and the smallest thing that is simply wrong.
Then `doctor`, which is where the mechanism lives — a cure is a field, not a sentence —
and only afterwards the two blocks that read it.

## What landed — measured, 2026-08-09

Per file, `git diff --numstat` against the branch point, so the rows add up to the total
rather than to an estimate of who deserved what:

| | landed |
|---|---|
| `doctor.py` — cures, the verdict, `--fix`, the coverage block | +147 |
| `init.py` — the workflow as a file, the machine block, where to go | +61 |
| `skeletons.py` — the stack-aware justfile | +46 |
| `ui.py` — the banner arithmetic, and three new renderers | +53 |
| `contract.py` — the ceiling and this raise | +20 |
| the five test files | +552 |
| **total** | **+879** |

`REPO_CEILING` moves from **13,671** to **14,590**. The arithmetic: 13,671 + 31 + 879 + 9.
The 31 is spec 003's uncommitted work, which was already in the tree when this started and
is not this spec's to carry or to hide. The 879 is measured above. The 9 is the ceiling
comment itself, written after the number is chosen and otherwise needing a second raise to
describe the first one.

The test half is five times the product half, and where it came from is the part worth
keeping. 106 lines were planned. The package sat at 88% against a mutation floor of 89
before any of this was written; the six screens took it to 87% by adding 311 mutants and
killing 231 of them, and three scoped rounds over the four changed modules took the
survivors from 80 to single figures — 358 lines. An adversarial review of the finished
branch found the last 88, and two of the things it found were defects rather than gaps.
The survivors were the same defect in five costumes:

- **A style name is invisible.** The suite reads the undecorated stream on purpose, so
  every colour in three new renderers and four new screens could be deleted with the whole
  thing green. Killed with decorated assertions, which is what spec 006 also ended up
  paying for and did not write down as a rule. It is one now: a renderer without a
  decorated test has no test.
- **A stream flag is invisible the same way.** `data=False` moves a line from stdout to
  stderr and nothing noticed. One assertion covers all thirty of them: in this verb every
  line is the report, so `err == ""`.
- **Three assertions compared a module with itself.** `*doctor.OPEN`, a loop over
  `RECIPES`, a loop over `TODOS`. Both sides move together and the sentence can be emptied.
- **`"FAILED" in out` passes on `XXFAILEDXX`.** Substring assertions on a title are not
  assertions on a title.
- **Two branches nothing drove**, and one of them was a defect rather than a gap: a stack
  we cannot name sitting beside one we can printed `# Filled in for: cobol, python` over a
  file carrying only python's commands.

## What the review found that the mutation floor could not

Both of these are the same kind of defect, and neither is visible to a mutant: the code did
exactly what it was written to do.

- **The last screen argued with itself.** Its first row counts the guard entries placed on
  this machine and its third step said "the guards are already loaded there". Under
  `--no-global` those are `0 guard entries` and a promise, two lines apart. The step now
  takes the count and says `run \`ai-eng init --global\`` when there is nothing there yet.
- **`--fix` reached `init`'s rewrite of the pin.** `ai-eng init --project` rewrote
  `.ai/config.toml` on every run — taking a dated backup and printing a line, which spec
  005 decided was enough — and that resets the pinned version, the guard windows and the
  observability endpoint somebody's alerts point at. Reachable only by typing the command,
  that is a footgun; reachable from `doctor --fix`, it is `ai-eng update` with its
  dirty-tree refusal, its keyboard and its typed `y` all removed, which is precisely and
  literally the objection ADR 0002 raised and ADR 0003 claims does not apply here.

  The fix is the rule, not the caller: **`init` writes the pin when it is absent and never
  rewrites it.** `ai-eng update` is the verb that changes governance, and it keeps its three
  gates. This reverses spec 005's decision to back it up and rewrite it, and a re-run now
  says the file was already there and was left alone.

## Tasks

- [ ] **T-1 The banner encloses its own wordmark.** `ui.banner` computes the frame width
  from the longest of the two lines inside it instead of carrying it as literal spaces.
  Check: `test_the_banner_frame_encloses_what_it_frames` — the frame's right edge equals
  the widest content line's, and it is derived, so a version number that grows a digit
  moves the frame with it. Rollback: restore the four literals.

- [ ] **T-2 A cure is a field.** `doctor.FIXES` maps an assertion number to the command
  that repairs it; a check that can fail two ways returns its own `(problem, cure)` pair
  and beats the number's default. The cure prose comes out of the four messages that
  carried it, because two homes for one fact is how the message and the flag come to
  disagree. `ui.cure` prints `fix: <command>` or the sentence saying a person does this
  one. Check: `test_every_failure_a_command_can_repair_names_that_command`, which now
  asserts the field and asserts the prose no longer names a command. Rollback: delete
  `FIXES` and `resolve`; the messages keep working, they just stop being actionable.

- [ ] **T-3 `--fix`, and the verdict that sends you to it.** `doctor --fix` runs the
  distinct cures in this process through `cli.main`, then re-runs itself without the flag
  and prints the new verdict. `ui.summary` frames the count, how many are one command
  away and which assertions are on a person. The `?` rows are gathered under the coverage
  block with their reasons and the sentence that says they are not passes. Check:
  `test_the_report_prints_one_line_per_state_and_hands_every_check_the_repository`.
  Rollback: drop the flag; `repair` is the only function that writes.

- [ ] **T-4 The coverage block explains its own vocabulary.** Two legend lines above it,
  the verdict word in a column of its own, and the reason in the column after — including
  the two UNPROVEN rows that were one word for opposite situations. The closing sentence
  becomes `doctor.OPEN`, three lines that say what none of the rows covers. Check:
  `test_the_coverage_line_says_exactly_what_each_surface_does_on_this_machine`, still one
  hand-written row per surface. Rollback: restore the single state string per row.

- [ ] **T-5 The install writes what the install needs.** `.github/workflows/check.yml`
  joins `OFFERS`, so it is written when absent and goes through the same picker and the
  same dated backup when it is not. `skeletons.justfile(stacks)` fills `lint`, `test` and
  `build` from `RECIPES` for every stack detected, and leaves the TODO for any it cannot
  name. `stacks()` asks the directory rather than a path, so `*.csproj` and `*.sln` find
  .NET with no branch. `init --no-project` is added: `--no-global` existed and its
  opposite did not, and `doctor --fix` needs to rewire a machine without also deciding to
  set up whatever repository the person is standing in. Check:
  `test_the_ci_workflow_is_written_rather_than_pasted_and_nothing_goes_to_stdout` and
  `test_the_shipped_check_recipe_runs_every_recipe_that_ships_with_it`, driven over no
  stack, one and all of them. Rollback: remove the two `OFFERS` rows.

- [ ] **T-6 Where to go, and what was left behind.** The last screen's third step names
  the surfaces this machine actually has, read from the wiring table and capped at two so
  it cannot wrap. The `Global ready` sentence becomes four counted rows through
  `ui.facts`. Check: `test_the_step_that_says_where_to_go_names_the_surfaces_this_machine_has`
  and `test_an_already_wired_machine_gets_the_block_it_left_behind_and_no_survey`, whose
  fixture is a machine with two links, one guard and no skills directory — a summary that
  is only right on a healthy machine hides the unhealthy one.

- [ ] **T-7 The gate.** `just check` and `python tests/adversarial/run.py`, output shown.
  `just mutate` measured and reported whether or not it moved.

## What this does not do

The `counts:` recipe keeps its `RAN lint=TODO` markers in every language. The number has
to come from the tool that did the work, and there is no cross-language way to ask for it
that is not a guess — a guess there is exactly the green nobody earned that the recipe
exists to prevent.
