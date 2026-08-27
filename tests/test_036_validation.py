"""Validation freshness, spec 036 / B-036-3.

The adoption record's validation table must not rot: every row's module keeps existing
with its contract symbol, and, where the row names a provenance marker, the module's
docstring carries it. A future refactor that deletes or splits one of the validated
modules fails this check with the reason to update the record first (specs 013-034 are
normative; nothing in spec 036 rewrites them, it only asserts them).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# (module, contract symbol, provenance marker or None). The marker is asserted only where
# the module's own docstring carries it — evidence.py, contract.py and capability.py name
# no spec in their first lines, so their rows assert module + symbol.
ROWS = [
    ("evidence", "verify", None),
    ("verify_cold", "Verdict", "spec 030"),
    ("contract", "audit_one", None),
    ("contract", "_anti_rationalization_problems", None),
    ("cost", "calibrate", "spec 029"),
    ("capability", "preflight", None),
    ("trim", "trim_output", "spec 033"),
    ("decision_fw", "named", "spec 034"),
]


def _docstring_head(module) -> str:
    return " ".join((module.__doc__ or "").splitlines()[:2])


def test_every_validated_module_keeps_its_contract():
    for name, symbol, marker in ROWS:
        module = importlib.import_module(f"ai_engineering.{name}")
        assert hasattr(module, symbol), (
            f"{name} lost its contract symbol {symbol}; update specs/036 ... before deleting it"
        )
        if marker is not None:
            assert marker in _docstring_head(module), (
                f"{name} no longer carries {marker} in its docstring"
            )
