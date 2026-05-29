"""spec-154 Phase 2 — unit tests for `_lib/run-hook.sh`.

`run-hook.sh <script.py> [args]` resolves a >=3.11 interpreter (via
`resolve-python.sh`) and execs the PASSED script under it. The exec is
transparent: the process that runs is the `.py` arg itself, NOT the
launcher — `run_hook_safe` verifies integrity via the script's own
`__file__`, so the launcher must not insert itself into argv.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "run-hook.sh"


def _make_exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _fake_python(version: tuple[int, int]) -> str:
    major, minor = version
    return (
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "-c" ]; then\n'
        '  case "$2" in\n'
        f"    *version_info*) [ {major} -gt 3 ] && exit 0; "
        f"[ {major} -eq 3 ] && [ {minor} -ge 11 ] && exit 0; exit 1;;\n"
        "  esac\n"
        "fi\n"
        # For a real run, echo the script path it was asked to execute so
        # the test can assert the .py arg reached the interpreter as $1.
        'echo "ran:$1"\n'
        "exit 0\n"
    )


def _setup_root(tmp_path: Path) -> tuple[Path, Path]:
    """A project root carrying a copy of the _lib resolver + launcher."""
    root = tmp_path / "proj"
    lib = root / ".ai-engineering" / "scripts" / "hooks" / "_lib"
    lib.mkdir(parents=True)
    resolver_src = LAUNCHER.parent / "resolve-python.sh"
    (lib / "resolve-python.sh").write_text(
        resolver_src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (lib / "run-hook.sh").write_text(LAUNCHER.read_text(encoding="utf-8"), encoding="utf-8")
    return root, lib


def _run_launcher(
    lib: Path, script: Path, path_dir: Path | None, *, project_dir: Path
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    parts = []
    if path_dir is not None:
        parts.append(str(path_dir))
    parts.extend(["/usr/bin", "/bin"])
    env["PATH"] = os.pathsep.join(parts)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        ["bash", str(lib / "run-hook.sh"), str(script)],
        capture_output=True,
        text=True,
        env=env,
    )


def test_execs_passed_script_under_resolved_python(tmp_path: Path) -> None:
    root, lib = _setup_root(tmp_path)
    venv_py = root / ".venv" / "bin" / "python"
    _make_exe(venv_py, _fake_python((3, 12)))
    script = root / ".ai-engineering" / "scripts" / "hooks" / "demo.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("# demo hook\n", encoding="utf-8")

    res = _run_launcher(lib, script, None, project_dir=root)
    assert res.returncode == 0, res.stderr
    # The resolved interpreter received the .py path as $1 — transparent exec.
    assert res.stdout.strip() == f"ran:{script}"


def test_guard_path_one_stderr_line_exit_zero(tmp_path: Path) -> None:
    root, lib = _setup_root(tmp_path)
    # No venv, no >=3.11 interpreter anywhere on PATH.
    empty = tmp_path / "emptybin"
    empty.mkdir()
    script = root / ".ai-engineering" / "scripts" / "hooks" / "demo.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("# demo hook\n", encoding="utf-8")

    res = _run_launcher(lib, script, empty, project_dir=root)
    assert res.returncode == 0, f"guard path must exit 0, got {res.returncode}"
    assert res.stdout == ""
    stderr_lines = [ln for ln in res.stderr.splitlines() if ln.strip()]
    assert len(stderr_lines) == 1, f"expected exactly one stderr line, got {stderr_lines!r}"
    assert "Python >=3.11" in stderr_lines[0]
