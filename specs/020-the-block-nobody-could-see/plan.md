# Plan: the block nobody could see — 020 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**. The specification was approved at digest
`1a36b1147335ec92d450fefd1596a9403e652b4362d43a140ef1008e27cacfac`; this plan is the second
half and carries its own digest. Specification 020 carries `status: draft` and authorises
nothing on its own.

One repository writer. Each Task is one atomic commit changing one primary production, policy
or skill file, plus only the test files that Task names. Rollback for every Task and every
repair is `git revert <commit>`.

**This plan is not edited while it is executed.** No checkboxes. What happened to each Task is
recorded in the block hand-off and in the commit messages, and the approved digest of this
file stays the digest that was approved.

## The protocol this plan runs under

Unchanged from 019. Per Task the writer confirms the authorised scope, runs the named check
and observes the expected red, implements the smallest change, makes the check green and runs
**the test files this Task names, by path** — never the whole gate — reads the diff for
secrets, personal data, machine paths and suppression comments, makes one revertible commit
without bypassing the hooks, and labels the hand-off **UNREVIEWED**.

Block close, in this order: freeze writes; run the block's suites by path; one fresh
read-only reviewer over the recorded base and every checkpoint commit; one consolidated
ledger; one repair wave; one bounded re-review; then `uv run python tests/seal_ceiling.py` as
the block's own commit; then `just check`, once. A second new family of blocking findings
after the repair wave stops the plan and returns to `/ai-spec`.

## The interpretation this plan makes, and why it is here rather than in the code

The specification says every row carries "the exact command that unblocks it" and that a row
whose fourth field would be "ask somebody" is not rendered. Read literally that removes the
class the specification was written for: a draft specification is cleared by a person
replying, and a reply is not a command.

This plan reads the requirement as **a literal the person can copy**, of which a shell
command is one kind and an approval sentence naming a digest is the other — `apruebo 020 en
1a36b114` is exactly as unambiguous as a command and exactly as un-fakeable, because the
digest is in it. What the requirement rules out is a field that says "decide this" or "ask
the owner", and both kinds above are ruled in. The interpretation is written here, in the
document that is approved beside the specification, rather than decided quietly in a
renderer.

## The ceiling

Measured while writing this: `contract.repo_lines` is 81,955 against `REPO_CEILING` 81,955 —
margin exactly zero — and the ratio is 46,042 over 24,084, which is 1.9117 against a maximum
of 2.0, so roughly 2,100 test lines of slack.

So **the first commit of each block puts the tree over the ceiling, and
`tests/test_contracts.py::test_the_line_ceiling_holds` plus
`tests/test_readiness.py::test_spec_010_004_intent_and_ceiling_transition_atomically` stay red
until that block's seal commit.** That is not a Task failing. No Task below runs `just seal`.

## What is counted today, so the numbers below can be checked rather than trusted

Measured on this tree: `docs/requirements.toml` holds 385 rows, of which 17 are BLOCKED or
CONTRADICTED, and all 17 carry both a `note` and an `evidence` command. Eleven specifications
are at `status: draft`; four of them have a `plan.md` — 010, 011, 018 and 019. So the first
render is expected to show **21 rows of 28 considered**, and the seven it drops are drafts
with no plan, which are waiting on the build rather than on a person.

019 will render as waiting for approval even though it was approved this morning, because the
approval was a sentence in a conversation and nothing in the tree records it. That is not a
bug in the collector. It is the defect this specification is about, showing itself on the
first run, and it must not be special-cased away.

## Block A — the record, and the collectors that read what already exists (Tasks 1–3)

1. **A row missing any of the four fields is refused, not filled** — **file**
   `src/ai_engineering/blocked.py`. A new module: a `Row` of `kind`, `id`, `what`, `since`,
   `why` and `action`; `FIELDS = ("what", "since", "why", "action")`; `stops(root)` reading
   `docs/blocked.toml` and returning rows; and `Unreadable` for a file nobody can parse.
   **check**: `uv run --with pytest==8.4.2 pytest -q
   tests/test_blocked.py::test_a_row_missing_any_of_the_four_is_refused`.
   **Red now**: the module and the node are both absent, so pytest exits 4 with
   `ERROR: not found`.
   **rollback**: `git revert <commit>`. **done when**: a row with all four fields is returned
   and a row missing any one of them is dropped with its id readable in the drop list, never
   returned with an empty field; a `docs/blocked.toml` that does not parse raises `Unreadable`
   rather than returning nothing, because an unreadable ledger of what is stuck is itself the
   fail-open direction; and no field is ever synthesised from another.

2. **The verdicts and the drafts already say it, and nothing asks them** — **file**
   `src/ai_engineering/blocked.py`. `collect(root)` returns `(shown, considered)`: the
   BLOCKED and CONTRADICTED rows of `docs/requirements.toml` that carry both a `note` and an
   `evidence`, mapped `subject` to `what`, the file's measured date to `since`, `note` to
   `why` and `evidence` to `action`; the specifications at `status: draft` that have a
   `plan.md`, with the frontmatter `date` as `since` and `apruebo <id> en <first twelve of the
   spec digest>` as `action`; and every row from `stops(root)`. Ordered stops first, then
   drafts, then verdicts, because the question the section answers is what unsticks the build.
   **check**: `uv run --with pytest==8.4.2 pytest -q
   tests/test_blocked.py::test_the_collector_says_what_it_dropped`.
   **Red now**: the node is absent.
   **rollback**: `git revert <commit>`. **done when**: `collect` over this tree returns 21
   shown and 28 considered; a verdict row with no `note` is counted in `considered` and absent
   from `shown`; a draft with no plan is likewise counted and absent; the draft rows' `action`
   carries a digest that matches `sha256` of the specification file as it is on disk; and the
   two numbers come from one pass, so they cannot disagree.

3. **A halt writes its record before it halts** — **file** `src/ai_engineering/report.py`,
   **also names** `policy/capabilities.toml`, which needs an `ai-report.blocked` mode with
   `write_roots = ["docs"]` and no network, because a subcommand that writes a governed file
   without a declared mode is the refusal the capability table exists for.
   **check**: `uv run --with pytest==8.4.2 pytest -q
   tests/test_report.py::test_a_stop_without_an_action_is_refused
   tests/test_capabilities.py`.
   **Red now**: the first node is absent; the second passes today and goes red the moment the
   mode is added without its row in the mode-list map.
   **rollback**: `git revert <commit>`. **done when**: `ai-eng report blocked --what … --why …
   --action …` appends one row to `docs/blocked.toml` and prints the row it wrote; the same
   command with any of the three omitted exits non-zero and names which; `--since` defaults to
   the run's date and is never invented for an existing row; writing twice with the same
   `--what` updates the row rather than appending a second, so a build that halts twice at the
   same gate does not grow the ledger; and the write cannot fail the run it is describing —
   an unwritable `docs/` is reported and returns INCOMPLETE rather than raising.

## Block B — the section a person opens (Tasks 4–6)

4. **The page reads what is stuck** — **file** `src/ai_engineering/solution_intent.py`.
   `Tree` gains `blocked: tuple` and `considered: int`, filled from `blocked.collect`, and the
   digest covers both — it is derived from the dataclass, so a field added here cannot escape
   it, and this Task asserts that rather than assuming it.
   **check**: `uv run --with pytest==8.4.2 pytest -q
   tests/test_solution_intent.py::test_a_row_that_changed_makes_the_page_stale`.
   **Red now**: the node is absent.
   **rollback**: `git revert <commit>`. **done when**: `digested(tree)` contains both new
   fields; changing one row's `action` changes `digest(tree)`; and `blocked.Unreadable`
   propagates rather than rendering a page that says nothing is stuck, which is the same
   fail-open the empty-index refusal already closed for the tracked-file list.

5. **One section, and it says what it dropped** — **file**
   `src/ai_engineering/solution_intent.py`. A `bloqueos` section, immediately after `resumen`,
   because it is the thing a person opens the page for. One table, four columns, one row per
   item, the `action` in a `<code>` span a reader can select. Above the table one line:
   `N de M · los otros M−N esperan al build, no a ti`.
   **check**: `uv run --with pytest==8.4.2 pytest -q
   tests/test_solution_intent.py::test_a_row_with_no_action_is_absent_and_the_count_says_so`.
   **Red now**: the node is absent.
   **rollback**: `git revert <commit>`. **done when**: the rendered page contains a row for
   every item `collect` returns and none for any it dropped; the count line's two numbers are
   the collector's, not recomputed from the rendered rows, so a renderer that silently drops
   one is caught by the numbers disagreeing with the row count; the section renders with a
   plain sentence and no table when nothing is stuck; and `just intent-page` prints PASS.

6. **A skill that stops says so before it stops** — **file**
   `.agents/skills/ai-build/SKILL.md`, **also names** `.agents/skills/ai-spec/SKILL.md`, which
   is the other skill that halts for authority.
   **check**: `uv run --with pytest==8.4.2 pytest -q tests/test_contracts.py -k "blocked or
   ceiling"`.
   **Red now**: the corpus assertion is absent; `test_the_line_ceiling_holds` is the block's
   expected red and is read past.
   **rollback**: `git revert <commit>`. **done when**: both skills carry one step saying that a
   gate they cannot pass is recorded with `ai-eng report blocked` **before** they stop, and
   that the record states the gate reached and the authority missing and grants nothing; the
   assertion is a regex over the corpus and not a substring, so the six words that defeated
   the Block B check cannot defeat this one; and both files stay inside the 80-line ceiling.

## Block close

Seal, then `just check` once, then the hand-off. The first render is expected to show 21 rows
of 28, including 019 waiting for an approval that happened and was never written down.
