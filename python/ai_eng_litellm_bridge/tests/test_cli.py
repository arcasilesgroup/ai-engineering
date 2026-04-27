"""CLI argparse + dispatch tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from ai_eng_litellm_bridge.cli import _build_parser, main


class TestParser:
    def test_serve_default_port(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["serve"])
        assert args.command == "serve"
        assert args.port == 4848
        assert args.host == "127.0.0.1"
        assert args.routing_config is None

    def test_serve_port_override(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["serve", "--port", "9999"])
        assert args.port == 9999

    def test_serve_routing_config_override(self, tmp_path: Any) -> None:
        # Use the pytest-managed temp dir to avoid S108 false positives on /tmp paths.
        cfg = str(tmp_path / "routes.toml")
        parser = _build_parser()
        args = parser.parse_args(["serve", "--routing-config", cfg])
        assert args.routing_config == cfg

    def test_no_subcommand_errors(self) -> None:
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])


class TestMain:
    def test_dispatches_to_serve(self, tmp_path: Any) -> None:
        captured: dict[str, Any] = {}

        def _fake_serve(**kwargs: Any) -> None:
            captured.update(kwargs)

        cfg = str(tmp_path / "r.toml")
        with patch("ai_eng_litellm_bridge.cli.serve", _fake_serve):
            rc = main(["serve", "--port", "5555", "--routing-config", cfg])
        assert rc == 0
        assert captured == {
            "port": 5555,
            "host": "127.0.0.1",
            "routing_config_path": cfg,
        }
