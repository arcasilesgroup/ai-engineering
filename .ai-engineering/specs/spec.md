---
spec: spec-106
title: Skills Consolidation + Architecture Thinking Integration + skill-creator Eval Loop
status: approved
effort: large
refs:
  - .ai-engineering/notes/adoption-s4-skills-consolidation-architecture.md
  - .ai-engineering/specs/spec-105.md
---

# Spec 106 — Skills Consolidation + Architecture Thinking Integration

## Summary

47 skills accumulan ~40-60% restatement de framework rules ya documentadas en `CLAUDE.md`, hot-spots de duplicación entre orchestrators (`dispatch`/`autopilot`/`run` ~35% kernel-overlap; `ai-commit ⊂ ai-pr` ~50%), `/ai-design` es opt-in only (no se enruta automáticamente desde `/ai-plan` cuando el spec contiene UI), architecture-patterns thinking tiene **0 hits** en toda la base de skills, y dos orphans (`/ai-analyze-permissions`, `/ai-video-editing`) acumulan inbound-zero. Top 5 skills más verbose (`ai-animation` 243 líneas / ~55% restatement, `ai-skill-evolve` 213 / ~60%, `ai-pr` 221 / ~50%, `ai-video-editing` 200 / ~65%, `ai-instinct` 179 / ~45%) cargan ~40-60% de líneas que solo restatean reglas que el agente ya recibe via CLAUDE.md preload. Resultado: cada gate-trigger del agente paga el costo de tokens duplicados, mirror sync (4 IDEs) propaga el peso multiplicativo, y nuevos skills heredan el patrón restatement-first. spec-106 ataca los 5 issues entrelazados con: (1) extract `_shared/execution-kernel.md` consumido por dispatch/autopilot/run (elimina ~35% kernel-overlap), (2) wire `/ai-design` routing en `/ai-plan` por keyword-detect (con `--skip-design` override) → autoroute UI specs hacia design-intent gen antes de task-decomposition, (3) crear `contexts/architecture-patterns.md` (curated de skills.sh/wshobson/agents/architecture-patterns) + step en `/ai-plan` "Identify fitting pattern" (on-demand load — NO siempre cargado), (4) `scripts/skill-audit.sh` advisory script que ejecuta skill-creator eval per-skill con threshold 80, warning-only en primera iteración, hard-gate cuando >90% skills cumplen, (5) restatement cleanup mechanical sweep eliminando líneas que duplican CLAUDE.md Don't / framework rules, target ≥400 líneas removidas distribuidas across 47 skills. Mirror sync (`.github/`/`.codex/`/`.gemini/`) regenera tras cada skill edit. Beneficio medible: tokens-per-trigger reducidos 30-40%, /ai-plan inherently architecture-aware en specs nuevas, /ai-design no requiere descubrimiento manual, audit-script identifica skills sub-threshold como refactor candidates con justification trazable.

## Goals

- G-1: `.claude/skills/_shared/execution-kernel.md` exists; `/ai-dispatch`, `/ai-autopilot`, `/ai-run` SKILL.md cada uno reference it via "Calls" section; combined line-count reduction ≥150 líneas across los 3 orchestrators. Verificable por `tests/unit/test_kernel_extraction.py` que asserts inclusion + line budget.
- G-2: `/ai-plan` auto-detects UI specs por keywords (`page`, `component`, `screen`, `dashboard`, `form`, `modal`, `design system`, `color palette`); routes through `/ai-design` BEFORE task decomposition; emits `design-intent.md`; supports `--skip-design` override. Verificable por `tests/integration/test_plan_design_routing.py`.
- G-3: `.ai-engineering/contexts/architecture-patterns.md` exists with ≥10 patterns (layered, hexagonal, CQRS, event-sourcing, ports-and-adapters, clean-architecture, pipes-and-filters, repository, unit-of-work, plus); `/ai-plan` SKILL.md step "Identify fitting pattern" added BEFORE task decomposition; pattern recorded in `plan.md` under `## Architecture` section. Verificable por `tests/unit/test_architecture_pattern_step.py`.
- G-4: `scripts/skill-audit.sh` exists, advisory mode (warning-only); reads each `.claude/skills/ai-*/SKILL.md`, evaluates via skill-creator eval rubric (4 dimensions: triggering-accuracy, boundary-clarity, verbosity, wire-integrity), threshold 80, emits `audit-report.json`; sub-threshold skills listed with refactor justification. Verificable por `tests/integration/test_skill_audit.py`.
- G-5: Restatement cleanup mechanical sweep across 47 skills removes ≥400 líneas (verified per file diff); zero functional content removed (only restatements of CLAUDE.md Don't rules / framework conventions). Verificable por `tests/unit/test_skill_line_budget_post_cleanup.py`.
- G-6: `ai-eng sync --check` PASS post-changes (mirror parity preserved across `.claude/`, `.github/`, `.codex/`, `.gemini/`).
- G-7: All Phase 7 G-13 from spec-105 still passes (no `(spec-105)` forward-refs reintroduced; no `(spec-106)` forward-refs introduced).
- G-8: Cross-IDE parity preserved: shared handlers (execution-kernel.md, design-routing.md if added) propagated to mirror IDE installs.
- G-9: 0 secrets, 0 vulnerabilities, 0 lint errors introduced; pre-existing failures unchanged.
- G-10: Coverage ≥80% on new modules (skill-audit.sh wrapper if any, design-routing handler if Python-backed).

## Non-Goals

- NG-1: Removal of orphan skills (`/ai-analyze-permissions`, `/ai-video-editing`) — out of scope spec-106. Sweep handled by future skill-deprecation spec.
- NG-2: Hard-gate enforcement on skill-audit threshold. spec-106 ships advisory-only; hard-gate landed when ≥90% skills cumplen (out-of-scope).
- NG-3: Restructure of skill folder layout. Skills stay at `.claude/skills/ai-*/SKILL.md`. Shared handlers go under `.claude/skills/_shared/` (new directory).
- NG-4: Migration of OTHER orchestrators (e.g., legacy `/ai-skill-evolve`, `/ai-create`). Only dispatch/autopilot/run (the 3 with measured ~35% overlap).
- NG-5: Auto-routing to other skills besides `/ai-design`. spec-106 wires only design routing per the note; future routing (e.g., `/ai-security` for security specs) is separate work.
- NG-6: Custom architecture-patterns per project. spec-106 ships canonical curated list; per-project override out of scope.
- NG-7: Modification of `verify` vs `review` boundary. Per pitfall in note: "NO consolidar sin medir — cambiar routing puede confundir." Boundary stays.
- NG-8: Touching `brainstorm ↔ plan` circular reference (25% mutual). Note marks this as low priority; out of scope.
- NG-9: Note-vs-write-vs-docs consolidation (20%, low risk per note). Out of scope.
- NG-10: explain-vs-guide routing (30%, low priority per note). Out of scope.
- NG-11: PR creation in this spec. Branch consolidation + multi-spec PR is final step after spec-106 done.

## Decisions

### D-106-01: Execution kernel shared handler

Create `.claude/skills/_shared/execution-kernel.md` with the canonical "dispatch agent per task → build-verify-review loop → artifact collection → board sync" flow. Modify `.claude/skills/ai-dispatch/SKILL.md`, `.claude/skills/ai-autopilot/SKILL.md`, `.claude/skills/ai-run/SKILL.md` to **delegate** to this handler instead of inlining the kernel. Each orchestrator keeps only its unique pre/post wrapper logic.

**Rationale**: ~35% overlap measured. Extracting to a shared handler enforces DRY at the SKILL.md layer (orchestrators are governance code, not implementation). Mirror sync propagates via `scripts/sync_command_mirrors.py` already covers `.claude/skills/**/*.md` recursive — no changes to sync logic needed (verified). Kernel is read by agents at execution time, not preloaded — token cost amortized only when orchestrator actually invoked.

### D-106-02: Design routing via `/ai-plan` keyword detection

Add new handler `.claude/skills/ai-plan/handlers/design-routing.md` invoked from `/ai-plan` Process step "Detect UI/frontend keywords". Keywords trigger pre-decomposition routing through `/ai-design` and emit `design-intent.md`. Override flag `--skip-design` bypasses routing. Keyword allowlist (configurable in handler, NOT in manifest per LESSONS principle):

```
page, component, screen, dashboard, form, modal,
design system, color palette, typography, layout,
ui, ux, frontend, react component, vue component,
interface, mobile screen, responsive, accessibility
```

False-positive mitigation: keyword allowlist conservative; `--skip-design` available; design-routing handler emits explicit log line stating routing decision so user sees rationale.

**Rationale**: `/ai-design` opt-in only today means UI specs reach `/ai-dispatch` without design intent → developer pays late cost. Auto-routing + opt-out is the inverse-default that matches actual usage frequency (UI work is common in target audience). Handler-based (not skill-modification) keeps `/ai-plan` SKILL.md stable; routing logic lives where it can be tested in isolation. Conservative keyword list reduces false positives.

### D-106-03: Architecture patterns context (on-demand load)

Create `.ai-engineering/contexts/architecture-patterns.md` curated from `https://skills.sh/wshobson/agents/architecture-patterns`. Initial 10+ patterns: layered, hexagonal, CQRS, event-sourcing, ports-and-adapters, clean-architecture, pipes-and-filters, repository, unit-of-work, microservices, modular-monolith. Each pattern: 1-2 paragraph description + when-to-use + when-NOT-to-use + example.

`/ai-plan` SKILL.md adds Process step (BEFORE task decomposition):
> "Read `.ai-engineering/contexts/architecture-patterns.md`. Identify fitting pattern for this spec. Record in `plan.md` under `## Architecture` section with justification. If none applicable, note 'ad-hoc' with explanation."

Context loaded on-demand by `/ai-plan` only (NOT preloaded for every skill trigger) → token cost amortized.

**Rationale**: 0 hits on architecture-patterns / pattern-library across 47 SKILL.md is a structural gap. Adding pattern-thinking to `/ai-plan` surfaces architecture decisions at planning time (not post-hoc via `verifier-architecture`). On-demand load avoids inflating every prompt; only `/ai-plan` invocations pay the cost. Curated list from external reference balances completeness vs noise.

### D-106-04: skill-creator eval audit script (advisory)

Create `scripts/skill-audit.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
THRESHOLD=${THRESHOLD:-80}
OUTPUT=${OUTPUT:-audit-report.json}
echo "[]" > "$OUTPUT"
for skill in .claude/skills/ai-*/SKILL.md; do
    name=$(dirname "$skill" | xargs basename)
    score=$(uv run ai-eng skill eval "$skill" --threshold "$THRESHOLD" --json 2>/dev/null || echo '{"score":0,"reason":"eval-failed"}')
    jq --arg n "$name" --argjson s "$score" '. + [{"skill":$n, "result":$s}]' "$OUTPUT" > "$OUTPUT.tmp"
    mv "$OUTPUT.tmp" "$OUTPUT"
done
echo "Audit complete. Sub-threshold skills:"
jq -r '.[] | select(.result.score < '"$THRESHOLD"') | "\(.skill): \(.result.score)/\(.result.reason)"' "$OUTPUT"
```

Audit dimensions (per skill-creator rubric): triggering-accuracy (description specificity), boundary-clarity (when-NOT-to-use), verbosity (line count vs information density), wire-integrity (calls/called-by accuracy).

Mode: **advisory only** in spec-106 — emits `audit-report.json` and prints sub-threshold skills, does NOT block CI. Hard-gate landed in future spec when ≥90% skills cumplen.

If `ai-eng skill eval` subcommand doesn't exist yet, the script handles gracefully (emits `eval-failed` records) and the spec-106 deliverable shifts to "advisory script + JSON contract; CLI subcommand follow-up."

**Rationale**: Per LESSONS "Stable framework orchestration should not become per-project config by default" — skill quality is framework concern, not per-project. Advisory-first pattern gives users feedback signal without breaking adoption (legacy skills probably <80 initially). Threshold 80 from skill-creator default. Hard-gate timeline depends on real refactor cadence.

### D-106-05: Restatement cleanup mechanical sweep

Sweep all 47 `.claude/skills/ai-*/SKILL.md` for restatement patterns:
- Lines explicitly restating CLAUDE.md Don't rules ("NEVER --no-verify", "NEVER push to main", etc.)
- Lines re-explaining framework conventions already in `.ai-engineering/contexts/session-governance.md`
- Lines restating manifest fields documented in `manifest.yml` schema
- Lines restating gate-policy already in `contexts/gate-policy.md`

Replacement pattern (per note example):
```
# Before (per-skill restatement):
"NEVER uses --no-verify on any git command (respects CLAUDE.md Don't)."

# After (one-liner):
"Honors CLAUDE.md Don't rules (binding)."
```

Estimated savings: ~400 lines across 47 skills (note's analysis). Sweep is mechanical — the agent reads each skill, identifies restatement patterns, replaces with one-liner reference. NO functional content removed; only restatements with provable upstream source.

Validation: `tests/unit/test_skill_line_budget_post_cleanup.py` asserts net line reduction ≥400 across the 47 skill files. Per-file diff manually reviewed — no functional removal.

**Rationale**: Top 5 skills carry 40-60% restatement (verified in note). Each agent invocation reads the skill verbatim; restatements multiply token cost across IDE mirrors. CLAUDE.md is the canonical source; per-skill restatements are stale-prone (CLAUDE.md updates don't propagate automatically). One-liner reference enforces single source of truth.

### D-106-06: TDD bundled GREEN+RED commit pattern (mirror spec-105)

Same workflow as spec-105: each phase commit bundles GREEN code (current phase) + RED tests for next phase, marked `@pytest.mark.spec_106_red` and excluded from CI default run. CI command: `pytest -m 'not spec_105_red and not spec_106_red'` post spec-105 + spec-106 lifecycle. Phase 6 final: zero residual markers (except documented opt-in like perf).

**Rationale**: spec-105 muscle memory confirmed. Same audit trail benefits. Same CI-green discipline.

### D-106-07: 6 phases (smaller scope than spec-105's 8)

| Phase | Scope |
|---|---|
| 1 | execution-kernel.md + dispatch/autopilot/run delegation |
| 2 | design-routing handler + /ai-plan keyword detection |
| 3 | architecture-patterns.md context + /ai-plan step |
| 4 | skill-audit.sh + audit-report.json contract |
| 5 | Restatement cleanup sweep across 47 skills |
| 6 | verify+review convergence + history + mirror sync final |

**Rationale**: scope is 5 deliverables vs spec-105's 11. Smaller phase count matches surface area. Phase 6 mirrors spec-105 Phase 8.

### D-106-08: Mirror sync after each skill edit

`scripts/sync_command_mirrors.py` (existing) MUST be invoked after any `.claude/skills/**/*.md` edit. Phase 5 (restatement sweep) ends with one batch sync; Phases 1, 2, 3 each end with sync. Test `tests/integration/test_skill_mirror_consistency_post_106.py` asserts `ai-eng sync --check` PASS after each commit.

**Rationale**: LESSONS "manifest.yml es la fuente de verdad absoluta" — same logic for skills. Without sync, IDE-mirrors drift and users in non-Claude IDEs see stale content.

## Risks

- **R-1 — Shared kernel handler not mirrored**. `_shared/execution-kernel.md` may not propagate to `.github/`/`.codex/`/`.gemini/`. *Mitigación*: verify `scripts/sync_command_mirrors.py` covers `_shared/` subdirectory; integration test `test_shared_handler_mirror.py` confirms.
- **R-2 — Design routing false positives**. Spec mentions "design system principles" in non-UI context (e.g., backend service spec discussing API design) — routing triggers spuriously. *Mitigación*: keyword allowlist conservative; `--skip-design` override; routing emits explicit log line so user sees rationale.
- **R-3 — Architecture-patterns context noise**. /ai-plan step adds prompt mass. *Mitigación*: on-demand load (NOT preloaded); pattern names + 1-2 paragraph descriptions only (not full implementation guides); user can request expansion via /ai-explain.
- **R-4 — skill-creator eval CLI subcommand missing**. `ai-eng skill eval` may not exist. *Mitigación*: script handles `eval-failed` records gracefully; spec-106 deliverable shifts to "advisory script + JSON contract"; follow-up spec adds CLI subcommand if telemetry shows demand.
- **R-5 — Restatement sweep removes functional content**. Mechanical sweep risks deleting unique guidance. *Mitigación*: per-file diff reviewed before commit; test asserts net line reduction NOT individual file counts; revert single-file if discovered.
- **R-6 — Top 5 verbose skills resist cleanup**. ai-animation/ai-skill-evolve/ai-pr/ai-video-editing/ai-instinct may have legitimate verbosity (e.g., motion patterns inherently verbose). *Mitigación*: target ≥400 lines TOTAL, NOT ≥X per file; if a skill has <50 lines removable, document and accept.
- **R-7 — Orchestrator delegation breaks existing tests**. `/ai-dispatch` tests may assert kernel content inline. *Mitigación*: sweep tests pre-cleanup; update assertions to reference shared handler; integration test confirms full flow works post-extraction.
- **R-8 — Mirror sync fails after sweep**. 47 SKILL.md edits + 4 IDEs × 47 = 188 file regenerations. *Mitigación*: batch sync at end of Phase 5; `ai-eng sync --check` mandatory before Phase 5 commit; if fail → revert sweep + investigate sync.
- **R-9 — Architecture patterns curated list goes stale**. External ref `skills.sh/wshobson/agents/architecture-patterns` may evolve. *Mitigación*: spec-106 ships snapshot; future spec can refresh if patterns added; LESSONS "stable framework orchestration" — patterns rarely change at fundamental level.
- **R-10 — Pre-existing failures cascade**. spec-105 left 5-6 pre-existing test isolation flakes. spec-106 changes may interact. *Mitigación*: baseline confirmed phase-by-phase; if new failure appears, immediately git stash + verify on parent.
- **R-11 — Skill audit script Bash portability**. `set -euo pipefail` + `jq` may fail on Windows / WSL. *Mitigación*: script is advisory; failure mode is `eval-failed` records, not block. Bash is canonical (POSIX); document Windows users run via WSL.
- **R-12 — Design-intent.md format unspecified**. /ai-design output format not constrained by /ai-plan. *Mitigación*: design-routing handler specifies minimum schema (purpose + visual direction + components list); /ai-design can extend; backward-compat for missing optional fields.

## References

- `.ai-engineering/notes/adoption-s4-skills-consolidation-architecture.md` — origen del spec.
- `.ai-engineering/specs/spec-105.md` — predecessor (just completed); spec-106 lands on same branch.
- External: `https://skills.sh/wshobson/agents/architecture-patterns` — curated source for D-106-03 patterns.
- Anthropic skill-creator eval rubric (referenced by D-106-04).
- `.claude/skills/ai-dispatch/SKILL.md`, `ai-autopilot/SKILL.md`, `ai-run/SKILL.md` — modified by D-106-01.
- `.claude/skills/ai-plan/SKILL.md` — modified by D-106-02 + D-106-03.
- `.ai-engineering/contexts/` — new file `architecture-patterns.md` (D-106-03).
- `scripts/sync_command_mirrors.py` — must propagate `_shared/` and per-skill edits.
- CLAUDE.md — single source of truth for Don't rules; restatements eliminated by D-106-05.
- LESSONS:
  - "Stable framework orchestration should not become per-project config by default" → D-106-04 advisory-first.
  - "manifest.yml es la fuente de verdad absoluta" → D-106-08 mirror sync mandatory.
  - "Elimination is simplification, not migration" → D-106-05 mechanical cleanup.

## Open Questions

- **OQ-1**: ¿`_shared/` subdirectory en `.claude/skills/` rompe convención de "una carpeta por skill"? Tentative: explicit underscore prefix marks shared (not invokable). If sync_command_mirrors.py treats `_*` as non-skill, fine; if it tries to register as skill, add exclusion. Decision in Phase 1.
- **OQ-2**: ¿`design-intent.md` location: `.ai-engineering/specs/design-intent.md` o `.ai-engineering/specs/<spec-id>/design-intent.md`? Tentative: per-spec subdirectory pattern matches autopilot artifacts. Phase 2 decides.
- **OQ-3**: ¿Architecture-patterns curated list updates manual or via WebFetch? Tentative: snapshot now (manual), schedule refresh as separate spec when external source materially changes.
- **OQ-4**: ¿`ai-eng skill eval` CLI subcommand creation in scope? Tentative: NO for spec-106 (out of scope per advisory-first). If `eval-failed` records dominate the report, Phase 4 documents need for follow-up CLI work.
- **OQ-5**: ¿Restatement cleanup affects test assertions? Many skill tests check for specific strings. Tentative: tests must be updated when assertions break; document in plan.md as part of T-5.X tasks.
