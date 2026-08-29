---
id: "047"
slug: autonomous-cycle-wall-budget
status: draft
date: 2026-08-29
ref: ""
---

# Plan: autonomous cycle with a wall budget

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and
this exact `plan.md`**, recorded at their canonical digests in their own `docs/adr/`
record. One repository writer, on one branch. Each task is one atomic commit; rollback for
every task is `git revert <commit>`.

**This plan is not edited while it is executed.** Each check names exactly one command,
because `ai-eng spec show --tick` executes the one command a box carries; the prose beside
each check states everything else the task must hold.

## The order, and why

The constants land first (1) because PO-27's evidence command greps for them and every
later file reads the numbers from that one home. The red fixture (2) precedes every green
it demands: the vitals reader (3, 4) and the critic boxes (5) land under it. The batched
gate (6) is independent and lands before the goal rules (7), because the goal's
anti-stall rule names `check-all`. The close (8) is the smoke and the record.

## Tasks

1. [x] <!--t:3a9b73e7df1f--> **The budgets join contract.py** —
   **file**: `src/ai_engineering/contract.py` — add `CYCLE_WALL_BUDGET_MINUTES = 180`,
   `CRITIC_TIMEBOX_MINUTES = 40`, `CRITIC_CALLS_MAX = 120` beside the other named
   budgets, each comment naming its source: 180 is the owner's decision of 2026-08-29
   (PO-27's row carries it), 40 divides the ceiling across five critics run serially,
   120 divides the postmortem's measured 409-call session across the same five and
   rounds down. The numbers are derived, and the comments say so — no constant pretends
   to be a measurement it does not have.
   **check**: `uv run python -c "from ai_engineering import contract; print(contract.CYCLE_WALL_BUDGET_MINUTES, contract.CRITIC_TIMEBOX_MINUTES, contract.CRITIC_CALLS_MAX)"`
   **rollback**: `git revert <commit>`; PO-27 reopens with it, no reader exists yet.
   **done when**: the three names import and print `180 40 120`, and they are the only
   place the numbers live.

2. [x] <!--t:5173586b76ec--> **The red fixture: timebox pins and the vitals arithmetic** —
   **file**: `tests/test_cycle_budget.py` — planted-fixture tests, red now: (a) each of
   the five critic skills names both bound numbers and the `TIMEBOXED` exit; (b) a
   two-hour event stream for one session parses to minutes attributed per `cls` beside
   the wall time first-to-last `ts`; (c) a 200-minute stream exits `INCOMPLETE` naming
   `OVER_BUDGET`; (d) a 90-minute stream exits `PASS`; (e) an event stream with no
   session match exits `INCOMPLETE [NO_DATA]` rather than passing on emptiness.
   **check**: `uv run --with pytest==9.1.1 pytest -q --collect-only tests/test_cycle_budget.py`
   **rollback**: `git revert <commit>`; a red file asks nothing of CI.
   **done when**: the file is committed, this check exits zero — the fixture collects,
   which means every import of `vitals`/`contract` lives inside a test body — and the
   run itself is red naming every missing half. Red for the right reasons: collectable
   shape, failing assertions, not an ImportError wearing a red.

3. [x] <!--t:6562d07c90e1--> **The vitals reader** —
   **file**: `src/ai_engineering/vitals.py` (new, stdlib-only) — reads
   `.ai/events.jsonl` for one session id, attributes minutes between consecutive `ts`
   stamps to the earlier event's `cls` (command, blocked, error, bypassed), computes
   wall time first-to-last `ts`, and returns the outcome: `PASS` inside
   `CYCLE_WALL_BUDGET_MINUTES`, `INCOMPLETE [OVER_BUDGET]` naming the largest bucket,
   `INCOMPLETE [NO_DATA]` when the session matches nothing. Never an approval from the
   clock alone: it reports arithmetic.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_cycle_budget.py -k "vitals or budget or no_data"`
   **rollback**: `git revert <commit>`; the reader has no caller yet.
   **done when**: those tests are green and the module imports nothing outside stdlib.

4. [ ] **The verb: `ai-eng report vitals`** —
   **file**: `src/ai_engineering/report.py` (subcommand `vitals --session <id>`,
   printing per-phase minutes and the verdict), `src/ai_engineering/cli.py` (the will
   banner names it — a writer the banner omits is a false statement about a run,
   D-046-05's rule).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_cycle_budget.py -k verb`
   **rollback**: `git revert <commit>`; the banner and the subcommand move together.
   **done when**: the command prints minutes and a verdict for a session it is given,
   exits zero inside budget, and `ai-eng report --help` lists `vitals`.

5. [x] <!--t:6ba2e0bdb287--> **The critics carry their box** —
   **file**: `.agents/skills/ai-challenge/SKILL.md`, `ai-council`, `ai-review`,
   `ai-verify`, `ai-security` — each gains the bound in its own voice: the timebox in
   minutes and calls (read from contract by the test, written as text here), the I/O
   contract ("the verdict returns in your result; you write no files"), and the
   `TIMEBOXED` exit with what it has when the box closes. The quoted corpus situations
   stay untouched — `skill_eval` counts only those.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_cycle_budget.py -k timebox`
   **rollback**: `git revert <commit>`; all five move in one commit or none.
   **done when**: the timebox pins are green, `RAN skilleval=428` still prints delta 0,
   and the fog ratchet passes.

6. [ ] **The batched gate: `just check-all`** —
   **file**: `justfile` — a `check-all` recipe running every `check` step with just's
   `-` prefix (verified present in 1.58: it continues after failure), collecting the red
   step names and exiting non-zero at the end with the full list; `check` itself does
   not change. A test asserts the prefix appears in `just -n check-all` output, because
   a recipe that quietly lost its prefixes is `check` wearing a new name.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py -k check_all`
   **rollback**: `git revert <commit>`; nothing calls the recipe yet.
   **done when**: the test is green and `just -n check-all` prints every step prefixed.

7. [ ] **The goal stops waiting and says so** —
   **file**: `.agents/skills/ai-goal/SKILL.md`, `ai-build` — the anti-stall rule: no
   step of an unattended cycle waits for input; a refused command is repaired or the
   turn closes with one `BLOCKED: <what> — unblock: <one thing>` line naming it; at the
   close, the goal prints `ai-eng report vitals` beside `ai-eng audit verify`. The
   batch rule from the postmortem lands beside it: one red never relaunches the whole
   gate — accumulate, repair in batch, one `check-all` pass.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_cycle_budget.py -k goal`
   **rollback**: `git revert <commit>`.
   **done when**: the goal test is green and the two skills name `check-all` and
   `report vitals` by their real commands.

8. [ ] **The close: smoke, ledger, record** —
   **file**: `docs/requirements.toml` untouched (PO-27's evidence command now answers —
   verify it), `CHANGELOG.md` — run the whole targeted set, print vitals on the live
   session, and state in the changelog what the budget does and does not decide.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_cycle_budget.py tests/test_requirements_ledger.py -k "cycle or ledger or commitment"`
   **rollback**: `git revert <commit>`; the record moves with the smoke.
   **done when**: every test named here is green, `grep -n CYCLE_WALL_BUDGET_MINUTES
   src/ai_engineering/contract.py` answers (PO-27's own command), and the changelog says
   the clock disqualifies and never approves.
