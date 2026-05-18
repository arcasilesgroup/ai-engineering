---
title: "AI Engineering Release Version CI/CD PyPI Brief"
status: draft
audience: "framework maintainers and release engineers"
branch: "codex/ai-engineering-release-version-cicd-pypi"
length_estimate: "cross-surface release hardening brief"
authoring_style: "evidence-cited diagnostic, spec-ready"
principles_required:
  - "§10.1 KISS"
  - "§10.5 TDD"
  - "§10.6 SDD"
  - "§10.7 Clean Code"
  - "§10.8 Hexagonal Architecture"
delivery_mode: "brief for /ai-brainstorm; no implementation"
mantra: "One release command, one version truth, one audited publish path."
---

# AI Engineering Release Version CI/CD PyPI Brief

## 1. Vision

ai-engineering needs one governed framework release spine from source version metadata to release PR, CI proof, supply-chain evidence, GitHub Release, and PyPI publication. The source repo already has the package, registry, release command, release guard, CI, SBOM, and PyPI workflow surfaces that were missing in the mistaken consumer-workspace draft, so the problem is no longer "find the upstream repo". The real problem is consolidation: `ai-eng release <VERSION>` is documented as the only normal release write path, but the current source tree also carries an independent semantic-release/CI-build path that can create tags and commit version changes directly to `main`. The target state is a single audited path with one version source, one release PR, one artifact set, one PyPI publish job, and one acceptance gate before any immutable package version is published.

## 2. Scope Boundary

In scope:

- Reconcile the framework source repo release surfaces: `pyproject.toml`, `src/ai_engineering/version/registry.json`, root and template `framework_version` manifests, `CHANGELOG.md`, `ai-eng release`, release-version guard, `ci-build.yml`, and `release.yml`.
- Decide which release orchestrator owns version calculation: the documented `ai-eng release <VERSION>` command or semantic-release automation, but not both as independent writers.
- Specify CI/CD gates for release PRs, tag creation, artifact build, artifact verification, SBOM/provenance, TestPyPI, PyPI, and GitHub Release finalization.
- Define tests that prove release-surface parity, guarded branch semantics, changelog promotion, workflow triggering, and OIDC/Trusted Publishing behavior without requiring real PyPI credentials.
- Preserve the existing hard constraints: no long-lived PyPI tokens, no manual version-surface edits, no `--no-verify`, no backwards-compatibility shims, no machine paths, and no silent dual-writes.

Out of scope for this brief:

- Performing an actual version bump or publishing a PyPI package.
- Manually configuring PyPI/TestPyPI project settings; the spec may document required settings, but the implementation must not assume local access to PyPI admin state.
- Rewriting unrelated CI jobs except where they participate in release/version publication.
- Replacing the full cross-IDE framework governance chain; this brief feeds `/ai-brainstorm`, then `/ai-plan`, then `/ai-build`, then `/ai-pr`.

## 3. Diagnostic Snapshot

The correct source repo contains real release surfaces. `pyproject.toml` names the package `ai-engineering` and sets the package version to `0.4.0`, while the root framework manifest also sets `framework_version: "0.4.0"` and project `version: "1.0.0"` `pyproject.toml:1-8`, `.ai-engineering/manifest.yml:10-13`. The bundled template manifest also carries `framework_version: "0.4.0"`, which makes framework-source releases different from consumer installs and confirms this brief belongs in the framework repo `src/ai_engineering/templates/.ai-engineering/manifest.yml:10-13`.

The version registry exists and currently declares `0.4.0` as `current`, with older versions demoted to `supported` `src/ai_engineering/version/registry.json:1-24`. The package build configuration includes that registry in the wheel, so registry drift affects installed lifecycle checks, not just source metadata `pyproject.toml:277-294`.

The documented release rule is explicit: `ai-eng release <VERSION>` is the only supported write path, and it owns `pyproject.toml`, `src/ai_engineering/version/registry.json`, source-repo `framework_version` manifests, and `CHANGELOG.md` promotion `.ai-engineering/reference/cli-reference.md:21-35`. The current CLI command exposes `--wait`, `--dry-run`, and `--skip-bump`, normalizes a leading `v`, resolves the project root, selects the VCS provider, executes the release orchestrator, and reports phase results to human or JSON output `src/ai_engineering/cli_commands/release.py:18-47`, `src/ai_engineering/cli_commands/release.py:48-105`.

The release orchestrator already encodes a governed path: validate, detect state, dry-run plan, prepare branch, create PR, optionally wait for merge, create tag, update install-state, emit deploy events, and monitor workflow status `src/ai_engineering/release/orchestrator.py:121-268`. Validation currently requires semver, a clean `main` or `master` working tree, a target greater than the current version, an available/authenticated VCS provider, and a valid changelog with no duplicate target section `src/ai_engineering/release/orchestrator.py:271-318`.

The release command's version mutator treats `pyproject.toml` as the package version source, updates the version line, updates `registry.json`, and syncs root/template `framework_version` manifests only when the template manifest identifies a framework source repo `src/ai_engineering/release/version_bump.py:159-167`, `src/ai_engineering/release/version_bump.py:191-208`, `src/ai_engineering/release/version_bump.py:211-248`. Registry updates demote every existing `current` entry to `supported`, add the new version as `current`, stamp the release date, and rewrite the JSON payload `src/ai_engineering/release/version_bump.py:251-273`.

The changelog helper supports the release path but only at a simple structural level today: it validates that `[Unreleased]` exists and the target section does not already exist, then promotes the `[Unreleased]` body into `## [<version>] - <date>` and clears the `[Unreleased]` section `src/ai_engineering/release/changelog.py:35-47`, `src/ai_engineering/release/changelog.py:50-76`. The docs skill has a stricter human-facing changelog contract: release sections need dates, Keep a Changelog grouping, comparison links, and explicit breaking-change placement `.codex/skills/ai-docs/handlers/changelog.md:56-69`. The implementation spec must decide whether to strengthen the release helper or add a separate release-readiness assertion.

A CI guard exists specifically to block casual version edits. It watches `pyproject.toml`, the root and template manifest `framework_version` lines, `registry.json`, and `CHANGELOG.md`; PRs outside `release/v<version>` fail if governed version surfaces changed; release PRs must include the full release file set `src/ai_engineering/policy/release_version_guard.py:12-40`, `src/ai_engineering/policy/release_version_guard.py:70-109`. Tests cover ignored manifest project-version edits, failure outside release branches, failure for incomplete file sets, and success for full release PRs `tests/unit/test_release_version_guard.py:13-94`.

The source repo also contains an independent CI-build release mechanism that conflicts with the documented write path. `pyproject.toml` configures python-semantic-release to write `pyproject.toml:project.version`, tag as `v{version}`, and derive bump types from conventional commits `pyproject.toml:189-202`. `.github/workflows/ci-build.yml` runs after successful `CI Check` on `main`, determines a semantic-release bump, edits `pyproject.toml` locally with `sed`, builds artifacts, creates a tag via the GitHub API, generates provenance/SBOM/checksums, drafts a GitHub Release, and then uses a direct GitHub API commit-back to update `pyproject.toml` and `registry.json` on `main` with `force=true` `.github/workflows/ci-build.yml:1-14`, `.github/workflows/ci-build.yml:50-78`, `.github/workflows/ci-build.yml:79-153`, `.github/workflows/ci-build.yml:155-228`. That path bypasses the `release/v<version>` branch rule, omits root/template manifest version sync, omits changelog promotion, and is not the `ai-eng release` PR path.

The PyPI release workflow exists and is closer to the desired publish shape than the mistaken consumer-workspace draft suggested. `.github/workflows/release.yml` is artifact-driven: it resolves a version or latest tag, verifies the tag exists, locates a successful `ci-build.yml` run for the tag commit, downloads the `dist` artifact, uses the protected `pypi` environment, grants OIDC `id-token: write`, publishes with `pypa/gh-action-pypi-publish`, then promotes or creates the GitHub Release `.github/workflows/release.yml:1-16`, `.github/workflows/release.yml:19-35`, `.github/workflows/release.yml:50-113`, `.github/workflows/release.yml:150-178`, `.github/workflows/release.yml:179-233`.

The PyPI workflow has important gaps for the governed release target. It only runs on `workflow_dispatch`, so a tag created by `ai-eng release --wait` will not automatically trigger it `.github/workflows/release.yml:19-27`, while the orchestrator's wait path creates a tag and monitors a workflow named `Release` as though the pipeline will run after tag creation `src/ai_engineering/release/orchestrator.py:210-251`, `src/ai_engineering/release/orchestrator.py:543-559`. The workflow verifies that `dist/` is non-empty before upload but does not run a release-specific metadata check, install smoke, TestPyPI publish/install, or artifact-to-version parity assertion `.github/workflows/release.yml:159-178`.

The regular CI gate surface is broad and mostly release-compatible. `CI Check` runs lint/format, duplication, OPA policy tests, risk acceptance, no-suppression, typecheck, unit/integration/e2e tests, SonarCloud, smoke installs, workflow sanity/actionlint/policy checks, gate-trailer verification, optional Snyk, and security audit `.github/workflows/ci-check.yml:71-165`, `.github/workflows/ci-check.yml:167-180`, `.github/workflows/ci-check.yml:260-331`, `.github/workflows/ci-check.yml:333-447`, `.github/workflows/ci-check.yml:449-512`, `.github/workflows/ci-check.yml:513-620`. Content integrity already invokes the release-version guard before `ai-eng check` and manifest validation `.github/workflows/ci-check.yml:664-698`.

Security posture is partially release-ready and partially advisory. The blocking security job installs gitleaks, runs pip-audit via the framework TLS wrapper, pins Semgrep CLI `1.163.0`, runs in-tree Semgrep rules as a blocking gate, and checks Semgrep skip ratio `.github/workflows/ci-check.yml:513-620`, `.github/workflows/ci-check.yml:645-662`. Community Semgrep packs are `continue-on-error` because registry access is unauthenticated/advisory pending a token `.github/workflows/ci-check.yml:624-644`. The spec phase must decide whether production releases may proceed while community packs are advisory, or whether release mode requires the token and blocks.

The release-readiness skill contract exists, but it is a user-facing spec rather than concrete release orchestration in the current command. `/ai-verify --release` promises an eight-dimension GO / CONDITIONAL GO / NO-GO gate over coverage, security, tests, lint, dependency vulnerabilities, types, documentation coherence, and packaging integrity `.codex/skills/ai-verify/SKILL.md:18-24`, `.codex/skills/ai-verify/SKILL.md:63-69`. The release implementation should call or emulate that gate before tag creation and before PyPI promotion, with evidence retained in the release artifact trail.

The project constitution raises the bar above ordinary packaging. Pre-commit, pre-push, CI, allowlist, and supply-chain gates require gitleaks, ruff, spec verification, Semgrep, pip-audit, tests, type checking, integration checks, SonarCloud, Scorecard, SBOM diff, Sigstore keyless OIDC signatures where available, SLSA provenance, CycloneDX SBOM per release, and immutable GitHub Action pins `CONSTITUTION.md:85-115`. The release design must not weaken these controls for the sake of convenience.

External packaging guidance reinforces the desired consolidation. PyPA's `pyproject.toml` spec treats `version` as required package metadata that may be static or dynamic, and the current repo chooses a static `project.version` `pyproject.toml:1-8`. PyPI Trusted Publishing uses OIDC to mint short-lived tokens and avoid long-lived API tokens. PyPI's trusted-publisher guide recommends `pypa/gh-action-pypi-publish`, a publishing environment, and job-level `id-token: write`, and shows TestPyPI publication via `repository-url: https://test.pypi.org/legacy/`. GitHub's Python publishing guide recommends separate build and publish jobs using artifacts, dedicated publishing environments, Trusted Publishing, and commit-SHA action pins. The `pypa/gh-action-pypi-publish` project explicitly recommends building distributions in a separate job, testing the same artifacts before upload, then publishing from a dedicated scoped job. GitHub artifact attestations and PyPI attestations provide provenance hooks that fit the constitution's Sigstore/SLSA/SBOM requirements.

## 4. Architecture

The proposed architecture is a four-port release spine with one domain decision and three adapters:

1. **Release domain and version authority.** `ai-eng release <VERSION>` remains the operator-facing release command because the CLI reference already names it as the sole write path `.ai-engineering/reference/cli-reference.md:29-35`. The spec must decide whether semantic-release becomes a read-only version-suggestion helper behind `ai-eng release --draft` or is removed from the release write path. It must not keep independent semantic-release tag/commit authority beside `ai-eng release`.
2. **Version-surface mutation adapter.** The mutator should continue to update `pyproject.toml`, `registry.json`, root/template manifests, and `CHANGELOG.md` as one atomic release PR, because both implementation and guard tests already encode that set `src/ai_engineering/release/version_bump.py:211-248`, `src/ai_engineering/policy/release_version_guard.py:38-40`, `tests/unit/test_release_version_guard.py:71-94`. The dry-run output should list old version, target version, release branch, exact files, changelog state, and workflow actions before any write.
3. **CI artifact/provenance adapter.** CI should build the release artifact once, upload the exact `dist/` set, generate checksums, SBOM, and artifact attestations, verify those attestations, and expose a machine-readable release packet. The current `ci-build.yml` already builds, attests, generates SBOM/checksums, and uploads artifacts `.github/workflows/ci-build.yml:76-153`, but it should stop creating tags and committing version bumps independently `.github/workflows/ci-build.yml:79-89`, `.github/workflows/ci-build.yml:155-228`.
4. **Publish adapter.** The PyPI adapter should be a top-level, scoped, protected-environment job that downloads prebuilt artifacts and publishes with OIDC/Trusted Publishing. The current `release.yml` already has a protected `pypi` environment and OIDC permission `.github/workflows/release.yml:150-178`, but the spec should add TestPyPI, artifact metadata/install checks, version parity, and an automatic trigger aligned with `ai-eng release --wait`.

The release spine should stay hexagonal: version calculation, file mutation, CI proof, and PyPI publication are separate ports. Domain logic decides whether a release is allowed; VCS, GitHub Actions, PyPI/TestPyPI, attestations, and SBOM tooling are adapters that can be tested independently.

## 5. Evidence Catalog

| Evidence | What it supports |
|---|---|
| `pyproject.toml:1-8` | Package name and static version are present in the real framework source repo. |
| `pyproject.toml:189-202` | Semantic-release currently has separate version/tag bump rules. |
| `pyproject.toml:277-294` | The wheel includes framework packages and `version/registry.json`. |
| `.ai-engineering/manifest.yml:10-20` | Root manifest declares framework version `0.4.0`, project version `1.0.0`, GitHub VCS, and Python stack. |
| `src/ai_engineering/templates/.ai-engineering/manifest.yml:10-13` | Template manifest also carries framework version `0.4.0`. |
| `src/ai_engineering/version/registry.json:1-24` | Version registry exists and marks `0.4.0` current. |
| `.ai-engineering/reference/cli-reference.md:21-35` | `ai-eng release <VERSION>` is the documented sole write path. |
| `src/ai_engineering/cli_commands/release.py:18-47` | CLI normalizes version, resolves root, builds `ReleaseConfig`, and executes the orchestrator. |
| `src/ai_engineering/release/orchestrator.py:121-268` | Orchestrator phase flow already models validate, PR, wait, tag, manifest, monitor. |
| `src/ai_engineering/release/orchestrator.py:271-318` | Validation gates semver, clean main/master, greater version, VCS auth, and changelog state. |
| `src/ai_engineering/release/version_bump.py:191-248` | Mutator updates package version, registry, and source-repo manifests. |
| `src/ai_engineering/release/changelog.py:35-76` | Changelog validation and promotion helpers exist but are simple. |
| `src/ai_engineering/policy/release_version_guard.py:12-40` | Guarded version-surface file set is explicit. |
| `src/ai_engineering/policy/release_version_guard.py:70-109` | Guard allows version surface changes only in release PRs with the full file set. |
| `tests/unit/test_release_version_guard.py:71-94` | Tests pin the expected full release PR file set. |
| `.github/workflows/ci-build.yml:50-78` | CI-build uses semantic-release output and locally edits `pyproject.toml` before building. |
| `.github/workflows/ci-build.yml:79-153` | CI-build can create tags, attest artifacts, generate SBOM/checksums, and draft releases. |
| `.github/workflows/ci-build.yml:155-228` | CI-build can commit version changes directly to `main` with `force=true`, bypassing release PR semantics. |
| `.github/workflows/release.yml:19-35` | PyPI release workflow is manual-only via `workflow_dispatch`. |
| `.github/workflows/release.yml:50-113` | Release workflow resolves a tag and matching successful CI-build artifact. |
| `.github/workflows/release.yml:150-178` | PyPI publish uses protected `pypi` environment, OIDC permission, and `pypa/gh-action-pypi-publish`. |
| `.github/workflows/release.yml:179-233` | Release workflow finalizes the GitHub Release after PyPI publish. |
| `.github/workflows/ci-check.yml:664-698` | Content-integrity job invokes release-version guard and framework checks. |
| `.codex/skills/ai-verify/SKILL.md:63-69` | `/ai-verify --release` defines release readiness dimensions and GO/NO-GO verdicts. |
| `CONSTITUTION.md:85-115` | Project-level gates require security, CI, supply-chain, SBOM, provenance, and action-pinning controls. |

## 6. Roadmap

### Milestone 0: Resolve release authority

Acceptance gate: `/ai-brainstorm` records one decision that either keeps `ai-eng release <VERSION>` as the sole write path and demotes/removes semantic-release write authority, or explicitly replaces `ai-eng release` documentation and guard semantics. The expected direction is to keep `ai-eng release` as the sole write path because the docs, guard, tests, and operator workflow already encode it.

### Milestone 1: Release dry-run and mutation parity

Acceptance gate: `ai-eng release <TARGET_VERSION> --dry-run` reports the old version, new version, branch, tag, changelog status, all files that would change, and workflow triggers. Unit tests prove the dry-run file list matches the release-version guard's required file set.

### Milestone 2: Remove competing CI write path

Acceptance gate: `ci-build.yml` no longer creates release tags or commits version changes directly to `main`. It may build and attest artifacts for already-merged release commits, but version mutation and changelog promotion occur only through a release PR created by `ai-eng release`.

### Milestone 3: Align release workflow trigger and monitor

Acceptance gate: the workflow that `ai-eng release --wait` monitors actually starts after the tag or release event it creates. Tests or workflow-policy checks prove `Release` can be triggered without manual dispatch for the governed path, while manual dispatch remains a recovery path if the spec approves it.

### Milestone 4: Artifact verification and TestPyPI

Acceptance gate: release artifacts are built once, checked for metadata/version parity, installed in a clean environment, optionally checked with `twine check` or equivalent, published to TestPyPI, installed from TestPyPI, then promoted to PyPI from the same artifact set.

### Milestone 5: Supply-chain evidence packet

Acceptance gate: every release publishes or links a release packet containing `dist/`, checksums, CycloneDX SBOM, GitHub artifact attestations or PyPI attestations, release-readiness result, changelog section, CI run URL, and PyPI project URL.

### Milestone 6: Release readiness as a blocking gate

Acceptance gate: `/ai-verify --release <TARGET_VERSION>` or an equivalent deterministic release-readiness command returns GO before tag creation and before PyPI publication. CONDITIONAL GO is allowed only when risk acceptances are present in the canonical store and referenced in the release packet.

## 7. Definition of Done

- `/ai-brainstorm --consume ai-engineering-release-version-cicd-pypi-brief.md` produces an approved spec before implementation.
- The approved spec records one release authority and removes the competing writer path.
- `ai-eng release <TARGET_VERSION> --dry-run` lists the exact release branch, tag, changed files, changelog promotion, CI workflow, and publish stages.
- The release mutator updates `pyproject.toml`, `src/ai_engineering/version/registry.json`, `.ai-engineering/manifest.yml`, `src/ai_engineering/templates/.ai-engineering/manifest.yml`, and `CHANGELOG.md` together, or the spec formally changes the guard file set.
- The release-version guard blocks any version-surface PR outside `release/v<version>` and any incomplete release file set.
- `ci-build.yml` no longer commits version bumps directly to `main` or creates tags independently of the governed release command.
- The `Release` workflow trigger matches the event produced by `ai-eng release --wait`.
- Release artifacts are built once and the same artifact set is used for metadata checks, TestPyPI, PyPI, GitHub Release assets, checksums, SBOM, and attestations.
- TestPyPI publish and install verification complete before production PyPI publication.
- PyPI publish uses Trusted Publishing/OIDC and no long-lived PyPI API token.
- Release jobs use protected environments, minimal permissions, timeouts, concurrency, and immutable action pins consistent with project policy.
- The release gate captures coverage, security, tests, lint, dependency vulnerabilities, types, docs coherence, and packaging integrity.
- The final release packet links the changelog section, release PR, tag, CI run, artifact checks, SBOM/provenance, TestPyPI proof, and PyPI release URL.

## 8. Quality Stamps

- **§10.6 SDD:** this brief is a draft problem statement only; implementation must wait for `/ai-brainstorm` and `/ai-plan`.
- **§10.5 TDD:** release authority, dry-run parity, workflow trigger alignment, guard behavior, artifact version parity, and changelog promotion should land test-first.
- **§10.1 KISS:** one release command, one release PR, one artifact set, one publish workflow. Remove or demote competing write paths rather than adding coordination glue between two releasers.
- **§10.7 Clean Code:** release failures must name the blocked phase, file, workflow, and next operator action. Current CLI phase output already provides the right shape `src/ai_engineering/cli_commands/release.py:89-105`.
- **§10.8 Hexagonal Architecture:** keep domain release decisions separate from VCS, GitHub Actions, PyPI/TestPyPI, SBOM, and attestation adapters.
- **SSOT-PD:** version authority is a datum; it must have exactly one canonical writable store/path and no silent dual-writes, consistent with `CONSTITUTION.md:84-88` and `docs/persistence-doctrine.md:1-35`.

## 9. Open Decisions

1. What is `<TARGET_VERSION>` and release type: patch, minor, major, release candidate, or prerelease?
2. Does semantic-release remain as a version-suggestion utility, or is it removed from the framework release workflow entirely?
3. Should `pyproject.toml:project.version` be the version SSOT, with registry/manifests/changelog as derived release surfaces, or should the release registry become the authoritative ledger with `pyproject.toml` as a generated target?
4. Should `ai-eng release --wait` create a tag after PR merge, create a GitHub Release, dispatch a workflow, or rely on a tag-push workflow trigger?
5. Should production release block on Semgrep community packs once a `SEMGREP_APP_TOKEN` exists, or are in-tree Semgrep rules plus pip-audit/gitleaks sufficient for GO?
6. Should TestPyPI run on every release PR, every release candidate tag, or only after merge to avoid namespace/version exhaustion?
7. Which attestation set is mandatory: GitHub artifact attestations, PyPI publish attestations, SLSA provenance, SBOM attestation, or all of them?
8. Should manual `workflow_dispatch` PyPI publish remain as a recovery path, and if so what risk acceptance or environment approval is required?
9. Should changelog validation in `src/ai_engineering/release/changelog.py` enforce the stricter Keep a Changelog contract currently documented in `/ai-docs`?
10. How should release packet evidence be stored: GitHub Release assets, `.ai-engineering/state/framework-events.ndjson`, `state.db`, markdown archive, or a combination with one canonical store per datum?

## 10. Migration

No backwards-compatibility shim is allowed. The current competing release surfaces should be hard-migrated into a single path:

1. **Inventory and freeze:** identify every workflow or command that can change package version, registry, manifests, changelog, tags, releases, or PyPI state. Freeze direct version edits outside `release/v<version>` PRs.
2. **Demote competing writer:** remove `ci-build.yml` tag creation and main commit-back, or convert those steps into read-only artifact/provenance work that runs after a governed release commit.
3. **Strengthen `ai-eng release`:** make dry-run explicit, guarantee file-set parity, and align `--wait` with an actual release workflow trigger.
4. **Add verification gates:** add release artifact checks, TestPyPI, production PyPI, and release packet verification.
5. **Document breakage:** update `CHANGELOG.md` and release docs to state that semantic-release/manual CI commit-back is no longer a release write path.

Per the project constitution, any renamed or deleted release workflow path is a hard migration with changelog documentation, not a deprecation shim `CONSTITUTION.md:71-77`.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| Competing release writers publish divergent versions | High | High | Make `ai-eng release` the only writer; remove CI-build tag/commit-back authority. |
| `ai-eng release --wait` creates a tag but no workflow runs | High | High | Align `Release` workflow trigger with tag/release event or explicit dispatch from the orchestrator. |
| Direct `main` commit-back bypasses release PR guard | High | High | Delete `force=true` commit-back and require release PRs with full file set. |
| Registry/manifests/changelog drift from package version | Medium | High | Test release file-set parity and fail if any governed surface is missing. |
| Publishing untested artifacts to PyPI | Medium | High | Build once, verify metadata/install, publish to TestPyPI, install from TestPyPI, then publish same artifacts to PyPI. |
| OIDC permission is too broad | Medium | Medium | Scope `id-token: write` to the publish job only, with protected environments and minimal permissions. |
| Advisory Semgrep packs hide release-blocking issues | Medium | Medium | Decide release-specific policy; require token or document advisory status as conditional release risk. |
| PyPI immutable version mistake | Medium | High | Dry-run, TestPyPI, artifact parity, and final human environment approval before production PyPI. |
| Changelog helper under-validates release quality | Medium | Medium | Promote `/ai-docs` changelog rules into deterministic release validation. |
| Artifact attestations are generated but not verified or discoverable | Medium | Medium | Include attestation verification and release packet links in acceptance criteria. |

## 12. References

Local evidence:

- `.ai-engineering/reference/cli-reference.md:21-35` — documented release command and sole write-path rule.
- `src/ai_engineering/cli_commands/release.py:18-105` — CLI release entry point.
- `src/ai_engineering/release/orchestrator.py:121-318` — release phases and validation.
- `src/ai_engineering/release/version_bump.py:191-273` — version mutation and registry sync.
- `src/ai_engineering/policy/release_version_guard.py:12-109` — guarded release file set and branch policy.
- `.github/workflows/ci-build.yml:50-228` — competing semantic-release/tag/commit-back path.
- `.github/workflows/release.yml:1-233` — current artifact-driven PyPI workflow.
- `.github/workflows/ci-check.yml:513-698` — current security and content-integrity gates.
- `.codex/skills/ai-verify/SKILL.md:63-69` — release-readiness gate contract.
- `CONSTITUTION.md:85-115` — mandatory gates and supply-chain bar.

External official references:

- Python Packaging User Guide, `pyproject.toml` specification: https://packaging.python.org/en/latest/specifications/pyproject-toml/
- Python Packaging User Guide, version specifiers: https://packaging.python.org/en/latest/specifications/version-specifiers/
- PyPI Trusted Publishers documentation: https://docs.pypi.org/trusted-publishers/
- PyPI publishing with a Trusted Publisher: https://docs.pypi.org/trusted-publishers/using-a-publisher/
- PyPI digital attestations: https://docs.pypi.org/attestations/
- GitHub Docs, build/test Python and publish to PyPI: https://docs.github.com/en/actions/tutorials/build-and-test-code/python#publishing-to-pypi
- GitHub Docs, artifact attestations: https://docs.github.com/en/actions/concepts/security/artifact-attestations
- PyPA `gh-action-pypi-publish`: https://github.com/pypa/gh-action-pypi-publish

## 13. Glossary

- **Release authority:** the single command or workflow allowed to decide and mutate release state.
- **Version SSOT:** the single canonical writable source for the package/framework version.
- **Governed version surface:** a file whose version-related content may change only through the release path.
- **Release PR:** a `release/v<version>` pull request carrying the full version/changelog file set.
- **Artifact-driven publish:** building distributions once, then passing the exact artifact set through verification and publish jobs.
- **Trusted Publishing:** PyPI's OIDC-backed publish flow that avoids long-lived API tokens.
- **TestPyPI:** a separate package index used to validate publication and installation before production PyPI.
- **Release packet:** discoverable evidence bundle for a release: PR, tag, CI, artifacts, checksums, SBOM, attestations, changelog, TestPyPI, and PyPI result.
- **Competing writer:** any command or workflow that can mutate release state outside the release authority.
- **Conditional GO:** a release-readiness result that permits release only with explicit risk acceptance in the canonical store.

## 14. Acceptance

- [ ] `/ai-brainstorm --consume ai-engineering-release-version-cicd-pypi-brief.md` is run and produces an approved spec.
- [ ] The approved spec names `<TARGET_VERSION>` or explicitly defers it to release execution input.
- [ ] The approved spec selects one release authority and documents the fate of semantic-release.
- [ ] `ai-eng release <TARGET_VERSION> --dry-run` reports old/new version, release branch, tag, changed files, changelog state, CI workflow, and publish stages.
- [ ] Release mutation updates `pyproject.toml`, `registry.json`, root manifest, template manifest, and `CHANGELOG.md` together, or the guard file set is intentionally changed with tests.
- [ ] Version-surface guard tests prove non-release PRs fail and full release PRs pass.
- [ ] `ci-build.yml` no longer tags or commits version changes directly to `main`.
- [ ] The `Release` workflow starts from the event produced by `ai-eng release --wait`.
- [ ] Build artifacts include both sdist and wheel and pass version metadata, install smoke, and artifact integrity checks.
- [ ] The same artifact set is used for TestPyPI, PyPI, GitHub Release assets, checksums, SBOM, and attestations.
- [ ] TestPyPI publication and install verification complete before production PyPI publication.
- [ ] PyPI publication uses Trusted Publishing/OIDC, protected environment approval, job-scoped permissions, timeouts, concurrency, and immutable action pins.
- [ ] `/ai-verify --release <TARGET_VERSION>` or equivalent returns GO before tag/PyPI promotion.
- [ ] Release packet evidence is discoverable from the GitHub Release or another approved canonical store.
- [ ] `CHANGELOG.md` documents the release path migration and any breaking removal of legacy release automation.
