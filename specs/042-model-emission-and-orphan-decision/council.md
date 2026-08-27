# Council — spec 042 (revision) "Model emission, consumer wiring and the orphan decision"

Round two of the council on the REVISED specification (spec digest 2026-08-26, second
round against it). The round-one gaps the chairman sent back were checked one by one
against the revision, and the revision's new material — the example event, the example
register, the example escalation, the deferred statuses, the chain-hook pass-through —
was read by the five lenses again, alone, then cross-read. Every finding carries a
command the reader can run; **[run]** marks the ones this council ran, with the output
recorded beside them. Refuted findings are struck through, never erased. The last round
is a chairman who never learns which lens wrote what. Nothing in this file grants
anything.

---

## Round one — five lenses on the revision, each alone

### The five round-one gaps, verified against the revision

- **G-1 — event-volume honesty: CLOSED.** B-042-4 says it plainly: "every denial still
  blocks the call, so the blocked count and the event volume are preserved exactly
  (8,745 blocked events stay 8,745)" (spec line 207), and the digest effect is now an
  honest relabel, not a claimed collapse. **[run]** the counts on the machine's chain
  unchanged: 12,575 loop_guard events, 11,075 blocked, 8,745 identical verdicts; 10,908
  blocked in the 14-day window, 8,745 identical.
- **G-2 — four states named, not merged: CLOSED.** B-042-2 names all four —
  `missing`, `undetermined`, actual (`model`), intent (`tier_model`) — says the digest
  line names which state it counts, and excludes `missing` events, counted separately as
  predating the field (spec lines 155-160).
- **G-3 — owed-a-script relabel, escalation as the script: PARTIALLY CLOSED.** The
  revision states the mechanism correctly — the rule-12 row relabels to "escalated to a
  person N times", and events carrying `escalated=True` are marked already-scripted
  rather than re-flagged. But the relabel depends on an `escalated` field no behaviour
  paragraph creates, and it consumes the rule-12 forcing signal (see the cross-read,
  G-R2). The direction is right; the carrier is missing.
- **G-4 — consumer defined mechanically: CLOSED.** "A production caller is defined
  mechanically: an `import`/`from` statement in `src/` or `hooks/` that binds the
  module, verified by an AST import-graph walk — not a docstring mention, not a prompt
  route, not a sentence in a SKILL.md" (spec line 170). The registration example's
  `consumer = "src/ai_engineering/audit.py"` rows match the real function-local imports
  in `audit.py` (lines 453, 475 — **[run]** `from ai_engineering import revalidate` /
  `cost` inside handlers).
- **G-5 — tier_model is a model string, not a tier label: CLOSED.** B-042-1 says "the
  router returns model strings, never tier labels"; the lowercasing belongs to the *step*
  sets internally (`_LOW_STEPS`/`_TOP_STEPS`), and the recorded value is the configured
  model string verbatim, no normalisation. The round-one confusion (a standard sentence
  with no value to lower-case) is gone, and the fallback sentence is now correct — the
  round-one wording ("any other verb falls back to `default_tier`") was replaced with the
  router's real chain, verified against the code: **[run]** `route()` over the ten CLI
  verbs on this tree's pin → `init/doctor/update/decide/accept/report/exception/uninstall`
  → `qwen3.8-flash` (medium), `spec` → `qwen3.6` (low), `audit` → `deepseek-v4-flash`
  (top) — `default_tier` is reached only when `medium` is absent, exactly as B-042-1 now
  says.

### Lens 1 — What does this increment cost?

- **C-1 — The revision's own digest arithmetic is off by one: after B-042-4 the repeats
  family still has three rows, not "two stable rows".** The escalation begins at the
  **third** identical denial (spec line 199); the guard denies from `seen >= 3`
  (`REPEATS = 3`, `hooks/loop_guard.py`), so denial #1 renders "made 3 times", denial #2
  renders "made 4 times", and only denial #3 onward gets the escalation text. The spec's
  "4 rows today → two stable rows (the full verdict + the escalation)" (line 212)
  merges two distinct full-verdict strings that the mechanism keeps apart. See it,
  **[run]** — simulate the post-change reason keys over the machine's chain, assigning
  per (session, fp) the denial index:
  ```
  repeats-family blocked events simulated: 11024
  9468  escalation
   804  full verdict (denial #1, "made 3 times")
   752  full verdict (denial #2, "made 4 times")
  => distinct rows after B-042-4 (repeats family): 3, not 2
  ```
  Add the unchanged failure arm ("Bash:pytest has failed 6 times in a row…", 51 events)
  and loop_guard carries **four** rows after the change, not two. The spec's own worked
  sentence carries the same error: a session hitting the call 15 times "gets 1 full
  verdict + 13 escalations" (lines 293-294) — 15 denials at seen 3,4,5,… split 2 full +
  13 escalations, never 1 + 13.
- **C-2 — The marquee deliverable ships as a column of zeros, and its enabling change
  is not in the increment.** The model distribution is the headline of B-042-2, but
  every one of the 63,847 durable-chain events and every buffered line predates the
  field. **[run]** `grep -c '"model"' ~/.ai-engineering/state/a63ff363e613/ad36fa1441e9.jsonl`
  → `0`. The first post-ship digest reads `missing: 63,847`, everything new reads
  `undetermined` until an adapter change — "until that adapter is taught to send a
  model" — that the spec names but neither prices nor schedules. The cost of the
  deliverable is paid at ship; the value arrives in a later increment no one owns.
  (The cross-read refutes the stronger accusation — the spec does say "honestly blank";
  see the refutation section.)
- **C-3 — One behaviour's digest dependency is a new report.py change the spec never
  lists as code.** B-042-2 makes the digest report a four-state distribution and
  B-042-4 makes it stop flagging `escalated=True` events — two product changes to
  `report.py` the spec delivers as prose inside behaviour sections, with no shape for
  the post-change lines (see E-4) and no worked count. The cost of the relabel is real
  code; the spec treats it as a labelling side-effect.

### Lens 2 — Can we get out of this, and does it stay honest going back?

- **R-1 — The "already scripted" relabel consumes the only forcing signal rule 12 has,
  and is expensive to walk back.** Today the digest prints a rule-12 row
  "loop_guard · this exact call has been made 6 times … 8745× same verdict each time →
  owed a script" — a signal 2,915 times over threshold (OWED_A_SCRIPT = 3). After
  B-042-4 the digest marks `escalated=True` events as already-scripted, so that row
  leaves the flagging set and a different row reads "escalated to a person N times" —
  which reads as *handled*. AGENTS.md rule 12's sentence is "the prompt that made it
  goes away in the same commit"; the spec's relabel retires the flag without any commit.
  A reader who wants the pre-change view must re-derive counts by hand; the red line
  that made loop_guard's repetition a thing to fix is gone from the product's own
  report. See it: `grep -n "OWED_A_SCRIPT\|same verdict each time" src/ai_engineering/report.py`
  — the flag fires on distinct `name · reason` keys with count ≥ 3, which is exactly
  the loop_guard escalation key the spec proposes to exempt.
- **R-2 — Within the chain hook, one model-less event would freeze the variable for the
  rest of the process under the literal `setdefault` line.** `setdefault` sets the key
  even when the default is `None`, so a later model-carrying payload could never
  overwrite it. **[run]** demo:
  `setdefault("AI_ENG_MODEL", {}.get("model"))` after a model-less event, then
  `setdefault("AI_ENG_MODEL", {"model": "…"}.get("model"))` → the second call is a
  no-op; the variable is locked at `None`. Two facts limit the blast radius — the hook
  is a per-event fresh process (`if __name__ == "__main__"` + `sys.stdin`, `chain.py`
  lines 235-236, 349), so the poison dies with the event; and `_emit` reads
  `os.environ.get(...) or UNDETERMINED` (`_emit.py` surface pattern), so a `None` reads
  as undetermined. But the *real* defect is worse than poisoning — see G-R1.
- **R-3 — The example register is not the register: five rows for eleven named
  modules.** B-042-3 enumerates eleven rows (consumers `model_router`, `revalidate`,
  `cost`; orchestrator-future `lane_merge`, `loopgate`; deferred `skillify`, `intake`,
  `verify_cold`, `evidencing`, `trim`, `decision_fw`). The example file
  (`policy/module-status.toml`, presented with a schema header) contains five. **[run]**
  `grep -c "\[\[module\]\]" specs/042-…/spec.md` → `5` rows; a register copied from the
  example verbatim fails refusal (a) — "a module with no status" — for six modules, and
  hides the two rows that would teach the disambiguation: `cost` (the second `consumer`
  via `audit.py`) and `lane_merge` (the second `orchestrator-future`). The register is
  self-correcting at test time, but the example cannot be the file it is dressed as.

### Lens 3 — The undecidable path: where does the described mechanism stop deciding?

- **U-1 — The escalation names the person channel; it still does not reach a person.
  PARTIALLY CLOSED.** Round one's finding was that the person channel was absent from
  the escalation. The revision names it verbatim — the `ai-eng exception --skip
  "<reason>" --guard loop_guard` recipe — and that recipe exists in the tree. **[run]**
  `grep -n "A person" hooks/_wrap.py` → line 124: `A person — not you — can grant one
  bypass: {recipe}`. What survives: the denial is a `user_message` to the model
  (`tests/test_hooks.py` pins it), so the recipient of "hand it to a person" is the
  entity that cannot hand it to anyone; a human can only grant the bypass if one is
  already watching. "Hands the decision to a person" is a string; the mechanism that
  reaches the person is still not described.
- **U-2 — The digest's relabel depends on an `escalated` field that no behaviour
  paragraph creates.** "the digest … marks events that carry `escalated=True` as already
  scripted" (lines 214-215) — every blocked event in the cited chain carries exactly
  `(fp, reason)` in `data`. **[run]** `python3 -c "… Counter(tuple(sorted((e.get('data')
  or {}).keys())) for e in blocked)"` → `[(('fp', 'reason'), 18650)]`. The one sentence
  that would create the flag — "the denied event's data carries `escalated=True`" — is
  absent; the digest behaviour the spec sells cannot read what B-042-4 describes. This
  is the revision's undone link between the guard's message change and the digest's
  relabel.
- **U-3 — For command events, the "actual" state of the distribution is
  undetermined-by-construction, on the only wired surface.** The `model` field comes from
  `AI_ENG_MODEL` in the emitting process. The chain hook (the only described setter) is a
  per-event subprocess that reads stdin — its environment never reaches the `cli.py`
  subprocess that emits command events. Real command events already read `undetermined`
  for their identity fields. **[run]** newest command event on the durable chain:
  `surface: undetermined, adapter: undetermined` — and `cli.py` has no `environ` handling
  at all (`grep -n "AI_ENG\|environ" src/ai_engineering/cli.py` → no hits). So
  `tier_model` (computed by cli) lands on command events; `model` (reported actual)
  cannot. The spec puts both on the same event and shows both populated in the example
  (see E-2, G-R3).

### Lens 4 — What is taken on trust?

- **T-1 — The founding numbers still re-derive exactly; the revision's honesty fixes
  hold.** **[run]** on `~/.ai-engineering/state/a63ff363e613/ad36fa1441e9.jsonl`:
  63,847 events; 12,575 loop_guard; 11,075 blocked; 8,745 identical verdicts; 14-day
  window 10,908 blocked / 8,745 identical; `blocked/(blocked+command)` = 18,650/38,925 =
  47.9% — the ratio the spec now states with its undefined-denominator caveat; the 48% /
  916 s figures are labelled surface observations the tree cannot reproduce. And the
  by_reason counter: **[run]** 11,075 blocked loop_guard events → **5** distinct rows,
  top row 8,745 — the spec's "the digest never printed 8,745 rows" is exactly right,
  and its "4 rows today" for the variant sentences ("6 times"/"5 times"/"4 times"/"3
  times") is exactly right (rows 777/723/779/8745); the fifth row is the failure arm.
- **T-2 — The quoted chain-hook line cannot run as written: `setdefault` rejects
  `None`.** B-042-2's carrier is
  `os.environ.setdefault("AI_ENG_MODEL", payload.get("model"))` (line 150). On a payload
  without a `model` key — every payload on the only wired surface today —
  `payload.get("model")` is `None`, and `os.environ.setdefault` with `None` raises
  `TypeError: str expected, not NoneType`. **[run]** the literal line against a
  model-less payload:
  ```
  (a) TypeError: str expected, not NoneType
  ```
  A hook that crashes is a hook that denies — the file's own doctrine
  (`chain.py:242-253`, `_wrap.py:4`) — so the one-line carrier, implemented as quoted,
  blocks every tool call on the wired surface. The guarding sentence ("only when the
  payload actually carries one", line 151) describes a conditional the shown code does
  not perform; the correct form is one `if "model" in payload:` away.
- **T-3 — The per-session repeat numbers are honest now. CLOSED.** The revision says
  "583 sessions hit the same sentence at least three times in that session (max 15)" and
  "830 sessions with loop_guard blocks". **[run]** 830 sessions with loop_guard blocks;
  583 sessions carry the identical verdict, and 583 of 583 hit it ≥ 3 times; max 15.
  The "one repeated call" framing is replaced by the per-session reading round one asked
  for.

### Lens 5 — The example nobody wrote (now written; what the new examples decide)

- **E-1 — The register example decides less than it pretends.** Written: file name,
  TOML shape, schema header, five rows, and reasons that cite real spec anchors —
  `loopgate`'s reason (031/B-031-2, 041) is machine-checkable: **[run]**
  `specs/031-…/spec.md:108` `### B-031-2 — Loop termination` names loopgate;
  `specs/041-…/spec.md:26,66` names it. But the file is five of the eleven rows B-042-3
  enumerates (R-3), and the two statuses that need disambiguating — a second `consumer`
  (`cost`) and a second `orchestrator-future` (`lane_merge`) — are the ones cut. The
  example that decides the shape hides the shape's only difficulty.
- **E-2 — The example command event shows a `model` value no described mechanism can
  place on a command event.** The example (line 220, caption "after B-042-1/B-042-2")
  shows `surface:"claude-code"` and `model:"deepseek-v4-flash"`. Its own section says "A
  surface that sends no model reports `model:"undetermined"`" (line 230), and B-042-2
  says the wired Claude Code adapter sends no `model` key — so on the only wired
  surface, surface events read undetermined, and command events cannot receive a model
  at all (U-3). **[run]** the newest real command event on this tree's chain reads
  `surface: undetermined, adapter: undetermined`; no command event carries a model key.
  The example's value is aspiration wearing the format of a record.
- **E-3 — The example escalation's numbers cannot be produced by the guard it
  illustrates.** The example says "this exact call (pytest -q tests/test_x.py) has been
  made 7 times in the last 6 — the third identical denial in this window" (line 269).
  The guard's window is 6 and the count in the sentence is `state["recent"].count(call)`
  over a list sliced to `[-window:]` — the count can never exceed 6. **[run]**
  `grep -n "WINDOW = \|\[-window:\]\|seen = state" hooks/loop_guard.py` → `WINDOW = 6`,
  `state["recent"] = (…)[-window:]`, `seen = state["recent"].count(call)`. And denials
  begin at `seen >= 3` (`REPEATS = 3`), so the *third* identical denial occurs at
  seen = 5, not 7 — "7 times" is off by two from any reading. The signature also omits
  the tool prefix B-042-4 specifies (`tool_name:first_argument` →
  "Bash:pytest -q tests/test_x.py"). The example the revision added to decide the shape
  contradicts the shape's own counting.
- **E-4 — Still no example of the digest output, which is where the revision makes its
  strongest claims.** The four-state distribution line, the "escalated to a person N
  times" rule-12 relabel, "excluded and counted separately", "two stable rows" — none
  has a worked post-change line. The context section quotes today's digest verbatim
  ("Per guard, in the 14 days since 2026-08-12: loop_guard 10908"); the revision never
  quotes the tomorrow it promises. Writing one line would have forced the decisions
  C-1 and U-2 had to make by hand: what the row reads when the state is zero, whether
  "N times" counts events or sessions, and where the `escalated` flag comes from.

---

## Round two — the cross-read (each lens sees the other four, shuffled, never its own)

### Lens A reads C-2, C-3, R-1, R-3, U-2, U-3, T-2, T-3, E-1, E-3, E-4 (not C-1, not its own)

- False alarm? **C-2's "the spec hides a zero column"** — one lens reads C-2 as accusing
  the revision of selling a distribution it knows is blank. The refuting command finds
  the caveat verbatim: `grep -n "honestly blank\|measurable for surfaces" spec.md` →
  B-042-2: "the distribution is measurable for surfaces that do report one, and honestly
  blank for those that do not". The revision does not hide it. What survives of C-2 is
  the part no caveat covers: the enabling adapter change is named but unscheduled — an
  ownership gap, not a honesty gap — and that survivor folds into G-R3.
- What we all missed: **the chain hook's per-event subprocess shape.** U-3 saw the env
  gap, T-2 saw a crashing line, R-2 saw a poisoning — nobody had all three plus the
  hook's fail-closed doctrine. Put together: `chain.py` reads stdin per event; its env
  dies with the process; the literal `setdefault` line raises on the only payload that
  exists today; and "a guard that crashes is a guard that denies" (`chain.py:242-253`).
  [→ G-R1]

### Lens B reads C-1, C-2, R-1, R-2, U-1, U-3, T-1, T-2, E-2, E-3 (not its own [reversibility])

- False alarm? **U-1's "the escalation still cannot reach a person"** — pushed hard by
  one lens, the finding dissolves: the escalation's job is not to notify; it is to make
  the *model* stop retrying and name the escape hatch. The recipe is verbatim in the
  text, and the recipe is the product's only person channel by design
  (`_wrap.py:123-124`). Refuting command **[run]: `grep -n "A person" hooks/_wrap.py` —
  the channel exists, the escalation names it, nothing in the spec's own claims says a
  notification mechanism exists.** The "hand it to a person" sentence overstates what a
  string does, but the finding's force ("the channel is absent") is a false alarm: the
  channel is present and named. Residue (the person is reached only if already
  watching) is a limit the spec's "challenged once" no longer hides.
- What we all missed: **the `escalated` flag is a dependency of the digest's relabel,
  and nothing creates it** — U-2 owned that alone, but crossing it with R-1 ("the
  relabel retires a forcing signal") shows the hole is double: no field, and no
  person-action to replace the flag that goes away. [→ G-R2]

### Lens C reads C-1, C-3, R-2, R-3, U-1, U-2, T-1, T-3, E-1, E-4 (not its own [undecidable path])

- False alarm? **T-2's "the chain line crashes and disables the product"** — one lens
  challenges the severity: the same sentence that quotes the line also states the guard
  ("only when the payload actually carries one — never from sessionId … and never from a
  guess", lines 150-152), so the spec's *prescription* is the guarded reading; a
  competent implementer writes the `if`. Refuting command **[run]: `grep -n "only when
  the payload actually carries one" spec.md` — the guard's intent is in the spec.** What
  survives is not the crash but the *disagreement*: the quoted code and its own
  guarding sentence cannot both be true, and the chain hook's crash-doctrine makes the
  literal reading product-disabling. The dead form and the live form must be told apart
  in the spec itself. [→ G-R1]
- What we all missed: **the "1 full verdict + 13 escalations" sentence and the "two
  stable rows" sentence are the same arithmetic error in two places** — C-1 owned the
  digest rows; E-3 owned the impossible "7 times"; neither had the other. Both come
  from treating the third-denial rule as "everything after the first is an escalation",
  which the guard cannot do because the first two denials still render distinct
  verdict strings. [→ G-R4]

### Lens D reads C-1, C-2, R-1, R-3, U-2, T-1, T-2, E-2, E-3, E-4 (not its own [trust])

- False alarm? **E-2's "the example value contradicts the wired surface"** — the
  example's own caption disarms the contradiction: it is captioned "after
  B-042-1/B-042-2", and the same block says "A surface that sends no model reports
  `model:"undetermined"`" (line 230). Refuting command **[run]: the example block's
  caption — the value is an illustrated populated state, and the author points at the
  undetermined state in the very next sentence.** The "the spec claims claude-code
  reports a model" reading is a false alarm. What survives is the mechanism half: for a
  *command* event, no described setter exists at all — undetermined is not the fallback,
  it is the only possible value, and the example dresses a command event in a surface
  report. [→ G-R3]
- What we all missed: **the `ms` field the spec says does not exist** — T-1 verified the
  honest ratio; the latency sentence ("no latency field exists") was never checked
  against the file it cites. **[run]** 8,010 durable events carry `data.ms` (command
  durations: `spec` 4,749; `doctor` 2,020; `audit` 586; plus the chain's own hot-path
  check, `chain.py:345`, which emits `ms` with its "over 200 ms" error). What is absent
  is *first-response latency* and any percentile — a real gap, but the sentence as
  written is contradicted by the file it describes. [→ G-R5]

### Lens E reads C-1, C-2, R-1, R-2, R-3, U-1, U-3, T-1, T-3, E-3 (not its own [example])

- False alarm? **R-3's "the example register is broken if copied"** — one lens argues a
  copied register fails refusal (a) *loudly*, at test time, so the incompleteness is
  self-detecting; the example is labelled "Example register", and the reader test's
  whole point is to refuse exactly this. Refuting command **[run]: B-042-3's refusal
  (a) — "the reader test refuses a module with no status" — so the omitted rows cannot
  silently ship.** The finding's reach narrows to clarity: the example still cannot show
  `cost` or `lane_merge`, the two rows where the statuses stop being synonyms, and the
  failure mode it teaches is the one the test exists to catch.
- What we all missed: **E-3's impossible counts and C-1's off-by-one rows are the same
  disease** — writing examples and simulating rows are the same act, and the revision
  did one but not the other. Every arithmetic claim in B-042-4 (7 times, 1+13,
  4→2 rows) comes from a mental model of the guard that counts denials as
  interchangeable; the guard's message renders `seen`, which is window-bounded. [→ G-R4]

### Gaps no single lens named *(the cross-read's blind-spot harvest)*

- **G-R1 — The chain hook's pass-through cannot run as quoted, and literal reading is
  product-disabling.** T-2 (a crashing line), R-2 (a poisoning variable), and the
  doctrine lines ("a guard that crashes is a guard that denies") never met in one lens.
  `os.environ.setdefault("AI_ENG_MODEL", payload.get("model"))` raises
  `TypeError: str expected, not NoneType` on every model-less payload — the only payload
  the wired surface produces — and the hook's fail-closed design translates that into
  denied tool calls. The guard sentence ("only when the payload actually carries one")
  and the quoted line cannot both be true; the spec must show the `if "model" in
  payload:` form. *Command:* the two demo snippets in T-2 — **[run]** output
  `TypeError: str expected, not NoneType`.
- **G-R2 — The digest's "already scripted" relabel depends on a field no behaviour
  creates, and retires the only forcing signal rule 12 has.** U-2 (blocked events carry
  only `(fp, reason)`, **[run]** `(('fp', 'reason'), 18650)`) and R-1 (the rule-12 row,
  2,915× over threshold, leaves the flagging set) are one hole: B-042-4 changes the
  denial *text* and the digest's relabel needs an `escalated=True` data field that no
  sentence adds — while AGENTS.md rule 12's "goes away in the same commit" commit never
  appears. The relabel is specified as a fact about events that do not exist.
- **G-R3 — "actual" (`model`) on command events is undetermined-by-construction on the
  wired surface, and the example event dresses it as populated.** U-3 (per-event hook
  subprocess; cli has no env source; real command events read `surface:
  undetermined`) + E-2's surviving half + C-2's survivor (the enabling adapter change is
  unscheduled). The distribution's two states on the only wired chain are `missing`
  (the 63,847-event backfile) and `undetermined` (everything new); the "actual" state
  the example shows populated is the one state no described mechanism can reach for
  command events. *Command:* the newest-command-event key check — **[run]**
  `surface: undetermined, adapter: undetermined`; `grep -c '"model"'` → 0.
- **G-R4 — Every arithmetic claim in B-042-4 is off the guard's real counting.** "7
  times in the last 6" (window-bounded at 6), "third identical denial" ↔ seen = 5,
  "1 full verdict + 13 escalations" (actually 2 + 13 over 15 denials), "two stable rows"
  (actually 3) — four claims, one cause: the escalation's start at the *third* denial
  leaves the first two denials rendering distinct full-verdict strings, and the message
  renders window-bound `seen`, not a denial index. *Command:* the simulation in C-1 —
  **[run]** `9468 escalation / 804 "3 times" / 752 "4 times"` and the window invariant
  grep.
- **G-R5 — "no latency field exists" is contradicted by the file the sentence cites.**
  The revision's honesty about 48% / 916 s is real; the new sentence over-corrects. The
  durable chain carries `data.ms` on 8,010 events — command durations and the chain's
  own hot-path check — so a duration field exists and a stranger can compute medians
  from it; what is genuinely absent is first-response latency and any percentile. The
  sentence should say that, or the next reader will re-derive "the product has no
  latency data" and be wrong. *Command:* the ms aggregation — **[run]** `8010 events
  with data.ms; by name: spec 4749, doctor 2020, audit 586, chain 199, accept 185`.

### Findings cut for carrying no command

*None fell to the cut rule: every round-one finding above carries a command the reader
can run (marked **[run]** where this council actually ran it).*

### Findings the cross-read refuted, with the command that refuted them

- ~~**T-2, severity edition — "implemented literally, the chain line disables the
  product."**~~ Refuted: the same sentence that quotes the line states the guard
  ("only when the payload actually carries one — never from `sessionId` … never from a
  guess", spec lines 150-152); the prescription is the guarded form, and a competent
  implementer writes the `if`. Refuting command **[run]:**
  `grep -n "only when the payload actually carries one" specs/042-…/spec.md` → line 151,
  the guard is in the spec. The survivor — the quoted code and its guard sentence
  disagree, and the literal reading is product-disabling under the fail-closed
  doctrine — lives on as G-R1.
- ~~**E-2, contradiction edition — "the example says the wired surface reports a
  model."**~~ Refuted by the example's own caption: the block is introduced "after
  B-042-1/B-042-2" and its next sentence is "A surface that sends no model reports
  `model:"undetermined"`" (spec lines 220, 230) — the author points at the blank state
  right beside the populated one; the value is an illustrated hypothetical, not a claim
  about the adapter. Refuting command **[run]:** `grep -n "A surface that sends no
  model\|after B-042-1/B-042-2" spec.md`. The mechanism half — a command event has no
  described model source at all, so its `model` is undetermined no matter what any
  adapter reports — survives as G-R3.
- ~~**C-2, honesty edition — "the spec sells a distribution it knows is blank."**~~
  Refuted: B-042-2 states the blankness verbatim — "the distribution is measurable for
  surfaces that do report one, and honestly blank for those that do not" (spec line
  155). Refuting command **[run]:** `grep -n "honestly blank" spec.md`. The survivor —
  the enabling adapter change is named but unscheduled, so the deliverable's value
  arrives in an unowned later increment — folds into G-R3.

---

## Round three — the chairman (the spec, both rounds, no lens names)

The lenses agree on five things. First: every round-one gap the chairman sent back is
closed or honestly narrowed — the volume sentence is exact ("8,745 blocked events stay
8,745"), the four model states are named and separately counted, the rule-12 relabel is
the right direction, the consumer definition is mechanical and AST-verified, and
`tier_model` is a model string. Second: the tree facts the revision cites re-derive
byte-for-byte on this machine — 63,847 events, 12,575 loop_guard, 11,075 blocked, 8,745
identical verdicts, 583 sessions at ≥ 3 with a max of 15, the 47.9% ratio with its
undefined denominator, and the by_reason counter that never printed 8,745 rows. Third:
the fallback sentence in B-042-1 is now exactly what the router does (`medium` when
configured, else `default_tier`, else the empty string) — the revision fixed the one
sentence about its own code that was wrong. Fourth: the register follows the
`skill-sequence.toml` pattern that works, and its reason citations check out against the
specs they name (031/B-031-2, 041, 037 rows 7 and 14 — all found in the tree). Fifth:
the fail-closed commitment is kept everywhere — no behaviour in the revision silently
allows anything.

Where they clash: whether the model distribution is a deliverable or a placeholder at
ship. One reading: the spec says honestly blank, so a column of `missing`/`undetermined`
is the correct first output. The other: the marquee claim ("the distribution can be read
from the product's own events") is repeated without the blankness in the same breath,
and the enabling adapter change is owned by nobody in the increment. Both are true; the
spec should say which sentence is the headline. They also split on the escalation's
reach: the person channel is named and real, and "names the person channel" is honest —
but "hands the decision to a person" is still a message to the machine, and a person is
reached only if already watching.

The blind spots the cross-read caught, that no single lens raised: the chain hook's
pass-through line raises `TypeError` on the only payload that exists today, and its
fail-closed doctrine turns that into a product block (G-R1); the digest's "already
scripted" relabel depends on an `escalated=True` field no behaviour creates, while
retiring the only forcing signal rule 12 has (G-R2); command events' `model` is
undetermined-by-construction on the wired surface and the example event dresses it as
populated (G-R3); every arithmetic claim in B-042-4 — 7 times, 1 + 13, four rows to two —
is off the guard's real counting, which is window-bounded at 6 and starts escalating at
the third denial (G-R4); and "no latency field exists" is contradicted by the 8,010
events that carry `data.ms` (G-R5).

Verdict: the revision closes the five round-one gaps it was sent back with, and its
honesty fixes are real — the volume sentence, the four states, the mechanical consumer,
the model-string, the corrected fallback all survive contact with the code. But the new
material introduces five defects of the same family: the spec's own examples and
arithmetic contradict the mechanisms they illustrate. The example event, the example
escalation, the "two stable rows" and "1 full verdict + 13 escalations" sentences, the
setdefault line, and the unflagged `escalated=True` describe a system its own guard
cannot produce. A reader copying the examples into tests or implementations carries the
contradictions in.

Recommendation: keep the four behaviours as shaped, and fix the new material in place of
the old. In B-042-2, replace the quoted line with the guarded form
(`if "model" in payload: os.environ.setdefault(...)`) and say explicitly that the
reported-actual state on command events reads `undetermined` on the wired surface until
an adapter change this spec names but does not make. In B-042-4, add one sentence
declaring the blocked event's data carries `escalated=True`, and re-derive the digest
claim from the guard's denial index: the repeats family becomes three rows (first
verdict, second verdict, escalation), not two. In the examples, make the escalation's
count window-bounded and its signature tool-prefixed, and show one post-change digest
line so the relabel's shape is decided by the file that has to print it. Leave the rule
12 flag in place until a person-action exists to replace it.

First step: two lines — the guarded `model` pass-through in B-042-2, and the
`escalated=True` field on the denied event in B-042-4 — because until those two lines
exist, the chain half of the distribution cannot run and the digest's relabel reads a
field no event carries.

---

## The two counts

- Gaps that appeared only after the cross-read: **5**
- Findings deleted, for carrying no command or for being refuted: **3**