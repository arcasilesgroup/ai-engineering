"""spec-185 D-185-01 (T-0.1): model-tier vocabulary + hook/twin parity gate.

There is no CI guard that the hook copy of ``observability.py`` and its
``src/ai_engineering/templates`` twin agree on ``_VALID_MODEL_TIERS``. This
test IS that guard: it asserts the two enums are identical, that the
vendor-neutral driver tiers are accepted, and that dispatch-metadata
validation still rejects a bogus tier.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_HOOK = _REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "observability.py"
_TWIN = (
    _REPO
    / "src"
    / "ai_engineering"
    / "templates"
    / ".ai-engineering"
    / "scripts"
    / "hooks"
    / "_lib"
    / "observability.py"
)

# Driver-capability tiers introduced by spec-185. Must all be legal event
# values so a non-Anthropic driver never raises ValueError.
_DRIVER_TIERS = frozenset({"frontier", "standard-floor", "stretch-floor"})


def _load(path: Path, name: str):
    assert path.is_file(), f"missing {path}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def hook_mod():
    return _load(_HOOK, "observability_hook")


@pytest.fixture(scope="module")
def twin_mod():
    return _load(_TWIN, "observability_twin")


@pytest.mark.unit
def test_hook_and_twin_enums_are_identical(hook_mod, twin_mod) -> None:
    assert hook_mod._VALID_MODEL_TIERS == twin_mod._VALID_MODEL_TIERS


@pytest.mark.unit
def test_driver_tiers_are_valid_event_values(hook_mod) -> None:
    assert _DRIVER_TIERS <= hook_mod._VALID_MODEL_TIERS


@pytest.mark.unit
def test_anthropic_dispatch_names_retained(hook_mod) -> None:
    # Additive, not a rename: the dispatch-effort axis stays legal.
    assert {"haiku", "sonnet", "opus"} <= hook_mod._VALID_MODEL_TIERS


@pytest.mark.unit
def test_vendor_neutral_tier_does_not_raise(hook_mod) -> None:
    # Would raise ValueError before spec-185.
    hook_mod._validate_dispatch_metadata({"model_tier": "standard-floor"})


@pytest.mark.unit
def test_bogus_tier_still_raises(hook_mod) -> None:
    with pytest.raises(ValueError):
        hook_mod._validate_dispatch_metadata({"model_tier": "gpt-9000"})
