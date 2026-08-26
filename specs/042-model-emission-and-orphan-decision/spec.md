---
id: "042"
slug: model-emission-and-orphan-decision
status: draft
date: 2026-08-26
ref: ""
supersedes: ""
---

# Model emission, consumer wiring and the orphan decision

## Who this is for, and what it is worth to them

The person who runs `/ai-goal` on this repository and approves what it produces, and every
stranger who installs the wheel for a repository they are accountable for. Spec 037 shipped
the model tiers (`[models]` in the pin) and a step router (`model_router.route`), but
nothing consumes the router and no event names the model that ran a command — so the
`[models]` section is a configured promise with no measurable reader, and the "how many
models, what distribution" question is unanswerable from the product's own telemetry. In
parallel, a set of framework modules (specs 029-037) ships with tests and no production
caller: they float, and a floating module is a decision deferred, not an infrastructure
lane. And the machine's own surface data shows the dominant tool friction: `loop_guard`
blocked 10,908 calls in 14 days, 8,745 of them carrying the identical deterministic verdict
from the same repeated exact call.

This spec closes all three: it wires the router to a real consumer, makes the model a
recorded event field the distribution can be read from, and settles every orphan module
with an explicit checked status. It does not claim a product-measured failure rate or a
latency percentile — those figures are surface observations this tree cannot reproduce,
and this spec says exactly that.

## Context and problem

**What is true today, measured in this tree and on this machine on 2026-08-26:**

- `src/ai_engineering/model_router.py` (spec 037 / B-037-2) maps cycle steps to tiers
  (`research`/`spec` → low, `security`/`review`/`plan`/`audit` → top, the rest → medium)
  with `default_tier` fallback. Its only caller in the tree is `tests/test_037_model_router.py`.
  The pin's `[models]` names `top = "deepseek-v4-flash"`, `medium = "qwen3.8-flash"`,
  `low = "qwen3.6"`, `default_tier = "deepseek-v4-flash"` — a promise nothing reads at
  runtime. The policy reader gate (`tests/test_threat_model.py`) sees the schema read at
  import, so the promise is *validated* but never *consumed*.
- `cli.py` emits one command event per run — through **two** code paths that carry
  different fields. The `--json` path (`_machine_result`, used by `_json_dispatch`)
  emits `verb`, `exit`, `outcome`; the plain-mode tail of `main()` emits `verb`, `exit`,
  `ms`. Both were measured live from `.ai/events.jsonl`. Neither carries a model name.
  `hooks/_emit.emit` stamps every event with `session`, `repo`, `machine`, `surface`,
  `adapter`, `operation_id`, `trace_id`; the surface env vars it reads are `AI_ENG_SURFACE`
  and `AI_ENG_ADAPTER` (set by `hooks/chain.py` for the Claude Code surface); there is no
  `AI_ENG_MODEL` anywhere in the tree, and no `model` key in the adapter payloads
  (`policy/adapters/*.json`).
- This machine's durable chain (`~/.ai-engineering/state/<repo>/<machine>.jsonl`, 63,847
  events spanning 2026-08-08→2026-08-25) records **12,575 `loop_guard` events, of which
  11,075 are blocked**, and **8,745 of those carry the identical verdict** "this exact call
  has been made 6 times in the last 6…". In the 14-day window the user quoted: 10,908
  blocked, 8,745 the identical verdict — reproduced independently by `ai-eng report digest`
  ("Per guard, in the 14 days since 2026-08-12: loop_guard 10908"). The repeats arm counts
  only to the window (`recent` is trimmed to `[-window:]`), so the measured verdicts span
  "made 3 / 4 / 5 / 6 times" — never 7 — at counts 777 / 779 / 723 / 8,745. The identical
  verdict recurs within a session: 583 sessions hit the same sentence at least three times
  in that session (max 15). The digest's `by_reason` counter already collapses identical
  reasons to **one row per reason** (a `Counter` keyed on guard — reason): 11,075 blocked
  events become 5 loop_guard rows, the top one 8,745 — so the digest never printed 8,745
  rows. What rule 12 (`OWED_A_SCRIPT = 3`, `report.py`) measures is the *same judgement
  resolving the same way*: 8,745 identical resolutions of one verdict is the rule-12
  trigger 2,915 times over, and the guard re-asserts the full sentence on every repeat
  instead of escalating after the third.
- The user's reported tool friction (48% of tool calls fail, p90 first-response 916 s)
  is a surface observation, **not** a product computation: `src/` and `hooks/` contain no
  failure-rate or latency/percentile code, and the closest derivable ratio in the chain
  (`blocked/(blocked + command) = 18,650/38,925 ≈ 47.9%`) rests on a denominator the
  product never defines (a clean pass writes no event, so there is no `allowed` count).
  Command events do carry an `ms` duration field (8,010 events on this machine's chain,
  7,811 of them command events), but nothing aggregates it into a percentile. This spec
  does not claim those numbers as its own measurement; it names loop_guard's 10,908
  blocks as the dominant blocked-control cause the digest can show anyone.
- Modules shipped by specs 029-037 with no production (non-test) caller in `src/` or
  `hooks/` by import: `lane_merge`, `loopgate` (spec 031 — the orchestrator's instruments,
  recorded in prose), `trim` (spec 033), `decision_fw` (spec 034), `skillify` (spec 033),
  `verify_cold` (spec 030), `evidencing` (spec 029), `intake` (spec 037 — routed by ai-spec
  paso 0, a skill instruction, not code). `revalidate` and `cost` are imported by
  `audit.py` (specs 030/029) — the pattern that works: a verb reads the module. A text
  grep for any of these names finds docstring/comment mentions (e.g. `evidencing` in
  `verify_cold.py`'s docstring, `trim` in `loop_guard.py`'s comment) that are **not**
  imports — which is why the register's caller check must be import-graph-based.

**The problem, in words a non-technical reader can follow:**

Three promises are not finished. The project lets each repository say which model should
do which kind of work, but nothing in the product actually reads that choice, and the
diary that records every command does not record which model ran it — so nobody can answer
"how many models did we use this week, and how was the work split?" from the project's
own records. Several shelves in the workshop hold tools that were built, tested and never
installed into any workbench: they need an explicit status — in use, waiting for a future
machine, or kept aside with a reason — so a stranger knows which is which. And the safety
gate that stops a repeated call from looping forever is doing its job — but it re-states
the same verdict 8,745 times instead of saying, from the third repeat on, "this has
resolved the same way; hand it to a person".

## Options considered

1. **Wire the router + record the model + decide every orphan + escalate the repeated
   verdict (chosen shape).** The router gains a real consumer (the command event records
   the model string the repository's tiers say the verb should route to, and `ai-goal` +
   the cycle skills name the tier each stage requests, per spec 037's roadmap item 3),
   `_emit` gains a `model` field read from a surface-provided env var exactly like
   `surface`/`adapter`, every orphan module is given exactly one checked status in a
   single register, and `loop_guard` keeps failing closed but escalates the repeated
   verdict to a person from the third identical denial in a window. Gives: measurable model
   distribution from the product's own events, a router with a runtime reader, no module
   left floating, and the dominant blocked-control cause attacked at its root (the
   message, not the count).
2. **Delete the orphans and the router.** The router becomes a dead module and `[models]`
   a documented-unused section; the orphans lose their tests and their shelf space;
   `loop_guard` stays as-is with 8,745 identical denials. Gives: fewer files, but throws
   away working, tested capability (loop terminators for the orchestrator, the extractor
   ai-note already routes to, the revalidation/cost pattern audit already consumes) and
   leaves the dominant friction unaddressed. Rejected: deletion buys nothing for the
   numbers that move the day.
3. **Record the model but don't wire the router; keep the orphans as-is with a doc
   comment.** The event carries the model, but the router's tier mapping stays
   consumption-free, the orphans stay floating, and loop_guard keeps the 8,745 identical
   denials. Gives: the smallest diff, and precisely the state this spec exists to end.
   Rejected for the same reason option 2's "as-is" was.

## Decision

**Option 1.** Four behaviours land in this increment:

### B-042-1 — The router is consumed: the command event records the model the pin says the verb routes to

`src/ai_engineering/model_router.route` gains a production caller in `cli.py`: the
command event's data carries `tier_model` — **the model string** the repository's
`[models]` tiers say this verb should route to. The router returns model strings, never
tier labels; a verb that maps to a cycle step (`spec` → `low`, `audit` → `top`) routes
by that step, and any other verb falls through `route()`'s own fallback — `medium` when
configured, else `default_tier`, else the empty string (the session's own model). Tiers
are lowercased *step* names internally (`_LOW_STEPS`/`_TOP_STEPS`); the recorded value
is the configured model string, verbatim from the pin — no normalisation, because
provider names may be case-sensitive. Both command-emit paths (the `--json`
`_machine_result` and the plain-mode `main()` tail) record it. The `[models]` section is
no longer a promise: every `ai-eng` command event carries the tier-model the pin says
the verb routes to, and `ai-goal` + the cycle skills name the tier each stage requests.
The router never hardcodes a model name; `default_tier` stays the fallback. The spec
makes no claim that the router **picked** the model the run used — the surface chooses
that; the event records the configured intent and, separately (B-042-2), the reported
actual.

### B-042-2 — `_emit` records the model, from the surface like every other identity field

`hooks/_emit.emit` gains a `model` field on every event, read from `AI_ENG_MODEL` the
same way `surface()` reads `AI_ENG_SURFACE`: the surface set it, so the record says so;
the surface did not, so the record says `UNDETERMINED`. `hooks/chain.py` passes through a
payload field named `model` only when the payload actually carries a **string** value
(`if isinstance(payload.get("model"), str): os.environ.setdefault("AI_ENG_MODEL", payload["model"])`
— never from `sessionId`, which is an opaque id always present, never a guess, and never
a non-string that would crash the fail-closed hook; the `isinstance` guard comes first
because `setdefault` with `None` raises `TypeError`). The chain hook's env change covers
events emitted **from that hook process**; a command event emitted by `cli.py` runs in a
separate process, so a surface that wants the `model` field on command events must export
`AI_ENG_MODEL` into the environment it launches `ai-eng` with — the hook pass-through
does not reach it. On the only wired surface today (Claude Code adapter, which sends no
`model` key), surface events read `undetermined` until that adapter is taught to send a
model — the distribution is measurable for surfaces that do report one, and honestly
blank for those that do not. The digest reports the model distribution with the **four
states named, not merged**: `missing` (event predates the field), `undetermined` (surface
did not say), actual (`model` — what the surface reported), and intent (`tier_model` —
what the pin says the verb routes to). The digest line names which state it is counting;
events carrying `missing` are excluded and counted separately as predating the field.

### B-042-3 — Every orphan module gets exactly one checked status, in one register

`policy/module-status.toml` is a single checked register (data + a product reader +
a test, the pattern `wiring.skill_sequence()` established for `skill-sequence.toml`).
One `[[module]]` row per caller-less module, each with exactly one status:

- `consumer` — imported by a production file. Only `model_router` (new, via `cli.py`),
  `revalidate` and `cost` (via `audit.py`) hold this status. **A production caller is
  defined mechanically**: an `import`/`from` statement in `src/` or `hooks/` that binds
  the module, verified by an AST import-graph walk — not a docstring mention, not a
  prompt route, not a sentence in a SKILL.md. The reader test refuses a `consumer` row
  whose module no production file imports, so a decorative import is the only way in and
  is itself visible in the diff.
- `orchestrator-future` — the module is an orchestrator instrument; spec 031 and 041
  record that in prose. `lane_merge` and `loopgate` hold this status. The reader test
  refuses a row marked `orchestrator-future` whose reason does not cite the spec that
  records the orchestrator (031/041), so the parking space is not ungated.
- `deferred` — kept, tested, not wired, with a reason. `skillify` (CLI exposure is
  roadmap P2, spec 037 row 12; the `ai-note` corpus routes it today — a prompt route,
  which is not a production caller), `intake` (a skill routes it — ai-spec paso 0; a code
  consumer is the P1 headstart-intake row, spec 037 rows 7/14), `verify_cold`,
  `evidencing`, `trim`, `decision_fw` (each with the spec that shipped it as the reason
  they exist). Deferred is a visible state, not a deletion: the register is the single
  place where "kept for later with this reason" is said, and a later spec that wires one
  changes the row.

The reader test refuses (a) a module with no status, (b) a `consumer` row whose module no
production file imports (AST-verified), (c) a status naming a consumer that does not
exist, and (d) an `orchestrator-future` row whose reason cites no orchestrator spec.

### B-042-4 — `loop_guard` denies every repeat and escalates the repeated verdict once per window

`hooks/loop_guard.py` keeps failing closed — a repeated exact call is still denied, every
time. What changes is what the denial *says* and, from the third identical denial in a
window, who it is addressed to:

- The first denial of a distinct exact call in a window keeps the full verdict sentence.
- The **third and every later identical denial in the same window** (the rule-12 moment:
  the same judgement has now resolved the same way three times) is denied with the same
  fail-closed decision but an **escalation text** that names the repeated call by its
  human-visible signature (`tool_name:first_argument`, e.g. `Bash:pytest` — never the
  16-hex `exact()` digest), states the repeats count (bounded by the window, so never
  more than `6`), and names the existing person channel verbatim: the
  `ai-eng exception --skip "<reason>" --guard loop_guard` recipe — the one channel in the
  product by which a person can grant a flow-guard bypass (`_wrap.py`). The escalation is
  a *message* change; every denial still blocks the call, so the blocked count and the
  event volume are preserved exactly (8,745 blocked events stay 8,745). The denial event
  for an escalation carries `escalated=True` in its data, and the second denial in a
  window — the one before the rule-12 moment — is the full verdict again, exactly as the
  measured session shape requires (a 15-hit session today emits 13 denials with four
  variant sentences "made 3/4/5/6 times"; after the change it emits the full verdict
  sentences plus escalations, and the variant rows collapse).
- The window is per-session (`state["recent"]` is session-scoped); a new session reopens
  it, and the digest's cross-session collapse already reduces identical reasons to one
  row per reason. The honest effect on the digest: the reason rows for the repeats family
  change from the variant sentences ("6 times", "5 times", "4 times", "3 times" — 4
  rows today) to the full verdict plus the escalation, and the owed-a-script (rule 12)
  row for loop_guard relabels from "same verdict each time → owed a script" to "escalated
  to a person N times" — the escalation *is* the script rule 12 owes, and the digest says
  so by reading `escalated=True` and counting those events as already scripted rather
  than flagging them again.

## The example nobody wrote (written here, because the shape decides the spec)

**Example command event** (plain mode, on this tree's pin, after B-042-1/B-042-2):

```json
{"ts":"2026-08-26T12:00:00.000Z","cls":"command","name":"audit","session":"s-1",
 "repo":"a63ff363e613","machine":"ad36fa1441e9","surface":"claude-code","adapter":"undetermined",
 "model":"undetermined","data":{"verb":"audit","exit":0,"ms":4120,
 "tier_model":"deepseek-v4-flash"}}
```

`model` is what the surface reported — `undetermined` here because the Claude Code
adapter sends no `model` key today (measured adapter values on this machine:
`undetermined`, `""`, or `1`; never `1.0`); `tier_model` is what the pin's `top` row says
`audit` routes to. An event written before this spec has no `model` key at all (state:
missing). The two fields are different facts and the digest never merges them.

**Example register** (`policy/module-status.toml` — the state the plan's task order
produces; `model_router` is `consumer` via `cli.py` once B-042-1's import lands, and the
register test runs on the completed increment):

```toml
schema = "urn:ai-engineering:module-status:1"
schema_version = "1"

[[module]]
name = "loopgate"
status = "orchestrator-future"
consumer = ""
reason = "spec 031 / B-031-2 and 041 record it as the orchestrator's loop terminator; no orchestrator exists yet"

[[module]]
name = "skillify"
status = "deferred"
consumer = ""
reason = "CLI exposure is roadmap P2 (spec 037 row 12); ai-note corpus routes it today; no code consumer until P2"

[[module]]
name = "model_router"
status = "consumer"
consumer = "src/ai_engineering/cli.py"

[[module]]
name = "revalidate"
status = "consumer"
consumer = "src/ai_engineering/audit.py"

[[module]]
name = "intake"
status = "deferred"
consumer = ""
reason = "ai-spec paso 0 routes it (a skill instruction, not code); a code consumer is the P1 headstart-intake row (spec 037 rows 7/14)"
```

**Example escalation text** — the third denial in a window of the exact call
`Bash` → `pytest -q tests/test_x.py`. The signature names the call the way `signature()`
does — `Bash:pytest`, the human-visible form, never the 16-hex `exact()` digest; the
count is the repeats arm's own count, which can reach `6` (the window) but no higher, so
no sentence ever claims more repeats than the window allows:

```
[loop_guard] BLOCKED: Bash:pytest — this exact call has been denied 3 times in the last
6. The loop is bounded; retrying returns what it returned before, and a denial has
already been issued for this call in this window. Hand it to a person:
ai-eng exception --skip "<reason>" --guard loop_guard
```

## Challenged once

**"Recording the model the pin *says* a verb routes to is not recording the model that
*did* run; the distribution would be the config, not reality."** True, and the two are
different facts, so they are two fields: `model` (what the surface reported via
`AI_ENG_MODEL`, B-042-2) and `tier_model` (what the pin's tiers say the verb routes to,
B-042-1). A repo that never sets `AI_ENG_MODEL` and never configures tiers reports
`UNDETERMINED` for the first and the empty string or `default_tier`'s value for the
second — honest unknowns, never a claimed match. The digest names which field it is
counting, and the four states (missing/undetermined/actual/intent) are shown, not merged.

**"Escalating the loop_guard message is cosmetic; the 8,745 denials are the guard doing
its job — a loop that keeps repeating should keep being denied."** The denial never
stops (fails closed, B-042-4); every repeated call is still blocked, so the count is
untouched. What changes is the reason payload — an identical verdict re-asserted 8,745
times is a judgement that has resolved the same way 8,745 times, and rule 12 says the
third resolution becomes a script. The script is: deny, deny with the full verdict, then
deny with the escalation that names the person channel (the `ai-eng exception` recipe).
A session that hits the same call 15 times (measured) today gets 13 denials carrying
four variant sentences ("made 3/4/5/6 times"); after the change it gets the full verdict
sentences plus escalations — the variant rows collapse, and the digest shows the
escalation as the script it is, not as a fresh owed-a-script row.

**"The orphan register is a new policy file; the threat-model test demands every policy
file have a product reader — that is a second copy of the same list."** The register is
data read by one reader (`wiring.module_status()`), the same one-reader pattern as
`skill-sequence.toml`; the threat-model gate sees the new file read by a product module,
and the register test's four refusals are the check that the register cannot drift from
the tree. One home, one reader, one checked truth.

**"An `orchestrator-future` status with a reason citing a spec is prose, not a check."**
The refusal (d) is machine-checkable: the reason must name a spec id (`031`/`041`) and
that spec's file must exist and mention the module. Prose yes — but quoted prose that the
gate verifies, which is the same enforcement `test_skill_sequence.py` applies to the
`[parallel] policy` sentence.

**"The example event shows `model` populated on a surface that sends none; the example
would ship `undetermined` on the only wired chain."** Correct, and the example says so:
`model:"undetermined"` with `tier_model` populated is the honest shape for the Claude
Code surface today, and a surface that exports `AI_ENG_MODEL` to the `ai-eng` process
fills the first field. The example is written that way deliberately — a populated `model`
on a surface that never reports one would be the exact "two copies" fiction the
challenged-once sections of earlier specs were written to end.

## Assumptions and unresolved risks

- Assumption: a surface that knows its model sets `AI_ENG_MODEL`; the field degrades to
  `UNDETERMINED` and nothing breaks for a stranger who never does. The chain hook passes
  through only a payload `model` string, never a guess, and never a non-string that would
  crash the fail-closed hook.
- Assumption: the per-session window is the right unit for the escalation. Measured on
  this machine, 583 of the 830 sessions with loop_guard blocks hit the identical verdict
  at least three times within that session, so the per-session window is where the
  rule-12 moment actually fires. A cross-session escalation would change the loop state
  file's lifetime and privacy posture — not in this spec.
- Unresolved: the product still cannot compute a tool-failure *rate* or a latency
  percentile — a clean pass writes no `allowed` event, so the rate's denominator does not
  exist, and although command events carry an `ms` duration field, nothing aggregates it
  into a percentile. Computing either means emitting an `allowed`/timestamp event on the
  hot path — a telemetry change this spec prices but does not make; the digest's blocked
  counts and rule-12 rows remain the product-measured friction facts.
- Unresolved: `trim` and `decision_fw` may earn a consumer in a later orchestration spec;
  they are `deferred` now with reasons, and the register makes the change visible when it
  happens.
- The inherited red stands, named correctly this time: `madr.validate` returns
  `INCOMPLETE [MADR_HOME_INVALID]` because the thirteen `specs/NNN-*/approval.md` dossiers
  (029-041 today; this spec's will be the fourteenth once its approval record is written)
  score as ambiguous MADR candidates outside `docs/adr/`. It is **not**
  `MADR_SCHEMA_INVALID` from ADR 0025, an attribution earlier specs and the intent
  carried and this spec corrects. Spec 042 does not authorise rewriting that history; the
  gate baseline is the same four `test_madr.py` failures plus the working-tree
  `test_intent.py` red (the pinned intent's `current_facts` entries exceed the
  240-character ceiling), neither introduced by this increment.

## Decision record

**D-042-01 — the router is consumed: every command event carries `tier_model`, the model
string the pin says the verb routes to; the surface's own report is a separate `model`
field.** Rationale: two facts, two fields; a configured intent is not a reported actual.

**D-042-02 — the event's `model` field comes from the surface (`AI_ENG_MODEL` is set only
by a surface that knows, or by the chain hook passing through a real payload `model`
string), and `UNDETERMINED`/`missing` are the honest unknowns.** Rationale: telemetry
observes and never decides — a model the surface did not report is a fact the record does
not have.

**D-042-03 — every orphan module ships with exactly one checked status in
`policy/module-status.toml`: consumer (AST-verified import), orchestrator-future
(reason cites the orchestrator spec), or deferred-with-reason.** Rationale: a floating
module is a decision deferred; the register and its reader make the status as checked as
a skill sequence, and "production caller" is mechanical, not prose.

**D-042-04 — loop_guard denies every repeat and escalates from the third identical denial
in a window; the escalation names the repeated call and the person channel; the blocked
count and event volume never change.** Rationale: rule 12 — the third identical resolution
is a script; the escalation is that script, and a guard that re-states the same verdict
thousands of times is a guard pretending its decision is fresh.