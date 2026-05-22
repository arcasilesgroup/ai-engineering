# Supply-Chain Control Matrix

> Operator + maintainer reference for dependency-ingress controls on this
> repo. Spec-152 (D-152-07/08/14/15), Wave 4. Pairs with
> [`docs/ci-branch-protection.md`](ci-branch-protection.md) (the single
> required `CI Result` aggregate) and the membership gate
> [`tests/unit/workflows/test_ci_aggregate_membership.py`](../tests/unit/workflows/test_ci_aggregate_membership.py).

This matrix maps every dependency-ingress surface to its **owner**, the
**gate** that enforces it, the **evidence** it produces, and the
**escalation** path when it blocks. The controls are deliberately
*non-overlapping*: each catches a class of risk the others do not (see
[Non-overlapping responsibilities](#non-overlapping-responsibilities)).

## Control matrix

| # | Ingress surface | Owner | Gate (where) | Trigger | Blocking threshold | Evidence | Escalation |
|---|-----------------|-------|--------------|---------|--------------------|----------|------------|
| 1 | New / changed dependency in a PR diff | `@arcasilesgroup/maintainers` | `dependency-review` job → `actions/dependency-review-action` (`ci-check.yml`) | every `pull_request`, **dependabot included** | `fail-on-severity: high` (vulnerable advisory on a newly-introduced or bumped dependency) | Action run log + PR check `CI Result` | Fix the dependency (pin/bump/remove) or `ai-eng risk accept --finding-id …` with owner + expiry |
| 2 | Full dependency-tree vulnerabilities (SCA) | `@arcasilesgroup/maintainers` | `snyk-security` job → `snyk test --severity-threshold=high` against `uv pip freeze` output (`ci-check.yml`) | every run **when `SNYK_TOKEN` is provisioned** (`has-snyk-token == 'true'`) | high+ vulnerability anywhere in the resolved tree | Snyk run log; `snyk monitor` snapshot on `main` | Fix/bump per spec Non-Goal (verification-tied bumps only) or `ai-eng risk accept` |
| 3 | Source-code security (SAST) | `@arcasilesgroup/maintainers` | `snyk-security` job → `snyk code test --severity-threshold=high` | every run when token provisioned | advisory today (`snyk code test` is not in a blocking class) | Snyk SAST run log | Triage; promote to blocking in a follow-up if signal is clean |
| 4 | Known-vulnerable installed packages (baseline) | `@arcasilesgroup/maintainers` | `pip-audit` — pre-push hook **and** the `security` job (`ci-check.yml`, via `ai_engineering.verify.tls_pip_audit`) | pre-push (local) + every CI run | advisory baseline (defense-in-depth alongside Snyk SCA) | pre-push output + `security` job log | Bump or `ai-eng risk accept`; the `security` job is `always_required` so a hard failure blocks `CI Result` |
| 5 | Dependency-resolution integrity | `@arcasilesgroup/maintainers` (CODEOWNERS on `pyproject.toml`, `uv.lock`) | `uv.lock` hash evidence — the lockfile pins every transitive package to a content hash; cache keys are keyed on `hashFiles('pyproject.toml', …)` (`ci-check.yml`) | every run | a tampered/unsynced lock changes the hash → cache miss + diff in review | `uv.lock` content hashes; CODEOWNERS-gated review | Maintainer review of the lock diff; regenerate with `uv lock` |
| 6 | Supply-chain-sensitive file edits | `@arcasilesgroup/maintainers` | `.github/CODEOWNERS` — explicit entries for `/.github/**`, `/.github/actions/**`, `release.yml`, `check_workflow_policy.py`, `pyproject.toml`, `uv.lock` | every PR touching those paths | required maintainer review before merge | PR review record | Request maintainer review; the rule is GitHub-enforced once branch protection requires CODEOWNERS review |
| 7 | GitHub Action / runtime-tool pinning | `@arcasilesgroup/maintainers` | `scripts/check_workflow_policy.py` (`workflow-sanity` job) — every external `uses:` must be a 40-char SHA; runtime installs must be version-pinned | every run (`workflow-sanity` is `always_required`) | any unpinned action or install → policy fails → `CI Result` fails | policy-check log | Resolve the tag to a SHA via `git ls-remote`; pin the install version |

## Dependabot PRs run the same `CI Result`

Dependabot opens PRs against `main` like any contributor, so its PRs run
the **identical** `CI Result` aggregate. The two ingress controls that
matter most for an automated dependency bump both apply:

- **`dependency-review`** is in the `pr_all` aggregate class — it MUST
  succeed on **every** PR, dependabot **included**. (It is deliberately
  **not** in `pr_only`, which exempts dependabot.) A dependabot bump that
  pulls in a high-severity advisory fails `CI Result` and cannot merge.
- **`snyk-security`** runs whenever `SNYK_TOKEN` is provisioned and the
  run is a trusted context (same-repo). Dependabot PRs from within the
  repo have access to the token; the SCA scan runs and blocks on high+.

The only ingress softening is the documented fork-PR / no-token path
below — which does not apply to in-repo dependabot PRs.

## Fork-PR and no-token behavior (D-152-08)

`snyk-security` is gated on `needs.change-scope.outputs.has-snyk-token`:

- **`has-snyk-token == 'true'`** (token provisioned, trusted context) —
  the job MUST run and succeed. In the aggregate's `token_conditional`
  class a *skip* is treated as a **FAIL** (the job must actually execute).
- **`has-snyk-token == 'false'`** (token unprovisioned, **or** a fork PR
  where GitHub withholds repo secrets) — the job `skipped` is
  **tolerated**; only an explicit `failure` fails the gate. Fork PRs are
  re-covered by the `snyk monitor` snapshot on push-to-`main` after merge.

This keeps the repo's CI green today (no token ⇒ skip tolerated) and
becomes enforcing the **moment the operator provisions `SNYK_TOKEN`** — no
further code change is required (see [Snyk enforcement
activation](#snyk-enforcement-activation-pending-operator-action)).

## Non-overlapping responsibilities

The three vulnerability gates are intentionally distinct — none is a
superset of another:

- **`dependency-review` = new-dependency *diff* on PRs.** It inspects only
  what the PR *adds or changes* in the dependency graph and fails on a
  newly-introduced high+ advisory or license violation. It is fast, runs
  on the PR diff, and stops a bad dependency *at the point of
  introduction*. It does **not** re-scan the pre-existing tree.
- **Snyk SCA (`snyk test`) = full dependency-tree vuln scan.** It scans
  the **entire** resolved tree (every transitive package from
  `uv pip freeze`), so it catches a newly-disclosed CVE in a dependency
  that was already present and unchanged by the PR — which
  `dependency-review` (diff-only) would miss.
- **`pip-audit` = advisory baseline.** A lightweight, dependency-light
  cross-check against the Python advisory database that runs on the
  pre-push hot path and in CI even when no Snyk token is present. It is the
  always-on floor beneath the token-gated Snyk SCA.

Together: `dependency-review` guards the *ingress edge* (the diff), Snyk
SCA guards the *standing tree* (full scan), and `pip-audit` is the
*token-independent baseline*. `uv.lock` hash evidence + CODEOWNERS make the
inputs to all three tamper-evident and review-gated.

## Snyk enforcement activation (pending operator action)

Snyk SCA is **promoted to a required gate** in the aggregate
(`token_conditional` class), but it only *activates* once an operator
provisions the secret:

1. Operator adds **`SNYK_TOKEN`** to the repo's Actions secrets.
2. On the next run, `change-scope` emits `has-snyk-token == 'true'`, the
   `snyk-security` job executes, and the aggregate requires it to succeed
   (a skip becomes a FAIL).
3. A follow-up runs `snyk test --severity-threshold=high`; each high+
   finding is then **fixed** (verification-tied pin/bump) or
   **`ai-eng risk accept`-ed** with an owner + expiry (spec-152 T-29).

Until step 1, CI stays green with the no-token skip-tolerant path above.
No code change is needed to flip Snyk from tolerated-skip to enforcing —
provisioning the token is the only operator action.
