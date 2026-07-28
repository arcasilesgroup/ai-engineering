---
title: "Three-Layer Agentic Stack — harden ai-engineering as the harness+loop layer for open models, under a graph layer and a governance plane"
status: draft
audience: framework-dev / operator
branch: feat/three-layer-open-model-harness
length_estimate: program (5 milestones M0-M4, >=4 concerns, >=60 files across canonical + 5 mirror surfaces; M3/M4 are separate deliverables)
authoring_style: diagnostic-brief
principles_required:
  - "§10.1 KISS"
  - "§10.2 YAGNI"
  - "§10.3 SOLID"
  - "§10.5 TDD"
  - "§10.6 SDD"
  - "§10.8 Hexagonal Architecture"
delivery_mode: /ai-autopilot
mantra: "The prompts already port. The harness does not."
---

# Three-Layer Agentic Stack — harden ai-engineering as the harness+loop layer for open models

> Successor to shipped **spec-189** (`open-model-portability`, PR #644 merged
> `c4c8063d`), which delivered *content-only* portability — `model_tier` retired in
> favour of `effort`, an agent `model:` validator, `tool_name_map` consumed at build
> time, BLUF front-loading enforced — and explicitly deferred live open-model
> execution and the eval layer
> (`.ai-engineering/specs/archive/spec-189-open-model-portability/spec.md:92-94`).
>
> **This brief is written against measurement, not inference.** On 2026-07-27 the four
> nan.builders chat models were probed directly and the real always-on context was
> replayed against them. Nine desk-research findings that would otherwise have shaped
> this spec were refuted by those probes and are recorded as dead in §5.2. Read §3.1
> before §4: the diagnosis inverted.

---

## 1. Vision

ai-engineering becomes the **harness and loop layer** of a three-layer agentic stack:
a graph layer (LangGraph) composes its skills into explicit topologies, and a
governance plane (Paperclip) owns the org chart, the budget and the human gates. For
that to be worth building, the bottom layer has to hold on models it was never
designed for — and on hosts that are not Claude Code.

The forcing function is not hypothetical. Local session transcripts already record
**22 sessions driven by open models, 10 of them inside this repository**:
`xiaomi/mimo-v2.5` across 12 sessions, `tencent/hy3` across 5 (plus 3 more on the
`:free` tier), `moonshotai/kimi-k3`, and `cohere/north-mini-code:free` — roughly 4,000
assistant messages, with zero recorded tool errors. The operator is running this
framework on open models today. The framework does not know it, cannot bill it, and
cannot guard it.

The measurement changed the thesis. The assumption behind the whole portability
lineage — that weaker models would fail to follow the fleet's prompts — is false at
the scale this repository operates. Against the real assembled always-on context
(`CLAUDE.md` plus all 54 skill `description` lines: 40,419 chars, measured
`prompt_tokens` 9,947-10,482), skill routing scored **8/8 on deepseek-v4-flash, 8/8 on
mimo-v2.5, 8/8 on gemma4**, with qwen3.6 correct 3/3 on retry. Handed the real
`.claude/skills/ai-commit/SKILL.md` body and a bash tool, **all four models made a
correct first tool call**. spec-189's content work holds up under load.

What does not hold up is everything below the prompt. There is no Anthropic Messages
API on this endpoint, so Claude Code — the only harness where the deterministic plane
is whole — cannot reach these models at all. The two hosts that can reach them run
**zero of the eleven canonical hook events**. The security guarantee does not degrade;
it disappears. And no supported path exists to invoke a skill from a subprocess, so
the graph layer above rests on an interface that was never built.

The win is a framework whose guarantees are a property of the *stack*, not of one
vendor's IDE.

---

## 2. Scope Boundary

**In scope**

- A fifth engine identity (`openai_compatible`) plus the enum amendments that let a
  non-Claude host emit audit events at all (`tools/skill_domain/event_schema.py:33-34`
  and its byte-twin `.ai-engineering/scripts/hooks/_lib/hook-common.py:50-53`).
- **OpenCode as the reference open-model harness**: a repo-root sync target, a working
  plugin-based guard plane, and the missing `agents/internal/` roster.
- The five heaviest dispatch-only skills gaining a real, tested inline fallback:
  `ai-build`, `ai-autopilot`, `ai-plan`, `ai-explore`, `ai-pr`.
- A per-family **capability table** recording measured runtime quirks
  (`schema_enforced_server_side`, `min_completion_budget`, reasoning-split), replacing
  today's four-field `FamilyToolProfile`
  (`scripts/sync_mirrors/tool_name_map.py:87-95`).
- **Spend-cap enforcement** — the schema slot exists end to end
  (`src/ai_engineering/state/observability.py:283-285`); only the producer is missing,
  and the provider now returns per-request cost.
- Widening `skill_lint` to the 58 handler files it currently cannot see
  (`tools/skill_lint/checks/portability.py:211-222`).
- A **read-only skill resolver** verb (name to canonical `SKILL.md` path plus handler
  set) — metadata, not execution.
- A cross-model replay gate in CI.

**Explicitly NOT in scope**

- **Model management.** D-189-01 stands: no runtime that detects, routes, selects,
  ranks or calls a model on the operator's behalf
  (`.ai-engineering/specs/archive/spec-189-open-model-portability/spec.md:85-86`). The
  capability table is *build-time data*, not a dispatcher. Reversing D-189-01 is
  Open Decision OD-1 and this brief does not assume it.
- **An `ai-eng skill run` verb.** It duplicates the harness's own skill loader, puts
  the framework into prompt assembly and tool wiring it owns none of, and lands on the
  wrong side of `CLAUDE.md:83`. §4.3 proposes the harness-native headless runner
  instead.
- **Semantic routing via the available `qwen3-embedding` / `rerank` models.** They are
  real and reachable, but E10 shows the retrieval problem they would solve does not
  exist, and any network call on the `UserPromptSubmit` path violates the
  under-1-second hot-path budget (`CLAUDE.md:166-173`). Record availability; do not
  wire it.
- **Building the graph layer or the Paperclip adapter inside this repository.** M3 and
  M4 are scoped here so M0-M2 build the right seams, but they ship separately — direct
  precedent: spec-178 shipped the website to `arcasilesgroup/ai-engineering-web`.
  Adding LangGraph to a wheel of stdlib-only hooks is a dependency-footprint decision
  (OD-7), and consumer installs have been bricked by less (spec-179).
- **Anything requiring Claude Code to reach nan.builders.** It cannot. See E2.

---

## 3. Diagnostic Snapshot

### 3.1 The inversion — what measurement killed

Nine findings that desk research rated blocker or high were refuted by direct probe.
They are recorded here because a spec written from the research alone would have
solved the wrong problems.

| # | Research claim | Verdict |
|---|---|---|
| 1 | "Tool calling validated on ONE model only; collapses the usable fleet to one model" | **REFUTED.** All four return HTTP 200 on single, parallel (n=2) and forced tool calls (E4) |
| 2 | "DeepSeek V4 rejects named-function `tool_choice` with HTTP 400" | **REFUTED for this deployment.** Forced `tool_choice` returns 200 (E4). Upstream `api.deepseek.com` behaviour does not transfer to this gateway |
| 3 | "vLLM 400 when reasoning + forced tool_choice combine; unsafe on every thinking model" | **REFUTED for this deployment.** No model rejected it (E4) |
| 4 | "No prompt caching; no cache-hit signal; treat every turn as full-price prefill" | **REFUTED.** `cached_tokens: 192` on mimo-v2.5, `cache_write_tokens` on deepseek (E6) |
| 5 | "mimo-v2.5 appears in no reachable model list; a 404 is possible at any time" | **REFUTED.** `GET /v1/models` returns it (E1) |
| 6 | "`json_schema` strict exists only on the two 256K models" | **HALF-REFUTED.** deepseek returns schema-valid strict output; mimo returns 200 with schema-**invalid** content — worse than a rejection (E5) |
| 7 | "Parallel tool calling unverified for all four" | **RESOLVED.** All four emit n=2 in one turn (E4) |
| 8 | "OpenAI-compatible via LiteLLM" | **CORRECTED.** `gen-`-prefixed ids with `provider_specific_fields` + `is_byok` indicate an OpenRouter-shaped aggregator (E3) |
| 9 | gemma4 "disregards the system prompt, rarely emits tool calls, degrades as context fills" | **NOT REPRODUCED** at this scale: 8/8 routing under the real 10.1K preamble (E10), correct first tool call (E11). Survives only as unverified beyond ~10.5K prompt tokens |

The one conclusion measurement **confirms and sharpens**: skill-description routing is
not the portability problem. That also kills the correctness justification for
stripping the 1,761-token `Trigger for` block from descriptions — it remains valid
only as a token-cost measure, never as a reliability fix.

### 3.2 The three real gaps

**Gap A — no reachable harness with a guard plane.**

`POST /v1/messages` returns 404 and `POST /anthropic/v1/messages` returns 404 against
`api.nan.builders`; only `/v1/chat/completions` works (E2). The cheapest imaginable
plan — repoint Claude Code with `ANTHROPIC_BASE_URL` and change nothing — **does not
exist for this provider**. Open-model execution must run on an OpenAI-shaped host, and
that is precisely where the deterministic plane is missing:

| Harness | Canonical hook events wired | Security guarantee |
|---|---|---|
| Claude Code | **11 / 11** (`.claude/settings.json:46,68,110,162,174,196,208,220,242,254,266`, count CI-locked at `tests/unit/hooks/test_canonical_events_count.py:24-40`) | EQUIVALENT — baseline |
| Codex | 4 / 11 (`.codex/hooks.json:3,25,47,65`; `SessionStart` declared empty at `:64`) | DEGRADED — and worse than the headline |
| OpenCode | **0 / 11** | ABSENT |
| pi.dev | **0 / 11** | ABSENT, and unbuilt |
| headless CLI | git plane 100%, tool plane 0% | SPLIT |

Stated plainly, because these are security findings and hedging them would be
misleading:

- **On Codex, `git commit --no-verify` is available.** `no-verify-guard.py` is wired at
  `.claude/settings.json:68` but absent from `.codex/hooks.json:25`, so the §13.6
  "never `--no-verify`" rule has no enforcer and a commit can bypass gitleaks, format
  and lint entirely. Separately, `injection-read-guard.py` is wired at
  `.claude/settings.json:110` but absent from `.codex/hooks.json:47`, so content
  injected into a `tool_response` — a fetched page, an MCP payload, a file read — is
  never scanned. `mcp-health.py` is absent at both events, so its fail-closed block on
  an unhealthy MCP server (`mcp-health.py:488-503`) does not exist there.
- **On OpenCode the entire tool plane is unguarded.**
  `.ai-engineering/scripts/hooks/opencode-hook-bridge.ts:84-90` has a `dispatch()` that
  returns `0` unconditionally; nothing loads it (no `.opencode/plugins/`, no
  `opencode.json` in repo or template, `src/ai_engineering/installer/templates.py:199-201`);
  and the one hook that could veto was mapped to the passive read-only `permission.asked`
  bus event rather than the blocking `permission.ask` with a mutable `output.status`
  (`opencode-hook-bridge.ts:28-51` vs `.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts:225-227`).
  The posture also inverts: OpenCode defaults most permissions to allow, and `--auto`
  auto-approves everything not explicitly denied — the opposite of the fail-closed rule
  at `.ai-engineering/reference/gate-policy.md`. The repo still lists `opencode` in
  `surfaces.enabled` (`.ai-engineering/manifest.yml:28-35`), and its only tests assert
  string presence in the `.ts` file rather than behaviour
  (`tests/integration/hooks/test_opencode_bridge.py:8-36`). Green CI here means nothing.
- **`.ai-engineering/scripts/hooks/cursor-hook-bridge.py:64-68` is structurally dead** —
  it dispatches to a lowercase filename (`pretooluse.py`) that does not exist, so every
  call hits the missing-handler branch and returns `0`. It is nonetheless sha-pinned at
  `.ai-engineering/state/hooks-manifest.json:61`, which makes it look enrolled.
- **Two audit-plane facts make all of the above undetectable after the fact.** The
  `engine` field is a closed 5-value enum (`tools/skill_domain/event_schema.py:33-34`,
  duplicated at `.ai-engineering/scripts/hooks/_lib/hook-common.py:50-53`); any event
  carrying `opencode`, `cursor`, `pi`, `langgraph` or the fallback `unknown`
  (`_lib/hook_context.py:131-147`) is silently refused. And `ai-eng audit verify`
  **always exits 0 by design** (`src/ai_engineering/cli_commands/audit_cmd.py:95-98`),
  with the doctor check hardcoded to WARN
  (`src/ai_engineering/doctor/phases/state.py:170-202`). Live stream confirms the blind
  spot: `claude_code` 48,115 events, `codex` 7,768, `ai_engineering` 6,222,
  `copilot` 9 — **zero cursor, zero opencode, zero antigravity**.

**Gap B — the subagent cliff, and it is architectural not stylistic.**

Nine skills dispatch subagents. Only four document an inline fallback
(`.claude/skills/ai-review/SKILL.md:74`, `ai-verify/SKILL.md:99`,
`ai-advise/SKILL.md:83`, `ai-simplify/SKILL.md:91`), and **three of those four
contradict it elsewhere in the same file** (`ai-review/SKILL.md:56`,
`ai-verify/SKILL.md:81`, `ai-advise/SKILL.md:69` each forbid reading agent files
inline). Coverage is inverted against risk: the five that carry **no** fallback —
`ai-build`, `ai-autopilot`, `ai-plan`, `ai-explore`, `ai-pr` — include the two that
dispatch unbounded N with three-level nesting. No test asserts any fallback paragraph.

E4 re-scopes this precisely: parallel tool calling works on all four models, so this is
a **harness-primitive** gap, not a model-capability gap. Any claim that open models
cannot drive fan-out is unsupported and must be dropped from the spec.

But five invariants need *isolation*, not concurrency, and inline execution violates
all five:

1. **Adversarial validation** — `.claude/agents/review-validator.md:56` ("You receive
   only the YAML finding block"). Inline, the context that produced the finding
   validates it; CONFIRMED/DISMISSED degrades to self-confirmation.
2. **Corroboration** — confidence is defined as the same finding surfacing from two
   independent agents (`.claude/skills/ai-autopilot/handlers/phase-quality.md:152-154`,
   `.claude/skills/ai-build/handlers/quality.md:92-94`). One context is one source, so
   the signal gating the bounded remediation pass becomes structurally unobtainable.
3. **Maker/checker separation** — enforced at the tool-declaration level:
   `.claude/agents/ai-build.md:3` is "the ONLY agent with code write permissions"
   against read-only reviewers. Inline, the checker holds Write and
   `ai-review/SKILL.md:72`'s "never modifies code" becomes prose.
4. **Transparency Protocol** — `hallucinated`/`aspirational` classification requires a
   different phase to cross-check the implementer's self-report
   (`.claude/skills/ai-autopilot/handlers/phase-implement.md:133`).
5. **Per-task isolation** — `.claude/skills/_shared/execution-kernel.md:13` ("Never let
   an agent carry context across tasks — isolation is the point").

Wave parallelism is *not* in this list and degrades cleanly: a fully-serial DAG is
documented as "an expected DAG shape, not a failure"
(`.claude/skills/ai-autopilot/handlers/phase-orchestrate.md:178`). Only DAG order is
correctness-bearing, and order survives serialization.

Audit trap: only 2 of 19 agent files declare the `Agent` tool
(`.claude/agents/ai-review.md:6`, `ai-verify.md:6`). The two heaviest dispatchers —
`ai-autopilot.md:6` and `ai-build.md:6` — do not, so any audit driven off `tools:`
frontmatter misses them entirely.

**Gap C — no programmatic entry, and the audit plane cannot see a graph node.**

Inside the framework the answer is unambiguous. `src/ai_engineering/cli_factory.py:502-508`
registers exactly one skill verb, `status`; `src/ai_engineering/cli_commands/skills.py:3,31-34`
is scoped to eligibility diagnostics and never reads a `SKILL.md` body. And
`CLAUDE.md:83` states verbatim: *"Invoke a skill via `/ai-<name>` in the IDE agent
surface — never via a synthetic terminal equivalent."*

That sentence forbids exactly the shape a graph layer would reach for. It does **not**
forbid driving a real IDE agent surface headlessly — but it carries no carve-out
saying so, which leaves a graph layer out-of-contract by ambiguity rather than by rule.

Three headless entries exist on the harness side, ranked by evidence:

| Entry | Status |
|---|---|
| `opencode run --command <name> [args] --format json` | **VIABLE, live-verified on 1.18.5.** Slash commands are a first-class addressable name, not a prompt-string convention. `--agent`, `--model provider/model`, `--session/--continue/--fork`, `--dir` all present. Server twin: `POST /session/:id/command` |
| `claude -p "/ai-<name> <args>"` | VIABLE, but a string-prompt convention rather than a typed API — and unusable against nan.builders (E2) |
| `codex exec "<prompt>" --json --output-schema <FILE>` | VIABLE for prompts; `/ai-` slash resolution unverified. Strongest structured-return contract in the set |
| `pi --print` + `/skill:<name>` | PARTIAL. `/skill:` is bound to the interactive TUI, and the model-side `<available_skills>` channel is emitted **only when the `read` tool is active** — running `--tools bash` silently drops all skills with no warning |

Two further dependencies must not be papered over. A graph node emitting as `langgraph`
writes **nothing** (the 5-value enum above, `emit` returns False with a stderr log
only). And token/cost attribution is Claude-Code-filesystem-coupled: the model string
comes only from a local Claude transcript path and `genai_system` is hardcoded to the
literal `"anthropic"` on every emission regardless of driver
(`.ai-engineering/scripts/hooks/_lib/transcript_usage.py:194,205-215`).

**The closed-enum failure is not hypothetical — it is dropping first-party events
today.** `.claude/skills/ai-spec-draft/SKILL.md` step 6 instructs emitting
`framework_event kind=brief_drafted`. `brief_drafted` is not a member of
`ALLOWED_EVENT_KINDS` (`tools/skill_domain/event_schema.py`), so the emit is refused
with `hook-common: refusing to emit malformed event` and returns False. Reproduced
while drafting this brief. Every `/ai-spec-draft` run since the skill shipped has
silently failed its own audit step, and nothing surfaced it — because a refused emit
writes to stderr and returns a boolean nobody checks. The same mechanism that will
silently swallow a graph node's telemetry is already swallowing a skill's. Fixing this
is a one-value enum addition across the two byte-twins, and it belongs in M0 as the
cheapest possible proof that the enum change works end to end.

### 3.3 What is measurably fine

Recorded so the spec does not spend effort here.

- **Content routing and procedural adherence** (E10, E11) — see §3.1.
- **Progressive disclosure already works.** 94,474 tokens across 79 files sit behind
  invocation gating — **59.5% of the skill tree**. The always-on tier is only 8.5% of
  the 120,855-token canonical corpus, so a further Anthropic-style 80% cut cannot come
  from handlers; it can only come from the always-on floor.
- **The deterministic verifier layer is the strongest thing in the repo** and the
  correct foundation for weak models: `.claude/agents/verifier-deterministic.md:17,21-68`
  runs gitleaks, ruff, pip-audit, pytest and ty in fixed order and reports exit codes,
  not opinions.
- **Bounded retries exist three independent ways** — `AIENG_RALPH_MAX_RETRIES` default
  5 clamped to a ceiling of 50 (`.ai-engineering/scripts/hooks/runtime-stop.py:74-76`),
  a per-check CI fix cap of 3 (`.claude/skills/ai-pr/handlers/watch.md:36`), and a
  wall-clock bound (`:86-89`). Clamping the env var itself exceeds the doctrine.
- **A BLOCKED third state already exists** and the research missed it: `/ai-build
  --no-hitl` promotes `NEEDS_CONTEXT` to `BLOCKED`, emits a structured
  `Reason/Detected/Recovery/Then retry` envelope and exits **78**
  (`src/ai_engineering/cli_commands/_exit_codes.py:52`;
  `.claude/skills/ai-build/handlers/no-hitl.md:90-142,144-163`).
- **The git plane is fully harness-independent.** `.git/hooks/pre-commit:1-6` and
  `pre-push:6` shell to `ai-eng gate <hook>` with no IDE dependency, reaching gitleaks
  (`src/ai_engineering/policy/checks/stack_runner.py:150-151`), semgrep (`:238-251`)
  and pip-audit (`src/ai_engineering/verify/tls_pip_audit.py:26-71`).

### 3.4 Two accuracy defects worth naming now

- **`.claude/skills/ai-build/SKILL.md:3` asserts the build agent runs "in an isolated
  worktree". There is no `ai-eng worktree` verb and no worktree step in
  `.claude/skills/_shared/execution-kernel.md`.** Actual isolation is declarative
  file-boundary frontmatter plus "Agent MUST stop immediately"
  (`.claude/skills/ai-autopilot/handlers/phase-implement.md:240`) — an honour system.
  This is a user-facing description claiming a mechanism the workflow never performs,
  and it is the class of instruction that degrades first on a weaker model.
- **`tiktoken` is absent from the project `.venv`**, so `tools/token_baseline/count.py:16-19`
  silently falls back to `len(text)/4` and reports 125,165 against a real 120,855 —
  a +3.6% overstatement that every published token claim inherits.

---

## 4. Architecture

### 4.1 Layer contract

```
+---------------------------------------------------------------+
|  GOVERNANCE PLANE  (Paperclip - separate product)             |
|  org chart | budget ceilings | human approvals | cost ledger  |
|  drives via: subprocess + exit code + PAPERCLIP_* env vars    |
+---------------------------------------------------------------+
                              |
+---------------------------------------------------------------+
|  GRAPH LAYER  (LangGraph - separate package)                  |
|  StateGraph | conditional edges | per-cycle counters          |
|  | checkpoint + interrupt() | deterministic non-LLM nodes     |
|  drives via: harness-native headless command runner           |
+---------------------------------------------------------------+
                              |
+===============================================================+
|  LOOP LAYER          (ai-engineering - THIS SPEC)             |
|  deterministic verifiers | bounded retries | stop conditions  |
|  externalized state | maker/checker | BLOCKED | spend caps    |
+---------------------------------------------------------------+
|  HARNESS LAYER       (ai-engineering - THIS SPEC)             |
|  54 skills | 19 agents | 11 hook events | gate plane          |
|  | engine identity | tool-name map | capability table         |
+===============================================================+
                              |
+---------------------------------------------------------------+
|  MODEL ACCESS  (operator-owned, NOT built here - D-189-01)    |
|  OpenAI /v1/chat/completions only - no Messages API (E2)      |
+---------------------------------------------------------------+
```

The boundary that matters: **the graph layer never reaches inside a skill.** It
addresses a skill by name through the harness's own command runner and consumes an
exit code plus a JSON event stream. That keeps prompt assembly, model routing and tool
wiring inside the harness — where they already live — and keeps this repository out of
the model-management business D-189-01 forbids.

### 4.2 Engine identity — the unblocking change

Both twins are amended in lockstep to admit an `openai_compatible` engine, and the
enum gains the values a foreign host actually emits:

- `tools/skill_domain/event_schema.py:33-34` (validation source)
- `.ai-engineering/scripts/hooks/_lib/hook-common.py:50-53` (hook-side byte twin)

A compounding defect ships with it: `hook-common.py:386,471,510,633` default to
`"claude_code"` while `hook_context.py:147` defaults to `"unknown"`, so under a foreign
harness some events are mislabelled as Claude and accepted while others are dropped.
Multi-harness attribution is impossible until both defaults agree.

### 4.3 The execution seam

**Proposal: the harness-native headless command runner is the graph layer's single
execution primitive**, with `opencode run --command` (and its
`POST /session/:id/command` server twin) as the reference implementation.

Rejected alternative: an `ai-eng skill run <name>` verb. It duplicates the harness's
own skill loader, puts the framework into prompt assembly it does not own, and lands
on the wrong side of `CLAUDE.md:83`.

The one seam legitimately missing from `ai-eng` is a **read-only skill resolver** — a
verb mapping `ai-build` to its canonical `SKILL.md` path plus handler set, so a
subprocess can hand the body to whatever harness it drives without hardcoding
`.claude/skills/<name>/SKILL.md`. That is metadata, and it sits naturally alongside the
existing `skill status`.

`CLAUDE.md:83` gains an explicit carve-out: driving a real IDE agent surface headlessly
is not a synthetic terminal equivalent.

### 4.4 OpenCode as the reference open-model surface

Four defects, one root cause.

Root cause: `src/ai_engineering/config/mirror_inventory.py:222-253` knows four
providers while the CLI enum and `SURFACE_REGISTRY` carry six
(`src/ai_engineering/cli_commands/core.py:112-113`). `.opencode` and `.cursor` have no
`_PROVIDER_FILE_MAPS` / `_PROVIDER_TREE_MAPS` entry, so `ai-eng dev sync` reports clean
while the root surface rots. This is the same class of bug as the known orphan
(`scripts/sync_mirrors/core.py:90-92` defines only `TPL_OPENCODE_*`; there is no
`ROOT/".opencode"` constant, in contrast to `core.py:59-70`).

Consequences, all citable: 52 root skills still carry the retired `model_tier:`
(`.opencode/skills/ai-build/SKILL.md:6`); the root surface has 52 of 54 skills, zero
handler files, zero `agents/internal/`, and zero inline-fallback paragraphs; and its
`/ai-review` preflight cites the wrong surface entirely
(`.opencode/skills/ai-review/SKILL.md:31,39` point at `.codex/agents/internal/`), so
`/ai-review` hard-STOPs for a missing-file reason before the inline fallback is ever
consulted.

The guard plane is ported by mapping the 22-hook plugin API — which exposes a
*blocking* `tool.execute.before` and `permission.ask`
(`.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts:173-321`) — onto the
canonical events, replacing the `dispatch()` that returns `0`.

**A security decision the spec must state explicitly, not assume.** Claude Code hook
bytes are sha-pinned and integrity-enforced
(`.ai-engineering/scripts/hooks/_lib/integrity.py`, exit 3 on mismatch). OpenCode
plugins and pi.dev extensions load unsigned. The spec must declare whether the
non-Claude guarantee is *equivalent* or *best-effort*, and it cannot be equivalent
without an integrity story for the plugin itself. See OD-4.

### 4.5 Capability table

`FamilyToolProfile` (`scripts/sync_mirrors/tool_name_map.py:87-95`) carries four fields
and explicitly excluded runtime quirks
(`.ai-engineering/specs/archive/spec-189-open-model-portability/spec.md:100-102`). The
measurements produced exactly the quirks it has nowhere to record, so it is replaced by
a frozen dataclass resolved exact-id then regex-pattern then default:

| Field | Why it exists | Evidence |
|---|---|---|
| `supports_tool_choice` | E4 refutes the documented DeepSeek rejection **for this deployment** — the row must be per-deployment, never inherited from vendor docs | E4 |
| `schema_enforced_server_side` | mimo-v2.5 returns 200 for `strict:true` and violates the schema. A boolean `supports_json_schema` cannot express "accepts the flag but does not honour it" | E5 |
| `min_completion_budget` | With `max_tokens=16` and thinking on, reasoning consumed the whole budget and content came back **empty** with `finish_reason: "length"` — empty, not truncated | E9 |
| `requires_reasoning_split` | Reasoning leaks into `message.reasoning_content` and `provider_specific_fields.reasoning` on deepseek and mimo, not on qwen3.6 or gemma4 | E8 |
| `verified` | Retained. E1 closes the MiMo open question: it resolves and tool-calls | E1 |

The existing table is provably stale in both directions —
`tool_name_map.py:144-166` records quirks that did not reproduce, and lacks every quirk
that did.

### 4.6 Spend caps

The schema slot exists end to end: `cost_usd` is shaped into the genai block
(`src/ai_engineering/state/observability.py:283-285`, byte-mirrored at
`.ai-engineering/scripts/hooks/_lib/observability.py:291-293`), summed by
`src/ai_engineering/state/audit_rollup.py:75` and printed by
`src/ai_engineering/cli_commands/audit_cmd.py:340`. Nothing populates it.

E7 supplies the producer for free: every response carries `usage.cost` (measured
`3.822e-05`) plus `cost_details.upstream_inference_prompt_cost` and
`_completions_cost`. Two adjacent defects ship with the fix — the emitter hardcodes
`genai_system="anthropic"` regardless of driver
(`.ai-engineering/scripts/hooks/_lib/transcript_usage.py:194,205-215`), and
`session_token_rollup` events carry no top-level `sessionId`, so `audit_rollup` skips
them entirely (`src/ai_engineering/state/audit_rollup.py:119-140` against the emitter
at `.ai-engineering/scripts/hooks/runtime-stop.py:686-694`).

Enforcement follows the existing `AIENG_MAX_*` clamp idiom
(`src/ai_engineering/config/concurrency.py:169-238`). Note those resolvers currently
have **zero production callers** on the dispatch path — the sole caller is the
`ai-eng host probe` diagnostic (`src/ai_engineering/cli_commands/host_cmd.py:55-56`) —
so the caps are honoured only by a model reading handler prose. A spend cap must not
repeat that mistake.

### 4.7 Graph-layer blueprint (M3, informative)

Recorded so M0-M2 build compatible seams. Sourced from `$HOME/repos/TradingAgents`,
introspected against langgraph 1.2.9.

- **State** — one flat `TypedDict` over `MessagesState`. Critical trap: every
  `Annotated[...]` in that repo holds *prose*, not a callable
  (`TradingAgents/tradingagents/agents/utils/agent_states.py:56-76`), so no key has a
  real reducer. Reducer-less keys cannot be written by two concurrent branches
  (`InvalidUpdateError`), which is a blocker for any wave fan-out. Every counter
  crossing a fan-out becomes `Annotated[int, operator.add]`.
- **Frozen spec rows** — the best pattern in that repo:
  `AnalystNodeSpec(key, agent_node, clear_node, tool_node, report_key)` drives node
  names, tool lookup, router binding and chaining from one table
  (`TradingAgents/tradingagents/graph/analyst_execution.py:6-53`). That is how 54
  skills compose without hand-wiring 54 edges. Put the effort tier on the spec row so a
  retry can re-dispatch the same node at a higher tier.
- **One exported `path_map` constant per router**, containing the router's complete
  return set, plus the property test asserting `returns <= set(PATH_MAP)` across drift
  labels (`TradingAgents/tests/test_risk_router_path_map.py:26-60`). Copy the constant
  and the test. Never route on `str.startswith()` over model-adjacent prose.
- **Per-cycle counters are missing upstream and are a blocker.** `should_continue_*`
  returns the tool node forever; the only bound is a global `recursion_limit=100`, so a
  model that keeps emitting tool calls burns the entire superstep budget inside one
  node and dies after every prior node's cost is sunk. Each cycle needs its own
  counter, ceiling, and a **degraded exit** that emits a partial report rather than
  crashing. ai-engineering's bounds map straight on: `AIENG_RALPH_MAX_RETRIES` to the
  per-cycle counter, `fix_attempts >= 3` to the gate loop, Hard Rule 5's single
  remediation pass to `REMEDIATION_MAX = 1`.
- **Context reset as a deterministic node** — pure Python emitting `RemoveMessage` plus
  one context-anchored placeholder, zero model calls
  (`TradingAgents/tradingagents/agents/utils/agent_utils.py:190-214`). Copy it; note
  the recorded portability bug at `:193-199` where a bare "Continue" placeholder made
  some OpenAI-compatible providers analyse the word "continue".
- **Checkpointing** — copy the run-signature idea (a deterministic thread id folding in
  graph-shape inputs so a resume under a changed graph starts fresh,
  `TradingAgents/tradingagents/graph/checkpointer.py:28-38`). The ai-engineering analog
  is `(spec id, plan revision sha, skill set, effort tier)`. Pin `langgraph>=1.0`; do
  not inherit that repo's two-majors-behind floor
  (`TradingAgents/pyproject.toml:12,18,19`).
- **HITL is exactly one primitive wide.** No `interrupt`, `interrupt_before` or
  `Command` appears anywhere in TradingAgents, but all of them exist in 1.2.9 and the
  checkpointer prerequisite is already there.
- **The load-bearing lesson is a dead feature, not a pattern.** Checkpointing and the
  entire memory loop run only inside `propagate()`, which the CLI never calls
  (`TradingAgents/tradingagents/graph/trading_graph.py:149-151` against `:377-383`),
  so `--checkpoint` is a no-op on the primary UX. **Lifecycle side-effects must live in
  the graph, never in a wrapper one entry point bypasses.**
- **Do not import the same-model-for-every-judge flaw.** All five debaters share one
  LLM instance and independence is prompt persona only
  (`TradingAgents/tradingagents/graph/setup.py:83-92`). ai-engineering already has this
  flaw — 15 of 19 agents declare `model: opus`, generator and every judge alike. Do not
  ship a second copy.

### 4.8 Governance-plane interface (M4, informative)

Paperclip claims below are source-verified against commit `aed4478c81925891a6d87ac0da5b0e1aba7c183d`
unless marked. Blog-sourced claims are marked and are **not** load-bearing —
notably, `createCostEvent` is **not** an MCP tool (cost reporting is REST-only), and
`getIssueContext` does not exist (the real name is `paperclipGetHeartbeatContext`);
both wrong names originate in a blog post.

| Capability | ai-engineering today | Gap |
|---|---|---|
| Task checkout / locking | Only the single live spec slot: `slot_status` at `.ai-engineering/scripts/spec_lifecycle.py:723,2060`; file-boundary conflict handling is prose | No checkout verb, no run-id ownership, no 409-vs-422 distinction |
| Context injection | Env-driven config is idiomatic (`AIENG_*`, `CLAUDE.md:200-260`) | No reader for any `PAPERCLIP_*` var. Cheap: one resolver module. **E12 makes consuming the workspace-cwd var mandatory, not optional** — a small model will otherwise fabricate one |
| Status transitions | Real lifecycle validator with illegal-move surfacing (`spec_lifecycle.py:79,527,577,611`); `/ai-board sync` already maps onto GitHub Projects v2 / ADO | A mapping table, not new machinery. `blocked` maps cleanly onto the existing BLOCKED state |
| Cost reporting | Schema slot complete end to end (§4.6) | Producer only — and E7 supplies it |
| Approval suspend + resume | BLOCKED state, structured envelope, exit 78 — explicitly designed for a machine consumer (`.claude/skills/ai-build/handlers/no-hitl.md:144-163`) | No HTTP sink; `--no-hitl` covers only `/ai-build`, zero occurrences in `ai-autopilot`, `ai-plan`, `ai-brainstorm` |
| Audit read access | Exit-code discipline exact (78/80/81, `_exit_codes.py:23,26,52`); `audit verify\|tokens\|replay` exist | NDJSON is gitignored and machine-local (`.gitignore:164`); the engine enum refuses `paperclip`, so a Paperclip-driven run emits nothing |

Two collision hazards, both source-verified: Paperclip ships its own skills and syncs
them into the harness skill directory that ai-engineering also owns (overwrite-vs-merge
is unverified); and its scheduler coalesces bursts into one run, so any wake handler
must read the full new-comment batch and be idempotent across restarts.

---

## 5. Evidence Catalog

### 5.1 Measured — probes against `https://api.nan.builders`, 2026-07-27

| id | Finding |
|---|---|
| E1 | `GET /v1/models` returns exactly: `deepseek-v4-flash`, `flux-2-klein`, `gemma4`, `kokoro`, `mimo-v2.5`, `qwen3-embedding`, `rerank`, `qwen3.6`, `whisper` |
| E2 | `POST /v1/messages` -> **404**; `POST /anthropic/v1/messages` -> **404**. Only `/v1/chat/completions` works |
| E3 | Response ids are `gen-`-prefixed and carry `provider_specific_fields` + `is_byok` — an OpenRouter-shaped aggregator, not raw LiteLLM |
| E4 | All four chat models: HTTP 200 on single tool call, **parallel tool calls (n=2 in one turn)**, forced `tool_choice {"type":"function"}`, and `response_format json_schema strict:true` |
| E5 | mimo-v2.5 returns 200 for `strict:true` with **schema-violating content** (asked `{name,age}`, returned `{"type":"metadata","data_features":[...]}`); deepseek-v4-flash, qwen3.6, gemma4 all schema-valid |
| E6 | Prompt caching live: `prompt_tokens_details.cached_tokens: 192` on mimo-v2.5; `cache_write_tokens` on deepseek |
| E7 | Per-request cost returned: `usage.cost` (e.g. `3.822e-05`) plus `cost_details.upstream_inference_prompt_cost` / `_completions_cost` |
| E8 | Reasoning tokens billed and reported separately (deepseek 20, mimo 22); reasoning text leaks into `message.reasoning_content` and `provider_specific_fields.reasoning` on deepseek and mimo only |
| E9 | With `max_tokens=16` and thinking on, reasoning consumed the entire budget: `message.content` **empty**, `finish_reason: "length"` |
| E10 | Real always-on context assembled (`CLAUDE.md` + 54 skill descriptions = 40,419 chars; measured `prompt_tokens` 9,947-10,482). 8 routing questions with known-correct answers: deepseek-v4-flash **8/8**, mimo-v2.5 **8/8**, gemma4 **8/8**; qwen3.6 dropped one connection at `max_tokens=4000`, then 3/3 on retry |
| E11 | Given the real `.claude/skills/ai-commit/SKILL.md` body plus a bash tool, all four models made a correct first tool call (a branch/status check = the skill's step 1) |
| E12 | qwen3.6 fabricated a working directory in an emitted command (`cd /home/user/ai-engineering && ...`) |
| E13 | Local transcripts: 22 sessions driven by open models, 10 in this repository (`xiaomi/mimo-v2.5` 2,681 msgs / 12 sessions; `tencent/hy3` 1,258 / 5; `moonshotai/kimi-k3` 26 / 1; `cohere/north-mini-code:free` 3 / 1). Zero recorded tool errors |

### 5.2 Repository citations

| Claim | Citation |
|---|---|
| Engine enum is a closed 5-value set, byte-duplicated | `tools/skill_domain/event_schema.py:33-34`; `.ai-engineering/scripts/hooks/_lib/hook-common.py:50-53` |
| **`/ai-spec-draft` emits a `kind` the schema refuses**, so its audit step has always silently failed | `.claude/skills/ai-spec-draft/SKILL.md` step 6 (`kind=brief_drafted`) against `ALLOWED_EVENT_KINDS` in `tools/skill_domain/event_schema.py`; reproduced 2026-07-27 |
| Engine defaults disagree between the two twins | `.ai-engineering/scripts/hooks/_lib/hook-common.py:386,471,510,633` vs `_lib/hook_context.py:147` |
| 11 canonical hook events, count CI-locked | `.claude/settings.json:46,68,110,162,174,196,208,220,242,254,266`; `tests/unit/hooks/test_canonical_events_count.py:24-40` |
| Codex wires 4 of 11; `SessionStart` declared empty | `.codex/hooks.json:3,25,47,64,65` |
| `no-verify-guard` absent from Codex PreToolUse | `.claude/settings.json:68` vs `.codex/hooks.json:25` |
| `injection-read-guard` absent from Codex PostToolUse | `.claude/settings.json:110` vs `.codex/hooks.json:47` |
| OpenCode bridge `dispatch()` returns 0 unconditionally | `.ai-engineering/scripts/hooks/opencode-hook-bridge.ts:84-90` |
| OpenCode bridge maps the passive event, not the blocking one | `opencode-hook-bridge.ts:28-51` vs `.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts:225-227` |
| OpenCode tests assert string presence, not behaviour | `tests/integration/hooks/test_opencode_bridge.py:8-36` |
| Cursor bridge dispatches to a filename that does not exist, yet is sha-pinned | `.ai-engineering/scripts/hooks/cursor-hook-bridge.py:64-68`; `.ai-engineering/state/hooks-manifest.json:61` |
| `audit verify` always exits 0 by design; doctor check hardcoded WARN | `src/ai_engineering/cli_commands/audit_cmd.py:95-98`; `src/ai_engineering/doctor/phases/state.py:170-202` |
| No repo-root `.opencode` sync target | `scripts/sync_mirrors/core.py:90-92` against `core.py:59-70` |
| Mirror validator knows 4 providers, registry carries 6 | `src/ai_engineering/config/mirror_inventory.py:222-253`; `src/ai_engineering/cli_commands/core.py:112-113` |
| Root `.opencode` still ships retired `model_tier` | `.opencode/skills/ai-build/SKILL.md:6` |
| Root `.opencode` `/ai-review` preflight cites the wrong surface | `.opencode/skills/ai-review/SKILL.md:31,39` |
| Inline fallbacks exist in 4 skills | `.claude/skills/ai-review/SKILL.md:74`; `ai-verify/SKILL.md:99`; `ai-advise/SKILL.md:83`; `ai-simplify/SKILL.md:91` |
| ...and are contradicted in 3 of the same 4 files | `ai-review/SKILL.md:56`; `ai-verify/SKILL.md:81`; `ai-advise/SKILL.md:69` |
| Adversarial validator requires isolation | `.claude/agents/review-validator.md:56` |
| Corroboration defined as two independent agents | `.claude/skills/ai-autopilot/handlers/phase-quality.md:152-154`; `.claude/skills/ai-build/handlers/quality.md:92-94` |
| Maker/checker enforced at tool-declaration level | `.claude/agents/ai-build.md:3` |
| Per-task isolation stated as a hard invariant | `.claude/skills/_shared/execution-kernel.md:13` |
| Serial DAG is an expected shape, not a failure | `.claude/skills/ai-autopilot/handlers/phase-orchestrate.md:178` |
| Only 2 of 19 agents declare the `Agent` tool | `.claude/agents/ai-review.md:6`; `ai-verify.md:6` |
| `ai-eng skill` exposes only `status` | `src/ai_engineering/cli_factory.py:502-508`; `src/ai_engineering/cli_commands/skills.py:3,31-34` |
| Synthetic terminal invocation prohibited | `CLAUDE.md:83` |
| Lint walks only `SKILL.md` + agent files; 58 handlers unscanned | `tools/skill_lint/checks/portability.py:211-222`; `tools/skill_lint/cli.py:251-259` |
| Portability lint is blind to 5 of 7 canonical tool names and strips code spans | `tools/skill_lint/checks/portability.py:10-20,63-75` |
| `skill_lint` is `required=False` in the pre-commit bundle | `src/ai_engineering/policy/checks/stack_runner.py:158-164` |
| `_EFFORT_TO_MODEL` has no extension point; validator hard-fails on a non-Anthropic alias | `scripts/sync_mirrors/core.py:369-375,378-395,1617-1627` |
| 10 of 19 agents sit outside `AGENT_METADATA` | `scripts/sync_mirrors/core.py:173,405-408` |
| Scaffold path re-mints the coupling (`model: opus\|sonnet`, no `effort:`) | `.claude/skills/ai-scaffold/handlers/create-agent.md:14,25` |
| `FamilyToolProfile` carries 4 fields; quirks explicitly excluded | `scripts/sync_mirrors/tool_name_map.py:87-95`; `spec-189/spec.md:100-102` |
| Documented quirks that did not reproduce | `scripts/sync_mirrors/tool_name_map.py:144-166` |
| `cost_usd` slot exists end to end, unpopulated | `src/ai_engineering/state/observability.py:283-285`; `src/ai_engineering/state/audit_rollup.py:75`; `src/ai_engineering/cli_commands/audit_cmd.py:340` |
| Cost emitter hardcodes `genai_system="anthropic"` | `.ai-engineering/scripts/hooks/_lib/transcript_usage.py:194,205-215` |
| `session_token_rollup` carries no `sessionId`, so the rollup skips it | `src/ai_engineering/state/audit_rollup.py:119-140` vs `.ai-engineering/scripts/hooks/runtime-stop.py:686-694` |
| Concurrency resolvers have no production caller on the dispatch path | `src/ai_engineering/config/concurrency.py:169-238`; `src/ai_engineering/cli_commands/host_cmd.py:55-56` |
| Worktree isolation claimed but not mechanized | `.claude/skills/ai-build/SKILL.md:3` against `.claude/skills/_shared/execution-kernel.md` |
| BLOCKED third state, structured envelope, exit 78 | `.claude/skills/ai-build/handlers/no-hitl.md:90-142,144-163`; `src/ai_engineering/cli_commands/_exit_codes.py:52` |
| Bounded retries, three independent bounds | `.ai-engineering/scripts/hooks/runtime-stop.py:74-76`; `.claude/skills/ai-pr/handlers/watch.md:36,86-89` |
| Convergence checker built but reinjection default off | `.ai-engineering/scripts/hooks/_lib/convergence.py:123-206`; `runtime-stop.py:88` |
| Git plane fully harness-independent | `.git/hooks/pre-commit:1-6`; `pre-push:6`; `src/ai_engineering/policy/checks/stack_runner.py:150-151,238-251` |
| `run-hook.sh` fails OPEN when no >=3.11 interpreter resolves | `.ai-engineering/scripts/hooks/_lib/run-hook.sh:22-60` |
| `locked_append` falls open on lock exhaustion | `.ai-engineering/scripts/hooks/_lib/locked_append.py:1-27` |
| `solution-intent.md` still keys the roster by opus/sonnet | `.ai-engineering/solution-intent.md:119-129` |
| `§6 Subagent Strategy` is unconditional | `.ai-engineering/reference/principles.md:221-226` |
| Anthropic-shaped caps and reserved words encoded as blocking | `tools/skill_lint/checks/token_budget.py:1-15,27-30`; `tools/skill_domain/rubric.py:652` |
| `tiktoken` absent, counter falls back to `len/4` | `tools/token_baseline/count.py:16-19,90-91` |
| Hot-path budget: under 1s pre-commit, under 5s pre-push | `CLAUDE.md:166-173` |
| Hard Rule 5 — one remediation pass then STOP | `CLAUDE.md:129-134` |
| Auto-merge enabled downstream of the fail-loud gate | `.claude/skills/ai-pr/SKILL.md:112,116` |
| Single live spec slot; `mark_shipped` clears it | `.ai-engineering/scripts/spec_lifecycle.py:452,723,2060` |
| NDJSON is gitignored, so CI cannot read it | `.gitignore:164` |

### 5.3 Corpus measurements

| Metric | Value | Source |
|---|---|---|
| Canonical corpus | 120,855 tokens / 95 files | `tools/token_baseline/count.py:8-14,55-76` |
| Skills / reference / agents / rulebooks | 64,229 / 25,168 / 22,309 / 9,149 | same |
| Always-on subtotal | 10,288 tokens (`CLAUDE.md` 3,738 + 54 skill descriptions 5,659 + 19 agent descriptions 891) | same |
| Turn-1 floor incl. §0 mandated reads | ~21,021 tokens | `CLAUDE.md:5-19,44-48` |
| Deferred (handlers + references + evals) | 94,474 tokens / 79 files = **59.5% of the skill tree** | `tools/skill_lint/checks/structure.py:6-10` |
| Description cap utilisation | mean 467 chars against a 1,024 cap (46%) | `tools/skill_lint/checks/token_budget.py:27` |
| Ordered procedural scaffolding in skill bodies | 24,000 of 64,229 tokens (37%) | `tools/skill_lint/checks/structure.py:11-17,42` |

---

## 6. Roadmap

**Precedence claim: M0 is a precondition for everything. M1 is a precondition for M3
and M4.** M2 is independent of M3/M4 and can run in parallel with M1.

### M0 — Truth and entry (precondition; smallest slice that proves value)

Landing M0 alone makes the 22 open-model sessions already happening visible, costed and
attributable. That is the minimum deliverable with standalone value.

- Add the `openai_compatible` engine to both enum twins; reconcile the disagreeing
  defaults.
- Add `brief_drafted` to `ALLOWED_EVENT_KINDS` — the cheapest end-to-end proof the enum
  change works, and it fixes a first-party skill whose audit step has never succeeded.
- Make a refused emit visible. Today it returns a boolean nobody checks, which is why
  the defect above survived undetected.
- Populate `cost_usd` from `usage.cost`; stop hardcoding `genai_system="anthropic"`;
  fix the missing `sessionId` on `session_token_rollup`.
- Add `tiktoken` to the project dependency set so the token counter stops silently
  running `len/4`.
- Add the read-only skill resolver verb.
- Add the `CLAUDE.md:83` carve-out for headless IDE-surface invocation.

**Gate:** a session driven by an OpenAI-compatible host emits framework events that
`ai-eng audit tokens --json` attributes to the correct engine, with a non-zero
`cost_usd`. Red test asserts a non-Claude engine value is accepted and a `langgraph`
value is still refused.

### M1 — OpenCode as the reference open-model harness

- Register `.opencode` (and `.cursor`) in `_PROVIDER_FILE_MAPS` / `_PROVIDER_TREE_MAPS`
  so `dev sync --check` stops reporting clean over a rotting surface — **the root-cause
  fix; do not hand-copy the orphan.**
- Add the repo-root `.opencode` sync target; regenerate; ship `agents/internal/`.
- Port the guard plane onto the plugin API's blocking `tool.execute.before` /
  `permission.ask`, replacing the `dispatch()` that returns 0.
- Decide and implement the plugin integrity story (OD-4).

**Gate:** on OpenCode, a staged secret is blocked, a `--no-verify` commit is blocked,
and an injected `tool_response` is scanned — each proven by a behavioural test, not a
string-presence assertion. `dev sync --check` fails on a deliberately stale root
`.opencode` file.

### M2 — Loop hardening

- Spend-cap enforcement following the `AIENG_MAX_*` clamp idiom, with a real caller on
  the dispatch path.
- Real `git worktree` isolation, **or** delete the two prose claims that assert a
  mechanism the workflow never performs. Shipping neither is not an option (OD-5).
- Inline fallback for the five skills that lack one, plus a test asserting every
  fallback paragraph exists; resolve the three self-contradictions.
- Move the judge agents off the generator's model — the cheapest high-leverage fix and
  simultaneously the portability proof.
- Widen `skill_lint` to the 58 handler files; un-blind it to `Agent`/`Task` literals;
  promote it to `required=True`.
- Capability table replacing `FamilyToolProfile`, populated from measurement.
- Per-model defences from §11: minimum `max_tokens` floor, client-side schema
  validation, `reasoning_content` stripping, explicit cwd injection.

**Gate:** a cross-model replay corpus (archived spec-187/189/200 plans) runs green on
Opus for the reference number, then on deepseek-v4-flash and gemma4, with pass defined
as `ai-eng check` green plus no blocker/critical from `/ai-review`. CI job costed and
declared required-or-advisory (OD-6).

### M3 — Graph layer (separate package)

StateGraph over the M0 seam, per-cycle counters with degraded exits, deterministic
non-LLM nodes for DAG build and gate verdict, checkpointing with a run signature, and
`interrupt()`/`Command(resume=...)` for both approval gates.

**Gate:** a two-node graph runs `/ai-plan` then `/ai-build` headlessly against an
approved spec, survives a kill-and-resume, and emits attributable events throughout.

### M4 — Governance plane adapter (separate package)

`PAPERCLIP_*` env resolver, status mapping, cost-event POST, BLOCKED-to-interaction
mapping with reconcile-on-wake.

**Gate:** an issue checked out from Paperclip drives a full chain run and reports cost,
status and a value-block comment back, with the approval path exercised.

---

## 7. Definition of Done

1. An OpenAI-compatible host emits framework events attributed to the correct engine,
   with populated `cost_usd`, verified by `ai-eng audit tokens --json`.
2. On OpenCode: staged-secret block, `--no-verify` block, and `tool_response` injection
   scan all proven by behavioural tests.
3. `ai-eng dev sync --check` fails on a stale repo-root `.opencode` file.
4. Zero `model_tier` occurrences under `.opencode/`.
5. Every dispatch-only skill has an inline fallback, asserted by a test; zero
   self-contradictions between a fallback paragraph and a Boundary/Common-Mistake in
   the same file.
6. `skill_lint` scans all 135 files under `.claude/skills/`, evaluates `Agent` and
   `Task` literals, and is `required=True` in the pre-commit bundle.
7. A spend cap is enforced by code on the dispatch path, not by prose.
8. Worktree isolation is either mechanized or its claims are deleted.
9. Judge agents do not share the generator's model.
10. A cross-model replay gate is green on at least two nan.builders models with a
    recorded Opus reference number.
11. The capability table records `schema_enforced_server_side` and
    `min_completion_budget`, populated from measurement, with a test pinning the
    mimo-v2.5 row.
12. Every per-model defence in §11 has a test.
13. CHANGELOG documents each breaking change under §13.3 (hard rename, no shims).

---

## 8. Quality Stamps

| Principle | Application |
|---|---|
| §10.1 KISS | The execution seam is the harness's own command runner. No new skill-execution runtime, no prompt assembly, no model router |
| §10.2 YAGNI | Embedding and rerank models are recorded and **not** wired — E10 shows the problem they solve does not exist. The graph and governance layers ship separately, not speculatively vendored in |
| §10.3 SOLID | The capability table is open for extension (regex rows, per-deployment) and closed for modification; adding a model family touches data, not control flow |
| §10.5 TDD | Every gate in §6 is a red test first. The cross-model replay corpus is the acceptance test for the whole program |
| §10.6 SDD | This brief precedes the spec; the spec precedes the plan. Every architectural claim carries `file:line` |
| §10.8 Hexagonal | Model access stays an operator-owned adapter outside the hexagon (D-189-01). The graph layer is a driving adapter; the governance plane is a driving adapter above it. Neither reaches inside a skill |
| Hard Rule 3 | No backwards-compat shims. The `.opencode` orphan is regenerated or deleted; `FamilyToolProfile` is replaced, not wrapped |
| Hard Rule 7 | The capability table is a single canonical store; the mirror `model:` lines remain derived and rebuildable |
| No soft-deprecation | Consistent with the operator directive: hard-remove or keep clean and silent. TradingAgents' per-call `DeprecationWarning` shim is explicitly listed as an anti-pattern not to copy |

---

## 9. Open Decisions

| id | Decision | Why it must be answered first |
|---|---|---|
| **OD-1** | **Does D-189-01 ("no runtime that detects, routes, selects, ranks or calls a model") still hold?** | The single gating decision. The capability table is build-time data and does not cross it; a per-node effort router in M3 does. Nothing in M3 can be planned until this is answered |
| **OD-2** | Root `.opencode/`: regenerate, or **delete**? OpenCode natively discovers `.claude/skills`, which makes the entire `.opencode/skills/` tree redundant — only `commands/` is OpenCode-specific | Delete-and-shrink may beat fix-the-generator. Changes M1's size by roughly 54 files x 2 trees |
| **OD-3** | Which harness is the reference: OpenCode (best headless seam, worst current state) or pi.dev (already the operator's daily driver, zero hook substrate)? | Determines where M1's effort lands. This brief proposes OpenCode on evidence; the operator's actual usage argues for pi |
| **OD-4** | Is the non-Claude security guarantee **equivalent** or **best-effort**? Claude hooks are sha-pinned; OpenCode plugins and pi extensions load unsigned | A security posture cannot be left implicit. Equivalent requires a plugin integrity story; best-effort requires saying so in the docs |
| **OD-5** | Worktree isolation: implement, or delete the claim? | Both defensible; shipping neither is not |
| **OD-6** | Is the cross-model CI gate **required** or **advisory**, and what is one matrix run's cost against the provider quota? | A Definition of Done with no red gate is the exact failure this brief flags for spec-187 |
| **OD-7** | Repo boundary: does the graph layer live here, in a sibling repo (precedent: spec-178), or as an optional extra? | LangGraph is a heavy dependency in a wheel of stdlib-only hooks; consumer installs have been bricked by less (spec-179) |
| **OD-8** | Which chain approval gates are human-only, which are delegable, and which are attestable by a machine principal? | `/ai-brainstorm` and `/ai-plan` both mandate a human, and `--no-hitl` exists only on `/ai-build`. An issue arriving with no spec **cannot start unattended today** |
| **OD-9** | Data governance for provider egress: retention, training-on-prompts, tenancy, jurisdiction, and the model licences (Gemma use policy vs Qwen Apache-2.0 vs DeepSeek MIT) | Running the chain there ships source, diffs and specs to a third party, under a CONSTITUTION with compliance gates |
| **OD-10** | Audit chain under concurrency: shard per writer, or serialize? Both chains are **already broken on main today** (events index 28333, decisions index 1) at N=1 concurrency, and every surface still reports exit 0 | Determines whether the chain can be a control-plane primitive at all |
| **OD-11** | Spec-slot addressing: keep N=1, or resolve `.ai-engineering/specs/<slot>/`? | A control plane running two workstreams destroys one. Smallest fix is one path-resolver function plus the same resolver in skill path references |
| **OD-12** | Which agency-agents roles to adopt (§12), and do they become agents (tripping ~5 hardcoded count gates) or sections in existing agents? | Sizing question for M2 |

---

## 10. Migration

Hard rename, hard delete, hard migration per CONSTITUTION §3. No shims.

| Change | Type | Breakage |
|---|---|---|
| `FamilyToolProfile` (4 fields) replaced by the capability dataclass | hard replace | Any consumer of the old shape. Consumers today: `scripts/sync_mirrors/core.py:164,169,997` only |
| Root `.opencode/` regenerated or deleted (OD-2) | hard migration | 52 files carrying retired `model_tier` disappear. If deleted, `opencode` leaves `manifest.surfaces.enabled` |
| `engine` enum gains `openai_compatible` | additive | None. Existing events keep validating |
| `skill_lint` promoted to `required=True` and widened to handlers | hard gate change | 64 BLUF + 4 portability failures currently invisible become blocking. Must land **after** the handler corpus is fixed, not with it |
| `.claude/skills/ai-build/SKILL.md:3` worktree claim | hard delete or hard implement (OD-5) | A user-facing description changes meaning |
| `.ai-engineering/scripts/hooks/cursor-hook-bridge.py` | hard delete | Structurally dead; removing it also removes a misleading sha-pin entry |
| `.ai-engineering/solution-intent.md:119-129` roster keyed by opus/sonnet | hard rewrite to `effort` | A §0 mandated read stops contradicting every SKILL.md |
| `.claude/skills/ai-scaffold/handlers/create-agent.md:14,25` | hard rewrite to ask `effort` | New agents stop re-minting the coupling |
| CHANGELOG | required | Each of the above under a `### Breaking changes` block, following the existing keyword-continuity convention |

---

## 11. Risks

| id | Risk | L | I | Mitigation |
|---|---|---|---|---|
| RK-1 | **mimo-v2.5 returns HTTP 200 on a schema contract it does not honour** (E5) | High | High | Never trust the 200. Validate client-side; re-ask once with the violation echoed; fail over to qwen3.6 or gemma4. Do not route mimo to any typed interface |
| RK-2 | **Empty content, not truncated content**, when `max_tokens` is small against a thinking model (E9) | High | High | Hard minimum-`max_tokens` floor at the client edge. Treat `finish_reason == "length"` **with empty content** as a distinct retryable class, never a parse failure |
| RK-3 | **Fabricated working directory** in emitted commands (E12) | Medium | High | Inject cwd explicitly into the tool contract; reject model-emitted absolute paths off an allowlist. Treat as a small-model class failure, not a qwen-only one |
| RK-4 | **Reasoning text leaks into the message and is billed** (E8) | High | Medium | Strip `reasoning_content` and `provider_specific_fields.reasoning` before parsing and before replaying history. Account reasoning tokens in any budget model |
| RK-5 | **Guard plane ported to an unsigned plugin** — a weaker model is more susceptible to injected instructions in the very repo content the guard reads | Medium | High | OD-4 must be decided explicitly. If best-effort, say so in the docs; do not let "equivalent" be inferred |
| RK-6 | Widening `skill_lint` reds 68 currently-invisible findings and blocks every PR | High | Medium | Fix the corpus first, promote to `required=True` second. Sequence is load-bearing (§10) |
| RK-7 | **Audit chain breaks worsen under concurrency.** `locked_append` falls open on lock exhaustion, verification cannot gate, and both chains are already broken at N=1 | Medium | High | OD-10. Sharding removes the shared-tail race rather than making it rarer, and is the change that makes promoting `audit verify` to blocking worth doing |
| RK-8 | **Single spec slot destroyed by concurrent workstreams** | Medium | High | OD-11. Resolver-based slot addressing defaults to today's exact paths, so single-operator behaviour is unchanged |
| RK-9 | Provider intermittency — one connection drop observed at `max_tokens=4000` (E10) | Medium | Low | Retry with exponential backoff, distinct from the 429 path. Cap fan-out at 3 concurrent |
| RK-10 | Scope inflation: this brief spans four layers | High | High | The precedence claim in §6 is the control. M0 alone has standalone value. M3/M4 ship separately (OD-7) |
| RK-11 | Provider egress of source, diffs and specs to a third party | Medium | High | OD-9 before any CI matrix run |
| RK-12 | LangGraph dependency bricks consumer installs (spec-179 precedent) | Medium | High | OD-7. Separate package is the default answer |

---

## 12. References

**External**

- `https://nan.builders/docs/models`, `https://nan.builders/docs/api` — provider datasheet and limits
- `https://opencode.ai/docs/skills/`, `/docs/agents/`, `/docs/permissions/`, `/docs/server/`, `/docs/sdk/` — harness capability source
- `https://reference.langchain.com/python/langgraph/graph/state/StateGraph/add_conditional_edges`, `https://docs.langchain.com/oss/python/langgraph/persistence` — API names verified against langgraph 1.2.9
- `https://docs.langchain.com/oss/python/langgraph/errors/INVALID_CONCURRENT_GRAPH_UPDATE` — the reducer-less concurrent-write blocker
- `https://github.com/paperclipai/paperclip` at `aed4478c81925891a6d87ac0da5b0e1aba7c183d` — control-plane schema, adapter contract and MCP tool list, all source-verified
- Anthropic, *"The new rules of context engineering for Claude 5 generation models"*, 2026-07-24 — the frontier-model doctrine this brief deliberately does not apply fleet-wide (§13, Tier calibration)
- *"Loop Engineering: The Anthropic Playbook"* (HuaShu, self-published, 11pp, not peer-reviewed) — treated as design claims to test, not findings
- `https://qwen.ai/blog?id=qwen3.6-35b-a3b`, `https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash`, `https://ai.google.dev/gemma/docs/core/model_card_4` — model cards
- `https://qwen.readthedocs.io/en/latest/getting_started/quickstart.html` — the greedy-decoding repetition warning behind RK-9's "never send `temperature=0`"

**Local reference implementations**

- `$HOME/repos/TradingAgents` — LangGraph patterns; state shape, frozen spec rows, path-map routers, capability table, and eleven documented anti-patterns
- `$HOME/repos/agency-agents` — agent taxonomy; see §12.1

**Prior art in this repository**

- `.ai-engineering/specs/archive/spec-187-fleet-simplify-portability/`
- `.ai-engineering/specs/archive/spec-189-open-model-portability/`
- `.ai-engineering/specs/drafts/open-model-portability-brief.md` — predecessor brief
- `.ai-engineering/specs/archive/spec-181-ai-pr-small-model-robustness/`

### 12.1 Agent-roster deltas worth adopting (OD-12)

From `$HOME/repos/agency-agents`, 269 agents across 17 divisions. Roughly 8 of the 9
user-facing ai-engineering agents already have a weaker analogue there, so there is no
net gain from importing the roster. Six patterns are worth stealing:

| Pattern | Value | Source |
|---|---|---|
| **Agent-role contract template** — `RECEIVES FROM` / `RESPONSIBILITY` / **`NOT RESPONSIBLE FOR`** / `PRODUCES` / `SUCCESS CRITERIA` / `FAILURE BEHAVIOR` / `TOOLS PERMITTED` / **`CONTEXT WINDOW BUDGET`** | The frontmatter schema ai-engineering's 19 agents should have. The two bolded fields are the ones most likely to improve small-model behaviour | `agency-agents/engineering/engineering-multi-agent-systems-architect.md:392-421` |
| **Adversarial default posture as a rule** — "Default to NEEDS WORK unless proven otherwise", enumerated automatic-fail triggers, and pre-authorized mediocre ratings ("C+/B- are normal") | Inverting the default verdict is a cheap, model-size-independent countermeasure to sycophantic self-approval — a known failure of this repo's own verifier agents | `agency-agents/testing/testing-reality-checker.md:21-38,122-141` |
| **Cost controller with an aborting circuit breaker** and a 3-step token-budget ladder (compress, truncate least-critical **with logging**, halt and escalate; never silently truncate) | A ready-made spec for M2's spend cap | `agency-agents/engineering/engineering-multi-agent-systems-architect.md:524-557` |
| **HITL gate designer** — 6 placement criteria mapped to 3 gate types (blocking approval with a timeout contract, advisory flag with a rollback window, sampling gate) | ai-engineering's gates are binary block/warn with no advisory or sampling tier and no timeout contract | `agency-agents/engineering/engineering-multi-agent-systems-architect.md:321-366` |
| **`tools.json` as a declarative install contract**, where a shared `format` name is a **byte-identity guarantee** | Converts mirror drift from a review question into a testable invariant — and would have prevented the `.opencode` orphan class of bug outright | `agency-agents/tools.json:2,3-19` |
| **Roster-scale originality gate** — entity-neutralized 8-word shingle overlap, FAIL at 40% | Directly transplantable to the 54-skill fleet, where **description-space** collision is the routing hazard | `agency-agents/scripts/check-agent-originality.sh:3-27` |

Six disqualifying properties mean the roster itself must not be imported: median agent
~2.5k tokens of system prompt (45 files violate their own >1,500-token split rule);
252 of 269 declare no `tools:` and 38 embed executable bash the model is told to run;
**221 of 269 assert cross-session memory that has no substrate in that repo** — a small
model reads that as licence to fabricate prior observations; unsourced quantitative
claims presented as findings; emoji in 199 of 269 headings, conflicting outright with
this repo's no-emoji posture; and a documented OpenCode ceiling where agents past ~119
registered are **silently dropped**.

---

## 13. Glossary

| Term | Meaning |
|---|---|
| **Harness layer** | The environment around one model: tools, permissions, filesystem, memory, runtime. ai-engineering's skills, agents, hooks and gate plane |
| **Loop layer** | The repeated think-act-check-feedback cycle: verifiers, retry bounds, stop conditions, externalized state |
| **Graph layer** | Explicit workflow topology: nodes, branches, joins, parallelism, state transitions, controlled cycles |
| **Governance plane** | Org chart, budget, human approvals, cost ledger — above the graph |
| **Effort tier** | `cheap` / `mid` / `high`, the sole dispatch axis since spec-189 (D-189-04). Replaced `model_tier` |
| **Capability table** | Per-model-family record of measured runtime quirks, resolved exact-id then regex then default. Build-time data, not a dispatcher |
| **Dispatch-only skill** | A skill whose body is substantially a subagent dispatch, with little or no inline-executable procedure |
| **Inline fallback** | The documented path for executing a dispatch-only skill sequentially in one context when the host has no subagent primitive (D-189-07) |
| **BLOCKED** | The third terminal state, neither pass nor fail: needs a human. Exit 78 with a structured envelope |
| **Guard plane** | The 11 canonical hook events plus the git-hook gate — the deterministic, model-independent enforcement layer |
| **Always-on context** | Content in the system prompt every turn: `CLAUDE.md` plus every skill and agent `description` line. Measured at 10,288 tokens |
| **Turn-1 floor** | Always-on context plus the §0 mandated reads: ~21,021 tokens before the operator's first word |
| **Schema-enforced server-side** | Whether a provider actually validates `json_schema strict:true` output, as opposed to accepting the flag and ignoring it (E5) |
| **Empty-on-length** | Reasoning consumed the whole output budget: `finish_reason: "length"` with empty content. A distinct retry class, not truncation (E9) |

---

## 14. Acceptance

- [ ] OD-1 answered: D-189-01 upheld or explicitly amended, with the re-entry trigger named
- [ ] OD-2 answered: root `.opencode/` regenerated or deleted
- [ ] OD-3 answered: reference harness chosen with a stated rationale
- [ ] OD-4 answered: non-Claude security guarantee declared equivalent or best-effort, in writing, in the docs
- [ ] OD-5 through OD-12 answered or explicitly deferred with a named trigger
- [ ] `openai_compatible` engine accepted by both enum twins; conflicting defaults reconciled
- [ ] `brief_drafted` accepted by `ALLOWED_EVENT_KINDS`; a `/ai-spec-draft` run emits a verifiable audit event
- [ ] A refused emit surfaces loudly instead of returning an unchecked boolean
- [ ] `cost_usd` populated from `usage.cost`; `genai_system` reflects the real driver; `session_token_rollup` carries `sessionId`
- [ ] `tiktoken` present in the project dependency set; token baseline re-measured and the corrected figure recorded
- [ ] Read-only skill resolver verb shipped
- [ ] `CLAUDE.md:83` carve-out for headless IDE-surface invocation landed and mirrored
- [ ] `.opencode` and `.cursor` registered in the mirror provider maps; `dev sync --check` fails on a deliberately stale root file
- [ ] Repo-root `.opencode` regenerated (or deleted per OD-2); zero `model_tier` occurrences remain
- [ ] OpenCode guard plane: staged-secret block, `--no-verify` block, and `tool_response` injection scan each proven by a behavioural test
- [ ] `cursor-hook-bridge.py` deleted; its sha-pin entry removed
- [ ] Inline fallback present in all nine dispatch-only skills, asserted by a test
- [ ] Zero contradictions between a fallback paragraph and a Boundary or Common-Mistake in the same file
- [ ] `skill_lint` scans all 135 files under `.claude/skills/`, evaluates `Agent`/`Task` literals, and is `required=True`
- [ ] Capability table shipped with `schema_enforced_server_side` and `min_completion_budget`; a test pins the mimo-v2.5 row
- [ ] Spend cap enforced by code on the dispatch path, with a caller
- [ ] Worktree isolation mechanized, or its claims deleted
- [ ] Judge agents no longer share the generator's model
- [ ] Every defence in §11 (RK-1 through RK-4) has a test
- [ ] Cross-model replay gate green on at least two nan.builders models, with the Opus reference number recorded
- [ ] `solution-intent.md` roster re-keyed to `effort`
- [ ] `ai-scaffold/handlers/create-agent.md` asks `effort`, not `model`
- [ ] CHANGELOG documents every breaking change under a `### Breaking changes` block
- [ ] `ai-eng check` green; `spec_lint --check` green; full test suite green

---

**Handoff:** `.ai-engineering/specs/drafts/three-layer-open-model-harness-brief.md` -> `/ai-brainstorm`

Next free spec number: **201** (191 has a stale sidecar; 193-199 are burned with no on-disk anchors; 200 is the highest archived).
