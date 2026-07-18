"""Client-Value Lens level resolver + config model (spec-186 D-186-02).

Pins the resolution precedence — ``AIENG_VALUE_LENS_LEVEL`` env, then
``manifest.value_lens.default_level``, then the built-in ``"full"`` — plus
the invalid-value fallback and the manifest field wiring.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering import value_lens
from ai_engineering.config.loader import load_manifest_config
from ai_engineering.config.manifest import ManifestConfig, ValueLensConfig

REPO = Path(__file__).resolve().parents[3]


def test_env_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIENG_VALUE_LENS_LEVEL", "lite")
    # Even if the manifest says something else, env wins.
    monkeypatch.setattr(value_lens, "_manifest_level", lambda: "ultra")
    assert value_lens.resolve_level() == "lite"


def test_env_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIENG_VALUE_LENS_LEVEL", "ULTRA")
    assert value_lens.resolve_level() == "ultra"


def test_manifest_used_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIENG_VALUE_LENS_LEVEL", raising=False)
    monkeypatch.setattr(value_lens, "_manifest_level", lambda: "lite")
    assert value_lens.resolve_level() == "lite"


def test_default_full_when_no_env_no_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIENG_VALUE_LENS_LEVEL", raising=False)
    monkeypatch.setattr(value_lens, "_manifest_level", lambda: None)
    assert value_lens.resolve_level() == "full"


def test_invalid_env_falls_back_to_full(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIENG_VALUE_LENS_LEVEL", "bogus")
    assert value_lens.resolve_level() == "full"


def test_invalid_manifest_falls_back_to_full(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIENG_VALUE_LENS_LEVEL", raising=False)
    monkeypatch.setattr(value_lens, "_manifest_level", lambda: "nonsense")
    assert value_lens.resolve_level() == "full"


def test_config_model_default() -> None:
    assert ValueLensConfig().default_level == "full"
    assert ManifestConfig().value_lens.default_level == "full"


def test_repo_manifest_parses_with_value_lens() -> None:
    config = load_manifest_config(REPO)
    assert config.value_lens.default_level == "full"
