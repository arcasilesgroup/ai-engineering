"""Unit tests for ``ai_engineering.policy.gate_cache`` cache key derivation.

RED phase for spec-104 T-0.5 (D-104-09 cache key inputs definition).

Target functions/constants (do not exist yet — created in T-0.6):
    - ``_compute_cache_key(check_name, args, staged_blob_shas, tool_version,
      config_file_hashes) -> str``
        Returns sha256 hex digest truncated to the first 32 chars.
    - ``_CONFIG_FILE_WHITELIST: dict[str, list[str]]`` — per-check allowed
      config files (relative paths only).

Each test currently fails with ``ImportError`` because the module is not
implemented. T-0.6 GREEN phase will implement both pieces and these tests
become the contract for D-104-09.

TDD CONSTRAINT: this file is IMMUTABLE after T-0.5 lands.
"""

from __future__ import annotations

import re
from typing import Any


def _make_inputs(**overrides: Any) -> dict[str, Any]:
    """Return canonical kwargs for ``_compute_cache_key``.

    Tests override individual fields to assert sensitivity / insensitivity
    properties without re-specifying the full payload each time.
    """

    base: dict[str, Any] = {
        "check_name": "ruff-check",
        "args": ["check", "src/"],
        "staged_blob_shas": [
            "0123456789abcdef0123456789abcdef01234567",
            "fedcba9876543210fedcba9876543210fedcba98",
        ],
        "tool_version": "0.6.4",
        "config_file_hashes": {
            "pyproject.toml": "a" * 64,
            ".ruff.toml": "b" * 64,
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_compute_cache_key_deterministic() -> None:
    """Same inputs across repeated calls produce the same key."""
    # Arrange
    from ai_engineering.policy.gate_cache import _compute_cache_key

    inputs = _make_inputs()

    # Act
    key_a = _compute_cache_key(**inputs)
    key_b = _compute_cache_key(**inputs)
    key_c = _compute_cache_key(**inputs)

    # Assert
    assert key_a == key_b == key_c


def test_compute_cache_key_input_order_irrelevant() -> None:
    """Reordering ``args``, ``staged_blob_shas``, or ``config_file_hashes``
    does not change the resulting key (sorted internally per D-104-09)."""
    # Arrange
    from ai_engineering.policy.gate_cache import _compute_cache_key

    args_forward = ["alpha", "beta"]
    args_reverse = ["beta", "alpha"]

    shas_forward = ["aaaa1111", "bbbb2222", "cccc3333"]
    shas_shuffled = ["cccc3333", "aaaa1111", "bbbb2222"]

    cfg_order_one = {"pyproject.toml": "x" * 64, ".ruff.toml": "y" * 64}
    cfg_order_two = {".ruff.toml": "y" * 64, "pyproject.toml": "x" * 64}

    inputs_forward = _make_inputs(
        args=args_forward,
        staged_blob_shas=shas_forward,
        config_file_hashes=cfg_order_one,
    )
    inputs_reordered = _make_inputs(
        args=args_reverse,
        staged_blob_shas=shas_shuffled,
        config_file_hashes=cfg_order_two,
    )

    # Act
    key_forward = _compute_cache_key(**inputs_forward)
    key_reordered = _compute_cache_key(**inputs_reordered)

    # Assert
    assert key_forward == key_reordered


def test_compute_cache_key_different_tool_version_yields_different_key() -> None:
    """Bumping ``tool_version`` invalidates the cache key naturally."""
    # Arrange
    from ai_engineering.policy.gate_cache import _compute_cache_key

    inputs_old = _make_inputs(tool_version="0.6.4")
    inputs_new = _make_inputs(tool_version="0.6.5")

    # Act
    key_old = _compute_cache_key(**inputs_old)
    key_new = _compute_cache_key(**inputs_new)

    # Assert
    assert key_old != key_new


def test_compute_cache_key_different_staged_blobs_yields_different_key() -> None:
    """Different staged content (different blob shas) → different key."""
    # Arrange
    from ai_engineering.policy.gate_cache import _compute_cache_key

    inputs_a = _make_inputs(
        staged_blob_shas=["1111111111111111111111111111111111111111"],
    )
    inputs_b = _make_inputs(
        staged_blob_shas=["2222222222222222222222222222222222222222"],
    )

    # Act
    key_a = _compute_cache_key(**inputs_a)
    key_b = _compute_cache_key(**inputs_b)

    # Assert
    assert key_a != key_b


def test_compute_cache_key_returns_32_char_hex() -> None:
    """Output is exactly 32 lowercase hex chars (sha256 truncated)."""
    # Arrange
    from ai_engineering.policy.gate_cache import _compute_cache_key

    hex_pattern = re.compile(r"^[0-9a-f]{32}$")
    inputs = _make_inputs()

    # Act
    key = _compute_cache_key(**inputs)

    # Assert
    assert isinstance(key, str)
    assert len(key) == 32
    assert hex_pattern.match(key) is not None, f"Key {key!r} is not 32-char lowercase hex"


def test_compute_cache_key_different_check_name_yields_different_key() -> None:
    """``check_name`` participates in the hash — different check, different key."""
    # Arrange
    from ai_engineering.policy.gate_cache import _compute_cache_key

    inputs_format = _make_inputs(check_name="ruff-format")
    inputs_check = _make_inputs(check_name="ruff-check")

    # Act
    key_format = _compute_cache_key(**inputs_format)
    key_check = _compute_cache_key(**inputs_check)

    # Assert
    assert key_format != key_check


def test_config_file_whitelist_covers_all_8_checks() -> None:
    """``_CONFIG_FILE_WHITELIST`` keys match the 8 checks defined in D-104-09."""
    # Arrange
    from ai_engineering.policy.gate_cache import _CONFIG_FILE_WHITELIST

    expected_checks = {
        "ruff-format",
        "ruff-check",
        "gitleaks",
        "ty",
        "pytest-smoke",
        "validate",
        "spec-verify",
        "docs-gate",
    }

    # Act
    actual_checks = set(_CONFIG_FILE_WHITELIST.keys())

    # Assert
    assert actual_checks == expected_checks, (
        f"Whitelist drift. Missing: {expected_checks - actual_checks}. "
        f"Unexpected: {actual_checks - expected_checks}."
    )


def test_config_file_whitelist_paths_relative_not_absolute() -> None:
    """All whitelisted config paths are relative (cross-platform)."""
    # Arrange
    from ai_engineering.policy.gate_cache import _CONFIG_FILE_WHITELIST

    # Drive-letter prefix (Windows) e.g. "C:\\path".
    windows_drive_pattern = re.compile(r"^[A-Za-z]:[\\/]")

    # Act / Assert
    for check_name, paths in _CONFIG_FILE_WHITELIST.items():
        assert isinstance(paths, list), (
            f"{check_name!r} value is not a list: {type(paths).__name__}"
        )
        for path in paths:
            assert isinstance(path, str), f"{check_name!r} contains non-str entry: {path!r}"
            assert not path.startswith("/"), f"{check_name!r} has absolute POSIX path: {path!r}"
            assert windows_drive_pattern.match(path) is None, (
                f"{check_name!r} has Windows drive-letter path: {path!r}"
            )
            assert not path.startswith("\\"), (
                f"{check_name!r} has UNC-style absolute path: {path!r}"
            )


def test_compute_cache_key_args_normalized() -> None:
    """``args`` content is whitespace-sensitive and cardinality-sensitive.

    Per D-104-09, args are sorted internally (covered by
    ``test_compute_cache_key_input_order_irrelevant``). This test asserts
    the complementary properties:

    * Different cardinality → different key.
    * Whitespace inside a token is preserved in the hash (no stripping).
    * Same multiset in different order → same key (sort invariant).
    """
    # Arrange
    from ai_engineering.policy.gate_cache import _compute_cache_key

    inputs_two_ordered = _make_inputs(args=["check", "."])
    inputs_one = _make_inputs(args=["check"])
    inputs_two_reversed = _make_inputs(args=[".", "check"])
    inputs_whitespace = _make_inputs(args=["check ", "."])  # trailing space

    # Act
    key_two_ordered = _compute_cache_key(**inputs_two_ordered)
    key_one = _compute_cache_key(**inputs_one)
    key_two_reversed = _compute_cache_key(**inputs_two_reversed)
    key_whitespace = _compute_cache_key(**inputs_whitespace)

    # Assert — cardinality matters
    assert key_two_ordered != key_one, "args=['check','.'] must differ from args=['check']"
    # Assert — sort invariant holds for same multiset
    assert key_two_ordered == key_two_reversed, (
        "args=['check','.'] and ['.','check'] must hash to the same key"
    )
    # Assert — whitespace inside a token is preserved
    assert key_two_ordered != key_whitespace, (
        "Trailing whitespace in an arg token must change the key"
    )


def test_compute_cache_key_no_state_leakage() -> None:
    """Calling with identical inputs across simulated isolated invocations
    yields the same key — the function holds no implicit state.

    We simulate two "separate processes" by mutating module-level globals
    that a poorly-implemented function might leak through (random seed,
    environment variable, time). Since ``_compute_cache_key`` is a pure
    sha256 over its declared inputs, none of these mutations may change
    the output.
    """
    # Arrange
    import os
    import random

    from ai_engineering.policy.gate_cache import _compute_cache_key

    inputs = _make_inputs()

    # Process-A simulation: stable seed, baseline env.
    random.seed(0)
    prior_env = os.environ.get("AIENG_CACHE_DEBUG")
    if "AIENG_CACHE_DEBUG" in os.environ:
        del os.environ["AIENG_CACHE_DEBUG"]
    try:
        key_process_a = _compute_cache_key(**inputs)
    finally:
        if prior_env is not None:
            os.environ["AIENG_CACHE_DEBUG"] = prior_env

    # Process-B simulation: different seed, env var set.
    random.seed(424242)
    os.environ["AIENG_CACHE_DEBUG"] = "1"
    try:
        key_process_b = _compute_cache_key(**inputs)
    finally:
        if prior_env is None:
            os.environ.pop("AIENG_CACHE_DEBUG", None)
        else:
            os.environ["AIENG_CACHE_DEBUG"] = prior_env

    # Assert
    assert key_process_a == key_process_b, (
        "Cache key must be a pure function of declared inputs; "
        "no leakage from random state or env vars."
    )
