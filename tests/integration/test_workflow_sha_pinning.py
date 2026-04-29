"""RED-phase test for spec-110 Phase 2 — workflow SHA-pinning.

Spec acceptance criterion (governance v3 harvest, Phase 2):
    Every ``uses:`` reference inside ``.github/workflows/*.yml`` must
    pin to a 40-character commit SHA (``^[a-f0-9]{40}$``) so untrusted
    upstream maintainers cannot retroactively retag a release. Mutable
    refs (``v4``, ``main``, ``latest``) are forbidden.

Self-references that target this organization (``arcasilesgroup/<repo>``)
are exempted because their tags are governed by the same trust boundary
that owns the workflows; pinning a self-reference would defeat the
purpose of versioned reusable workflows.

Status: RED. Initial audit during ``/ai-brainstorm`` flagged at least
``SonarSource/sonarqube-scan-action@v7.0.0`` (``ci-check.yml``) and
``actions/cache@v4`` (multiple jobs in ``ci-check.yml`` and
``ci-build.yml``) as mutable. T-2.3 replaces them with SHA pins. This
test deliberately fails now to drive the GREEN phase.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# Repo root: tests/integration/<this file> → up 3 levels.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

# 40-character lowercase hex SHA — git's full commit hash.
SHA_RE = re.compile(r"^[a-f0-9]{40}$")

# Self-reference exemption per plan-110 D-110-05 implication. References to
# repositories owned by ``arcasilesgroup`` are governed by the same trust
# boundary as the workflows themselves and may use mutable tags.
SELF_REFERENCE_OWNER = "arcasilesgroup"


def _iter_uses(node: Any) -> list[str]:
    """Recursively collect every ``uses:`` value from a parsed workflow tree.

    GitHub Actions allows ``uses:`` keys to appear at the step level
    (``jobs.<id>.steps[].uses``) and at the job level (reusable workflow
    callers: ``jobs.<id>.uses``). The walker handles both shapes plus any
    future nesting by recursing into every dict/list it encounters.
    """
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "uses" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_iter_uses(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_iter_uses(item))
    return found


def _extract_ref(uses: str) -> str:
    """Return the ref portion (after the last ``@``) of a ``uses:`` value.

    ``uses:`` syntax is ``<owner>/<repo>[/<path>]@<ref>``. ``rsplit`` on
    the last ``@`` is robust to subpath separators and to docker-image
    references that may contain ``@sha256:`` (which would also be a
    pinned form, but is not used in this repo).
    """
    return uses.rsplit("@", 1)[-1] if "@" in uses else ""


def _extract_owner(uses: str) -> str:
    """Return the owner portion of a ``uses:`` value (text before first ``/``).

    ``uses: actions/checkout@<sha>`` → ``actions``.
    ``uses: arcasilesgroup/reusable/.github/workflows/foo.yml@main`` → ``arcasilesgroup``.
    Falls back to the empty string if the value does not contain a slash
    (e.g. a docker-image-only reference) so the caller treats it as
    non-self-reference and falls through to the SHA check.
    """
    target = uses.split("@", 1)[0]
    return target.split("/", 1)[0] if "/" in target else ""


def test_all_actions_pinned_to_sha() -> None:
    """Every ``uses:`` reference in ``.github/workflows/*.yml`` is SHA-pinned.

    Asserts that for each ``uses:`` value found by walking each workflow's
    parsed YAML tree:

    1. The reference splits on ``@`` and the suffix is a 40-char lowercase
       hex SHA matching ``^[a-f0-9]{40}$``.

    Self-references whose owner is ``arcasilesgroup`` are exempt — they
    are governed by the same trust boundary and may use mutable tags.

    The test reports ALL violations (not just the first) so a single
    failing run surfaces the full remediation work for T-2.3.
    """
    assert WORKFLOWS_DIR.is_dir(), (
        f"Expected workflows directory at {WORKFLOWS_DIR}; cannot "
        "validate SHA pinning without workflow files."
    )

    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml"))
    assert workflow_files, (
        f"No ``.yml`` files found under {WORKFLOWS_DIR}; spec-110 Phase 2 "
        "requires at least one workflow to validate."
    )

    violations: list[str] = []
    for workflow_path in workflow_files:
        parsed = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        for uses in _iter_uses(parsed):
            owner = _extract_owner(uses)
            if owner == SELF_REFERENCE_OWNER:
                continue
            ref = _extract_ref(uses)
            if not SHA_RE.match(ref):
                violations.append(
                    f"{workflow_path.relative_to(REPO_ROOT)}: '{uses}' — "
                    f"ref '{ref}' is not a 40-char SHA"
                )

    assert not violations, (
        "All third-party ``uses:`` references in .github/workflows/*.yml must "
        "pin to a 40-character commit SHA. Found "
        f"{len(violations)} violation(s):\n  - " + "\n  - ".join(violations)
    )
