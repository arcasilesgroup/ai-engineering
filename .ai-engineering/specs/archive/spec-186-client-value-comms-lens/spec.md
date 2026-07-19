---
spec: spec-186
slug: client-value-comms-lens
title: "spec-186 — Client-Value Lens: stakeholder-legible communication for the skill chain"
status: approved
effort: medium
branch: TBD
target_dispatch: /ai-autopilot
summary: Add a Client-Value Lens — a canonical value-block (bottom line, impact, risk, next) the 5 chain skills emit in every user-facing report and question, so non-technical sponsors get plain, agile-framed value; blocking CI enforces it, carve-outs keep code and security precise.
---

## Summary

The ai-engineering chain (`/ai-brainstorm → /ai-plan → /ai-build → /ai-autopilot → /ai-pr`) produces excellent machine artifacts — schema-locked specs, patch-ready plans, integrity reports — but every human-facing moment is authored for an engineer or a downstream agent. A non-technical sponsor (product owner, client, or an autonomous agentic company acting as one) reading a `/ai-plan` STOP sees unified-diff hunks and `§10.x` anchors; a `/ai-brainstorm` proposal grades technical Pros/Cons with no business-value clause. Nowhere in the chain is a change framed as an increment of value — impact, risk, and what it unlocks — in plain terms.

This spec introduces a **Client-Value Lens**: a thin, always-available communication discipline that renders every user-facing report *and every question a chain skill asks* as a concise, non-technical, agile-framed value statement — without turning sessions into verbose prose, and without ever softening the precision of code, commits, gates, or security warnings. It borrows the proven mechanics of the caveman and ponytail plugins (two-hook injection, level ladder, hard carve-outs) but ships *with the framework* as a repo-level convention, so autonomous consumers get it even without those host plugins installed. Full research and evidence: `doc: .ai-engineering/specs/drafts/client-value-comms-lens-brief.md`.

## Goals

- A canonical reference doc `.ai-engineering/reference/value-lens.md` defines the 6-field value block, per-field length caps, the `lite`/`full`/`ultra` audience ladder, and the carve-out list — the single writable home for the datum.
- The 5 chain skills (`ai-brainstorm`, `ai-plan`, `ai-build`, `ai-autopilot`, `ai-pr`) emit the value block at their end-of-phase report step, citing the reference.
- The same 5 skills frame every user-facing *question* they pose (interrogation prompts, approval asks) in PO/stakeholder-legible terms — plain language, per-option trade-offs, why-it-matters — not raw technical prompts.
- Default audience level is `full` (PO/stakeholder); `lite`/`full`/`ultra` are selectable via `AIENG_VALUE_LENS_LEVEL` env → manifest default → `full` precedence.
- Reinforcement reuses the existing `SessionStart` (`runtime-session-start.py`) and `UserPromptSubmit` (`runtime-progressive-disclosure.py`) hooks; the canonical hook-event count stays at 11 and hot-path budgets (<1s pre-commit, <5s pre-push) hold.
- A blocking CI test fails if any of the 5 chain skills omits the value-block contract.
- A test asserts the carve-outs: code, commit messages, unified-diff patch hunks, security warnings, acceptance-criteria test conditions, gate verdicts, and irreversible-action confirmations are written precise/normal — never value-speak.
- No emoji, no machine-absolute paths; mirrors regenerated from CANONICAL; count/parity gates green; CHANGELOG documents the hard-adopt.

## Non-Goals

- No rewrite of the spec, plan, or PR-body *artifact* schemas — the lens is a human layer above the machine contract, which is untouched.
- No fleet-wide adoption across all 54 skills / 9 agents in v1 — chain-first only; broader reach is a follow-on spec.
- No new Claude Code plugin, and no dependency on caveman or ponytail being installed — the lens travels with the framework.
- No change to the README/onboarding prose voice — `.ai-engineering/reference/brand-voice.md` stays scoped to documentation copy.
- No changes to off-chain reporting/memory skills (`ai-standup`, `ai-sprint`, `ai-prose`) — they may consume the block later, but are not the delivery vehicle here.
- No adaptive audience-detection in v1 — a fixed default plus explicit level override, no inference logic.

## Decisions

### D-186-01 — v1 scope is the 5 chain skills only (chain-first)

**Choice**: Adopt the lens in `ai-brainstorm`, `ai-plan`, `ai-build`, `ai-autopilot`, `ai-pr` only. Do NOT touch the other 49 skills or the 9 agents in v1.
**Rationale**: Operator decision (2026-07-18). These are the surfaces where a human sponsor reads a report and decides. Fleet-wide adoption would touch every SKILL.md and trip ~5 count/parity gates for no additional proof of the contract. Prove the value-block form on the highest-traffic path first; generalise in a follow-on once it holds. KISS/YAGNI.

### D-186-02 — Default audience level is `full`; ladder is `lite`/`full`/`ultra`

**Choice**: Ship three levels — `lite` (engineer: bottom line + inline detail), `full` (PO/stakeholder: all 5 fields, jargon translated), `ultra` (exec/autonomous: bottom line + risk only). Default `full`. Resolve `AIENG_VALUE_LENS_LEVEL` env → manifest key → `full`.
**Rationale**: Operator decision (2026-07-18). `full` is the broadest-legible middle for a non-technical human sponsor. The ladder (repurposed from caveman's intensity levels to audience depth) lets autonomous consumers opt into `ultra` and engineers into `lite` without a second mechanism. Env→manifest→default mirrors caveman's `readFlag` precedence — one proven pattern.

### D-186-03 — The lens governs user-facing QUESTIONS, not only reports

**Choice**: Apply the lens to every point where a chain skill addresses the human — interrogation questions, approach proposals, and approval asks — in addition to end-of-phase report blocks. Questions carry plain-language framing and per-option trade-offs so a PO/stakeholder can answer meaningfully.
**Rationale**: Operator requirement (2026-07-18): "que el interrogatorio del brainstorm … te pregunte con sentido para que PO/stakeholders lo entiendan." A value block on the report is worthless if the sponsor could not understand the question that shaped it. Extending the lens to questions closes the loop; the `AskUserQuestion` used in this very brainstorm (plain options, trade-off previews) is the reference implementation.

### D-186-04 — Cadence: user-facing interaction points, not internal turns

**Choice**: Emit the lens at every user-facing interaction point — questions and phase reports — but NOT on internal working turns (tool calls, intermediate reasoning, routine acknowledgements).
**Rationale**: Follows from D-186-03. Phase-boundary-only is too narrow (it misses questions); persistent-per-turn (caveman-style) risks verbosity creep on routine messages. Scoping to interaction points captures every moment a sponsor reads or decides while leaving working turns lean. Field caps and the Lauchman two-question filter guard the remaining verbosity risk.

### D-186-05 — Adoption is enforced by a blocking CI test on the chain skills

**Choice**: A CI test hard-fails if any of the 5 chain skills omits the value-block contract at its report/question step. Not advisory.
**Rationale**: Operator decision (2026-07-18). The analogous `§10.x` citation rule is advisory/MINOR and only ~12 of 55 skills comply (`tools/skill_lint/checks/principles.py:9-14`) — soft enforcement demonstrably under-adopts. A blocking gate on a 5-skill scope is cheap to satisfy and guarantees the contract actually ships.

### D-186-06 — SSOT is a new `reference/value-lens.md`, not a §10.9 principle

**Choice**: The value-block contract, level ladder, and carve-out list live in a new `.ai-engineering/reference/value-lens.md`, peer to `brand-voice.md` / `principles.md` / `gate-policy.md`. Working name "Client-Value Lens" (operator may rename). Do NOT promote it to a new §10.9 engineering principle.
**Rationale**: One canonical writable store per datum (`CLAUDE.md` §13.7, DRY §10.4); skills cite it, never re-declare the fields. A §10.x principle inherits the same soft-enforced citation machinery (D-186-05) — a reference doc plus a blocking test is strictly stronger. Placement per `knowledge-placement.md:38` (reusable cross-surface guidance → `reference/`).

### D-186-07 — Reinforcement reuses existing hooks; no new hook event

**Choice**: Inject the compact contract once at `SessionStart` (`runtime-session-start.py`) and append a one-line reminder to the existing `additionalContext` on `UserPromptSubmit` (`runtime-progressive-disclosure.py:360-375`). Add NO new hook event beyond the canonical 11.
**Rationale**: The native equivalent of caveman's proven two-hook injection already exists and is hot-path-cached. Reusing it reaches all chain surfaces with near-zero marginal cost and keeps `tests/unit/hooks/test_canonical_events_count.py` green. Adding a bespoke hook would be new surface for no benefit — KISS.

### D-186-08 — Carve-outs are load-bearing and test-asserted

**Choice**: The lens NEVER applies value-speak to: source code, commit messages, unified-diff patch hunks, security warnings, acceptance-criteria test conditions, gate verdicts, and irreversible-action confirmations. These stay precise/normal. A test asserts the carve-out list is present and honoured.
**Rationale**: This is the single most important transfer from caveman (`Code/commits/security: write normal`) and ponytail (never simplify trust boundaries). Value framing that softened a security warning or blurred a gate verdict would be a governance regression. The block *summarises* exact output for the sponsor; it never replaces or softens it.

### D-186-09 — Composability: hard carve-out from caveman; ships with the framework

**Choice**: When caveman is also active, the value block is a declared carve-out from caveman compression (it renders in full; surrounding chatter may stay terse). The lens is repo-level and travels with the framework install — it does not require caveman/ponytail.
**Rationale**: The lens is orthogonal — ponytail governs *what you build*, caveman *how you talk*, the lens *how you frame value*. A fragment-compressed value block would destroy the sponsor framing, so the block must be exempt. Shipping with the framework is the whole point versus the host-level plugins: an autonomous consumer running ai-engineering unattended gets the value signal with nothing extra installed.

### D-186-10 — The value block is a fixed 6-field BLUF form with per-field caps

**Choice**: The canonical block is: (1) Bottom line — what changed + the "so that" value, 1 line; (2) Why it matters — impact in plain terms, 1-2 sentences; (3) What's done / now possible — acceptance criteria as outcomes, 2-3 bullets; (4) Risk / watch-outs — name → impact → mitigation, or explicit "None", 1-2 lines; (5) Next / decision needed, 1 line; (6, optional) Details — collapsed spec/PR/commit/`file:line` pointers. Field caps enforced.
**Rationale**: This is the BLUF/Minto pyramid rendered as a form — answer first (Field 1), support (2-5), evidence (6). An exec reads Field 1 and stops; a PO reads 1-5; an engineer expands Field 6. Concise-but-complete by construction — detail is subordinated behind Field 6, never omitted. Per-field caps plus one-idea-per-field are the anti-verbosity guardrail.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Value-speak leaks into code/commit/security/patch/verdict output | Medium | High | Carve-out list (D-186-08) is load-bearing and test-asserted; mirrors caveman's proven `Code/commits/security` exemption |
| The block/questions become verbose prose, defeating the goal | High | Medium | Per-field caps + Lauchman two-question filter + positive-concision phrasing + detail behind Field 6; cadence excludes internal turns (D-186-04) |
| Hook reinforcement adds hot-path latency | Medium | Medium | Reuse the already-cached `runtime-progressive-disclosure` rig; one appended line; assert <1s/<5s budgets and unchanged 11-event count |
| Blocking CI on chain skills churns during rollout | Medium | Low | Land the contract in `value-lens.md` first (Wave 1), then flip the gate on once the 5 skills carry it (Wave 3/4) — failing-first, one PR per wave |
| CANONICAL / mirror edit trips a count or parity gate | Medium | Low | New reference doc + pointer row only; run `ai-eng dev sync` + full count/parity suite before push |
| caveman compression clips the value block when both active | Low | Medium | Declare the block a hard carve-out from caveman (D-186-09); render full |
| Default level wrong for autonomous consumers | Low | Low | Configurable via `AIENG_VALUE_LENS_LEVEL` / manifest (D-186-02); document the trade-off |

## References

- doc: .ai-engineering/specs/drafts/client-value-comms-lens-brief.md
- doc: .ai-engineering/reference/brand-voice.md
- doc: .ai-engineering/reference/principles.md
- doc: .ai-engineering/reference/knowledge-placement.md

## Open Questions

- Final name for the lens ("Client-Value Lens" is the working handle; operator may prefer a caveman/ponytail-style single word). Does not block `/ai-plan`.
- Whether `ultra` should be the default specifically for detected autonomous/headless runs (v1 keeps `full` default with explicit override; revisit if autonomous usage dominates).
- Exact manifest key name for the default level (e.g. `value_lens.default_level`) — settled at `/ai-plan`.
