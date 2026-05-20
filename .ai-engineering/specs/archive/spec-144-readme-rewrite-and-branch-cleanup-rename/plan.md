---
spec: spec-144
title: README Rewrite and Branch Cleanup Rename
status: draft
pipeline: standard
phases: 6
total: 35
completed: 0
---

# Plan — spec-144 README Rewrite and Branch Cleanup Rename

## Design

Design intent captured at `.ai-engineering/specs/spec-144/design-intent.md` (auto-routed from `/ai-plan` because matched keywords: design system, ui, ux, typography, layout, interface).

## Architecture

**Pattern:** Ports and Adapters.

**Why:** The rename is a port-label change: canonical `.claude/skills/ai-branch-cleanup/` is the port surface, while `.codex/`, `.gemini/`, `.github/`, `.cursor/`, `.opencode/`, `.agent/`, and installer templates are adapters regenerated or verified from the canonical source. The README work follows the same shape: `.ai-engineering/README.md` is the Tier 4 narrative source, `src/ai_engineering/templates/.ai-engineering/README.md` is the install adapter, and tests enforce the adapter stays byte-identical.

**Pipeline classification:** full. The spec touches more than five files, crosses docs/tests/config/skill/template surfaces, includes a hard rename, and requires mirror-sync verification. It remains `pipeline: standard` in frontmatter because this is a single executable `/ai-build` contract rather than an `/ai-autopilot` aggregate plan.

## Gate Strategy

- Section preflight already passed: `ai-eng spec verify --sections .ai-engineering/specs/spec.md`.
- RED/GREEN pairs are explicit for brand contract, README parity, README content, rename guards, and changelog entries.
- Generated mirrors are not hand-edited except when a generator misses a non-generated template; canonical `.claude/` edits precede `ai-eng dev sync`.
- Historical `.ai-engineering/state/framework-events.ndjson`, `.ai-engineering/state/state.db`, archived specs, and prior CHANGELOG sections are read-only except for one new append-only rename audit event.

## Phase 1: Brand Voice Contract

- [ ] T-1.1 — RED: add brand-voice contract test
  - Agent: build
  - Files: tests/unit/docs/test_brand_voice_contract.py:new
  - Principles applied: §10.5 TDD, §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic):
    ```diff
    --- /dev/null
    +++ b/tests/unit/docs/test_brand_voice_contract.py
    @@
    +from pathlib import Path
    +
    +ROOT = Path(__file__).resolve().parents[3]
    +BRAND = ROOT / ".ai-engineering" / "reference" / "brand-voice.md"
    +
    +
    +def test_brand_voice_reference_exists_and_cites_design_sources() -> None:
    +    text = BRAND.read_text(encoding="utf-8")
    +    for needle in ("docs/design.pen:", "docs/untitled.pen:"):
    +        assert needle in text
    +
    +
    +def test_brand_voice_declares_terminal_native_rules() -> None:
    +    text = BRAND.read_text(encoding="utf-8")
    +    for needle in (
    +        "{ai} engineering",
    +        "mid-dot stat line",
    +        "[PASS]",
    +        "[WARN]",
    +        "[FAIL]",
    +        "no emoji",
    +        "bash fences",
    +        "yaml fences",
    +    ):
    +        assert needle in text
    ```
  - Gate: `pytest tests/unit/docs/test_brand_voice_contract.py -q` fails before the reference exists.

- [ ] T-1.2 — GREEN: create prose brand voice source of truth
  - Agent: build
  - Files: .ai-engineering/reference/brand-voice.md:new
  - Principles applied: §10.1 KISS, §10.4 DRY, §10.6 SDD
  - Patch (deterministic): prose synthesis required from `.ai-engineering/specs/spec.md` and `.ai-engineering/specs/spec-144/design-intent.md`; no fixed hunk because the document is authored content, not a mechanical replacement.
  - Gate: `pytest tests/unit/docs/test_brand_voice_contract.py -q` passes.

- [ ] T-1.3 — VERIFY: ensure brand reference contains no anonymous-content violations
  - Agent: verify
  - Files: .ai-engineering/reference/brand-voice.md:new; tests/docs/test_links.py:79
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification.
  - Gate: `pytest tests/docs/test_links.py::test_readme_minimal tests/unit/docs/test_brand_voice_contract.py -q` passes with no `/Users/`, `/home/<name>/`, or conversational PII patterns.

## Phase 2: README Contracts and Rewrite

- [ ] T-2.1 — RED: add governance README/template parity test
  - Agent: build
  - Files: tests/unit/docs/test_governance_readme_template_parity.py:new
  - Principles applied: §10.4 DRY, §10.5 TDD
  - Patch (deterministic):
    ```diff
    --- /dev/null
    +++ b/tests/unit/docs/test_governance_readme_template_parity.py
    @@
    +from pathlib import Path
    +
    +ROOT = Path(__file__).resolve().parents[3]
    +LIVE = ROOT / ".ai-engineering" / "README.md"
    +TEMPLATE = ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "README.md"
    +
    +
    +def test_governance_readme_template_is_byte_identical() -> None:
    +    assert LIVE.exists(), f"missing live governance README: {LIVE}"
    +    assert TEMPLATE.exists(), f"missing template governance README: {TEMPLATE}"
    +    assert LIVE.read_bytes().replace(b"\r\n", b"\n") == TEMPLATE.read_bytes().replace(b"\r\n", b"\n")
    ```
  - Gate: `pytest tests/unit/docs/test_governance_readme_template_parity.py -q` passes today or fails with clear drift after rewrite-only edits.

- [ ] T-2.2 — RED: add README content contract tests
  - Agent: build
  - Files: tests/unit/docs/test_readme_brand_contract.py:new
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic):
    ```diff
    --- /dev/null
    +++ b/tests/unit/docs/test_readme_brand_contract.py
    @@
    +from pathlib import Path
    +
    +ROOT = Path(__file__).resolve().parents[3]
    +
    +
    +def test_root_readme_declares_current_surfaces_and_brand() -> None:
    +    text = (ROOT / "README.md").read_text(encoding="utf-8")
    +    assert "Antigravity" not in text
    +    for surface in ("Claude Code", "GitHub Copilot", "OpenAI Codex", "Gemini CLI", "OpenCode", "Cursor"):
    +        assert surface in text
    +    assert "{ai} engineering" in text
    +    assert "/ai-brainstorm → /ai-plan → /ai-build → /ai-pr" in text
    +    assert len(text.splitlines()) <= 120
    +
    +
    +def test_governance_readme_has_inline_quick_start_and_no_deleted_link() -> None:
    +    text = (ROOT / ".ai-engineering" / "README.md").read_text(encoding="utf-8")
    +    assert "GETTING_STARTED.md" not in text
    +    assert "## Quick Start" in text
    +    assert "ai-eng install" in text
    +    assert "/ai-start" in text
    +    assert "/ai-brainstorm → /ai-plan → /ai-build → /ai-pr" in text
    ```
  - Gate: `pytest tests/unit/docs/test_readme_brand_contract.py -q` fails before README rewrite.

- [ ] T-2.3 — GREEN: rewrite root README hero and install block
  - Agent: build
  - Files: README.md:1
  - Principles applied: §10.1 KISS, §10.7 Clean Code
  - Patch (deterministic): authored replacement of the top section only; preserve existing banner/badge block, then add the approved tagline, a copyable `ai-eng install` command, and the mid-dot stat line.
  - Gate: `python - <<'PY'\nfrom pathlib import Path\ntext=Path('README.md').read_text(); assert '{ai} engineering' in text; assert 'ai-eng install' in text; assert len(text.splitlines()) <= 120\nPY` passes.

- [ ] T-2.4 — GREEN: rewrite root README chain, surfaces, and attribution
  - Agent: build
  - Files: README.md:35
  - Principles applied: §10.4 DRY, §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): authored replacement of the middle/end sections; include `/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`, all six enabled surfaces, required links, and preserve the “Standing on the shoulders of …” attribution table.
  - Gate: `pytest tests/docs/test_links.py::test_readme_minimal tests/unit/docs/test_readme_brand_contract.py::test_root_readme_declares_current_surfaces_and_brand -q` passes.

- [ ] T-2.5 — GREEN: rewrite governance README header and Quick Start
  - Agent: build
  - Files: .ai-engineering/README.md:1
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Patch (deterministic): authored replacement of the top section; remove `GETTING_STARTED.md`, add `## Quick Start`, `ai-eng install`, `/ai-start`, and the canonical chain.
  - Gate: `pytest tests/unit/docs/test_readme_brand_contract.py::test_governance_readme_has_inline_quick_start_and_no_deleted_link -q` passes.

- [ ] T-2.6 — GREEN: rewrite governance README doctrine and sync map
  - Agent: build
  - Files: .ai-engineering/README.md:40
  - Principles applied: §10.4 DRY, §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): authored replacement of persistence, runbook, skill-chain, and sync sections; cite `docs/persistence-doctrine.md`; replace stale `ai-eng sync` mentions with `ai-eng dev sync`.
  - Gate: `rg -n "GETTING_STARTED.md|ai-eng sync( |$)" .ai-engineering/README.md` returns no hits.

- [ ] T-2.7 — GREEN: copy governance README to installer template
  - Agent: build
  - Files: src/ai_engineering/templates/.ai-engineering/README.md:1
  - Principles applied: §10.4 DRY, §10.8 Hexagonal Architecture
  - Patch (deterministic): `cp .ai-engineering/README.md src/ai_engineering/templates/.ai-engineering/README.md`.
  - Gate: `pytest tests/unit/docs/test_governance_readme_template_parity.py -q` passes.

- [ ] T-2.8 — VERIFY: preserve team README placeholder
  - Agent: verify
  - Files: .ai-engineering/team/README.md:1
  - Principles applied: §10.1 KISS, §10.2 YAGNI
  - Patch (deterministic): read-only verification; if no defect is found, leave the file unchanged.
  - Gate: `test "$(wc -l < .ai-engineering/team/README.md | tr -d ' ')" = "4"` passes.

- [ ] T-2.9 — VERIFY: run README/documentation slice
  - Agent: verify
  - Files: README.md:1; .ai-engineering/README.md:1; src/ai_engineering/templates/.ai-engineering/README.md:1; tests/docs/test_links.py:203
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification.
  - Gate: `pytest tests/docs/test_links.py tests/unit/docs/test_brand_voice_contract.py tests/unit/docs/test_readme_brand_contract.py tests/unit/docs/test_governance_readme_template_parity.py -q` passes.

## Phase 3: Canonical Skill Rename

- [ ] T-3.1 — RED: update canonical naming guard for new skill slug
  - Agent: build
  - Files: tests/architecture/test_naming_clarity.py:40
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic):
    ```diff
    --- a/tests/architecture/test_naming_clarity.py
    +++ b/tests/architecture/test_naming_clarity.py
    @@
     _DEPRECATED_SKILLS: tuple[str, ...] = (
    @@
         "ai-write",
         "ai-prompt",
    +    "ai-repo-tidy",
     )
    @@
    -    "ai-repo-tidy",
    +    "ai-branch-cleanup",
    ```
  - Gate: `pytest tests/architecture/test_naming_clarity.py -q` fails before the directory rename.

- [ ] T-3.2 — RED: retarget cleanup/consolidation tests to `/ai-branch-cleanup`
  - Agent: build
  - Files: tests/unit/test_cleanup_history_rotation.py:1; tests/unit/test_consolidate_spec_action.py:1
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): replace active `ai-repo-tidy` paths/caller names with `ai-branch-cleanup`; keep historical spec IDs unchanged.
  - Gate: `pytest tests/unit/test_cleanup_history_rotation.py tests/unit/test_consolidate_spec_action.py -q` fails before canonical rename.

- [ ] T-3.3 — GREEN: rename canonical `.claude` skill directory and self-references
  - Agent: build
  - Files: .claude/skills/ai-repo-tidy/SKILL.md:1 -> .claude/skills/ai-branch-cleanup/SKILL.md:1
  - Principles applied: §10.1 KISS, §10.2 YAGNI, §10.8 Hexagonal Architecture
  - Patch (deterministic):
    ```diff
    git mv .claude/skills/ai-repo-tidy .claude/skills/ai-branch-cleanup
    --- a/.claude/skills/ai-branch-cleanup/SKILL.md
    +++ b/.claude/skills/ai-branch-cleanup/SKILL.md
    @@
    -name: ai-repo-tidy
    +name: ai-branch-cleanup
    @@
    -# Repo Tidy
    +# Branch Cleanup
    ```
    Then replace every active `/ai-repo-tidy` occurrence in that file with `/ai-branch-cleanup`.
  - Gate: `pytest tests/architecture/test_naming_clarity.py tests/unit/test_cleanup_history_rotation.py -q` passes for `.claude` canonical path.

- [ ] T-3.4 — GREEN: update canonical sibling skill references
  - Agent: build
  - Files: .claude/skills/ai-commit/SKILL.md:3; .claude/skills/ai-resolve-conflicts/SKILL.md:3; .claude/skills/ai-autopilot/SKILL.md:84; .claude/skills/ai-pr/SKILL.md:104; .claude/skills/ai-pr/handlers/watch.md:22; .claude/skills/ai-simplify-sweep/SKILL.md:114; .claude/skills/ai-start/SKILL.md:124; .claude/skills/_shared/consolidate-spec.md:5
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Patch (deterministic): replace active `/ai-repo-tidy` and `ai-repo-tidy` caller references with `/ai-branch-cleanup` and `ai-branch-cleanup`.
  - Gate: `rg --hidden -n "ai-repo-tidy" .claude/skills` returns no active hits.

- [ ] T-3.5 — GREEN: update default skill registry key and count comment
  - Agent: build
  - Files: src/ai_engineering/config/framework_defaults.py:249
  - Principles applied: §10.1 KISS, §10.4 DRY
  - Patch (deterministic):
    ```diff
    --- a/src/ai_engineering/config/framework_defaults.py
    +++ b/src/ai_engineering/config/framework_defaults.py
    @@
    -# --- skills registry (48 entries, kept here so /ai-scaffold maintains a single source) ---
    +# --- skills registry (53 entries, kept here so /ai-scaffold maintains a single source) ---
    @@
    -    "ai-repo-tidy": {"type": "delivery", "tags": ["git"]},
    +    "ai-branch-cleanup": {"type": "delivery", "tags": ["git"]},
    ```
  - Gate: `pytest tests/unit/config/test_manifest.py -q` passes.

- [ ] T-3.6 — GREEN: update validator user-facing lifecycle messages
  - Agent: build
  - Files: src/ai_engineering/validator/categories/file_existence.py:282; tests/unit/validator/test_history_md_warn.py:1; tests/unit/installer/test_phases.py:155
  - Principles applied: §10.1 KISS, §10.7 Clean Code
  - Patch (deterministic): replace active `/ai-repo-tidy` references with `/ai-branch-cleanup` in messages/tests; preserve spec-131 IDs.
  - Gate: `pytest tests/unit/validator/test_history_md_warn.py tests/unit/installer/test_phases.py -q` passes.

- [ ] T-3.7 — GREEN: update reference docs and template reference copies
  - Agent: build
  - Files: .ai-engineering/reference/model-dispatch-policy.md:44; .ai-engineering/reference/surface-axioms.md:39; src/ai_engineering/templates/.ai-engineering/reference/model-dispatch-policy.md:44; src/ai_engineering/templates/.ai-engineering/reference/surface-axioms.md:39
  - Principles applied: §10.4 DRY, §10.8 Hexagonal Architecture
  - Patch (deterministic): replace active `ai-repo-tidy` with `ai-branch-cleanup` and copy live reference docs to template counterparts if those reference docs are byte-equivalent mirrors.
  - Gate: `pytest tests/unit/validator/test_mirror_sync_categories.py -q` passes.

- [ ] T-3.8 — GREEN: update session bootstrap live/template footer references
  - Agent: build
  - Files: .ai-engineering/scripts/session_bootstrap.py:1024; src/ai_engineering/templates/.ai-engineering/scripts/session_bootstrap.py:1024; tests/unit/test_session_bootstrap_template_parity.py:1
  - Principles applied: §10.4 DRY, §10.5 TDD
  - Patch (deterministic):
    ```diff
    --- a/.ai-engineering/scripts/session_bootstrap.py
    +++ b/.ai-engineering/scripts/session_bootstrap.py
    @@
    -        lines.append(f"- {pc} pending — run `/ai-repo-tidy` to review")
    +        lines.append(f"- {pc} pending — run `/ai-branch-cleanup` to review")
    @@
    -    lines.append("`/ai-review` review · `/ai-pr` ship · `/ai-test` verify · `/ai-repo-tidy` tidy")
    +    lines.append("`/ai-review` review · `/ai-pr` ship · `/ai-test` verify · `/ai-branch-cleanup` tidy")
    ```
    Copy the same bytes to the template script or apply the same hunk there.
  - Gate: `pytest tests/unit/test_session_bootstrap_template_parity.py tests/unit/scripts/test_session_bootstrap.py -q` passes.

- [ ] T-3.9 — GREEN: update remaining active tests that pin old slug
  - Agent: build
  - Files: tests/perf/test_hot_path_budgets.py:14; tests/mirrors/test_count_parity.py:14
  - Principles applied: §10.1 KISS, §10.7 Clean Code
  - Patch (deterministic): replace active expected slug with `ai-branch-cleanup`; leave old CHANGELOG historical entries untouched unless the line lives in `[Unreleased]`.
  - Gate: `pytest tests/perf/test_hot_path_budgets.py tests/mirrors/test_count_parity.py -q` passes.

- [ ] T-3.10 — VERIFY: canonical rename slice passes
  - Agent: verify
  - Files: .claude/skills/ai-branch-cleanup/SKILL.md:1; src/ai_engineering/config/framework_defaults.py:249; tests/architecture/test_naming_clarity.py:1
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification.
  - Gate: `pytest tests/architecture/test_naming_clarity.py tests/unit/test_cleanup_history_rotation.py tests/unit/test_consolidate_spec_action.py tests/unit/test_session_bootstrap_template_parity.py -q` passes.

## Phase 4: Mirror and Template Propagation

- [ ] T-4.1 — GREEN: regenerate generated IDE and provider mirrors
  - Agent: build
  - Files: .codex/skills/**; .gemini/skills/**; .github/skills/**; src/ai_engineering/templates/project/**
  - Principles applied: §10.4 DRY, §10.8 Hexagonal Architecture
  - Patch (deterministic): run `ai-eng dev sync` from the repository root after canonical `.claude` edits.
  - Gate: `ai-eng dev sync --check` reports mirrors in sync.

- [ ] T-4.2 — GREEN: handle non-generated residual template command names
  - Agent: build
  - Files: src/ai_engineering/templates/project/.opencode/commands/ai-repo-tidy.md:1 -> src/ai_engineering/templates/project/.opencode/commands/ai-branch-cleanup.md:1
  - Principles applied: §10.1 KISS, §10.4 DRY
  - Patch (deterministic): if `ai-eng dev sync` does not delete/regenerate the old command file, `git mv` it to the new command name and replace active slug text inside.
  - Gate: `rg --hidden -n "ai-repo-tidy" src/ai_engineering/templates/project/.opencode/commands` returns no active hits.

- [ ] T-4.3 — VERIFY: mirror generated provenance and parity
  - Agent: verify
  - Files: tests/integration/test_skill_mirror_consistency.py:1; tests/unit/test_template_skill_parity.py:1; tests/integration/test_shared_handler_mirror.py:1
  - Principles applied: §10.4 DRY, §10.5 TDD
  - Patch (deterministic): read-only verification.
  - Gate: `pytest tests/integration/test_skill_mirror_consistency.py tests/unit/test_template_skill_parity.py tests/integration/test_shared_handler_mirror.py -q` passes.

- [ ] T-4.4 — VERIFY: residual old-slug scan with historical allowlist
  - Agent: verify
  - Files: repository-wide grep result
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification; command must fail if active code/docs/tests still contain `ai-repo-tidy` outside `.ai-engineering/state/`, `.ai-engineering/specs/archive/`, `.ai-engineering/specs/drafts/`, and historical CHANGELOG sections before `[Unreleased]`.
  - Gate: `rg --hidden -n "ai-repo-tidy" . --glob '!/.git/**'` reviewed; only allowed historical hits remain.

## Phase 5: Changelog, Audit, and Follow-up Issue

- [ ] T-5.1 — RED: add changelog expectation for current Unreleased rename/docs entries
  - Agent: build
  - Files: tests/unit/docs/test_changelog_spec144.py:new
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic):
    ```diff
    --- /dev/null
    +++ b/tests/unit/docs/test_changelog_spec144.py
    @@
    +from pathlib import Path
    +
    +ROOT = Path(__file__).resolve().parents[3]
    +
    +
    +def _unreleased() -> str:
    +    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    +    start = text.index("## [Unreleased]")
    +    end = text.find("\n## [", start + 1)
    +    return text[start:end if end != -1 else None]
    +
    +
    +def test_spec144_breaking_rename_is_documented() -> None:
    +    block = _unreleased()
    +    assert "### BREAKING" in block
    +    assert "/ai-repo-tidy" in block
    +    assert "/ai-branch-cleanup" in block
    +    assert "no alias" in block.lower() or "no shim" in block.lower()
    +
    +
    +def test_spec144_readme_rewrite_is_documented_as_changed() -> None:
    +    block = _unreleased()
    +    assert "### Changed" in block
    +    assert "README" in block
    +    assert "brand" in block.lower()
    ```
  - Gate: `pytest tests/unit/docs/test_changelog_spec144.py -q` fails before CHANGELOG update.

- [ ] T-5.2 — GREEN: update `[Unreleased]` changelog
  - Agent: build
  - Files: CHANGELOG.md:8
  - Principles applied: §10.2 YAGNI, §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): add `### BREAKING` entry for `/ai-repo-tidy` to `/ai-branch-cleanup` with no alias/shim and add `### Changed` entry for README/brand rewrite; keep prior `### Fixed` release-finalization entry.
  - Gate: `pytest tests/unit/docs/test_changelog_spec144.py tests/unit/test_changelog_parser.py tests/unit/test_changelog_breaking_keywords.py -q` passes.

- [ ] T-5.3 — GREEN: append rename audit event without rewriting history
  - Agent: build
  - Files: .ai-engineering/state/framework-events.ndjson:append-only
  - Principles applied: §10.6 SDD, §10.8 Hexagonal Architecture
  - Patch (deterministic): append one `framework_operation` event using the existing spec lifecycle append helper or equivalent stdlib append under the framework-events lock, with `detail.operation=skill_renamed`, `from=ai-repo-tidy`, `to=ai-branch-cleanup`, `policy_source=CONSTITUTION.md`, and `spec=spec-144`.
  - Gate: `tail -n 20 .ai-engineering/state/framework-events.ndjson | rg '"operation": "skill_renamed"|"operation":"skill_renamed"'` finds the new event.

- [ ] T-5.4 — GUARD: create asset-team follow-up issue or record blocker
  - Agent: guard
  - Files: .ai-engineering/specs/spec-144/asset-follow-up.md:new
  - Principles applied: §10.2 YAGNI, §10.6 SDD
  - Patch (deterministic): if `/ai-issue`/GitHub issue creation is available, create an issue for stale counts in `docs/design.pen:15131` and `docs/untitled.pen:482`; otherwise write `.ai-engineering/specs/spec-144/asset-follow-up.md` with the blocked issue payload for operator filing.
  - Gate: follow-up issue URL exists in the PR body, or the blocked payload file exists and names both stale design-file lines.

## Phase 6: Sanity Review and Final Gates

- [ ] T-6.1 — VERIFY: canonical-doc sanity review report
  - Agent: verify
  - Files: CONSTITUTION.md:1; CLAUDE.md:1; AGENTS.md:1; GEMINI.md:1; .github/copilot-instructions.md:1; .ai-engineering/specs/spec-144/canonical-doc-sanity.md:new
  - Principles applied: §10.3 SOLID, §10.6 SDD
  - Patch (deterministic): create a short report recording zero divergences or listing divergences as follow-up items; do not rewrite canonical mirrors in this task.
  - Gate: `.ai-engineering/specs/spec-144/canonical-doc-sanity.md` exists and states whether any follow-up is needed.

- [ ] T-6.2 — VERIFY: no accidental source changes outside spec scope
  - Agent: verify
  - Files: git diff
  - Principles applied: §10.3 SOLID, §10.7 Clean Code
  - Patch (deterministic): read-only verification.
  - Gate: `git diff --name-only` contains only README/brand docs, rename surfaces, generated mirrors/templates, tests, CHANGELOG, plan/spec artifacts, and append-only audit event.

- [ ] T-6.3 — VERIFY: documentation, rename, mirror, and release-quality gates
  - Agent: verify
  - Files: full repository
  - Principles applied: §10.5 TDD, §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification.
  - Gate: `pytest tests/docs/test_links.py -q && pytest tests/architecture/test_naming_clarity.py tests/unit/test_cleanup_history_rotation.py tests/unit/test_consolidate_spec_action.py -q && ai-eng dev sync --check && ai-eng verify --full` pass.

- [ ] T-6.4 — VERIFY: full test suite
  - Agent: verify
  - Files: full repository
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification.
  - Gate: `pytest -q` passes.

- [ ] T-6.5 — GUARD: PR handoff checklist
  - Agent: guard
  - Files: .ai-engineering/specs/spec-144/pr-handoff.md:new
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): create a PR handoff note that references `spec-144`, the consumed brief, gate results, residual historical grep hits, and the asset follow-up issue/payload.
  - Gate: handoff note exists and contains the commands/results from T-6.3 and T-6.4.

## Approval Gate

This plan is planning-only. `/ai-build` must not run until the operator explicitly approves `.ai-engineering/specs/plan.md`.
