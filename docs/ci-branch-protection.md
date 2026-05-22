# CI Branch Protection

> Operator reference for the single required status check on `main`.
> Spec-152 (D-152-02/03). Pairs with the membership gate
> `tests/unit/workflows/test_ci_aggregate_membership.py`, which proves the
> aggregate evaluates every blocking job.

## One required check: `CI Result`

Branch protection for `main` requires **exactly one** status check:

```
CI Result
```

`CI Result` is the GitHub display name of the `ci-check-result` job in
[`.github/workflows/ci-check.yml`](../.github/workflows/ci-check.yml). It
is an *aggregate gate*: it `needs:` every other job in the workflow, runs
with `if: always()`, and a final bash step inspects each dependency's
`result` and exits non-zero if any required job did not succeed.

Requiring a single aggregate — rather than pinning each individual job in
the GitHub branch-protection UI — is deliberate:

- **One trustworthy signal.** Merge eligibility is decided by one job
  whose pass/fail is the logical AND of every gate. There is no drift
  between "what the UI requires" and "what CI actually runs".
- **No fail-open hole.** A required job that the aggregate never inspects
  would be awaited-but-never-checked (its failure silently ignored). The
  membership test (below) makes that shape impossible.
- **Conditional jobs stay green-able.** Jobs gated on `code`/`docs`/PR
  context resolve to `skipped` on irrelevant changes; the aggregate
  accepts the skip for those classes instead of blocking the merge.

## The four job classes

The evaluate step sorts every dependency into one of four arrays and
applies a class-specific rule. (`change-scope`, the upstream
`paths-filter` data provider, is checked separately and must always
succeed — it feeds the `code`/`docs` signals the classes below read.)

| Class | Rule | Skip accepted? | Failure tolerated? |
|-------|------|----------------|--------------------|
| `always_required` | MUST succeed on every run | No | No |
| `code_conditional` | MUST succeed when `code == true`; otherwise skip is fine | When `code != true` | Only when `code != true` |
| `pr_only` | MUST succeed on non-Dependabot PRs | On push / Dependabot | Only off the PR path |
| `optional` | Informational — may skip | Yes | **No** (a `failure` still fails the gate) |

Current membership (authoritative source is the workflow itself):

- **`always_required`** — `workflow-sanity`, `security`, `content-integrity`.
- **`code_conditional`** — `lint`, `duplication`, `opa-policies`,
  `risk-acceptance`, `no-suppression`, `typecheck`, `test-unit`,
  `test-integration`, `test-e2e`, `test-docs`, `framework-smoke`,
  `build-check`, `sonarcloud`.
- **`pr_only`** — `verify-gate-trailers`.
- **`optional`** — `snyk-security` (skipped when no `SNYK_TOKEN` is
  available, e.g. fork PRs; covered on push-to-main).

Note that `optional` is not a free pass: an optional job that *fails*
still fails `CI Result`. The class only tolerates a *skip*.

## Individual-gate requirements are optional defense-in-depth

Because the membership test guarantees the aggregate evaluates every
blocking job, marking individual jobs as required in the branch-protection
UI is **redundant** — `CI Result` already covers them. Operators MAY add
individual required checks as belt-and-suspenders, but the supported,
minimal configuration is a single required check: `CI Result`.

## The membership gate keeps this honest

[`tests/unit/workflows/test_ci_aggregate_membership.py`](../tests/unit/workflows/test_ci_aggregate_membership.py)
parses `ci-check.yml` and asserts that every blocking job appears in
**both** `ci-check-result.needs` **and** exactly one evaluated array (or,
for `change-scope`, its dedicated guard). A new job that is added to the
workflow but not wired into the aggregate fails this test in CI — so the
single-required-check model cannot silently regress into a fail-open hole.

## Applying the setting

Repo settings → Branches → branch protection rule for `main` → "Require
status checks to pass before merging" → add **`CI Result`**. This is an
operator-applied repo-settings change; it is not enforced by code.
