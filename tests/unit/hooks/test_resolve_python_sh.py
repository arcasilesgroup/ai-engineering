"""spec-154 Phase 1 — unit tests for `_lib/resolve-python.sh`.

The hook libraries legitimately require Python >=3.11 (``datetime.UTC``
etc.). Bare ``python3`` on a host may resolve to <3.11 (e.g. macOS
system 3.9.6), which raises ``ImportError: cannot import name 'UTC'``.
The resolver picks a >=3.11 interpreter for hook dispatch.

These tests drive the resolver via ``bash -c`` (sourcing the script and
calling ``resolve_python "$root"``) against a synthetic project root with
fake interpreters on ``PATH``. Stdlib + bash only — no pytest fixtures
beyond ``tmp_path``.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RESOLVER = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "resolve-python.sh"


def _make_exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _fake_python(version: tuple[int, int]) -> str:
    """A fake python that answers the >=3.11 gate via exit code.

    The resolver gates bare ``python3`` with
    ``python3 -c 'import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)'``.
    This stub honours that by parsing ``-c`` and exiting accordingly; for
    any other argv it just exits 0 (it is a real "interpreter" for exec).
    """
    major, minor = version
    return (
        "#!/usr/bin/env bash\n"
        f'if [ "$1" = "-c" ]; then\n'
        f'  case "$2" in\n'
        f"    *version_info*) [ {major} -gt 3 ] && exit 0; "
        f"[ {major} -eq 3 ] && [ {minor} -ge 11 ] && exit 0; exit 1;;\n"
        f"  esac\n"
        f"fi\n"
        f'echo "fake-python-{major}.{minor}"\n'
        f"exit 0\n"
    )


def _run_resolver(root: Path, path_dir: Path | None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    # Build a clean PATH: only the fake bin dir (+ /usr/bin /bin for bash et al).
    parts = []
    if path_dir is not None:
        parts.append(str(path_dir))
    parts.extend(["/usr/bin", "/bin"])
    env["PATH"] = os.pathsep.join(parts)
    script = f'source "{RESOLVER}"\nresolve_python "{root}"\n'
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
    )


def test_prefers_project_venv(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    venv_py = root / ".venv" / "bin" / "python"
    _make_exe(venv_py, _fake_python((3, 12)))
    # Also a named python3.13 on PATH — venv must still win.
    bindir = tmp_path / "bin"
    _make_exe(bindir / "python3.13", _fake_python((3, 13)))

    res = _run_resolver(root, bindir)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == str(venv_py)


def test_trusts_named_python313(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir(parents=True)
    bindir = tmp_path / "bin"
    _make_exe(bindir / "python3.13", _fake_python((3, 13)))

    res = _run_resolver(root, bindir)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == str(bindir / "python3.13")


def test_trusts_named_python311(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir(parents=True)
    bindir = tmp_path / "bin"
    _make_exe(bindir / "python3.11", _fake_python((3, 11)))

    res = _run_resolver(root, bindir)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == str(bindir / "python3.11")


def test_named_order_prefers_higher(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir(parents=True)
    bindir = tmp_path / "bin"
    _make_exe(bindir / "python3.11", _fake_python((3, 11)))
    _make_exe(bindir / "python3.12", _fake_python((3, 12)))
    _make_exe(bindir / "python3.13", _fake_python((3, 13)))

    res = _run_resolver(root, bindir)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == str(bindir / "python3.13")


def test_gates_bare_python3_on_version(tmp_path: Path) -> None:
    """Bare python3 that is <3.11 is rejected -> non-zero / empty."""
    root = tmp_path / "proj"
    root.mkdir(parents=True)
    bindir = tmp_path / "bin"
    _make_exe(bindir / "python3", _fake_python((3, 9)))

    res = _run_resolver(root, bindir)
    assert res.returncode != 0, f"expected failure, got stdout={res.stdout!r}"
    assert res.stdout.strip() == ""


def test_accepts_bare_python3_when_modern(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir(parents=True)
    bindir = tmp_path / "bin"
    _make_exe(bindir / "python3", _fake_python((3, 12)))

    res = _run_resolver(root, bindir)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == str(bindir / "python3")


def test_returns_nonzero_when_nothing_modern(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir(parents=True)
    bindir = tmp_path / "bin"  # empty
    bindir.mkdir()

    res = _run_resolver(root, bindir)
    assert res.returncode != 0
    assert res.stdout.strip() == ""


def test_caches_resolved_path(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    venv_py = root / ".venv" / "bin" / "python"
    _make_exe(venv_py, _fake_python((3, 12)))

    res = _run_resolver(root, None)
    assert res.returncode == 0, res.stderr
    cache = root / ".ai-engineering" / "runtime" / "resolved-python.txt"
    assert cache.is_file(), "resolver must cache the resolved interpreter"
    assert cache.read_text(encoding="utf-8").strip() == str(venv_py)


def test_rereads_cache(tmp_path: Path) -> None:
    """A pre-seeded valid cache is honoured even with nothing on PATH."""
    root = tmp_path / "proj"
    cached_py = tmp_path / "cached" / "python"
    _make_exe(cached_py, _fake_python((3, 12)))
    cache = root / ".ai-engineering" / "runtime" / "resolved-python.txt"
    cache.parent.mkdir(parents=True)
    cache.write_text(str(cached_py) + "\n", encoding="utf-8")

    empty = tmp_path / "emptybin"
    empty.mkdir()
    res = _run_resolver(root, empty)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == str(cached_py)


def test_rereresolves_when_cache_stale(tmp_path: Path) -> None:
    """A cached path that is no longer executable triggers re-resolution."""
    root = tmp_path / "proj"
    # Cache points at a non-existent interpreter.
    cache = root / ".ai-engineering" / "runtime" / "resolved-python.txt"
    cache.parent.mkdir(parents=True)
    cache.write_text(str(tmp_path / "gone" / "python") + "\n", encoding="utf-8")
    # But a real venv python exists.
    venv_py = root / ".venv" / "bin" / "python"
    _make_exe(venv_py, _fake_python((3, 12)))

    res = _run_resolver(root, None)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == str(venv_py)
    assert cache.read_text(encoding="utf-8").strip() == str(venv_py)
