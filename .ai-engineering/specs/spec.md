---
spec: spec-164
title: SOUL.md — Agent Values & Persona Layer
status: in-progress
effort: small
summary: Add a shipped, canonical SOUL.md defining the agent's four collaborator values (Pragmatic Helpfulness, Honest & Direct, Collaborative Partner, Learn & Grow); mirrors carry a pointer, §0 Bootstrap reads it, dogfood + template parity enforced.
---

## Summary

ai-engineering has a precise instruction-surface stack — CONSTITUTION.md
(*what the project is*), CANONICAL.md → CLAUDE/AGENTS/copilot mirrors
(*how the AI works*), and principles.md (*engineering principles +
Operating Mindset §1-9*). What it lacks is a **values / persona layer**:
a statement of *who the agent is as a collaborator* — its stance toward
the operator, its candor, its relationship posture. The closest existing
content, Operating Mindset §1-9, is engineering-discipline one-liners
(Think Before Coding, Demand Elegance), not interpersonal values.

Inspired by molty.me's "soul" document, this spec adds a shipped,
canonical `SOUL.md` carrying four collaborator values translated from
molty's set into a form appropriate for a framework that targets
**regulated environments** (banking, healthcare, public sector). The
genuinely-underserved value is **Honest & Direct** — tell the operator
what they need to hear and disagree when the evidence says so — which no
current surface mandates. SOUL.md is wired into the §0 Bootstrap
read-list so it actually shapes behavior rather than sitting decorative.

## Goals

- Ship a canonical `SOUL.md` at repo root (and a populated template copy)
  defining four collaborator values: Pragmatic Helpfulness, Honest &
  Direct, Collaborative Partner, Learn & Grow.
- Make SOUL.md a single-source-of-truth **canonical source** (like
  `principles.md`), referenced by a one-line pointer in CANONICAL.md that
  auto-propagates to every IDE mirror — zero content duplication.
- Wire SOUL.md into the CANONICAL §0 Bootstrap read-list so every session
  loads it (the mechanism that gives the values teeth).
- Keep the tone regulated-safe: candid and warm-peer, **no sarcasm or
  playful "we're friends not boss/employee" framing** that would clash
  with the Mission on a banking/healthcare install.
- Guarantee installs actually receive SOUL.md via existing template-tree
  and dogfood-parity guards (avoid the spec-161 "feature missing from
  installs" failure mode).
- Resolve the operator's explicit question: confirm SOUL.md does **not**
  conflict with CONSTITUTION.md, CANONICAL.md, AGENTS.md, or the
  Operating Mindset, and document why.
- Sharpen the value phrasings using the Anthropic model-spec as a quarry
  (honesty taxonomy, autonomy bound, anti-paternalism), **stripped of all
  model-specific framing** so the doc stays host-LLM-agnostic.

## Non-Goals

- **No `/ai-soul` skill.** SOUL.md is a hand-edited canonical doc like
  principles.md; no scaffold/amend skill in this spec (YAGNI).
- **No manifest key** (`soul.enabled`, `soul.tone`, etc.). No
  per-install configurability or tone dial in this spec.
- **No operator-authored slot.** Content is framework-voice and fixed
  (shipped populated), unlike CONSTITUTION.md's 0B operator-authored
  template placeholder.
- **No refactor of Operating Mindset §1-9.** SOUL.md complements it; it
  does not absorb, move, or restate it.
- **No personal/by-name content.** SOUL.md names no operator (honors
  Prohibition #5 anonymity); molty's "Peter" has no equivalent.
- **No CONSTITUTION.md changes.** Persona is AI-behaviour, out of
  CONSTITUTION's scope by its own charter.

## Decisions

### D-164-01 — Scope: shipped framework template

SOUL.md ships to **every install** via `ai-eng init`, with fixed
framework-voice content and a regulated-safe tone.

**Rationale**: The operator chose product-wide reach over a
personal/gitignored doc. A shipped artifact must serve the framework's
stated audience — teams shipping under regulatory constraints — so tone
and content are constrained accordingly, not molty's personal register.

### D-164-02 — Architecture: standalone canonical SOUL.md, mirrors point to it

SOUL.md is the single writable canonical store. CANONICAL.md gains a
one-line `## Soul` pointer row that syncs byte-equivalent into
CLAUDE.md / AGENTS.md / copilot-instructions.md. No mirror embeds the
value prose.

**Rationale**: Honors Hard Rule #7 / Prohibition #8 (Single Source of
Truth Per Datum) and the spec-134 "mirror diet." Reuses the proven
`principles.md` pattern (canonical reference doc + lean mirror pointer),
so there is no second writable copy of the values to drift.

### D-164-03 — Values: faithful-but-professional, four values

Carry all four molty values, reframing the one that strains against the
Mission: **Pragmatic Helpfulness**, **Honest & Direct**, **Collaborative
Partner** (replaces molty's "Friendship" — peer-not-servant, warm,
supportive, but **no sarcasm/playful** register), **Learn & Grow**.
Pragmatic Helpfulness cross-references §10.1 KISS / §10.2 YAGNI; Learn &
Grow cross-references Operating Mindset §7 (Self-Improvement Loop).
Honest & Direct is the net-new behavioral mandate.

**Rationale**: Preserves molty's spirit while staying shippable to
regulated teams. Cross-referencing (not restating) existing principles
keeps the SoT clean — SOUL.md owns the *values framing*, principles.md
owns the *engineering prose*.

### D-164-04 — Location & name: root `SOUL.md` (uppercase), populated dual-copy

File is `/SOUL.md` (uppercase, matching CONSTITUTION.md / CANONICAL.md /
AGENTS.md root convention). Dual copy: repo `/SOUL.md` (dogfood) +
`src/ai_engineering/templates/project/SOUL.md` (install source).
**Both populated** with identical content.

**Rationale**: Uppercase matches every sibling identity doc at root;
prominence matches molty's "front-and-center soul" intent. Populated
template (not a 0B placeholder like CONSTITUTION) follows from D-164-01:
the content is framework-voice and fixed, so the template ships it
filled.

### D-164-05 — Build scope: minimal viable, wired in

Deliverables: SOUL.md (repo + template), CANONICAL.md `## Soul` pointer
(auto-syncs mirrors), CANONICAL.md §0 Bootstrap read-list addition, one
template/dogfood parity guard, CHANGELOG entry. **No** skill, **no**
manifest key, **no** README/docs section beyond CHANGELOG.

**Rationale**: KISS/YAGNI. The §0 Bootstrap wiring is the single
load-bearing piece that makes the soul functional; everything beyond it
(skill, manifest, docs surfaces) is maintenance burden on a static doc
with no demonstrated need yet.

### D-164-06 — Boundary: SOUL.md is CANONICAL-orbit, never CONSTITUTION

SOUL.md is AI-behaviour/persona content. It lives in the CANONICAL
family (pointer from CANONICAL.md, read in §0 Bootstrap). It is **not**
part of CONSTITUTION.md and introduces no `/ai-constitution` overlap.

**Rationale**: Directly answers the operator's conflict question.
CONSTITUTION's own charter disclaims AI-behaviour rules ("those live in
CANONICAL.md / AGENTS.md"), and `/ai-constitution` explicitly excludes
persona. Placing SOUL.md in the CANONICAL orbit is the only assignment
consistent with the existing boundary contract — so there is no
conflict by construction.

### D-164-07 — SOUL.md is a hand-edited source, not a generated mirror

SOUL.md is edited by hand (like principles.md / CANONICAL.md), carries no
`DO NOT EDIT` header, and is not regenerated by sync_mirrors. Repo and
template copies are kept byte-identical (dogfood parity).

**Rationale**: It is a *source* in the SoT model, not a derived mirror.
Treating it as hand-edited matches principles.md exactly and keeps the
sync system's generated-vs-source boundary clean.

### D-164-08 — Value content sourced (model-agnostically) from the Anthropic model-spec

The four values are phrased using crisp one-liners distilled from
Anthropic's published model-spec (the "soul" document), translated to be
**host-LLM-agnostic** — no "Claude/Anthropic" framing, no
principal-hierarchy, no harm/WMD content. Concrete additions to SOUL.md:

- **Preamble:** values exist so the agent can reason to the right action
  when the rules don't cover the case — they are not themselves rules
  (mirrors the CANONICAL §0 "understand the goals" spirit).
- **#1 Pragmatic Helpfulness:** "an over-cautious or watered-down
  response is never 'safe' — failing to help is a real cost; treat the
  operator as a capable adult" (anti-paternalism).
- **#2 Honest & Direct:** "diplomatically honest, never dishonestly
  diplomatic; state calibrated confidence — no faked certainty in a fix;
  disagree when the evidence says so; vague-to-avoid-friction is
  cowardice."
- **#3 Collaborative Partner:** "voice concerns once, then respect the
  operator's decision and execute it their way" — the autonomy bound that
  keeps #2 from reading as insubordination.
- **Boundary line:** "hard limits (secrets, suppression, prohibitions)
  are the deterministic plane's job, not this file's — SOUL.md is the
  judgment layer above them" (reinforces D-164-06).

**Rationale**: The model-spec is the best-written articulation of the
exact values already chosen in D-164-03; reusing its phrasings raises
quality at near-zero cost. Stripping model-specific framing is mandatory
because SOUL.md is read by every IDE host (Codex, Gemini, Copilot,
Cursor), not just Claude — importing "Claude is trained by Anthropic"
would be a category error on a non-Claude host. The full 8000-word
source is a quarry, never loaded: SOUL.md lifts ~8 lines and stays ≤1
page (token-efficiency constraint of §0 Bootstrap loading).

### D-164-09 — ASCII value headers, no emoji

Value headers are plain ASCII matching the Operating Mindset /
principles.md numbered style (`### 1. Pragmatic Helpfulness` … `### 4.
Learn & Grow`). molty's emoji glyphs (⚡💎🤝🌱) are dropped.

**Rationale**: SOUL.md is read into model context every session, so emoji
are pure token waste with zero semantic gain; the sibling governance docs
(CONSTITUTION / CANONICAL / principles.md) are emoji-free, so glyphs would
break house style; and although the file is not stdout today, any future
CLI path that echoes it would hit the cp1252 glyph-crash lesson — ASCII
plants no landmine. The identity lives in the value names and one-liners,
not the glyphs (which only worked in molty's HTML/personal-brand medium).

## Risks

- **Tone clash on regulated installs.** *Mitigation:* candid-professional
  register, no sarcasm (D-164-03); content is plain prose an operator can
  hand-edit in their own install copy if needed (D-164-07).
- **SoT duplication with Operating Mindset / principles.md.**
  *Mitigation:* SOUL.md owns *values framing* only; it cross-references
  §10.1/§10.2/§7 rather than restating them, and mirrors carry a pointer
  not a copy (D-164-02, D-164-03).
- **Template-parity drift — install never receives SOUL.md** (the
  spec-161 failure mode). *Mitigation:* register SOUL.md in
  `test_template_tree_completeness` + `test_dogfood_parity`; plan must
  confirm the parity assertion fails without the template copy.
- **Decorative-doc risk — agent never reads it.** *Mitigation:* §0
  Bootstrap read-list wiring (D-164-05) is mandatory, not optional.
- **Anonymity violation** (Prohibition #5). *Mitigation:* framework-voice,
  second-person "the operator", zero names (Non-Goals).
- **Root-doc count / surface-parity tests may assert on root markdown
  set.** *Mitigation:* plan audits `tests/mirrors/test_count_parity.py`
  and `tests/architecture/test_surface_parity.py` for any root-file
  enumeration that a new SOUL.md would break, and updates expectations.
- **Model-specific framing leak** (D-164-08). The Anthropic model-spec
  quarry is Claude-specific; copied verbatim it breaks on a non-Claude
  host. *Mitigation:* SOUL.md content review asserts zero
  "Claude/Anthropic/principal-hierarchy" tokens; phrasings are about *the
  agent*, never *the model*.

## References

- doc: https://www.molty.me/ (inspiration — "soul" document for a personal AI)
- doc: .ai-engineering/reference/principles.md (the canonical-source + lean-mirror pattern SOUL.md reuses)
- doc: src/ai_engineering/templates/project/CANONICAL.md (pointer host + §0 Bootstrap read-list)
- doc: CONSTITUTION.md (boundary: AI-behaviour rules disclaimed → SOUL.md sits in CANONICAL orbit)
- doc: Anthropic model-spec / "soul" document (phrasing quarry for D-164-08; mined model-agnostically, never loaded)

## Open Questions

_None — all authoring decisions resolved._
