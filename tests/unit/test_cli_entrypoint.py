"""Coverage for ai_engineering.cli module entrypoint."""

from __future__ import annotations

import runpy
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def test_cli_module_import_has_app() -> None:
    mod = runpy.run_module("ai_engineering.cli", run_name="ai_engineering.cli")
    assert "app" in mod


def test_cli_main_invokes_app() -> None:
    called = {"count": 0}

    def _fake_app() -> None:
        called["count"] += 1

    with patch("ai_engineering.cli_factory.create_app", return_value=_fake_app):
        runpy.run_module("ai_engineering.cli", run_name="__main__")
    assert called["count"] == 1
