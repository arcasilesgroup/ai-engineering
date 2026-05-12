"""Hexagonal direction contract enforcement (spec-132 D-132-13).

This test invokes ``lint-imports`` against the
``[tool.importlinter]`` block in ``pyproject.toml`` and asserts that
every contract is KEPT. The contract pins the spec-132 D-132-13
direction rule: modules in the ``core`` layer (governance, state,
policy, validator, plus the relocated ``ai_engineering.core`` tree)
must not import modules in the ``adapters`` layer (cli_commands,
installer, vcs, ide, updater, issues).

Pragmatic scope note: D-132-13 strict prescribes physical mass
relocation of the flat ``src/ai_engineering/`` tree. Sub-005 ships
the DIRECTION enforcement using the existing flat tree as named-
layer membership lists. Physical relocation is deferred. The
contract carries a small ``ignore_imports`` baseline for the legacy
entanglements that the follow-up relocation spec will untangle.

Running ``lint-imports`` as a subprocess (vs importing the API)
keeps this test isolated from importlinter's CLI side-effects and
mirrors the CI invocation exactly.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_hexagonal_direction_contract_kept() -> None:
    """``lint-imports`` reports all contracts KEPT.

    Failure means a new import edge crosses the direction seam (core
    importing from adapters). The fix is one of:
      1. Refactor the import to flow the other direction (preferred).
      2. Move the importing module out of the ``core`` layer if it is
         genuinely an adapter.
      3. Land a decision row in ``state.db`` and add the edge to
         ``ignore_imports`` in ``pyproject.toml``.
    """
    lint_imports = shutil.which("lint-imports")
    if lint_imports is None:
        pytest.skip(
            "lint-imports binary not on PATH; install via "
            "``uv sync`` (import-linter is a dev dependency)."
        )
    result = subprocess.run(
        [lint_imports],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "import-linter reported a direction violation:\n"
        f"---stdout---\n{result.stdout}\n"
        f"---stderr---\n{result.stderr}\n"
        "Fix: refactor the import or, with an approved decision row, "
        "add the edge to ``ignore_imports`` in pyproject.toml."
    )
