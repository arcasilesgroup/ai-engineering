"""spec-201 D-201-18 — cross-model replay ships ADVISORY, never blocking.

A blocking gate against a third-party provider would make every merge hostage
to that provider's uptime and quota — one connection drop was already observed
during probing — and would egress fixture text on every pull request. The
advisory property is pinned here as structure rather than left to a comment:

* every job carries ``continue-on-error: true``;
* the workflow lives OUTSIDE the ``CI Result`` aggregate by construction,
  because that aggregate enumerates jobs from ``ci-check.yml`` alone;
* every action it uses is byte-identical to one already present in
  ``skill-evals.yml``, so the repository's Actions allowlist is structurally
  incapable of producing a ``startup_failure`` on a new action name.

RK-11 additionally requires the data-governance posture to be written into the
spec BEFORE any CI matrix run; that is asserted here too, so the job cannot
land ahead of its own egress declaration.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
REPLAY_PATH = REPO_ROOT / ".github" / "workflows" / "cross-model-replay.yml"
SKILL_EVALS_PATH = REPO_ROOT / ".github" / "workflows" / "skill-evals.yml"
CI_CHECK_PATH = REPO_ROOT / ".github" / "workflows" / "ci-check.yml"
SPEC_PATH = REPO_ROOT / ".ai-engineering" / "specs" / "spec.md"
ARCHIVE_DIR = REPO_ROOT / ".ai-engineering" / "specs" / "archive"
CORPUS_DIR = REPO_ROOT / ".ai-engineering" / "evals" / "cross-model-replay"
_PLACEHOLDER_PREFIX = "# No active spec"


def _spec_text() -> str | None:
    """The spec-201 spec, wherever the lifecycle currently keeps it.

    D-167 consolidation runs ``mark_shipped`` on this branch BEFORE the merge:
    it snapshots the spec into ``specs/archive/spec-201-<slug>/spec.md`` and
    overwrites the live slot with the ``# No active spec`` placeholder. A test
    bound to the live slot alone reds this PR, then reds ``main``, then blocks
    every subsequent PR — the idle-slot regression already paid for once in
    PR#565. Archive first, live slot second, placeholder tolerated.
    """
    candidates = [*sorted(ARCHIVE_DIR.glob("spec-201-*/spec.md")), SPEC_PATH]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        text = candidate.read_text(encoding="utf-8")
        if not text.lstrip().startswith(_PLACEHOLDER_PREFIX):
            return text
    return None


def _uses(workflow: dict) -> set[str]:
    """Every ``uses:`` string across every job step."""
    found: set[str] = set()
    for job in (workflow.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("uses"), str):
                found.add(step["uses"])
    return found


@pytest.fixture(scope="module")
def workflow() -> dict:
    assert REPLAY_PATH.exists(), f"missing workflow: {REPLAY_PATH}"
    return yaml.safe_load(REPLAY_PATH.read_text(encoding="utf-8"))


def test_workflow_parses_and_declares_its_triggers(workflow: dict) -> None:
    """Both a paths-filtered PR trigger and a deliberate manual dispatch."""
    # PyYAML lowers the `on:` key to the boolean ``True``.
    triggers = workflow.get(True) or workflow.get("on") or {}
    assert "workflow_dispatch" in triggers, list(triggers)
    assert "pull_request" in triggers, list(triggers)
    assert (triggers["pull_request"] or {}).get("paths"), (
        "the PR trigger must be paths-filtered — this job talks to a third party"
    )


def test_every_job_is_advisory(workflow: dict) -> None:
    """``continue-on-error: true`` everywhere: advisory means it cannot block."""
    jobs = workflow.get("jobs") or {}
    assert jobs, "workflow declares no jobs"
    for name, job in jobs.items():
        assert job.get("continue-on-error") is True, (
            f"job {name!r} must set `continue-on-error: true` (D-201-18)"
        )


def test_workflow_is_outside_the_required_ci_aggregate(workflow: dict) -> None:
    """The `CI Result` aggregate cannot see a job in a separate workflow file.

    Asserted rather than assumed: the aggregate enumerates its dependencies
    from ``ci-check.yml``'s own jobs, so a job defined elsewhere is advisory by
    construction — no flag to flip, nothing to forget.
    """
    ci_check = yaml.safe_load(CI_CHECK_PATH.read_text(encoding="utf-8"))
    needs = set(ci_check["jobs"]["ci-check-result"]["needs"])
    for name in workflow.get("jobs") or {}:
        assert name not in needs, f"{name!r} leaked into the required CI aggregate"
    assert "cross-model-replay" not in CI_CHECK_PATH.read_text(encoding="utf-8")


def test_introduces_no_new_action_reference(workflow: dict) -> None:
    """Every non-local action is already used by `skill-evals.yml`, verbatim.

    The repository's Actions allowlist rejects unknown action names with a
    ``startup_failure``. Reusing existing references at existing SHAs makes
    that failure mode structurally impossible for this workflow.
    """
    known = _uses(yaml.safe_load(SKILL_EVALS_PATH.read_text(encoding="utf-8")))
    for reference in _uses(workflow):
        if reference.startswith("./"):
            continue
        assert reference in known, (
            f"{reference!r} is not already used by skill-evals.yml — "
            "a new action name can trip the repository Actions allowlist"
        )
        _, _, pin = reference.partition("@")
        assert len(pin) == 40 and all(c in "0123456789abcdef" for c in pin), reference


def test_spec_records_the_data_governance_posture() -> None:
    """RK-11: retention, tenancy, jurisdiction and model licences, in the spec."""
    spec = _spec_text()
    if spec is None:
        pytest.skip("spec-201 is neither in the live slot nor in the archive")
    assert "## Data Governance" in spec
    section = spec.split("## Data Governance", 1)[1].split("\n## ", 1)[0].lower()
    for item in ("retention", "tenancy", "jurisdiction", "licen"):
        assert item in section, f"Data Governance section does not address {item!r}"


def test_claude_reference_is_a_recorded_file_not_a_claim() -> None:
    """ "With a recorded Claude reference" must be a file on disk."""
    reference = CORPUS_DIR / "claude-reference.json"
    corpus = CORPUS_DIR / "corpus.json"
    assert reference.is_file(), reference
    assert corpus.is_file(), corpus

    corpus_data = json.loads(corpus.read_text(encoding="utf-8"))
    reference_data = json.loads(reference.read_text(encoding="utf-8"))

    questions = corpus_data["questions"]
    assert len(questions) == 8, "brief E10 recorded eight routing questions"
    for question in questions:
        assert question["id"] and question["prompt"] and question["expected"]

    answers = reference_data["answers"]
    assert {a["id"] for a in answers} == {q["id"] for q in questions}
    assert reference_data["score"] == len(questions), "the recorded reference is 8/8"
