---
id: "025"
slug: skill-sequence-map
status: draft
date: 2026-08-25
ref: ""
supersedes: ""
---

# Skill sequence map

## Who this is for, and what it is worth to them

The person who installs the wheel and meets a catalogue of sixteen skills. Today every
skill on their surface shows a phase and one example — `# ai-spec · decide`, "say
something like: …" — and nothing says what to run before it, after it, or whether it can
run alone. The dependency between skills is the question this person is actually asking,
and the answer is not on the surface they see.

The maintainer who dogfoods the governed cycle, who watched one migration this week run
research → spec → challenge → council → brief, then build → review → verify → security →
audit → ship, and who cannot point at one checked artifact that says that order is the
order. Today it is prose in `ai-cycle/SKILL.md`, and nothing in the gate reads it.

When this is done, the order is data with a test, and the router a person meets says what
comes next.

## Context and problem

The order of the governed cycle exists in exactly one place today: the prose list in
`.agents/skills/ai-cycle/SKILL.md` ("First half — up to the person": research, spec,
challenge, council, then a brief and stop; "Second half — after them": build, review,
verify, security, audit, ship). Verified in this session:

- **No test reads that sequence.** `tests/` references `ai-cycle` once, in
  `test_capabilities.py`, and only to assert its capability phase. Rename `ai-research`
  tomorrow and the corpus refusals that name it would fail the gate — but the numbered
  list in `ai-cycle` rots in silence.
- **The pieces of the map already exist as checked data, unconnected.** Phases live in
  `policy/capabilities.toml` and are read by `wiring.phases()`; `PHASE_ORDER`
  `("discover", "decide", "plan", "build", "verify")` is in `wiring.py`; `phase_map()`
  already groups the catalogue for display; the frontmatter flag `context: fork` +
  `background: false` is enforced as a pair by `contract.py`. What is missing is the
  sequence, the gate between the halves, and the fork/parallel markers — none of which
  any of those files knows.
- **The fork marker is real and already meaningful.** Seven skills carry `context: fork`:
  the five critics (challenge, council, review, verify, security) plus `ai-explore` and
  `ai-research`. The cycle's stages can be checked against it.
- **The phases of the cycle stages are monotonic.** research (discover) → spec, challenge,
  council (decide) → build (build) → review, verify, security, ship (verify). The audit
  step is a verb (`ai-eng audit verify`), not a skill — the map must carry verb stages.

The problem, in one sentence: a decision that resolves the same way in every session —
which stage follows which — is written as prose in one SKILL.md, is not checked by any
test, and is not shown to the person who needs it. That is AGENTS.md rule 12 by the book:
"a decision that always comes out the same is code, not a prompt."

This does not contradict the research in `.ai/reports/008-decision-interface.html`, which
is about the *format of outputs* (BLUF, tables, CTA, XML). That decision is separate and
stays open; this specification is about the *order of skills*. The router improvement here
is the prerequisite that makes either output-format change visible where a person meets
the catalogue.

## Options considered

1. **`policy/skill-sequence.toml` as the single source of the order, plus a test, plus a
   "Sigue →" line in the generated routers.** The map is data in its home (`policy/` is
   the data home; `surfaces.toml`, `threat-model.toml`, `capabilities.toml` live there).
   It names the two halves in order, the human gate between them, and per-stage
   `fork`/verb markers. A test (`tests/test_skill_sequence.py`) checks: every name in the
   map exists in the tree (or is a declared verb), phases are non-decreasing along the
   cycle using the existing `PHASE_ORDER`, every stage marked `fork` carries
   `context: fork` + `background: false` in its frontmatter (and vice versa), and the gate
   section separates the halves. `wiring.router_body()` gains one line — the next stage
   from the map — so `install_routers()` shows it on the surface a person actually meets.
   `ai-cycle/SKILL.md` stops restating the list and points at the map, killing the second
   copy. Costs: one policy file (~40 lines), one test file, small changes to `wiring.py`
   (read map, one template line), `ai-cycle/SKILL.md`, and the mut/`test_threat_model`
   assertions that pin router text. Risks: any new cycle stage must be recorded in the
   map or the test fails — which is the point.

2. **Per-skill frontmatter fields: `follows:` and `fork: true` on every SKILL.md.** The
   order becomes a property of each skill, read by the gate. Costs: all sixteen skill
   files edited, `contract.EXTENSIONS` extended, every router and the corpus evaluation
   taught to read a new field, and a fork flag added to skills that are also usable
   standalone. This is a mirror of the map spread across sixteen files, and the failure
   mode is exactly the one the tree already names: "a second copy here would be a second
   answer within a week" (`wiring.py`, on the phase map). The order belongs to the cycle,
   not to any one skill; a skill that can be called alone has no meaningful `follows:`.
   It also bloats the corpus catalogue budget (`CATALOG_MAX = 50_000`) for no new
   information. Loses.

3. **Derive the order automatically from the corpus refusals plus the phases.** The
   hand-off graph already encodes "this skill sends that situation elsewhere". Costs:
   no new data, but the graph is a routing map, not a sequence — nothing in any refusal
   says research runs before spec, or that the human gate sits between council and build.
   The derivation would have to guess, and a guessed map checked by a test is a test that
   asserts what the guesser decided. This also cannot represent the two non-skill steps:
   the brief and `ai-eng audit verify`. Loses.

4. **Keep the prose list in `ai-cycle` and add nothing.** Costs: zero files, and the
   exact defect this specification names — the order is uncheckable prose nobody sees.
   Loses on AGENTS.md rule 12 and on the user-facing gap: a person meeting the catalogue
   still cannot tell what runs next.

## Decision

Option 1. `policy/skill-sequence.toml` becomes the one checked copy of the governed
cycle's order. The map has three parts:

- `first_half = ["ai-research", "ai-spec", "ai-challenge", "ai-council"]` — up to the
  brief;
- `[gate]` — the human approval: a record with the specification's exact digest, which
  is the line between the halves (this is `ai-cycle`'s existing stop, made data);
- `second_half = ["ai-build", "ai-review", "ai-verify", "ai-security", "audit",
  "ai-ship"]` — after the person, with `audit` declared as the verb `ai-eng audit verify`.

Per stage: `fork = true` exactly for the skills whose frontmatter carries
`context: fork` + `background: false`. In the tree today that is research, challenge and
council in the first half, and review, verify and security in the second; spec, build and
ship are not fork. The map is read from the frontmatter at implementation time, never
decided by taste, and the test checks the two agree.
`fork` means the stage runs in its own context for independence; `parallel` at stage
level is refused — `ai-cycle` already refuses "run all six build stages in parallel" —
and the only concurrency is fork-context plus task-level parallelism inside `ai-build`
governed by the plan. The map records that refusal as data instead of prose.

The test reads the map, the skill tree and `capabilities.toml` (via the existing
`wiring.phases()` — no second copy of phases), and fails on: a stage name that is neither
a skill nor a declared verb, a non-monotonic phase sequence, a fork flag that disagrees
with the frontmatter, an empty gate, or a stage appearing twice.

The router: `router_body()` adds one line for cycle stages — `Sigue en el ciclo: <next
stage>`, and for the stage before the gate, `Sigue: la aprobación humana del brief`. A
skill outside the cycle (ai-explore, ai-debug, ai-note, ai-report, …) gets no line, so
the absence itself says "standalone". `ai-cycle/SKILL.md` is edited to name the map file
instead of restating the numbered list; the narrative about stopping, attempts and
escalation stays.

Because the order constrains every future cycle addition, record the decision as an ADR
at approval: propose `ai-eng decide --madr "the governed cycle's order is checked policy
data"` — proposal, not approval.

## Challenged once

The strongest case against: the map is a *second* source of truth, and `ai-cycle/SKILL.md`
will drift from it — the prose says five stages, the map says four, nobody notices until
a session follows the wrong one.

It fails on two grounds. First, the edit removes the second copy: `ai-cycle` will name
the map as the home of the order ("the sequence lives in `policy/skill-sequence.toml`")
and keep only what the map cannot say — the stop, the attempt budget, the escalation
shape. A file that no longer restates the list cannot drift from it. Second, the test is
the backstop for the copy that remains: every stage name in the map must exist in the
tree, so a rename or removal in either direction fails the gate, and the fork flags are
checked against frontmatter, so the two files that do overlap cannot disagree. What is
left to drift is wording, and wording is not the sequence.

A weaker but real version: regenerating the routers changes their bytes, and tests that
pin router text or digests (the mut suite, `test_threat_model`) will go red. That is
expected and bounded: those assertions are updated in the same commit, and the receipt
already records the new digest as the designed install flow. Not a reason to keep the
order uncheckable.

## Assumptions and unresolved risks

Assumed without proof: no consumer repository outside this tree depends on the exact
router bytes (the router body is generated at install and hashed into the receipt, and
regeneration is the designed path; only this tree's tests pin the text). Assumed: the
five cycle stages before the gate and the six after it are the intended order — this
mirrors `ai-cycle/SKILL.md` as it stands today, and the map is the place to correct it,
in a review, with the diff visible.

Open and named: `ai-explore` carries `context: fork` but is not a cycle stage; the map
ignores it, and the fork check only covers stages the map declares. The word "fork" for
`ai-research` inside the cycle means independent context, not parallel execution — the
map's wording must not read as permission to run it concurrently with `ai-spec`. Whether
the output-format canon from `.ai/reports/008` lands as a persona line, an `ai-report`
addition or a seventeenth skill is a separate decision, still open, and explicitly not
decided here.

## Examples somebody can check

Given `policy/skill-sequence.toml` with a stage renamed to a skill that does not exist,
When the gate runs, Then `uv run pytest -q tests/test_skill_sequence.py` fails and names
the missing stage. The same file with `second_half` reordered so `ai-ship` precedes
`ai-build` fails on monotonic phases. The same file with `ai-review` marked `fork = true`
after its `context: fork` frontmatter line is removed fails on the frontmatter check.

Given the map's `[gate]` section emptied, When the gate runs, Then the test fails: the
line between the halves must be declared.

Given the routers are regenerated (`ai-eng init` on a surface with a commands root),
When a person opens the router for `ai-spec`, Then it contains
`Sigue en el ciclo: ai-challenge`, and the router for `ai-council` contains
`Sigue: la aprobación humana del brief`. Checked by
`uv run pytest -q tests/test_threat_model.py -k router`.

Given the router for `ai-note`, When a person opens it, Then it contains no "Sigue" line:
a skill outside the cycle is standalone by the absence of the line. Same command.

Given `ai-cycle` is invoked after this lands, When it runs the first half, Then it stops
at the brief exactly as it does today; the map changed what is checked, not what happens.
Checked by `uv run pytest -q tests/` staying green.

## Decisions

<!-- One `**D-NNN-NN — <the decision>**` per line, each with a `**Rationale:**` under it.
     `ai-eng decide` does not write here: it writes a record under docs/adr/. -->

**D-025-01 — the governed cycle's order is checked policy data.** The order of the two
halves, the human gate between them and the fork/verb markers live in
`policy/skill-sequence.toml`, verified by `tests/test_skill_sequence.py`, and shown as a
"Sigue" line in generated routers.
**Rationale:** the order is a decision that resolves identically every session; rule 12
makes it code; the router is the surface a person meets.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification changes a CLI/library (`wiring.py`), a policy file and two skill texts; it
adds no service, no URL and no second hop, so the service-shaped boxes are `not applicable`.

- [x] CI/CD — `just check`, run by `.github/workflows/check.yml` on every push; nothing here is deployed and `.github/workflows/release.yml` is what publishes the wheel
- [x] Logs — not applicable, and that is the rule: this spec adds one policy file, one test file and one generated line; every verb still emits the one JSON line `ai-eng digest` reads, and no stage in the map writes anything
- [x] Traces — not applicable, and that is the rule: one process, no second hop, no trace
- [x] Errors — not applicable: the only new code path is `wiring.next_stage`, which reads a file and returns a string; a missing or unparseable map returns an empty map and the router omits the "Sigue" line, and `contract.audit` and the new test both fail the gate if the policy file disappears
- [x] Health and data age — `tests/test_skill_sequence.py` is the age of the map: it runs in `just test` on every gate and fails if the map names a stage the tree does not carry, so the map cannot go stale without the gate saying so
- [x] External check — `.github/workflows/check.yml` runs the whole gate on every push to this repository, and `install-matrix.yml` installs the built wheel on three platforms; what it cannot check is written down in R-025-01 at plan time, because `install_routers` only writes into a surface with a `commands` root and the matrix never exercises one
- [x] Second path — the map is read by two routes that share no line of code: `wiring.skill_sequence` renders the "Sigue" line the routers carry, and `tests/test_skill_sequence.py` asserts the same map against the tree; the fork claim is read off the SKILL.md frontmatter, so the two cannot drift
- [x] Security — `just security`: gitleaks, semgrep and trivy on every push, over a change that adds no dependency and no network call
