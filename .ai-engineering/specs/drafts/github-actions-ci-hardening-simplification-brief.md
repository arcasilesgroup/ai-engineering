---
title: "GitHub Actions CI/CD Supply-Chain Hardening and Simplification"
status: draft
audience: /ai-brainstorm
branch: spec-147-wave-1
length_estimate: "~430 lines"
authoring_style: "Staff CI/Supply-Chain Architect — evidence-anchored, source-current as of 2026-05-21, no implementation"
principles_required: [KISS, YAGNI, SDD, TDD, clean-code, hexagonal]
delivery_mode: "End-to-end CI/CD supply-chain hardening with aggregate gate integrity, dependency/action/tool governance, cache trust-boundary isolation, artifact provenance, and topology simplification"
mantra: "One authoritative CI result, one governed release path, no trust-boundary bleed, every dependency/action/tool/artifact pinned, scanned, attested, or verified."
---

> READ FIRST. This brief is an intake artifact for `/ai-brainstorm`. It does not implement the change. It captures the May 21, 2026 GitHub Actions audit and subsequent supply-chain expansion: the repo's release workflow is substantially governed, but the CI aggregate, workflow policy checker, action/dependency/tool pinning, cache boundaries, scanner contracts, dependency ingress, and artifact verification path have gaps that should be closed before more release automation is layered on top.

---

## 1. Vision

ai-engineering should have a smaller, stricter GitHub Actions estate where the aggregate `CI Result` is the single reliable branch-protection signal, release artifacts are produced only by the tag-triggered release workflow, and the whole software supply chain is governed from source change to published PyPI package. The target state covers more than cache poisoning: source/workflow ownership, dependency ingress, action and runtime-tool provenance, cache trust tiers, SAST/SCA ownership, secret/OIDC minimization, SBOM/provenance/attestation verification, and release topology simplification all become deterministic checks instead of reviewer memory.

## 2. Scope Boundary

### In scope

| Area | Included work |
|------|---------------|
| Aggregate gate integrity | Make `ci-check-result` evaluate every blocking CI job, especially anti-suppression, so branch protection can trust one required check. |
| Source and workflow governance | Treat `.github/**`, release code, dependency manifests, lockfiles, and governance docs as protected supply-chain inputs with explicit ownership/review rules. |
| Workflow policy checker | Normalize trigger parsing, scan workflows plus local composite actions, enforce immutable action refs consistently, and cover the policy with failing tests. |
| Dependency ingress | Govern `pyproject.toml`, `uv.lock`, Dependabot updates, dependency review, private-index distribution lock, `pip-audit`, and Snyk SCA as one dependency intake system. |
| Runtime tool supply chain | Pin or verify actionlint, gitleaks, Snyk, CycloneDX tooling, Semgrep packs, and any other CI-installed executable fetched at runtime. |
| Artifact provenance | Ensure wheels, sdists, SBOMs, checksums, attestations, TestPyPI proofs, and PyPI publish proofs form a verifiable release packet. |
| Secret and OIDC minimization | Keep long-lived secrets out of publish paths; constrain `id-token: write`, publish environments, token-bearing jobs, and privileged triggers. |
| Cache trust boundaries | Classify every cache as untrusted-PR, trusted-main, or release/privileged; prevent cache save/restore paths from crossing those tiers. |
| SAST/SCA ownership | Define what SonarCloud blocks, what Snyk dependency scanning blocks, whether Snyk Code is duplicate or complementary SAST, and what `snyk monitor` means. |
| Concurrency governance | Add `concurrency` to PR-triggered workflows or encode explicit, tested exceptions. |
| Release protection | Preserve the current tag-triggered, same-run artifact release topology and add any missing risk-acceptance gate around `CONDITIONAL GO`. |
| Topology simplification | Decide whether `ci-build.yml`, standalone `sbom.yml`, and `.github/actions/run-gates` are canonical or redundant, then simplify without weakening evidence. |
| Governance docs coverage | Stop bypassing CI for governance docs or route docs-only governance changes through a targeted lightweight gate. |

### Explicitly NOT in scope

| Area | Exclusion |
|------|-----------|
| Publishing a release | This brief only prepares the spec. Release workflow execution remains unchanged until a spec is approved. |
| Rewriting the Python test strategy | The pytest suite and deselections are only touched if required by CI topology simplification. |
| Changing the canonical SDD chain | `/ai-brainstorm -> /ai-plan -> /ai-build -> /ai-pr` remains the implementation path. |
| Adding a new CI provider | This spec is about GitHub Actions only. |
| Broad dependency upgrades | Version bumps are allowed only when tied to pinning, verification, or an identified action deprecation. |
| Blanket cache deletion | This brief does not require deleting all CI caches; it requires deleting, disabling, or isolating caches that can bridge trust boundaries. |
| Replacing every security product | The spec should assign clear roles to existing scanners before adding new tools. |
| Full reproducible-build program | Reproducibility can be an open decision; this brief requires provenance and verification first. |

## 3. Diagnostic Snapshot

The project Constitution defines CI as the final authority and says CI should rerun local gates plus slower checks, including integration tests, SonarCloud, Scorecard, and SBOM diff (`CONSTITUTION.md:90-101`). The same supply-chain bar requires Sigstore keyless OIDC verification where available, SLSA provenance metadata, CycloneDX SBOM publication, OpenSSF Scorecard in CI, `--ignore-scripts` for npm/bun installs, and immutable commit SHAs for GitHub Actions (`CONSTITUTION.md:109-115`).

The dogfood manifest runs in regulated mode and defines the active quality thresholds, so CI policy gaps should be treated as governance defects rather than optional cleanup (`.ai-engineering/manifest.yml:81-90`). The manifest also leaves `cicd.standards_url` empty, so `/ai-pipeline` has no project-specific external standards document to consume for future pipeline generation (`.ai-engineering/manifest.yml:99-103`).

The Python package supply-chain surface is explicit: runtime dependencies live in `pyproject.toml`, dev scanning includes `pip-audit`, and the project already carries targeted CVE overrides for vulnerable transitive dependencies (`pyproject.toml:9-21`, `pyproject.toml:33-46`, `pyproject.toml:174-182`). The lockfile records package artifact URLs and hashes, so dependency integrity has a usable raw material, but the CI policy still needs to decide which dependency-change checks are blocking (`uv.lock:101-103`).

The project documents an optional enterprise artifact feed model that can enforce private-index distribution lock and avoid public PyPI fallback, but it is commented configuration rather than active CI policy (`pyproject.toml:48-90`). Dependabot is configured to open weekly grouped update PRs for both Python dependencies and GitHub Actions, but update automation is not the same as a merge-blocking dependency review policy (`.github/dependabot.yml:19-50`).

CODEOWNERS currently defaults all paths to maintainers and separately calls out the manifest, but it does not encode a distinct review boundary for workflows, release code, dependency manifests, lockfiles, or publish configuration (`.github/CODEOWNERS:4-12`). That is acceptable as a default ownership floor, but supply-chain-sensitive paths should have explicit review expectations in the spec.

`ci-check.yml` is the main PR and push workflow, but it ignores `docs/**` and several text/doc formats at trigger level (`.github/workflows/ci-check.yml:3-17`). That ignore list is risky because governance doctrine lives in docs, including the persistence doctrine cited by the bootstrap rules (`docs/persistence-doctrine.md:8-20`).

The CI workflow contains an anti-suppression job that runs `uv run no_suppression --root .` (`.github/workflows/ci-check.yml:135-145`). That job is not in `build-check.needs` and is also absent from `ci-check-result.needs`, so the aggregate CI check can ignore the anti-suppression result if branch protection keys only on `CI Result` (`.github/workflows/ci-check.yml:732-749`, `.github/workflows/ci-check.yml:761-784`).

The workflow sanity job installs actionlint by executing a script from the `rhysd/actionlint` `main` branch through `curl` and `bash` (`.github/workflows/ci-check.yml:432-444`). The same CI file installs Snyk with `npm install -g snyk --ignore-scripts`, which disables install scripts but still consumes the latest package rather than a pinned version (`.github/workflows/ci-check.yml:481-503`).

`ci-check.yml` uses `actions/cache` for `.ai-engineering/cache/gate/` in lint, typecheck, unit, and e2e jobs, with keys derived from `github.event.pull_request.base.sha || github.sha` and broad restore prefixes (`.github/workflows/ci-check.yml:80-87`, `.github/workflows/ci-check.yml:156-163`, `.github/workflows/ci-check.yml:188-195`, `.github/workflows/ci-check.yml:274-281`). That cache is a performance optimization today, but the spec must treat it as a supply-chain surface: if any future privileged trigger or trusted branch job writes a key that an untrusted PR can influence, the cache can become a persistence channel into later jobs.

The security job also caches `~/.semgrep` with a broad `semgrep-packs-${{ runner.os }}-` restore prefix (`.github/workflows/ci-check.yml:544-554`). `ci-build.yml` runs from `workflow_run`, enables `setup-uv` caching, and restores/saves `.ai-engineering/cache/gate/` from a workflow-run SHA plus broad fallback keys (`.github/workflows/ci-build.yml:3-35`). Those caches are not release artifacts, but they should still be classified by trust tier because `workflow_run` is a privileged trigger class in GitHub Actions security guidance.

The release workflow does not call `actions/cache` directly, but its release-readiness and release-build jobs call `./.github/actions/setup-env` (`.github/workflows/release.yml:113`, `.github/workflows/release.yml:221`). The setup composite enables `astral-sh/setup-uv` cache by default and passes that setting into `setup-uv` (`.github/actions/setup-env/action.yml:22-25`, `.github/actions/setup-env/action.yml:40-43`). Because the PyPI publish path later uses job-scoped OIDC (`.github/workflows/release.yml:365-379`, `.github/workflows/release.yml:455-468`), the spec should explicitly decide whether release jobs must run cold (`enable-cache: "false"`) or verify restored cache contents before any build material reaches attestation/publish.

The security job downloads a gitleaks tarball from GitHub Releases and extracts it without checking a checksum or signature (`.github/workflows/ci-check.yml:521-526`). Semgrep is pinned to `1.163.0`, but community pack aliases remain advisory and may fetch from the registry when credentials are present (`.github/workflows/ci-check.yml:555-566`, `.github/workflows/ci-check.yml:625-645`).

The local deterministic security stack is broader than Snyk/SonarCloud: the Constitution requires gitleaks, semgrep, and pip-audit in local/CI gates (`CONSTITUTION.md:90-101`), `.gitleaks.toml` exists with explicit allowlist path rules (`.gitleaks.toml:1-33`), and `.semgrep.yml` includes in-tree security rules such as hardcoded-secret detection (`.semgrep.yml:67-75`). The spec should preserve those deterministic gates while deciding which external scanners are blocking, advisory, or dashboard-only.

SonarCloud is already modeled as a code-conditional blocking gate: it waits for the test jobs, downloads coverage reports, runs `SonarSource/sonarqube-scan-action`, and appears in both `build-check.needs` and the `code_conditional` aggregate list (`.github/workflows/ci-check.yml:334-369`, `.github/workflows/ci-check.yml:732-749`, `.github/workflows/ci-check.yml:802-815`). Snyk is present but less governed: `snyk test` performs dependency/SCA scanning against an exported `requirements.txt`, `snyk code test` performs a SAST pass, and `snyk monitor` only runs on `main` (`.github/workflows/ci-check.yml:481-512`). The final aggregate currently classifies `snyk-security` as optional, so Snyk findings or Snyk execution failures are informational unless the spec promotes that job to a required class (`.github/workflows/ci-check.yml:761-784`, `.github/workflows/ci-check.yml:822-825`).

The standalone SBOM workflow installs `cyclonedx-bom` without a version pin before generating and uploading `sbom.cdx.json` (`.github/workflows/sbom.yml:45-55`). The release workflow separately generates a CycloneDX SBOM and checksum file inside its own build job (`.github/workflows/release.yml:280-309`), so SBOM production exists in at least two places. The release build also invokes `uv run --with cyclonedx-bom` without a version pin, so the release SBOM toolchain itself needs the same pin/verify treatment as the standalone SBOM path (`.github/workflows/release.yml:280-287`).

The release workflow already has strong artifact-integrity primitives: it builds distributions once, uploads release artifacts with short retention, generates SHA256 checksums, creates GitHub artifact attestations for `dist/*`, verifies those attestations with `gh attestation verify`, and carries publish proofs through TestPyPI and PyPI environments (`.github/workflows/release.yml:280-363`, `.github/workflows/release.yml:365-498`). The supply-chain gap is less about inventing provenance and more about making every artifact consumer verify the packet and deciding whether GitHub attestations are sufficient or whether PyPI/Sigstore package attestations are also required.

The workflow policy script declares generic policies for no `pull_request_target`, top-level permissions, job timeouts, PR concurrency, SHA pinning, and release topology preservation (`scripts/check_workflow_policy.py:1-9`). The script already has `workflow_triggers()` to handle PyYAML's boolean `on` key (`scripts/check_workflow_policy.py:54-65`), but `main()` still uses `data.get("on")` for the generic `pull_request_target` and PR-concurrency checks (`scripts/check_workflow_policy.py:423-444`).

The policy script does not currently inspect cache semantics: it does not reject `actions/cache` under privileged triggers, does not distinguish restore-only from save-capable cache usage, does not require trust-tier prefixes in cache keys, and does not flag `setup-*` action caches inside composites (`scripts/check_workflow_policy.py:1-9`, `scripts/check_workflow_policy.py:390-459`). That omission matters because cache writes happen outside normal source review and can persist beyond the PR that created them.

The SHA pinning policy exempts action prefixes including `actions/`, `pypa/`, `astral-sh/`, `SonarSource/`, `CycloneDX/`, `EndBug/`, and `dorny/` (`scripts/check_workflow_policy.py:20-30`). That exemption conflicts with the Constitution's broader requirement that GitHub Actions are pinned to immutable commit SHAs (`CONSTITUTION.md:109-115`), and the current checker only scans `.github/workflows/*.yml`, not composite actions (`scripts/check_workflow_policy.py:413-459`).

The local setup composite action contains external `uses:` references for `actions/setup-python` and `astral-sh/setup-uv` (`.github/actions/setup-env/action.yml:36-43`). Because the workflow policy script does not scan `.github/actions/**/action.yml`, drift inside composites is less protected than drift inside workflow files (`scripts/check_workflow_policy.py:413-459`).

Several PR-triggered workflows do not declare top-level `concurrency`: install smoke (`.github/workflows/install-smoke.yml:13-22`), install time budget (`.github/workflows/install-time-budget.yml:14-25`), and worktree fast second (`.github/workflows/worktree-fast-second.yml:19-30`). The policy says PR workflows must have concurrency, but the generic parser bug prevents that policy from firing for these files (`scripts/check_workflow_policy.py:423-444`).

The release workflow is stronger than the rest of the CI estate: it is triggered by `v*` tags or protected manual recovery inputs, uses top-level read-only permissions, and keys concurrency by tag or recovery version (`.github/workflows/release.yml:3-23`). Its build job validates package metadata, performs a clean local install smoke, creates `sbom.cdx.json`, and writes SHA256 checksums (`.github/workflows/release.yml:208-309`).

The release workflow then generates and verifies GitHub artifact attestations with job-scoped `contents: read`, `attestations: write`, and `id-token: write` permissions (`.github/workflows/release.yml:311-363`). TestPyPI and PyPI publish jobs use dedicated environments plus job-scoped `id-token: write`, and production PyPI waits for TestPyPI publish and install proof (`.github/workflows/release.yml:365-498`).

The release tests explicitly guard against `workflow_run` artifact reuse, require tag-triggered releases, assert job-scoped permissions, enforce build-once topology, and verify attestation commands are present (`tests/unit/workflows/test_release_workflow_policy.py:94-160`, `tests/unit/workflows/test_release_workflow_policy.py:175-230`). That release path should be preserved as the golden path while the surrounding CI is simplified.

`ci-build.yml` runs on `workflow_run` after `CI Check` succeeds on `main`, checks out the completed run's `head_sha`, builds with `uv build`, and uploads `dist` for 90 days (`.github/workflows/ci-build.yml:3-48`). The main CI also has a `build-check` job that runs `uv build`, and the release workflow builds release artifacts again from the release tag (`.github/workflows/ci-check.yml:732-759`, `.github/workflows/release.yml:208-309`).

`install-smoke.yml` intentionally records syscall evidence gaps on macOS and Windows via `continue-on-error` skip-note steps, and it skips the `os_release` re-probe assertion pending a spec-125 state migration follow-up (`.github/workflows/install-smoke.yml:306-352`, `.github/workflows/install-smoke.yml:356-405`). Those gaps may be acceptable, but their advisory status should be explicit in the spec rather than silently inherited.

`label-sync.yml` grants only `issues: write`, then performs `actions/checkout` and calls `EndBug/label-sync` with a pinned-looking SHA comment (`.github/workflows/label-sync.yml:9-23`). During the audit, remote tag verification showed the file's `EndBug/label-sync` SHA is not fetchable from that repository, so the spec should require a policy gate that verifies pinned refs are reachable rather than merely regex-shaped.

## 4. Architecture

The proposed change should preserve the release workflow's tag-triggered, same-run artifact architecture and improve the complete source-to-package supply chain with ten explicit layers.

1. **Source and ownership layer.** Workflows, composites, release scripts, dependency manifests, lockfiles, CODEOWNERS, and governance docs become first-class protected inputs. Ownership, review, and branch/tag protection expectations should be explicit rather than inferred from default maintainers.
2. **Workflow policy layer.** `scripts/check_workflow_policy.py` becomes the canonical static policy gate for GitHub Actions files. It must parse triggers through `workflow_triggers()` everywhere, scan `.github/workflows/*.yml` plus `.github/actions/**/action.yml`, enforce top-level permission blocks, job timeouts, PR concurrency or explicit exceptions, no `pull_request_target`, immutable action refs, and optional reachability checks for pinned action SHAs.
3. **Aggregate result layer.** `ci-check-result` becomes the trusted branch-protection signal only if every required job is listed exactly once and classified as always-required, code-conditional, PR-only, advisory, or intentionally skipped. The aggregate should be generated or tested from a single required-job manifest to prevent new jobs from being forgotten.
4. **Dependency ingress layer.** `pyproject.toml`, `uv.lock`, dependency override decisions, Dependabot PRs, dependency-review policy, `pip-audit`, and Snyk SCA should form one intake contract: every new/changed dependency is reviewed, scanned, and traceable to a lockfile hash or approved private index.
5. **Executable and action supply-chain layer.** Runtime tool installs move to pinned versions plus checksum/signature verification, or to dedicated pinned actions where appropriate. The spec should define one reusable helper or policy manifest for actionlint/gitleaks/Snyk/CycloneDX/Semgrep-style tool installation so checksum handling is not copy-pasted.
6. **Cache trust-boundary layer.** Every cache declaration must declare a trust tier and behavior: restore-only in untrusted PR jobs, save-only or restore/save in trusted main jobs, and disabled or cryptographically verified in release/OIDC jobs. The default posture should be: no `actions/cache` or implicit setup-action cache in release artifact production; no cache save from fork or `pull_request_target` code paths; no broad restore key that crosses `pr-`, `main-`, and `release-` prefixes; and a cache-bust/cleanup runbook when policy changes.
7. **Secret and OIDC layer.** Long-lived publish credentials stay out of workflows. `id-token: write` is job-scoped only to attestation and publish jobs, publish jobs use protected environments, and privileged triggers are fail-closed to canonical repo/tag/recovery contexts.
8. **Artifact provenance layer.** Wheels, sdists, SBOMs, checksums, attestations, TestPyPI install proof, PyPI publish proof, and release notes become one verified release packet. Consumers should verify provenance before publish/finalize, not merely upload evidence.
9. **Security-scanner ownership layer.** SonarCloud remains the code-quality/SAST quality gate unless the spec deliberately changes that role. Snyk must be classified separately as dependency SCA (`snyk test`), optional/complementary SAST (`snyk code test`), and dashboard snapshot (`snyk monitor`); the aggregate result should not call Snyk `covered` while treating the job as optional without an explicit risk decision.
10. **Topology and governance coverage layer.** The release workflow remains the only release artifact authority. `ci-build.yml`, `sbom.yml`, and `.github/actions/run-gates` must each be classified as canonical, advisory, or redundant, while CI path filters distinguish low-risk prose from governance doctrine.

This architecture keeps the deterministic plane deterministic: static workflow policy, aggregate CI requirements, and release topology are checked by code and tests, not by reviewer memory. It also aligns with the Constitution's supply-chain bar without expanding the release workflow's privileged footprint.

## 5. Evidence Catalog

| # | Finding | Evidence |
|---|---------|----------|
| E-1 | CI is final authority and must run slower checks. | `CONSTITUTION.md:90-101` |
| E-2 | Supply-chain bar requires OIDC/SLSA/SBOM/Scorecard and immutable SHA-pinned Actions. | `CONSTITUTION.md:109-115` |
| E-3 | Repo is in regulated gate mode. | `.ai-engineering/manifest.yml:81-90` |
| E-4 | Project CI standards URL is empty. | `.ai-engineering/manifest.yml:99-103` |
| E-5 | Main CI ignores docs paths. | `.github/workflows/ci-check.yml:3-17` |
| E-6 | Workflow sanity installs actionlint from a mutable branch script. | `.github/workflows/ci-check.yml:432-444` |
| E-7 | Anti-suppression job exists. | `.github/workflows/ci-check.yml:135-145` |
| E-8 | Anti-suppression is absent from build-check needs. | `.github/workflows/ci-check.yml:732-749` |
| E-9 | Anti-suppression is absent from final aggregate needs. | `.github/workflows/ci-check.yml:761-784` |
| E-10 | Snyk install is unpinned. | `.github/workflows/ci-check.yml:481-503` |
| E-11 | Gitleaks tarball install lacks checksum/signature verification. | `.github/workflows/ci-check.yml:521-526` |
| E-12 | Standalone SBOM workflow installs cyclonedx-bom unpinned. | `.github/workflows/sbom.yml:45-55` |
| E-13 | Policy helper handles PyYAML boolean `on`. | `scripts/check_workflow_policy.py:54-65` |
| E-14 | Generic policy path still uses `data.get("on")`. | `scripts/check_workflow_policy.py:423-444` |
| E-15 | Action-prefix exemptions weaken SHA policy. | `scripts/check_workflow_policy.py:20-30`, `scripts/check_workflow_policy.py:396-403` |
| E-16 | Policy scans only workflows, not composites. | `scripts/check_workflow_policy.py:413-459` |
| E-17 | Setup composite contains external Actions. | `.github/actions/setup-env/action.yml:36-43` |
| E-18 | Release workflow starts from tags or protected recovery inputs. | `.github/workflows/release.yml:3-23` |
| E-19 | Release build creates metadata validation, SBOM, and checksums. | `.github/workflows/release.yml:208-309` |
| E-20 | Release attestation job has job-scoped OIDC and verifies attestations. | `.github/workflows/release.yml:311-363` |
| E-21 | PyPI publish waits for TestPyPI path. | `.github/workflows/release.yml:365-498` |
| E-22 | Release packet finalization collects proofs and publishes GitHub Release assets. | `.github/workflows/release.yml:500-717` |
| E-23 | Release tests forbid `workflow_run` release artifacts. | `tests/unit/workflows/test_release_workflow_policy.py:147-165` |
| E-24 | Release tests enforce job topology and attestation. | `tests/unit/workflows/test_release_workflow_policy.py:175-230` |
| E-25 | `ci-build.yml` builds/upload `dist` after CI. | `.github/workflows/ci-build.yml:3-48` |
| E-26 | Install smoke has documented macOS/Windows evidence gaps and state migration TODO. | `.github/workflows/install-smoke.yml:306-405` |
| E-27 | Label sync uses checkout plus a pinned-looking EndBug ref under only `issues: write`. | `.github/workflows/label-sync.yml:9-23` |
| E-28 | CI gate caches use base/head-derived keys plus broad restore prefixes. | `.github/workflows/ci-check.yml:80-87`, `.github/workflows/ci-check.yml:156-163`, `.github/workflows/ci-check.yml:188-195`, `.github/workflows/ci-check.yml:274-281` |
| E-29 | Semgrep pack registry cache uses a broad OS-level restore prefix. | `.github/workflows/ci-check.yml:544-554` |
| E-30 | `ci-build.yml` is a `workflow_run` build that enables setup-uv cache and gate-cache restore/save. | `.github/workflows/ci-build.yml:3-35` |
| E-31 | Release readiness/build call setup-env; setup-env enables uv cache by default. | `.github/workflows/release.yml:113`, `.github/workflows/release.yml:221`, `.github/actions/setup-env/action.yml:22-25`, `.github/actions/setup-env/action.yml:40-43` |
| E-32 | Snyk runs dependency test, Snyk Code test, and main-only monitor. | `.github/workflows/ci-check.yml:481-512` |
| E-33 | Snyk is included in aggregate needs but classified optional. | `.github/workflows/ci-check.yml:761-784`, `.github/workflows/ci-check.yml:822-825` |
| E-34 | SonarCloud is blocking code-conditional SAST/quality signal. | `.github/workflows/ci-check.yml:334-369`, `.github/workflows/ci-check.yml:802-815` |
| E-35 | Current workflow policy does not classify cache usage or setup-action cache settings. | `scripts/check_workflow_policy.py:1-9`, `scripts/check_workflow_policy.py:390-459` |
| E-36 | Runtime dependencies, dev scanning deps, and CVE overrides live in pyproject. | `pyproject.toml:9-21`, `pyproject.toml:33-46`, `pyproject.toml:174-182` |
| E-37 | Lockfile entries include package artifact URLs and hashes. | `uv.lock:101-103` |
| E-38 | Private-index distribution lock exists only as commented operator guidance. | `pyproject.toml:48-90` |
| E-39 | Dependabot updates Python dependencies and GitHub Actions weekly. | `.github/dependabot.yml:19-50` |
| E-40 | CODEOWNERS defaults to maintainers and separately calls out only the manifest. | `.github/CODEOWNERS:4-12` |
| E-41 | Gitleaks and Semgrep are configured as deterministic secret/SAST gates. | `.gitleaks.toml:1-33`, `.semgrep.yml:67-75` |
| E-42 | Release SBOM generation also installs CycloneDX tooling without an explicit version pin. | `.github/workflows/release.yml:280-287` |
| E-43 | Release workflow already emits checksums, attestations, attestation verification, and publish proofs. | `.github/workflows/release.yml:289-363`, `.github/workflows/release.yml:393-410`, `.github/workflows/release.yml:481-498` |
| E-44 | PyPI/TestPyPI publish jobs use job-scoped OIDC and dedicated environments. | `.github/workflows/release.yml:365-388`, `.github/workflows/release.yml:448-477` |

## 6. Roadmap

### Milestone 1 — Policy gate correctness

Acceptance gates:

- `scripts/check_workflow_policy.py` uses `workflow_triggers()` for every trigger-sensitive check.
- Unit tests prove a PyYAML-loaded workflow with `pull_request_target` is rejected.
- Unit tests prove a PyYAML-loaded PR workflow without `concurrency` is rejected unless an explicit allowlist entry exists.
- The scanner includes `.github/actions/**/action.yml` in addition to `.github/workflows/*.yml`.
- The checker fails any non-local `uses:` reference that is not a 40-character commit SHA.
- Optional: pinned action refs are verified as reachable by `git ls-remote` in a slower CI job or cached policy check.

### Milestone 2 — Aggregate CI result integrity

Acceptance gates:

- `no-suppression` is included in `build-check.needs` if build-check remains the code gate.
- `no-suppression` is included in `ci-check-result.needs` and in the code-conditional required list.
- Tests assert every blocking job declared in `ci-check.yml` is represented in `ci-check-result`.
- Optional/advisory jobs are named explicitly and cannot fail silently without appearing in the aggregate report.
- Branch-protection documentation states whether to require `CI Result` only or individual gates plus `CI Result`.

### Milestone 3 — General supply-chain control-plane baseline

Acceptance gates:

- A supply-chain control matrix maps each surface to an owner, gate, evidence artifact, and escalation path: source/workflow changes, dependency changes, action references, runtime tool downloads, caches, secrets/OIDC, SBOM/provenance, and release publish.
- CODEOWNERS or repository rules explicitly protect `.github/**`, `.github/actions/**`, `pyproject.toml`, `uv.lock`, release workflow files, policy scripts, and governance docs.
- Dependabot update PRs for pip and GitHub Actions require the same aggregate CI result as human PRs and cannot bypass dependency/security gates.
- Dependency Review, Snyk SCA, and `pip-audit` have non-overlapping responsibilities and a documented blocking threshold for regulated mode.
- Dependency changes include lockfile integrity evidence and either pass public registry review or use the documented private-index distribution lock path.
- Scorecard is implemented or recorded as an explicit risk-accepted follow-up, because the Constitution already names it as part of CI.
- Release packet verification defines which artifacts must be verified before PyPI publish and which are final evidence only.

### Milestone 4 — Cache trust-boundary hardening

Acceptance gates:

- Every cache site is inventoried, including direct `actions/cache`, `actions/cache/restore`, `actions/cache/save`, and implicit setup-action caches such as `setup-uv`.
- Cache keys use trust-tier prefixes such as `pr-`, `main-`, and `release-`; `restore-keys` cannot fall back across trust tiers.
- Untrusted PR jobs use restore-only caching or no caching; save-capable cache actions run only on trusted `push`/`main` contexts after code has passed required gates.
- Release-readiness and release-build either pass `enable-cache: "false"` to `setup-env` or verify restored cache contents before any artifact is built, attested, or published.
- Jobs with `id-token: write`, publish environments, or release artifact authority do not restore mutable dependency/build caches unless an approved cryptographic cache signature scheme exists.
- Static policy rejects `actions/cache` in `pull_request_target`, `workflow_run` jobs that check out untrusted refs, and release/OIDC jobs unless an explicit reviewed exception names the trust boundary and verification mechanism.
- A cache incident runbook documents how to list, delete, and rotate GitHub Actions caches after suspected poisoning.

### Milestone 5 — Runtime tool reproducibility

Acceptance gates:

- actionlint installation is pinned to a release artifact and checksum, or replaced by a pinned action with immutable SHA.
- gitleaks installation verifies checksum or signature in both CI and release readiness paths.
- Snyk CLI is pinned to a specific version or moved to a pinned official action, preserving `--ignore-scripts` where npm is still used.
- Snyk dependency scanning (`snyk test`) has an explicit gate class: blocking high+ in regulated mode when `SNYK_TOKEN` is configured, or advisory with a recorded risk acceptance if the token is optional.
- Snyk Code (`snyk code test`) is either promoted as complementary SAST with SARIF/JSON evidence or documented as advisory/duplicate relative to SonarCloud; `snyk monitor` is documented as a main-branch dashboard snapshot, not a blocking SAST gate.
- `cyclonedx-bom` install is version-pinned in both standalone SBOM and release build paths.
- Semgrep community packs are pinned, mirrored, or explicitly kept advisory with a documented registry/authentication risk.
- Tests or policy checks fail on unpinned `uv pip install`, `uv run --with`, `npm install -g`, or `curl | bash` in workflows unless explicitly allowlisted with a rationale.
- Action transitive dependencies are inventoried or covered by an accepted exception so pinned top-level actions do not hide mutable nested supply-chain edges.

### Milestone 6 — Topology simplification

Acceptance gates:

- `release.yml` remains the only authority for release artifacts consumed by TestPyPI, PyPI, and GitHub Release.
- `ci-build.yml` is either removed, renamed to a documented advisory package-smoke workflow, or connected to a documented consumer that does not affect release.
- `sbom.yml` is either retained as per-commit advisory SBOM with pinned tooling or merged into a canonical supply-chain workflow.
- `.github/actions/run-gates` is either adopted by `ci-check.yml` where behavior matches or deleted to avoid dead abstraction.
- Any workflow deletion is a hard deletion with CHANGELOG coverage, not a shim.

### Milestone 7 — Governance docs and evidence gaps

Acceptance gates:

- Changes to governance docs run at least workflow sanity, content integrity, and relevant security policy checks.
- `install-smoke.yml` evidence gaps are either closed or explicitly classified as advisory with tracked follow-up IDs.
- `CONDITIONAL GO` release readiness either blocks publishing or requires a concrete risk-acceptance artifact in the release packet.
- OpenSSF Scorecard and SBOM diff expectations from the Constitution are either implemented in CI or the Constitution/brief records an approved follow-up decision.

## 7. Definition of Done

- `uv run python scripts/check_workflow_policy.py` fails on PR workflows without concurrency, `pull_request_target`, mutable action refs, unscanned composite drift, and unpinned executable installs where policy covers them.
- `ci-check-result` cannot pass while any required gate, including `no-suppression`, failed or was skipped unexpectedly.
- The release workflow continues to pass existing release topology tests and still uses tag-triggered, same-run artifacts.
- Every supply-chain-sensitive source path has explicit ownership/review coverage.
- Every GitHub Action `uses:` reference in workflows and composites is pinned to a reachable immutable commit SHA, with a plan for transitive action dependency visibility.
- Every runtime-downloaded executable is pinned and checksum/signature verified, or replaced by an immutable action.
- Dependency changes are governed by Dependabot/dependency-review/SCA policy and lockfile hash evidence.
- Release artifact jobs run without mutable caches or verify cache signatures before artifact creation.
- PR caches cannot save to cache keys that trusted main/release workflows restore.
- Snyk has an explicit blocking/advisory contract for dependency test, code test, and monitor, and the aggregate CI result implements that contract.
- SBOMs, checksums, provenance, and publish proofs are produced and verified according to a documented release-packet contract.
- Redundant build/SBOM workflows are removed or formally marked advisory with a documented consumer.
- Governance docs changes no longer bypass all relevant CI checks.
- CHANGELOG records any workflow deletion, hard rename, or behavior change that affects operators.

## 8. Quality Stamps

| Principle | Application |
|-----------|-------------|
| §10.1 KISS | One aggregate CI result, one release artifact authority, one policy checker for workflows and composites. |
| §10.2 YAGNI | Do not build a generalized CI framework; fix the known GitHub Actions surfaces in this repo. |
| §10.5 TDD | Add failing tests for policy parser, aggregate job membership, composite scanning, dependency-review expectations, cache trust tiers, release-packet verification, and unpinned install detection before changes. |
| §10.6 SDD | Promote this brief through `/ai-brainstorm`; do not patch workflows directly from the draft. |
| §10.7 Clean Code | Replace repeated shell install fragments with clear reusable helpers only when reuse reduces complexity. |
| §10.8 Hexagonal Architecture | Keep GitHub Actions syntax checks as adapters around deterministic policy rules, not embedded reviewer lore. |

## 9. Open Decisions

1. **CI branch protection target:** Should branch protection require only `CI Result`, or also individual gates for defense in depth?
2. **`ci-build.yml` fate:** Remove it, rename it as advisory package-smoke, or document a consumer for the uploaded `dist` artifact?
3. **Standalone SBOM workflow:** Keep per-commit advisory SBOM in addition to release SBOM, or consolidate supply-chain evidence into release plus a scheduled audit?
4. **Scorecard gap:** Implement OpenSSF Scorecard now, or amend the Constitution/roadmap with an explicit follow-up?
5. **Action reachability check:** Should CI verify pinned SHAs against GitHub remotes on every PR, nightly, or only in Dependabot/action update PRs?
6. **`CONDITIONAL GO`:** Should release readiness `CONDITIONAL GO` publish automatically, or require `ai-eng risk accept` evidence in the release packet?
7. **Policy exceptions:** Are any PR-triggered workflows intentionally allowed without `concurrency`, or should the rule be absolute?
8. **`run-gates` composite:** Should CI adopt it despite bespoke deselections and coverage variants, or delete it as unused abstraction?
9. **Release cache posture:** Should release-readiness and release-build disable all setup/dependency caches, or allow restore-only caches with cryptographic validation?
10. **PR cache posture:** Should PR workflows use restore-only caching, or should cache save be allowed for trusted same-repo branches after required gates pass?
11. **Snyk gate class:** In regulated mode, should missing `SNYK_TOKEN` fail CI, warn with risk acceptance, or keep the Snyk job optional?
12. **Snyk SAST overlap:** Should `snyk code test` be blocking alongside SonarCloud, advisory as secondary signal, or disabled to avoid duplicated SAST noise?
13. **Cache cleanup authority:** Which workflow or runbook owns cache listing/deletion after suspected poisoning or after changing cache key trust tiers?
14. **Supply-chain baseline target:** The Constitution names SLSA v1.0, while the external approved SLSA specification is now v1.2; should the spec align to current SLSA Build/Source tracks, target Build L1 immediately, target L2-style hosted/signed provenance, or define a repo-specific verifiable subset?
15. **Dependency review gate:** Should GitHub dependency-review-action be added as a blocking PR gate, or are Snyk SCA plus `pip-audit` enough for Python dependency changes?
16. **Explicit ownership paths:** Should `.github/**`, release workflows, `pyproject.toml`, `uv.lock`, and policy scripts get dedicated CODEOWNERS entries beyond the default maintainers rule?
17. **Package attestations:** Is GitHub artifact attestation sufficient for release artifacts, or should PyPI/Sigstore package attestations be added and verified by consumers?
18. **Action transitive dependencies:** Should the policy require an Actions Bill of Materials / transitive action inventory, or accept top-level SHA pinning plus Dependabot?
19. **Runner hardening and egress:** Should this spec add egress policy/harden-runner controls, or leave runner network controls to a follow-up?

## 10. Migration

This is a CI governance migration with no backwards-compatibility shims.

- Workflow deletions or renames are hard changes and must be recorded in CHANGELOG.
- Existing release tags and releases remain valid; release history is not rewritten.
- If `ci-build.yml` is removed, consumers must use release artifacts or a newly documented advisory package-smoke artifact.
- If per-commit SBOM remains, its artifact name and retention policy must stay documented.
- Pinned tool versions should be updated through normal dependency/update workflows, not by floating tags.
- Dependency intake changes are hard policy changes: update Dependabot/dependency-review/SCA expectations together, and document any private-index distribution lock requirements.
- Cache key migrations are hard cutovers: bust old keys, delete risky entries where possible, and do not rely on fallback restore keys from the previous trust tier.
- If release caches are disabled, accept the slower release path as the secure default rather than adding compatibility shims.
- Provenance/SBOM changes must preserve existing release history while requiring stronger evidence for new releases only.
- Any new policy allowlist must live in one explicit, reviewed location and include a reason plus expiry or follow-up.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tightening policy breaks currently passing workflows. | High | Medium | Land parser and policy tests first, then fix workflows in small commits. |
| Removing `ci-build.yml` breaks an undocumented consumer. | Medium | Medium | Search workflow artifacts and docs; if a consumer exists, document it before simplification. |
| Runtime checksum verification adds maintenance overhead. | Medium | Medium | Centralize version and checksum declarations in a helper or policy manifest. |
| Action reachability checks are slow or flaky. | Medium | Low | Run reachability nightly or only on workflow/action changes; keep regex pinning in PR hot path. |
| `CONDITIONAL GO` policy becomes too strict for urgent releases. | Medium | High | Allow release with explicit risk-acceptance artifact and follow-up, not silent success. |
| Governance-doc CI expansion increases docs-only PR cost. | Medium | Low | Route governance docs to lightweight sanity/content/security checks rather than full test matrix. |
| Adopting `run-gates` hides bespoke pytest deselections. | Medium | Medium | Only adopt where command parity is exact; otherwise delete the composite. |
| Cache poisoning bridges PR code into release artifacts. | Medium | Critical | Disable release caches or verify signed cache contents; split restore/save and trust-tier keys; reject privileged cache use by policy. |
| Broad restore keys revive old poisoned cache entries after a key migration. | Medium | High | Bust keys with new trust-tier prefixes and delete old entries through the cache cleanup runbook. |
| Making Snyk blocking fails CI when `SNYK_TOKEN` is absent. | Medium | Medium | Decide token absence policy in `/ai-brainstorm`; regulated mode should require either a token or explicit risk acceptance. |
| Duplicate SonarCloud and Snyk Code SAST creates noisy false positives. | Medium | Medium | Assign scanner ownership: SonarCloud blocking quality/SAST, Snyk Code complementary/advisory unless proven low-noise. |
| Compromised GitHub Action or moved tag bypasses source review. | Medium | Critical | Enforce full SHA pinning, reachability checks, Dependabot action updates, and optional transitive action inventory. |
| Malicious or vulnerable dependency enters through an approved update PR. | Medium | High | Require dependency review, Snyk/pip-audit thresholds, lockfile hash evidence, and owner review for manifest/lockfile changes. |
| Trusted Publishing is treated as sufficient by itself. | Medium | Critical | Keep publish jobs minimal, job-scope OIDC, use protected environments, verify release packet before publish, and protect workflow/tag changes. |
| SBOM/provenance exists but consumers never verify it. | Medium | High | Define release-packet verification gates before TestPyPI/PyPI/finalize and document consumer verification commands. |
| Private-index distribution lock guidance is mistaken for active protection. | Medium | Medium | Mark it as optional operator config unless CI verifies it; add an explicit decision for public PyPI vs private feed mode. |

## 12. References

External sources consulted on 2026-05-21:

- GitHub Docs, workflow syntax and granular `permissions`: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- GitHub Docs, automatic token authentication and least privilege: https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication
- GitHub Docs, security hardening and script injection guidance: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
- GitHub Docs, events that trigger workflows and `workflow_run` security warning: https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#workflow_run
- GitHub Docs, artifact attestations and required `id-token`/`attestations` permissions: https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations
- GitHub Docs, PyPI trusted publishing with OIDC and protected environments: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-pypi
- GitHub Actions cache action reference: https://github.com/actions/cache
- GitHub Actions checkout action reference: https://github.com/actions/checkout
- GitHub Docs, secure use reference for untrusted checkout, cache sharing, SHA pinning, OIDC, and Scorecards: https://docs.github.com/en/enterprise-cloud@latest/actions/reference/security/secure-use
- GitHub CodeQL query help, cache poisoning via caching untrusted files: https://codeql.github.com/codeql-query-help/actions/actions-cache-poisoning-direct-cache/
- SafeDep, TanStack cache poisoning incident analysis: https://safedep.io/tanstack-github-actions-cache-poisoning/
- Endor Labs, misconfigured CI workflow and npm supply-chain compromise: https://www.endorlabs.com/learn/how-a-misconfigured-ci-workflow-became-an-npm-supply-chain-compromise
- Snyk CLI command reference: https://docs.snyk.io/developer-tools/snyk-cli/commands
- Snyk CLI `test` command reference: https://docs.snyk.io/developer-tools/snyk-cli/commands/test
- Snyk CLI `monitor` command reference: https://docs.snyk.io/developer-tools/snyk-cli/commands/monitor
- SLSA v1.2 specification and provenance model: https://slsa.dev/spec/latest/
- Sigstore keyless signing overview: https://docs.sigstore.dev/cosign/signing/overview/
- PyPI Trusted Publishers security model: https://docs.pypi.org/trusted-publishers/security-model/
- PyPI publishing with a Trusted Publisher: https://docs.pypi.org/trusted-publishers/using-a-publisher/
- PyPI attestations security model: https://docs.pypi.org/attestations/security-model/
- GitHub dependency review documentation: https://docs.github.com/en/code-security/concepts/supply-chain-security/about-dependency-review
- OpenSSF Scorecard Action documentation: https://github.com/ossf/scorecard-action

Repo evidence is cited in sections 3 and 5 with `file:line` references.

## 13. Glossary

| Term | Meaning |
|------|---------|
| Aggregate CI result | The final `ci-check-result` job intended to summarize all required CI checks. |
| Blocking gate | A job whose failure must prevent merge or release. |
| Advisory workflow | A workflow that produces signal but does not block PR merge or release. |
| Immutable action ref | A GitHub Actions `uses:` reference pinned to a concrete commit SHA. |
| Runtime tool install | A workflow step that downloads or installs an executable during a job. |
| Same-run artifact | An artifact uploaded and downloaded within the same workflow run, not reused from another run. |
| Release packet | The final bundle of release proofs, checksums, attestations, notes, and publish evidence. |
| Reachability check | A verification that a pinned action SHA exists in the referenced remote repository. |
| Cache trust tier | A label for whether cache data is produced by untrusted PR code, trusted main-branch code, or release/privileged jobs. |
| Restore-only cache | A cache step that can read existing cache entries but cannot save modified contents at job completion. |
| Cache poisoning | Persisting malicious files in CI cache so a later trusted workflow restores and executes or packages them. |
| SCA | Software Composition Analysis; dependency vulnerability scanning such as `snyk test` or `pip-audit`. |
| SAST | Static Application Security Testing; code vulnerability scanning such as SonarCloud or `snyk code test`. |
| Snyk monitor | A Snyk snapshot for ongoing dashboard monitoring of open-source vulnerabilities; not a substitute for a blocking CI test and not supported for Snyk Code. |
| Supply-chain control plane | The deterministic policies and evidence that govern source, dependencies, actions, tools, caches, artifacts, and publishing. |
| Dependency ingress | The path by which third-party code enters the repo or release, including manifests, lockfiles, update PRs, private indexes, and SCA gates. |
| Provenance | Evidence describing how an artifact was built, by which workflow, from which inputs, and under which identity. |
| Trusted Publishing | PyPI OIDC publishing that exchanges a CI identity token for a short-lived publish credential instead of storing a long-lived API token. |
| Release packet verification | A gate that checks checksums, SBOM, attestations, install proof, and publish proof before release finalization. |
| Action transitive dependency | A nested action, script, runtime package, or container consumed by a top-level GitHub Action. |

## 14. Acceptance

- [ ] `/ai-brainstorm --consume github-actions-ci-hardening-simplification-brief.md` promotes a spec that preserves release workflow strengths.
- [ ] Policy parser uses `workflow_triggers()` for all trigger-sensitive logic.
- [ ] Policy checker scans `.github/workflows/*.yml` and `.github/actions/**/action.yml`.
- [ ] Policy checker rejects mutable or unreachable external action refs according to the approved performance tier.
- [ ] `no-suppression` is included in aggregate CI requirements.
- [ ] PR-triggered workflows either define `concurrency` or carry an explicit tested exception.
- [ ] `.github/**`, release workflows, dependency manifests, lockfiles, and policy scripts have explicit review/ownership expectations.
- [ ] Dependency ingress has a documented blocking policy across Dependabot, dependency review, Snyk SCA, `pip-audit`, and lockfile evidence.
- [ ] actionlint, gitleaks, Snyk, Semgrep pack usage, and CycloneDX installs are pinned or verified.
- [ ] GitHub Actions top-level and transitive dependency risks are either inventoried or explicitly risk-accepted.
- [ ] Every cache has a declared trust tier, and no PR/fork cache can be restored by release or OIDC publish jobs.
- [ ] Release-readiness and release-build run with caches disabled or with verified cache integrity.
- [ ] Snyk dependency test, Snyk Code test, and Snyk monitor have explicit blocking/advisory semantics in `ci-check-result`.
- [ ] SBOM, checksum, attestation, TestPyPI proof, PyPI proof, and release-packet verification semantics are documented and tested.
- [ ] Scorecard/SLSA/Sigstore/PyPI attestation expectations are implemented or explicitly deferred with risk acceptance.
- [ ] `ci-build.yml`, `sbom.yml`, and `run-gates` each have a documented canonical/advisory/deleted status.
- [ ] Governance docs changes run the approved minimum CI checks.
- [ ] Release workflow still passes existing release policy tests.
- [ ] `CONDITIONAL GO` publish semantics are decided and tested.
- [ ] CHANGELOG documents workflow deletions, hard renames, and operator-visible behavior changes.
