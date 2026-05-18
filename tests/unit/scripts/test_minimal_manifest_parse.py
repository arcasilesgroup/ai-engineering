"""RED-phase tests for ``_read_manifest_minimal`` in session_bootstrap.py (spec-142 T-1).

Contract under test (T-2 will implement):

* ``_read_manifest_minimal(path: Path) -> dict`` -- stdlib-only YAML
  mini-parser that extracts only the two fields the dashboard needs:
  ``name`` and ``surfaces.enabled``.  Never raises; returns ``{}`` on
  error or missing fields.

These tests intentionally fail with ``AttributeError`` / ``ImportError``
until T-2 lands the helper in
``.ai-engineering/scripts/session_bootstrap.py``.

Anchors: spec-142 D-142-01 (mini-parser scope), D-142-07 (parser grammar).
TDD §10.5 RED phase.  §10.1 KISS (2-field grammar only).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / ".ai-engineering" / "scripts"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# RED-phase: this import resolves (session_bootstrap is importable) but the
# attribute _read_manifest_minimal does NOT yet exist -- that is the expected
# failure mode.  T-2 adds the helper; these tests then turn green.
import session_bootstrap  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path: Path, content: str) -> Path:
    """Write *content* to a ``manifest.yml`` inside *tmp_path*."""
    path = tmp_path / "manifest.yml"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# (a) Flow-list ``surfaces.enabled`` syntax
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_flow_list_surfaces_enabled(tmp_path: Path) -> None:
    """Flow-list ``surfaces.enabled: [github-copilot]`` is parsed correctly.

    The helper must return a dict with exactly the ``name`` and
    ``surfaces.enabled`` shape the dashboard consumes.
    """
    path = _write_manifest(
        tmp_path,
        "name: my-project\nsurfaces:\n  enabled: [github-copilot]\n",
    )

    result = session_bootstrap._read_manifest_minimal(path)

    assert isinstance(result, dict)
    assert result.get("name") == "my-project"
    surfaces = result.get("surfaces", {})
    assert isinstance(surfaces, dict)
    assert surfaces.get("enabled") == ["github-copilot"]


# ---------------------------------------------------------------------------
# (b) Block-list ``surfaces.enabled`` syntax
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_block_list_surfaces_enabled(tmp_path: Path) -> None:
    """Block-list ``surfaces.enabled:`` with ``- github-copilot`` is equivalent to (a)."""
    path = _write_manifest(
        tmp_path,
        "name: my-project\nsurfaces:\n  enabled:\n  - github-copilot\n",
    )

    result = session_bootstrap._read_manifest_minimal(path)

    assert isinstance(result, dict)
    surfaces = result.get("surfaces", {})
    assert isinstance(surfaces, dict)
    assert surfaces.get("enabled") == ["github-copilot"]


# ---------------------------------------------------------------------------
# (c) Unquoted name value
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unquoted_name_parses_cleanly(tmp_path: Path) -> None:
    """Unquoted ``name: ai-engineering`` is returned as a plain string."""
    path = _write_manifest(tmp_path, "name: ai-engineering\n")

    result = session_bootstrap._read_manifest_minimal(path)

    assert result.get("name") == "ai-engineering"


# ---------------------------------------------------------------------------
# (d) Double-quoted name value — quotes must be stripped
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_double_quoted_name_strips_quotes(tmp_path: Path) -> None:
    """``name: "ai-engineering"`` must resolve to the bare string ``ai-engineering``."""
    path = _write_manifest(tmp_path, 'name: "ai-engineering"\n')

    result = session_bootstrap._read_manifest_minimal(path)

    assert result.get("name") == "ai-engineering"


# ---------------------------------------------------------------------------
# (e) Parity with yaml.safe_load on the real repo manifest
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parity_with_yaml_safe_load_on_real_manifest() -> None:
    """Mini-parser result is a strict subset that matches ``yaml.safe_load``.

    The two fields ``name`` and ``surfaces.enabled`` returned by the
    mini-parser must equal the values ``yaml.safe_load`` sees in the
    real ``.ai-engineering/manifest.yml``.
    """
    real_manifest = REPO_ROOT / ".ai-engineering" / "manifest.yml"
    assert real_manifest.is_file(), f"real manifest not found: {real_manifest}"

    with real_manifest.open(encoding="utf-8") as fh:
        full = yaml.safe_load(fh)

    mini = session_bootstrap._read_manifest_minimal(real_manifest)

    assert isinstance(mini, dict)

    # The real repo manifest has both `name` and `surfaces.enabled`.
    # R-142-01: if the mini-parser silently fails to extract them, CI MUST go red.
    assert "name" in mini, (
        "mini-parser did not extract `name` from the real manifest — "
        "either the manifest schema changed (update _read_manifest_minimal grammar) "
        "or the parser regressed. R-142-01 mitigation must remain load-bearing."
    )
    assert mini["name"] == full.get("name"), (
        f"mini-parser name {mini['name']!r} differs from yaml.safe_load {full.get('name')!r}"
    )

    assert "surfaces" in mini, "mini-parser did not extract `surfaces` from the real manifest"
    assert "enabled" in mini["surfaces"], (
        "mini-parser did not extract `surfaces.enabled` from the real manifest"
    )
    full_enabled = (full.get("surfaces") or {}).get("enabled") or []
    assert mini["surfaces"]["enabled"] == full_enabled, (
        f"mini-parser surfaces.enabled {mini['surfaces']['enabled']!r} "
        f"differs from yaml.safe_load {full_enabled!r}"
    )


# ---------------------------------------------------------------------------
# (f) Missing field — file present but no ``name:`` key
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_missing_name_field_returns_empty_or_no_key(tmp_path: Path) -> None:
    """A manifest without a ``name:`` key must not raise; ``name`` absent from result."""
    path = _write_manifest(
        tmp_path,
        "schema_version: '2.0'\nsurfaces:\n  enabled: [claude-code]\n",
    )

    result = session_bootstrap._read_manifest_minimal(path)

    assert isinstance(result, dict)
    # The helper must not raise; ``name`` may be absent or the dict may be {}.
    assert "name" not in result or result.get("name") is None


# ---------------------------------------------------------------------------
# (g) Malformed file — garbage bytes must not raise
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_malformed_file_returns_empty_dict(tmp_path: Path) -> None:
    """Garbage bytes / invalid YAML must produce ``{}``; the helper MUST NOT raise."""
    path = tmp_path / "manifest.yml"
    path.write_bytes(b"\xff\xfe garbage: [unclosed bracket\n\x00")

    result = session_bootstrap._read_manifest_minimal(path)

    assert result == {}, f"malformed file must return empty dict, got {result!r}"


# ---------------------------------------------------------------------------
# (h) CRLF line endings — name must not include trailing carriage return
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_name_strips_carriage_return(tmp_path: Path) -> None:
    """A manifest with CRLF line endings must not bleed ``\\r`` into the name.

    On Windows checkouts without ``.gitattributes eol=lf``, lines end with
    ``\\r\\n``.  The regex must exclude ``\\r`` so ``result["name"]`` is clean.
    H-1 guard (spec-142 Phase 6 review).
    """
    path = tmp_path / "manifest.yml"
    path.write_bytes(b"name: foo\r\nother: bar\r\n")

    result = session_bootstrap._read_manifest_minimal(path)

    assert result.get("name") == "foo", (
        f"name must be 'foo' without trailing carriage return, got {result.get('name')!r}"
    )


# ---------------------------------------------------------------------------
# (i) Inline YAML comment — name must not include comment text
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_name_ignores_inline_comment(tmp_path: Path) -> None:
    """A name line with an inline YAML comment must yield only the scalar value.

    ``name: foo  # production label`` must parse to ``"foo"``, not
    ``"foo  # production label"``.  ``yaml.safe_load`` strips comments;
    the mini-parser must match that behaviour.
    H-1 guard (spec-142 Phase 6 review).
    """
    path = _write_manifest(tmp_path, "name: foo  # production label\n")

    result = session_bootstrap._read_manifest_minimal(path)

    assert result.get("name") == "foo", (
        f"name must be 'foo' without inline comment, got {result.get('name')!r}"
    )
