---
execution_route:
  version: 1
  spec: spec-152
  executor: autopilot
  automation: hitl
  concern_count: 7
  estimated_files: 24
  reason: >
    Seven milestones across five dependency-ordered waves: workflow-policy
    parser/scan correctness, aggregate-gate integrity, cache trust tiers,
    runtime-tool pinning, dependency ingress + ownership, Snyk promotion, and
    release provenance (Scorecard / SLSA L2 / PyPI attestations / harden-runner).
    Multi-concern, >20 files, requires DAG wave execution with parallel agents —
    /ai-autopilot is the executor.
  safe_next_command: "/ai-autopilot"
spec: spec-152
title: "Plan — GitHub Actions CI/CD Supply-Chain Hardening and Simplification"
status: draft
pipeline: full
total: 39
completed: 0
---

# Plan — GitHub Actions CI/CD Supply-Chain Hardening and Simplification

> Contract for `/ai-autopilot`. Spec: `.ai-engineering/specs/spec.md`
> (spec-152, D-152-01..25, AC1..12). **HARD GATE**: operator approves this plan
> before any executor runs (§10.6 SDD). `status: draft` ⇒ recommendation only.

## Design

`design-routing: skipped (substring false-positives only — "ui" inside "build",
"form" inside "platform"; no UI surface)`. This is an infrastructure/CI-policy
spec with zero frontend surface; `/ai-design` is not invoked and no design
intent is captured. (D-106-02 keyword matcher is substring-based; the explicit
log line is the false-positive safety valve.)

## Architecture

- **Pattern**: Hexagonal (§10.8) for `scripts/check_workflow_policy.py` — pure
  policy predicates (`workflow_triggers`, SHA/cache/install classifiers) at the
  core, `git`/`yaml`/filesystem at the edges. Declarative-config for the
  workflow + composite YAML (no canonical pattern file: `architecture-patterns.md`
  is absent from `.claude/skills/ai-plan/`; Step 6 failed open and the pattern
  was selected directly).
- **Key invariant — one trustworthy signal**: branch protection requires exactly
  `CI Result`; `ci-check-result` must evaluate *every* blocking job. A required
  job that the aggregate never inspects is a fail-open hole (the spec-152 root
  defect).
- **Key invariant — scope boundary (D-152-01)**: every change lands under this
  repo's `.github/**`, `scripts/`, `tests/`, `docs/`, and governance files.
  **Zero** diff to `/ai-pipeline` generators, installer templates, generated
  mirrors, or any client-consumed framework logic. Any such diff is a wave-level
  STOP.
- **Key invariant — TDD-first (§10.5, D-152-24)**: every behavior change is
  preceded by a RED test. CI policy is the canonical deterministic surface;
  regressions must fail loud.
- **Key invariant — hard migration (D-152-25)**: deletions/renames and cache-key
  changes are hard cutovers; coupled tests update in the same wave; CHANGELOG
  records operator-visible breakage. No shims.
- **Release-policy coupling**: `check_workflow_policy.check_release_workflow_policy`
  hard-codes `_RELEASE_JOB_ORDER` (L37-46), `expected_needs` (L172-194), and
  `_expect_text` fragment lists. Wave 5 jobs added to `release.yml` MUST update
  these tuples and `tests/unit/workflows/test_release_workflow_policy.py` in
  lockstep.

## External dependencies (operator actions, not code)

- **`SNYK_TOKEN`** must be provisioned in repo secrets before Wave 4 T-28 flips
  Snyk to required (D-152-07). Build agent cannot set secrets.
- **Branch protection** must be set to require `CI Result` (documented in T-12);
  repo-settings change is operator-applied after merge.

---

## Wave 1 — Policy gate correctness (D-152-04/05/06/21)

> Gate: `uv run python scripts/check_workflow_policy.py` exercises
> `workflow_triggers()` for all trigger checks, scans composites, narrows SHA
> exemptions; new unit tests in `tests/unit/workflows/test_check_workflow_policy.py`
> are green. Protects every later wave.

- [ ] T-1 — RED: boolean-`on:` workflow with `pull_request_target` must be rejected
- Agent: build
- Files: tests/unit/workflows/test_check_workflow_policy.py
- Principles applied: §10.5 TDD
- Patch (deterministic): none — author a test that loads a YAML fixture whose
  `on:` parses to the PyYAML boolean key `True` (bare `on:` block) carrying
  `pull_request_target`, calls `main()` (cwd-scoped to a tmp `.github/workflows`),
  and asserts a failure is returned. Currently passes silently → must fail RED.
- Gate: test fails with current `main()` (proves the `data.get("on")` bug).

- [ ] T-2 — GREEN: route `main()` trigger checks through `workflow_triggers()`
- Agent: build
- Files: scripts/check_workflow_policy.py:426-438
- Principles applied: §10.8 Hexagonal, §10.4 DRY
- Patch (deterministic):
  ```diff
  -        triggers = data.get("on")
  +        triggers = workflow_triggers(data)
           if isinstance(triggers, dict) and "pull_request_target" in triggers:
               failures.append(f"{workflow}: 'pull_request_target' is not allowed")

           if "permissions" not in data:
               failures.append(f"{workflow}: missing top-level permissions block")

  -        # Concurrency required for workflows with pull_request trigger
  -        has_pr_trigger = (
  -            (isinstance(triggers, dict) and "pull_request" in triggers)
  -            or (isinstance(triggers, str) and triggers == "pull_request")
  -            or (isinstance(triggers, list) and "pull_request" in triggers)
  -        )
  +        # workflow_triggers() always returns a normalized dict.
  +        has_pr_trigger = "pull_request" in triggers
  ```
- Gate: T-1 passes; full `test_check_workflow_policy.py` green; policy passes on the repo.

- [ ] T-3 — RED: PR workflow without `concurrency` rejected unless allowlisted
- Agent: build
- Files: tests/unit/workflows/test_check_workflow_policy.py
- Principles applied: §10.5 TDD
- Patch (deterministic): none — two tests: (a) a `pull_request`-triggered fixture
  with no `concurrency` returns a failure; (b) the same workflow name present in
  the concurrency allowlist returns no failure.
- Gate: both tests fail RED (allowlist mechanism does not exist yet).

- [ ] T-4 — GREEN: concurrency allowlist mechanism (D-152-21)
- Agent: build
- Files: scripts/check_workflow_policy.py:440-444
- Principles applied: §10.2 YAGNI, §10.7 Clean Code
- Patch (deterministic): none (judgment) — add a module-level
  `_CONCURRENCY_ALLOWLIST: dict[str, str]` mapping workflow filename → rationale,
  and skip the missing-`concurrency` failure when `workflow.name` is a key.
  Empty by default; entries require a rationale string + a `# expires: <date>`
  comment. Keep it a single explicit reviewed location (spec Migration §).
- Gate: T-3 passes; existing PR workflows (install-smoke, install-time-budget,
  worktree-fast-second) either gain `concurrency` (preferred) or an allowlist
  entry — decided per-workflow in T-4a.

- [ ] T-4a — GREEN: add `concurrency` to PR workflows missing it
- Agent: build
- Files: .github/workflows/install-smoke.yml, .github/workflows/install-time-budget.yml, .github/workflows/worktree-fast-second.yml
- Principles applied: §10.1 KISS
- Patch (deterministic): none (per-file) — add a top-level
  `concurrency:\n  group: <name>-${{ github.ref }}\n  cancel-in-progress: true`
  block to each, mirroring `ci-check.yml:22-24`. Prefer this over allowlisting.
- Gate: policy check passes for all three; no allowlist entries needed.

- [ ] T-5 — RED: composite `action.yml` with a tag-pinned `uses:` must be rejected
- Agent: build
- Files: tests/unit/workflows/test_check_workflow_policy.py
- Principles applied: §10.5 TDD
- Patch (deterministic): none — fixture `.github/actions/foo/action.yml` with a
  composite `runs.steps[].uses` pinned to a tag (not a 40-char SHA); assert the
  scanner flags it. RED because composites are unscanned today (glob at L414).
- Gate: test fails RED.

- [ ] T-6 — GREEN: scan `.github/actions/**/action.yml` for SHA pinning
- Agent: build
- Files: scripts/check_workflow_policy.py:413-459
- Principles applied: §10.8 Hexagonal, §10.3 SOLID
- Patch (deterministic): none (judgment) — extend the glob and add a composite
  SHA-pin pass; composites have no `jobs:` — steps live under `runs.steps`, so
  refactor `_check_sha_pinning` to accept a step list, then call it for both
  workflow jobs and composite `runs.steps`. Representative glob change:
  ```diff
  -    workflows = sorted(p for p in Path(".github/workflows").glob("*.yml"))
  +    workflows = sorted(Path(".github/workflows").glob("*.yml"))
  +    composites = sorted(Path(".github/actions").glob("*/action.yml"))
  ```
- Gate: T-5 passes; `setup-env/action.yml` external `uses:` (setup-python,
  setup-uv) are already SHA-pinned so the repo stays green.

- [ ] T-7 — RED: non-local `uses:` without a 40-char SHA rejected for first-party orgs too
- Agent: build
- Files: tests/unit/workflows/test_check_workflow_policy.py
- Principles applied: §10.5 TDD
- Patch (deterministic): none — fixture with `actions/checkout@v4` (tag, not SHA)
  asserted to FAIL once the exemption is narrowed. RED today (prefix-exempted).
- Gate: test fails RED.

- [ ] T-8 — GREEN: SHA-pin all currently tag/prefix-exempt actions across workflows + composites
- Agent: build
- Files: .github/workflows/*.yml, .github/actions/*/action.yml
- Principles applied: §10.1 KISS
- Patch (deterministic): none (resolve-and-replace) — for every `uses:` under an
  exempt prefix (`actions/`, `github/`, `pypa/`, `astral-sh/`, `SonarSource/`,
  `CycloneDX/`, `EndBug/`, `dorny/`) resolve the tag to its commit SHA via
  `git ls-remote` and rewrite as `owner/action@<sha> # <tag>`. MUST precede T-8b
  or CI breaks. Re-run actionlint after.
- Gate: `test_workflow_sha_pinning.py` green; actionlint clean.

- [ ] T-8b — GREEN: narrow/remove `_FIRST_PARTY_PREFIXES` (D-152-05)
- Agent: build
- Files: scripts/check_workflow_policy.py:20-30, 396-403
- Principles applied: §10.7 Clean Code
- Patch (deterministic): none (judgment) — reduce the exemption tuple to the
  minimal reviewed set (resolve OQ5: full removal vs `actions/` only) with an
  inline rationale + expiry comment. Default recommendation: full removal now
  that T-8 pinned everything.
- Gate: T-7 passes; policy passes on the repo.

- [ ] T-9 — GREEN: SHA reachability check off the hot path (D-152-06)
- Agent: build
- Files: scripts/check_workflow_policy.py, .github/workflows/nightly-matrix.yml
- Principles applied: §10.8 Hexagonal, §10.2 YAGNI
- Patch (deterministic): none (judgment) — add an opt-in
  `--check-reachability` flag that runs `git ls-remote <repo> <sha>` per pinned
  ref (adapter at the edge; pure ref-extraction in the core), and wire it into
  the nightly/advisory workflow (and an action-change-triggered path), NOT the
  PR hot path. The audit found a `label-sync.yml` ref shaped-but-unreachable —
  this catches it.
- Gate: a unit test stubs `git ls-remote` and asserts an unreachable SHA fails;
  PR hot path unchanged (regex-only).

---

## Wave 2 — Aggregate integrity + topology simplification (D-152-02/03/13/25)

> Gate: a membership test enumerates every blocking job in `ci-check.yml` and
> proves each is represented in `ci-check-result`; `ci-build.yml` + `run-gates`
> deleted; release policy test still green; CHANGELOG updated.

- [ ] T-10 — RED: every blocking job in `ci-check.yml` must be represented in `ci-check-result`
- Agent: build
- Files: tests/unit/workflows/test_ci_aggregate_membership.py (new)
- Principles applied: §10.5 TDD
- Patch (deterministic): none — parse `ci-check.yml`, compute the set of
  non-aggregate jobs that are blocking (exclude `ci-check-result` itself and
  explicitly-advisory jobs), and assert each appears in BOTH `ci-check-result.needs`
  AND one of the evaluated arrays (`always_required`/`code_conditional`/`pr_only`/
  required-`optional`). RED: `no-suppression` is in neither.
- Gate: test fails RED naming `no-suppression`.

- [ ] T-11 — GREEN: wire `no-suppression` into the aggregate
- Agent: build
- Files: .github/workflows/ci-check.yml:757-772, 788-808, 827-840
- Principles applied: §10.1 KISS
- Patch (deterministic):
  ```diff
  @@ build-check.needs @@
         risk-acceptance,
  +      no-suppression,
         typecheck,
  @@ ci-check-result.needs @@
         risk-acceptance,
  +      no-suppression,
         typecheck,
  @@ code_conditional array @@
             "risk-acceptance:${{ needs.risk-acceptance.result }}"
  +          "no-suppression:${{ needs.no-suppression.result }}"
             "typecheck:${{ needs.typecheck.result }}"
  ```
- Gate: T-10 passes; `ci-check-result` fails if `no-suppression` is `failure`
  or unexpectedly `skipped` when `code==true`.

- [ ] T-12 — GREEN: branch-protection documentation (D-152-03)
- Agent: build
- Files: docs/ci-branch-protection.md (new)
- Principles applied: §10.7 Clean Code
- Patch (deterministic): none (prose) — document that the single required check
  is `CI Result`; explain the aggregate's four job classes; state that
  individual-gate requirements are optional defense-in-depth. Link from CONTRIBUTING/README.
- Gate: doc exists, names `CI Result` as the required check; docs gate passes.

- [ ] T-13 — GREEN: hard-delete `ci-build.yml` + `run-gates`; update coupled tests
- Agent: build
- Files: .github/workflows/ci-build.yml (rm), .github/actions/run-gates/ (rm -r), tests/unit/workflows/test_composite_actions.py, tests/unit/test_release_authority.py, tests/integration/test_workflow_sha_pinning.py, tests/integration/test_ci_cache_key_schema.py
- Principles applied: §10.1 KISS, §10.2 YAGNI
- Patch (deterministic): none (deletion + test edits) — `git rm` both surfaces;
  remove `run_gates` fixtures/tests from `test_composite_actions.py`
  (`test_run_gates_*`); drop `ci-build` references from the four coupled tests so
  deletion fails loud, never silently. Verified 2026-05-22: zero consumers of the
  `dist` artifact, zero `uses:` of run-gates.
- Gate: full suite green; `test_release_workflow_policy.py` still passes
  (its `ci-build.yml` forbidden-fragment check at policy L198 is unaffected).

- [ ] T-14 — GREEN: CHANGELOG records the deletions (D-152-25)
- Agent: build
- Files: CHANGELOG.md
- Principles applied: §10.7 Clean Code
- Patch (deterministic): none (prose) — add a "Removed" entry: `ci-build.yml`
  (orphaned post-CI build; use release artifacts) and `.github/actions/run-gates`
  (unreferenced composite). Note breaking nature per D-152-25.
- Gate: docs/changelog gate passes.

---

## Wave 3 — Cache trust tiers + runtime-tool pinning (D-152-09/10/11/12)

> Gate: no PR/fork cache key restorable by main/release/OIDC jobs; release jobs
> cold; policy rejects privileged caches + unpinned installs; all runtime tools
> pinned/verified. Extends `test_ci_cache_key_schema.py`.

- [ ] T-15 — RED: cache keys must carry a trust-tier prefix; no cross-tier restore fallback
- Agent: build
- Files: tests/integration/test_ci_cache_key_schema.py
- Principles applied: §10.5 TDD
- Patch (deterministic): none — assert every `actions/cache` `key`/`restore-keys`
  in `ci-check.yml` begins with a `pr-`/`main-`/`release-` tier token and that no
  `restore-keys` entry omits the tier (the current broad `gate-cache-${os}-`
  fallback). RED today.
- Gate: test fails RED on the 5 gate-cache sites + semgrep cache.

- [ ] T-16 — GREEN: retype all cache keys with trust-tier prefixes (D-152-09)
- Agent: build
- Files: .github/workflows/ci-check.yml (gate-cache: ~89-95,164-171,196-203,283-289; semgrep: 572-577)
- Principles applied: §10.1 KISS
- Patch (deterministic): representative (apply to every cache site) —
  ```diff
  -          key: gate-cache-${{ runner.os }}-${{ hashFiles('pyproject.toml', '.ruff.toml', '.gitleaks.toml') }}-${{ github.event.pull_request.base.sha || github.sha }}
  +          key: gate-cache-${{ github.event_name == 'pull_request' && 'pr' || 'main' }}-${{ runner.os }}-${{ hashFiles('pyproject.toml', '.ruff.toml', '.gitleaks.toml') }}-${{ github.sha }}
             restore-keys: |
  -            gate-cache-${{ runner.os }}-${{ hashFiles('pyproject.toml', '.ruff.toml', '.gitleaks.toml') }}-
  -            gate-cache-${{ runner.os }}-
  +            gate-cache-${{ github.event_name == 'pull_request' && 'pr' || 'main' }}-${{ runner.os }}-${{ hashFiles('pyproject.toml', '.ruff.toml', '.gitleaks.toml') }}-
  ```
  PR jobs restore-only within the `pr-` tier; the broad cross-tier fallback is
  removed (busts old keys per D-152-25). Same prefix scheme for semgrep cache.
- Gate: T-15 passes.

- [ ] T-17 — GREEN: release jobs run cold (D-152-10)
- Agent: build
- Files: .github/workflows/release.yml (setup-env calls ~L113, ~L221)
- Principles applied: §10.1 KISS
- Patch (deterministic): none (per call) — pass `enable-cache: "false"` to every
  `./.github/actions/setup-env` invocation in `release-readiness` and
  `release-build` (setup-env default is `true`, action.yml:23-25).
- Gate: a release-policy test asserts release setup-env calls disable cache; no
  OIDC/publish job restores a mutable cache.

- [ ] T-18 — RED: policy rejects privileged caches + composite setup-action caches
- Agent: build
- Files: tests/unit/workflows/test_check_workflow_policy.py
- Principles applied: §10.5 TDD
- Patch (deterministic): none — fixtures: (a) `actions/cache` under a
  `pull_request_target` job → fail; (b) `actions/cache` in a `workflow_run` job
  that checks out an untrusted ref → fail; (c) `enable-cache: true` in a composite
  used by a release/OIDC job → flag; (d) a named reviewed exception → pass.
- Gate: tests fail RED.

- [ ] T-19 — GREEN: cache-trust policy in the checker (D-152-11)
- Agent: build
- Files: scripts/check_workflow_policy.py
- Principles applied: §10.8 Hexagonal, §10.3 SOLID
- Patch (deterministic): none (judgment) — add a pure `classify_cache_usage`
  predicate: reject `actions/cache`(`/restore`,`/save`) under
  `pull_request_target`, untrusted `workflow_run` checkout, and release/OIDC jobs
  unless a reviewed `_CACHE_EXCEPTIONS` entry names the trust boundary; require
  tier prefixes in keys; flag setup-action `enable-cache:true` inside composites.
- Gate: T-18 passes; repo passes.

- [ ] T-20 — RED: policy flags unpinned runtime installs
- Agent: build
- Files: tests/unit/workflows/test_check_workflow_policy.py
- Principles applied: §10.5 TDD
- Patch (deterministic): none — fixtures asserting failures for `curl ... | bash`,
  `npm install -g <pkg>` (no `@version`), `uv run --with <pkg>` (no `==`), and
  `uv pip install <pkg>` (no `==`) in step `run:` text, unless allowlisted.
- Gate: tests fail RED.

- [ ] T-21 — GREEN: unpinned-install policy in the checker (D-152-12)
- Agent: build
- Files: scripts/check_workflow_policy.py
- Principles applied: §10.8 Hexagonal
- Patch (deterministic): none (judgment) — pure `scan_install_pins(steps_text)`
  with a reviewed `_INSTALL_ALLOWLIST` (filename + rationale). Detect the four
  patterns above in step `run:` blocks.
- Gate: T-20 passes; the repo passes only AFTER T-22 pins the offenders.

- [ ] T-22 — GREEN: pin + verify every runtime tool (D-152-12)
- Agent: build
- Files: .github/workflows/ci-check.yml (actionlint 462-465, snyk 514, gitleaks 544-548), .github/workflows/sbom.yml:46, .github/workflows/release.yml (cyclonedx ~284)
- Principles applied: §10.7 Clean Code, §10.4 DRY
- Patch (deterministic): cyclonedx pin (sbom.yml) representative —
  ```diff
  -        run: uv pip install cyclonedx-bom
  +        run: uv pip install "cyclonedx-bom==<pinned>"
  ```
  Plus (judgment): replace actionlint `curl|bash` from `main` with a pinned
  release+`sha256sum` check (or a pinned-SHA action); add `sha256sum -c` for the
  gitleaks tarball; pin `snyk` (`npm install -g snyk@<ver> --ignore-scripts`);
  pin cyclonedx in `release.yml`. Centralize version+checksum in one reusable
  `scripts/ci/install_tool.sh` helper so checksums are declared once (DRY).
- Gate: T-20/T-21 policy passes; actionlint/gitleaks/snyk/cyclonedx all run.

---

## Wave 4 — Dependency ingress, ownership, Snyk promotion (D-152-07/08/14/15)

> Gate: `dependency-review` blocking on PRs; CODEOWNERS protects supply-chain
> paths; Snyk required on trusted contexts with findings fixed/risk-accepted;
> ingress threshold matrix documented. **Requires `SNYK_TOKEN` provisioned.**

- [ ] T-23 — RED: dependency-review must be a blocking PR gate
- Agent: build
- Files: tests/unit/workflows/test_ci_aggregate_membership.py
- Principles applied: §10.5 TDD
- Patch (deterministic): none — assert a `dependency-review` job exists, uses a
  SHA-pinned `actions/dependency-review-action`, and is in a required aggregate
  array. RED today.
- Gate: test fails RED.

- [ ] T-24 — GREEN: add dependency-review job + wire to aggregate (D-152-14)
- Agent: build
- Files: .github/workflows/ci-check.yml
- Principles applied: §10.1 KISS
- Patch (deterministic): none (judgment) — add a `dependency-review` job
  (`actions/dependency-review-action@<sha>`) gated to `pull_request`, set its
  `fail-on-severity` per OQ4 (default `high` to match Snyk SCA), and add it to
  `ci-check-result.needs` + the `pr_only` (or code_conditional) array.
- Gate: T-23 passes.

- [ ] T-25 — GREEN: explicit CODEOWNERS for supply-chain paths (D-152-15)
- Agent: build
- Files: .github/CODEOWNERS
- Principles applied: §10.7 Clean Code
- Patch (deterministic):
  ```diff
   .ai-engineering/manifest.yml         @arcasilesgroup/maintainers
  +
  +# spec-152: supply-chain-sensitive paths require explicit maintainer review
  +/.github/**                          @arcasilesgroup/maintainers
  +/.github/actions/**                  @arcasilesgroup/maintainers
  +/.github/workflows/release.yml       @arcasilesgroup/maintainers
  +/scripts/check_workflow_policy.py    @arcasilesgroup/maintainers
  +/pyproject.toml                      @arcasilesgroup/maintainers
  +/uv.lock                             @arcasilesgroup/maintainers
  ```
- Gate: CODEOWNERS parses (no `gh` validation error); review.

- [ ] T-26 — GREEN: dependency-ingress threshold matrix doc (D-152-14)
- Agent: build
- Files: docs/supply-chain-control-matrix.md (new)
- Principles applied: §10.7 Clean Code
- Patch (deterministic): none (prose) — document non-overlapping responsibilities
  + blocking thresholds for dependency-review vs Snyk SCA vs `pip-audit`, the
  `uv.lock` hash-evidence requirement, and that Dependabot PRs run the same
  `CI Result`. One supply-chain control matrix (surface → owner → gate → evidence
  → escalation) per spec M3.
- Gate: doc exists; docs gate passes.

- [ ] T-27 — RED: `snyk-security` must be required on trusted contexts (not optional)
- Agent: build
- Files: tests/unit/workflows/test_ci_aggregate_membership.py
- Principles applied: §10.5 TDD
- Patch (deterministic): none — assert `snyk-security` is NOT in the `optional`
  array and IS evaluated as required when the run is a trusted context
  (push/main or same-repo PR); assert the fork-PR skip path is explicitly handled
  (documented), not silently green. RED today (it is `optional`, L848-850).
- Gate: test fails RED.

- [ ] T-28 — GREEN: promote Snyk to required + pin CLI (D-152-07/08)
- Agent: build
- Files: .github/workflows/ci-check.yml:504-535, 847-850
- Principles applied: §10.3 SOLID
- Patch (deterministic): none (judgment) — move `snyk-security` from `optional`
  to a context-aware required class: required when `has-snyk-token == 'true'`
  (trusted contexts); on a fork PR where GitHub withholds the secret, the job is
  documented-skipped and covered post-merge on main (D-152-08). Pin the Snyk CLI
  (overlaps T-22). Keep `snyk code test` advisory; `snyk monitor` main-only.
- Gate: T-27 passes; with a token, a `snyk test` high+ failure fails `CI Result`.

- [ ] T-29 — GREEN: run Snyk, triage findings, fix or risk-accept (D-152-07)
- Agent: build
- Files: (remediation — varies); .ai-engineering risk-acceptance records if used
- Principles applied: §10.9 (Autonomous Bug Fixing), §10.5 TDD
- Patch (deterministic): none (investigative) — with `SNYK_TOKEN` set, run
  `snyk test`/`snyk code test`; for each high+ finding either remediate (pin/bump
  per spec Non-Goal on broad upgrades — only verification-tied bumps) or record
  `ai-eng risk accept --finding-id …` with owner + expiry. Operator must
  provision the token first.
- Gate: `snyk test --severity-threshold=high` clean OR every residual finding has
  a risk-acceptance record.

---

## Wave 5 — Aspirational provenance + governance coverage (D-152-16/17/18/19/20/22/23)

> Gate: Scorecard in CI; harden-runner egress; SLSA L2 signed provenance; PyPI/
> Sigstore attestations verified; docs-only changes gated; CONDITIONAL GO blocks
> without risk acceptance; release-packet verification documented + tested.
> Release-policy tuples (`_RELEASE_JOB_ORDER` etc.) updated in lockstep.

- [ ] T-30 — GREEN: OpenSSF Scorecard in CI (D-152-16)
- Agent: build
- Files: .github/workflows/scorecard.yml (new), tests/unit/workflows/test_scorecard.py (new)
- Principles applied: §10.1 KISS
- Patch (deterministic): none (judgment) — add `ossf/scorecard-action@<sha>` on a
  scheduled + push-to-main trigger, least-privilege `permissions`, SARIF upload;
  classify advisory-or-required per regulated thresholds. RED test first asserts
  the workflow + pinned action.
- Gate: scorecard test green; policy passes (SHA-pinned, timeouts, permissions).

- [ ] T-31 — GREEN: harden-runner egress control (D-152-19, OQ2)
- Agent: build
- Files: .github/workflows/ci-check.yml, release.yml, sbom.yml, scorecard.yml; tests/unit/workflows/test_harden_runner.py (new)
- Principles applied: §10.1 KISS
- Patch (deterministic): none (judgment) — add `step-security/harden-runner@<sha>`
  as the first step of each job, `egress-policy: audit` initially (OQ2: flip to
  `block` with an allowlist after one green cycle). RED test asserts presence.
- Gate: harden-runner test green; all jobs still pass in audit mode.

- [ ] T-32 — GREEN: SLSA L2 signed provenance + Constitution alignment (D-152-18)
- Agent: build
- Files: .github/workflows/release.yml, CONSTITUTION.md:109-115, scripts/check_workflow_policy.py:37-194, tests/unit/workflows/test_release_workflow_policy.py
- Principles applied: §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): none (judgment) — add L2-style signed provenance to the
  release pipeline (build → provenance generation/signing → verify), update
  `CONSTITUTION.md` SLSA reference from v1.0 to the targeted track (OQ1: build vs
  build+source), and update `_RELEASE_JOB_ORDER`/`expected_needs`/`_expect_text`
  + the release policy test in lockstep with any new release jobs.
- Gate: `test_release_workflow_policy.py` green with the new topology; provenance
  verified before publish.

- [ ] T-33 — GREEN: PyPI/Sigstore package attestations + consumer verify (D-152-17)
- Agent: build
- Files: .github/workflows/release.yml, scripts/check_workflow_policy.py, tests/unit/workflows/test_release_workflow_policy.py
- Principles applied: §10.6 SDD
- Patch (deterministic): none (judgment) — emit PyPI attestations / Sigstore
  signatures alongside the existing GitHub artifact attestation; add a verify
  step before finalize; extend the release-policy fragment expectations + test.
- Gate: release policy test asserts attestation emission + verification.

- [ ] T-34 — GREEN: governance-docs CI floor (D-152-22)
- Agent: build
- Files: .github/workflows/ci-check.yml:3-17, 26-49; tests/unit/workflows/test_docs_gate.py (new)
- Principles applied: §10.1 KISS
- Patch (deterministic): none (judgment) — relax the `docs/**` `paths-ignore` so a
  docs-only change still runs a lightweight gate (workflow-sanity +
  content-integrity + relevant security policy) by reusing the existing
  `change-scope.outputs.docs` signal (L33); keep the heavy test matrix gated to
  `code==true`. RED test asserts a docs-only change triggers the floor.
- Gate: docs-gate test green; docs-only PR is not fully CI-bypassed.

- [ ] T-35 — GREEN: CONDITIONAL GO risk gate + release-packet verification contract (D-152-20/23)
- Agent: build
- Files: .github/workflows/release.yml (release-readiness, finalize), docs/release-packet-verification.md (new), tests/unit/workflows/test_release_workflow_policy.py
- Principles applied: §10.6 SDD
- Patch (deterministic): none (judgment) — make `CONDITIONAL GO` block publish
  unless an `ai-eng risk accept` artifact is present in the release packet;
  document which artifacts (wheels, sdists, SBOM, checksums, attestations,
  TestPyPI proof) MUST be verified before PyPI publish vs final-evidence-only.
- Gate: release-readiness test asserts CONDITIONAL GO blocks without the
  risk-acceptance artifact; verification step asserted present before publish.

- [ ] T-36 — GREEN: cache-cleanup runbook (D-152-25, spec OQ #13)
- Agent: build
- Files: docs/cache-cleanup-runbook.md (new)
- Principles applied: §10.7 Clean Code
- Patch (deterministic): none (prose) — document how to list/delete/rotate GitHub
  Actions caches after suspected poisoning or after a trust-tier key migration
  (`gh cache list`/`gh cache delete`), and which workflow/owner owns it.
- Gate: runbook exists; docs gate passes.

- [ ] T-37 — GREEN: final CHANGELOG + cross-doc consistency (D-152-25)
- Agent: build
- Files: CHANGELOG.md
- Principles applied: §10.7 Clean Code
- Patch (deterministic): none (prose) — record operator-visible changes: Snyk now
  blocking, dependency-review added, cache-key trust-tier migration (old keys
  busted), CONDITIONAL GO publish semantics, SLSA/attestation/Scorecard/
  harden-runner additions, CONSTITUTION SLSA reference bump.
- Gate: docs/changelog gate passes; `ai-eng spec verify` counters consistent.

---

## Phase order + gate criteria

| Wave | Depends on | Exit gate |
|------|-----------|-----------|
| W1 Policy correctness | — | `check_workflow_policy.py` parser fixed, composites scanned, exemptions narrowed; new policy tests green |
| W2 Aggregate + topology | W1 | membership test green; `no-suppression` enforced; dead workflows deleted; release policy still green |
| W3 Caches + tools | W1, W2 | trust-tier cache keys; release cold; cache + install policy enforced; tools pinned/verified |
| W4 Ingress + Snyk | W3 | dependency-review blocking; CODEOWNERS; Snyk required + findings resolved (token provisioned) |
| W5 Aspirational + governance | W4 | Scorecard, harden-runner, SLSA L2, PyPI/Sigstore attestations, docs floor, CONDITIONAL GO gate, runbook |

Within a wave, RED test tasks must land and fail before their GREEN partner.
Final whole-changeset gate (post-W5): `uv run python scripts/check_workflow_policy.py`
green, full test suite green, `release.yml` passes existing + extended release
policy tests, and the D-152-01 scope-boundary check (zero diff to client-consumed
framework logic) holds.

## Self-review (§10.7)

- Iteration 1 — caught: (a) `_RELEASE_JOB_ORDER`/`expected_needs` coupling for
  Wave-5 release jobs → added to Architecture invariants + T-32/T-33 files; (b)
  T-8 ordering hazard (narrowing exemptions before pinning breaks CI) → split into
  T-8 (pin) → T-8b (narrow); (c) Snyk required-vs-fork-PR token absence is
  judgment, not a mechanical patch → T-27/T-28 prose + context-aware test; (d)
  T-21 install policy would fail the repo before T-22 pins offenders → gate notes
  the ordering.
- Iteration 2 — confirmed: every GREEN task has a RED partner or an explicit gate;
  no code-write task assigned to a read-only agent; deletions (T-13) update
  coupled tests in the same task; scope-boundary invariant (D-152-01) is a
  wave-level STOP. No further concerns.
