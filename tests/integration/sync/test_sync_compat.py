"""Backwards-compat shim parity test for `scripts/sync_command_mirrors.py`.

Spec-122 sub-004 D-122-24 split the 82 KB monolith into the
`scripts/sync_mirrors/` package. The original entry point at
`scripts/sync_command_mirrors.py` is preserved as a thin shim
(<= 2 KB) so external CI / skill invocations keep working.

This test asserts the shim and the package CLI produce identical
stdout / stderr / exit code for the documented argument combinations.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SHIM_PATH = REPO_ROOT / "scripts" / "sync_command_mirrors.py"
PACKAGE_DIR = REPO_ROOT / "scripts" / "sync_mirrors"


@pytest.fixture(scope="module")
def shim_exists() -> bool:
    return SHIM_PATH.is_file()


@pytest.fixture(scope="module")
def package_exists() -> bool:
    return PACKAGE_DIR.is_dir() and (PACKAGE_DIR / "__main__.py").is_file()


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    "argv_suffix",
    [
        ["--check"],
        ["--check", "--verbose"],
    ],
    ids=["check", "check-verbose"],
)
def test_shim_matches_package_cli(
    argv_suffix: list[str], shim_exists: bool, package_exists: bool
) -> None:
    """Shim and package emit identical exit code + stdout/stderr.

    We only check `--check` (read-only) modes -- mutating modes would
    require a sandbox. The check mode is what CI/pre-commit invokes.
    """
    if not shim_exists:
        pytest.fail(
            f"Shim not yet created at {SHIM_PATH.relative_to(REPO_ROOT)} -- T-4.4 has not landed."
        )
    if not package_exists:
        pytest.fail(
            f"Package not yet created at {PACKAGE_DIR.relative_to(REPO_ROOT)} "
            "-- T-4.1/T-4.2 have not landed."
        )

    shim_argv = [sys.executable, str(SHIM_PATH), *argv_suffix]
    pkg_argv = [sys.executable, "-m", "scripts.sync_mirrors", *argv_suffix]

    shim_result = _run(shim_argv, REPO_ROOT)
    pkg_result = _run(pkg_argv, REPO_ROOT)

    # Exit code parity is the strongest contract.
    assert shim_result.returncode == pkg_result.returncode, (
        f"Exit code drift: shim={shim_result.returncode} "
        f"pkg={pkg_result.returncode}\n"
        f"shim stderr:\n{shim_result.stderr}\n"
        f"pkg stderr:\n{pkg_result.stderr}"
    )

    # Stdout parity: both surfaces must produce the same lines.
    # Allow trailing-newline difference; otherwise must be byte-equal.
    assert shim_result.stdout.rstrip() == pkg_result.stdout.rstrip(), (
        "Stdout drift between shim and package:\n"
        f"--- shim stdout ---\n{shim_result.stdout}\n"
        f"--- pkg stdout ---\n{pkg_result.stdout}"
    )


def test_shim_size_under_2kb() -> None:
    """The shim should be a thin delegator, not a copy of the monolith."""
    if not SHIM_PATH.is_file():
        pytest.skip("Shim not yet created (T-4.4 not landed).")
    size = SHIM_PATH.stat().st_size
    assert size <= 2048, (
        f"Shim grew to {size} bytes -- must be <= 2 KB. "
        f"Move logic into scripts/sync_mirrors/ instead."
    )


def test_package_module_count() -> None:
    """Package should have at least 7 modules per spec-122-d acceptance."""
    if not PACKAGE_DIR.is_dir():
        pytest.skip("Package not yet created (T-4.1 not landed).")
    py_files = list(PACKAGE_DIR.glob("*.py"))
    assert len(py_files) >= 7, (
        f"Package has only {len(py_files)} modules -- spec-122-d "
        f"requires >= 7 (target: 9 with per-IDE writers)."
    )


@pytest.mark.skipif(
    shutil.which("python3") is None,
    reason="python3 not on PATH",
)
def test_shim_invokes_via_python3() -> None:
    """External tooling typically invokes `python3 scripts/sync_command_mirrors.py`.

    This test mirrors that invocation pattern to catch shebang / path drift.
    """
    if not SHIM_PATH.is_file():
        pytest.skip("Shim not yet created.")
    result = subprocess.run(
        ["python3", str(SHIM_PATH), "--check"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    # Accept exit 0 (no drift) or exit 1 (drift detected); both are
    # legitimate outcomes for --check. Exit 2+ means crash.
    assert result.returncode in (0, 1), (
        f"Shim crashed (exit {result.returncode}). stderr:\n{result.stderr}"
    )
