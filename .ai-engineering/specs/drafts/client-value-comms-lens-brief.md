---
title: "Client-Value Lens — Concise, Stakeholder-Legible Communication for the ai-engineering Skill Chain"
status: draft
audience: /ai-brainstorm
reader: framework maintainers
branch: TBD (assigned at /ai-brainstorm promotion)
length_estimate: "~365 lines"
authoring_style: "Staff Principal Architect — evidence-anchored, BLUF-ordered, carve-out-disciplined, no hedging"
principles_required: [KISS, YAGNI, DRY, SOLID, SDD, TDD, clean-code, hexagonal]
delivery_mode: "Multi-wave, single-concern-per-PR / hard-adopt / no-shim / Conventional Commits"
mantra: "Cada cambio llega como un resultado que el sponsor puede sopesar, no como un mecanismo que debe descifrar. Answer first, detail on request, jargon on a leash — and never at the cost of a precise gate, commit, or security warning."
---

> **READ FIRST.** This brief is a structured intake for `/ai-brainstorm`. It is the human-readable contract between the idea phase and the spec phase. It was authored from a codebase audit of the ai-engineering skill chain plus an external prior-art sweep (BLUF/Minto, agile value framing, plain-language, Anthropic output-steering) on 2026-07-18, and a mechanics study of the caveman + ponytail Claude Code plugins installed on this workstation. Diagnostic claims carry `file:line` citations; machine-absolute paths are rewritten to `$HOME/...`. No implementation begins until this brief is promoted to `spec-NNN` and approved. Reader audience: framework maintainers.
>
> **The thesis, stated as a test.** A skill "communicates its value" when a *non-technical sponsor* — a product owner, a client, an autonomous agentic company acting as one — reads the report and can correctly answer three questions without decoding the mechanism: *what changed, why it matters, and what it risks or unlocks.* Today the chain fails that test. The `/ai-plan` output is unified-diff hunks and `§10.x` anchors (`.claude/skills/ai-plan/SKILL.md:44-57`); the `/ai-brainstorm` proposal grades `Effort`/`Risk` in engineer terms with no business-value clause (`.claude/skills/ai-brainstorm/handlers/interrogate.md:97-109`); no surface in `brainstorm → plan → build → pr` carries an agile increment-of-value statement. The artifacts are excellent. The *translation for the human who is paying for them* is missing.

---

## 1. Vision

ai-engineering produces governance-grade artifacts — schema-locked specs, patch-ready plans, integrity reports. But every one of those artifacts is authored for an engineer or a downstream agent. The human on the other side of a `/ai-brainstorm` or `/ai-plan` STOP is frequently *not* an engineer: they are the operator deciding whether to spend the increment, the product owner weighing scope, or — increasingly — an autonomous agentic company running the chain unattended and needing a legible value signal to act on.

The vision is a **Client-Value Lens**: a thin, always-available communication discipline that renders every question, proposal, plan, and change as a *concise, non-technical, agile-framed value statement* — impact, risk, and increment — **without** turning the session into verbose prose, and **without** touching the precision of code, commits, gates, or security warnings.

Two existing plugins already prove the shape works on this machine. Caveman governs *how you talk* (terse); ponytail governs *what you build* (lazy/minimal). Both are orthogonal, composable, and — critically — both exempt high-stakes output from their style (`$HOME/.claude/plugins/cache/caveman/caveman/.../skills/caveman/SKILL.md:54-74`; ponytail `.../skills/ponytail/SKILL.md:87-115`). The Client-Value Lens is the third orthogonal axis: it governs *how you frame value*. It is caveman's concision aimed at a sponsor instead of a hacker.

The lens is expressed through one artifact — a **fixed-field, BLUF-ordered value block** — and one adoption rig that mirrors caveman's proven two-hook injection, reusing native ai-engineering hooks rather than adding new surface.

---

## 2. Scope Boundary

### In scope

| Item | Reason |
|------|--------|
| A canonical value-block contract (fields + caps + level ladder + carve-outs) | The one datum this brief introduces; needs a single writable home |
| Adoption across the canonical chain — `/ai-brainstorm`, `/ai-plan`, `/ai-build`, `/ai-autopilot`, `/ai-pr` | These are where a human sponsor reads a report and decides |
| Native reinforcement via existing `SessionStart` + `UserPromptSubmit` hooks | Caveman's proven pattern; the native equivalent already exists (`.ai-engineering/scripts/hooks/runtime-progressive-disclosure.py:360-375`) |
| A level ladder (lite / full / ultra ↔ dev / PO / exec) mapped to audience depth | Caveman's level system, repurposed from intensity to audience |
| Carve-out list (code, commits, patch hunks, security, acceptance criteria, irreversible-action confirms stay precise) | The single most important transfer from caveman/ponytail — value-speak must never corrupt exact output |

### Explicitly NOT in scope

| Item | Why excluded |
|------|--------------|
| Rewriting the spec / plan / PR *artifact* schemas | The machine artifacts stay exactly as they are; the lens adds a human layer above them, it does not replace the contract |
| A repo-wide tone/voice rewrite of README / docs prose | Covered by `.ai-engineering/reference/brand-voice.md:1-3` (documentation authority, out of runtime scope) |
| Cross-session memory or reporting skills (`ai-standup`, `ai-sprint`, `ai-prose`) | Off-chain; may *consume* the block later but are not the delivery vehicle |
| A new Claude Code plugin | The lens is a *repo-level* convention that travels with the framework install; caveman/ponytail are host-level plugins — deliberately not the model here |
| Full 54-skill adoption in v1 | Chain-first (5 skills); fleet-wide is a follow-on decision, not a v1 gate |

---

## 3. Diagnostic Snapshot

Current-state evidence. Every "currently" sentence cites `file:line`.

### 3.1 The chain reports to humans in engineer-only vocabulary (HIGH)

Currently, `/ai-plan`'s user-facing output is the "exhaustive patch-ready output template": per-task `T-N`, `Agent`, `Files`, `Principles §10.x`, a `Patch (deterministic):` unified diff, and a `Gate` line (`.claude/skills/ai-plan/SKILL.md:44-57`). Step 12 then just prints `safe_next_command` and STOPs (`.claude/skills/ai-plan/SKILL.md:42`). There is no narrative slot and no value statement — a non-technical sponsor reading a plan sees diff hunks and model-tier routing.

Currently, `/ai-brainstorm` proposals are templated with `How / Pros / Cons / Effort (S/M/L) / Risk (low/med/high)` and a `## Recommendation` (`.claude/skills/ai-brainstorm/handlers/interrogate.md:97-109`). The `Effort`/`Risk` axes exist, but Pros/Cons are technical and there is **no business-impact or agile value-increment clause** — no "so that <sponsor-legible outcome>". The spec-review summary reports *process* metrics (iteration counts, concerns found/resolved), not delivered value (`.claude/skills/ai-brainstorm/handlers/spec-review.md:81-90`).

Currently, `/ai-build` and `/ai-autopilot` phase reports are machine tables keyed `| # | Severity | Source | Category | Description | File:Line | Reproducer |` (`.claude/skills/ai-build/handlers/quality.md:100`; `.claude/skills/ai-autopilot/handlers/phase-quality.md:170`). Autopilot names a "transparency / Integrity Report" (`.claude/skills/ai-autopilot/SKILL.md:24,58`) but it is a defect ledger, not a value summary. The `/ai-pr` body composes `Summary / Test Plan / Work Items / Checklist` (`.claude/skills/ai-pr/SKILL.md:83,111-113`) — dev-facing, no impact/risk for a non-technical reader.

### 3.2 The only value-framing vocabulary that exists is off-chain (MEDIUM)

Currently, the sole audience-tuned value surface is `/ai-prose`, whose audience table maps `executive → "Business value and risk"` and `manager → "Impact and timeline"` (`.claude/skills/ai-prose/SKILL.md:48-52`; `.claude/skills/ai-prose/handlers/content.md:59`). But `/ai-prose` is an off-chain content skill — it is never invoked inside `brainstorm → plan → build → pr`. The spec `summary:` field is defined as outcome-not-method (`.ai-engineering/reference/spec-schema.md:15-23`), the closest existing value hook, but it is capped at ≤300 chars and bound to the PR body (`.ai-engineering/reference/spec-schema.md:20`). `/ai-explain` has a `TL;DR` tier (`.claude/skills/ai-explain/SKILL.md:43`) — code explanation only. **No TL;DR / stakeholder-value / increment-of-value convention exists inside the chain skills themselves.**

### 3.3 There is no repo-level output-style mechanism at all (MEDIUM)

Currently, the closest thing to a tone mechanism is `.ai-engineering/reference/brand-voice.md`, explicitly scoped to "prose authority for README and onboarding copy" — documentation text, **not** skill/agent runtime output (`.ai-engineering/reference/brand-voice.md:1-3`). caveman and ponytail are Claude Code *plugin-level* (host), not repo-level, so they do not travel with an ai-engineering install and cannot be relied on by an autonomous consumer. A runtime comms convention that ships *with the framework* is genuinely new surface area.

### 3.4 The proven adoption rig already exists natively — unused for comms (LOW, and this is the opportunity)

Currently, `.ai-engineering/scripts/hooks/runtime-progressive-disclosure.py:360-375` already emits `hookSpecificOutput.additionalContext` on `UserPromptSubmit` — the exact native equivalent of how caveman re-injects its per-turn reminder (`$HOME/.claude/hooks/caveman-mode-tracker.js:108-129`, injected string at `:121-127`). It is wired at `.claude/settings.json:61-62`, with a live `SessionStart` slot at `.claude/settings.json:220-236` → `runtime-session-start.py`, and it already caches a skills index to stay inside the hot-path budget (`.ai-engineering/scripts/hooks/runtime-progressive-disclosure.py:115-200`). The rig to make a lens fleet-wide and self-reinforcing is present; it has simply never carried a communication payload.

---

## 4. Architecture

The lens is **one datum, one rig, one attach-point contract** — deliberately KISS.

### 4.1 Component A — the value-block contract (SSOT)

A new reference doc `.ai-engineering/reference/value-lens.md`, peer to `principles.md`, `brand-voice.md`, `gate-policy.md`, placed per `.ai-engineering/reference/knowledge-placement.md:38` (reusable cross-surface guidance → `reference/`). It is the single writable home for the datum (SSOT-per-datum, `CLAUDE.md` §13.7). It defines the **one-screen value block** — a fixed-field, BLUF-ordered form (not free prose), each field length-capped:

| # | Field | Holds | Cap | Basis |
|---|-------|-------|-----|-------|
| 1 | **Bottom line** | What changed + the value, "so that <sponsor outcome>" | 1 line | BLUF/Minto answer-first; INVEST-Valuable |
| 2 | **Why it matters** | Impact in plain terms (important / positive / negative) — significance, not mechanism | 1–2 sentences | "explain impact not mechanism" (plain-language) |
| 3 | **What's done / now possible** | Acceptance criteria as user-facing outcomes; the shippable increment | 2–3 bullets | AC-as-outcomes; increment-of-value |
| 4 | **Risk / watch-outs** | Named risk → impact if it lands → mitigation underway. Explicit "None" if none | 1–2 lines | Risk sequence: name→impact→response→decision |
| 5 | **Next / decision needed** | The next step, or the exact decision required (what, by whom, by when) | 1 line | Decision-point framing |
| 6 *(opt.)* | **Details** | Collapsed pointer layer: spec / PR / commit / `file:line` refs + the technical detail | link only | Progressive-disclosure layer 3–4 |

Ordering is load-bearing: it is the BLUF/Minto pyramid rendered as a form. An exec reads Field 1 and stops; a PO reads 1–5; an engineer expands Field 6. Concise-but-complete *by construction* — detail is subordinated, never omitted.

### 4.2 Component B — the level ladder (audience, not intensity)

Caveman's `lite / full / ultra` intensity ladder (`$HOME/.claude/.../skills/caveman/SKILL.md:28-52`) is repurposed to **audience depth**:

- **lite** → engineer-facing: Field 1 + Field 6 inline; technical terms kept.
- **full** (default) → PO / stakeholder: all fields 1–5; jargon translated or defined inline on first use.
- **ultra** → exec / autonomous-sponsor: Field 1 + Field 4 only; zero jargon; one business outcome + its single risk.

### 4.3 Component C — the reinforcement rig (native two-hook, no new surface)

Mirror caveman's dual-injection using hooks that already exist — **no new hook event beyond the canonical 11**:

- **`SessionStart`** (`runtime-session-start.py`, `.claude/settings.json:220-236`): inject the compact contract once (the field list + carve-outs), the way caveman's `SessionStart` prints the full ruleset.
- **`UserPromptSubmit`** (`runtime-progressive-disclosure.py:360-375`, `.claude/settings.json:61-62`): append a one-line reminder to the existing `additionalContext` — e.g. `"CLIENT-VALUE LENS ACTIVE (full): report changes as sponsor outcomes — bottom line, impact, risk, next. Code/commits/security/patches: write precise/normal."` — reusing the cached, hot-path-bounded machinery already there.

### 4.4 Component D — attach points

Each canonical-chain skill emits the value block at its **end-of-phase STOP / report step**, citing `value-lens.md`: `/ai-brainstorm` at the proposal/recommendation and spec-review summary (`handlers/interrogate.md:97-109`, `handlers/spec-review.md:81-90`); `/ai-plan` at step 12 before `safe_next_command` (`SKILL.md:42`); `/ai-build` + `/ai-autopilot` above the defect table (`quality.md:100`, `phase-quality.md:170`); `/ai-pr` as a value preamble to the composed body (`SKILL.md:111-113`). The machine artifact underneath is untouched.

### 4.5 Component E — carve-outs (the load-bearing transfer)

Exactly as caveman exempts `Code/commits/security` and ponytail refuses to simplify trust boundaries, the lens **never** applies value-speak to: source code, commit messages, unified-diff patch hunks, security warnings, acceptance-criteria *test conditions*, gate verdicts, and irreversible-action confirmations. Those are written precise and normal. The value block *summarizes* them for the sponsor; it never replaces or softens them.

### 4.6 Composability

Orthogonal to both plugins: ponytail = *what you build*, caveman = *how you talk*, Client-Value Lens = *how you frame value*. When caveman is also active, the value block is a declared carve-out from caveman compression (a fragment-only block would destroy the sponsor framing) — the block renders in full; the surrounding chatter stays terse.

---

## 5. Evidence Catalog

| ID | Claim | Citation |
|----|-------|----------|
| E-1 | Plan output is engineer-only (diffs, §10.x, tiers); no value slot | `.claude/skills/ai-plan/SKILL.md:44-57`, `:42` |
| E-2 | Brainstorm proposal has Effort/Risk but no business-value / "so that" clause | `.claude/skills/ai-brainstorm/handlers/interrogate.md:97-109` |
| E-3 | Spec-review summary reports process metrics, not value | `.claude/skills/ai-brainstorm/handlers/spec-review.md:81-90` |
| E-4 | Build/Autopilot reports are defect tables; Integrity Report is a ledger | `.claude/skills/ai-build/handlers/quality.md:100`, `.claude/skills/ai-autopilot/handlers/phase-quality.md:170`, `.claude/skills/ai-autopilot/SKILL.md:24,58` |
| E-5 | PR body is dev-facing (Summary/Test Plan/Checklist) | `.claude/skills/ai-pr/SKILL.md:83,111-113` |
| E-6 | Only value vocabulary is off-chain `ai-prose`; spec `summary:` is ≤300ch PR-bound | `.claude/skills/ai-prose/SKILL.md:48-52`, `.ai-engineering/reference/spec-schema.md:15-23,20` |
| E-7 | No repo-level output-style mechanism; brand-voice is docs-only | `.ai-engineering/reference/brand-voice.md:1-3` |
| E-8 | Native UserPromptSubmit `additionalContext` rig already exists | `.ai-engineering/scripts/hooks/runtime-progressive-disclosure.py:360-375`, `.claude/settings.json:61-62` |
| E-9 | Native SessionStart slot + hot-path cache | `.claude/settings.json:220-236`, `runtime-progressive-disclosure.py:115-200` |
| E-10 | Caveman proves two-hook injection + carve-outs + level ladder | `$HOME/.claude/hooks/caveman-mode-tracker.js:108-129`, caveman `SKILL.md:13-15,28-52,54-74` |
| E-11 | §10.x citation is soft-enforced (MINOR) and only ~12/55 skills cite it | `tools/skill_lint/checks/principles.py:9-14,46`, `.ai-engineering/reference/principles.md:15-17` |
| E-12 | Mirror byte-parity + count gates constrain any CANONICAL edit | `.ai-engineering/reference/mirror-authoring.md:13-14`, `tools/skill_lint/checks/md_mirror.py:257-262` |

---

## 6. Roadmap

Single-concern PR per wave.

### Wave 1 — Define the datum (SSOT)

- **M1.1** Author `.ai-engineering/reference/value-lens.md`: the 6-field block, per-field caps, the lite/full/ultra audience ladder, the carve-out list, and the anti-verbosity guardrails (field caps + Lauchman two-question filter + inline-jargon rule + positive-concision phrasing). *Gate:* a structural test asserts the doc exists and declares all six fields + the carve-out list (peer to how `md_mirror.py:257-262` asserts extracted reference docs exist).
- **M1.2** Add the CANONICAL §14–16 pointer row for `value-lens.md`; regenerate mirrors via `ai-eng dev sync`. *Gate:* `tests/architecture/test_surface_parity.py` + count gates green.

### Wave 2 — Native reinforcement rig

- **M2.1** Extend `runtime-session-start.py` to inject the compact contract once per session, and `runtime-progressive-disclosure.py:360-375` to append the one-line lens reminder to `additionalContext`, gated by the active level. Reuse the existing cache; no new hook event. *Gate:* hook fires under the pre-commit <1s / pre-push <5s budget (`core.py:1062-1065`); a test asserts the 11 canonical events are unchanged (`tests/unit/hooks/test_canonical_events_count.py`).
- **M2.2** Level selection: resolve `AIENG_VALUE_LENS_LEVEL` (env) → manifest default → `full`, mirroring caveman's `readFlag` precedence (`$HOME/.claude/hooks/caveman-config.js:39-59`). *Gate:* unset-env defaults to `full`; a test asserts precedence.

### Wave 3 — Chain attach points

- **M3.1** `/ai-brainstorm` + `/ai-plan` emit the value block at their STOP/report steps, citing `value-lens.md`. *Gate:* a test asserts each chain SKILL.md report step references the block contract.
- **M3.2** `/ai-build`, `/ai-autopilot`, `/ai-pr` emit the block above/around their existing artifact. *Gate:* same test extended; the machine artifact table/PR body is unchanged (diff-asserted).

### Wave 4 — Guardrails + composability

- **M4.1** Encode carve-outs as an explicit list in `value-lens.md` and assert (test) that code/commit/patch/security/AC/confirm contexts are named exempt.
- **M4.2** Declare orthogonality with caveman/ponytail; the value block is a caveman-compression carve-out. Document in CHANGELOG (hard-adopt, no dual-tone toggle).

---

## 7. Definition of Done

1. A canonical `value-lens.md` defines the 6-field block, per-field caps, the lite/full/ultra ladder, and the carve-out list — the single writable home for the datum (E-6, E-7).
2. Each canonical-chain skill (`brainstorm`, `plan`, `build`, `autopilot`, `pr`) emits the block at its human-facing report step, citing the reference (E-1..E-5).
3. Every emitted block is BLUF-ordered, field-capped, and defines any unavoidable jargon inline; no field exceeds its cap.
4. Carve-outs are honored: code, commits, patch hunks, security warnings, acceptance-criteria test conditions, gate verdicts, and irreversible-action confirmations are written precise/normal — never value-speak (E-10).
5. Reinforcement reuses the existing `SessionStart` + `UserPromptSubmit` hooks, stays within hot-path budgets, and adds no hook event beyond the canonical 11 (E-8, E-9).
6. The level ladder is selectable with a documented default (`full`).
7. No emoji, no machine paths, anonymous content; mirrors regenerated from CANONICAL; count/parity gates green (E-12).
8. CHANGELOG documents the hard-adopt; no backwards-compat shim, no dual-tone toggle (`CLAUDE.md` §13.3).

---

## 8. Quality Stamps

| Principle | How this brief honors it |
|-----------|--------------------------|
| §10.1 KISS | One datum, one rig, one attach contract; reuses existing hooks rather than adding surface |
| §10.2 YAGNI | No new plugin, no artifact-schema rewrite, no v1 fleet-wide adoption |
| §10.4 DRY | Single SSOT reference doc; skills cite it, never re-declare the field list |
| §10.3 SOLID | The lens is a presentation port above the artifact; the machine contract underneath is untouched |
| §10.5 TDD | Every milestone lands behind a failing-first test (doc-exists, event-count, precedence, attach-point citation) |
| §10.6 SDD | This brief precedes the spec; spec precedes code |
| §10.7 Clean Code | Fixed fields with names that predict content; jargon defined inline |
| §10.8 Hexagonal | Value block is an adapter over the report boundary; carve-outs keep the exact-output port unpolluted |

Contracts honored: `CLAUDE.md` §13.3 (no shims), §13.4 (anonymous, no emoji), §13.7 (SSOT per datum), Hot-Path Discipline. No emojis; no machine-absolute paths.

---

## 9. Open Decisions

The spec phase must resolve these:

1. **Reinforcement scope** — extend the existing `runtime-progressive-disclosure` UserPromptSubmit injection (cheapest, hot-path-shared) versus a `SessionStart`-only one-shot (lower per-turn cost, weaker persistence) versus reference-doc-plus-skill-citation with *no* hook reminder (zero latency, relies wholly on skills reading the doc). Recommendation: extend the existing hook (E-8) — proven by caveman, near-zero marginal cost.
2. **Level toggle storage + default** — env `AIENG_VALUE_LENS_LEVEL` + manifest key vs caveman-style flag file vs a slash command. Default `full` or `lite`? (Autonomous consumers may want `ultra` by default.)
3. **Adoption breadth** — chain-only (5 skills) in v1, or all 54? Recommendation: chain-first; fleet-wide is a follow-on once the contract proves out.
4. **Enforcement strength** — a blocking CI test that chain skills carry the block, or advisory only? Note: the analogous §10.x citation test is MINOR/non-blocking and only ~12/55 skills comply (E-11) — soft enforcement demonstrably under-adopts. Recommendation: blocking for the 5 chain skills.
5. **Naming + taxonomy** — "Client-Value Lens" as a `reference/` doc peer, or promote to a new §10.9 engineering principle? A principle gets the citation machinery but inherits its soft enforcement.
6. **Emission cadence** — block at phase boundaries only (proposed), or a persistent per-turn framing like caveman? Persistent is more legible but risks verbosity creep on every message.
7. **caveman/ponytail composability contract** — is the value block a hard carve-out from caveman compression (block always renders full), and does an autonomous run with neither plugin still get the lens? (Yes — it ships with the framework; that is the whole point vs the host-level plugins.)

---

## 10. Migration

Per `CLAUDE.md` §13.3 (`CONSTITUTION.md` Prohibitions): hard adopt, no backwards-compat shim, no dual-tone toggle.

- **New surface** (Wave 1): `value-lens.md` is additive; the CANONICAL pointer row and mirror regeneration are mechanical (`ai-eng dev sync`).
- **Behavior change** (Wave 2/3): chain skills gain a report block; the underlying artifact contracts (spec schema, plan template, PR body, defect tables) are unchanged and un-migrated — the lens sits *above* them.
- **Hooks** (Wave 2): reuse existing `SessionStart` + `UserPromptSubmit`; if hook bytes change, regenerate `hooks-manifest.json` so integrity stays `enforce`.
- **CHANGELOG** records the hard-adopt and the level default; no alias, no legacy "verbose mode".

No data migration. The datum is new; nothing is renamed or deleted.

---

## 11. Risks

Likelihood × Impact, with mitigations.

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Value-speak leaks into code/commit/security/patch output | Medium | High | Carve-out list is load-bearing and test-asserted (M4.1); mirrors caveman's proven `Code/commits/security` exemption |
| The block becomes verbose prose, defeating the goal | High | Medium | Per-field caps + Lauchman two-question filter + positive-concision phrasing + detail behind Field 6 |
| Hook reinforcement adds hot-path latency | Medium | Medium | Reuse the already-cached progressive-disclosure rig; one appended line; assert <1s/<5s budgets |
| Soft enforcement → chain skills skip the block (as §10.x is skipped, ~12/55) | Medium | Medium | Blocking CI test for the 5 chain skills (Open Decision 4) rather than advisory |
| CANONICAL/mirror edit trips a count/parity gate | Medium | Low | New reference doc + pointer row only; run `dev sync` + full count/parity suite before push |
| caveman compression clips the value block | Low | Medium | Declare the block a hard carve-out from caveman; render full |
| Level default wrong for autonomous consumers | Low | Low | Configurable via env/manifest; document the trade-off (Open Decision 2) |

---

## 12. References

External prior art and explanatory references:

1. BLUF (Bottom Line Up Front) — put the takeaway first. LogRocket, *Using the BLUF acronym to improve communication*. https://blog.logrocket.com/product-management/using-the-bluf-acronym-to-improve-communication/
2. Minto Pyramid Principle — answer, then key arguments, then evidence. Untools, https://untools.co/minto-pyramid/ ; BetterUp, https://www.betterup.com/blog/minto-pyramid
3. Agile value framing — user-story "so that <value>", INVEST-Valuable, acceptance criteria as plain outcomes. Cybermedian, https://www.cybermedian.com/the-ultimate-guide-to-agile-user-stories-acceptance-criteria-invest/ ; Scrum Alliance, https://resources.scrumalliance.org/Article/need-know-acceptance-criteria
4. Definition of Done vs Acceptance Criteria (global bar vs story scope). Nulab, https://nulab.com/learn/software-development/definition-of-done-vs-acceptance-criteria/
5. Risk communication sequence — name → impact → response → decision point; tailor by audience. Safran, https://www.safran.com/blog/how-to-communicate-risk-to-project-stakeholders
6. Progressive disclosure — index → summary → detail → source. Nielsen Norman Group, https://www.nngroup.com/articles/progressive-disclosure/
7. Plain language — reader-focused, explain impact not mechanism, Lauchman two-question filter, define jargon inline. US National Archives Top-10 Principles, https://www.archives.gov/open/plain-writing/10-principles.html ; Evidence for Democracy, *Plain Language Summaries Toolkit*.
8. Anthropic — audience-anchoring steers depth; prefer positive concision examples over negatives; concision must never compromise completeness. *Prompting Claude Opus 4.8*, https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8 ; Claude Code *Output styles*, https://code.claude.com/docs/en/output-styles

Internal anchors: `.ai-engineering/reference/principles.md:15-17` (§10.x citation pattern), `.ai-engineering/reference/knowledge-placement.md:38` (reference-doc placement), `.ai-engineering/reference/mirror-authoring.md:13-14` (mirror contract), `.ai-engineering/reference/spec-schema.md:15-23` (spec `summary:` field), `.claude/skills/ai-spec-draft/SKILL.md:41-59` (this skill's contract). Mechanics study: `$HOME/.claude/plugins/cache/caveman/caveman/.../skills/caveman/SKILL.md:13-15,28-52,54-74`, `$HOME/.claude/hooks/caveman-{activate,mode-tracker,config}.js`, ponytail `.../skills/ponytail/SKILL.md:23-27,87-115`.

---

## 13. Glossary

- **Client-Value Lens** — the runtime communication discipline this brief proposes: render changes as concise, non-technical, agile-framed value statements, exempting exact output.
- **Value block** — the fixed-field, BLUF-ordered form (Bottom line / Why it matters / What's done / Risk / Next / Details) the lens emits.
- **BLUF** — Bottom Line Up Front: the conclusion/recommendation in the first line.
- **Minto Pyramid** — top-down structure: main answer, then supporting arguments, then evidence.
- **Increment of value** — a shippable slice of business value communicated as an outcome, not a technical milestone.
- **Acceptance criteria (as outcomes)** — per-story "done" conditions phrased in user-facing terms; distinct from the global Definition of Done.
- **Carve-out** — output deliberately exempt from the lens (code, commits, patch hunks, security, gate verdicts, AC test conditions, irreversible-action confirms), written precise/normal.
- **Level ladder** — lite/full/ultra mapped to audience depth (dev / PO / exec), repurposed from caveman's intensity ladder.
- **Two-hook rig** — caveman's proven injection: full ruleset at `SessionStart`, one-line reminder at `UserPromptSubmit`.
- **SSOT (per datum)** — every datum has one canonical writable store; here, `value-lens.md` (`CLAUDE.md` §13.7).
- **Progressive disclosure** — reveal in stages: headline first, depth on request (Field 6).
- **Chain skills** — the canonical `/ai-brainstorm → /ai-plan → /ai-build → /ai-autopilot → /ai-pr` surfaces where a human sponsor reads and decides.

---

## 14. Acceptance

Checklist form of the Definition of Done. Each item is independently verifiable.

- [ ] `.ai-engineering/reference/value-lens.md` exists and declares the 6-field block, per-field caps, the lite/full/ultra ladder, and the carve-out list (E-6, E-7).
- [ ] Each chain skill (`brainstorm`, `plan`, `build`, `autopilot`, `pr`) emits the value block at its human-facing report step, citing the reference (E-1..E-5).
- [ ] Every emitted block is BLUF-ordered, field-capped, and defines unavoidable jargon inline; no field exceeds its cap.
- [ ] Code, commits, patch hunks, security warnings, AC test conditions, gate verdicts, and irreversible-action confirmations are written precise/normal — never value-speak (E-10).
- [ ] Reinforcement reuses `SessionStart` + `UserPromptSubmit`, stays under <1s/<5s budgets, and the canonical event count is unchanged at 11 (E-8, E-9).
- [ ] `AIENG_VALUE_LENS_LEVEL` resolves env → manifest → `full`; a test asserts the precedence and default.
- [ ] Mirrors regenerated from CANONICAL; count/parity gates green; no emoji, no machine paths (E-12).
- [ ] CHANGELOG documents the hard-adopt; zero backwards-compat shims, no dual-tone toggle (`CLAUDE.md` §13.3).
