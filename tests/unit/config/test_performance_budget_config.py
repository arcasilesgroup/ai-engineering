"""Contract tests for ``performance.budget`` (spec-201 D-201-13).

The token spend cap ships DISABLED. ``max_session_tokens: 0`` means "no cap",
because a non-zero shipped default would begin denying agent dispatches in
every consumer repository at a number nobody chose. Enforcement is live and
proven at a configured value (``tests/unit/hooks/test_spend_cap_guard.py``);
the DEFAULT is inert, and that is pinned here.

There is no ``performance:`` block in either the root or the template
``manifest.yml`` — the pydantic default IS the shipped value, so this module is
the only place the shipped default can be asserted.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.config.manifest import (
    PerformanceBudgetConfig,
    PerformanceConfig,
)


def test_spend_cap_ships_disabled() -> None:
    """The shipped default is 0 — inert, never a number nobody chose."""
    assert PerformanceBudgetConfig().max_session_tokens == 0
    assert PerformanceConfig().budget.max_session_tokens == 0


def test_budget_is_a_first_class_performance_field() -> None:
    """``performance.budget`` sits beside ``performance.concurrency``."""
    performance = PerformanceConfig()
    assert isinstance(performance.budget, PerformanceBudgetConfig)
    assert performance.concurrency is not None


def test_configured_value_round_trips_through_the_loader(tmp_path: Path) -> None:
    """An explicit manifest value survives ``load_manifest_config``."""
    manifest = tmp_path / ".ai-engineering" / "manifest.yml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "performance:\n  budget:\n    max_session_tokens: 250000\n",
        encoding="utf-8",
    )
    config = load_manifest_config(tmp_path)
    assert config.performance.budget.max_session_tokens == 250000


def test_absent_block_falls_back_to_the_disabled_default(tmp_path: Path) -> None:
    """A manifest with no ``performance:`` block leaves the cap off."""
    manifest = tmp_path / ".ai-engineering" / "manifest.yml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("providers:\n  vcs: github\n", encoding="utf-8")
    config = load_manifest_config(tmp_path)
    assert config.performance.budget.max_session_tokens == 0


def test_this_repository_ships_the_cap_disabled() -> None:
    """The repo's own manifest declares no cap — the default is what ships."""
    repo_root = Path(__file__).resolve().parents[3]
    config = load_manifest_config(repo_root)
    assert config.performance.budget.max_session_tokens == 0
