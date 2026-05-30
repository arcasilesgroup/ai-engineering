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
        ("1.0.0", "1.0.0+local", True),  # local segment is lower precedence
        ("not-a-version", "0.9.0", False),  # invalid -> fail-open
        ("0.9.0", "garbage", False),  # invalid current -> fail-open
    ],
)
def test_is_newer(latest: str, current: str, expected: bool) -> None:
    assert is_newer(latest, current) is expected
