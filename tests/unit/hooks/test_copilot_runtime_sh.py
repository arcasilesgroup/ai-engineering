"""spec-154 AC5 — unit tests for `_lib/copilot-runtime.sh`.

`copilot_framework_python_script` and `copilot_framework_python_inline`
delegate interpreter selection to the shared `resolve-python.sh` resolver
so Copilot dispatch enforces the same >=3.11 gate as Claude Code and
Codex.

The subprocess PATH is HERMETIC (a single sandbox bin dir seeded with the
coreutils the scripts need, never `/usr/bin` or `/bin`) so an ambient
`python3.12` on CI cannot leak into the resolver's named-interpreter
probe and defeat the no-interpreter (127) cases. The bash launcher is
POSIX, so `make_sandbox_bin` skips these on Windows (spec-154 R4 — the
Windows pwsh/.ps1 dispatch path is a deferred follow-up).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests._hermetic_bin import hermetic_env, make_exe, make_sandbox_bin

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "copilot-runtime.sh"
RESOLVER = RUNTIME.parent / "resolve-python.sh"


def _fake_python(version: tuple[int, int]) -> str:
    """A fake python that answers the >=3.11 gate and echoes its argv."""
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
    sandbox = make_sandbox_bin(tmp_path)
    root = _setup_root(tmp_path)
    make_exe(root / ".venv" / "bin" / "python", _fake_python((3, 12)))
    target = root / "hello.py"
    target.write_text("# target script\n", encoding="utf-8")

    body = (
        f'source "{_runtime_path(root)}"\n'
        f'copilot_framework_python_script "{root}" "{target}" --flag value\n'
    )
    res = subprocess.run(
        ["bash", "-c", body], capture_output=True, text=True, env=hermetic_env(sandbox)
    )
    assert res.returncode == 0, res.stderr
    # The resolved venv interpreter received the script path + args as argv.
    assert res.stdout.strip() == f"ran:{target} --flag value"


def test_inline_happy_path_selects_venv_and_forwards_args(tmp_path: Path) -> None:
    sandbox = make_sandbox_bin(tmp_path)
    root = _setup_root(tmp_path)
    make_exe(root / ".venv" / "bin" / "python", _fake_python((3, 13)))

    body = f'source "{_runtime_path(root)}"\ncopilot_framework_python_inline "{root}" alpha beta\n'
    res = subprocess.run(
        ["bash", "-c", body], capture_output=True, text=True, env=hermetic_env(sandbox)
    )
    assert res.returncode == 0, res.stderr
    # Inline mode runs `python - <args>`; the stub echoes "- alpha beta".
    assert res.stdout.strip() == "ran:- alpha beta"


def _run_no_interpreter(root: Path, call: str, sandbox: Path) -> subprocess.CompletedProcess[str]:
    """Source the runtime and invoke ``call`` with NO interpreter reachable.

    ``copilot-runtime.sh`` runs under ``set -e``, so the function's nonzero
    return is captured via ``|| rc=$?`` and echoed. PATH is the hermetic
    sandbox (coreutils only, no python), so the resolver exhausts every
    branch and the functions honour their 127 fail contract — on any host,
    independent of the runner's ambient ``/usr/bin`` python.
    """
    body = f'source "{_runtime_path(root)}"\nrc=0\n{call} || rc=$?\necho "rc=$rc"\n'
    return subprocess.run(
        ["bash", "-c", body], capture_output=True, text=True, env=hermetic_env(sandbox)
    )


def test_script_returns_127_when_no_interpreter(tmp_path: Path) -> None:
    sandbox = make_sandbox_bin(tmp_path)
    root = _setup_root(tmp_path)
    target = root / "hello.py"
    target.write_text("# target script\n", encoding="utf-8")

    res = _run_no_interpreter(root, f'copilot_framework_python_script "{root}" "{target}"', sandbox)
    assert "rc=127" in res.stdout, (
        f"expected 127 fail contract, got {res.stdout!r} / {res.stderr!r}"
    )


def test_inline_returns_127_when_no_interpreter(tmp_path: Path) -> None:
    sandbox = make_sandbox_bin(tmp_path)
    root = _setup_root(tmp_path)

    res = _run_no_interpreter(root, f'copilot_framework_python_inline "{root}"', sandbox)
    assert "rc=127" in res.stdout, (
        f"expected 127 fail contract, got {res.stdout!r} / {res.stderr!r}"
    )
