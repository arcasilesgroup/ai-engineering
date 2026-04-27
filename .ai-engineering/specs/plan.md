# Plan: spec-106 Skills Consolidation + Architecture Thinking + skill-creator Eval

**Spec ref**: `.ai-engineering/specs/spec.md` (status: approved, 2026-04-27 autonomous)
**Effort**: large
**Pipeline**: full (build + verify; cero guard tasks; verify+review en Phase 6)
**Phases**: 6
**Tasks**: ~75 (build: ~62, verify: ~13)
**Branch**: `feat/spec-101-installer-robustness` (umbrella; renamed at PR creation)
**TDD pattern**: cada commit bundla GREEN code (current phase) + RED tests (next phase) marked `@pytest.mark.spec_106_red`. CI runs `pytest -m 'not spec_105_red and not spec_106_red'` → green throughout. Phase 6 verifica zero markers residuales.

---

### Phase 1: execution-kernel.md + dispatch/autopilot/run delegation
**Gate**: `.claude/skills/_shared/execution-kernel.md` exists; 3 orchestrators delegate (no inline kernel); combined line reduction >=150; sync --check PASS; CI green.

- [x] T-1.1: Add `pytest.mark.spec_106_red` marker to `[tool.pytest.ini_options].markers` in `pyproject.toml` (agent: build)
- [x] T-1.2: Create `.claude/skills/_shared/execution-kernel.md` with canonical "dispatch agent per task → build-verify-review loop → artifact collection → board sync" flow extracted from current dispatch/autopilot/run overlap (agent: build)
- [x] T-1.3: Read `.claude/skills/ai-dispatch/SKILL.md`, identify the kernel section (Process steps), replace with delegation to `_shared/execution-kernel.md` (agent: build)
- [x] T-1.4: Read `.claude/skills/ai-autopilot/SKILL.md`, identify wave-execution kernel, replace with delegation reference (agent: build)
- [x] T-1.5: Read `.claude/skills/ai-run/SKILL.md`, identify backlog-executor kernel, replace with delegation reference (agent: build)
- [x] T-1.6: Verify `scripts/sync_command_mirrors.py` covers `_shared/` subdirectory; if not, extend to include (agent: build)
- [x] T-1.7: Run `uv run ai-eng sync` to regenerate IDE mirrors; confirm `_shared/execution-kernel.md` propagates to `.github/`, `.codex/`, `.gemini/` (agent: build)
- [x] T-1.8: Run `uv run ai-eng sync --check` and confirm exit 0 (agent: verify)
- [x] T-1.9: Write `tests/unit/test_kernel_extraction.py` (no marker, immediate GREEN) asserting (a) `_shared/execution-kernel.md` exists, (b) dispatch/autopilot/run SKILL.md contains string `_shared/execution-kernel.md`, (c) combined line count of 3 orchestrators decreased >=150 vs baseline (record baseline as constant) (agent: build)
- [x] T-1.10: Write `tests/integration/test_shared_handler_mirror.py` (no marker, immediate GREEN) asserting `_shared/execution-kernel.md` byte-equivalent across 4 IDE mirrors (agent: build)
- [x] T-1.11: Write RED test skeleton `tests/integration/test_plan_design_routing.py` marked, covering Phase 2 G-2 keyword detection + handler invocation (agent: build)
- [x] T-1.12: Write RED test skeleton `tests/unit/test_design_keyword_allowlist.py` marked, covering allowlist of UI keywords + false-positive cases + --skip-design override (agent: build)
- [x] T-1.13: Run `pytest -m 'not spec_105_red and not spec_106_red' --no-cov -q` and confirm PASS (delta vs spec-105 P8 baseline only +new GREEN tests) (agent: verify)
- [x] T-1.14: Stage and commit `feat(spec-106): Phase 1 GREEN execution-kernel + Phase 2 RED design-routing tests` (agent: build)

---

### Phase 2: design-routing handler + /ai-plan keyword detection
**Gate**: `.claude/skills/ai-plan/handlers/design-routing.md` exists; /ai-plan invokes handler at right step; --skip-design override works; design-intent.md emitted at known location; T-1.11/T-1.12 RED tests now PASS unmarked.

- [ ] T-2.1: Create `.claude/skills/ai-plan/handlers/design-routing.md` with: (a) keyword allowlist (page, component, screen, dashboard, form, modal, design system, color palette, typography, layout, ui, ux, frontend, react component, vue component, interface, mobile screen, responsive, accessibility), (b) detection logic (case-insensitive substring match against spec.md body), (c) routing to `/ai-design`, (d) emission to `.ai-engineering/specs/<spec-id>/design-intent.md` or fallback `.ai-engineering/specs/design-intent.md`, (e) `--skip-design` override behavior (agent: build)
- [ ] T-2.2: Modify `.claude/skills/ai-plan/SKILL.md` Process section to add step "Read spec.md; invoke design-routing handler if keywords match; if routed, ensure /ai-design output linked in plan.md under '## Design' section before task decomposition" (agent: build)
- [ ] T-2.3: Run `uv run ai-eng sync` to regenerate mirrors; confirm `.claude/skills/ai-plan/handlers/design-routing.md` propagates (agent: build)
- [ ] T-2.4: Run `uv run ai-eng sync --check` exit 0 (agent: verify)
- [ ] T-2.5: Write `tests/integration/test_plan_design_routing.py` body — fixture spec.md with UI keywords; assert handler detects + plan.md contains `## Design` section (agent: build)
- [ ] T-2.6: Write `tests/unit/test_design_keyword_allowlist.py` body — 10+ test cases for keyword detection (positive + false-positive + override) (agent: build)
- [ ] T-2.7: Remove markers from these 2 test files; confirm GREEN (agent: build)
- [ ] T-2.8: Write RED test skeleton `tests/integration/test_architecture_pattern_step.py` marked, covering Phase 3 G-3 `/ai-plan` reads architecture-patterns.md + records pattern in plan.md (agent: build)
- [ ] T-2.9: Write RED test skeleton `tests/unit/test_architecture_patterns_curated_list.py` marked, asserting >=10 patterns + each has when-to-use + when-NOT-to-use (agent: build)
- [ ] T-2.10: Run `pytest -m 'not spec_105_red and not spec_106_red'` and confirm PASS (agent: verify)
- [ ] T-2.11: Stage and commit `feat(spec-106): Phase 2 GREEN design-routing + Phase 3 RED architecture-patterns tests` (agent: build)

---

### Phase 3: architecture-patterns.md context + /ai-plan step
**Gate**: `.ai-engineering/contexts/architecture-patterns.md` exists with >=10 patterns; /ai-plan adds Architecture step; T-2.8/T-2.9 RED tests PASS.

- [ ] T-3.1: Create `.ai-engineering/contexts/architecture-patterns.md` with curated 10+ patterns. Each entry format: `## Pattern Name` + `**Description**:` (1-2 paragraphs) + `**When to use**:` (bullet list) + `**When NOT to use**:` (bullet list) + `**Example**:` (1-paragraph). Patterns: layered, hexagonal, CQRS, event-sourcing, ports-and-adapters, clean-architecture, pipes-and-filters, repository, unit-of-work, microservices, modular-monolith. Source: `https://skills.sh/wshobson/agents/architecture-patterns` (snapshot, manual curation) (agent: build)
- [ ] T-3.2: Modify `.claude/skills/ai-plan/SKILL.md` Process section to add step BEFORE task decomposition: "Read `.ai-engineering/contexts/architecture-patterns.md`. Identify fitting pattern for this spec. Record in `plan.md` under `## Architecture` section with justification. If none applicable, note 'ad-hoc' with explanation." (agent: build)
- [ ] T-3.3: Run `uv run ai-eng sync` to regenerate; confirm context propagates if mirror sync covers `.ai-engineering/contexts/` (else note: contexts may not need IDE-mirroring — they're consumed via path) (agent: build)
- [ ] T-3.4: Run `uv run ai-eng sync --check` exit 0 (agent: verify)
- [ ] T-3.5: Write `tests/unit/test_architecture_patterns_curated_list.py` body — assert 10+ headings, each with required subsections, words count > minimum threshold per section (agent: build)
- [ ] T-3.6: Write `tests/integration/test_architecture_pattern_step.py` body — fixture spec.md; run `/ai-plan` (or simulate); assert plan.md contains `## Architecture` section with non-empty pattern reference (agent: build)
- [ ] T-3.7: Remove markers from these 2 test files; confirm GREEN (agent: build)
- [ ] T-3.8: Write RED test skeleton `tests/integration/test_skill_audit_advisory.py` marked, covering Phase 4 G-4 `scripts/skill-audit.sh` execution + audit-report.json schema (agent: build)
- [ ] T-3.9: Write RED test skeleton `tests/unit/test_audit_report_schema.py` marked, asserting JSON schema (skill, result.score, result.reason fields) (agent: build)
- [ ] T-3.10: Run `pytest -m 'not spec_105_red and not spec_106_red'` and confirm PASS (agent: verify)
- [ ] T-3.11: Stage and commit `feat(spec-106): Phase 3 GREEN architecture-patterns + Phase 4 RED skill-audit tests` (agent: build)

---

### Phase 4: skill-audit.sh + audit-report.json contract
**Gate**: `scripts/skill-audit.sh` exists, advisory mode works (no CI block); emits `audit-report.json` with valid schema; T-3.8/T-3.9 RED tests PASS.

- [ ] T-4.1: Create `scripts/skill-audit.sh` advisory script per D-106-04 spec. Bash, `set -euo pipefail`. Iterate `.claude/skills/ai-*/SKILL.md`. For each, attempt `uv run ai-eng skill eval` (gracefully fail to `eval-failed` record if subcommand missing). Emit `audit-report.json` with array of `{skill, result: {score, reason}}` entries (agent: build)
- [ ] T-4.2: chmod +x `scripts/skill-audit.sh` (agent: build)
- [ ] T-4.3: Write `tests/integration/test_skill_audit_advisory.py` body — invoke `bash scripts/skill-audit.sh` via subprocess; assert exit 0 (advisory); assert `audit-report.json` created in cwd; assert JSON parsable (agent: build)
- [ ] T-4.4: Write `tests/unit/test_audit_report_schema.py` body — load fixture audit-report.json; assert schema (list of objects, each with skill+result.score+result.reason) (agent: build)
- [ ] T-4.5: Remove markers from these 2 test files; confirm GREEN (agent: build)
- [ ] T-4.6: Write RED test skeleton `tests/unit/test_skill_line_budget_post_cleanup.py` marked, covering Phase 5 G-5 >=400 line reduction across 47 skills (agent: build)
- [ ] T-4.7: Run `pytest -m 'not spec_105_red and not spec_106_red'` and confirm PASS (agent: verify)
- [ ] T-4.8: Stage and commit `feat(spec-106): Phase 4 GREEN skill-audit advisory + Phase 5 RED line-budget test` (agent: build)

---

### Phase 5: Restatement cleanup mechanical sweep across 47 skills
**Gate**: >=400 line reduction net across 47 skills; zero functional content removed; sync --check PASS; T-4.6 RED test PASS.

- [ ] T-5.1: Establish baseline: capture `wc -l .claude/skills/ai-*/SKILL.md` total before sweep; record in plan.md as `BASELINE_LINES` constant (agent: build)
- [ ] T-5.2: Identify common restatement patterns by sampling 5 skills (top verbose: ai-animation, ai-skill-evolve, ai-pr, ai-video-editing, ai-instinct). Document patterns in `.ai-engineering/specs/_history.md` for traceability (agent: build)
- [ ] T-5.3: Sweep 47 SKILL.md files batch 1 (ai-a* through ai-d*): replace explicit CLAUDE.md Don't restatements with one-liner reference per D-106-05 example (agent: build)
- [ ] T-5.4: Sweep batch 2 (ai-e* through ai-l*): same pattern (agent: build)
- [ ] T-5.5: Sweep batch 3 (ai-m* through ai-s*): same pattern (agent: build)
- [ ] T-5.6: Sweep batch 4 (ai-t* through ai-z*): same pattern (agent: build)
- [ ] T-5.7: Re-measure: capture `wc -l .claude/skills/ai-*/SKILL.md` total post-sweep; compute delta vs BASELINE_LINES (agent: verify)
- [ ] T-5.8: If delta < 400 lines, identify additional restatement patterns (gate-policy, manifest schema, session-governance) and apply targeted sweeps to reach >=400 (agent: build)
- [ ] T-5.9: Write `tests/unit/test_skill_line_budget_post_cleanup.py` body — assert post-cleanup total <= (BASELINE_LINES - 400) (agent: build)
- [ ] T-5.10: Remove marker from this test file; confirm GREEN (agent: build)
- [ ] T-5.11: Run `uv run ai-eng sync` to regenerate all IDE mirrors with cleaned skills (agent: build)
- [ ] T-5.12: Run `uv run ai-eng sync --check` exit 0; if fail → revert sweep + investigate (agent: verify)
- [ ] T-5.13: Run `pytest -m 'not spec_105_red and not spec_106_red'` and confirm PASS — pay special attention to existing skill-content assertion tests; update assertions if they reference removed restatement strings (agent: verify)
- [ ] T-5.14: Stage and commit `feat(spec-106): Phase 5 GREEN restatement cleanup sweep + mirror sync` (agent: build)

---

### Phase 6: verify+review convergence
**Gate**: `pytest -m 'spec_106_red'` collects 0 tests; coverage >=80% on new modules; ai-eng validate PASS; ai-eng sync --check PASS; lint/format clean; _history.md updated.

- [ ] T-6.1: Run `pytest -m 'spec_106_red' --collect-only` and confirm zero tests remain marked (agent: verify)
- [ ] T-6.2: Run `pytest -m 'not spec_105_red and not spec_106_red' --no-cov -q` full suite; confirm pre-existing failures only (test_doctor_remaining_branches + isolation flakes) — no spec-106 regressions (agent: verify)
- [ ] T-6.3: Run `uv run ai-eng validate` and confirm exit 0 (agent: verify)
- [ ] T-6.4: Run `uv run ai-eng sync --check` and confirm exit 0 (agent: verify)
- [ ] T-6.5: Run `uv run gitleaks protect --staged --no-banner` and `uv run pip-audit --strict` (gracefully accept if pip-audit network-failed); confirm zero findings introduced by spec-106 (agent: verify)
- [ ] T-6.6: Run `uv run ruff check` and `uv run ruff format --check` on full src/ + tests/; must pass (agent: verify)
- [ ] T-6.7: Run `uv run ty check src/` if available; note pre-existing diagnostics (out of scope) (agent: verify)
- [ ] T-6.8: Update `.ai-engineering/specs/_history.md` with spec-106 phase summary: commit SHAs + test counts + restatement reduction metrics + lessons (e.g., "_shared/ subdirectory works for shared handlers") (agent: build)
- [ ] T-6.9: Stage and commit `feat(spec-106): Phase 6 GREEN — verify+review convergence + history update` (agent: build)

---

## Dependencies (cross-phase)

- Phase 1 → Phase 2: shared kernel pattern established before design-routing reuses it.
- Phase 2 → Phase 3: design-routing handler in /ai-plan before architecture step adds another /ai-plan modification (avoid SKILL.md merge churn).
- Phase 3 → Phase 4: contexts populated before audit script eval (so eval has full surface).
- Phase 4 → Phase 5: audit identifies sub-threshold candidates before mechanical cleanup; Phase 5 sweep informed by audit output.
- Phase 5 → Phase 6: cleanup must be done before final verify+review (review evaluates final state).

## What this plan does NOT do

- No removal of orphan skills (NG-1).
- No hard-gate enforcement on audit threshold (NG-2; advisory only).
- No restructure of skill folder layout beyond `_shared/` addition (NG-3).
- No migration of legacy orchestrators outside dispatch/autopilot/run (NG-4).
- No auto-routing besides /ai-design (NG-5).
- No per-project architecture-patterns override (NG-6).
- No verify/review boundary changes (NG-7).
- No brainstorm-plan circular ref break (NG-8).
- No note/write/docs consolidation (NG-9).
- No explain/guide routing (NG-10).
- No PR creation (NG-11; final step after spec-106 done).
- No spec-101/spec-104/spec-105 production code changes outside what's required for kernel extraction (Phase 1).
