"""spec-140 W2.T7 — composite actions (setup-env + run-gates) drift gate.

W2.T3 / W2.T4 extracted two composite actions under ``.github/actions/``:

* ``setup-env`` — checkout + setup-python + setup-uv + uv sync. Replaces the
  4-step pre-amble that lived in every CI job.
* ``run-gates`` — a single ``case`` dispatch for the lint / type-check /
  unit / integration gate commands.

The composites are byte-pinned via this drift gate so a future edit cannot
silently strip an input or break the schema without CI catching it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
ACTIONS_DIR = REPO_ROOT / ".github" / "actions"

SETUP_ENV_PATH = ACTIONS_DIR / "setup-env" / "action.yml"
RUN_GATES_PATH = ACTIONS_DIR / "run-gates" / "action.yml"


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
    ``uv-version`` pins the uv release; ``fetch-depth`` switches between
    shallow and full clone; ``sync`` lets callers skip the default
    ``uv sync --dev`` step for build-from-wheel flows.
    """
    inputs = setup_env.get("inputs") or {}
    required_inputs = {"python-version", "uv-version", "fetch-depth", "sync"}
    missing = required_inputs - set(inputs)
    assert not missing, f"setup-env missing inputs: {sorted(missing)}"
    # `python-version` defaults to 3.12 — the PR-blocking version (D-140-03).
    assert str(inputs["python-version"].get("default")) == "3.12", (
        f"setup-env python-version default must be 3.12; "
        f"got {inputs['python-version'].get('default')!r}"
    )


def test_setup_env_steps_cover_checkout_python_uv_and_sync(setup_env: dict) -> None:
    """Composite must wire checkout + setup-python + setup-uv + uv sync."""
    steps = (setup_env.get("runs") or {}).get("steps") or []
    uses_strings = " ".join(step.get("uses", "") for step in steps if "uses" in step)
    run_strings = " ".join(step.get("run", "") for step in steps if "run" in step)

    assert "actions/checkout" in uses_strings, "setup-env must call actions/checkout"
    assert "actions/setup-python" in uses_strings, "setup-env must call actions/setup-python"
    assert "astral-sh/setup-uv" in uses_strings, "setup-env must call astral-sh/setup-uv"
    assert "uv sync" in run_strings, "setup-env must run `uv sync` by default"


# ---------------------------------------------------------------------------
# run-gates (W2.T4)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def run_gates() -> dict:
    return _load(RUN_GATES_PATH)


def test_run_gates_action_file_exists() -> None:
    """W2.T4 lands the composite at the canonical path."""
    assert RUN_GATES_PATH.exists(), f"expected composite at {RUN_GATES_PATH}"


def test_run_gates_is_a_composite_action(run_gates: dict) -> None:
    """``runs.using: composite``."""
    assert run_gates.get("name"), "run-gates action.yml must declare a name"
    runs = run_gates.get("runs") or {}
    assert runs.get("using") == "composite", (
        f"run-gates must be a composite action; got runs.using={runs.get('using')!r}"
    )


def test_run_gates_accepts_gate_input(run_gates: dict) -> None:
    """`gate` is the sole required input."""
    inputs = run_gates.get("inputs") or {}
    assert "gate" in inputs, f"run-gates must declare a `gate` input; got {list(inputs)}"
    assert inputs["gate"].get("required") is True, "`gate` input must be required"


def test_run_gates_dispatches_all_four_gates(run_gates: dict) -> None:
    """The composite MUST handle every gate value the callers can pass."""
    steps = (run_gates.get("runs") or {}).get("steps") or []
    run_block = " ".join(step.get("run", "") for step in steps if "run" in step)
    for gate in ("lint", "type-check", "unit", "integration"):
        assert f"{gate})" in run_block, (
            f"run-gates is missing a case arm for `{gate}`. Run block:\n{run_block}"
        )
