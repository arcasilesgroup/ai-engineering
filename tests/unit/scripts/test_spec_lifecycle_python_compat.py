"""Python 3.9 import-compatibility guard for ``spec_lifecycle.py`` (D-135-13).

The script is invoked from hooks via ``#!/usr/bin/env python3``. On macOS that
shebang resolves to the system Python 3.9, even though the framework wheel
declares ``requires-python = ">=3.11"``. Importing the 3.11-only ``UTC``
symbol from ``datetime`` makes the script crash silently (fail-open per skill
contract), which leaves spec lifecycle sidecars unwritten during
``/ai-brainstorm`` and ``/ai-spec-draft`` bootstrap. See D-135-13.

This test parses the script as AST and forbids ``from datetime import UTC``,
so the regression is caught under any pytest interpreter — no need to install
Python 3.9 on contributor machines or CI runners.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / ".ai-engineering" / "scripts" / "spec_lifecycle.py"
)


@pytest.mark.unit
def test_script_does_not_import_utc_symbol_from_datetime() -> None:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "datetime":
            imported = {alias.name for alias in node.names}
            assert "UTC" not in imported, (
                "spec_lifecycle.py must not import `UTC` from `datetime` — "
                "it is Python 3.11+ only and the script runs under the host "
                "shebang (macOS system Python 3.9). Use `timezone.utc`. See "
                "D-135-13."
            )
