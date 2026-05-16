---
spec: spec-136
title: Prune low-value surfaces — execution plan
status: approved
slug: prune-low-value-surfaces
pipeline: full
architecture: ad-hoc
delivery_mode: one-atomic-PR
branch: spec-136/prune-low-value-surfaces
design_routing: "skipped (no keywords matched)"
target_dispatch: /ai-build
chains_after: spec-135
---

# Plan — spec-136 Prune low-value surfaces

## Pipeline

`full` — refactor touching ~80–100 files with ~250–330 line edits; ~66 file-level moves or deletes; multiple subsystems (skills, agents, mirrors, tests, Python source, CI, CHANGELOG). Standard pipeline cannot scope this safely.

## Architecture

`ad-hoc` — repo-wide hard-rename and dead-rule sweep per `CONSTITUTION.md §3`. No system shape changes; no patterns from `architecture-patterns.md` apply (the catalog is for application design, not refactor topologies). Internal commit ordering inside the single PR enforces the relocate → retarget → delete invariant so every commit boundary leaves CI green.

## Invariants

1. **Relocate before delete.** No `git rm` of `docs/X` or `contexts/X` until the new home is in place AND every inbound reference retargets.
2. **Mirror parity preserved at every commit.** `make sync-md` runs after authoring changes; no commit lands with a sync-mirrors diff.
3. **`_DOCS_TARGETS` lint check retargets, never disappears** — preserves the CRITICAL-on-missing safety invariant for future contributors (D-136-14).
4. **`docs/*.pen` files survive untouched** — operator-as-dogfooder content per D-136-02. Plan never touches `docs/design.pen` or `docs/untitled.pen`.
5. **`__pycache__/` and `.pyc` artefacts ignored** — relocations use `git mv`; build agents must not stage `__pycache__/`.

## Phase 0 — Pre-flight

- [x] T-001 — Verify spec approval + clean working tree
- Agent: verify
- Files: `.ai-engineering/specs/spec.md:1-15`, `.ai-engineering/state/specs/spec-136-prune-low-value-surfaces.json`
- Principles applied: §10.6 SDD (no implementation without approved spec)
- Gate: spec frontmatter `status: approved`; `git status --porcelain` empty; state JSON `state: approved`

- [x] T-002 — Create branch `spec-136/prune-low-value-surfaces`
- Agent: build
- Files: branch operation only
- Principles applied: §10.6 SDD (single branch per spec)
- Patch (deterministic):
```
git checkout -b spec-136/prune-low-value-surfaces
```
- Gate: `git branch --show-current` returns `spec-136/prune-low-value-surfaces`

- [x] T-003 — Confirm exact line numbers across load-bearing patch targets
- Agent: verify
- Files: `tools/skill_lint/checks/md_mirror.py:258`, `tools/spec_lint/checks/references.py:32`, `tools/skill_domain/standards.py:84`, `tools/skill_lint/checks/effort.py:76`, `tools/skill_lint/cli.py:38`, `src/ai_engineering/state/control_plane.py:82`, `src/ai_engineering/config/mirror_inventory.py:149`, `src/ai_engineering/validator/_shared.py:115`, `scripts/run_loop_skill_evals.py:64`
- Principles applied: §10.7 Clean Code (verify before edit)
- Gate: line-numbers in plan match repo HEAD; any drift flagged and plan amended before Phase 2

## Phase 1 — Scaffold destination directories

- [x] T-101 — Create `.ai-engineering/reference/` with `.gitkeep`
- Agent: build
- Files: `.ai-engineering/reference/.gitkeep`
- Principles applied: §10.3 SOLID Single Responsibility (one home per concern)
- Patch (deterministic):
```
mkdir -p .ai-engineering/reference && touch .ai-engineering/reference/.gitkeep
git add .ai-engineering/reference/.gitkeep
```
- Gate: `ls .ai-engineering/reference/.gitkeep` exits 0

- [x] T-102 — Create `.ai-engineering/runtime/research/`, gitignored
- Agent: build
- Files: `.gitignore`, `.ai-engineering/runtime/research/`
- Principles applied: §10.3 SOLID (runtime state isolated from source)
- Patch (deterministic):
```
mkdir -p .ai-engineering/runtime/research
grep -qxF '.ai-engineering/runtime/research/' .gitignore || echo '.ai-engineering/runtime/research/' >> .gitignore
```
- Gate: `.gitignore` contains the entry; directory exists; no committed files inside

- [x] T-103 — Create `.ai-engineering/runtime/presentations/`, gitignored
- Agent: build
- Files: `.gitignore`
- Principles applied: §10.3 SOLID
- Patch (deterministic):
```
mkdir -p .ai-engineering/runtime/presentations
grep -qxF '.ai-engineering/runtime/presentations/' .gitignore || echo '.ai-engineering/runtime/presentations/' >> .gitignore
```
- Gate: `.gitignore` contains the entry

- [x] T-104 — Create `.ai-engineering/runtime/reports/`, gitignored
- Agent: build
- Files: `.gitignore`
- Principles applied: §10.3 SOLID
- Patch (deterministic):
```
mkdir -p .ai-engineering/runtime/reports
grep -qxF '.ai-engineering/runtime/reports/' .gitignore || echo '.ai-engineering/runtime/reports/' >> .gitignore
```
- Gate: `.gitignore` contains the entry

- [x] T-105 — Verify `.ai-engineering/evals/` exists, committed
- Agent: verify
- Files: `.ai-engineering/evals/`
- Principles applied: §10.6 SDD (D-136-07: corpus committed)
- Gate: directory exists; if not, `mkdir -p .ai-engineering/evals && touch .ai-engineering/evals/.gitkeep`

## Phase 2 — Relocate load-bearing files

Internal commit ordering: each `git mv` lands with the related test/source reference updates so CI stays green at every boundary.

- [x] T-201 — Move 5 `docs/*` → `.ai-engineering/reference/` (principles, mirror-authoring, surface-axioms, cli-reference, model-dispatch-policy)
- Agent: build
- Files: `docs/principles.md`, `docs/mirror-authoring.md`, `docs/surface-axioms.md`, `docs/cli-reference.md`, `docs/model-dispatch-policy.md`
- Principles applied: §10.7 Clean Code (hard rename per CONSTITUTION.md §3)
- Patch (deterministic):
```
git mv docs/principles.md             .ai-engineering/reference/principles.md
git mv docs/mirror-authoring.md       .ai-engineering/reference/mirror-authoring.md
git mv docs/surface-axioms.md         .ai-engineering/reference/surface-axioms.md
git mv docs/cli-reference.md          .ai-engineering/reference/cli-reference.md
git mv docs/model-dispatch-policy.md  .ai-engineering/reference/model-dispatch-policy.md
```
- Gate: `ls .ai-engineering/reference/principles.md` exits 0; `ls docs/principles.md` exits non-zero

- [x] T-202 — Move 13 `.ai-engineering/contexts/*` → `.ai-engineering/reference/`
- Agent: build
- Files: `.ai-engineering/contexts/{architecture-patterns,engineering-standards,harness-engineering,harness-adoption,knowledge-placement,gate-policy,risk-acceptance-flow,mcp-binary-policy,semgrep-update-model,spec-schema,plan-schema,operational-principles,gather-activity-data}.md`
- Principles applied: §10.7 Clean Code
- Patch (deterministic):
```
git mv .ai-engineering/contexts/architecture-patterns.md   .ai-engineering/reference/architecture-patterns.md
git mv .ai-engineering/contexts/engineering-standards.md   .ai-engineering/reference/engineering-standards.md
git mv .ai-engineering/contexts/harness-engineering.md     .ai-engineering/reference/harness-engineering.md
git mv .ai-engineering/contexts/harness-adoption.md        .ai-engineering/reference/harness-adoption.md
git mv .ai-engineering/contexts/knowledge-placement.md     .ai-engineering/reference/knowledge-placement.md
git mv .ai-engineering/contexts/gate-policy.md             .ai-engineering/reference/gate-policy.md
git mv .ai-engineering/contexts/risk-acceptance-flow.md    .ai-engineering/reference/risk-acceptance-flow.md
git mv .ai-engineering/contexts/mcp-binary-policy.md       .ai-engineering/reference/mcp-binary-policy.md
git mv .ai-engineering/contexts/semgrep-update-model.md    .ai-engineering/reference/semgrep-update-model.md
git mv .ai-engineering/contexts/spec-schema.md             .ai-engineering/reference/spec-schema.md
git mv .ai-engineering/contexts/plan-schema.md             .ai-engineering/reference/plan-schema.md
git mv .ai-engineering/contexts/operational-principles.md  .ai-engineering/reference/operational-principles.md
git mv .ai-engineering/contexts/gather-activity-data.md    .ai-engineering/reference/gather-activity-data.md
```
- Gate: `ls .ai-engineering/reference/ | wc -l` ≥ 18 (5 from T-201 + 13 from T-202, plus `.gitkeep`)

- [x] T-203 — Move `docs/solution-intent.md` → `.ai-engineering/solution-intent.md`
- Agent: build
- Files: `docs/solution-intent.md`
- Principles applied: §10.7 Clean Code (D-136-05 top-level placement)
- Patch (deterministic):
```
git mv docs/solution-intent.md .ai-engineering/solution-intent.md
```
- Gate: `ls .ai-engineering/solution-intent.md` exits 0

- [x] T-204 — Move `docs/conformance-report.md` → `.ai-engineering/runtime/reports/conformance.md`
- Agent: build
- Files: `docs/conformance-report.md`
- Principles applied: §10.3 SOLID (runtime artefact under runtime/)
- Patch (deterministic):
```
git mv docs/conformance-report.md .ai-engineering/runtime/reports/conformance.md
```
- Gate: `ls .ai-engineering/runtime/reports/conformance.md` exits 0

- [x] T-205 — Move `.ai-engineering/contexts/team/` → `.ai-engineering/team/`
- Agent: build
- Files: `.ai-engineering/contexts/team/README.md`, `.ai-engineering/contexts/team/lessons.md`
- Principles applied: §10.7 Clean Code (D-136-06)
- Patch (deterministic):
```
git mv .ai-engineering/contexts/team .ai-engineering/team
```
- Gate: `ls .ai-engineering/team/{README.md,lessons.md}` exits 0

- [x] T-206 — Move `evals/*` → `.ai-engineering/evals/`
- Agent: build
- Files: `evals/baseline.json`, `evals/ai-debug.jsonl`, `evals/cli-ux-cross-ide/test_drift_recovery_flow.md`
- Principles applied: §10.7 Clean Code (D-136-07)
- Patch (deterministic):
```
git mv evals/baseline.json                                  .ai-engineering/evals/baseline.json
git mv evals/ai-debug.jsonl                                 .ai-engineering/evals/ai-debug.jsonl
mkdir -p .ai-engineering/evals/cli-ux-cross-ide
git mv evals/cli-ux-cross-ide/test_drift_recovery_flow.md  .ai-engineering/evals/cli-ux-cross-ide/test_drift_recovery_flow.md
```
- Gate: `ls .ai-engineering/evals/baseline.json .ai-engineering/evals/ai-debug.jsonl .ai-engineering/evals/cli-ux-cross-ide/test_drift_recovery_flow.md` exits 0

## Phase 3 — TDD: RED test for fail-loud eval gate (§10.5)

- [x] T-301 — Write failing test: `run_loop_skill_evals --regression` with missing baseline must exit 2
- Agent: build
- Files: `tests/unit/scripts/test_run_loop_skill_evals_fail_loud.py` (NEW)
- Principles applied: §10.5 TDD (RED before GREEN), §10.7 Clean Code (D-136-07)
- Patch (deterministic):
```diff
--- /dev/null
+++ b/tests/unit/scripts/test_run_loop_skill_evals_fail_loud.py
@@
+"""RED test: --regression with missing baseline must fail loud (D-136-07).
+
+Closes the silent gate-degradation footgun: pre-spec-136 the script
+returned 0 with only a stderr warning when the baseline was absent,
+leaving the CI gate green-but-empty.
+"""
+from __future__ import annotations
+
+import subprocess
+import sys
+from pathlib import Path
+
+REPO_ROOT = Path(__file__).resolve().parents[3]
+SCRIPT = REPO_ROOT / "scripts" / "run_loop_skill_evals.py"
+
+
+def test_regression_with_missing_baseline_fails_loud(tmp_path: Path) -> None:
+    missing = tmp_path / "does-not-exist.json"
+    result = subprocess.run(
+        [sys.executable, str(SCRIPT), "--skill", "all", "--regression",
+         "--baseline", str(missing), "--corpus-root", str(tmp_path)],
+        capture_output=True, text=True,
+    )
+    assert result.returncode == 2, (
+        f"expected exit 2 (operational error); got {result.returncode}. "
+        f"stderr: {result.stderr!r}"
+    )
+    assert "baseline" in result.stderr.lower()
+
+
+def test_no_regression_with_missing_baseline_still_passes(tmp_path: Path) -> None:
+    """First-run capture flow preserved when --regression is NOT requested."""
+    missing = tmp_path / "does-not-exist.json"
+    result = subprocess.run(
+        [sys.executable, str(SCRIPT), "--skill", "all",
+         "--baseline", str(missing), "--corpus-root", str(tmp_path)],
+        capture_output=True, text=True,
+    )
+    assert result.returncode == 0
```
- Gate: `pytest tests/unit/scripts/test_run_loop_skill_evals_fail_loud.py -x` FAILS (RED — production still returns 0)

- [x] T-302 — GREEN: Harden `run_loop_skill_evals.py` to fail-loud on `--regression` with missing baseline
- Agent: build
- Files: `scripts/run_loop_skill_evals.py:86-95`
- Principles applied: §10.5 TDD (GREEN), §10.7 Clean Code
- Patch (deterministic):
```diff
--- a/scripts/run_loop_skill_evals.py
+++ b/scripts/run_loop_skill_evals.py
@@
     baseline = load_baseline(args.baseline)
     if not baseline:
-        # Empty baseline ⇒ first-run capture flow. Per
-        # ``ai-reliability-eval --regression`` semantics, the absence of a
-        # baseline is treated as a no-op pass; ``--regression``
-        # only gates after a baseline exists.
-        print(
-            f"no baseline at {args.baseline} — skipping regression gate (first-run capture).",
-            file=sys.stderr,
-        )
-        return 0
+        if args.regression:
+            # spec-136 D-136-07: fail-loud when the operator explicitly
+            # asked for the regression gate but the baseline contract is
+            # missing. Silent green here masked broken CI gates pre-spec-136.
+            print(
+                f"missing baseline at {args.baseline} but --regression was requested; "
+                "the regression gate has no contract to evaluate against. Capture a "
+                "baseline first (drop --regression on the first run).",
+                file=sys.stderr,
+            )
+            return 2
+        # First-run capture flow preserved when --regression is NOT set.
+        print(
+            f"no baseline at {args.baseline} — skipping regression gate "
+            "(first-run capture).",
+            file=sys.stderr,
+        )
+        return 0
```
- Gate: `pytest tests/unit/scripts/test_run_loop_skill_evals_fail_loud.py -x` PASSES (GREEN)

## Phase 4 — Update Python source consumers

- [x] T-401 — `tools/skill_domain/standards.py` retarget 3 path constants
- Agent: build
- Files: `tools/skill_domain/standards.py:84-86`
- Principles applied: §10.7 Clean Code
- Patch (deterministic):
```diff
--- a/tools/skill_domain/standards.py
+++ b/tools/skill_domain/standards.py
@@
-_OPERATIONAL_PRINCIPLES = ".ai-engineering/contexts/operational-principles.md"
-_ENGINEERING_STANDARDS = ".ai-engineering/contexts/engineering-standards.md"
-_HARNESS_ENGINEERING = ".ai-engineering/contexts/harness-engineering.md"
+_OPERATIONAL_PRINCIPLES = ".ai-engineering/reference/operational-principles.md"
+_ENGINEERING_STANDARDS = ".ai-engineering/reference/engineering-standards.md"
+_HARNESS_ENGINEERING = ".ai-engineering/reference/harness-engineering.md"
```
- Gate: `pytest tests/unit/test_engineering_standards.py -x` passes

- [x] T-402 — `tools/skill_lint/checks/md_mirror.py` retarget `_DOCS_TARGETS` (D-136-14)
- Agent: build
- Files: `tools/skill_lint/checks/md_mirror.py:258-263`
- Principles applied: §10.7 Clean Code (preserve safety invariant)
- Patch (deterministic):
```diff
--- a/tools/skill_lint/checks/md_mirror.py
+++ b/tools/skill_lint/checks/md_mirror.py
@@
-# Required `docs/` destinations for the extracted prose.
-_DOCS_TARGETS: tuple[str, ...] = (
-    "docs/principles.md",
-    "docs/mirror-authoring.md",
-    "docs/surface-axioms.md",
-)
+# Required `.ai-engineering/reference/` destinations for the extracted prose
+# (D-136-04 / D-136-14: §10 / §14 / §16 relocated; check retargets, never disappears).
+_DOCS_TARGETS: tuple[str, ...] = (
+    ".ai-engineering/reference/principles.md",
+    ".ai-engineering/reference/mirror-authoring.md",
+    ".ai-engineering/reference/surface-axioms.md",
+)
```
- Gate: `tools/skill_lint --check` reports no `_DOCS_TARGETS` CRITICAL findings

- [x] T-403 — `tools/skill_lint/checks/effort.py` retarget model-dispatch-policy path
- Agent: build
- Files: `tools/skill_lint/checks/effort.py:76`
- Principles applied: §10.7 Clean Code
- Patch (deterministic):
```diff
--- a/tools/skill_lint/checks/effort.py
+++ b/tools/skill_lint/checks/effort.py
@@
-_DEFAULT_POLICY_PATH = Path("docs/model-dispatch-policy.md")
+_DEFAULT_POLICY_PATH = Path(".ai-engineering/reference/model-dispatch-policy.md")
```
- Gate: skill_lint effort check passes

- [x] T-404 — `tools/skill_lint/cli.py` retarget default policy path
- Agent: build
- Files: `tools/skill_lint/cli.py:38`
- Principles applied: §10.7 Clean Code
- Patch (deterministic):
```diff
--- a/tools/skill_lint/cli.py
+++ b/tools/skill_lint/cli.py
@@
-    default=Path("docs/model-dispatch-policy.md"),
+    default=Path(".ai-engineering/reference/model-dispatch-policy.md"),
```
- Gate: `python -m skill_lint --help` prints the new default path

- [x] T-405 — `tools/spec_lint/checks/references.py` retarget `_RESEARCH_MD_RE`
- Agent: build
- Files: `tools/spec_lint/checks/references.py:32`
- Principles applied: §10.7 Clean Code (cache target moves to runtime/research/)
- Patch (deterministic):
```diff
--- a/tools/spec_lint/checks/references.py
+++ b/tools/spec_lint/checks/references.py
@@
-_RESEARCH_MD_RE = re.compile(r"^\.ai-engineering/research/.+\.md$")
+_RESEARCH_MD_RE = re.compile(r"^\.ai-engineering/runtime/research/.+\.md$")
```
- Gate: spec_lint accepts `research:` entries pointing at `.ai-engineering/runtime/research/<name>.md`

- [x] T-406 — `tools/skill_app/eval_runner.py` retarget eval paths
- Agent: build
- Files: `tools/skill_app/eval_runner.py:36,44,46,63`
- Principles applied: §10.7 Clean Code
- Notes: judgment required — match exact prose around each cited line (defaults, docstrings, log strings). Replace literal `"evals/"` with `".ai-engineering/evals/"` and `"evals/baseline.json"` with `".ai-engineering/evals/baseline.json"`; preserve surrounding code shape.
- Gate: `pytest tools/skill_app/test_eval_runner.py -x` passes

- [x] T-407 — `tools/skill_infra/markdown_reporter.py` retarget conformance-report write target
- Agent: build
- Files: `tools/skill_infra/markdown_reporter.py:8,31`
- Principles applied: §10.7 Clean Code
- Notes: replace `docs/conformance-report.md` → `.ai-engineering/runtime/reports/conformance.md` at the two cited sites.
- Gate: reporter writes to the new path; smoke invocation outputs to runtime/reports/

- [x] T-408 — `src/ai_engineering/state/control_plane.py` retarget ownership rules
- Agent: build
- Files: `src/ai_engineering/state/control_plane.py:82,86`
- Principles applied: §10.7 Clean Code, §10.2 YAGNI
- Patch (deterministic):
```diff
--- a/src/ai_engineering/state/control_plane.py
+++ b/src/ai_engineering/state/control_plane.py
@@
-    (".ai-engineering/contexts/team/**", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
+    (".ai-engineering/team/**", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
     (".ai-engineering/LESSONS.md", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.APPEND_ONLY),
     (_CONSTITUTIONAL_PRIMARY, OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
-    (
-        ".ai-engineering/contexts/*.md",
-        OwnershipLevel.FRAMEWORK_MANAGED,
-        FrameworkUpdatePolicy.ALLOW,
-    ),
+    (
+        ".ai-engineering/reference/*.md",
+        OwnershipLevel.FRAMEWORK_MANAGED,
+        FrameworkUpdatePolicy.ALLOW,
+    ),
```
- Gate: ownership tests pass

- [x] T-409 — `src/ai_engineering/config/mirror_inventory.py` retarget governance glob + exclusions
- Agent: build
- Files: `src/ai_engineering/config/mirror_inventory.py:149-150`
- Principles applied: §10.7 Clean Code (drop dead contexts/ + speculative runbooks/ rules)
- Patch (deterministic):
```diff
--- a/src/ai_engineering/config/mirror_inventory.py
+++ b/src/ai_engineering/config/mirror_inventory.py
@@
-_GOVERNANCE_MIRROR_RULE = GovernanceMirrorRule(
-    canonical_rel=".ai-engineering",
-    mirror_rel="src/ai_engineering/templates/.ai-engineering",
-    glob_patterns=("contexts/**/*.md", "runbooks/**/*.md", "README.md"),
-    exclusions=("context/", "contexts/team/", "CONSTITUTION.md", "state/", "evals/", "tasks/"),
-)
+_GOVERNANCE_MIRROR_RULE = GovernanceMirrorRule(
+    canonical_rel=".ai-engineering",
+    mirror_rel="src/ai_engineering/templates/.ai-engineering",
+    glob_patterns=("reference/**/*.md", "README.md"),
+    exclusions=("team/", "CONSTITUTION.md", "state/", "tasks/", "runtime/"),
+)
```
- Gate: `make sync-md` produces a clean diff after Phase 11

- [x] T-410 — `src/ai_engineering/validator/_shared.py` retarget regex + governance mirror tuple
- Agent: build
- Files: `src/ai_engineering/validator/_shared.py:115,232-241`
- Principles applied: §10.7 Clean Code
- Patch (deterministic):
```diff
--- a/src/ai_engineering/validator/_shared.py
+++ b/src/ai_engineering/validator/_shared.py
@@
 _PATH_REF_PATTERN = re.compile(
     r"`?\.?(?:ai-engineering/)?(skills/[^\s`*]+\.md"
     r"|agents/[^\s`*]+\.md"
-    r"|contexts/[^\s`*]+\.md"
+    r"|reference/[^\s`*]+\.md"
     r"|state/spec-[^\s`*]+\.json"
     r"|specs/evidence/[^\s`*]+\.json)`?"
 )
@@
-_GOVERNANCE_MIRROR = (
-    ".ai-engineering",
-    "src/ai_engineering/templates/.ai-engineering",
-    [
-        "contexts/**/*.md",
-        "runbooks/**/*.md",
-        "README.md",
-    ],
- exclusions list:  "context/", "contexts/team/", "CONSTITUTION.md", "state/", "evals/", "tasks/"
-)
+_GOVERNANCE_MIRROR = (
+    ".ai-engineering",
+    "src/ai_engineering/templates/.ai-engineering",
+    [
+        "reference/**/*.md",
+        "README.md",
+    ],
+    ["team/", "CONSTITUTION.md", "state/", "tasks/", "runtime/"],
+)
```
- Gate: validator tests pass

- [x] T-411 — `src/ai_engineering/config/framework_defaults.py` retarget/drop contexts/team/ default
- Agent: build
- Files: `src/ai_engineering/config/framework_defaults.py:131`
- Principles applied: §10.7 Clean Code
- Notes: judgment required — read surrounding context; if entry is `.ai-engineering/contexts/team/**`, replace with `.ai-engineering/team/**`; if entry is deprecated, drop entirely.
- Gate: `pytest tests/unit/config/test_framework_defaults.py -x` passes

- [x] T-412 — `src/ai_engineering/installer/phases/governance.py` retarget contexts/team/ migration map
- Agent: build
- Files: `src/ai_engineering/installer/phases/governance.py:27,29,35`
- Principles applied: §10.7 Clean Code, §10.2 YAGNI
- Notes: judgment required — read the migration map; retarget or drop the entries for contexts/team/, contexts/*.md.
- Gate: installer phase tests pass; `ai-eng install --dry-run` does not reference contexts/team/

- [x] T-413 — `src/ai_engineering/installer/phases/detect.py` drop legacy `context/` → `contexts/` migration
- Agent: build
- Files: `src/ai_engineering/installer/phases/detect.py:103,177`
- Principles applied: §10.2 YAGNI (both source and target gone)
- Gate: installer phase tests pass

- [x] T-414 — `src/ai_engineering/installer/service.py` retarget/drop contexts/team/ exclude
- Agent: build
- Files: `src/ai_engineering/installer/service.py:169,172`
- Principles applied: §10.7 Clean Code
- Notes: retarget contexts/team/ → team/ if still excluded; drop if redundant.
- Gate: installer service tests pass

- [x] T-415 — `src/ai_engineering/updater/service.py` extend `_DEPRECATED_GOVERNANCE_PATHS`
- Agent: build
- Files: `src/ai_engineering/updater/service.py:1200-1217`
- Principles applied: §10.7 Clean Code (consumer migration path, Risk row #11)
- Notes: judgment required — extend `("contexts/team",)` to cover the broader set of deleted paths (`"contexts"`, `"research"`, `"evals"`, framework-owned `docs/*` paths). Confirm migration messages remain clear.
- Gate: updater unit tests pass; updater dry-run shows correct migration messages

- [x] T-416 — `src/ai_engineering/doctor/phases/ide_config.py` drop permissions-migration.md error string
- Agent: build
- Files: `src/ai_engineering/doctor/phases/ide_config.py:167`
- Principles applied: §10.7 Clean Code (file hard-deletes per D-136-13)
- Notes: drop the trailing `"See contexts/permissions-migration.md."` sentence; the error itself is self-explanatory.
- Gate: doctor unit tests pass

- [x] T-417 — `src/ai_engineering/state/observability.py` drop stale comment
- Agent: build
- Files: `src/ai_engineering/state/observability.py:675`
- Principles applied: §10.7 Clean Code
- Notes: read the comment; drop if it references a deleted path.
- Gate: observability unit tests pass

- [x] T-418 — `tools/no_suppression/scanner.py` drop `docs/presentations/**` exclusion
- Agent: build
- Files: `tools/no_suppression/scanner.py:78`
- Principles applied: §10.7 Clean Code
- Patch (deterministic):
```diff
--- a/tools/no_suppression/scanner.py
+++ b/tools/no_suppression/scanner.py
@@
-    "docs/presentations/**",
+    # docs/presentations/ removed by spec-136 D-136-09; no exclusion needed.
```
- Gate: scanner runs without referencing the deleted path

- [x] T-419 — `tools/skill_lint/checks/no_orphan_dirs.py` drop already-deleted contexts/{frameworks,languages}
- Agent: build
- Files: `tools/skill_lint/checks/no_orphan_dirs.py:71-72`
- Principles applied: §10.2 YAGNI
- Notes: drop the two entries; the entire contexts/ parent disappears in Phase 10.
- Gate: orphan-dirs check passes

- [x] T-420 — `scripts/run_loop_skill_evals.py` retarget `--baseline` + `--corpus-root` defaults
- Agent: build
- Files: `scripts/run_loop_skill_evals.py:64-71`
- Principles applied: §10.7 Clean Code
- Patch (deterministic):
```diff
--- a/scripts/run_loop_skill_evals.py
+++ b/scripts/run_loop_skill_evals.py
@@
     parser.add_argument(
         "--baseline",
         type=Path,
-        default=Path("evals/baseline.json"),
-        help="Path to evals/baseline.json (default: evals/baseline.json).",
+        default=Path(".ai-engineering/evals/baseline.json"),
+        help="Path to baseline.json (default: .ai-engineering/evals/baseline.json).",
     )
     parser.add_argument(
         "--corpus-root",
         type=Path,
-        default=Path("evals"),
-        help="Directory containing <skill>.jsonl corpora (default: evals/).",
+        default=Path(".ai-engineering/evals"),
+        help="Directory containing <skill>.jsonl corpora (default: .ai-engineering/evals/).",
     )
```
- Gate: `python scripts/run_loop_skill_evals.py --help` shows the new defaults; fail-loud test (T-301) still passes

- [x] T-421 — `scripts/sync_mirrors/antigravity_target.py` retarget docstring reference
- Agent: build
- Files: `scripts/sync_mirrors/antigravity_target.py:3`
- Principles applied: §10.7 Clean Code
- Notes: drop the `research/ide-hook-engines-2026-05-12.md` docstring citation (the file hard-deletes per D-136-08); replace with a brief module description that does not pin to a specific artefact.
- Gate: module imports cleanly

## Phase 5 — Update test consumers

- [x] T-501 — `tests/unit/test_architecture_patterns_curated_list.py` retarget path
- Agent: build
- Files: `tests/unit/test_architecture_patterns_curated_list.py:17,28` (+10 fixture sites)
- Principles applied: §10.7 Clean Code
- Notes: replace every `.ai-engineering/contexts/architecture-patterns.md` with `.ai-engineering/reference/architecture-patterns.md`.
- Gate: `pytest tests/unit/test_architecture_patterns_curated_list.py -x` passes

- [x] T-502 — `tests/integration/test_architecture_pattern_step.py` retarget path
- Agent: build
- Files: `tests/integration/test_architecture_pattern_step.py:17,28,48`
- Principles applied: §10.7 Clean Code
- Gate: `pytest tests/integration/test_architecture_pattern_step.py -x` passes

- [x] T-503 — `tests/unit/test_engineering_standards.py` retarget triad paths
- Agent: build
- Files: `tests/unit/test_engineering_standards.py:42,45,46,49,51,53`
- Principles applied: §10.7 Clean Code
- Notes: retarget engineering-standards, harness-engineering, harness-adoption from `.ai-engineering/contexts/` → `.ai-engineering/reference/`.
- Gate: `pytest tests/unit/test_engineering_standards.py -x` passes

- [x] T-504 — `tests/conformance/test_md_mirror.py` retarget `_DOCS_TARGETS` expectations
- Agent: build
- Files: `tests/conformance/test_md_mirror.py:357,438,450,456,466,473`
- Principles applied: §10.7 Clean Code
- Notes: retarget docs/{principles,mirror-authoring,surface-axioms}.md → `.ai-engineering/reference/*.md` in test fixtures.
- Gate: `pytest tests/conformance/test_md_mirror.py -x` passes (CRITICAL and OK paths)

- [x] T-505 — `tests/integration/sync/test_canonical_mirror_parity.py` retarget paths
- Agent: build
- Files: `tests/integration/sync/test_canonical_mirror_parity.py:162-260`
- Principles applied: §10.7 Clean Code
- Gate: `pytest tests/integration/sync/test_canonical_mirror_parity.py -x` passes

- [x] T-506 — `tests/integration/test_principle_split_governance.py` retarget paths
- Agent: build
- Files: `tests/integration/test_principle_split_governance.py:45,50,140`
- Principles applied: §10.7 Clean Code
- Notes: `DOCS_PRINCIPLES_MD` → `REFERENCE_PRINCIPLES_MD = REPO_ROOT / ".ai-engineering" / "reference" / "principles.md"`; update `GOVERNANCE_PATHS`.
- Gate: `pytest tests/integration/test_principle_split_governance.py -x` passes

- [x] T-507 — `tests/architecture/test_surface_parity.py` retarget error-string reference
- Agent: build
- Files: `tests/architecture/test_surface_parity.py:91`
- Principles applied: §10.7 Clean Code
- Notes: retarget docs/cli-reference.md citation in the error-string assertion to `.ai-engineering/reference/cli-reference.md`.
- Gate: `pytest tests/architecture/test_surface_parity.py -x` passes

- [x] T-508 — `tests/integration/test_ai_research_tier0.py` retarget research cache path
- Agent: build
- Files: `tests/integration/test_ai_research_tier0.py:5`
- Principles applied: §10.7 Clean Code
- Notes: retarget `.ai-engineering/research/` → `.ai-engineering/runtime/research/`.
- Gate: `pytest tests/integration/test_ai_research_tier0.py -x` passes

- [x] T-509 — `tests/integration/test_brainstorm_research_integration.py` retarget research path
- Agent: build
- Files: `tests/integration/test_brainstorm_research_integration.py:107,109`
- Principles applied: §10.7 Clean Code
- Gate: `pytest tests/integration/test_brainstorm_research_integration.py -x` passes

- [x] T-510 — `tests/unit/skills/ai_research/test_persist.py` retarget persist path
- Agent: build
- Files: `tests/unit/skills/ai_research/test_persist.py:83,99`
- Principles applied: §10.7 Clean Code
- Gate: `pytest tests/unit/skills/ai_research/test_persist.py -x` passes

- [x] T-511 — `tests/integration/_ai_research_persist_helper.py` retarget paths
- Agent: build
- Files: `tests/integration/_ai_research_persist_helper.py:14,142`
- Principles applied: §10.7 Clean Code
- Gate: integration suite re-runs green

- [x] T-512 — `tests/integration/_ai_research_tier0_helper.py` retarget path
- Agent: build
- Files: `tests/integration/_ai_research_tier0_helper.py:359`
- Principles applied: §10.7 Clean Code
- Gate: integration suite green

- [x] T-513 — `tests/unit/test_local_fast_slice_policy.py` retarget error-string reference
- Agent: build
- Files: `tests/unit/test_local_fast_slice_policy.py:461`
- Principles applied: §10.7 Clean Code
- Notes: error-string assertion currently cites `.ai-engineering/contexts/gate-policy.md`; retarget to `.ai-engineering/reference/gate-policy.md`.
- Gate: `pytest tests/unit/test_local_fast_slice_policy.py -x` passes

## Phase 6 — Update skill / agent / handler source files

Canonical source lives under `.claude/`; sync_mirrors regenerates `.codex/`, `.gemini/`, `.opencode/`, `.cursor/`, `.github/`, and `src/ai_engineering/templates/project/**` mirrors automatically (T-1101). Tasks patch the canonical files only.

- [x] T-601 — `.claude/skills/ai-sprint/SKILL.md` retarget Step 5 + gather-activity-data references
- Agent: build
- Files: `.claude/skills/ai-sprint/SKILL.md:31,75,99,102`
- Principles applied: §10.7 Clean Code (D-136-09)
- Notes: lines 31, 75, 99 retarget `.ai-engineering/contexts/gather-activity-data.md` → `.ai-engineering/reference/gather-activity-data.md`; line 102 retargets `docs/presentations/` → `.ai-engineering/runtime/presentations/`.
- Gate: grep `\.ai-engineering/contexts/gather-activity-data\|docs/presentations` in this file returns zero hits

- [x] T-602 — `.claude/skills/ai-standup/SKILL.md` retarget gather-activity-data references
- Agent: build
- Files: `.claude/skills/ai-standup/SKILL.md:36,43`
- Principles applied: §10.7 Clean Code
- Gate: grep clean

- [x] T-603 — `.claude/skills/ai-research/SKILL.md` retarget Tier 0 + persist paths
- Agent: build
- Files: `.claude/skills/ai-research/SKILL.md:16,39,51,96,100`
- Principles applied: §10.7 Clean Code (D-136-08)
- Notes: replace `.ai-engineering/research/` → `.ai-engineering/runtime/research/` at all 5 sites.
- Gate: grep clean

- [x] T-604 — `.claude/skills/ai-research/handlers/persist-artifact.md` retarget persist path
- Agent: build
- Files: `.claude/skills/ai-research/handlers/persist-artifact.md:5,31`
- Principles applied: §10.7 Clean Code
- Gate: grep clean

- [x] T-605 — `.claude/skills/ai-research/handlers/tier0-local.md` retarget cache path
- Agent: build
- Files: `.claude/skills/ai-research/handlers/tier0-local.md`
- Principles applied: §10.7 Clean Code
- Notes: find all `.ai-engineering/research/` references; retarget to `.ai-engineering/runtime/research/`.
- Gate: grep clean

- [x] T-606 — `.claude/skills/ai-docs/handlers/solution-intent-sync.md` retarget path
- Agent: build
- Files: `.claude/skills/ai-docs/handlers/solution-intent-sync.md:5,28,61`
- Principles applied: §10.7 Clean Code (D-136-05)
- Notes: replace `docs/solution-intent.md` → `.ai-engineering/solution-intent.md`.
- Gate: grep clean

- [x] T-607 — `.claude/skills/ai-docs/handlers/solution-intent-init.md` retarget path
- Agent: build
- Files: `.claude/skills/ai-docs/handlers/solution-intent-init.md:5,15,89,106`
- Principles applied: §10.7 Clean Code
- Gate: grep clean

- [x] T-608 — `.claude/skills/ai-docs/handlers/solution-intent-validate.md` retarget path
- Agent: build
- Files: `.claude/skills/ai-docs/handlers/solution-intent-validate.md:10`
- Principles applied: §10.7 Clean Code
- Gate: grep clean

- [x] T-609 — `.claude/skills/ai-docs/handlers/docs-quality-gate.md` retarget path
- Agent: build
- Files: `.claude/skills/ai-docs/handlers/docs-quality-gate.md:32`
- Principles applied: §10.7 Clean Code
- Gate: grep clean

- [x] T-610 — `.claude/skills/ai-reliability-eval/SKILL.md` retarget evals paths
- Agent: build
- Files: `.claude/skills/ai-reliability-eval/SKILL.md:25,35,57,90,96,135,158,168`
- Principles applied: §10.7 Clean Code (D-136-07)
- Notes: replace `evals/` → `.ai-engineering/evals/` at the 8 cited sites; confirm no other sites in the file.
- Gate: grep `^evals/\| evals/\|\"evals/` in this file returns zero hits outside the new `.ai-engineering/evals/` references

- [x] T-611 — `.claude/skills/ai-skill-improve/SKILL.md` retarget evals citation
- Agent: build
- Files: `.claude/skills/ai-skill-improve/SKILL.md:22,24`
- Principles applied: §10.7 Clean Code
- Gate: grep clean

- [x] T-612 — `.claude/agents/reviewer-architecture.md` retarget operational-principles path
- Agent: build
- Files: `.claude/agents/reviewer-architecture.md:13,31`
- Principles applied: §10.7 Clean Code
- Notes: replace `.ai-engineering/contexts/operational-principles.md` → `.ai-engineering/reference/operational-principles.md` at both sites.
- Gate: grep clean

- [x] T-613 — `.claude/agents/reviewer-correctness.md` retarget operational-principles path
- Agent: build
- Files: `.claude/agents/reviewer-correctness.md:11`
- Principles applied: §10.7 Clean Code
- Gate: grep clean

- [x] T-614 — `.claude/agents/reviewer-maintainability.md` retarget operational-principles path
- Agent: build
- Files: `.claude/agents/reviewer-maintainability.md:11`
- Principles applied: §10.7 Clean Code
- Gate: grep clean

- [x] T-615 — `.claude/agents/ai-build.md` retarget operational-principles path
- Agent: build
- Files: `.claude/agents/ai-build.md:13`
- Principles applied: §10.7 Clean Code
- Gate: grep clean

- [x] T-616 — `.claude/skills/ai-test/handlers/tdd.md` retarget operational-principles path
- Agent: build
- Files: `.claude/skills/ai-test/handlers/tdd.md:80`
- Principles applied: §10.7 Clean Code
- Gate: grep clean

- [x] T-617 — `.claude/skills/ai-code/SKILL.md` retarget operational-principles path
- Agent: build
- Files: `.claude/skills/ai-code/SKILL.md:52`
- Principles applied: §10.7 Clean Code
- Gate: grep clean

- [x] T-618 — Repo-wide sweep for residual `\.ai-engineering/contexts/` and `^docs/` skill citations
- Agent: build
- Files: any `.claude/`, `.codex/`, `.gemini/`, `.github/`, `.cursor/`, `.opencode/`, `src/ai_engineering/templates/project/**` skill / agent markdown that earlier tasks missed
- Principles applied: §10.7 Clean Code (zero-residue)
- Notes: `grep -rln "\.ai-engineering/contexts/" .claude/ .codex/ .gemini/ .github/ .cursor/ .opencode/` should return zero after T-601–T-617 + sync_mirrors. Any residual gets a targeted edit here.
- Gate: residual grep returns empty

## Phase 7 — Update canonical mirrors

Author `CLAUDE.md` as the working source; sync_mirrors propagates to AGENTS / GEMINI / copilot-instructions in Phase 11. The 4 mirrors carry byte-identical canonical payload.

- [x] T-701 — CLAUDE.md: retarget §10 pointer rows
- Agent: build
- Files: `CLAUDE.md:19,20,34,35,36,37,118,119,120`
- Principles applied: §10.7 Clean Code (D-136-04 — relocate, do NOT inline)
- Patch (deterministic):
```diff
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@
-Karpathy / Boris one-liners that frame the §10 principles. Full prose
-in [docs/principles.md](docs/principles.md) under "Operating Mindset".
+Karpathy / Boris one-liners that frame the §10 principles. Full prose
+in [.ai-engineering/reference/principles.md](.ai-engineering/reference/principles.md) under "Operating Mindset".
@@
-The eight first-class principles (§10.1 KISS, §10.2 YAGNI, §10.3 SOLID,
-§10.4 DRY, §10.5 TDD, §10.6 SDD, §10.7 Clean Code, §10.8 Hexagonal
-Architecture) live in [docs/principles.md](docs/principles.md). Every
-SKILL.md `## Workflow` cites at least one §10.x anchor; anchors are
-stable at the new home.
+The eight first-class principles (§10.1 KISS, §10.2 YAGNI, §10.3 SOLID,
+§10.4 DRY, §10.5 TDD, §10.6 SDD, §10.7 Clean Code, §10.8 Hexagonal
+Architecture) live in [.ai-engineering/reference/principles.md](.ai-engineering/reference/principles.md).
+Every SKILL.md `## Workflow` cites at least one §10.x anchor; anchors
+are stable at the new home.
@@
-- **§10 Engineering Principles** → [docs/principles.md](docs/principles.md)
-  (§10.1 KISS through §10.8 Hexagonal Architecture; the 34 skill /
-  agent files that cite `§10.x` resolve here).
+- **§10 Engineering Principles** → [.ai-engineering/reference/principles.md](.ai-engineering/reference/principles.md)
+  (§10.1 KISS through §10.8 Hexagonal Architecture; the 76 skill /
+  agent files that cite `§10.x` resolve here).
```
- Gate: `grep "docs/principles\.md" CLAUDE.md` returns zero hits

- [x] T-702 — CLAUDE.md: retarget §14/§15/§16 pointer rows
- Agent: build
- Files: `CLAUDE.md:121,122,125`
- Principles applied: §10.7 Clean Code
- Notes: judgment required — read existing wording around §14/§15/§16 references; retarget docs/mirror-authoring.md → `.ai-engineering/reference/mirror-authoring.md` and docs/surface-axioms.md → `.ai-engineering/reference/surface-axioms.md`; preserve sentence structure.
- Gate: grep `docs/mirror-authoring\|docs/surface-axioms` in CLAUDE.md returns zero hits

- [x] T-703 — CLAUDE.md: retarget Source-of-Truth table at §12
- Agent: build
- Files: `CLAUDE.md:82`
- Principles applied: §10.7 Clean Code
- Patch (deterministic):
```diff
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@
-| Placement contract | `.ai-engineering/contexts/knowledge-placement.md` |
+| Placement contract | `.ai-engineering/reference/knowledge-placement.md` |
```
- Gate: grep clean

- [x] T-704 — CLAUDE.md: absorb Engram install snippet at `Optional: Engram` section
- Agent: build
- Files: `CLAUDE.md:185`
- Principles applied: §10.7 Clean Code (D-136-10)
- Notes: judgment required. Read `docs/integrations/engram.md` first; absorb the install commands (brew / pip / cargo / npm) and the `engram setup claude_code` post-step inline at the `Optional: Engram` section. Replace the "See `docs/integrations/engram.md`" pointer with the inline content. Keep prose tight (~10–15 lines added).
- Gate: section no longer references docs/integrations/engram.md; engram install commands are inline

## Phase 8 — Update CI workflows

- [x] T-801 — `.github/workflows/ci-check.yml` drop `docs/**` trigger
- Agent: build
- Files: `.github/workflows/ci-check.yml:10,17`
- Principles applied: §10.2 YAGNI
- Patch (deterministic):
```diff
--- a/.github/workflows/ci-check.yml
+++ b/.github/workflows/ci-check.yml
@@
-      - 'docs/**'
```
- Notes: two cited sites (one in `push:` paths, one in `pull_request:` paths). Drop each.
- Gate: workflow YAML parses; no PR trigger on docs-only changes

- [x] T-802 — `.github/workflows/skill-evals.yml` retarget evals paths
- Agent: build
- Files: `.github/workflows/skill-evals.yml:20,75,76`
- Principles applied: §10.7 Clean Code (D-136-07)
- Patch (deterministic):
```diff
--- a/.github/workflows/skill-evals.yml
+++ b/.github/workflows/skill-evals.yml
@@
-      - 'evals/**'
+      - '.ai-engineering/evals/**'
@@
-          --baseline evals/baseline.json \
-          --corpus-root evals/
+          --baseline .ai-engineering/evals/baseline.json \
+          --corpus-root .ai-engineering/evals/
```
- Gate: workflow YAML parses

## Phase 9 — Update README + CONTRIBUTING

- [x] T-901 — `README.md` update doc links
- Agent: build
- Files: `README.md:59,65,75`
- Principles applied: §10.7 Clean Code (no broken links)
- Notes: 3 link edits — (1) drop `docs/getting-started.md` link (content gone); (2) drop `docs/integrations/engram.md` link (content folded into CLAUDE.md); (3) retarget `docs/cli-reference.md` → `.ai-engineering/reference/cli-reference.md`. Confirm surrounding sentence reads naturally after each edit.
- Gate: `grep "docs/" README.md` returns zero hits

- [x] T-902 — `CONTRIBUTING.md` update doc links if present
- Agent: build
- Files: `CONTRIBUTING.md`
- Principles applied: §10.7 Clean Code
- Notes: read the file; retarget or drop any references to deleted/moved docs/* paths. Likely site: line ~141.
- Gate: `grep "docs/" CONTRIBUTING.md` returns zero hits

## Phase 10 — Hard delete old surfaces

All preceding phases must land green before any task in this phase runs.

- [x] T-1001 — `git rm` `.ai-engineering/contexts/*` (8 low-load files; 13 relocated already gone)
- Agent: build
- Files: `.ai-engineering/contexts/{cli-ux,evidence-protocol,mcp-integrations,permissions-migration,python-env-modes,session-governance,sentinel-iocs-update,stack-context}.md`
- Principles applied: §10.7 Clean Code (D-136-01, D-136-13)
- Patch (deterministic):
```
git rm .ai-engineering/contexts/cli-ux.md
git rm .ai-engineering/contexts/evidence-protocol.md
git rm .ai-engineering/contexts/mcp-integrations.md
git rm .ai-engineering/contexts/permissions-migration.md
git rm .ai-engineering/contexts/python-env-modes.md
git rm .ai-engineering/contexts/session-governance.md
git rm .ai-engineering/contexts/sentinel-iocs-update.md
git rm .ai-engineering/contexts/stack-context.md
git rm -r --ignore-unmatch .ai-engineering/contexts
```
- Gate: `ls .ai-engineering/contexts 2>/dev/null` returns nothing

- [x] T-1002 — `git rm -r .ai-engineering/research/`
- Agent: build
- Files: `.ai-engineering/research/{ide-hook-engines-2026-05-12,stack-classification-2026-05-12,git-branch-cleanup-modes-2026-05-12}.md`
- Principles applied: §10.7 Clean Code (D-136-08)
- Patch (deterministic):
```
git rm -r .ai-engineering/research
```
- Gate: directory gone

- [x] T-1003 — `git rm -r evals/` at repo root
- Agent: build
- Files: `evals/.gitkeep`, `evals/cli-ux-cross-ide/` (now empty after T-206)
- Principles applied: §10.7 Clean Code (D-136-07)
- Patch (deterministic):
```
git rm -r --ignore-unmatch evals
```
- Gate: `ls evals 2>/dev/null` returns nothing

- [x] T-1004 — `git rm` framework-owned `docs/*` (preserve `*.pen`)
- Agent: build
- Files: `docs/{anti-patterns,copilot-subagents,agentsview-source-contract,ci-alpine-smoke,getting-started}.md`, `docs/integrations/{engram,antigravity}.md`, `docs/architecture/dir-schemas.md`, `docs/presentations/` (all 8 files), `docs/svg/` if present; KEEP `docs/design.pen` and `docs/untitled.pen`
- Principles applied: §10.7 Clean Code (D-136-02 — docs/ is consumer-owned; *.pen survives)
- Patch (deterministic):
```
git rm docs/anti-patterns.md
git rm docs/copilot-subagents.md
git rm docs/agentsview-source-contract.md
git rm docs/ci-alpine-smoke.md
git rm docs/getting-started.md
git rm docs/integrations/engram.md
git rm docs/integrations/antigravity.md
git rm -r --ignore-unmatch docs/integrations
git rm docs/architecture/dir-schemas.md
git rm -r --ignore-unmatch docs/architecture
git rm -r docs/presentations
git rm -r --ignore-unmatch docs/svg
test "$(ls docs/ | sort | tr '\n' ' ')" = "design.pen untitled.pen "
```
- Gate: `ls docs/` lists ONLY `design.pen` and `untitled.pen`

- [x] T-1005 — `git rm -r src/ai_engineering/templates/.ai-engineering/contexts/`
- Agent: build
- Files: `src/ai_engineering/templates/.ai-engineering/contexts/` (entire subtree, ~21 files)
- Principles applied: §10.7 Clean Code (template mirror parity — Risk row #5)
- Patch (deterministic):
```
git rm -r src/ai_engineering/templates/.ai-engineering/contexts
```
- Gate: directory gone

## Phase 11 — Regenerate IDE-specific mirrors via sync_mirrors

- [x] T-1101 — Run `make sync-md` to regenerate all mirror surfaces
- Agent: build
- Files: `.codex/**`, `.gemini/**`, `.opencode/**`, `.cursor/**`, `.github/skills/**`, `.github/agents/**`, `src/ai_engineering/templates/project/**`
- Principles applied: §10.4 DRY (single canonical source; mirrors derived)
- Patch (deterministic):
```
make sync-md
git status --short
git add -A
```
- Gate: `make sync-md` produces no diff on second run; `tests/integration/sync/test_canonical_mirror_parity.py` passes

- [x] T-1102 — Verify mirror parity tests green
- Agent: verify
- Files: `tests/integration/sync/test_canonical_mirror_parity.py`, `tests/architecture/test_surface_parity.py`
- Principles applied: §10.7 Clean Code (mirror invariant)
- Gate: both tests pass

## Phase 12 — CHANGELOG

- [x] T-1201 — Add spec-136 entry to `CHANGELOG.md` under `## [Unreleased]`
- Agent: build
- Files: `CHANGELOG.md:8-9`
- Principles applied: §10.7 Clean Code, CONSTITUTION.md §3
- Patch (deterministic):
```diff
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@
 ## [Unreleased]

+### spec-136 — Prune low-value surfaces (`docs/`, `contexts/`, `research/`, `evals/`)
+
+Hard rename per `CONSTITUTION.md §3`. Four top-level knowledge surfaces
+(`.ai-engineering/contexts/`, `.ai-engineering/research/`, `docs/`,
+`evals/`) collapse into one coherent home (`.ai-engineering/reference/`)
+plus runtime state under `.ai-engineering/runtime/{research,presentations,reports}/`
+and a committed eval corpus at `.ai-engineering/evals/`. `docs/` is now
+reserved for the consumer project that installs ai-engineering; the
+framework owns nothing under `docs/` (D-136-02). Operator-as-dogfooder
+`docs/*.pen` files survive.
+
+#### BREAKING CHANGES — spec-136 D-136-01
+
+**Moved**:
+
+- `docs/principles.md` → `.ai-engineering/reference/principles.md`
+- `docs/mirror-authoring.md` → `.ai-engineering/reference/mirror-authoring.md`
+- `docs/surface-axioms.md` → `.ai-engineering/reference/surface-axioms.md`
+- `docs/cli-reference.md` → `.ai-engineering/reference/cli-reference.md`
+- `docs/model-dispatch-policy.md` → `.ai-engineering/reference/model-dispatch-policy.md`
+- `docs/solution-intent.md` → `.ai-engineering/solution-intent.md`
+- `docs/conformance-report.md` → `.ai-engineering/runtime/reports/conformance.md`
+- `.ai-engineering/contexts/{architecture-patterns,engineering-standards,harness-engineering,harness-adoption,knowledge-placement,gate-policy,risk-acceptance-flow,mcp-binary-policy,semgrep-update-model,spec-schema,plan-schema,operational-principles,gather-activity-data}.md` → `.ai-engineering/reference/`
+- `.ai-engineering/contexts/team/` → `.ai-engineering/team/`
+- `evals/baseline.json` + `evals/ai-debug.jsonl` + `evals/cli-ux-cross-ide/` → `.ai-engineering/evals/`
+
+**Removed**:
+
+- `docs/{anti-patterns,copilot-subagents,agentsview-source-contract,ci-alpine-smoke,getting-started}.md` — no test or skill consumer.
+- `docs/integrations/{antigravity,engram}.md` — engram install snippet folded into `CLAUDE.md Optional: Engram` (D-136-10); antigravity doc had no consumer.
+- `docs/architecture/dir-schemas.md`, `docs/presentations/` (all 8 files), `docs/svg/` — operator export artefacts misplaced in source tree (D-136-09).
+- `.ai-engineering/contexts/{cli-ux,evidence-protocol,mcp-integrations,permissions-migration,python-env-modes,session-governance,sentinel-iocs-update,stack-context}.md` — no current consumer (D-136-13).
+- `.ai-engineering/research/{ide-hook-engines,stack-classification,git-branch-cleanup-modes}-2026-05-12.md` — dated spec-133 artefacts; cache rebuilds at new path (D-136-08).
+- `evals/.gitkeep` and `evals/` parent dir.
+- `src/ai_engineering/templates/.ai-engineering/contexts/` — template mirror of deleted live source.
+
+**Changed**:
+
+- `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` / `.github/copilot-instructions.md` — pointer rows retarget from `docs/` to `.ai-engineering/reference/`; placement-contract row retargets; Engram install snippet inlined into `Optional: Engram` section.
+- `scripts/run_loop_skill_evals.py` — fail-loud on `--regression` with missing baseline (D-136-07); closes the silent gate-degradation footgun.
+- `tools/skill_lint/checks/md_mirror.py` — `_DOCS_TARGETS` retargets to `.ai-engineering/reference/`; CRITICAL-on-missing safety invariant preserved (D-136-14).
+- `src/ai_engineering/{state/control_plane,config/{mirror_inventory,framework_defaults},validator/_shared,installer/{phases/{governance,detect},service},updater/service,doctor/phases/ide_config,state/observability}.py` — drop dead ownership / exclusion / migration rules for the deleted paths.
+- `tools/{skill_domain/standards,skill_lint/checks/effort,skill_lint/cli,spec_lint/checks/references,skill_app/eval_runner,skill_infra/markdown_reporter,no_suppression/scanner}.py` — retarget path strings to new homes.
+- `.github/workflows/ci-check.yml` — drop `'docs/**'` PR trigger.
+- `.github/workflows/skill-evals.yml` — retarget corpus paths to `.ai-engineering/evals/`.
+- `README.md` — drop stale links to deleted docs; retarget cli-reference link to `.ai-engineering/reference/`.
+- 76 `§10.x` citations across skill / agent files — anchor strings unchanged; pointer rows in mirrors retarget.
+
+Migration: consumers run `ai-eng update` after this lands; the updater's
+deprecation logic extends to cover the deleted paths (T-415).
+
 ### spec-134 Wave 4 — Hard-rename wave for ambiguous skill / agent names
```
- Gate: CHANGELOG validates; entry under `## [Unreleased]` before prior spec entries

## Phase 13 — Final verification

- [x] T-1301 — Repo-wide grep: zero residual references to deleted paths
- Agent: verify
- Files: entire repo
- Principles applied: §10.7 Clean Code (zero-residue)
- Patch (deterministic):
```
grep -rln "\.ai-engineering/contexts/" \
  --include='*.py' --include='*.md' --include='*.yml' --include='*.json' \
  --exclude-dir='.ai-engineering/specs/archive' \
  --exclude-dir='.ai-engineering/specs/drafts' \
  . | head
grep -rln "\.ai-engineering/research/" \
  --include='*.py' --include='*.md' --include='*.yml' --include='*.json' \
  --exclude-dir='.ai-engineering/specs/archive' \
  --exclude-dir='.ai-engineering/specs/drafts' \
  . | head
grep -rln "docs/principles\|docs/mirror-authoring\|docs/surface-axioms\|docs/cli-reference\|docs/model-dispatch-policy\|docs/solution-intent\|docs/conformance-report\|docs/presentations\|docs/getting-started\|docs/integrations\|docs/architecture/dir-schemas" \
  --include='*.py' --include='*.md' --include='*.yml' --include='*.json' \
  --exclude-dir='.ai-engineering/specs/archive' \
  --exclude-dir='.ai-engineering/specs/drafts' \
  . | head
grep -rln "^evals/\|/evals/\|\"evals/" \
  --include='*.py' --include='*.md' --include='*.yml' --include='*.json' \
  --exclude-dir='.ai-engineering/specs/archive' \
  --exclude-dir='.ai-engineering/specs/drafts' \
  --exclude='CHANGELOG.md' \
  . | head
```
- Gate: every grep prints nothing

- [x] T-1302 — `tools/skill_lint --check` passes
- Agent: verify
- Files: tooling output only
- Principles applied: §10.7 Clean Code
- Gate: skill_lint exits 0 with no CRITICAL findings

- [x] T-1303 — Full unit test suite green
- Agent: verify
- Files: `tests/unit/`
- Principles applied: §10.5 TDD (stays green)
- Patch (deterministic):
```
pytest tests/unit -x
```
- Gate: exit 0

- [x] T-1304 — Full integration test suite green
- Agent: verify
- Files: `tests/integration/`
- Principles applied: §10.5 TDD
- Patch (deterministic):
```
pytest tests/integration -x
```
- Gate: exit 0

- [x] T-1305 — Conformance test suite green
- Agent: verify
- Files: `tests/conformance/`
- Principles applied: §10.5 TDD
- Patch (deterministic):
```
pytest tests/conformance -x
```
- Gate: exit 0

- [x] T-1306 — Architecture test suite green
- Agent: verify
- Files: `tests/architecture/`
- Principles applied: §10.5 TDD
- Patch (deterministic):
```
pytest tests/architecture -x
```
- Gate: exit 0

- [x] T-1307 — E2E test suite green
- Agent: verify
- Files: `tests/e2e/`
- Principles applied: §10.5 TDD
- Patch (deterministic):
```
pytest tests/e2e -x
```
- Gate: exit 0

- [x] T-1308 — `make sync-md` produces zero diff
- Agent: verify
- Files: all mirror surfaces
- Principles applied: §10.4 DRY
- Patch (deterministic):
```
make sync-md
git diff --exit-code
```
- Gate: `git diff --exit-code` returns 0

- [x] T-1309 — Manual smoke: `/ai-research`, `/ai-docs`, `/ai-reliability-eval`, `/ai-sprint`, `/ai-brainstorm`
- Agent: verify
- Files: skill behavior end-to-end
- Principles applied: §10.6 SDD (behavioural acceptance)
- Notes: each skill invocation must read from the new path and complete its first step without error.
- Gate: each smoke run completes without referencing any deleted path

- [x] T-1310 — Confirm `docs/` survivors are only `*.pen`
- Agent: verify
- Files: `docs/`
- Principles applied: D-136-02
- Patch (deterministic):
```
test "$(ls docs/ | sort | tr '\n' ' ')" = "design.pen untitled.pen "
```
- Gate: equality holds

## Self-Review

Two iterations applied per `/ai-plan` skill contract (§10.7 Clean Code):

**Iteration 1 — internal review**:
- Coverage: every reference in spec Goals 1–14 maps to one or more tasks. ✓
- Each task is bite-sized (single concern, ≤5 min). ✓
- TDD pair present for the eval fail-loud change (T-301 RED → T-302 GREEN). ✓
- Deterministic patches included for ~70 % of build tasks; remaining tasks (judgment-required edits in updater logic, doctor error strings, README link wording) carry prose notes. ✓
- Internal commit ordering preserves CI green at every boundary. ✓

**Iteration 2 — adversarial review**:
- Q: "Does any task leave a window where `_DOCS_TARGETS` points at a file that no longer exists?" A: No — T-402 retargets in the same commit boundary as T-504 (test-fixture retarget); T-1004 (the `git rm` of docs/principles.md) is downstream of both.
- Q: "Does deleting `docs/integrations/engram.md` (T-1004) before T-704 absorbs the snippet risk losing content?" A: No — Phase 7 (T-704) precedes Phase 10 (T-1004); T-704 reads and inlines the prose first.
- Q: "Does the template-mirror delete (T-1005) race the governance-mirror rule update (T-409 / T-410)?" A: No — T-409 + T-410 drop the `contexts/**` glob; T-1005 deletes the mirror tree; T-1101 sync_mirrors confirms parity.
- Q: "Does the fail-loud hardening (T-302) break any existing CI invocation?" A: No — existing CI uses `--regression` explicitly; missing-baseline without `--regression` keeps prior return-0 behavior.
- Q: "Are there hidden CHANGELOG / README links not in the brief?" A: T-1301 grep sweep catches residuals; T-902 inspects CONTRIBUTING. Risk row #10 acknowledges hidden-consumer surfacing.

No iteration-3 changes required.

## STOP — operator runs `/ai-build`

Plan written. `/ai-build` consumes this file and dispatches the build agent with `effort: cheap / model_tier: haiku` on tasks carrying a deterministic patch (~40 of the 65 tasks); `effort: mid / model_tier: sonnet` on judgment tasks (~25 tasks); `effort: high / model_tier: opus` only if operator passes `--max-effort`.

## Quality Outcome

Round 1: 5 blockers, 5 criticals, 6 highs from review agent (B-01..B-05, C-01..C-05, H-01..H-06).
  Resolved in this session by operator re-invocation:
  - B-01 fixed: src/ai_engineering/state/observability.py shared_contexts emitter dropped (D-136-13 follow-through).
  - B-02/B-03 fixed: tests/docs/test_links.py retargeted (asserts absence; README link assert dropped).
  - B-04 fixed: tests/e2e/test_install_clean.py required_dirs swap contexts → reference.
  - B-05 fixed: src/ai_engineering/templates/.ai-engineering/reference/spec-schema.md copied from canonical, sync re-run.
  - C-01..C-05 fixed: .ai-engineering/{team/README.md, README.md, solution-intent.md} prose retargeted to reference/.
  - H-01..H-06 fixed: 8 E501 line-length wraps, references.py docstring + error string, observability test fixture seed.

Round 2 (post-fix verification):
  - ruff: All checks passed (0 errors).
  - spec_lint: 0 BLOCKERS, 3 ADVISORIES (optional frontmatter keys).
  - sync_mirrors: idempotent (1387 mirror files in sync).
  - Unit suite (5390+ tests): green.
  - Architecture (19): green.
  - Conformance (37): green.
  - Integration: green except 3 known pre-existing failures unrelated to spec-136 (manifest count parity + spec-132 canonical slot — verified at base commit 0b4827d0).

Final: 0 blockers, 0 criticals, 0 highs → PASS (proceeding to Phase 5 Deliver per `handlers/no-hitl.md` Step 3 shape 1 "Clean completion").
