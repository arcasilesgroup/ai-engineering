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

## The job classes

The evaluate step sorts every dependency into one of five arrays and
applies a class-specific rule. (`change-scope`, the upstream
`paths-filter` data provider, is checked separately and must always
succeed — it feeds the `code`/`docs`/token signals the classes below read.)

| Class | Rule | Skip accepted? | Failure tolerated? |
|-------|------|----------------|--------------------|
| `always_required` | MUST succeed on every run | No | No |
| `code_conditional` | MUST succeed when `code == true`; otherwise skip is fine | When `code != true` | Only when `code != true` |
| `docs_conditional` | MUST succeed when `docs == true` OR `code == true` (the docs CI floor) | When neither docs nor code changed | Only when neither changed |
| `pr_only` | MUST succeed on non-Dependabot PRs | On push / Dependabot | Only off the PR path |
| `token_conditional` | MUST succeed when `has-snyk-token == true`; skip tolerated only when the token is absent | When no `SNYK_TOKEN` (unprovisioned / fork PR) | No |

Current membership (authoritative source is the workflow itself):

- **`always_required`** — `workflow-sanity`, `security`, `content-integrity`.
- **`code_conditional`** — `lint`, `duplication`, `opa-policies`,
  `risk-acceptance`, `no-suppression`, `typecheck`, `test-unit`,
  `test-integration`, `test-e2e`, `test-docs`, `framework-smoke`,
  `build-check`, `sonarcloud`.
- **`docs_conditional`** — `docs-gate` (the lightweight docs floor —
  content integrity + secret scan + workflow policy — that runs whenever
  docs OR code change so a docs-only PR is still inspected instead of fully
  bypassing CI — D-152-22).
- **`pr_only`** — `verify-gate-trailers`.
- **`token_conditional`** — `snyk-security`. Mandatory (blocking high+)
  the moment `SNYK_TOKEN` is provisioned; until then — and on fork PRs that
  cannot read the secret — the job skips and the skip is tolerated so CI is
  not wedged. A *failure* always fails the gate (D-152-07/08).

There is no `pr_all` class: its only member, `dependency-review`, was
removed as infeasible — GitHub's `actions/dependency-review-action`
requires the org Dependency Graph, which is disabled here, so the check
could never run (a never-running required gate is itself a fail-open
hole). SCA is carried by `snyk-security` (`token_conditional`) +
`pip-audit` (in the `always_required` `security` job); see
[`docs/supply-chain-control-matrix.md`](supply-chain-control-matrix.md).
There is also no `optional` class: spec-152 removed the catch-all
informational bucket so every dependency lands in a class with a defined
blocking rule.

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

## Environment deployment policies (release publishing)

> The 0.8.0 release nearly failed here: spec-152 made
> [`release.yml`](../.github/workflows/release.yml) **tag-triggered**
> (`on: push: tags: ['v*']`), but the `pypi` environment still allowed only
> the `main` *branch*, so the first tag-triggered publish was rejected —
> *"Tag v0.8.0 is not allowed to deploy to pypi due to environment
> protection rules."* This section is the operator contract that keeps that
> from recurring.

The Release workflow runs from a **tag ref** (`refs/tags/vX.Y.Z`) and
deploys through three GitHub **deployment environments**, each with its own
protection rules under Settings → Environments:

| Environment | Deploying job | Required deployment policy |
|-------------|---------------|----------------------------|
| `pypi` | `publish-pypi` | a **`v*` tag** policy (Selected branches and tags) |
| `testpypi` | `publish-testpypi` | unrestricted, **or** a `v*` tag policy |
| `github-release` | `finalize-release-packet` | unrestricted, **or** a `v*` tag policy |

The rule: **any environment that restricts deployments MUST include a *tag*
policy matching the workflow's `v*` glob.** GitHub's "Deployment branches
and tags" setting has three modes:

- **No restriction** (`deployment_branch_policy: null`) — every ref,
  tags included, may deploy. `testpypi` and `github-release` sit here today.
- **Protected branches only** — *tags can never deploy*; a tag-triggered
  release is rejected outright. Never select this for a release environment.
- **Selected branches and tags** (`custom_branch_policies: true`) — only the
  listed patterns may deploy, so an explicit `v*` rule of type **`tag`** (not
  `branch`) is mandatory. `pypi` sits here: `main` (branch) + `v*` (tag).

### Coupling to the `tag-protection-v` ruleset

The `v*` pattern is shared by two distinct controls that must stay in
agreement:

- the **`tag-protection-v`** ruleset (Settings → Rules, target `tag`)
  governs *who may create* a `v*` release tag;
- each environment's **`v*` tag deployment policy** governs *whether that
  tag may deploy* to PyPI / TestPyPI / the GitHub Release.

Both key on `v*`; changing the tag shape in one without the other reopens
the drift.

### Applying or repairing a policy

To move an environment to "Selected branches and tags" and add the `v*`
tag rule (repeat per restricted environment — the environment must already
be in "Selected branches and tags" mode for the POST to take effect):

```bash
gh api --method POST \
  repos/arcasilesgroup/ai-engineering/environments/pypi/deployment-branch-policies \
  -f name='v*' -f type='tag'
```

### Why this is guarded twice

Like the `CI Result` check above, environment policies live in **GitHub
settings, not in the repo**, so committed code cannot enforce them. Two
guards make drift loud instead of silent:

- **`ai-eng doctor`** runs a `release-env-policy` runtime check
  ([`src/ai_engineering/doctor/runtime/release_env_policy.py`](../src/ai_engineering/doctor/runtime/release_env_policy.py))
  that reads each environment's *live* deployment policy and WARNs when the
  `v*` tag pattern is missing. It is operator-run, needs `gh` authenticated
  with admin scope, and is WARN-only (never blocks a developer's run).
- **[`tests/unit/workflows/test_release_env_policy_docs.py`](../tests/unit/workflows/test_release_env_policy_docs.py)**
  fails CI if `release.yml` stays tag-triggered while a deployment
  environment it uses is left undocumented in this table — so adding a new
  publish environment forces a matching policy note here. The tag trigger
  itself is held in place by
  [`scripts/check_workflow_policy.py`](../scripts/check_workflow_policy.py)
  (`workflow-sanity` job).
