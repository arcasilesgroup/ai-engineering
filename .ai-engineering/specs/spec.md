---
spec: spec-143
slug: ai-engineering-release-version-cicd-pypi
title: Release Version CI/CD PyPI Spine — One Authority, Hardened Provenance, Trusted Publish
status: approved
effort: large
summary: Make `ai-eng release` the only framework release authority, hard-remove semantic-release writes, and align tag-triggered TestPyPI→PyPI publishing with full provenance, least-privilege CI, protected recovery, and release-packet evidence.
branch: codex/ai-engineering-release-version-cicd-pypi
source_brief: .ai-engineering/specs/drafts/ai-engineering-release-version-cicd-pypi-brief.md
target_dispatch: /ai-plan
mantra: "One release command, one version truth, one audited publish path."
approved_at: 2026-05-18
approved_by: operator
---

# spec-143 — Release Version CI/CD PyPI Spine

> Mantra: **One release command, one version truth, one audited publish path.**

## Summary

The framework source repo already has a release command, version registry, release-version guard, CI build workflow, artifact/SBOM generation, and PyPI Trusted Publishing workflow. The defect is not missing machinery; it is competing authority. `.ai-engineering/reference/cli-reference.md` says `ai-eng release <VERSION>` is the only supported write path, while `.github/workflows/ci-build.yml` can still use semantic-release to create tags and force-commit version changes directly to `main`. That dual-writer design violates SSOT-PD, bypasses release PR semantics, omits some governed version surfaces, and exposes the package publish path to avoidable supply-chain risk. This spec consolidates releases around `ai-eng release`, hard-removes semantic-release release authority, aligns `ai-eng release --wait` with an automatic `v*` tag-triggered `Release` workflow, validates the final artifact set through TestPyPI before production PyPI, and requires full provenance evidence in a GitHub Release packet with an NDJSON audit pointer.

## Goals

1. **Single release authority.** `ai-eng release <TARGET_VERSION>` is the only normal command or workflow allowed to mutate framework release state: package version, registry, root/template framework manifests, changelog, release branch, release tag, GitHub Release, and PyPI/TestPyPI publication.
2. **Semantic-release removed.** python-semantic-release configuration, dependency surface, and CI release write steps are hard-removed. No disabled semantic-release release path remains as confusing dead machinery.
3. **Version SSOT preserved.** `pyproject.toml` `[project].version` remains the version SSOT. `src/ai_engineering/version/registry.json`, root/template `framework_version` manifests, and `CHANGELOG.md` are governed derived release surfaces updated together through the release PR.
4. **Dry-run parity.** `ai-eng release <TARGET_VERSION> --dry-run` reports old version, target version, release branch, tag, governed changed files, changelog promotion state, workflow trigger, TestPyPI stage, PyPI stage, and release-packet outputs before any write.
5. **Guarded release PRs.** Release-version guard tests prove that governed version-surface changes fail outside `release/v<version>` and that release PRs fail unless the full file set is present or the guard file set is intentionally changed with tests.
6. **Tag-triggered governed publish.** `ai-eng release --wait` creates or verifies a `v<TARGET_VERSION>` tag after the release PR merges, and the `Release` workflow starts automatically from a `push` trigger on `v*` tags. The orchestrator monitors the run that this tag event creates.
7. **Manual dispatch is recovery-only.** `workflow_dispatch` remains on the `Release` workflow only as a protected recovery path. It requires protected environment approval and records recovery context; it is not documented or treated as a normal equivalent release path.
8. **Build once, publish same artifacts.** The release pipeline builds sdist and wheel once from the trusted release ref, verifies metadata/version parity, runs clean-environment install smoke, generates SHA256 checksums and CycloneDX SBOM, verifies artifact attestations, publishes that same artifact set to TestPyPI, installs from TestPyPI, and only then promotes the same artifact set to production PyPI.
9. **Full provenance and release packet.** Every release publishes a GitHub Release packet containing or linking the dist artifacts, checksums, CycloneDX SBOM, GitHub artifact attestations, PyPI publish attestations when emitted by Trusted Publishing, release-readiness result, changelog section, CI run URL, TestPyPI proof, PyPI URL, and recovery/manual-dispatch context when used. `.ai-engineering/state/framework-events.ndjson` records the canonical pointer to that packet.
10. **Supply-chain hardening.** Release jobs use least-privilege permissions, job-scoped OIDC, protected `testpypi` and `pypi` environments, immutable action SHA pins, timeouts, concurrency, no long-lived PyPI tokens, no untrusted PR artifacts, no privileged publish from fork/PR contexts, and fail-closed verification where required auth/config exists.
11. **Release readiness gate.** `/ai-verify --release <TARGET_VERSION>` or an equivalent deterministic release-readiness command returns GO before tag creation and before production PyPI publication. CONDITIONAL GO is allowed only when risk acceptance or explicitly advisory evidence is recorded in the release packet.
12. **Security scanner policy explicit.** Production releases block on in-tree Semgrep, gitleaks, and pip-audit now. Semgrep community packs remain conditional/advisory until registry authentication is configured; the release packet must state that condition rather than silently dropping the signal.
13. **Documentation and changelog updated.** CLI reference, release docs, workflow comments, and `CHANGELOG.md` document the hard migration away from semantic-release/manual CI commit-back and the governed release path.

## Non-Goals

- No actual PyPI/TestPyPI publication or concrete package version bump as part of this spec implementation. `<TARGET_VERSION>` remains execution input to `ai-eng release <TARGET_VERSION>`.
- No replacement of GitHub Actions as the CI/CD provider.
- No long-lived PyPI API tokens, username/password publishing, or secret-based normal PyPI publish path.
- No deprecation shim for semantic-release. The removed release path is a hard migration documented in `CHANGELOG.md`.
- No support for publishing artifacts built from pull request, fork, or other untrusted refs.
- No broad rewrite of unrelated CI jobs except where they participate in release/version mutation, artifact provenance, release readiness, or publish governance.
- No weakening of existing pre-commit, pre-push, CI, action-pinning, SBOM, SAST, dependency-audit, or risk-acceptance controls to make release publishing easier.
- No change to consumer-project install/update semantics except where release metadata in the packaged framework must remain coherent.
- No attempt to store large release artifacts in `state.db` or committed markdown archives.

## Decisions

### D-143-01 — `ai-eng release` is the sole release authority

`ai-eng release <TARGET_VERSION>` remains the only normal release write path. It owns release validation, version mutation, release PR creation, release PR merge waiting, tag creation, workflow monitoring, and release packet audit pointers.

**Rationale**: The CLI reference, release guard, tests, and existing mutator already encode this authority. Keeping an independent CI semantic-release writer would preserve the SSOT-PD violation and leave two paths capable of changing immutable release state.

### D-143-02 — semantic-release is hard-removed, not disabled

python-semantic-release release configuration and CI write behavior are removed from the framework release flow. The implementation must not leave a disabled or comments-only semantic-release release path behind.

**Rationale**: The user selected hard removal. A disabled release engine is operational ambiguity; the constitution forbids backwards-compatibility shims for removed or migrated content. The migration is documented in `CHANGELOG.md`.

### D-143-03 — `pyproject.toml` package version is the version SSOT

`pyproject.toml` `[project].version` remains the canonical writable package version. The registry, root/template framework manifests, and changelog are derived release surfaces updated atomically by the release PR.

**Rationale**: The current project uses static package metadata; PyPA requires project version metadata to be present statically or dynamically, and the repo already uses a static version. Keeping this SSOT minimizes churn and lets the existing guard and mutator evolve rather than invert the release model.

### D-143-04 — target version is execution input

The spec does not pick the next real framework version. `<TARGET_VERSION>` is supplied when the operator runs `ai-eng release <TARGET_VERSION>`.

**Rationale**: This spec designs and hardens the release system. Choosing the next package version belongs to release execution, not to the system-design spec.

### D-143-05 — `Release` workflow starts from `push` on `v*` tags

The governed publish workflow starts automatically when the release command creates or verifies a `v<TARGET_VERSION>` tag after the release PR merges. `ai-eng release --wait` monitors the workflow run for that tag's commit.

**Rationale**: This directly aligns existing orchestrator behavior with GitHub Actions. It avoids creating a GitHub Release before PyPI succeeds and avoids adding a separate workflow-dispatch API dependency to the orchestrator.

### D-143-06 — manual `workflow_dispatch` is protected recovery only

`workflow_dispatch` remains on the `Release` workflow only as a recovery path. It requires protected environment approval and records recovery context in the release packet and audit event.

**Rationale**: Operators need a way to recover from a failed or expired tag-triggered run, but the normal path must remain one governed path. Recovery must be visible and reviewable, not an equivalent hidden release path.

### D-143-07 — TestPyPI runs after merge/tag and before production PyPI

TestPyPI publication and install verification run on the final artifact set after the release PR merges and tag-triggered release starts, before production PyPI publication.

**Rationale**: This validates the exact artifacts intended for production while avoiding TestPyPI version exhaustion on every release PR. Release PR CI still builds and validates artifacts without publishing.

### D-143-08 — full provenance set is mandatory when available

The release evidence set includes GitHub artifact attestations, PyPI Trusted Publishing attestations when the platform emits them, CycloneDX SBOM, SHA256 checksums, metadata/version checks, install smoke results, and verification output before production publish. If a supported attestation mechanism is missing or unverifiable, production publish blocks; if a mechanism is genuinely unsupported by the platform, the release packet records that unsupported status explicitly.

**Rationale**: The user emphasized supply-chain security and governance. The release surface is a package-compromise vector; minimum viable OIDC publish is not enough for the framework's regulated-environment promise.

### D-143-09 — GitHub Release assets are the canonical release packet store

The release packet is stored as GitHub Release assets and links attached to the release tag. `.ai-engineering/state/framework-events.ndjson` records an audit pointer to that packet.

**Rationale**: Release assets are public, discoverable next to the tag, and suitable for generated artifacts. `state.db` is inappropriate for large provenance artifacts, and a markdown archive would require post-release commits and duplicate CI-generated evidence.

### D-143-10 — privileged publish jobs never consume untrusted artifacts

Release publish jobs must build from or download artifacts produced on trusted release refs only, must not use artifacts uploaded by pull request/fork contexts, and must scope `id-token: write` to publish jobs rather than the entire workflow.

**Rationale**: The user explicitly called out preventing CI/CD changes from injecting hacks. Artifact substitution and overbroad OIDC are high-impact supply-chain failure modes.

### D-143-11 — release readiness can be CONDITIONAL only with evidence

Release readiness returns GO or NO-GO by default. CONDITIONAL GO is allowed only when the condition is explicit, traceable, and recorded in the release packet, such as advisory Semgrep community-pack status before registry authentication exists.

**Rationale**: Silent degradation is worse than a visible conditional release. This preserves progress while keeping auditors and operators aware of unresolved release posture.

### D-143-12 — changelog validation is strengthened for release quality

The release path validates a Keep a Changelog-compatible target section, date, non-empty release notes, and explicit breaking-change placement when release-path semantics change.

**Rationale**: The current changelog helper only checks `[Unreleased]` and duplicate target sections. Release hardening needs deterministic documentation quality, especially for hard-removing semantic-release from the release path.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| Release workflow refactor creates a new supply-chain injection path | Medium | Critical | Enforce trusted refs only, no PR/fork artifacts, job-scoped OIDC, protected environments, SHA-pinned actions, artifact attestation verification, and workflow-policy tests. |
| Tag-triggered workflow does not match orchestrator monitor lookup | Medium | High | Add tests/policy checks proving `ai-eng release --wait` creates the event that the `Release` workflow listens to and monitors by tag SHA. |
| Removing semantic-release breaks an unknown maintainer habit | Medium | Medium | Hard migration documented in `CHANGELOG.md` and release docs; no shim, but `ai-eng release --dry-run` provides the supported replacement workflow. |
| TestPyPI or PyPI Trusted Publishing configuration is absent | Medium | High | Fail with named environment/config error before production PyPI; manual project setup remains operator-owned but documented. |
| TestPyPI version immutability blocks rerun after a partial failure | Medium | Medium | Run TestPyPI only after final tag; require dry-run and artifact verification before publish; document recovery via new target version or explicit recovery path. |
| Attestations are generated but not verified | Medium | High | Verification is an acceptance criterion before production PyPI, and results must appear in the release packet. |
| Community Semgrep packs remain advisory longer than intended | Medium | Medium | Release packet records CONDITIONAL GO while unauthenticated; once registry auth exists, release policy can fail-closed without changing the architecture. |
| Manual recovery dispatch becomes a shadow normal path | Low | High | Keep it protected, require recovery context, and document tag push as the only normal governed path. |
| CI action SHA pins drift or are replaced with mutable tags | Medium | High | Workflow policy tests block mutable action references in release-related workflows. |
| Changelog stricter validation blocks urgent release | Medium | Medium | Block by default; risk acceptance can be recorded only through canonical risk workflow and linked in the release packet. |

## References

- doc: .ai-engineering/specs/drafts/ai-engineering-release-version-cicd-pypi-brief.md
- doc: .ai-engineering/reference/cli-reference.md:21-35 — documented release command and sole write-path rule.
- doc: src/ai_engineering/cli_commands/release.py:18-105 — CLI release entry point and phase output.
- doc: src/ai_engineering/release/orchestrator.py:121-318 — current release phases and validation.
- doc: src/ai_engineering/release/orchestrator.py:543-559 — current monitor lookup for workflow `Release` by tag SHA.
- doc: src/ai_engineering/release/version_bump.py:191-273 — version mutation and registry sync.
- doc: src/ai_engineering/release/changelog.py:35-76 — current changelog validation and promotion helper.
- doc: src/ai_engineering/policy/release_version_guard.py:12-109 — guarded release file set and branch policy.
- doc: tests/unit/test_release_version_guard.py:71-94 — current full release PR file-set test.
- doc: .github/workflows/ci-build.yml:50-228 — competing semantic-release/tag/main commit-back path.
- doc: .github/workflows/release.yml:1-233 — current manual artifact-driven PyPI workflow.
- doc: .github/workflows/ci-check.yml:513-698 — current security and content-integrity gates.
- doc: .codex/skills/ai-verify/SKILL.md:63-69 — release-readiness gate contract.
- doc: CONSTITUTION.md:85-115 — mandatory gates and supply-chain bar.
- doc: Python Packaging User Guide, `pyproject.toml` specification — https://packaging.python.org/en/latest/specifications/pyproject-toml/
- doc: Python Packaging User Guide, version specifiers — https://packaging.python.org/en/latest/specifications/version-specifiers/
- doc: PyPI Trusted Publishers — https://docs.pypi.org/trusted-publishers/
- doc: PyPI publishing with a Trusted Publisher — https://docs.pypi.org/trusted-publishers/using-a-publisher/
- doc: PyPI digital attestations — https://docs.pypi.org/attestations/
- doc: GitHub Docs, build/test Python and publish to PyPI — https://docs.github.com/en/actions/tutorials/build-and-test-code/python#publishing-to-pypi
- doc: GitHub Docs, artifact attestations — https://docs.github.com/en/actions/concepts/security/artifact-attestations
- doc: PyPA `gh-action-pypi-publish` — https://github.com/pypa/gh-action-pypi-publish

## Open Questions

None. The brainstorm resolved the release authority, semantic-release disposition, TestPyPI timing, workflow trigger, Semgrep community-pack policy, manual dispatch policy, provenance set, release-packet store, and target-version handling.
