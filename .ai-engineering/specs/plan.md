---
spec: spec-143
slug: ai-engineering-release-version-cicd-pypi
title: plan — Release Version CI/CD PyPI Spine
status: approved
pipeline: full
total: 54
completed: 54
files_touched: 24
tdd_pairs: 18
generated: 2026-05-18
approved_at: 2026-05-18
approved_by: operator
---

# Plan — spec-143 Release Version CI/CD PyPI Spine

> Mantra: **One release command, one version truth, one audited publish path.**

## Pre-flight

- Spec schema: `.ai-engineering/specs/spec.md` contains required frontmatter and required sections (`Summary`, `Goals`, `Non-Goals`, `Decisions`, `Risks`). Open questions are empty.
- Lifecycle caution: the active spec frontmatter and `.ai-engineering/state/specs/ai-engineering-release-version-cicd-pypi.json` still say `status: draft`. This `/ai-plan` invocation produced the build contract, but `/ai-build` remains blocked until the operator explicitly approves the spec + this plan.
- Existing worktree: active uncommitted spec/lifecycle files existed before planning; `/ai-plan` only rewrote `.ai-engineering/specs/plan.md`.
- Pipeline classification: `full` — release authority + CI/CD + provenance + CLI + docs, touching >5 files and supply-chain surfaces.
- Design routing: skipped as a false positive. The substring matcher hit `form` and `ui` inside non-UI release/provenance prose; no page/component/screen/frontend work exists, so no `/ai-design` artifact is required.
- External docs checked: GitHub Actions workflow syntax / OIDC / artifact attestations, PyPI Trusted Publishers / TestPyPI, PyPI digital attestations, and PyPA `gh-action-pypi-publish` README semantics.

## Architecture

Primary pattern: **Pipes and Filters**, with the existing `VcsProvider` protocol preserved as a Ports-and-Adapters seam.

Rationale: the governed release is a deterministic pipeline of independent filters — validate, mutate version surfaces, create PR, wait for merge, run readiness, tag, build once, attest, publish to TestPyPI, install-smoke, publish to PyPI, assemble release packet, emit audit pointer. Each filter owns a narrow input/output contract and can be unit-tested independently. The release orchestrator already keeps provider-specific operations behind `VcsProvider`; this plan extends the pipeline without leaking GitHub/PyPI details into unrelated domain code.

## Phases

1. **Remove competing release authority** — hard-delete semantic-release config/deps/CI writers.
2. **Codify release workflow policy** — tests prevent tag-trigger drift, privilege creep, and artifact substitution.
3. **Rewrite release workflow** — tag-triggered build-once TestPyPI→PyPI pipeline with attestations and release packet.
4. **Release readiness + audit pointer** — deterministic GO / CONDITIONAL GO / NO-GO before tag/publish and packet URL in audit.
5. **Dry-run parity** — `ai-eng release --dry-run` previews the full governed path.
6. **Changelog + guard hardening** — release docs quality and version-surface guard remain fail-closed.
7. **Docs + migration note** — document hard removal and supported release path.
8. **Single final quality loop** — one full verification round; blockers stop.

---

## Phase 1 — Remove competing release authority

- [x] T-1 — RED: add release-authority drift test
- Agent: build
- Status: DONE — RED gate failed on semantic-release dependency/config, CI writer, and release workflow comments as expected.
- Files: tests/unit/test_release_authority.py:1 (NEW)
- Principles applied: §10.5 TDD, §10.6 SDD, §10.4 DRY
- Patch (deterministic): omit — test synthesis required. Assert active release surfaces (`pyproject.toml`, `uv.lock`, `.github/workflows/ci-build.yml`, `.github/workflows/release.yml`, `.ai-engineering/reference/cli-reference.md`, `src/ai_engineering/templates/.ai-engineering/reference/cli-reference.md`) contain no semantic-release dependency/config/command or CI commit-back release writer. Allow historical mentions only in active spec/drafts/archive/changelog history.
- Gate: `uv run pytest -q tests/unit/test_release_authority.py` fails on current `python-semantic-release`, `[tool.semantic_release]`, `uv run semantic-release`, and release workflow comments.

- [x] T-2 — GREEN: remove semantic-release from project config
- Agent: build
- Status: DONE — removed `python-semantic-release`, `[tool.semantic_release]`, and the obsolete GitPython override.
- Files: pyproject.toml:42, pyproject.toml:176, pyproject.toml:189
- Principles applied: §10.2 YAGNI, §10.4 DRY, §10.6 SDD
- Patch (deterministic): applied as planned — removed the `python-semantic-release` dev dependency, the obsolete GitPython override tied to semantic-release, and all `[tool.semantic_release]` configuration blocks from `pyproject.toml`.
- Gate: `uv run pytest -q tests/unit/test_release_authority.py` still fails only on lock/workflow/doc references.

- [x] T-3 — GREEN: regenerate lockfile after dependency removal
- Agent: build
- Status: DONE — `uv lock` regenerated `uv.lock` with no semantic-release package/config matches.
- Files: uv.lock:1
- Principles applied: §10.4 DRY, §10.6 SDD
- Patch (deterministic): omit — generated lockfile; run `uv lock` after T-2.
- Gate: `rg -n "python-semantic-release|semantic_release|semantic-release" uv.lock` returns no matches.

- [x] T-4 — GREEN: reduce `ci-build.yml` to non-release package build
- Agent: build
- Status: DONE — `ci-build.yml` now only builds/uploads package artifacts after a successful `CI Check`.
- Files: .github/workflows/ci-build.yml:1
- Principles applied: §10.1 KISS, §10.2 YAGNI, §10.6 SDD
- Patch (deterministic): omit — YAML rewrite needs care. Remove `workflow_dispatch`, top-level `contents: write`, `id-token: write`, `attestations: write`, semantic-release detection, local version bump, tag creation, attest/SBOM/checksum release work, draft GitHub Release creation, supply-chain release uploads, and force commit-back. Keep only post-`CI Check` package build/upload if still useful.
- Gate: `uv run pytest -q tests/unit/test_release_authority.py` no longer reports `.github/workflows/ci-build.yml`; `python scripts/check_workflow_policy.py` passes.

- [x] T-5 — VERIFY: semantic-release hard-removal gate is green
- Agent: verify
- Status: DONE — reran after release workflow rewrite; release authority/docs tests pass and active release surfaces contain no semantic-release matches.
- Files: tests/unit/test_release_authority.py:1, pyproject.toml:34, uv.lock:1, .github/workflows/ci-build.yml:1
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — read-only verification.
- Gate: `uv run pytest -q tests/unit/test_release_authority.py && rg -n "semantic-release|python-semantic-release|semantic_release" pyproject.toml uv.lock .github/workflows .ai-engineering/reference/cli-reference.md src/ai_engineering/templates/.ai-engineering/reference/cli-reference.md` returns no active release-path matches.

---

## Phase 2 — Codify release workflow policy

- [x] T-6 — RED: release workflow trigger policy test
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1 (NEW)
- Principles applied: §10.5 TDD, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — test synthesis required. Parse `.github/workflows/release.yml` and assert `on.push.tags` contains `v*`, `workflow_dispatch` exists only for protected recovery, and no release normal path depends on `release.published` or `workflow_run` from `ci-build.yml`.
- Gate: `uv run pytest -q tests/unit/workflows/test_release_workflow_policy.py::test_release_workflow_starts_on_v_tags` fails on current dispatch-only workflow.

- [x] T-7 — RED: release workflow least-privilege policy test
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.5 TDD, §10.3 SOLID, §10.6 SDD
- Patch (deterministic): omit — test synthesis required. Assert no top-level `id-token: write`; OIDC is job-scoped to TestPyPI/PyPI publish jobs; `attestations: write` is scoped to build/attest job; `contents: write` is scoped only to GitHub Release packet finalization; every job has `timeout-minutes` and concurrency is keyed by tag/version.
- Gate: targeted test fails on current top-level `id-token: write` and `contents: write`.

- [x] T-8 — RED: no untrusted artifact reuse policy test
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.5 TDD, §10.6 SDD, §10.8 Hexagonal Architecture
- Patch (deterministic): omit — test synthesis required. Assert release jobs build/download artifacts produced within the same tag-triggered workflow only; forbid `gh run list --workflow=ci-build.yml`, `run-id: ${{ needs.resolve-version.outputs.ci-run-id }}`, and PR/fork artifact contexts in publish jobs.
- Gate: targeted test fails on current `ci-build.yml` artifact lookup/download.

- [x] T-9 — RED: release packet artifact contract test
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.5 TDD, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — test synthesis required. Assert final workflow creates/uploads release packet assets: dist artifacts, `CHECKSUMS-SHA256.txt`, CycloneDX SBOM, GitHub attestation verification log, PyPI/TestPyPI publish evidence, release-readiness JSON, release notes, CI run URL, and recovery context when used.
- Gate: targeted test fails because current workflow only publishes dist and release notes.

- [x] T-10 — GREEN: add release-specific policy helpers
- Agent: build
- Files: scripts/check_workflow_policy.py:1, tests/unit/test_check_workflow_policy.py:1, tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.3 SOLID, §10.4 DRY, §10.7 Clean Code
- Patch (deterministic): omit — helper design required. Keep generic workflow policy reusable; add narrow release-workflow helper(s) instead of inlining assertions in many tests.
- Gate: `uv run pytest -q tests/unit/test_check_workflow_policy.py tests/unit/workflows/test_release_workflow_policy.py` fails only on release workflow content, not helper absence.

- [x] T-11 — VERIFY: workflow policy red tests fail for expected current-state reasons
- Agent: verify
- Files: tests/unit/workflows/test_release_workflow_policy.py:1, .github/workflows/release.yml:1
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — read-only verification.
- Gate: failure messages name the current dispatch-only trigger, top-level OIDC/contents write, `ci-build.yml` artifact dependency, and missing packet artifacts; no unrelated YAML parse errors.

---

## Phase 3 — Rewrite release workflow

- [x] T-12 — RED: build-on-tag job topology test
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.5 TDD, §10.1 KISS
- Patch (deterministic): omit — test synthesis required. Assert job order: `resolve-version` → `release-readiness-pre-tag-or-pre-publish`/`release-readiness` → `release-build` → `attest-and-verify` → `publish-testpypi` → `verify-testpypi-install` → `publish-pypi` → `finalize-release-packet`.
- Gate: targeted test fails until workflow has the new DAG.

- [x] T-13 — GREEN: rewrite release trigger and resolver
- Agent: build
- Files: .github/workflows/release.yml:1
- Principles applied: §10.1 KISS, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — YAML rewrite. Add `push.tags: ['v*']`; keep `workflow_dispatch` with explicit `version` and `recovery_reason`; resolve version from `github.ref_name` on tag push or dispatch input on recovery; check out the exact tag/ref with `fetch-depth: 0`; fail if dispatch lacks recovery reason.
- Gate: T-6 passes; T-12 still fails on downstream jobs.

- [x] T-14 — RED: release build artifact integrity test
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — test synthesis required. Assert `release-build` runs `uv build`, validates wheel/sdist metadata version equals tag version, performs clean-environment install smoke from local `dist/`, creates CycloneDX SBOM, and writes SHA256 checksums covering dist + SBOM.
- Gate: targeted test fails until build job contains the checks.

- [x] T-15 — GREEN: implement build-once artifact generation
- Agent: build
- Files: .github/workflows/release.yml:36
- Principles applied: §10.1 KISS, §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — workflow commands require synthesis. Use the pinned local setup composite or pinned first-party actions already in repo; build once from the tag ref; upload named artifacts (`release-dists`, `release-supply-chain`) for same-run downstream jobs only.
- Gate: T-14 passes; workflow policy and YAML parse tests pass.

- [x] T-16 — RED: GitHub artifact attestation test
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — test synthesis required. Assert attestation generation uses GitHub artifact attestations with `attestations: write` + `id-token: write` on the attestation job and verifies every `dist/*` file via `gh attestation verify` before publication.
- Gate: targeted test fails until attest + verify steps exist.

- [x] T-17 — GREEN: add GitHub artifact attestation generation and verification
- Agent: build
- Files: .github/workflows/release.yml:80
- Principles applied: §10.3 SOLID, §10.6 SDD, §10.8 Hexagonal Architecture
- Patch (deterministic): omit — workflow implementation required. Use a job-scoped permissions block (`contents: read`, `attestations: write`, `id-token: write`) and write verification output to a packet artifact.
- Gate: T-16 passes; `python scripts/check_workflow_policy.py` passes.

- [x] T-18 — RED: TestPyPI publish/install gate test
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — test synthesis required. Assert `publish-testpypi` uses `environment: testpypi`, job-scoped `id-token: write`, `pypa/gh-action-pypi-publish` with `repository-url: https://test.pypi.org/legacy/`, and downstream install smoke uses TestPyPI plus PyPI fallback only for dependencies.
- Gate: targeted test fails until TestPyPI job exists.

- [x] T-19 — GREEN: implement TestPyPI publish and install proof
- Agent: build
- Files: .github/workflows/release.yml:120
- Principles applied: §10.5 TDD, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — workflow implementation required. Publish the same `release-dists` artifact; capture TestPyPI URL/log as `testpypi-proof.txt`; install the package version in a clean venv from TestPyPI before production.
- Gate: T-18 passes; packet artifact includes TestPyPI proof.

- [x] T-20 — RED: production PyPI publish gate test
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — test synthesis required. Assert `publish-pypi` needs successful TestPyPI publish + install proof, uses `environment: pypi`, job-scoped `id-token: write`, no username/password/API-token inputs, and publishes the exact same `release-dists` artifact.
- Gate: targeted test fails until PyPI job is gated by TestPyPI proof.

- [x] T-21 — GREEN: implement production PyPI publish
- Agent: build
- Files: .github/workflows/release.yml:155
- Principles applied: §10.1 KISS, §10.6 SDD, §10.8 Hexagonal Architecture
- Patch (deterministic): omit — workflow implementation required. Do not use long-lived PyPI tokens; rely on Trusted Publishing; ensure no PR/fork condition can reach this job.
- Gate: T-20 passes; `rg -n "PYPI_TOKEN|password:|username:" .github/workflows/release.yml` has no normal publish credential hits.

- [x] T-22 — RED: GitHub Release packet finalization test
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.5 TDD, §10.6 SDD, §10.4 DRY
- Patch (deterministic): omit — test synthesis required. Assert `finalize-release-packet` uses `contents: write`, creates/updates GitHub Release for the tag after PyPI succeeds, uploads all packet assets with `--clobber`, includes release notes from target changelog section, and records CI run URL.
- Gate: targeted test fails until final packet job exists.

- [x] T-23 — GREEN: implement GitHub Release packet finalization
- Agent: build
- Files: .github/workflows/release.yml:190
- Principles applied: §10.4 DRY, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — workflow implementation required. Generate a `release-packet.json` manifest listing asset names, checksums, attestation verification, TestPyPI proof, PyPI URL, readiness verdict, changelog source, workflow run URL, and recovery context.
- Gate: T-22 passes; final job depends on production PyPI success.

- [x] T-24 — RED: manual recovery context test
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — test synthesis required. Assert `workflow_dispatch` requires `version` and `recovery_reason`, runs through the same TestPyPI→PyPI pipeline, and writes recovery context into `release-packet.json`; tag push path records `recovery: false`.
- Gate: targeted test fails until recovery context is mandatory.

- [x] T-25 — GREEN: wire protected recovery context
- Agent: build
- Files: .github/workflows/release.yml:19
- Principles applied: §10.1 KISS, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — YAML implementation required. Keep recovery protected by the same `testpypi`/`pypi` environments and no separate shadow publish branch.
- Gate: T-24 passes; `python scripts/check_workflow_policy.py` passes.

---

## Phase 4 — Release readiness and audit pointer

- [x] T-26 — RED: release-readiness service verdict tests
- Agent: build
- Files: tests/unit/test_release_readiness.py:1 (NEW)
- Principles applied: §10.5 TDD, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — test synthesis required. Cover GO when all dimensions pass; NO-GO for blocker/critical security, failed tests, failed package build, missing changelog; CONDITIONAL GO only when findings are accepted/advisory and evidence records the condition.
- Gate: `uv run pytest -q tests/unit/test_release_readiness.py` fails with missing service.

- [x] T-27 — GREEN: implement deterministic release-readiness service
- Agent: build
- Files: src/ai_engineering/release/readiness.py:1 (NEW), src/ai_engineering/verify/service.py:1
- Principles applied: §10.3 SOLID, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — service design required. Prefer a small `release/readiness.py` that composes existing verify/gate/build/changelog helpers rather than bloating `verify.service`; output a JSON-serializable evidence object with `verdict`, `conditions`, `dimensions`, and `artifact_path`.
- Gate: T-26 passes; functions remain ≤30 LOC where practical.

- [x] T-28 — RED: CLI `ai-eng verify --release` tests
- Agent: build
- Files: tests/unit/test_verify_release_cli.py:1 (NEW), src/ai_engineering/cli_commands/verify_cmd.py:25
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — CLI test synthesis required. Assert `ai-eng verify --release 0.5.0` prints GO/CONDITIONAL GO/NO-GO, exits non-zero on NO-GO, and JSON mode includes release-readiness evidence.
- Gate: targeted CLI test fails because `verify_cmd` currently has no `--release` option.

- [x] T-29 — GREEN: expose release readiness through `ai-eng verify`
- Agent: build
- Files: src/ai_engineering/cli_commands/verify_cmd.py:25, src/ai_engineering/cli_factory.py:341
- Principles applied: §10.1 KISS, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — CLI renderer integration required. Add `--release [VERSION]` without reintroducing mode sprawl; normal `ai-eng verify` behavior remains unchanged.
- Gate: T-28 passes; existing `tests/unit/test_release_cli.py` and verify tests still pass.

- [x] T-30 — RED: orchestrator blocks tag creation on readiness NO-GO
- Agent: build
- Files: tests/unit/test_release_orchestrator.py:445
- Principles applied: §10.5 TDD, §10.6 SDD, §10.3 SOLID
- Patch (deterministic): omit — test synthesis required. In wait path, assert `_run_release_readiness` is called after merge and before `_create_tag`; NO-GO returns a failed `readiness` phase and never calls `_create_tag`; CONDITIONAL GO proceeds and records condition text.
- Gate: targeted orchestrator test fails because no readiness phase exists.

- [x] T-31 — GREEN: insert readiness phase before tag creation
- Agent: build
- Files: src/ai_engineering/release/orchestrator.py:210
- Principles applied: §10.3 SOLID, §10.6 SDD, §10.8 Hexagonal Architecture
- Patch (deterministic): omit — integration required. Add a narrow helper that calls the release-readiness service (not a shell) so unit tests stay deterministic; write readiness evidence to `.ai-engineering/runtime/release/<version>/release-readiness.json` for packet upload.
- Gate: T-30 passes; wait path success test updates expected phases.

- [x] T-32 — RED: workflow readiness artifact test
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — test synthesis required. Assert release workflow runs `ai-eng verify --release <version>` before TestPyPI and PyPI, uploads `release-readiness.json`, and blocks production on NO-GO.
- Gate: targeted workflow test fails until workflow has readiness job.

- [x] T-33 — GREEN: wire readiness into release workflow
- Agent: build
- Files: .github/workflows/release.yml:90
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — workflow implementation required. Reuse the CLI created in T-29 and pass its JSON output as packet evidence.
- Gate: T-32 passes.

- [x] T-34 — RED: deploy audit includes release packet pointer
- Agent: build
- Files: tests/unit/test_deploy_event_wiring.py:219, tests/unit/test_release_orchestrator.py:445
- Principles applied: §10.5 TDD, §10.6 SDD, §10.4 DRY
- Patch (deterministic): omit — test synthesis required. Assert successful release monitoring records a packet URL or manifest URL in the deploy event metadata/result, not only the workflow run URL.
- Gate: targeted tests fail because current `emit_deploy_event` result is just tag/run output.

- [x] T-35 — GREEN: carry release packet pointer through result and audit
- Agent: build
- Files: src/ai_engineering/release/orchestrator.py:95, src/ai_engineering/cli_commands/release.py:41, src/ai_engineering/state/audit.py:192
- Principles applied: §10.4 DRY, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — data-shape change required. Add `release_packet_url`/`release_packet_ref` to `ReleaseResult` and JSON output; use release URL + uploaded `release-packet.json` convention when workflow API cannot expose assets directly.
- Gate: T-34 passes; existing deploy event tests update to preserve tag/pipeline events plus packet pointer.

---

## Phase 5 — Dry-run parity

- [x] T-36 — RED: dry-run parity test
- Agent: build
- Files: tests/unit/test_release_orchestrator.py:123
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — test synthesis required. Assert `ai-eng release <VERSION> --dry-run` output includes old version, target version, release branch, tag, governed changed files, changelog promotion state, workflow trigger, TestPyPI stage, PyPI stage, readiness gate, and release-packet outputs.
- Gate: targeted dry-run test fails on current branch/tag-only output.

- [x] T-37 — GREEN: add structured dry-run plan helper
- Agent: build
- Files: src/ai_engineering/release/orchestrator.py:73
- Principles applied: §10.1 KISS, §10.4 DRY, §10.6 SDD
- Patch (deterministic): omit — helper synthesis required. Add `ReleaseDryRunPlan` or plain formatter; no writes in dry-run; reuse existing version/changelog/guard constants to avoid duplicate governed file lists.
- Gate: T-36 passes; `--dry-run` remains success-only when validation passes.

- [x] T-38 — RED: release CLI JSON exposes dry-run/readiness/packet fields
- Agent: build
- Files: tests/unit/test_release_cli.py:41
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — CLI test synthesis required. Assert JSON result includes `dry_run_plan`, `readiness`, and `release_packet_url` when present.
- Gate: targeted test fails until CLI payload is extended.

- [x] T-39 — GREEN: extend release CLI result rendering
- Agent: build
- Files: src/ai_engineering/cli_commands/release.py:41
- Principles applied: §10.1 KISS, §10.7 Clean Code
- Patch (deterministic): omit — rendering update required. Human output should list dry-run plan lines without claiming publish happened.
- Gate: T-38 passes; existing release CLI tests remain green.

---

## Phase 6 — Changelog and guard hardening

- [x] T-40 — RED: strict changelog validation tests -- DONE
- Agent: build
- Files: tests/unit/test_changelog_parser.py:1
- Principles applied: §10.5 TDD, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — test synthesis required. Add cases for missing `[Unreleased]`, duplicate target, target section date format, empty release notes, missing Keep-a-Changelog subgroup, and required `### BREAKING` placement when release-path semantics changed.
- Gate: `uv run pytest -q tests/unit/test_changelog_parser.py` fails on current permissive validation.

- [x] T-41 — GREEN: strengthen changelog helpers -- DONE
- Agent: build
- Files: src/ai_engineering/release/changelog.py:35
- Principles applied: §10.1 KISS, §10.5 TDD, §10.7 Clean Code
- Patch (deterministic): omit — parser changes required. Keep regex parser small; do not add a markdown parser dependency.
- Gate: T-40 passes; `promote_unreleased` still preserves an empty `[Unreleased]` section.

- [x] T-42 — RED: release-version guard target/full-set tests -- DONE
- Agent: build
- Files: tests/unit/test_release_version_guard.py:71, src/ai_engineering/policy/release_version_guard.py:12
- Principles applied: §10.5 TDD, §10.6 SDD, §10.4 DRY
- Patch (deterministic): omit — test synthesis required. Assert release PR branch version matches changed `pyproject.toml` target version when detectable; full file set remains pyproject, registry, root manifest, template manifest, changelog; changes to guard file-set logic require tests touching `tests/unit/test_release_version_guard.py`.
- Gate: targeted guard tests fail until version matching / guard-change evidence exists.

- [x] T-43 — GREEN: extend release-version guard evidence -- DONE
- Agent: build
- Files: src/ai_engineering/policy/release_version_guard.py:12, tests/unit/test_release_version_guard.py:1
- Principles applied: §10.3 SOLID, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — guard logic required. Keep branch/version matching best-effort and fail-closed only when target version is clearly detectable.
- Gate: T-42 passes; current full release PR test still passes.

- [x] T-44 — RED: privileged publish jobs cannot run on PR/fork contexts
- Agent: build
- Files: tests/unit/workflows/test_release_workflow_policy.py:1
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — test synthesis required. Assert PyPI/TestPyPI/finalize jobs include conditions restricting them to tag push or explicit workflow_dispatch recovery, never `pull_request`, fork refs, or uploaded PR artifacts.
- Gate: targeted workflow test fails until `if:` guards are explicit.

- [x] T-45 — GREEN: add fail-closed publish context guards
- Agent: build
- Files: .github/workflows/release.yml:150
- Principles applied: §10.6 SDD, §10.8 Hexagonal Architecture
- Patch (deterministic): omit — workflow implementation required. Use event/ref checks and environment protections; keep manual recovery visible, not an alternate hidden release path.
- Gate: T-44 passes.

---

## Phase 7 — Documentation and migration notes

- [x] T-46 — RED: release docs drift test -- DONE
- Agent: build
- Files: tests/unit/docs/test_release_docs.py:1 (NEW)
- Principles applied: §10.5 TDD, §10.6 SDD, §10.4 DRY
- Patch (deterministic): omit — test synthesis required. Assert CLI reference root + template docs describe `ai-eng release` as sole authority, tag-triggered Release workflow, TestPyPI before PyPI, provenance packet, protected recovery dispatch, and hard removal of semantic-release/manual CI commit-back.
- Gate: targeted docs test fails on current docs.

- [x] T-47 — GREEN: update release CLI/reference docs -- DONE
- Agent: build
- Files: .ai-engineering/reference/cli-reference.md:21, src/ai_engineering/templates/.ai-engineering/reference/cli-reference.md:21
- Principles applied: §10.4 DRY, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — prose update required. Keep docs free of machine paths/PII and avoid documenting `workflow_dispatch` as a normal path.
- Gate: T-46 passes.

- [x] T-48 — GREEN: add CHANGELOG migration entry -- DONE
- Agent: build
- Files: CHANGELOG.md:7
- Principles applied: §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — prose update required. Add an `[Unreleased]` entry stating semantic-release/manual CI commit-back was hard-removed, `ai-eng release` is sole authority, and releases now publish a provenance packet through TestPyPI→PyPI.
- Gate: `rg -n "semantic-release|TestPyPI|Trusted Publishing|release packet" CHANGELOG.md` shows the new migration note in `[Unreleased]`.

- [x] T-49 — VERIFY: docs and active release path contain no stale semantic-release instructions -- DONE
- Agent: verify
- Status: DONE — reran after release workflow rewrite; `tests/unit/docs/test_release_docs.py` and `tests/unit/test_release_authority.py` pass.
- Files: .ai-engineering/reference/cli-reference.md:21, src/ai_engineering/templates/.ai-engineering/reference/cli-reference.md:21, .github/workflows/release.yml:1, CHANGELOG.md:7
- Principles applied: §10.4 DRY, §10.6 SDD
- Patch (deterministic): omit — read-only verification.
- Gate: `uv run pytest -q tests/unit/docs/test_release_docs.py tests/unit/test_release_authority.py` passes.

---

## Phase 8 — Single final quality loop

- [x] T-50 — VERIFY: targeted release unit suite -- DONE
- Agent: verify
- Status: DONE — `uv run pytest -q tests/unit/test_release_authority.py tests/unit/workflows/test_release_workflow_policy.py tests/unit/test_release_orchestrator.py tests/unit/test_release_cli.py tests/unit/test_release_readiness.py tests/unit/test_changelog_parser.py tests/unit/test_release_version_guard.py` passed (85 tests).
- Files: tests/unit/test_release_authority.py:1, tests/unit/workflows/test_release_workflow_policy.py:1, tests/unit/test_release_orchestrator.py:1, tests/unit/test_release_cli.py:1, tests/unit/test_release_readiness.py:1, tests/unit/test_changelog_parser.py:1, tests/unit/test_release_version_guard.py:1
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): omit — read-only verification.
- Gate: `uv run pytest -q tests/unit/test_release_authority.py tests/unit/workflows/test_release_workflow_policy.py tests/unit/test_release_orchestrator.py tests/unit/test_release_cli.py tests/unit/test_release_readiness.py tests/unit/test_changelog_parser.py tests/unit/test_release_version_guard.py` passes.

- [x] T-51 — VERIFY: workflow policy and SHA pinning -- DONE
- Agent: verify
- Status: DONE — `uv run python scripts/check_workflow_policy.py` passed and SHA pinning/check_workflow_policy tests passed (14 tests).
- Files: scripts/check_workflow_policy.py:1, .github/workflows/release.yml:1, .github/workflows/ci-build.yml:1, tests/integration/test_workflow_sha_pinning.py:1
- Principles applied: §10.6 SDD, §10.8 Hexagonal Architecture
- Patch (deterministic): omit — read-only verification.
- Gate: `python scripts/check_workflow_policy.py && uv run pytest -q tests/integration/test_workflow_sha_pinning.py tests/unit/test_check_workflow_policy.py` passes.

- [x] T-52 — VERIFY: release dry-run smoke in a temporary git repo -- DONE
- Agent: verify
- Status: DONE — created a temporary clean git fixture and `uv run ai-eng release 0.2.0 --dry-run --target <fixture>` exited 0, printed all dry-run parity fields, and left fixture status clean.
- Files: src/ai_engineering/release/orchestrator.py:121, src/ai_engineering/cli_commands/release.py:25
- Principles applied: §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — read-only verification with tmp fixture.
- Gate: create a temporary clean git fixture or use existing release CLI test fixture; `ai-eng release <next-version> --dry-run --target <fixture>` exits 0 and prints all parity fields without modifying files.

- [x] T-53 — VERIFY: regulated quality gates single round -- DONE
- Agent: verify
- Status: DONE — single fail-loud round passed: `ruff format --check`, `ruff check`, `ty check` (1 warning diagnostic, exit 0), full `pytest -q` (7735 passed, 27 skipped, 1 deselected, 1 xpassed), workflow policy check, and TLS pip-audit.
- Files: src/ai_engineering/:1, tests/:1, .github/workflows/:1, pyproject.toml:1
- Principles applied: §10.5 TDD, §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): omit — read-only verification.
- Gate: one fail-loud round: `uv run ruff format --check src tests`, `uv run ruff check src tests`, `uv run ty check --exclude 'src/ai_engineering/templates/**' src`, `uv run pytest -q`, `python scripts/check_workflow_policy.py`, and `uv run python -m ai_engineering.verify.tls_pip_audit`.

- [x] T-54 — GUARD: final acceptance review against spec-143 decisions -- DONE
- Agent: guard
- Status: DONE — acceptance matrix maps D-143-01 through D-143-12 to files/tests; 12/12 decisions have implementation and test/doc evidence, with no BLOCKER findings.
- Files: .ai-engineering/specs/spec.md:1, .ai-engineering/specs/plan.md:1, .github/workflows/release.yml:1, src/ai_engineering/release/:1, src/ai_engineering/cli_commands/release.py:1
- Principles applied: §10.6 SDD, §10.7 Clean Code, §10.8 Hexagonal Architecture
- Patch (deterministic): omit — advisory review only.
- Gate: produce an acceptance matrix mapping D-143-01 through D-143-12 to implemented files/tests. Any BLOCKER stops; no automatic second quality-loop round.

### T-54 Acceptance Matrix

| Decision | Status | Evidence |
|---|---|---|
| D-143-01 — `ai-eng release` sole authority | MET | `tests/unit/test_release_authority.py`; `.github/workflows/ci-build.yml` now build-only; `.ai-engineering/reference/cli-reference.md`; `src/ai_engineering/cli_commands/release.py`; `src/ai_engineering/release/orchestrator.py`. |
| D-143-02 — semantic-release hard-removed | MET | `pyproject.toml` and `uv.lock` contain no semantic-release dependency/config; active workflow/doc scan passes; `tests/unit/test_release_authority.py`. |
| D-143-03 — `pyproject.toml` version SSOT | MET | `src/ai_engineering/release/version_bump.py`; `src/ai_engineering/policy/release_version_guard.py`; `tests/unit/test_release_version_guard.py`; dry-run governed file list. |
| D-143-04 — target version is execution input | MET | `ai-eng release VERSION` CLI contract, `ReleaseDryRunPlan.target_version`, `tests/unit/test_release_cli.py`, `tests/unit/test_release_orchestrator.py`. |
| D-143-05 — Release starts from `push` on `v*` tags | MET | `.github/workflows/release.yml` `push.tags`; `tests/unit/workflows/test_release_workflow_policy.py::test_release_workflow_starts_on_v_tags`. |
| D-143-06 — manual dispatch is protected recovery only | MET | `.github/workflows/release.yml` requires `version` + `recovery_reason`, records recovery context, and still uses protected `testpypi`/`pypi` environments; workflow policy tests. |
| D-143-07 — TestPyPI before production PyPI | MET | `publish-testpypi` → `verify-testpypi-install` → `publish-pypi` DAG in `.github/workflows/release.yml`; workflow policy tests T-18/T-20. |
| D-143-08 — provenance evidence mandatory when available | MET | Release workflow builds SBOM/checksums, GitHub attestation verify log, readiness JSON, TestPyPI/PyPI proofs; `tests/unit/workflows/test_release_workflow_policy.py`. |
| D-143-09 — GitHub Release packet is canonical packet store | MET | `finalize-release-packet` uploads packet assets; `release-packet.json`; `release_packet_url`/`release_packet_ref` in `ReleaseResult` and deploy audit; `tests/unit/test_deploy_event_wiring.py`. |
| D-143-10 — privileged jobs never consume untrusted artifacts | MET | Release workflow same-run artifacts only, no `ci-build.yml` run-id dependency, tag/recovery guards, no PR/fork publish context; workflow policy tests T-8/T-44. |
| D-143-11 — CONDITIONAL GO only with evidence | MET | `src/ai_engineering/release/readiness.py`, `ai-eng verify --release`, readiness artifact output, `tests/unit/test_release_readiness.py`, `tests/unit/test_verify_release_cli.py`. |
| D-143-12 — changelog validation strengthened | MET | `src/ai_engineering/release/changelog.py`, `tests/unit/test_changelog_parser.py`, docs drift test, `CHANGELOG.md` migration note. |

Guard verdict: PASS — no BLOCKER. Non-blocking note: `ty check` reports an existing warning diagnostic for `typer.core.TyperCommand`; command exits 0 and T-53 passed.

---

## Quality Outcome

Final: 0 blockers, 0 criticals, 0 highs -> PASS

Evidence:
- T-50 targeted release unit suite: 85 passed.
- T-51 workflow policy and SHA pinning: workflow policy passed; 14 passed.
- T-52 release dry-run smoke: passed in temporary clean git fixture without file mutation.
- T-53 regulated quality round: `ruff format --check`, `ruff check`, `ty check` (1 non-blocking warning, exit 0), full `pytest -q` (7735 passed, 27 skipped, 1 deselected, 1 xpassed), `uv run python scripts/check_workflow_policy.py`, and `uv run python -m ai_engineering.verify.tls_pip_audit` passed.
- T-54 guard acceptance matrix: D-143-01 through D-143-12 all MET; no BLOCKER.
