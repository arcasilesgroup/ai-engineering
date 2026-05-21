"""Tests for ``ai_engineering.config.loader`` fail-loud behavior (spec-147 G1).

The manifest loader previously swallowed ``(OSError, yaml.YAMLError)`` and
returned an all-defaults ``ManifestConfig`` — a corrupt manifest was
indistinguishable from a missing one. spec-147 G1 T-1.9/1.10 splits the two:

* ``FileNotFoundError`` (manifest absent) STILL returns defaults — a fresh
  consumer project without a manifest is a legitimate state.
* A parse error (corrupt YAML on an EXISTING file) fails loud with a named
  error that points at the offending path — silent default-substitution can
  no longer mask a broken config.

The named error subclasses ``ValueError`` so callers that already wrap the
load in ``except (OSError, ValueError)`` keep their opt-in fail-open posture
(e.g. ``policy.gates._get_active_stacks``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.config.loader import (
    InvalidManifestError,
    load_manifest_config,
)
from ai_engineering.config.manifest import ManifestConfig


def _manifest_path(root: Path) -> Path:
    path = root / ".ai-engineering" / "manifest.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_absent_manifest_returns_defaults(tmp_path: Path) -> None:
    """The contrast case: a genuinely-missing manifest still returns defaults."""
    config = load_manifest_config(tmp_path)
    assert isinstance(config, ManifestConfig)


def test_corrupt_manifest_raises_named_error(tmp_path: Path) -> None:
    """A corrupt-YAML manifest must fail loud with a named, path-bearing error."""
    path = _manifest_path(tmp_path)
    # Unbalanced flow-sequence bracket -> yaml.YAMLError on safe_load.
    path.write_text("providers:\n  stacks: [python, dotnet\n", encoding="utf-8")

    with pytest.raises(InvalidManifestError) as exc_info:
        load_manifest_config(tmp_path)

    # The message names the offending path so the operator can find it.
    assert "manifest.yml" in str(exc_info.value)


def test_invalid_manifest_error_is_value_error(tmp_path: Path) -> None:
    """The named error subclasses ValueError so existing ``except ValueError``
    fail-open callers keep working unchanged."""
    path = _manifest_path(tmp_path)
    path.write_text(": not valid [[[", encoding="utf-8")

    with pytest.raises(ValueError):
        load_manifest_config(tmp_path)


def test_empty_manifest_returns_defaults(tmp_path: Path) -> None:
    """An empty (but present) manifest is a valid, default-everything state —
    distinct from a corrupt one."""
    path = _manifest_path(tmp_path)
    path.write_text("", encoding="utf-8")

    config = load_manifest_config(tmp_path)
    assert isinstance(config, ManifestConfig)
