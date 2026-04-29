"""spec-114 Phase 1 T-1.2 — assert _lib/copilot-common.ps1 exposes 4 functions.

D-114-01 contract (PowerShell parity with copilot-common.sh):
  - Read-StdinPayload   (read_stdin_payload)
  - Emit-Event          (emit_event)
  - Should-FailOpen     (should_fail_open)
  - Log-ToStderr        (log_to_stderr)

PowerShell function names use Verb-Noun convention. The test allows any
of: kebab-case, Verb-Noun, or snake_case form, so the lib author can
pick the most idiomatic spelling.

Sealed: PowerShell uses Get-Content + ConvertFrom-Json + ConvertTo-Json
only (D-114-01).

Test strategy: prefer pwsh subprocess to introspect with `Get-Command`;
fall back to source-grep when pwsh isn't on the runner (CI macOS rarely
ships pwsh by default).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
LIB_PATH = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "copilot-common.ps1"

# Map from canonical (snake_case) name to acceptable PowerShell aliases.
_FUNCTION_ALIASES: dict[str, tuple[str, ...]] = {
    "read_stdin_payload": ("Read-StdinPayload", "Read-CopilotStdinPayload", "read_stdin_payload"),
    "emit_event": ("Emit-Event", "Emit-CopilotEvent", "emit_event"),
    "should_fail_open": ("Should-FailOpen", "Invoke-FailOpen", "should_fail_open"),
    "log_to_stderr": ("Log-ToStderr", "Write-StderrLog", "log_to_stderr"),
}


@pytest.fixture(scope="module")
def pwsh_path() -> str | None:
    return shutil.which("pwsh")


def test_lib_file_exists() -> None:
    assert LIB_PATH.is_file(), f"missing shared lib: {LIB_PATH}"


def test_lib_exports_required_functions(pwsh_path: str | None) -> None:
    """Each required function must be defined in the lib (any allowed alias)."""
    if pwsh_path is not None:
        # Preferred path: ask pwsh once to confirm Get-Command sees every
        # required function. A single process avoids cold-start flake on
        # Windows CI where PowerShell startup can exceed a tight per-alias
        # timeout under the Python 3.11 unit matrix.
        probe_lines = [f". '{LIB_PATH}'", "$missing = @()"]
        for canonical, aliases in _FUNCTION_ALIASES.items():
            checks = " -or ".join(
                f"(Get-Command '{name}' -ErrorAction SilentlyContinue)" for name in aliases
            )
            probe_lines.append(f"if (-not ({checks})) {{ $missing += '{canonical}' }}")
        probe_lines.extend(
            [
                "if ($missing.Count -gt 0) {",
                "  Write-Error ('Missing functions: ' + ($missing -join ', '))",
                "  exit 1",
                "}",
                "exit 0",
            ]
        )
        get_command_probe = "; ".join(probe_lines)
        result = subprocess.run(
            [pwsh_path, "-NoProfile", "-NonInteractive", "-Command", get_command_probe],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"required function aliases missing from {LIB_PATH.name}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
        return

    # Fallback: source grep when pwsh is unavailable.
    text = LIB_PATH.read_text(encoding="utf-8")
    for canonical, aliases in _FUNCTION_ALIASES.items():
        pattern = re.compile(
            r"^\s*function\s+(?:" + "|".join(re.escape(a) for a in aliases) + r")\b",
            re.IGNORECASE | re.MULTILINE,
        )
        assert pattern.search(text), (
            f"function `{canonical}` (aliases={aliases}) not declared in {LIB_PATH.name}; "
            "expected a `function <name>` declaration."
        )


def test_lib_uses_only_sealed_dependencies() -> None:
    """Sealed contract: no external commands beyond PowerShell builtins.

    Per D-114-01: `_lib/copilot-common.ps1` must NOT shell out to python,
    perl, awk, sed, etc. for core paths.
    """
    assert LIB_PATH.is_file(), f"missing shared lib: {LIB_PATH}"
    text = LIB_PATH.read_text(encoding="utf-8")
    forbidden = (
        "& python ",
        "& python3 ",
        "& perl ",
        "& ruby ",
        "Invoke-Expression",
    )
    for token in forbidden:
        assert token not in text, (
            f"sealed-deps violation: `{token}` appears in {LIB_PATH.name}; "
            "D-114-01 requires PowerShell builtins only."
        )
