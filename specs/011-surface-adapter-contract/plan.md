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

### Amendment, made while reviewing Task 9

Task 9's done-when asked for discovery and invocation to be "executed and receipted". The
delivery executes and receipts neither, and the commit message says so plainly while the
plan did not — the same silent drift the Task 7 amendment wrote a paragraph against, one
task later.

They are not receipted because they cannot be executed here. Proving discovery needs Claude
Code itself: a key withheld from fork pull requests, a billed session, and a
non-deterministic answer — and `doctor.coverage` already refuses that route in its own
docstring, "no probes, no billed sessions". Anything cheaper collapses to "the files are
present", which `policy/check-evidence-v1.schema.json` names as not-proof in as many words:
`metadata_is_proof: false`. So the honest delivery is the refusal, made checkable.

9. **The two states nobody can execute stay unproven** — **file** `.github/workflows/install-matrix.yml`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_surface_adapter.py::test_the_matrix_proves_discovery_and_invocation_separately`.
   **rollback**: `git revert <commit>`. **done when**: exactly one receipt is written and it
   is the enforcement one; the job asserts from the same output that discovery and
   invocation read `SURFACE_RECEIPT_MISSING`, so a state that borrowed another's answer
   fails the run. Receipting either of them from anything weaker than the surface itself is
   refused, and the refusal is what this task delivers.

### Block C — opencode, and the fail-open spec 010 wrote down and left open

Spec 010's own deferred notes name it twice: "OpenCode currently checks only `status===2`;
`null` from spawn failure/timeout can pass" and "The OpenCode `status===2`/`null` risk
remains explicitly open until P1." This is P1. A guard that allows the call when its own
dispatcher fails to spawn is the root pattern this product exists to cure, sitting in the
one surface file no Python test can reach.

It is also the surface with the strongest available proof: the plugin is our code, it runs
under node, and its deny path can be executed directly — which is more than claude-code
has, where the job exercises the dispatcher and not the adapter.

10. **The plugin fails closed** — **file** `surfaces/opencode.ts`.
    **check**: `npm exec -- tsc --noEmit` plus the node case in Task 11's step.
    **rollback**: `git revert <commit>`. **done when**: anything that is not an observed
    clean allow denies — a non-zero status, a null status from spawn failure or timeout, a
    signal, or an error — and the thrown message says which, so a denial caused by a broken
    install is not reported as a policy denial.

    **This done-when was met, then unmet, then met again.** The first implementation denied
    on any non-zero status, as written here. It was narrowed to `status === 2` on the
    strength of a dispatcher comment describing exit 1 as non-blocking and a measurement
    showing an ordinary call exiting 1 — and the code was narrowed without amending this
    line, which is the silent drift the Task 7 amendment wrote a paragraph against. A review
    found both supports false: that comment describes a fail-open the same team fixed, and
    the measurement was an artifact of running the dispatcher under `PYTHONSAFEPATH`, which
    breaks its own imports. Run properly it exits 0. The narrow version allowed
    `git commit --no-verify` whenever the interpreter started and the dispatcher did not.

### Amendment, made while executing Task 11

Task 11 asked the installed-wheel matrix to run the plugin and receipt it. The matrix has
no TypeScript-capable toolchain and cannot be given one cheaply: `setup-node` is an action,
and every action added here has to clear a repository allowlist before the workflow will
start at all — a workflow that never starts has no job and no log to read, which this
repository has already paid for once.

`just typecheck` is the recipe that owns this surface and the one place node and npm are
guaranteed, so the execution lands there and runs in CI through `just check` like every
other gate. What it cannot do is write a receipt: a receipt says a denial executed on an
installed artifact, and this runs from the checkout. So opencode's enforcement stays
`SURFACE_RECEIPT_MISSING`, which is the truth.

That is a smaller delivery than the task asked for and it is the honest one. The fail-open
is closed and proved by execution; the receipt waits for a matrix that can run the surface.

11. **The plugin's denial executes in the gate** — **file** `justfile`.
    **check**: `just typecheck`.
    **rollback**: `git revert <commit>`. **done when**: `just typecheck` runs the plugin's
    deny path for both cases and fails if either allows; a node that cannot run it fails
    the recipe rather than skipping, because a proof that stops running without saying so
    still reads green. No receipt is written and opencode's enforcement stays unproven.

### Block C closed, after three review rounds

The added rule earned its place again. Round one rejected the fail-open narrowing; round
two rejected its repairs (the escaping landed in one of three copies, and the plugin test
was writing the operator's real OpenCode heartbeat); round three rejected the repairs to
*those* — the anchor fix appended a trailer after a blank line, which starts a second
trailer block and drops the `Co-Authored-By:` that roughly half this repository's commits
carry. Each round's finding was introduced by the previous round's repair, and none was
found by re-reading.

Three times in this block a test agreed with the defect because it chose the input that
could not see it: a POSIX path cannot see a Windows escape, and a commit message with no
trailers cannot see a trailer being orphaned. Twice the agreeing test was written in the
same commit as the fix it was supposed to prove.

**A correction to the record, because the commit that carries it cannot be amended.**
Commit `f849796a`'s message says the forged heartbeat "reported opencode as proven on a
machine where the plugin is not installed" and that "doctor now says UNPROVEN". All three
parts are false. On this machine opencode *is* installed, it is unwired, and
`doctor.standing` returns at the unwired branch before the heartbeat branch is reached —
so the word read UNPROVEN before and after. `BLOCKS` comes only from an enforcement
receipt and never from a heartbeat. The repair itself is correct and verified: the suite
no longer writes into the operator's home. Only the account of the consequence was
unbacked, written while correcting an unbacked claim, which is now the seventh instance of
that pattern this wave has measured.

### Block R — the record's own fail-open, found while closing Block C

A commit-msg hook failing in front of me, not a search. Diagnosing it produced findings
that belong to the audit chain rather than to any surface, so they get their own block
rather than being folded into one that has already closed.

What is already repaired: the hook appended the verb's whole stdout to the commit message,
so a chain that does not hold wrote a rendered `✗ FAIL` block into it, and `|| true` kept
that silent. Machine state, repaired outside the tree: `git config ai.eng` was read once,
at 2026-08-15T07:46Z, naming an install whose `audit` has no `--anchor` flag, and repointed
at the editable one. That is a single reading of a file with no history — the value at any
earlier moment is not recoverable, so it is a fault that was present, not a fault that can
be dated or blamed for anything.

**Correction, one review round later.** The sentence that stood here said the anchor
"errored on every commit this repository has ever made and no commit in `git log` carries
the trailer". Both halves are false: 111 commits carry an `Ai-Eng-Anchor:` trailer with
this machine's real id, the newest on 2026-08-10 at `seq=917` — the last clean link. I had
probed three commits for a trailer key that does not exist (`Ai-Eng-Audit`), read the empty
result as proof of absence, and wrote it into the correction whose own subject is unbacked
claims.

**And a correction to that correction, one round later again.** It went on to say the
`ai.eng` misconfiguration "is not why the anchors stopped", naming the chain break instead.
That is asserted, not measured. What is measured: there is no commit at all between the
last anchored one (2026-08-10T18:01:14Z) and the first BROKEN link (2026-08-12T12:26:06Z),
so the history has no observation in the window where the two causes could be told apart.
What is **not** measured, and was written here as though it were: that the misconfiguration
was already in effect then. Nothing dates it — `ai.eng` is `.git/config` state with no
history, it has since been repaired, and the chain records no CLI version on any of its 987
links. So the honest statement is that the chain break is sufficient on its own and the
misconfiguration cannot be placed in time at all. Replacing an unmeasured cause with another
unmeasured cause is the same defect wearing the corrected sentence, and doing it a second
time inside the correction is how this section reached three rounds.

What is open, and what this block is for:

12. **A process that is not the operator cannot poison the operator's chain** — **file**
    `hooks/_emit.py`. **check**: `uv run pytest tests/test_record.py -k
    a_foreign_machine_cannot_write_into_this_chain`. **rollback**: `git revert <commit>`.
    **done when**: the buffer follows the same home the sealed chain follows, so a test
    faking `machine_id()` writes to its own buffer; and a buffered line whose stamp names
    another machine is sealed as that machine's, not as this one's tampering. Measured
    today: 22 permanently BROKEN links dated 2026-08-12, each carrying a different fake
    machine id, 11 of them a `pytest-of-…` path in the payload and the other 11 an
    `uninstall` verb record — they come in pairs — written by this product's own test
    suite into the operator's real chain, because the buffer is repository-local and
    `AI_ENGINEERING_HOME` does not redirect it. `ai-eng audit verify`, the command the
    README offers as the tamper detector, therefore fails on this machine for good, and
    `audit --anchor` refuses a footer, so no future commit here can be anchored. One
    poisoned line is a ratchet with no way back.

13. **A break that has been accounted for can be closed without rewriting the chain** —
    **file** `src/ai_engineering/audit.py`. **check**: `uv run pytest tests/test_record.py
    -k an_accounted_break_is_recorded_not_erased`. **rollback**: `git revert <commit>`.
    **done when**: a human with authority can record, as a new link, that a named range of
    links is known-bad and why; verification reports the break and the accounting together
    and stops blocking the anchor; and nothing anywhere deletes or edits an existing link,
    because that is the act the chain exists to detect. Without this, task 12 stops new
    poisoning and leaves this machine's record permanently unusable.

14. **The buffer is sealed, and a buffer that is not sealed says so** — **file**
    `hooks/session.py`. **check**: `uv run pytest tests/test_record.py -k
    an_unsealed_buffer_is_reported`. **rollback**: `git revert <commit>`. **done when**:
    `doctor` reports the age of the newest sealed link and the depth of the unsealed
    buffer, and an unsealed buffer beyond a stated bound is not PASS. Measured on
    2026-08-15: the durable chain has 987 links and stops at 2026-08-12T23:10:45Z, while
    the buffer had 4,499 unsealed lines and is still growing — the depth is a live counter
    and the figure here is the reading, not a property. `flush()` has exactly one caller
    outside the suite, on `SessionEnd`/`Stop`. Half of "survives losing the laptop" went
    stale with nothing said, and `_emit.emit` swallows every failure to one stderr line,
    which is where both of this block's defects lived unseen.

### Blocks D onward — one surface per block, in provability order

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
