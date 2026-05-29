"""spec-154 keystone regression — hook dispatch resolves >=3.11.

Reproduces the production bug: a host where bare ``python3`` is <3.11
(macOS system 3.9.6) cannot run the hook libraries, which import
``datetime.UTC`` (raises ``ImportError: cannot import name 'UTC'``).

Case 1: with a forced <3.11 ``python3`` FIRST on PATH but a >=3.11
interpreter available (the project ``.venv``), invoking a representative
hook THROUGH ``run-hook.sh`` runs it under >=3.11 — no ImportError,
exit 0. This FAILS against the OLD bare-``python3`` wiring (the fake
python3 raises) and PASSES through the launcher.

Case 2: with NO >=3.11 interpreter anywhere, the launcher prints exactly
one stderr line and exits 0 (fail-open hot path).
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks"
LAUNCHER = HOOKS_DIR / "_lib" / "run-hook.sh"
GUARD = HOOKS_DIR / "prompt-injection-guard.py"
VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"


def _make_exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


# A "python3" stub that mimics system 3.9.6: it CANNOT run the hook
# libraries and raises on any real execution, but answers the resolver's
# version gate honestly (exit 1 -> "I am <3.11").
_FAKE_PY39 = "\n".join(
    [
        "#!/usr/bin/env bash",
        'if [ "$1" = "-c" ]; then',
        '  case "$2" in',
        "    *version_info*) exit 1;;",  # <3.11
        "  esac",
        "fi",
        'echo "ImportError: cannot import name UTC" >&2',
        "exit 1",
        "",
    ]
)


def _run_through_launcher(*, path_dir: Path, project_dir: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([str(path_dir), "/usr/bin", "/bin"])
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        ["bash", str(LAUNCHER), str(GUARD)],
        input="{}",
        capture_output=True,
        text=True,
        env=env,
    )


def test_dispatch_picks_modern_interpreter_over_stale_python3(tmp_path: Path) -> None:
    assert VENV_PY.is_file(), "project .venv must exist to exercise the venv-first path"
    # Clear any prior resolver cache so the resolution is exercised fresh.
    cache = REPO_ROOT / ".ai-engineering" / "runtime" / "resolved-python.txt"
    saved = cache.read_text(encoding="utf-8") if cache.is_file() else None
    if cache.is_file():
        cache.unlink()
    try:
        bindir = tmp_path / "bin"
        _make_exe(bindir / "python3", _FAKE_PY39)  # stale 3.9 first on PATH

        res = _run_through_launcher(path_dir=bindir, project_dir=REPO_ROOT)
        assert res.returncode == 0, f"stderr={res.stderr!r} stdout={res.stdout!r}"
        assert "ImportError" not in res.stderr, (
            "hook ran under the stale 3.9 python3 instead of the venv"
        )
    finally:
        if saved is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(saved, encoding="utf-8")
        elif cache.is_file():
            cache.unlink()


def test_dispatch_fails_open_when_no_modern_interpreter(tmp_path: Path) -> None:
    # Isolated project root with NO venv and NO pyproject (so no uv path),
    # only a stale 3.9 python3 on PATH.
    proj = tmp_path / "proj"
    (proj / ".ai-engineering" / "runtime").mkdir(parents=True)
    bindir = tmp_path / "bin"
    _make_exe(bindir / "python3", _FAKE_PY39)

    res = _run_through_launcher(path_dir=bindir, project_dir=proj)
    assert res.returncode == 0, f"fail-open must exit 0, got {res.returncode}"
    stderr_lines = [ln for ln in res.stderr.splitlines() if ln.strip()]
    assert len(stderr_lines) == 1, f"expected one stderr line, got {stderr_lines!r}"
    assert "Python >=3.11" in stderr_lines[0]
