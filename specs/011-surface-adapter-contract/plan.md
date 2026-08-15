# Plan: the surface adapter contract — P1 atomic execution

## Authority and atomicity gate

This plan lands under the standing delegation the repository owner gave when they closed
P0: "cierra el P0 automáticamente rellenando tú lo que haga falta… no perdamos el goal que
debemos hacer todo y dar menos vueltas en aprobaciones y quedarte bloqueados." That
instruction is recorded verbatim in the CHANGELOG entry commit `ae523990`, which is the
same reference MADRs 0005, 0006 and 0007 carry, and it is the authority this plan names.
It is not a blanket grant: it covers proceeding without a fresh approval round for each
record, and it covers nothing that needs separate consent.

**Still requiring separate, explicit consent, and not covered here:** any push, tag,
release, publication, global installation, or network call. No release receipt or
publishing authority is implied by anything in this plan.

There is exactly one repository writer. Each Task is one atomic commit changing one primary
production, policy, documentation or workflow file, plus only its focused supporting test
and fixture files. Rollback for every Task and repair is `git revert <commit>`.

Every check named below is an exact future red check: run it with `uv`, using the named
`path::node`. It is red now because the node or file is absent, and becomes green only
after that Task. No broad `-k`, placeholder node or invented green result is acceptable.

## The protocol this plan runs under, and the one thing that changed


Everything from spec-010's "Block checkpoint and review protocol" carries over unaltered:
one writer, TDD red first for the exact cause, atomic UNREVIEWED checkpoints, no full gate
between tasks, a consolidated fresh review at block close, bounded repairs, one `just
check` when the review is clean.

**One rule is added, and it is the only thing this session measured that the research did
not anticipate.** Spec-010's protocol allows exactly one bounded re-review. Block D spent
it and the re-review still returned REJECT — five findings, every one introduced by a
repair to the first review, one of them a blocker. Repairing those produced five commits
with no independent reader, and a third review run outside the protocol found three more.

> **A re-review that returns REJECT re-arms itself.** The block is not closed while a
> review's own repairs are unread. Rounds are not capped; what is capped is closing over
> them. A repair round is work, not a closing step, and carries the same red-first
> discipline as a task.

The measured progression that justifies it: **14 findings, then 5, then 3.**

## Sequence

The spec's decision D-011-02 sets the shape: adapters land one at a time, each behind its
own executed denial. So the blocks are not "all contracts, then all adapters" — they are
the contract once, then one surface per sub-block, in the order of what can actually be
proved today.

### Block A — the contract and the three receipts (Tasks 1–6)

1. **Adapter contract schema** — **file** `policy/surface-adapter-v1.schema.json`.
   **check**: `pytest -q tests/test_surface_adapter.py::test_adapter_schema_is_closed_and_versioned`.
   **rollback**: `git revert <commit>`. **done when**: closed schema, `additionalProperties`
   false, carrying detection signal, bidirectional translation tables for payload field,
   lifecycle event, exit meaning and reply, heartbeat states and trust requirement; every
   translation table is exhaustive and an unknown value on either side has no mapping.

2. **Invalid fixtures before the reader** — **file** `tests/fixtures/surface-adapter-v1.json`.
   **check**: `pytest -q tests/test_surface_adapter.py::test_every_invalid_adapter_fixture_is_refused`.
   **rollback**: `git revert <commit>`. **done when**: at least one invalid fixture per
   closed field, including a translation table with a hole in it, and each is refused before
   any adapter exists to satisfy them.

3. **Three states, three receipts** — **file** `src/ai_engineering/surface.py`.
   **check**: `pytest -q tests/test_surface_adapter.py::test_discovery_invocation_and_enforcement_are_separate_receipts`.
   **rollback**: `git revert <commit>`. **done when**: discovery, invocation and enforcement
   are read from three separate check-evidence receipts; a missing receipt is `INCOMPLETE`
   for that state alone and never borrows another's answer; a T3 surface reports enforcement
   not applicable and cannot be given a denial receipt.

### Amendment, made while executing Task 4

Tasks 4 and 6 were the wrong way round and the code said so. Deleting the static `proven`
field breaks its only reader — `doctor.py:820` — so Task 4 as written forced a second
product home into one commit, which this plan's own atomicity rule forbids. Doctor has to
take its answer from the receipts *before* the flag it currently reads can go.

They are swapped below. Nothing else changes: the same two tasks, the same checks, the same
done-whens. Recording it here rather than quietly reordering, because a plan that drifts
without saying so is a plan nobody can review against what happened.

4. **Doctor reads the three states** — **file** `src/ai_engineering/doctor.py`.
   **check**: `pytest -q tests/test_surface_adapter.py::test_coverage_prints_three_states_and_never_one_word_for_three_questions`.
   **rollback**: `git revert <commit>`. **done when**: the coverage block prints discovery,
   invocation and enforcement separately; no row can print a word for a state without a
   receipt; the legend defines each state in the vocabulary already used.

### Amendment, made while executing Task 5

Task 5 said `surface proof` and named `cli.py`, which means an eleventh verb. Counted
before writing it: AGENTS.md states a ten-verb CLI, two assertions pin exactly ten, and the
installed-wheel matrix counts them from the artifact. So a new verb is a doctrine change
plus four files, to deliver a report a verb that already exists is for.

`report` is that verb — "produce the local governed report" — it already has subcommands,
and its declared scope already covers reading this repository's records and writing nothing
more than a local receipt. `report surfaces` needs no new verb, no doctrine amendment and
no change to the counts. Rule 5 says delete before you abstract; this is the same instinct
one step earlier, which is not adding the thing in the first place.

The exit criterion the proposal names is a command that answers per surface. It does not
say the command must be a verb, and a subcommand answers it exactly.

5. **The `surface proof` report** — **file** `src/ai_engineering/report.py`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_surface_adapter.py::test_surface_proof_reports_three_states_and_invents_none`.
   **rollback**: `git revert <commit>`. **done when**: `ai-eng report surfaces` reports the
   three states per surface with the age of each proof, returns `INCOMPLETE` rather than a
   state for anything unreceipted, and adds no verb — the two exact-ten assertions and the
   installed-wheel count stay untouched, which is the evidence that it added none.

### Amendment, made while executing Task 6

Task 6 is two tasks. Deleting the field and teaching its reader to live without it are
different homes — `policy/surfaces.toml` and `src/ai_engineering/doctor.py` — and Task 4
did not remove the dependency, it added a second block beside it. So the flag still has a
reader, and one commit cannot both retire the reader and delete what it reads.

Splitting it also exposes the consequence separately, which is worth its own commit
message: once the coverage word comes from a receipt, **every surface reads UNPROVEN**,
including the one that has read BLOCKS since the beginning. That is not a regression. It is
spec 010's own sentence — three surfaces read UNPROVEN and stay that way until a denial
actually executes there — applied to all eight, because none of them has ever receipted one.

6a. **The coverage word comes from a receipt** — **file** `src/ai_engineering/doctor.py`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_surface_adapter.py::test_the_coverage_word_is_earned_and_never_declared`.
   **rollback**: `git revert <commit>`. **done when**: `standing` takes the surfaces whose
   enforcement receipt proved, never `surface["proven"]`; the one-word block and the
   three-state block agree by construction because both read the same receipts; every row
   that has no receipt reads UNPROVEN, and the tests that pinned the old word move with it.

6b. **`proven` stops being writable** — **file** `policy/surfaces.toml`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_surface_adapter.py::test_no_surface_flag_can_assert_a_state_a_receipt_has_not_earned`.
   **rollback**: `git revert <commit>`. **done when**: the field is deleted, not deprecated,
   and the test fails if it returns under any spelling.

### Block B — the denial that already runs, receipted

Restored: the Task 6 amendment above replaced a span reaching to the next heading and took
Block B's three tasks with it. Recorded rather than quietly re-added, because a plan losing
a block silently is the failure mode the amendments exist to prevent.

### Amendment, made while starting Block B

Task 7 said `src/ai_engineering/adapters/claude_code.py`. Two things are wrong with that,
and the second is the one that matters.

Everything the contract asks an adapter for — a detection signal, four translation tables,
a trust ceremony — is data, and AGENTS.md says where data lives: "`policy/` — data, not
code". A module holding a dict is a dict with a `.py` extension.

The second: nothing would read it. The interim audit's largest single finding is
`capability.py`, where fifteen capabilities declare six governed fields each, the schema
validates them, and every declared action still returns `ENFORCEMENT_UNAVAILABLE` because
nothing calls the preflight. **A declaration that governs nothing is the defect this wave
is fixing, not a step toward fixing it.** Writing a second one, in the same wave, to satisfy
a task number, would be indefensible.

So Task 7 is deferred, and Block B is the two tasks that close the gap this wave actually
left open: the wheel executes a denial and nothing receipts it.

7. **Deferred.** An adapter record lands when a reader needs one, not before.

8. **The wheel's denial writes its receipt** — **file** `.github/workflows/install-matrix.yml`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_surface_adapter.py::test_the_matrix_receipts_the_denial_it_already_executes`.
   **rollback**: `git revert <commit>`. **done when**: the step that already denies
   `--no-verify` from the installed wheel writes a check-evidence receipt for
   `claude-code.enforcement` naming the command it ran, and the job asserts
   `ai-eng report surfaces` reads that state as PASS in the same run — so the loop is proved
   end to end rather than asserted. Nothing is committed or uploaded: the receipt is a
   runtime artifact, and the proof is that it was read, not that it was kept.

9. **The three states, from the artifact** — **file** `.github/workflows/install-matrix.yml`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_surface_adapter.py::test_the_matrix_proves_discovery_and_invocation_separately`.
   **rollback**: `git revert <commit>`. **done when**: discovery and invocation are executed
   and receipted separately from enforcement, each by something that would fail if the
   surface could not do it; a state nobody could execute stays unreceipted rather than
   acquiring a receipt for a weaker thing.

### Blocks C onward — one surface per block, in provability order

`opencode` (routers exist to be built and a denial is plausible), then `codex-cli` (links
and `agents/openai.yaml`, with the trust ceremony), then `cursor`, `copilot-cli` and
`vscode-copilot`. Each block is the same three tasks: adapter, negative fixtures from the
wheel, receipts. **A block whose denial cannot be executed does not ship an adapter.** It
records why, keeps the T3 answer, and the wave says which surfaces reached enforcement and
which did not — never an average.

`pi` and `zed` get no adapter and no block. They are T3 by the frozen contract.

## What must not happen, stated so a reviewer can check it

- No surface acquires a state it has not receipted, including by inheriting a sibling's.
- No translation table has a default branch. An unknown value is a denial, and there is a
  test for the unknown value on each side.
- No `proven`-shaped field returns under another name.
- Nothing here touches P2–P5, the guard/telemetry contract, the dispatcher or the record
  verbs.
- The line ceiling is measured and stated per block; it is not raised silently, and if it
  must rise the commit message says why.

## What this plan cannot decide

The order of Blocks C onward is a guess about which surfaces can be made to deny, and that
is a question the first executed attempt answers better than any plan. The order is
therefore explicitly revisable between blocks, by amendment, with the same approval each
amendment has always needed here.
