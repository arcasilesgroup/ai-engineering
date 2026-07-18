---
spec: spec-187
title: "Fleet Audit — Simplify + Model-Portability"
status: approved
effort: large
summary: "Simplify and portability-harden the whole skill/agent/.md fleet: blocking lints enforce Anthropic authoring limits + canonical-only edits, canonical tokens -16.9% (ceiling, D-187-12), prose->procedure, all dead surface hard-deleted — shipped full-fleet via /ai-autopilot."
---

# Fleet Audit — Simplify + Model-Portability

## Summary

The 54 skills, 19 agents, and canonical `.md` surface of `ai-engineering` are
powerful but verbose, prose-heavy, and quietly Claude-Code-shaped in ways that
degrade on open-weight models. ~78% of the repo's `.md` (176k of 226k lines) is
generated mirror duplication from one `.claude/` canonical source; the session
routing tax alone is ~6,412 tokens of `description:` fields; 44/54 skills carry
an identical 22-line `## Examples` block; three documented behaviors
(`--consume`, `AIENG_MODEL_TIER`, `overrides/<stack>/debug.md`) do not exist;
14 `deprecated:true` forwarder stubs violate the repo's own hard-delete rule;
and 10 runbooks plus a reference triad are orphaned. This exact audit has been
drafted five times and never shipped because no attempt became an executable
spec. This spec makes the fleet simpler, more deterministic (prose → numbered
procedure), single-sourced, and structurally portable — enforced by lints so
regression is a red gate — and hard-deletes the dead surface (its own five
predecessor drafts, three fictional references, legacy stubs) plus two
enumerated live-content scope cuts. No IDE surface and no OS is dropped.
Delivered full-fleet via `/ai-autopilot`.

## Goals

- Cut the canonical token footprint versus a W1 `token-baseline` snapshot, with
  **100% of existing conformance / parity / count-gate tests green**. **Achieved
  −16.9%** (143,566 → 119,336 tokens; ~−30k lines fleet-wide across mirrors).
  The original ≥25% target proved unreachable without capability loss — an
  evidence-backed finding (D-187-12): five successive aggressive passes showed
  diminishing returns (+1.7k → +3.6k → +0.7k tokens), and the ~8000-test
  contract web reds on any core-content cut, so the remaining gap lives in
  load-bearing Workflow steps / contract tables / decision records. −16.9% is
  the capability-preserving ceiling, honoring "igual de potente o más".
- Land three lints — **portability**, **structure/procedure**, **token-budget**
  — warn-only in W1, flipped to **blocking-green** by W5.
- Enforce the Anthropic authoring contract fleet-wide: every `description:` is
  third-person "what + when" under the 1,024-char cap; every `name` ≤64 chars
  with no reserved words; every SKILL.md body <500 lines; references one level
  deep; TOC on any reference file over 100 lines.
- `grep` returns **0** for `--consume`, `AIENG_MODEL_TIER`,
  `overrides/<stack>/debug.md`, and `deprecated:true` stubs anywhere in the repo.
- Delete genuinely-dead surface (5 predecessor drafts, 3 fictional refs, the 6
  zero-inbound `reviewer-*` flat stubs per surface, non-consumer-shipped orphan
  runbooks) **plus** the two enumerated deliberate scope cuts (reference triad,
  `ai-analyze-permissions`) — each with its guard/installer tests and count-gates
  updated to the new **correct** value in the same change; 0 broken links, 0
  dangling refs, 0 accidental orphans remaining.
- Canonical prose carries no un-gated model-family assumption; a documented
  tool-name mapping table covers the open-weight families; `AGENTS.md`'s
  portable entry point carries a hook/hot-path pointer.
- **Surface/OS preservation** — all 6 IDE surfaces (Claude Code, Codex, Copilot,
  OpenCode, Cursor, Antigravity) and all 3 OSes (Windows/macOS/Linux) retain
  support; the only reductions are the two enumerated scope cuts above (D-187-09).
- Every structural rule above is backed by a test/lint so drift cannot land
  without a visible red gate.

## Non-Goals

- **No live open-weight model execution or eval runs** this cycle — the
  portability bar is structural neutrality, lint-enforced only.
- **No new IDE mirror families** (`.kimi/`, `.glm/`, …) — canonical is made
  neutral; the mirror tree is not widened.
- **No accidental surface/OS/skill loss** — the 6 IDE surfaces and 3 OSes stay
  supported; parity / OS-matrix / count gates are updated only to reflect the
  enumerated deletions, NEVER loosened to permit an un-enumerated reduction
  (D-187-09).
- **No `CHANGELOG.md` rewrite** (append-only history, not a living doc).
- **No Python behavior changes** beyond what dead-reference/skill deletion
  forces (deleting guard tests, updating count-gates).
- **Not building** the `overrides/<stack>/debug.md` feature — the references are
  deleted; the feature was never built (`spec-135` decision was hard-delete).
- No live-model behavioral benchmark for any family, MiMo included.

## Decisions

### D-187-01 — Deliver full-fleet as one wave-gated spec via `/ai-autopilot`
**Choice:** All five waves (audit+gates → skills → agents → docs+cross-link →
portability+block) ship under this single spec, decomposed by `/ai-autopilot`
into sub-specs + a dependency DAG with a per-wave gate, rather than a
spine-first or two-spec split.
**Rationale**: The five predecessors died as *briefs that never became specs*.
The executability leap is precisely turning this into one approved, wave-gated
spec that autopilot decomposes and gates wave-by-wave — that structure is the
anti-death mitigation, not the scope reduction. Operator selected this shape
over spine-first and split alternatives.

### D-187-02 — North-star is a composite metric, not a single number
**Choice:** Success = verbosity cut (≥25% canonical tokens) **and** determinism
(structure lint) **and** dead-surface removal, all three, not any one alone.
**Rationale**: The operator explicitly kept all three objectives. 25% is
achievable from Examples collapse + description contract + dead-surface purge
without touching capability; mirror-tree savings ride along ~6–7× for free.

### D-187-03 — Portability via canonical neutrality + documented tool-name map, no new mirror dirs
**Choice:** Make canonical prose model-neutral and document a tool-name mapping
table (Kimi/GLM/DeepSeek/Qwen/MiMo) inside `scripts/sync_mirrors/`; add no new
mirror directories.
**Rationale**: YAGNI until a real open-weight harness exists; new mirror dirs
would widen the 78% duplication this spec is shrinking. A structural lint is
deterministic and cheap, matching the no-live-runs bar.

### D-187-04 — Hard-delete via a shipping-aware gate; two enumerated live-content cuts
**Choice:** Two buckets, each hard-deleted, no deprecation:
(A) **Genuinely dead** — 5 predecessor drafts; `--consume` / `AIENG_MODEL_TIER` /
`overrides/<stack>/debug.md` reference prose; the 6 zero-inbound `reviewer-*`
flat forwarder stubs per surface; orphan runbooks NOT shipped to consumers. Gate:
**zero-inbound AND not-consumer-shipped AND not-surface-present**, reconfirmed at
delete time.
(B) **Enumerated deliberate scope cuts** (live content the operator chose to
remove) — the reference triad (`engineering-standards.md`, `harness-adoption.md`,
`harness-engineering.md`) plus its installer-contract test (`test_phases.py:175`),
and `ai-analyze-permissions` across all 5 install surfaces plus its guard tests +
count-gates. The `verifier-deterministic` flat stub is deleted ONLY after the
canonical ai-verify handler + `translate_refs` are retargeted to
`internal/verifier-deterministic.md`, so regeneration yields no dangling ref.
Every deletion updates its tests/count-gates to the new **correct** value — never
loosens a surface/OS/parity gate (D-187-09).
**Rationale**: Operator directive ("directamente fuera", no deprecation) +
`CLAUDE.md` §13.3. Adversarial verification (spec-187 surface/OS pass) DISPROVED
the original 'orphan' premise for two targets: the reference triad is
consumer-shipped + `test_phases.py`-tested, and `ai-analyze-permissions` is a live
Claude-Code skill on 5 surfaces — a link-only 'zero-inbound' gate would silently
remove supported content. The shipping-aware gate keeps bucket A safe and forces
bucket B to be explicit, enumerated, and operator-chosen.

### D-187-05 — Canonical-only edits; mirrors are regenerated, never hand-edited
**Choice:** Every rewrite happens in `.claude/` canonical +
`src/.../templates/CANONICAL.md`; `scripts/sync_mirrors/core.py` regenerates all
mirror families; no mirror file is ever edited by hand.
**Rationale**: `CLAUDE.md` §13.7 SSOT-per-datum; 78% of the surface is derived.
Hand-editing mirrors is the drift/formatter-brick failure class already recorded
in the project memory corpus.

### D-187-06 — Enforce the Anthropic authoring contract as lints
**Choice:** Description = third-person what+when ≤1024 chars; name ≤64 chars, no
reserved words; body <500 lines; refs one level deep; TOC on 100+-line refs;
`## Examples` collapses to at most one canonical example or moves to
`references/`.
**Rationale**: These are Anthropic's own published thresholds and the exact
levers a fleet audit should pull; encoding them as lints makes drift a red gate
(§10.5 TDD) instead of a review opinion.

### D-187-07 — Lints ship warn-only first, flip to blocking last
**Choice:** Portability / structure / token-budget lints run warn-only in W1 and
flip to blocking in W5.
**Rationale**: Avoids a big-bang red CI on day one; false-positives get tuned
against the real corpus before the gate becomes hard.

### D-187-08 — MiMo declared untested
**Choice:** MiMo portability is covered structurally by the neutrality lint but
declared unverified; no live-behavior claim is made.
**Rationale**: No primary portability source for MiMo surfaced in research;
honest scoping beats an unbacked guarantee.

### D-187-09 — Surface/OS-preservation invariant
**Choice:** No currently-supported IDE surface (Claude Code, Codex, Copilot,
OpenCode, Cursor, Antigravity) and no OS (Windows/macOS/Linux) loses support
through this spec. The only support reductions are the two enumerated deliberate
cuts in D-187-04 bucket B. All reductions are explicit; there is no accidental or
silent surface/OS/skill loss. Parity, OS-matrix, and count gates are updated only
to reflect enumerated deletions — never relaxed to permit an un-enumerated
reduction.
**Rationale**: The operator's explicit requirement is to keep "support for what
we deliver today." Verification showed the delete plane could otherwise trade
support for token savings because the guard tests were declared mutable; this
invariant is the hard boundary that stops the simplification from becoming a
regression.

### D-187-10 — New lints honor the Windows cp1252 safe-output posture
**Choice:** The portability / structure / token-budget lints (and any new CLI
output) emit pure ASCII on non-tty / raw streams, with glyphs only via the Rich
styled path — matching the existing `cli_ui.py` / `session_bootstrap.py` posture.
**Rationale**: Cross-OS verification confirmed the shipped product hardens Windows
cp1252 consoles; a new lint printing `◈`/`→` to a non-tty stream would crash
install-smoke on Windows (a recorded failure class). Deterministic ASCII keeps the
tri-OS guarantee (D-187-09).

### D-187-11 — Recalibrate the skill rubric to the new authoring standard
**Choice:** The `tools/skill_domain/rubric.py` grade rubric (+ its conformance
tests) enforced the retired M1/M2 standard and conflicts with D-187-06. Three
aligned changes: (a) `rule_6` — one canonical example is OK (was ≥2; the ≥2 rule
rewarded the identical 22-line double-example boilerplate the audit found in
44/54 skills); 0 examples is a visible INFO, never penalised. (b) `rule_1` —
sanctioned framework frontmatter (`effort`, `model_tier`, `argument-hint`,
`tags`, `requires` — all already in `_TOLERATED_EXTRA_FIELDS`) is INFO
regardless of count; penalising the *count* of fields the rubric tolerates by
*name* was internally inconsistent. (c) `rule_5` — `Quick start` dropped from
required sections (redundant with the description under the leaner standard);
`Workflow` / `Examples` / `Integration` stay required.
**Rationale**: spec-187 redefines what a good skill looks like (D-187-06), so
the gate that enforces the old shape must move with it — this is the spec doing
its job, not loosening a gate to hide a defect. Genuinely-substandard skills
still surface: real MAJOR/CRITICAL issues (missing `Workflow`, over-long bodies,
anti-patterns) remain blocking, and the change is honest — it left ai-pr at a
legitimate lower grade until its real content issues were addressed, not zeroed
out. Overall rubric health improved under the same gate (principles MAJOR 25→8,
pairs 9→5, Grade-C 2→0).

### D-187-12 — Token target revised to the capability-preserving ceiling (−16.9%)
**Choice:** Goal-1's ≥25% canonical-token cut is revised to the achieved
**−16.9%** (143,566 → 119,336). The composite north-star (D-187-02) is otherwise
fully met: determinism (prose→procedure, structure lint blocking), dead-surface
removal, portability, and SSOT all delivered.
**Rationale**: The 25% was set before the baseline existed. An audit + five
successive aggressive simplification passes (W-waves, reach-25, smart framing
removal, untapped-.md, agents/rulebook deep) established that the canonical
surface is denser than raw line-counts implied — most reference "headroom" is
load-bearing tables / decision records / schema contracts, and the fleet's
~8000-test contract web reds on any core-content cut. Diminishing returns
(+1.7k → +3.6k → +0.7k tokens per pass) confirm −17% as the ceiling reachable
without deleting documented capability, which the spec forbids ("igual de
potente o más"). Reaching 25% would require an explicit override to cut
capability; the operator chose to ship the capability-preserving win. Real value
delivered beyond the %: ~−30k lines fleet-wide, all redundant framing removed,
stale defects fixed (skill count 54→53, ai-explore obsolete external-research
prose, runbook layer-count, duplicated sections), 3 blocking authoring lints, an
8-family portability tool-map, and a portable AGENTS.md entry — all 6 IDE
surfaces + tri-OS intact.

## Risks

- **This 6th attempt also dies unconsumed** — likelihood High, impact High.
  Mitigation: it is an approved wave-gated spec (not a brief), decomposed by
  `/ai-autopilot` with a gate per wave, single owner, and it deletes its own
  predecessors so there is no parallel draft to drift toward.
- **Touching `sync_mirrors` bricks consumer installs** (formatter/manifest
  class in the memory corpus) — Med / High. Mitigation: parity +
  hooks-manifest tests as wave gates; regenerate, never hand-edit.
- **Accidental surface/OS/skill loss, or a false-orphan deletion** — Med / High.
  (Verification already caught two false 'orphan' premises — the reference triad
  and `ai-analyze-permissions` are live/shipped.) Mitigation: the D-187-09
  invariant + the shipping-aware delete gate (zero-inbound AND not-consumer-shipped
  AND not-surface-present); bucket-B cuts are explicit and enumerated; gates are
  updated to correct values, never loosened.
- **Count-gate breakage from skill/section removal** — Med / Med. Mitigation:
  run full `tests/unit/{config,docs}` + `ai-eng check` every wave.
- **Portability/structure lint false-positives block benign prose** — Med / Med.
  Mitigation: warn-only in W1, tune, block in W5 (D-187-07).
- **MiMo portability unverifiable** — Low / Low. Mitigation: structural lint
  only, documented as untested (D-187-08).

## References

- doc: .ai-engineering/specs/drafts/fleet-audit-simplify-portability-brief.md
- doc: CLAUDE.md §13.3 (hard-delete, no shims) · §13.7 (SSOT per datum)
- doc: platform.claude.com Agent Skills — overview + authoring best-practices (description ≤1024 chars, body <500 lines, progressive disclosure)
- research: .ai-engineering/runtime/research/spec-187-fleet-audit.md

## Open Questions

- **Build vs buy the lints** — adopt external tools (`ctxlint`, `skills-check`,
  `promptfoo test-agent-skills`, `Vale`, `token-baseline`, `mdcompress`,
  `lychee`) vs write thin in-repo lints. Resolve in `/ai-plan` (implementation
  detail; recommendation: buy the mature link/prose layer, own the
  skill/portability lints).
- Per-runbook delete happens at delete time under the D-187-04 shipping-aware
  gate: a runbook shipped in `templates/.ai-engineering/runbooks/` is treated as
  live (kept, or an enumerated cut), not auto-deleted as an orphan.
