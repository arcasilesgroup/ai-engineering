---
title: Prune contexts/, research/, docs/, evals/ — Surface Cleanup Brief
status: draft
audience: framework-dev
branch: proposed `spec-NNN/prune-low-value-surfaces` (TBD by `/ai-brainstorm`)
length_estimate: ~640 lines
authoring_style: Staff Principal Architect — evidence-first, no emoji
principles_required: [§10.1 KISS, §10.2 YAGNI, §10.3 SOLID, §10.6 SDD, §10.7 Clean Code]
delivery_mode: cross-surface refactor (5 waves; hard delete per CONSTITUTION.md §3)
mantra: Delete first; relocate only when load-bearing.
---

# Prune `.ai-engineering/contexts/`, `.ai-engineering/research/`, `docs/`, `evals/` — Surface Cleanup Brief

> **Audience**: `/ai-brainstorm` → `/ai-plan` → `/ai-build` (or `/ai-autopilot`).
> **Branch**: TBD (proposed `spec-NNN/prune-low-value-surfaces`).
> **Authoring lens**: Staff Principal Architect, IQ-200 calibration. KISS · YAGNI · SOLID · SDD · Clean Code · Hard rename per CONSTITUTION.md §3.
> **Status**: feedback from operator after eight months of lived experience; impact analysis dispatched 2026-05-16 by `/ai-spec-draft` (parallel `/ai-explore` sweep).

---

## 1. Vision

Four top-level knowledge surfaces — `.ai-engineering/contexts/`, `.ai-engineering/research/`, `docs/`, `evals/` — were created at different moments for distinct historical reasons. They have accumulated heterogeneous, low-coherence content. The operator's diagnosis: these directories increase complexity without proportional value. The empirical evidence below confirms this: three of the four either contain runtime state misplaced in source-controlled paths (`research/`, `evals/`) or duplicate content that could live closer to its consumer (`contexts/`); the fourth (`docs/`) carries 1.1 MB of binary presentation/design assets alongside the canonical anchor for the framework's `§10.x` engineering principles.

This brief proposes a **hard delete** of all four directories per `CONSTITUTION.md §3` (no backwards-compat shims, no redirect files), with surgical relocation of the ~10 demonstrably load-bearing files to coherent new homes. The endpoint is a flatter repository: principles inlined into the canonical mirrors, runbooks in `.ai-engineering/runbooks/`, runtime state in `.ai-engineering/runtime/`, and zero ambiguity about where a future contributor should look for any given artifact.

---

## 2. Scope Boundary

**In scope**

- Hard delete of `.ai-engineering/contexts/`, `.ai-engineering/research/`, `docs/`, `evals/` with all subdirectories and files.
- Hard delete of the corresponding template mirrors at `src/ai_engineering/templates/.ai-engineering/contexts/` and any other template-side residue.
- Relocation of 8–12 demonstrably load-bearing files to coherent new homes (`.ai-engineering/runbooks/`, `.ai-engineering/policies/`, `.ai-engineering/evals/`, repo root for `SOLUTION-INTENT.md`).
- Inlining of `principles.md` (§10), `mirror-authoring.md` (§14/§15), `surface-axioms.md` (§16) into the four canonical mirror payloads (CLAUDE.md, AGENTS.md, GEMINI.md, `.github/copilot-instructions.md`) and `CANONICAL.md` / `CONSTITUTION.md` as the authoritative source.
- Update of all inbound references (Python `src/`, Python `tools/`, tests, Markdown, YAML, scripts).
- Update of CI workflows that hardcode trigger paths or runner paths.
- Removal of dead ownership / exclusion / migration rules in `control_plane.py`, `mirror_inventory.py`, `validator/_shared.py`, `installer/phases/governance.py`, `updater/service.py`.
- CHANGELOG entries documenting each hard rename and hard delete.

**Out of scope (explicitly)**

- `/ai-research` Tier 3 auto-persist behaviour — the persistence path may move, but the persist semantics stay.
- `/ai-reliability-eval` corpus schema — the `.jsonl` format is unchanged; only its on-disk location moves.
- The §10.x anchor system itself — only its on-disk home changes (the 76 in-skill citations stay verbatim).
- Engram setup semantics — the integration doc relocates but content semantics are unchanged.
- New skills, new agents, or new commands — this brief deletes and relocates only.

---

## 3. Diagnostic Snapshot

Each directory's current state, with `file:line` evidence drawn from the dispatched `/ai-explore` impact analysis.

### 3.1 `.ai-engineering/contexts/` — 23 files, ~140 KB

Heterogeneous accumulation of (a) tested architectural references (`architecture-patterns.md`, `engineering-standards.md`), (b) policy documents (`gate-policy.md`, `risk-acceptance-flow.md`, `mcp-binary-policy.md`, `semgrep-update-model.md`), (c) governance contracts (`knowledge-placement.md`), (d) schema docs (`spec-schema.md`, `plan-schema.md`), (e) operational notes (`permissions-migration.md`, `python-env-modes.md`, `session-governance.md`, `evidence-protocol.md`, `stack-context.md`, `cli-ux.md`, `mcp-integrations.md`, `sentinel-iocs-update.md`, `operational-principles.md`, `harness-engineering.md`, `harness-adoption.md`, `gather-activity-data.md`), and (f) `team/` (operator-owned `README.md` and `lessons.md`).

The `CLAUDE.md` Source-of-Truth table at `CLAUDE.md:82` cites `.ai-engineering/contexts/knowledge-placement.md` as the **placement contract** — a circular bootstrap: the contract that defines where things go lives in the dumping ground.

Load-bearing inbound references:

- Nine pytest functions in `tests/unit/test_architecture_patterns_curated_list.py:17` and three in `tests/integration/test_architecture_pattern_step.py:17` read `architecture-patterns.md` directly via `read_text()` with schema assertions.
- `tests/unit/test_engineering_standards.py:49,51,53` reads the triad (`engineering-standards.md`, `harness-engineering.md`, `harness-adoption.md`) with `is_file()` + `read_text()`.
- `src/ai_engineering/state/control_plane.py:82` and `:86` hardcode `".ai-engineering/contexts/team/**"` and `".ai-engineering/contexts/*.md"` as ownership-tier rules.
- `src/ai_engineering/config/mirror_inventory.py:149` globs `contexts/**/*.md` for the governance template sync.
- `tools/skill_domain/standards.py:84,85,86` carry three path constants (`_OPERATIONAL_PRINCIPLES`, `_ENGINEERING_STANDARDS`, `_HARNESS_ENGINEERING`) emitted as `canonical_refs` metadata.
- `src/ai_engineering/installer/phases/governance.py:27,29,35` and `installer/phases/detect.py:103,177`, `installer/service.py:169,172`, `updater/service.py:1200-1217` carry installer / updater logic referencing `contexts/team/` and `contexts/` ownership.
- `src/ai_engineering/doctor/phases/ide_config.py:167` emits the error-message string `"See contexts/permissions-migration.md."`.
- `src/ai_engineering/validator/_shared.py:115,236,240` carries `contexts/` patterns in regex + glob lists.

Total inbound references: **LOAD-BEARING 7, DOC-ONLY 8, CONFIGURABLE 2**.

### 3.2 `.ai-engineering/research/` — 3 files, ~20 KB

Three dated external-evidence artifacts from spec-133 (2026-05-12): `ide-hook-engines-2026-05-12.md`, `stack-classification-2026-05-12.md`, `git-branch-cleanup-modes-2026-05-12.md`. All carry YAML frontmatter (`topic`, `date`, `tier: external-evidence`, `consumers`).

The directory is the runtime write target for `/ai-research` Tier 0 cache (short-circuit path for repeated research queries) and Tier 3 auto-persist.

Load-bearing inbound references:

- `tools/spec_lint/checks/references.py:32` hardcodes `_RESEARCH_MD_RE = re.compile(r"^\.ai-engineering/research/.+\.md$")` — the validator for `research:` prefix entries in spec.md frontmatter.
- Five test references at `tests/integration/test_ai_research_tier0.py:5`, `tests/integration/test_brainstorm_research_integration.py:107`, `tests/unit/skills/ai_research/test_persist.py:83,99`, `tests/integration/_ai_research_persist_helper.py:14,142`, `tests/integration/_ai_research_tier0_helper.py:359`.
- ~40 SKILL.md / handler files across `.claude/`, `.codex/`, `.gemini/`, `.github/`, and `src/ai_engineering/templates/project/*/skills/ai-research/` carry the literal path string (entry points: `.claude/skills/ai-research/SKILL.md:16,39,51,96,100` and `.claude/skills/ai-research/handlers/persist-artifact.md:5,31`).
- `scripts/sync_mirrors/antigravity_target.py:3` cites `research/ide-hook-engines-2026-05-12.md` in its module docstring.
- `.ai-engineering/contexts/spec-schema.md:28,40` documents the `research:` prefix convention (already inside the doomed `contexts/`).

The fundamental issue: this is **runtime artifact storage** sitting in a source-controlled directory whose name (`research`) does not signal "runtime". The convention `.ai-engineering/runtime/` exists for exactly this case (documented at `CLAUDE.md:205-209`).

Total inbound references: **LOAD-BEARING 5, DOC-ONLY 3, CONFIGURABLE 0**.

### 3.3 `docs/` — 36 files, ~1.4 MB

Dominated by binary assets: `design.pen` at 696 KB, `untitled.pen` at 121 KB, and four `.pptx` files (presentations totalling ~230 KB). Textual content splits into three tiers:

- **High-load** (tests + CRITICAL lint check): `principles.md` (§10 home), `mirror-authoring.md` (§14/§15), `surface-axioms.md` (§16), `cli-reference.md`, `model-dispatch-policy.md` (SSOT for effort tier), `solution-intent.md` (`/ai-docs` write target), `conformance-report.md` (generator output baseline).
- **Mid-load**: `integrations/engram.md`, `getting-started.md`, `architecture/dir-schemas.md`.
- **Low-load** (links only, no test asserts content): `anti-patterns.md`, `copilot-subagents.md`, `agentsview-source-contract.md`, `ci-alpine-smoke.md`, `integrations/antigravity.md`, `presentations/speech-script.md`.

Critical cascades:

- `tools/skill_lint/checks/md_mirror.py:258` defines `_DOCS_TARGETS = ("docs/principles.md", "docs/mirror-authoring.md", "docs/surface-axioms.md")` and emits **CRITICAL** when any is absent. Conformance test `tests/conformance/test_md_mirror.py:438,466` covers both passing and failing paths.
- `tests/integration/sync/test_canonical_mirror_parity.py:162,164,170,173,206,207,215,218,229,234,237,260` reads all three docs with `read_text()` and asserts content alignment with the mirrors.
- `tests/integration/test_principle_split_governance.py:45,50` defines `DOCS_PRINCIPLES_MD = REPO_ROOT / "docs" / "principles.md"` inside `GOVERNANCE_PATHS`.
- `.github/workflows/ci-check.yml:10,17` carries `'docs/**'` in PR trigger paths.
- `.claude/skills/ai-docs/handlers/solution-intent-sync.md:5,28,61` writes `docs/solution-intent.md`; `solution-intent-init.md:5,15,89,106` initialises it; `solution-intent-validate.md:10` reads it; `docs-quality-gate.md:32` lints it.
- `.claude/skills/ai-sprint/SKILL.md:102` writes `docs/presentations/generate_sprint_review.py`.
- `tools/skill_lint/checks/effort.py:76` and `tools/skill_lint/cli.py:38` set `_DEFAULT_POLICY_PATH = Path("docs/model-dispatch-policy.md")` as the SSOT for effort validation.
- `tools/skill_infra/markdown_reporter.py:8,31` writes `docs/conformance-report.md`.
- `tools/no_suppression/scanner.py:78` carries `"docs/presentations/**"` in its exclusion list.
- `README.md:59,65,75` links to `docs/getting-started.md`, `docs/integrations/engram.md`, `docs/cli-reference.md`.

**§10.x citation cascade**: `grep -rn "§10\." --include="*.md"` across `.claude/skills/`, `.claude/agents/`, `.gemini/skills/`, `.codex/skills/`, `.github/skills/` returns **76 occurrences** (per the impact analysis cross-directory summary). Every one resolves to `docs/principles.md` via the pointer row at `CLAUDE.md:36` / `AGENTS.md:36` / `GEMINI.md:36` / `.github/copilot-instructions.md:36`. Hard deleting `docs/principles.md` without relocating the §10 content triggers a **four-gate failure**: `md_mirror.py` CRITICAL → `test_canonical_mirror_parity.py` → `test_principle_split_governance.py` → `tools/skill_lint --check`.

Total inbound references: **LOAD-BEARING 9, DOC-ONLY 5, CONFIGURABLE 0**.

### 3.4 `evals/` — 4 files, ~12 KB

Pilot seed for the skill-set regression gate. Content:

- `baseline.json` — one entry (`ai-debug`, `pass_at_1: 1.0`); notes that the full 46-skill corpus is deferred.
- `ai-debug.jsonl` — three eval cases for the `/ai-debug` skill (pilot seed).
- `cli-ux-cross-ide/test_drift_recovery_flow.md` — spec-133 drift-recovery eval definition with `decisions: [D-133-11, D-133-24]` and a six-stack matrix.
- `.gitkeep` — placeholder.

Load-bearing inbound references:

- `.github/workflows/skill-evals.yml:20` carries `'evals/**'` in `paths:` trigger; `:75,76` hardcode `--baseline evals/baseline.json --corpus-root evals/`.
- `scripts/run_loop_skill_evals.py:64,65,70,71` defaults `--baseline` to `Path("evals/baseline.json")` and `--corpus-root` to `Path("evals")`.
- `tools/skill_app/eval_runner.py:36,44,46,63` reads baseline + globs `corpus_root/*.jsonl`.
- `.claude/skills/ai-reliability-eval/SKILL.md:25,35,57,90,96,135,158,168` operates against these paths; `.claude/skills/ai-skill-improve/SKILL.md:22,24` cites evidence from `evals/<skill>.jsonl`.

**Silent gate degradation risk**: `scripts/run_loop_skill_evals.py:86-92` treats a missing baseline as the "first-run capture flow" and exits 0 with only a warning. Hard deleting `evals/` makes the regression gate a silent no-op in CI without any failing assertion — operators get no signal that the gate is broken.

Design intent already documented at `src/ai_engineering/validator/_shared.py:229,230`: *"evals/ is runtime state"*. The directory is excluded from the governance template sync at `src/ai_engineering/config/mirror_inventory.py:150`, confirming it should not be tracked in source-of-truth files at all — it is runtime state misplaced at repo root.

Total inbound references: **LOAD-BEARING 5, DOC-ONLY 4, CONFIGURABLE 0**.

### 3.5 Cross-Directory Pattern

All four directories share a meta-pattern: each accumulated content because no other home felt obviously correct at the moment of creation. The operator's intuition that they "increase complexity without proportional value" is empirically grounded — three of the four either contain runtime state (`research/`, `evals/`) or duplicate content that could live closer to its consumer (`contexts/`); the fourth (`docs/`) has 11% binary assets and an inconsistent split between governance-critical anchors and operator presentation drafts.

---

## 4. Architecture

The proposed end state collapses four directories into three coherent locations plus inline content in the canonical mirrors.

```
BEFORE (4 surfaces, fuzzy purpose)         AFTER (3 surfaces, sharp purpose)
─────────────────────────────────────      ────────────────────────────────────
.ai-engineering/contexts/        (23) ─┐
.ai-engineering/research/         (3) ─┤
docs/                             (36) ─┼──► .ai-engineering/runbooks/      (~6)
evals/                             (4) ─┤    .ai-engineering/policies/      (~1)
                                       │    .ai-engineering/evals/          (~4)
                                       │    .ai-engineering/runtime/research/ (3 - gitignored)
                                       │
                                       └──► CLAUDE.md / AGENTS.md / GEMINI.md
                                            copilot-instructions.md / CONSTITUTION.md
                                            absorb §10, §14, §15, §16,
                                            placement contract, gate policy
```

### 4.1 New homes per surface

1. **§10 Engineering Principles** (`docs/principles.md`) → **inline §10 directly into the four canonical mirror payloads** and `CANONICAL.md` master source. The pointer row at `CLAUDE.md:36` dissolves; the actual §10.1–§10.8 content appears under §10 of each mirror. The 76 `§10.x` citations across skill surfaces resolve to in-document anchors. **Open Decision #1** discusses the inline-vs-file alternative.
2. **Mirror authoring contract** (`docs/mirror-authoring.md`) → inline into `CONSTITUTION.md §14` (the per-file authoring table + the `<!-- ide-extras:start -->` fence contract). Update `tools/skill_lint/checks/md_mirror.py:259` to check inline content instead of file existence.
3. **Surface axioms** (`docs/surface-axioms.md`) → inline into `CONSTITUTION.md §16` (A1 Surface Axiom + A2 No-Twin Axiom). Update `md_mirror.py:260` accordingly.
4. **Engineering-standards triad** (`engineering-standards.md`, `harness-engineering.md`, `harness-adoption.md`) → `.ai-engineering/runbooks/`. Update `tools/skill_domain/standards.py:84,85,86` constants and `tests/unit/test_engineering_standards.py:49,51,53` paths.
5. **Architecture patterns** (`architecture-patterns.md`) → `.ai-engineering/runbooks/architecture-patterns.md`. Update 12 test references.
6. **Schema documents** (`spec-schema.md`, `plan-schema.md`) → `.ai-engineering/runbooks/`. Internal consumers in `tools/spec_lint/` and `tools/plan_lint/` update paths.
7. **CLI reference** (`docs/cli-reference.md`) → `.ai-engineering/runbooks/cli-reference.md`. Update `tests/architecture/test_surface_parity.py:91` error message string.
8. **Model dispatch policy** (`docs/model-dispatch-policy.md`) → `.ai-engineering/policies/model-dispatch-policy.md`. Update `tools/skill_lint/checks/effort.py:76`, `tools/skill_lint/cli.py:38`, plus tests.
9. **Solution intent** (`docs/solution-intent.md`) → `SOLUTION-INTENT.md` at repo root. Update `/ai-docs` handler files across all four IDE surfaces (~16 handler files via sync-mirrors).
10. **Engram integration** (`docs/integrations/engram.md`) → fold install commands into `CLAUDE.md §188 "Optional: Engram"` (currently a summary at `CLAUDE.md:185`). Operator decides whether to keep the verbose install detail inline or drop it entirely.
11. **Policy documents** (`gate-policy.md`, `risk-acceptance-flow.md`, `mcp-binary-policy.md`, `semgrep-update-model.md`) → fold relevant content into `CONSTITUTION.md §13 Hard Rules` as inline subsections. `tests/unit/test_local_fast_slice_policy.py:461` error string updates to cite the new home.
12. **Placement contract** (`knowledge-placement.md`) → fold into `CLAUDE.md §12 Source-of-Truth` as an inline paragraph. The table row dissolves into a self-contained explanation.
13. **Research artefacts** (3 dated files from spec-133) → `.ai-engineering/runtime/research/` (gitignored runtime state) or `.ai-engineering/specs/archive/research/` (preserve as historical evidence). The `/ai-research` Tier 0 cache target updates in the skill SKILL.md + handlers + `tools/spec_lint/checks/references.py:32` regex.
14. **Evals corpus** (`baseline.json`, `ai-debug.jsonl`, `cli-ux-cross-ide/test_drift_recovery_flow.md`) → `.ai-engineering/evals/` (the runtime path already referenced by `tests/unit/test_verify_taxonomy.py:90`). Update `.github/workflows/skill-evals.yml:75,76` + `scripts/run_loop_skill_evals.py:64,65,70,71` + `tools/skill_app/eval_runner.py:36,44,46,63`.
15. **`docs/conformance-report.md`** → `.ai-engineering/runtime/reports/conformance.md` (the report is a runtime artefact, not source-of-truth). Update `tools/skill_infra/markdown_reporter.py:8,31`.

### 4.2 Hard deletions (no relocation)

The following content is recommended for hard deletion with no relocation. Each is independently checked in §11 Risks and §9 Open Decisions.

- `docs/presentations/` — 4 `.pptx`, 4 generator `.py`, 12 `.svg` (~570 KB). Operator presentations are not source-controlled artefacts in a framework repo; export to non-repo location.
- `docs/*.pen` — 2 binary design files (~820 KB). No consumer; if archived elsewhere, no value remains.
- `docs/anti-patterns.md`, `docs/copilot-subagents.md`, `docs/agentsview-source-contract.md`, `docs/ci-alpine-smoke.md`, `docs/getting-started.md`, `docs/integrations/antigravity.md`, `docs/architecture/dir-schemas.md` — no test asserts content; only README/CONTRIBUTING prose links. Operator confirms during `/ai-brainstorm`.
- `contexts/permissions-migration.md`, `contexts/sentinel-iocs-update.md`, `contexts/python-env-modes.md`, `contexts/session-governance.md`, `contexts/stack-context.md`, `contexts/evidence-protocol.md`, `contexts/operational-principles.md`, `contexts/gather-activity-data.md`, `contexts/cli-ux.md`, `contexts/mcp-integrations.md`, `contexts/team/` — review case-by-case during `/ai-plan`; merge any genuinely-needed content into the closest skill SKILL.md or `CONSTITUTION.md` section.
- `evals/.gitkeep` — placeholder; no value.

### 4.3 Reference rewrites at a glance

| Surface | Approximate edit count |
|---|---|
| Python `src/` (control_plane, mirror_inventory, validator, framework_defaults, installer, updater, doctor, state, vcs) | ~25–30 line edits |
| Python `tools/` (standards, skill_lint, spec_lint, skill_infra, no_suppression) | ~15–20 line edits |
| Tests (`tests/unit/`, `tests/integration/`, `tests/conformance/`, `tests/architecture/`, `tests/e2e/`) | ~70–90 line edits across ~25 files |
| Mirrors (CLAUDE.md, AGENTS.md, GEMINI.md, copilot-instructions.md, CANONICAL.md, plus 7 template mirrors) | ~40–60 line edits (auto-regenerated by `make sync-md` after CANONICAL.md authoring) |
| Skills + handlers across `.claude/`, `.gemini/`, `.codex/`, `.github/`, `src/ai_engineering/templates/project/*/` | ~50–80 line edits (auto-regenerated) |
| CI workflows (`.github/workflows/ci-check.yml`, `skill-evals.yml`) | ~5–8 line edits |
| Scripts (`scripts/sync_mirrors/core.py`, `scripts/run_loop_skill_evals.py`, `scripts/sync_mirrors/antigravity_target.py`) | ~10–15 line edits |
| Top-level docs (`README.md`, `CONTRIBUTING.md`) | ~5–10 line edits |

**Total**: ~250–330 line edits across ~80–100 files. Concentration in tests and mirror surfaces (the latter regenerated by sync).

---

## 5. Evidence Catalog

| Claim | Evidence |
|---|---|
| `architecture-patterns.md` has 9 hard-asserting tests + 3 integration tests | `tests/unit/test_architecture_patterns_curated_list.py:17,28`, `tests/integration/test_architecture_pattern_step.py:17,28,48` |
| Tests read engineering-standards triad directly | `tests/unit/test_engineering_standards.py:42,45,46,49,51,53` |
| `control_plane.py` hardcodes contexts/ ownership rules | `src/ai_engineering/state/control_plane.py:82,86,87` |
| `mirror_inventory.py` globs `contexts/**/*.md` | `src/ai_engineering/config/mirror_inventory.py:149,150` |
| Three context path constants in `standards.py` | `tools/skill_domain/standards.py:84,85,86,302` |
| `_RESEARCH_MD_RE` hardcodes research/ path | `tools/spec_lint/checks/references.py:32` |
| Five tests exercise `.ai-engineering/research/` path | `tests/integration/test_ai_research_tier0.py:5`, `tests/integration/test_brainstorm_research_integration.py:107,109`, `tests/unit/skills/ai_research/test_persist.py:83,99`, `tests/integration/_ai_research_persist_helper.py:14,142`, `tests/integration/_ai_research_tier0_helper.py:359` |
| `_DOCS_TARGETS` CRITICAL check for principles/mirror-authoring/surface-axioms | `tools/skill_lint/checks/md_mirror.py:258,259,260,261,262` |
| `test_canonical_mirror_parity.py` reads all three docs | `tests/integration/sync/test_canonical_mirror_parity.py:162,164,170,173,206,215,229,234,237,260` |
| `test_principle_split_governance.py` requires `principles.md` | `tests/integration/test_principle_split_governance.py:45,50,140` |
| Conformance test exercises CRITICAL+OK paths | `tests/conformance/test_md_mirror.py:357,438,450,456,466,473` |
| CLAUDE.md / mirrors point to docs/ files | `CLAUDE.md:20,36,82,118,122,125,185`, `AGENTS.md:20,36,82,115,118,122,125`, `GEMINI.md:20,36,82,115,118,122,125`, `.github/copilot-instructions.md:82` |
| `/ai-docs` writes `docs/solution-intent.md` | `.claude/skills/ai-docs/handlers/solution-intent-sync.md:5,28,61`, `solution-intent-init.md:5,15,89,106`, `solution-intent-validate.md:10`, `docs-quality-gate.md:32` |
| `/ai-sprint` writes `docs/presentations/generate_sprint_review.py` | `.claude/skills/ai-sprint/SKILL.md:102` |
| Model dispatch policy is SSOT for effort tier | `tools/skill_lint/checks/effort.py:76`, `tools/skill_lint/cli.py:38` |
| `skill-evals.yml` hardcodes evals/ paths | `.github/workflows/skill-evals.yml:20,75,76` |
| Regression gate silently no-ops on missing baseline | `scripts/run_loop_skill_evals.py:64,65,70,71,86,87,88,89,90,91,92` |
| Eval runner reads baseline + corpus | `tools/skill_app/eval_runner.py:36,44,46,63` |
| `evals/` is runtime-state by design | `src/ai_engineering/validator/_shared.py:229,230,240` |
| CI trigger paths `'docs/**'` | `.github/workflows/ci-check.yml:10,17` |
| README links into docs/ | `README.md:59,65,75` |
| Conformance report writer | `tools/skill_infra/markdown_reporter.py:8,31` |
| Installer / updater / doctor reference contexts/ paths | `src/ai_engineering/installer/phases/governance.py:27,29,35`, `installer/phases/detect.py:103,177`, `installer/service.py:169,172`, `updater/service.py:1200,1204,1211,1217`, `doctor/phases/ide_config.py:167` |
| Validator regex + glob patterns cite contexts/ | `src/ai_engineering/validator/_shared.py:115,236,240` |
| Engram doc cited in mirrors | `CLAUDE.md:185`, `scripts/sync_mirrors/core.py:1007,1044,1124` |

---

## 6. Roadmap

Five waves. Each is independently mergeable; each leaves CI green at completion. Wave order matters — Wave 2 (inline §10) must land **before** Wave 4 (delete `docs/`) to avoid the four-gate cascade.

### Wave 1 — Relocate non-critical load-bearing content

Move runbook + policy content to new homes without touching §10 / §14 / §16. Old paths still exist during this wave (parallel state, gates green).

- Move triad (`engineering-standards.md`, `harness-engineering.md`, `harness-adoption.md`) + `architecture-patterns.md` + `spec-schema.md` + `plan-schema.md` to `.ai-engineering/runbooks/`.
- Move `cli-reference.md` to `.ai-engineering/runbooks/`.
- Move `model-dispatch-policy.md` to `.ai-engineering/policies/`.
- Move `solution-intent.md` to repo root `SOLUTION-INTENT.md`.
- Update `tools/skill_domain/standards.py:84-86`, `tools/skill_lint/checks/effort.py:76`, `tools/skill_lint/cli.py:38`, 12 test references for architecture-patterns, 3 test references for the standards triad, `.claude/skills/ai-docs/handlers/*` (regenerate mirrors via `make sync-md`), `tests/architecture/test_surface_parity.py:91`.

**Acceptance**: relocated files in new homes; old paths still exist; full test suite green; `make sync-md` clean.

### Wave 2 — Inline §10 + §14 + §16 into mirrors

Critical wave. Eliminates the §10.x cascade risk before Wave 4 deletes `docs/`.

- Author §10.1–§10.8 inline content in `CANONICAL.md` (the master mirror source).
- Run `make sync-md` to regenerate `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md` with the inline §10 block.
- Same for §14 (`mirror-authoring.md` content) and §16 (`surface-axioms.md` A1/A2 content) — folded into `CONSTITUTION.md` master source, then mirrored where applicable.
- Update `tools/skill_lint/checks/md_mirror.py:258-262`: drop `_DOCS_TARGETS = (...)` file-existence check; replace with inline-content assertion (verify §10 anchor block present in each mirror).
- Update `tests/integration/sync/test_canonical_mirror_parity.py:162-260`: assert inline content rather than `read_text()` on three external files.
- Update `tests/integration/test_principle_split_governance.py:45,50,140`: drop `DOCS_PRINCIPLES_MD` from `GOVERNANCE_PATHS`; assert content inline.

**Acceptance**: 76 `§10.x` citations across skills resolve to in-document anchors; `tools/skill_lint --check` green; `tests/integration/sync/test_canonical_mirror_parity.py` green; `tests/integration/test_principle_split_governance.py` green.

### Wave 3 — Relocate runtime state (research + evals)

- Move `evals/baseline.json`, `evals/ai-debug.jsonl`, `evals/cli-ux-cross-ide/test_drift_recovery_flow.md` to `.ai-engineering/evals/`.
- Update `.github/workflows/skill-evals.yml:20,75,76`, `scripts/run_loop_skill_evals.py:64,65,70,71`, `tools/skill_app/eval_runner.py:36,44,46,63`.
- Update `.claude/skills/ai-reliability-eval/SKILL.md` + handler files (regenerate mirrors).
- Move `.ai-engineering/research/*.md` to `.ai-engineering/runtime/research/` (add `runtime/research/` to `.gitignore`) — or `.ai-engineering/specs/archive/research/` if archive semantics preferred (Open Decision #2).
- Update `tools/spec_lint/checks/references.py:32` regex to the new path.
- Update `.claude/skills/ai-research/SKILL.md` + `handlers/persist-artifact.md` + `handlers/tier0-local.md` (regenerate mirrors).
- Update 5 test fixtures: `tests/integration/test_ai_research_tier0.py:5`, `test_brainstorm_research_integration.py:107,109`, `tests/unit/skills/ai_research/test_persist.py:83,99`, `tests/integration/_ai_research_persist_helper.py:14,142`, `tests/integration/_ai_research_tier0_helper.py:359`.
- **Hardening**: change `scripts/run_loop_skill_evals.py:86-92` from silent-no-op to fail-loud when `--baseline` path is missing AND `--regression` mode is requested. Prevents the silent gate degradation called out in §3.4.

**Acceptance**: regression gate runs against new path with same semantics; missing-baseline-with-regression now fails loud; `/ai-research` Tier 0 cache lookup hits new path; 5 integration tests green.

### Wave 4 — Hard delete old directories

This is the destructive wave. All preceding waves must have landed.

- `git rm -r .ai-engineering/contexts/`
- `git rm -r .ai-engineering/research/` (if not already moved to gitignored runtime path in Wave 3)
- `git rm -r docs/`
- `git rm -r evals/`
- `git rm -r src/ai_engineering/templates/.ai-engineering/contexts/` (template mirror)
- Update `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `CANONICAL.md` to drop all `docs/` and `contexts/` pointer rows.
- Update `README.md` (lines 59, 65, 75) and `CONTRIBUTING.md` (line 141).
- Drop dead rules:
  - `src/ai_engineering/config/mirror_inventory.py:149,150` — drop `contexts/**/*.md` glob + `contexts/team/` exclusion.
  - `src/ai_engineering/validator/_shared.py:115,236,240` — drop `contexts/` regex + glob + `evals/` exclusion (now misplaced).
  - `src/ai_engineering/state/control_plane.py:82,86,87` — drop contexts/ ownership rules.
  - `src/ai_engineering/config/framework_defaults.py:131` — drop `contexts/team/**` default.
  - `src/ai_engineering/installer/phases/governance.py:27,29,35` — drop `contexts/team/` and migration map entry.
  - `src/ai_engineering/installer/phases/detect.py:103,177` — drop legacy `context/ → contexts/` migration.
  - `src/ai_engineering/installer/service.py:169,172` — drop `contexts/team/` exclude.
  - `src/ai_engineering/updater/service.py:1200,1204,1211,1217` — drop `_DEPRECATED_GOVERNANCE_PATHS = ("contexts/team",)`.
  - `src/ai_engineering/doctor/phases/ide_config.py:167` — drop or rewrite the `contexts/permissions-migration.md` error string.
  - `src/ai_engineering/state/observability.py:675` — drop stale comment.
  - `tools/no_suppression/scanner.py:78` — drop `"docs/presentations/**"` exclusion.
  - `tools/skill_lint/checks/no_orphan_dirs.py:71,72` — drop `.ai-engineering/contexts/{frameworks,languages}` (already-deleted).
- Drop `'docs/**'` from `.github/workflows/ci-check.yml:10,17` PR trigger.

**Acceptance**: zero inbound references to deleted directories (verified by `grep -rn` sweep); full test suite green; `tools/skill_lint --check` green; `make sync-md` clean.

### Wave 5 — Final sweep + CHANGELOG

- `grep -rn "\.ai-engineering/contexts" --include="*.py" --include="*.md" --include="*.yml" --include="*.json"` → expect zero hits (excluding archived spec drafts that pre-date this work).
- Same for `\.ai-engineering/research`, `docs/`, `evals/`.
- Update `CHANGELOG.md` with hard-rename + hard-delete entries per `CONSTITUTION.md §3`.
- Update spec-128's `cli-ux-cross-ide-rearch-brief.md:615,882` to drop now-invalid eval path references (or relocate that brief's eval references).
- Run `make sync-md` — no diff expected.
- Run full conformance + integration + e2e test suites.
- Run manual smoke: `/ai-research`, `/ai-docs`, `/ai-reliability-eval`, `/ai-sprint`, `/ai-brainstorm` end-to-end against new paths.

**Acceptance**: zero dangling references; CHANGELOG entries land; manual smoke green.

---

## 7. Definition of Done

- All four directories deleted from working tree and from `src/ai_engineering/templates/`.
- Load-bearing content relocated:
  - `.ai-engineering/runbooks/` holds engineering-standards triad, architecture-patterns, schema docs, cli-reference.
  - `.ai-engineering/policies/` holds model-dispatch-policy.
  - `.ai-engineering/evals/` holds baseline + corpora.
  - `.ai-engineering/runtime/research/` (gitignored) holds research artefacts — or they are archived under `.ai-engineering/specs/archive/research/`.
  - Repo root holds `SOLUTION-INTENT.md`.
  - §10 inlined into the four canonical mirrors; §14 + §16 inlined into `CONSTITUTION.md`.
- All inbound references updated (Python, YAML, Markdown, scripts).
- `tools/skill_lint --check` runs without `_DOCS_TARGETS` CRITICAL findings.
- `make sync-md` produces a no-op diff.
- Full test suite green: unit, integration, conformance, architecture, e2e.
- CHANGELOG entries land for each relocation/deletion.
- Manual smoke of `/ai-research`, `/ai-docs`, `/ai-reliability-eval`, `/ai-sprint`, `/ai-brainstorm` against new paths.

---

## 8. Quality Stamps

Principles applied:

- **§10.1 KISS** — three coherent surfaces (`runbooks/`, `policies/`, `evals/`) replace four heterogeneous ones; no new abstractions.
- **§10.2 YAGNI** — drop content with no current consumer (presentations, `.pen` files, anti-patterns essay).
- **§10.3 SOLID (Single Responsibility)** — each new directory has one purpose: runbooks reference, policies declare, evals capture state.
- **§10.6 SDD** — every relocation and deletion gated by approved spec + plan (this brief is the contract).
- **§10.7 Clean Code** — eliminate fuzzy-purpose surfaces; eliminate dead ownership / exclusion / migration rules.

Contracts honoured:

- `CONSTITUTION.md §3` hard rename — no backwards-compat shims, no redirect files.
- `CONSTITUTION.md §13.4` anonymous content — no machine paths introduced; all references use `$HOME/...` style or relative repo paths.
- A1 Surface Axiom — each canonical artefact has exactly one home after the refactor.
- A2 No-Twin Axiom — preserved (no duplicate sources of truth introduced).

---

## 9. Open Decisions

1. **§10 inline vs file at repo root** — inline §10.1–§10.8 directly into each of the four canonical mirrors (recommended; eliminates the pointer-chain entirely) versus relocate `principles.md` to `PRINCIPLES.md` at repo root and keep the pointer row. Inline adds ~150 lines to each mirror; the four mirrors already carry identical canonical payload of ~190 lines, so the increase is ~80% but parity remains easy to verify.
2. **Research artefact archival** — `.ai-engineering/runtime/research/` (gitignored; cache survives between sessions but not across `git clean -fdx`) versus `.ai-engineering/specs/archive/research/` (committed; preserved indefinitely as historical evidence for the three spec-133 artefacts). The Tier 0 cache feature must work in either case.
3. **`/ai-sprint` Step 5 write target** — `.claude/skills/ai-sprint/SKILL.md:102` writes `docs/presentations/generate_sprint_review.py`. Options: (a) update SKILL.md to a non-`docs/` write target (e.g., `~/Documents/presentations/` outside the repo), (b) drop presentation generation from `/ai-sprint`, (c) keep `docs/presentations/` alive as an exception to the deletion. **Operator decision**.
4. **`evals/.ai-engineering/evals/` versus `.ai-engineering/runtime/evals/`** — committed (regression gate has a stable anchor) versus runtime (no commit, ephemeral). Recommendation: committed (the baseline is the gate's contract).
5. **`solution-intent.md` location** — `SOLUTION-INTENT.md` at repo root (matches README/CHANGELOG convention for first-class project artefacts) versus `.ai-engineering/solution-intent.md` (keeps the framework's own state self-contained). Recommendation: repo root.
6. **`docs/presentations/` and `docs/*.pen`** — full hard delete (recommended; not source-controlled artefacts in a framework repo) versus operator-driven export to a non-repo location before deletion.
7. **Wave ordering** — ship the five waves as five separate PRs (safer; each gate-passable in isolation) versus one combined atomic PR (~250–330 line edits). Recommendation: five PRs, each gated on green CI.
8. **`/ai-explore` versus `/ai-research` skill clarification** — Item #15 in `dx-excellence-refactor-brief.md` flagged these as functionally distinct but confusingly described. This brief's research relocation does not resolve that; carries forward to a future brief.

---

## 10. Migration

Hard rename per `CONSTITUTION.md §3`. No backwards-compat shims, no redirect files, no aliases.

**For each relocated file**:

- Waves 1–3: write new file, update inbound references, leave old file in place temporarily. Gates green.
- Wave 4: `git rm` the old file, regenerate sync-md, commit.
- CHANGELOG entry: `### Removed` lists each old path; `### Moved` lists each old → new mapping.

**For each deleted file (no relocation)**:

- CHANGELOG entry: `### Removed` lists the path with a one-line justification.
- No grace period — single commit removes the file and any inbound references.

**For template mirrors** (`src/ai_engineering/templates/`):

- The 21 contexts/ files in the template mirror at `src/ai_engineering/templates/.ai-engineering/contexts/` are byte-identical to the live files (confirmed by `diff` in impact analysis).
- Wave 4 explicitly deletes the template mirror in the same commit as the live source; `mirror_inventory.py:149` drops the rule in the same commit.

**For external consumers (existing installations)**:

- A consumer who already ran `ai-eng install` has the old paths in their `.ai-engineering/` tree.
- They run `ai-eng update` after the deletion lands; the updater's deprecation logic (already present in `src/ai_engineering/updater/service.py:1200-1217`, currently scoped to `contexts/team`) extends to cover the deleted paths.
- No version pin or compatibility flag — consumers either update or pin to a pre-deletion release.

---

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| §10.x cascade failure if `principles.md` deleted before inline lands | High | Critical (4-gate failure: `md_mirror.py` CRITICAL, `test_canonical_mirror_parity.py`, `test_principle_split_governance.py`, `skill_lint --check`) | Wave 2 inlines §10 BEFORE Wave 4 deletes; pre-Wave-4 grep confirms zero remaining file-references |
| Eval regression gate silently no-ops in CI after `evals/` deletion | Medium | High (silent gate degradation; CI green despite gate skipped) | Wave 3 moves baseline + corpus before Wave 4 deletes; Wave 3 hardens `run_loop_skill_evals.py:86-92` to fail-loud when `--regression` requested with missing baseline |
| `tools/skill_lint --check` errors on missing `_DOCS_TARGETS` files between Wave 1 and Wave 2 | Medium | Medium | Wave 2 lands before Wave 4; during the gap, `_DOCS_TARGETS` still points to the existing files (no premature delete) |
| Sync-mirrors emits stale mirror content during transition | Medium | Medium (mirror parity test fails) | Each wave includes `make sync-md` at the end + a sync-mirrors test run; commit only when diff is clean |
| Template mirror at `src/ai_engineering/templates/.ai-engineering/contexts/` left in tree after live source deleted | Low | Medium (governance sync re-seeds the live tree from template) | Wave 4 explicitly deletes the template mirror in the same PR; `mirror_inventory.py:149` drops the rule in the same commit |
| `/ai-docs` skill breaks for operators relying on literal `docs/solution-intent.md` path | Low | Medium (skill behaviour break) | Wave 1 ships handler updates to the new path before deletion; existing `solution-intent.md` files in consumer projects migrate via `ai-eng update` |
| `tests/integration/test_brainstorm_research_integration.py` and 4 siblings fail during research path move | Low | Medium (test failure) | Wave 3 updates fixtures and the `spec_lint` regex in one commit; integration tests re-run before merge |
| `/ai-sprint` Step 5 breaks (write target `docs/presentations/generate_sprint_review.py` removed) | Low | Medium (skill behaviour break) | Open Decision #3 resolves this before Wave 4: update SKILL.md, drop the step, or carve out an exception for `docs/presentations/` |
| `cli-ux-cross-ide-rearch-brief.md:615,882` references `evals/cli-ux-cross-ide/test_drift_recovery_flow.md` — moving eval breaks the spec draft cross-reference | Low | Low | Wave 5 updates the brief; spec drafts are not enforced by tests |
| 76 `§10.x` citation grep miss (a SKILL.md in a non-surveyed surface) | Low | High | Wave 2 pre-check: `grep -rn "§10\." --include="*.md"` across the entire repo (no `--include` filters); reconcile count before Wave 4 |
| Operator workflow disruption (PR slides previously delivered from `docs/presentations/`) | Low | Low | Open Decision #6 + operator agrees to export to non-repo location before Wave 4 |
| `/ai-explore` versus `/ai-research` skill description ambiguity (#15 from dx-excellence brief) lingers | Low | Low | Out of scope; future brief addresses |

---

## 12. References

- `CONSTITUTION.md §3` — *"no backwards-compat shims for renamed/deleted/migrated content. Hard rename, hard delete, hard migration. CHANGELOG documents the breakage."*
- `CONSTITUTION.md §13` — Hard Rules (secrets gate, no suppression, etc.).
- `CLAUDE.md §10` — Engineering Principles pointer chain (the row being eliminated by Wave 2).
- `CLAUDE.md §12` — Source-of-Truth table; placement-contract row at `CLAUDE.md:82`.
- `CLAUDE.md §14–§16` — Mirror authoring + surface axioms pointer chain (the rows being eliminated by Wave 2).
- Existing brief `.ai-engineering/specs/drafts/dx-excellence-refactor-brief.md` — establishes "AGENTS.md, CLAUDE.md, GEMINI.md, copilot-instructions.md are mirror copies carrying identical payload" precedent for inline content.
- Existing brief `.ai-engineering/specs/drafts/skills-agents-excellence-v2-brief.md` — establishes refactor cadence per wave.
- Existing brief `.ai-engineering/specs/drafts/cli-ux-cross-ide-rearch-brief.md:615,882` — currently references `evals/cli-ux-cross-ide/test_drift_recovery_flow.md`; Wave 5 updates.
- spec-134 sub-005 plan at `.ai-engineering/runtime/autopilot/sub-005/plan.md` — the spec that established `docs/principles.md` as §10's anchor home.
- spec-128 reference at `tests/unit/test_spec_128_surface_6_absence.py:8,54` — prior work has already moved framework surface area in a similar direction (`contexts/languages/` and `contexts/frameworks/` were already deleted).
- Impact analysis dispatched 2026-05-16 by `/ai-spec-draft` via `/ai-explore` agent — full inventory + reference analysis backing this brief.

---

## 13. Glossary

- **Anchor chain** — the pointer indirection from a `§10.x` citation in a SKILL.md to its definition in `docs/principles.md` via the §10 pointer row in the canonical mirrors.
- **Canonical mirror** — one of `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`; the four files carry byte-identical canonical payload.
- **Hard delete** — removal with no backwards-compat shim, no redirect, no alias. Per `CONSTITUTION.md §3`.
- **Load-bearing reference** — an inbound reference whose removal causes a test failure, hook break, sync break, or behavioural break at runtime (as opposed to a DOC-ONLY dangling-link reference).
- **Mirror parity** — the property that the four canonical mirrors carry byte-identical payload (enforced by `tests/integration/sync/test_canonical_mirror_parity.py`).
- **Runbook** — a non-policy reference document consulted by humans or skills during operations (e.g., `architecture-patterns.md`, `engineering-standards.md`).
- **Runtime state** — files written and read by skill execution at runtime, not source-controlled artefacts; convention `.ai-engineering/runtime/` (gitignored).
- **Silent gate degradation** — the failure mode where a CI gate becomes a no-op without emitting a failure signal; the gate appears green but does nothing. Mitigated by fail-loud assertions.
- **Surface** — a top-level directory or file with a coherent purpose. `.ai-engineering/contexts/` is currently NOT a coherent surface (heterogeneous content).
- **Template mirror** — the `src/ai_engineering/templates/.ai-engineering/` tree that ships with the installed framework; mirrors the live `.ai-engineering/` (enforced by `scripts/sync_mirrors/core.py`).
- **Tier 0 cache** — the `/ai-research` short-circuit path that returns cached external evidence from a prior research run (tier ladder: 0 local cache → 1 free MCPs → 2 web → 3 NotebookLM persistent).

---

## 14. Acceptance

- [ ] `.ai-engineering/contexts/` deleted from working tree.
- [ ] `.ai-engineering/research/` deleted from working tree.
- [ ] `docs/` deleted from working tree.
- [ ] `evals/` deleted from working tree.
- [ ] `src/ai_engineering/templates/.ai-engineering/contexts/` deleted (template mirror).
- [ ] Engineering-standards triad, architecture-patterns, schema docs, cli-reference relocated to `.ai-engineering/runbooks/`.
- [ ] Model-dispatch-policy relocated to `.ai-engineering/policies/`.
- [ ] Baseline + corpora relocated to `.ai-engineering/evals/`.
- [ ] Research artefacts relocated to `.ai-engineering/runtime/research/` (gitignored) or `.ai-engineering/specs/archive/research/` (per Open Decision #2).
- [ ] `SOLUTION-INTENT.md` lives at repo root.
- [ ] §10.1–§10.8 inlined into `CANONICAL.md` and propagated to the four canonical mirrors.
- [ ] §14 Mirror Authoring + §16 Surface Axioms inlined into `CONSTITUTION.md`.
- [ ] All Python references updated (`grep -rn "\.ai-engineering/contexts\|\.ai-engineering/research\|docs/principles\|docs/mirror-authoring\|docs/surface-axioms\|docs/cli-reference\|docs/model-dispatch-policy\|docs/solution-intent\|evals/" --include='*.py'` returns zero hits in `src/` and `tools/`).
- [ ] All Markdown references in skills + agents updated across the four IDE surfaces.
- [ ] All test references updated (~25 test files, ~70–90 line edits).
- [ ] `.github/workflows/ci-check.yml` drops `'docs/**'` trigger; `.github/workflows/skill-evals.yml` points to `.ai-engineering/evals/`.
- [ ] `scripts/run_loop_skill_evals.py:86-92` hardened: fail-loud when `--regression` requested with missing baseline.
- [ ] `make sync-md` produces a no-op diff.
- [ ] `tools/skill_lint --check` passes (no `_DOCS_TARGETS` CRITICAL).
- [ ] Full conformance + integration + e2e test suites green.
- [ ] `CHANGELOG.md` carries `### Moved` and `### Removed` entries per `CONSTITUTION.md §3`.
- [ ] Manual smoke run of `/ai-research`, `/ai-docs`, `/ai-reliability-eval`, `/ai-sprint`, `/ai-brainstorm` against new paths.

---

> Hand off to `/ai-brainstorm --consume prune-contexts-docs-research-evals-brief.md` to promote this brief to an approved `spec.md`.
