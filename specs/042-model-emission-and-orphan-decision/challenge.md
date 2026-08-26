# Challenge — spec 042 round two (revised digest)

Critic reads: the revised `spec.md` and the tree only. Verdict scale: `WRONG` (tree contradicts),
`UNPROVEN` (nothing can decide it), `OK` (tree agrees). Command and actual output follow each
finding. Worst first.

## Round-one corrections — verified

### C1. Inherited red is `MADR_HOME_INVALID` from `specs/*/approval.md`, not `MADR_SCHEMA_INVALID` — OK

Command:
```
uv run python -c "from pathlib import Path; from ai_engineering import madr; print(madr.validate(Path('.')))"
```
Output:
```
Validation(outcome='INCOMPLETE', code='MADR_HOME_INVALID', reason='MADR exists outside docs/adr')
```
The spec's sentence now names the exact code the validator returns. The baseline footnote also
verifies: `uv run --with pytest==9.1.1 pytest -q tests/test_madr.py` → `4 failed, 33 passed`;
`tests/test_intent.py` → `1 failed, 15 passed`, failing on
`tests/test_intent.py:68: assert all(len(entry) <= 240 ...)` — the 240-character ceiling. Both
reds match the spec's "same four test_madr.py failures plus the working-tree test_intent.py red".

### C2. cli.py's two command-emit paths, field lists — OK

Command:
```
grep -n "tier_model\|_machine_result\|emit(" src/ai_engineering/cli.py
```
Output (the two command-emit calls):
```
232  paths.load("_emit").emit(command, "command", verb=command, exit=..., outcome=execution.outcome)
538  paths.load("_emit").emit(verb, "command", verb=verb, exit=code, ms=int((time.perf_counter()-started)*1000))
```
The `--json` path (`_machine_result`, reached via `_json_dispatch` at line 398) emits `verb`,
`exit`, `outcome`; the plain-mode `main()` tail emits `verb`, `exit`, `ms`. The spec's
field-list sentence matches each path exactly. Caveat: neither path carries `tier_model` today
(grep for `tier_model` across `src/`/`hooks/`/`tests/` returns nothing) — B-042-1 is still
proposal, consistent with `status: draft`.

### C3. Digest never printed 8,745 rows; `by_reason` already collapses — OK

Command:
```
python3 - <<EOF … from collections import Counter over ~/.ai-engineering/state/a63ff363e613/ad36fa1441e9.jsonl …
EOF
```
Output:
```
distinct reasons (blocked loop_guard): 5
  8745  this exact call has been made 6 times in the last 6. …
   779  this exact call has been made 4 times …
   777  this exact call has been made 3 times …
   723  this exact call has been made 5 times …
    51  Bash:pytest has failed 6 times in a row …
```
`by_reason` in `report.py:37` is `Counter(f"{name} — {reason}" ...)` — one row per guard–reason
pair; 11,075 blocked loop_guard events collapse to 5 rows, top 8,745, exactly as the spec now
says. The "4 variant rows today" (`6/5/4/3 times`) is also confirmed. The spec's corrected
wording ("the digest never printed 8,745 rows … `by_reason` counter already collapses …") holds.

### C4. 48% / 916 s attributed as surface observation, not digest measurement — OK

Command:
```
grep -rn -i "percentile\|latency\|p90\|failure.rate" src/ hooks/ --include="*.py"
```
Output:
```
hooks/_emit.py:5: work on a hot path where latency is a security property.
hooks/chain.py:6: here latency is a security property, not a convenience.
```
No failure-rate or latency/percentile computation exists; the spec now says the figures are "a
surface observation, not a product computation". The derivable ratio it offers checks out on the
same chain: `blocked/(blocked+command) = 18,650/38,925 ≈ 47.9%` (below), and no `allowed`-class
event exists in the whole 63,847-event chain, so "a clean pass writes no event" is true.

---

## New material — attacked, worst first

### F1. WRONG — the example escalation "has been made 7 times in the last 6" is a state the guard cannot produce

`hooks/loop_guard.py` trims the per-session `recent` list to the last `window` calls before
counting, so the printed repeat count can never exceed the window (6):

```
state["recent"] = (state["recent"] + [call])[-window:]     # window = 6
seen = state["recent"].count(call)
```

Command:
```
grep -c "made 7 times" ~/.ai-engineering/state/a63ff363e613/ad36fa1441e9.jsonl
```
Output:
```
0
```
The entire 63,847-event chain contains no "made 7 times" (and no × ≥ 7) reason; the repeats
family maxes at "made 6 times". The spec's own example escalation text ("this exact call
(pytest -q tests/test_x.py) has been made 7 times in the last 6 — the third identical denial in
this window") therefore describes an unreachable verdict. B-042-4 says the window stays the
per-session `recent` mechanism ("The window is per-session (`state["recent"]` is
session-scoped)"), so the count it escalates with is capped at 6. `WRONG` against
`hooks/loop_guard.py` mechanics and against every recorded event.

### F2. WRONG — "any other verb falls back to `default_tier`" describes the wrong router behaviour

B-042-1: "a verb that maps to a cycle step routes by that step, any other verb falls back to
`default_tier`". The router it says it consumes does no such thing: `route()` returns `medium`
for any verb outside `_LOW_STEPS`/`_TOP_STEPS`, and `default_tier` only when `medium` is unset.

Command:
```
uv run python -c "
import tomllib; from pathlib import Path
from ai_engineering import model_router
cfg = tomllib.loads(Path('.ai/config.toml').read_text()); print(cfg['models'])
print(route('audit'), route('doctor'), route('report'), route('build'))"
```
Output:
```
{'top': 'deepseek-v4-flash', 'medium': 'qwen3.8-flash', 'low': 'qwen3.6', 'default_tier': 'deepseek-v4-flash'}
deepseek-v4-flash qwen3.8-flash qwen3.8-flash qwen3.8-flash
```
With this tree's pin, an unmapped verb records `tier_model = "qwen3.8-flash"`, never
`default_tier`. The same misreading sits in the "What is true today" bullet's partner sentence —
the router's own docstring ("falling back to default_tier when a tier is missing") is what the
spec should quote. As written, B-042-1's contract and the router it wires would disagree on the
majority of commands.

### F3. WRONG — the example register marks `model_router` as consumer, which the register's own refusal (b) forbids in this tree

`policy/module-status.toml` does not exist and `wiring.module_status()` does not exist, so the
register is proposal. But the example row `name = "model_router" / status = "consumer" /
consumer = "src/ai_engineering/cli.py"` fails the spec's own refusal (b) ("a `consumer` row
whose module no production file imports (AST-verified)") against the current tree:
`src/ai_engineering/cli.py` has no import of `model_router`. The event example is explicitly
labelled "after B-042-1/B-042-2"; the register example is not, yet it silently depends on
B-042-1 landing before it can pass the gate it introduces.

Command:
```
python3 - <<EOF  # one AST import walk over src/ + hooks/ and tests/ for model_router
EOF
```
Output:
```
model_router   prod-imports: NONE   test-imports: ['tests/test_037_model_router.py']
```
The same walk confirms the rest of the register's premises: `lane_merge`, `loopgate`, `trim`,
`decision_fw`, `skillify`, `verify_cold`, `evidencing`, `intake` have no production importer;
`revalidate` and `cost` are imported by `src/ai_engineering/audit.py` only. And the
grep-vs-import distinction the spec draws is real: `trim` appears in `loop_guard.py`'s comment
("the trim below drops…") and never as an import.

### F4. WRONG — the example command event cannot exist on this tree's pin / surface

The spec's canonical event (claiming to be "plain mode, on this tree's pin") contains four
values the real emit path cannot produce:
- `"adapter":"1.0"` — `chain.py:276` sets `AI_ENG_ADAPTER = adapter_version("claude-code")`,
  which is `str(1)` = `"1"` (the `claude-code.adapter.json` declares `"adapter_version": 1`);
  `"1.0"` appears in zero of 63,847 chain events.
- `"model":"deepseek-v4-flash"` on `"surface":"claude-code"` — B-042-2 itself states the Claude
  Code adapter sends no `model` key ("surface events read `undetermined` until that adapter is
  taught to send a model"); the adapter payloads (`policy/adapters/*.json`) contain no `model`
  key. The example contradicts the spec's own field semantics.
- `"ts":"…T12:00:00.000Z"` — `_emit.now()` is `datetime.now(UTC).isoformat(timespec="milliseconds")`,
  which every real event shows as `+00:00` (e.g. `"ts":"2026-08-24T23:58:28.827+00:00"`), never `Z`.
- The example omits `operation_id` and `trace_id`, which `_emit.emit` stamps on every event
  (200/200 of the last 200 chain events).

Command:
```
python3 - <<EOF  # print the latest 'command' event and count identity fields in the last 200
EOF
```
Output:
```
{"adapter": "undetermined", "cls": "command", "data": {"exit": 0, "ms": 6, "verb": "decide"},
 "machine": "ad36fa1441e9", "name": "decide", "operation_id": "09d47efc-…",
 "repo": "a63ff363e613", "surface": "undetermined", "trace_id": "00c40959-…",
 "ts": "2026-08-24T23:58:28.827+00:00"}
last 200 with operation_id: 200 | trace_id: 200 | surface: 200 | adapter: 200
surface values: {'undetermined': 187, 'claude-code': 13}   adapter values: {'undetermined': 187, '1': 13}
```
The example's `session: "s-1"` is also stylized (real ids are 12-hex), which is fine for an
example; the four fields above are not cosmetic.

### F5. WRONG — "the thirteen dossiers (this one included once written)" is off by one

Command:
```
ls specs/*/approval.md | wc -l ; ls specs/042-model-emission-and-orphan-decision/approval.md
```
Output:
```
13
ls: cannot access 'specs/042-model-emission-and-orphan-decision/approval.md': No such file or directory
```
The thirteen existing dossiers are 029–041; 042 has none. "This one included once written"
implies the thirteen include spec 042's — they cannot; once 042 is written the count is
fourteen. The corrected phrasing would be "the thirteen dossiers 029–041 (a fourteenth once
this is written)".

### F6. WRONG — B-042-4's promise arithmetic: "1 full verdict + 13 escalations instead of 15 identical sentences"

Today the guard denies occurrences 3–15 of a 15-hit session (occ. 1–2 pass): 13 denials, and
the sentences are not "15 identical" — they are the 4 variants the spec itself lists ("3/4/5/6
times", with ≥7 clamped to 6). Under the proposed rule ("first denial keeps the full verdict;
the third and every later identical denial escalates"), the second denial has no stated
behaviour, and neither reading of "third denial" (third occurrence / third denial event)
produces 1 full + 13 escalations (that sum is 14 messages for 13 denials). Command:
```
grep -n "seen\|recent\] = \|window" hooks/loop_guard.py
```
Output:
```
WINDOW = 6
seen = state["recent"].count(call)
state["recent"] = (state["recent"] + [call])[-window:]
```
The denial–message mapping in the spec does not add up.

### F7. WRONG — the example escalation's "human-visible signature" is not the signature the spec defines

B-042-4 defines the escalation as naming "the repeated call by its human-visible signature
(`tool_name:first_argument`, not the 16-hex `exact()` digest)". `signature()` produces
`Bash:pytest` for `pytest -q tests/test_x.py`; the example instead prints the full command
`(pytest -q tests/test_x.py)`. Command:
```
uv run python -c "import sys; sys.path.insert(0,'hooks'); from loop_guard import signature; print(signature({'tool_name':'Bash','tool_input':{'command':'pytest -q tests/test_x.py'}}))"
```
Output:
```
Bash:pytest
```
Minor, but the example is the only concrete statement of the escalation shape.

### F8. UNPROVEN — every B-042-2/B-042-3/B-042-4 implementation claim (four-state column, register and its four refusals, AST import-graph reader, `escalated=True` digest marking)

Nothing in the tree implements these; the spec is `status: draft`, so this is expected and
consistent — but none of these sentences can be executed:
```
ls policy/module-status.toml            → No such file or directory
grep -n "module_status" src/ai_engineering/wiring.py   → (no hits)
grep -n "model" src/ai_engineering/report.py          → (no hits: no distribution counting exists)
grep -rn "AI_ENG_MODEL" src/ hooks/ tests/            → (no hits)
```
The four refusals (a)–(d), the "AST import-graph walk" reader, the four-state digest line, the
chain-hook `model` passthrough (guardrail "never from `sessionId`"), and the digest relabel of
rule-12 rows are all `UNPROVEN` — they are contracts for future code, and the tree can neither
confirm nor refute them. The one sub-claim that is decidable, "no `model` key in the adapter
payloads", is true: `policy/adapters/*.json` keys are `adapter_version, deny_protocol,
detection, proof, schema, schema_version, surface_id, translations, trust`.

## What I could not test, and why

- The four-state model column, the module-status register, its reader and four refusal tests,
  the AST import-graph walk, the chain-hook `model` passthrough, and the loop_guard escalation
  message / `escalated=True` / digest relabel — none exist in the tree (spec is a draft whose
  B-042-1…4 "land" in a future increment; `policy/module-status.toml` absent, no
  `wiring.module_status`, no model code in `report.py`, no `AI_ENG_MODEL`). Verified only for
  internal consistency and against the machinery the spec claims to extend.
- "ai-goal + the cycle skills name the tier each stage requests" — no `ai-goal` file lives in
  this tree (only provenance mentions in specs/028/031/038/039 and 037's roadmap), so the tier
  naming cannot be executed here.
- `evidencing`'s attribution to "spec 029" — `specs/029…/spec.md` never names the module; only
  `src/ai_engineering/evidencing.py`'s docstring ("Recheck semantics for spec 029 / B-029-3")
  supports it. `verify_cold`→030, `loopgate`/`lane_merge`→031 (incl. B-031-2), `trim`/
  `skillify`→033, `decision_fw`→034, `intake`→037, and `revalidate`/`cost`→030/029 all verify
  by name in their specs.
- Spec 037 "roadmap row 12"/"rows 7/14": the roadmap table's rows are "12-13" (skillify, P2) and
  "7"/"14" (headstart intake P1, B-037-3, "paso 0 de ai-spec") — the spec's citations are
  accurate in substance, off-by-one only in the skillify row label ("row 12" vs "12-13").