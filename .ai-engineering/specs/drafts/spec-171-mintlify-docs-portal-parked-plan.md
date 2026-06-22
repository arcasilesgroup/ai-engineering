---
spec: spec-171
title: Mintlify Documentation Portal
status: approved
pipeline: autopilot
phases: 5
execution_route:
  version: 1
  spec: spec-171
  executor: autopilot
  automation: hitl
  concern_count: 5
  estimated_files: 85
  reason: "Five-concern large spec (scaffold, authored content, generated reference, operator-gated deploy, CI/packaging integration) with ~85 file changes — above the autopilot threshold (>=3 concerns or >=10 files)."
  safe_next_command: "/ai-autopilot"
---

# Plan — spec-171 Mintlify Documentation Portal

## Design

Design intent captured at `.ai-engineering/specs/spec-171/design-intent.md`
(auto-routed from /ai-plan because matched keywords: page, ui). Theme final
only after operator sign-off at Phase 1 (D-171-08).

## Architecture

Pattern: **ad-hoc** (static MDX content tree + derived-cache generator).
The generator (`tools/docs_portal/generate_reference.py`) follows **Pipes
and Filters** (`.ai-engineering/reference/architecture-patterns.md`):
registry sources (`.claude/skills/*/SKILL.md`, `.claude/agents/ai-*.md`,
`.ai-engineering/reference/cli-reference.md`) → frontmatter parse →
MDX render → idempotent write. Per CONSTITUTION Prohibition 8 every
generated file is a labelled derived cache with a rebuild command.

Cross-phase invariants:

- No new third-party GitHub Actions (D-171-04, Actions allowlist).
- Brand-voice on every page: English, zero emoji, `{ai} engineering`
  prose / `ai-engineering` identifiers, no PII or machine paths.
- `mint` version pinned wherever `npx` invokes it (reproducible CI).
- Operator dashboard work (Phase 4) starts in parallel with Phase 1 —
  subdomain must be known before T-5.3/T-5.4 execute; live-endpoint
  verification (T-4.1) is post-merge acceptance.

## Phase 1: M0 Scaffold

Gate: `npx mint validate` clean inside `docs-portal/`; operator theme sign-off.

- [ ] **T-1.1**: Create `docs-portal/docs.json` (site name `ai-engineering`,
      two-tab navigation skeleton Documentation + Reference, neutral
      placeholder colors) plus a minimal `docs-portal/index.mdx` stub so
      navigation resolves.
  - Agent: build
  - Files: docs-portal/docs.json, docs-portal/index.mdx
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Patch (deterministic): omitted — new-file authoring against the
    docs.json schema requires judgment.
  - Gate: `cd docs-portal && npx --yes mint@<PINNED_VERSION> validate` exits 0
    (pin chosen at T-1.1 from the current mint release; reused everywhere)
- [ ] **T-1.2**: Extract the Arcasiles palette from `docs/design.pen` via
      Pencil MCP (`get_variables` / `get_screenshot`), map to `docs.json`
      `colors.{primary,light,dark}` + background, present rendered theme to
      operator for sign-off (D-171-08).
  - Agent: build
  - Files: docs-portal/docs.json
  - Principles applied: §10.4 DRY (brand SoT stays in design.pen)
  - Patch (deterministic): omitted — color mapping is judgment + operator
    checkpoint.
  - Gate: operator sign-off recorded in PR description; `mint validate` clean
- [ ] **T-1.3**: Produce `docs-portal/logo/` light+dark wordmark SVGs and
      `docs-portal/favicon.svg` (export from design.pen via Pencil
      `export_nodes`, else minimal text-based SVG per brand-voice); wire
      into `docs.json`.
  - Agent: build
  - Files: docs-portal/logo/light.svg, docs-portal/logo/dark.svg, docs-portal/favicon.svg, docs-portal/docs.json
  - Principles applied: §10.1 KISS
  - Patch (deterministic): omitted — asset creation.
  - Gate: `mint validate` clean; assets referenced in docs.json render in `mint dev`

## Phase 2: M1 Authored Content

Gate: `npx mint broken-links` clean; every normative claim links to its
canonical in-repo doc on GitHub; brand-voice compliant.

- [ ] **T-2.1**: Write landing `docs-portal/index.mdx` — value statement,
      stat line (54 skills · 9 agents · 6 surfaces · 1 governed flow),
      CardGroup CTAs to quickstart and governed-flow.
  - Agent: build
  - Files: docs-portal/index.mdx
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omitted — prose authoring.
  - Gate: `mint broken-links` clean; stat line matches README.md:30
- [ ] **T-2.2**: Write `get-started/installation.mdx` (CodeGroup: uv /
      pipx / pip, commands identical to README install block).
  - Agent: build
  - Files: docs-portal/get-started/installation.mdx
  - Principles applied: §10.4 DRY (same commands README asserts)
  - Patch (deterministic): omitted — prose authoring.
  - Gate: commands byte-match README install commands
- [ ] **T-2.3**: Write `get-started/quickstart.mdx` (Steps: install →
      `ai-eng install` → `/ai-start`) and `get-started/governed-flow.mdx`
      (canonical chain with Mermaid, cites CLAUDE.md §11; explicitly
      explains `/ai-spec-draft` as the OPTIONAL deep-research pre-step
      that produces a brief consumed by `/ai-brainstorm`).
  - Agent: build
  - Files: docs-portal/get-started/quickstart.mdx, docs-portal/get-started/governed-flow.mdx
  - Principles applied: §10.6 SDD
  - Patch (deterministic): omitted — prose authoring.
  - Gate: chain string matches README.md:113 canonical chain
- [ ] **T-2.4**: Write `concepts/constitution.mdx` and
      `concepts/skills-and-agents.mdx` (summarize + link canonical docs;
      never fork normative content).
  - Agent: build
  - Files: docs-portal/concepts/constitution.mdx, docs-portal/concepts/skills-and-agents.mdx
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Patch (deterministic): omitted — prose authoring.
  - Gate: every normative claim carries a GitHub link to the canonical doc
- [ ] **T-2.5**: Write `concepts/hooks.mdx` (11 canonical events, integrity
      pinning), `concepts/quality-gates.mdx` (gate-policy summary,
      fail-open/closed doctrine), `concepts/persistence.mdx` (three-tier
      files-only model, links persistence-doctrine.md).
  - Agent: build
  - Files: docs-portal/concepts/hooks.mdx, docs-portal/concepts/quality-gates.mdx, docs-portal/concepts/persistence.mdx
  - Principles applied: §10.4 DRY
  - Patch (deterministic): omitted — prose authoring.
  - Gate: `mint broken-links` clean
- [ ] **T-2.6**: Write `guides/ide-setup.mdx` (Tabs: Claude Code / Copilot /
      Codex / Antigravity / OpenCode / Cursor).
  - Agent: build
  - Files: docs-portal/guides/ide-setup.mdx
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omitted — prose authoring.
  - Gate: one tab per supported surface; `mint validate` clean
- [ ] **T-2.7**: Write `guides/risk-acceptance.mdx` (risk-acceptance-flow
      summary) and `guides/upgrading.mdx` (`ai-eng update` path).
  - Agent: build
  - Files: docs-portal/guides/risk-acceptance.mdx, docs-portal/guides/upgrading.mdx
  - Principles applied: §10.4 DRY
  - Patch (deterministic): omitted — prose authoring.
  - Gate: `mint broken-links` clean
- [ ] **T-2.8**: Write `changelog.mdx` — link-only page to CHANGELOG.md on
      GitHub (D-171-07); register all Phase 2 pages in `docs.json` navigation.
  - Agent: build
  - Files: docs-portal/changelog.mdx, docs-portal/docs.json
  - Principles applied: §10.2 YAGNI
  - Patch (deterministic): omitted — nav wiring depends on prior pages.
  - Gate: `mint validate` + `mint broken-links` clean
- [ ] **T-2.9**: Write `guides/mcp-integrations.mdx` — the MCP servers the
      framework consumes per skill (NotebookLM for /ai-research Tier 3,
      fal-ai for /ai-media, Pencil for .pen design assets, board/work-item
      providers, et al.), sourced at build time from the skill SKILL.md
      files and `.ai-engineering/reference/mcp-binary-policy.md` — never
      invented from memory. Register in docs.json navigation.
  - Agent: build
  - Files: docs-portal/guides/mcp-integrations.mdx, docs-portal/docs.json
  - Principles applied: §10.4 DRY (enumerate from skill SoT, not memory)
  - Patch (deterministic): omitted — prose authoring from repo evidence.
  - Gate: every MCP named traces to a SKILL.md or reference doc citation; `mint broken-links` clean
- [ ] **T-2.10**: Verify Phase 2: brand sweep (zero emoji, naming contract,
      no PII/machine paths), link sweep, English-only check across
      `docs-portal/**`.
  - Agent: verify
  - Files: docs-portal/** (read-only)
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omitted — read-only verification.
  - Gate: grep sweeps return zero violations; `mint broken-links` clean

## Phase 3: M2 Generated Reference (TDD pair)

Gate: `tests/docs/test_portal_reference_parity.py` green; regeneration
idempotent; generator fails loud on malformed frontmatter.

- [ ] **T-3.1**: RED — write `tests/docs/test_portal_reference_parity.py`
      asserting: (a) generated skill-page count == manifest
      `skills.total` (loaded via `ManifestConfig`, not hardcoded);
      (b) agent-page count == `agents.total`; (c) double-run idempotency
      (second run produces zero diff); (d) every generated file carries the
      GENERATED header; (e) generator raises on a malformed-frontmatter
      fixture.
  - Agent: build
  - Files: tests/docs/test_portal_reference_parity.py
  - Principles applied: §10.5 TDD (RED)
  - Patch (deterministic): omitted — test synthesis.
  - Gate: test FAILS (generator absent)
- [ ] **T-3.2**: GREEN — implement `tools/docs_portal/generate_reference.py`:
      parse `.claude/skills/*/SKILL.md` frontmatter (name, description,
      argument-hint, tags) and `.claude/agents/ai-*.md`; emit
      `reference/skills/<name>.mdx` + `reference/agents/<name>.mdx` +
      CardGroup index pages, each with header
      `{/* GENERATED — rebuild: python tools/docs_portal/generate_reference.py */}`;
      fail loud (non-zero exit, named file) on missing/malformed frontmatter.
  - Agent: build
  - Files: tools/docs_portal/__init__.py, tools/docs_portal/generate_reference.py
  - Principles applied: §10.5 TDD (GREEN), §10.4 DRY, §10.3 SOLID
  - Patch (deterministic): omitted — new module synthesis.
  - Gate: T-3.1 test green
- [ ] **T-3.3**: Extend generator to render `reference/cli.mdx` from
      `.ai-engineering/reference/cli-reference.md` (transform, GENERATED
      header) and author `reference/environment.mdx` (AIENG_* tunables
      table from the CLAUDE.md Runtime Layer Tunables block).
  - Agent: build
  - Files: tools/docs_portal/generate_reference.py, docs-portal/reference/environment.mdx
  - Principles applied: §10.4 DRY
  - Patch (deterministic): omitted — transform logic.
  - Gate: parity test green; `mint validate` clean
- [ ] **T-3.4**: Run the generator; commit the 54 skill + 9 agent + cli +
      index pages; register the Reference tab nav in `docs.json`.
  - Agent: build
  - Files: docs-portal/reference/**, docs-portal/docs.json
  - Principles applied: §10.6 SDD
  - Patch (deterministic): omitted — generated output commit.
  - Gate: `pytest tests/docs -q` green; `mint validate` + `mint broken-links` clean
- [ ] **T-3.5**: Verify Phase 3: confirm idempotency on clean tree
      (`git status --porcelain` empty after regeneration), GENERATED headers
      present, zero hand-edits under `docs-portal/reference/`.
  - Agent: verify
  - Files: docs-portal/reference/** (read-only)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omitted — read-only verification.
  - Gate: regeneration diff empty; parity suite green

## Phase 4: M3 Deploy (operator-gated)

Operator dashboard actions — the agent cannot perform these. Start them in
parallel with Phase 1; only T-4.1 requires merged `main`.

* [x] Operator: create Mintlify account/org (free Starter tier) — DONE
      2026-06-12; org auto-provisioned the starter template (replaced
      wholesale once `docs-portal/` syncs from `main`).
* [ ] Operator: install the Mintlify GitHub App on this repo.
* [ ] Operator: set monorepo path `/docs-portal`, production branch `main`,
      PR preview deployments ON.
* [x] Operator: subdomain chosen and reported — `arcasiles.mintlify.app`
      (consumed by T-5.3/T-5.4).
* [ ] Operator: verify OSS-program eligibility — arcasilesgroup status vs
      the program's "not owned or primarily maintained by a for-profit
      company" clause (D-171-10 hedge against free-tier re-gating).

- [ ] **T-4.1**: Post-merge acceptance — verify portal live: `/llms.txt`,
      `/llms-full.txt`, `/mcp` respond 200 over HTTPS; PR preview URL
      appears on a test PR.
  - Agent: verify
  - Files: none (live HTTP checks)
  - Principles applied: §10.6 SDD (Definition of Done is observable)
  - Patch (deterministic): omitted — runtime verification.
  - Gate: `curl -fsS https://arcasiles.mintlify.app/llms.txt` exits 0; preview comment observed

## Phase 5: M4 Integration

Gate: `tests/unit/docs` + `tests/docs` green locally AND in CI;
install-smoke unaffected; docs-gate runtime within budget.

- [ ] **T-5.1**: Un-ignore `.mdx` at the workflow trigger and add
      `docs-portal/**` to the `docs` change-scope filter — portal-only PRs
      must trigger docs-gate (today `paths-ignore: '**.mdx'` skips CI
      entirely for pure-MDX changes).
  - Agent: build
  - Files: .github/workflows/ci-check.yml:17-20,28-31,81-87
  - Principles applied: §10.1 KISS, §10.5 TDD (gate must observe its subject)
  - Patch (deterministic):
    ```diff
    @@ push.paths-ignore / pull_request.paths-ignore (both blocks) @@
         paths-ignore:
    -      - '**.mdx'
           - '**.rst'
           - '**.txt'
    @@ change-scope filter: docs @@
             docs:
               - '**/*.md'
    +          - 'docs-portal/**'
    ```
  - Gate: `uv run python scripts/check_workflow_policy.py` exits 0
- [ ] **T-5.2**: Add a "Portal validation" step to the docs-gate job after
      "Content integrity": pinned `npx mint` validate + broken-links run in
      `docs-portal/`; measure job runtime stays within the 10-minute
      timeout with margin.
  - Agent: build
  - Files: .github/workflows/ci-check.yml (docs-gate job, after the "Content integrity" step)
  - Principles applied: §10.1 KISS (no new Action, D-171-04)
  - Patch (deterministic):
    ```diff
    @@ docs-gate steps, after "Content integrity" @@
    +      - name: Portal validation (mint)
    +        working-directory: docs-portal
    +        run: |
    +          npx --yes mint@<PINNED_VERSION> validate
    +          npx --yes mint@<PINNED_VERSION> broken-links
    ```
  - Gate: docs-gate green on the PR; runtime delta under 2 minutes
- [ ] **T-5.3**: Add `[project.urls]` to `pyproject.toml` (Homepage =
      portal, Documentation = portal, Repository = GitHub, Changelog =
      GitHub CHANGELOG). Requires the Phase 4 subdomain value.
  - Agent: build
  - Files: pyproject.toml:8 (after `requires-python`)
  - Principles applied: §10.1 KISS
  - Patch (deterministic):
    ```diff
    @@ [project] block, after requires-python @@
     requires-python = ">=3.11"
    +
    +[project.urls]
    +Homepage = "https://arcasiles.mintlify.app"
    +Documentation = "https://arcasiles.mintlify.app"
    +Repository = "https://github.com/arcasilesgroup/ai-engineering"
    +Changelog = "https://github.com/arcasilesgroup/ai-engineering/blob/main/CHANGELOG.md"
    ```
  - Gate: `uv build` succeeds; `tests/unit/config` suite green
- [ ] **T-5.4**: Add the portal Documentation link to README within the
      170-line cap (165 today — 5 lines headroom; prefer editing an
      existing line; absolute raw URL per README link convention).
      Requires the Phase 4 subdomain value.
  - Agent: build
  - Files: README.md
  - Principles applied: §10.1 KISS
  - Patch (deterministic): omitted — line-budget judgment.
  - Gate: `uv run pytest tests/unit/docs tests/docs -q` green locally (line cap + brand contract)
- [ ] **T-5.5**: CHANGELOG entry under Unreleased documenting the portal
      (Keep-a-Changelog format).
  - Agent: build
  - Files: CHANGELOG.md
  - Principles applied: §10.6 SDD
  - Patch (deterministic): omitted — release-notes prose.
  - Gate: `uv run pytest tests/docs/test_changelog_spec_146.py -q` green
- [ ] **T-5.6**: Final verify — full local docs gate: `uv run pytest
      tests/docs tests/unit/docs tests/unit/config -q`, `uv run ai-eng
      check`, `python -m spec_lint --check`, regeneration idempotency,
      secret/PII sweep over `docs-portal/**`.
  - Agent: verify
  - Files: repo-wide (read-only)
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): omitted — read-only verification.
  - Gate: all listed commands exit 0
