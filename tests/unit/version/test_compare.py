"""Canonical PEP 440 version comparison (spec-156 D-156-11)."""

from __future__ import annotations

import pytest

from ai_engineering.version.compare import is_newer


@pytest.mark.parametrize(
    ("latest", "current", "expected"),
    [
        ("0.9.0", "0.8.4", True),
        ("0.9.0rc1", "0.8.4", True),  # rc beats older final — old parser missed this
        ("0.9.0", "0.8.4.dev1", True),  # final beats dev — old parser missed this
        ("0.9.0", "0.9.0", False),  # equal is not newer
        ("0.8.4", "0.9.0", False),  # older is not newer
        ("0.9", "0.9.0", False),  # ragged arity, equal
        ("1.0.0+local", "1.0.0", True),  # PEP 440: a local version > its base
        ("1.0.0", "1.0.0+local", False),  # base is not newer than its local
        # The D-156-12 motivating case: a clean PyPI release vs an editable
        # dev+git-local install (the shape live __version__ produces on a
        # checkout) — the notice must fire for these installs.
        ("0.9.0", "0.8.4.dev3+g1a2b3c", True),  # newer release > older dev+local install
        ("0.8.4", "0.8.4.dev3+g1a2b3c", True),  # final > its own dev pre-release (local seg)
        ("0.8.4.dev3+gabc123", "0.8.4", False),  # dev pre-release is not newer than its final
        ("not-a-version", "0.9.0", False),  # invalid -> fail-open
        ("0.9.0", "garbage", False),  # invalid current -> fail-open
    ],
)
def test_is_newer(latest: str, current: str, expected: bool) -> None:
    assert is_newer(latest, current) is expected
