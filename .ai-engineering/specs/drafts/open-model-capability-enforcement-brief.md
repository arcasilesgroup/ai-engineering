---
title: "Open-Model Capability Enforcement — make the measured nan.builders capability data load-bearing instead of inert"
status: draft
audience: framework-dev / operator
branch: feat/open-model-capability-enforcement
length_estimate: spec (4 milestones M0-M3, 3 concerns, ~25-35 files across canonical + generated mirrors; no new surface)
authoring_style: diagnostic-brief
principles_required:
  - "§10.1 KISS"
  - "§10.2 YAGNI"
  - "§10.4 DRY"
  - "§10.5 TDD"
  - "§10.6 SDD"
delivery_mode: /ai-build
mantra: "We measured what the open models do. Nothing reads the measurement."
---

# Open-Model Capability Enforcement

> Successor to shipped **spec-201** (`three-layer-open-model-harness`, squash
> `6c9b9a4c`), which admitted non-Claude engines into the audit plane, collapsed
> seven skill trees to two, ported a guard plane to OpenCode, and recorded a
> measured per-family capability table. It deliberately stopped short of consuming
> that table at runtime and escalated one assignment it could not derive
> (`.ai-engineering/specs/archive/spec-201-three-layer-open-model-harness/spec.md:102-126`).
>
> This brief is written against the repository at `6c9b9a4c` with a green suite
> (9054 passed, 26 skipped, 2 xfailed), `skill_lint --check` exit 0, `ai-eng check`
> 7/7, and `ai-eng dev sync --check` clean. Every claim below cites a line that
> exists on `main` today.

## 1. Vision

`ai-engineering` already knows how DeepSeek v4 Flash, Qwen 3, MiMo v2.5, Kimi, GLM
and Gemma behave, because spec-201 probed them against a live OpenAI-compatible
endpoint and wrote the results down: which family honours a strict JSON schema
server-side, which leaks reasoning text into a message field, which fabricates
absolute working directories in shell commands, and what the smallest usable
completion budget is
(`scripts/sync_mirrors/tool_name_map.py:100-136`). That table is the single most
valuable open-model asset in the repository, and exactly one field of it is read by
production code — the Copilot tool-rename map
(`scripts/sync_mirrors/core.py:183`). Every measured behavioural field is exercised
only by its own unit test.

The vision is narrow and mechanical: make the measurement load-bearing. A family
that was measured to violate a JSON schema under HTTP 200 should cause the framework
to validate client-side rather than trust the status code. A family measured to leak
`reasoning_content` should have it stripped before parsing. A family measured to
fabricate absolute paths should meet a guard that expects it. And the token telemetry
that already resolves `deepseek` should also resolve `qwen` and `mimo`, because the
capability table proves the framework can name them.

Parity with Opus 5 or Fable 5 is not a claim about model intelligence — it is a claim
that the deterministic plane behaves identically regardless of who drives it, and that
where an open family is measurably weaker, the framework compensates deterministically
instead of hoping.

## 2. Scope Boundary

**In scope.**

- Wiring the measured capability fields (`schema_enforced_server_side`,
  `min_completion_budget`, `reasoning_field`, `fabricates_absolute_paths`) into the
  code paths whose correctness they govern.
- Collapsing the two divergent model vocabularies onto one resolver so
  `gen_ai.system` attribution covers every family the capability table names.
- Resolving the D-201-16 judge-independence assignment that spec-201 escalated, and
  removing the `strict` xfail that pins it open
  (`tests/architecture/test_agent_model_independence.py:88-108`).
- Removing the whitelist contradiction that grades a valid model override as a defect
  (`tools/skill_domain/rubric.py:652-657` vs `scripts/sync_mirrors/core.py:424-435`).
- Extending the advisory replay gate so a skill or agent edit can actually trigger it,
  and so the corpus covers the families the operator runs.

**Explicitly NOT in scope.**

- **Model management.** D-189-01 stands, reaffirmed as D-201-20
  (`.ai-engineering/specs/archive/spec-201-three-layer-open-model-harness/spec.md:408-417`).
  Nothing here detects, routes, ranks, selects or calls a model on the operator's
  behalf. Consuming a build-time table is not dispatch.
- **Per-family prose variants of skills or agents.** No `profile: full | lean` axis,
  no branch-by-model instruction sets. Two payloads for one contract is the
  no-twin axiom violation the repository already forbids
  (`.ai-engineering/reference/surface-axioms.md`).
- **Recalibrating `effort:` per model.** `effort` is a semantic capability
  declaration, not a per-provider tuning knob
  (`scripts/sync_mirrors/core.py:381-394`).
- **Promoting the replay gate to blocking.** D-201-18's rationale — provider uptime
  and quota on the merge path — is unchanged.
- **New surfaces, new hook events, new agent trees.** D-201-22 stands.
- **The graph layer and governance-plane adapter.** Out-of-repo, per spec-201.

## 3. Diagnostic Snapshot

**Finding 1 — The capability table has one production consumer out of nine fields.**
`TOOL_FAMILY_MAP` declares eight families (`claude`, `copilot`, `gemini`, `kimi`,
`glm`, `deepseek`, `qwen`, `mimo`) with measured behavioural fields
(`scripts/sync_mirrors/tool_name_map.py:142`). The only import outside its own test
is `scripts/sync_mirrors/core.py:183`, which reads `TOOL_FAMILY_MAP["copilot"].name_map`.
`schema_enforced_server_side`, `min_completion_budget`, `reasoning_field`,
`prompt_cache`, `per_request_cost`, `fabricates_absolute_paths`, `model_ids` and
`model_pattern` have zero runtime readers; they are asserted by
`tests/unit/config/test_tool_name_map.py:82-199` and nothing else. The measurement
that MiMo returns HTTP 200 with schema-violating content
(`scripts/sync_mirrors/tool_name_map.py:104-107`) currently changes no behaviour.

**Finding 2 — Two model vocabularies, neither reads the other.** Token attribution
resolves `gen_ai.system` through an independent needle list covering
`claude`, `codex`, `gpt`, `o1-`, `o3-`, `o4-`, `gemini`, `deepseek`, `mistral`,
`grok` (`.ai-engineering/scripts/hooks/_lib/transcript_usage.py:72-83`). `qwen`,
`mimo`, `kimi` and `glm` are absent, so a session driven by Qwen 3 or MiMo v2.5
attributes to `unknown` (`:87`, `:107-110`) even though the capability table already
matches those model ids by pattern. Two tables, one fact — a §10.4 DRY break with a
concrete cost: the operator's own fleet is the part that goes unattributed.

**Finding 3 — The judge-independence mechanism shipped; the assignment is blocked by a
whitelist.** `resolve_agent_model` makes `AgentMeta.model` an override that wins over
the effort-derived tier alias, and its test proves an arbitrary identifier resolves
(`scripts/sync_mirrors/core.py:424-435`;
`tests/architecture/test_agent_model_independence.py:156-171` asserts
`"some-provider/some-model-2026"`). But the agent rubric still grades anything outside
`{opus, sonnet, haiku}` as `MINOR` (`tools/skill_domain/rubric.py:652-657`), which is
the exact vocabulary the override exists to escape. The assignment therefore sits
open as a `strict` xfail (`tests/architecture/test_agent_model_independence.py:88-97`),
and all 19 canonical agents still carry a tier alias — 15 `opus`, 4 `sonnet` — so
every judge shares the generator's model.

**Finding 4 — The override axis cannot reach the ten agents that need it.** The
build-time validator only cross-checks agents present in `AGENT_METADATA`
(`scripts/sync_mirrors/core.py:1596-1612`), which is keyed by bare name for the nine
user-facing agents (`scripts/sync_mirrors/core.py:192`). Agent names are derived by
stripping the `ai-` prefix (`scripts/sync_mirrors/core.py:752`), so
`reviewer-correctness`, `verifier-acceptance` and the other internal specialists
resolve to no metadata and keep a hand-typed passthrough `model:`
(`scripts/sync_mirrors/core.py:438-447`). Ten of the twelve agents named in
`JUDGE_AGENTS` (`tests/architecture/test_agent_model_independence.py:47-60`) are
ungoverned: there is no place to declare their override and no validator to catch
drift if someone edits the literal by hand.

**Finding 5 — The replay gate cannot observe the regressions it exists to catch.**
`cross-model-replay.yml` triggers only on changes to the corpus, the runner script,
or the workflow itself (`.github/workflows/cross-model-replay.yml:28-31`). A change to
any `SKILL.md`, agent, or canonical instruction payload — precisely what a routing
regression would come from — never fires it. The corpus is eight routing questions
graded by case-insensitive substring match
(`.ai-engineering/evals/cross-model-replay/corpus.json` header), and the model list is
`("deepseek-v4-flash", "gemma4")` (`scripts/run_cross_model_replay.py:55`) — neither
Qwen 3 nor MiMo v2.5, despite both having capability rows.

**Finding 6 — The deterministic plane is genuinely model-agnostic, and this is
verified, not assumed.** On `6c9b9a4c` the full suite passes (9054 passed, 26 skipped,
2 xfailed), `skill_lint --check` exits 0 with every blocking check clean
(`portability(block) OK=154`, `structure(block) OK=73`, `token_budget(block) OK=73`,
`front_loading(block) OK=73`), `ai-eng check` reports 7/7, and
`regenerate-hooks-manifest.py --check` reports 80 hooks OK. None of that plane calls a
model. It is not the parity risk and needs no work here.

**Finding 7 — Guard coverage is tiered, and the tiers are honest but uneven.** Claude
Code registers 11 canonical hook events with sha-pinned, integrity-enforced bytes. The
OpenCode plane re-exports one bridge (`.opencode/plugin/ai-engineering.ts:10`) wiring
two write guards and one read guard
(`.ai-engineering/scripts/hooks/opencode-hook-bridge.ts:139-140`) out of 80 pinned
hook scripts. D-201-03 documents this as best-effort rather than equivalent, which is
correct reporting; it is recorded here as the true parity ceiling for an operator
running open models on OpenCode, not as a defect to fix in this spec.

**Finding 8 — The token-spend guard ships disabled.** `spend-cap-guard.py` reads
`AIENG_MAX_SESSION_TOKENS` then `performance.budget.max_session_tokens`, defaulting to
`0` = off (`.ai-engineering/scripts/hooks/spend-cap-guard.py:17-24`;
`src/ai_engineering/config/manifest.py:350-362`). Denominating in tokens rather than
USD was deliberate — only the OpenAI-compatible path reports a per-request cost
(`scripts/sync_mirrors/tool_name_map.py:117-120`). Shipping off is defensible; the gap
is that no documented default exists for an operator whose whole reason to run open
models is cost.

## 4. Architecture

Three seams, one direction of travel: the capability table becomes the single model
vocabulary, and the things that currently guess start asking it.

**Seam A — one resolver, two callers.** `resolve_capability(model_id)` already exists
in `tool_name_map.py` and matches by exact id then by pattern
(`tests/unit/config/test_tool_name_map.py:159-162`). `resolve_genai_system` grows a
`gen_ai.system` field on `FamilyCapability` and delegates, deleting
`_GENAI_SYSTEM_NEEDLES` (`.ai-engineering/scripts/hooks/_lib/transcript_usage.py:72-83`).
The `unknown` floor stays as the terminal honest answer for an unrecognised id.
Constraint: hooks are stdlib-only and must not import from `scripts/`, so the table
either moves to a hook-visible `_lib` module or is emitted as generated data by
`ai-eng dev sync` — the spec phase decides which (Open Decision 9.1).

**Seam B — measured fields wired to the paths they govern.** `min_completion_budget`
and `reasoning_field` belong to whatever parses a provider response;
`schema_enforced_server_side` belongs to whatever trusts a strict-schema contract;
`fabricates_absolute_paths` belongs to the command guard that already inspects Bash
arguments. Each field gets exactly one consumer or is deleted as speculative data
(§10.2 YAGNI). A field with no honest consumer today should not survive the spec.

**Seam C — the model axis reaches every agent, and the graders agree on its
vocabulary.** Internal specialists gain metadata governance so an override can be
declared and validated for them, and `_agent_rule_3_model_declared` stops treating
"not a Claude tier alias" as a defect — the rule becomes "declares a model that
`resolve_agent_model` can resolve", which is what the generator already enforces at
`scripts/sync_mirrors/core.py:1598-1612`. Only then is the D-201-16 assignment
mechanically expressible, and the `strict` xfail comes off in the same change.

Module boundaries are unchanged: no new package, no new surface, no new hook event.

## 5. Evidence Catalog

| Claim | Citation |
|---|---|
| Capability table declares 8 families with measured fields | `scripts/sync_mirrors/tool_name_map.py:142` |
| Measured-field semantics (schema, budget, reasoning, paths) | `scripts/sync_mirrors/tool_name_map.py:100-136` |
| Only production consumer is the Copilot name map | `scripts/sync_mirrors/core.py:183` |
| Measured fields asserted only by their own test | `tests/unit/config/test_tool_name_map.py:82-199` |
| Divergent `gen_ai.system` needle list, no qwen/mimo/kimi/glm | `.ai-engineering/scripts/hooks/_lib/transcript_usage.py:72-83` |
| Unrecognised model resolves to `unknown` | `.ai-engineering/scripts/hooks/_lib/transcript_usage.py:87,107-110` |
| Transcript discovery is Claude-shaped, with one env override | `.ai-engineering/scripts/hooks/_lib/transcript_usage.py:166-193` |
| Model override axis resolves any identifier | `scripts/sync_mirrors/core.py:424-435` |
| Effort-to-model map is a closed three-value vocabulary | `scripts/sync_mirrors/core.py:381-394` |
| Rubric grades non-tier models as MINOR | `tools/skill_domain/rubric.py:652-657` |
| Conformance test pins the tier vocabulary at half the fleet | `tests/conformance/test_agents_rubric.py:67-81` |
| Build-time validator only governs `AGENT_METADATA` agents | `scripts/sync_mirrors/core.py:1596-1612` |
| Specialists keep an ungoverned passthrough model | `scripts/sync_mirrors/core.py:438-447` |
| Agent names strip the `ai-` prefix | `scripts/sync_mirrors/core.py:752` |
| Judge roster spans 12 agents, 10 of them ungoverned | `tests/architecture/test_agent_model_independence.py:47-60` |
| Assignment pinned open as a strict xfail | `tests/architecture/test_agent_model_independence.py:88-97` |
| Override mechanism proven with a non-Claude identifier | `tests/architecture/test_agent_model_independence.py:156-171` |
| Replay path filter excludes skills and agents | `.github/workflows/cross-model-replay.yml:28-31` |
| Replay model list omits qwen and mimo | `scripts/run_cross_model_replay.py:55` |
| Replay is advisory by construction | `.github/workflows/cross-model-replay.yml:4-12` |
| Spend cap ships disabled, denominated in tokens | `.ai-engineering/scripts/hooks/spend-cap-guard.py:17-24` |
| Manifest default `max_session_tokens: 0` | `src/ai_engineering/config/manifest.py:350-362` |
| OpenCode plane is a thin re-export of one bridge | `.opencode/plugin/ai-engineering.ts:10` |
| OpenCode wires 2 write guards and 1 read guard | `.ai-engineering/scripts/hooks/opencode-hook-bridge.ts:139-140` |
| Model management remains out of scope | `.ai-engineering/specs/archive/spec-201-three-layer-open-model-harness/spec.md:408-417` |
| D-201-16 rationale for the independent axis | `.ai-engineering/specs/archive/spec-201-three-layer-open-model-harness/spec.md:348-362` |

## 6. Roadmap

**M0 — One model vocabulary.** Give `FamilyCapability` a `gen_ai_system` field,
delete `_GENAI_SYSTEM_NEEDLES`, route `resolve_genai_system` through
`resolve_capability`, and resolve the hook-import constraint from Seam A.
*Gate*: a Qwen 3 and a MiMo v2.5 model id each attribute to a named system, not
`unknown`; existing `resolve_genai_system` tests pass unchanged; hooks stay
stdlib-only; the pre-commit budget stays under one second.

**M1 — Measured fields become behaviour.** Wire each surviving capability field to
exactly one consumer; delete any field with no honest consumer.
*Gate*: every field in `FamilyCapability` is either read by production code or gone,
proven by an import-graph test rather than a comment.

**M2 — The model axis reaches every judge.** Extend metadata governance to the
internal specialists, relax `_agent_rule_3_model_declared` to agree with
`resolve_agent_model`, assign the judge identifier, and remove the `strict` xfail.
*Gate*: `test_judges_do_not_share_the_generator_model` passes with the marker
removed; `test_no_judge_was_downgraded_to_buy_independence` still passes;
`ai-eng dev sync --check` and `ai-eng check` stay clean; every mirror carries the
resolved literal.

**M3 — The replay gate can regress.** Widen the workflow path filter to the canonical
skill and agent trees, add the operator's families to the model list, and grow the
corpus beyond routing.
*Gate*: a deliberate one-line routing break in a canonical `SKILL.md` fires the
workflow and lowers the score against the recorded Claude reference; the job stays
advisory and still exits 0 unprovisioned.

## 7. Definition of Done

- No model-family vocabulary exists outside `TOOL_FAMILY_MAP`.
- `gen_ai.system` resolves for every family the capability table names, including
  Qwen 3 and MiMo v2.5; unrecognised ids still read `unknown`.
- Every field on `FamilyCapability` has a production consumer, or does not exist.
- All 12 judge agents are metadata-governed, and none shares a generator's model.
- No judge trades capability for independence: user-facing judges stay `effort: high`.
- `tools/skill_domain/rubric.py` and `scripts/sync_mirrors/core.py` agree on what a
  legal agent model is.
- The `strict` xfail at `tests/architecture/test_agent_model_independence.py:89` is
  removed, not re-scoped.
- The replay workflow fires on canonical skill and agent changes and covers the
  operator's families.
- Full suite, `skill_lint --check`, `ai-eng check`, `ai-eng dev sync --check` and the
  hooks-manifest check are all green; the ruff baseline of 28 findings does not move.
- Hooks remain stdlib-only; the pre-commit hot path stays under one second.

## 8. Quality Stamps

- **§10.1 KISS** — one resolver replaces two vocabularies; no per-model branching.
- **§10.2 YAGNI** — a measured field with no consumer is deleted, not preserved.
- **§10.4 DRY** — model-family knowledge has exactly one canonical home.
- **§10.5 TDD** — each milestone gate is a test that fails before the change lands;
  M2's gate already exists and is red-by-marker today.
- **§10.6 SDD** — this brief precedes the spec; the spec precedes the plan.
- **Single Source of Truth Per Datum** (§13.7) — the capability table becomes the one
  writable store for model-family facts.
- **No suppression** (§13.2) — the xfail marker is removed by satisfying the contract,
  never by widening it.
- **Surface Axiom / No-Twin Axiom** — no per-family prose variants are introduced.

## 9. Open Decisions

1. **Where the capability table lives so hooks can read it.** Hooks are stdlib-only
   and cannot import `scripts/`. Options: move the table into a hook-visible `_lib`
   module and have `sync_mirrors` import it; or keep it in `scripts/` and emit
   generated data at `ai-eng dev sync` time. The second adds a generated artefact and
   a staleness class; the first moves build-time data into the hot path. The spec
   must pick one and say why.
2. **Which model identifier the judges move to.** Escalated by spec-201 and still not
   derivable from the repository — no tier alias can express "different model, same
   capability", so this needs an operator decision naming a full identifier.
3. **Whether `prompt_cache` and `per_request_cost` earn a consumer.** Both are
   measured facts with no obvious caller. If none appears, §10.2 says delete.
4. **Whether the metadata-governance extension to specialists reuses `AGENT_METADATA`
   or adds a sibling registry.** Reuse is simpler; a sibling keeps the user-facing
   nine visibly distinct from the internal ten.
5. **Whether the replay corpus grows beyond routing** into a small execution corpus,
   and if so, what the egress posture is for anything richer than fixture text.
6. **Whether a documented non-zero `max_session_tokens` default ships** for
   open-model operators, or the cap stays opt-in.

## 10. Migration

Per CONSTITUTION.md §3, hard changes only — no shims, no compatibility aliases.

- `_GENAI_SYSTEM_NEEDLES` is **deleted**, not deprecated. Its behaviour is replaced by
  `resolve_capability`; the `unknown` floor is preserved because it is correct, not
  because it is compatible.
- Any `FamilyCapability` field with no consumer is **removed** from the dataclass and
  from `tests/unit/config/test_tool_name_map.py`; the removal is a CHANGELOG breaking
  entry.
- `_agent_rule_3_model_declared` changes its acceptance predicate rather than gaining
  a second one. `tests/conformance/test_agents_rubric.py:67-81` is rewritten to the
  new contract in the same change.
- Agent `model:` literals that change are regenerated through
  `resolve_agent_model` across every mirror in one `ai-eng dev sync`; no surface keeps
  a stale literal.
- The `strict` xfail is deleted with its reason string, per the instruction embedded
  in the marker itself.
- Template mirrors under `src/ai_engineering/templates/` move in the same commit —
  spec-161 shipped features that were missing from consumer installs until a
  follow-up PR because a template twin was skipped.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Moving the capability table breaks the stdlib-only hook contract | Medium | High — every hook on every surface | Decide Open Decision 9.1 before any code; add an import-purity test to the hook suite |
| Relaxing the rubric rule hides a genuinely malformed model literal | Medium | Medium — silent agent misconfiguration | The new predicate delegates to `resolve_agent_model`, which already hard-errors on an unresolvable value |
| Judge identifier is assigned without operator input | Low | High — reverses an escalation on the operator's behalf | Blocked by design: M2 cannot start until Open Decision 9.2 is answered |
| Extending governance to specialists trips a hidden count gate | Medium | Medium — red CI on unrelated tests | Precedent: adding a skill trips roughly five hardcoded count gates; run the full `tests/unit/config` and `tests/unit/docs` trees plus `ai-eng check` before pushing |
| Widening the replay path filter makes it fire on most PRs | High | Low — advisory job, `continue-on-error` | Accepted; the job is skip-clean when unprovisioned and never enters `CI Result` |
| Deleting an unused capability field loses a measurement that was expensive to obtain | Medium | Medium — re-probing costs provider time | Move the measurement into the spec's evidence section before deleting the field, so the number survives the code |
| Template-mirror drift ships a fix that consumer installs never receive | Medium | High — silent divergence | Byte-parity copy in the same commit; verify with `ai-eng dev sync --check` |

## 12. References

- `.ai-engineering/specs/archive/spec-201-three-layer-open-model-harness/spec.md` —
  the predecessor's non-goals, D-201-16, D-201-18 and D-201-20.
- `.ai-engineering/specs/archive/spec-189-open-model-portability/spec.md` — content
  portability, `effort` as the semantic axis, D-189-01.
- `.ai-engineering/specs/drafts/three-layer-open-model-harness-brief.md` — the source
  brief whose E5/E8/E9/E12 probes produced the capability table.
- `.ai-engineering/specs/archive/spec-181-ai-pr-small-model-robustness/` — prior art
  on hardening a single skill for weaker models.
- OpenTelemetry GenAI semantic conventions — the `gen_ai.system` vocabulary the
  capability table's values must stay inside.
- `.ai-engineering/reference/gate-policy.md` — fail-open versus fail-closed posture
  for the guards touched in M1.
- `.ai-engineering/reference/surface-axioms.md` — the No-Twin Axiom that forbids
  per-family prose variants.

## 13. Glossary

- **Capability table** — `TOOL_FAMILY_MAP`, the per-family record of measured
  open-model behaviour. Build-time data, never a dispatcher.
- **Family** — a group of models sharing tool-call and response behaviour
  (`deepseek`, `qwen`, `mimo`, `kimi`, `glm`, `gemini`, `claude`, `copilot`).
- **Model axis** — `AgentMeta.model` as an override independent of `effort`,
  introduced by D-201-16 so "different model, same capability" is expressible.
- **Tier alias** — one of `opus`, `sonnet`, `haiku`; the closed vocabulary that
  `effort` maps to, and the thing the model axis exists to escape.
- **Judge agent** — an agent that assesses work another agent produced: the two
  user-facing judges plus the ten internal review and verify specialists.
- **Inert data** — a recorded measurement with no production consumer. The central
  defect this brief addresses.
- **Advisory gate** — a CI job that reports without blocking merge, advisory by
  construction rather than by a flag.

## 14. Acceptance

- [ ] `TOOL_FAMILY_MAP` is the only model-family vocabulary in the repository.
- [ ] `resolve_genai_system` delegates to `resolve_capability`; the needle list is deleted.
- [ ] A Qwen 3 model id and a MiMo v2.5 model id each resolve to a named `gen_ai.system`.
- [ ] An unrecognised model id still resolves to `unknown`.
- [ ] Every `FamilyCapability` field has a production consumer or has been removed.
- [ ] An import-graph test proves the consumer claim rather than asserting it in prose.
- [ ] All 12 judge agents are metadata-governed with a validated `model:`.
- [ ] `test_judges_do_not_share_the_generator_model` passes with the xfail marker removed.
- [ ] `test_no_judge_was_downgraded_to_buy_independence` still passes.
- [ ] `test_user_facing_judges_keep_their_high_effort_tier` still passes.
- [ ] `tools/skill_domain/rubric.py` accepts exactly what `resolve_agent_model` resolves.
- [ ] `tests/conformance/test_agents_rubric.py` is rewritten to the new contract.
- [ ] The replay workflow fires on canonical skill and agent changes.
- [ ] The replay model list covers the operator's families.
- [ ] Template mirrors under `src/ai_engineering/templates/` are byte-parity updated.
- [ ] Full suite green; `skill_lint --check`, `ai-eng check`, `ai-eng dev sync --check`
      and the hooks-manifest check all pass.
- [ ] Ruff baseline stays at 28 findings.
- [ ] Hooks remain stdlib-only; pre-commit stays under one second.
- [ ] CHANGELOG records every deletion as a breaking entry.
