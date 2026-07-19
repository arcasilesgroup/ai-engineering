---
title: "spec-188 skillmap-signal-recovery — execution plan"
spec: spec-188
status: approved
execution_route:
  version: 1
  spec: spec-188
  executor: build
  automation: assisted
  concern_count: 1
  estimated_files: 6
  reason: "Single concern (spec-frontmatter integrity): 3 mechanical archive doc-fixes + one additive YAML-strict gate with TDD; <=6 files, no sub-spec decomposition, no cross-surface mirror parity (tools/spec_lint is framework-dev-only, not a shipped template)."
  safe_next_command: "/ai-build"
---

# spec-188 skillmap-signal-recovery — execution plan

Pipeline: **standard**. Executor: **build**. Architecture pattern: **ad-hoc**
(targeted gate hardening + doc fixes; no new module boundary).

Contract: spec-188 (`.ai-engineering/specs/spec.md`, `status: approved`). Two
concerns collapse to one goal — spec-frontmatter integrity: (A) fix the 3 real
malformed-doc bugs `sm` found in the frozen archive, (B) harden `spec_lint` to
fail closed on non-YAML frontmatter so the framework catches the bug-class itself.

TDD ordering: the RED regression test (T-2.1) precedes the GREEN gate change
(T-2.2). Phase 1 (archive fixes) lands before Phase 3 verify so the hardened
check finds the governed corpus clean.

---

## Phase 1 — Fix the 3 real bugs sm found (mechanical)

- [x] T-1.1 — Quote the spec-186 archive spec.md title (fix invalid YAML)
  - Agent: build
  - Files: `.ai-engineering/specs/archive/spec-186-client-value-comms-lens/spec.md:4`
  - Principles applied: §10.1 KISS, §13.3 hard edit no shim
  - Patch (deterministic):
    ```diff
    --- a/.ai-engineering/specs/archive/spec-186-client-value-comms-lens/spec.md
    +++ b/.ai-engineering/specs/archive/spec-186-client-value-comms-lens/spec.md
    @@ -1,5 +1,5 @@
     ---
     spec: spec-186
     slug: client-value-comms-lens
    -title: spec-186 — Client-Value Lens: stakeholder-legible communication for the skill chain
    +title: "spec-186 — Client-Value Lens: stakeholder-legible communication for the skill chain"
     status: approved
    ```
  - Gate: `python -c "import yaml,pathlib; yaml.safe_load(pathlib.Path('.ai-engineering/specs/archive/spec-186-client-value-comms-lens/spec.md').read_text().split('---')[1])"` exits 0.
  - effort: cheap / model_tier: haiku

- [x] T-1.2 — Quote the spec-186 archive plan.md title (fix invalid YAML)
  - Agent: build
  - Files: `.ai-engineering/specs/archive/spec-186-client-value-comms-lens/plan.md:2`
  - Principles applied: §10.1 KISS, §13.3 hard edit no shim
  - Patch (deterministic):
    ```diff
    --- a/.ai-engineering/specs/archive/spec-186-client-value-comms-lens/plan.md
    +++ b/.ai-engineering/specs/archive/spec-186-client-value-comms-lens/plan.md
    @@ -1,3 +1,3 @@
     ---
    -title: spec-186 — Client-Value Lens: stakeholder-legible communication — execution plan
    +title: "spec-186 — Client-Value Lens: stakeholder-legible communication — execution plan"
     spec: spec-186
    ```
  - Gate: `yaml.safe_load` of the plan.md frontmatter block exits 0.
  - effort: cheap / model_tier: haiku

- [x] T-1.3 — Balance the unbalanced inline backtick in spec-177 archive plan.md
  - Agent: build
  - Files: `.ai-engineering/specs/archive/spec-177-docs-rewrite-visual-system/plan.md:142`
  - Principles applied: §10.1 KISS
  - Patch (deterministic): on L142 the prose contains a stray inline triple-backtick
    token `` ```text `` (21 backticks on the line → odd/unbalanced). Remove the three
    literal backticks of that token only: replace the substring `` the plain ```text block ``
    with `the plain text block`. This drops 3 backticks (21 → 18, balanced) and preserves
    meaning. Change nothing else on the line.
  - Gate: line 142 backtick count is even; `sm check --analyzers core/backtick-unbalanced` (if run) reports 0 for this file. Deterministic local gate: the plan file has no odd-backtick inline line outside code fences.
  - effort: cheap / model_tier: haiku

---

## Phase 2 — Harden spec_lint frontmatter gate (TDD: RED before GREEN)

- [x] T-2.1 — RED: regression test asserting malformed-YAML frontmatter is a BLOCKER
  - Agent: build
  - Files: `tests/unit/test_spec_lint.py`
  - Principles applied: §10.5 TDD (fails before the fix, passes after)
  - Patch (deterministic): append to `tests/unit/test_spec_lint.py`:
    ```python


    def test_frontmatter_malformed_yaml_colon_title_is_blocker(tmp_path: Path) -> None:
        # spec-188 D-188-02 — an unquoted title whose mid-value colon breaks YAML
        # must be a BLOCKER. The stdlib partition parser silently accepted it (that
        # is how the spec-186 bug shipped); spec_lint now strict-parses the block.
        spec_path = tmp_path / "spec.md"
        spec_path.write_text(
            "---\n"
            "spec: spec-999\n"
            "title: spec-999 — Thing: subtitle that breaks yaml\n"
            "status: approved\n"
            "effort: small\n"
            "summary: valid one-line summary\n"
            "---\n\n# Body\n",
            encoding="utf-8",
        )
        results = check_frontmatter(spec_path)
        assert any(
            r.check_name == "frontmatter_yaml_invalid" and r.severity == "BLOCKER"
            for r in results
        )


    def test_frontmatter_quoted_colon_title_passes_yaml(tmp_path: Path) -> None:
        # The quoted form (the spec-186 fix) parses cleanly — no yaml_invalid finding.
        spec_path = tmp_path / "spec.md"
        spec_path.write_text(
            "---\n"
            "spec: spec-999\n"
            'title: "spec-999 — Thing: subtitle that is now quoted"\n'
            "status: approved\n"
            "effort: small\n"
            "summary: valid one-line summary\n"
            "---\n\n# Body\n",
            encoding="utf-8",
        )
        results = check_frontmatter(spec_path)
        assert not any(r.check_name == "frontmatter_yaml_invalid" for r in results)
    ```
  - Gate: `python -m pytest tests/unit/test_spec_lint.py::test_frontmatter_malformed_yaml_colon_title_is_blocker` FAILS (no such check yet) — confirms RED.
  - effort: mid / model_tier: sonnet

- [x] T-2.2 — GREEN: strict-parse the frontmatter block with yaml, emit BLOCKER on YAMLError
  - Agent: build
  - Files: `tools/spec_lint/checks/frontmatter.py`
  - Principles applied: §10.5 TDD, §10.6 SDD, gate-policy.md (integrity gate → fail closed)
  - Patch (deterministic): two hunks. Add the import (isort: third-party group after stdlib):
    ```diff
    @@
     from __future__ import annotations

     import datetime as _dt
     from dataclasses import dataclass
     from pathlib import Path

    +import yaml
    +
     _VALID_SEVERITIES = {"OK", "ADVISORY", "BLOCKER"}
    ```
    Insert the strict-parse check right after `results` is initialised (keep the
    existing `_parse_frontmatter` helper untouched — `decisions.py` imports it):
    ```diff
    @@ def check_frontmatter(spec_path: Path) -> list[CheckResult]:
         results: list[CheckResult] = []

    +    # spec-188 D-188-02 — strict YAML validation of the frontmatter block.
    +    # The stdlib partition parser above tolerates malformed YAML (e.g. an
    +    # unquoted value whose mid-value colon starts a phantom key). spec_lint
    +    # is an integrity gate and must fail closed on frontmatter a real YAML
    +    # parser rejects (gate-policy.md). Block spans the lines between the
    +    # opening fence (line 1) and the closing fence (``fence_line``).
    +    block = "\n".join(text.splitlines()[1 : fence_line - 1])
    +    try:
    +        yaml.safe_load(block)
    +    except yaml.YAMLError as exc:
    +        results.append(
    +            CheckResult(
    +                "frontmatter_yaml_invalid",
    +                "BLOCKER",
    +                f"frontmatter is not valid YAML: {str(exc).splitlines()[0]}",
    +            )
    +        )
    +
         for required in sorted(REQUIRED_FIELDS):
    ```
    Also add `frontmatter_yaml_invalid` to the `check_frontmatter` docstring Emits list.
  - Gate: `python -m pytest tests/unit/test_spec_lint.py::test_frontmatter_malformed_yaml_colon_title_is_blocker tests/unit/test_spec_lint.py::test_frontmatter_quoted_colon_title_passes_yaml` PASSES (RED → GREEN).
  - effort: mid / model_tier: sonnet

---

## Phase 3 — Verify, document, integrate

- [x] T-3.1 — Verify: hardened check finds the governed corpus clean; no regressions
  - Agent: verify
  - Files: repo-wide (read-only)
  - Principles applied: §10.4 Verification-before-done, D-188-05 (scope = governed surfaces)
  - Patch (deterministic): omit — run:
    `python -m spec_lint --check .ai-engineering/specs/spec.md` → 0 BLOCKERs beyond the
    expected `plan_frontmatter_missing`/plan-shape (this plan now has frontmatter, so
    re-check plan.md too); then run the hardened `check_frontmatter` over every
    `.ai-engineering/specs/**/{spec,plan}.md` and confirm the ONLY files that would have
    flagged `frontmatter_yaml_invalid` are the two spec-186 files fixed in Phase 1 (now
    clean). Any other file flagged → STOP and triage (D-188-05), do not auto-edit.
  - Gate: `python -m pytest tests/unit/test_spec_lint.py tests/integration/test_spec_lint_e2e.py tests/perf/test_spec_lint_budget.py` all green; spec_lint median under the 500 ms budget.
  - effort: mid / model_tier: sonnet

- [x] T-3.2 — CHANGELOG entry
  - Agent: build
  - Files: `CHANGELOG.md`
  - Principles applied: §13.3 (document the breakage/change), §10.7 Clean Code
  - Patch (deterministic): under the `Unreleased` heading add:
    ```
    - spec-188: spec_lint frontmatter check now strict-parses YAML and fails closed
      on malformed frontmatter (`frontmatter_yaml_invalid` BLOCKER). Fixed two invalid
      unquoted-colon titles in the archived spec-186 and one unbalanced inline backtick
      in the archived spec-177 plan. skill-map (sm) stays a one-off tool — no sm config
      or CI gate added (reaffirms D-173-03).
    ```
  - Gate: `python -m pytest tests/docs` green (CHANGELOG line-cap / format checks pass).
  - effort: cheap / model_tier: haiku

- [x] T-3.3 — Full-suite green + secrets/format gate
  - Agent: verify
  - Files: repo-wide (read-only)
  - Principles applied: §13.1 secrets gate, §13.6 conventional commit readiness
  - Patch (deterministic): omit — `ai-eng gate pre-commit` (ruff format/lint + gitleaks on
    staged) clean; `python -m pytest tests/unit tests/integration -q` green; confirm no
    `tools/spec_lint` template twin exists to sync (framework-dev-only path).
  - Gate: gate pre-commit exits 0; full unit+integration suite green.
  - effort: mid / model_tier: sonnet

---

## Definition of Done (mirrors spec-188 Acceptance)

- [x] spec-186 spec.md:4 + plan.md:2 titles quoted; both frontmatter blocks `yaml.safe_load`-parse.
- [x] spec-177 plan.md:142 backtick balanced.
- [x] `frontmatter.py` emits `frontmatter_yaml_invalid` BLOCKER on non-YAML frontmatter; `_parse_frontmatter` untouched.
- [x] Regression test red-before / green-after; quoted-form companion passes.
- [x] Full spec_lint unit + e2e + perf suites green; median under 500 ms budget.
- [x] CHANGELOG updated; no sm config / CI gate; no taxonomy or name-pair change.

## Quality Outcome

Single quality round — PASS, no remediation pass needed.

- **TDD**: `frontmatter_yaml_invalid` test RED pre-fix → GREEN post-fix; quoted-form companion passes.
- **Verify (deterministic)**: `gitleaks protect --staged` → 0 leaks; `ruff check` + `ruff format --check` clean on touched files.
- **D-188-05 triage**: hardened check run over all 118 governed spec/plan files → 0 `frontmatter_yaml_invalid` after the spec-186 fix (corpus clean, no surprises).
- **Suites**: spec_lint unit+e2e+perf (57 passed, budget green), docs (514 passed), conformance+unit/docs (174 passed), corpus/frontmatter/history targeted (123 passed).
- **Review**: 9-line additive logic (block-slice → `yaml.safe_load` → BLOCKER on `YAMLError`); off-by-one verified against the fence indices and confirmed by the passing corpus. `_parse_frontmatter` left intact (imported by `decisions.py`). No template twin (`tools/spec_lint` is framework-dev-only).
- **Findings**: none blocker/critical/high.
