"""spec-152 W5.T30 — OpenSSF Scorecard CI workflow (D-152-16).

The Scorecard workflow runs the OpenSSF supply-chain posture analysis on a
weekly schedule + push-to-main, publishes the score to the public OpenSSF
dashboard (OIDC), and captures the SARIF result as a workflow artifact. These
tests pin the workflow's security contract:

* the workflow file exists;
* ``ossf/scorecard-action`` is SHA-pinned (a tag/branch ref is a retag risk);
* the SARIF result is captured via a SHA-pinned, top-level ``uses:`` action
  (the canonical example uses the ``github/codeql-action/upload-sarif``
  *sub-path* action, but the frozen ``--check-reachability`` audit cannot
  resolve a sub-path ref — see the workflow comment — so SARIF is captured via
  the reachable ``actions/upload-artifact`` instead);
* the workflow grants ``security-events: write`` + ``id-token: write`` at the
  job that needs it (least-privilege: top-level is ``read-all``);
* every job carries ``timeout-minutes``.

Loaded as raw YAML (not via the policy module) so the assertions are
independent of ``check_workflow_policy.py`` internals.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCORECARD_PATH = REPO_ROOT / ".github" / "workflows" / "scorecard.yml"

SCORECARD_ACTION = "ossf/scorecard-action"
# The canonical Scorecard example uploads SARIF via the
# ``github/codeql-action/upload-sarif`` SUB-PATH action. The frozen
# ``--check-reachability`` audit resolves a pin via
# ``git ls-remote https://github.com/<repo>`` and a sub-path URL 404s, so this
# workflow captures SARIF with the reachable, top-level ``actions/upload-artifact``
# instead (see scorecard.yml). The test asserts the result is captured by a
# SHA-pinned action, not which specific uploader.
SARIF_RESULT_FILE = "results.sarif"
_SHA40 = 40


def _load() -> dict[str, Any]:
    assert SCORECARD_PATH.exists(), f"missing workflow: {SCORECARD_PATH}"
    data = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "scorecard.yml must parse to a YAML mapping"
    return data


def _triggers(data: dict[str, Any]) -> dict[str, Any]:
    """Return the trigger mapping, normalizing PyYAML's boolean ``on:`` key."""
    raw = data.get("on", data.get(True, {}))
    if isinstance(raw, str):
        return {raw: None}
    if isinstance(raw, list):
        return {str(item): None for item in raw}
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _all_uses(data: dict[str, Any]) -> list[str]:
    uses: list[str] = []
    for job in data.get("jobs", {}).values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if isinstance(step, dict):
                value = step.get("uses")
                if isinstance(value, str) and value:
                    uses.append(value.split("#")[0].strip())
    return uses


def _is_sha_pinned(use: str) -> bool:
    if "@" not in use:
        return False
    ref = use.rsplit("@", 1)[1]
    return len(ref) == _SHA40 and all(c in "0123456789abcdef" for c in ref)


def test_scorecard_workflow_exists() -> None:
    """The Scorecard workflow file is present (D-152-16)."""
    assert SCORECARD_PATH.exists(), (
        "scorecard.yml must exist to run the OpenSSF Scorecard supply-chain "
        "posture analysis (spec-152 T-30/D-152-16)"
    )


def test_scorecard_action_is_sha_pinned() -> None:
    """``ossf/scorecard-action`` is pinned to a 40-char commit SHA."""
    data = _load()
    uses = _all_uses(data)
    scorecard_uses = [u for u in uses if u.split("@")[0] == SCORECARD_ACTION]
    assert scorecard_uses, f"scorecard.yml must invoke {SCORECARD_ACTION}; found uses: {uses!r}"
    for use in scorecard_uses:
        assert _is_sha_pinned(use), (
            f"{use!r} must be SHA-pinned (owner/action@<40-hex-sha> # vN.M.P) — a "
            "tag/branch ref is a retag supply-chain risk (D-152-05)"
        )


def test_scorecard_captures_sarif_result() -> None:
    """The SARIF result is produced and captured by a SHA-pinned uploader.

    The analysis step writes ``results.sarif`` and a subsequent ``uses:`` step
    captures it (artifact upload or code-scanning upload). Asserting on the
    captured filename keeps the test agnostic to which uploader is used, while
    still requiring that whatever uploads it is SHA-pinned (next test).
    """
    data = _load()
    text = SCORECARD_PATH.read_text(encoding="utf-8")
    assert SARIF_RESULT_FILE in text, f"scorecard.yml must produce/capture {SARIF_RESULT_FILE!r}"
    # A capture step references the SARIF file in a `with:` input.
    captured = False
    for job in data.get("jobs", {}).values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            with_block = step.get("with") or {}
            if isinstance(with_block, dict) and any(
                isinstance(v, str) and SARIF_RESULT_FILE in v for v in with_block.values()
            ):
                captured = step.get("uses", "")
    assert captured, f"a step must capture {SARIF_RESULT_FILE!r} (artifact or code-scanning upload)"
    assert _is_sha_pinned(str(captured).split("#")[0].strip()), (
        f"the SARIF uploader {captured!r} must be SHA-pinned (D-152-05)"
    )


def test_all_scorecard_actions_are_sha_pinned() -> None:
    """Every ``uses:`` in scorecard.yml is SHA-pinned (no first-party exemption)."""
    data = _load()
    unpinned = [u for u in _all_uses(data) if not u.startswith("./") and not _is_sha_pinned(u)]
    assert not unpinned, f"scorecard.yml has unpinned actions (D-152-05): {unpinned!r}"


def test_scorecard_triggers_schedule_push_main_and_dispatch() -> None:
    """Scorecard runs weekly + on push-to-main + manual dispatch."""
    data = _load()
    triggers = _triggers(data)
    assert "schedule" in triggers, "scorecard.yml must run on a schedule (weekly cron)"
    assert "workflow_dispatch" in triggers, "scorecard.yml must allow manual dispatch"
    push = triggers.get("push")
    assert isinstance(push, dict), "scorecard.yml must trigger on push (to publish results)"
    branches = push.get("branches") or []
    assert "main" in branches, (
        f"scorecard.yml push trigger must target the default branch 'main'; got {branches!r}"
    )


def test_scorecard_has_least_privilege_permissions() -> None:
    """Top-level is read-only; the analysis job adds only the writes it needs."""
    data = _load()
    top = data.get("permissions")
    assert top == "read-all" or (isinstance(top, dict) and top.get("contents") == "read"), (
        f"scorecard.yml top-level permissions must be read-only (read-all); got {top!r}"
    )

    jobs = data.get("jobs", {})
    assert isinstance(jobs, dict) and jobs, "scorecard.yml must declare jobs"
    grants_security_events = False
    grants_id_token = False
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        perms = job.get("permissions")
        if isinstance(perms, dict):
            if perms.get("security-events") == "write":
                grants_security_events = True
            if perms.get("id-token") == "write":
                grants_id_token = True
    assert grants_security_events, (
        "a scorecard job must grant 'security-events: write' to upload SARIF"
    )
    assert grants_id_token, (
        "a scorecard job must grant 'id-token: write' to publish the Scorecard result"
    )


def test_scorecard_jobs_have_timeouts() -> None:
    """Every job declares ``timeout-minutes`` (policy + runaway guard)."""
    data = _load()
    jobs = data.get("jobs", {})
    assert isinstance(jobs, dict) and jobs, "scorecard.yml must declare jobs"
    missing = [
        name for name, job in jobs.items() if isinstance(job, dict) and "timeout-minutes" not in job
    ]
    assert not missing, f"scorecard.yml jobs missing timeout-minutes: {missing}"
