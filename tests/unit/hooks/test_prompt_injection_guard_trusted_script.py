"""Tests for the trusted-script bypass lane in ``prompt-injection-guard``.

spec-131 sub-004 T-4.F / D-131-12: Bash invocations matching the literal
``trustedArgvs`` entries AND whose sha256 matches the ``trustedScripts``
manifest entry short-circuit the IOC + injection pattern scans. Dual-key
enforcement (literal argv match + script bytes match) closes the
``bash -c "..."`` bypass and the byte-modification bypass.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
GUARD_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "prompt-injection-guard.py"
INTEGRITY_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "integrity.py"


@pytest.fixture
def guard():
    """Load ``prompt-injection-guard.py`` under a fresh module name."""
    sys.modules.pop("aieng_prompt_injection_guard_trust", None)
    spec = importlib.util.spec_from_file_location("aieng_prompt_injection_guard_trust", GUARD_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_prompt_injection_guard_trust"] = module
    spec.loader.exec_module(module)
    return module


def test_helper_exists(guard) -> None:
    """Trusted-script matcher MUST be exposed at module scope."""
    assert hasattr(guard, "_is_trusted_script_argv")


def _setup_manifest(tmp_path: Path, script_text: str, argv: str) -> tuple[Path, Path]:
    """Materialise a fake project root with a trusted script + manifest."""
    project = tmp_path
    script_rel = "scripts/trust.py"
    script = project / script_rel
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(script_text)
    sha = hashlib.sha256(script.read_bytes()).hexdigest()
    manifest = project / ".ai-engineering" / "state" / "hooks-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "hooks": {},
                "trustedScripts": {script_rel: sha},
                "trustedArgvs": [argv],
            }
        )
    )
    return project, script


def test_matched_argv_with_clean_bytes_returns_argv(
    guard, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, _script = _setup_manifest(
        tmp_path,
        "print('trusted')",
        "python3 scripts/trust.py",
    )
    # Clear any cached manifest from prior tests.
    monkeypatch.setattr(
        guard,
        "_resolve_trusted_script_path",
        lambda content, project_root: project_root / "scripts" / "trust.py",
    )
    result = guard._is_trusted_script_argv("python3 scripts/trust.py", project)
    assert result == "python3 scripts/trust.py"


def test_matched_argv_with_drift_returns_drift_sentinel(
    guard, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When argv matches but bytes drift, the helper signals drift."""
    project, script = _setup_manifest(
        tmp_path,
        "print('original')",
        "python3 scripts/trust.py",
    )
    # Modify the script bytes to force drift.
    script.write_text("print('tampered')")
    monkeypatch.setattr(
        guard,
        "_resolve_trusted_script_path",
        lambda content, project_root: project_root / "scripts" / "trust.py",
    )
    result = guard._is_trusted_script_argv("python3 scripts/trust.py", project)
    assert result == guard._TRUSTED_SCRIPT_DRIFT_SENTINEL


def test_argv_with_extra_args_does_not_match(
    guard, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``python3 scripts/trust.py --extra`` is NOT a literal match."""
    project, _script = _setup_manifest(
        tmp_path,
        "print('trusted')",
        "python3 scripts/trust.py",
    )
    result = guard._is_trusted_script_argv("python3 scripts/trust.py --extra", project)
    assert result is None


def test_argv_via_bash_c_does_not_match(
    guard, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``bash -c "python3 scripts/trust.py"`` bypasses the literal match."""
    project, _script = _setup_manifest(
        tmp_path,
        "print('trusted')",
        "python3 scripts/trust.py",
    )
    result = guard._is_trusted_script_argv('bash -c "python3 scripts/trust.py"', project)
    assert result is None


def test_empty_trusted_argvs_no_match(guard, tmp_path: Path) -> None:
    """No ``trustedArgvs`` entries -> no possible match."""
    project = tmp_path
    manifest = project / ".ai-engineering" / "state" / "hooks-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "hooks": {},
                "trustedScripts": {},
                "trustedArgvs": [],
            }
        )
    )
    assert guard._is_trusted_script_argv("python3 scripts/trust.py", project) is None


def test_drift_sentinel_is_distinct_from_none(guard) -> None:
    """Drift sentinel MUST be a non-None constant so callers can branch."""
    assert guard._TRUSTED_SCRIPT_DRIFT_SENTINEL is not None
    assert isinstance(guard._TRUSTED_SCRIPT_DRIFT_SENTINEL, str)
