# Plan: the four days two specs cost — 019 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**, naming the SHA-256 digest of each. The reply is the gate; no approval file
is created. Specification 019 carries `status: draft` and authorises nothing on its own.

Block H is behind a second gate that this approval does not open. It computes a width and
never spends it, and its clamp holds while the Intent still says one writer owns repository
changes. Nothing in this plan changes that sentence, and nothing here may be read as
permission to change it.

There is exactly one repository writer. Each Task is one atomic commit changing one primary
production, policy, documentation or skill file, plus only the test and fixture files that
Task names. Two Tasks name a second production file and say why in their own text; every
other Task names one. Rollback for every Task and every repair is `git revert <commit>`.

**This plan is not edited while it is executed.** That is the defect specification 019 exists
to close, and a plan that closed it by rewriting its own bytes would have reopened it in the
same commit. There are no checkboxes below. What happened to each Task is recorded in the
block hand-off, which lives in the conversation and in the commit messages, and the approved
digest of this file stays the digest that was approved.

## The protocol this plan runs under

Everything in specification 010's block checkpoint and review protocol carries over unaltered.
Per Task, the single writer: confirms the authorised scope; runs the named check and observes
the expected red; implements the smallest change; makes the check green and runs **the test
files this Task names, by path** — not `just quick`, which takes one module name and has no
file to run for four of the Tasks below and no module at all for the skill and build-file
ones; runs `git diff --check` and reads the changed content for secrets, personal data,
machine paths, suppression comments and out-of-scope writes; makes one verified revertible
commit without bypassing the hooks; and labels the hand-off **UNREVIEWED**.

A full semantic review and `just check` do **not** run after each Task.

**Block close, in this order, and the order matters.** Freeze writes. Run the block's related
suites by path. Give one fresh read-only reviewer the recorded base and every checkpoint
commit. Take one consolidated ledger. Make one repair wave. Take one bounded re-review of
that ledger. Then `uv run python tests/seal_ceiling.py`, which is the block's last code
change and its own commit — rollback `git revert <commit>` — because it rewrites both
`src/ai_engineering/contract.py` and `tests/test_contracts.py` and sealing before the repairs
are in seals a number that is about to move. Only then `just check`, once. If a second new
family of blocking findings appears after the repair wave, stop and return to `/ai-spec`
rather than continuing.

Every check named below carries its own label. **Red now** means the command reports the
failure today, exactly as written. **Red after the assertion** means the node exists and
passes today, and goes red the moment the writer adds the assertion the Task names — which
is the TDD order for a Task whose subject is a contract string rather than a behaviour. Node
identifiers are written in full, because a mistyped selector exits with "no tests collected"
and that is indistinguishable from a node that is genuinely absent.

## The ceiling, and which Tasks are expected to hold it red

Measured while writing this: `contract.repo_lines` is 78,682 against `REPO_CEILING` 78,682 —
margin exactly zero — and the test ratio is 44,673 over 22,565, which is 1.9797 against a
maximum of 2.0, so roughly 450 test lines of slack for the whole plan.

The consequence is stated here rather than discovered: **the first commit of every block puts
the tree over the ceiling, and `tests/test_contracts.py::test_the_line_ceiling_holds` plus
`tests/test_readiness.py` stay red until that block's seal commit.** That is not a Task
failing. It is what a zero-margin ceiling and a once-per-block seal mean together, and the
alternative — sealing per Task — reads a shared git index and would bake another session's
staged work into this repository's own ceiling, which has already happened here once.

Two consequences for the writer. Tasks 4, 11, 14, 15, 17 and 19 have `tests/test_contracts.py`
among their named files, so their own suite carries that red; run it and read past that one
node, and say so in the hand-off. And seal only while holding the tree alone: no Task below
runs `just seal`, and the block-close seal is refused if another session has staged work.

The test ratio has no sealer. Roughly 450 lines is the budget for every new test in this plan,
and Task 14's two frozen lists of sixteen and eighteen directory names are the largest single
draw. If the ratio goes red, that is a real stop and a return to `/ai-spec`, not a seal.

## Block A — the gate's time back, with every check kept (Tasks 1–3)

This block is first because every later block close runs `just check` once, and `just check`
runs the suite twice. Paying for that six times before making it cheap is the velocity the
specification's own case for this option promised and would then have spent.

1. [ ] **Both full-suite recipes run across the machine's cores** — **file** `justfile`.
   **check**: `uv run --with pytest==9.1.1 pytest -q -n auto tests/test_dag.py`. **Red now**:
   it exits 4 with `unrecognized arguments: -n`, because the pinned environment has no
   distribution plugin. Green once the plugin is pinned beside the others and both recipes
   carry the flag.
   **also names** `tests/test_p0_completeness.py`, whose line 232 pins the suite recipe's exact
   text and must move with it; the claim that pin protects — that the recipe runs the whole
   tests directory — stays literally true.
   **rollback**: `git revert <commit>`. **done when**: the suite recipe and the coverage recipe
   both run at the detected core count and never at a literal above it — a run at sixteen
   produced two unexplained extra failures on an eight-core machine and the detected count
   produced none in three runs; `just test` and `just cover` report the same passed, skipped
   and failed counts as before across three runs; and the coverage total is unchanged with the
   floor still exiting zero.

2. [ ] **A unit test about a file reader stops calling the security lane** — **file**
   `tests/test_threat_model.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_threat_model.py --durations=3`.
   **Red now**: the slowest line names
   `test_a_threat_model_that_is_not_utf_8_is_a_verdict_too`, which calls the real baseline with
   the engine list unpatched. What that costs is not a fixed number and this plan does not
   claim one: two runs measured it at 2.19 and 1.37 seconds with a warm dependency database,
   and an earlier run measured twenty. This check reads a name out of the output rather than an
   exit code, and it is the only one in this plan that does. A wall-time floor written as an
   assertion would fail on a loaded runner, which is a worse control than the durations line a
   person reads at block close.
   **rollback**: `git revert <commit>`. **done when**: the test empties the engine list and the
   cross-check list the way the test at line 235 already does, both of its assertions are
   unchanged and still produce a verdict of one, the test no longer appears in the three
   slowest lines, and the real pinned engines still run over the whole repository in the
   security recipe, which is where they are supposed to be observed.

3. [ ] **The mutation runner spends the cheap suite first** — **file** `tests/mutation.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q
   tests/test_quality_gate.py::test_the_mutation_runner_spends_the_cheap_suite_first`.
   **Red now**: the node is absent.
   **rollback**: `git revert <commit>`. **done when**: the assertion reads the call order out
   of the source and not the docstring — the docstring already describes the fixed behaviour
   the code does not have, so an assertion a reworded comment can satisfy is no assertion; the
   adversarial runner is invoked first and the test runner only when it passed; and the
   fourteen printed rows and the final count are unchanged, compared against a run captured
   before the change and kept as the block's artefact.

## Block B — the cadence that invalidated its own approval (Task 4)

4. [ ] **The build skill stops editing the plan and stops running the whole gate per Task** —
   **file** `.agents/skills/ai-build/SKILL.md`, with its sibling `corpus.md`.
   **check**: `uv run --with pytest==9.1.1 pytest -q
   tests/test_contracts.py::test_the_build_skill_neither_edits_the_plan_nor_gates_each_task`.
   **Red now**: the node is absent, and the strings it will refuse are present — `checkbox` at
   lines 20 and 37 of the skill and at line 24 of the corpus, and `Run the gate exactly as CI
   runs it` at line 35. No existing test pins this file's wording, so no other pin has to move.
   **rollback**: `git revert <commit>`. **done when**: the assertion covers the skill's
   description, its numbered steps and its Done-when list, and the corpus, because the skill
   restates both repaired behaviours in three further places that a two-string ban does not
   reach; step 5 runs the Task's focal check and the test files the Task names instead of the
   gate; the instruction to edit the plan is deleted rather than replaced by a second copy of
   the existing escalation step; the hand-off is labelled unreviewed; and the full gate is
   named once at block close.

## Block C — the greens that are not greens (Tasks 5–10)

5. [ ] **A failed git call is not an empty change set** — **file**
   `src/ai_engineering/checkpoint.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q
   tests/test_checkpoint.py::test_a_checkpoint_over_a_base_that_does_not_exist_is_not_a_pass`.
   **Red now**: the node is absent, and the behaviour is reproducible in a scratch repository
   holding a claim and one fresh passing receipt — a base reference that does not exist gives
   claimed-paths PASS over zero files, staged-privacy SKIPPED, and an aggregate that is not a
   failure. Reproduce it in a scratch repository and never against this working tree: the
   verify path calls out to the remote and writes local references.
   **also names** `tests/test_checkpoint.py:302`, which asserts today that an unresolvable base
   gives an empty list; a raising helper makes it raise, and its own docstring already promises
   the receipts do not claim a pass, so it is the pre-existing false green this Task closes.
   **rollback**: `git revert <commit>`. **done when**: the helper raises on a non-zero exit, the
   privacy and claimed-paths receipts turn that into INCOMPLETE naming the git command that
   failed, and the aggregate verdict is not PASS.

6. [ ] **The content digest moves into the package that needs it** — **file**
   `src/ai_engineering/evidence.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q
   tests/test_ran_receipt.py::test_the_digest_the_receipt_carries_comes_from_the_package`.
   **Red now**: the node is absent, and the digest is computed by a function inside
   `tests/ran_receipt.py`, a script run by path from `git-hooks/commit-msg` and from two build
   recipes. Nothing under `src/` can import it, so Task 7 could only reach it by copying the
   algorithm into a second file, which is the drift this repository exists to refuse.
   **also names** `tests/ran_receipt.py`, `git-hooks/commit-msg` and `justfile`, which call it
   by its old home, and `tests/test_quality_gate.py`, which pins that prose. This Task is a
   move with its callers, not a behaviour change: the digest of the same tree before and after
   must be the same string, and the hand-off carries both.
   **rollback**: `git revert <commit>`. **done when**: one function computes the digest, it
   lives under `src/`, every caller reads it from there, and the receipt written by the build
   recipe is byte-identical to the one written before the move.

7. [ ] **A receipt is evidence for the code it was taken over** — **file**
   `src/ai_engineering/checkpoint.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q
   tests/test_checkpoint.py::test_a_receipt_taken_before_the_staged_change_is_incomplete`.
   **Red now**: the node is absent. The reader at line 145 takes four fields — none binds a
   receipt to this code — and the handler at line 168 silently drops the one receipt in the
   tree that carries a content digest, because it has no finished-at field. Task 6 must land
   first.
   **also names** `tests/test_mut_checkpoint.py`, which pins the age rows.
   **rollback**: `git revert <commit>`. **done when**: a receipt carrying a content digest is
   read and **preferred when present**, and the age rule still decides the rest — the
   specification says prefer, and a rule that refused every ageing receipt would leave a fresh
   clone permanently incomplete, because the receipts directory is not committed; a preferred
   receipt whose digest does not match the tree reads INCOMPLETE with a cure naming the command
   to run; and the plan hand-off says in one line that a digest receipt carries no outcome
   field, so presence means the suite passed and the failure branch stays with the aged ones.

8. [ ] **An import inside this package is an ordering edge** — **file**
   `src/ai_engineering/dag.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q
   tests/test_dag.py::test_a_package_import_puts_the_imported_file_first`. **Red now**: the
   node is absent, and three tasks over three modules that import each other return no edges
   at all, because the module derivation produces the source-layout spelling while this
   repository's own imports produce the package spelling.
   **rollback**: `git revert <commit>`. **done when**: a task over a file that another task's
   file imports is ordered behind it for both spellings, the existing ordering test stays
   green, and a file that cannot be read is still an incompletion rather than a missing edge.

9. [ ] **The ordering module can name the claims that could start together** — **file**
   `src/ai_engineering/dag.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q
   tests/test_dag.py::test_the_wave_is_the_claims_with_nothing_in_front_of_them`. **Red now**:
   the node and the function are absent; the ordering function computes the set on every pass
   and keeps only its first element. Task 8 must land first, because a set derived from edges
   that never fire is worse than no set.
   **rollback**: `git revert <commit>`. **done when**: the function returns the sorted claims
   with no incoming edge; the claim **behind** a shared-path edge is not among them, while the
   one in front of it is, because a shared path is oriented by work item and not refused; and
   an unreadable file propagates as the same incompletion the ordering function already raises.

10. [ ] **One working tree holds one claim** — **file** `src/ai_engineering/claim.py`.
    **check**: `uv run --with pytest==9.1.1 pytest -q
    tests/test_claim.py::test_a_second_claim_in_one_working_tree_is_refused`. **Red now**: the
    node is absent, and the claim file is written unconditionally at line 209 with no lock and
    no existence check anywhere in the function, so the second claim silently becomes the scope
    the guard confines the first writer to.
    **rollback**: `git revert <commit>`. **done when**: taking a claim while the tree already
    holds a different one is refused with its own code and a cure that says to release it or
    take the task in its own worktree; a claim file that cannot be read is the same refusal,
    which specification 019 repair 9 now says in as many words; no remote reference is created
    by the refused call; and the docstring at `tests/test_claim.py:162` that says "five
    refusals, in a fixed order" is corrected in the same commit, because there are now six.

## Block D — the examples become a thing a command reads (Tasks 11–14)

11. [ ] **The template asks for a command and the output it prints** — **file**
    `src/ai_engineering/spec.py`.
    **check**: `uv run --with pytest==9.1.1 pytest -q
    tests/test_contracts.py::
    test_the_template_gives_the_spec_every_section_the_skill_demands_of_it`.
    **Red after the assertion**: the node passes today; the writer adds an assertion for the
    new clause first and watches it fail.
    **rollback**: `git revert <commit>`. **done when**: the heading is byte-identical to the
    three specifications that already carry it; the two phrases the existing assertions read
    are still present; the prompt names a worked shape in which the Then carries the command
    and the exact output in backticks; and **the worked shape's verb is deliberately not one
    the Task 12 parser accepts**, so a freshly created specification does not satisfy the
    executable clause on the day it is written, which is the failure Task 14 needs to be able
    to observe.

12. [ ] **A function counts what an examples section actually holds** — **file**
    `src/ai_engineering/spec.py`.
    **check**: `uv run --with pytest==9.1.1 pytest -q
    tests/test_mut_spec.py::test_the_examples_section_is_counted_by_what_it_holds`. **Red
    now**: the node and the function are absent.
    **rollback**: `git revert <commit>`. **done when**: the function returns the count of
    Given, When and Then lines in the section and the count of Then paragraphs that name a
    command from a closed verb list and carry a second code span after it; a specification with
    no heading returns zeroes; the verb list contains at least the build runner, the package
    runner, the test runner, the interpreter, `git` and this project's own command, because
    specification 019's own success example uses `git` and it is the only specification the
    Task 14 executable rule will not have frozen; and the list carries a comment naming itself
    as a ceiling and the condition for widening it. This Task's home is the mutation-selected
    test file, not the contract file, so the parser gets mutation coverage.

13. [ ] **The show subcommand prints what it observed and decides nothing** — **file**
    `src/ai_engineering/spec.py`.
    **check**: `uv run --with pytest==9.1.1 pytest -q
    tests/test_record.py::test_show_says_what_the_examples_section_holds`. **Red now**: the
    node is absent and the subcommand prints the file and nothing else.
    **also names** `tests/test_mut_spec.py`, which holds the exact-output assertions over this
    subcommand at lines 207, 210 and 1089; the new line must not contain the substring `1 of`,
    or the multi-match guard at line 210 breaks for a reason unrelated to what it guards.
    **rollback**: `git revert <commit>`. **done when**: the line is descriptive, carries no
    verdict word, and changes no exit code.

14. [ ] **The gate reads authored specifications, with two frozen baselines** — **file**
    `tests/test_contracts.py`.
    **check**: `uv run --with pytest==9.1.1 pytest -q
    tests/test_contracts.py::test_a_specification_carries_examples_somebody_can_check`. **Red
    now**: the node is absent. Tasks 11 and 12 must land first: this node calls the Task 12
    parser rather than re-implementing the rule, so that the repository holds one definition of
    the executable clause and not two.
    **rollback**: `git revert <commit>`. **done when**: two closed lists exist and are named
    separately — sixteen specifications frozen out of the structure rule and eighteen out of
    the executable rule, because neither of the two older ones that carry the section satisfies
    the executable clause today; both lists are asserted to name only directories that exist,
    so a rename turns the gate red instead of quietly shrinking it; the docstring says a freshly
    created specification reds this gate until its author fills the section, so the failure
    reads as intended; and **four proofs are run before the commit lands, not three** — a
    scratch specification with no section reds the structure rule naming it; removing one name
    from the structure baseline reds it naming that specification; a scratch specification
    carrying the heading with three Given, three When and three Then lines and no command reds
    the executable rule and passes the structure rule, which is exactly the undecidable-path
    example specification 019 wrote; and the scratch directories are deleted afterwards.

## Block E — the plan's own tasks become enumerable (Tasks 15–16)

15. [ ] **A plan's tasks are something a script can read** — **file** `tests/test_contracts.py`.
    **check**: `uv run --with pytest==9.1.1 pytest -q
    tests/test_contracts.py::test_a_plan_names_a_file_a_check_a_rollback_and_a_done_when`.
    **Red now**: the node is absent, and no test in this repository opens a plan at all.
    **rollback**: `git revert <commit>`. **done when**: every task of every authored plan not
    on the frozen list carries the four fields, and the check field is a command in backticks
    beginning with a known runner rather than a sentence; the four plans that carry no
    executable check are frozen by name with one line each saying why, because the constitution
    forbids retro-editing them; the frozen list is asserted not to grow; and the list is
    asserted to name only directories that exist.

16. [ ] **A task is handed over as an envelope, not as the bytes it came from** — **file**
    `src/ai_engineering/spec.py`.
    **check**: `uv run --with pytest==9.1.1 pytest -q
    tests/test_mut_spec.py::test_one_task_is_read_out_of_a_plan_as_an_envelope`. **Red now**:
    the node and the function are absent. Task 15 must land first, because an envelope read out
    of a plan with no enforced shape is a parser with no contract behind it.
    **rollback**: `git revert <commit>`. **done when**: `spec show` grows one option that prints
    one task's identifier, the digest of the specification and of the plan it was read from, the
    file, the check, the rollback and the done-when, and nothing else; a task number that does
    not exist, a plan that does not parse, or a digest the caller named that does not match the
    bytes on disk each refuse rather than print a partial envelope; no subcommand is added, so
    the verb's closed list of five does not move and the four pinned usage lines stay green; and
    the printed envelope for the largest plan in the tree is under one kilobyte, against the
    128,047 bytes specification 019 measures as today's cost.

## Block F — the two stages with no house (Tasks 17–19)

17. [ ] **The verify capability stops being declared and absent** — **file**
    `.agents/skills/ai-verify/SKILL.md`, with its sibling `corpus.md`.
    **check**: `uv run --with pytest==9.1.1 pytest -q
    tests/test_contracts.py::
    test_every_declared_capability_has_a_skill_or_names_where_its_work_went`.
    **Red after the deletion**: the node passes today; it goes red the moment the verify row
    leaves the absorption map with no skill directory beside it, which is the first edit of
    this Task. No schema change is needed — the manifest's closed list of fifteen identifiers
    already contains this one, and nothing caps the number of skill directories.
    **also names** `docs/requirements.toml`, whose two rows still record that a passing test
    forbids this skill from existing. A skill that lands while the register says it must not is
    two records disagreeing, and specification 019 repair 6 says both move together.
    **rollback**: `git revert <commit>`. **done when**: the skill is at or under the line ceiling
    and at or under the readability ceiling; it has two routes, one that runs the gate and the
    security lane and ticks each production-ready box beside the command that ticked it, and one
    that walks a specification's examples and marks each passed, failed or incomplete against a
    real command, **calling the Task 12 parser rather than re-deciding what executable means**;
    incomplete is the default for a box or an example with no command pasted beside it; the
    corpus routes cases no sibling claims; and `uv run python tests/skill_eval.py` is green.

18. [ ] **The security report declines the dynamic surface instead of passing over it** — **file**
    `src/ai_engineering/scan.py`.
    **check**: `uv run --with pytest==9.1.1 pytest -q
    tests/test_scan.py::test_a_tree_with_no_authorised_target_declines_the_dynamic_scan`. **Red
    now**: the node is absent, and the report's last printed line is the images line, so a
    repository with a deployed preview gets a zero exit and no sentence saying a running target
    was never looked at.
    **also names** `tests/test_scan.py`'s two whole-report pins, which both end on that line and
    must be extended in the same commit so neither can pass quietly.
    **rollback**: `git revert <commit>`. **done when**: one skipped line is printed after the
    images line, using the word this module already uses for declining rather than the word the
    research report used, which this repository's status vocabulary does not have; the line
    touches no verdict and has no branch.

19. [ ] **The security skill says where a running target goes and what the answer is today** —
    **file** `.agents/skills/ai-security/SKILL.md`, with its sibling `corpus.md`.
    **check**: `uv run --with pytest==9.1.1 pytest -q
    tests/test_contracts.py::test_the_guidance_a_requirement_asks_for_is_in_the_file_that_owes_it`.
    **Red after the row**: the node passes today; it goes red the moment the new pinned row is
    added and the sentence is not yet in the file. The row's first field is a free-text label,
    so it is labelled with the decision it comes from and needs no invented requirement
    identifier; if the reviewer reads that field as an identifier instead, the row moves to a
    new register entry and this Task names `docs/requirements.toml` too.
    **rollback**: `git revert <commit>`. **done when**: the skill says that no scanner pinned
    here touches a running target, that the report says so, and that calling a running service
    safe on a static scan is incomplete and never a pass; the corpus routes the question and
    names the deferral; the skill is still under both ceilings; and the new text carries none of
    the words on the jargon list, table rows included. Task 18 lands first, because this
    sentence claims the report says something it does not yet say.

## Block G — the Solution Intent a person reads (Tasks 20–22)

The owner decided this after the plan was first written: the Solution Intent belongs under
`docs/`. Specification 019 repair 11 carries the decision, and these three Tasks are it.

20. [ ] **The page and the generator enter the repository** — **file**
    `src/ai_engineering/solution_intent.py`, with the page it writes at
    `docs/solution-intent.html`.
    **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_solution_intent.py`. **Red
    now**: the file is absent, and so are the two files it tests — both exist untracked in the
    working tree and one `git clean` from gone.
    **rollback**: `git revert <commit>`. **done when**: three assertions hold — writing the
    page then asking whether it is stale answers no; flipping one specification's status makes
    it answer yes and the reason names the tree digest; and every field of the record the page
    renders appears in the digest payload, derived from the dataclass rather than a hand-kept
    list, which is the regression test for the defect this generator already had once. The
    page counts lines through the contract module and not through a second walk, so its
    numbers are the ones the ceiling and the ratio gate enforce; it excludes only itself, and
    says so on the page, because a page whose length feeds the number it prints never settles.

21. [ ] **The command the failure message promises exists** — **file**
    `src/ai_engineering/report.py`.
    **check**: `uv run --with pytest==9.1.1 pytest -q
    tests/test_record.py::test_report_intent_writes_the_page_and_says_where`. **Red now**: the
    node is absent, and the staleness message tells the operator to run a command the argument
    parser rejects. A gate whose remedy is a command that does not exist is worse than no gate.
    **also names** `src/ai_engineering/cli.py`, whose one-line summary for the report verb lists
    three subcommands and would then list four. This is the second of the two Tasks that
    carries a second production file on purpose: the summary is the only place a person finds
    the subcommand, and shipping the route without it is shipping it hidden.
    **rollback**: `git revert <commit>`. **done when**: the subcommand writes the page and
    prints where it wrote it; the ten verbs are still ten; and the staleness message names the
    command that now works.

22. [ ] **The page cannot go stale without the gate saying so** — **file** `justfile`.
    **check**: `uv run --with pytest==9.1.1 pytest -q
    tests/test_p0_completeness.py::test_the_gate_checks_the_page_is_about_this_tree`. **Red
    now**: the node is absent, and nothing in the eleven recipes the gate depends on mentions
    the page. Tasks 20 and 21 land first, because the recipe calls what they build.
    **rollback**: `git revert <commit>`. **done when**: one recipe runs the staleness check and
    exits non-zero when the page was built from a different tree; it sits before the receipt
    recipe, which writes last; and the failure text names the command that regenerates the
    page. Note for the writer: from this Task onward every commit that changes a
    specification, a plan, a decision record, a skill, a hook class or the verb table also
    regenerates the page, and that is the intended cost — it is what "always up to date" means
    when a machine rather than a person is keeping the promise.

## Block H — width, and it stays one (Task 23)

Block H may not start until Blocks A through G are closed and reviewed, **and** until the
accountable role has said in writing that this block may open. It changes no constraint, and it
exists so that the constraint has something executable behind it.

23. [ ] **A width is arithmetic over the records, and it is one** — **file**
    `src/ai_engineering/spec.py`.
    **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_wave.py`, three cases: two
    disjoint claims and a declared width of four, while the Intent still carries the one-writer
    sentence, gives one and the reason names that file; the same tree with the sentence absent
    gives two; a declared width that is not a positive integer gives one. **Red now**: the file
    and the subcommand are absent.
    **also names** two more files, and this is one of the two Tasks that carries a second
    production file on purpose. `src/ai_engineering/cli.py` holds the sentence describing which
    subcommand reaches the network, and it is already wrong — the checkpoint subcommand reaches
    the remote too — so adding a third reacher while leaving that sentence unread would be
    shipping a known-false declaration. And `tests/test_mut_spec.py` pins the verb's usage line
    in four places; adding a subcommand reds all four, so the named check alone would go green
    over a red module.
    **rollback**: `git revert <commit>`. **done when**: the subcommand reads the claims from the
    remote, derives the independent set, and reports the smallest of the declared width, the
    size of that set, and one; every unknown — an absent, unparseable or non-positive width, a
    remote that cannot be read, an unreadable file, an empty or single-item set — resolves to
    one; the facts it returns are observations and never a verdict about the branch; and the
    width this repository computes today is one, and the hand-off shows it.

## What this plan is not doing, and why

**Nothing here gets a URL, so there is no deployment task and no observability task.** Every
Task changes a module, a build recipe, a test or a skill inside this repository. The
production-ready boxes in specification 019 stay unticked and this plan does not tick them.

**The build skill does not stop clamping the width.** That is specification 019's second block
and it needs the accountable role to approve a coordination plan at an exact digest and to
change the Intent's constraint in the same commit. Task 23 computes a number that is always one
until then, and that is the intended end state of this plan.

**No mutation baseline is committed.** The statistics file is untracked and holds a partial run,
so no command can answer whether the mutation score fell. Specification 019 records that as an
unresolved risk and does not decide it, so deciding it here would widen this plan's own scope.
Every claim in Block A about keeping quality rests on the passed, skipped and failed counts and
the coverage total, and on nothing else.

**The cheap suite recipe still takes one module, and this plan stops depending on it.** There
is no test file named for the specification module, and the skill and build-file Tasks have no
module name to pass, so the per-Task protocol above names test files by path instead. Widening
that recipe is a real improvement and it is not one of the ten repairs.

**Plan approval does not become a machine-readable fact.** Two skills stop on a condition
nothing in the source can read. That is real, and specification 019 does not decide it.

**The third collection in the counts recipe stays.** It costs about a second of a suite budget
measured in minutes, so removing it for speed would be argued on the wrong grounds. There is an
honest reason to change it — it prints a count from a collection while the run that executed
those tests prints none — and that reason belongs in its own record.

**No selection map, and no floor is lowered.** A changed-file-to-test map does not fail when it
is wrong, it skips, quietly. The coverage floor and the mutation floor are not touched.
