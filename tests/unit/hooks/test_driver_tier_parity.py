"""spec-185 T-0.4: hook/package driver-tier parity + sidecar roundtrip.

The stdlib hook copy (``_lib/driver_tier.py``) and the package copy
(``ai_engineering.state.driver_tier``) carry independent family maps with no
other CI guard. This test asserts they resolve identically across a battery of
model ids, and that the hook sidecar write/read roundtrips.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from ai_engineering.state import driver_tier as pkg_dt

_REPO = Path(__file__).resolve().parents[3]
_HOOK = _REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "driver_tier.py"
_TWIN = (
    _REPO
    / "src"
    / "ai_engineering"
    / "templates"
    / ".ai-engineering"
    / "scripts"
    / "hooks"
    / "_lib"
    / "driver_tier.py"
)

_MODEL_IDS = [
    "claude-fable-5",
    "claude-mythos-5",
    "claude-opus-4-8",
    "claude-sonnet-5",
    "claude-haiku-4-5-20251001",
    "gpt-5",
    "gpt-5-mini",
    "gpt-4.1-2025",
    "gpt-4.1-nano",
    "gpt-4o",
    "gpt-4o-mini",
    "glm5.2",
    "glm-4-flash",
    "glm-4-air",
    "deepseek-v4-flash",
    "mimo-v2.5",
    "qwen3.6",
    "gemma4",
    "totally-unknown-model",
    "",
]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def hook_dt():
    return _load(_HOOK, "hook_driver_tier")


@pytest.mark.unit
def test_hook_twin_is_byte_identical() -> None:
    assert _HOOK.read_bytes() == _TWIN.read_bytes()


@pytest.mark.unit
@pytest.mark.parametrize("model_id", _MODEL_IDS)
def test_hook_and_pkg_resolve_identically(hook_dt, model_id: str) -> None:
    assert hook_dt.resolve_driver_tier(model_id, env={}) == pkg_dt.resolve_driver_tier(
        model_id, env={}
    )


@pytest.mark.unit
def test_family_maps_agree(hook_dt) -> None:
    assert hook_dt._FAMILY_TIERS == pkg_dt._FAMILY_TIERS
    assert hook_dt.DRIVER_TIERS == pkg_dt.DRIVER_TIERS


@pytest.mark.unit
def test_sidecar_write_read_roundtrip(
    hook_dt, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AIENG_DRIVER_TIER", raising=False)
    tier = hook_dt.write_driver_tier(tmp_path, "deepseek-v4-flash")
    assert tier == "standard-floor"
    assert hook_dt.read_driver_tier(tmp_path) == "standard-floor"


@pytest.mark.unit
def test_sidecar_lands_in_canonical_runtime_dir(hook_dt, tmp_path: Path) -> None:
    # spec-125 D-125-09: state/runtime/ is forbidden for new code; the
    # canonical runtime dir is .ai-engineering/runtime/ (plan.md T-0.4 gate).
    assert hook_dt.driver_tier_path(tmp_path) == (
        tmp_path / ".ai-engineering" / "runtime" / "driver-tier.json"
    )


@pytest.mark.unit
def test_sidecar_missing_reads_conservative_default(hook_dt, tmp_path: Path) -> None:
    assert hook_dt.read_driver_tier(tmp_path) == "stretch-floor"


@pytest.mark.unit
@pytest.mark.parametrize(
    "garbage",
    [
        "",  # empty (benign aborted-publish state)
        "{not json",  # corrupt JSON
        '["x"]',  # valid JSON, not an object
        '{"tier": "bogus"}',  # object with an unknown tier value
        '{"tier": {"x": 1}}',  # object with a non-string tier
    ],
)
def test_sidecar_corrupt_reads_conservative_default(hook_dt, tmp_path: Path, garbage: str) -> None:
    path = hook_dt.driver_tier_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(garbage, encoding="utf-8")
    assert hook_dt.read_driver_tier(tmp_path) == "stretch-floor"


@pytest.mark.unit
def test_sidecar_corruption_emits_framework_error(
    hook_dt, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # gate-policy: plumbing fails open and must log. Corruption (not absence)
    # appends a framework_error line mirroring trace_context's fallback.
    monkeypatch.syspath_prepend(str(_REPO / ".ai-engineering" / "scripts" / "hooks"))
    path = hook_dt.driver_tier_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")

    assert hook_dt.read_driver_tier(tmp_path) == "stretch-floor"

    events = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
    assert events.exists(), "corruption should append a framework_error event"
    entry = json.loads(events.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert entry["kind"] == "framework_error"
    assert entry["component"] == "state.driver_tier"
    assert entry["detail"]["error_code"] == "driver_tier_corrupted"


@pytest.mark.unit
def test_override_env_wins(hook_dt) -> None:
    assert (
        hook_dt.resolve_driver_tier("claude-opus-4-8", env={"AIENG_DRIVER_TIER": "stretch-floor"})
        == "stretch-floor"
    )
