"""spec-154 AC5 — unit tests for `_lib/copilot-runtime.sh`.

`copilot_framework_python_script` and `copilot_framework_python_inline`
delegate interpreter selection to the shared `resolve-python.sh` resolver
so Copilot dispatch enforces the same >=3.11 gate as Claude Code and
Codex. These tests drive both public functions through the shared
resolver via subprocess against a synthetic project root:

* happy path — a fake ``$root/.venv/bin/python`` is selected and runs the
  target script (or inline ``-`` stdin) with args preserved;
* no-interpreter case — the functions honour their 127 fail contract when
  no venv / named / uv / bare-3.11 interpreter is reachable (PATH scrubbed
  via ``env -i``).

Stdlib + bash only — no pytest fixtures beyond ``tmp_path``.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "copilot-runtime.sh"
RESOLVER = RUNTIME.parent / "resolve-python.sh"


def _make_exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _fake_python(version: tuple[int, int]) -> str:
    """A fake python that answers the >=3.11 gate and echoes its argv.

    The resolver gates bare ``python3`` with a ``-c`` version probe; this
    stub honours that. For a real invocation it echoes the script path /
    stdin marker plus the forwarded args so the test can assert arg
    forwarding through the runtime functions.
    """
    major, minor = version
    return (
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "-c" ]; then\n'
        '  case "$2" in\n'
        f"    *version_info*) [ {major} -gt 3 ] && exit 0; "
        f"[ {major} -eq 3 ] && [ {minor} -ge 11 ] && exit 0; exit 1;;\n"
        "  esac\n"
        "fi\n"
        'echo "ran:$*"\n'
        "exit 0\n"
    )


def _setup_root(tmp_path: Path) -> Path:
    """A project root carrying a copy of the _lib resolver + runtime."""
    root = tmp_path / "proj"
    lib = root / ".ai-engineering" / "scripts" / "hooks" / "_lib"
    lib.mkdir(parents=True)
    (lib / "resolve-python.sh").write_text(RESOLVER.read_text(encoding="utf-8"), encoding="utf-8")
    (lib / "copilot-runtime.sh").write_text(RUNTIME.read_text(encoding="utf-8"), encoding="utf-8")
    return root


def _runtime_path(root: Path) -> Path:
    return root / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "copilot-runtime.sh"


def test_script_happy_path_selects_venv_and_forwards_args(tmp_path: Path) -> None:
    root = _setup_root(tmp_path)
    venv_py = root / ".venv" / "bin" / "python"
    _make_exe(venv_py, _fake_python((3, 12)))
    target = root / "hello.py"
    target.write_text("# target script\n", encoding="utf-8")

    body = (
        f'source "{_runtime_path(root)}"\n'
        f'copilot_framework_python_script "{root}" "{target}" --flag value\n'
    )
    res = subprocess.run(
        ["bash", "-c", body],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    # The resolved venv interpreter received the script path + args as argv.
    assert res.stdout.strip() == f"ran:{target} --flag value"


def test_inline_happy_path_selects_venv_and_forwards_args(tmp_path: Path) -> None:
    root = _setup_root(tmp_path)
    venv_py = root / ".venv" / "bin" / "python"
    _make_exe(venv_py, _fake_python((3, 13)))

    body = f'source "{_runtime_path(root)}"\ncopilot_framework_python_inline "{root}" alpha beta\n'
    res = subprocess.run(
        ["bash", "-c", body],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    # Inline mode runs `python - <args>`; the stub echoes "- alpha beta".
    assert res.stdout.strip() == "ran:- alpha beta"


def _run_scrubbed(root: Path, call: str, empty_bin: Path) -> subprocess.CompletedProcess[str]:
    """Source the runtime and invoke ``call`` with no interpreter reachable.

    ``copilot-runtime.sh`` runs under ``set -e``, so the function's
    nonzero return is captured via ``|| rc=$?`` (which suppresses ``set
    -e`` for that command) and echoed. PATH is scrubbed to an empty bin
    dir plus the system dirs that carry shell utilities (``bash``,
    ``dirname``) but NO modern interpreter: the only ``python3`` reachable
    is the macOS system 3.9, which the resolver's >=3.11 gate rejects, and
    there is no named ``python3.11+`` / ``uv`` on this PATH. The resolver
    therefore exhausts every branch and fails -> the 127 fail contract.
    """
    empty_bin.mkdir(parents=True, exist_ok=True)
    body = f'source "{_runtime_path(root)}"\nrc=0\n{call} || rc=$?\necho "rc=$rc"\n'
    env = {"PATH": os.pathsep.join([str(empty_bin), "/usr/bin", "/bin"])}
    return subprocess.run(
        ["/bin/bash", "-c", body],
        capture_output=True,
        text=True,
        env=env,
    )


def test_script_returns_127_when_no_interpreter(tmp_path: Path) -> None:
    root = _setup_root(tmp_path)
    target = root / "hello.py"
    target.write_text("# target script\n", encoding="utf-8")

    res = _run_scrubbed(
        root,
        f'copilot_framework_python_script "{root}" "{target}"',
        tmp_path / "emptybin",
    )
    assert "rc=127" in res.stdout, (
        f"expected 127 fail contract, got {res.stdout!r} / {res.stderr!r}"
    )


def test_inline_returns_127_when_no_interpreter(tmp_path: Path) -> None:
    root = _setup_root(tmp_path)

    res = _run_scrubbed(
        root,
        f'copilot_framework_python_inline "{root}"',
        tmp_path / "emptybin",
    )
    assert "rc=127" in res.stdout, (
        f"expected 127 fail contract, got {res.stdout!r} / {res.stderr!r}"
    )
