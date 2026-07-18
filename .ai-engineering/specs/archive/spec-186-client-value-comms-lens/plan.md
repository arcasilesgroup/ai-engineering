---
title: spec-186 — Client-Value Lens: stakeholder-legible communication — execution plan
spec: spec-186
status: draft
pipeline: full
execution_route:
  version: 1
  spec: spec-186
  executor: autopilot
  automation: assisted
  concern_count: 6
  estimated_files: 22
  reason: "Six coupled concerns (SSOT reference doc, dual-hook reinforcement rig, 5-skill adoption of the value block + question framing, a new blocking skill_lint check, manifest schema + level resolver, CHANGELOG) across ~22 files spanning installer twins, mirror regeneration, and a hooks-manifest re-pin. Multi-concern + broad surface + gated wave ordering (contract before the blocking gate) → autopilot with wave decomposition."
  safe_next_command: "/ai-autopilot"
---

## Design

Design-intent is PRE-SETTLED in brainstorm (D-186-01…D-186-10). `--skip-design`
rationale: scope (5 chain skills), default level (`full`), questions-and-reports
cadence, blocking-CI enforcement, reference-doc SSOT (not §10.9), the native
two-hook rig, and the carve-out list were all decided and operator-approved
during `/ai-brainstorm`.

Layered convention (SSOT doc → hook reinforcement → skill citations →
conformance gate). No new runtime component — the lens is a presentation
adapter over the existing report/question boundary (§10.8 Hexagonal). The
machine artifacts (spec schema, plan template, PR body, defect tables) are
untouched; the value block sits above them.

## Architecture

Pattern: **convention + conformance-gate** (ad-hoc within
`architecture-patterns.md`). One canonical writable datum
(`.ai-engineering/reference/value-lens.md`), reinforced by the two existing
hooks, cited by the 5 chain skills, and guarded by one blocking `skill_lint`
check. Env→manifest→default (`full`) level resolution mirrors caveman's
`readFlag` precedence.

### Wave ordering (gated)

Contract lands before the gate flips. Wave 1 writes the SSOT doc + an existence
test; Wave 2 wires the hooks; Wave 3 makes the 5 skills carry the block; Wave 4
turns the blocking gate ON (safe only after Wave 3) and adds config + CHANGELOG.
One single-concern PR per wave.

### Known install-twin / mirror gotchas (baked into tasks)

- Editing a hook script changes its sha → re-pin `.ai-engineering/state/hooks-manifest.json` (T-25) AND copy byte-identical to the installer template twin (T-24). No CI guards this twin parity.
- Editing `.claude/` skill files → run `ai-eng dev sync` to regenerate `.codex/ .agents/ .github` mirrors (T-36); editing a mirror directly fails surface-parity.
- Editing CANONICAL template → `ai-eng dev sync` regenerates `CLAUDE.md/AGENTS.md/.github` (T-14); never edit those mirrors directly.
- Adding a manifest top-level key silently drops unless a model field is added (root model is `extra="ignore"`) → T-45 adds `ValueLensConfig`.

---

## Phase 1 — SSOT datum + existence gate

- [ ] T-11 — RED: conformance test asserts the value-lens contract exists and is shaped
- Agent: build
- Files: tests/conformance/test_value_block.py (new)
- Principles applied: §10.5 TDD
- Patch (deterministic): none — asserts `.ai-engineering/reference/value-lens.md` exists and contains the 6 field headings (Bottom line / Why it matters / What's done / Risk / Next / Details) + a `Carve-out` section; RED because the doc is absent.
- Gate: pytest tests/conformance/test_value_block.py (RED — doc missing)

- [ ] T-12 — GREEN: author the value-lens SSOT reference doc
- Agent: build
- Files: .ai-engineering/reference/value-lens.md (new)
- Principles applied: §10.4 DRY, §10.1 KISS, §10.6 SDD
- Patch (deterministic): none (judgment) — author: the 6-field BLUF block with per-field caps (D-186-10); the `lite`/`full`/`ultra` audience ladder (D-186-02); the carve-out list (D-186-08: code, commits, patch hunks, security warnings, AC test conditions, gate verdicts, irreversible-action confirms stay precise); anti-verbosity guardrails (field caps, Lauchman two-question filter, inline-jargon rule, positive-concision phrasing); a one-paragraph "applies to questions AND reports" clause (D-186-03/04). No emoji, no machine paths.
- Gate: pytest tests/conformance/test_value_block.py::test_doc_exists_and_shaped (GREEN)

- [ ] T-13 — Add the CANONICAL §14-16 pointer row for value-lens.md
- Agent: build
- Files: src/ai_engineering/templates/project/CANONICAL.md:164-166
- Principles applied: §10.4 DRY (one pointer to the SSOT)
- Patch (deterministic):
```diff
   (security/integrity boundaries fail closed; plumbing fails open and must log).
+- **Client-Value communication** (stakeholder-legible reports + questions) →
+  [.ai-engineering/reference/value-lens.md](.ai-engineering/reference/value-lens.md)
+  (the 6-field value block, lite/full/ultra audience ladder, and carve-outs;
+  the 5 chain skills cite it, enforced by `tests/conformance/test_value_block.py`).
 
 <!-- ide-extras:start -->
```
- Gate: markdownlint clean; row present before the ide-extras fence

- [ ] T-14 — Regenerate root mirrors from CANONICAL
- Agent: build
- Files: CLAUDE.md, AGENTS.md, .github/copilot-instructions.md (generated — do not hand-edit)
- Principles applied: §10.4 DRY
- Patch (deterministic): none — run `ai-eng dev sync`
- Gate: tests/architecture/test_surface_parity.py green; skill_lint md_mirror check green

---

## Phase 2 — Dual-hook reinforcement rig

- [ ] T-21 — RED: test asserts the lens reminder rides UserPromptSubmit unconditionally + SessionStart injects the contract
- Agent: build
- Files: tests/unit/hooks/test_value_lens_injection.py (new)
- Principles applied: §10.5 TDD
- Patch (deterministic): none — asserts (a) UserPromptSubmit `additionalContext` contains the lens reminder EVEN when no skills rank (i.e. the pre-ranking early-return paths still emit it), (b) SessionStart emits `additionalContext` carrying the compact contract; RED because neither exists yet.
- Gate: pytest tests/unit/hooks/test_value_lens_injection.py (RED)

- [ ] T-22 — GREEN: emit the lens reminder unconditionally in the UserPromptSubmit hook
- Agent: build
- Files: .ai-engineering/scripts/hooks/runtime-progressive-disclosure.py:305-375
- Principles applied: §10.3 SOLID, §10.8 Hexagonal (presentation adapter)
- Patch (deterministic): none (judgment) — restructure `main()` so `additionalContext` is ALWAYS emitted for UserPromptSubmit: the one-line lens reminder fires unconditionally (currently 6 early-returns at :305,319,329,334,339,345 skip the emission), with the ranked-skill `hint` (:360-363) appended only when present. Single stdout JSON object per hook (do not double-write). Read the active level via the T-46 resolver. Stdlib-only; lazy-import `ai_engineering` per the hook convention.
- Gate: test_value_lens_injection UserPromptSubmit case GREEN; test_runtime_progressive_disclosure_node_fallback still green

- [ ] T-23 — GREEN: inject the compact contract at SessionStart
- Agent: build
- Files: .ai-engineering/scripts/hooks/runtime-session-start.py:98-113
- Principles applied: §10.3 SOLID
- Patch (deterministic): none (judgment) — add a `sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": <compact contract>}}))` before the `passthrough_stdin` at :113. FIRST verify `memory-session-start.py` (the canonical SessionStart runner) does not already emit `additionalContext` — if it does, add the block there instead to avoid a double stdout-JSON collision.
- Gate: test_value_lens_injection SessionStart case GREEN; test_runtime_session_start still green

- [ ] T-24 — Copy both edited hooks byte-parity to the installer template twin
- Agent: build
- Files: src/ai_engineering/templates/.ai-engineering/scripts/hooks/runtime-progressive-disclosure.py, src/ai_engineering/templates/.ai-engineering/scripts/hooks/runtime-session-start.py
- Principles applied: §10.4 DRY (twin parity)
- Patch (deterministic): none — `cp` each canonical hook over its template twin (byte-identical)
- Gate: `diff -q` both canonical/template pairs report identical

- [ ] T-25 — Re-pin the hooks-manifest sha
- Agent: build
- Files: .ai-engineering/state/hooks-manifest.json
- Principles applied: §10.5 TDD (integrity gate)
- Patch (deterministic): none — run `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py`
- Gate: `regenerate-hooks-manifest.py --check` exits 0; tests/unit/hooks/test_canonical_events_count.py (==11) green

---

## Phase 3 — Chain-skill adoption (report block + question framing)

- [ ] T-31 — ai-brainstorm: value block at report + question-framing rule at interrogation
- Agent: build
- Files: .claude/skills/ai-brainstorm/handlers/spec-review.md:81-90, .claude/skills/ai-brainstorm/handlers/interrogate.md:43-63, .claude/skills/ai-brainstorm/SKILL.md:70
- Principles applied: §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): none (judgment) — add a value-block emission citing `value-lens.md` at the Spec Review Summary + Step 9 STOP; add a question-framing rule (plain language, per-option trade-offs, why-it-matters) at Step 3 Ask Questions and the Questioning Rules block. Reference implementation: the `AskUserQuestion` used in this spec's own brainstorm.
- Gate: value_block check passes for ai-brainstorm

- [ ] T-32 — ai-plan: value block at the Step 12 report
- Agent: build
- Files: .claude/skills/ai-plan/SKILL.md:42, .claude/skills/ai-plan/SKILL.md:44-57
- Principles applied: §10.6 SDD
- Patch (deterministic): none (judgment) — emit the value block (citing `value-lens.md`) alongside `safe_next_command` at Step 12, before STOP.
- Gate: value_block check passes for ai-plan

- [ ] T-33 — ai-build: value block at Record Quality Outcome
- Agent: build
- Files: .claude/skills/ai-build/handlers/quality.md:205-214
- Principles applied: §10.6 SDD
- Patch (deterministic): none (judgment) — emit the value block at the `## Quality Outcome` write step (report, not the intermediate findings table).
- Gate: value_block check passes for ai-build

- [ ] T-34 — ai-autopilot: value block at the Transparency/Integrity Report
- Agent: build
- Files: .claude/skills/ai-autopilot/handlers/phase-deliver.md:16-25
- Principles applied: §10.6 SDD
- Patch (deterministic): none (judgment) — emit the value block within the `## Integrity Report` builder (Step 1 Build Transparency Report).
- Gate: value_block check passes for ai-autopilot

- [ ] T-35 — ai-pr: value block at PR body compose (Summary)
- Agent: build
- Files: .claude/skills/ai-pr/SKILL.md:83, .claude/skills/ai-pr/SKILL.md:111-113
- Principles applied: §10.6 SDD
- Patch (deterministic): none (judgment) — the PR body `## Summary` compose emits the value block (bounded; `summary:` frontmatter stays the deterministic PR input).
- Gate: value_block check passes for ai-pr

- [ ] T-36 — Regenerate skill mirrors from .claude
- Agent: build
- Files: .codex/, .agents/, .github/ skill mirrors (generated)
- Principles applied: §10.4 DRY
- Patch (deterministic): none — run `ai-eng dev sync`
- Gate: tests/architecture/test_surface_parity.py green

---

## Phase 4 — Blocking enforcement + config + CHANGELOG

- [ ] T-41 — RED: conformance test asserts the value_block check is BLOCKING for the 5 chain skills
- Agent: build
- Files: tests/conformance/test_value_block.py (extend)
- Principles applied: §10.5 TDD
- Patch (deterministic): none — assert a chain skill missing the block yields exit 1 from `skill_lint` (and that a non-chain skill is unaffected); RED until wired.
- Gate: pytest tests/conformance/test_value_block.py (RED)

- [ ] T-42 — GREEN: implement the value_block skill_lint check
- Agent: build
- Files: tools/skill_lint/checks/value_block.py (new)
- Principles applied: §10.3 SOLID
- Patch (deterministic): none (judgment) — mirror `checks/principles.py`: `RubricResult`-style return + `check_value_block_citation(skill_md)` + a driver that filters to the explicit 5-skill set {ai-brainstorm, ai-plan, ai-build, ai-autopilot, ai-pr} (NOT all `ai-*`, and NOT the CLAUDE.md §11 chain which differs — it includes ai-spec-draft, excludes ai-autopilot). Return CRITICAL when a target skill omits the `value-lens.md` citation.
- Gate: unit of the check GREEN for present/absent cases

- [ ] T-43 — Wire value_block into skill_lint CLI as a blocking check
- Agent: build
- Files: tools/skill_lint/cli.py:31, tools/skill_lint/cli.py:175, tools/skill_lint/cli.py:217-219, tools/skill_lint/cli.py:241-244, tools/skill_lint/cli.py:41-80
- Principles applied: §10.5 TDD, §10.7 Clean Code
- Patch (deterministic): none (judgment) — import + invoke in `main()`, add severity counters + summary line, and add a `value_block_results` branch to `_exit_code` that returns 1 on any CRITICAL (mirror the blocking `effort`/`md_mirror` branches at :70-77, NOT the advisory `principles` path at :67).
- Gate: T-41 blocking assertion GREEN; `skill_lint` self-run over the repo green

- [ ] T-44 — RED: test default_level resolves env → manifest → full
- Agent: build
- Files: tests/unit/config/test_value_lens_config.py (new)
- Principles applied: §10.5 TDD
- Patch (deterministic): none — assert precedence: `AIENG_VALUE_LENS_LEVEL` wins; else `manifest.value_lens.default_level`; else `full`; RED until model + resolver exist.
- Gate: pytest tests/unit/config/test_value_lens_config.py (RED)

- [ ] T-45 — GREEN: ValueLensConfig model + manifest.yml block
- Agent: build
- Files: src/ai_engineering/config/manifest.py:379, src/ai_engineering/config/manifest.py:408, .ai-engineering/manifest.yml:193
- Principles applied: §10.3 SOLID
- Patch (deterministic):
```diff
     performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
+    value_lens: ValueLensConfig = Field(default_factory=ValueLensConfig)
```
```diff
     fail_closed: false
+
+# Client-Value Lens default audience level (spec-186 D-186-02).
+# AIENG_VALUE_LENS_LEVEL env overrides this. One of: lite | full | ultra.
+value_lens:
+  default_level: full
```
  Plus (judgment) a `class ValueLensConfig(BaseModel): default_level: str = "full"` near the other block models in manifest.py.
- Gate: manifest validation green; ManifestConfig parses value_lens

- [ ] T-46 — GREEN: level resolver helper (env → manifest → full), shared by the hook + skills
- Agent: build
- Files: src/ai_engineering/value_lens.py (new; small pure helper)
- Principles applied: §10.4 DRY (one resolver, two consumers), §10.1 KISS
- Patch (deterministic): none (judgment) — `resolve_level() -> str` reading `AIENG_VALUE_LENS_LEVEL` then `ManifestConfig.value_lens.default_level` then `"full"`, validated against {lite, full, ultra}. Lazy-importable by the T-22 hook.
- Gate: test_value_lens_config precedence GREEN

- [ ] T-47 — CHANGELOG hard-adopt entry
- Agent: build
- Files: CHANGELOG.md:10
- Principles applied: §10.7 Clean Code
- Patch (deterministic):
```diff
 ### Breaking changes
 
+- spec-186: Client-Value Lens adopted across the 5 chain skills
+  (`/ai-brainstorm`, `/ai-plan`, `/ai-build`, `/ai-autopilot`, `/ai-pr`).
+  These skills now emit a fixed value block in every user-facing report and
+  question. Hard-adopt: no dual-tone toggle, no legacy verbose mode. The new
+  reference `.ai-engineering/reference/value-lens.md` is the contract; a
+  blocking `skill_lint` check fails if a chain skill omits it.
+
 - spec-183: Three stale CLI commands were removed (hard delete, no compat
```
- Gate: markdownlint clean

---

## Gate summary (Definition of Done → verifiable)

- [ ] `value-lens.md` exists + shaped (T-12) — tests/conformance/test_value_block.py
- [ ] Lens reminder rides UserPromptSubmit unconditionally + SessionStart injects contract (T-22/T-23) — tests/unit/hooks/test_value_lens_injection.py
- [ ] Hook twins byte-identical + manifest re-pinned + 11-event count intact (T-24/T-25) — regenerate-hooks-manifest.py --check, test_canonical_events_count
- [ ] All 5 chain skills carry the block + mirrors regenerated (T-31…T-36) — test_surface_parity
- [ ] Blocking check hard-fails on omission (T-42/T-43) — tests/conformance/test_value_block.py
- [ ] default_level resolves env→manifest→full (T-45/T-46) — tests/unit/config/test_value_lens_config.py
- [ ] CHANGELOG documents the hard-adopt (T-47)
- [ ] Carve-outs asserted: code/commits/patch/security/AC/verdict/confirm stay precise (T-12 doc + T-41 test)
