---
spec: spec-128
title: Context Layout Refactor — Stack-Based Overrides
status: approved
effort: large
---

# Context Layout Refactor — Stack-Based Overrides

## Summary

Current `.ai-engineering/contexts/{frameworks,languages}/` (29 files) and `.github/instructions/*.instructions.md` (17 files) duplicate content the model already knows from training. They restate generic React patterns, ASP.NET Core best practices, Python idioms, etc. — content the LLM has stronger priors for than any 200-line Markdown file. Loading them costs tokens, dilutes attention, and adds maintenance overhead while providing near-zero project-specific signal.

Apply KISS/DRY/YAGNI: delete training-redundant files, rename `adapters/` to `overrides/`, restructure to per-stack layout (`overrides/csharp-azure/`, `overrides/typescript-react/`). Each stack carries only project-specific deltas — what the model would not know without being told. Aligns with GitHub Copilot official guidance (Aug 2025): `copilot-instructions.md` suffices as Copilot baseline; `AGENTS.md` is the cross-agent SSOT; path-specific instructions are optional and meant for genuine project-specific exceptions.

## Goals

- Delete `.ai-engineering/contexts/frameworks/` (15 files) and `.ai-engineering/contexts/languages/` (14 files).
- Delete `.github/instructions/*.instructions.md` (17 files) at root and in `src/ai_engineering/templates/project/.github/instructions/`.
- Rename `.ai-engineering/adapters/` to `.ai-engineering/overrides/`.
- Restructure `overrides/` by stack (e.g., `csharp-azure/`, `typescript-react/`, `python/`, `go/`, `rust/`, `kotlin-android/`, `swift-ios/`).
- Refactor `scripts/sync_mirrors/core.py` Surface 6 — remove generation of `instructions/*.instructions.md`.
- Refactor `tools/skill_domain/standards.py` — remove explicit refs to 3 deleted instructions files.
- Refactor `tools/skill_app/deterministic_router.py` — resolve by stack instead of by separate language/framework lookups.
- Update telemetry taxonomy in `tools/skill_app/.../observability` — `{language, framework}` context classes become `{stack}`.
- Update tests: `tests/unit/test_framework_context_loads.py`, `tests/adapters/test_adapter_scaffolding.py`.
- Update 4 IDE mirrors (`.claude`, `.codex`, `.gemini`, `.github`) so all refs to deleted paths resolve.
- All hot-path budgets pass (pre-commit ≤1s, pre-push ≤5s, `/ai-commit` ≤1.5s, `/ai-pr` ≤8s).
- All eval gates pass (no regression vs baseline; `tests/integration/test_eval_regression_gate.py`).
- `hooks-manifest.json` regenerated and `--check` clean.

## Non-Goals

- Migrating generic content from deleted files into `overrides/`. Start fresh; only project-specific deltas survive.
- Adding new stacks beyond confirmed-needed set during this spec. Future stacks added separately.
- Redesigning Copilot integration. Keep `.github/copilot-instructions.md` (autogen Surface 8 from CLAUDE.md) and `AGENTS.md` as-is.
- Touching `CONSTITUTION.md`, governance hooks (`skill_lint`, layer isolation tests), or risk accumulator.
- Refactoring skill semantics. This spec only updates path references in skills/agents — no behavior change.
- Adding `dart`, `java`, `php` adapters. Those were a separate request; track as follow-up specs after this refactor lands.

## Decisions

- **D-128-01**: New directory name is `overrides/`, not `priors/`, `deltas/`, or keep `adapters/`. Rationale: `overrides/` explicitly captures intent — project-specific content that overrides the model's training-default assumptions. Other names tested in conversation; user confirmed `overrides/`.

- **D-128-02**: Bare-language tokens (`overrides/csharp/`, `overrides/typescript/`, `overrides/python/`, etc.), 7 stacks matching current adapters/. Rationale (revised after T-001 audit): composite tokens (`csharp-azure`) would break `tools/skill_app/deterministic_router.py` `_EXT_TO_STACK` extension inference (`.cs` → which composite?). Framework variants live as sections inside `overrides/<stack>/conventions.md` (e.g., `## Azure`, `## React` subsections). Easy migration to subdirectory layout (`overrides/csharp/azure/`) if expressiveness justifies it later.

- **D-128-03**: Hard delete + start fresh; no content migration into `overrides/`. Rationale: the hypothesis is that content in `contexts/{frameworks,languages}/` is training-redundant. Migration would preserve the redundancy. New `overrides/<stack>/` files are written from scratch only when concrete project-specific deltas are identified.

- **D-128-04**: Delete all 17 `.github/instructions/*.instructions.md`, including the 3 standalone files (`testing.instructions.md`, `markdown.instructions.md`, `sonarqube_mcp.instructions.md`). Rationale: research (see References) confirms GitHub Copilot does not require these files. `.github/copilot-instructions.md` + `AGENTS.md` provide sufficient instruction surface. If genuine project-specific exceptions emerge later, add files per GitHub's stated guidance ("Add `.instructions.md` files when you need different rules for different file types").

- **D-128-05**: Keep `AGENTS.md` as canonical SSOT for cross-agent rules. Rationale: official GitHub support since Aug 2025 (Copilot coding agent), JetBrains support since Mar 2026. Consumed by Copilot, Claude, Gemini, Codex.

- **D-128-06**: Keep `.github/copilot-instructions.md` (root) as Copilot's always-on baseline; keep Surface 8 in `sync_mirrors/core.py` that generates it from `CLAUDE.md`. Rationale: low cost, official Copilot recommendation, zero training-redundancy risk because content is project rules.

- **D-128-07**: Surface 6 in `sync_mirrors/core.py` (lang instructions generator) is removed entirely, not redirected. Rationale: KISS. `overrides/<stack>/` files are authored by humans for project-specific deltas; auto-generation defeats the point.

- **D-128-08**: Telemetry taxonomy collapses `{language, framework}` context classes into a single `{stack}` class. Rationale: stack is the new unit; separate classes for language vs framework no longer reflect the layout.

- **D-128-09**: Initial stack list = `python`, `typescript`, `go`, `rust`, `swift`, `csharp`, `kotlin` (7 stacks, bare-language tokens matching current `adapters/<lang>/` directories). Rationale: per T-001 audit, composite tokens break router; user adjudicated Option A.

- **D-128-10**: Create `overrides/_shared/` for cross-cutting refs (compliance-trace.md, observability `shared-framework` class, execution-kernel `team:` key). Rationale: avoids duplicating cross-stack content in 7 stack dirs.

- **D-128-11**: Manifest `providers.stacks` field accepts bare-language tokens. Composite tokens rejected to keep router simple (stdlib only).

## Plan Amendments (post-T-001 audit)

The following plan amendments were locked after the T-001 audit and ai-guard advisory:

- **AM-01 (Phase ordering)**: Invert plan Phase 4 (filesystem nuke) ↔ Phase 6 (IDE mirror ref updates). Mirror refs MUST be updated to point at `overrides/` BEFORE the filesystem nuke deletes the old paths. Rationale: ai-guard concern #1 — `.claude/skills/ai-review/handlers/lang-*.md` × 4 mirrors silently degrade if they reference deleted paths.

- **AM-02 (T-014 scope expanded)**: T-014 (`tools/skill_domain/standards.py` cleanup) must also resolve `LegacyRetirementStatus.BLOCKED` state for the `manual-instruction-families` family — either advance to `RETIRED` or remove the family entry. Rationale: ai-guard concern #2 — leaving BLOCKED status with deleted surfaces creates governance drift.

- **AM-03 (T-025 scope expanded)**: T-025 must include `.claude/agents/ai-build.md` lines 33–36 (and 4 IDE mirror equivalents in `.codex/agents/`, `.gemini/agents/`, `.github/agents/` — name variant: `build.agent.md`). Rationale: ai-guard warn #3.

- **AM-04 (T-006 prerequisite)**: Before T-006 baseline `/ai-eval`, run `ai-eng audit query "SELECT kind, COUNT(*) FROM events WHERE kind LIKE '%context%' GROUP BY kind"` to verify whether context_load events are emitted under any kind string. Rationale: ai-guard warn #4 — telemetry absence supports training-redundancy hypothesis but unverified.

- **AM-05 (Article V compliance)**: T-024/T-025 edit only `.claude/` (canonical source per Article V); T-026 propagates via `scripts/sync_mirrors/core.py`. Document in PR. Rationale: ai-guard info #5.

## Risks

- **R1: Telemetry taxonomy change breaks downstream consumers.** Mitigation: update `emit_declared_context_loads`, `tests/unit/test_framework_context_loads.py`, and any audit projections in the same spec. Add migration test asserting no `language` or `framework` class is emitted.

- **R2: 4 IDE mirrors (`.claude`, `.codex`, `.gemini`, `.github`) drift during refactor.** Mitigation: include `scripts/sync_mirrors/core.py` execution as a plan acceptance step; assert mirror parity test passes.

- **R3: Eval regression if model performance silently depended on the deleted content.** Mitigation: run `/ai-eval` before refactor (baseline) and after (post-change); abort and re-plan if regression exceeds the regression-gate threshold. `tests/integration/test_eval_regression_gate.py` enforces this.

- **R4: Hot-path budget regression from changes to skills or hooks.** Mitigation: hot-path budget tests in CI gate (`tests/perf/test_skill_lint_budget.py`); profile any failing hook before re-tuning.

- **R5: Hidden refs in skills/agents miss the rename.** Mitigation: full-repo grep audit before deletion (across all 4 mirrors); symbol search for `contexts/frameworks`, `contexts/languages`, `adapters/`, `instructions/`. Each ref classified: update / delete / keep with rationale.

- **R6: `hooks-manifest.json` stale after editing hook scripts.** Mitigation: run `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py`; gate on `--check` in CI.

- **R7: Router regression from stack-based resolve.** Mitigation: `tests/unit/router/test_deterministic_router.py` updated to cover stack resolution before code change (TDD). RED → GREEN.

- **R8: Spec-127 (47 skills, 9 orchestrators) referenced in manifest may have implicit deps on deleted paths.** Mitigation: manifest review during exploration phase; flag any skill whose declared context includes deleted paths.

## References

- doc: https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot
- doc: https://code.visualstudio.com/docs/copilot/customization/custom-instructions
- doc: https://github.blog/changelog/2025-08-28-copilot-coding-agent-now-supports-agents-md-custom-instructions/
- doc: https://github.blog/changelog/2025-11-12-copilot-code-review-and-coding-agent-now-support-agent-specific-instructions/
- doc: https://code.visualstudio.com/docs/copilot/customization/custom-agents
- doc: .ai-engineering/contexts/architecture-patterns.md
- doc: .ai-engineering/contexts/spec-schema.md
- doc: CLAUDE.md (governance hooks, runtime layer, hot-path discipline)

## Open Questions

- **Q1: Initial stack list for `overrides/`.** Proposed minimum: `csharp-azure`, `typescript-react`, `typescript-node`, `python`, `go`, `rust`, `kotlin-android`, `swift-ios`. Resolved during planning task T-002.
- **Q2: Should `overrides/_shared/` exist for cross-stack rules** (e.g., common security floor, MCP integration patterns)? Or duplicate per stack? Lean toward `_shared/` for genuinely cross-cutting; resolved during T-003.
- **Q3: Fate of current `adapters/<lang>/tdd_harness.md`, `security_floor.md`, `examples/` content** — the slim-first hypothesis says most is training-redundant. Resolved during T-004 (audit-and-classify pass before final write).
- **Q4: Manifest schema field for stack declaration.** Currently `providers.stacks: [python, react]`. Likely becomes `providers.stacks: [python, typescript-react]` (single composite token). Resolved during T-005.
