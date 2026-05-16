"""RED-phase tests for ``skill_scripts_lib.manifest_reader`` (spec-129 T-1).

Contract under test (T-2 will implement):

* ``resolve_stack(manifest_path: Path) -> str`` -- returns the configured
  stack string. Schema: reads ``providers.stacks[0]`` from
  ``.ai-engineering/manifest.yml`` (single-stack projects today; the
  resolver picks the first declared stack as the project's primary).
* ``read_work_items(manifest_path: Path) -> dict`` -- returns the
  ``work_items`` block verbatim as a Python dict.
* ``MissingManifestError`` -- raised when the path does not exist.
* ``InvalidManifestError`` -- raised when the YAML is malformed.

Perf floor: 100 sequential ``resolve_stack`` calls complete in < 5 s
wall-clock (proxy for the spec's ≤50 ms p95 per call).

These tests intentionally fail with ``ModuleNotFoundError`` until T-2
lands ``.ai-engineering/scripts/skills/_lib/manifest_reader.py`` and
exposes it on ``sys.path`` as ``skill_scripts_lib``.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

# RED-phase: this import MUST fail until T-2 lands. The failure is the
# signal that the GREEN phase still has work to do.
from skill_scripts_lib.manifest_reader import (
    InvalidManifestError,
    MissingManifestError,
    read_work_items,
    resolve_stack,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MINIMAL_FIXTURE = FIXTURES_DIR / "manifest_minimal.yml"
MALFORMED_FIXTURE = FIXTURES_DIR / "manifest_malformed.yml"


@pytest.mark.unit
def test_resolve_stack_returns_configured_stack_from_minimal_manifest() -> None:
    """``resolve_stack`` returns the first stack string in ``providers.stacks``."""
    # Arrange
    manifest_path = MINIMAL_FIXTURE
    assert manifest_path.is_file(), f"fixture missing: {manifest_path}"

    # Act
    stack = resolve_stack(manifest_path)

    # Assert -- the minimal fixture pins ``providers.stacks: [python]``.
    assert isinstance(stack, str), f"expected str, got {type(stack).__name__}"
    assert stack == "python"


@pytest.mark.unit
def test_read_work_items_returns_dict_from_minimal_manifest() -> None:
    """``read_work_items`` returns the top-level ``work_items`` block as a dict."""
    # Arrange
    manifest_path = MINIMAL_FIXTURE

    # Act
    work_items = read_work_items(manifest_path)

    # Assert -- shape mirrors the canonical manifest block (provider +
    # state_mapping + hierarchy at minimum).
    assert isinstance(work_items, dict), f"expected dict, got {type(work_items).__name__}"
    assert work_items.get("provider") == "github"
    assert "state_mapping" in work_items
    assert "hierarchy" in work_items
    # Nested block sanity: hierarchy is itself a dict.
    assert isinstance(work_items["hierarchy"], dict)


@pytest.mark.unit
def test_resolve_stack_raises_missing_manifest_error_when_path_absent(
    tmp_path: Path,
) -> None:
    """Absent manifest path raises the typed ``MissingManifestError``."""
    # Arrange -- a path that is guaranteed not to exist.
    absent = tmp_path / "does-not-exist" / "manifest.yml"
    assert not absent.exists()

    # Act + Assert
    with pytest.raises(MissingManifestError):
        resolve_stack(absent)


@pytest.mark.unit
def test_read_work_items_raises_missing_manifest_error_when_path_absent(
    tmp_path: Path,
) -> None:
    """``read_work_items`` raises ``MissingManifestError`` on absent path too."""
    # Arrange
    absent = tmp_path / "no-such-dir" / "manifest.yml"

    # Act + Assert
    with pytest.raises(MissingManifestError):
        read_work_items(absent)


@pytest.mark.unit
def test_resolve_stack_raises_invalid_manifest_error_on_malformed_yaml() -> None:
    """Malformed YAML raises the typed ``InvalidManifestError`` (not raw YAMLError)."""
    # Arrange
    manifest_path = MALFORMED_FIXTURE
    assert manifest_path.is_file(), f"fixture missing: {manifest_path}"

    # Act + Assert
    with pytest.raises(InvalidManifestError):
        resolve_stack(manifest_path)


@pytest.mark.unit
def test_read_work_items_raises_invalid_manifest_error_on_malformed_yaml() -> None:
    """``read_work_items`` also wraps YAML errors in ``InvalidManifestError``."""
    # Arrange
    manifest_path = MALFORMED_FIXTURE

    # Act + Assert
    with pytest.raises(InvalidManifestError):
        read_work_items(manifest_path)


@pytest.mark.unit
def test_missing_manifest_error_is_exception_subclass() -> None:
    """``MissingManifestError`` is a real ``Exception`` subclass."""
    assert issubclass(MissingManifestError, Exception)


@pytest.mark.unit
def test_invalid_manifest_error_is_exception_subclass() -> None:
    """``InvalidManifestError`` is a real ``Exception`` subclass."""
    assert issubclass(InvalidManifestError, Exception)


@pytest.mark.unit
def test_resolve_stack_perf_smoke_100_calls_under_5_seconds() -> None:
    """100 sequential ``resolve_stack`` calls finish in < 5 s wall-clock.

    Proxy for the spec §Phase 0 gate of ≤50 ms p95 per call. We use
    ``time.monotonic`` per the python conventions doc -- ``time.time``
    can jump backwards on NTP sync.
    """
    # Arrange
    manifest_path = MINIMAL_FIXTURE
    iterations = 100

    # Act
    start = time.monotonic()
    for _ in range(iterations):
        resolve_stack(manifest_path)
    elapsed = time.monotonic() - start

    # Assert -- generous local-machine ceiling so CI noise doesn't flake.
    assert elapsed < 5.0, (
        f"{iterations} resolve_stack calls took {elapsed:.3f}s "
        f"(>5s ceiling, ~{elapsed * 1000 / iterations:.1f}ms per call)"
    )
