# Plan: model emission, consumer wiring and the orphan decision — 042 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and
this exact `plan.md`**, recorded at their digests in their own record. One repository
writer, on a branch carrying the whole 042 change. Each task is one atomic commit touching
one primary production, policy or skill file plus the files that task names. Rollback for
every task is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the gate in the same
chain as the commit itself. `ai-eng spec show 042 --task <n>` refuses any task whose
digests have moved.

## The order, and why

The event field lands first (B-042-2) because everything else reads it: the red fixture,
then `_emit` gains `model`, then the surface chain hook passes through a payload `model`
field. The router consumption (B-042-1) follows: both command-emit paths in `cli.py`
record `tier_model`, and `ai-goal` + the cycle skills name the tier each stage requests,
pinned by a test. The orphan register (B-042-3) is data plus one reader mirroring
`wiring.skill_sequence()`: the policy file, the reader, the deferred-status assertions,
then the register test. The loop_guard escalation (B-042-4) lands last because its
fixture asserts the digest's rule-12 row relabels without the blocked count moving. Each
task starts with its **red fixture** — the test that fails before the behaviour exists —
implemented in the same commit, exactly as specs 031, 040 and 041 built theirs.

## What this plan is not doing, and why

- **No new verb.** The ten-verb table is pinned by doctrine and `tests/test_contracts.py`;
  `skillify` and `intake` are `deferred` in the register, not wired to a decorative
  import.
- **No change to the tier mapping.** `model_router`'s `_LOW_STEPS`/`_TOP_STEPS` sets and
  the `default_tier` fallback (spec 037) are the contract; this plan adds consumers, not
  tiers.
- **No `AI_ENG_MODEL` guessing.** The chain hook passes through a real payload `model`
  field only; anything else stays `UNDETERMINED`, and old events stay `missing`.
- **No deletion of `verify_cold`, `evidencing`, `trim` or `decision_fw`.** They are
  deferred with reasons in the register; deletion is a later decision a person makes with
  the register in front of them.
- **No claim of a product-measured failure rate or latency percentile.** The 48% / 916s
  figures are surface observations; the digest reports blocked counts, rule-12 rows and
  the model distribution, and no new `allowed`-event hot-path telemetry is added.
- **No acceptance of ADR 0025 / no history rewrite of spec 026.** The inherited
  `madr.validate` red is `MADR_HOME_INVALID` from the `specs/*/approval.md` dossiers;
  it is recorded, not fixed here; the final task asserts no new MADR failure.
- **No change to `.ai/intent.md`, `CONSTITUTION.md`, or the one-writer rule.**
- **No new just recipe and no change to `justfile`/`test_quality_gate.py`** — the new
  suites are picked up by the existing `test` recipe with no wiring.
- **No CI/CD box ticked as new.** Adds no service, endpoint or URL.

## The boundary this plan may not cross

The event field is telemetry (observes, never decides): `_emit` records `UNDETERMINED`
when the surface did not report a model, and no code refuses on a missing model. The
register never writes: it is data read by `wiring`'s reader, and the reader refuses
inconsistency without changing a module. The loop_guard change never weakens a denial:
every repeat is still denied (fails closed); only the message escalates from the third
identical denial in a window.

## Tasks

1. [ ] **Red fixture: the model field and the tier-model on the command event** —
   **file** `tests/test_model_event.py` (new): a command event emitted through
   `paths.load("_emit").emit("audit", "command", verb="audit", exit=0)` carries
   `model` from the `AI_ENG_MODEL` env var when set and `UNDETERMINED` when not;
   `cli.py`'s command event records `tier_model` the pin's `[models]` says `audit`
   (a top step) should route to; a local run with no env and no pin reports
   `UNDETERMINED` for `model` and the empty string for `tier_model` (the session's
   own model, `route()`'s final fallback); with a pin reports the configured model
   string.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_model_event.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before `_emit` and `cli.py` ship the behaviour,
   and green after — the event names the model, honestly or `UNDETERMINED`.

2. [ ] **`_emit` records `model` (B-042-2)** —
   **file** `hooks/_emit.py` (the event dict gains `model = os.environ.get("AI_ENG_MODEL")
   or UNDETERMINED`, beside `surface` and `adapter`, read once per event; the docstring
   names the env var, the honest-unknown rule and the missing-state distinction) + the
   green half of `tests/test_model_event.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_model_event.py -k emit`
   **rollback**: `git revert <commit>`.
   **done when**: every new event carries `model`; no surface, no guess — `UNDETERMINED`;
   an event written before the change is `missing`, never conflated.

3. [ ] **The chain hook passes through the payload's `model` field (B-042-2)** —
   **file** `hooks/chain.py` (when the payload the surface sent actually carries a
   `model` key, set `AI_ENG_MODEL` with `setdefault` beside `AI_ENG_SURFACE`/
   `AI_ENG_ADAPTER`; never read `sessionId` for it — that is an opaque id, always
   present, and using it would make every event claim a model) + the chain fixture in
   `tests/test_chain_read.py` or the event tests.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_chain_read.py tests/test_model_event.py -k chain`
   **rollback**: `git revert <commit>`.
   **done when**: a surface that reports a `model` in its payload produces events whose
   `model` matches; a surface that does not produces `UNDETERMINED`.

4. [ ] **The command event names the tier-model from the pin (B-042-1)** —
   **file** `src/ai_engineering/cli.py` (in **both** command-emit paths —
   `_machine_result` and the plain-mode tail of `main()` — add `tier_model` to the
   emitted command event's data: `model_router.route` for the verb — `spec`/`audit`
   map to cycle steps, every other verb falls through `route()`'s own fallback
   (`medium` when configured, else `default_tier`, else the empty string); the verb
   table's help text and the envelope stay untouched) + the green half of
   `tests/test_model_event.py` (the local-run pin case: `ai-eng audit` emits
   `tier_model` equal to the pin's `top` value; `ai-eng report` emits `medium`).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_model_event.py -k cli`
   **rollback**: `git revert <commit>`.
   **done when**: both emit paths record `tier_model` — `audit` → the pin's `top`
   model string, an unmapped verb → `medium` when configured (else `default_tier`,
   else the empty string); nothing else changes.

5. [ ] **`ai-goal` and the cycle skills name the tier each stage requests (B-042-1)** —
   **file** `.agents/skills/ai-goal/SKILL.md` + `.agents/skills/ai-security/SKILL.md` +
   `.agents/skills/ai-review/SKILL.md` + `.agents/skills/ai-spec/SKILL.md` + a new
   `tests/test_cycle_tiers.py` (each cycle stage's SKILL.md names the tier it requests —
   top for security/review/plan/audit, low for research/spec, medium for build/verify/
   ship — matching `model_router`'s own `_TOP_STEPS`/`_LOW_STEPS` sets, so the router and
   the instruction cannot drift; the test reads both and refuses a mismatch).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_cycle_tiers.py && uv run python tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: every stage names its tier, the test pins the router's sets against the
   skills, and the routing baseline does not move.

6. [ ] **The report digest reports the model distribution with four states (B-042-1)** —
   **file** `src/ai_engineering/report.py` (the digest prints `Models: <count> distinct`
   naming which of the four states it counts — missing / undetermined / actual (`model`)
   / intent (`tier_model`) — counting `missing` separately as predating the field, never
   merging the states) + the fixtures in `tests/test_mut_record.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_mut_record.py`
   **rollback**: `git revert <commit>`.
   **done when**: the digest answers "how many models, what distribution" from the events
   alone, names the state it is counting, and prints an honest "none observed" on an
   empty window.

7. [ ] **Red fixture: the orphan register and its reader** —
   **file** `tests/test_orphan_register.py` (new): a module with no production caller and
   no status in `policy/module-status.toml` is refused; a `consumer` row whose module no
   production file **imports** is refused; a status naming a consumer that does not exist
   is refused; an `orchestrator-future` row whose reason cites no orchestrator spec is
   refused; `lane_merge`/`loopgate` are `orchestrator-future` citing 031/041, `skillify`/
   `intake`/`verify_cold`/`evidencing`/`trim`/`decision_fw` are `deferred`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_orphan_register.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before the register exists, and green after — every
   module has exactly one status, checked by all four refusals.

8. [ ] **The register: `policy/module-status.toml` + the reader in `wiring` (B-042-3)** —
   **file** `policy/module-status.toml` (new: one `[[module]]` row — `lane_merge`,
   `loopgate` `orchestrator-future` (031/041); `model_router` `consumer` via
   `src/ai_engineering/cli.py`, `revalidate`/`cost` `consumer` via `audit.py`;
   `skillify` (037 row 12 P2), `intake` (ai-spec paso 0), `verify_cold`, `evidencing`,
   `trim`, `decision_fw` `deferred` with reasons) + `src/ai_engineering/wiring.py`
   (`module_status()` reads the file and returns the map, mirroring `skill_sequence()`;
   the reader refuses a `consumer` whose module no production file imports, and an
   `orchestrator-future` whose reason cites no spec) + the green half of
   `tests/test_orphan_register.py` (the caller check is an **import graph**, not a text
   grep: `ast` walks `src/` and `hooks/` for real `import`/`from` statements binding the
   module — measured on this tree, `evidencing` appears in `verify_cold.py`'s docstring
   and `trim` in `loop_guard.py`'s comment, and neither is an import, exactly the false
   positive a text grep would count).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_orphan_register.py`
   **rollback**: `git revert <commit>`.
   **done when**: the register names every module exactly once, the reader returns it,
   the caller check is import-graph-based (docstrings and prompt routes are not
   consumers), and the threat-model gate sees the new policy file has a product reader
   (its `rglob` picks the file up and `wiring` reads it).

9. [ ] **The register test asserts skillify/intake are deferred, not consumer (B-042-3)** —
   **file** `policy/module-status.toml` (the `skillify` row is `deferred` with reason
   "CLI exposure is roadmap P2, spec 037 row 12; the ai-note corpus routes it today" and
   the `intake` row `deferred` with "ai-spec paso 0 routes it; a code consumer is the P1
   headstart-intake row, spec 037 rows 7/14") + the green half of
   `tests/test_orphan_register.py` (these two rows are `deferred`, so the test must see
   that `ai-note`'s corpus line and `ai-spec`'s paso 0 are prompt routes, explicitly not
   production callers under the import-graph definition) +
   `tests/test_skillify.py` still green.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_orphan_register.py tests/test_skillify.py tests/test_037_intake.py`
   **rollback**: `git revert <commit>`.
   **done when**: `skillify` and `intake` are provably `deferred` (not silently
   `consumer`), their prompt routes are recorded as not-callers, and their own suites
   still pass.

10. [ ] **Red fixture: loop_guard escalates the repeated verdict, count preserved** —
    **file** `tests/test_loop_guard_escalation.py` (new): three identical exact calls in a
    window produce three `blocked` events — the first carries the full verdict, the third
    carries the escalation text naming the call by its human-visible signature, the
    repeats count and the `ai-eng exception --skip … --guard loop_guard` recipe, and the
    `escalated=True` marker; a fresh window restarts the count; a different call is
    unaffected; the blocked count and event volume are preserved).
    **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_loop_guard_escalation.py`
    **rollback**: `git revert <commit>`.
    **done when**: the fixture is red before the guard changes, and green after — every
    repeat is still denied, the message escalates from the third, the count is intact.

11. [ ] **`loop_guard` escalates per window (B-042-4)** —
    **file** `hooks/loop_guard.py` (the repeats arm keeps denying every repeat; the first
    denial of a distinct exact call keeps the full verdict; the **third and every later
    identical denial in the window** return the escalation text naming the call by its
    human-visible signature `tool_name:first_argument`, the repeats count, and the
    person channel verbatim `ai-eng exception --skip "<reason>" --guard loop_guard`;
    events carrying the escalation are emitted `blocked` with `escalated=True`) + the
    green half of `tests/test_loop_guard_escalation.py` + `report.py`'s rule-12 row
    relabels loop_guard's escalation as already-scripted rather than re-flagging it.
    **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_loop_guard_escalation.py tests/test_mut_record.py`
    **rollback**: `git revert <commit>`.
    **done when**: three identical calls in a window yield one full verdict + one or two
    escalations (never the identical sentence four times), the blocked count and event
    volume do not move, and the digest shows the escalation as the script rule 12 owes —
    not a fresh owed-a-script row.

12. [ ] **The gate** —
    **file** none (verification).
    **check**: `just check`
    **rollback**: `git revert <commit>`.
    **done when**: `just check` reports exactly the same pre-existing failures as before
    this block — the four `test_madr.py` failures (`MADR_HOME_INVALID` from the
    `specs/*/approval.md` dossiers, correctly attributed this time) + the working-tree
    `test_intent.py` red, neither introduced by this increment — no new failure, the new
    suites pass with their clean controls, and the spec, plan and approval of 042 are
    committed at their exact digests.