## spec-106 — Phase 5 restatement patterns identified

Phase 5 T-5.2 sample (top verbose: ai-animation, ai-skill-evolve, ai-pr, ai-video-editing, ai-instinct, ai-create, ai-eval, ai-slides, ai-media, ai-autopilot, ai-board-discover, ai-platform-audit, ai-pipeline, ai-test, ai-code, ai-verify, ai-review, ai-commit, ai-governance) — common restatement patterns to remove:

1. **Stack-context preamble redundancy**: Many skills include a "## Step 0: Load Stack Contexts / Follow `.ai-engineering/contexts/stack-context.md`. Apply loaded standards to all subsequent work." block. The first sentence alone references the file; the second sentence ("Apply loaded standards to all subsequent work") restates a CLAUDE.md (section 10) framework rule.
2. **CLAUDE.md Don't restatements**: ai-commit reiterates "NEVER uses `--no-verify`" and "NEVER pushes to `main`/`master`" (literally restated from CLAUDE.md Don't #1, #5).
3. **Quality gate body restatements**: `ai-test`, `ai-pr`, `ai-commit`, `ai-release-gate` re-list `coverage >= 80`, `cyclomatic <= 10` thresholds — these live in CLAUDE.md Quality Gates and `manifest.yml`.
4. **Hardcoded skill-list/agent-list/section-counter restatements**: skill markdown sometimes hard-codes counts (e.g., "47 skills", "10 agents", "14 stacks") instead of referencing `manifest.yml`.
5. **Verbose process-summary blocks**: Some skills duplicate the summary in Purpose/When-to-Use/Process headers. Redundant prose can collapse to one source.
6. **Decision-store / framework-events restatements**: skill files re-explain the canonical state-file paths and schemas already documented in CLAUDE.md "Source of Truth" + observability sections.
7. **Sync command restatements**: `python scripts/sync_command_mirrors.py` block repeated across ai-create, ai-skill-evolve, ai-platform-audit, etc., when one canonical reference suffices.

Phase 5 sweep policy: replace each restatement with one-liner reference (e.g., "Honors CLAUDE.md Don't rules (binding)") OR delete entirely when already covered by Process / Integration / external SOT, while preserving every Process step, Quick Reference, Common Mistakes, Integration, Handler-table, and Output-Contract section.

## spec-106 — Skills Consolidation + Architecture Thinking + skill-creator Eval

**Branch**: `feat/spec-101-installer-robustness` (umbrella; PR creation deferred per CLAUDE.md Don't #5).
**Phases**: 6. **Tasks closed**: ~75 (build + verify). **Cycle pattern**: each commit shipped GREEN code for the current phase plus RED tests (`@pytest.mark.spec_106_red`) for the next phase, mirroring spec-104/105.

**Phase commit SHAs**:
- P1 `2cb5b4ab` — `_shared/execution-kernel.md` extracted; dispatch/autopilot/run delegate; `sync_command_mirrors.py` extended for `_shared/`; 4 RED test scaffolds for design-routing.
- P2 `9f942c6a` — `ai-plan/handlers/design-routing.md` (markdown-only handler) with keyword allowlist + `--skip-design` override; `## Design` linked from plan.md; design-keyword tests GREEN; architecture-pattern RED scaffolds.
- P3 `19e699fa` — `.ai-engineering/contexts/architecture-patterns.md` curated (11 patterns: layered, hexagonal, CQRS, event-sourcing, ports-and-adapters, clean-architecture, pipes-and-filters, repository, unit-of-work, microservices, modular-monolith); `/ai-plan` adds Architecture step before task decomposition; pattern-step tests GREEN; skill-audit RED scaffolds.
- P4 `246966cf` — `scripts/skill-audit.sh` advisory (threshold 80, never CI-blocking); `audit-report.json` schema (skill, result.score, result.reason); skill-audit tests GREEN; line-budget RED scaffold.
- P5 `7740b1b1` — restatement cleanup sweep across 47 skills (4 batches a-d, e-l, m-s, t-z); BASELINE_LINES = 5736 → POST_LINES = 5335 (DELTA = 401 lines, target ≥ 400 met); 35 skills swept, 12 already minimal; line-budget test GREEN; mirror sync regenerated.
- P6 `dce384df` — verify+review convergence; mirror gap fix for `architecture-patterns.md` (template mirror added at `src/ai_engineering/templates/.ai-engineering/contexts/architecture-patterns.md`); `_history.md` updated.

**Key metrics**:
- Restatement reduction: **5736 → 5335 (-401 lines, -7.0%)** across 47 skills, 35 swept, zero functional content removed.
- Architecture patterns curated: **11** with When-to-use + When-NOT-to-use + Example per pattern (`.ai-engineering/contexts/architecture-patterns.md`).
- Skill audit script: `scripts/skill-audit.sh` advisory mode (exit 0 always), threshold 80, `audit-report.json` emitted with parsable schema.
- Shared kernel extraction: `.claude/skills/_shared/execution-kernel.md` byte-equivalent across `.github/`, `.codex/`, `.gemini/` mirrors via extended `sync_command_mirrors.py`.
- Design routing: markdown-only handler at `.claude/skills/ai-plan/handlers/design-routing.md` with 19 UI keywords; emits to `.ai-engineering/specs/<spec-id>/design-intent.md`; `--skip-design` override.
- `pytest -m 'not spec_105_red and not spec_106_red' --no-cov`: **4735 passed, 1 failed, 2 skipped, 1 xpassed** (700s). The 1 failure (`test_doctor_remaining_branches::test_coverage_closure.py`) is **pre-existing** — verified failing on parent commit 71d38d9d (spec-104 head) before spec-106 began. Not introduced by spec-106.
- `pytest -m 'spec_106_red' --collect-only`: **0 tests** (zero residual markers).
- `ai-eng validate`: **PASS** (7/7 categories) after architecture-patterns.md mirror added.
- `ai-eng sync --check`: **PASS** (mirrors in sync).
- `ruff check` + `ruff format --check`: **PASS** (468 files formatted; all checks passed).
- `gitleaks protect --staged`: **0 leaks**.
- `pip-audit`: 1 known vulnerability (pip CVE-2026-3219) — pre-existing, accepted via spec-105 P8 risk-acceptance precedent. Not introduced by spec-106.
- `ty check src/`: 3 pre-existing diagnostics (cpp probe + watch-loop literal + unused type-ignore) — out of spec-106 scope.

**Lessons learned**:
1. **`_shared/` subdirectory works for shared handlers**: extracting common orchestration kernel to `.claude/skills/_shared/execution-kernel.md` and delegating from dispatch/autopilot/run cut combined orchestrator surface ≥150 lines without coupling. `sync_command_mirrors.py` extended to include `_shared/` propagates byte-equivalent across 4 IDE mirrors.
2. **Markdown-only handlers are valid for routing**: `ai-plan/handlers/design-routing.md` performs keyword detection + emission via prose instructions (no Python execution). Pattern works for any keyword-driven downstream skill routing.
3. **Mirror-sync validator is separate from `ai-eng sync`**: adding canonical files under `.ai-engineering/contexts/` requires a parallel copy at `src/ai_engineering/templates/.ai-engineering/contexts/` for `validate` mirror-sync to pass. `sync` PASSes without the template mirror because it operates on `.claude/.codex/.gemini/.github/` IDE pairs — the governance template mirror is independent. P6 surfaced this gap and added the missing template copy.
4. **Restatement sweep yields linear gains**: identifying 7 restatement patterns (stack-context preamble, CLAUDE.md Don't restatements, quality-gate body restatements, hardcoded counters, verbose process summaries, decision-store paths, sync-command restatements) and sweeping 4 alphabetical batches reliably hits ≥400-line target. Functional content (Process, Quick Reference, Common Mistakes, Integration, Handler tables, Output Contracts) preserved.
5. **Advisory script vs CI gate**: `scripts/skill-audit.sh` deliberately exits 0 even with sub-threshold skills — D-106-04 design choice keeps skill quality visible without blocking releases. CI-blocking variants reserved for future spec if signal proves consistently actionable.
6. **Pre-existing failure inventory is stable**: `test_doctor_remaining_branches` (1 failure) verified failing on parent commit 71d38d9d (spec-104 head) and on every spec-106 phase commit. Same 6-flake set documented in spec-105 (P8 lesson 2). Spec-106 inherits the inventory unchanged; no spec-106 regression introduced.
