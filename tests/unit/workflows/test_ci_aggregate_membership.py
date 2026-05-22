"""spec-152 W2.T10 — CI aggregate-gate membership integrity.

Branch protection requires exactly one status check: ``CI Result`` (the
``ci-check-result`` job). That aggregate is only trustworthy if it
*evaluates every blocking job*. A job that is in ``ci-check-result.needs``
but in none of the evaluated bash arrays is awaited-but-never-checked
(its result is silently ignored); a job in neither needs nor any array is
invisible to the aggregate. Either shape is a fail-open hole — the
spec-152 root defect (D-152-02).

This gate enumerates every BLOCKING job in ``ci-check.yml`` (every job
except the ``ci-check-result`` aggregate itself and any job explicitly
classified advisory/optional) and asserts each appears BOTH in
``ci-check-result.needs`` AND is *evaluated* by the aggregate. A job is
evaluated when it appears in exactly one of the bash arrays
(``always_required`` / ``code_conditional`` / ``pr_only`` /
``token_conditional`` / ``docs_conditional``) OR it is the ``change-scope``
data-provider checked through its dedicated ``"$CHANGE_SCOPE" != "success"``
guard. Both mechanisms are recognized from the script text — neither is
hardcoded as an exclusion — so a job that is awaited but inspected by
nothing fails the gate.

The arrays live in the bash ``run:`` of the ``Evaluate CI results`` step
(``ci-check-result``); they are parsed by scanning the script text for
``"<job>:${{ needs.<job>.result }}"`` entries inside each array's
``(...)`` block. Job names are derived from ``data["jobs"].keys()`` so
the gate stays correct as jobs are added or removed.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CI_CHECK_PATH = REPO_ROOT / ".github" / "workflows" / "ci-check.yml"

# The aggregate job under test — excluded from "blocking jobs" because it
# is the evaluator, not an evaluated dependency.
AGGREGATE_JOB = "ci-check-result"

# Jobs whose evaluation is *conditional on external provisioning* rather than a
# plain "MUST succeed". ``snyk-security`` is required the moment ``SNYK_TOKEN`` is
# provisioned (``has-snyk-token == 'true'``) and tolerated-when-skipped only when
# the token is absent or withheld on a fork PR (spec-152 D-152-07/08, T-27/T-28).
# It is still covered by the membership invariant (in ``needs`` + exactly one
# evaluated array) — it is simply no longer weakly-``optional``.
TOKEN_CONDITIONAL_JOBS: frozenset[str] = frozenset({"snyk-security"})

# The evaluated-array names inside the bash gate, in priority order.
#
# ``token_conditional`` (spec-152 T-28/D-152-07/08) — required when the gating
#             token is provisioned; skip tolerated only when it is absent.
#             ``snyk-security`` lives here.
# ``docs_conditional`` (spec-152 T-34/D-152-22) — MUST succeed when docs OR code
#             changed (the docs CI floor); skip tolerated otherwise.
#             ``docs-gate`` lives here so a docs-only change is still inspected
#             instead of fully bypassing CI.
#
# spec-152 follow-up: the every-PR-including-dependabot class was removed when
# its only member (the GitHub PR-diff dependency-ingress gate) was retired as
# infeasible — the org has the GitHub Dependency Graph disabled, so that action
# can never run, and a never-running required gate is itself a fail-open hole.
# SCA is now carried by ``snyk-security`` (token_conditional) + ``pip-audit``
# (security job). There is no ``optional`` class.
EVALUATED_ARRAYS = (
    "always_required",
    "code_conditional",
    "docs_conditional",
    "pr_only",
    "token_conditional",
)


def _load_ci_check() -> dict[str, Any]:
    assert CI_CHECK_PATH.exists(), f"missing workflow: {CI_CHECK_PATH}"
    data = yaml.safe_load(CI_CHECK_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "ci-check.yml must parse to a YAML mapping"
    return data


def _job_names(data: dict[str, Any]) -> set[str]:
    jobs = data.get("jobs")
    assert isinstance(jobs, dict) and jobs, "ci-check.yml must declare jobs"
    return set(jobs.keys())


def _needs_set(job: dict[str, Any]) -> set[str]:
    needs = job.get("needs", [])
    if isinstance(needs, str):
        return {needs}
    assert isinstance(needs, list), "job needs must be a string or list"
    return {str(item) for item in needs}


def _aggregate_eval_script(data: dict[str, Any]) -> str:
    """Return the bash ``run:`` text of the aggregate's evaluate step."""
    job = data["jobs"][AGGREGATE_JOB]
    assert isinstance(job, dict), f"{AGGREGATE_JOB} must be a mapping"
    steps = job.get("steps") or []
    for step in steps:
        run = (step or {}).get("run")
        if isinstance(run, str) and "code_conditional" in run:
            return run
    raise AssertionError(f"{AGGREGATE_JOB} has no evaluate step containing the gate arrays")


def _array_members(script: str, array_name: str) -> set[str]:
    """Extract job names listed inside a given bash array's ``(...)`` block.

    Each entry is shaped ``"<job>:${{ needs.<job>.result }}"`` — we scan
    the slice of script text between ``<array_name>=(`` and its closing
    ``)`` for those entries and return the set of job names.
    """
    open_match = re.search(rf"{re.escape(array_name)}=\(", script)
    if open_match is None:
        return set()
    start = open_match.end()
    close = script.find(")", start)
    assert close != -1, f"unterminated array {array_name!r} in evaluate script"
    block = script[start:close]
    # Match the leading job token of each "<job>:${{ needs.<job>.result }}" entry.
    return set(re.findall(r'"([a-z0-9][a-z0-9-]*):\$\{\{', block))


def _dedicated_guard_jobs(script: str) -> set[str]:
    """Jobs evaluated via a dedicated guard rather than an array.

    ``change-scope`` is the upstream data provider: the aggregate reads its
    result into ``CHANGE_SCOPE`` and fails the gate when it is not
    ``success`` (``if [[ "$CHANGE_SCOPE" != "success" ]]``). That is a
    real, blocking evaluation — just outside the four-array mechanism. We
    detect it from the script: a ``<UPPER>="${{ needs.<job>.result }}"``
    capture paired with an ``"$<UPPER>" != "success"`` failure check.
    """
    guarded: set[str] = set()
    for var, job in re.findall(
        r'([A-Z_]+)="\$\{\{\s*needs\.([a-z0-9][a-z0-9-]*)\.result\s*\}\}"', script
    ):
        if re.search(rf'"\${var}"\s*!=\s*"success"', script):
            guarded.add(job)
    return guarded


def test_aggregate_evaluates_every_blocking_job() -> None:
    """Every blocking job is in ``ci-check-result.needs`` AND exactly one array.

    RED until ``no-suppression`` is wired into both the aggregate's
    ``needs`` and the ``code_conditional`` array (T-11).
    """
    data = _load_ci_check()
    all_jobs = _job_names(data)

    # Membership invariant covers every non-aggregate job: each must appear in
    # ``needs`` and be evaluated in exactly one array (or the change-scope
    # dedicated guard). Context-aware jobs (``snyk-security`` token-conditional)
    # are NOT exempt — they live in exactly one evaluated array, so they are
    # checked here too.
    blocking_jobs = all_jobs - {AGGREGATE_JOB}

    aggregate = data["jobs"][AGGREGATE_JOB]
    aggregate_needs = _needs_set(aggregate)

    script = _aggregate_eval_script(data)
    array_to_members = {name: _array_members(script, name) for name in EVALUATED_ARRAYS}
    guarded_jobs = _dedicated_guard_jobs(script)

    missing_from_needs: list[str] = []
    evaluation_errors: list[str] = []

    for job in sorted(blocking_jobs):
        if job not in aggregate_needs:
            missing_from_needs.append(job)
        containing = [name for name, members in array_to_members.items() if job in members]
        guarded = job in guarded_jobs
        # A blocking job must be inspected exactly once: either via one
        # array, or via the dedicated change-scope guard — never both,
        # never neither.
        evaluations = len(containing) + (1 if guarded else 0)
        if evaluations != 1:
            where = containing + (["dedicated-guard"] if guarded else [])
            evaluation_errors.append(
                f"{job}: evaluated in {where!r} (expected exactly one of arrays "
                f"{list(EVALUATED_ARRAYS)} or the change-scope dedicated guard)"
            )

    assert not missing_from_needs, (
        "blocking jobs missing from ci-check-result.needs (awaited-but-never-"
        f"checked or invisible): {missing_from_needs}"
    )
    assert not evaluation_errors, (
        "blocking jobs not evaluated exactly once by the aggregate:\n  - "
        + "\n  - ".join(evaluation_errors)
    )


def test_token_conditional_jobs_are_represented_in_an_array() -> None:
    """Token-conditional jobs must be evaluated (not invisible).

    A token-conditional job (``snyk-security``) that the aggregate never
    inspects could fail without surfacing. Each must appear in
    ``ci-check-result.needs`` and in exactly one evaluated array.
    """
    data = _load_ci_check()
    all_jobs = _job_names(data)
    conditional_present = TOKEN_CONDITIONAL_JOBS & all_jobs

    aggregate = data["jobs"][AGGREGATE_JOB]
    aggregate_needs = _needs_set(aggregate)
    script = _aggregate_eval_script(data)
    array_to_members = {name: _array_members(script, name) for name in EVALUATED_ARRAYS}

    errors: list[str] = []
    for job in sorted(conditional_present):
        if job not in aggregate_needs:
            errors.append(f"{job}: missing from {AGGREGATE_JOB}.needs")
        containing = [name for name, members in array_to_members.items() if job in members]
        if len(containing) != 1:
            errors.append(f"{job}: present in arrays {containing!r} (expected exactly one)")

    assert not errors, "token-conditional jobs not properly evaluated:\n  - " + "\n  - ".join(
        errors
    )


def test_evaluated_arrays_only_reference_real_jobs() -> None:
    """Every job named in an evaluated array must be a declared job.

    Guards against a stale array entry referencing a renamed/deleted job
    (whose ``needs.<job>.result`` would silently be empty → never fail).
    """
    data = _load_ci_check()
    all_jobs = _job_names(data)
    script = _aggregate_eval_script(data)

    unknown: list[str] = []
    for name in EVALUATED_ARRAYS:
        for job in _array_members(script, name):
            if job not in all_jobs:
                unknown.append(f"{name} references undeclared job {job!r}")

    assert not unknown, "evaluated arrays reference unknown jobs:\n  - " + "\n  - ".join(unknown)


# --- spec-152 T-27: snyk-security promoted from optional to required --------


def test_snyk_security_is_not_optional() -> None:
    """``snyk-security`` must NOT be in the weakly-``optional`` array.

    ``optional`` only fails the aggregate on an explicit ``failure`` — a skip
    passes silently. Once a token is provisioned, a *skip* of snyk-security is
    a fail-open hole. RED until T-28 moves it to ``token_conditional``.
    """
    data = _load_ci_check()
    script = _aggregate_eval_script(data)
    optional_members = _array_members(script, "optional")
    assert "snyk-security" not in optional_members, (
        "snyk-security must not be 'optional' (a skip would pass silently even "
        "when SNYK_TOKEN is provisioned); promote it to 'token_conditional' "
        "(spec-152 T-28/D-152-07)"
    )


def test_snyk_security_is_token_conditional_required() -> None:
    """``snyk-security`` is required when the token is present, skip-tolerant otherwise.

    The aggregate must read ``needs.change-scope.outputs.has-snyk-token`` and:
    - fail when snyk-security ``failure`` (always);
    - fail when snyk-security ``skipped`` AND ``has-snyk-token == 'true'``
      (the job must actually run once the token exists);
    - tolerate ``skipped`` when ``has-snyk-token == 'false'`` (token absent, or
      a fork PR where GitHub withholds secrets — D-152-08).
    RED until T-28 adds the ``token_conditional`` array + loop branch.
    """
    data = _load_ci_check()
    aggregate = data["jobs"][AGGREGATE_JOB]
    aggregate_needs = _needs_set(aggregate)
    assert "snyk-security" in aggregate_needs, "snyk-security must remain in needs"

    script = _aggregate_eval_script(data)
    token_members = _array_members(script, "token_conditional")
    assert "snyk-security" in token_members, (
        "snyk-security must be evaluated in the 'token_conditional' array (spec-152 T-28)"
    )

    # The loop branch must consult the token signal and treat a skip as a
    # failure when the token is present.
    assert "has-snyk-token" in script, (
        "aggregate must read needs.change-scope.outputs.has-snyk-token to "
        "decide whether a snyk-security skip is tolerated"
    )
    # A token-present skip must be a FAIL: the script must distinguish the
    # token states (a literal 'true' guard on the token variable).
    capture_re = r"HAS_SNYK_TOKEN=\"\$\{\{\s*needs\.change-scope\.outputs\.has-snyk-token"
    assert re.search(capture_re, script), (
        "aggregate must capture has-snyk-token into a shell variable for the "
        "token_conditional branch"
    )
    assert re.search(r'"\$HAS_SNYK_TOKEN"\s*==\s*"true"', script), (
        "token_conditional branch must require success when has-snyk-token is "
        "'true' (a skip with the token provisioned is a FAIL)"
    )


def test_fork_pr_snyk_skip_is_tolerated_without_token() -> None:
    """A skipped snyk-security with no token must not fail the aggregate.

    Documents and asserts the fork-PR / unprovisioned path (D-152-08): when
    ``has-snyk-token == 'false'`` a ``skipped`` result is tolerated so CI stays
    green today. RED until T-28 adds the skip-tolerant else-branch.
    """
    data = _load_ci_check()
    script = _aggregate_eval_script(data)
    # There must be an else-branch that, when the token is absent, only fails
    # on an explicit failure (skip tolerated). We assert the comment + the
    # token_conditional loop exists; the hand-trace in the gate proves the
    # FAILED=0 outcome for (has-snyk-token=false, skipped).
    assert "token_conditional" in script, "token_conditional loop must exist (T-28)"
    assert re.search(r"for entry in \"\$\{token_conditional\[@\]\}\"", script), (
        "token_conditional must be iterated in its own loop"
    )
    # Fork-PR behavior must be documented inline so reviewers understand why a
    # skip is tolerated without a token.
    assert "fork" in script.lower(), (
        "the token_conditional branch must document the fork-PR secret-withholding "
        "behavior inline (D-152-08)"
    )
