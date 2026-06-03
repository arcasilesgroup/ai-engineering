---
title: Stale-Issue Audit Remediation — Execution Plan
spec: spec-163
status: draft
pipeline: full
execution_route:
  version: 1
  spec: spec-163
  executor: autopilot
  automation: assisted
  concern_count: 2
  estimated_files: 28
  reason: >
    Two workstreams with distinct risk profiles. Workstream A is a set of
    independent low-risk cleanups (~10 files); Workstream B is a multi-concern
    architecture-enforcement refactor (import-linter gate + layer-violation /
    import-cycle remediation across policy, verify, installer, doctor, detector,
    updater, platforms, release — plus solution-intent + DEC sync). ≥3 concerns
    and ≥10 files => autopilot decomposition.
  safe_next_command: "/ai-autopilot"
---

# spec-163 — Execution Plan

## Design

No UI surface. Two deliverable classes: (1) source deletions + one new test
(Workstream A); (2) a declarative architecture-enforcement gate plus the
import rewires/DEC-acceptances it forces, and a documentation resync
(Workstream B). `--skip-design` rationale: no user-facing visual/interaction
change; the only new "interface" is the `.importlinter` contract file, which is
config, not UX.

## Architecture

Pattern: **ad-hoc** (cleanup) + **policy-as-config** (the import-linter gate).
Workstream B encodes the existing `solution-intent.md` layer map as
`.importlinter` contracts so layering becomes a PR-time gate rather than a
weekly-scan finding — enforcement moves left, no new runtime architecture.

Sequencing (D-163-01): **Workstream A ships first as an independent wave**; it
has zero dependency on B. Within B: B1 (gate scaffold with a baseline ignore
list) must land before B2/B3 so each rewire can tighten the contract; B4/B5 are
independent of B2/B3 and can run in parallel.

---

## Workstream A — Bounded cleanups (independent wave)

### Phase A1 — Confirmed-orphan deletions (#461, #499 subset)

- [ ] T-A1.1 — Delete empty stub module `lib/render.py`
  - Agent: build
  - Files: `src/ai_engineering/lib/render.py` (3 lines, 0 symbols)
  - Principles applied: §10.2 YAGNI, §10.4 DRY
  - Patch (deterministic): `git rm src/ai_engineering/lib/render.py`
  - Gate: `grep -rn "lib.render\|from.*lib import render" src tests` returns 0; `pytest -q` green

- [ ] T-A1.2 — Delete orphan cli_ui widgets
  - Agent: build
  - Files: `src/ai_engineering/cli_ui.py` — `progress_bar:345`, `score_badge:366`, `metric_table:378`
  - Principles applied: §10.2 YAGNI
  - Patch (deterministic): remove the three function defs (verified otheruse=0 in brainstorm sweep)
  - Gate: `grep -rn "progress_bar\|score_badge\|metric_table" src tests` returns only the deletion; ruff clean; `pytest tests/unit -k cli_ui` green

- [ ] T-A1.3 — Delete orphan platform setup-result classes
  - Agent: build
  - Files: `src/ai_engineering/platforms/azure_devops.py:40` (`AzureDevOpsSetupResult`), `src/ai_engineering/platforms/sonar.py:44` (`SonarSetupResult`)
  - Principles applied: §10.2 YAGNI, §10.3 SOLID
  - Patch (deterministic): remove the two dataclasses (otheruse=0); drop now-unused imports if any
  - Gate: `grep -rn "AzureDevOpsSetupResult\|SonarSetupResult" src tests` returns 0; `pytest tests/unit/platforms` green

- [ ] T-A1.4 — Delete remaining orphan singletons
  - Agent: build
  - Files: `src/ai_engineering/policy/checks/sonar.py:245` (`query_sonar_measures`), `src/ai_engineering/state/defaults.py:198` (`default_instinct_meta`), `src/ai_engineering/doctor/environment.py:93` (`issue_from_failure`)
  - Principles applied: §10.2 YAGNI
  - Patch (deterministic): remove the three symbols; **string/getattr guard** — grep dynamic refs, not just imports (R3)
  - Gate: `grep -rn "query_sonar_measures\|default_instinct_meta\|issue_from_failure" src tests` returns 0; `pytest -q` green
  - Note (D-163-02): do NOT touch `state/instincts.py` `read_instinct_observations` / `save_instincts_document` / `save_instinct_meta` / `load_instinct_meta` — excluded pending dual-writer trace.

### Phase A2 — Remove orphan `setup_app` Typer (#462)

- [ ] T-A2.1 — RED: pin the setup command-group contract
  - Agent: build
  - Files: `tests/unit/cli/test_setup_wiring.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): assert `ai-eng setup --help` lists platforms/github/sonar/azure-devops/sonarlint AND `not hasattr(ai_engineering.cli_commands.setup, "setup_app")`
  - Gate: test FAILS before T-A2.2 (the attr still exists)

- [ ] T-A2.2 — GREEN: delete the orphan instance + decorators, keep the functions
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/setup.py` — remove `setup_app = typer.Typer(...)` (36-40) and the five `@setup_app.command(...)` decorator lines (53, 141, 210, 327, 405); the five `setup_*_cmd` functions remain (cli_factory.py:521-530 rebinds them)
  - Principles applied: §10.2 YAGNI, §10.7 Clean Code
  - Patch: judgment — Typer's `.command()` decorator returns the function unchanged, so dropping the decorators leaves `setup.setup_platforms_cmd` et al. callable; keep `import typer` (still used for `Argument`/`prompt`)
  - Gate: T-A2.1 passes; `ai-eng setup platforms --help` works; `pytest tests/unit/cli` green

### Phase A3 — Pin spec-109 G-7 render_detection qualifier (#490)

- [ ] T-A3.1 — RED→GREEN: test the PATH-check qualifier
  - Agent: build
  - Files: `tests/unit/test_render_detection.py` (new); reads `src/ai_engineering/installer/ui.py:93` (`render_detection`, D-109-08 qualifier at :96)
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch: judgment — capture `render_detection(...)` output (it prints; capture via capsys/console) and assert the substring `PATH check; install may use different mechanism` appears under the `Tools:` line; implementation already present so the test goes RED only if the qualifier is removed
  - Gate: `pytest tests/unit/test_render_detection.py` green; mutate-check: deleting the qualifier line makes it fail

### Phase A4 — Remove G-1 hardcoded baseline (#510 residual)

- [ ] T-A4.1 — RED: empty manifest yields actionable error, not a fallback list
  - Agent: build
  - Files: `tests/unit/doctor/test_tools_phase.py` (extend or new)
  - Principles applied: §10.5 TDD
  - Patch: judgment — assert that when `load_required_tools()` is empty, doctor emits `manifest not found, run ` + "`ai-eng install`" and does NOT probe the four baseline tools
  - Gate: test FAILS before T-A4.2

- [ ] T-A4.2 — GREEN: hard-delete `_BASELINE_PATH_TOOLS` + consumers (D-163-06)
  - Agent: build
  - Files: `src/ai_engineering/doctor/phases/tools.py` — remove `_BASELINE_PATH_TOOLS` (128) and its consumers (284, 638); replace each fallback with the actionable diagnostic; fix the docstrings referencing it (246, 588)
  - Principles applied: §10.2 YAGNI, §13.3 no-shim
  - Patch: judgment — at the empty-manifest branch, emit the diagnostic instead of `_BASELINE_PATH_TOOLS` iteration
  - Gate: T-A4.1 passes; `grep -rn "_BASELINE_PATH_TOOLS" src` returns 0; `pytest tests/unit/doctor` green

---

## Workstream B — Architecture-drift CI gate (sequenced wave)

### Phase B1 — import-linter gate scaffold (#496/#497, D-163-03)

- [ ] T-B1.1 — Add `import-linter` dev dependency
  - Agent: build
  - Files: `pyproject.toml` (dev deps), `uv.lock`
  - Principles applied: §10.6 SDD
  - Patch (deterministic): add `import-linter>=2.0` to the dev group; `uv lock`
  - Gate: `uv sync --dev` clean; `lint-imports --help` resolves

- [ ] T-B1.2 — Author `.importlinter` contracts from the SI layer map
  - Agent: build
  - Files: `.importlinter` (new)
  - Principles applied: §10.3 SOLID, §10.8 Hexagonal
  - Patch: judgment — one `layers` contract (Core ▸ Infra ▸ Policy ▸ Auxiliary ▸ Platform per `solution-intent.md §3.1`) + `forbidden`/`independence` contracts for the cycle pairs; seed `ignore_imports` with the CURRENT live violations so the gate starts green and blocks only NEW drift (R1)
  - Gate: `lint-imports` exits 0 against the seeded baseline

- [ ] T-B1.3 — Wire the gate into CI (not the hot path)
  - Agent: build
  - Files: `.github/workflows/*.yml` (the lint/check workflow)
  - Principles applied: §10.6 SDD; Hot-Path Discipline (CI-only, off pre-commit)
  - Patch: judgment — add a `lint-imports` step; SHA-pin per CI Actions governance (see memory ci-actions-governance-constraints)
  - Gate: workflow parses; step runs green on the seeded baseline

### Phase B2 — Layer-violation remediation (#496, D-163-07)

> For each: rewire upward→inward where incidental, else DEC-accept with rationale and remove from the `.importlinter` baseline. One task per cluster; tighten the contract as each clears.

- [ ] T-B2.1 — `release` → version/git (`release/orchestrator.py:14`, `version_bump.py:13`)
  - Agent: build · Principles: §10.3 SOLID · Gate: `lint-imports` passes with this pair un-ignored; `pytest tests/unit/release` green
- [ ] T-B2.2 — `platforms` → credentials (`azure_devops.py:21`, `detector.py:11`, `sonar.py:22`)
  - Agent: build · Principles: §10.3 SOLID · Gate: contract tightened; `pytest tests/unit/platforms` green
- [ ] T-B2.3 — `policy` → Auxiliary/Infra (`checks/sonar.py:14`, `checks/stack_runner.py:28`, `checks/branch_protection.py:10`)
  - Agent: build · Principles: §10.3 SOLID · Gate: contract tightened; `pytest tests/unit/policy` green
- [ ] T-B2.4 — `updater` → installer/state (`updater/service.py:27,51`)
  - Agent: build · Principles: §10.3 SOLID · Gate: contract tightened; `pytest tests/unit/updater` green
- [ ] T-B2.5 — `doctor` → Core+Infra (`doctor/service.py:42`, `phases/tools.py:42`, `phases/detect.py:22`, `phases/hooks.py:22`) — likely DEC-ACCEPT (doctor orchestrates installer phases)
  - Agent: build · Principles: §10.3 SOLID · Gate: DEC record written OR rewired; `lint-imports` green
- [ ] T-B2.6 — `detector` → installer (`detector/readiness.py:20`)
  - Agent: build · Principles: §10.3 SOLID · Gate: resolved jointly with the installer↔detector cycle (T-B3.2)

### Phase B3 — Import-cycle breaks (#497, D-163-07)

- [ ] T-B3.1 — Break/accept `policy ↔ verify` (`policy/checks/stack_runner.py:35` ↔ `verify/taxonomy.py:11`, `verify/service.py:239`)
  - Agent: build · Principles: §10.3 SOLID · Patch: judgment — extract the shared checker registry into a leaf module or invert · Gate: `lint-imports` independence contract green; `pytest tests/unit/{policy,verify}` green
- [ ] T-B3.2 — Break/accept `installer ↔ detector` (`installer/service.py:35` ↔ `detector/readiness.py:20`)
  - Agent: build · Principles: §10.3 SOLID · Gate: cycle contract green
- [ ] T-B3.3 — Break/accept `installer ↔ doctor` (`installer/service.py:36-38`, `auto_remediate.py:20-22` ↔ `doctor/phases/*`)
  - Agent: build · Principles: §10.3 SOLID · Patch: judgment — most invasive (R2); prefer DEC-accept if the orchestration coupling is inherent · Gate: contract green OR DEC recorded
- [ ] T-B3.4 — Resolve `policy→state`, `policy→hooks`, `hooks→state` coupling (#388) — break or DEC-accept as a cohesive cluster
  - Agent: build · Principles: §10.3 SOLID · Gate: `lint-imports` green; DEC record if accepted

### Phase B4 — solution-intent ↔ disk sync (#498/#421, D-163-04, D-163-08)

- [ ] T-B4.1 — Remove ghost `pipeline` node + add `prereqs`/`templates` to the SI layer map
  - Agent: build
  - Files: `.ai-engineering/solution-intent.md` (mermaid diagram ~:261; layer tables)
  - Principles applied: §10.6 SDD
  - Patch: judgment — delete the `pipeline["pipeline…"]` node (no such package); add `prereqs` and `templates` nodes to their layers
  - Gate: no SI node lacks a matching `src/ai_engineering/` dir; no `src` top-level package missing from the map

- [ ] T-B4.2 — Amend DEC-001 to permit nested skill subdirectories (D-163-04)
  - Agent: build
  - Files: `.ai-engineering/solution-intent.md` (DEC-001 ~:719)
  - Principles applied: §10.6 SDD
  - Patch: judgment — restate DEC-001 to allow `handlers/`/`references/`/`scripts/`/`evals/` inside each `ai-<name>/`
  - Gate: DEC-001 text matches the observed `.claude/skills/*/` shape

- [ ] T-B4.3 — Refresh SI version banner (#421)
  - Agent: build
  - Files: `.ai-engineering/solution-intent.md:16`
  - Principles applied: §10.4 DRY
  - Patch (deterministic): replace `0.4.0 (framework)` with the current `pyproject` version (`0.10.1` at plan time; read live)
  - Gate: banner == `grep ^version pyproject.toml`

### Phase B5 — Tech-debt posture (#495, D-163-05)

- [ ] T-B5.1 — Record the complexity-threshold DEC
  - Agent: build
  - Files: `.ai-engineering/solution-intent.md` (DEC store) — new DEC
  - Principles applied: §10.6 SDD
  - Patch: judgment — document that C901/PLR0912/13/15 are advisory (non-blocking), the `audit:exempt` mechanism, and the reduce-worst-offender posture; explicitly NOT a mass refactor
  - Gate: DEC present; cross-links #495

- [ ] T-B5.2 — Reduce the top non-exempt complexity offenders
  - Agent: build
  - Files: top src/ offenders NOT already `audit:exempt` (e.g. `validator/categories/mirror_sync.py:895` `_check_instruction_parity` C901:22; `verify/scoring.py:124` PLR0913:9) — **exclude** `templates/.../hooks/*` (R4 manifest churn)
  - Principles applied: §10.7 Clean Code, §10.3 SOLID
  - Patch: judgment — extract helpers / introduce Options dataclasses; behavior-preserving
  - Gate: chosen functions drop below threshold; `pytest` green; no behavior change

### Phase B6 — Issue closeout (handled at /ai-pr)

- [ ] T-B6.1 — On merge, close folded issues with forward-links
  - Agent: build (PR pipeline)
  - Files: n/a (GitHub) — close #492 (skill-count resolved + SI sync folded), and #462/#490/#495/#496/#497/#498/#499/#510/#421 against the merged PR
  - Principles applied: §10.6 SDD
  - Gate: each closed issue comments the PR # and the implementing decision

---

## Gate Summary

| Wave | Exit gate |
|------|-----------|
| A (A1–A4) | All orphan greps return 0; new tests green; `pytest -q` green; ruff clean |
| B1 | `lint-imports` green on seeded baseline; CI wired (SHA-pinned) |
| B2/B3 | Each cluster un-ignored from `.importlinter` and passing, or DEC-accepted; layer/cycle suites green |
| B4/B5 | SI matches disk; DEC-001 + threshold DEC present; offender functions below threshold |
| Final | `/ai-verify` GO; secrets + lint + full suite green; no new import-linter violation |

## Notes for the executor

- **Route**: `/ai-autopilot` — Workstream A as Wave 1 (independent), Workstream B
  decomposed into sub-specs (B1 gate → B2/B3 remediation → B4/B5 docs).
- **R1 baseline discipline**: B1 seeds `ignore_imports` with current violations so
  the gate blocks only NEW drift; B2/B3 shrink the baseline to zero (or DEC).
- **R3**: every deletion greps dynamic references (getattr/registry/strings), not
  just imports, before removal.
- **R4**: B5 avoids `.ai-engineering/scripts/hooks/` to dodge hooks-manifest churn;
  if unavoidable, regen manifest + template twin in the same commit.
- **D-163-02**: the `state/instincts.py` read/save cluster stays untouched.
