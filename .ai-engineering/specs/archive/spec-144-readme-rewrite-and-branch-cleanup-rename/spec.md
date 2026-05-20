---
spec: spec-144
title: README Rewrite and Branch Cleanup Rename
status: approved
effort: large
summary: Rewrite README surfaces around the governed-flow brand and hard-rename /ai-repo-tidy to /ai-branch-cleanup with no shim, verified by sync, docs, changelog, and rename tests.
refs:
  - brief: .ai-engineering/specs/drafts/readme-rewrite-and-branch-cleanup-rename-brief.md
  - doc: docs/persistence-doctrine.md
  - doc: .ai-engineering/reference/principles.md
---

# Spec 144 - README Rewrite and Branch Cleanup Rename

## Summary

The repository onboarding surface is stale in two user-visible ways: the root README names Antigravity while the active manifest enables OpenCode and Cursor, and the governance README plus installer-template twin link to the deleted `GETTING_STARTED.md`. This spec rewrites the README surfaces around the current `{ai} engineering` brand voice, creates a prose brand-voice reference extracted from the Penpot design sources, and hard-renames `/ai-repo-tidy` to `/ai-branch-cleanup` without a compatibility shim so the skill slug reveals its actual branch-cleanup purpose.

## Goals

- Replace the root `README.md` with a concise landing page that stays at or below the existing 120-line test cap, opens with the design-system tagline, declares the six enabled surfaces from `.ai-engineering/manifest.yml`, preserves the existing attribution table, and points first-time operators to the canonical chain `/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`.
- Rewrite `.ai-engineering/README.md` so it has zero dead links, includes an inline Quick Start instead of pointing to deleted `GETTING_STARTED.md`, explains the four-tier persistence doctrine, and uses the same terminal-native brand voice as the root README.
- Keep `src/ai_engineering/templates/.ai-engineering/README.md` byte-identical to `.ai-engineering/README.md` and add a test that fails when those two files drift.
- Review `.ai-engineering/team/README.md` and preserve the existing four-line placeholder unless a concrete defect is found during implementation.
- Add `.ai-engineering/reference/brand-voice.md` as the prose authority for README voice rules, citing `docs/design.pen` and `docs/untitled.pen` line evidence for the `{ai} engineering` wordmark, shell-prompt CTA, mid-dot stat line, code-comment header, bracket-tag status grammar, and no-emoji convention.
- Hard-rename the `/ai-repo-tidy` skill to `/ai-branch-cleanup` across canonical `.claude/` skill sources, generated root mirrors, installer-template provider surfaces, Python registry/user-facing strings, reference docs, session bootstrap scripts, tests, and non-historical documentation references.
- Leave historical audit/state records untouched while ensuring a fresh `rg --hidden -n 'ai-repo-tidy'` after implementation returns only explicitly allowed historical hits.
- Update `CHANGELOG.md` `[Unreleased]` with one `### BREAKING` entry for the skill rename and one `### Changed` entry for the README/brand rewrite.
- Run the rename and documentation gates: `pytest tests/docs/test_links.py -q`, `pytest tests/architecture/test_naming_clarity.py tests/unit/test_cleanup_history_rotation.py tests/unit/test_consolidate_spec_action.py -q`, `ai-eng dev sync --check`, `ai-eng verify --full`, and full `pytest -q` before PR handoff.

## Non-Goals

- Do not edit `docs/design.pen` or `docs/untitled.pen`; stale counts in those design assets are tracked by a separate asset-team follow-up.
- Do not generate new logos, SVGs, screenshots, raster images, or inline visual assets for the README files.
- Do not change `/ai-repo-tidy` behavior while renaming it; branch cleanup, spec sweep, runtime rotation, and report behavior remain identical under the new slug.
- Do not preserve an `/ai-repo-tidy` alias, shim, deprecation wrapper, or compatibility fallback.
- Do not rewrite `CONSTITUTION.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, or `.github/copilot-instructions.md` unless the sanity review finds a blocker and the operator explicitly approves a follow-up.
- Do not expand the docs portal under `docs/` beyond the new `.ai-engineering/reference/brand-voice.md` reference.
- Do not rewrite append-only `.ai-engineering/state/framework-events.ndjson` or mutate historical records in `.ai-engineering/state/state.db`.

## Decisions

### D-144-01: Promote the consumed brief as one large, four-wave spec

The work ships as one large spec with four implementation waves: brand voice reference, README rewrite, skill rename, and canonical-doc sanity review.

**Rationale**: The README rewrite and skill rename touch different file families but share one first-contact DX goal: make the front door current, branded, and intent-revealing. Splitting them would duplicate sync/checklist work across mirrors, tests, CHANGELOG, and PR review.

### D-144-02: Brand voice gets a Markdown prose source of truth

Create `.ai-engineering/reference/brand-voice.md` as the Markdown authority for prose rules extracted from `docs/design.pen` and `docs/untitled.pen`; leave the `.pen` files as read-only visual design sources.

**Rationale**: README authors and doc skills can consume a small Markdown reference reliably. Reading encrypted or large design artifacts for every future prose edit would be expensive and error-prone, while editing `.pen` assets is outside the documentation wave.

### D-144-03: README replacements are targeted, not exhaustive docs rewrites

Rewrite `README.md`, `.ai-engineering/README.md`, and `src/ai_engineering/templates/.ai-engineering/README.md`; review `.ai-engineering/team/README.md` and keep its four-line placeholder unless a concrete defect appears.

**Rationale**: The brief identifies specific stale onboarding links, stale surface names, and missing brand voice. The team placeholder already has the desired minimal shape, so rewriting it without evidence would violate KISS and add noise.

### D-144-04: Governance README quick start is inline

Replace the dead `GETTING_STARTED.md` link in `.ai-engineering/README.md` and the installer template twin with a short inline Quick Start that points to `ai-eng install`, `/ai-start`, and the canonical chain.

**Rationale**: A new operator stays inside the governance README for the next command. Inline quick start removes a deleted-file dependency and keeps the first-success path in one Tier 4 document.

### D-144-05: Template README drift is blocked by a test

Add or extend a CI test that asserts `.ai-engineering/README.md` and `src/ai_engineering/templates/.ai-engineering/README.md` are byte-identical.

**Rationale**: A test is less machinery than a pre-commit copier and stronger than a manual checklist. It preserves the existing mirror-sync expectation while keeping the canonical store obvious: the live governance README is copied into the template twin during implementation.

### D-144-06: `/ai-repo-tidy` hard-renames to `/ai-branch-cleanup`

Rename the skill slug, directories, frontmatter, examples, cross-references, registry key, tests, and generated/template surfaces from `ai-repo-tidy` to `ai-branch-cleanup` with no alias.

**Rationale**: `ai-repo-tidy` is vague and overlaps general cleanup language; `ai-branch-cleanup` names the dominant behavior. The Constitution forbids backward-compatibility shims for renamed content, so the break is documented rather than hidden.

### D-144-07: Rename audits use `framework_operation` with `detail.operation=skill_renamed`

Emit rename traceability as `kind=framework_operation` with `detail.operation=skill_renamed`, `from=ai-repo-tidy`, `to=ai-branch-cleanup`, and `spec=spec-144`.

**Rationale**: `skill_renamed` is a detail operation, not a top-level event kind in the current event schema. Reusing `framework_operation` preserves the audit-kind allowlist and avoids a schema expansion for a one-off rename.

### D-144-08: Stale registry-count comment is fixed in the rename wave

Update the stale `src/ai_engineering/config/framework_defaults.py` comment that claims the skill registry has 48 entries while touching the registry key for the rename.

**Rationale**: The same file is already in scope for the slug replacement. Fixing the adjacent stale comment in the same wave reduces future confusion without creating a separate hygiene commit.

### D-144-09: Changelog records one breaking change and one docs change

Place the skill rename under `CHANGELOG.md` `[Unreleased]` `### BREAKING`, and place the README/brand rewrite under `### Changed`.

**Rationale**: Only the slug rename breaks external automation. The README rewrite is user-visible but not API-breaking, so it belongs in `Changed` while the rename gets the required hard-rename notice.

### D-144-10: Design-asset count drift becomes a follow-up issue

File a separate `/ai-issue` for stale counts in `docs/design.pen` and `docs/untitled.pen` instead of editing those assets in this PR.

**Rationale**: The `.pen` files are visual design sources outside this spec's textual documentation scope. A tracked issue prevents the drift from being forgotten without forcing asset editing into the README/rename PR.

### D-144-11: Canonical-doc sanity review reports divergence but does not auto-rewrite

Read `CONSTITUTION.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, and `.github/copilot-instructions.md` during Wave 4; if divergence exists, report it and spin off a follow-up unless the operator explicitly approves inclusion.

**Rationale**: The operator scoped this work to README rewrite plus rename. Canonical mirrors are generated governance surfaces with their own contracts, so unplanned rewrites risk broad review churn.

### D-144-12: README code fences and symbols use terminal-native conventions

Codify `bash` for shell-command fences, `yaml` for manifest snippets, literal `{ai} engineering` in prose, mid-dot stat lines for compact counts, bracket tags for statuses, and a hard no-emoji rule in `brand-voice.md`.

**Rationale**: The design sources use shell prompts, monospaced command blocks, and bracket statuses instead of emoji. Making these rules explicit keeps future documentation edits consistent without rereading the visual assets.

### D-144-13: Historical state is read-only during the rename

Do not edit `.ai-engineering/state/framework-events.ndjson`, `.ai-engineering/state/state.db`, or archived historical spec/CHANGELOG references solely to remove `ai-repo-tidy`.

**Rationale**: The audit chain and history files are witnesses, not rewrite targets. The verification grep must distinguish active references from historical records so the hard rename does not corrupt audit provenance.

## Risks

- **README structural gate failure**: `tests/docs/test_links.py::test_readme_minimal` enforces the root README cap and required links. Mitigation: run `pytest tests/docs/test_links.py -q` before and after the rewrite; keep the root README at or below 120 lines.
- **Mirror drift after the rename**: root mirrors and installer-template provider surfaces can diverge from `.claude/` after directory moves. Mitigation: run `ai-eng dev sync`, then `ai-eng dev sync --check`, and inspect residual `ai-repo-tidy` hits.
- **Historical grep false positives**: append-only state and archived history contain valid old slugs. Mitigation: define the allowlist in the plan and fail only on non-historical active references.
- **External automation breakage**: operators with scripts invoking `/ai-repo-tidy` must update them. Mitigation: document the exact `/ai-branch-cleanup` replacement in `CHANGELOG.md` under `### BREAKING`.
- **Brand voice overreach**: README prose can become decorative instead of useful. Mitigation: brand rules must support command-first onboarding; root README line cap and link tests keep the result concise.
- **Template README sync remains manual by accident**: a future edit can change one README without the other. Mitigation: add the byte-equivalence test in the same wave as the template update.
- **Audit schema misuse**: emitting `skill_renamed` as a top-level event kind would violate the current event schema. Mitigation: use D-144-07 and test/inspect event-shape code before writing any audit row.

## References

- brief: `.ai-engineering/specs/drafts/readme-rewrite-and-branch-cleanup-rename-brief.md`
- doc: `CONSTITUTION.md` (hard-rename/no-shim policy)
- doc: `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` / `.github/copilot-instructions.md` (canonical chain and mirror payload)
- doc: `docs/persistence-doctrine.md` (Tier 4 Markdown source-of-truth doctrine)
- doc: `.ai-engineering/reference/spec-schema.md` (spec shape)
- evidence: `README.md:23` lists Antigravity while `.ai-engineering/manifest.yml:28` enables OpenCode and Cursor.
- evidence: `.ai-engineering/README.md:5` and `src/ai_engineering/templates/.ai-engineering/README.md:5` link to deleted `GETTING_STARTED.md`.
- evidence: `tests/docs/test_links.py:203-228` enforces the root README structural cap and link requirements.
- evidence: `docs/design.pen:3291` provides the tagline; `docs/design.pen:3862-3911` provides bracket-tag status grammar.
- evidence: `docs/untitled.pen:522` provides the shell-prompt CTA; `docs/untitled.pen:1944` provides the mid-dot stat-line pattern.
- evidence: `src/ai_engineering/config/framework_defaults.py:262`, `src/ai_engineering/validator/categories/file_existence.py:282`, `.ai-engineering/reference/model-dispatch-policy.md:44`, and `.ai-engineering/reference/surface-axioms.md:39` contain active `ai-repo-tidy` references.
- evidence: `tests/unit/test_cleanup_history_rotation.py:19-22`, `tests/unit/test_consolidate_spec_action.py:21`, and `tests/architecture/test_naming_clarity.py:59` pin rename-sensitive behavior.

## Open Questions

None. The eight open decisions from the consumed brief are resolved in this spec: template sync (D-144-05), stale registry comment (D-144-08), dead-link replacement (D-144-04), no-emoji/code-fence voice rules (D-144-12), changelog shape (D-144-09), asset-team handoff (D-144-10), canonical-doc review scope (D-144-11), and README code-block conventions (D-144-12).
