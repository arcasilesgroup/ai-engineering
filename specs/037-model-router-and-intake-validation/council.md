# Council — 037 model router and intake validation

A five-lens read of `spec.md`, then a cross-read, then a chairman. The lenses never see
each other in round one; in round two each sees the four others relabelled and not its own.
Every finding and every refutation carries a command that was run; its output is written
down below it. Nothing here grants anything.

## Round one — five lenses, each alone

### Cost

What does this change cost, and is the cost claim measurable at the moment of signing?

- **Finding A1 — the economy claim is asserted, not measurable: every example that would
  quantify it dies before asserting anything.** The headline promise ("a stranger on a tight
  budget pays frontier prices for a rename") and the receipt "2 passed" both depend on
  fixtures that do not exist in this tree, so there is nothing yet to measure a saving
  against. The cost of a reader verifying Example 1 is one failed run.
  Command: `uv run --with pytest==9.1.1 pytest -q tests/test_037_model_router.py`
    ```
    no tests ran in 0.00s
    ERROR: file or directory not found: tests/test_037_model_router.py

    === exit: 4
    ```

- **Finding A2 — the measurable economy is thinner than the headline on this machine.**
  The pin maps `top = "deepseek-v4-flash"` and `medium = "deepseek-v4-flash"`, so `route()`
  can return at most two distinct model strings; only steps sent to `low` buy anything
  against today's single-model flow. "Per-repository model tiering" is a two-name relabel
  until a third distinct model is configured.
  Command: `sed -n '/\[models\]/,+8p' .ai/config.toml`
    ```
    [models]
    # Per-repository model tiers (spec 037). Any provider name fits; `default_tier` is used
    # when a tier is not configured. Adjust here, never in framework code.
    top = "deepseek-v4-flash"
    medium = "deepseek-v4-flash"
    low = "qwen3.6"
    ```

- **Finding A3 — the gate that would make the economy durable is not wired.** The
  Production-ready "CI/CD" box says `just check` runs "the new fixtures on every push
  (`.github/workflows/check.yml`)", but the workflow never names them, so a regression in
  the router would sail through the only automated gate.
  Command: `grep -c '037\|intake\|model_router\|models\.schema' .github/workflows/check.yml`
    ```
    0
    ```

### Reversibility

What is hard to un-write?

- **Finding B1 — the only edit to an existing governed flow is committed to paper before
  any consumer exists.** B-037-3 changes `ai-spec`'s procedure (step 0: intake) while
  explicitly deferring the wiring ("task-scoped"); no skill in the corpus mentions the
  intake at all, so the change is present only as prose. Reversing it later costs another
  spec cycle; completing it is deferred work. The additive `[models]` section is by
  contrast the most reversible piece of the whole spec — all keys optional, no migration.
  Command: `grep -c 'validate_intake\|step 0\|intake' .agents/skills/ai-spec/SKILL.md`
    ```
    0
    ```

### The undecidable path

Which claim cannot be decided from the spec as written?

- **Finding C1 — `default_tier` has no value anywhere.** The pin writes no `default_tier`
  key (only a comment says one "is used"), the spec never gives a fallback literal, and the
  fixture that would pin one does not exist. "Degrades to `default_tier`" and "returns the
  `default_tier` value, never empty" are undecidable until code chooses an arbitrary
  default.
  Command: `sed -n '/default_tier/p' .ai/config.toml`
    ```
    # Per-repository model tiers (spec 037). Any provider name fits; `default_tier` is used
    ```

- **Finding C2 — the step→tier mapping is only partially pinned.** The examples fix
  `research→low`, `security→top`, `build→(default_tier)`; the other six named steps
  (`spec, plan, review, verify, audit, ship`) are "the rest to medium" with no enumeration,
  so a reader cannot say what `route("plan")` or `route("audit")` returns. The one command
  the spec offers to decide it exits 4.
  Command: `uv run --with pytest==9.1.1 pytest -q tests/test_037_model_router.py -k default_tier`
    ```
    no tests ran in 0.00s
    ERROR: file or directory not found: tests/test_037_model_router.py

    === exit: 4
    ```

- **Finding C3 — `bail_out(request)`'s predicate has no criterion.** "small enough to
  handle inline" carries no bound (no tool-call count, no context measure). MR-01's real
  criteria (`número de tool calls estimadas…`) live in the cited report, not in this spec
  and not in any fixture.
  Command: `sed -n '/### B-037-2/,+7p' specs/037-model-router-and-intake-validation/spec.md`
    ```
    ### B-037-2 — Step router and cost honesty
    A `src/ai_engineering/model_router.py` (stdlib-only): `route(step, config) -> str` maps
    each step of the governed cycle (research, spec, plan, build, review, verify, security,
    audit, ship) to a tier — cheap work (mechanical edits, spec generation) routes to `low`,
    hard reasoning (architecture, security, review) to `top`, the rest to `medium` — and
    `bail_out(request)` returns whether the work is small enough to handle inline (model-router
    MR-01). The router is a pure function over config, so it is testable without a provider; it
    ```

- **Finding C4 — the validator's "acceptance signal" is never defined.** The four required
  fields are named, but nothing says what counts as "names an acceptance signal", so two
  implementers can disagree on the same opening request; the denial example only names
  absence, never presence.
  Command: `sed -n '/### B-037-3/,+6p' specs/037-model-router-and-intake-validation/spec.md`
    ```
    ### B-037-3 — Validated intake template
    `specs/new-goal-template.md` (a copy-paste template) + `src/ai_engineering/intake.py`:
    `validate_intake(text)` returns `PASS` when the opening request names the goal, the
    constraints, the intended outcome and an acceptance signal, and `INCOMPLETE` with the
    missing fields when it does not. `ai-spec`'s procedure gains step 0: when the opening
    request fails `validate_intake`, ask the intake questions (capped, the way the research's
    ```

### Taken on trust

What is asserted that a reader is asked to take without checking?

- **Finding D1 — a citation is wrong in an author-level detail.** The reference is said to
  name "MR-01/02/03 and the deepsec pre-flight as the gap". It does name MR-01/02/03, but it
  never mentions deepsec; a reader who follows the citation for the pre-flight claim lands
  on a document that does not contain it.
  Command: `grep -ci deepsec .ai/research/reports/02-model-router/report.md`
    ```
    0
    ```

- **Finding D2 — the example receipts are asserted numbers for files that do not exist.**
  "2 passed", "1 passed" (three times) are written as measured facts about
  `tests/test_037_model_router.py` and `tests/test_037_intake.py`, neither of which is in
  the tree.
  Command: `test -f tests/test_037_model_router.py; echo $?`
    ```
    1
    ```

- **Finding D3 — the schema's "Second path" is not what the box claims.** B-037-1 says the
  schema mirrors `capability-manifest.schema.json` (that anchor file exists) and the
  Production-ready box says the schema is asserted by `tests/test_contracts.py`. That file's
  only two "models" hits are governance-agent sentences, not a read of any models schema.
  Command: `grep -n 'models' tests/test_contracts.py`
    ```
    2208: # gap was found: models "never grant authority or accept risk", and until now a bare
    2283: The constitution says models "may investigate, propose and review; they never grant
    ```

  (Verified, not trusted: the claims that `cost.py` holds no tier/route code and that the
  pin now carries `[models]` both check out, the latter in commit `30f8ec1e`.)

### The example nobody wrote

Which example is asserted but not written?

- **Finding E1 — the four Examples are unwritten promises.** Every "Then" in "Examples
  somebody can check" is backed by a command that dies "file or directory not found". Run
  against the current tree, all of them exit 4; the receipts are future tenses.
  Command: `uv run --with pytest==9.1.1 pytest -q tests/test_037_intake.py -k incomplete`
    ```
    no tests ran in 0.00s
    ERROR: file or directory not found: tests/test_037_intake.py

    === exit: 4
    ```

- **Finding E2 — the template example is doubly unwritten.** Its input file,
  `specs/new-goal-template.md`, does not exist, so there is no template whose "own example"
  could pass; the copy-paste contract is asserted over a file that is absent.
  Command: `test -f specs/new-goal-template.md; echo $?`
    ```
    1
    ```

- **Finding E3 — no example or fixture exercises the `PASS` branch at all.** The only
  intake example even intimated is the denial; the spec's headline claim — "a well-formed
  free-form request passes without ever seeing the template" — has no example and no
  fixture name anywhere.
  Command: `test -f tests/test_037_intake.py; echo $?`
    ```
    1
    ```

## Round two — the cross-read, relabelled, and none sees its own

Each lens sees the other four answers, shuffled, and is asked two things: which finding is
a false alarm (and what command shows it), and what did all of us miss. Rankings were not
taken. Refutations carry commands that were run.

### What the cross-read struck through

- ~~**Finding R1 — the spec is fiction: the pin never gained `[models]`, so per-repository
  tiering cannot exist in this tree.**~~ — refuted by
  `sed -n '/\[models\]/,+8p' .ai/config.toml`, which prints the section (added in commit
  `30f8ec1e`, `+6` config lines). The section is real.
    ```
    [models]
    # Per-repository model tiers (spec 037). Any provider name fits; `default_tier` is used
    top = "deepseek-v4-flash"
    medium = "deepseek-v4-flash"
    low = "qwen3.6"
    ```

- ~~**Finding R2 — the cited model-router report does not exist, so the MR-01/02/03
  citation cannot be checked.**~~ — refuted by
  `test -f .ai/research/reports/02-model-router/report.md`, which prints `present`; the MR
  rows are in it.
    ```
    present
    ```

- ~~**Finding R3 — the step→tier mapping appears nowhere, so nothing of the reference's
  routing content is preserved.**~~ — refuted in part by
  `sed -n '100,105p' .ai/research/reports/02-model-router/report.md`, which prints the
  reference's own routing sentence ("mecánico → cheap, reasoning → expensive"). The general
  shape is preserved; only the per-step enumeration is undecidable (C2 stands).
    ```
    1. MR-01 → Guard de orquestación: implementar un bail-out determinista antes de spawnear ...
    2. MR-05 → Verificación post-delegación: el orquestador siempre verifica resultados ...
    3. MR-02 → Tabla de costos configurable: crear un recurso de economía de modelos ...
    4. MR-03 → Fan-out con model-per-chunk: cuando se fan-out, cada chunk lleva su model ...
    5. MR-06 → Criterio de routing: documentar los criterios de "route on shape" ...
    ```

- ~~**Finding R4 — the "Second path" box is backed: `tests/test_contracts.py` already reads
  the models schema (two grep hits).**~~ — refuted by
  `grep -n 'models' tests/test_contracts.py`: hits are at lines 2208 and 2283, both
  governance-agent wording, and no `policy/models.schema.json` exists to be read.
    ```
    2208: models "never grant authority or accept risk"
    2283: models "may investigate, propose and review; they never grant
    ```

### What the cross-read caught that no single lens named

The misses, written down so the count can be recomputed rather than believed
(listed under their own heading below).

## Round three — the chairman wrote this

Nobody here knows which lens said what. This is new text, not a ranking.

**What the lenses agree on.** The chosen shape is small and reversible: one config section,
one stdlib module, one template and validator, no new dependency and no network call. The
reference's real routing content — route down for mechanical work, route up for hard
reasoning, bail out early — is genuinely preserved in spirit. The pin change is real and
verified (`[models]` present, commit `30f8ec1e`), and so is the in-code claim about
`cost.py` holding no tier/route table. The intake idea (validate shape, not form; a
well-formed free request should pass untouched) is sound and matches the user's API-input
analogy. And every "measured" example receipt in the spec is currently unverifiable.

**Where they clash.** Whether the missing artifacts make the spec *not ready* or merely
*unwritten* — everyone agrees the receipt language is premature, not everyone agrees it
blocks. Whether the economy is a real saving or, on a machine whose `top` and `medium` are
the same model, a two-name relabel. And whether the silent drop of MR-03 (model-per-chunk
fan-out) and MR-05 (post-delegation verification) is an honest scope choice or a claim of
"the reference's real content is preserved" that overreaches.

**Blind spots the cross-read caught.** Only in the second round did it surface that the
`PASS` branch of the intake has no example and no fixture — every example and every lens
was working around the denial path. Only then did it surface that `bail_out` cannot be
imported at all today, that MR-03/MR-05 disappear while a section claims the reference is
preserved, and that the pin changed (`[models]`) while the schema that is supposed to
describe that section does not exist. One lens nearly reported the missing "Second path"
as wired because `grep -c` on `test_contracts.py` returns a nonzero 2 — the two hits say
nothing about a schema.

**Verdict.** The design is right and small, but the evidence layer the reader is asked to
sign describes artifacts that are not in this tree: all four example commands exit 4, and
the schema, template and module are all absent. The claims that could be checked did check
out; one citation (deepsec in the model-router report) is wrong; and at least two reference
findings (MR-03, MR-05) are dropped without a word while the spec says the reference's
content is preserved. Read as a design, this is sound. Read as a *measured* specification,
as its receipts insist, it does not yet stand.

**Recommendation.** Land the artifacts and their fixtures before the "Examples somebody can
check" receipts are claimed: `src/ai_engineering/model_router.py`, `intake.py`,
`specs/new-goal-template.md` and `policy/models.schema.json`, together with
`tests/test_037_model_router.py` and `tests/test_037_intake.py` carrying exactly the
example cases. Correct the deepsec attribution or move the pre-flight citation to the
document that carries it. Decide MR-03 and MR-05 explicitly — carry them or mark them
out of scope — instead of silently dropping them under a "preserved" claim. And pin
`default_tier`'s fallback value in both the config and the degraded example before the
"never empty" promise can be tested.

**One first step.** Ship `policy/models.schema.json` and a `tests/test_037_model_router.py`
containing the three example cases, and leave the `-k default_tier` degraded receipt intact
so Example 1's "2 passed" stops being unmeasurable; if fixtures must lag, demote the
Examples section from measured language to intended.

The three sections below are the only ones a script reads. Their bullet counts must equal
the two totals stated at the bottom; the counts were recomputed below rather than trusted.

### Gaps no single lens named

- **M1 — no example or fixture exercises the `PASS` branch of `validate_intake`**; only the
  denial path is even intimated, and it is dead (its file does not exist). Every lens
  reasoned around the denial example without noticing the success path was never written.
  Command: `uv run --with pytest==9.1.1 pytest -q tests/test_037_intake.py -k pass`
    ```
    no tests ran in 0.00s
    ERROR: file or directory not found: tests/test_037_intake.py

    === exit: 4
    ```

- **M2 — the cited reference's MR-03 (model-per-chunk fan-out) and MR-05 (post-delegation
  verification) are silently dropped** while the Decision claims "the reference's real
  content … is preserved". `MR-03` appears twice in the report; no form of
  fan-out/per-chunk appears in this spec, and no verification rule is added anywhere.
  Command: `grep -c 'MR-03' .ai/research/reports/02-model-router/report.md; grep -ci 'fan-out\|fanout\|per-chunk' specs/037-model-router-and-intake-validation/spec.md`
    ```
    2
    0
    ```

- **M3 — `bail_out` cannot be exercised today**: the module does not exist, so even a
  shape-check call dies unimportably. The function the spec carries over from MR-01 has no
  home in the tree to be tested against.
  Command: `uv run python -c "from ai_engineering.model_router import bail_out; print(bail_out('fix a typo'))"`
    ```
    Traceback (most recent call last):
      File "<string>", line 1, in <module>
    ModuleNotFoundError: No module named 'ai_engineering.model_router'
    ```

- **M4 — the pin changed and the schema that is supposed to describe the change does
  not**; an early adopter configuring `[models]` is told to mirror a schema that is nowhere
  in the tree, so the "any provider fits" contract has no machine-readable form to fit.
  Command: `test -f policy/models.schema.json; echo $?`
    ```
    1
    ```

### Findings cut for carrying no command

- **Cut1 — the router is called "read once per goal" yet also declared a pure function**; a
  pure function has no cache, so the sentence implies a consumer-side memo that fights the
  purity claim. A reading-level tension no single command demonstrates, so it was cut in
  round one rather than written as a finding.
- **Cut2 — "any provider fits, no vendor lock-in" is unfalsifiable today.** On a machine
  whose tiers collapse to two model names, the no-lock-in promise cannot be exercised, and
  the claim that a stranger pays "frontier prices" needs price data no command fetches.
  Cut for carrying no runnable command.

### Findings the cross-read refuted, with the command that refuted them

- ~~**Finding R1 — the spec is fiction: the pin never gained `[models]`, so per-repository
  tiering cannot exist in this tree.**~~ — refuted by
  `sed -n '/\[models\]/,+8p' .ai/config.toml` (section present, added in commit `30f8ec1e`).
    ```
    [models]
    # Per-repository model tiers (spec 037). Any provider name fits; `default_tier` is used
    top = "deepseek-v4-flash"
    medium = "deepseek-v4-flash"
    low = "qwen3.6"
    ```

- ~~**Finding R2 — the cited model-router report does not exist, so the MR-01/02/03
  citation cannot be checked.**~~ — refuted by
  `test -f .ai/research/reports/02-model-router/report.md`.
    ```
    present
    ```

- ~~**Finding R3 — the step→tier mapping appears nowhere, so nothing of the reference's
  routing content is preserved.**~~ — refuted in part by
  `sed -n '100,105p' .ai/research/reports/02-model-router/report.md`, which prints the
  routing sentence "mecánico → cheap, reasoning → expensive".
    ```
    4. MR-03 → Fan-out con model-per-chunk: cuando se fan-out, cada chunk lleva su model
       asignado según su naturaleza (mecánico → cheap, reasoning → expensive).
    ```

- ~~**Finding R4 — the "Second path" box is backed: `tests/test_contracts.py` already reads
  the models schema (two grep hits).**~~ — refuted by
  `grep -n 'models' tests/test_contracts.py`: hits at lines 2208 and 2283 are governance
  wording; no models schema exists.
    ```
    2208: models "never grant authority or accept risk"
    2283: models "may investigate, propose and review; they never grant
    ```

## The two counts

- Gaps that appeared only after the cross-read: **4**
- Findings deleted, for carrying no command or for being refuted: **6**