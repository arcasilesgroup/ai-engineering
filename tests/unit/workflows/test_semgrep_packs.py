"""spec-141 M2.T5 — Semgrep pack coverage drift gate.

The CI semgrep step is the only invocation that fans out across the
community packs (in-tree rules cover the project-specific risks; the
packs cover OWASP / language-idiom hardening). If a future edit
silently drops a `--config p/<name>` flag or unpins the CLI version,
the deterministic anchor that makes the scan reproducible disappears
and the coverage matrix shrinks without anyone noticing.

This test parses `.github/workflows/ci-check.yml` and asserts the four
community pack flags + the pinned `semgrep==<version>` install line are
all present in the security job. Failing the test = the spec-141 M2
guarantee has been silently undone.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci-check.yml"

# Four Python-relevant community packs (D-141-02). Order matters for the
# runtime invocation but the drift gate only checks set-membership so
# reordering the `--config` flags inside the workflow stays compatible
# with this test.
REQUIRED_PACKS: frozenset[str] = frozenset(
    {
        "p/python",
        "p/owasp-top-ten",
        "p/security-audit",
        "p/bash",
    }
)


@pytest.fixture(scope="module")
def workflow() -> dict:
    """Parse `ci-check.yml` once per test module."""
    assert WORKFLOW_PATH.exists(), f"missing workflow: {WORKFLOW_PATH}"
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _security_steps(workflow: dict) -> list[dict]:
    """Return the ordered step list for the `security` job."""
    jobs = workflow.get("jobs", {})
    security = jobs.get("security")
    assert security is not None, (
        f"spec-141 M2 expects a `security` job in ci-check.yml; got jobs: {sorted(jobs)}"
    )
    steps = security.get("steps", [])
    assert steps, "security job has no steps"
    return steps


def _step_by_name(steps: list[dict], name: str) -> dict:
    """Find the first step whose `name` matches; fail loud if absent."""
    for step in steps:
        if step.get("name") == name:
            return step
    available = [s.get("name") for s in steps]
    raise AssertionError(f"no step named {name!r} in security job; available: {available}")


def test_semgrep_step_contains_all_four_community_packs(workflow: dict) -> None:
    """spec-141 M2.T1 — every required pack appears as a `--config p/<name>` flag.

    As of 2026-05 the semgrep.dev registry returns HTTP 403 for
    unauthenticated requests, so the community-pack invocation runs as a
    separate `continue-on-error` step (`semgrep (community packs —
    advisory)`) while the in-tree rules stay in the authoritative gate
    step (`semgrep (in-tree rules — must pass)`). This test asserts the
    advisory step still names all four packs so the coverage matrix is
    not silently dropped when SEMGREP_APP_TOKEN gets provisioned later.
    """
    steps = _security_steps(workflow)
    pack_step = _step_by_name(steps, "semgrep (community packs — advisory)")
    run_block = pack_step.get("run", "")
    assert run_block, "community-pack step has empty `run:` block"

    missing: list[str] = []
    for pack in sorted(REQUIRED_PACKS):
        flag = f"--config {pack}"
        if flag not in run_block:
            missing.append(flag)
    assert not missing, (
        f"spec-141 M2 drift: community-pack step missing required `--config` flag(s): "
        f"{missing}. Run block:\n{run_block}"
    )


def test_semgrep_step_keeps_in_tree_config(workflow: dict) -> None:
    """The in-tree `.semgrep.yml` config MUST stay in the authoritative gate.

    Removing it would silently drop the project-specific rules
    (aieng.injection.*, aieng.deserialize.*, …) from the CI surface.
    The in-tree step runs WITHOUT `continue-on-error` so any finding
    fails the build loudly.
    """
    steps = _security_steps(workflow)
    intree_step = _step_by_name(steps, "semgrep (in-tree rules — must pass)")
    run_block = intree_step.get("run", "")
    assert "--config .semgrep.yml" in run_block, (
        "spec-141 M2: in-tree semgrep step must keep `--config .semgrep.yml`. "
        f"Run block:\n{run_block}"
    )
    assert "--error" in run_block, (
        "spec-141 M2: in-tree semgrep step must keep `--error` so findings fail the build."
    )
    # The in-tree step is the authoritative gate — must NOT continue-on-error.
    assert not intree_step.get("continue-on-error", False), (
        "spec-141 M2: in-tree semgrep step must be authoritative (no continue-on-error)."
    )


def test_semgrep_install_step_pins_cli_version(workflow: dict) -> None:
    """spec-141 M2.T2 — `pip install semgrep==<version>` pin is present.

    Pinning the CLI is the only documented way to fix the scan surface
    (pack aliases roll forward from HEAD). The drift gate asserts the
    pin syntax exists; bumping the version is the quarterly procedure
    documented at `.ai-engineering/reference/semgrep-update-model.md`.
    """
    install_step = _step_by_name(_security_steps(workflow), "Install semgrep")
    run_block = install_step.get("run", "")
    assert run_block, "Install semgrep step has empty `run:` block"

    pin_re = re.compile(r"semgrep==\d+\.\d+(?:\.\d+)?")
    match = pin_re.search(run_block)
    assert match is not None, (
        "spec-141 M2.T2: `Install semgrep` step must pin the CLI version via "
        f"`semgrep==<version>`. Got: {run_block!r}"
    )
