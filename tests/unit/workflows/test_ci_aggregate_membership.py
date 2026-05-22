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
(``always_required`` / ``code_conditional`` / ``pr_only`` / ``optional``)
OR it is the ``change-scope`` data-provider checked through its dedicated
``"$CHANGE_SCOPE" != "success"`` guard. Both mechanisms are recognized
from the script text — neither is hardcoded as an exclusion — so a job
that is awaited but inspected by nothing fails the gate.

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

# Jobs explicitly classified as advisory/optional: the aggregate may
# accept a skip or (per the optional class) must not let a *failure* pass,
# but they are not "MUST succeed" blocking jobs. They still must appear in
# an evaluated array and in ``needs`` — the membership invariant covers
# every non-aggregate job — but they are documented here so the blocking
# subset is explicit and self-checking.
ADVISORY_JOBS: frozenset[str] = frozenset({"snyk-security"})

# The four evaluated-array names inside the bash gate, in priority order.
EVALUATED_ARRAYS = ("always_required", "code_conditional", "pr_only", "optional")


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

    # Blocking = every job except the aggregate itself and explicit advisories.
    blocking_jobs = all_jobs - {AGGREGATE_JOB} - ADVISORY_JOBS

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


def test_advisory_jobs_are_still_represented_in_an_array() -> None:
    """Advisory/optional jobs must still be evaluated (not invisible).

    An advisory job that the aggregate never inspects could fail without
    surfacing. Each advisory job must appear in ``ci-check-result.needs``
    and in exactly one evaluated array (typically ``optional``).
    """
    data = _load_ci_check()
    all_jobs = _job_names(data)
    advisory_present = ADVISORY_JOBS & all_jobs

    aggregate = data["jobs"][AGGREGATE_JOB]
    aggregate_needs = _needs_set(aggregate)
    script = _aggregate_eval_script(data)
    array_to_members = {name: _array_members(script, name) for name in EVALUATED_ARRAYS}

    errors: list[str] = []
    for job in sorted(advisory_present):
        if job not in aggregate_needs:
            errors.append(f"{job}: missing from {AGGREGATE_JOB}.needs")
        containing = [name for name, members in array_to_members.items() if job in members]
        if len(containing) != 1:
            errors.append(f"{job}: present in arrays {containing!r} (expected exactly one)")

    assert not errors, "advisory jobs not properly evaluated:\n  - " + "\n  - ".join(errors)


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
