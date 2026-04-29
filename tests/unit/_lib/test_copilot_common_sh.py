"""spec-114 Phase 1 T-1.1 — assert _lib/copilot-common.sh exposes 4 functions.

D-114-01 contract:
  - read_stdin_payload  -- read JSON from stdin into $PAYLOAD
  - emit_event          -- append a canonical NDJSON line to framework-events
  - should_fail_open    -- exit 0 wrapper for fail-open hooks
  - log_to_stderr       -- structured stderr logger (no PII)

Sealed: shell uses Bash builtins + jq only (D-114-01).

The lib lives at:
  .ai-engineering/scripts/hooks/_lib/copilot-common.sh

Test strategy: function discovery via `bash -c 'source <lib>; type <fn>'`.
We do not invoke the functions here — that's the integration test contract.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
LIB_PATH = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "copilot-common.sh"

REQUIRED_FUNCTIONS = (
    "read_stdin_payload",
    "emit_event",
    "should_fail_open",
    "log_to_stderr",
)


@pytest.fixture(scope="module")
def bash_path() -> str:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash not available on this host")
    return bash


def test_lib_file_exists() -> None:
    assert LIB_PATH.is_file(), f"missing shared lib: {LIB_PATH}"


@pytest.mark.parametrize("fn", REQUIRED_FUNCTIONS)
def test_lib_exports_required_functions(bash_path: str, fn: str) -> None:
    """Each required function must be defined after sourcing the lib.

    We use `type <fn>` rather than `declare -F` so the failure message is
    actionable: bash prints the exact function body or `not found`.
    """
    cmd = ["env", "-i", bash_path, "-c", f"set -e; source '{LIB_PATH}'; type {fn}"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"function `{fn}` not exported by {LIB_PATH.name}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "is a function" in result.stdout, (
        f"`{fn}` exists but is not a shell function: {result.stdout}"
    )


def test_lib_uses_only_sealed_dependencies() -> None:
    """Sealed contract: no external commands beyond Bash builtins + jq.

    Per D-114-01: `_lib/copilot-common.sh` must NOT shell out to python,
    perl, awk, sed, etc. for core paths. We allow `jq` (canonical JSON)
    and `cat` (POSIX builtin alias). The check is heuristic — line-level
    grep for known offenders.
    """
    assert LIB_PATH.is_file(), f"missing shared lib: {LIB_PATH}"
    text = LIB_PATH.read_text(encoding="utf-8")
    forbidden = ("python ", "python3 ", "perl ", "ruby ", "node ", " awk ")
    for token in forbidden:
        assert token not in text, (
            f"sealed-deps violation: `{token.strip()}` appears in {LIB_PATH.name}; "
            "D-114-01 requires Bash builtins + jq only."
        )
