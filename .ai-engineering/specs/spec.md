---
spec: spec-136
slug: prune-low-value-surfaces
title: Prune `docs/`, `.ai-engineering/contexts/`, `.ai-engineering/research/`, `evals/` — Single `.ai-engineering/reference/` Home
status: approved
effort: large
branch: spec-136/prune-low-value-surfaces
source_brief: .ai-engineering/specs/drafts/prune-contexts-docs-research-evals-brief.md
target_dispatch: /ai-autopilot
chains_after: spec-135
delivery_mode: one-atomic-PR
mantra: Delete by default; relocate only what is load-bearing; ai-engineering owns nothing under `docs/`.
principles_required: [§10.1 KISS, §10.2 YAGNI, §10.3 SOLID, §10.6 SDD, §10.7 Clean Code]
---

# Prune `docs/`, `.ai-engineering/contexts/`, `.ai-engineering/research/`, `evals/` — Single `.ai-engineering/reference/` Home

## Summary

Four top-level knowledge surfaces accumulated heterogeneous, low-coherence content over eight months — `.ai-engineering/contexts/` (23 files, dumping ground), `.ai-engineering/research/` (3 dated artifacts misplaced in source-controlled tree), `docs/` (36 files including 820 KB of binary design assets, plus framework-owned reference docs that violate the consumer-vs-framework ownership boundary), and `evals/` at repo root (4 files, runtime-state misplaced at top level). They increase complexity without proportional value. This spec hard-deletes all four surfaces per `CONSTITUTION.md §3` (no backwards-compat shims) and collapses the framework's load-bearing reference content into a **single flat `.ai-engineering/reference/` folder** (~19 files), with runtime state moved under `.ai-engineering/runtime/{research,presentations,reports}/`, the eval corpus moved under `.ai-engineering/evals/`, and `solution-intent.md` + `team/` lifted to `.ai-engineering/` top-level. The operator's `docs/*.pen` design files survive as user-owned dogfooding content — ai-engineering never writes to `docs/` again. Endpoint: one atomic PR `spec-136/prune-low-value-surfaces`, ~250–330 line edits across ~80–100 files, ~66 file-level moves or deletes, all governance gates green at merge.

## Goals

1. **Hard-delete `.ai-engineering/contexts/`, `.ai-engineering/research/`, `evals/` from the working tree and from `src/ai_engineering/templates/.ai-engineering/contexts/`** — verified by `grep -rln "\\.ai-engineering/contexts\\|\\.ai-engineering/research\\|^evals/" --include='*.py' --include='*.md' --include='*.yml' --include='*.json'` returning zero hits outside `.ai-engineering/specs/archive/`.
2. **Empty `docs/` of all framework-owned content; preserve only `docs/*.pen`** — operator-as-dogfooder retains their two design files. After merge, `ls docs/` returns only `design.pen` and `untitled.pen`; no `.md`, `.py`, `.pptx`, `.svg`, `.png` artefacts remain.
3. **Single flat `.ai-engineering/reference/` folder holds ~19 load-bearing reference docs** — principles, mirror-authoring, surface-axioms, cli-reference, model-dispatch-policy, architecture-patterns, engineering-standards + harness triad, all 5 policy/contract docs (gate-policy, risk-acceptance-flow, mcp-binary-policy, semgrep-update-model, knowledge-placement), spec-schema, plan-schema, operational-principles, gather-activity-data. No `runbooks/` or `policies/` subdivision.
4. **Pointer rows retarget cleanly across 4 canonical mirrors** — `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md` continue to carry byte-identical canonical payload; `make sync-md` produces a no-op diff; mirror-parity test stays green.
5. **76 `§10.x` citations across skill/agent files resolve to the new path verbatim** — citations stay literal (`§10.1 KISS` etc.); only the pointer-row target in mirrors changes from `docs/principles.md` to `.ai-engineering/reference/principles.md`.
6. **All load-bearing skill references retarget** — `operational-principles` (5 reviewer-* + ai-build + ai-test + ai-code + ai-sprint = 9 sites + 4 template mirrors); `gather-activity-data` (ai-standup + ai-sprint = 3 sites + template mirrors); `solution-intent` (ai-docs handlers, 4 surfaces); auto-regenerated via `make sync-md`.
7. **Runtime state moves to `.ai-engineering/runtime/`** — `docs/conformance-report.md` → `.ai-engineering/runtime/reports/conformance.md`; `/ai-sprint` Step 5 retargets to `.ai-engineering/runtime/presentations/`; `/ai-research` Tier 0 cache target retargets to `.ai-engineering/runtime/research/` (gitignored). The 3 spec-133 dated research files hard-delete (Tier 0 cache rebuilds organically).
8. **Eval corpus moves to `.ai-engineering/evals/` with hardened gate** — `evals/baseline.json`, `evals/ai-debug.jsonl`, `evals/cli-ux-cross-ide/test_drift_recovery_flow.md` relocate; `.github/workflows/skill-evals.yml:20,75,76`, `scripts/run_loop_skill_evals.py:64,65,70,71`, `tools/skill_app/eval_runner.py:36,44,46,63` retarget; `scripts/run_loop_skill_evals.py:86-92` hardens to fail-loud when `--regression` requested with missing baseline (closes the silent gate-degradation risk).
9. **Engram install snippet folds into `CLAUDE.md` `Optional: Engram` section** — currently at `CLAUDE.md:185` as a summary; absorbs the install-commands prose from `docs/integrations/engram.md`; the docs file hard-deletes. Sync-mirrors propagates to AGENTS / GEMINI / copilot-instructions.
10. **Dead ownership / exclusion / migration rules drop** — `control_plane.py:82,86,87`, `mirror_inventory.py:149,150`, `validator/_shared.py:115,236,240`, `framework_defaults.py:131`, `installer/phases/governance.py:27,29,35`, `installer/phases/detect.py:103,177`, `installer/service.py:169,172`, `updater/service.py:1200-1217`, `doctor/phases/ide_config.py:167`, `observability.py:675`, `no_suppression/scanner.py:78`, `skill_lint/checks/no_orphan_dirs.py:71,72`, `skill_lint/checks/md_mirror.py:258` retarget or drop.
11. **CI trigger paths clean** — `.github/workflows/ci-check.yml:10,17` drops `'docs/**'` from PR trigger; `.github/workflows/skill-evals.yml` retargets to `.ai-engineering/evals/`.
12. **`team/` is operator-owned, lifted to top level** — `.ai-engineering/contexts/team/` → `.ai-engineering/team/`. Updates `control_plane.py` ownership rules and `framework_defaults.py` defaults.
13. **CHANGELOG documents the breakage** — single block adds `### Moved` (~16 entries) + `### Removed` (~25 entries) + `### Changed` (mirrors + README links).
14. **Full test suite green at merge** — unit, integration, conformance, architecture, e2e all pass; `tools/skill_lint --check` clean; `make sync-md` no-op diff.

## Non-Goals

1. **No new abstractions.** No new skills, no new agents, no new commands. Existing skill semantics preserved.
2. **No §10 inlining into mirror payloads.** Earlier brief recommendation rejected after cost analysis (~1,270 duplicated lines across 5 surfaces). §10 stays as a single source at the new path; pointer rows retarget.
3. **No reorganization inside `.ai-engineering/reference/`.** Single flat folder; no `runbooks/` or `policies/` sub-buckets. The operator's brief discussion settled this.
4. **No `docs/*.pen` deletion.** The two operator design files survive as user-owned dogfooding content. ai-engineering tooling never writes to `docs/`.
5. **No grace period.** Hard delete in a single PR; no redirect files, no aliases, no compatibility shims.
6. **No version-pinning for downstream consumers.** Consumers run `ai-eng update`; the updater's existing deprecation logic (`updater/service.py:1200-1217`, scoped to `contexts/team` today) extends to cover the deleted paths.
7. **No `/ai-research` Tier 3 auto-persist semantics change.** Cache target relocates from `.ai-engineering/research/` → `.ai-engineering/runtime/research/`; persist semantics unchanged.
8. **No `/ai-reliability-eval` corpus schema change.** `.jsonl` format unchanged; only on-disk location moves.
9. **No `/ai-explore` vs `/ai-research` skill description disambiguation** (item carried forward from `dx-excellence-refactor-brief.md` #15). Out of scope.
10. **No move of `CONSTITUTION.md` content.** CONSTITUTION.md stays at 197 lines; policy docs (gate-policy, risk-acceptance-flow, etc.) live as separate reference files under `.ai-engineering/reference/`, not folded into CONSTITUTION.
11. **No multi-PR delivery.** One atomic PR `spec-136/prune-low-value-surfaces`. The earlier brief's five-wave-five-PR proposal is rejected per operator preference.
12. **No rescue of `docs/presentations/speech-script.md`.** All 8 files under `docs/presentations/` plus `docs/svg/` hard-delete.

## Decisions

### D-136-01 — Hard rename per `CONSTITUTION.md §3`

**Choice:** Hard delete all four directories (`.ai-engineering/contexts/`, `.ai-engineering/research/`, `evals/`) and empty `docs/` of framework-owned content in a single atomic PR. No backwards-compat shims. No redirect files. No aliases.

**Rationale:** `CONSTITUTION.md §3` is non-negotiable on this. Soft renames preserve dead code paths that accumulate technical debt and confuse future contributors about which path is the "real" one. The 8-month accumulation that produced the four surfaces happened precisely because of soft pluralism.

### D-136-02 — `docs/` belongs to the consumer, not to ai-engineering

**Choice:** `docs/` is reserved for the project that installs ai-engineering. Framework-owned content moves to `.ai-engineering/`. `docs/*.pen` survives as operator-as-dogfooder content.

**Rationale:** This sharp ownership boundary eliminates the chronic ambiguity about whether a file in `docs/` is framework-owned or consumer-owned. Without it, every new framework artifact races for `docs/` because the directory name signals "documentation generically". The operator's dogfooding `.pen` files are explicitly user-content and survive accordingly.

### D-136-03 — Single flat `.ai-engineering/reference/` folder

**Choice:** All ~19 load-bearing reference docs land in `.ai-engineering/reference/` with no further sub-bucketing. Rejected: `runbooks/` + `policies/` split (the brief's original proposal).

**Rationale:** Reference docs do not benefit from category sub-folders at this scale (~19 files). One coherent home with one rule ("if it's framework reference, it's in reference/") beats two sub-folders that force every contributor to decide which bucket a new doc lives in. KISS (§10.1) over SoC at this granularity.

### D-136-04 — `§10` content relocates; does NOT inline into mirrors

**Choice:** `docs/principles.md` (254 lines, KISS → Hexagonal Architecture) → `.ai-engineering/reference/principles.md`. Pointer rows in the 4 mirrors retarget from `docs/principles.md` to `.ai-engineering/reference/principles.md`. 76 `§10.x` citations in skill files stay verbatim.

**Rationale:** The original brief recommended inline-into-mirrors. Cost analysis rejected: inline would duplicate 254 lines across 5 surfaces (CANONICAL + 4 mirrors) = ~1,270 lines, growing each mirror's canonical payload from ~190 → ~444 lines (~2.3×). Each `§10` edit would require regenerating 5 surfaces. The pointer-chain is not the friction worth eliminating; the source ambiguity is, and that's already eliminated by D-136-02. The relocation cost is one rename + one pointer-row retarget.

### D-136-05 — `solution-intent.md` at `.ai-engineering/` top-level, not repo root

**Choice:** `docs/solution-intent.md` → `.ai-engineering/solution-intent.md` (top-level, single file). Rejected: `SOLUTION-INTENT.md` at repo root.

**Rationale:** Operator's principle (D-136-02): "ai-engineering owns content under `.ai-engineering/`; repo root belongs to the consumer project." `SOLUTION-INTENT.md` at root would put framework-authored content next to the consumer's `README.md`, violating the ownership boundary.

### D-136-06 — `team/` lifts to top-level

**Choice:** `.ai-engineering/contexts/team/` → `.ai-engineering/team/`.

**Rationale:** `team/` is operator-owned content (lessons.md + README.md). Keeping it under the deleted `contexts/` namespace would either preserve `contexts/` as a single-purpose vestigial folder or force a deeper rename. Top-level is cleanest: `team/` describes itself; the surrounding directory tells you it's framework-state.

### D-136-07 — Eval corpus committed at `.ai-engineering/evals/`, gate hardens fail-loud

**Choice:** `evals/baseline.json`, `evals/ai-debug.jsonl`, `evals/cli-ux-cross-ide/test_drift_recovery_flow.md` → `.ai-engineering/evals/` (committed, not gitignored). Plus: `scripts/run_loop_skill_evals.py:86-92` changes from "silently treat missing baseline as first-run capture" to "fail-loud when `--regression` requested with missing baseline".

**Rationale:** The baseline is the regression gate's contract — must be a committed artefact, not runtime state. The silent-no-op behavior was a footgun the brief surfaced: deleting `evals/` made the CI gate a green-but-empty no-op without any signal. Hardening to fail-loud closes the risk class.

### D-136-08 — `/ai-research` Tier 0 cache: hard delete 3 dated files; new target `.ai-engineering/runtime/research/` (gitignored)

**Choice:** The 3 spec-133 dated artifacts (`ide-hook-engines-2026-05-12.md`, `stack-classification-2026-05-12.md`, `git-branch-cleanup-modes-2026-05-12.md`) hard-delete. The Tier 0 cache rebuilds organically into a fresh gitignored target.

**Rationale:** spec-133 already shipped (commit `0b4827d0`); the 3 files are dated evidence whose cache value is near-zero for new queries. Honors "delete by default" (D-136-01). The new path under `runtime/` aligns with the convention that runtime state lives in `.ai-engineering/runtime/`.

### D-136-09 — `/ai-sprint` Step 5 retargets to `.ai-engineering/runtime/presentations/`; `docs/presentations/` hard-deletes wholly

**Choice:** Update `.claude/skills/ai-sprint/SKILL.md:102` Step 5 write target from `docs/presentations/generate_sprint_review.py` to `.ai-engineering/runtime/presentations/generate_sprint_review.py`. Hard-delete all 8 files under `docs/presentations/` (4 `.py`, 3 `.pptx`, 1 `.md`) + `docs/svg/`. Drop `tools/no_suppression/scanner.py:78`'s `"docs/presentations/**"` exclusion.

**Rationale:** Sprint review decks are runtime artefacts of `/ai-sprint` invocations, not source-controlled framework code. They belong under `runtime/`. The existing `docs/presentations/` files are stale outputs from past invocations and have no current consumer. `speech-script.md` is operator prose with no test consumer — operator can export it before merge if desired.

### D-136-10 — Engram install snippet folds into `CLAUDE.md`; `docs/integrations/engram.md` hard-deletes

**Choice:** Absorb the install-commands prose from `docs/integrations/engram.md` into the existing `CLAUDE.md` `Optional: Engram` section (currently a summary at `CLAUDE.md:185`). Sync-mirrors propagates to AGENTS / GEMINI / copilot-instructions. Then hard-delete `docs/integrations/engram.md`. Rejected: relocate to `.ai-engineering/reference/integrations/engram.md`.

**Rationale:** Engram is a third-party integration mentioned in a single short section of the mirrors. A dedicated reference doc is overkill; the prose belongs adjacent to the section that references it.

### D-136-11 — Policy docs ARE load-bearing → all to `.ai-engineering/reference/`

**Choice:** `gate-policy.md` (167), `risk-acceptance-flow.md` (232), `mcp-binary-policy.md` (81), `semgrep-update-model.md` (106), `knowledge-placement.md` (62) all relocate to `.ai-engineering/reference/`. Rejected: fold into `CONSTITUTION.md §13`.

**Rationale:** Cited as `canonical_refs` metadata by `skill_domain/standards.py` and surfaced through skill metadata. Folding 648 lines into `CONSTITUTION.md` would bloat it 197 → 845 lines (4.3×), destroying its identity as the lean hard-rules document. The reference/ folder is the right home.

### D-136-12 — One atomic PR `spec-136/prune-low-value-surfaces`, single merge

**Choice:** Ship as one PR squashing all five logical waves (relocate, retarget, runtime moves, hard delete + dead-rule sweep, CHANGELOG). Rejected: five sequential PRs; rejected: three-PR compromise.

**Rationale:** Matches operator pattern (PR #509 shipped 6 specs together: spec-128 + 129 + 131 + 132 + 133 + 134). Single review surface; single CHANGELOG block; one revert command if regression appears. Wave ordering still matters internally (relocate before delete) but the commits within the PR follow that order.

### D-136-13 — Bulk hard-delete of low-load files; no rescue list

**Choice:** Hard-delete the following without relocation. From `contexts/`: cli-ux.md, evidence-protocol.md, mcp-integrations.md, permissions-migration.md, python-env-modes.md, session-governance.md, sentinel-iocs-update.md, stack-context.md. From `docs/`: anti-patterns.md, copilot-subagents.md, agentsview-source-contract.md, ci-alpine-smoke.md, getting-started.md, integrations/antigravity.md, architecture/dir-schemas.md, conformance-report.md (relocated to runtime/), all of presentations/, all of svg/.

**Rationale:** None have load-bearing consumers (no test asserts content; no skill cites them as canonical refs). README link cleanup (lines 59, 65, 75) handles the only dangling-reference exposure. Cumulative deletion: ~16 files + 2 dirs.

### D-136-14 — `_DOCS_TARGETS` lint check retargets, does not delete

**Choice:** `tools/skill_lint/checks/md_mirror.py:258-262` keeps the existence check but retargets the three paths: `docs/principles.md` → `.ai-engineering/reference/principles.md`, `docs/mirror-authoring.md` → `.ai-engineering/reference/mirror-authoring.md`, `docs/surface-axioms.md` → `.ai-engineering/reference/surface-axioms.md`. The CRITICAL-on-missing semantics stay.

**Rationale:** The check is the load-bearing protection that surfaces a 4-gate failure if these files vanish. Keeping the check with retargeted paths preserves the safety invariant for future contributors who might be tempted to delete the new home.

### D-136-15 — Engineering principles application

**Choice:** Apply `§10.1 KISS`, `§10.2 YAGNI`, `§10.3 SOLID (Single Responsibility)`, `§10.6 SDD`, `§10.7 Clean Code`.

**Rationale:** KISS — collapse 4 fuzzy surfaces into 3 sharp ones (reference, runtime, evals). YAGNI — drop content with no consumer (~16 files). SOLID — each surviving directory carries one purpose. SDD — entire refactor gated by this approved spec. Clean Code — eliminate dead ownership / exclusion / migration rules.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `§10.x` cascade failure if `principles.md` deleted before pointer rows retarget | Medium | Critical (4-gate failure: `md_mirror.py` CRITICAL → `test_canonical_mirror_parity.py` → `test_principle_split_governance.py` → `tools/skill_lint --check`) | Internal commit ordering inside the PR: relocate-first commits land before delete commits; the relocate commit retargets pointer rows simultaneously; pre-merge CI verifies the full chain on every push |
| Silent eval-gate degradation if `evals/` deleted before `run_loop_skill_evals.py` hardens | Medium | High (CI green but gate is no-op) | Same commit that retargets `--baseline` / `--corpus-root` also hardens `:86-92` to fail-loud when `--regression` requested with missing baseline (D-136-07); test added under `tests/unit/scripts/test_run_loop_skill_evals_fail_loud.py` |
| `operational-principles.md` cited by 4 reviewer agents + ai-build + ai-test + ai-code + ai-sprint — broad surface for path-update mistakes | High | Medium (skill agents fail to read referenced standard) | `sync_mirrors` regenerates all `.codex/`, `.gemini/`, `.opencode/`, `.cursor/`, `.github/` and `src/ai_engineering/templates/project/*/` surfaces from `.claude/` source; pre-merge grep `\.ai-engineering/contexts/operational-principles` returns zero hits across the repo |
| `gather-activity-data.md` retargets across `/ai-standup` + `/ai-sprint` + their template mirrors | Medium | Medium | Same `sync_mirrors` pass; same grep gate |
| Template mirror at `src/ai_engineering/templates/.ai-engineering/contexts/` left in tree after live source deleted (governance sync re-seeds the live tree) | Medium | High (re-creates the deleted tree on next install) | Same PR drops `mirror_inventory.py:149,150` rule + deletes the template mirror tree; `tests/architecture/test_surface_parity.py` re-runs to confirm |
| README.md links (`docs/getting-started.md`, `docs/integrations/engram.md`, `docs/cli-reference.md`) dangle after deletes | Low | Low | README updates included in PR; getting-started + antigravity links drop entirely; cli-reference link retargets to `.ai-engineering/reference/cli-reference.md`; engram fold makes the docs-link redundant |
| `cli-ux-cross-ide-rearch-brief.md:615,882` references `evals/cli-ux-cross-ide/test_drift_recovery_flow.md` — moving eval breaks the draft brief's cross-reference | Low | Low | Brief is in `specs/drafts/`, not enforced by tests; PR updates the two references for hygiene |
| `tests/integration/test_brainstorm_research_integration.py` + 4 siblings fail during research path move | Medium | Medium | Same commit updates fixtures and `tools/spec_lint/checks/references.py:32` regex; integration tests re-run on every push |
| Operator workflow disruption: `/ai-sprint review` runs after merge land in `.ai-engineering/runtime/presentations/` not `docs/presentations/` | Low | Low | Operator-facing change is documented in CHANGELOG; the new path is the natural home for runtime artefacts |
| Hard-delete of low-load files surfaces a hidden consumer we did not grep | Low | Medium | Pre-merge grep across `.py`, `.md`, `.yml`, `.json`, `.toml` files; CI green is the final gate; revert is one commit if a hidden consumer surfaces post-merge |
| `team/` move triggers updater logic on consumer projects | Medium | Low | `updater/service.py:1200-1217` already carries deprecation logic for `contexts/team`; extends naturally to cover the move-target; the operator's own `team/` content migrates correctly because the move is in the same PR as the rule update |
| Python 3.9 `spec_lifecycle.py` continues to fail on local host (UTC import) | Known | Low | Already tracked under D-135-13 (fail-open per skill contract); spec-136 inherits the manual-bootstrap state; not blocking |

## References

- doc: `.ai-engineering/specs/drafts/prune-contexts-docs-research-evals-brief.md` — source brief, 14-section evidence-dense input (486 lines)
- doc: `CONSTITUTION.md` §3 (no backwards-compat shims) and §13 (hard rules)
- doc: `CLAUDE.md` §10 (Engineering Principles pointer chain), §12 (Source-of-Truth table), §14–§16 (mirror authoring + surface axioms pointer chain)
- doc: `.ai-engineering/specs/drafts/dx-excellence-refactor-brief.md` — establishes mirror-parity precedent
- doc: `.ai-engineering/specs/drafts/skills-agents-excellence-v2-brief.md` — establishes refactor cadence
- doc: `.ai-engineering/specs/archive/spec-135-framework-performance-hardening.md` — predecessor spec, parked for sequencing
- pr: anthropics/ai-engineering#509 — most recent multi-spec PR establishing one-atomic-PR pattern

## Open Questions

1. **CHANGELOG version bump.** Does this PR cut a new minor version (`0.6.0`) given the breaking nature of the path renames, or land under an existing `## Unreleased` block? Answer at `/ai-pr` time.
2. **`team/` migration on existing consumer installs.** `updater/service.py:1200-1217` currently handles `contexts/team` deprecation. Does the same logic need extending for the other deleted paths (`contexts/`, `research/`, `evals/`, `docs/*`), or do consumers rebuild via `ai-eng install`? Answer at `/ai-plan` time when the updater changeset is scoped.
3. **`spec_lifecycle.py` Python 3.9 bug.** Tracked under D-135-13 as fail-open. Worth opening a separate task to fix the `from datetime import UTC` import to use `datetime.timezone.utc` for 3.9-compat? Not blocking spec-136; mentioned for surface visibility.
