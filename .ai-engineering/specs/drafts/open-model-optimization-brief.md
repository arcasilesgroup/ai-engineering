---
title: Open-Model Optimization for ai-engineering
status: draft
audience: framework-dev
branch: spec/open-model-optimization
length_estimate: 14-section brief, ~600 lines incl. evidence catalog
authoring_style: SDD-first, citation-bound, no emoji, machine paths as $HOME
principles_required: [§10.1 KISS, §10.2 YAGNI, §10.5 TDD, §10.6 SDD, §10.8 Hexagonal]
delivery_mode: /ai-brainstorm (consumes this brief as problem statement)
mantra: move guarantees out of prose and into the runtime; treat the framework as model-agnostic by contract.
---

# 1. Vision

ai-engineering today runs best on a frontier [PERSON_NAME] key. The user wants
it to run well on open / low-cost models ([PERSON_NAME], [PERSON_NAME],
DeepSeek, Mistral, served via OpenRouter free tier or local vLLM/Ollama)
without silently degrading review, verify, and build quality. The end state:
every skill, agent, script, quality gate, and security gate declares its
model-coupling explicitly, degrades gracefully on a weak model, and keeps its
hard gates deterministic so that quality does not depend on how strong the
model is. This brief is the line-level deep analysis of where the framework
assumes a frontier model and what to change per file.

# 2. Scope

In scope:
- Model-selection surface (skill `effort`, agent `model:` frontmatter, driver-tier substrate).
- Prompt/instruction design across skills and agents (BLUF, length, structured output, reasoning placement).
- Tool/orchestration assumptions (Agent-tool fallback, concurrency budget vs rate limits).
- Quality + security gates (deterministic vs LLM-judgment split, judge-model strength).
- Token efficiency (description tax, session-load tax, example-block bloat).

Out of scope:
- Vendor SDK integration (Anthropic/OpenAI client wiring) — that is transport, not model-coupling.
- Rewriting the 54-skill fleet body prose wholesale — only targeted, gated edits.
- New model hosting infrastructure — we assume an OpenAI-compatible endpoint exists.

# 3. Diagnostic Snapshot

Current-state evidence (every claim cites `file:line`).

- **Agent `model:` is Anthropic-hardcoded, no tier axis.** 19/19 `.claude/agents/*.md` declare a literal `model: opus` or `model: sonnet` (`.claude/agents/ai-build.md:4`, `.claude/agents/ai-review.md:4`, `.claude/agents/verifier-deterministic.md:4`). All 8 `reviewer-*`, both `verifier-*`, `review-context`, `review-validator` pin `opus` — the heaviest tier — with no `effort`/tier axis. An operator on a free-tier open model has zero lever to downgrade the review/verify fleet.
- **Skill `effort` and agent `model:` are two disconnected vocabularies.** Skills declare `effort: cheap|mid|high` checked by `tools/skill_lint/checks/effort.py:36,55-58`; agents hand-type a literal `model:` value. No live wiring joins them.
- **`model_tier` residue in orphan mirrors.** Spec-189 purged `model_tier` from `.claude/skills/*/SKILL.md` (0 hits) but `.opencode/skills/*/SKILL.md` still emits `model_tier=haiku|sonnet|opus` (e.g. `.opencode/skills/ai-build/SKILL.md:34-37`) — an orphan mirror tree outside canonical sync.
- **`AIENG_MODEL_TIER` is a dead env var** (0 Python readers) yet referenced textually in `.claude/skills/ai-build/SKILL.md:32` per `drafts/fleet-audit-simplify-portability-brief.md:173`.
- **`tool_name_map.py` is mostly unwired.** `scripts/sync_mirrors/tool_name_map.py:1-176` documents open-weight tool-call quirks for kimi/glm/deepseek/qwen/mimo (lines 131-168): DeepSeek rejects dict args, needs JSON-string args (`:144-149`); Kimi-K2 needs `functions.{name}:{idx}` special-token IDs (`:131-137`); Qwen double-escapes (`:151-157`). Only `copilot`'s `name_map` is consumed (`core.py:990` `_translate_copilot_tools`); the 5 open-weight profiles have zero runtime consumers.
- **BLUF is frontmatter-only, not in skill bodies.** CSO `description` is the mandated BLUF (blocking, `tools/skill_domain/rubric.py:257-324`) but `grep -c "^BLUF" .claude/skills/*/SKILL.md` = 0 everywhere. `ai-build/SKILL.md:1-10`, `ai-review/SKILL.md` open straight into headings with no inline one-liner — a weak model reading only the first body paragraph gets no anchor.
- **No machine-checkable acceptance grammar.** `spec-schema.md:30` shows acceptance is freeform prose a weak model must parse implicitly.
- **Agent-tool fallback only on 4 of ~9 dispatch skills.** `ai-review/SKILL.md:74`, `ai-verify/SKILL.md:99`, `ai-simplify/SKILL.md:91`, `ai-advise/SKILL.md:83` state an inline-fallback. The 7 skills `ai-autopilot/SKILL.md`, `ai-build/SKILL.md`, `ai-docs/SKILL.md`, `ai-explore/SKILL.md`, `ai-ide-audit/SKILL.md:33`, `ai-onboard/SKILL.md`, `ai-plan/SKILL.md` assume the Agent-tool primitive with no fallback — confirmed portability gap on the explore/plan/build critical path.
- **Concurrency fan-out ignores rate limits/cost.** `AIENG_MAX_WAVE_AGENTS`/`AIENG_MAX_QUALITY_AGENTS`/`AIENG_MAX_THREAD_WORKERS` auto-tune from `min(free_ram_gb // 4, cores // 2, 6)` (`src/ai_engineering/config/concurrency.py:36-48`) — RAM/CPU only, zero token-cost or RPM awareness.
- **Highest-coupling gate is LLM-judgment.** `verifier-acceptance.md` and 8 `reviewer-*.md` are pure LLM-judgment, each emitting `confidence: 20-100` (`reviewer-security.md:51`), with a 5-step self-challenge chain (`verifier-acceptance.md:37-43`) and nuanced calibration (`review-validator.md:54`) that assume strong self-critique — degrades sharply on Llama/Mistral-class models.
- **Deterministic tier is a strength.** `verifier-deterministic.md:9,13` runs gitleaks/ruff/pip-audit/pytest/ty with "Make NO subjective judgments"; `orchestrator.py:444` precomputes `pass|block` from tool exit codes. Model-agnostic by design.
- **Portability lint enforcement mismatch.** `tools/skill_lint/checks/portability.py:33` claims BLOCKING but `stack_runner.py:162,174` registers `skill_lint`/`spec_lint` `required=False` — operators may believe portability is enforced when it silently is not.
- **Description tax substantiated.** Total `description:` bytes across 54 SKILL.md = 26,037 chars (~6.5k tokens), individual descriptions 500-712 chars (`ai-autopilot/SKILL.md:712`, `ai-build/SKILL.md:661`, `ai-board/SKILL.md:646`) — force-loaded into context for every skill invocation regardless of which runs.
- **Session-load tax.** `CLAUDE.md` (14,441 bytes) + `CONSTITUTION.md` (9,507) + `SOUL.md` (1,827) = 25,775 bytes (~6.4k tokens), mandated every session by `CLAUDE.md §0`, unconditional before any skill work. Combined floor ~13k tokens of instruction overhead before the first user turn.
- **Dangling precursor work.** PR #639 (`spec-185/open-model-resilience`) shipped a runtime `driver-tier.json` substrate (vendor-neutral `frontier`/`standard-floor`/`stretch-floor`) but was abandoned, diverged from the `AIENG_MODEL_TIER` purge, branch-only (`drafts/open-model-portability-brief.md:87,174`).

# 4. Architecture

Proposed structural change — a three-layer model-coupling contract:

1. **Tier substrate (single source of truth).** Reconcile/relaunch the `driver-tier.json` substrate from spec-185: a per-session, vendor-neutral tier (`frontier` / `standard-floor` / `stretch-floor`) resolved from the active endpoint, read by both skill and agent resolution. One writable store; skills' `effort` and agents' `model:` both derive from it. No second tier vocabulary.
2. **Resolution layer.** Extend `_effort_to_model` (already in `scripts/sync_mirrors/core.py`) to map `effort`→`model` for canonical agents too, so a single `effort:` axis drives both skills and agents. Kill the literal `model:` literals in `.claude/agents/*.md:4`.
3. **Gates split (already partly real).** Keep `verifier-deterministic` as the hard gate. Downgrade `verifier-acceptance` + `reviewer-*` to "soft signal" with deterministic fallback when the judge tier is weak, and split the 5-step self-challenge into independently-gradable sub-checks.
4. **Orchestration portability.** Inline-fallback clause on all 7 dispatch-assuming skills; rate-limit/cost-aware concurrency knob alongside the RAM/CPU budget.
5. **Tool quirk wiring.** Promote `tool_name_map.py` open-weight profiles from docs to a parse-and-correct retry consumer.

Surface boundaries unchanged (hexagonal): the tier substrate lives in `state`/`config`; prompts live in skills/agents; runtime consumers in `cli_commands`/`installer`/`vcs` adapters — core/policy/validator must not import them (per `pyproject.toml:232-268`).

# 5. Evidence Catalog

| Claim | Citation |
|-------|----------|
| Agent model hardcoded, no tier axis | `.claude/agents/ai-build.md:4`, `verifier-deterministic.md:4` |
| Skill effort vs agent model disconnected | `tools/skill_lint/checks/effort.py:36,55-58` |
| model_tier residue in orphan mirror | `.opencode/skills/ai-build/SKILL.md:34-37` |
| Dead AIENG_MODEL_TIER referenced | `.claude/skills/ai-build/SKILL.md:32` |
| tool_name_map unwired for open weights | `scripts/sync_mirrors/tool_name_map.py:131-168`, `core.py:990` |
| BLUF frontmatter-only | `tools/skill_domain/rubric.py:257-324`, `ai-build/SKILL.md:1-10` |
| No acceptance grammar | `spec-schema.md:30` |
| Agent-tool fallback missing on 7 skills | `ai-ide-audit/SKILL.md:33`, `ai-explore/SKILL.md`, `ai-plan/SKILL.md` |
| Fallback present on 4 skills (pattern) | `ai-review/SKILL.md:74`, `ai-verify/SKILL.md:99` |
| Concurrency RAM/CPU only | `src/ai_engineering/config/concurrency.py:36-48` |
| LLM-judgment gate self-challenge | `verifier-acceptance.md:37-43`, `revifier-security.md:51` |
| Deterministic tier model-agnostic | `verifier-deterministic.md:9,13`, `orchestrator.py:444` |
| Portability lint enforcement mismatch | `tools/skill_lint/checks/portability.py:33`, `stack_runner.py:162,174` |
| Description tax | `ai-autopilot/SKILL.md:712`, `ai-build/SKILL.md:661` |
| Session-load tax | `CLAUDE.md §0`, `CONSTITUTION.md`, `SOUL.md` |
| Dangling spec-185 driver-tier | `drafts/open-model-portability-brief.md:87,174` |

# 6. Milestones

- **M0 — Reconcile precursor.** Decide: revive spec-185 `driver-tier.json` substrate or hard-delete it. (Open decision D1.)
- **M1 — Tier substrate live.** Single vendor-neutral tier per session, read by skill+agent resolution. Acceptance: a `frontier`/`standard-floor`/`stretch-floor` signal resolves for an OpenRouter free-tier endpoint.
- **M2 — Agent resolution de-literalized.** `effort:` drives all 19 agents; literal `model:` removed; sync_mirrors derives agent `model:` like Copilot's already does. Acceptance: flipping effort downgrades reviewer/verifier fleet with no file edits.
- **M3 — Gate hardening.** `verifier-acceptance` + `reviewer-*` emit independent sub-check verdicts; deterministic fallback when judge tier weak. Acceptance: a `standard-floor` run still emits a hard `pass|block` via the deterministic tier with no silent quality collapse.
- **M4 — Orchestration portability.** Inline-fallback on 7 skills; cost/RPM-aware concurrency knob. Acceptance: a free-tier (20 RPM) run respects the cap, no fallback-absent skill.
- **M5 — Tool quirk wiring.** `tool_name_map.py` open-weight profiles consumed at runtime. Acceptance: DeepSeek JSON-string arg quirk auto-corrected on dispatch.
- **M6 — Token diet.** Trim top-5 descriptions; session digest for the 3 bootstrap files; BLUF line in every SKILL.md body. Acceptance: per-session instruction bytes below a defined ceiling.

# 7. Definition of Done

- Every skill and agent declares model-coupling explicitly (no hidden assumption of frontier).
- On a `standard-floor` open model, all hard gates (verify/review security/quality) still produce deterministic `pass|block` verdicts.
- No skill assumes the Agent-tool primitive without a documented inline fallback.
- Description + session-load instruction bytes reduced by a measurable margin.
- `tool_name_map.py` open-weight quirks are consumed, not just documented.
- No orphan mirror (` .opencode/skills`) retains `model_tier` residue.

# 8. Quality Stamps

- §10.1 KISS — one tier vocabulary (effort), not two.
- §10.2 YAGNI — no new SDK; reuse OpenAI-compatible endpoint assumption.
- §10.5 TDD — a structural test pins the 14-section brief shape AND a test pins "every agent has an `effort:` axis derived from tier".
- §10.6 SDD — this brief precedes the spec; spec cites it.
- §10.8 Hexagonal — tier substrate in core/config; adapters consume; core/policy/validator do not import adapters (`pyproject.toml:232-268`).

# 9. Open Decisions

- **D1 — Revive or delete spec-185 `driver-tier.json`?** It is the only branch with a real runtime tier substrate; reviving saves M1 work but requires reconciling with the `AIENG_MODEL_TIER` purge.
- **D2 — Tier granularity.** Two tiers (`frontier` / `standard-floor`) vs three (add `stretch-floor`)? Affects how many agent variants exist.
- **D3 — Where does judgment degrade to deterministic?** Threshold: when judge tier is `standard-floor`, do `reviewer-*` outputs become advisory-only, or do we run fewer of them?
- **D4 — Session digest vs lazy-load.** Do we cache a summarized digest of CONSTITUTION/CLAUDE/SOUL, or load on-demand by gate? Caching risks staleness.

# 10. Migration

Per CONSTITUTION.md §3 — no shims, hard rename/migration.
- `model:` literals in `.claude/agents/*.md:4` are hard-replaced by derived `effort:` → `model:` via sync_mirrors; no compatibility `model:` fallback kept.
- `model_tier=` residue in `.opencode/skills/*/SKILL.md` is hard-deleted (orphan mirror regenerated from canonical).
- `AIENG_MODEL_TIER` textual references hard-deleted; if a tier var is needed, it is `AIENG_DRIVER_TIER` from the new substrate.
- CHANGELOG documents each break.

# 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Downgrading reviewer fleet to weak model silently lowers review signal | High | High | Deterministic fallback (M3); gate warns when judge tier weak |
| Inline fallback on 7 skills doubles maintenance | Med | Low | Replicate the existing 4-skill clause verbatim; CI parity test |
| Reviving spec-185 diverges further from main | Med | Med | Rebase first; D1 decision before M1 |
| Session digest goes stale vs source docs | Low | Med | Digest regenerated by `ai-eng dev sync`, not hand-edited |
| Description-trim breaks skill routing keywords | Med | Low | Keep CSO 3-trigger + negative-scope minimum (`rubric.py:257-324`) |
| tool_name_map wiring adds retry latency on frontier | Low | Low | Only apply per-family correction when family detected |

External research corroborates the core thesis: open models claiming 128K
often have ~32K effective context (arXiv:2410.18745); CoT degrades
instruction-following on small models (arXiv:2505.11423, Llama3-8B 75.2%→59.0%);
a weak model is a fragile judge (arXiv:2604.16790); structured output via
constrained decoding is the highest-leverage fix (vLLM structured outputs
docs, [PERSON_NAME]). These validate M3 (deterministic gates) and M6
(context/token diet).

# 12. References

- Internal: `drafts/open-model-portability-brief.md` (spec-189 precursor, most diagnoses already here), `drafts/fleet-audit-simplify-portability-brief.md` (description-tax claim), `spec-schema.md`, `docs/persistence-doctrine.md`.
- External (open-model behavior):
  - Effective context length: arXiv:2410.18745
  - Reasoning vs instruction-following: arXiv:2505.11423 (NeurIPS 2025)
  - LLM-as-judge bias / weak judges: arXiv:2411.15594, arXiv:2604.16790
  - Constrained decoding (structured output): vLLM structured_outputs docs; [PERSON_NAME]; XGrammar
  - Multi-agent orchestration capacity-bound: arXiv:2601.11327; α-UMi tool-split: arXiv:2401.07324
  - Model routing: RouteLLM (lmsys.org/blog/2024-07-01-routellm)
  - Provider quirks: DeepSeek-R1 README (no system prompt, temp 0.6); Qwen3 docs (no greedy, temp 0.6 thinking); Llama 3 prompting (AWS)

# 13. Glossary

- **Driver tier** — vendor-neutral model capability tier per session (`frontier` / `standard-floor` / `stretch-floor`), the single source of truth for skill `effort` and agent `model:`.
- **standard-floor** — the open/low-cost model class this brief must support (e.g. [PERSON_NAME] 8B, DeepSeek-V3, Mistral via free tier).
- **Inline fallback** — a SKILL.md clause that, when no Agent-tool primitive exists, executes specialists sequentially by reading their files inline.
- **Deterministic tier** — gate stage that runs tool-driven checks (ruff/gitleaks/pip-audit/pytest/ty) and computes verdict from exit codes, model-agnostic.
- **Judgment tier** — gate stage that relies on LLM self-critique/confidence; model-strength-coupled.

# 14. Acceptance

- [ ] Single vendor-neutral driver tier resolves per session for an OpenRouter free-tier endpoint.
- [ ] All 19 `.claude/agents/*.md` derive `model:` from `effort:`; no literal `model:` at line 4.
- [ ] Flipping effort to `standard-floor` downgrades the reviewer/verifier fleet with zero file edits.
- [ ] `verifier-acceptance` + `reviewer-*` emit independent sub-check verdicts; deterministic fallback fires when judge tier is weak.
- [ ] All 7 dispatch-assuming skills have a documented inline-fallback clause.
- [ ] Concurrency fan-out respects a cost/RPM ceiling, not just RAM/cores.
- [ ] `tool_name_map.py` open-weight profiles are consumed at runtime (DeepSeek/Qwen/Kimi quirks auto-corrected).
- [ ] Top-5 skill `description:` fields trimmed to CSO minimum; skill BODY carries a BLUF line.
- [ ] Bootstrap (CONSTITUTION/CLAUDE/SOUL) instruction bytes below a defined ceiling.
- [ ] No `model_tier=` residue in any mirror; `AIENG_MODEL_TIER` references removed.
- [ ] A structural test asserts "every agent exposes an `effort:` axis derived from the tier substrate".
- [ ] Hard gates still emit deterministic `pass|block` on a `standard-floor` run with no silent quality collapse.
