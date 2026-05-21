"""Acceptance gate: fresh ``ai-eng install`` produces zero noise.

spec-132 D-132-01 / sub-001 acceptance: a fresh install on an empty
project root must finish without WARN noise on stderr, without
leaving legacy JSON sidecars behind, and within the 30-second budget.
The smoke test is deliberately small in scope so it can grow as later
sub-specs land (Renderer, help-on-empty, surface consolidation).

This test exercises the higher-level ``install()`` entry point so the
manifest write + state.db bootstrap chain runs end-to-end without the
shell fork overhead of a ``subprocess`` invocation. Direct
``install_with_pipeline()`` invocation skips the manifest layer, which
yields ValidationError noise when downstream loaders read it.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from ai_engineering.installer.service import install
from ai_engineering.state.state_db import _reset_fallback_warnings


def _ensure_project_marker(tmp_path: Path) -> None:
    """Mark the tmp directory as a project root so install does not bail."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "smoke"\nversion = "0.0.1"\n', encoding="utf-8"
    )


def test_fresh_install_emits_no_stale_state_warning(tmp_path: Path, caplog) -> None:
    """spec-132 D-132-07: no stale-state warnings during a fresh install."""
    _reset_fallback_warnings()
    _ensure_project_marker(tmp_path)

    with caplog.at_level(logging.WARNING):
        install(tmp_path, stacks=["python"])

    stale_warnings = [r for r in caplog.records if "stale state JSON fallback" in r.getMessage()]
    assert not stale_warnings, (
        "Fresh install should not emit any stale-state warnings: "
        + "; ".join(r.getMessage() for r in stale_warnings)
    )


def test_fresh_install_state_files(tmp_path: Path) -> None:
    """Install state-file shape: ownership stays state.db-only; decisions are files-only.

    spec-132 D-132-08: no ownership-map.json sidecar (still state.db until P3).
    spec-148 P2: decision-store.json IS the canonical decision SoT and must exist.
    """
    _reset_fallback_warnings()
    _ensure_project_marker(tmp_path)

    install(tmp_path, stacks=["python"])

    state_dir = tmp_path / ".ai-engineering" / "state"
    assert not (state_dir / "ownership-map.json").exists(), (
        "ownership-map.json must not appear post-install (spec-132 D-132-08; state.db until P3)"
    )
    assert (state_dir / "decision-store.json").is_file(), (
        "decision-store.json must exist post-install (spec-148 P2 files-only)"
    )


def test_fresh_install_under_thirty_seconds(tmp_path: Path) -> None:
    """spec-132 sub-001 acceptance: install completes in <30s wall-clock."""
    _reset_fallback_warnings()
    _ensure_project_marker(tmp_path)

    started = time.monotonic()
    install(tmp_path, stacks=["python"])
    elapsed = time.monotonic() - started

    assert elapsed < 30.0, f"Fresh install took {elapsed:.2f}s; spec-132 acceptance budget is 30s."


def test_only_root_constitution_after_install(tmp_path: Path) -> None:
    """spec-132 D-132-14: exactly one CONSTITUTION.md after install."""
    _reset_fallback_warnings()
    _ensure_project_marker(tmp_path)

    install(tmp_path, stacks=["python"])

    matches = sorted(tmp_path.rglob("CONSTITUTION.md"))
    assert len(matches) == 1, (
        "Expected exactly one CONSTITUTION.md per install; found:\n"
        + "\n".join(str(p.relative_to(tmp_path)) for p in matches)
    )
