"""spec-154 keystone regression — hook dispatch resolves >=3.11.

Reproduces the production bug: a host where bare ``python3`` is <3.11
(macOS system 3.9.6) cannot run the hook libraries, which import
``datetime.UTC`` (raises ``ImportError: cannot import name 'UTC'``).

Case 1 (AC6): with a forced <3.11 ``python3`` on the hermetic PATH but a
>=3.11 interpreter available via the project ``.venv``, invoking a
SENTINEL hook THROUGH ``run-hook.sh`` runs it under >=3.11 — exit 0, the
sentinel reports its own ``sys.version_info`` (>=3.11), and the stale 3.9
did NOT run. This FAILS against the OLD bare-``python3`` wiring (which
would run the 3.9 fake) and PASSES through the launcher.

Case 2: with NO >=3.11 interpreter anywhere, the launcher prints exactly
one stderr line and exits 0 (fail-open hot path).

Hermeticity: every subprocess ``PATH`` is a single sandbox bin dir
(coreutils + the test's fakes), never ``/usr/bin``/``/bin`` — so an
ambient CI ``python3.12`` cannot leak and be trusted by name. The tests
fabricate everything they assert on; they do NOT depend on a committed
``REPO_ROOT/.venv`` (CI checkouts have none).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests._hermetic_bin import hermetic_env, make_exe, make_sandbox_bin

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks"
LAUNCHER = HOOKS_DIR / "_lib" / "run-hook.sh"
GUARD = HOOKS_DIR / "prompt-injection-guard.py"
VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"


# A "python3" stub that mimics system 3.9.6: it CANNOT run the hook
# libraries and raises on any real execution, but answers the resolver's
# version gate honestly (exit 1 -> "I am <3.11"). It also drops a marker
# file on real exec so a test can prove the stale python NEVER ran.
def _fake_py39(marker: Path) -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            'if [ "$1" = "-c" ]; then',
            '  case "$2" in',
            "    *version_info*) exit 1;;",  # <3.11
            "  esac",
            "fi",
            f'echo stale-3.9-ran > "{marker}"',
            'echo "ImportError: cannot import name UTC" >&2',
            "exit 1",
            "",
        ]
    )


# A real >=3.11 venv shim: exec the genuine running interpreter (the
# >=3.11 venv python that runs pytest). This is what the resolver finds
# first under ``<root>/.venv/bin/python``.
def _venv_shim() -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            f'exec "{sys.executable}" "$@"',
            "",
        ]
    )


# A self-describing sentinel hook: reports its interpreter version so the
# test proves WHICH python actually ran it. Avoids needing the full repo
# manifest under the tmp project root (which the real guard would require).
_SENTINEL = "import sys\nprint(f'PYVER={sys.version_info[0]}.{sys.version_info[1]}')\n"


def _copy_lib(root: Path) -> Path:
    """Copy the real resolver + launcher into ``root``'s _lib (sourced relatively)."""
    lib = root / ".ai-engineering" / "scripts" / "hooks" / "_lib"
    lib.mkdir(parents=True, exist_ok=True)
    (lib / "resolve-python.sh").write_text(
        (LAUNCHER.parent / "resolve-python.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (lib / "run-hook.sh").write_text(LAUNCHER.read_text(encoding="utf-8"), encoding="utf-8")
    return lib


def _run_through_launcher(
    lib: Path, script: Path, sandbox_bin: Path, *, project_dir: Path
) -> subprocess.CompletedProcess[str]:
    env = hermetic_env(sandbox_bin, CLAUDE_PROJECT_DIR=str(project_dir))
    bash = str(sandbox_bin / "bash")
    return subprocess.run(
        [bash, str(lib / "run-hook.sh"), str(script)],
        input="{}",
        capture_output=True,
        text=True,
        env=env,
    )


def test_dispatch_picks_modern_interpreter_over_stale_python3(tmp_path: Path) -> None:
    """AC6 — launcher selects the >=3.11 venv over a stale 3.9 ``python3``.

    Fully fabricated + hermetic: tmp project root with a real >=3.11 venv
    shim, a fake 3.9 ``python3`` as the only python on PATH, and a
    self-describing sentinel hook. No dependency on a committed repo
    ``.venv``.
    """
    root = tmp_path / "proj"
    lib = _copy_lib(root)

    # >=3.11 venv shim (exec the genuine running interpreter).
    make_exe(root / ".venv" / "bin" / "python", _venv_shim())

    # Stale 3.9 python3 — the ONLY python on the hermetic PATH.
    sandbox_bin = make_sandbox_bin(tmp_path)
    marker = tmp_path / "stale-ran.marker"
    make_exe(sandbox_bin / "python3", _fake_py39(marker))

    sentinel = root / ".ai-engineering" / "scripts" / "hooks" / "sentinel.py"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(_SENTINEL, encoding="utf-8")

    res = _run_through_launcher(lib, sentinel, sandbox_bin, project_dir=root)

    assert res.returncode == 0, f"stderr={res.stderr!r} stdout={res.stdout!r}"
    assert "ImportError" not in res.stderr, (
        "hook ran under the stale 3.9 python3 instead of the venv"
    )
    assert not marker.exists(), "the stale 3.9 python3 must NOT have run the hook"
    # The sentinel reports the interpreter that actually ran it: >=3.11.
    assert "PYVER=3." in res.stdout, f"unexpected sentinel output: {res.stdout!r}"
    minor = int(res.stdout.split("PYVER=3.", 1)[1].split()[0])
    assert minor >= 11, f"launcher selected a <3.11 interpreter: {res.stdout!r}"


def test_dispatch_fails_open_when_no_modern_interpreter(tmp_path: Path) -> None:
    """Fail-open — no venv, no pyproject, only a stale 3.9: one stderr line, exit 0."""
    root = tmp_path / "proj"
    lib = _copy_lib(root)
    (root / ".ai-engineering" / "runtime").mkdir(parents=True, exist_ok=True)

    sandbox_bin = make_sandbox_bin(tmp_path)
    marker = tmp_path / "stale-ran.marker"
    make_exe(sandbox_bin / "python3", _fake_py39(marker))

    sentinel = root / ".ai-engineering" / "scripts" / "hooks" / "sentinel.py"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(_SENTINEL, encoding="utf-8")

    res = _run_through_launcher(lib, sentinel, sandbox_bin, project_dir=root)
    assert res.returncode == 0, f"fail-open must exit 0, got {res.returncode}"
    stderr_lines = [ln for ln in res.stderr.splitlines() if ln.strip()]
    assert len(stderr_lines) == 1, f"expected one stderr line, got {stderr_lines!r}"
    assert "Python >=3.11" in stderr_lines[0]


@pytest.mark.skipif(
    not (REPO_ROOT / ".venv" / "bin" / "python").exists(),
    reason="needs local project .venv (CI checkouts have none)",
)
def test_real_guard_runs_through_launcher_under_venv(tmp_path: Path) -> None:
    """Faithful end-to-end: the REAL prompt-injection-guard, through the real
    launcher, under the repo ``.venv`` — proving the production wiring runs a
    >=3.11 hook to completion. Skipped on CI (no committed ``.venv``)."""
    sandbox_bin = make_sandbox_bin(tmp_path)
    marker = tmp_path / "stale-ran.marker"
    make_exe(sandbox_bin / "python3", _fake_py39(marker))

    # Run the genuine repo launcher + guard against the real repo root so
    # the guard finds the manifest it expects. The repo .venv is resolved
    # by absolute path (not PATH), so the PATH stays hermetic.
    env = hermetic_env(sandbox_bin, CLAUDE_PROJECT_DIR=str(REPO_ROOT))
    res = subprocess.run(
        [str(sandbox_bin / "bash"), str(LAUNCHER), str(GUARD)],
        input="{}",
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0, f"stderr={res.stderr!r}"
    assert "ImportError" not in res.stderr
    assert not marker.exists(), "the stale 3.9 python3 must NOT have run the guard"
