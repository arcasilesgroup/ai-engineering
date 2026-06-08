"""spec-166 — gate-trailer waiver for docs-only and fork PRs.

``verify-gate-trailers`` requires every non-merge commit to carry the
``Ai-Eng-Gate: passed`` trailer, which only the local ``commit-msg`` hook
injects. Docs-only contributors and fork/external contributors cannot
produce it, so legitimate PRs (e.g. a runbook translation from a workshop
contributor) are hard-blocked.

spec-166 waives the requirement where it carries no signal:

* **code-free changesets** — ``change-scope.outputs.code != 'true'`` (the
  local gate protects no code); and
* **fork PRs** — ``github.event.pull_request.head.repo.fork == true`` (the
  hook cannot run; repo secrets are withheld).

The waiver is an in-step early-exit (D-166-02): the job still runs and
reports ``success``, so the ``CI Result`` aggregate's ``pr_only`` contract
is left unchanged. This test pins all four invariants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CI_CHECK_PATH = REPO_ROOT / ".github" / "workflows" / "ci-check.yml"

JOB = "verify-gate-trailers"


def _load_ci_check() -> dict[str, Any]:
    assert CI_CHECK_PATH.exists(), f"missing workflow: {CI_CHECK_PATH}"
    data = yaml.safe_load(CI_CHECK_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "ci-check.yml must parse to a YAML mapping"
    return data


def _job(data: dict[str, Any]) -> dict[str, Any]:
    job = data["jobs"].get(JOB)
    assert isinstance(job, dict), f"ci-check.yml must declare job {JOB!r}"
    return job


def _needs_set(job: dict[str, Any]) -> set[str]:
    needs = job.get("needs", [])
    if isinstance(needs, str):
        return {needs}
    assert isinstance(needs, list), "job needs must be a string or list"
    return {str(item) for item in needs}


def _trailer_step_run(job: dict[str, Any]) -> str:
    """Return the bash ``run:`` text of the trailer-checking step."""
    for step in job.get("steps") or []:
        run = (step or {}).get("run")
        if isinstance(run, str) and "Ai-Eng-Gate" in run:
            return run
    raise AssertionError(f"{JOB} has no step that checks the Ai-Eng-Gate trailer")


def test_job_depends_on_change_scope() -> None:
    """D-166-03: the waiver reads change-scope.outputs.code, so it must
    declare change-scope as a dependency (else the output is unavailable)."""
    job = _job(_load_ci_check())
    assert "change-scope" in _needs_set(job), (
        f"{JOB} must `needs: [change-scope]` to read its `code` output (D-166-03)"
    )


def test_code_free_changeset_is_waived() -> None:
    """D-166-01: a code-free changeset short-circuits to success."""
    run = _trailer_step_run(_job(_load_ci_check()))
    assert "needs.change-scope.outputs.code" in run, (
        "trailer step must read change-scope.outputs.code to waive docs-only PRs"
    )
    assert '!= "true"' in run or "!= 'true'" in run, (
        "trailer step must branch on code != 'true' (docs-only waiver)"
    )


def test_fork_pr_is_waived() -> None:
    """D-166-01: a fork PR short-circuits to success (hook cannot run)."""
    run = _trailer_step_run(_job(_load_ci_check()))
    assert "github.event.pull_request.head.repo.fork" in run, (
        "trailer step must read head.repo.fork to waive fork PRs"
    )


def test_waiver_uses_early_exit_zero() -> None:
    """D-166-02: the waiver is an early-exit (job stays success), not a
    failure path — there must be at least one `exit 0` in the step."""
    run = _trailer_step_run(_job(_load_ci_check()))
    assert "exit 0" in run, "waiver must `exit 0` so the job reports success"


def test_ci_result_pr_only_still_lists_the_job() -> None:
    """D-166-02: the CI Result aggregate is unchanged — verify-gate-trailers
    must remain in the `pr_only` array so the contract is not silently
    dropped along with the job-level change."""
    data = _load_ci_check()
    aggregate = data["jobs"].get("ci-check-result")
    assert isinstance(aggregate, dict), "ci-check.yml must declare ci-check-result"
    script = ""
    for step in aggregate.get("steps") or []:
        run = (step or {}).get("run")
        if isinstance(run, str) and "pr_only=" in run:
            script = run
            break
    assert script, "ci-check-result must have an evaluate step defining pr_only"
    pr_only_start = script.index("pr_only=(")
    pr_only_block = script[pr_only_start : script.index(")", pr_only_start)]
    assert JOB in pr_only_block, (
        f"{JOB} must stay in the CI Result `pr_only` array (aggregate unchanged)"
    )
