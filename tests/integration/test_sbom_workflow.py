"""RED-phase test for spec-110 Phase 2 — SBOM workflow presence.

Spec acceptance criterion (governance v3 harvest, Phase 2 gate):
    A new workflow ``.github/workflows/sbom.yml`` generates and uploads
    a CycloneDX SBOM (``sbom.cdx.json``) as an artifact on every PR and
    push to ``main``. The workflow must use ``actions/upload-artifact``
    to publish the artifact so consumers can audit the dependency tree
    of any commit that lands on the default branch.

Status: RED (``.github/workflows/sbom.yml`` does not yet exist). T-2.7
creates the workflow during the GREEN phase. This test deliberately
fails now to drive that work.

Tolerances:
- The ``on:`` block in GitHub Actions YAML can take several shapes
  (``on: push``, ``on: [push, pull_request]``, ``on: { push: ... }``).
  The trigger checks accept any of these as long as ``pull_request`` is
  present and ``push`` is configured for ``main``. ``push`` configured
  with no branch filter is also accepted (it implies all branches,
  including ``main``).
- Any 40-character SHA suffix on ``actions/upload-artifact`` is
  accepted; SHA-pinning is enforced separately by
  ``test_workflow_sha_pinning.py`` so this test stays focused on
  SBOM-specific behaviour.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Repo root: tests/integration/<this file> → up 3 levels.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SBOM_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "sbom.yml"

UPLOAD_ARTIFACT_ACTION = "actions/upload-artifact"
SBOM_ARTIFACT_FILENAME = "sbom.cdx.json"


def _normalize_triggers(on_node: Any) -> dict[str, Any]:
    """Return a ``{trigger_name: trigger_config_or_None}`` view of ``on:``.

    GitHub Actions accepts three shapes for ``on:``:

    1. Scalar — ``on: push`` → ``{"push": None}``.
    2. Sequence — ``on: [push, pull_request]`` →
       ``{"push": None, "pull_request": None}``.
    3. Mapping — ``on: { push: { branches: [main] }, pull_request: {} }``
       which passes through unchanged.

    The normalised form lets trigger-presence assertions stay simple
    regardless of which YAML shape the workflow author chose.
    """
    if isinstance(on_node, str):
        return {on_node: None}
    if isinstance(on_node, list):
        return {item: None for item in on_node if isinstance(item, str)}
    if isinstance(on_node, dict):
        return dict(on_node)
    return {}


def _push_targets_main(push_config: Any) -> bool:
    """Return ``True`` when a ``push`` trigger configuration covers ``main``.

    ``push_config`` is the value mapped from the ``push`` key in the
    normalised ``on:`` block. It can be:

    - ``None`` — no filter, all branches → covers ``main``.
    - A mapping without ``branches`` — covers ``main``.
    - A mapping with ``branches: [..., "main", ...]`` — covers ``main``.
    - A mapping with ``branches`` listing only other refs — does NOT
      cover ``main``.
    """
    if push_config is None:
        return True
    if not isinstance(push_config, dict):
        return False
    branches = push_config.get("branches")
    if branches is None:
        return True
    if isinstance(branches, list):
        return "main" in branches
    if isinstance(branches, str):
        return branches == "main"
    return False


def _iter_steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every ``steps[]`` entry across every job in the workflow.

    Steps are nested under ``jobs.<id>.steps`` in GitHub Actions YAML.
    Returning a flat list keeps downstream assertions simple — order is
    not significant for the upload-artifact presence check.
    """
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return []
    flattened: list[dict[str, Any]] = []
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if isinstance(steps, list):
            flattened.extend(step for step in steps if isinstance(step, dict))
    return flattened


def _path_contains_sbom_filename(with_path: Any) -> bool:
    """Return ``True`` when an ``upload-artifact`` ``with.path`` covers the SBOM.

    The ``path`` input accepts either a single string or a multiline
    string with one path per line. Both shapes are normalised to a
    membership check against the literal ``sbom.cdx.json`` filename so
    minor formatting differences (trailing newline, leading ``./``) do
    not break the assertion.
    """
    if not isinstance(with_path, str):
        return False
    return SBOM_ARTIFACT_FILENAME in with_path


def test_sbom_workflow_present_and_uploads_artifact() -> None:
    """``.github/workflows/sbom.yml`` exists, triggers correctly, uploads SBOM.

    Asserts:

    1. ``.github/workflows/sbom.yml`` is present at the repository root.
    2. The workflow's ``on:`` triggers include ``pull_request`` and a
       ``push`` configuration that targets the ``main`` branch (either
       no branch filter or an explicit ``branches: [main]`` list).
    3. At least one step across all jobs uses
       ``actions/upload-artifact@<ref>`` (any ref — SHA-pinning is
       validated by ``test_workflow_sha_pinning.py``).
    4. That upload-artifact step's ``with.path`` references the literal
       ``sbom.cdx.json`` filename so the SBOM is published as an
       artifact, not just generated.
    """
    assert SBOM_WORKFLOW_PATH.is_file(), (
        f"SBOM workflow must exist at {SBOM_WORKFLOW_PATH}. "
        "Create it via spec-110 Phase 2 T-2.7 — see plan-110.md for the "
        "CycloneDX generation + upload-artifact contract."
    )

    workflow = yaml.safe_load(SBOM_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict), (
        f"{SBOM_WORKFLOW_PATH} must parse as a YAML mapping at the top "
        f"level; got {type(workflow).__name__}."
    )

    # YAML parses the bare key ``on`` as the boolean ``True`` (PyYAML
    # YAML 1.1 behaviour). Quoted ``"on"`` parses as a string. Accept
    # both so the test does not depend on workflow-author quoting style.
    on_node = workflow.get("on")
    if on_node is None:
        on_node = workflow.get(True)
    triggers = _normalize_triggers(on_node)

    assert "pull_request" in triggers, (
        f"{SBOM_WORKFLOW_PATH.relative_to(REPO_ROOT)} must trigger on "
        f"``pull_request``. Found triggers: {sorted(triggers)}."
    )
    assert "push" in triggers, (
        f"{SBOM_WORKFLOW_PATH.relative_to(REPO_ROOT)} must trigger on "
        f"``push``. Found triggers: {sorted(triggers)}."
    )
    assert _push_targets_main(triggers["push"]), (
        f"{SBOM_WORKFLOW_PATH.relative_to(REPO_ROOT)} ``push`` trigger "
        f"must target the ``main`` branch (either no branch filter or "
        f"``branches: [main]``). Got: {triggers['push']!r}."
    )

    upload_steps: list[dict[str, Any]] = []
    for step in _iter_steps(workflow):
        uses = step.get("uses")
        if isinstance(uses, str) and uses.split("@", 1)[0] == UPLOAD_ARTIFACT_ACTION:
            upload_steps.append(step)

    assert upload_steps, (
        f"{SBOM_WORKFLOW_PATH.relative_to(REPO_ROOT)} must contain at "
        f"least one step that uses ``{UPLOAD_ARTIFACT_ACTION}@<ref>`` "
        "to publish the generated SBOM as a workflow artifact."
    )

    sbom_uploads = [
        step
        for step in upload_steps
        if isinstance(step.get("with"), dict)
        and _path_contains_sbom_filename(step["with"].get("path"))
    ]
    assert sbom_uploads, (
        f"{SBOM_WORKFLOW_PATH.relative_to(REPO_ROOT)} must include an "
        f"``{UPLOAD_ARTIFACT_ACTION}`` step whose ``with.path`` "
        f"references ``{SBOM_ARTIFACT_FILENAME}``. Found "
        f"{len(upload_steps)} upload-artifact step(s) but none uploaded "
        f"the SBOM file."
    )
