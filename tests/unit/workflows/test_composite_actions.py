"""spec-140 W2.T7 — composite-action (setup-env) drift gate.

W2.T3 extracted the ``setup-env`` composite under ``.github/actions/``:

* ``setup-env`` — setup-python + setup-uv + uv sync. Replaces the
  pre-amble that lived in every CI job (callers do their own checkout).

The composite is byte-pinned via this drift gate so a future edit cannot
silently strip an input or break the schema without CI catching it.

spec-152 W2.T13 hard-deleted the ``run-gates`` composite (zero ``uses:``
references; the gate commands are invoked inline in ``ci-check.yml``).
Its drift tests were removed in the same change so the deletion fails
loud rather than leaving an orphaned fixture asserting a vanished file.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
ACTIONS_DIR = REPO_ROOT / ".github" / "actions"

SETUP_ENV_PATH = ACTIONS_DIR / "setup-env" / "action.yml"


def _load(path: Path) -> dict:
    assert path.exists(), f"missing composite action: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# setup-env (W2.T3)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def setup_env() -> dict:
    return _load(SETUP_ENV_PATH)


def test_setup_env_action_file_exists() -> None:
    """W2.T3 lands the composite at the canonical path."""
    assert SETUP_ENV_PATH.exists(), f"expected composite at {SETUP_ENV_PATH}"


def test_setup_env_is_a_composite_action(setup_env: dict) -> None:
    """``runs.using: composite`` is the contract for a reusable action."""
    assert setup_env.get("name"), "setup-env action.yml must declare a name"
    runs = setup_env.get("runs") or {}
    assert runs.get("using") == "composite", (
        f"setup-env must be a composite action; got runs.using={runs.get('using')!r}"
    )


def test_setup_env_inputs_match_contract(setup_env: dict) -> None:
    """Inputs MUST cover the parameters every caller relies on.

    ``python-version`` (default 3.12) is consumed by the matrix jobs;
    ``uv-version`` pins the uv release; ``sync`` lets callers skip the
    default ``uv sync --dev`` step for build-from-wheel flows. Per the
    fix landed after the first CI green attempt, ``fetch-depth`` is no
    longer accepted — callers do their own ``actions/checkout`` before
    invoking this composite so the action.yml file is resolvable on the
    runner (chicken-and-egg: a local composite cannot perform its own
    checkout because the action file itself must already be on disk).
    """
    inputs = setup_env.get("inputs") or {}
    required_inputs = {"python-version", "uv-version", "sync"}
    missing = required_inputs - set(inputs)
    assert not missing, f"setup-env missing inputs: {sorted(missing)}"
    # `python-version` defaults to 3.12 — the PR-blocking version (D-140-03).
    assert str(inputs["python-version"].get("default")) == "3.12", (
        f"setup-env python-version default must be 3.12; "
        f"got {inputs['python-version'].get('default')!r}"
    )
    # Composite must NOT advertise fetch-depth: callers own checkout.
    assert "fetch-depth" not in inputs, (
        "setup-env must NOT accept fetch-depth — callers do their own checkout "
        "before invoking this composite. See action.yml IMPORTANT note."
    )


def test_setup_env_steps_cover_python_uv_and_sync(setup_env: dict) -> None:
    """Composite must wire setup-python + setup-uv + uv sync.

    ``actions/checkout`` is intentionally NOT in the composite — callers
    own it (see ``test_setup_env_inputs_match_contract`` for the why).
    """
    steps = (setup_env.get("runs") or {}).get("steps") or []
    uses_strings = " ".join(step.get("uses", "") for step in steps if "uses" in step)
    run_strings = " ".join(step.get("run", "") for step in steps if "run" in step)

    assert "actions/setup-python" in uses_strings, "setup-env must call actions/setup-python"
    assert "astral-sh/setup-uv" in uses_strings, "setup-env must call astral-sh/setup-uv"
    assert "uv sync" in run_strings, "setup-env must run `uv sync` by default"
    # Negative assertion: caller-owned checkout must not be in the composite.
    assert "actions/checkout" not in uses_strings, (
        "setup-env must NOT include actions/checkout — callers must checkout first"
    )
