---
title: "Open-Model Portability — make the whole fleet execute on Kimi, GLM, DeepSeek, Qwen, MiMo"
status: draft
audience: framework-dev / operator
branch: feat/open-model-portability
length_estimate: multi-wave (5 milestones M0-M4, >=3 concerns, >=40 files across canonical + 4 mirror surfaces)
authoring_style: diagnostic-brief
principles_required:
  - "§10.1 KISS"
  - "§10.2 YAGNI"
  - "§10.3 SOLID"
  - "§10.4 DRY"
  - "§10.5 TDD"
  - "§10.6 SDD"
  - "§10.8 Hexagonal Architecture"
delivery_mode: /ai-autopilot
mantra: "Stop assuming the model is Opus. The harness is a port; the model is an adapter."
---

# Open-Model Portability — make the whole fleet execute on Kimi, GLM, DeepSeek, Qwen, MiMo

> Successor to shipped **spec-187** (`fleet simplify + model-portability`,
> commit `2b7471c5`), which built the *inert* foundations — a tool-name map wired
> nowhere, a portability lint blind to the hardest gap, an AGENTS.md entry point —
> and explicitly deferred live open-model execution
> (`.ai-engineering/specs/archive/spec-187-fleet-simplify-portability/spec.md:66-67`).
> Must reconcile with the **open** PR #639 (`spec-185/open-model-resilience`),
> whose own re-entry trigger authorises this brief: *"when
> `.ai-engineering/runtime/driver-tier.json` records a non-frontier driver in real
> working sessions, a new spec is brainstormed FROM the failures."*

## 1. Vision

The framework runs today on the assumption that the driving model is Claude Opus 4.8
inside Claude Code — a model that forgives disordered prompts, deep-nested JSON tool
schemas, forcible tool selection, and 4+ iteration ReAct loops. Open models (Qwen,
DeepSeek, Kimi/Moonshot, GLM/Zhipu, MiMo/Xiaomi) do not forgive any of those. They
support OpenAI-style tool calling and now match Claude on pure function-calling
accuracy (GLM-4.5 tops BFCL v3 at 76.7%), but they fail differently: malformed tool-call
JSON that vendors themselves warn is unavoidable, rejection of forced `tool_choice` on
reasoning/thinking-default models (DeepSeek reasoner/V4, GLM-4.6),
reasoning-model format drift, and per-family quirks that a single hardcoded temperature
or system-prompt convention silently breaks.

We do **not** build model access — the operator connects their own OpenAI-compatible
surface (Cline, opencode, Codex, a raw endpoint). Our job is to make the fleet *content*
— 53 skills, 9 user agents plus the review/verify families, 11 canonical hook events, the harness — port
to any of them without capability loss. The winning move is not a new SDK or a LangGraph
rewrite. It is: (a) wire the map spec-187 left inert, (b) replace Claude-literal model
names with an effort/tier abstraction that resolves per-family, (c) give the four
dispatch-only skills an inline fallback, (d) prove it with a cross-model eval battery
that turns spec-185's telemetry into a red/green gate.

## 2. Scope Boundary

**In scope**
- All 53 canonical skills (`.claude/skills/ai-*/SKILL.md`) — prompt hardening + neutral frontmatter.
- All 19 canonical agents (`.claude/agents/*.md`) keep their hand-authored Claude-valid `model:` (frontier-harness ground truth, never rewritten — `.claude` is a read-only glob source, `core.py:59`); `AGENT_METADATA` gains an `effort` key as the sole SEMANTIC source, cross-checked by a build-time validator. Only the mirror `model:` lines derive from `effort`.
- The 4 dispatch-only skills with a forbidden inline path: `ai-advise`, `ai-review`, `ai-verify`, `ai-simplify`.
- The tool-name map (`scripts/sync_mirrors/tool_name_map.py`) — wire it into mirror generation.
- The engine-detection seam (`.ai-engineering/scripts/hooks/_lib/hook_context.py`) — add a generic OpenAI-compatible member.
- Reconciliation of the open PR #639 driver-tier substrate (merge-or-supersede, resolve the naming collision).
- A cross-model eval harness (Promptfoo x DeepEval) as the M4 gate.
- The 4 mirror surfaces (`.codex/`, `.agents/`, `.github/`) via `scripts/sync_mirrors/core.py` — regenerated, never hand-edited.

**Explicitly NOT in scope**
- Building or hosting model access (API keys, endpoints, routers) — the operator owns this.
- A LangGraph / CrewAI / AutoGen rewrite — the fleet is markdown + Python hooks, not a Python agent app.
- Fine-tuning or model-weight changes.
- Guaranteeing byte-identical *output quality* across models — we guarantee the fleet *runs and produces schema-valid tool calls*, not that GLM writes exactly what Opus writes.
- Removing Claude Code support — Claude Code remains one harness (the `frontier` tier), not the only one.
- Adopting TOON (Token-Oriented Object Notation) or any non-YAML/JSON serialization for fleet content — models are pretrained on YAML/JSON/Markdown; TOON helps only uniform record arrays (which the fleet has none of) and loses ~7pp accuracy on nested data. Stay on YAML/Markdown.
- RAG-style chunk-retrieval tuning (ParadeDB, contextual-retrieval preprocessing) — nothing in this repo retrieves skill/spec CHUNKS; progressive-disclosure ranks the `description` field only. That advice is N/A here.

## 3. Diagnostic Snapshot

Current state, evidence-cited. The fleet is quietly Claude-Code-shaped in five load-bearing ways.

**Prior art is inert.** spec-187 shipped three deliverables that establish vocabulary but change no runtime. The tool-name map documents 8 families (`claude`/`copilot`/`gemini` + open-weight `kimi`/`glm`/`deepseek`/`qwen`/`mimo`) with per-family call-format quirks — Kimi's `functions.{name}:{idx}` special-token IDs (`scripts/sync_mirrors/tool_name_map.py:129-133`), DeepSeek's string-only args (`tool_name_map.py:140-146`) — but its own docstring states "No mirror family consumes this map yet" (`tool_name_map.py:8`), naming itself input to "a future harness" (`tool_name_map.py:14`). MiMo is `verified=False`, no primary source (`tool_name_map.py:155-164`). The portability lint flags un-gated Claude-only tool literals (`tools/skill_lint/checks/portability.py:1-237`) but is registered `required=False` in the pre-commit path (`src/ai_engineering/policy/checks/stack_runner.py:160-164`) with no direct CI step.

**The Agent-tool dispatch gap is invisible to the gate.** The portability lint *deliberately* excludes `Agent`/`Task` from its flagged-literal set, treating them as domain vocabulary (`portability.py:13-18`). So four skills forbid the only non-Claude alternative and still pass with zero findings: `ai-advise/SKILL.md:70` ("never reads the agent file inline; dispatches via the Agent tool"), `ai-review/SKILL.md:55`, `ai-verify/SKILL.md:80`, `ai-simplify/SKILL.md:12,30`. Agent-side mirrors repeat it (`.claude/agents/ai-review.md:19-24`, `ai-verify.md:19-21`). No harness outside Claude Code has a standard subagent primitive — opencode uses Task/`@mention`, Roo uses Orchestrator/Boomerang subtasks, Cline/Aider/Codex have no durable subagents at all.

**Literal Claude model names are hardcoded fleet-wide.** All 19 agents pin a Claude family in frontmatter — `.claude/agents/ai-build.md:4` (`model: opus`), same for `ai-review.md:4`/`ai-verify.md:4`/`ai-plan.md:4`, `sonnet` for the rest. This propagates mechanically through `scripts/sync_mirrors/core.py:126,140,936` into every mirror (`.codex/agents/ai-build.md:4`, `.agents/agents/ai-build.md:4`, `.github/agents/build.agent.md:4`). The `model_tier` enum is blocking-lint-locked to `haiku|sonnet|opus` (`tools/skill_lint/checks/effort.py:41,57`), baked into all 53 skills' frontmatter and into live dispatch prose (`ai-build/SKILL.md:22-26`), and mapped in the SSOT table (`.ai-engineering/reference/model-dispatch-policy.md:9-13`) — conflating a portable effort concept with Anthropic family names. Note a neutral `effort: cheap|mid|high` axis *already coexists* in the same frontmatter and the same lint (`effort.py:40`; `_POLICY_ROW_RE` at `:57` validates both axes side by side), so the portable vocabulary partly exists already — the work is to promote it to sole authority, not invent it.

**The engine seam is a closed 4-value set with no generic member.** `hook_context.py:56-68` declares `engine: str  # claude_code, antigravity, github_copilot, codex` — detection at `hook_context.py:111-147`, no `openai_compatible` value for a raw self-hosted endpoint, which is the literal target surface. Per-engine bridge scripts exist for those 4 only (`codex-hook-bridge.py`, `cursor-hook-bridge.py`, `copilot-adapter.py`, `opencode-hook-bridge.ts`); none for a bare chat-completions harness. The 1337-line security guard `prompt-injection-guard.py` assumes the Claude Code hook-decision stdout/exit-code contract; `codex-hook-bridge.py:17` notes Codex "does not require a JSON response on stdout" — whether a non-Claude host honours a deny response is asserted nowhere in-repo.

**An open PR already ships a competing substrate.** `spec-185/open-model-resilience` (PR #639, state OPEN, `mergedAt: null`) adds a vendor-neutral 3-tier vocabulary `("frontier","standard-floor","stretch-floor")` resolved from the SessionStart `model` field, published to `.ai-engineering/runtime/driver-tier.json` every session (`.ai-engineering/scripts/hooks/_lib/driver_tier.py`, `src/ai_engineering/state/driver_tier.py`, both branch-only). It was amended observe-only (D-185-15). It diverged *before* spec-187 purged `AIENG_MODEL_TIER`, so its D-185-16 dependency on that variable at "ai-build step 2c" is now dead on main (0 grep hits) — rebasing #639 hits this directly. Its `_FAMILY_TIERS` also has no `kimi` needle, unlike the merged tool-name map.

**Authoring structure is already half-hardened — cite it, don't rebuild it.** The open-model doc-structure playbook (front-loading, reason-in-prose, stable headers, deterministic verdicts) is mostly already enforced here: the BLUF lives in the blocking `description` field (CSO, >=3 triggers + negative scope, `tools/skill_domain/rubric.py:257-324`); reasoning crammed into YAML is a MAJOR lint (`rubric.py:108-121`); procedure must live in a numbered `## Workflow` body, prose-heavy Workflows flagged (`tools/skill_lint/checks/structure.py:1-24`); specs enforce exact-string L2 headers (`## Summary/Goals/Non-Goals/Decisions/Risks`, `tools/spec_lint/checks/sections.py:17-53`); and a precomputed deterministic verdict already exists at the gate layer (`gate-findings.json` `outcome: pass|block` from exit codes, `src/ai_engineering/policy/orchestrator.py:444`). The real gaps: skill BODIES lack a consistent one-line BLUF (some, e.g. `ai-review/SKILL.md`, open straight into `## Workflow`); acceptance criteria are freeform prose, not a machine-checkable grammar (NO EARS/SHALL anywhere, `spec-schema.md:30`); and no retrieval consumes skill chunks — so RAG-style advice is N/A.

## 4. Architecture

Hexagonal framing (§10.8): the **fleet content is the domain core**; the **model family is an adapter**; the **harness is a port**. Today the core imports the adapter (Claude names hardcoded in skills/agents) and assumes one port (Claude Code dispatch). The fix inverts both dependencies.

```
                 DOMAIN CORE (portable, model-neutral)
   skills: numbered procedure · flat schemas · GENERIC parse-retry
   agents: roles · hooks: integrity   — NO per-family prose in the core
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼ BUILD-TIME (static, per-surface)               ▼ RUNTIME (per-session)
   MODEL ADAPTER — tool_name_map.py (EXTENDED)        driver-tier.json
   name-map · tool-id · schema · temp · sys-prompt    (spec-185: which tier
   · reasoning_content · tool_choice  [per family]     drives THIS session)
        │                                                   │
   core.py emits per-surface frontmatter at build:     DISPATCH + HARNESS PORTS
   Claude-valid `model:` for .claude,                  capability shim: Agent
   family hints for the 4 mirrors                      tool -> inline-seq
        │                                              fallback; engine detect
        │                                              +openai_compatible
        └───────────────────────┬───────────────────────┘
                                ▼
   M4 EVAL — (a) CI fixture-replay: schema-validity · tool-call-F1 vs
   recorded malformed responses      (gates PRs, no creds needed)
             (b) operator-run LIVE battery: operator-local acceptance,
   NOT a repo CI gate (§2: no model access in CI)
```

Module boundaries (the two axes are separate — build-time is static, runtime is per-session; conflating them is this design's easiest mistake):
- **Adapter (build-time)** — `tool_name_map.py` grows from inert reference to a consumed table, *extended* additively with 7 Optional fields (`X | None = None`, kwargs-only, `frozen`) appended after its current 4 (`tool_name_style`/`call_format_notes`/`verified`/`name_map`, `tool_name_map.py:71-91`): `temperature_default`, `temperature_rescale_factor` (Kimi Anthropic-endpoint x0.6), `min_p` (UNVERIFIED for every family — ships `None`), `system_prompt_constraint`, `reasoning_content_protocol`, `tool_choice_support` (free-text NOT bool — support is uneven, see M11), `structured_output_mechanism`. Additive + defaulted keeps all 8 existing kwargs-only constructions compiling and all 8 pinned tests green. `core.py` reads it AT BUILD TIME to emit per-surface frontmatter + per-family call-format notes. It does NOT read `driver-tier.json` (that file does not exist until a session runs).
- **Core hygiene** — the model-neutral hardening (numbered procedure, flat schemas, a GENERIC parse-and-correct loop) lives in the 53 skills. Per-family quirks do NOT live in skill prose — only in the adapter table. This is the actual dependency inversion: a core that embedded per-family prose would import every adapter, the opposite of §10.8.
- **Dispatch port** — the four dispatch-only skills gain a documented inline-sequential path selected by capability detection (does this harness expose a subagent primitive?). The Agent-tool path stays the `frontier` default; inline is the floor.
- **Harness port** — `hook_context.py` engine enum gains `openai_compatible`. Crucially, a bare `/chat/completions` endpoint fires ZERO of the 11 canonical hook events and every `.ai-engineering/scripts/hooks/*.py` script is dark — including the sole content-injection security gate `prompt-injection-guard.py` (`.claude/settings.json:89-98`). The ONLY surviving control is `gitleaks` (a git-native pre-commit hook, NOT one of the 11 events), conditional on the operator committing through git with hooks installed. So those surfaces are "content-portable but ungoverned" with a documented security posture (Open Decision 8). Where a host DOES fire hooks but ignores a deny response, fail closed on the edit itself. (Codex is already a partial-governance case — 6/11 events unwired, injection-guard Bash-only — so M3's parity audit must cover the FULL 11-event/matcher set, not just "does a bridge exist".)
- **Telemetry spine (runtime)** — `driver-tier.json` is read only AT RUNTIME by the dispatch/eval layers to decide "am I on a floor tier, harden accordingly." It never gates frontmatter generation.

## 5. Evidence Catalog

| # | Claim | Citation |
|---|-------|----------|
| 1 | spec-187 named the problem: fleet is "quietly Claude-Code-shaped" | `.ai-engineering/specs/archive/spec-187-fleet-simplify-portability/spec.md:13-14` |
| 2 | spec-187 non-goal: no live open-weight execution this cycle | `.ai-engineering/specs/archive/spec-187-fleet-simplify-portability/spec.md:66-67` |
| 3 | D-187-03 chose canonical neutrality + documented tool-name map | `.ai-engineering/specs/archive/spec-187-fleet-simplify-portability/spec.md:101-107` |
| 4 | Tool-name map wired nowhere ("No mirror family consumes this map yet") | `scripts/sync_mirrors/tool_name_map.py:8,14` |
| 5 | Map documents 5 open-weight families + per-family quirks | `scripts/sync_mirrors/tool_name_map.py:97-165` |
| 6 | Kimi special-token tool-ID format quirk | `scripts/sync_mirrors/tool_name_map.py:129-133` |
| 7 | DeepSeek string-only args quirk | `scripts/sync_mirrors/tool_name_map.py:140-146` |
| 8 | MiMo flagged unverified (D-187-08) | `scripts/sync_mirrors/tool_name_map.py:155-164` |
| 9 | Portability lint whitelists Agent/Task — the gap is invisible | `tools/skill_lint/checks/portability.py:13-18` |
| 10 | Lint registered required=False, no direct CI step | `src/ai_engineering/policy/checks/stack_runner.py:160-164` |
| 11 | ai-advise forbids inline agent read (dispatch-only) | `.claude/skills/ai-advise/SKILL.md:70` |
| 12 | ai-review lists inline read as a Common Mistake | `.claude/skills/ai-review/SKILL.md:55` |
| 13 | ai-verify repeats the dispatch-only anti-pattern | `.claude/skills/ai-verify/SKILL.md:80` |
| 14 | ai-simplify dispatch-only, no inline path | `.claude/skills/ai-simplify/SKILL.md:12,30` |
| 15 | All agents pin a literal Claude model name | `.claude/agents/ai-build.md:4` |
| 16 | Only Copilot's mirror reads `AGENT_METADATA.model`; other mirrors copy the canonical frontmatter | `scripts/sync_mirrors/core.py:936` |
| 16b | `.claude/agents/*.md` is a read-only glob source, never a write target | `scripts/sync_mirrors/core.py:59` |
| 17 | Verified in generated mirror surfaces (`model: opus` at line 4; line 3 is `description:`) | `.codex/agents/ai-build.md:4`, `.github/agents/build.agent.md:4` |
| 18 | model_tier enum blocking-locked to haiku/sonnet/opus | `tools/skill_lint/checks/effort.py:41,57` |
| 19 | Dispatch-effort leaks into live workflow prose (`## Model dispatch` block) | `.claude/skills/ai-build/SKILL.md:22-26` |
| 19b | A neutral `effort` axis (`cheap\|mid\|high`) already coexists with `model_tier` | `tools/skill_lint/checks/effort.py:40,57` |
| 19c | `FamilyToolProfile` has no temp/sys-prompt/reasoning_content/tool_choice field | `scripts/sync_mirrors/tool_name_map.py:71-91` |
| 20 | effort<->model_tier SSOT uses only 3 Claude literals | `.ai-engineering/reference/model-dispatch-policy.md:9-13` |
| 21 | Engine enum is a closed 4-value set, no generic member | `.ai-engineering/scripts/hooks/_lib/hook_context.py:56-68` |
| 22 | Engine detection priority order | `.ai-engineering/scripts/hooks/_lib/hook_context.py:111-147` |
| 23 | Codex bridge notes no stdout JSON required (contract unverified) | `.ai-engineering/scripts/hooks/codex-hook-bridge.py:17` |
| 24 | Security guard assumes Claude hook-decision contract (1337 lines) | `.ai-engineering/scripts/hooks/prompt-injection-guard.py` |
| 25 | AGENTS.md portable entry point: invoke SKILL.md body directly | `AGENTS.md:180-182` |
| 26 | ai-build encodes bounded ReAct retry loop (max 3 / max 2) | `.claude/agents/ai-build.md:41,66` |
| 27 | Concurrency assumes N parallel subagent dispatch | `src/ai_engineering/config/concurrency.py:169,241,267` |
| 28 | Tool-name-map family list pinned by test | `tests/unit/config/test_tool_name_map.py:24-25` |
| 29 | Portability-lint exclusion behavior locked by test | `tests/unit/skill_lint/test_portability.py:1-147` |
| 30 | run-hook.sh already engine-neutral (dir-walk fallback) — reusable seam | `.ai-engineering/scripts/hooks/_lib/run-hook.sh:24-37` |
| 31 | Progressive-disclosure ranks the `description` field only — no skill-chunk retrieval exists | `.ai-engineering/scripts/hooks/runtime-progressive-disclosure.py:156-166` |
| 32 | BLUF lives in the blocking CSO `description` (>=3 triggers + negative scope) | `tools/skill_domain/rubric.py:257-324` |
| 33 | Reasoning crammed into YAML frontmatter is a MAJOR lint finding | `tools/skill_domain/rubric.py:108-121` |
| 34 | Specs enforce exact-string L2 headers (stable chunk boundaries already) | `tools/spec_lint/checks/sections.py:17-53` |
| 35 | Precomputed deterministic verdict already exists at the gate layer | `src/ai_engineering/policy/orchestrator.py:444` |
| 36 | No EARS/SHALL/WHEN notation anywhere; Goals = freeform bullets | `.ai-engineering/reference/spec-schema.md:30` |

## 6. Roadmap

Five milestones, each with an acceptance gate. M0 first because it clears the substrate collision; M4 last because it needs everything above to test.

- **M0 — Reconcile spec-185 (runtime substrate for M2-M4).** Decide merge-or-supersede for PR #639; land the vendor-neutral driver-tier telemetry on main; resolve the `AIENG_MODEL_TIER` -> `AIENG_DRIVER_TIER` naming collision (the old var is already purged from main); add the missing `kimi` needle to `_FAMILY_TIERS`. Feeds M2/M3/M4 (the runtime axis), NOT M1. **Gate:** `driver-tier.json` publishes on every session on main; parity tests green in both suites; 0 dangling `AIENG_MODEL_TIER` refs.
- **M1 — Prompt hardening (core hygiene, parallel to M0).** Reads only the tool-name map (already on main, commit `2b7471c5`), so it runs concurrently with M0 — the parallelism is structural, not optimistic: M0's `driver_tier.py` is untracked on main and M1 has zero `driver_tier` refs. Two disjoint parts: (a) model-neutral hygiene on the core skills — imperative prose -> numbered procedure, flat tool schemas, explicit "use EXCLUSIVELY when ..." descriptions, a GENERIC parse-and-correct loop (max 2-3) wherever a skill consumes structured tool output, plus front-loading: every skill body opens with a one-line BLUF and states each gate/constraint BEFORE its rationale (mitigates lost-in-the-middle for floor models, Liu et al.), and reasoning stays in prose while only gates/verdicts serialize to structure (forcing reasoning into strict JSON costs 25-63pp on reasoning tasks per "Let Me Speak Freely", while structured EXTRACTION gains +18.8pp — the parse-and-correct loop IS the reason-in-prose-then-serialize mitigation); (b) per-family quirks kept in the adapter table ONLY, never in skill prose. **Gate:** a new `tests/conformance` check asserts every skill that parses tool output carries a retry-bound annotation (a static grep-able property — the loop itself is EXERCISED, not asserted, by the M4 CI fixture-replay against recorded malformed responses) AND that no skill body hardcodes a family-specific quirk (grep `.claude/skills/*/SKILL.md` bodies for `kimi|deepseek|qwen|glm|mimo` — baseline is already clean at 0 matches today, so this pins neutrality, not a retrofit); portability lint *extended* but STAYS `required=False` (promotion deferred to M3, per §11).
- **M2 — Neutral frontmatter (build-time adapter inversion).** Delete `model_tier` and promote the *existing* `effort` axis (`cheap|mid|high`, already live at `effort.py:40`) to sole skill vocabulary. Canonical agents keep their hand-typed Claude-valid `model:` verbatim — `.claude` is NEVER a write target (`core.py:59` is a read-only glob), so a build-time **validator** in `validate_canonical()` (`core.py:1521`) cross-checks each agent's `model:` against `AGENT_METADATA[name].effort` (precedent: `effort.py:56-59` for skills); only the mirror generators derive `model:` from `effort` — and only Copilot's actually reads `AGENT_METADATA.model` today (`core.py:936`); codex (`:774`) + cursor/antigravity (`:822`) currently copy the canonical frontmatter through and must be extended. So the "no Claude model name" rule is scoped to SKILLS, not agents. Resolution is build-time via the tool-name map only — NOT driver-tier. Wire `tool_name_map.py` into `core.py` (kill its "inert" status). **Atomic lockstep set — 10 members** (one commit or the required lint reds every file; CRITICAL: change the SSOT table column count and `_POLICY_ROW_RE` in the SAME commit or `load_policy().findall()` silently returns 0 rows): (1) `_POLICY_ROW_RE` + `VALID_MODEL_TIERS` (`effort.py:41,56-59`); (2) `model-dispatch-policy.md` SSOT table + its byte-identical doc-twin under `src/ai_engineering/templates/`; (3) all 53 skill frontmatter; (4) `AGENT_METADATA` (agents keep `model:`, see B1); (5) `skill_lint/cli.py --enforce-tier` block (`:182-186,231`); (6) `skill_domain/rubric.py` `_TOLERATED_EXTRA_FIELDS` (`:116`); (7) `_lib/observability.py` frozenset/validator + its template twin, THEN regenerate `hooks-manifest.json`; (8) hard-delete `spec-131/apply_effort_model_tier.py` + its 2 test files; (9) regenerate Surface-5 install-template SKILL.md copies via `core.py`; (10) rewrite `test_effort.py` + rename `test_model_tier_effort_fields.py`; cosmetic `CONSTITUTION.md:46`. **Gate:** `model_tier` deleted, `effort` sole axis; `test_tool_name_map.py` asserts the map is *consumed*, not inert; all 4 mirror surfaces regenerate clean; a new negative-regression test `tests/conformance/test_no_runtime_reads_at_buildtime.py` greps `scripts/sync_mirrors/**/*.py` for `driver.tier`/`driver_tier` and FAILS on any match (pins the build-time/runtime boundary, B2).
- **M3 — Dispatch + harness shim (port inversion) + lint promotion.** Give `ai-advise`/`ai-review`/`ai-verify`/`ai-simplify` a documented inline-sequential fallback selected by capability detection; add `openai_compatible` to the engine enum; document that a hook-less endpoint runs NO governance layer and give those surfaces an explicit "content-portable but ungoverned" security posture; define the fail-closed edit-emission fallback where a hook-firing host ignores a deny response. Promote the portability lint to `required=True` HERE — not because an early flip would red the four skills (it would not: portability is clean today at OK=72/MAJOR=0, and Agent/Task stay excluded until M3), but because `stack_runner`'s `required` flag gates the WHOLE `skill_lint` bundle (8 sub-checks, one switch at `stack_runner.py:159-163`), so flipping during M1's 53-skill rewrite risks bricking CI on transient findings elsewhere, and promoting before the fix gives false coverage. (D-187-07 already made portability blocking inside `skill_lint`'s own exit code, `cli.py:45-113`; this `required=True` flip is the OUTER pre-commit wrapper.) **Gate:** lint is Agent/Task-aware AND `required=True`; a smoke test drives one skill through the inline path with no Agent tool; hook-less surfaces documented as ungoverned (only `gitleaks` survives); the `openai_compatible` parity audit covers the full 11-event/matcher set (Codex today unwires 6/11, injection-guard Bash-only — do not replicate).
- **M4 — Cross-model eval (split: CI gate + operator battery).** (a) A CI-runnable **fixture-replay** layer — a Promptfoo custom-script provider (`exec:`/`file://` Python) returns a recorded tool-call fixture as `output` while carrying the real `tools:` schema, so `is-valid-openai-tools-call` + `tool-call-f1` validate the static output offline (schema from provider config, no endpoint, no credentials); a recorded MALFORMED tool_call reds the gate. CI uses `type:function` tools ONLY (`type:mcp` actually executes and must never appear). (b) An operator-run **live battery** — identical tests/assertions, provider swapped to `openai:chat:<model>` with `config.apiBaseUrl=${OPENAI_BASE_URL}`; operator-local acceptance, explicitly NOT a repo CI gate (§2: no model access in CI). Drop DeepEval for first ship (Promptfoo covers the named metrics). Feed live failures back per spec-185's re-entry doctrine. **Gate:** fixture-replay green in CI; the operator battery + its runbook documented; `driver-tier.json` non-frontier sessions produce an eval artifact.

## 7. Definition of Done

- A skill's BODY is hardened so that, on a floor-tier model, it elicits schema-valid tool calls: numbered procedure, flat schema, explicit tool descriptions, and a documented parse-and-correct retry bound. (Actual runtime recovery — constructing the call, setting temperature, echoing `reasoning_content`, executing the retry — is the harness/model's job, not the fleet's, per §2. The fleet guarantees content hardening + a testable annotation, not runtime behavior.)
- No canonical SKILL contains a literal Claude model family name as its selector; the `effort` axis is the sole skill vocabulary. Canonical AGENTS keep a Claude-valid `model:` for the frontier harness, generated from `AGENT_METADATA` + `effort`; the mirrors carry family hints.
- The four dispatch-only skills run to completion on a harness with no subagent primitive (inline-sequential fallback exercised by a test).
- `tool_name_map.py` is consumed by `core.py`, not inert; its `FamilyToolProfile` carries the generation/protocol quirk fields; its test asserts consumption.
- The engine enum includes `openai_compatible`; hook-less surfaces are documented as "content-portable but ungoverned"; where a host fires hooks but ignores a deny response, the edit fails closed.
- PR #639 is reconciled (merged or explicitly superseded), the naming collision gone, the `kimi` needle present.
- The M4 CI fixture-replay layer gates PRs (schema-validity + tool-call-F1 vs recorded responses); the live cross-model battery is documented operator-local acceptance, NOT a repo CI gate.
- Open-model acceptance is DETERMINISTIC/precomputed (fixture-replay + `gate-findings.json` `outcome`), never LLM-as-judge — a floor-tier model cannot reliably judge quality beyond its own ceiling; the value-lens already carves out gate verdicts + machine-checkable acceptance conditions as must-render-exact.
- All existing conformance/parity/portability tests green; new tests added for each milestone gate.

## 8. Quality Stamps

- **§10.1 KISS** — reuse the existing engine seam (`hook_context.py`) and the existing map (`tool_name_map.py`) rather than a new abstraction layer; wire what is already built before adding.
- **§10.2 YAGNI** — no model-access/router code (operator owns access); no LangGraph rewrite; inline fallback only where a real harness lacks subagents.
- **§10.3 SOLID** — dependency inversion: the core stops importing the Claude adapter; family quirks live behind one table.
- **§10.4 DRY** — one tool-name map, one driver-tier telemetry file, one effort vocabulary — no per-skill re-derivation.
- **§10.5 TDD** — every milestone lands its gate test first; portability lint extended in M1 (stays `required=False`) and promoted to `required=True` in M3, co-located with its fix.
- **§10.6 SDD** — this brief -> spec -> plan before any edit; the 4-mirror surfaces regenerate, never hand-edited (D-187-05).
- **§10.8 Hexagonal Architecture** — a ports/adapters inversion (core / model-adapter / dispatch-port / harness-port). The core carries model-neutral hygiene ONLY; per-family quirks live in the adapter table, never in skill prose — otherwise the core would import every adapter.
- Contracts honoured: Surface Axiom + No-Twin Axiom (`tests/architecture/test_surface_parity.py`), mirror count parity (`tests/mirrors/test_count_parity.py`), authoring rubrics (`tests/conformance/`).

## 9. Open Decisions

Choices the spec phase must resolve:

1. **PR #639: merge or supersede?** Merging preserves history but forces a rebase through the `AIENG_MODEL_TIER` purge. Superseding is cleaner but discards a reviewed branch. The driver-tier telemetry is the RUNTIME substrate M2-M4 read (M1 does not need it). Recommendation: rebase-and-merge M0 first, fixing the collision in the rebase; run M1 in parallel.
2. **Which vocabulary survives?** THREE axes coexist today: the neutral `effort` (`cheap|mid|high`, already live at `effort.py:40`), `model_tier` (`haiku|sonnet|opus`), and spec-185's driver tiers (`frontier`/`standard-floor`/`stretch-floor`). The spec must pick one authority. Recommendation: delete `model_tier`, promote the existing `effort` axis as the sole skill vocabulary, and keep the spec-185 tiers as the RUNTIME driver signal only (never a frontmatter field).
3. **How aggressive is the portability-lint promotion?** Making Agent/Task context-aware (M3) will flag the four dispatch-only skills — do they get a documented inline path (fix) or a risk-accepted exemption (defer)? The brief assumes fix, promoted in M3 alongside the fix.
4. **Eval battery scope for the first ship.** Which >=2 open families are the M4 live-battery acceptance floor — pick by the operator's actual configured surfaces, or fix a default pair (e.g. DeepSeek + GLM as the best-documented tool-callers)? (The CI fixture-replay layer is family-agnostic and always runs.)
5. **Security-guard fallback semantics.** On a host that FIRES hooks but ignores a deny response, do we fail-closed by refusing to emit the edit, or degrade to warn-only? `reference/gate-policy.md` says fail-closed at trust boundaries — but that may make some harnesses unusable. Explicit call needed.
6. **Delivery vehicle.** >=3 concerns and >40 files across 5 surfaces -> `/ai-autopilot` decomposition, or linear `/ai-plan` -> `/ai-build` per milestone? The collision pair is M1xM2 (both edit the same `SKILL.md`), NOT M0xM1 (M0 touches `driver_tier.py`/`_lib`, file-disjoint from `.claude/skills` — safe to parallelize). Skill BODIES embed `model_tier` literals (`ai-build/SKILL.md:22-26`), so the M1/M2 split is NOT clean by frontmatter-vs-body line range — dispatch ONE agent per `SKILL.md` applying M1 hygiene AND M2 `model_tier`->`effort` together in the same commit. Brief leans autopilot with that constraint.
7. **Quirk-table extension — RESOLVED (extend).** Append 7 Optional fields to `FamilyToolProfile` (`temperature_default`, `temperature_rescale_factor`, `min_p`, `system_prompt_constraint`, `reasoning_content_protocol`, `tool_choice_support`, `structured_output_mechanism`); all `X|None=None` so coverage can be uneven by design (`min_p` ships all-`None` — not on any card; `tool_choice_support` is free-text because forced-tool support varies, see M11). Additive → the 8 pinned tests stay green. The DRY/anti-drift argument depends on this single home, so extend rather than scatter.
8. **Hook-less endpoint governance — RESOLVED (ship ungoverned, documented).** A raw `/chat/completions` surface fires ZERO of the 11 hook events; the entire hook inventory including `prompt-injection-guard.py` is dark, only `gitleaks` (git-native pre-commit) survives. This is a structural property of headless model access, not a wiring gap — no engine-enum extension changes it. Ship those surfaces as "content-portable but ungoverned" with an explicit security posture. (Factual note: `value-lens` is a CI content contract not a hook; `session_bootstrap` is the `/ai-start` skill not a hook; "Ralph" is a loop inside `runtime-stop.py`.)
9. **EARS-style acceptance grammar — adopt optionally?** EARS (`WHEN <trigger> THE SYSTEM SHALL <response>`) is real (5 patterns, Mavin) and Kiro uses it natively for testable acceptance — but Spec Kit does NOT (open feature request #1356, unshipped), and Böckeler is skeptical of the "spec-anchored" middle ground the finding cited (misattribution — she leans spec-first). The framework has ZERO EARS today; `spec_lint` Goals are freeform verifiable bullets. Decision: adopt EARS as an OPTIONAL grammar for the machine-checkable subset of §14 Acceptance (helps floor models follow unambiguous, testable criteria) without mandating it fleet-wide or conflicting with the freeform Goals contract, or defer as ceremony. Recommendation: optional, opt-in per spec.

## 10. Migration

Hard changes per CONSTITUTION.md §3 — no backwards-compat shims (§13.3).

- **Hard rename** `AIENG_MODEL_TIER` -> `AIENG_DRIVER_TIER` (the former is already purged from main; M0 completes the rename and its telemetry consumer). CHANGELOG documents the breakage.
- **Hard replace** literal `model: opus|sonnet` frontmatter and `model_tier: haiku|sonnet|opus` with the neutral vocabulary across 19 agents + 53 skills + 4 mirror surfaces in one regeneration pass; no dual-read of old + new field names.
- **Hard delete** the "inert" status of `tool_name_map.py` — it is consumed or it is removed; no third state.
- **Reconcile** PR #639 in-place (rebase through the purge), not as a parallel branch — one substrate, not two.
- **Supersession note:** this brief supersedes the model-portability portion of the shipped spec-187 (its non-goal deferral) and the observe-only ceiling of spec-185; both are explicitly named so the audit trail is unbroken.

## 11. Risks

Likelihood x Impact, with mitigations.

| Risk | L | I | Mitigation |
|------|---|---|------------|
| Rebasing PR #639 through the `AIENG_MODEL_TIER` purge silently drops the driver-tier consumer | Med | High | M0 rebases first with the collision as an explicit task; branch-only parity tests (`test_driver_tier_parity.py`) ported to main as the gate |
| Promoting the `required=True` lint flip too early gives FALSE coverage (blind to Agent/Task) and can brick CI (the flag gates the whole `skill_lint` bundle) | Med | High | Extend the lint in M1 but keep `required=False`; flip `required=True` only in M3, co-located with the Agent-awareness + inline fix (`stack_runner.py:159-163` is a single bundle switch) |
| M1xM2 (NOT M0xM1) edit the same `SKILL.md` files — bodies embed `model_tier` literals (`ai-build/SKILL.md:22-26`) — so naive per-milestone waves collide | Med | Med | One agent per `SKILL.md` applies M1 hygiene + M2 `model_tier`->`effort` in the same commit; M0 is file-disjoint (`driver_tier.py`) and stays a separate parallel wave |
| Neutral-frontmatter regeneration breaks the 5-surface mirror parity | Med | Med | Regenerate via `core.py` only (never hand-edit mirrors); `test_count_parity.py` + surface-parity as the gate before merge |
| Security guard degrades open on a host that ignores deny responses -> unguarded edits; hook-less endpoints run NO governance at all | Med | High | Fail-closed at the edit-emission boundary (Open Decision 5); document hook-less surfaces as "ungoverned" with an explicit posture (Open Decision 8); do not ship M3 without both resolved |
| Per-family quirks drift as vendors ship point-releases (Kimi temp rescale, DeepSeek reasoning-echo) | High | Med | Encode quirks in ONE extended table (`FamilyToolProfile`), not scattered across 53 skills; M4 fixture-replay catches format regressions per family |
| "Works on open models" is claimed without live proof (spec-187's exact trap) | Med | High | M4 CI fixture-replay gates PRs deterministically (no creds); the live battery is operator-local acceptance — proven in CI by fixtures, validated live by the operator |
| "Cannot force a tool" premise over-generalizes one DeepSeek thinking-mode limitation | Med | Med | Closed matrix: DeepSeek reasoner/V4 + GLM-4.6 (auto-only) reject forced `tool_choice`; non-thinking DeepSeek + Qwen + Kimi K2 accept required/forced-fn; MiMo unverified. Ship the per-family `tool_choice_support` field (deepseek=`non-thinking-only`, glm=`auto-only`, qwen=`full`, kimi=`full`, mimo=`unverified`); justify the inline fallback by subagent-absence, not `tool_choice`; route forced-tool work to a non-thinking model or auto+validation |
| No rollback/kill-switch for a >40-file hard cutover if a floor-tier model regresses | Med | Med | Milestone-ordered landing with a per-milestone revert procedure; driver-tier-gated floor hardening so frontier behavior is untouched until the port is proven |
| MiMo remains unverified (no primary source) and blocks the family matrix | Med | Low | Keep MiMo `verified=False`; exclude from the M4 acceptance floor until a primary source exists; do not gate on it |

## 12. References

External evidence (cited, from the parallel research sweep). Every claim above that rests on model behavior traces to one of these.

- Agent Skills SKILL.md open standard, 30+ tools adopted (Codex, Copilot, Cursor, Gemini CLI, VS Code) — [aggregator; corroborate the count against agentskills.io / Anthropic's spec before quoting it]: https://noqta.tn/en/news/skill-md-open-standard-30-ai-coding-tools-adoption-2026
- AGENTS.md standard (flat project context, no skill/subagent concept), Linux Foundation stewarded: https://agents.md
- DeepSeek function calling + strict mode (`additionalProperties:false`, all-props-required): https://api-docs.deepseek.com/guides/function_calling
- DeepSeek THINKING-MODE rejects `tool_choice:"required"` (HTTP 400 "Thinking mode does not support this tool_choice"); non-thinking `deepseek-chat` accepts forced tool/function: https://github.com/deepseek-ai/DeepSeek-V3/issues/1376
- DeepSeek thinking-mode drops sampling params (temperature etc.): https://api-docs.deepseek.com/guides/thinking_mode/
- DeepSeek thinking-mode requires echoing `reasoning_content` each turn or HTTP 400: https://github.com/n8n-io/n8n/issues/22579
- Qwen function calling: vendor warns tool calls can be malformed, parse yourself in production: https://qwen.readthedocs.io/en/latest/framework/function_call.html
- Qwen structured output requires the literal word "JSON", up to 128 functions: https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output
- Kimi K2 model card: temp 0.6; Anthropic-compatible endpoint silently rescales temp x0.6 (the earlier min-p figure is dropped — not on the card): https://huggingface.co/moonshotai/Kimi-K2-Instruct
- GLM-4.6 (200K context, tool-use during inference), Z.ai docs: https://docs.z.ai/guides/llm/glm-4.6
- GLM-4.6 forced tool_choice unsupported ("only auto is supported"), Z.ai API reference: https://docs.z.ai/api-reference/llm/chat-completion
- Qwen supports auto/required/none/forced-function tool_choice: https://www.alibabacloud.com/help/en/model-studio/qwen-function-calling
- Kimi K2 supports required/forced-function tool_choice: https://platform.kimi.ai/docs/api/chat
- Promptfoo custom-script provider (offline fixture-replay, no credentials): https://www.promptfoo.dev/docs/providers/custom-script/
- Promptfoo Python provider returns canned/recorded output: https://www.promptfoo.dev/docs/providers/python/
- Promptfoo deterministic assertions (`is-valid-function-call` / `is-valid-openai-tools-call` / `tool-call-f1`, validate static output offline): https://www.promptfoo.dev/docs/configuration/expected-outputs/deterministic/
- Promptfoo openai-compatible `apiBaseUrl` (live operator battery): https://www.promptfoo.dev/docs/providers/openai/
- Berkeley Function-Calling Leaderboard (BFCL v3/v4 holistic agentic eval): https://gorilla.cs.berkeley.edu/leaderboard.html
- Lost in the Middle (Liu et al.) — U-shaped position curve, front-loading mitigates (~20-30pt), holds to ~30B open models (the "7B extracts YAML without reasoning" rider is NOT from this paper): https://arxiv.org/abs/2307.03172
- "Let Me Speak Freely?" (EMNLP 2024) — strict JSON-mode drops REASONING 25-63pp (not 10-15%); structured EXTRACTION gains +18.8pp; reason-in-prose-then-serialize recovers most: https://arxiv.org/abs/2408.02442
- Anthropic Contextual Retrieval — the -67% is a full RAG pipeline (embeddings+BM25+rerank), explicitly NOT document authoring, so N/A to static skill markdown; ParadeDB "+40-60% from stable headers" has no locatable primary source: https://www.anthropic.com/engineering/contextual-retrieval
- EARS (Easy Approach to Requirements Syntax), Mavin — 5 patterns (Ubiquitous / WHEN / WHILE / WHERE / IF-THEN): https://alistairmavin.com/ears/
- AWS Kiro uses EARS for acceptance criteria (Spec Kit does NOT — feature request #1356; Böckeler is skeptical of "spec-anchored"): https://kiro.dev/docs/specs/feature-specs/requirements-first/
- TOON (Token-Oriented Object Notation) — tabular-only, -7pp on nested data; do NOT adopt for instruction docs: https://github.com/toon-format/toon
- opencode subagents (Task tool / `@mention`, markdown agent files) — closest analog to Claude dispatch: https://opencode.ai/docs/agents/
- Roo Code Orchestrator / Boomerang subtasks: https://docs.roocode.com/features/boomerang-tasks
- Promptfoo tool-call assertions (`is-valid-function-call`, `tool-call-f1`) + model x prompt matrix: https://www.promptfoo.dev/docs/configuration/tools/
- DeepEval Tool Correctness (deterministic `tools_called` vs `expected_tools` + Argument Correctness): https://deepeval.com/docs/metrics-tool-correctness
- SWE-bench Verified reliability caveat (~19.78% solved cases semantically incorrect) — [aggregator (steel.dev); cite the primary SWE-bench-Verified audit before quoting the figure]: https://leaderboard.steel.dev/leaderboards/swe-bench-verified/

## 13. Glossary

- **Open model / open-weight model** — Qwen, DeepSeek, Kimi (Moonshot), GLM (Zhipu/Z.ai), MiMo (Xiaomi): weights published, served behind an OpenAI-compatible `/chat/completions` API by the operator's own surface.
- **OpenAI-compatible surface** — any harness or endpoint (Cline, opencode, Codex, vLLM, Ollama, a hosted API) exposing the OpenAI messages + tools schema; the framework never provisions this.
- **Driver tier** — spec-185's vendor-neutral capability bucket (`frontier` / `standard-floor` / `stretch-floor`) resolved from the SessionStart `model` field, published to `driver-tier.json`.
- **Dispatch port** — the mechanism a harness uses to run a subagent in isolated context (Claude Agent tool, opencode Task, Roo Boomerang) or its absence (Cline/Aider/Codex -> inline-sequential).
- **Inert artifact** — code shipped but wired into no consumer (the current state of `tool_name_map.py`).
- **Parse-and-correct loop** — a bounded (2-3 pass) retry that catches a malformed tool-call payload, returns the exact parse error to the model, and asks it to reissue — mandatory on open models per vendor docs.
- **Tool-call-F1** — eval metric: F1 of the set of tools the model called vs the expected set.
- **BLUF** — bottom-line-up-front: the one-line takeaway stated at the very top so a floor-tier model reads it before drifting (front-loading, Liu et al.). In this repo the skill BLUF is the `description` field.
- **EARS** — Easy Approach to Requirements Syntax: 5 controlled-natural-language patterns (Ubiquitous / WHEN / WHILE / WHERE / IF-THEN) for unambiguous, testable acceptance criteria.
- **Precomputed deterministic verdict** — a pass/fail computed by rule (exit codes, schema check) rather than asked of the model; the only trustworthy acceptance signal on a floor model, which cannot judge quality beyond its own ceiling.

## 14. Acceptance

Checklist form of the Definition of Done (§7):

- [ ] A skill body on a DeepSeek/Qwen/GLM/Kimi surface elicits schema-valid tool calls; the body carries a documented parse-and-correct retry bound (runtime recovery is the harness's job, §2).
- [ ] No canonical SKILL uses a literal Claude model family name as its selector; agents keep a generated Claude-valid `model:` for the frontier harness, family hints in the mirrors.
- [ ] `model_tier` deleted; the neutral `effort` axis is the sole skill vocabulary; the atomic lockstep set (regex, frozenset, SSOT table, frontmatter, `AGENT_METADATA`) lands in one commit.
- [ ] The four dispatch-only skills run to completion with no subagent primitive available (inline fallback, test-exercised).
- [ ] `tool_name_map.py` is consumed by `core.py`; `FamilyToolProfile` carries the generation/protocol quirk fields; its test asserts consumption, not inertness.
- [ ] Engine enum includes `openai_compatible`; hook-less surfaces documented as "content-portable but ungoverned"; fail-closed edit-emission where a hook-firing host ignores a deny response.
- [ ] PR #639 reconciled; `AIENG_MODEL_TIER` fully renamed; `kimi` needle present in `_FAMILY_TIERS`.
- [ ] M4 CI fixture-replay gate green (schema-validity + tool-call-F1 vs recorded responses); the live cross-model battery documented as operator-local acceptance, not a repo CI gate.
- [ ] Portability lint promoted to `required=True` in M3 (Agent/Task-aware), extended-but-`required=False` in M1; all conformance/parity tests green.
- [ ] CHANGELOG documents every hard rename/replace/delete; no backwards-compat shim introduced.
