---
spec: spec-152
slug: github-actions-supply-chain-hardening
title: GitHub Actions CI/CD Supply-Chain Hardening and Simplification
status: approved
effort: large
summary: "Harden ai-engineering's own GitHub Actions estate: seal the fail-open CI aggregate, fix and extend the workflow-policy gate to composites, pin every action and tool, isolate caches by trust tier, make Snyk blocking, delete dead workflows, and add Scorecard, SLSA L2 provenance and harden-runner."
---

# GitHub Actions CI/CD Supply-Chain Hardening and Simplification

## Summary

ai-engineering's release workflow is strongly governed, but the surrounding
CI estate has supply-chain holes that reviewer memory currently papers over.
The aggregate `CI Result` is **fail-open**: the `no-suppression` job exists
(`ci-check.yml:143`) yet appears in no `needs` list and no required-job array,
so a failed or skipped anti-suppression run is invisible to branch protection.
The static workflow-policy gate has a live parser bug — `main()` reads raw
`data.get("on")` (`check_workflow_policy.py:426-438`) so PyYAML's boolean `on:`
key silently bypasses the `pull_request_target` and PR-concurrency checks — and
it never scans composite actions, cache semantics, or runtime tool installs.
Two workflows are dead weight: `ci-build.yml` uploads a `dist` artifact with
90-day retention that **no consumer reads**, and `.github/actions/run-gates` is
referenced by **nothing**. Runtime tools are partially unpinned (actionlint via
`curl|bash` off `main`, Snyk via unpinned `npm i -g`, cyclonedx-bom unpinned in
two places). Caches use broad `${os}-` restore keys that bridge PR, main, and
release trust tiers — a cache-poisoning persistence channel. Snyk runs only when
`SNYK_TOKEN` is set and is classified optional, so with no token CI is always
green. This spec closes the full source-to-PyPI supply chain for **this repo's
own dogfood pipeline**, preserves the release workflow's tag-triggered same-run
artifact topology, and simplifies the estate by deleting redundant surfaces.

Verified 2026-05-22: commit `15e2c4f1` (spec-147 wave 1) hardened only local
gates and hooks — it touched **zero** `.github/workflows/*` files — so every CI
gap in the source brief is still live.

## Goals

- **G1 — Trustworthy aggregate.** `ci-check-result` cannot pass while any
  blocking job (including `no-suppression`) failed or was skipped unexpectedly,
  and a test proves every blocking job in `ci-check.yml` is represented in the
  aggregate.
- **G2 — Correct, broader policy gate.** `check_workflow_policy.py` parses
  triggers through `workflow_triggers()` everywhere, scans
  `.github/actions/**/action.yml` in addition to `.github/workflows/*.yml`, and
  enforces SHA pinning, cache trust tiers, and unpinned-install detection.
- **G3 — Pinned, verified supply chain.** Every `uses:` reference (workflows +
  composites) is a reachable immutable commit SHA, and every runtime-downloaded
  executable is version-pinned and checksum/signature-verified or replaced by a
  pinned action.
- **G4 — Cache trust isolation.** Every cache declares a trust tier; PR/fork
  caches cannot be restored by main, release, or OIDC publish jobs.
- **G5 — Snyk is a blocking gate.** `snyk-security` is promoted from optional to
  required; `SNYK_TOKEN` is provisioned; current findings are triaged and fixed
  or risk-accepted.
- **G6 — Governed dependency ingress.** Dependabot, GitHub dependency-review,
  Snyk SCA, `pip-audit`, and `uv.lock` hash evidence form one documented intake
  contract with non-overlapping blocking thresholds.
- **G7 — Explicit ownership.** Supply-chain-sensitive paths have dedicated
  CODEOWNERS entries beyond the wildcard default.
- **G8 — Simplified topology.** `ci-build.yml` and `run-gates` are hard-deleted;
  `release.yml` remains the sole release-artifact authority; CHANGELOG records
  the breakage.
- **G9 — Aspirational supply-chain bar.** OpenSSF Scorecard, PyPI/Sigstore
  package attestations, SLSA L2-style signed provenance, and
  `step-security/harden-runner` egress control are all implemented in this spec.
- **G10 — Governance-docs coverage.** Docs-only changes run a lightweight
  sanity + content-integrity + security gate instead of bypassing CI entirely.

## Non-Goals

- **Not changing what clients consume.** This hardens ai-engineering's own
  `.github/` estate only. It must NOT alter `/ai-pipeline` outputs, installer
  templates, generated mirrors, or any framework logic that downstream client
  projects receive. CI hardening is project-internal dogfood (D-152-01).
- **Not publishing a release.** The release workflow's execution is unchanged
  until this spec ships; no new release is cut by this work.
- **Not adding a new CI provider.** GitHub Actions only; no Azure Pipelines or
  other provider work.
- **Not rewriting the pytest strategy.** Test selection/deselection is touched
  only where CI topology simplification forces it.
- **Not broad dependency upgrades.** Version bumps are allowed only when tied to
  pinning, checksum verification, or an identified action deprecation.
- **Not blanket cache deletion.** Caches that cannot bridge trust boundaries may
  remain; only tier-crossing caches are isolated or removed.
- **Not a generalized CI framework.** Fix the known surfaces in this repo; do
  not build reusable CI tooling for arbitrary projects (YAGNI).

## Decisions

- **D-152-01 — Dogfood-CI-only scope boundary.** All changes target this repo's
  own `.github/**`, `scripts/`, and CI-policy surfaces. No change leaks into
  `/ai-pipeline` generators, installer templates, or client-consumed framework
  logic.
  **Rationale**: operator directive — "snyk y la parte de CI es algo de este
  proyecto, que no afecte a la lógica de ai-engineering que consumen los
  clientes." Keeps the framework product stable while the dogfood pipeline
  hardens.
- **D-152-02 — Seal the aggregate.** Add `no-suppression` to `build-check.needs`
  and `ci-check-result.needs`, and into the code-conditional required array. Add
  a test asserting every blocking job declared in `ci-check.yml` is represented
  in `ci-check-result`.
  **Rationale**: branch protection keys on `CI Result`; a required job that the
  aggregate never evaluates is a silent fail-open hole (verified at
  `ci-check.yml:143,755-808,819-840`).
- **D-152-03 — Branch protection requires `CI Result` only.** Document that the
  single required check is `CI Result`; individual-gate requirements are
  optional defense-in-depth, not mandated.
  **Rationale**: KISS — one trustworthy aggregate beats N brittle required
  checks, once D-152-02 makes it trustworthy.
- **D-152-04 — Policy parser correctness + composite scan.** `main()` uses
  `workflow_triggers()` for the `pull_request_target` and PR-concurrency checks;
  the scanner globs `.github/actions/**/action.yml` in addition to workflows.
  **Rationale**: PyYAML parses bare `on:` as the boolean key `True`, so
  `data.get("on")` returns `None` and both checks silently pass; composites
  carry external `uses:` that are currently unscanned.
- **D-152-05 — Hardened SHA pinning, narrowed exemptions.** Require a 40-char
  commit SHA for every non-local `uses:` in workflows and composites; remove the
  broad first-party prefix exemptions (`actions/`, `github/`, `pypa/`,
  `astral-sh/`, `SonarSource/`, `CycloneDX/`, `EndBug/`, `dorny/`) or narrow them
  to a documented, minimal, reviewed allowlist with rationale.
  **Rationale**: Constitution §Supply-chain-bar requires immutable SHA pinning
  with no blanket vendor exemption (`CONSTITUTION.md:109-115`).
- **D-152-06 — Reachability off the hot path.** Verify pinned-SHA reachability
  via `git ls-remote` nightly and on workflow/action-change PRs only; the PR hot
  path keeps the regex pin check.
  **Rationale**: remote calls are slow/flaky; the audit found a `label-sync.yml`
  ref that is regex-shaped but not fetchable, so reachability is needed — just
  not on every PR.
- **D-152-07 — Snyk is mandatory and blocking.** Provision `SNYK_TOKEN`; promote
  `snyk-security` from `optional` to required (code-conditional). `snyk test`
  (SCA) blocks high+; `snyk code test` is advisory secondary SAST (SonarCloud
  remains primary); `snyk monitor` stays a main-only dashboard snapshot.
  Implementation runs Snyk, triages findings, and fixes or risk-accepts each.
  **Rationale**: operator directive — "snyk es un paso obligatorio, debemos
  saber que fallos o security issues lanza y arreglarlo." Silent-green-without-
  token (`ci-check.yml:509,847-850`) is the defect this removes.
- **D-152-08 — Snyk fail-closed on trusted contexts; documented fork exception.**
  On push/main and same-repo PRs the token is present and the gate is required.
  Fork PRs (where GitHub withholds secrets) are covered by the post-merge main
  run with a documented advisory window, not a silent skip.
  **Rationale**: GitHub does not expose `secrets.SNYK_TOKEN` to fork PRs;
  context-scoped enforcement replaces the current always-skip behavior.
- **D-152-09 — Cache trust tiers.** Every cache key carries a `pr-`, `main-`, or
  `release-` prefix; `restore-keys` cannot fall back across tiers. PR jobs are
  restore-only; cache save runs only on trusted push/main after required gates
  pass.
  **Rationale**: broad `gate-cache-${os}-` and `semgrep-packs-${os}-` restore
  keys bridge PR↔main↔release today, a cache-poisoning persistence channel
  (`ci-check.yml:89-95,165-203,283-289,572-577`).
- **D-152-10 — Release jobs run cold.** `release-readiness` and `release-build`
  call `setup-env` with `enable-cache:false`; no OIDC/publish job restores a
  mutable dependency/build cache before artifacts are built and attested.
  **Rationale**: `setup-env` defaults `enable-cache:true`
  (`setup-env/action.yml:22-25,40-43`); restoring mutable cache into a publish
  path can poison release artifacts.
- **D-152-11 — Static cache policy in the checker.** `check_workflow_policy.py`
  rejects `actions/cache` (and `/restore`, `/save`) under `pull_request_target`,
  untrusted `workflow_run` checkout jobs, and release/OIDC jobs unless an
  explicit reviewed exception names the trust boundary; it flags setup-action
  caches inside composites and requires trust-tier key prefixes.
  **Rationale**: cache writes happen outside normal source review and persist
  beyond the PR that created them.
- **D-152-12 — Runtime tool pinning + verification.** actionlint is pinned to a
  release artifact + checksum or replaced by a pinned-SHA action; gitleaks adds
  checksum/signature verification; Snyk CLI is version-pinned (keeping
  `--ignore-scripts`); `cyclonedx-bom` is version-pinned in `sbom.yml` and
  `release.yml`; semgrep packs are pinned/mirrored or explicitly advisory. One
  reusable install helper centralizes version+checksum declarations, and the
  policy gate fails unpinned `curl|bash`, `npm install -g`, `uv run --with`, and
  `uv pip install` unless allowlisted with rationale.
  **Rationale**: every runtime-fetched executable is a supply-chain ingress;
  centralization prevents copy-pasted checksum drift (Clean Code §10.7).
- **D-152-13 — Topology simplification.** Hard-delete `ci-build.yml` (orphaned
  `dist`, zero consumers) and `.github/actions/run-gates` (unreferenced). Retain
  `sbom.yml` as per-commit advisory SBOM with pinned tooling (or merge into a
  canonical supply-chain workflow — see OQ3). CHANGELOG records the deletions.
  **Rationale**: dead workflows and abstractions are KISS/YAGNI violations and
  unscanned attack surface (verified zero consumers/references 2026-05-22).
- **D-152-14 — Dependency ingress contract.** Add `actions/dependency-review-
  action` (pinned SHA) as a blocking PR gate; document non-overlapping
  thresholds for dependency-review vs Snyk SCA vs `pip-audit`; require Dependabot
  PRs to pass the same `CI Result`; require `uv.lock` hash evidence for
  dependency changes.
  **Rationale**: one governed intake closes the gap where update PRs bypass
  human-PR security gates.
- **D-152-15 — Explicit ownership.** CODEOWNERS gains dedicated entries for
  `.github/**`, `.github/actions/**`, release workflow files, `pyproject.toml`,
  `uv.lock`, `scripts/check_workflow_policy.py`, and governance docs.
  **Rationale**: supply-chain-sensitive paths need an explicit review boundary
  beyond the wildcard default (`CODEOWNERS:6`).
- **D-152-16 — OpenSSF Scorecard in CI.** Wire `ossf/scorecard-action` (pinned
  SHA) into CI with results published; classify required-or-advisory per
  regulated thresholds.
  **Rationale**: Constitution already names Scorecard as part of the CI
  supply-chain bar; low effort, operator-selected.
- **D-152-17 — PyPI/Sigstore package attestations.** Add PyPI attestations and
  Sigstore signing beyond the existing GitHub artifact attestation; release
  consumers verify them before finalize.
  **Rationale**: strengthens publish provenance beyond build-time attestation;
  operator-selected.
- **D-152-18 — SLSA L2 signed provenance.** Move from the current GitHub-
  attestation (~L1) posture to L2-style signed provenance, and update the
  Constitution's SLSA reference (currently v1.0) to the targeted current track
  as part of this change so the stated bar stays honest.
  **Rationale**: operator selected maximal provenance; the Constitution version
  note must not drift from the implemented reality.
- **D-152-19 — harden-runner egress control.** Add `step-security/harden-runner`
  (pinned SHA) across CI and release jobs with an egress policy.
  **Rationale**: constrains network exfiltration from a compromised step;
  operator-selected.
- **D-152-20 — `CONDITIONAL GO` requires risk acceptance.** Release-readiness
  `CONDITIONAL GO` does not auto-publish; it requires an `ai-eng risk accept`
  artifact present in the release packet.
  **Rationale**: regulated mode forbids silent conditional publish; risk
  acceptance must be owner-attributed and spec-referenced.
- **D-152-21 — Concurrency allowlist, not absolute.** PR-triggered workflows
  must declare `concurrency` OR appear in a single reviewed allowlist entry with
  rationale and expiry; the rule and its allowlist are test-covered.
  **Rationale**: some workflows may legitimately opt out; exceptions must be
  explicit, reviewed, and tested rather than silently tolerated by a parser bug.
- **D-152-22 — Governance-docs CI floor.** Docs-only changes (including
  `docs/**`) run a lightweight sanity + content-integrity + relevant security
  policy gate instead of being ignored at trigger level.
  **Rationale**: governance doctrine lives in docs (e.g.
  `docs/persistence-doctrine.md`); a full CI bypass for it is a coverage hole
  (`ci-check.yml:3-17`).
- **D-152-23 — Release-packet verification contract.** Document which artifacts
  (wheels, sdists, SBOM, checksums, attestations, TestPyPI proof) MUST be
  verified before PyPI publish vs which are final evidence only; consumers
  verify provenance, not merely upload it.
  **Rationale**: SBOM/provenance with no enforced verification step is evidence
  theater.
- **D-152-24 — TDD-first delivery.** A failing test lands before each behavior
  change: policy parser (boolean `on:`), aggregate membership, composite
  scanning, cache-tier prefixes, unpinned-install detection, dependency-review
  presence, and release-packet verification.
  **Rationale**: §10.5 TDD; CI policy is the canonical deterministic surface that
  must be test-locked so regressions fail loud.
- **D-152-25 — Hard migration, no shims.** Workflow deletions/renames and
  cache-key migrations are hard cutovers; old cache keys are busted; CHANGELOG
  documents every operator-visible breakage.
  **Rationale**: CONSTITUTION §13.3 forbids backwards-compat shims for
  renamed/deleted content.

## Acceptance Criteria

- **AC1 (G1, D-152-02)** — `ci-check-result` fails when `no-suppression` (or any
  blocking job) is `failure` or unexpectedly `skipped`; a unit test enumerates
  every blocking job in `ci-check.yml` and asserts each appears in the aggregate
  `needs` + a required-job array.
- **AC2 (G2, D-152-04/05)** — `check_workflow_policy.py` rejects a PyYAML-
  boolean-`on:` workflow that uses `pull_request_target`, rejects a PR workflow
  missing `concurrency` unless allowlisted, scans `.github/actions/**/action.yml`,
  and fails any non-local `uses:` that is not a 40-char SHA; all four have tests.
- **AC3 (G2, D-152-11)** — the policy gate rejects `actions/cache` under
  `pull_request_target`/untrusted `workflow_run`/release-OIDC jobs without a
  named exception, flags setup-action caches in composites, and requires
  trust-tier key prefixes; tests cover each.
- **AC4 (G3, D-152-12)** — actionlint, gitleaks, Snyk CLI, `cyclonedx-bom`, and
  semgrep packs are each pinned/verified or explicitly advisory; the policy gate
  fails unpinned `curl|bash`, `npm install -g`, `uv run --with`, and
  `uv pip install` unless allowlisted; tests cover detection.
- **AC5 (G3, D-152-06)** — every `uses:` in workflows + composites is a 40-char
  SHA; a nightly/action-change reachability job verifies SHAs via `git ls-remote`
  and fails on an unreachable ref.
- **AC6 (G4, D-152-09/10)** — no PR/fork cache key can be restored by a main,
  release, or OIDC publish job; release-readiness and release-build run with
  caches disabled; tests assert the trust-tier prefixes and the release cold-
  cache setting.
- **AC7 (G5, D-152-07/08)** — `snyk-security` is in the required aggregate
  arrays; `snyk test` blocks high+ on trusted contexts; current Snyk findings are
  fixed or carry an `ai-eng risk accept` record; the fork-PR exception is
  documented.
- **AC8 (G6/G7, D-152-14/15)** — `dependency-review-action` is a blocking PR
  gate; CODEOWNERS has explicit supply-chain-path entries; the
  dependency-review/Snyk/`pip-audit` threshold matrix is documented; Dependabot
  PRs run the same `CI Result`.
- **AC9 (G8, D-152-13/25)** — `ci-build.yml` and `.github/actions/run-gates` are
  deleted; `release.yml` remains the only release-artifact authority and still
  passes `test_release_workflow_policy.py`; CHANGELOG records the deletions.
- **AC10 (G9, D-152-16/17/18/19)** — Scorecard runs in CI; PyPI/Sigstore
  attestations are produced and verified; SLSA L2-style signed provenance is
  generated and the Constitution SLSA reference is updated; `harden-runner` runs
  with an egress policy across CI + release.
- **AC11 (G10, D-152-22)** — a docs-only change triggers the lightweight
  sanity/content/security gate and does not silently bypass all of CI.
- **AC12 (D-152-20/23)** — `CONDITIONAL GO` release-readiness blocks publish
  absent a risk-acceptance artifact; the release-packet verification contract is
  documented and a test asserts the verification step exists before publish.

## Affected Surfaces

- Workflows: `.github/workflows/ci-check.yml`, `release.yml`, `sbom.yml`,
  `install-smoke.yml`, `install-time-budget.yml`, `worktree-fast-second.yml`,
  `label-sync.yml`; **deleted**: `ci-build.yml`.
- Composites: `.github/actions/setup-env/action.yml`; **deleted**:
  `.github/actions/run-gates/`.
- Policy + tests: `scripts/check_workflow_policy.py`. **Extend** the existing
  test homes rather than greenfielding: `tests/integration/test_workflow_sha_pinning.py`
  (D-152-05), `tests/integration/test_ci_cache_key_schema.py` (D-152-09),
  `tests/unit/workflows/test_composite_actions.py` (composite scan). Add new
  tests for aggregate-membership, unpinned-install detection, dependency-review
  presence, and release-packet verification.
- **Test coupling to deleted surfaces** (second-order, must update with the
  deletion in D-152-13): `tests/unit/workflows/test_composite_actions.py` asserts
  `run-gates` exists (`test_run_gates_action_file_exists`); `ci-build.yml` is
  referenced by `tests/unit/test_release_authority.py`,
  `tests/unit/workflows/test_release_workflow_policy.py`,
  `tests/integration/test_workflow_sha_pinning.py`, and
  `tests/integration/test_ci_cache_key_schema.py`. These tests are updated or
  removed in the same wave so deletion fails loud, never silently.
- Dependency/ownership: `.github/dependabot.yml`, `.github/CODEOWNERS`,
  `pyproject.toml`, `uv.lock`.
- Governance: `CONSTITUTION.md` (SLSA reference), `CHANGELOG.md`, a
  branch-protection doc, and a cache-cleanup runbook.
- Repo settings (operator action, not code): provision `SNYK_TOKEN` secret;
  configure branch protection to require `CI Result`.

## Delivery Plan

Full-program scope; delivered via `/ai-autopilot` in dependency-ordered waves
(`/ai-plan` refines the DAG):

- **Wave 1 — Policy foundation** (D-152-04/05): fix the parser, scan composites,
  harden SHA pinning, add reachability scaffolding. TDD-first; protects all
  later waves.
- **Wave 2 — Aggregate + topology** (D-152-02/03/13): seal `ci-check-result`,
  add membership test, hard-delete `ci-build.yml` + `run-gates`.
- **Wave 3 — Caches + tools** (D-152-09/10/11/12): trust-tier caches, cold
  release caches, static cache policy, tool pinning + install helper + install
  detection.
- **Wave 4 — Ingress + ownership + Snyk** (D-152-07/08/14/15): dependency-review
  gate, CODEOWNERS, Snyk promotion + finding remediation.
- **Wave 5 — Aspirational + governance** (D-152-16..23): Scorecard, PyPI/Sigstore
  attestations, SLSA L2, harden-runner, docs CI floor, CONDITIONAL GO risk gate,
  release-packet verification.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tightening policy breaks currently-passing workflows. | High | Medium | Land parser + policy tests first (Wave 1), then fix workflows in small commits. |
| Making Snyk blocking turns CI red until findings are fixed. | High | Medium | Triage findings in Wave 4; fix high+ or `ai-eng risk accept` with owner+expiry before flipping the gate to required. |
| Fork PRs cannot access `SNYK_TOKEN`, blocking external contributors. | Medium | Medium | D-152-08: required on trusted contexts, post-merge main coverage + documented advisory window for forks. |
| Cache poisoning bridges PR code into release artifacts. | Medium | Critical | Disable release caches (D-152-10); trust-tier keys + restore-only PR caches (D-152-09); reject privileged cache use by policy (D-152-11). |
| Broad restore keys revive poisoned entries after key migration. | Medium | High | Bust old keys; new trust-tier prefixes; cache-cleanup runbook (D-152-25). |
| Compromised/moved Action bypasses source review. | Medium | Critical | Full SHA pinning + reachability + Dependabot action updates (D-152-05/06/14). |
| SLSA L2 + PyPI attestations + harden-runner add real effort and flakiness. | Medium | Medium | Sequence them last (Wave 5) on top of proven provenance; start harden-runner in audit mode before block. |
| SBOM/provenance produced but never verified. | Medium | High | Release-packet verification contract gates publish (D-152-23). |
| Aspirational scope creep stretches the spec. | Medium | Medium | Wave 5 is independently shippable; if it slips, Waves 1–4 still deliver the security core. |
| Deleting `ci-build.yml` breaks an undocumented consumer. | Low | Medium | Verified zero consumers 2026-05-22; CHANGELOG documents the removal. |
| Hardening leaks into client-consumed framework logic. | Low | High | D-152-01 scope boundary; review confirms no `/ai-pipeline`/installer/template diff. |

## References

- research: `.ai-engineering/specs/drafts/github-actions-ci-hardening-simplification-brief.md`
- doc: `CONSTITUTION.md:90-115` — CI final-authority + supply-chain bar
- doc: `.ai-engineering/manifest.yml:81-90` — regulated gate mode
- doc: GitHub security hardening for Actions — https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
- doc: GitHub Actions cache poisoning (CodeQL) — https://codeql.github.com/codeql-query-help/actions/actions-cache-poisoning-direct-cache/
- doc: SLSA v1.2 specification — https://slsa.dev/spec/latest/
- doc: PyPI attestations security model — https://docs.pypi.org/attestations/security-model/
- doc: OpenSSF Scorecard Action — https://github.com/ossf/scorecard-action
- doc: step-security/harden-runner — https://github.com/step-security/harden-runner

## Open Questions

- **OQ1** — SLSA L2 target: build track only, or build + source track? Default
  to build-track L2 unless `/ai-plan` finds source-track is low-cost here.
- **OQ2** — harden-runner initial posture: ship in `audit` egress mode first and
  flip to `block` after one green cycle, or `block` immediately with a curated
  allowlist?
- **OQ3** — `sbom.yml`: keep as standalone per-commit advisory SBOM (pinned), or
  merge into a single canonical supply-chain workflow alongside Scorecard?
- **OQ4** — dependency-review fail threshold: block on `moderate+` or `high+` in
  regulated mode, and how does that reconcile with the Snyk `high+` SCA threshold?
- **OQ5** — SHA-pin exemptions (D-152-05): full removal of all first-party
  prefixes, or a minimal reviewed allowlist (e.g. `actions/` only) with expiry?
