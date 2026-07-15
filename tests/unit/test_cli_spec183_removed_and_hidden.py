"""spec-183 D-183-02 / D-183-03: removed-command tombstones + hidden release.

- ``spec activate``, ``maintenance branch-cleanup``, ``maintenance spec-reset``
  are removed: each prints ``removed; use '<new>'`` and exits 2.
- ``release`` is hidden from the help tree and the JSON command list but stays
  fully invocable (``hidden`` != disabled).
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

runner = CliRunner()


@pytest.mark.parametrize(
    ("argv", "replacement"),
    [
        (["spec", "activate"], "spec start"),
        (["maintenance", "branch-cleanup"], "cleanup branches"),
        (["maintenance", "spec-reset"], "cleanup specs"),
    ],
)
def test_removed_command_tombstone(argv: list[str], replacement: str) -> None:
    result = runner.invoke(create_app(), argv)
    assert result.exit_code == 2
    assert f"removed; use '{replacement}'" in result.output


@pytest.mark.parametrize(
    ("argv", "replacement"),
    [
        (["maintenance", "spec-reset", "--dry-run"], "cleanup specs"),
        (["maintenance", "branch-cleanup", "--dry-run", "--force"], "cleanup branches"),
        (["spec", "activate", "some/path"], "spec start"),
    ],
)
def test_removed_command_tombstone_swallows_old_flags(argv: list[str], replacement: str) -> None:
    # A verbatim migration invocation (old flags included) must still hit the
    # removal message, not a "No such option" usage error.
    result = runner.invoke(create_app(), argv)
    assert result.exit_code == 2
    assert f"removed; use '{replacement}'" in result.output


def test_release_absent_from_json_command_list() -> None:
    result = runner.invoke(create_app(), ["--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    commands = payload["result"]["commands"]
    assert "release" not in commands


def test_release_still_invocable() -> None:
    # hidden != disabled: `ai-eng release --help` must still resolve.
    result = runner.invoke(create_app(), ["release", "--help"])
    assert result.exit_code == 0
