---
title: "Fleet Audit — Simplify + Model-Portability for Skills, Agents, and every .md"
status: draft
audience: framework-dev / operator
branch: audit/fleet-simplify-portability
length_estimate: multi-wave refactor (5 waves, ≥3 concerns, ≥30 files)
authoring_style: diagnostic-brief
principles_required:
  - "§10.1 KISS"
  - "§10.2 YAGNI"
  - "§10.4 DRY"
  - "§10.5 TDD"
  - "§10.6 SDD"
  - "§10.7 Clean Code"
delivery_mode: /ai-autopilot
mantra: "Less prose, more procedure — one canonical source, portable to every model."
---

# Fleet Audit — Simplify + Model-Portability for Skills, Agents, and every .md

> Supersedes five unconsumed predecessor drafts (see §10). This brief is the
> executable consolidation: it ships or it hard-deletes its own scope. No sixth
> parallel draft.

## 1. Vision

Make every skill, agent, and `.md` in `ai-engineering` **simpler, more
deterministic, single-sourced, and portable to any model family** — Claude,
GPT, Gemini, and open-weight (Kimi, GLM, DeepSeek, Qwen, MiMo) — without losing
one unit of capability. The framework today is powerful but verbose,
prose-heavy, and quietly Claude-Code-shaped in ways that degrade on open
models. We cut the noise, convert imperative prose to numbered procedure,
delete what nothing reads, and enforce the result with lints so drift is
impossible without a red test. The winning move is not adding a doc — it is
deleting five that never shipped and lint-gating the sixth.

## 2. Scope Boundary

**In scope**
- All 54 canonical skills (`.claude/skills/ai-*/SKILL.md`).
- All 19 agents (`.claude/agents/*.md`: 9 user-facing + 10 internal review/verify).
- Canonical `.md`: top-level rulebook set, `.ai-engineering/reference/*`,
  `.ai-engineering/runbooks/*`, `.ai-engineering/overrides/**`, `docs/*`.
- The `src/ai_engineering/templates/.../CANONICAL.md` generation source and
  `scripts/sync_mirrors/core.py` (mirrors are derived; fixes route through the
  generator, not the mirrors).
- A new **portability lint** + **structure lint** + **token-baseline** gate.

**Explicitly NOT in scope**
- Live open-weight model execution / eval runs (portability bar is structural
  neutrality, lint-enforced — no live runs this cycle; §7).
- Rewriting `CHANGELOG.md` (4,030L, append-only history, not a living doc).
- Python source behavior changes beyond what a dead-reference deletion forces.
- Adding new IDE mirror families (e.g. `.kimi/`, `.glm/`) — deferred; this cycle
  makes the **canonical** source neutral, not the mirror tree wider (§9 D-4).

## 3. Diagnostic Snapshot

Current state, evidence-cited. Every claim below carries a `file:line` anchor.

**Surface size.** 54 skills, 19 agents, 243 scoped canonical files / 45,824
lines; repo-wide 1,948 `.md` files / 226,053 lines. **~78% (176,683 lines) is
generated skill/agent mirror duplication** across `.claude/ .codex/ .agents/
.github/ .opencode/` + `src/.../templates/` — derived by `scripts/sync_mirrors/core.py`
from the single `.claude/` canonical source. *Lever: shrink canonical, mirrors
shrink for free.*

**Description tax.** 54 `description:` fields = **25,649 raw chars (~6,412
tokens) loaded every session** for routing. Longest: `ai-autopilot/SKILL.md:3`
(712 chars), `ai-verify/SKILL.md:3` (692), `ai-build/SKILL.md:3` (661) — all
over Anthropic's own guidance that a description states what+when concisely
(hard cap 1,024 chars; these are near it while carrying prose).

**Example bloat.** 52/54 skills carry a `## Examples` section; **44/54 have
exactly 22 lines** — a rigid copy-paste template. **1,161 total lines** spent on
Examples corpus-wide. This is the single largest hand-authored cut with no
capability loss.

**Dead references (documented behavior that does not exist).**
- `overrides/<stack>/debug.md`: instructed at `.claude/skills/ai-debug/SKILL.md:110-112`
  (+13 mirror/template copies), **exists in 0 locations for all 12 stacks**;
  the real decision (`spec-135 .../plan.md:51`) was "HARD DELETE" — the skill
  misremembers it as "consolidate into debug.md".
- `--consume`: printed at `.claude/skills/ai-spec-draft/SKILL.md:35,90` (+~18
  copies) but `ai-brainstorm/SKILL.md` has **zero** "consume"; real flag is
  `--consolidate-spec` (`ai-brainstorm/SKILL.md:6,26-35`).
- `AIENG_MODEL_TIER`: claimed at `.claude/skills/ai-build/SKILL.md:32` (+6
  copies), **read by 0 Python files**; absent from the live tunable inventory
  `CLAUDE.md:172-211`.

**Hard-rule self-violation.** 14 `deprecated: true` forwarder stubs in
`.github/agents/*.md` + `.codex/agents/*.md` (e.g.
`.github/agents/reviewer-compatibility.md:1-10`) directly violate `CLAUDE.md`
§13 Rule 3 ("No backwards-compat shims… hard delete"). Not shipped to consumers
(installer template has no `.github/agents/`), so deletable now.

**Orphans / dead surface.**
- 10/14 `.ai-engineering/runbooks/*.md` have **zero** inbound refs from any
  skill/agent/doc and zero Python consumers (`code-quality.md`, `consolidate.md`,
  `dependency-health.md`, `feature-scanner.md`, `governance-drift.md`,
  `refine.md`, `security-scan.md`, `stale-issues.md`, `wiring-scanner.md`,
  `work-item-audit.md`) — schema-tested (`tests/unit/test_runbook_contracts.py`)
  but operationally undiscoverable.
- Reference triad `engineering-standards.md`, `harness-adoption.md`,
  `harness-engineering.md`: only consumer is an existence-check test
  (`tests/unit/test_engineering_standards.py:49,51,53`); linked from 0 live docs.
- `ai-analyze-permissions` — strongest true-orphan skill (no `## Integration`,
  0 inbound, excluded from mirrors per `ai-scaffold/SKILL.md:117`).

**Portability risks (Claude-Code-shaped assumptions).**
- `tools:` frontmatter hardcodes Claude tool names (`ai-build.md:6` →
  `[Read, Write, Edit, Bash, Glob, Grep]`); a per-family mapping exists **only**
  for Copilot (`.github/agents/build.agent.md:4`) — **no mapping for any
  open-weight harness**.
- 49/54 skills end with a bare `$ARGUMENTS` token (`ai-brainstorm/SKILL.md:129`)
  and the entire cross-skill dispatch graph is expressed as `/ai-*`
  slash-commands — inert on a raw-API host with no slash layer.
- `AGENTS.md:169-170` ide-extras fence is **empty**: the generic/portable entry
  point carries zero hook/hot-path guidance, so non-Claude/non-Copilot engines
  get none.

**Prior art (the load-bearing finding).** Five overlapping briefs on this exact
scope sit unconsumed in `.ai-engineering/specs/drafts/`:
`skills-agents-excellence-v2-brief.md` (708L), `skills-agents-excellence-refactor.md`
(903L), `prune-contexts-docs-research-evals-brief.md` (485L),
`less-is-more-quality-engine-brief.md`, `framework-simplification-less-is-more-brief.md`.
They cite stale counts (50 skills / 26 agents vs 54/19). **The problem is not
discovery — it is that no prior attempt was executable.** This brief must be
the one that ships.

## 4. Architecture

Five structural moves, each lint-anchored so it cannot regress silently.

1. **Canonical-only edits, generated mirrors.** All rewrites happen in `.claude/`
   canonical + `src/.../templates/CANONICAL.md`; `scripts/sync_mirrors/core.py`
   regenerates the 5–6 mirror families. Token savings on canonical multiply
   ~6–7× through the mirror tree automatically. No mirror is ever hand-edited.

2. **Description contract (routing plane).** Every `description:` = third-person
   "what + when", trigger-triad (capability / trigger / user-vocabulary),
   hard-capped and lint-enforced well under 1,024 chars. Descriptions are the
   only session-loaded text; this is the highest-leverage token cut.

3. **Body = procedure, not prose.** `## Workflow` becomes numbered steps /
   checklists / tables (structure lint scores prose-ratio). `## Examples`
   collapses to at most one canonical example or moves to `references/`
   (progressive disclosure). Target body < 500 lines (already met; enforce as a
   ceiling), refs one level deep, TOC on 100+-line reference files.

4. **Portability-neutral canonical + translation table.** Extract a
   `tools:`-name mapping table in `scripts/sync_mirrors/` keyed by family;
   canonical skill/agent prose avoids un-gated Claude-only idioms; the
   `AGENTS.md` generic entry gains a portable hook/hot-path pointer. Open-weight
   families get a documented tool-name map (no new mirror dirs this cycle).

5. **Hard-delete plane.** Dead refs, orphans, deprecated stubs, and the 5
   predecessor drafts are removed outright (no deprecation, per §13 Rule 3 and
   operator directive). Deletion is gated on zero-inbound + test-confirmed-dead.

New gates (build-vs-buy decided in §9): a **portability lint**, a **structure
lint**, and a **`token-baseline` snapshot** proving the reduction.

## 5. Evidence Catalog

| # | Claim | Evidence (`file:line`) |
|---|-------|------------------------|
| E1 | Mirror duplication = ~78% of all `.md` lines, generated from `.claude/` | `scripts/sync_mirrors/core.py`; `.codex/skills/ai-brainstorm/SKILL.md:8-10` |
| E2 | Description tax ~6,412 tokens/session; longest 712 chars | `ai-autopilot/SKILL.md:3`; `ai-verify/SKILL.md:3`; `ai-build/SKILL.md:3` |
| E3 | 44/54 skills carry identical 22-line Examples block; 1,161 lines total | `ai-brainstorm/SKILL.md` `## Examples`; corpus-wide |
| E4 | Dead ref `overrides/<stack>/debug.md` (0 files exist) | `ai-debug/SKILL.md:110-112`; `spec-135.../plan.md:51` |
| E5 | Dead flag `--consume`; real flag `--consolidate-spec` | `ai-spec-draft/SKILL.md:35,90`; `ai-brainstorm/SKILL.md:6,26-35` |
| E6 | Dead env var `AIENG_MODEL_TIER` (0 Python readers) | `ai-build/SKILL.md:32`; `CLAUDE.md:172-211` |
| E7 | 14 `deprecated:true` shims violate Hard Rule 3 | `.github/agents/reviewer-compatibility.md:1-10`; `CLAUDE.md` §13.3 |
| E8 | 10/14 runbooks orphaned (0 inbound, 0 Python) | `tests/unit/test_runbook_contracts.py:13-27` |
| E9 | Reference triad orphaned (test-only consumer) | `tests/unit/test_engineering_standards.py:49,51,53` |
| E10 | `tools:` frontmatter Claude-native; only Copilot mapped | `ai-build.md:6`; `.github/agents/build.agent.md:4` |
| E11 | `$ARGUMENTS` + `/ai-*` idioms assume slash-command host | `ai-brainstorm/SKILL.md:129` |
| E12 | Empty portable-entry ide-extras fence | `AGENTS.md:169-170` |
| E13 | Five unconsumed predecessor briefs, stale counts | `.ai-engineering/specs/drafts/skills-agents-excellence-v2-brief.md`; +4 |

## 6. Roadmap

Wave-gated (matches the operator's chosen full-fleet phased shape). Each wave
lands a green gate before the next starts.

- **W1 — Audit + baseline + gates (foundation).** Snapshot `token-baseline`
  over canonical surface. Land the three lints (portability / structure /
  token-budget) in CI as *warn-only* first. Hard-delete the 5 predecessor
  drafts + confirmed dead refs (E4–E7) + orphan surface (E8–E9) gated on
  zero-inbound. Gate: lints run green (warn), dead-ref greps return 0, tests green.
- **W2 — Skills rewrite (54).** Description contract (E2) + Examples collapse
  (E3) + prose→procedure (structure lint). Regenerate mirrors. Gate: token
  reduction target hit on canonical, all conformance/parity tests green.
- **W3 — Agents rewrite (19).** Same treatment; `tools:` mapping table extracted.
  Gate: agent parity tests green, portability lint green.
- **W4 — Docs + cross-link + reference/runbook reorg.** Fix one-way/miswired
  links, index or delete runbooks, resolve reference-triad, fill portable
  `AGENTS.md` pointer (E12). Gate: link checker (lychee) 0 broken, 0 orphans.
- **W5 — Portability neutrality + flip lints to blocking.** Canonical neutrality
  lint passes; per-family tool-map documented; lints flip warn→block. Gate: all
  three lints blocking-green in CI.

## 7. Definition of Done

Composite north-star (operator selected verbosity **and** determinism **and**
dead-surface removal):

1. **Verbosity.** Canonical skill+agent (description + body) token footprint
   reduced by a target ≥ **25%** vs the W1 `token-baseline` snapshot, with
   **100% of existing conformance/parity/count-gate tests green**. (Exact % set
   in §9 D-2 after baseline.)
2. **Determinism / procedure.** Structure lint: ≥ target share of skill
   `## Workflow` steps are numbered/checklist/tabular vs free prose; no skill
   body > 500 lines; refs one level deep.
3. **Dead-surface removal.** All of E4–E9 removed; 5 predecessor drafts deleted;
   0 orphan/miswired links (lychee); 14 deprecated stubs gone (E7).
4. **Portability (structural neutrality, no live runs).** Portability lint
   blocking-green: no un-gated Claude-only tool literal in canonical prose;
   `tools:` family-map covers documented targets; `$ARGUMENTS`/`/ai-*` idioms
   either host-gated or documented as harness-provided; `AGENTS.md` portable
   entry carries hook/hot-path pointer.
5. **SSOT.** Every edit in canonical only; mirrors regenerate clean; parity
   tests green; `token-baseline` proves the delta.

## 8. Quality Stamps

- **§10.1 KISS / §10.2 YAGNI** — deletion over abstraction; no new mirror dirs,
  no speculative open-weight harness this cycle.
- **§10.4 DRY** — canonical-only edits; generated mirrors; kill copy-paste
  Examples and duplicated dead-ref prose.
- **§10.5 TDD** — every structural rule becomes a lint/test; drift is a red gate.
- **§10.6 SDD** — this brief → `/ai-brainstorm` spec → `/ai-plan` → delivery.
- **§10.7 Clean Code** — procedure over prose; the framework practises the
  determinism it preaches.
- Contracts honoured: `CLAUDE.md` §13.3 (hard delete, no shims), §13.7 (SSOT
  per datum), surface-axioms parity (`test_surface_parity.py`).

## 9. Open Decisions (for `/ai-brainstorm` to resolve)

- **D-1 Predecessor drafts.** Harvest-then-hard-delete all 5, or keep 1 as a
  merged appendix? *Recommend: harvest key roadmaps into this brief's spec, then
  hard-delete all 5 (they are the noise the operator asked us to remove).*
- **D-2 Token target.** Exact reduction % — set after W1 `token-baseline`.
  *Recommend ≥25% canonical, treat mirror savings as free multiplier.*
- **D-3 Build vs buy the lints.** Adopt external tools (`ctxlint`, `skills-check`,
  `promptfoo test-agent-skills`, `Vale`, `token-baseline`, `mdcompress`,
  `lychee`) vs write minimal in-repo lints. *Recommend: buy the mature link/prose
  layer (Vale + lychee), write thin in-repo skill/portability lints we own.*
- **D-4 Open-weight mirrors.** Add `.kimi/`/`.glm/` mirror families now, or only
  neutralize canonical + document a tool-name map? *Recommend: neutralize +
  document; defer new mirror dirs (YAGNI until a real open-weight harness exists).*
- **D-5 Runbook fate.** Delete the 10 orphans, or wire them into a discovery
  index? *Recommend: delete unless a named workflow consumes them.*
- **D-6 `ai-analyze-permissions`.** Keep (terminal entry point) or delete (true
  orphan)? Needs an owner decision.
- **D-7 MiMo.** No portability benchmark exists `[unsourced]` — flag MiMo as
  untested; neutrality lint covers it structurally, live behavior unverified.

## 10. Migration

Hard rename / hard delete / hard migration only — no shims, no deprecation
window (`CLAUDE.md` §13.3 + operator directive "directamente fuera"). CHANGELOG
documents each breakage.

- **Hard-delete now (W1):** 5 predecessor drafts; dead-ref prose (E4–E6) across
  all mirror + template copies; 14 deprecated forwarder stubs (E7); orphan
  runbooks + reference triad (E8–E9) once zero-inbound reconfirmed at delete time.
- **Regeneration:** every canonical edit re-runs `ai-eng dev sync` /
  `scripts/sync_mirrors/core.py`; hooks-manifest + parity tests re-pin. Never
  hand-edit a mirror (prevents the mirror-drift class already in the memory
  corpus).
- **No backwards-compat token** kept for `--consume` → `--consolidate-spec`; the
  string is deleted, not aliased.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| 6th brief also dies in `drafts/` | High | High | Executable wave-gates + single owner + this brief deletes its predecessors; route via `/ai-autopilot` |
| Touching `sync_mirrors` bricks consumer installs (formatter/manifest class in memory corpus) | Med | High | Parity + hooks-manifest tests as W-gates; regenerate, never hand-edit |
| Over-aggressive deletion removes load-bearing content | Med | High | Delete only zero-inbound + test-confirmed-dead; reconfirm at delete time |
| Portability lint false-positives block benign prose | Med | Med | Ship warn-only in W1, tune, flip to block in W5 |
| Count-gate breakage from skill/section removal (new-skill-count-gates class) | Med | Med | Run full `tests/unit/config` + `tests/unit/docs` + `ai-eng check` per wave |
| MiMo portability unverifiable | Low | Low | Structural lint only; documented as untested |

## 12. References

External evidence (full citation set retained in research artifacts):

- Anthropic — Agent Skills overview + authoring best-practices (description ≤1024
  chars, third-person what+when; SKILL.md body <500 lines; refs one level deep;
  TOC on 100+-line files; progressive disclosure): platform.claude.com Agent
  Skills docs; anthropic.com/engineering "Equipping agents… with Agent Skills".
- Cross-model portability: "Control Illusion" (arXiv 2502.15851) + role-conflict
  studies — system>user hierarchy fails across families (Llama/Qwen
  anti-hierarchy); HuggingFace transformers #45419 + vLLM tool-calling guide —
  no shared tool-call standard (Kimi `functions.{name}:{idx}` IDs; GLM
  `tool_stream`; Claude XML idioms degrade elsewhere).
- Determinism: "When LLMs Stop Following Steps" (arXiv 2605.00817) — accuracy
  61%→20% from 5→95 steps; "Less Back-and-Forth" (arXiv 2605.20149) — checklists
  7.50 vs 5.67 raw, fewer tokens; Oracle "Recipes for Determinism".
- Tooling: `ctxlint`, `skills-check`, `token-baseline`, `trs audit-docs`,
  `mdcompress` (faithfulness-audited), `Vale`, `lychee`, `promptfoo
  test-agent-skills`; security scanners SkillSpector (NVIDIA), Backslash.
- NotebookLM deep-research notebook `6be473e4-c6e9-458a-bec6-c5cd861146d8`
  (fleet audit) — synthesis of the above plus Kimi-K2.5 / GitBook skill.md
  guides; harvest-at-brainstorm for open-model quirks (DeepSeek-V3 schema
  hallucination, Qwen single-purpose task-confusion, Gemini/Gemma JSON fencing).

## 13. Glossary

- **Canonical surface** — the hand-authored `.claude/` skills/agents +
  `.ai-engineering/` docs that `sync_mirrors` regenerates all IDE mirrors from.
- **Mirror family** — a generated IDE-specific copy tree (`.codex/`, `.agents/`,
  `.github/`, `.opencode/`, `.cursor/`).
- **Description tax** — total chars of all skill `description:` fields, loaded
  every session for routing.
- **Portability lint** — a structural check that canonical prose carries no
  un-gated model-family-specific assumption.
- **Structure lint** — a check scoring procedure (numbered/checklist/table) vs
  free prose in a skill `## Workflow`.
- **Trigger triad** — description pattern: capability + trigger conditions + user
  vocabulary.

## 14. Acceptance

- [ ] W1 `token-baseline` snapshot captured; 3 lints live (warn-only); 5
      predecessor drafts + confirmed dead refs (E4–E7) + orphans (E8–E9) deleted.
- [ ] W2 all 54 skills meet description contract + Examples collapsed +
      structure lint; canonical token reduction ≥ target; parity tests green.
- [ ] W3 all 19 agents rewritten; `tools:` family-map extracted; portability
      lint green.
- [ ] W4 links: 0 broken (lychee), 0 orphans; runbook/reference reorg done;
      `AGENTS.md` portable pointer filled.
- [ ] W5 portability + structure + token lints flipped to blocking, all green.
- [ ] No `--consume`, `AIENG_MODEL_TIER`, `overrides/<stack>/debug.md`, or
      `deprecated:true` stub remains anywhere (grep = 0).
- [ ] `ai-eng check` and full `tests/unit/{config,docs}` green; mirrors clean.
