"""Tests for the trusted-script lane manifest extension (spec-131 sub-004 T-4.D).

`hooks-manifest.json` gains two additive keys:

* ``trustedScripts`` — ``{relative_path: sha256}`` mirror of ``hooks`` for
  scripts that legitimately bypass RTK rewriting + IOC re-evaluation.
* ``trustedArgvs`` — list of literal argv forms the prompt-injection-guard
  short-circuits on (dual-key enforcement closes the ``bash -c "..."``
  bypass).

The regenerator (``regenerate-hooks-manifest.py``) MUST:
1. Populate both keys from module-level constants ``TRUSTED_SCRIPTS`` and
   ``TRUSTED_ARGVS``.
2. Preserve the existing ``hooks`` key shape (open-closed extension).
3. ``--check`` detects drift on both keys.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
REGENERATE_PATH = REPO / ".ai-engineering" / "scripts" / "regenerate-hooks-manifest.py"
INTEGRITY_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "integrity.py"


@pytest.fixture
def regen():
    """Load the regenerator module under a fresh name."""
    sys.modules.pop("aieng_regen_manifest", None)
    spec = importlib.util.spec_from_file_location("aieng_regen_manifest", REGENERATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_regen_manifest"] = module
    spec.loader.exec_module(module)
    return module


def test_module_exposes_trusted_constants(regen) -> None:
    """The regenerator MUST declare ``TRUSTED_SCRIPTS`` + ``TRUSTED_ARGVS``."""
    assert hasattr(regen, "TRUSTED_SCRIPTS"), (
        "regenerate-hooks-manifest.py must declare TRUSTED_SCRIPTS list"
    )
    assert hasattr(regen, "TRUSTED_ARGVS"), (
        "regenerate-hooks-manifest.py must declare TRUSTED_ARGVS list"
    )
    assert isinstance(regen.TRUSTED_SCRIPTS, list)
    assert isinstance(regen.TRUSTED_ARGVS, list)


def test_build_manifest_contains_trusted_keys(regen) -> None:
    """``_build_manifest`` MUST emit the two new keys."""
    manifest = regen._build_manifest()
    assert "trustedScripts" in manifest
    assert "trustedArgvs" in manifest
    assert isinstance(manifest["trustedScripts"], dict)
    assert isinstance(manifest["trustedArgvs"], list)


def test_existing_hooks_key_preserved(regen) -> None:
    """Open-closed: the existing ``hooks`` key MUST remain."""
    manifest = regen._build_manifest()
    assert "hooks" in manifest
    assert isinstance(manifest["hooks"], dict)
    assert manifest["hooks"], "hooks dict must not be empty"


def test_on_disk_manifest_has_trusted_keys() -> None:
    """The committed manifest carries both new keys."""
    manifest_path = REPO / ".ai-engineering" / "state" / "hooks-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "trustedScripts" in payload, (
        "hooks-manifest.json must carry trustedScripts after sub-004 T-4.D"
    )
    assert "trustedArgvs" in payload


def test_check_mode_passes_when_fresh(tmp_path: Path) -> None:
    """``--check`` returns 0 immediately after a fresh regenerate."""
    proc = subprocess.run(
        [sys.executable, str(REGENERATE_PATH), "--check"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    # Must not fail with stale manifest after T-4.D ships.
    assert proc.returncode == 0, f"--check failed: stderr={proc.stderr!r} stdout={proc.stdout!r}"


def test_manifests_equal_compares_trusted_scripts(regen, tmp_path: Path) -> None:
    """Helper that compares manifests MUST consider trustedScripts."""
    current = {
        "hooks": {"a.py": "abc"},
        "trustedScripts": {"trust.py": "def"},
        "trustedArgvs": [],
    }
    existing = {
        "hooks": {"a.py": "abc"},
        "trustedScripts": {"trust.py": "DIFFERENT"},
        "trustedArgvs": [],
    }
    helper = getattr(regen, "_manifests_equal", None) or getattr(regen, "_hooks_equal", None)
    assert helper is not None
    assert not helper(current, existing), "trustedScripts drift must register as not-equal"


def test_verify_trusted_script_helper_exists(tmp_path: Path) -> None:
    """``_lib/integrity.py`` exposes ``verify_trusted_script`` for T-4.F."""
    spec = importlib.util.spec_from_file_location("aieng_lib_integrity_trust", INTEGRITY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "verify_trusted_script"), (
        "_lib/integrity.py must expose verify_trusted_script for trusted-script lane"
    )


def test_verify_trusted_script_matches(tmp_path: Path) -> None:
    """Happy path: script bytes match a trustedScripts entry."""
    spec = importlib.util.spec_from_file_location("aieng_lib_integrity_trust2", INTEGRITY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    project = tmp_path
    script = project / "scripts" / "trust.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('trusted')")
    rel = script.relative_to(project).as_posix()
    sha = hashlib.sha256(script.read_bytes()).hexdigest()
    manifest = project / ".ai-engineering" / "state" / "hooks-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "hooks": {},
                "trustedScripts": {rel: sha},
                "trustedArgvs": [],
            }
        )
    )
    # Bust the manifest cache so the fresh write is observed.
    if hasattr(module, "_MANIFEST_CACHE"):
        module._MANIFEST_CACHE.clear()
    ok, reason = module.verify_trusted_script(script, project)
    assert ok is True
    assert reason is None


def test_verify_trusted_script_drift(tmp_path: Path) -> None:
    """sha256 drift surfaces as a failure with a reason string."""
    spec = importlib.util.spec_from_file_location("aieng_lib_integrity_trust3", INTEGRITY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    project = tmp_path
    script = project / "scripts" / "trust.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('tampered')")
    rel = script.relative_to(project).as_posix()
    manifest = project / ".ai-engineering" / "state" / "hooks-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "hooks": {},
                "trustedScripts": {rel: "0" * 64},
                "trustedArgvs": [],
            }
        )
    )
    if hasattr(module, "_MANIFEST_CACHE"):
        module._MANIFEST_CACHE.clear()
    ok, reason = module.verify_trusted_script(script, project)
    assert ok is False
    assert reason is not None
    assert "mismatch" in reason or "drift" in reason
