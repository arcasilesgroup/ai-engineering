"""Tests for the Surface domain primitive (spec-133 D-133-15).

RED-first: assert the registry shape and Surface invariants before any
production code exists.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ai_engineering.domain.surface import (
    SURFACE_IDS,
    Surface,
    SurfaceUnknownError,
    get_surface,
    iter_surfaces,
)


def test_surface_registry_has_seven_canonical_ids() -> None:
    expected = {
        "claude-code",
        "codex",
        "gemini-cli",
        "github-copilot",
        "opencode",
        "cursor",
        "antigravity",
    }
    assert set(SURFACE_IDS) == expected


def test_iter_surfaces_returns_seven_frozen_dataclasses() -> None:
    surfaces = list(iter_surfaces())
    assert len(surfaces) == 7
    for s in surfaces:
        assert isinstance(s, Surface)
        with pytest.raises((AttributeError, TypeError, FrozenInstanceError)):
            s.id = "mutated"  # frozen


def test_each_surface_carries_required_fields() -> None:
    for s in iter_surfaces():
        assert s.id
        assert s.display_name
        assert s.instruction_files
        assert s.tree_dir
        assert s.hook_engine in {"native", "plugin", "stdio", "none"}
        assert s.audit_capability in {"full", "partial", "none"}


def test_claude_code_carries_hook_engine_native() -> None:
    s = get_surface("claude-code")
    assert s.hook_engine == "native"
    assert s.audit_capability == "full"
    assert ".claude/" in s.tree_dir


def test_opencode_carries_plugin_engine_full_surface() -> None:
    s = get_surface("opencode")
    assert s.hook_engine == "plugin"
    assert s.audit_capability == "full"
    assert ".opencode/" in s.tree_dir


def test_cursor_carries_stdio_engine_full_surface() -> None:
    s = get_surface("cursor")
    assert s.hook_engine == "stdio"
    assert s.audit_capability == "full"
    assert ".cursor/" in s.tree_dir


def test_antigravity_is_mirror_only() -> None:
    s = get_surface("antigravity")
    assert s.hook_engine == "none"
    assert s.audit_capability == "none"


def test_get_surface_unknown_raises() -> None:
    with pytest.raises(SurfaceUnknownError):
        get_surface("not-a-surface")


def test_surface_ids_returns_tuple_not_list_for_immutability() -> None:
    assert isinstance(SURFACE_IDS, tuple)


def test_each_surface_has_autodetect_marker() -> None:
    for s in iter_surfaces():
        # Allow None for surfaces with no project-level marker (none for now)
        assert s.autodetect_marker is None or isinstance(s.autodetect_marker, tuple)
