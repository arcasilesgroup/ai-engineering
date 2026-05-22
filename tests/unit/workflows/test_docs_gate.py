"""spec-152 W5.T34 — governance-docs CI floor (D-152-22).

Before this wave a docs-only change fully bypassed CI: ``docs/**`` was in the
``paths-ignore`` of both the ``push`` and ``pull_request`` triggers, so the
workflow never started and the required ``CI Result`` check reported success by
default. A docs-only PR that introduced a machine path, a leaked secret in a
fenced block, or a malformed workflow snippet would merge unchecked.

The floor relaxes that: ``docs/**`` no longer fully skips CI. A lightweight
``docs-gate`` job runs the CHEAP checks (workflow sanity-equivalent + content
integrity + a secret scan) whenever docs change, while the heavy test matrix
stays gated to ``code == true``.

These tests assert:

* ``docs/**`` is no longer in either ``paths-ignore`` list;
* a ``docs-gate`` job exists and is gated on the docs change signal;
* ``docs-gate`` is wired into ``ci-check-result.needs`` and an evaluated array
  (so the aggregate actually inspects it);
* the heavy matrix (``test-unit`` / ``test-integration``) stays ``code``-gated.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CI_CHECK_PATH = REPO_ROOT / ".github" / "workflows" / "ci-check.yml"

AGGREGATE_JOB = "ci-check-result"
DOCS_GATE_JOB = "docs-gate"
HEAVY_MATRIX_JOBS = ("test-unit", "test-integration")
EVALUATED_ARRAYS = (
    "always_required",
    "code_conditional",
    "docs_conditional",
    "pr_only",
    "pr_all",
    "token_conditional",
    "optional",
)


def _load() -> dict[str, Any]:
    assert CI_CHECK_PATH.exists(), f"missing workflow: {CI_CHECK_PATH}"
    data = yaml.safe_load(CI_CHECK_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "ci-check.yml must parse to a YAML mapping"
    return data


def _triggers(data: dict[str, Any]) -> dict[str, Any]:
    raw = data.get("on", data.get(True, {}))
    return raw if isinstance(raw, dict) else {}


def _needs_set(job: dict[str, Any]) -> set[str]:
    needs = job.get("needs", [])
    if isinstance(needs, str):
        return {needs}
    return {str(item) for item in needs} if isinstance(needs, list) else set()


def _aggregate_eval_script(data: dict[str, Any]) -> str:
    job = data["jobs"][AGGREGATE_JOB]
    for step in job.get("steps") or []:
        run = (step or {}).get("run")
        if isinstance(run, str) and "code_conditional" in run:
            return run
    raise AssertionError(f"{AGGREGATE_JOB} has no evaluate step containing the gate arrays")


def _array_members(script: str, array_name: str) -> set[str]:
    open_match = re.search(rf"{re.escape(array_name)}=\(", script)
    if open_match is None:
        return set()
    start = open_match.end()
    close = script.find(")", start)
    assert close != -1, f"unterminated array {array_name!r}"
    block = script[start:close]
    return set(re.findall(r'"([a-z0-9][a-z0-9-]*):\$\{\{', block))


def test_docs_paths_no_longer_fully_ignored() -> None:
    """``docs/**`` is removed from both ``paths-ignore`` lists.

    Leaving ``docs/**`` in ``paths-ignore`` means a docs-only change never
    triggers CI and ``CI Result`` defaults to success — the fail-open hole the
    floor closes (D-152-22).
    """
    data = _load()
    triggers = _triggers(data)
    offenders: list[str] = []
    for event in ("push", "pull_request"):
        cfg = triggers.get(event)
        if not isinstance(cfg, dict):
            continue
        ignore = cfg.get("paths-ignore") or []
        if "docs/**" in ignore:
            offenders.append(event)
    assert not offenders, (
        f"'docs/**' must NOT be in paths-ignore for {offenders} — a docs-only "
        "change must still run the docs CI floor (spec-152 T-34/D-152-22)"
    )


def test_docs_gate_job_exists_and_is_docs_scoped() -> None:
    """A ``docs-gate`` job exists and runs when docs (or code) change.

    It must consult the ``change-scope`` docs signal so it actually runs on a
    docs-only change rather than being silently code-gated.
    """
    data = _load()
    jobs = data.get("jobs", {})
    assert DOCS_GATE_JOB in jobs, (
        f"{DOCS_GATE_JOB!r} job must exist to run the docs CI floor (T-34)"
    )
    job = jobs[DOCS_GATE_JOB]
    assert isinstance(job, dict), f"{DOCS_GATE_JOB} must be a mapping"
    condition = str(job.get("if", ""))
    # It must run on docs changes — either an explicit docs-output gate or no
    # `if` at all (runs whenever the workflow triggers). A pure `code == true`
    # gate would defeat the floor on a docs-only change.
    assert "docs" in condition or condition == "", (
        f"{DOCS_GATE_JOB} must run on docs changes (gate on change-scope.outputs.docs "
        f"or run unconditionally); got if: {condition!r}"
    )
    assert not re.fullmatch(
        r"\s*\$\{\{\s*needs\.change-scope\.outputs\.code\s*==\s*'true'\s*\}\}\s*", condition
    ), f"{DOCS_GATE_JOB} must not be gated solely on code == true (defeats the floor)"


def test_docs_gate_is_wired_into_aggregate() -> None:
    """``docs-gate`` is in ``ci-check-result.needs`` and exactly one array."""
    data = _load()
    aggregate = data["jobs"][AGGREGATE_JOB]
    assert DOCS_GATE_JOB in _needs_set(aggregate), (
        f"{DOCS_GATE_JOB} must be in {AGGREGATE_JOB}.needs so the aggregate awaits it"
    )
    script = _aggregate_eval_script(data)
    containing = [
        name for name in EVALUATED_ARRAYS if DOCS_GATE_JOB in _array_members(script, name)
    ]
    assert len(containing) == 1, (
        f"{DOCS_GATE_JOB} must be evaluated in exactly one array; found {containing!r}"
    )


def test_heavy_matrix_stays_code_gated() -> None:
    """The heavy test matrix remains gated to ``code == true``.

    The floor must NOT run the full unit/integration matrix on a docs-only
    change — that would defeat the cost saving the paths-ignore once provided.
    """
    data = _load()
    jobs = data.get("jobs", {})
    for name in HEAVY_MATRIX_JOBS:
        job = jobs.get(name)
        assert isinstance(job, dict), f"{name} job must exist"
        condition = str(job.get("if", ""))
        assert "code == 'true'" in condition or "code==true" in condition.replace(" ", ""), (
            f"{name} must stay gated to code == 'true' (heavy matrix off the docs floor); "
            f"got if: {condition!r}"
        )
