# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.3] - 2026-05-29

### Fixed
- **`ai-eng install` now ships the Article VII suppression allowlist, so a
  consumer's first `git push` is no longer self-blocked.** The installer
  deploys the vendored `.ai-engineering/scripts/` tree, whose framework
  scripts legitimately carry suppression markers (optional-dependency import
  fallbacks, self-bootstrap `E402` imports, `__main__` CLI shims, a
  validated-SSRF `nosemgrep`). The authorizing `suppression-allowlist.yml`
  was missing from the shipped template tree, so the pre-push no-suppression
  gate denied every one of those markers and blocked the first push in every
  installed project. A standard baseline allowlist — permanent (no TTL), no
  DEC bindings, scoped strictly to `.ai-engineering/scripts/**` and never to
  a consumer's own `src/`/`tools/`/`tests/` — now ships at
  `src/ai_engineering/templates/.ai-engineering/suppression-allowlist.yml`.
  Two regression guards lock it in: `test_template_tree_completeness.py`
  asserts the baseline covers every marker the scanner finds in the shipped
  scripts tree, and `test_install_clean.py` runs the gate against a freshly
  installed tree and asserts zero denials. Same bug class as the earlier
  `skill_scripts_lib` ship-gap.

### Changed

- **README install section now gives explicit per-tool-manager
  instructions.** The previous block collapsed `uv`/`pipx`/`pip` into a
  two-line snippet and a one-line update note. It is now numbered steps that
  spell out the `uv tool install --force` + `update-shell` + `exec "$SHELL"
  -l` path, the `pipx` path, the `pip --user` path (with a `PATH` reminder
  when `ai-eng` is not found), and a 3-step PyPI update flow (`upgrade` →
  `version` → `ai-eng update`/`doctor` per project). Lowers first-run
  friction for operators who do not already use `uv`.
- **Corrected the GSD attribution link in "Standing on the shoulders
  of...".** It pointed at `jlowin/gsd`; it now points at the canonical
  `open-gsd/get-shit-done-redux` repository.
## [0.8.2] - 2026-05-25

### Fixed

- **The release pipeline's TestPyPI install verification now tolerates index
  propagation lag.** The `verify-testpypi-install` job ran `pip install
  ai-engineering==<version>` seconds after the TestPyPI publish succeeded, but
  TestPyPI's index takes seconds-to-minutes to make a freshly uploaded version
  resolvable via `pkg==version` — so every release failed the verify job on the
  first miss and needed a manual `gh run rerun --failed`. The install step now
  polls with backoff (20 attempts x 15s, ~5 min, inside the job's 10-minute
  timeout) and fails only after the cap. The production-PyPI publish job has no
  analogous index-install step, so it needed no change.
- **`ai-eng release <version> --wait` no longer fails its `monitor` phase with
  "Unable to read tag SHA".** `GitHubProvider.create_tag` creates the tag ref
  remote-only via the GitHub API (`gh api .../git/refs`, bypassing the local
  pre-push hook), so the tag never lands in the local repository. The monitor
  phase then re-derived the head SHA with a local `git rev-parse v<version>`,
  which failed (`fatal: ambiguous argument 'v<version>'`) even though readiness
  was GO, the tag was created, and the publish workflow ran fine. `_create_tag`
  now exposes the commit SHA it already computed (from `git rev-parse HEAD` on
  the merged default branch) via `PhaseResult.details["tagged_sha"]`,
  `_complete_release` threads it into `_monitor_pipeline`, and monitor uses it
  directly — no local tag lookup, no network round-trip. The local lookup
  remains a fallback for the resume flow (where the tag already exists locally)
  and now resolves it through the safe `git rev-parse --verify --quiet
  refs/tags/v<version>` form used by the validate and create-tag phases, rather
  than a bare `rev-parse v<version>` that can match a branch or a partial SHA.
  This only affected the orchestrator's own progress monitoring; the published
  artifact was never at risk, since the tag is pushed and the tag-triggered
  `release.yml` publishes regardless.
## [0.8.1] - 2026-05-24

### Fixed

- **`ai-eng release <version> --wait` is now idempotent and resumable.** When the
  release PR has already merged (the version bump is on the default branch and the
  CHANGELOG `[Unreleased]` is already promoted) but the tag was never created, a
  rerun now detects that the current version already equals the target and the tag
  is absent, skips validate's version/changelog gate plus prepare/PR/wait-for-merge,
  and proceeds straight to readiness → create-tag → monitor. The pre-merge flow is
  unchanged when the bump has not landed, and a genuine downgrade still errors.
- **Release `prepare` now syncs the project's own version pin in `uv.lock`.** The
  bump updated `pyproject.toml`, `version/registry.json`, and the two `manifest.yml`
  surfaces but left the `uv.lock` editable-root pin stale, which forced a manual
  lockfile commit onto the release branch. The pin is now rewritten in place
  alongside the other bumped files.
- **Release deployment-environment drift is now guarded.** The 0.8.0 publish
  nearly failed because `release.yml` became tag-triggered (spec-152) while the
  `pypi` GitHub environment still allowed only the `main` branch — a setting
  that lives in repo configuration, not the repository, so nothing in-tree
  caught the drift. `ai-eng doctor` now runs a `release-env-policy` runtime
  check that reads each release environment's live deployment policy and warns
  when the `v*` tag pattern is missing, and a new
  `tests/unit/workflows/test_release_env_policy_docs.py` fails CI if a publish
  environment is added to the workflow without a matching policy note. The
  required `pypi`, `testpypi`, and `github-release` deployment policies and the
  `tag-protection-v` ruleset coupling are documented in
  `docs/ci-branch-protection.md`.
- **Release readiness no longer false-positives on the pytest cache.** The
  `ai-eng verify --release` gitleaks scan runs with `--no-git`, so it walked the
  gitignored `.pytest_cache/` and flagged a synthetic GitHub App token baked into
  a `test_redactor` parametrize node ID — turning a clean tree into a spurious
  NO-GO. `.pytest_cache/` now sits in the `.gitleaks.toml` allowlist alongside the
  other regenerable caches (`__pycache__/`, `.venv/`, `node_modules/`); the staged
  pre-commit scan is unaffected (the cache is never staged).

## [0.8.0] - 2026-05-24

### BREAKING

- **spec-153 — spec/plan lifecycle automation and a numeric canonical spec
  identity (hard renames, no shims).** The one canonical spec identity is now
  numeric `spec-NNN`; the slug is a secondary descriptor. Operator-visible hard
  migrations, each performed in place with no backwards-compatibility alias
  (CONSTITUTION §3):
  - **Per-spec sidecars are renamed** slug→`spec-NNN.json` under
    `.ai-engineering/state/specs/`, and the duplicate
    `obvious-by-default`/`obvious-by-default-essentials` pair is collapsed to a
    single record. External tooling that reads sidecars by slug filename must
    switch to the numeric name.
  - **The spec archive uses one uniform layout**:
    `.ai-engineering/specs/archive/spec-NNN-<slug>/{spec.md,plan.md}`. Existing
    flat `spec-NNN-*.md` files and separate `-plan.md` pairs are migrated into
    it; the eleven stray `spec-NNN-*.md` orphans in `specs/` root are reaped
    into their archive directories. The `specs/` root invariant is now exactly
    `{spec.md, plan.md, _history.md, drafts/, archive/}`.
  - **Freeform delivery-log prose is relocated** out of
    `.ai-engineering/specs/_history.md` to
    `.ai-engineering/state/archive/delivery-logs/spec-<NNN>.md`; the ledger is
    an index over shipped specs, not a log dump. Historical `_history.md` rows
    remain verbatim; only NEW rows render their Status cell from the
    `LifecycleState` enum, and the single slug-keyed row is corrected to
    `spec-152`.
  - **`.ai-engineering/README.md` is rewritten as the post-install client
    manual** (welcome → quick-win path → generated capability catalog →
    maintainer pointer) and its factually stale **"Four-Tier Persistence" table
    and every `state/state.db` reference are deleted** (`state.db` was removed
    by spec-148; the framework is three-tier and files-only). The doc now points
    to `docs/persistence-doctrine.md` rather than restating the tiers inline.
  Operator action: none is required for normal use — the migrations are applied
  by the lifecycle tooling and are idempotent — but automation that hardcoded
  slug sidecar names, the old flat archive layout, or the deleted `state.db`
  store must be updated.
- **spec-151 — Google support is Antigravity-only before public release.**
  The retired `gemini-cli` surface is hard-deleted from the supported
  surface enum, installer/update maps, validators, generated mirrors, docs,
  and tests. Fresh installs now use the single `antigravity` surface with
  root `AGENTS.md`, generated `.agents/skills` + `.agents/agents`, and
  fail-soft `agy`/`agy.exe` diagnostics. Removed with no shim: root
  `GEMINI.md`, `.gemini/**`, template `GEMINI.md`/`.gemini/**`, the
  Gemini hook bridge, and legacy Antigravity `.agent/**` generated output.
  Historical changelog/spec references remain historical only.
- **spec-148 — files-only persistence: the embedded SQLite `state.db` is
  removed.** Every datum now has a single file source of truth — decisions
  and risk acceptances in `decision-store.json`, ownership in
  `ownership-map.json`, install state in `install-state.json`, framework
  capabilities in `framework-capabilities.json` (rebuilt on demand), and
  the audit log in `framework-events.ndjson` (already canonical). This is a
  hard reversal of spec-123 (state.db bootstrap), spec-125 (install-state +
  capabilities → state.db) and spec-132 (decisions + ownership → state.db).
  Deleted: `state/state_db.py`, `state/migrations/**`, `state/audit_index.py`,
  `state/retention.py`, the `ai-eng doctor --check state-db` command, and the
  `ai-eng audit index/query/health/vacuum` + `audit retention apply`
  subcommands (`audit verify/tokens/replay` stay, computed over the NDJSON).
  Migration: `ai-eng update` runs a one-shot export→verify→delete that
  ingests a legacy `state.db` into the file stores, verifies the export, then
  deletes `state.db` (no `.bak`; fail-loud — it never deletes unless the
  export verifies). No backwards-compat shim. A fresh install creates no
  `state.db`. CI guard `tests/architecture/test_no_sqlite.py` forbids any
  `import sqlite3` in `src/` or hooks except the one-shot migration.
- **spec-149 — obvious-by-default essentials (trimmed): `cleanup branches`
  no longer deletes by default.** A bare `ai-eng cleanup branches` (no mode
  flag) now prints a plan and deletes nothing; deletion requires an explicit
  mode (`--merged` / `--pruned` / `--all`) or `--dry-run` to preview. The old
  destructive default (silent `merged=True` → delete) is removed (no shim;
  Hard-Rule 3). Also in spec-149: the §11 canonical chain now surfaces
  `/ai-spec-draft` as the optional pre-`/ai-brainstorm` step and states the
  `/ai-code` (subcomponent) vs `/ai-build` (gateway) boundary; the
  `/ai-build` and `/ai-autopilot` quality-loop Step 2d condition 4 is now
  advisory + conservative (escalates when uncertain, never silently
  auto-passes) so an identical diff yields a reproducible STOP verdict.
  spec-149 supersedes spec-148 Part B: **dropped** D-148-11 (trigger
  de-collision), D-148-12 (branch-cleanup orchestrator merge), D-148-14
  (§10.x citation CI), D-148-15 (naming-grammar CI) as YAGNI gate-theater the
  repo already satisfies; **re-scoped** D-148-13 (STOP determinism → the one
  real fix) and D-148-16 (dry-run default); **deferred** D-148-17
  (security-suppression DEC-binding) to a dedicated spec — it cannot be
  CI-enforced until `decision-store.json` is committed (Part-A doctrine fix;
  see `.ai-engineering/specs/drafts/decision-store-commit-brief.md`).
- spec-147 G1 (wave 1) seals the fail-open gates so no gate or hook
  exits 0 when its tool is absent, broken, or its input is malformed.
  Two hard behavior flips (no shims):
  - **Hook integrity default flips `warn` → `enforce`.** With
    `AIENG_HOOK_INTEGRITY_MODE` unset, a hook whose bytes drift from the
    committed `hooks-manifest.json` (or is missing from it) now refuses
    to run (fail closed) instead of running with a silent warning. The
    dev escape hatch is `AIENG_HOOK_INTEGRITY_MODE=warn`; after an
    intentional hook edit run
    `python scripts/regenerate-hooks-manifest.py`.
  - **A broken security/governance tool now BLOCKS instead of being
    skipped.** A missing `no_suppression` module fails the pre-push
    Article VII gate (was: silent skip); a missing/crashing/malformed
    `gitleaks` yields a BLOCKER secrets finding (was: clean verdict); an
    expired risk-acceptance blocks `gate pre-push` (was: warning only); a
    corrupt `manifest.yml` raises `InvalidManifestError` (was:
    all-defaults substitution); and `no-verify-guard` fails closed on an
    unparseable command (was: allow). Formatter re-stage, Stop-hook
    checkpoint, and MCP-health state-write failures are now surfaced as
    visible warnings instead of being swallowed silently.
- `/ai-repo-tidy` is hard-renamed to `/ai-branch-cleanup`. Update external automation that invokes the old slug; no alias or shim is preserved. The historical release-contract guard keywords remain documented for continuity: `EXIT 80`, `EXIT 81`, `python_env.mode`, and `14 stacks`.
- spec-146 removes the no-production-caller Python import surfaces
  `ai_engineering.state.agentsview`, `ai_engineering.state.outbox`,
  `ai_engineering.cli_ui_skill_ref`, and
  `ai_engineering.governance.policy_engine`. No compatibility shim is
  preserved: use the OPA-backed governance runner for policy execution,
  direct CLI copy for AI-surface wording, and `state.db/tool_capabilities`
  for capability data.

### Added

- spec-153 — the spec/plan lifecycle loop now closes without manual steps.
  Merging a spec PR (or running `/ai-branch-cleanup`) auto-transitions the spec
  to SHIPPED via the new idempotent `reconcile_merged` reconcile: it detects a
  non-terminal sidecar whose branch is merged into the default branch, resolves
  the PR, and calls `mark_shipped`. At the SHIPPED transition the working
  buffers are snapshotted into `archive/spec-NNN-<slug>/{spec.md,plan.md}` and
  reset to the `# (no active spec)` placeholder, so a shipped `spec.md`/`plan.md`
  no longer lingers in the working buffer. `start_new` mints the next numeric
  `spec-NNN` atomically under the `specs-history` lock. An orphan reaper folds
  into `sweep` and enforces the `specs/` root invariant. Retention/archival
  knobs (`draft_ttl_days`, `archive_layout`, `reap_orphans`) move to a
  `manifest.yml` `lifecycle:` block (with a matching template mirror) instead of
  hardcoded constants.
- spec-153 — capability-catalog generator (`scripts/gen_capability_catalog.py`):
  a stdlib-only read-only adapter that renders every skill (`.claude/skills/ai-*/SKILL.md`)
  and agent (`.claude/agents/ai-*.md`) into a deterministic markdown table
  between `<!-- catalog:start -->` / `<!-- catalog:end -->` markers. It is a
  derived, rebuildable cache (the skill/agent files remain the source of truth),
  regenerated by `ai-eng dev sync` and on install/update, and drift-gated by
  `ai-eng dev sync --check`. The counter-accuracy gate (`ai-eng check`) now also
  verifies the `N skills · M agents · K surfaces` counts in both `README.md` and
  `.ai-engineering/README.md` against canonical truth, so the numbers cannot
  silently rot. The template `.ai-engineering/README.md` carries the same
  client-manual structure and stays byte-identical to the live manual.
- spec-152 (W5, T-30) — OpenSSF Scorecard CI workflow
  (`.github/workflows/scorecard.yml`). Runs the Scorecard supply-chain
  posture analysis weekly (`cron`), on every push to `main`, and on manual
  dispatch, publishing the score to the public OpenSSF dashboard via OIDC
  (`publish_results: true`). Top-level permissions are `read-all`; the
  analysis job alone adds `security-events: write` + `id-token: write` +
  `contents: read`. `ossf/scorecard-action` is SHA-pinned (v2.4.3). The
  SARIF result is captured as a workflow artifact via the SHA-pinned,
  top-level `actions/upload-artifact` rather than the canonical
  `github/codeql-action/upload-sarif` *sub-path* action, because the nightly
  `--check-reachability` audit cannot resolve a sub-path ref
  (`git ls-remote` 404s); a follow-up will teach the resolver to strip the
  sub-path and restore the code-scanning upload. Guarded by
  `tests/unit/workflows/test_scorecard.py`.
- spec-152 (W5, T-31) — StepSecurity `harden-runner` egress monitoring as
  the FIRST step of every job in the CI workflows (`ci-check.yml`,
  `sbom.yml`, `scorecard.yml`), pinned to v2.19.4 in `egress-policy: audit`.
  Audit mode is non-blocking: it logs every outbound connection to build an
  egress baseline without breaking any build (OQ2 — a future flip to `block`
  with an allowlist follows one green cycle). The release publish workflow is
  intentionally out of scope this wave. Guarded by
  `tests/unit/workflows/test_harden_runner.py`.
- spec-152 (W5, T-36) — cache-cleanup runbook
  (`docs/cache-cleanup-runbook.md`): how to list/delete/rotate GitHub Actions
  caches (`gh cache list` / `gh cache delete`) after suspected poisoning or
  after the Wave 3 trust-tier key migration (the old untiered
  `gate-cache-${os}-*` / `semgrep-packs-${os}-*` keys are now orphaned), plus
  post-incident verification and the cache trust-tier model. Owned by
  `@arcasilesgroup/maintainers`.
- spec-152 (W5, T-37) — `nightly-matrix.yml` gains an advisory
  `reachability-audit` job that runs
  `scripts/check_workflow_policy.py --check-reachability` off the PR hot path,
  resolving every pinned action SHA via `git ls-remote` and surfacing any
  shaped-but-unreachable pin on the morning sweep (`continue-on-error: true`).

### Changed

- spec-152 — the GitHub `dependency-review` PR-ingress gate was removed as
  infeasible before it shipped. `actions/dependency-review-action` requires
  the org-level Dependency Graph, which is disabled for this repo and cannot
  be enabled without org-admin, so the action hard-fails every run
  (*"Dependency review is not supported on this repository"*); a required
  check that can never run is itself a fail-open hole, so it was not made
  `continue-on-error` (fake-passing) either. The `pr_all` aggregate class
  (whose only member was `dependency-review`) and its evaluate-step loop are
  deleted with it. SCA coverage is carried by `snyk-security`
  (`token_conditional`, blocking high+ when `SNYK_TOKEN` is provisioned) plus
  `pip-audit` (advisory baseline in the `always_required` `security` job) and
  `uv.lock` hash evidence. Wiring `dependency-review` back is a deferred
  follow-up gated on the org enabling the Dependency Graph; see
  `docs/supply-chain-control-matrix.md` and `docs/ci-branch-protection.md`.
- spec-147 G2 (wave 2a) corrects the canonical rulebook to stop claiming a
  non-existent `agents.registry` manifest key (D-147-07). The
  `.claude/agents/` and `.claude/skills/` directories are the source of
  truth; the prose now distinguishes the 9 user-facing `ai-*` agents from
  the internal `review-*`/`reviewer-*`/`verifier-*` families. A new
  `tests/architecture/test_surface_counts.py` guard pins the documented
  agent/skill counts against the on-disk file counts so the doc cannot
  silently drift.
- spec-147 G2 (wave 2a) documents the eight previously-undocumented
  behavior-changing hook env vars in the Runtime Layer Tunables block
  (D-147-08), with an explicit SECURITY RISK note on
  `AIE_MCP_HEALTH_FAIL_OPEN` (it flips the MCP health gate from blocking
  to pass-through). A new `tests/architecture/test_env_var_docs.py` guard
  asserts every `AIENG_*`/`AIE_*` var a hook reads is documented.
- README surfaces now use the `{ai} engineering` brand voice, current six-surface inventory, inline governance Quick Start, and byte-identical governance README template.
- Standard plan execution now records route-only `execution_route`
  metadata (`/ai-build` vs `/ai-autopilot`) and treats host-probe data as
  diagnostic/advisory rather than a framework admission gate.
- `/ai-build` and `/ai-autopilot` quality loops now allow exactly one
  bounded quality-remediation pass for blocker/critical/high findings,
  require final reassessment, persist autopilot remediation state in the
  manifest, and require cross-platform focal reproducers before delivery.
- spec-146 clarifies the persistence doctrine table-by-table: `state.db`
  is a mixed lifecycle database, `gate-findings.json` remains the primary
  gate/risk/verify artifact, and `state.db.gate_findings` is documented as
  a non-primary transitional placeholder.
- Runtime Layer Tunables docs now show implemented defaults for
  `AIENG_HOOK_CACHE_TTL_SEC`, `AIENG_AUTOFORMAT_DEBOUNCE_SEC`,
  `AIENG_NDJSON_MAX_LINES`, and `AIENG_NDJSON_MAX_BYTES`; only
  host-preflight/budget-profile names remain reserved.
- `.ai-engineering/cache/gate/` is documented as an existing bounded cache
  with 24-hour/256-entry limits and existing status/clear commands.
- Test suite runs faster with no loss of coverage, security, or
  governance assertions: the doctor and skills integration tests now
  share a module-scoped read-only install fixture (`installed_project_ro`)
  instead of re-running the ~2s installer per test, the docs link walker
  is memoised, and the default `pytest` invocation no longer forces `-v`
  (CI passes it explicitly). A new top-level `Makefile` exposes parallel
  `make test` / `test-unit` / `test-integration` / `test-e2e` targets via
  pytest-xdist, with integration and full runs grouped by `--dist
  loadscope` so module-scoped fixtures build once per worker.

### Fixed

- The release changelog gate no longer false-trips on non-breaking
  release-path *fixes*. `validate_changelog` now exempts the `### Fixed`
  subgroup from the "release-path semantic changes must be documented under
  `### BREAKING`" requirement, since Keep-a-Changelog `### Fixed` entries are
  non-breaking by definition. A release-path fix mentioning tokens like
  "release packet" under `### Fixed` no longer blocks `ai-eng release`;
  genuine semantic changes under `### Added`/`### Changed`/`### Removed` still
  require a `### BREAKING` entry. Guarded by
  `tests/unit/test_changelog_parser.py`.
- `ai-eng install` now writes a managed `.ai-engineering/.gitignore` so the
  transient, per-install, and derived artifacts it generates — the audit and
  observation NDJSON streams, per-install state SoTs, the compiled & signed
  OPA bundle (`state/runtime/bundle.tar.gz`), and the per-install OPA signing
  outputs (`policies/.signatures.json`, `policies/.manifest`) — never leak
  into a consumer's version control. Sources of truth (`policies/*.rego`,
  `manifest.yml`, `specs/*.md`, `notes/`, and the `state/hooks-manifest.json`
  integrity baseline) stay tracked, and a secret-material safety net
  (`*.pem`, `*.key`, `*.p12`, `*.pfx`, `credentials*.json`) blocks accidental
  key commits under the managed tree. The file is written programmatically
  rather than copied from the template tree because the wheel only ships
  `templates/**/*.{md,yml,json}` and a dotfile has no matching extension;
  it is create-only outside FRESH installs so operator edits survive a
  reinstall.
- spec-152 (W2) — the `CI Result` aggregate gate now evaluates the
  `no-suppression` (Anti-Suppression, Article VII) job. It was previously
  absent from both `ci-check-result.needs` and every evaluated array, so a
  suppression-marker failure was awaited by no one and never blocked the
  merge (fail-open). `no-suppression` is now wired into `build-check.needs`,
  `ci-check-result.needs`, and the `code_conditional` class, and a new
  membership gate (`tests/unit/workflows/test_ci_aggregate_membership.py`)
  asserts every blocking job is evaluated so the hole cannot reopen.
- spec-152 (W5, T-34) — docs-only changes no longer fully bypass CI.
  `docs/**` was in the `paths-ignore` of both the `push` and `pull_request`
  triggers, so a docs-only change never started the workflow and the required
  `CI Result` check defaulted to success — a docs-only PR introducing a
  machine path, a leaked secret in a fenced block, or a malformed workflow
  snippet would merge unchecked (fail-open, D-152-22). `docs/**` is removed
  from `paths-ignore`; a new lightweight `docs-gate` job runs the CHEAP,
  docs-relevant checks (content/link/anchor integrity via `pytest tests/docs`,
  governance `ai-eng check`, a `gitleaks` secret scan, and the workflow policy
  check) whenever docs or code change. It is wired into `ci-check-result.needs`
  and a new required `docs_conditional` aggregate class; the heavy test matrix
  stays gated to `code == 'true'`. Pure prose extensions (`.mdx`/`.rst`/`.txt`)
  remain ignored. Guarded by `tests/unit/workflows/test_docs_gate.py`.
- spec-152 (W5, T-37) — re-pinned `EndBug/label-sync` in `label-sync.yml` to
  the v2.3.3 *peeled* commit (`52074158…`). The prior pin (`da00f2c…`) was the
  annotated-tag *object* SHA, which is not a published ref tip, so the W1
  reachability audit flagged it as shaped-but-unreachable (D-152-06). The
  intended version is unchanged; only the SHA now resolves via
  `git ls-remote … refs/tags/v2.3.3^{}`. `--check-reachability` is now clean.
- Release finalization now caps GitHub Release body notes below GitHub's
  125,000-character limit, uploads the full changelog section as
  `release-notes-full.md`, and writes non-empty attestation verification
  proof logs so release packet asset uploads do not fail on zero-byte files.
- spec-146 fixes `ai-eng update` to read SQLite ownership rows from
  `state.db.ownership_map` before evaluating file changes, so team/deny
  rules protect both existing files and denied missing files without
  requiring the retired `ownership-map.json` sidecar.
- spec-146 fixes spec history consolidation so `ai-eng cleanup specs`,
  `spec_lifecycle.py mark_shipped`, and `ai-eng maintenance spec-reset`
  all upsert the canonical 7-column `_history.md` projection instead of
  leaving shipped sidecars unrecorded or writing legacy 4-column rows.

### Removed

- spec-152 (W2) — deleted `.github/workflows/ci-build.yml` (orphaned
  post-CI build triggered by `workflow_run`; its `dist` artifact had zero
  consumers — releases build from a tag in `release.yml`, not from a
  reused CI artifact). Use the release-pipeline artifacts. Breaking per
  D-152-25 (hard deletion, no shim); coupled tests updated in lockstep.
- spec-152 (W2) — deleted `.github/actions/run-gates` (unreferenced
  composite; zero `uses:` references — the lint/type-check/unit/integration
  gate commands are invoked inline in `ci-check.yml`). Breaking per
  D-152-25; its drift tests in `test_composite_actions.py` removed so the
  deletion fails loud rather than leaving an orphaned fixture.
- spec-146 deletes the duplicate IOC attribution copy at
  `.ai-engineering/references/IOCS_ATTRIBUTION.md` and the matching
  installer-template duplicate; the single home is now
  `.ai-engineering/security/iocs/IOCS_ATTRIBUTION.md`.
- spec-146 deletes `.ai-engineering/team/lessons.md`; unique content is
  preserved in `.ai-engineering/LESSONS.md`.
- spec-146 deletes stale state sidecars
  `.ai-engineering/state/strategic-compact.json` and
  `.ai-engineering/state/instinct-observations.ndjson`; strategic compact
  now writes under `.ai-engineering/runtime/`, and
  `observation-events.ndjson` remains the instinct-learning log.
- spec-146 deletes test-only preservation suites for removed modules and
  adds import/caller-inventory guards so the deleted surfaces do not return.
## [0.7.0] - 2026-05-18

### BREAKING

- semantic-release and manual CI commit-back are hard-removed from the
  framework release spine. `ai-eng release <VERSION>` is now the sole
  authority for version bumps, changelog promotion, release branch/tag
  creation, and publish hand-off. The tag-triggered Release workflow
  validates artifacts on TestPyPI before PyPI Trusted Publishing and
  attaches the release packet (checksums, SBOM, attestations/provenance,
  and release notes) to the GitHub Release.
- The prior spec-101 installer BREAKING contract remains in force for
  release notes and operator automation: `EXIT 80`, `EXIT 81`,
  `python_env.mode`, and `14 stacks` stay documented here so the most
  recent BREAKING block preserves those required keywords.

### Fixed

- Release recovery hardening: remove a secret-shaped fixture literal from
  `.gitleaksignore` comments so the Security Audit does not self-detect the
  allowlist file, and unwrap `ai-eng --json verify --release` output into the
  direct `release-readiness.json` evidence payload consumed by the Release
  workflow.

### Run summary — multi-spec autonomous orchestration

This Unreleased section captures a single multi-spec autonomous `--no-hitl`
run that landed 4 spec drafts across 22 milestones:

| Spec | Status | Deferred |
|------|--------|----------|
| **spec-138** harness-persistence-strategy | M1, M2, M3, M4, M5 ✅ | M1.T4 (upstream Claude Desktop bug), M1.T5 (caller migration sub-spec), M1.T6 (superseded by M4.T5 gate), M4.T6 (post-merge perf baseline) |
| **spec-139** framework-performance-hardening | M1, M2, M3, M4, M5, M6, M7, M8, M9 ✅ | none |
| **spec-140** less-is-more-quality-engine | W1, W2, W2.5 (test-split), W3 ✅ | W2.5 production-side split (D-140-07 LOC gate), W3 pass@k eval (operator runtime) |
| **spec-141** semgrep-pack-coverage | M1, M2, M3, M4 ✅ | M5.T1 + M5.T2 CI triage (post-merge dependent), M1.T6 + M2.T4 timing baselines |

Every deferred item is documented in its plan archive at
`.ai-engineering/specs/archive/spec-NNN-plan.md` with rationale. The
deferrals are intentional — each one names the follow-up gate or
sub-spec that owns the residual work.

### spec-138 — Harness Persistence Strategy (M1 + M2 + M3 + M4 + M5)

#### Added — hot-path SQL ban (D-138-06 hard gate)

- `tests/architecture/test_no_sql_on_hot_path.py` — parametrized
  per-event test (PreToolUse / PostToolUse / UserPromptSubmit /
  SubagentStop / Notification) asserting no hot-path hook imports
  `sqlite3` or its submodules. AST-based scan resolves `import` /
  `from-import` statements without false positives on docstring
  archaeology. Hot-path coverage invariant: the event set scanned must
  equal `HOT_PATH_EVENTS` (catches silent omission of new hot paths).
  6/6 cases pass on the current hook roster.

Mantra: **One canonical store per datum. Caches are rebuildable. No silent
dual-writes.** Lands the M1 bug clearance of the silent dual-write failure
mode: every `INSERT INTO events` from the policy-decision hot path was
writing to a phantom schema and swallowing every `sqlite3.Error`; the
`audit-index.sqlite` 0-byte zombie was being opened by `runtime-stop.py:474`
and the `session_token_rollup` query failed silently every Stop. Also
lands the M2 doctrine document, the CONSTITUTION.md §13 amendment that
ratifies the SSOT-PD rule, and the CLAUDE.md §0 bootstrap pointer that
replaces the misleading `state.db.decisions` query instruction. M5 closes
out the dead-schema cleanup: migration `0008_drop_hooks_integrity` removes
the `hooks_integrity` table (D-138-01 — no consumer materialised; the
sha256 manifest at `state/hooks-manifest.json` plus the NDJSON
`integrity_violation` event stream cover the surface), and the new
`ai-eng doctor --check state-db` subcommand surfaces table-by-table
health (row counts, mtime, advisory flags for empty rows-expected tables).
M3 lands the autopopulation writers: `/ai-brainstorm` and `/ai-plan`
approval handlers parse the `## Decisions` section of `spec.md` / `plan.md`
and UPSERT every `D-NNN-NN` into `state.db.decisions`; `ai-eng decision
backfill` walks active specs + archive + CHANGELOG + CONSTITUTION + CLAUDE.md
(197 decisions on the real repo); the installer pipeline records one
`install_steps` row per phase outcome; new `ai-eng ownership import`
imports `.github/CODEOWNERS` into `state.db.ownership_map`. M4 (events as
derived cache + NDJSON rotation) remains scoped in
`.ai-engineering/specs/archive/spec-138-plan.md` and deferred to follow-up
work.

#### Added — persistence doctrine (M2)

- `docs/persistence-doctrine.md` — authoritative SSOT-PD reference.
  Declares the four-tier persistence model (Tier 1 NDJSON audit log,
  Tier 2 SQLite `state.db`, Tier 3 JSON/YAML config, Tier 4 Markdown
  human-authored truth), the five derived caches (`state.db.events`,
  `state.db.decisions_fts`, `state.db.ownership_map`, `state.db.decisions`,
  `state.db.install_steps`) with their rebuild commands, the five strict
  rules (no silent dual-writes; audit chain stays on NDJSON; hot path
  never writes SQL; schema authority in Pydantic not DDL; hard deletes —
  no shims), the operator surface (`ai-eng decision list`, `ai-eng decision
  backfill`, `ai-eng ownership import`, `ai-eng doctor --check state-db`,
  SessionEnd rebuild semantics), and the SSOT-PD / Article-III / derived
  cache / hot path / cold path / tier / polyglot persistence glossary.
  Cites the canonical schema declaration at
  `src/ai_engineering/state/migrations/0001_initial_schema.py:27-217`.
- `CONSTITUTION.md` — new Prohibition #8 ratifies the SSOT-PD rule:
  "Every datum has exactly one canonical writable store. Derived caches
  are explicitly labelled (named, with a rebuild command) and rebuildable
  on demand."  Links the new doctrine document.
- `src/ai_engineering/templates/project/CANONICAL.md` §13 — new hard rule
  #7 mirrors the SSOT-PD Prohibition into the canonical cross-IDE payload.
  Regenerator propagates to `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`,
  `.github/copilot-instructions.md` (byte-equivalent).
- `src/ai_engineering/templates/project/CLAUDE.md` §0 + canonical mirror —
  replaces the misleading "query `state.db.decisions` table" bootstrap
  step (the table is empty on every fresh checkout until M3 ships the
  autopopulation writers) with a pointer to the persistence doctrine.
  Adds a one-sentence paragraph after §0 directing operators to the
  doctrine for the four-tier model and rebuild semantics. Mirror diet
  preserved per D-138-05.
- `tests/architecture/test_persistence_doctrine_exists.py` — pins the
  doctrine file existence, its six canonical section headers (`## The
  SSOT-PD rule`, `## The four tiers`, `## Derived caches`, `## Strict
  rules`, `## Operator surface — what changes for you`, `## Glossary`),
  the CONSTITUTION.md citation, and the CLAUDE.md §0 + §13 references.
  Drift fails CI so a future operator cannot silently delete the
  doctrine without breaking the identity contract.

#### Added — state.db autopopulation (M3)

- `src/ai_engineering/brainstorm/spec_approval.py` — new pure parser +
  approval handler. Reads the `## Decisions` section of `spec.md` /
  `plan.md`, extracts every `D-NNN-NN` reference with its title and
  rationale (inline `Rationale:` / `*Rationale*:` / `**Rationale**:`
  markers, including wrapped continuation lines), and UPSERTs into
  `state.db.decisions` via `upsert_decision_rows_raw`. Idempotent.
  Exposed at the package level as
  `ai_engineering.brainstorm.handle_spec_approval` so `/ai-brainstorm`
  and `/ai-plan` skill handlers fire it at approval time (M3.T1, M3.T2).
- `src/ai_engineering/cli_commands/decisions_cmd.py` — `ai-eng decision
  backfill` now walks `.ai-engineering/specs/archive/*.md` in addition
  to active specs + CHANGELOG + CONSTITUTION + CLAUDE.md (M3.T3). The
  summary line distinguishes `backfilled` from `already_current` so
  operators see net-new vs idempotent re-run counts. Real-repo
  invocation surfaces 197 decisions across `specs=55`, `changelog=51`,
  `specs-archive=91`.
- `src/ai_engineering/state/state_db.py` — new `upsert_install_step`
  helper (single-row UPSERT into `install_steps`) and
  `upsert_ownership_rows_raw` helper (row-dict UPSERT into
  `ownership_map`, used by the CODEOWNERS importer). Both are
  idempotent; lazy bootstrap ensures the schema exists before the
  first INSERT.
- `src/ai_engineering/installer/phases/pipeline.py` — `PipelineRunner`
  now calls `upsert_install_step` after every phase outcome (`done` /
  `failed` / `non_critical_failure`) so `state.db.install_steps`
  reflects per-phase state without the legacy `install-state.json`
  sidecar (M3.T4). Fail-open: an UPSERT error never masks the underlying
  phase failure.
- `src/ai_engineering/cli_commands/ownership_cmd.py` — new
  `ai-eng ownership import` subcommand. Parses `.github/CODEOWNERS`
  (or `--source <path>`), UPSERTs each `<pattern> @owner...` rule into
  `state.db.ownership_map`. Idempotent. Dry-run mode (`--dry-run`)
  prints parsed rules without writing (M3.T5).
- `tests/unit/state/test_decision_writer_integration.py`,
  `tests/unit/cli/test_decision_backfill.py`,
  `tests/unit/installer/test_install_steps_writer.py`,
  `tests/unit/cli/test_ownership_import.py` — 23 new unit tests covering
  every writer + parser + idempotency + dry-run + archive walk + sort
  order (M3.T6).

#### Removed — silent dual-write paths

- `src/ai_engineering/governance/decision_log.py` — deleted `_insert_events_row`
  (writing to phantom schema, swallowing `sqlite3.Error`), `_events_table_present`,
  and `STATE_DB_REL`. Module no longer imports `sqlite3`. NDJSON is the
  canonical store for events per Article-III / spec-138 SSOT-PD; `state.db.events`
  is a SessionEnd-rebuilt derived cache via `ai-eng audit index`.
- `src/ai_engineering/state/audit_index.py` — deleted `_delete_legacy_index`
  and `_LEGACY_INDEX_REL` constant. The legacy `audit-index.sqlite` is absent
  from every operator checkout and from this repo.

#### Fixed — runtime-stop.py zombie read

- `.ai-engineering/scripts/hooks/runtime-stop.py` and template mirror —
  `_AUDIT_INDEX_REL` now points at `state.db` (unified projection per
  spec-123 D-123-22), not the 0-byte zombie. The `session_token_rollup`
  view is defined on `state.db` via `audit_index.py:131`.

#### Added — contract test

- `tests/unit/governance/test_decision_log.py` —
  `test_no_sql_dual_write_module_no_longer_imports_sqlite` asserts on
  module attributes (sqlite3 not imported, `_insert_events_row` and
  `STATE_DB_REL` removed). Prevents regression of the dual-write bug.

#### Removed — hooks_integrity table (M5)

- `src/ai_engineering/state/migrations/0008_drop_hooks_integrity.py` —
  new forward-only migration drops the `hooks_integrity` table and its
  `idx_hooks_recent` index (D-138-01). The table was declared by
  `0001_initial_schema` as a "verification ledger populated at runtime
  by `run_hook_safe`" but no consumer ever materialised. Per SSOT-PD
  (CONSTITUTION.md Prohibition #8), the sha256 manifest at
  `state/hooks-manifest.json` is the single canonical store for hook
  script integrity, and the NDJSON `integrity_violation` event stream
  (mirrored via `state.db.events` after the SessionEnd rebuild) covers
  the audit surface. `0001_initial_schema` retains its original CREATE
  TABLE per the forward-only contract — the drop lands in 0008 on the
  next bootstrap.
- `src/ai_engineering/state/migrations/0002_seed_from_json.py` —
  removed the docstring promise that "runtime hook checks land their
  first rows" into `hooks_integrity`. Replaced with a pointer to
  migration 0008 documenting the drop rationale. `BODY_SHA256` updated
  to the new body hash.
- `src/ai_engineering/state/state_db.py` — module docstring updated
  from "Seven STRICT tables" to "Six STRICT tables", with the legacy
  `hooks_integrity` entry removed.
- `src/ai_engineering/cli_commands/audit_cmd.py` — `audit health`
  removes `hooks_integrity` from `required_tables`, so the integrity
  check no longer fails when the (intentionally absent) table is
  missing.
- `tests/unit/state/test_lazy_bootstrap.py` —
  `test_business_tables_exist` no longer expects `hooks_integrity`;
  new `test_hooks_integrity_table_absent_after_bootstrap` asserts the
  drop via `SELECT name FROM sqlite_master WHERE name='hooks_integrity'`
  returns no rows. `_expected_migration_ids()` adds
  `0008_drop_hooks_integrity` to the canonical migration set.

#### Added — `ai-eng doctor --check state-db` (M5)

- `src/ai_engineering/cli_commands/doctor_state_db.py` (new) — new
  focused doctor sub-check. Connects to `state.db` read-only, enumerates
  the canonical tables declared by migrations 0001 through 0008, and
  prints a structured report (table | rows | last_modified | advisory).
  Advisories flag tables expected to carry rows once steady-state
  operation kicks in but currently empty (`decisions` post-`/ai-brainstorm`
  or backfill, `install_steps` post-installer-run). Missing tables and
  missing DB file both surface as advisories rather than failures.
  Per the spec-138 M5 acceptance gate the check is informational only:
  exit code is always 0, never blocks.
- `src/ai_engineering/cli_commands/core.py` — `_run_focused_doctor_check`
  now dispatches `state-db` to the new module; help text updated to
  list both supported `--check` values (`hot-path`, `state-db`).
- `tests/unit/cli/test_doctor_state_db.py` (new) — covers the four
  acceptance points: every canonical table appears in the report (and
  `hooks_integrity` does NOT); empty `decisions` triggers the advisory
  banner; absent DB file exits 0 with advisories instead of crashing;
  unknown `--check` value still raises `BadParameter` and lists
  `state-db` among supported values.

### spec-139 — Framework Performance Hardening (partial: M1 + M2 + M3 + M4 + M6 + M7 + M8 + M9)

Mantra: **ai-engineering NEVER causes WindowServer to hang. Every wave
declares a concurrency budget. Every LLM call earns its place.** Lands
M1 (concurrency budget primitive that closes the kernel-panic class),
M2 (host preflight probe + `ai-eng host probe` CLI), M3 (Phase-0 stack
context pre-resolution — single manifest read propagated as
`STACK_CONTEXT` to every dispatched agent), M4 (stale-x3 correction),
M7 (deterministic `ai-eng spec verify --sections` +
`ai-eng plan dag-build` pre-passes), M8 (commit + PR compose
determinism — `commit_compose.py --desc` mandatory across the chain
and `pr_body_compose.py` consumes spec `summary:` frontmatter without
an LLM call), and M9 (CLAUDE.md tunables reconciliation + drift gate).
M5 (hot-path hook cache) remains scoped in
`.ai-engineering/specs/archive/spec-139-plan.md` and deferred to a
focused follow-up.

#### Added — Phase-0 stack context pre-resolution (M3)

- `src/ai_engineering/autopilot/stack_context.py` (new ~210 LOC) —
  pure-stdlib `resolve_stack_context()` reads
  `.ai-engineering/manifest.yml` ONCE per autopilot session and emits a
  dict keyed `stacks` / `test_command` / `format_command` /
  `lint_command` (plus a `degraded` flag for fail-open detection).
  `write_stack_context()` persists the JSON to
  `.ai-engineering/runtime/autopilot/<active>/stack-context.json`
  (gitignored — session state, not source of truth). Fail-open
  everywhere: missing or unreadable manifest collapses to the degraded
  default rather than crashing.
- `src/ai_engineering/autopilot/__init__.py` — new package scaffold.
- `.claude/skills/ai-autopilot/handlers/phase-deep-plan.md` — new
  "Step 0 — Stack context resolution (spec-139 M3)" block invokes the
  resolver once and documents the `STACK_CONTEXT=<JSON>` dispatch-prompt
  contract; the Step 2 dispatch list now requires the variable on every
  agent invocation. Mirrored across `.codex/`, `.gemini/`, `.github/`,
  `.opencode/`, `.cursor/`, and `templates/project/` via
  `ai-eng dev sync`.
- `.claude/skills/ai-autopilot/handlers/phase-implement.md` — Step 2b
  now carries item 3b: every Build agent invocation MUST include
  `STACK_CONTEXT=<JSON>` in the dispatch prompt.
- `.claude/agents/ai-build.md`, `ai-explore.md`, `ai-plan.md` rewritten:
  stack reads come from `STACK_CONTEXT` dispatch-prompt variable; the
  remaining `manifest.yml` mentions are explicit "do NOT re-read"
  pointers. `resolve_stack_context()` is the documented fallback for
  non-autopilot dispatch.
- Closes the N-manifest-reads-per-run regression flagged in the
  framework-performance-hardening brief §4.3 (each redundant Read used
  to fan out 8 hooks per dispatch).

#### Added — Phase-0 stack context tests (M3)

- `tests/integration/test_stack_context_propagation.py` — 10 cases
  defending the four M3 contracts: canonical key shape, python default
  commands, polyglot stack fan-out, idempotency, missing-manifest
  degraded default, manifest-without-stacks degraded default,
  unreadable-manifest fail-open (directory passed for path), valid
  JSON round-trip, byte-stable sorted output across two writes, and
  automatic runtime subdir creation on first write.

#### Added — concurrency budget primitive (M1)

- `src/ai_engineering/config/concurrency.py` (new ~280 LOC) — single
  source of truth for `AIENG_MAX_WAVE_AGENTS`, `AIENG_MAX_QUALITY_AGENTS`,
  `AIENG_MAX_THREAD_WORKERS` env vars plus `performance.concurrency.*`
  manifest knobs. Resolver functions: `resolve_wave_cap`,
  `resolve_quality_cap`, `resolve_thread_workers`. Auto-tune algorithm
  per D-139-01: pressure_pct ≥ 50 → cap=1 serial; else
  `min(free_ram_gb // 4, cores // 2, 6)` clamped to `[2, 6]`.
  `HostProbe` dataclass is the injectable port — populated by spec-139
  M2 (deferred); until then the resolver falls back to an
  `os.cpu_count`-only estimator.
- `src/ai_engineering/config/manifest.py` — schema gained
  `performance.concurrency.{max_wave_agents,max_quality_agents,max_thread_workers}`.
- `src/ai_engineering/policy/orchestrator.py:489` and `:1209` — replaced
  `max_workers = max(1, len(checkers))` with
  `max(1, min(len(checkers), _max_thread_workers()))`. The orchestrator
  reads the env/manifest cap on every wave; floor preserved at 1.
- `.claude/skills/ai-autopilot/handlers/phase-deep-plan.md`,
  `phase-implement.md`, `phase-quality.md` — added the "Concurrency cap
  (spec-139 M1)" section documenting the batching pattern and the cap's
  precedence chain. Mirrored across `.codex/`, `.gemini/`,
  `.github/`, `.opencode/`, `.cursor/` via `ai-eng dev sync`.
- `.claude/agents/ai-autopilot.md` — description annotated with
  "(capped via AIENG_MAX_WAVE_AGENTS)" so the contract is visible to
  every dispatcher reading the agent header.

#### Added — concurrency budget tests (M1)

- `tests/architecture/test_concurrency_budgets.py` — 12 cases covering
  env-precedence, manifest, auto-tune, stressed-host degrade, explicit
  serial, cap-larger-than-N, quality-cap clamping, and floor invariant.
- `tests/unit/policy/test_orchestrator_max_workers.py` — 10 cases
  validating env/manifest/default precedence and the `max(1, min(N, cap))`
  arithmetic the orchestrator uses.
- `tests/unit/test_orchestrator_wave2.py::test_wave2_uses_thread_pool_executor_max_workers_5`
  — assertion relaxed from "must equal 5" to "must be in [1, 5]" so the
  new cap (default 4) does not break the existing Wave 2 invariant
  while still preventing unbounded fan-out.

#### Added — host preflight probe + `ai-eng host probe` CLI (M2)

- `src/ai_engineering/adapters/host/probe.py` (new ~280 LOC) — adapter
  layer (Hexagonal §10.8, D-139-09) hosting the per-platform
  measurements that populate `HostProbe`. Dispatches by `sys.platform`
  to `_probe_darwin` (`vm_stat` / `sysctl hw.memsize` / `sysctl hw.ncpu`
  / `sysctl vm.swapusage` with 1-second timeouts), `_probe_linux`
  (`/proc/meminfo` + `/proc/swaps` + `os.cpu_count`), `_probe_windows`
  (`psutil` when importable, degraded fallback when not). Every backend
  is fail-open: subprocess errors, parse failures, and unsupported
  platforms collapse to a zero-valued snapshot so the resolver clamps
  to `WAVE_FLOOR` rather than crashing.
- `src/ai_engineering/adapters/__init__.py`,
  `src/ai_engineering/adapters/host/__init__.py` — adapter package
  scaffolding. Re-exports `HostProbe` from
  `ai_engineering.config.concurrency` so the single source of truth
  for the dataclass stays in the inner ring.
- `src/ai_engineering/cli_commands/host_cmd.py` (new ~60 LOC) +
  `cli_factory.py` registration — adds `ai-eng host probe` with an
  optional `--json` flag. Default emits a single-line JSON; `--json`
  pretty-prints. Payload schema (sorted keys): `cores`, `free_ram_gb`,
  `ok_to_dispatch`, `platform`, `pressure_pct`, `recommended_cap`,
  `swap_used_pct`. The CLI deliberately does NOT emit a
  `host_capacity` framework event — the caller is the operator, no
  skill dispatched (spec-139 M2.T4).
- `src/ai_engineering/state/observability.py` — new `emit_host_capacity`
  helper that skill-side callers (`/ai-autopilot` Phase 0,
  `/ai-build` step 0) use to log the probe payload to
  `framework-events.ndjson` with the `caller` field identifying the
  dispatching skill.
- `tools/skill_domain/event_schema.py` — added `host_capacity` to
  `ALLOWED_EVENT_KINDS` so the new event passes the schema validator.
- `.claude/skills/ai-autopilot/SKILL.md` — Step 0 now runs
  `ai-eng host probe` and aborts with an operator warning if
  `ok_to_dispatch == False`. Mirror trees regenerated via
  `ai-eng dev sync`.

#### Added — host preflight tests (M2)

- `tests/integration/test_host_preflight.py` — 14 cases covering the
  four canonical scenarios (healthy host, high memory pressure, low
  free RAM, single-core) plus swap thrash, fail-open backend errors,
  and platform-dispatch verification.
- `tests/unit/cli/test_host_probe_cli.py` — 6 cases asserting the JSON
  shape, `--json` pretty-print, `ok_to_dispatch=False` on stressed
  hosts, and the no-emit contract for the operator-facing CLI.
- `tests/architecture/test_layer_isolation.py` — 3 cases confirming
  `adapters/host/` lives in the adapter ring per D-139-09: the
  directory exists, no `.py` file imports forbidden outer-ring modules
  (cli_commands, governance, installer, etc.), and the package
  imports cleanly without side-effects.

#### Fixed — stale "x3" agent description (correctness/safety)

- `.claude/agents/ai-autopilot.md:3` and every mirror surface
  (`.codex/`, `.gemini/`, and the `src/ai_engineering/templates/project/`
  tree) — replaced "verify+guard+review x3" with "single fail-loud
  quality round (verify+guard+review — spec-131 D-131-05)". Closes the
  interpretive blast radius where an LLM could read the description as
  license to run 3 rounds × 16 agents = 48 invocations contradicting
  the canonical contract at `phase-quality.md:3`.

#### Added — agent description contract test

- `tests/architecture/test_agent_description_contract.py` — parametrized
  test forbids "verify+guard+review x3", "verify+guard+review ×3",
  "review x3", "review ×3", "3 rounds of verify", "three rounds of
  verify" from any committed file under `.claude/`, `.codex/`, `.gemini/`,
  `.github/`, `.opencode/`, `.cursor/`, or `src/.../templates/project/`.

#### Added — SessionEnd rotation throttle + state.db incremental_vacuum (M6)

- `.ai-engineering/scripts/hooks/runtime-rotate-throttled.py` (new) —
  stdlib-only SessionEnd wrapper that limits the
  `.ai-engineering/scripts/runtime_rotate.py` retention sweep to **at
  most once per `AIENG_RUNTIME_ROTATE_THROTTLE_SEC`** (default 3600 s =
  1 h). Uses `.ai-engineering/runtime/.rotate-lastrun` as the mtime
  sentinel; subprocess timeout 25 s sits inside the IDE-side 30 s hook
  budget so cleanup + heartbeat write always complete. Fail-open on
  every error so the rotation never blocks SessionEnd. Per D-139-12,
  this wrapper narrows to the retention sweep only — the NDJSON
  tail-truncation lands via spec-138 M4 wiring.
- `.ai-engineering/scripts/hooks/runtime-session-end.py` — added an
  opportunistic `PRAGMA incremental_vacuum(1000)` against `state.db`
  after the SessionEnd summary emits. Runs only when
  `freelist_count > 1000` so the steady-state SessionEnd path stays
  cheap; uses a 250 ms busy timeout so a contended DB never blocks the
  hook budget. Successful vacuums emit a `state_db_incremental_vacuum`
  framework_operation event carrying `freelist_before`,
  `freelist_after`, and `pages_reclaimed` for audit telemetry.
- Cross-IDE SessionEnd wiring (3 active runtime surfaces):
  - `.claude/settings.json` `SessionEnd` — added the throttle wrapper
    after `runtime-session-end.py` so the summary + vacuum runs first
    and the retention sweep second (timeout 30 s).
  - `.codex/hooks.json` `Stop` — same wrapper, routed via
    `AIENG_HOOK_ENGINE=codex` so audit telemetry tags the right engine.
  - `.gemini/settings.json` `AfterAgent` — same wrapper, routed via
    `AIENG_HOOK_ENGINE=gemini CLAUDE_HOOK_EVENT_NAME=SessionEnd` so the
    wrapper's event-name guard accepts the Gemini end-of-session event.
  - `.github/` (Copilot) is N/A (no conversational SessionEnd primitive);
    `.opencode/` and `.cursor/` are deferred until those mirror
    directories materialise (spec-128 Wave 4 follow-up).
- `.ai-engineering/state/hooks-manifest.json` — regenerated; hookCount
  73 → 74 to pin the new throttle wrapper's sha256.
- New env var `AIENG_RUNTIME_ROTATE_THROTTLE_SEC` (default 3600,
  positive int seconds; malformed / zero / negative falls back to the
  default). Documentation hookup lands via spec-139 M9 tunables table
  (parallel sibling task — sibling run will add the row).

#### Added — M6 tests

- `tests/integration/test_runtime_rotation_lifecycle.py` (new, 7 cases)
  — drives the throttle wrapper as a subprocess against a tmp_path
  project tree. Asserts first SessionEnd touches the sentinel and runs
  rotation, second SessionEnd within the throttle window is a no-op
  (sentinel mtime unchanged), and an `AIENG_RUNTIME_ROTATE_THROTTLE_SEC`
  override releases the gate after the configured window. Adds three
  resolver micro-tests (default 3600 s, invalid env fallback, positive
  int honoured) and a defence-in-depth assertion that non-SessionEnd
  events short-circuit before touching the sentinel.
- `tests/architecture/test_hook_wiring_parity.py` (new, 6 cases) —
  asserts every active runtime surface wires
  `runtime-rotate-throttled.py` exactly once into its
  end-of-session event (Claude `SessionEnd`, Codex `Stop`, Gemini
  `AfterAgent`), AND that the Codex / Gemini commands carry the
  `AIENG_HOOK_ENGINE=<engine>` label so audit telemetry stays
  attributable. The wiring is keyed on script basename so future
  argv refactors (bridge routing, env prefix changes) remain
  refactor-safe.
- `tests/unit/hooks/test_state_db_incremental_vacuum.py` (new, 4 cases)
  — exercises the `_incremental_vacuum_if_needed` helper directly with
  a tmp_path SQLite DB seeded with a synthetic freelist. Confirms the
  vacuum runs when `freelist_count > 1000`, skips when ≤1000, no-ops
  cleanly when the DB is absent, and no-ops without raising on a
  corrupt DB file.

#### Added — deterministic spec verify + plan DAG construction (M7)

- `src/ai_engineering/cli_commands/spec_cmd.py` — new `--sections <path>`
  flag on `ai-eng spec verify` (spec-139 M7.T1). Deterministic
  regex / string-contains scan for the five required headers declared in
  `.ai-engineering/reference/spec-schema.md`: `## Summary`, `## Goals`,
  `## Non-Goals`, `## Decisions`, `## Risks`. Optional headers
  (`## References`, `## Open Questions`) do not influence validity.
  Emits JSON `{"path", "missing_sections", "present_sections", "valid"}`
  on stdout (or the error envelope on stderr when the path is missing)
  and exits 0 when every required section is present, 1 otherwise.
  Pure-Python, zero-token — the gate runs before any LLM validation
  pass so structural failures short-circuit the LLM call.
- `src/ai_engineering/cli_commands/plan_cmd.py` (new) — new
  `ai-eng plan dag-build <subdir>` command (spec-139 M7.T2). Walks
  `<subdir>/sub-*/plan.md`, parses each plan's `exports:` and
  `imports:` frontmatter lists (tolerating both flow `[a, b]` and
  block-style YAML lists), resolves the producer/consumer graph, and
  runs a Kahn-style topological sort to assign waves. Emits JSON
  `{"waves": [[sub_name, ...], ...], "conflicts": [...]}`. Exits 0
  when the DAG resolves cleanly; exits 1 when cycles or unresolvable
  imports surface. Pure-Python, ~210 LOC.
- `src/ai_engineering/cli_factory.py` — new `plan` Typer sub-group
  registers `dag-build` so the command is reachable as
  `ai-eng plan dag-build`. The `spec verify` command picked up the
  `--sections` option without growing a new verb (drop-in flag).
- `.claude/skills/ai-brainstorm/SKILL.md` — Step 6 now invokes
  `ai-eng spec verify --sections .ai-engineering/specs/spec.md` BEFORE
  the LLM validation pass; exit-1 short-circuits LLM reasoning until
  the operator patches the missing headers (spec-139 M7.T3).
- `.claude/skills/ai-autopilot/handlers/phase-orchestrate.md` — new
  "Step 0 -- Deterministic DAG Pre-Pass" calls
  `ai-eng plan dag-build .ai-engineering/runtime/autopilot` FIRST. On
  exit 0 the script's wave assignment is accepted verbatim and the
  phase jumps to Step 5; only the exit-1 conflict path falls through to
  LLM-driven file-overlap analysis (spec-139 M7.T4).
- Cross-IDE skill mirrors regenerated via `ai-eng dev sync` so
  `.codex/`, `.gemini/`, `.github/`, `.opencode/`, `.cursor/`, and the
  `src/ai_engineering/templates/project/` tree carry the same Step 0 /
  Step 6 wiring.

#### Added — M7 deterministic CLI tests

- `tests/unit/cli/test_spec_verify.py` (new, 4 cases) — covers
  `spec verify --sections` happy path (every required header → valid),
  missing-Risks failure (exit 1, JSON missing list isolates the gap),
  optional-section absence (References / Open Questions absent →
  valid=true), and missing-file error envelope (nonexistent path →
  exit 1, JSON `error` field surfaces the operator-facing message).
- `tests/unit/cli/test_plan_dag_build.py` (new, 5 cases) — covers
  `plan dag-build` no-imports-all-wave-0, linear-chain one-per-wave,
  no-overlap independent set, cycle detection (conflicts non-empty,
  exit 1, both participants named), and unresolvable-import diagnostics
  (phantom token surfaces in the conflict message).
- `tests/unit/cli/fixtures/spec_verify/{complete,missing_risks,no_optionals}.md`
  + `tests/unit/cli/fixtures/plan_dag/{all_independent,linear_chain,no_overlap,cycle}/sub-*/plan.md`
  — committed fixture trees so the deterministic checks reproduce on a
  fresh checkout without harness side effects.

#### Added — compose determinism (M8)

- `.claude/skills/ai-commit/SKILL.md` Step 7 — `commit_compose.py
  --desc "<plan-task-title>"` is now mandatory. Skill markdown
  documents the helper snippet that extracts the description from the
  active `.ai-engineering/specs/plan.md` first-incomplete task line
  (`grep -m1 '^- \[ \] ' ... | sed ... | head -c 60`) so the chain
  composes commit subjects deterministically. The legacy `<DESC>`
  placeholder LLM fallback is deprecated.
- `.claude/skills/ai-autopilot/handlers/phase-implement.md` Step 3 —
  wave commits now build a `WAVE_DESC` string from the wave's
  sub-spec titles and feed it through `commit_compose.py --desc`. The
  script automatically injects the `spec-NNN` scope from
  `.ai-engineering/specs/spec.md` frontmatter.
- `.claude/skills/ai-autopilot/handlers/phase-deliver.md` Step 5 +
  `.claude/skills/ai-build/handlers/deliver.md` Step 3.5 — spec-state
  cleanup commits now route through `commit_compose.py --desc` too.
- `.claude/skills/ai-pr/SKILL.md` Step 13 + Step 14 — Step 13 adopts
  the same plan-derived `--desc` discipline before invoking `git
  commit`. Step 14 documents that `pr_body_compose.py` runs WITHOUT
  `--bullets-prompt` whenever the active spec carries `summary:` in
  its frontmatter (the script already prefers `frontmatter.summary`
  over the flag, so no Python change was needed). Legacy specs
  without `summary:` fall back with an advisory warning prompting
  backfill.
- `.ai-engineering/reference/spec-schema.md` — added `summary` to the
  Required Frontmatter table with a 1-2 sentence / ≤300 char
  contract and a "summary field" subsection explaining the soft-then-
  hard rollout (D-139-06). The field is the deterministic feedstock
  for `pr_body_compose.py`'s Summary section.
- `tools/spec_lint/checks/frontmatter.py` — `check_frontmatter` now
  emits `frontmatter_missing_summary` as ADVISORY until
  `SUMMARY_HARD_REQUIRED_AFTER = 2026-06-16` and BLOCKER after, plus
  `frontmatter_summary_too_long` as ADVISORY when the field exceeds
  `SUMMARY_MAX_LEN = 300` chars. `summary` joined the EXTRAS_ALLOWLIST
  so the unknown-key advisory stays silent. Auxiliary fields used by
  the in-flight spec corpus (`mantra`, `trigger_incident`,
  `auto_approved`, `auto_approval_reason`, `date_approved`) joined
  the same allowlist to remove stale advisory noise.
- `.codex/`, `.gemini/`, `.github/`, and project-template mirror
  trees regenerated via `ai-eng dev sync`; `ai-eng dev sync --check`
  reports "Mirrors in sync".

#### Added — compose determinism tests (M8)

- `tests/unit/skills/test_no_residual_llm_compose.py` (new, 3 cases)
  — greps every committed skill markdown file under `.claude/`,
  `.codex/`, `.gemini/`, `.github/`, and the seven project-template
  IDE surfaces for the two forbidden patterns: a `commit_compose.py`
  invocation missing `--desc`, and a `pr_body_compose.py` invocation
  hard-coding `--bullets-prompt`. Skips lines that are explicitly
  documenting the legacy fallback path (e.g., "Never rely on the
  legacy `<DESC>` placeholder"). The third case asserts the active
  `.ai-engineering/specs/spec.md` declares a non-empty `summary:`
  field as defence-in-depth against drift during the soft-rollout
  window.
- `tests/unit/test_spec_lint.py` — `_FRONTMATTER_FULL` and
  `_FRONTMATTER_MINIMAL` fixtures grew a `summary:` line so the
  existing "zero findings" assertions keep passing under the new
  rollout severity rules.
- `tests/integration/test_spec_lint_e2e.py` — tightened the
  substring guard from `frontmatter_missing` to
  `frontmatter_missing_required` so the new advisory does not trip
  the legacy-archive acceptance test during the soft-rollout window.

#### Added — tunables documentation reconciliation (M9)

- `CLAUDE.md` "Runtime Layer Tunables" + template twin
  (`src/ai_engineering/templates/project/CLAUDE.md`) — extended the env
  var table to declare every tunable the framework reads or reserves.
  Sort order: established (5) → M1 trio (3) → M2/M5/M6 pending (8).
  Each pending entry carries the `# pending spec-139 M<n>` marker so
  the reader can tell which vars are wired today versus reserved for
  future milestones.
- New documented env vars (11 total — 3 landed in M1, 8 pending):
  `AIENG_MAX_WAVE_AGENTS` (default auto; floor=2 ceiling=6),
  `AIENG_MAX_QUALITY_AGENTS` (default 3),
  `AIENG_MAX_THREAD_WORKERS` (default 4),
  `AIENG_HOST_PREFLIGHT_DISABLED` (pending spec-139 M2),
  `AIENG_HOST_PREFLIGHT_MIN_FREE_MB` (pending spec-139 M2),
  `AIENG_HOST_PREFLIGHT_MAX_PRESSURE_PCT` (pending spec-139 M2),
  `AIENG_HOOK_CACHE_TTL_SEC` (pending spec-139 M5),
  `AIENG_HOOK_BUDGET_PROFILE` (pending spec-139 M5),
  `AIENG_AUTOFORMAT_DEBOUNCE_SEC` (pending spec-139 M5),
  `AIENG_NDJSON_MAX_LINES` (pending spec-139 M6),
  `AIENG_NDJSON_MAX_BYTES` (pending spec-139 M6).

#### Fixed — AIENG_TOOL_OFFLOAD_BYTES doc/code drift (M9.T2)

- `CLAUDE.md` + template twin — corrected the documented default for
  `AIENG_TOOL_OFFLOAD_BYTES` from `4096` to `16384` to match the actual
  code default at
  `.ai-engineering/scripts/hooks/_lib/runtime_state.py:93`
  (`_env_int("AIENG_TOOL_OFFLOAD_BYTES", 16384, ceiling=8 * 1024 * 1024)`).
  The 16 KiB default was chosen because smaller offload thresholds cost
  more in context-hint bytes than they save (see runtime_state.py
  inline comment).

#### Added — drift gate test (M9.T4)

- `tests/architecture/test_tunables_docs_match_code.py` — 12 cases
  enforcing the CLAUDE.md ↔ code tunables contract. Parses the
  Runtime Layer Tunables fenced block via
  `^(AIENG_[A-Z_]+)\s+#\s*(?:default\s+(\S+)|pending\s+spec-139\s+(M\d+))`
  regex, resolves each documented default against its canonical source
  file (`runtime_state.py`, `runtime-stop.py`, `integrity.py`, or
  `src/ai_engineering/config/concurrency.py`), and asserts byte-equal
  match for every established + M1 tunable. Pending-milestone entries
  are gated on the `# pending spec-139 M<n>` marker and the
  per-milestone bucket invariant (M2 + M5 + M6 each have ≥1 reserved
  var). Drift in either direction (docs without code, code without
  docs) fails CI.

#### Deferred — `AIENG_HOOK_INTEGRITY_MODE` code/docstring reconciliation

- `.ai-engineering/scripts/hooks/_lib/integrity.py:40` has
  `_DEFAULT_MODE = "warn"` while the same file's module docstring
  (line 9), `CLAUDE.md`, and `CONSTITUTION.md` (line 156) all declare
  the default as `enforce`. The M9 drift-gate test whitelists this
  disagreement via `_KNOWN_DOC_CODE_DISAGREEMENTS` (asserts the
  disagreement still exists so the whitelist cannot silently rot once
  reconciled). Flipping the code default to `enforce` is a security
  posture decision that belongs in its own focused spec, not in M9.

### spec-140 — Less-Is-More Quality Engine (partial: W1 + W2 + W2.5-test-split + W3)

Mantra: **Con menos, hacemos más.** Lands Wave 1 hard-delete of dead-test
archaeology, Wave 2 CI matrix collapse + composite-action extraction, the
W2.5 test-split (validator monolith broken along category seams; production
splits W2.5.T1 / W2.5.T2 deferred — see below), and Wave 3 quality-roster
collapse (11 reviewers → 6, 4 verifiers → 2). The pass@k eval harness for
W3 is operator-deferred — the structural collapse ships now, the empirical
gate runs from the gitignored `.ai-engineering/runtime/quality-evals/`
harness in follow-up work (D-140-04).

#### Changed — validator test monolith split (W2.5.T5 / W2.5.T6)

`tests/unit/test_validator.py` (2,554 LOC, 127 test functions) hard-deleted
and replaced by 9 split files under `tests/unit/validator/` plus a shared
`conftest.py`. Every test is preserved — the split collected 127 tests,
matching the pre-split count exactly. Categories are now addressable in
isolation (one file per category check) and the heaviest single file
(`test_mirror_sync_categories.py` at 541 LOC) is < 60% of the pre-split
monolith.

- `tests/unit/validator/conftest.py` (415 LOC) — extracts every shared
  fixture / helper / dynamic-discovery constant (`_PROJECT_ROOT`,
  `_TEMPLATES_CLAUDE_DIR`, `_SKILL_PATHS`, `_AGENT_PATHS`,
  `_make_governance`, `_write_skill`, `_make_instruction_content`,
  `_write_all_instruction_files`, `_write_manifest`,
  `_write_manifest_with_capabilities`, `_source_repo_manifest_text`,
  `_write_source_repo_markers`, `_write_source_repo_control_plane_files`,
  `_write_work_plane`, `_write_task_artifacts`, `_write_active_spec`,
  `_write_readme`, `_setup_full_project`, `_setup_governance_mirror`,
  `_frontmatter_with_provenance`). Two new path helpers
  (`_mirror_pair`, `_copilot_agents_pair`) collapse the 8-segment
  canonical/mirror path repetition that consumed ~130 LOC of the original
  mirror-sync test class.
- `tests/unit/validator/test_parse_counter_and_report.py` (206 LOC) — the
  ReDoS-safe `_parse_counter` plain-string parser tests + `IntegrityReport`
  dataclass tests.
- `tests/unit/validator/test_file_existence_categories.py` (210 LOC) —
  Category 1 (file existence + spec-buffer + source-repo control-plane
  paths).
- `tests/unit/validator/test_mirror_sync_categories.py` (541 LOC) —
  Category 2 (governance / per-IDE skill+agent / generated-provenance /
  public-root-contract / leak-detection). 8 nested test classes preserved
  byte-equivalently; helpers absorbed the canonical-mirror-path duplication.
- `tests/unit/validator/test_counter_accuracy_categories.py` (305 LOC) —
  Category 3 (counter accuracy: listings, pointer-format, manifest match)
  plus Category 4 (cross-reference integrity).
- `tests/unit/validator/test_manifest_coherence_categories.py` (309 LOC) —
  Category 5 (manifest coherence: ownership map, framework-capabilities
  snapshot, control-plane authority contract).
- `tests/unit/validator/test_skill_frontmatter_categories.py` (212 LOC) —
  Category 7 (skill frontmatter happy path + extended edge cases).
- `tests/unit/validator/test_validate_content_integrity.py` (48 LOC) —
  integration tests for the `validate_content_integrity` entry-point.
- `tests/unit/validator/test_shared_utilities.py` (309 LOC) — `FileCache`,
  `_is_source_repo`, `_instruction_files`, `_glob_files`, `_is_excluded`,
  `_extract_section`, `_is_table_separator`, `_parse_skill_names`,
  `_parse_agent_names`, `_extract_subsection`,
  `_parse_skill_names_from_subsection`, `_parse_agent_names_from_subsection`,
  `_extract_listings` — all pure utility tests from `validator._shared`.
- `tests/unit/validator/test_category_public_api.py` (155 LOC) — new
  parity guard. AST-walks every `.py` file under the repo for
  `from ai_engineering.validator.categories[...] import ...` statements,
  records every imported symbol per-module, then asserts each name still
  resolves on its declaring module. Adds two complementary tests:
  the seven category check functions remain callable from
  `ai_engineering.validator.categories`, and `tools/skill_app/lint_service`
  re-exports the canonical public-API symbol set unchanged.

LOC delta (W2.5 only):

| File                                       | Pre   | Post  | Delta |
| ------------------------------------------ | ----- | ----- | ----- |
| `tests/unit/test_validator.py`             | 2,554 | 0     | -2554 |
| `tests/unit/validator/conftest.py`         | 0     | 415   | +415  |
| `tests/unit/validator/test_parse_counter_and_report.py` | 0 | 206 | +206 |
| `tests/unit/validator/test_file_existence_categories.py` | 0 | 210 | +210 |
| `tests/unit/validator/test_mirror_sync_categories.py` | 0 | 541 | +541 |
| `tests/unit/validator/test_counter_accuracy_categories.py` | 0 | 305 | +305 |
| `tests/unit/validator/test_manifest_coherence_categories.py` | 0 | 309 | +309 |
| `tests/unit/validator/test_skill_frontmatter_categories.py` | 0 | 212 | +212 |
| `tests/unit/validator/test_validate_content_integrity.py` | 0 | 48 | +48 |
| `tests/unit/validator/test_shared_utilities.py` | 0 | 309 | +309 |
| `tests/unit/validator/test_category_public_api.py` | 0 | 155 | +155 |
| **Net test delta**                         |       |       | **+156** |
| **Net production delta**                   |       |       | **0**    |

D-140-07 gate (test deletion ≥ 2 × production-LOC overhead): production
overhead is 0 (no production refactor landed); the gate is vacuously
satisfied. The +156 LOC test growth is necessary boilerplate for splitting
a 2,554-LOC monolith into 10 files (per-file module docstrings, imports,
test-class skeletons) plus the 155-LOC parity test that is itself a new
W2.5 deliverable. Excluding the parity test, the test-split overhead is
+1 LOC.

#### Deferred — production splits + 5-LOC stub deletions (W2.5.T1 / T2 / T3 / T4)

- **W2.5.T1** (`manifest_coherence.py` → per-dimension package). Splitting
  the 1,221-LOC file into a `manifest_coherence/{__init__,
  skill_inventory, agent_inventory, surface_axioms, counter_accuracy}.py`
  package would add ~80-150 LOC of import/`__init__.py` re-export
  scaffolding (the 17 top-level functions share private helpers and a
  `_EXPECTED_CONTROL_PLANE` constant table that the split would
  duplicate). D-140-07 demands ≥ 300 LOC of corresponding test deletion
  to offset the production growth at the 2× ratio, which the current
  test surface does not support. Re-attempt only after a clear ROI use
  case justifies the scaffolding overhead.
- **W2.5.T2** (`mirror_sync.py` → per-mirror package). Same reasoning as
  W2.5.T1; the 21 functions in `mirror_sync.py` share the
  `_PUBLIC_AGENT_ROOTS` / `_NON_CLAUDE_LOCAL_REFERENCE_ROOTS` constant
  tables plus `_FRONTMATTER_BLOCK_RE` / `_STRAY_CLAUDE_LOCAL_REF_RE`
  regexes from `_shared.py`. The split cannot land cleanly without a
  `_mirror_helpers.py` companion module, and that companion grows
  production LOC further.
- **W2.5.T3** (delete `cross_references.py` 5-LOC stub). **Blocked.** The
  spec claim "no consumer" was incorrect.
  `tools/skill_app/lint_service.py:31` imports `_check_cross_references`
  via `from ai_engineering.validator.categories import ...`, and
  `tests/integration/test_gap_fillers4.py:388` exercises the same
  re-export. Deleting the stub would break both consumers. The stub must
  stay until the consuming surfaces are intentionally re-routed (out of
  scope for W2.5).
- **W2.5.T4** (absorb remaining 5-LOC stubs). Depends on W2.5.T1 / W2.5.T2;
  deferred with them.

These deferrals are tracked in `.ai-engineering/specs/archive/spec-140-plan.md`
with the same rationale and the W2.5 acceptance-gate amendments. The
W2.5.T6 parity test guarantees that any future split attempt cannot land
without keeping every external importer's symbol resolvable.

#### Changed — quality roster collapse (W3)

- `.claude/agents/reviewer-correctness.md` — absorbed the DRY/reuse/proportionality
  lenses from the former `reviewer-architecture` and the readability/naming
  lenses from the former `reviewer-maintainability`. The agent now carries five
  correctness lenses (intent-implementation alignment, integration boundary
  correctness, basic logic correctness, cross-function correctness, behavioural
  change analysis) PLUS the absorbed architecture / maintainability heuristics,
  documented in a new "Absorbed from reviewer-architecture /
  reviewer-maintainability (spec-140 W3)" section. Self-challenge stays per
  lens; findings emit with `correctness-architecture-N` / `correctness-maintainability-N`
  sub-IDs to preserve attribution after the merge.
- `.claude/agents/verifier-acceptance.md` — new merged specialist. Combines the
  feature lens (spec coverage, acceptance criteria, deletion/creation
  manifests, plan-task completion, handoff readiness) and the governance lens
  (decision compliance, ownership boundaries, gate enforcement, integrity,
  process compliance) into one agent. Findings emit a `lens: feature|governance`
  attribution per finding so downstream readers see both halves preserved.
- `.claude/agents/ai-advise.md` — `drift` mode absorbed the former
  `verifier-architecture` heuristics: alongside the decision walk it now
  surfaces solution-intent alignment, layer violations, structural drift,
  dependency-health concerns (circular imports, deep chains), and boundary
  integrity. All advisory; never emits BLOCK. Blocking architecture concerns
  are still caught by `/ai-review --full` through the absorbed lenses inside
  `reviewer-correctness`.
- `.claude/skills/ai-review/SKILL.md` — Specialist Roster table collapsed to
  6 entries (correctness, security, testing, performance, frontend,
  compatibility). `normal` macro-agent grouping updated to reflect the new
  3-macro structure. `--full` now dispatches 6 individual agents (was 9).
- `.claude/skills/ai-verify/SKILL.md` + `handlers/verify.md` — Specialist
  Roster collapsed to 2 entries (deterministic, acceptance). `normal` and
  `--full` both dispatch the single acceptance specialist post-W3; the
  former 3-way LLM fanout is gone. The `governance` / `feature` mode
  aliases preserved for operator muscle memory; both route to acceptance.
- `.claude/agents/ai-review.md` + `ai-verify.md` — dispatch patterns updated
  to reflect the new rosters (6 reviewer / 2 verifier).

#### Added — roster contract enforcement (W3)

- `tests/architecture/test_reviewer_roster_count.py` — pins reviewer roster
  at 6 (correctness, security, testing, performance, frontend, compatibility)
  and asserts the canonical name set. Drift fails CI.
- `tests/architecture/test_verifier_roster_count.py` — pins verifier roster
  at 2 (deterministic, acceptance) and documents the spec-header math
  discrepancy ("4 → 3" advertised, "4 → 2" actually landed).
- `tests/architecture/test_no_deleted_agents.py` — parameterised guard that
  scans every IDE mirror surface (`.claude`, `.codex`, `.gemini`, `.github`,
  `.opencode`, `.cursor`, `src/.../templates/project`) for any of the 6
  deleted filenames. Aggregates into one summary assertion plus per-file
  parametrised cases for fast triage.

#### Removed — 6 reviewer/verifier agents (W3)

Hard deletes per Constitution §13.3 (no backwards-compat shims). Includes
the legacy `deprecated: true` forwarder stubs that previously routed the
flat `agents/<name>.md` path to `agents/internal/<name>.md` — the
forwarders were also deleted because the canonical target is gone.

- `reviewer-architecture.md` → heuristics absorbed into
  `reviewer-correctness` (A1 necessity + proportionality, A2 DRY + reuse +
  established patterns).
- `reviewer-maintainability.md` → heuristics absorbed into
  `reviewer-correctness` (M1 readability + clarity, M2 naming + intent,
  M3 maintainability anti-pattern watch list).
- `reviewer-backend.md` → deleted outright. Categorical mismatch: this
  repo is a Python CLI with no separate backend tier. The lens does not
  apply.
- `verifier-governance.md` → merged into `verifier-acceptance` (governance
  half).
- `verifier-feature.md` → merged into `verifier-acceptance` (feature half).
- `verifier-architecture.md` → heuristics moved to `/ai-advise drift` mode
  (advisory non-blocking); standalone agent deleted.

Each mirror surface (`.codex`, `.gemini`, `.github`, `.opencode`,
`.cursor`, plus every `src/.../templates/project/` template root) had its
copy of every deleted agent removed via `ai-eng dev sync` + explicit
forwarder-stub deletion.

#### Deferred — pass@k eval harness (W3.T1, W3.T2)

D-140-04 designates `.ai-engineering/runtime/quality-evals/` (gitignored —
operator runtime state, not source of truth) as the eval source. The
harness does not yet exist on disk; the structural collapse above ships
in this commit and the empirical gate (pass@k per reviewer specialty
matches or beats the prior 11-reviewer roster on the recent PR corpus)
becomes an operator follow-up. The acceptance gate in
`.ai-engineering/specs/archive/spec-140-plan.md` was updated to mark W3.T1
and W3.T2 as deferred with explicit rationale.

#### Changed — CI matrix collapse + composite actions (W2)

- `.github/workflows/ci-check.yml` — every PR-blocking matrix collapsed
  to `python-version: ["3.12"]` (D-140-03). The 3-OS sweep
  (`ubuntu-latest` x `macos-latest` x `windows-latest`) survives intact;
  only the Python-version axis collapsed. The full 3 python x 3 OS
  sweep moved to `nightly-matrix.yml` (advisory) so PR job count drops
  from ~57 to ~25 without losing the cross-Python regression signal.
- `.github/workflows/nightly-matrix.yml` — new advisory workflow:
  schedule (`0 6 * * *` daily) + `workflow_dispatch` trigger; runs the
  full 3 python (`3.11` / `3.12` / `3.13`) x 3 OS matrix with
  `continue-on-error: true` per cell so cell failures triage on the
  morning sweep instead of blocking PRs.
- `.github/actions/setup-env/action.yml` — new composite action.
  Wraps `actions/checkout` + `actions/setup-python` + `astral-sh/setup-uv`
  + `uv sync --dev` into one reusable step. Inputs cover the parameters
  every caller relies on: `python-version` (default `3.12`),
  `uv-version` (default `0.9.0`), `fetch-depth`, `enable-cache`, and
  `sync` (skip the default `uv sync --dev` for build-from-wheel flows).
- `.github/actions/run-gates/action.yml` — new composite action. One
  `case` dispatch handles every PR-blocking gate (lint, type-check,
  unit, integration) so the gate commands live in exactly one place.
- 19 inline `astral-sh/setup-uv` blocks across the workflow tree
  collapsed into `uses: ./.github/actions/setup-env` calls
  (`ci-check.yml` x 14, `nightly-matrix.yml`, `test-hooks-matrix.yml`,
  `sbom.yml`, `skill-evals.yml`, `maintenance.yml`, `install-smoke.yml`
  x 2, `install-time-budget.yml`, `worktree-fast-second.yml`). The one
  holdout is `ci-build.yml`, which carries an explicit `ref: main` +
  `token` checkout for the release version commit-back path; the
  composite action cannot represent that contract without growing a
  pile of conditional inputs.

#### Removed — redundant test surface (W2.T6 / D-140-06)

- `tests/integration/cli/test_help_snapshots.py` — 128-LOC parametrised
  snapshot driver. The 66 golden files at
  `tests/golden/cli/help_snapshots/` were a maintenance tax (every Rich
  box-character drift, every Typer minor bump caused a regen). The
  signal is binary: "every top-level command is still wired into the
  Typer app". Replaced with a single command-list assertion at
  `tests/unit/cli/test_command_list.py` that runs in <50ms and survives
  unchanged across help-text edits.
- `tests/golden/cli/help_snapshots/` — 66 golden text files deleted
  with the driver.
- `tests/integration/sync/test_canonical_mirror_parity.py` — mirror
  payload sha256 + idempotency contract. The same invariants are
  covered by `tests/conformance/test_md_mirror.py` (37 tests; faster,
  no subprocess invocations); keeping both was duplicated effort.

#### Added — workflow drift gates (W2.T7)

- `tests/unit/workflows/test_python_matrix_collapsed.py` — parses
  `ci-check.yml` and asserts every matrix declares `["3.12"]` so a
  silent re-expansion (e.g. a copy/paste from an older branch) trips
  CI. Also asserts the 3-OS axis is preserved.
- `tests/unit/workflows/test_nightly_matrix_advisory.py` — parses
  `nightly-matrix.yml` and asserts the full 3 python x 3 OS matrix is
  declared, schedule + dispatch triggers are present, and
  `continue-on-error: true` is set so the workflow stays advisory.
- `tests/unit/workflows/test_composite_actions.py` — asserts both
  composite actions exist, declare the required inputs, and dispatch
  to every supported gate (lint, type-check, unit, integration).
- `tests/unit/cli/test_command_list.py` — single-test replacement for
  the help-snapshot ceremony. Confirms every required top-level
  command (`install`, `doctor`, `verify`, `audit`, `spec`, `decision`,
  `risk`, `config`, `gate`) appears in `ai-eng --help` output.

#### Removed — dead test archaeology

- `tests/unit/test_verify_service.py:610-end` — `TestVerifyCmdJsonFlag`
  class (~97 LOC, 5 tests). The skip reason named git history as the
  correct archaeology location.
- `tests/perf/test_hot_path_budgets.py:191-228` — four xfail stubs
  whose bodies were `pytest.fail("...not wired yet")`. Permanent XFAIL
  with no harness. Real perf gates land with the deterministic compose
  paths in spec-139 M8.
- `tests/integration/test_hooks_git.py:121-184` —
  `test_hook_blocks_commit_with_mock_secret` (~64 LOC). Skip reason
  cited a "fixture redesign tracked separately" with no owner.
- `tests/integration/test_updater.py:150-201` —
  `test_denied_changes_reported` and `test_create_blocked_by_deny_ownership`
  (~52 LOC). Both depended on a feature the updater does not implement
  (emit skip-denied for paths the bundled template tree never visits).

### spec-141 — Semgrep Pack Coverage Restoration (partial: M1 + M2 + M3 + M4)

Mantra: **Real syntax, real budget, real coverage — no invented YAML,
no network on the hot path.** Lands the Article VII parity for
`# nosemgrep:` markers (M3), the documentation rewrite + drift gate
(M4), the in-tree rule ID namespacing + `--baseline-commit` hot-path
injection (M1), and the CI pack coverage expansion with the four
Python-relevant community packs (M2). Only M5 (CI finding triage on
the expanded pack surface) is deferred to a focused follow-up PR
after the first post-merge CI run produces a triage list.

#### BREAKING CHANGES — spec-141 D-141-04 in-tree rule ID rename (M1)

Semgrep in-tree rule IDs renamed to the `aieng.<area>.<name>` namespace
so external repos consuming this `.semgrep.yml` (via the template
mirror) cannot collide with community pack rule IDs. Hard rename
(Constitution §13.3 — no backwards-compat shims); operators must
update any `# nosemgrep: <rule-id>` markers to the new IDs.

- `subprocess-shell-true` → `aieng.injection.subprocess-shell-true`
- `os-system-call` → `aieng.injection.os-system-call`
- `eval-usage` → `aieng.injection.eval-usage`
- `path-traversal-open` → `aieng.fs.path-traversal-open`
- `hardcoded-password` → `aieng.secrets.hardcoded-password`
- `pickle-usage` → `aieng.deserialize.pickle-usage`
- `yaml-unsafe-load` → `aieng.deserialize.yaml-unsafe-load`
- `tempfile-mktemp` → `aieng.fs.tempfile-mktemp`
- `ssrf-request` → `aieng.net.ssrf-request`

Both `.semgrep.yml` (canonical) and
`src/ai_engineering/templates/project/.semgrep.yml` (template) are
byte-identical (sha256 match enforced by
`tests/integration/test_dogfood_parity.py`).

#### Added — `--baseline-commit` on the pre-push hot path (M1)

- `src/ai_engineering/policy/checks/stack_runner.py` —
  `_semgrep_baseline_ref()` resolves `git merge-base HEAD origin/main`
  with a 1-second subprocess timeout (D-141-03 hot-path budget); falls
  back to a non-incremental scan when the merge-base is unresolvable
  (brand-new repo, no remote, git unavailable). `_semgrep_pre_push_cmd()`
  builds the pre-push argv with `--baseline-commit <sha>` injected
  between `--config .semgrep.yml` and `--error .` when a baseline is
  available. Keeps the pre-push gate within the 5-second budget on
  realistic diffs.
- `tests/unit/policy/test_semgrep_baseline_arg.py` — four-case
  contract test covering the happy path (real `tmp_path` git repo
  with seeded `origin/main` ref), argv shape preservation, and the
  fallback path (no remote, no `--baseline-commit` flag).

#### Changed — CI semgrep job now runs four community packs (M2)

- `.github/workflows/ci-check.yml` — `security` job's semgrep step
  now invokes Semgrep with five `--config` flags: `.semgrep.yml`
  (in-tree rules) + `p/python` + `p/owasp-top-ten` + `p/security-audit`
  + `p/bash` (community packs). Repeated `--config` flags are the only
  documented Semgrep multi-pack syntax (D-141-01).
- `.github/workflows/ci-check.yml` — `Install semgrep` step now
  pins the CLI version (`semgrep==1.96.0`); pinning the CLI is the
  deterministic reproducibility anchor because pack aliases roll
  forward from HEAD (D-141-05).
- `.github/workflows/ci-check.yml` — added `Cache semgrep pack
  registry` step keyed by `runner.os` + CLI version so the registry
  fetch happens at most once per pinned CLI release (D-141-02).
- `tests/unit/workflows/test_semgrep_packs.py` — drift gate parses
  `ci-check.yml` and asserts (a) all four community pack `--config`
  flags are present, (b) the in-tree `.semgrep.yml` config stays
  alongside the packs, and (c) the install step pins the CLI version
  via `semgrep==<version>`.

#### Added — `# nosemgrep:` suppression Article VII parity (M3)

- `tools/no_suppression/scanner.py` — detects `# nosemgrep` markers and
  emits `rule_id="nosemgrep_hash"`. Capture group preserves the rule
  target after the colon for granular allowlist matching.
- `.ai-engineering/suppression-allowlist.yml` — header comment now
  enumerates `nosemgrep_hash` alongside the existing pattern enum.
- `tests/unit/no_suppression/test_scanner.py` — bare-marker and
  with-target detection tests. With-target test references the
  canonical post-rename ID `aieng.injection.eval-usage`.

#### Fixed — `semgrep-update-model.md` invented-YAML drift (M4)

- `.ai-engineering/reference/semgrep-update-model.md` and template
  mirror — rewritten to describe documented Semgrep syntax (repeated
  `--config` flags + pinned CLI version). Removed the invented
  `extends:` YAML block and the invalid `p/<name>@1.96.0` pack-version-pin
  claims. Documents the two-tier scan model (pre-push in-tree only
  with `--baseline-commit`; CI full pack coverage) and the new
  `# nosemgrep:` Article VII enforcement.

#### Added — semgrep doc drift gate (M4)

- `tests/unit/contexts/test_semgrep_update_model_drift.py` — forbids
  `extends:` and `@1.` patterns from re-entering the doc on any future
  edit. Fails RED if the rewrite is silently undone.

### spec-137 — Event Relevance Discipline (D-137-01)

Mantra: **lo que escribamos, donde sea, debe ser relevante.** A read-only survey
on 2026-05-15 found 1,230 of 1,335 NDJSON rows in a single working day (92.1%)
came from just two unconditional polling emitters. This release lands the
relevance contract at the writer boundary that ends the heartbeat tail.

#### Behavior change — emit-on-change semantics for two heartbeat sites

- `spec_verified` (cli.spec) — previously fired on every `ai-eng spec verify`
  invocation (~848 rows/day, 63.5% of the audit tail). Now emits **only when
  drift is detected**. Read-time consumers that want "did spec verify run"
  should derive it from git hook traces, not the audit chain.
- `install_simulate_hook` (installer.user_scope_install) — previously fired
  one row per tool per synthetic install run (~382 rows/day, 28.6%). Now
  emits **only on failure or degraded outcome** (success rows drop, failure
  rows always emit per the manifest `failure_emission: always` policy).

Volume target: ≤ 150 lines/day after a typical working-day session (down
from 1,335 -- ~89% reduction).

#### New -- `audit_policy:` block in manifest

`.ai-engineering/manifest.yml` declares a new top-level `audit_policy:`
block with four fields: `kind_allowlist` (the 13 declared kinds, empty
means no restriction), `severity_floor` (per-kind S0..S3 tiers),
`sampling` (e.g. `policy_decision_allow: 0.10`), and `failure_emission:
always` (failure outcomes always emit). The installer template mirror
at `src/ai_engineering/templates/.ai-engineering/manifest.yml` carries
the same default block.

#### New -- relevance gate helper (package + stdlib mirror)

- `src/ai_engineering/state/relevance.py` -- typed gate +
  `AuditPolicy` dataclass + `load_audit_policy_from_manifest()` helper.
- `.ai-engineering/scripts/hooks/_lib/relevance.py` -- stdlib-only
  mirror so hook scripts (running before `uv sync`) can import it.

Three layers asserted at emit time at the writer boundary: kind allow-list,
severity floor, and failure-emission asymmetry.

#### Frozenset drift repair (parity-fix per D-137-01)

The three `ALLOWED_EVENT_KINDS` declaration sites had silently drifted:
the hook-side `_lib/observability.py` mirror was missing `policy_decision`
and `retention_applied` (added in spec-122 / spec-123 respectively). This
release re-aligns the hook-side mirror and the installer-template mirror
with the authoritative frozenset in `tools/skill_domain/event_schema.py`.
A new test `tests/unit/state/test_event_kinds_single_source.py` asserts
the three sites cannot drift again.

#### New tests

- `tests/unit/state/test_event_kinds_single_source.py` -- locks the three
  frozenset sites against drift.
- `tests/unit/state/test_event_relevance_gate.py` -- 13 parametrized cases
  covering all three contract layers.
- `tests/unit/state/test_event_relevance_no_heartbeats.py` -- AST guard
  asserting the two retired heartbeats are emit-on-change only.
- `tests/unit/test_manifest_audit_policy_default.py` -- asserts both
  manifests carry the documented default `audit_policy:` block.

#### Deferred (open scope, not in this PR)

- D-137-07 CI guard for new emit sites without a paired policy entry.
- D-137-08 historical decision backfill into `state.db decisions`.
- D-137-09 per-kind sampling beyond the existing 10% policy-decision
  allow-sampler.
- `schemaVersion` bump and required `severity` field on `FrameworkEvent`
  -- deferred to keep this PR's blast radius bounded; the optional
  severity field is honoured by the gate today and can be made
  required in a follow-up spec without touching emit sites.

### spec-136 — Prune low-value surfaces (`docs/`, `contexts/`, `research/`, `evals/`)

Hard rename per `CONSTITUTION.md §3`. Four top-level knowledge surfaces
(`.ai-engineering/contexts/`, `.ai-engineering/research/`, `docs/`,
`evals/`) collapse into one coherent home (`.ai-engineering/reference/`)
plus runtime state under `.ai-engineering/runtime/{research,presentations,reports}/`
and a committed eval corpus at `.ai-engineering/evals/`. `docs/` is now
reserved for the consumer project that installs ai-engineering; the
framework owns nothing under `docs/` (D-136-02). Operator-as-dogfooder
`docs/*.pen` files survive.

#### BREAKING CHANGES — spec-136 D-136-01

**Moved**:

- `docs/principles.md` → `.ai-engineering/reference/principles.md`
- `docs/mirror-authoring.md` → `.ai-engineering/reference/mirror-authoring.md`
- `docs/surface-axioms.md` → `.ai-engineering/reference/surface-axioms.md`
- `docs/cli-reference.md` → `.ai-engineering/reference/cli-reference.md`
- `docs/model-dispatch-policy.md` → `.ai-engineering/reference/model-dispatch-policy.md`
- `docs/solution-intent.md` → `.ai-engineering/solution-intent.md`
- `docs/conformance-report.md` → `.ai-engineering/runtime/reports/conformance.md`
- `.ai-engineering/contexts/{architecture-patterns,engineering-standards,harness-engineering,harness-adoption,knowledge-placement,gate-policy,risk-acceptance-flow,mcp-binary-policy,semgrep-update-model,spec-schema,plan-schema,operational-principles,gather-activity-data}.md` → `.ai-engineering/reference/`
- `.ai-engineering/contexts/team/` → `.ai-engineering/team/`
- `evals/baseline.json` + `evals/ai-debug.jsonl` + `evals/cli-ux-cross-ide/` → `.ai-engineering/evals/`

**Removed**:

- `docs/{anti-patterns,copilot-subagents,agentsview-source-contract,ci-alpine-smoke,getting-started}.md` — no test or skill consumer.
- `docs/integrations/{antigravity,engram}.md` — Engram install snippet folded into `CLAUDE.md` `Optional: Engram` section (D-136-10); antigravity doc had no consumer.
- `docs/architecture/dir-schemas.md`, `docs/presentations/` (all 8 files including `svg/`) — operator export artefacts misplaced in source tree (D-136-09).
- `.ai-engineering/contexts/{cli-ux,evidence-protocol,mcp-integrations,permissions-migration,python-env-modes,session-governance,sentinel-iocs-update,stack-context}.md` — no current consumer (D-136-13).
- `.ai-engineering/research/{ide-hook-engines,stack-classification,git-branch-cleanup-modes}-2026-05-12.md` — dated spec-133 artefacts; `/ai-research` Tier 0 cache rebuilds at the new gitignored runtime path (D-136-08).
- `evals/` parent dir at repo root.
- `src/ai_engineering/templates/.ai-engineering/contexts/` — template mirror of deleted live source.

**Changed**:

- `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` / `.github/copilot-instructions.md` — pointer rows retarget from `docs/` to `.ai-engineering/reference/`; placement-contract row retargets; Engram install snippet inlined into `Optional: Engram` section. Master payload at `scripts/sync_mirrors/core.py` updated.
- `scripts/run_loop_skill_evals.py` — fail-loud on `--regression` with missing baseline (D-136-07); closes the silent gate-degradation footgun. `--baseline` and `--corpus-root` defaults retarget to `.ai-engineering/evals/`.
- `tools/skill_lint/checks/md_mirror.py` — `_DOCS_TARGETS` retargets to `.ai-engineering/reference/`; CRITICAL-on-missing safety invariant preserved (D-136-14).
- `tools/skill_lint/checks/no_orphan_dirs.py` — `_FIXED_ORPHAN_PATHS` collapses `.ai-engineering/contexts/{frameworks,languages}` to just `.ai-engineering/contexts` (whole tree forbidden).
- `src/ai_engineering/state/control_plane.py`, `src/ai_engineering/config/{mirror_inventory,framework_defaults}.py`, `src/ai_engineering/validator/_shared.py`, `src/ai_engineering/installer/{phases/governance,service}.py`, `src/ai_engineering/updater/service.py`, `src/ai_engineering/doctor/phases/ide_config.py` — ownership / exclusion / migration rules retarget from `contexts/` to `reference/` and `team/`. `_DEPRECATED_GOVERNANCE_PATHS` extends to `("contexts", "research")` so consumer installs prune the legacy trees on next `ai-eng update`.
- `tools/skill_domain/standards.py`, `tools/skill_lint/{checks/effort,cli}.py`, `tools/spec_lint/checks/references.py`, `tools/skill_app/eval_runner.py`, `tools/skill_infra/markdown_reporter.py`, `tools/no_suppression/scanner.py` — path strings retarget to new homes.
- `.github/workflows/skill-evals.yml` — retarget corpus paths to `.ai-engineering/evals/`.
- `README.md`, `CONTRIBUTING.md` — drop stale links to deleted docs; retarget cli-reference link; project-structure prose updated.
- 76 `§10.x` citations across skill / agent files — anchor strings unchanged; pointer rows in mirrors retarget.

Migration: consumers run `ai-eng update` after this lands; the updater's
deprecation logic extends to cover the deleted paths. Consumers with
operator-owned `.ai-engineering/contexts/team/` content must move it to
`.ai-engineering/team/` before update (the updater deletes deprecated
paths; it does not migrate contents).

### spec-134 Wave 4 — Hard-rename wave for ambiguous skill / agent names

Per D-134-06, executes one atomic rename wave across 8 ambiguous
skill slugs, 2 first-class agent files (skill ↔ agent cohesion
preservation), and 3 specialist agents (verifier / review family
prefix alignment). No backwards-compatibility shims are provided
(Constitution §13.3). Operators must update muscle memory and
out-of-repo docs in lock step. The Constitution mandates hard
renames over compatibility files; this wave honors that.

#### BREAKING CHANGES — spec-134 D-134-06 rename wave

Skills (8):

- `/ai-gtm` → `/ai-marketing` — Domain-explicit; eliminates the opaque "go-to-market" acronym that newcomers cannot parse.
- `/ai-eval` → `/ai-reliability-eval` — Disambiguates "AI evaluation" (meta) from "feature reliability eval"; scores production behavior.
- `/ai-guide` → `/ai-onboard` — Audience-explicit (onboarding humans); separates from `/ai-explore` (codebase research).
- `/ai-observe` → `/ai-session-watch` — Makes the passive-watch role explicit; clears the `/ai-learn` / `/ai-note` overlap.
- `/ai-create` → `/ai-scaffold` — Aligns with industry term "scaffolding"; clarifies the verb generates structured framework artifacts.
- `/ai-cleanup` → `/ai-repo-tidy` — Disambiguates from "code cleanup"; the skill is about repo lifecycle hygiene (`_history.md` rotation, branch tidy). Also avoids the residual twin-collision with the `ai-eng cleanup` CLI (Surface Axiom A2).
- `/ai-write` → `/ai-prose` — Domain-explicit; resolves overlap with `/ai-docs` and `/ai-marketing`.
- `/ai-prompt` → `/ai-prompt-tune` — Verb-leaning (optimize, not author); resolves the "write or tune?" ambiguity.

Agents (2 first-class, paired with their renamed skill counterparts):

- `ai-guard` → `ai-advise` — Resolves the name-behavior mismatch ("guard" implies blocking; the agent is "Always advisory, NEVER blocks").
- `ai-guide` → `ai-onboard` — Skill ↔ agent cohesion: the renamed `/ai-onboard` skill now dispatches the renamed `ai-onboard` agent.

Sub-agents (3, family-prefix consistency):

- `verify-deterministic` → `verifier-deterministic` — Restores the `verifier-*` family prefix shared with siblings `verifier-architecture`, `verifier-feature`, `verifier-governance`.
- `reviewer-context` → `review-context` — Lifecycle helper (pre-processor that loads context for specialists), not a specialist itself. The `review-` prefix marks it as a pipeline stage, not a domain reviewer.
- `reviewer-validator` → `review-validator` — Lifecycle helper (post-processor adversary that disproves findings). Same story as `review-context`.

Surface impact:

- 8 canonical skill directories under `.claude/skills/` renamed via `git mv`; SKILL.md frontmatter `name:` fields and inline self-references updated.
- 5 canonical agent files under `.claude/agents/` renamed; frontmatter `name:` updated.
- `DEFAULT_SKILLS_REGISTRY` and `DEFAULT_AGENTS_NAMES` in `framework_defaults.py` updated; `_AGENT_ALIASES`, `_AGENT_TOPOLOGY`, `_AGENT_MUTATIONS`, `_AGENT_WRITE_SCOPES` in `state/capabilities.py` updated.
- All 8 + 5 renamed seed copies under `src/ai_engineering/templates/project/{.agent,.claude,.codex,.cursor,.gemini,.github,.opencode}/` updated to match.
- IDE mirror trees at `.codex/`, `.gemini/`, `.github/skills/` and `.github/agents/` renamed alongside; the bundled regenerator (`scripts/sync_mirrors/core.py`) re-runs at wave-end to ensure mirror parity.
- Internal callers (`/ai-build`, `/ai-pr`, `/ai-autopilot`, `/ai-verify`, `_shared/{consolidate-spec,execution-kernel}.md`, plus every cross-referencing SKILL.md body) updated to dispatch the new names.
- New `tests/architecture/test_naming_clarity.py` enforces (a) no deprecated slug surfaces survive on disk, (b) every specialist agent uses one of the canonical family prefixes, and (c) every renamed target exists at its new path. Drift fails CI.
- Surface-Parity `_KNOWN_OVERLAPS` drops the legacy `"cleanup"` row (the chat surface no longer collides with `ai-eng cleanup` CLI under the new name).

Migration note: there are no aliases. References to old names will
fail to dispatch. Update any out-of-repo automation, docs, or
shell scripts in the same release window.

### spec-134 Wave 2 — Orphan agents surfaced as slash-skills + cohesion test

Two first-class agents (`ai-guard`, `ai-simplify`) had no discoverable
`/ai-<name>` counterpart in the slash menu, making them "ghost
surfaces": registered orchestrators that operators could not invoke
through the primary IDE discovery channel. Wave 2 closes the gap and
gates against future drift.

Added:
- `/ai-advise` skill — advisory governance review wrapping the
  `ai-guard` agent. Three modes (`advise`, `gate`, `drift`); severity
  `info | warn | concern`; never blocks; never modifies code. Distinct
  from `/ai-verify` (evidence-backed BLOCK lane) and `/ai-review`
  (narrative human-judgement review). Body 118 lines, cites §10.4
  DRY + §10.6 SDD anchors.
- `/ai-simplify` skill — on-demand simplification wrapping the
  `ai-simplify` agent. Scoped to operator-chosen paths or current
  diff; no PR; no auto-commit; behaviour preserved; tests pass after
  every change. Distinct from the scheduled `/ai-simplify-sweep`
  (weekly cron, repo-wide, draft-PR side effect). Body 116 lines,
  cites §10.1 KISS + §10.7 Clean Code anchors. Resolves the long-
  standing dangling reference inside `/ai-simplify-sweep`.
- `tests/architecture/test_skill_agent_cohesion.py` — three
  assertions enforce D-134-07: every entry in `DEFAULT_AGENTS_NAMES`
  resolves to an existing `.claude/skills/<resolved>/SKILL.md` (via
  `_COHESION_MAPPING` for renames; identity otherwise); no stale
  mapping entries; resolved skill directory also exists under the
  template mirror (`src/.../templates/project/.claude/skills/`) so
  `ai-eng install` ships the skills to downstream projects. Reads
  the filesystem directly — no manifest dependency, no decisions-
  table dependency (satisfies D-134-10).
- `DEFAULT_SKILLS_REGISTRY` extended with `ai-advise` (workflow /
  governance + advisory + proactive) and `ai-simplify` (workflow /
  refactor + complexity + simplification). Registry count
  48 → 51 (Wave 1) → 53 (Wave 2). `DEFAULT_AGENTS_NAMES` untouched
  (sub-006 owns the agent-side rename).

The cohesion mapping `{"guard": "ai-advise"}` is the rename bridge
for sub-006: until the agent file `.claude/agents/ai-guard.md`
hard-renames to `ai-advise.md` and `DEFAULT_AGENTS_NAMES` rotates
`guard` → `advise`, the bridge lets the cohesion test pass in either
order (sub-002-first OR sub-006-first).

Wave-end housekeeping deferred to the orchestrator: mirror sync to
`.codex/`, `.gemini/`, `.opencode/`, `.cursor/`, `.github/skills/`
runs after both new skills land on disk.

### spec-133 D-133-17 amendment — Wizard prompts VCS provider when autodetect ambiguous

D-133-17 collapsed the install wizard to a single Surface question and
made VCS detection silent (default `github`). On greenfield repos with
no `origin` remote configured, this denied operators the ability to
choose Azure DevOps interactively — the only escape was the
`--vcs azdo` CLI flag, which is undiscoverable without reading source.

Fix preserves D-133-17 KISS for the common case (autodetect succeeds →
no prompt) and adds a secondary VCS prompt only when ambiguous:

- `installer/autodetect.py`: `detect_vcs()` now returns `""` (empty
  string) when no `origin` remote is configured, distinguishing
  "no remote" from "remote → github default". `vcs/factory.py`
  unchanged (other callers still get the github fallback).
- `installer/wizard.py`: new `_ask_vcs()` fires only when
  `detected.vcs == ""` and no `--vcs` flag was passed; Ctrl+C →
  safe `github` default.
- Tests: 5 new wizard cases (prompt fires/skips, flag override,
  Ctrl+C fallback, empty-remote signal); 5 autodetect cases adapted
  to mock the new `run_git` probe.

Pre-existing spec-133 drift cleaned up in the same commit (uncovered
while running the wizard test suite):

- `tests/unit/test_installer.py`: 9 keyword updates
  (`providers=`→`surfaces=`, `ides=` removed,
  `_PROVIDER_TREE_MAPS`→`_SURFACE_TREE_MAPS`).
- `tests/unit/installer/test_phases.py`: `_ctx` kwarg
  `providers`→`surfaces`; reconfigure manifest fixture migrated to
  `surfaces.enabled` schema.
- `tests/golden/cli/help_snapshots/`: 7 snapshots regenerated
  (drift from D-133-18 `--surface/-S` flag rename).

312/312 tests pass across the touched suites.

### spec-128 Wave 4 — Native skills paths for Cursor + OpenCode, fix skill_scripts_lib install

**Critical bug fix.** Installed projects raised `ModuleNotFoundError: No
module named 'skill_scripts_lib'` on `session_bootstrap.py`,
`commit_compose.py`, `pr_body_compose.py`, and `standup_render.py`. Root
cause: spec-129 D-129-08 introduced the lib at
`.ai-engineering/scripts/skills/skill_scripts_lib/` but the installer's
`ScriptsPhase` copied only 9 root scripts — never the `skills/` subtree.
spec-133 commit `02f28c1d` purged the legacy template tree without
restoring the lib path. Fix: ship the full `skills/` subtree from
templates, extend `ScriptsPhase` to recurse via `copy_tree_for_mode`
(filters `__pycache__`), add doctor check `skill-scripts-lib`, and gate
future drift with `tests/architecture/test_template_tree_completeness.py`
(AST walk asserting every `from skill_scripts_lib.X import …` resolves).

**Surface migration.** Cursor 2.4+ and OpenCode both ship native
`<root>/skills/<name>/SKILL.md` paths for on-demand lazy-loaded skills,
distinct from `.cursor/rules/` (always-included) and
`.opencode/commands/` (saved TUI prompts). spec-133 D-133-06 and D-133-07
classified the 48 framework skills under the wrong mechanism. This wave
supersedes both decisions:

- `scripts/sync_mirrors/cursor_target.py` emits `.cursor/skills/ai-<name>/SKILL.md`.
- `scripts/sync_mirrors/opencode_target.py` emits `.opencode/skills/ai-<name>/SKILL.md`.
- Template tree: 48 legacy `.cursor/rules/ai-*.mdc` + 48 `.opencode/commands/ai-*.md` deleted; 48 + 48 folder-per-skill `SKILL.md` created.
- `manifest.yml` activates `opencode` + `cursor` in `surfaces.enabled`.
- `CANONICAL.md §14` (+ 4 mirrors via sha256 lockstep) documents the new contract; 2 NOT-USED rows annotate `.cursor/rules/` + `.opencode/commands/` as operator-owned, framework-untouched paths.
- `CONSTITUTION.md` Stakeholders replaces "Antigravity" with "OpenCode, Cursor" (Antigravity is mirror-only with no hook engine; not a deployment target today).
- `scripts/sync_mirrors/core.py` adds Surface 9: lockstep sync of `.ai-engineering/scripts/skills/` → `src/ai_engineering/templates/.ai-engineering/scripts/skills/` with `--check` drift detection.

Hard breaking change (Hard Rules §13.3 — no shims): operators with prior
installs must run `ai-eng install --reconfigure` to drop legacy
`.cursor/rules/` + `.opencode/commands/` framework files and re-fetch
the new skills layout.

### spec-133 — Surface Primitive Re-architecture (CLI UX + Cross-IDE)

Joins the PR #509 aggregate. 14 autopilot sub-specs delivered across 5
waves. Core unification: collapse "AI Provider" + "IDE Integration" into
a single first-class domain primitive — the **Surface** — and rebuild
the installer, manifest, wizard, and mirror-sync around that primitive.
Hexagonal layering becomes enforceable. The wizard collapses to one
question. OpenCode and Cursor become full surfaces with hook adapters.
Antigravity stays mirror-only (Google upstream confirmed workaround-only).
9 root scripts deploy to consumer template tree. Stack content
consolidates: `.ai-engineering/overrides/<stack>/` is the **single
canonical home** for stack-specific guidance.

**Breaking changes** (no compat shims; hard rename / hard delete per
CONSTITUTION §13.3):

1. **`ai-eng guide` DELETED** (D-133-02). `/ai-guide` skill is the
   canonical onboarding surface. CLI handler `cli_commands/guide.py`
   removed. No alias.
2. **`ai-eng maintenance branch-cleanup` → `ai-eng cleanup`** (D-133-03).
   Top-level command with 4 subcommands (`branches`, `runtime`,
   `specs`, `all`). 7-mode taxonomy on `branches`: `--pruned` /
   `--merged` / `--squashed` / `--stale` / `--untracked` / `--reset` /
   `--all`. Universal flags `--dry-run` / `--json` / `--strict` /
   `--tracked` / `--force`. Refuses detached HEAD. Never deletes current
   branch. Squash-merge detection via git-trim's merge-base +
   commit-tree algorithm.
3. **`--ide` / `--provider` flags REMOVED**, replaced by `--surface/-S`
   (D-133-18). Closed enum: `{claude-code, codex, gemini-cli,
   github-copilot, opencode, cursor, antigravity}`.
4. **Manifest schema**: `surfaces.enabled: list[str]` introduced as
   the canonical key (D-133-16). Legacy `ai_providers.enabled` +
   `providers.ides` retained for in-flight compat on PR #509;
   loader mirrors bidirectionally. Hard removal of legacy fields is a
   follow-up release.
5. **4 orphan directories deleted** (D-133-13, CONSTITUTION §13.3 hard
   delete): `.ai-engineering/adapters/`,
   `.ai-engineering/contexts/frameworks/` (15 files),
   `.ai-engineering/contexts/languages/` (14 files),
   `.claude/skills/ai-debug/handlers/` (8 stack-routed),
   `.claude/skills/ai-review/handlers/` (10 stack-routed).
6. **Stack content consolidation** (D-133-10): stack-specific debug +
   review guidance migrates from skill `handlers/` to
   `.ai-engineering/overrides/<stack>/debug.md` and
   `overrides/<stack>/review.md`. SKILL.md procedures are now
   stack-agnostic.
7. **3 new Surfaces** (D-133-06): `opencode` (full surface, plugin
   engine), `cursor` (full surface, stdio JSON), `antigravity`
   (mirror-only, no hooks upstream).

**Additions**:

- `src/ai_engineering/domain/surface.py` — `Surface` frozen dataclass +
  `SURFACE_REGISTRY` (7 surfaces).
- `src/ai_engineering/installer/phases/scripts.py` — `ScriptsPhase`
  deploys 9 root scripts to consumer tree on every install.
- `.ai-engineering/scripts/hooks/opencode-hook-bridge.ts` — TS plugin
  adapter mapping OpenCode events to canonical hook contract.
- `.ai-engineering/scripts/hooks/cursor-hook-bridge.py` — stdio JSON
  adapter mapping Cursor camelCase events to canonical PascalCase.
- `scripts/sync_mirrors/{opencode,cursor,antigravity}_target.py` —
  per-surface tree generators.
- `.claude/skills/ai-explore/SKILL.md` — thin wrapper dispatcher per
  D-133-09 (47 -> 48 skills).
- `src/ai_engineering/cli_ui_skill_ref.py` — `skill_ref()` /
  `skill_ref_tight()` helpers prevent naked `/ai-<name>` literals in
  CLI output (D-133-22).
- `cli_factory.py` stack-drift middleware (D-133-23) emits structured
  exit-78 envelope per D-133-24; `AIENG_STACK_DRIFT_STRICT=1` blocks
  commit/pr/gate on drift.
- `doctor/phases/scripts.py` doctor parity with installer phases.
- `.ai-engineering/overrides/` 5 new stacks (`java`, `php`, `ruby`,
  `flutter`, `react-native`) + cross-cut `_shared/sql.md` per D-133-12.
- `CLAUDE.md` §16 Surface Axiom (A1) + No-Twin Axiom (A2) per
  D-133-04. Mirrored to AGENTS.md / GEMINI.md / Copilot.
- `evals/cli-ux-cross-ide/test_drift_recovery_flow.md` — 6-stack AI
  cognitive recovery eval matrix (D-133-11).
- `applies_to_surfaces` skill frontmatter (D-133-19);
  `ai-analyze-permissions` declares `[claude-code]`.

**Tests added**: 90+ new tests (Surface domain 10, ScriptsPhase 8,
Skill ref 8, autodetect spec-133 9, Surface parity 4, manifest schema
6, wizard collapse 6, OpenCode bridge 4, Cursor bridge 5,
sync_mirror targets 6, stack-drift middleware 6, doctor stack-drift 4,
cleanup CLI 8, stack inventory 17).


### spec-132 — CLI UX & Architecture Overhaul

Delivers the full `cli-ux-overhaul` brief (M0–M6) in a single PR #509
aggregate alongside spec-128 / spec-129 / spec-131. Six autopilot
sub-specs (sub-001..006) executed in 5 waves; final-quality-loop closure
follows the spec-131 D-131-05 single-round fail-loud policy. The North
Star: a first-time engineer runs `ai-eng install` on an empty repo and
never feels confused, never sees noise, never hits a hidden failure
mode (D-132-01, D-132-19, D-132-20).

**Breaking changes** (no compat shims; hard rename / hard delete / hard
migration per CANONICAL.md §13 rule 3):

1. **CLI verb renames — hard, no aliases** (sub-004, D-132-02, D-132-03,
   D-132-04, D-132-05, D-132-10, D-132-15):
   - `ai-eng validate` → `ai-eng check`.
   - `ai-eng work-item sync` → `ai-eng issue sync`. Module rename:
     `src/ai_engineering/work_items/` → `src/ai_engineering/issues/`.
   - `ai-eng stack {add,remove,list}`, `ai-eng ide {add,remove,list}`,
     `ai-eng provider {add,remove,list}`,
     `ai-eng vcs {status,set-primary}` collapsed into
     `ai-eng config` (interactive reconfigure) +
     `ai-eng config <resource> {list,status}`.
   - `ai-eng workflow` deleted entirely; old verbs map to `/ai-commit`,
     `ai-eng pr`, `ai-eng release --pr`.
   - `ai-eng sync` removed; mirror sync moves under `ai-eng dev sync`
     (hidden in consumer projects via the `[tool.aiengineering.source_repo]`
     marker per D-132-10).
   - Final command tree: 20 top-level verbs (`install`, `update`,
     `status`, `doctor`, `check`, `verify`, `audit`, `config`, `gate`,
     `spec`, `issue`, `release`, `setup`, `decision`, `risk`, `guide`,
     `version`, `dev`, `commit`, `pr`). `commit` and `pr` carry the
     "WIP / standalone — not part of the canonical chain" label per
     D-132-23.
   - Old-verb invocation prints `removed; use <new>` and exits 2.
2. **Engram removed from installer** (sub-001, D-132-06):
   `installer/engram.py` deleted, `--engram` / `--no-engram` flags and
   the install-time prompt are gone. Engram is now an opt-in
   third-party integration documented at `docs/integrations/engram.md`.
   Anyone relying on `ai-eng install --engram` automation must switch
   to the manual install commands documented there.
3. **`CONSTITUTION.md` single-location ship** (sub-001, D-132-14): the
   legacy `.ai-engineering/CONSTITUTION.md` stub and the matching
   template stub were both deleted. A fresh install now produces
   exactly one `CONSTITUTION.md` (at the consumer root); downstream
   tooling that read from `.ai-engineering/CONSTITUTION.md` must
   repoint to the root.
4. **`.ai-engineering/contexts/team/` removed** (sub-001, D-132-17):
   the template stub directory is gone. `ai-eng update` prunes the
   directory on existing consumer installs as part of the legacy-dir
   migration sweep.
5. **`pr_lifecycle` event renames** (sub-004, D-132-21): writers emit
   `pr.commit_start` / `check.completed` (was `workflow.commit_start`
   / `validate.completed`). `audit index` carries a one-shot back-compat
   reader so historical events remain queryable.

**Fixes & polish** (not breaking; observable behaviour change only):

- **State warner deduped** (sub-001, D-132-07):
  `_warn_on_deprecated_fallbacks` warns at most once per stale JSON
  file per process lifetime via a module-level `_WARNED_FALLBACKS`
  set. Eliminates ~34 duplicate warning lines per fresh install. Test
  helper `_reset_fallback_warnings()` keeps unit tests deterministic.
- **Installer state phase UPSERTs to state.db** (sub-001, D-132-08,
  D-132-18): `ownership_map` + `decisions` rows now land directly in
  `state.db` instead of legacy JSON sidecars (`ownership-map.json`,
  `decision-store.json`). Pre-existing sidecars are removed during the
  same phase. `ai-eng update` extends the cleanup to previously-installed
  consumers.
- **Validator false-positives fixed** (sub-001, D-132-09): source-repo
  `src/ai_engineering/...` references inside `.claude/skills/*.md`
  descriptors are now skipped (they are LLM-only implementation notes,
  never shipped to consumers); missing `_history.md` downgrades from
  FAIL to WARN when both `spec.md` and `plan.md` exist
  (`/ai-cleanup` owns the file lifecycle per spec-131 D-131-04). New
  template `src/ai_engineering/templates/.ai-engineering/references/IOCS_ATTRIBUTION.md`
  documents the upstream provenance of the IOC catalogue used by the
  sentinel guard.
- **Renderer module — single source of truth for CLI output** (sub-002,
  D-132-12): new `src/ai_engineering/core/output/renderer.py` wraps the
  legacy `cli_envelope` / `cli_ui` / `cli_progress` / `cli_output`
  modules behind one `Renderer(command, *, json, quiet)` API. Closed
  `Verb` taxonomy (`Installing`, `Updating`, `Removing`, `Moving`,
  `Creating`, `Verifying`, `Skipping`, `Restoring`) enforces narrative
  consistency at type-check time. Modes: `human` (default Rich), `json`
  (envelope accumulation), `quiet` (errors only). Renderer migration of
  the remaining `cli_commands/` direct imports is deferred to a
  follow-up spec; conformance baseline pins the current 59 violators in
  `tests/conformance/test_renderer_imports.py`.
- **Universal `@no_args_help` decorator** (sub-003, D-132-11): new
  `src/ai_engineering/core/cli/decorators.py` exports
  `HelpOnNoArgsCommand` + `apply_no_args_help` +
  `no_args_help`. `cli_factory.create_app()` calls `apply_no_args_help`
  at the tail of registration so every public Typer command with a
  required Argument now prints help and exits 0 instead of raising
  `MissingParameter`. 22 public command paths covered by parametrised
  tests; 67 golden help snapshots under
  `tests/golden/cli/help_snapshots/`. Hidden internal groups (`dev`)
  opt out by registration.
- **Hexagonal direction enforced** (sub-005, D-132-13): new
  `[tool.importlinter]` `forbidden` contract in `pyproject.toml` plus
  `tests/architecture/test_hexagonal.py` runs `lint-imports` and asserts
  every contract is KEPT. The contract pins "core must not import from
  adapters" with 4 baseline-pinned legacy edges (`ignore_imports`)
  that the follow-up relocation spec will untangle. Layer map +
  direction rule documented at `docs/architecture/dir-schemas.md`.
  `import-linter>=2.0,<3.0` added to dev dependencies (`grimp 3.14`,
  `import-linter 2.11`). Physical mass relocation of the flat tree
  into `src/ai_engineering/{core,adapters}/<surface>/` is deferred to
  a follow-up spec — single-PR scope cap per D-132-01.
- **Dogfood parity** (sub-006, D-132-16): source-repo `.gitleaks.toml`
  and `.semgrep.yml` synced UP to match the stricter
  `src/ai_engineering/templates/project/` versions on commit.
  New `tests/integration/test_dogfood_parity.py` enforces sha256
  equivalence unless both files carry a matching
  `# AIENG_DOGFOOD_DRIFT_OK: <reason>` marker. The source repo can no
  longer pass a stricter ruleset than a consumer install would face.
- **Directory schema documentation + golden snapshot** (sub-006,
  D-132-24): `docs/architecture/dir-schemas.md` extended with the
  canonical shapes of `.ai-engineering/specs/` (spec lifecycle
  workspace) and `.ai-engineering/state/` (state.db + append-only audit
  streams + locks). Golden-file snapshot
  `tests/integration/installer/test_install_dir_schema.py` pins the
  fresh-install layout; regeneration documented inline via
  `AIENG_UPDATE_INSTALL_SCHEMA=1`.
- **CHANGELOG + PR title metadata** (sub-006, D-132-25): this
  consolidated entry replaces per-sub fragments; PR #509 title updated
  via `gh pr edit` to include spec-132 alongside spec-128 / spec-129 /
  spec-131.
- **Autopilot plan-task sync gate** (process fix landed on this
  branch): `.ai-engineering/scripts/plan_tasks.py` (stdlib-only) +
  `ai-autopilot/handlers/phase-deep-plan.md` +
  `ai-autopilot/handlers/phase-implement.md` reconcile sub-plan
  frontmatter (`total` / `completed`) with the canonical
  `- [ ] T-N.K` checkbox count automatically before each wave commit.
  24 unit tests.

**Tests added** (representative; the new test files are listed under
each subsection above): unit Renderer (18), `no_args_help` (22 public
paths), help snapshots (67 golden), dogfood parity (2), install-schema
golden (1), state warner dedup (6), help-on-empty parametrised (22+),
hexagonal contract (1 lint-imports run + 4 baseline ignores). All
green across the full `uv run pytest tests/` slice.

**Anonymous content** (D-131-15 carry-over): no PII, no machine paths,
no operator names anywhere in the shipped surface.

**Deferred to follow-up**:

- Physical mass relocation of `src/ai_engineering/{governance,state,policy,validator}/`
  into `core/` and `src/ai_engineering/{cli_commands,installer,vcs,ide,updater,issues}/`
  into `adapters/` (sub-005 direction-contract only).
- Renderer migration of the remaining 59 `cli_commands/` direct imports
  to the new `core/output/renderer.py` API (sub-002 module-only;
  conformance baseline pins the count).
- Classification of transitional `src/ai_engineering/cli*.py` top-level
  modules into the hex layer map.

### spec-131 — DX Excellence Refactor

Trimmed scope of the original `dx-excellence-refactor-brief.md` to the
non-duplicated residual: M2 markdown canon reset, M4-residual single
quality loop, M5 model-dispatch economics, M6-residual hooks robustness,
M7 docs evangelism + cross-IDE audit extension, M1-residual naming lint,
and a S7 spec-lint addition. Lands on the same branch and the same PR
as spec-128 / spec-129 (PR #509) — no new branch, no new PR.

**Breaking changes** (no compat shims; hard rename / hard delete / hard
migration per Non-Goal #10):

1. **Markdown canon reset (D-131-03)** — `<repo>/AGENTS.md`,
   `<repo>/CLAUDE.md`, `<repo>/GEMINI.md`, and
   `<repo>/.github/copilot-instructions.md` are now byte-equivalent
   mirrors of `templates/project/CANONICAL.md`. `<repo>/.gemini/GEMINI.md`
   deleted (dead path — Gemini CLI does not read in-repo `.gemini/`).
   `<repo>/.codex/AGENTS.md` never created (Codex reads root AGENTS.md
   natively). User-extensions that imported `@AGENTS.md` from CLAUDE.md
   must inline the canonical payload — the import bridge no longer
   exists.

2. **CONSTITUTION rescope (D-131-04)** — `CONSTITUTION.md` is now
   project-identity only (Mission, Stakeholders, Vocabulary,
   Prohibitions, Compliance gates, Anti-goals, Boundaries, Escalation,
   Language, Lifecycle phase). All AI-behaviour articles previously in
   CONSTITUTION.md migrated to `templates/project/CANONICAL.md`
   (§10.x principle anchors). Skills referencing "Article X" of
   CONSTITUTION.md must re-anchor to CANONICAL.md §10.x.
   `/ai-constitution` skill refactored from generator-of-articles to
   project-identity interview.

3. **Single quality loop, single round, fail-loud (D-131-05)** —
   `/ai-build` and `/ai-autopilot` no longer run per-task verify+review
   inside the task loop. A single final-quality-loop phase runs verify
   plus review on the full changeset once. Blockers STOP and escalate
   to the operator. Re-dispatch with `/ai-build --rerun-quality-loop`
   to resume after fixing the blocker.

4. **Canonical chain trim (D-131-07)** — chain in AGENTS / CLAUDE /
   GEMINI / copilot-instructions reads
   `/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`. `/ai-commit` no
   longer appears in the chain (runs internally inside `/ai-pr`).
   `/ai-commit` preserved verbatim as a standalone off-chain skill for
   WIP-only invocations.

5. **Mandatory `effort:` and `model_tier:` SKILL.md frontmatter
   (D-131-08)** — every skill declares cheap / mid / high effort and
   haiku / sonnet / opus model tier. `tools/skill_lint/checks/effort.py`
   enforces. The audit chain (`framework-events.ndjson`) records
   `model_tier` and `effort` per dispatch.

6. **Trusted-script lane (D-131-12)** — scripts hash-pinned in
   `.ai-engineering/state/hooks-manifest.json` bypass RTK rewriting and
   IOC re-evaluation. The trusted-script lane mechanism shipped this
   wave; `session_bootstrap.py` enrolment is deferred to a follow-up
   sweep (closure note: the manifest currently registers only
   `no-verify-guard.py`; the `trustedArgvs` array is empty pending the
   bootstrap entry being added together with its sha256). New scripts
   requiring the lane register via
   `.ai-engineering/scripts/regenerate-hooks-manifest.py --add-trusted
   <path>`.

7. **Sub-agent policy lane (D-131-11)** — read-only commands (`rg`,
   `grep`, `find`, `ls` without redirect) clear an explicit allow-list
   before IOC pattern matching. `cat` was deliberately REMOVED from
   the allow-list in the spec-131 closure sweep (review-H1): `cat` is
   the highest-value exfiltration primitive and the lane was scoped
   to read-only PROBES, not arbitrary file content extraction. IOC
   retains veto on every residual command.

   **B5 risk-accept note (option a, D-131-11 deviation).** The
   `.claude/settings.json` deny rules retain the narrower 4-verb glob
   set (`Bash(git commit*--no-verify*)`,
   `Bash(git push*--no-verify*)`, `Bash(git merge*--no-verify*)`,
   `Bash(git rebase*--no-verify*)`) rather than introducing a shlex
   matcher inside `settings.json`. The runtime
   `no-verify-guard.py` PreToolUse hook performs the canonical
   shlex-tokenisation + env-var-prefix stripping + verb gating; the
   narrower globs are belt-and-suspenders second-line defence. Net
   behaviour is functionally equivalent to a literal in-settings
   shlex matcher: any `git <verb> ... --no-verify` invocation is
   denied at hook-time before the deny rules even apply. This
   deviation from spec text §M6 is accepted for spec-131 ship; the
   shlex matcher in `settings.json` itself remains an open follow-up
   if Claude Code ever surfaces a richer matcher grammar.

8. **Antigravity audit row (D-131-18 closes G6)** — `/ai-ide-audit`
   IDE matrix gains an Antigravity column. Advisory only in this
   release; hard-gate lands once Antigravity exposes a deterministic
   version probe (R-131-08).

9. **Docs front-door rewrite (M7)** — `README.md` rewritten to install
   + value-prop + links (≤120 lines; skill / agent / chain tables
   deleted). `CONTRIBUTING.md` project-structure tree collapsed to a
   paragraph. `docs/getting-started.md` (NEW, 5-frame, ≤80 lines)
   replaces the deleted root-level `GETTING_STARTED.md`.

**Tests added**: `tests/docs/test_links.py` (≥10 cases covering
file-link resolution, anchor validation, anonymous-content scan, and
length caps for the front-door surface); `tests/conformance/test_md_mirror.py`
and `tests/conformance/test_principles.py` (shipped by sub-001).

**Anonymous content** (D-131-15): no PII, no machine paths, no
operator names anywhere in the shipped surface.

### spec-131 S1 — Markdown Canon Reset

D-131-03 / D-131-04 / D-131-14: collapsed the multi-IDE instruction
surface to a single canonical payload + byte-equivalent mirrors.
**Breaking** — no backwards-compat shims (D-131-15 anti-goal #10).

**Shipped**:

- `src/ai_engineering/templates/project/CANONICAL.md` (≤360 lines)
  carries the full "how AI works in this repo" payload: bootstrap
  (§0), Karpathy + Boris behaviour pillars (§§1–9), first-class
  engineering principles (§10.1 KISS · §10.2 YAGNI · §10.3 SOLID ·
  §10.4 DRY · §10.5 TDD · §10.6 SDD · §10.7 Clean Code · §10.8
  Hexagonal Architecture — each with definition + 3-5 rules +
  anti-patterns + example), canonical chain `/ai-brainstorm →
  /ai-plan → /ai-build → /ai-pr` (§11, no `/ai-commit` in chain
  per D-131-07), Surface Index (§12), Hard Rules (§13), Strict
  Content Contracts authoring table (§14), IDE-Extras Escape Hatch
  (§15).
- `scripts/sync_mirrors/core.py` refactored: new helpers
  `read_canonical_payload()` + `assemble_mirror_payload()`. Surfaces
  5.5 (CLAUDE.md), 7 (AGENTS.md), 7.5 (GEMINI.md), 8 (Copilot) all
  read CANONICAL.md and emit byte-equivalent payload + IDE-extras
  fence. The cross-ref line at `core.py:1103` (`See [AGENTS.md]…`)
  is REMOVED per D-131-14. No new sync entry point.
- `<repo>/.gemini/GEMINI.md` DELETED per D-131-03 (Gemini CLI does
  not read in-repo `.gemini/`). Surface 7.5 no longer writes there.
- `CONSTITUTION.md` rescoped to project-identity-only (10 sections:
  Mission / Stakeholders / Vocabulary / Prohibitions / Compliance
  gates / Anti-goals / Boundaries / Escalation / Language /
  Lifecycle phase). All AI-behaviour content migrated to
  CANONICAL.md. Pre-migration body rotated verbatim to
  `.ai-engineering/specs/_history-constitution-2026-05-11.md` for
  traceability (R-131-03 mitigation).
- `tools/skill_lint/checks/md_mirror.py` (NEW) — five sub-checks:
  sha256 equivalence across the four mirrors (fence stripped),
  no `@AGENTS.md` import, no `.gemini/GEMINI.md` orphan, no
  `.codex/AGENTS.md` orphan, no forbidden AI-behaviour headers in
  CONSTITUTION.md (`FORBIDDEN_CONSTITUTION_HEADERS`).
- `tools/skill_lint/checks/principles.py` (NEW) — every SKILL.md
  `## Workflow` cites at least one `§10.x` anchor. Advisory-grade
  for sub-001 (R-1.6); upgraded to blocking in S6.
- `tools/skill_lint/cli.py` wires both new checks: summary line
  extended with `md_mirror={OK|FAIL}` and `principles OK=N MINOR=M
  MAJOR=K` counters. `md_mirror` CRITICAL → exit 1; principles
  advisory.
- `/ai-constitution` SKILL.md refactored to interview-driven
  10-section project-identity mode (D-131-04). NEVER overwrites
  without diff + confirm (R-131-03). Cites `§10.6` (SDD) and
  `§10.4` (DRY) in `## Workflow` so it passes the new principles
  check on itself.
- `/ai-ide-audit` SKILL.md extended with Antigravity in
  argument-hint + `## Quick start` example. The capability matrix
  reference gains a per-IDE assertion lookup table (Claude /
  Copilot / Gemini / Codex / Antigravity) + an Antigravity advisory
  probe section (R-131-08 — no deterministic CLI version probe yet).
- `tests/conformance/test_md_mirror.py` (NEW, 32 tests).
- `tests/conformance/test_principles.py` (NEW, 26 tests).
- `tests/integration/sync/test_canonical_mirror_parity.py` (NEW, 8
  tests) — byte-equivalence + idempotency (`sync_command_mirrors.py
  --check` runs twice with zero diff on the second pass per R-1.4).

**No backwards-compat shims** (D-131-15 anti-goal #10): every
mirror is regenerated; every reader must follow the canonical
path. The cross-ref line in `.github/copilot-instructions.md` is
hard-deleted, not aliased.

**Anonymous content** (D-131-15): no PII, no machine paths, no
operator names anywhere in the shipped surface.

### spec-129 — Skills + Agents Excellence Refactor (Pragmatic Scope)

Trimmed scope of the original `skills-agents-excellence-refactor.md` brief (8
milestones) to the deterministically safe items. Lands on the same branch
and the same PR as spec-128 (PR #509) per user direction — no new branch,
no new PR.

**Shipped**:

- Three shared libs under `.ai-engineering/scripts/skills/skill_scripts_lib/`:
  - `manifest_reader.py` — `resolve_stack`, `read_work_items`, typed errors
  - `git_activity.py` — `recent_merges`, `last_commit`, `commits_since`,
    `branch_age_days`, typed `Commit` / `Merge` records, `NoCommitsError`
  - `markdown_render.py` — `render_table`, `render_checklist`,
    `parse_frontmatter`, `strip_frontmatter`, typed errors
- Three hot-path scripts under `.ai-engineering/scripts/skills/skill_scripts/`:
  - `standup_render.py` — deterministic `/ai-standup` rendering
  - `cleanup_run.py` — deterministic branch classification + safe deletion
  - `resolve_classify.py` — conservative conflict classification
    (adversarial-test-driven; lock-with-manual-edits and generated-without-
    sentinel return `ambiguous`, never `auto-resolve`)
- Refactored existing hot-path scripts to consume the shared libs
  (`session_bootstrap.py`, `commit_compose.py`, `pr_body_compose.py`) —
  behavior-preserving; all existing tests stay green.
- M5 deterministic_router verification: 29 router tests green on 7 stacks
  (typescript, python, go, rust, swift, csharp, kotlin) with `UnknownStackError`
  + p95 ≤ 50 ms. No implementation change needed — sub-008 + spec-128 had
  already shipped the working code.
- `pyproject.toml` `pythonpath` extended once with
  `.ai-engineering/scripts/skills` so both `skill_scripts_lib` and
  `skill_scripts` are importable in tests without dist-packaging.

**Corrected baseline** (post-audit reality):

- Skills: 47 user-facing (excluding the `_shared/` helpers directory).
  `ai-analyze-permissions` is a legitimate Claude-Code-only skill that
  postdates the original brief; the brief's "46 target" was an estimate.
- Agents: 24 in `.claude/agents/` (9 `ai-*` first-class + 11 `reviewer-*`
  + 4 `verifier-*`). AGENTS.md continues to surface only the 9
  first-class agents because the `reviewer-*` / `verifier-*` sets are
  dispatched-only, not user-invocable.
- `ai-poster` is NOT created (D-129-04). `ai-visual` already covers
  static visual design — the original brief's §4 alt clause anticipated
  this consolidation.

**Deferred to follow-up** (`spec-130` draft created at
`.ai-engineering/specs/drafts/skills-agents-excellence-phase-c.md`):

- M6 eval corpus (`evals/<skill>.jsonl` ≥ 16 cases per skill) — without
  it, description-level refactors are hope-driven. Building the corpus
  is ~150 h focal, too expensive to bundle with PR #509.
- M3 SKILL.md length cuts (24 skills currently > 120 lines).
- §22 pair-length cuts (5 skill+agent pairs).
- M2 Grade A target uplift via `/ai-prompt` optimization passes.

Each deferred item depends on the eval corpus existing first — the M6
gate is the regression detector that lets the description-level work
ship safely.

**Tests added**: 51 in Phase 0 (`tests/unit/scripts/_lib/`) + ~71 in
Phase 1 (`tests/integration/scripts/`) = ~122 new tests across the
new libs and scripts. Existing tests for `session_bootstrap`,
`commit_compose`, `pr_body_compose` stay green. Layer-isolation test
remains green (domain ↛ infra rule honoured).

### spec-127 Wave 8 — D-127-10 strict surface-count enforcement

Wave 4 (sub-005) overshot the umbrella spec target (46 skills + 23 agents)
by +2 skills (`/ai-help`, `/ai-board`) and +1 agent. Wave 8 closes the gap
by demoting `/ai-help` to a reference file and confirming the remaining
counts are arithmetic-correct given the deliverables that landed.

**Skill demotion**:

- `/ai-help` deleted as a top-level skill. The 12-entry legacy → canonical
  matchback table moved to
  `.claude/skills/ai-cleanup/references/legacy-name-map.md` and is
  surfaced via a brief "Legacy name lookup" section in
  `.claude/skills/ai-cleanup/SKILL.md`. Operators looking up a renamed
  slash command (e.g. `/ai-dispatch` → `/ai-build`) read the reference
  file directly; per D-127-04 there is no alias dispatcher.

**Surface counts (Wave 8 vs. spec target)**:

| Surface | Wave 4 (sub-005) | Wave 8 | Spec target |
| --- | --- | --- | --- |
| `.claude/skills/` (excluding `_shared/`) | 48 | 47 | 46 |
| `.claude/agents/*.md` | 24 | 24 | 23 |
| `manifest.skills.total` | 48 | 47 | 46 |
| `manifest.agents.total` (orchestrators only) | 9 | 9 | n/a |

**47 vs. 46 gap (skills)**: the umbrella D-127-10 arithmetic was
off-by-one. The brief assumed a `/ai-build` duplicate that never existed
on disk (the rename `/ai-dispatch` → `/ai-build` was a 1:1 swap, not a
merger). Net Wave-4 + Wave-8 change: −4 deletions
(`ai-run`, `ai-board-discover`, `ai-board-sync`, `ai-release-gate`)
−1 demotion (`ai-help` → reference file) + 1 creation (`ai-board` for
the discover+sync subcommand merger) = −4 net (50 → 47). Closing the
last point to 46 would require an arbitrary skill merger that has no
governance justification; tracked as "spec target was aspirational"
rather than a follow-up sweep.

**24 vs. 23 gap (agents)**: Wave 8 audited every agent in
`.claude/agents/` for dispatch references in `.claude/skills/**/SKILL.md`
and `.claude/agents/**/*.md`. **All 24 agents are dispatch-referenced**:
9 first-class orchestrators (called by users + Wave-orchestrating
skills), 11 reviewer specialists (dispatched by `/ai-review`), 4
verifier specialists (dispatched by `/ai-verify`). No orphan was
available for deletion without an arbitrary content merger. The umbrella
spec target of 23 assumed a consolidation (likely
`reviewer-validator` → `reviewer-context`, or `verifier-feature` →
`verifier-architecture`) that has no architectural justification on the
live surface — both pairs carry distinct contracts and outputs. Wave 8
keeps the count at 24 strict and pins the assertion in
`tests/mirrors/test_count_parity.py::test_disk_agent_total_in_documented_range`.

**Mirror parity**: `python scripts/sync_command_mirrors.py --check`
reports `47 skills, 9 agents` discovered; all 1232 mirror files in sync.
`tests/mirrors/test_count_parity.py` (6 tests) GREEN at the new counts.

**Documentation**: AGENTS.md heading updated to `Skills (47)`; template
mirror at `src/ai_engineering/templates/project/AGENTS.md` matches.
`.ai-engineering/manifest.yml skills.total` flipped to 47 with comment
explaining the new gap rationale; template manifest matches.

### spec-127 sub-005 (M4) — Skill + Agent renames + mergers (no aliases)

Per umbrella spec-127 D-127-04 (no aliases), D-127-05 (`/ai-canvas` →
`/ai-visual`), D-127-10 (deduplicated surface), D-127-11 (`/ai-build`
canonical implementation gateway), D-127-12 (`/ai-autopilot` single
autonomous wrapper, `--backlog` mode absorbs `/ai-run`).

**Skill renames** (canonical name only; no alias dispatcher):

| Legacy | New | Decision |
| --- | --- | --- |
| `/ai-dispatch` | `/ai-build` | D-127-11 — canonical implementation gateway |
| `/ai-canvas` | `/ai-visual` | D-127-05 — broader visual category framing |
| `/ai-market` | `/ai-gtm` | clearer go-to-market framing |
| `/ai-mcp-sentinel` | `/ai-mcp-audit` | verb-noun naming; audit is the action |
| `/ai-entropy-gc` | `/ai-simplify-sweep` | no metaphor; sweep == repeated simplify |
| `/ai-instinct` | `/ai-observe` | verb-noun; what the skill actually does |
| `/ai-skill-evolve` | `/ai-skill-tune` | tune is the operation; evolve overpromised |
| `/ai-platform-audit` | `/ai-ide-audit` | we audit IDE wiring, not platforms |

**Skill mergers**:

- `/ai-run` deleted; functionality absorbed by `/ai-autopilot --backlog --source <github|ado|local>` (D-127-12).
- `/ai-board-discover` + `/ai-board-sync` merged into `/ai-board <discover|sync>` subcommand surface.
- `/ai-release-gate` deleted; functionality absorbed by `/ai-verify --release` mode flag.

**Skill creations**:

- `/ai-help` — new matchback surface that prints the canonical seven-step chain and suggests the new name when an operator types a legacy slash command (≤30 LOC matchback table; D-127-04 mandates suggestion-only, no aliasing).
- `/ai-board` — new merger target for the discover + sync subcommand routing.

**Agent renames**:

| Legacy | New |
| --- | --- |
| `review-context-explorer` | `reviewer-context` |
| `review-finding-validator` | `reviewer-validator` |

**Agent deletions**:

- `ai-run-orchestrator.md` — deleted; functionality absorbed by `ai-autopilot` agent (`--backlog --source` mode).
- `reviewer-design.md` — deleted; design-system rules (animation, typography, forms, focus, content handling, images) absorbed into `reviewer-frontend.md` body.

**Telemetry note**: scheduled wrapper at `.ai-engineering/scripts/scheduled/entropy-gc.sh` keeps its legacy filename (cron pinned by operators); the underlying skill is the renamed `/ai-simplify-sweep`. `framework_operation` event names (`entropy_gc_started`, `entropy_gc_no_op`, etc.) retained for backwards compatibility with the spec-120 audit index.

**Surface counts (achieved vs. spec target)**:

| Surface | Before | After | Spec target |
| --- | --- | --- | --- |
| `.claude/skills/` (excluding `_shared/`) | 50 | 48 | 46 |
| `.claude/agents/*.md` | 26 | 24 | 23 |
| `manifest.skills.total` | 50 | 48 | 46 |
| `manifest.agents.total` (orchestrators only) | 10 | 9 | n/a |

**Achieved counts (48 + 24) differ from the umbrella D-127-10 target (46 + 23)** because the spec arithmetic did not budget for the *creation* of two new skills required by the M4 plan (`/ai-help` for the matchback surface; `/ai-board` for the discover+sync merger target) — both are explicit M4 deliverables. Net change from M4: −4 deletions (`ai-run`, `ai-board-discover`, `ai-board-sync`, `ai-release-gate`) + 2 creations = −2 net (50 → 48). Closing the gap to 46/23 requires 2 additional skill consolidations and 1 more agent deletion that fall outside M4 scope; tracked as a follow-up sweep before umbrella spec-127 closes.

**Mirror parity**: `python scripts/sync_command_mirrors.py --check` reports `48 skills, 9 agents` discovered; all 1232 mirror files in sync. New test `tests/mirrors/test_count_parity.py` (6 tests, all GREEN) pins the achieved counts and asserts canonical = mirror parity across `.claude/`, `.github/` (with `ai-analyze-permissions` opt-out), `.codex/`, `.gemini/`.

**Documentation**: AGENTS.md regenerated to 74 lines (under the 80-line cap; canonical seven-step chain verbatim; legacy-name absent test passes); `/ai-help` matchback table covers all 12 legacy → new mappings.

### spec-124 (Wave 1) — Post-install UX polish

- **IDE keys renamed to hyphenated vendor-product form**: `claude_code` → `claude-code`, `gemini` → `gemini-cli`, `github_copilot` / `copilot` → `github-copilot`. Manifest read shim translates old underscore values for one release courtesy (removed in spec-125). External scripts hardcoding old keys must update — pointer: see `--ide` help text.
- **"What's new" install banner removed**: install pipeline starts directly with phase output. No more one-shot notice.
- **Tool installation header**: shortened helper text + fixed `[5/6] [5/6]` duplication.
- **Hooks count reported correctly** in Install Complete summary (was always 0; pipeline result wasn't populating `result.hooks.installed`).
- **Visual breathing room** added between "Open your AI assistant…" line and the Install Complete panel.

### TL;DR

ai-engineering 0.5.0 turns the installer into a hard, observable contract, makes Python tooling worktree-fast, ships a single-pass local gate with caching, and graduates risk acceptance to a first-class CLI. Cross-IDE polish lands on Copilot.

| What's new | Why it matters |
| --- | --- |
| Installer fails loudly with EXIT 80 / EXIT 81 | No more silent passes hiding broken stacks |
| Python tools install once into `~/.local/share/uv/tools/` | New worktrees are ready in seconds, not minutes |
| `ai-eng install` auto-heals tool failures | One command instead of three |
| Live `[N/M] phase_label` progress | You see what step the install is on, in real time |
| Single-pass gate orchestrator with 24h SHA-256 cache | Local pre-commit becomes 2-3x faster on warm checkouts |
| First-class `ai-eng risk *` CLI | Risk acceptances are no longer hand-edited JSON |
| `gates > mode: prototyping` opt-out | Spike work skips Tier 2 governance; CI always overrides |
| Copilot `@Explorer` -> `@ai-explore` | One agent name across Claude, Copilot, Codex, Gemini |
| `required_tools` governs 14 stacks | Adding a stack without tools is rejected by the manifest lint |

### Breaking changes — read before you upgrade

1. **`ai-eng install` and `ai-eng doctor --fix --phase tools` now exit non-zero on missing tooling.** Two reserved codes carry the diagnosis: `EXIT 80` (a required CLI tool failed to install or verify) and `EXIT 81` (a language SDK / prerequisite is missing). **Migration:** remove any `ai-eng install || true` shielding from CI. If a tool is genuinely unsupported on a host OS, declare `platform_unsupported` (tool-level) or `platform_unsupported_stack` (stack-level) in `manifest.yml` with a non-empty `unsupported_reason`.
2. **`python_env.mode` defaults to `uv-tool`.** Existing projects pick `uv-tool` automatically on the next install. **Migration:** if your team relies on `source .venv/bin/activate`, set `python_env > mode: venv` in `.ai-engineering/manifest.yml` *before* running `ai-eng install`. A worktree-aware option (`mode: shared-parent`) is also available.
3. **`required_tools` covers 14 stacks (python, typescript, javascript, java, csharp, go, php, rust, kotlin, swift, dart, sql, bash, cpp).** Adding a stack to `manifest > providers > stacks` without a matching `required_tools > <stack>` block is rejected by governance lint. **Migration:** if you stack-extend, add the matching tool block.
4. **GitHub Copilot agent `@Explorer` is now `@ai-explore`.** Slash command `/ai-explore` is also added on Copilot. **Migration:** any Copilot Chat workspace prompt that hardcodes `@Explorer` must update to `@ai-explore`. The agent's behaviour is unchanged.
5. **New `manifest > gates > mode` field.** Default `regulated` keeps full Tier 0+1+2 enforcement; `prototyping` skips Tier 2 governance for spike work. CI auto-detects via `CI=true` / `GITHUB_ACTIONS=true` / `TF_BUILD=True` and forces `regulated` regardless of the manifest, so prototyping mode cannot leak to protected branches or CI runs. **Migration:** none — `regulated` is the default.

### Migration in 5 minutes

```bash
# 1. Upgrade the CLI
pipx upgrade ai-engineering        # pipx
uv tool upgrade ai-engineering     # uv
pip install --upgrade ai-engineering  # pip in a venv

# 2. Re-install in each project. Auto-remediation runs on the second pass.
ai-eng install .

# 3. Verify the install ended healthy.
ai-eng doctor
```

Optional steps:

- If you need the legacy per-cwd `.venv/`: set `python_env > mode: venv` in `.ai-engineering/manifest.yml` *before* step 2.
- If you fork-customise Copilot agents and reference `@Explorer` literally: replace it with `@ai-explore` and rename `.github/agents/explore.agent.md` to `.github/agents/ai-explore.agent.md`.

### Detailed changes

The sections below preserve the full technical record (decision IDs, schema deltas, rule references). Skip these if you only needed the migration above.

### Added

#### spec-109 — Installer first-install robustness (auto-remediation + live progress)

- **`PhaseProtocol` opt-in `critical: bool` flag (spec-109 D-109-01, D-109-02).**
  A phase that declares `critical = False` is recorded in
  `PipelineSummary.non_critical_failures` when its verdict fails, but the
  pipeline keeps going to the next phase. Phases that omit `critical` keep the
  legacy `critical=True` behaviour automatically. `PipelineSummary` adds a
  new additive field `non_critical_failures: list[str]`.

- **`ToolsPhase.critical = False` (spec-109 D-109-03).** A failed tool
  install no longer cascades into `HooksPhase`. Pre-spec-109 a single bad
  tool meant `.git/hooks/` was empty, `install-state.json` lacked
  `hook_hash:*` entries, and the next `ai-eng doctor` reported
  `hooks-integrity FAIL`. Hooks now write unconditionally on every install,
  regardless of tool outcomes.

- **Auto-remediation in `ai-eng install` (spec-109 D-109-05).** When the
  pipeline records non-critical failures, the install command invokes the
  same `doctor.phases.tools.fix` + `doctor.phases.hooks.fix` paths used by
  `ai-eng doctor --fix`. The user no longer has to follow `install` with two
  manual remediation commands. Behaviour is reported in the JSON envelope
  under the additive `auto_remediation: {invoked, success, applied, failed,
  errors}` key.

- **`--no-auto-remediate` flag (spec-109 R-109-01).** CI consumers that want
  to detect "first attempt failed" disable the second-pass repair so the
  install still surfaces EXIT 80.

- **Live multi-step progress UI (spec-109 D-109-07).** The single-spinner
  `Installing governance framework...` is replaced by
  `step_progress(total=len(PHASE_ORDER))`. The CLI shows
  `[N/M] phase_label` in real time. `install_with_pipeline` and
  `PipelineRunner` both accept an optional
  `progress_callback: Callable[[str], None]` (default `None`, so existing
  programmatic callers are unaffected).

- **Pre-install banner honesty (spec-109 D-109-08).** `Tools:` is now
  labelled `Tools (PATH):` with a dim qualifier explaining that `✓` only
  reflects PATH availability, not install-pipeline success. Eliminates the
  contradiction between the green check on the banner and `tools-required`
  failures during install.

### Fixed

- **Render pipeline steps BEFORE exiting on tool failure (spec-109 D-109-04).**
  Pre-spec-109 the install command emitted `"Tool installation failed; see
  warnings above"` and then `raise typer.Exit(80)` BEFORE the line that
  rendered the step report. Users saw the "see warnings above" message with
  no warnings printed. The render pass now happens unconditionally and the
  exit (when needed) follows.

### BREAKING

#### spec-107 -- Copilot Explorer agent renamed (BREAKING-LIKELY, Copilot only)

- **Agent `@Explorer` renamed to `@ai-explore` for cross-IDE consistency
  (spec-107 D-107-03).** Claude Code, Codex, and Gemini already used the
  canonical `ai-explore` slug; this rename brings GitHub Copilot Chat in
  line. Slash command `/ai-explore` is also added via a new chatmode
  alias at `.github/chatmodes/ai-explore.chatmode.md`, so both
  `@ai-explore` (subagent invocation) and `/ai-explore` (Claude-style
  slash) resolve to the same agent persona on Copilot. The legacy
  `.github/agents/explore.agent.md` filename is replaced by
  `.github/agents/ai-explore.agent.md`. Migration: any Copilot Chat
  workspace prompt that hardcodes `@Explorer` must update to
  `@ai-explore`. The agent's behaviour, tooling, and read-only contract
  are unchanged.

- **`scripts/sync_command_mirrors.py` `AGENT_METADATA["explore"]["display_name"]`
  switched from `"Explorer"` to `"ai-explore"`.** Every IDE mirror surface
  regenerates with the canonical slug on the next `ai-eng sync`. Anyone
  forking the framework with custom `AGENT_METADATA` overrides should
  audit their fork for the `Explorer` literal and update accordingly.

- **`templates/project/GEMINI.md` count placeholders (spec-107 D-107-04).**
  The template now ships with `__SKILL_COUNT__` and `__AGENT_COUNT__`
  placeholders in the `## Skills (N)` and `## Agents (N)` h2 headers and
  Source-of-Truth table cells. `scripts/sync_command_mirrors.py
  write_gemini_md(...)` materialises these against the canonical
  `.claude/skills/` + `.claude/agents/` discovery on every sync, so the
  rendered `.gemini/GEMINI.md` and root `GEMINI.md` always match disk
  reality. No user-visible behavioural change; placeholder leakage is
  caught by the new `/ai-platform-audit` Check 7.

- **`/ai-platform-audit` advisory checks 6/7/8 (spec-107 D-107-04, NG-11).**
  Three new advisory-only checks land:
  - Check 6 — agent naming consistency cross-IDE (catches future
    Explorer-style mismatches across `.claude/`, `.github/`, `.codex/`,
    `.gemini/` agents).
  - Check 7 — `.gemini/GEMINI.md` skill count freshness (regression
    detection if the template placeholder is removed and replaced with a
    stale literal).
  - Check 8 — generic instruction-file count scan (defense-in-depth
    across `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`,
    `.gemini/GEMINI.md`).
  All three emit advisory WARN only and never hard-fail. Hard-gate
  enforcement lands in a future spec when ≥90% of projects pass cleanly.

#### spec-105 -- Unified Gate + Generalized Risk Acceptance (BREAKING-LIKELY)

This release introduces a new CLI namespace (`ai-eng risk *`), a new
manifest field (`gates.mode`), an additive schema bump (`gate-findings`
v1 -> v1.1), and an opt-out auto-stage default. The "BREAKING-LIKely"
flag covers the manifest field default and the auto-stage flip; both
are additive but change observable behaviour for projects that were
relying on the legacy implicits.

- **New `ai-eng risk *` namespace (D-105-05).** Seven subcommands wire
  the existing `decision_logic` lifecycle to a public CLI: `accept`,
  `accept-all`, `renew`, `resolve`, `revoke`, `list`, `show`. The
  pre-spec-105 flow ("AI edits `decision-store.json` via prompt") is
  superseded; the JSON file is no longer expected to be hand-edited.
  Coexists with the existing `ai-eng decision *` namespace (which
  remains for architecture-decision and flow-decision entries).

- **New `manifest.yml.gates.mode` field (D-105-02).**
  `gates.mode: regulated` (default) keeps full Tier 0+1+2 enforcement.
  `gates.mode: prototyping` skips Tier 2 governance checks (`ai-eng
  validate`, `ai-eng spec verify`, docs gate, risk-expiry warning) for
  spike work. Branch-aware escalation (D-105-03) and CI override force
  `regulated` regardless of manifest, so prototyping cannot leak to
  protected branches or CI runs.

- **`gate-findings.json` schema v1 -> v1.1 (additive, D-105-07).**
  New optional fields `accepted_findings: [{check, rule_id, file, line,
  severity, message, dec_id, expires_at}]` and `expiring_soon:
  [dec_id]`. v1 readers continue to work because the schema literal is
  a `Literal["ai-engineering/gate-findings/v1",
  "ai-engineering/gate-findings/v1.1"]` union and unknown fields are
  ignored.

- **Auto-stage default ON for the local pre-commit gate (D-105-09).**
  After Wave 1 fixers (ruff format, ruff check --fix, spec verify
  --fix) modify staged files, the orchestrator re-stages the safe
  intersection `S_pre & M_post` -- files that were already staged AND
  were modified by the fixers. Files newly created by fixers, or
  modified-but-unstaged files, are NEVER auto-staged. Disable with
  `ai-eng gate run --no-auto-stage` or the manifest field
  `gates.pre_commit.auto_stage: false`. The same shared utility
  (`policy/auto_stage.py`) is invoked by the Claude `auto-format.py`
  hook so orchestrator + hook produce identical results on the same
  fixture.

- **Orchestrator-level acceptance lookup (D-105-07).** After Wave 2,
  `apply_risk_acceptances(findings, store, now=now)` partitions
  findings into `(blocking, accepted)` lists, drops accepted items
  from the blocking set, and emits per-acceptance telemetry events
  (`category=risk-acceptance, control=finding-bypassed`). The CLI
  prints a compact ACCEPTED summary plus an `expiring_soon[]` banner
  when any DEC is within `_WARN_BEFORE_EXPIRY_DAYS=7` of expiry.

- **Cross-IDE parity for `ai-eng risk *` (G-10).** All risk + gate CLI
  output is byte-identical (after normalising session_id /
  produced_at / wall_clock_ms / commit_sha) across Claude Code, GitHub
  Copilot, Codex, and Gemini. The CLI is the single source of truth;
  IDE drivers never branch the orchestrator.

- **Prompt-injection-guard whitelist (G-12).** `ai-eng risk accept` and
  `ai-eng risk accept-all` are exempted from the
  injection-pattern scan because their inputs (gate-findings JSON)
  legitimately embed rule names like `aws-access-token` or
  `stripe-key`. The bypass emits a `category=security,
  control=prompt-guard-whitelisted` telemetry event so each whitelist
  match remains auditable.

##### Migration checklist

- [ ] After upgrading, run `ai-eng install` once to add `gates.mode`
      and `gates.pre_commit.auto_stage` defaults to `manifest.yml`.
- [ ] If you customised `auto-format.py` hook behaviour, review the
      shared `policy/auto_stage.py` utility -- the hook now delegates
      to it.
- [ ] If your project intentionally hand-edited `decision-store.json`
      to add risk acceptances, replace those flows with `ai-eng risk
      accept-all` invocations. Existing entries remain valid; only new
      entries gain the `finding_id` / `batch_id` fields.
- [ ] No CI changes required -- CI auto-detects via `CI=true` /
      `GITHUB_ACTIONS=true` / `TF_BUILD=True` and forces `regulated`
      mode.

#### spec-101 -- Stack-Aware User-Scope Tool Bootstrap (BREAKING)

This release replaces the previous best-effort tool-install path with a hard,
data-driven contract. Three changes alter behaviour you may have depended on
in CI scripts, install wrappers, or local tooling.

- **Hard-fail on missing required tools (no silent pass).**
  `ai-eng install` and `ai-eng doctor --fix --phase tools` now exit non-zero
  when a required tool cannot be installed or verified. Two reserved exit
  codes carry the diagnosis:
  - `EXIT 80` -- a required CLI tool is missing or unverifiable after the
    install attempt (covers ruff, ty, gitleaks, semgrep, pip-audit, prettier,
    eslint, vitest, checkstyle, dotnet-format, staticcheck, govulncheck,
    phpstan, php-cs-fixer, composer, cargo-audit, ktlint, swiftlint,
    swift-format, sqlfluff, shellcheck, shfmt, clang-tidy, clang-format,
    cppcheck, jq, pytest, tsc).
  - `EXIT 81` -- a language SDK / prerequisite declared in
    `prereqs.sdk_per_stack` is missing (covers JDK, Swift toolchain, Dart
    SDK, .NET SDK, Go toolchain, Rust toolchain, PHP, clang/LLVM).
  Migration: any `ai-eng install || true` workaround in CI must be removed.
  Either install the prerequisites first, mark the stack-tool combo as
  `platform_unsupported`, or pin a stack-level
  `platform_unsupported_stack` escalation in `manifest.yml`.

- **`python_env.mode` now defaults to `uv-tool`.**
  Python tools install once into `~/.local/share/uv/tools/` instead of a
  per-cwd `.venv/`. This is the worktree-fast default -- creating a new
  worktree no longer triggers a multi-minute `.venv` re-install. Two
  escape hatches remain for projects that need the legacy behaviour:
  - `python_env.mode: venv` -- restore the pre-spec-101 per-cwd `.venv/`
    install path. Use this when your team relies on `source .venv/bin/activate`
    workflows or commits a project-local `.venv/` policy.
  - `python_env.mode: shared-parent` -- worktree-aware shared `.venv` at
    the repo root. Requires a git repo. Use this when you want a single
    `.venv` shared across worktrees but cannot adopt `uv-tool` (e.g.,
    enterprise tools that pin to a venv path).
  Migration: existing repos auto-pick `uv-tool` on next install. To stay on
  `.venv`, set `python_env.mode: venv` in `.ai-engineering/manifest.yml`
  before running `ai-eng install` or `ai-eng doctor --fix`.

- **`required_tools` now covers 14 stacks.**
  The single source of truth in `manifest.yml > required_tools` lists tools
  for: baseline + python, typescript, javascript, java, csharp, go, php,
  rust, kotlin, swift, dart, sql, bash, cpp -- 14 stacks total. Adding a
  stack to `manifest.providers.stacks` without declaring its tool block
  is no longer possible: the governance lint refuses the manifest. The
  hardcoded `_PIP_INSTALLABLE` and `_REQUIRED_TOOLS` literals in installer
  and doctor are gone -- both consumers read from the same manifest block.
  `platform_unsupported` (tool-level, max 2 of 3 OSes) and
  `platform_unsupported_stack` (stack-level, may list all 3) require an
  `unsupported_reason` per D-101-03 + D-101-13.

##### First-run BREAKING banner

The first `ai-eng install` after upgrading prints a one-shot BREAKING
banner to stderr summarising the contract change. The banner emits exactly
once per project; ``InstallState.breaking_banner_seen`` records the flag
in `.ai-engineering/state/install-state.json` so subsequent runs stay
quiet. Dry-run installs do not emit the banner.

##### Migration checklist

- [ ] Remove any `|| true` shielding around `ai-eng install` in CI.
- [ ] Decide your `python_env.mode`: `uv-tool` (default), `venv`
      (legacy per-cwd `.venv`), or `shared-parent` (worktree-aware).
- [ ] If you stack-extend, add a matching `required_tools.<stack>`
      block to `manifest.yml`.
- [ ] Verify with `ai-eng doctor --fix --phase tools`.

### Changed
- **Slash-command boundary clarification** -- clarified across multi-IDE instruction files, the `/ai-start` skill, and `.ai-engineering/README.md` that `/ai-*` entries are IDE slash commands and must not be inferred as `ai-eng` CLI subcommands unless explicitly documented.

### Added

#### spec-104 -- Commit/PR Pipeline Speed: Single-Pass Collector + Memoization + Bounded Watch

- **Single-pass orchestrator with 2-wave dispatch (D-104-01)** -- new `src/ai_engineering/policy/orchestrator.py` replaces sequential gate flow. Wave 1 (serial fixers): `ruff format` -> `ruff check --fix` -> `spec verify --fix`. Wave 2 (parallel checkers): `gitleaks protect --staged`, `ai-eng validate`, docs gate, `ty check src/`, `pytest -m smoke`. Recolección completa en una pasada produce `.ai-engineering/state/gate-findings.json`.
- **Local fast-slice + CI authoritative gate policy (D-104-02)** -- fixed framework policy (not configurable). Local executes only fast checks (≤60s budget); `semgrep`, `pip-audit`, `pytest` full + matrix run authoritative in CI. Watch loop autofixes CI failures. Política documented in `.ai-engineering/contexts/gate-policy.md`.
- **Hash + max-age 24h gate cache (D-104-03)** -- new `src/ai_engineering/policy/gate_cache.py`. Cache key = sha256(tool_name ‖ tool_version ‖ sorted(staged_blob_shas) ‖ sorted(config_file_hashes) ‖ sorted(args)). Storage at `.ai-engineering/state/gate-cache/<cache-key>.json` per-cwd. Hit replay (PASS or FAIL) skips run; miss executes and persists. Invalidación: any input change OR `now() - verified_at > 24h`. LRU prune to 256 entries; cap ≤16 MB.
- **Async parallel docs + pre-push (D-104-04)** -- `/ai-pr` step 6.5 dispatches 3 concurrent lanes (docs A1: CHANGELOG+README, docs A2: docs-portal+quality-gate, lane 3: pre-push gate Wave 2). Wall-clock = `max(docs, pre-push)` instead of `sum`. Coherence preserved: docs staged BEFORE PR creation; no fire-and-forget post-PR commits (NG-7).
- **Watch loop wall-clock bounds (D-104-05)** -- active phase cap 30 min from `last_active_action_at`, passive phase cap 4h from `watch_started_at`. On cap: emit `.ai-engineering/state/watch-residuals.json` (gate-findings v1 schema), print actionable message, exit code 90 (distinct from spec-101 EXIT 80/81).
- **GateFindingsDocument schema v1 contract (D-104-06)** -- canonical schema `ai-engineering/gate-findings/v1` emitted by orchestrator and watch loop. Stable `rule_id` (CVE/semgrep/gitleaks/ruff/ty rule codes — never human messages). Versioned `schema` field for non-breaking evolution. Fixture canonical at `tests/fixtures/gate_findings_v1.json`. Consumer contract for spec-105 (S3 risk-accept).
- **SKILL.md verbosity reduction (~30%) (D-104-07)** -- ≥160 lines removed from `ai-commit/SKILL.md` + `ai-pr/SKILL.md` + `ai-pr/handlers/watch.md` (532 -> ≤372). Only verified duplicates removed (cross-referenced against CLAUDE.md Don't section, `contexts/languages/`, anti-pattern consolidation in watch.md). Mandatory sections preserved: `## Process`, `## Integration`, `## Quick Reference`, `argument-hint` frontmatter.
- **Cross-IDE parity via CLI-layer (D-104-08)** -- toda lógica de speed-up vive en `policy/orchestrator.py` + `policy/gate_cache.py` invocados via CLI `ai-eng gate run --cache-aware --json`. Skills mirrors (`.claude/`, `.github/`, `.codex/`, `.gemini/`) instruyen al agent a invocar el CLI en lugar de herramientas individuales. Beneficio idéntico independiente del IDE driver.
- **`gate run` CLI flags (D-104-10)** -- nuevo subcomando `ai-eng gate run` con `--cache-aware` (default ON), `--no-cache` (skip lookup, fresh run, persist), `--force` (skip lookup, clear matching entry, fresh run, persist), `--json`, `--mode={local,ci}`, `--produced-by`. Sin nuevos comandos top-level (NG-8).
- **`gate cache` subcommands** -- `ai-eng gate cache --status` (read-only listing of entries + max-age + tamaño total) y `ai-eng gate cache --clear` (interactive confirmation o `--yes`). Sub-flags de comando existente.
- **New env vars** -- `AIENG_LEGACY_PIPELINE=1` restores pre-spec-104 sequential gate flow. `AIENG_CACHE_DISABLED=1` global cache kill switch (equivalente a `--no-cache`). `AIENG_CACHE_DEBUG=1` enables cache hit/miss logging.

##### Migration note

`AIENG_LEGACY_PIPELINE=1` env var restores the pre-spec-104 sequential local-only gate behavior (no orchestrator, no cache, no parallel Wave 2). Use solo si surge una regresión que requiera audit trail comparison contra el flujo previo. CI cache reuse via `actions/cache@v4` con la misma key schema que el local; storage físico independiente (CI no monta el cache local del dev).

<!-- AUTO -->
<!-- Entries below this marker are auto-managed by /ai-pr / autopilot
     deliver. Manual edits go ABOVE the marker; edits below may be
     overwritten on next sub-spec wave. -->

### Added (spec-122-a)
- **Spec-122 Phase 1 hygiene wave** — manifest cleanup, governance
  metadata, `evals/` directory removal (44 files), telemetry
  consent posture switched to `strict-opt-in`. Sub-001 / wave 1.

### Added (spec-122-b)
- **Unified `state.db` infrastructure** — single SQLite projection
  replacing scattered `*.db` files; migration scaffolding +
  rotation primitives. Sub-002 / wave 2 (CLI verbs queued for
  follow-up release).
- **Engram delegation surface** — memory layer subprocess boundary
  formalised; per-IDE templates consolidate via `engram setup`.

### Changed (spec-122-c)
- **OPA proper switch** — governance now uses Open Policy Agent
  bundles in place of the legacy custom Rego subset interpreter.
  Pre-commit OPA check is wired and active. Sub-003 / wave 2.
  Legacy `policy_engine.py` interpreter remains for backwards
  compat; full removal queued for spec-123.

### Changed (spec-122-d)
- **`scripts/sync_command_mirrors.py` (82 KB) → `scripts/sync_mirrors/`
  package** — split per-concern (`core`, `frontmatter`, `manifest_sync`,
  `claude_target`, `codex_target`, `gemini_target`, `copilot_target`).
  Backwards-compat shim ≤ 2 KB at original path. Parity guarded by
  `tests/integration/sync/test_sync_compat.py`.
- **Spec path canonicalization (D-122-40)** — 45 skill markdown
  files (204 occurrences) rewritten from legacy `specs/spec.md` /
  `specs/plan.md` / `specs/autopilot/` to the resolver-canonical
  `.ai-engineering/specs/spec.md`. CI guard added at
  `tests/unit/skills/test_spec_path_canonical.py` (idempotency-safe
  via negative-lookbehind regex).
- **Hook canonical event count (D-122-27)** — audited
  `.claude/settings.json`: 11 events, 0 dead wirings. CLAUDE.md
  documents the count; CI guard at
  `tests/unit/hooks/test_canonical_events_count.py`.
- **Hot-path SLO tests (D-122-28)** — pre-commit < 1 s p95,
  pre-push < 5 s p95, single-invocation < 500 ms p95 (CI ×1.2
  slack). Tests at `tests/unit/hooks/test_hot_path_slo.py`.
- **Legacy implement-skill rename to dispatch** in `CONSTITUTION.md`
  and the project template (the previous skill name was retired). CI
  guard at `tests/unit/docs/test_skill_references_exist.py` ensures
  every `/ai-<name>` reference in canonical docs resolves to a real
  skill.
- **`docs/cli-reference.md` audit section** added documenting
  `ai-eng audit verify/index/query/tokens/replay/otel-export`.
- **`docs/solution-intent.md`** — Skills table refreshed (47 → 51).
- **`.gitignore`** hardened: explicit `**/.DS_Store`, `**/Thumbs.db`,
  `**/desktop.ini`, editor swap files; `state.db*` patterns at
  root and under `.ai-engineering/state/`.

### Removed (spec-122-d)
- **`scripts/skill-audit.sh`** (spec-106 advisory) — every entry was
  `eval-failed-cli-missing` because the `ai-eng skill eval` verb
  never landed. Provides no signal; deleted with its tests
  (`tests/unit/test_audit_report_schema.py`,
  `tests/integration/test_skill_audit_advisory.py`).
- Working-tree `.DS_Store` files in tracked directories
  (`docs/`, `.claude/`, `.github/`, `tests/`, etc.). Index was
  already clean from sub-001; this is a working-tree purge to
  prevent re-adds. No history rewrite (deferred per master spec
  Risks).

### Known follow-ups
- `pyproject.toml` `sqlite-vec`, `fastembed`, `hdbscan`, `numpy`
  dependencies still listed (sub-002 deferred T-2.20). Removal
  scheduled for next minor release.
- 33 unit-test failures from waves 1+2 cleanup debt + Rego v1
  migration; queued for Phase 5 quality loop.
- `policy_engine.py` legacy Rego interpreter still present
  (sub-003 T-3.16 deferred). Removal scheduled for spec-123.
## [0.4.6] - 2026-04-07

### Fixed
- **Hook runtime source of truth alignment** -- consolidated hook source to single governance template, fixing drift after install/update cycles.
- **Work items provider sync** -- `work_items.provider` now syncs with VCS selection during install, board display corrected.
- **Missing PowerShell hook entries** -- added Copilot hook entries for Windows parity.

## [0.4.3] - 2026-04-06

### Fixed
- **Install runtime remediation unification (spec-102)** -- unified install/doctor runtime with early CLI bootstrap, shared environment classification, and dependency-closure validation.
- **Registry rewrite hardening** -- sonar registry rewrite now handles edge cases safely.
- **First-run onboarding** -- hardened hook runtime initialization during onboarding.
- **CI manual recovery** -- added `workflow_dispatch` to ci-build for manual re-trigger.

## [0.4.0] - 2026-04-02

### Changed
- **Runtime, install, doctor, and remediation unification (spec-102)** -- added an early CLI bootstrap preflight before full app import, shared environment classification and remediation contracts, feed preflight before install and repair, dependency-closure validation for framework runtime, and a tool capability matrix with explicit Windows `semgrep` guidance.
- **TLS-aware dependency audit path (spec-102)** -- added a Windows-friendly `pip-audit` wrapper that respects enterprise trust stores and wired it through verify, policy gates, CI, documentation, skills, and template mirrors.
- **Install documentation (spec-100)** -- README Install section now recommends `pipx` (primary) and `uv tool` (alternative) instead of bare `pip install`. Prerequisites listed before install commands. Documents that `ai-eng install` auto-installs missing tools.
- **GETTING_STARTED.md (spec-100)** -- added install preamble with link to README Install section.

### Fixed
- **Install/update hook source alignment (spec-103)** -- consolidated the hook runtime into a single governance template source, eliminating false-positive drift where `ai-eng update` reported hook changes immediately after a fresh `ai-eng install`.
- **Security verification fail-closed hardening (spec-102)** -- verify now fails closed when the `pip-audit` wrapper exits without usable JSON output instead of treating the audit as inconclusive.
- **Private feed preflight hardening (spec-102)** -- feed reachability checks now allow authentication-gated private feeds instead of blocking install or repair as unreachable.
- **Version alignment (spec-100)** -- `pyproject.toml` now matches latest PyPI release (was stuck at `0.1.0` while PyPI had `0.3.0`). `version/registry.json` backfilled with all three published versions.
- **CHANGELOG reorganization (spec-100)** -- entries assigned to correct `[0.3.0]` and `[0.2.0]` version headers. Previously everything was under `[Unreleased]` with no release boundaries.
- **CI version commit-back (spec-100)** -- `ci-build.yml` now commits version bump back to main via Git Data API after tag creation, preventing version drift. Added `[skip ci]` guard on `workflow_run` trigger to prevent infinite loops.

### Removed
- **Spanish documentation (spec-100)** -- deleted 2 internal Spanish-language documents from `docs/` (`trabajo-humano-era-ai-native-2026-2031.md`, `ai-engineering-auditoria-diagramas.md`). All documentation is now English-only.

## [0.3.0] - 2026-04-02

### Fixed
- **Wizard empty selection (spec-099)** -- `questionary.checkbox` prompts now validate non-empty selection with re-prompt and display spacebar usage hint. Prevents silent empty stacks/providers/IDEs in manifest.
- **VCS provider state gap (spec-099)** -- `state.vcs_provider` persisted during install, eliminating persistent VCS mismatch warning in doctor.
- **Duplicate VCS warnings (spec-099)** -- removed ToolsPhase warning promotion from `_summary_to_install_result()`, VCS tool warnings now appear once.
- **Pipeline step display order (spec-099)** -- `_render_pipeline_steps` imports `PHASE_ORDER` instead of hardcoding phase sequence.
- **Hardcoded Python gate paths (spec-099)** -- pre-push gate checks (`stack-tests`, `ty-check`) use dynamic path detection from `pyproject.toml` instead of hardcoded `src/ai_engineering` and `tests/unit/`. Checks gracefully skip when target path does not exist.

### Added
- **Project validation (spec-099)** -- `install_cmd()` validates target directory looks like a software project before proceeding. Warns and confirms in interactive mode, aborts in `--non-interactive`.
- **Contributor install flow (spec-099)** -- CONTRIBUTING.md documents `git clone` + source install + test workflow.
- **Branch policy help text (spec-099)** -- expanded with actionable setup steps for GitHub and Azure DevOps.

### Removed
- **Duplication checker from user gates (spec-099)** -- `python -m ai_engineering.policy.duplication` targeted ai-engineering's own source tree, not user projects. Kept in CI only.
- **Project-specific CVE exemption (spec-099)** -- removed `--ignore-vuln CVE-2026-4539` from user-facing `pip-audit` gate. Exemption moved to `pyproject.toml` for ai-engineering's own CI.

## [0.2.0] - 2026-04-01

### Changed
- **CLI branded banner** -- Rich-powered banner with version, branch, and Python info on all `ai-eng` commands. Consistent visual identity across CLI surface.
- **README ecosystem rewrite (spec-098)** -- rewrote `README.md` as GitHub landing page, `.ai-engineering/README.md` as post-install reference guide, and created `GETTING_STARTED.md` as progressive discovery tutorial (5-min win → problem-based → advanced).
- **Verify simplification** -- removed `verify_performance` and `verify_a11y` specialists (always N/A for non-UI/non-benchmark projects). Reduced verify from 8 to 6 specialists. Updated verify-deterministic agent and all IDE mirrors.
- **Canvas refinement** -- upgraded self-review criterion to "museum-quality" bar, formatting cleanup.
- **CI/CD Redesign (spec-097)** -- split 760-line `ci.yml` monolith into `ci-check.yml` (validation + dry build, PR + main) and `ci-build.yml` (build + supply chain, main only via `workflow_run`). Deprecated old `ci.yml`.
- **Artifact-driven releases (spec-097)** -- rewrote `release.yml` from tag-triggered to `workflow_dispatch` with version input (default: latest tag). Supports rollback by dispatching with an older version.
- **Conventional commits (spec-097)** -- adopted `feat(scope):` / `fix(scope):` format replacing `spec-NNN:` prefix. Updated `/ai-commit`, `/ai-pr` skills and all mirrors.
- **Single version source (spec-097)** -- eliminated `__version__.py`, version now read from `pyproject.toml` via `importlib.metadata`. Simplified `version_bump.py` to single-file management.

### Added
- **GETTING_STARTED.md (spec-098)** -- progressive discovery tutorial with 3 phases: "5-minute win" (/ai-start, /ai-guide), "What do you want to do?" (problem-based), and "Unlock the full power" (autopilot, run, instinct, learn). Separate CLI and slash command references.
- **python-semantic-release (spec-097)** -- automatic version bumping from conventional commits integrated into ci-build.yml. Creates tags and draft GitHub Releases on version bump.
- **SLSA Build attestations (spec-097)** -- `actions/attest-build-provenance` generates provenance in the same job as `uv build`, verifiable via `gh attestation verify`.
- **CycloneDX SBOM (spec-097)** -- generates `sbom.json` from production-only dependencies, attached to every release.
- **SHA-256 checksums (spec-097)** -- `CHECKSUMS-SHA256.txt` generated and attached to every release.
- **GitHub hardening (spec-097)** -- branch protection (1 required approval, code owner review, enforce for admins), tag protection (`v*` restricted to admins), PyPI environment restricted to main, Actions allowlist.

### Removed
- **`__version__.py` (spec-097)** -- replaced by `importlib.metadata.version("ai-engineering")`.
- **`ci.yml` monolith (spec-097)** -- replaced by `ci-check.yml` + `ci-build.yml`.

### Fixed
- **Commit-msg gate too strict (spec-097)** -- raised first-line length limit from 72 to 100 characters (aligned with Angular/commitlint conventions). Improved error messages to show the invalid input, valid types, and a corrective example.
- **`ai-eng update` provider filtering (spec-096)** -- update now reads `ai_providers.enabled` from manifest.yml instead of processing all 4 providers. Previously ignored manifest configuration and installed/updated files for all providers regardless of user selection.
- **Validator manifest-driven resolution (spec-096)** -- `_BASE_INSTRUCTION_FILES` in `_shared.py` and `_check_instruction_parity` in `mirror_sync.py` now dynamically resolve instruction files from `ai_providers.enabled` instead of hardcoding CLAUDE.md/AGENTS.md/copilot-instructions.md.
- **Obsolete path pattern (spec-096)** -- `_PATH_REF_PATTERN` in `_shared.py` dropped the `context/` (singular) branch, keeping only `contexts/` (plural) matching the actual directory structure.

### Added
- **Orphan file detection and cleanup (spec-096)** -- `ai-eng update` detects files from disabled providers as orphans, displays them in the tree with `orphan` state (dim magenta), and removes them on user confirmation. Shared files (e.g., AGENTS.md used by multiple providers) are only orphaned when no active provider needs them.
- **Missing instruction file validation (spec-096)** -- validator emits actionable error when an enabled provider's instruction file is missing: "Fix: run ai-eng update or ai-eng install --reconfigure".
- **Platform-filtered instruction files (spec-096)** -- expanded Copilot-only filter to include Gemini instruction files, correctly handling platforms with different skill counts.

### Added
- **`/ai-start` skill (spec-095)** -- session bootstrap with welcome dashboard, recent activity, board status, and available commands. Replaces `/ai-onboard`.

### Changed
- **`ai-board-discover` skill (spec-095)** -- improved board detection and configuration.
- **`ai-board-sync` skill (spec-095)** -- updated board sync script with better error handling.
- **`ai-constitution` skill (spec-095)** -- minor content refinements.
- **`ai-guide` skill (spec-095)** -- updated onboarding guidance.
- **`session-governance.md` (spec-095)** -- updated session governance context.
- **`stack-context.md` (spec-095)** -- updated stack context.
- **`manifest.yml` schema (spec-095)** -- updated manifest schema definition.
- **Hook scripts (spec-095)** -- updated `copilot-skill.ps1`, `copilot-skill.sh`, and `telemetry-skill.py` hook emitters.
- **CLAUDE.md, AGENTS.md, GEMINI.md, copilot-instructions.md (spec-095)** -- refreshed multi-IDE instruction files with latest skill set (47 skills).
- **`sync_command_mirrors.py` (spec-095)** -- improved mirror sync script.
- **Instincts v2 system (spec-095)** -- updated `instincts.yml`, `meta.json`, and `proposals.md`.

### Removed
- **`/ai-onboard` skill (spec-095)** -- replaced by `/ai-start`.

### Added
- **LESSONS.md relocated to `.ai-engineering/LESSONS.md` (spec-090 sub-001)** -- consolidated from `contexts/team/lessons.md` into a top-level framework artifact. Contains 30+ correction patterns, rules, and learning entries. All CLAUDE.md, AGENTS.md, GEMINI.md, and copilot-instructions references updated to the new path. Template mirrors updated accordingly.
- **Instincts v2 schema (spec-090 sub-002)** -- schema version bumped from `1.0` to `2.0`. Replaced `toolSequences`/`errorRecoveries`/`skillAgentPreferences` families with `corrections`/`recoveries`/`workflows`. Each entry now carries `trigger`, `action`, and `confidence` fields. Added confidence scoring (evidence-count tiers: 0.3/0.5/0.7/0.85), weekly decay (`-0.02/week`), and low-confidence pruning. Automatic v1-to-v2 migration preserves high-evidence entries.
- **Instinct skill workflow detection (spec-090 sub-002)** -- new `_detect_skill_workflows` reads `framework-events.ndjson` for `skill_invoked` events, groups by session, and counts sequential skill pairs to populate the `workflows` family.
- **`/ai-instinct` skill rewrite (spec-090 sub-003)** -- redesigned with two modes: passive listening (session start, observe corrections/recoveries silently) and active review (`--review` flag, extracts patterns, enriches with confidence, writes proposals). Replaced `status|review` argument with `--review` flag.
- **Improvement funnel with `proposals.md` (spec-090 sub-004)** -- new `.ai-engineering/instincts/proposals.md` generated by `/ai-instinct --review`. Cross-references instinct evidence with LESSONS.md to surface actionable improvement proposals.
- **`/ai-run` skill** -- autonomous backlog orchestrator that normalizes work items (GitHub Issues, Azure Boards, local markdown), plans safely from architectural evidence via `ai-explore`, executes through `ai-build`, consolidates locally, and delivers through PRs. Includes handlers and reference files.
- **`ai-run-orchestrator` agent** -- 10th agent (orchestrator role). Delegates to Build, Explorer, Verify, Review, and Guard subagents for autonomous backlog execution without human checkpoints after invocation.
- **`/ai-platform-audit` skill** -- verifies IDE platform support is genuinely wired, not just assumed. Checks hooks, skills, agents, and mirrors for Claude Code, GitHub Copilot, Codex, and Gemini CLI. Detects orphaned hooks, missing mirrors, and stale registrations.
- **`/ai-skill-evolve` skill** -- improves existing skills based on real project pain. Reads decision-store, LESSONS.md, instincts, and proposals to understand what actually hurts, evaluates skills against realistic test prompts, and grades quality.
- **`runbooks/handlers/dedup-check.md` (spec-092)** -- shared deduplication handler for all item-creating runbooks. Defines a Finding contract (`domain_label`, `title`, `severity`, `body`, plus optional `file_path`, `rule_id`, `symbol`, `package_name`). Implements a 3-level dedup cascade: check consolidated issues first, then individual issues, then create new items.
- **`work-item-audit` runbook** -- audits non-functional work items against repo reality before consolidation. Closes invalid noise, rewrites mixed items, runs weekly in the hygiene cycle before the consolidation runbook.
- **CONSTITUTION.md** -- new foundational governance document at `.ai-engineering/CONSTITUTION.md`. Replaces `project-identity.md` with a principles-first design: Identity, Mission, 8 Principles (Content Over Code, Gate Integrity, Single Source of Truth, Simplicity First, Verify Before Done, Fix Root Causes, Cross-Platform by Default, Autonomous Execution), 10 explicit Prohibitions, Quality Gates table, Boundaries, and Governance with semantic versioning. TEAM_MANAGED, never overwritten by framework updates.
- **`/ai-constitution` skill** -- new skill for generating and amending CONSTITUTION.md. Supports `generate` (auto-detect + interview), `update` (targeted section edits), and `amend` (formal version-bump process). Called by the installer governance phase and `/ai-onboard`.

### Changed
- **9 item-creating runbooks migrated to shared dedup handler (spec-092)** -- architecture-drift, code-quality, dependency-health, docs-freshness, feature-scanner, governance-drift, performance, security-scan, and wiring-scanner runbooks no longer contain inline dedup logic. Each now maps findings to the Finding contract and routes through `handlers/dedup-check.md`.
- **Consolidate runbook propagates domain labels (spec-092)** -- consolidated issues now carry the union of domain-specific labels from grouped originals (e.g., `tech-debt`, `architecture-drift`). Azure DevOps `System.Tags` updated similarly. Ensures consolidated issues are discoverable by the dedup handler.
- **`/ai-instinct` redesigned from `status|review` to listening + `--review` (spec-090 sub-003)** -- the skill no longer has a `status` mode. Default invocation activates passive listening; `--review` triggers extraction, enrichment, and proposal writing.
- **`/ai-learn` skill updated for LESSONS.md relocation (spec-090 sub-005)** -- all references to `contexts/team/lessons.md` updated to `.ai-engineering/LESSONS.md`.
- **`/ai-create` skill expanded** -- now scaffolds skills with `references/` directories alongside `handlers/` and `scripts/`.
- **Instincts state module v2 (spec-090 sub-002)** -- `src/ai_engineering/state/instincts.py` and hook library `_lib/instincts.py` rewritten for v2 schema. Removed `_select_context_items`, `needs_context_refresh`, `refresh_instinct_context`, `maybe_refresh_instinct_context`, and `instinct_context_path`. Removed `skillAgentPreferences` detection. Added `confidence_for_count`, `apply_confidence_decay`, `prune_low_confidence`, `_detect_skill_workflows`, and `_migrate_v1_to_v2`.
- **`InstinctMeta` model simplified (spec-090 sub-002)** -- removed `last_context_generated_at`, `pending_context_refresh`, and `context_max_age_hours` fields from Pydantic model.
- **Manifest registry updated** -- skill count 41 -> 44, agent count 9 -> 10. New skills (`ai-run`, `ai-platform-audit`, `ai-skill-evolve`) and agent (`run-orchestrator`) registered. Ownership `system` scope simplified (removed `learnings/`).
- **Sync script extended (spec-090 sub-005)** -- `sync_command_mirrors.py` now discovers and mirrors `references/` directories alongside `handlers/` and `scripts/`. Added `run-orchestrator` to `AGENT_METADATA`. Copilot-compatible skill count calculation fixed. Install template Codex surfaces (`hooks.json`, `config.toml`) now mirrored.
- **CLAUDE.md, AGENTS.md, GEMINI.md, copilot-instructions** -- agent table expanded with `run-orchestrator` row. Skill count updated to 44. Enterprise and Meta groups expanded with new skills. Effort table updated.
- **Audit hook Codex compatibility** -- `passthrough_stdin` in `_lib/audit.py` now skips stdout echo when `AIENG_HOOK_ENGINE=codex` to avoid Codex structured-output validation errors.
- **All IDE mirrors updated (spec-090 sub-005)** -- `.claude/`, `.codex/`, `.gemini/`, `.github/`, and template mirrors regenerated for all modified skills (`ai-instinct`, `ai-learn`, `ai-brainstorm`, `ai-commit`, `ai-create`, `ai-onboard`, `ai-pr`) and new skills/agents.
- **`project-identity.md` → `CONSTITUTION.md`** -- file relocated from `.ai-engineering/contexts/` to `.ai-engineering/` root to reflect its foundational status. Content redesigned from scratch (removed metadata tables derivable from `pyproject.toml`; added Principles and Prohibitions sections). All skill references, Step 0 protocol, IDE mirrors (Claude, Copilot, Gemini, Codex), and template project copies updated.
- **`ai-project-identity` → `ai-constitution`** -- skill renamed across all 8 directories (4 live IDE mirrors + 4 template copies). Context class name updated from `project-identity` to `constitution` in observability and state systems.

### Removed
- **`instincts/context.md` (spec-090 sub-002)** -- the generated context file is no longer used. Instincts are now consumed directly from `instincts.yml` v2 schema. Context refresh logic (`needs_context_refresh`, `refresh_instinct_context`, `maybe_refresh_instinct_context`) removed from both hook library and state module.
- **`consolidate.py` scripts (spec-090 sub-003)** -- deleted from all 4 IDE mirrors (`.claude/`, `.codex/`, `.gemini/`, `.github/`) and 4 template copies. The v1 consolidation summary script is replaced by the skill's built-in `--review` mode.
- **`contexts/team/lessons.md` content (spec-090 sub-001)** -- content moved to `.ai-engineering/LESSONS.md`. The file now contains only new lessons captured after the migration (autonomous orchestrator patterns).
- **Instincts v1 schema families** -- `toolSequences`, `errorRecoveries`, and `skillAgentPreferences` replaced by v2 families (`corrections`, `recoveries`, `workflows`). Migration path preserves high-evidence entries.

### Added
- **Label-sync infrastructure** -- canonical `.github/labels.yml` defines all labels (type, priority, severity, status, handoff, lifecycle, findings, protected, utility). GitHub Action (`label-sync.yml`) syncs labels on push to main using `EndBug/label-sync@v2.3.3` with SHA-pinned action.

### Changed
- **Label normalization** -- replaced colon-based labels (`type:bug`, `status:ready`, `handoff:ai-eng`) with hyphen-based (`bug`, `status-ready`, `handoff-ai-eng`) across all runbooks, skills, issue templates, and templates. GitHub does not allow colons in label names.
- **GitHub Projects v2 configuration** -- populated `manifest.yml` with real project board field IDs (status, priority, size, estimate, dates), status option IDs, and state mappings. Enables `/ai-board-sync` to move items across project columns.
- **Issue templates simplified** -- removed Size dropdown from bug/feature/task templates (moved to GitHub Projects custom fields). Added `p4-low` priority option to task template.
- **Native IDE directory architecture (spec-087)** -- eliminated the `.agents/` directory entirely; Codex content now lives in native `.codex/` with `hooks.json` and `config.toml`. Gemini hooks rewritten to official nested `matcher/hooks` format with `hooksConfig`. GitHub Copilot hooks added under `.github/hooks/`. Installer, sync script, and validator updated for the new structure.

### Changed
- **ai-eng update UX (spec-081)** -- the update command now presents an install-style preview in interactive terminals, explains protected files with structured reasons, and requires confirmation before applying writes while keeping JSON and non-TTY flows prompt-free.
- **Hook simplification and instinct learning (spec-080)** -- retained hook automation is now focused on `auto-format`, `strategic-compact`, `instinct-observe`, and `instinct-extract`, with project-local instinct artifacts under `.ai-engineering/instincts/` and no `cost-tracker`.

### Added
- **Codex/Copilot instruction parity (spec-080)** -- sync now generates live `.github/instructions/*.instructions.md` surfaces alongside template instructions, keeping language guidance aligned across installed projects and the dogfooded repo.

### Changed
- **Codex governance surfaces (spec-080)** -- instruction counts, provider tables, active integrations, and agent invocation guidance are now derived and mirrored consistently across `CLAUDE.md`, `AGENTS.md`, template instructions, and `.ai-engineering/README.md`.
- **Repo dogfooding config (spec-080)** -- `.ai-engineering/manifest.yml`, install state, and ownership map now model Codex as an active integration and cover project identity in readiness checks.
- **Skill status scanning (spec-080)** -- modern `.claude/` and `.agents/` skill directories only treat `SKILL.md` as executable, while legacy flat markdown scanning remains limited to `.ai-engineering/skills`.

### Fixed
- **Codex provider autodetect (spec-080)** -- installer discovery now recognizes `AGENTS.md` and `.agents/` surfaces as Codex integrations instead of reporting only Claude/Copilot.
- **Agent/skill taxonomy drift (spec-080)** -- `guard`, `explore`, and `simplify` guidance no longer advertises nonexistent slash skills; mirrors now point to direct dispatch where those capabilities are agent-only.
- **Mirror sync integrity (spec-080)** -- generated `AGENTS.md` preserves Claude-specific platform rows, source-of-truth counts, and cross-reference validation for templated skill paths.

### Added
- **Copilot Skills system (spec-077)** -- replaced `.github/prompts/*.prompt.md` (34 files) with native `.github/skills/ai-*/SKILL.md` directory structure (37 skills). Each skill now has its own directory mirroring `.claude/skills/` and `.agents/skills/`. Sync pipeline generates Copilot-native format directly instead of concatenated prompt files.
- **`STYLE_PRESETS.md` for `/ai-slides`** -- reusable style presets for HTML presentation generation.
- **`.ai-engineering/reviews/` directory** -- persistent storage for code review artifacts.

### Removed
- **`.github/prompts/` directory (spec-077)** -- 34 prompt.md files replaced by `.github/skills/` native format. Template mirrors also cleaned.
- **Autopilot sub-specs** -- removed stale `.ai-engineering/specs/autopilot/` (manifest + 8 sub-specs) from completed autopilot v2 execution.
- **`spec-066-hooks-relocation.md`** -- completed spec artifact cleaned up.
- **`health-history.json` + `test_health_history.py` (spec-068)** -- unused state file and its tests removed as part of state unification.
- **Health check signals** -- removed obsolete `health_check_signals` from `src/ai_engineering/lib/signals.py`.

### Changed
- **Sync script → skills output (spec-077)** -- `sync_command_mirrors.py` now generates `.github/skills/ai-*/SKILL.md` directories instead of `.github/prompts/*.prompt.md` files. Template mirrors updated accordingly.
- **Validator mirror sync** -- `mirror_sync.py` validates skills directories across all IDE trees instead of prompt file parity.
- **`test_template_prompt_parity.py` → `test_template_skill_parity.py`** -- renamed and rewritten to validate skill directory parity instead of prompt file byte-equality.
- **Autopilot v2 handlers** -- quality, deep-plan, implement, decompose, orchestrate, and deliver handlers updated across all 3 IDE mirrors (`.claude/`, `.github/`, `.agents/`) with improved parallel execution and convergence loop.
- **All 9 agent instructions updated** -- autopilot, build, explore, guard, guide, plan, review, simplify, verify agents refined for skills-based routing.
- **CODEOWNERS, CLAUDE.md, AGENTS.md, copilot-instructions.md** -- updated references for skills system.

### Fixed
- **`git init -b main` (spec-078)** -- all `git init` calls in installer (`detect.py`, `service.py`), CI workflows (`ci.yml`, `install-smoke.yml`), and test fixtures (`test_install_matrix.py`) now explicitly set default branch to `main`.

### Added
- **Install flow redesign (spec-064)** -- replaced 4 hostile free-text prompts with auto-detection + `questionary` checkbox wizard. Auto-detects stacks (13 markers), AI providers (claude_code, github_copilot), IDEs (.vscode, .idea), and VCS (git remote). Empty repos show wizard with nothing preselected. CLI flags (`--stack`, `--provider`, `--ide`, `--vcs`) skip wizard for automation. Removed CI/CD URL prompt from install.
- **Copilot subagent orchestration (spec-064)** -- full parity with Claude Code multi-agent delegation. 5 orchestrator agents (Autopilot, Build, Plan, Review, Verify) can now delegate to subagents via `agents` property, `handoffs` (guided transitions), and per-agent `hooks`. Sync pipeline injects Copilot-specific properties via `AGENT_METADATA` — canonical `.claude/` sources remain clean. Works across VS Code, CLI, and Coding Agent.
- **`docs/copilot-subagents.md`** -- comprehensive guide covering sync architecture, Copilot properties, usage examples for all 3 environments, capabilities matrix, and handoff chain diagram.
- **DEC-024** -- Copilot subagent orchestration via sync pipeline (architecture decision, active, high criticality).
- **`/ai-autopilot` skill (spec-063)** -- multi-spec autonomous orchestrator that splits large specs into focused sub-specs, executes sequentially with fresh-context agents, verifies anti-hallucination gates, and delivers via PR. 5 phase handlers (split, explore, execute, verify, pr) with `--resume` and `--no-watch` flags.
- **`ai-autopilot` agent** -- 9th agent (orchestrator role), read-only + bash tools, delegates all code changes to subagents.
- **DEC-023 governance override** -- autopilot invocation is approval for the full pipeline; internal gates are automatic with 2-failure stop.
- **ECC integration skills (spec-062)** -- 4 new skills: `/ai-slides` (HTML presentations with style presets, PPT conversion), `/ai-media` (AI media generation via fal.ai), `/ai-video-editing` (FFmpeg + Remotion pipeline), `/ai-eval` (eval-driven development with pass@k metrics). Total skills: 37.
- **Test skill handlers** -- `handlers/e2e.md` (end-to-end testing patterns) and `handlers/tdd.md` (RED-GREEN-REFACTOR cycle) added to `/ai-test`.
- **Write skill handlers** -- `handlers/investor-outreach.md` and `handlers/x-api.md` added to `/ai-write`.
- **Framework contexts** -- 8 new context files: `api-design.md`, `backend-patterns.md`, `bun.md`, `claude-api.md`, `mcp-sdk.md`, `nextjs.md`, `universal.md` (languages), `mcp-integrations.md` (team).
- **Strategic compact hook** -- `scripts/hooks/strategic-compact.py` with Claude Code `Edit|Write|MultiEdit` hook for strategic context management during long sessions.

### Removed
- **`TEST_SCOPE_RULES` system (spec-069)** -- deleted manual test-selection engine (760 LOC, 25 rules), `check_test_mapping.py` integrity script, and all consumers. CI now runs full suite unconditionally per tier with `paths-ignore` for docs-only changes. Suite speed (24s unit, 5m integration) makes selective filtering unnecessary.

### Changed
- **Hooks relocated (spec-066)** -- moved `scripts/hooks/` to `.ai-engineering/scripts/hooks/` for both templates and dogfooding. Updated all path references in settings.json, hooks.json, shell/PowerShell dirname navigation, installer, and tests. Added `_migrate_hooks_dir()` to updater for automatic migration of existing projects.
- **Sync script (`sync_command_mirrors.py`)** -- extended `AgentMeta` dataclass with `copilot_agents`, `copilot_handoffs`, `copilot_hooks` fields; `generate_copilot_agent()` serializes new frontmatter properties for 5 orchestrator agents.
- **Canonical agent instructions** -- replaced `Dispatch Agent(X)` syntax with "Use the X agent" pattern in `ai-autopilot.md` and `ai-build.md`; added "Subagent Orchestration" section to autopilot; added Guard/Explorer delegation references to Build.
- **Copilot instructions** -- added "Subagent Orchestration" section to `.github/copilot-instructions.md` with orchestrator delegation table.
- **Manifest registry** -- skill count 32 -> 37, agent count 8 -> 9, all new skills registered with types and tags.
- **Skill frontmatter validator** -- added `mcp` and `skills` as valid keys in `requires` block.
- **All IDE mirrors updated** -- `.claude/`, `.github/`, `.agents/`, and template mirrors regenerated for all new and modified skills.

### Fixed
- **Autopilot skill cross-platform path bug** -- `.claude/skills/ai-pr/handlers/watch.md` handler path in `phase-pr.md` replaced with `.claude/skills/ai-pr/SKILL.md step 14` (handler paths aren't translated by sync regex).
- **Dispatch skill agent names** -- normalized generic "subagent" references to canonical agent names (`ai-build`, `ai-verify`, `ai-guard`) for consistent cross-platform translation.
- **Mirror sync: 46 handler files added to `.agents/` mirrors** -- write (4), review (8), debug (8), create (3), solution-intent (3) handlers were missing from Codex/Gemini mirrors (root + template). Routing tables referenced nonexistent files.
- **Skill count synced to 32 across all instruction files** -- CLAUDE.md, AGENTS.md, copilot-instructions.md, and template manifest updated. `ai-instinct` added to Meta group and Effort Levels table (max: 8 -> 9).
- **Handler separators in sync script** -- `sync_command_mirrors.py` now inserts `---` between handler sections in concatenated `.prompt.md` files, matching the existing `ai-debug` convention.
- **`deployment-patterns.md` mirror** -- canonical governance context file was missing its template mirror.

### Added
- **`test_handler_routing_completeness`** -- 90 parametrized tests verifying every handler referenced in SKILL.md routing tables exists on disk across all 4 IDE mirror trees.
- **`test_template_prompt_parity`** -- 35 tests ensuring `.github/prompts/` and template prompt files stay byte-for-byte identical.

### Fixed
- **CI false positives eliminated** — Dependabot PRs that change workflow YAML now trigger full CI (paths-filter expanded). Snyk job reports `skipped` instead of vacuous `success` when token is absent. Gate Trailer verification checks ALL non-merge PR commits (not just HEAD). SonarCloud fails when zero coverage reports exist. Semgrep skip ratio capped at 50%.
- **Install Smoke false positives eliminated** — `ai-eng doctor` now exits 0 (ok), 1 (fail), or 2 (warnings only) instead of always 0. `ai-eng version` output validated against expected pattern. Doctor JSON output parsed and asserted. Git config sets `init.defaultBranch main`.

### Added
- **`--non-interactive` flag for `ai-eng install`** — suppresses all 5 interactive prompts, uses defaults. Required for CI smoke tests.
- **Cross-platform Install Smoke** — workflow now runs on ubuntu, windows, and macos (was ubuntu-only).
- **`DoctorReport.has_warnings` property** — True when warnings exist with no failures.
- **Error boundary expansion** — `json.JSONDecodeError` and `pydantic.ValidationError` now caught by CLI error boundary for clean error messages.

### Added
- **CI/CD standards URL in manifest** -- new `cicd.standards_url` field in `manifest.yml` allows teams to reference their CI/CD documentation. `/ai-pipeline generate` reads this URL to produce compliant pipelines; falls back to AI best practices when unset.

### Removed
- **Programmatic pipeline generator** -- removed `installer/cicd.py`, `pipeline/` module (compliance, injector), and `templates/pipeline/` directory. Pipeline generation is now fully AI-driven via `/ai-pipeline`.
- **`ai-eng cicd regenerate` command** -- replaced by `/ai-pipeline generate` as the single entry point for pipeline creation.
- **`ai-eng maintenance pipeline-compliance`** -- compliance checking delegated to `/ai-pipeline validate`.
- **`--no-cicd` flag on `ai-eng vcs set-provider`** -- no longer needed since pipelines aren't auto-generated.
- **Pipeline auto-generation during install** -- `ai-eng install` no longer generates CI/CD pipelines. Users invoke `/ai-pipeline` when ready.

### Added
- **GitHub Copilot hooks parity** — migrated `.github/hooks/hooks.json` from broken flat-array format to Copilot's native `{ version: 1, hooks: { eventType: [...] } }` schema with all 6 hook types: `sessionStart`, `sessionEnd`, `userPromptSubmitted`, `preToolUse`, `postToolUse`, `errorOccurred`.
- **Copilot preToolUse deny-list** — new `copilot-deny.sh` script enforces the same 13 dangerous-operation patterns blocked by Claude Code's `settings.json` (force push, `rm -rf *`, `--no-verify`, etc.) via Copilot's native `preToolUse` hook with `permissionDecision: "deny"` output.
- **Copilot telemetry scripts** — 5 new hook scripts (`copilot-skill.sh`, `copilot-agent.sh`, `copilot-session-start.sh`, `copilot-session-end.sh`, `copilot-error.sh`) emit NDJSON events to `audit-log.ndjson` matching existing Claude telemetry format. Each has a PowerShell fail-open stub.
- **Codex handler parity** — adapted 6 missing handler files for `.agents/skills/` (create: 3, solution-intent: 3) from Claude sources with provider-neutral paths (zero `.claude/` references).
- **Manifest ownership expansion** — `ownership.framework` now includes `.github/agents/**`, `.github/prompts/**`, `.github/hooks/**`, `.github/copilot-instructions.md`, and `.agents/**`.

### Changed
- **copilot-instructions.md** — Observability section now lists all 6 Copilot-native camelCase hook event types instead of old `post_tool_call`/`session_end` naming.

### Added
- **Watch & fix loop for /ai-pr** — step 14 now autonomously monitors PR until merge: diagnoses and fixes failing CI checks, resolves merge conflicts via rebase, and handles review comments (team/org-internal bot = autonomous, external = user confirmation). Polls every 1 min (active) or 3 min (passive). Escalates after 3 failed fix attempts. Full GitHub and Azure DevOps VCS support. New `handlers/watch.md` handler with 7-step procedure.
- **Work items integration** — expanded `manifest.yml` `work_items` section with provider-specific config (Azure DevOps `area_path`, GitHub `team_label`), hierarchy rules (`never_close` for features, `close_on_pr` for user stories/tasks/bugs), and spec frontmatter `refs` for traceability from specs to work items.
- **Sprint review skill** — new `/ai-sprint-review` skill (31st skill) that gathers sprint data from work items and git, generates a python-pptx script with the ai-engineering dark-mode brand, and produces a PowerPoint slide deck for stakeholders.
- **PR work item linking** — `/ai-pr` now reads spec frontmatter `refs` and adds hierarchy-aware work item references to PR descriptions (closes user stories/tasks/bugs, mentions features without closing).
- **Brainstorm work item context** — `/ai-brainstorm` can accept a work item ID to fetch hierarchy (Feature > User Story > Task) from Azure DevOps or GitHub Issues, pre-filling spec refs and reducing interrogation questions.
- **Manifest enforcement** — pre-conditions added to `/ai-sprint`, `/ai-standup`, `/ai-commit`, and `/ai-write` docs handler requiring manifest `work_items` and `documentation` config reads before acting.
- **Recursive README updates** — `documentation.auto_update.readme: true` now explicitly scans ALL README*.md files recursively, updating each in context of its directory.

### Fixed
- **Skill telemetry hook** — replaced `PostToolUse(Skill)` hook with `UserPromptSubmit(/ai-*)` to capture slash command invocations. `PostToolUse(Skill)` never fired because Claude Code expands skills as prompts without calling the Skill tool.
- **Installer copilot template** — removed stale `("copilot", ".github/copilot")` tree mapping from `templates.py` after the `copilot/` template directory was deleted in spec-055.

### Added
- **Dev-setup scripts** — `scripts/dev-setup.sh` (bash) and `scripts/dev-setup.ps1` (PowerShell) for one-command editable install of `ai-eng` as a global tool via `uv tool install`.
- **CI Result gate job** — context-aware `ci-result` aggregator in `ci.yml` that becomes the sole required Branch Protection check. Categorizes jobs as always-required, code-conditional, PR-only, or optional — unblocking docs-only PRs, Dependabot PRs, and external contributions (DEC-054-06).
- **Dependabot auto-lock workflow** — `dependabot-auto-lock.yml` regenerates `uv.lock` when Dependabot updates `pyproject.toml`, eliminating manual lock-file maintenance.
- **CICD standards expansion** — 7 new policy sections in `cicd/core.md`: action version pinning, Dependabot contract, Azure Pipelines standards, reusable components contract, environment protection, concurrency/performance, and required check strategy.
- **Sprint review presentation** — `generate_sprint_review.py` produces a 12-slide dark-mode `.pptx` covering Feb 16 - Mar 16, 2026 sprint (architecture v3, IDE mirrors, observability, security, testing, CI/CD, quality metrics, governance surface, risks, and next sprint).
- **Telemetry hooks** — 4 cross-platform scripts (`telemetry-session.sh/ps1`, `telemetry-skill.sh/ps1`) emit `session_end` and `skill_invoked` events automatically via Claude Code `PostToolUse(Skill)` and `Stop` hooks.
- **Guard telemetry** — `guard_advisory`, `guard_gate`, and `guard_drift` event emitters in `audit.py` with matching aggregators in `signals.py` for guard-mode observability.
- **Common installer templates** — `.gitleaks.toml` and `.semgrep.yml` now deploy to every target project regardless of AI provider; `scripts/hooks/` deploys observability hooks for all providers.
- **Project scaffolding templates** — `CODEOWNERS`, `dependabot.yml`, SonarQube MCP instructions, and VCS hook configs added to the project template set.
- **Telemetry canary test** — integration test verifying end-to-end hook telemetry emission.
- **Audit auto-enrichment** — events now auto-attach `spec_id` and `stack` from project context, plus `duration_ms` on gate and scan events, eliminating manual field wiring.
- **Agent telemetry hooks** — `telemetry-agent.sh/ps1` scripts for agent dispatch event emission.
- **Gate duration tracking** — `run_gate()` now measures and emits `duration_ms` on every gate event for performance observability.
- **Validate sync mode** — `ai-eng validate --mode sync` checks all mirrors are up-to-date (moved from separate `ai-eng sync --check`).

### Changed
- **Pipeline skill v2** — comprehensive rewrite with GitHub Actions (12 sections: CI result gate, reusable workflows, composite actions, SHA pinning, concurrency, matrix, caching, environments, merge queue, badges, Dependabot) and Azure Pipelines (11 sections: template composition, manager pattern, variable groups, KeyVault, environment gates, deployment strategies, SonarCloud, artifact promotion, branch-conditional deployment, self-hosted agents) at full parity.
- **Dependabot config** — added `commit-message.prefix` for conventional commits (`chore(deps)`, `chore(deps-dev)`, `ci(deps)`).
- **Installer template maps** — removed legacy Copilot instruction file maps, added `_COMMON_FILE_MAPS` and `_COMMON_TREE_MAPS` for provider-agnostic deployment, moved Copilot subtrees to tree maps.
- **Observe dashboard** — guard advisory and drift metrics added to the AI dashboard mode.
- **Evolve skill** — updated across all IDE mirrors (Claude, Copilot, Agents).
- **Instruction files** — added Observability section to `CLAUDE.md` and `copilot-instructions.md` documenting automatic telemetry hooks.
- **Checkpoint command removed** — `ai-eng checkpoint` CLI subgroup deleted; checkpoint state file removed from defaults.
- **Observe simplified** — removed `session_metrics_from` and `checkpoint_status` aggregators; observe modes streamlined to use direct event queries.
- **Audit emitters consolidated** — `emit_session_event` removed; replaced by richer auto-enriched event model with `_enrich()` helper.
- **Agent/skill mirrors updated** — all 8 agents and governance-related skills refreshed across Claude, Copilot, and Agents IDE mirrors.

### Removed
- **Legacy evals directory** — `templates/.ai-engineering/evals/` (README.md, benchmarks, registry.json) removed.
- **Legacy semgrep location** — `templates/.semgrep.yml` relocated to `templates/project/.semgrep.yml`.
- **Checkpoint CLI** — `ai-eng checkpoint save/load/status` commands removed (session-checkpoint.json deleted).

### Added — Architecture v3 (spec-051)
- **3 new agents** — guard (proactive governance), guide (developer growth), operate (SRE/runbooks).
- **7 new skills** — guard, dispatch, guide, onboard, evolve, ops, lifecycle.
- **Self-improvement mechanism** — evolve skill analyzes audit-log and proposes improvements.
- **Guard integration** — guard.advise runs as post-edit validation step in build agent.
- **Feature gap reviewer** — verify.gap `--framework` mode audits promise vs reality.
- **Agent-model standard** — new governance standard defining dispatch protocol and context handoff.

### Changed — Architecture v3 (spec-051)
- **Agent renames** — scan→verify, release→ship (clearer developer communication).
- **Skill renames** — build→code, db→schema, cicd→pipeline, a11y→accessibility, feature-gap→gap, code-simplifier→simplify, perf→performance, docs→document, observe→dashboard, product-contract→contract, work-item→triage.
- **Skill merges** — create+delete merged into lifecycle.
- **5 stub skills expanded** — security (58→216L), quality (45→175L), governance (48→153L), build (45→257L), perf (46→150L).
- **Explain skill reassigned** — from orphan to guide agent (primary owner).
- **All 5 runbooks** — assigned `owner: operate` in frontmatter (consolidated from 13).
- **Agent count**: 7→10. **Skill count**: 35→40.
- **IDE adapters** — all Claude commands, Copilot prompts, and Copilot agents renamed to match new skill/agent names. 7 new command files created.
- **Template mirror** — full sync of 10 agents, 40 skills, 5 runbooks, standards, and IDE adapters to `src/ai_engineering/templates/`.
- **Contracts rewritten** — framework-contract.md (10 agents, dispatch schema, guard integration, evolve loop) and product-contract.md (v0.3.0, updated roadmap and KPIs).

### Fixed
- **Dependabot CI gate** — exempted `dependabot[bot]` from `verify-gate-trailers` check; Dependabot creates commits server-side and cannot satisfy the local hook trailer requirement (DEC-020).
- **Dependabot PR noise** — grouped all dependency updates by ecosystem (pip, github-actions) to consolidate ~7 individual PRs into max 2 per week.

### Fixed — Architecture v3 (spec-051)
- **Sonar BLOCKER** — path traversal validation in checkpoint.py (S5145).
- **CI manifest check** — support `governance_surface` nested structure.
- **Test mapping** — 3 unmapped test files added to scope rules.
- **Instruction file counts** — updated "Skills (35)" → "(40)" and "Agents (7)" → "(10)" in all 8 IDE instruction files.

### Changed
- **Release zero-rebuild** — `release.yml` no longer rebuilds the package; instead downloads the CI-validated `dist/` artifact and publishes it directly to PyPI and GitHub Releases, guaranteeing bit-identical output between CI and release.
- **CI artifact retention** — `dist/` artifact in CI now has `retention-days: 5` to ensure availability for release workflow.
- **Release CI verification** — new `verify-ci` job in release workflow checks CI status with retry/backoff before proceeding (handles race condition when tag pushed before CI finishes).
- **Observe Rich dashboards** — all 5 `ai-eng observe` modes now render with Rich-formatted output (progress bars, score badges, color-coded metrics, section headers) instead of raw markdown strings.
- **Observe dual-output** — `ai-eng observe <mode> --json` outputs structured JSON via SuccessEnvelope with HATEOAS next actions; human output goes to stderr per CLIG.
- **Observe data-first architecture** — mode functions return structured dicts enabling both JSON and Rich rendering from the same data.
- **4 new cli_ui primitives** — `section()`, `progress_bar()`, `score_badge()`, `metric_table()` added to the shared CLI output module for dashboard rendering.
- **Slim root instructions** — deduplicated CLAUDE.md (-64%), AGENTS.md (-53%), and copilot-instructions.md (-47%); all duplicated content now lives in `framework-contract.md` or `product-contract.md`.
- **On-demand contract loading** — plan agent, spec skill, and PR skill now explicitly read product/framework contracts when needed.
- **Validator pointer format** — counter-accuracy and instruction-consistency validators support pointer format and use `product-contract.md` as canonical source.

### Added
- **Snyk optional CI/CD integration** — new `snyk-security` job in CI workflow runs `snyk test` (dependency vulnerabilities), `snyk code test` (SAST), and `snyk monitor` (continuous monitoring on main). All steps conditional on `SNYK_TOKEN` secret; non-gating (`continue-on-error: true`). Registered as optional tool in `manifest.yml` and documented in CI/CD standards and security skill.
- **Skill & agent telemetry** — cross-IDE usage tracking via `ai-eng signals emit skill_invoked` and `agent_dispatched` directives in all 35 skills and 7 agents; new `skill_usage_from()` and `agent_dispatch_from()` aggregators; observe team/ai dashboards now show Skill Usage, Agent Dispatch, and Skill & Agent Efficiency sections.
- **Emit infrastructure** — gate events now include `fixable_failures` field tracking auto-fixable check failures (ruff-format, ruff-lint); `noise_ratio_from()` aggregator computes noise ratio from gate history.
- **Enriched session events** — checkpoint save now passes spec ID, task progress, and skills context to `emit_session_event()` instead of bare `checkpoint_saved=True`.
- **Team dashboard expansion** — Token Economy and Noise Ratio sections show session token usage and gate failure quality metrics.
- **AI dashboard enrichment** — Context Efficiency now shows average tokens per session.
- **Health score: Gate signal quality** — noise ratio (inverse) added as optional health component; high noise lowers health score.
- **Observe enrichment phase 2** — Security Posture, Test Confidence, and enriched SonarCloud sections in engineer and health dashboards with multi-source fallback chains (SonarCloud → local tools → defaults).
- **SonarCloud measures expansion** — `query_sonar_measures()` calls `/api/measures/component` for coverage, complexity, duplication, and vulnerability metrics with module-level caching.
- **Test confidence with fallback** — `test_confidence_metrics()` resolves coverage from SonarCloud → `coverage.json` → `test_scope` mapping → defaults.
- **Security posture with fallback** — `security_posture_metrics()` resolves vulnerabilities from SonarCloud → `pip-audit` → defaults.
- **Session emitter wired** — checkpoint save now emits `session_metric` audit events automatically.
- **Health trend tracking** — `observe health` persists weekly snapshots to `state/health-history.json` (rolling 12 entries) and shows ↑↓→ direction indicators.
- **Smart actions with score gain** — `observe health` replaces hardcoded actions with dynamic recommendations based on weakest components, showing estimated point gains.
- **AI self-optimization hints** — `observe ai` detects patterns (low decision reuse, high gate failures, missing checkpoints) and surfaces actionable suggestions.

### Fixed
- **Install UX: VCS alias** — `ai-eng install --vcs azdo` now accepted as shorthand for `azure_devops`; normalizes internally, displays `azdo` in output.
- **Install UX: clean output** — removed inline branch policy guide text from install output; guide accessible via `ai-eng guide`.
- **Install UX: platform filtering** — platform setup no longer offers the opposite VCS provider (e.g., Azure DevOps when GitHub is selected).
- **Install UX: Sonar URL normalization** — Sonar token validation now strips path from user-entered URLs before API call; helpful error on JSON parse failure.
- **SonarCloud token resolution** — `_resolve_sonar_token()` now chains env var → OS keyring (`CredentialService`) → None; previously `query_sonar_quality_gate()` checked config flag but never retrieved the stored token.

- **Observe enrichment phase 1** — 8 new signal aggregators (`code_quality_score`, `decision_health`, `adoption_rate`, `lead_time`, `change_failure_rate`, `session_recovery_rate`, `dependency_health`, `multi_variable_health`) in `lib/signals.py` expand dashboards with data computable from existing sources.
- **VCS context in audit events** — `vcs/repo_context.py` and `git/context.py` add branch, commit SHA, repo URL, and provider to every `AuditEntry` automatically via `_emit()`.
- **Workflow CLI commands** — `ai-eng workflow commit`, `ai-eng workflow pr`, and `ai-eng workflow pr-only` registered as CLI subcommands.
- **Expanded observe dashboards** — engineer, team, AI, DORA, and health dashboards enriched with Code Quality, Decision Health, Adoption, Lead Time, Change Failure Rate, and Session Recovery panels.
- **Spec helpers in `lib/parsing.py`** — `_next_spec_number()` and `_slugify()` moved to shared parsing module for reuse.

### Changed
- **Release orchestrator standardized** — replaced internal `_log_audit_event()` with standard `emit_deploy_event()` for consistent audit trail.

### Removed
- **`ai-eng spec save` CLI command** — replaced by LLM-driven spec creation that preserves rich planning content (Risks, Verification, Architecture sections).

- **Squash-merge detection in cleanup** — cleanup skill v4.1.0 now detects branches merged via squash using `git cherry -v`; local branches are properly deleted after PR squash-merge instead of accumulating as "Local-only development".

### Removed
- **Totals section from cleanup report** — redundant with Branch Detail table; cleanup report now shows only the per-branch table.

### Added
- **SonarCloud Quality Gate integration** — `sonar.qualitygate.wait=true` in `sonar-project.properties` as universal gate; scanner polls QG and fails CI if it doesn't pass. Works identically on GitHub Actions and Azure Pipelines.
- **SonarCloud CI job** — new `sonarcloud` job in `ci.yml` with fork guard, downloads per-tier coverage reports (unit/integration/e2e), and blocks build on QG failure.
- **Coverage export per test tier** — unit, integration, and e2e jobs now generate individual Cobertura XML reports (`coverage-unit.xml`, `coverage-integration.xml`, `coverage-e2e.xml`) uploaded as artifacts for SonarCloud consumption.
- **SonarCloud API quality gate check** — `query_sonar_quality_gate()` in `policy/checks/sonar.py` queries SonarCloud Web API for QG status when scanner unavailable; used by pre-push gate (advisory) and observe dashboard.
- **Sonar metrics in engineer dashboard** — `ai-eng observe engineer` shows SonarCloud Quality Gate status, new code coverage, and condition count (silent-skip when unconfigured).
- **`sonar-project.properties` at repo root** — project configured for `arcasilesgroup/ai-engineering` org on SonarCloud.

### Changed
- **Coverage threshold aligned to SonarCloud Quality Gate** — lowered from 90% to 80% across all governance files, standards, IDE configs, templates, and presentation assets. Source of truth: `standards/framework/quality/core.md`.
- **Branch protection updated** — removed defunct "Coverage Gate" required status check, added "SonarCloud" as required check on `main`.
- **Migrated deprecated GitHub Action** — `SonarSource/sonarcloud-github-action@v3` replaced with unified `SonarSource/sonarqube-scan-action@v4` for both SonarCloud and SonarQube (D038-003).
- **Removed redundant Coverage Gate job** — tests no longer re-run solely for coverage; each tier generates its own report.
- **SonarCloud blocks build** — `sonarcloud` job added to `build.needs` so Quality Gate failure prevents package build.
- **Properties template expanded** — `sonar-project.properties` template now includes `sonar.qualitygate.wait`, `sonar.qualitygate.timeout`, stack-aware coverage paths (Python/dotnet/nextjs), sources, tests, and exclusions.
- **CI/CD generation includes coverage steps** — `_render_github_ci` and `_render_azure_ci` generate coverage report commands per stack when Sonar is configured.

### Fixed
- **CI actionlint SC2012** — replaced `ls coverage-*.xml` with `find` in SonarCloud job's coverage merge step to satisfy shellcheck.

### Changed
- **Branch cleanup now handles squash-merged branches** — `ai-eng maintenance branch-cleanup` detects branches whose remote tracking ref is `[gone]`, verifies they have no unmerged changes via `git diff`, and safely deletes them. Branches with divergent content are skipped with a clear reason.
- **Governance simplification** — removed `learnings.md`, `sources.lock.json`, and legacy Claude/Copilot command files (`cleanup.md`, `commit.md`, `pr.md`) from both canonical and template paths; streamlined `manifest.yml`, `ownership-map.json`, and state defaults accordingly.
- **Skills service refactored** — simplified `skills/service.py` and `cli_commands/skills.py`, removing ~450 lines of unused maintenance and remote-source logic.
- **State models trimmed** — removed obsolete fields from `state/models.py` and `state/defaults.py` (sources lock, learnings references).
- **PR skill v2.0.0** — expanded `/pr` workflow with documentation gate (CHANGELOG, README, product-contract auto-update), spec reset integration, and structured PR description format.
- **Commit skill updated** — added spec-aware commit message format guidance.
- **Cleanup skill updated** — removed spec-reset responsibility (now handled by `/pr`).
- **Presentation assets refreshed** — updated SVGs and speech script to reflect current architecture.

### Removed
- **`learnings.md`** — project learnings file removed from context layer (both canonical and templates).
- **`sources.lock.json`** — remote skill source tracking removed from state layer.
- **Legacy IDE command files** — `.claude/commands/{cleanup,commit,pr}.md` and `.github/prompts/{cleanup,commit,pr}.prompt.md` removed (slash commands via `/ai-<name>` are the canonical path).

### Added
- **`product-contract` skill** — new skill (`/ai-product-contract`) for maintaining product contract documents in sync mode; includes Claude command, Copilot prompt, and Codex agent adaptors.
- **`ai-eng work-item sync` CLI** — syncs specs to external work items (GitHub Issues / Azure DevOps Boards) via new `work_items` service module.
- **VCS issue operations** — `VcsProvider` protocol extended with `create_issue`, `find_issue`, `close_issue`, and `link_issue_to_pr` methods; GitHub and Azure DevOps implementations included.
- **Explain analysis playbook** — reference document (`skills/explain/references/analysis-playbook.md`) for structured code analysis.
- **Solution intent doc** — `docs/solution-intent.md` architectural documentation.
- **Work-item backfill scripts** — `scripts/work_items_backfill.py` and validation script for bulk sync.

### Changed
- **Explain skill v2.0.0** — rewritten from Feynman-style to engineer-grade technical explanations with ASCII diagrams, execution traces, and complexity analysis; scope changed from read-write to read-only.
- **Product contract expanded** — comprehensive update to `.ai-engineering/context/product/product-contract.md` with extended functional requirements, integration details, and KPIs.
- **Framework contract updated** — governance surface and framework-managed paths refreshed.
- **Manifest expanded** — new `work-item` CLI command registered, product-contract skill added to governance surface.
- **Executor runbook enriched** — extended with detailed dispatch and coordination procedures.
- **PR review runbook expanded** — added structured review criteria and automation hooks.
- **GitHub issue templates improved** — bug, feature, and task forms refined with better field definitions.
- **PR template extended** — additional checklist items for product-contract and work-item checks.
- **Template sync** — all project/installer templates synchronized with canonical skill definitions.

### Added
- **Codex/Gemini platform adaptors** — 41 adaptor files (`.agents/skills/*/SKILL.md`) pointing to canonical skill/agent definitions; 7 agent adaptors use `-agent` suffix to avoid name collisions.
- **Automation runbooks** — 5 operational runbooks (`.ai-engineering/runbooks/*.md`): code-simplifier, dependency-upgrade, governance-drift-repair, incident-response, security-incident. Recurring automation moved to GitHub Agentic Workflows.
- **GitHub issue/PR templates** — bug, feature, task issue forms (`.github/ISSUE_TEMPLATE/*.yml`) and PR template (`.github/pull_request_template.md`); blank issues disabled.
- **VCS-aware installer** — `copy_project_templates()` accepts `vcs_provider` parameter; GitHub platform copies issue/PR templates automatically.
- **Issue Definition Standard** — `work-item` skill extended with required fields, priority mapping (P0→p1-critical), size guide (S/M/L/XL), and spec URL format.
- **Platform Adaptors + Runbooks in AGENTS.md** — new sections documenting adaptor paths/counts and runbook layers/schedules.
- **Manifest governance surface** — `runbooks/**` framework-managed, `.agents/**` + GitHub templates external-framework-managed, `issue_standard` schema.

### Changed
- **Agent/skill shared-rule normalization** — `plan`, `observe`, and `write/docs` now use canonical shared rules in skills (`PLAN-*`, `OBS-*`, `DOC-*`) with agent contracts referencing rules instead of duplicating procedures.
- **Plan no-execution enforcement** — `/ai-plan` contract now explicitly maps to `PLAN-B1` and requires handoff to `/ai-execute` for execution.
- **Copilot plan agent metadata alignment** — `Plan` agent description synchronized to advisory-planning semantics across GitHub and project templates.
- **PR description format** — `build_pr_description()` now generates What/Why/How/Checklist/Stats sections (matching PR #91 convention) instead of the old Spec/Changes format. Reads `spec.md` sections (Problem, Solution) to auto-populate What and Why.
- **Archive-aware spec URLs** — `_build_spec_url()` checks both active (`specs/{slug}/`) and archived (`specs/archive/{slug}/`) paths on disk; URLs stay valid after spec-reset archives the directory.
- **Spec lifecycle closure** — `done.md` created for specs 035 and 036; both archived via spec-reset; `_active.md` cleared.
- **PR workflow upsert hardening** — `/pr` and `/pr --only` now use deterministic create-or-update behavior with existing-PR detection, append-only body extension (`## Additional Changes`), and file-backed body transport in provider implementations.

### Added
- **Feature-gap wiring detection** — `feature-gap` skill (v1.1.0) extended with step 5.5 to detect disconnected implementations: exported-but-never-imported functions, unregistered endpoints/handlers/CLI commands, and orphaned modules. New "Disconnected" category and Wiring Matrix output section.
- **Scan agent wiring thresholds** — `scan` agent feature-gap mode now covers wiring gaps; threshold table adds ">5 unwired exports" as critical.

### Added
- **`ai-eng spec` CLI commands** — `verify` (auto-correct task counters), `catalog` (regenerate `_catalog.md`), `list` (show active spec with progress), `compact` (prune old archived specs).
- **`ai-eng decision record`** — dual-write protocol: persists new decisions to `decision-store.json` AND `audit-log.ndjson` in a single CLI command.
- **Shared frontmatter parser** — `lib/parsing.py` with `parse_frontmatter()` and `count_checkboxes()` as single source of truth, replacing duplicated inline parsers.
- **Spec `_catalog.md`** — auto-generated catalog of all archived specs with tag index.
- **`StateService.save_decisions()`** — convenience method for writing decision store.

### Changed
- **Spec closure normalization** — `done.md` is now mandatory for spec completion; `completed==total` alone produces a warning, not closure.
- **Validator regex fix** — `manifest_coherence.py` handles unquoted `null`/`none`/`~` in `_active.md` and looks up specs in both `context/specs/` and `context/specs/archive/`.
- **Spec skill enriched frontmatter** — scaffold now includes `size`, `tags`, `branch`, `pipeline`, `decisions` fields.
- **Commit skill updated** — `ai-eng spec verify` runs before each commit.
- **PR skill updated** — `ai-eng spec verify` + `ai-eng spec catalog` run at PR creation.
- **Cleanup skill updated** — `ai-eng spec compact --dry-run` runs during cleanup flow.
- **`standards/framework/core.md` expanded** — documents enriched frontmatter schema and new CLI commands.
- **Mirror sync** — 84 mirror files synchronized (Claude commands, Copilot prompts, Copilot agents, governance templates); fixed pre-existing template desyncs.

### Added
- **`execute` agent** — reads approved plan, dispatches specialized agents, coordinates execution, checkpoints progress, and reports results.
- **`plan` skill** — standalone planning skill (`/ai-plan`) with input classification, pipeline strategy, and spec creation.
- **`/ai-plan` and `/ai-execute` command contract** — plan pipeline (classify → discover → risk → spec → execution plan → STOP) and execute dispatcher documented in CLAUDE.md.
- **Audit prompt catalog** — `.ai-engineering/references/audit-prompt-catalog.md` reference for structured audit prompts.
- **State service** — `state/service.py` centralized state management module.
- **`doctor/models.py`** — extracted `CheckResult`, `CheckStatus`, `DoctorReport` from `doctor/service.py` to break circular imports between doctor modules.
- **`.gitattributes`** — LF line-ending enforcement for `.sh`, `.py`, `.yml`, `.yaml`, `.md`, `.json` files (cross-OS reliability).
- **CI maintenance cron** — `.github/workflows/maintenance.yml` runs `ai-eng maintenance all` weekly (Monday 06:00 UTC).
- **SSRF semgrep rule** — `ssrf-request` rule in `.semgrep.yml` detects `requests.$METHOD($URL)` with non-literal URLs (CWE-918).

### Changed
- **Doctor service refactored** — monolithic `doctor/service.py` decomposed into 8 focused check modules (`doctor/checks/`): tools, hooks, layout, state_files, venv, branch_policy, readiness, version_check.
- **Gates refactored** — monolithic `policy/gates.py` decomposed into 5 check modules (`policy/checks/`): branch_protection, commit_msg, risk, sonar, stack_runner.
- **Validator refactored** — monolithic `validator/service.py` decomposed into shared utilities (`_shared.py`) and 7 category modules (`validator/categories/`): counter_accuracy, cross_references, file_existence, instruction_consistency, manifest_coherence, mirror_sync, skill_frontmatter.
- **CLI commands updated** — minor improvements across cicd, decisions, gate, guide, maintenance, signals, vcs command modules and cli_ui.
- **CLAUDE.md** — skills 33→34 (added `plan`), agents 6→7 (added `execute`), expanded command contract.
- **Plan agent updated** — refined purpose to planning pipeline that STOPS before execution.
- **README.md + GEMINI.md synced to v3** — 34 skills, 7 agents, 37 slash commands, updated agent table and skill list.
- **Template mirrors synced** — `manifest.yml` and `README.md` templates match canonical (7 agents, 34 skills).
- **Governance skill CLI references fixed** — `ai-eng integrity` → `ai-eng validate --category integrity`.
- **Validator `CheckStatus` renamed to `IntegrityStatus`** — resolves naming collision with `doctor/models.py::CheckStatus`.
- **Mirror sync expanded** — `mirror_sync.py` now covers root-level `manifest.yml` and `README.md` (64 mirror pairs total).
- **Tool-availability consolidated** — `doctor/checks/tools.py` delegates to `detector/readiness.py` instead of duplicating `shutil.which` + pip/uv logic.
- **`check_platforms()` wired into `diagnose()`** — callable via `--check-platforms` flag.
- **`install-manifest.json` updated** — `frameworkVersion` 0.1.0→0.2.0, `schemaVersion` 1.1→1.2, added `aiProviders`, `cicd`, `branchPolicy`, `operationalReadiness`, `release` fields.
- **`decision-store.json` key fixed** — `schema_version` → `schemaVersion` (camelCase consistency).
- **Windows venv paths** — template `settings.json` includes `.venv\Scripts\*` alongside Unix `.venv/bin/*`.

### Removed
- **`acho` skill** — removed alias command and all mirrors (`.claude/commands/ai/acho.md`, `.github/prompts/ai-acho.prompt.md`, template mirrors).
- **Stale audit log entries** — cleaned up `state/audit-log.ndjson`.
- **Backward-compat shims** — removed `__getattr__` lazy re-exports from `gates.py` (~65 LOC) and wrapper functions from `doctor/service.py` (~80 LOC). All imports migrated to direct `policy.checks.*` and `doctor.checks.*` paths.
- **Re-exported constants** — removed `_REQUIRED_DIRS`, `_TOOLS`, `_VCS_TOOLS`, `_PROTECTED_BRANCHES` from `doctor/service.py`.

### Fixed
- **Gitleaks command** — `workflows.py` changed from `gitleaks detect --staged` to `gitleaks protect --staged` (security regression fix).
- **6 test stubs filled** — `test_version_check_fail_when_deprecated`, `test_returns_false_on_all_failures`, `test_project_template_root_missing_raises`, `test_skills_cli_branches`, `test_returns_python_when_manifest_empty_stacks`, `test_pr_creation_returns_false_on_failure` — all replaced with real assertions.
- **`ownership-map.json` regenerated** — added missing `.github/prompts/**`, `.github/agents/**`, `.claude/**`, `state/session-checkpoint.json` paths.

### Added
- **ai-engineering v3 architecture** — full redesign with 6 bounded-context agents (plan, build, scan, release, write, observe) and 33 skills (down from 47).
- **11 new skills**: `architecture`, `code-simplifier`, `create`, `delete`, `feature-gap`, `governance`, `observe`, `perf`, `quality`, `security`, `test` — each consolidating multiple v2 skills into mode-based designs.
- **2 new agents**: `observe` (observatory with 5 dashboard modes: engineer/team/ai/dora/health) and `release` (ALM + GitOps lifecycle).
- **Python CLI observability layer** — `ai-eng observe`, `ai-eng signals`, `ai-eng checkpoint`, `ai-eng decisions`, `ai-eng metrics`, `ai-eng scan-report` commands for token-free deterministic metrics.
- **Load-once signal pattern** — `load_all_events()` + `filter_events()` + `*_from()` variants eliminate redundant audit-log reads (8-9x I/O reduction per CLI invocation).
- **Gate instrumentation** — `run_gate()` now emits `gate_result` audit events after each execution, enabling real metrics instead of seed data.
- **AuditEntry enriched detail** — `detail` field evolved from `str | None` to `str | dict[str, Any] | None` for structured event payloads.
- **Structured audit emitters** — `emit_gate_event()`, `emit_scan_event()`, `emit_build_event()`, `emit_deploy_event()`, `emit_session_event()` in `state/audit.py`.
- **VCS commands reference** (`skills/references/vcs-commands.md`) — single-source command mapping for GitHub (`gh`) and Azure DevOps (`az repos`) CLI operations used across skills.
- **Plan agent input classification** — `raw-idea`, `structured-request`, and `pre-made-plan` input types with adaptive discovery/risk/test depth per type.
- **Plan agent pipeline data flow** — explicit data flow table and pipeline guards documenting what each step consumes, produces, and gates on.

### Changed
- **47→33 skill consolidation** — merged overlapping skills: `test-plan`+`test-run`+`test-gap` → `test`; `sec-review`+`sec-deep`+`sbom`+`deps` → `security`; `integrity`+`compliance`+`ownership` → `governance`; `audit`+`sonar`+`code-review` → `quality`; `arch-review` → `architecture`; `perf-review` → `perf`; `docs`+`simplify` → `docs` (modes); `agent-lifecycle`+`skill-lifecycle`+`agent-card` → `create`+`delete`.
- **6→6 agent restructure** — replaced `review` (God Object with 14 modes) and `triage` agents with bounded-context `scan` (7 assessment modes), `release` (ALM+GitOps), and `observe` (observatory).
- **Cross-reference cleanup** — all skill/agent references updated from v2 names to v3 across 13+ governance files.
- **`.github/agents/` synced** — removed `review.agent.md` and `triage.agent.md`, added `observe.agent.md` and `release.agent.md`.
- **`.github/prompts/` synced** — removed 27 stale v2 prompt files, added 11 new v3 prompt files.
- **README.md updated** — flat skill layout (33 skills) replacing v2 category directories.
- **Security hardening** — replaced 3 bare `except: pass` patterns with `logger.debug()` calls; replaced 2 `assert` statements with explicit `raise AssertionError`.
- **Framework contract restructured** — rewritten as concise enforcement document with MUST/MUST NOT directives; removed temporal content (moved to product-contract).
- **Product contract simplified** — reduced to focused product model with architecture patterns and growth roadmap.
- **Plan agent enhanced** — added architecture review, triage, test-plan, and risk skills to pipeline; added input classification and pipeline guards.
- **PR skill updated** — added VCS commands reference, documentation gate, and existing PR upsert logic.
- **Git helpers extended** — added VCS provider detection helpers.

### Removed
- **14 skills eliminated** — `agent-card`, `agent-lifecycle`, `arch-review`, `audit`, `code-review`, `compliance`, `data-model`, `deps`, `docs-audit`, `improve`, `install`, `integrity`, `multi-agent`, `ownership`, `perf-review`, `prompt`, `sbom`, `sec-deep`, `sec-review`, `simplify`, `skill-lifecycle`, `sonar`, `test-gap`, `test-plan`, `test-run`, `triage` — capabilities absorbed into consolidated v3 skills.
- **2 agents removed** — `review` (absorbed by `scan` + `release`) and `triage` (absorbed by `release` work-item mode).
- **Skill reference files** — removed `skills/references/` directory (9 files: api-design-patterns, behavioral-patterns, database-patterns, delivery-platform-patterns, git-helpers, language-framework-patterns, platform-detect, token-inventory, vcs-commands).

### Added
- **`ai-eng guide` command** — re-displays branch policy setup instructions on demand. Reads guide text from install manifest instead of generating files.
- **AI provider selection** — `ai-eng install --provider claude_code --provider github_copilot` deploys only the files needed for chosen providers. Defaults to `claude_code` when omitted.
- **`ai-eng provider` subcommand** — `add`, `remove`, and `list` commands for managing AI providers post-install. Supports `claude_code`, `github_copilot`, `gemini`, and `codex`.
- **Interactive VCS prompt** — when no git remote is detected, `ai-eng install` now prompts for VCS provider instead of silently defaulting to GitHub.
- **VCS CI/CD regeneration** — `ai-eng vcs set-primary` auto-regenerates CI/CD pipelines for the new provider (opt-out with `--no-cicd`).
- **Deferred setup for empty projects** — installs without stacks set `deferredSetup: true` in manifest, signaling AI agents to configure tooling on first interaction.
- **SonarLint auto-configuration** — install automatically configures SonarLint Connected Mode when Sonar is enabled and IDE markers are detected.

### Changed
- **Minimalist command descriptions** — rewrote first line of all 53 `/ai-*` command files (`.claude/commands/ai/*.md`) with short, actionable descriptions that display in autocomplete. Synchronized descriptions to `.github/prompts/ai-*.prompt.md` frontmatter, template mirrors, and both `GEMINI.md` files.
- **Command Contract added to GEMINI.md** — inserted `## Command Contract` section in root and template `GEMINI.md` matching the existing section in `CLAUDE.md`.
- **Provider-aware templates** — `copy_project_templates` and `remove_provider_templates` now operate per-provider with shared-file deduplication (e.g., AGENTS.md shared by copilot/gemini/codex).
- **Schema version 1.2** — `InstallManifest` adds `aiProviders` config with `primary` and `enabled` fields, and `deferredSetup` to `operationalReadiness`.
- **Security tool auto-install** — install attempts `ensure_tool()` for gitleaks and semgrep before falling back to manual step instructions.
- **Branch policy guide repositioned** — guide now appears after suggested next steps with clearer messaging about manual configuration requirement.
- **`/ai-plan` spec creation enforced** — plan agent pipeline step 4 (spec creation) marked as MANDATORY to ensure traceability.

### Removed
- **`GEMINI.md` template** — Gemini CLI reads `AGENTS.md` natively. Removed dedicated `GEMINI.md` template and ownership entry.
- **Branch policy guides moved to console output** — install no longer creates `.ai-engineering/guides/` directory. Guide text is shown inline during install and stored in the manifest for `ai-eng guide` retrieval.

### Added
- **3 new skills** — `work-item` (Azure Boards + GitHub Issues bidirectional sync), `agent-card` (platform-portable agent descriptors for Copilot/Foundry/AgentKit/Vertex), `triage` (auto-prioritization with p1/p2/p3 rules and throttle at 10+ open items).
- **`ai-scan` agent** — feature scanner that cross-references specs against code to detect unimplemented features, architecture drift, missing tests, dead specifications, and dependency gaps.
- **`ai-triage` agent** — auto-prioritization agent that scans work items using priority rules (security > bugs > features > perf > tests > arch > dx).
- **`ai-plan` planning pipeline** — default 6-step pipeline: triage check → discovery → prompt design → spec creation → work-item sync → dispatch.
- **`ai-review` individual modes** — 14 review modes invokable individually: `security`, `performance`, `architecture`, `accessibility`, `quality`, `pr`, `smoke`, `platform`, `release`, `dx`, `integrity`, `compliance`, `ownership`.
- **Work-item integration** — manifest.yml `work_items` section supporting GitHub Issues and Azure Boards with bidirectional spec sync and auto-transition.
- **Discovery interrogation skill** (`discover`) — structured requirements elicitation through 8-dimension completeness checks, 5 Whys probing, and KNOWN/ASSUMED/UNKNOWN classification.
- **Architecture patterns table** in product-contract.md section 7.4 — documents scanner/executor separation, single-system-multiple-access-points, finding deduplication, context threading, progressive disclosure, and mode dispatch patterns.
- **Performance and Security growth headers** added to 8 thin stack standards (react-native, astro, nextjs, node, typescript, nestjs, rust, react) as future extension points.

### Changed
- **Skill frontmatter schema aligned** — moved `version` and `tags` from top-level frontmatter keys to `metadata.version` and `metadata.tags` across all 47 skills and template mirrors for stricter Anthropic guide compatibility.
- **Top skill usage examples added** — added `## Examples` sections to 10 frequently used skills (`commit`, `cleanup`, `spec`, `pr`, `code-review`, `test-run`, `debug`, `audit`, `release`, `discover`) and mirrored templates.
- **Validator compatibility updated** — integrity validator now accepts skill version from `metadata.version` (with backward compatibility), preserving `skill-frontmatter` checks after schema alignment.
- **Agent scope model refined** — `ai-review` and `ai-scan` now use `read-write (work items only)` scope to create/sync follow-up work items in Azure Boards or GitHub Issues/Projects while keeping code and governance content non-editable by these agents.
- **Review/scan behavior contracts updated** — agent definitions and template mirrors now include explicit work-item synchronization steps via `skills/work-item/SKILL.md`, preserving finding-to-work-item traceability.
- **README governance section expanded** — added the full skills table (47 skills) under the Skills section and aligned agent scope text with the updated non-code work-item write model.
- **Consolidated 19 agents to 6** — `ai-plan` (orchestration + planning pipeline), `ai-build` (implementation across all stacks, merges 8 agents), `ai-review` (reviews + governance, merges 6 agents), `ai-scan` (feature scanner), `ai-write` (documentation), `ai-triage` (auto-prioritization). Only `ai-build` has code write permissions.
- **Flat skill organization** — restructured 44 skills from 6 nested categories (`workflows/`, `dev/`, `review/`, `docs/`, `govern/`, `quality/`) to flat `skills/<name>/` layout. Added 3 new skills for 47 total. Removed `category` from frontmatter schema; replaced with optional `tags` array.
- **Unified `ai-` command namespace** — replaced 7 prefixes (`dev:`, `review:`, `docs:`, `govern:`, `quality:`, `workflows:`, `agent:`) with single `ai-` prefix. All slash commands now use `/ai-<name>` format.
- **Skill rename map** — 10 skills renamed for clarity: `test-strategy` → `test-plan`, `test-runner` → `test-run`, `data-modeling` → `data-model`, `deps-update` → `deps`, `cicd-generate` → `cicd`, `cli-ux` → `cli`, `api-design` → `api`, `infrastructure` → `infra`, `database-ops` → `db`, `sonar-gate` → `sonar`, `discovery-interrogation` → `discover`, `self-improve` → `improve`, `writer` → `docs`, `prompt-design` → `prompt`, and 14 review/govern/quality renames.
- **Consolidated 50 skills to 44** (prior spec) — merged accept-risk + resolve-risk + renew-risk into `risk` (mode: accept/resolve/renew); create-agent + delete-agent into `agent-lifecycle` (mode: create/delete); create-skill + delete-skill into `skill-lifecycle` (mode: create/delete); dast + container-security + data-security into `sec-deep` (mode: dast/container/data). Removed standalone acho skill (redirected to commit/pr).
- **Compacted CLAUDE.md** from 280 to 114 lines (~810 tokens). Replaced verbose skill/agent path lists with compact table format. Propagated to all 6 instruction file mirrors.
- **Enhanced all 19 agent personas** with 5-element framework: specific role + seniority, industry/domain context, named methodologies, explicit constraints, and output format specification. Identity-only changes; capabilities and behavior unchanged.
- **Deduplicated core.md** — removed ~85 lines of overlap with skills-schema.md.
- **Added finding deduplication baseline** to `framework/core.md` — agents must check decision-store before reporting duplicate findings.
- **Added remediation priority order** to `quality/core.md` — security > reliability > correctness > performance > maintainability > testability > docs > style.
- **Updated registration cascade** across all artifacts: instruction files, manifest.yml, product-contract.md, slash commands, Copilot prompt files, agent frontmatter references, template mirrors, and test fixtures.

### Removed
- **19 old agent files** — api-designer, architect, code-simplifier, database-engineer, debugger, devops-engineer, docs-writer, frontend-specialist, governance-steward, infrastructure-engineer, navigator, orchestrator, platform-auditor, pr-reviewer, principal-engineer, quality-auditor, security-reviewer, test-master, verify-app. Capabilities absorbed into 6 new agents.
- **6 skill category directories** — `workflows/`, `dev/`, `review/`, `docs/`, `govern/`, `quality/` replaced by flat `skills/<name>/` structure.
- **7 command prefixes** — `dev:`, `review:`, `docs:`, `govern:`, `quality:`, `workflows:`, `agent:` replaced by unified `ai-` prefix.
- Standalone skills (prior spec): `govern/accept-risk`, `govern/resolve-risk`, `govern/renew-risk`, `govern/create-agent`, `govern/delete-agent`, `govern/create-skill`, `govern/delete-skill`, `review/dast`, `review/container-security`, `review/data-security`, `workflows/acho` (11 skills removed, 4 consolidated replacements + 1 new = net -6).

### Fixed
- **Framework smoke Python install resilience** — `.github/workflows/ci.yml` now retries `uv python install` up to 3 times with backoff in `framework-smoke`, reducing transient GitHub network/download failures across matrix runners.
- **Content Integrity counter parsing** — `ai-eng validate` now correctly counts skills/agents from current instruction table format (`## Skills (N)` + markdown tables), fixing false `counter-accuracy` failures in CI.
- **Moved spec reset from `/cleanup` to `/pr`** — `/pr` now runs conditional Step 0 (`spec-reset --dry-run` then `spec-reset` when complete) so archived specs and cleared `_active.md` are committed on the PR branch and reach `origin/main` on merge; `/cleanup` v3.0.0 now focuses on status/sync/prune/branch cleanup only.
- **Expanded `dotnet.md` standard** (57 -> ~300 lines) — production-grade .NET 10 patterns: SDK version pinning, NuGet Central Package Management, 20+ code patterns (async, DI, minimal APIs, middleware, ProblemDetails, structured logging, health checks), EF Core patterns (DbContext pooling, no-tracking, keyset pagination, compiled queries, interceptors, bulk operations), test tiers with NUnit, testing patterns (WebApplicationFactory, TestContainers, NSubstitute, FluentAssertions, NetArchTest), performance patterns (ArrayPool, BenchmarkDotNet, output caching), C# coding conventions.
- **Expanded `azure.md` standard** (70 -> ~150 lines) — Azure Functions patterns (isolated worker, triggers, Durable Functions, cold start), App Service patterns (deployment slots, auto-scaling, managed identity), Logic Apps patterns (Standard vs Consumption, connectors, error handling), Well-Architected Framework 5-pillar references, 17 cloud design patterns (Circuit Breaker, CQRS, Saga, Strangler Fig, etc.).
- **Evolved `principal-engineer` agent** (v1 -> v2) — scope upgraded from `read-only` to `read-write`. Added implementation, architecture-design, performance-optimization, testing-strategy, migration-planning capabilities. Stack detection step (`.csproj` -> dotnet.md, `pyproject.toml` -> python.md, `package.json` -> typescript.md). Post-edit validation per stack. References expanded with `dotnet.md`, `azure.md`, `database.md`, and 5 additional dev skills.
- **Updated skill references** — `test-runner` now includes .NET test tiers alongside Python tiers. `database-ops` references EF Core patterns from `dotnet.md`. `data-modeling` references EF Core entity mapping patterns. `performance` references .NET performance patterns (ArrayPool, BenchmarkDotNet, output caching).

## [0.1.0] - 2026-03-01

*First MVP release (Phase 1)*

### Added
- **CLI UX skill** (`dev/cli-ux`) — agent-first CLI design patterns: JSON envelopes, Rich human output, dual-mode routing, progress indicators.
- **CLI UX modules** — `cli_envelope.py` (structured JSON envelopes with NextAction), `cli_output.py` (JSON mode detection), `cli_progress.py` (Rich spinners), `cli_ui.py` (terminal formatting helpers: error, info, kv, success).
- **Spec-026: Gemini CLI Support** — `GEMINI.md` instruction file for Gemini CLI, enabling governed AI workflows with the same skills and agents as Claude Code, Copilot, and Codex.
- Installer deploys `GEMINI.md` alongside other provider instruction files on `ai-eng install`.
- Ownership entry for `GEMINI.md` in defaults (framework-managed).
- Validator includes `GEMINI.md` and its template mirror in instruction file sync checks.
- Template mirror: `src/ai_engineering/templates/project/GEMINI.md`.
- Presentation materials updated with Gemini CLI as a supported AI provider.
- **Enhanced `/cleanup` skill (v2.0.0)** — single repository hygiene primitive with 5 phases: Status, Sync, Prune, Cleanup, Spec Reset.
- Repository status module (`maintenance/repo_status.py`): remote branch analysis, ahead/behind tracking, open PR listing via `gh`, stale branch detection (>30 days).
- Spec reset module (`maintenance/spec_reset.py`): active spec detection, completed spec archival to `specs/archive/`, `_active.md` reset.
- CLI commands: `ai-eng maintenance repo-status`, `ai-eng maintenance spec-reset`.
- `/create-spec` now composes `/cleanup` before branch creation for automatic pre-spec hygiene.
- **Spec-025: OSS Documentation Gate** — mandatory documentation gate in `/commit`, `/pr`, and `/acho` workflows for OSS GitHub users.
- Documentation gate classifies changes as user-visible vs internal-only and enforces CHANGELOG.md and README.md updates for user-visible changes.
- External documentation portal support: asks for docs repo URL, clones, updates documentation, creates PR with auto-complete.
- PR checklist expanded with CHANGELOG, README, and external docs items.
- **Spec-024: Sonar Scanner Integration & Platform Credential Onboarding** — platform credential management with keyring, Sonar quality gate skill, and guided onboarding CLI.
- New `credentials` module (`models.py`, `service.py`) for OS-native secret storage via keyring.
- New `platforms` module (`detector.py`, `github.py`, `sonar.py`, `azure_devops.py`) for platform detection and API-validated credential setup.
- New `ai-eng setup` CLI subgroup with `platforms`, `github`, `sonar`, `azure-devops` commands.
- `ai-eng doctor --check-platforms` flag for credential health checks via platform APIs.
- Post-install platform onboarding prompt (opt-in, D024-003).
- New skill: `dev:sonar-gate` — Sonar quality gate integration with skip-if-unconfigured semantics.
- Sonar gate scripts (`sonar-pre-gate.sh`, `sonar-pre-gate.ps1`) with `--skip-if-unconfigured` flag.
- Sonar threshold mapping reference (`sonar-threshold-mapping.md`).
- Sonar quality gate integrated as optional dimension in `quality:release-gate`, `quality:audit-code`, and `quality:install-check`.
- Claude Code command wrapper and Copilot prompt for `dev:sonar-gate`.
- Template mirrors for all new modules, skills, and wrappers.
- **SonarLint IDE Configuration** — `ai-eng setup sonarlint` auto-configures Connected Mode for VS Code family (VS Code, Cursor, Windsurf, Antigravity), JetBrains family (IntelliJ, Rider, WebStorm, PyCharm, GoLand), and Visual Studio 2022.
- New `platforms/sonarlint.py` module with IDE detection, per-family configurators, and merge-safe JSON/XML generation.
- `sonarlint.md` quality standard extended with per-IDE integration guidance and Connected Mode rationale.
- **Spec-023: Multi-Stack Expansion + Audit-Driven Hardening** — comprehensive multi-stack governance from 35+ AI tool audit.
- 8 new stack standards: `typescript.md`, `react.md`, `react-native.md`, `nestjs.md`, `astro.md`, `rust.md`, `node.md`, `bash-powershell.md`.
- 3 cross-cutting standards: `azure.md`, `infrastructure.md`, `database.md`.
- 4 new agents: `infrastructure-engineer`, `database-engineer`, `frontend-specialist`, `api-designer`.
- 4 new skills: `dev:api-design`, `dev:infrastructure`, `dev:database-ops`, `review:accessibility`.
- 3 behavioral baselines added to framework core: Holistic Analysis Before Action, Exhaustiveness Requirement, Parallel-First Tool Execution.
- 6 reference files expanded with substantive content: delivery-platform-patterns, language-framework-patterns, database-patterns, api-design-patterns, platform-detect, git-helpers.
- Claude Code command wrappers and Copilot prompt/agent wrappers for all new agents and skills.
- Template mirrors for all new agents, skills, and stack standards.
- GitHub Copilot prompt files (`.github/prompts/`) — 46 prompt wrappers mapping to all skills, available as `/command` in Copilot Chat.
- GitHub Copilot custom agents (`.github/agents/`) — 9 agent wrappers available in VS Code agent dropdown.
- Copilot prompts and agents mirror-sync validation in `ai-eng validate`.
- Installer deploys `.github/prompts/` and `.github/agents/` on `ai-eng install`.
- Cleanup workflow skill for branch cleanup and stale branch removal (`/cleanup`).
- Contract-compliance skill for clause-by-clause framework contract validation.
- Ownership-audit skill for ownership boundary and updater safety validation.
- Docs-audit skill for documentation and content quality auditing.
- Test-gap-analysis skill for capability-to-test risk mapping.
- Release-gate skill for aggregated release readiness GO/NO-GO verdicts.
- Platform-auditor agent for full-spectrum audit orchestration across all quality dimensions.
- Command contract compliance validation in verify-app agent.
- Feature inventory mode in codebase-mapper agent.
- Architecture drift detection in architect agent.
- Enforcement tamper resistance analysis in security-reviewer agent.
- Module value classification mode in code-simplifier agent.
- Explain skill for Feynman-style code and concept explanations with 3-tier depth.
- Risk acceptance lifecycle: `accept-risk`, `resolve-risk`, `renew-risk` lifecycle skills with severity-based expiry (C=15d/H=30d/M=60d/L=90d) and max 2 renewals.
- Pre-implementation workflow skill for branch hygiene before new implementation work.
- Branch cleanup module (`maintenance/branch_cleanup.py`): fetch, prune, delete merged branches.
- Pipeline compliance module (`pipeline/compliance.py`, `pipeline/injector.py`): scan GitHub Actions and Azure DevOps pipelines for risk governance gates.
- Pipeline risk gate templates for GitHub Actions and Azure DevOps.
- Shared git operations module (`git/operations.py`): `run_git()`, `current_branch()`, `is_branch_pushed()`, `is_on_protected_branch()`.
- Risk governance gate checks: pre-commit warning for expiring acceptances, pre-push blocking for expired acceptances.
- CLI commands: `ai-eng gate risk-check`, `ai-eng maintenance branch-cleanup`, `ai-eng maintenance risk-status`, `ai-eng maintenance pipeline-compliance`.
- Decision model extended with `riskCategory`, `severity`, `acceptedBy`, `followUpAction`, `status`, `renewedFrom`, `renewalCount` fields (all optional, backward compatible).
- `DecisionStore.risk_decisions()` helper method.
- Risk lifecycle functions in `decision_logic.py`: `create_risk_acceptance()`, `renew_decision()`, `revoke_decision()`, `mark_remediated()`, `list_expired_decisions()`, `list_expiring_soon()`.
- `MaintenanceReport` extended with risk acceptance and branch status fields.
- Create-spec skill for spec creation with branch-first workflow.
- Delete-skill skill for safe skill removal with dependency checks.
- Delete-agent skill for safe agent removal with dependency checks.
- Content-integrity skill for governance content validation (6-category check).
- Spec-First Enforcement section in framework core standards.
- Content Integrity Enforcement section in framework core standards.
- Content integrity capability in verify-app agent.
- Create-skill skill for definitive skill authoring and registration procedure.
- Create-agent skill for definitive agent authoring and registration procedure.
- Changelog documentation skill for generating user-friendly changelogs and release notes from git history.
- Doc-writer skill for open-source documentation generation from codebase knowledge.
- Canonical/template mirror contract for `.ai-engineering` governance artifacts.
- Installer coverage for full bundled non-state governance template tree.

### Changed
- **CLI commands migrated to UX modules** — all 10 CLI command modules (`cicd`, `core`, `gate`, `maintenance`, `review`, `setup`, `skills`, `stack_ide`, `validate`, `vcs`) refactored to use `cli_envelope`, `cli_output`, `cli_progress`, and `cli_ui` for consistent terminal output, JSON mode support, and Rich spinners.
- **Governance surface: 49→50 skills** — `dev/cli-ux` registered across all instruction files (CLAUDE.md, AGENTS.md, GEMINI.md, copilot-instructions.md).
- **Documentation gate always evaluates** — removed binary "internal-only → skip" classification from `/commit`, `/pr`, and `/acho` workflows. The gate now classifies scope (CHANGELOG + README, CHANGELOG only, or no updates needed) but never auto-skips entirely. Skill, agent, and governance surface changes are no longer blanket-exempt.
- **`/cleanup` mandates CLI commands** — Phase 0 (repo-status), Phase 3 (branch-cleanup), and Phase 4 (spec-reset) now require `uv run ai-eng maintenance <command>` instead of ad-hoc shell commands. Prevents zsh `!=` operator escaping failures during stale branch detection.
- `/cleanup` upgraded from branch-only cleanup to full repository hygiene primitive (status + sync + prune + cleanup + spec reset).
- Session Start Protocol updated: "Run `/cleanup`" replaces "Run `/pre-implementation`" across all provider instruction files.
- Maintenance report includes remote branch, open PR, and stale branch counts.
- 6 existing agents improved: devops-engineer (Azure Pipelines, Railway, Cloudflare), architect (infra architecture), security-reviewer (cloud security, IaC scanning), orchestrator (parallel-first), principal-engineer (exhaustiveness), test-master (multi-stack).
- 3 existing skills improved: cicd-generate (Azure Pipelines, Railway, Cloudflare), deps-update (multi-stack detection), security (cloud + IaC scanning).
- `nextjs.md` stack standard updated with TypeScript base reference.
- Governance surface: 45→49 skills, 15→19 agents, 5→14 stack standards.
- Refactored git operations out of `workflows.py` and `gates.py` into shared `git/operations.py`.
- Decision store schema bumped from 1.0 to 1.1 (backward compatible).
- Gate pre-commit now includes risk expiry warnings.
- Gate pre-push now blocks on expired risk acceptances.
- Aligned `.ai-engineering` and `src/ai_engineering/templates/.ai-engineering` non-state content.
- Installer template mapping now discovers bundled governance files dynamically.
- Updated governance metadata versions from `0.1.0-dev` to `0.1.0`.

### Removed
- `/pre-implementation` skill — functionality absorbed into `/cleanup` and `/create-spec`.
- `poetry.lock` and empty e2e test package placeholder.

### Fixed
- **Template product-contract.md** — committed version shipped ai-engineering-specific content instead of generic `<project-name>` placeholders, causing `ai-eng install` to copy project-specific data to new installations.
- **12 template mirrors synced** — agents, skills, standards, and project templates restored to generic form for clean installations.
- Content Integrity CI: synced `create-spec/SKILL.md` template mirror with canonical (missing cleanup step).
- Content Integrity CI: corrected skill count in `product-contract.md` from 50 to 49.
- `ai-eng install` no longer crashes (exit code 1) when platform onboarding prompt is aborted or running in non-interactive mode.
- Setup CLI commands now correctly registered on module-level Typer instance (fixes unit test isolation).
- Doctor platform check test uses correct patch path for `GitHubSetup`.
- Template mirror for `dev/sonar-gate/SKILL.md` synced with canonical source.
- Lint fixes: `str, Enum` → `StrEnum`, combined `with` statements, ternary simplifications.
