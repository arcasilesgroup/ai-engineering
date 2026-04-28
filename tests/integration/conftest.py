"""Integration test conftest -- shared fixtures.

The ``hermetic_install_env`` fixture below is a NAMED (non-autouse)
helper that integration tests can opt into via:

    pytestmark = pytest.mark.usefixtures("hermetic_install_env")

It engages the spec-101 synthetic-OK simulate hooks so the install
pipeline short-circuits the network-bound install mechanism. Tests that
patch ``TOOL_REGISTRY`` directly (e.g. ``test_install_idempotence.py``)
must NOT use this fixture -- their mocks expect ``mechanism.install()``
to be invoked, which the synthetic-OK hook bypasses.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def hermetic_install_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the install pipeline into the synthetic-success path.

    Sets the spec-101 simulate hooks so the
    ``AIENG_TEST_SIMULATE_INSTALL_OK="*"`` wildcard short-circuits each
    required tool to a synthetic ``InstallResult(failed=False)``. The
    framework still exercises every code path UP TO the mechanism
    boundary -- only the network call is replaced.

    ``AIENG_DEV_BUILD=1`` is set defensively so the synthetic-OK hook
    fires regardless of whether the test runner picks up the editable
    install (``uv sync --dev``) or a wheel install. The Wave 27
    production-refusal logic is preserved -- this only opts-in tests
    that explicitly want the synthetic path.
    """
    monkeypatch.setenv("AIENG_TEST", "1")
    monkeypatch.setenv("AIENG_TEST_SIMULATE_INSTALL_OK", "*")
    monkeypatch.setenv("AIENG_DEV_BUILD", "1")
