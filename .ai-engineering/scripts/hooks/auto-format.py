#!/usr/bin/env python3
"""PostToolUse hook: auto-format files after Edit, Write, or MultiEdit.

Detects language by file extension and runs the appropriate formatter.
All errors silently swallowed -- exit 0 always.

spec-105 D-105-09: after the formatter rewrites a file, the hook calls
the shared ``policy/auto_stage.py`` primitive to re-stage exactly the
``S_pre & M_post`` intersection so the user's commit reflects the
formatted state. The intersection is set-strict; never a superset.
"""

import contextlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin, read_stdin

# spec-105 D-105-09: best-effort import of the shared auto-stage utility.
# When the framework package isn't on sys.path (eg the hook running from a
# stripped-down context) we fall back to a no-op so the hook never breaks
# the user's edit flow.
with contextlib.suppress(Exception):
    from ai_engineering.policy.auto_stage import (
        capture_staged_set,
        restage_intersection,
    )

_FORMAT_TOOLS = {"Edit", "Write", "MultiEdit"}
_FORMATTER_TIMEOUT = 15

_PROJECT_ROOT_MARKERS = {
    "package.json",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
}

_SOLUTION_GLOB = "*.sln"


def _find_project_root(file_dir: Path) -> Path:
    """Walk up from file_dir to find the nearest project root."""
    current = file_dir
    for _ in range(30):
        for marker in _PROJECT_ROOT_MARKERS:
            if (current / marker).exists():
                return current
        for sln in current.glob(_SOLUTION_GLOB):
            if sln.is_file():
                return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return file_dir


def _run_formatter(cmd: list[str], cwd: str) -> None:
    """Run a formatter command with timeout, swallowing all errors."""
    with contextlib.suppress(Exception):
        subprocess.run(
            cmd,
            capture_output=True,
            timeout=_FORMATTER_TIMEOUT,
            cwd=cwd,
        )


def _check_tool_available(tool: str) -> bool:
    """Check if a command-line tool is available."""
    try:
        result = subprocess.run(
            [tool, "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _find_local_binary(project_root: Path, binary_name: str) -> str | None:
    """Find a binary in node_modules/.bin/ relative to project root."""
    local_bin = project_root / "node_modules" / ".bin" / binary_name
    if local_bin.exists():
        return str(local_bin)
    return None


def _detect_js_formatter(project_root: Path) -> str | None:
    """Detect whether to use biome or prettier for JS/TS files."""
    if (project_root / "biome.json").exists() or (project_root / "biome.jsonc").exists():
        return "biome"
    prettier_markers = [
        ".prettierrc",
        ".prettierrc.json",
        ".prettierrc.yml",
        ".prettierrc.yaml",
        ".prettierrc.js",
        ".prettierrc.cjs",
        ".prettierrc.mjs",
        ".prettierrc.toml",
        "prettier.config.js",
        "prettier.config.cjs",
        "prettier.config.mjs",
    ]
    for marker in prettier_markers:
        if (project_root / marker).exists():
            return "prettier"
    if (project_root / "package.json").exists():
        try:
            with open(project_root / "package.json", encoding="utf-8") as f:
                pkg = json.load(f)
            if "prettier" in pkg:
                return "prettier"
        except Exception:
            pass
    return "prettier"


def _format_python(file_path: str, project_root: Path) -> None:
    """Format a Python file using ruff."""
    if not _check_tool_available("ruff"):
        return
    _run_formatter(["ruff", "format", file_path], cwd=str(project_root))


def _format_js_ts(file_path: str, project_root: Path) -> None:
    """Format a JS/TS file using biome or prettier."""
    formatter = _detect_js_formatter(project_root)

    if formatter == "biome":
        local_bin = _find_local_binary(project_root, "biome")
        if local_bin:
            _run_formatter([local_bin, "format", "--write", file_path], cwd=str(project_root))
        else:
            _run_formatter(["npx", "biome", "format", "--write", file_path], cwd=str(project_root))
    else:
        local_bin = _find_local_binary(project_root, "prettier")
        if local_bin:
            _run_formatter([local_bin, "--write", file_path], cwd=str(project_root))
        else:
            _run_formatter(["npx", "prettier", "--write", file_path], cwd=str(project_root))


def _format_go(file_path: str, project_root: Path) -> None:
    """Format a Go file using gofmt."""
    _run_formatter(["gofmt", "-w", file_path], cwd=str(project_root))


def _format_rust(file_path: str, project_root: Path) -> None:
    """Format a Rust file using rustfmt."""
    _run_formatter(["rustfmt", file_path], cwd=str(project_root))


def _format_csharp(file_path: str, project_root: Path) -> None:
    """Format a C# file using dotnet format."""
    _run_formatter(["dotnet", "format", "--include", file_path], cwd=str(project_root))


_EXTENSION_FORMATTERS = {
    ".py": _format_python,
    ".ts": _format_js_ts,
    ".tsx": _format_js_ts,
    ".js": _format_js_ts,
    ".jsx": _format_js_ts,
    ".go": _format_go,
    ".rs": _format_rust,
    ".cs": _format_csharp,
}


def _maybe_restage_after_format(project_root: Path) -> None:
    """Best-effort re-stage of ``S_pre & M_post`` after the formatter ran.

    spec-105 D-105-09: the hook captures S_pre once per invocation, runs
    the formatter, and re-stages exactly the intersection. Errors are
    silently swallowed so the hook never breaks the user's edit flow.
    """
    try:
        s_pre = capture_staged_set(project_root)
    except Exception:
        return
    if not s_pre:
        return
    with contextlib.suppress(Exception):
        restage_intersection(project_root, s_pre)


def main() -> None:
    data = read_stdin()
    tool_name = data.get("tool_name", "")

    if tool_name not in _FORMAT_TOOLS:
        passthrough_stdin(data)
        return

    tool_input = data.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, TypeError):
            tool_input = {}

    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
    if not file_path:
        passthrough_stdin(data)
        return

    file_path_obj = Path(file_path)
    extension = file_path_obj.suffix.lower()

    formatter_fn = _EXTENSION_FORMATTERS.get(extension)
    if formatter_fn is None:
        passthrough_stdin(data)
        return

    file_dir = file_path_obj.parent if file_path_obj.parent.is_dir() else Path.cwd()
    project_root = _find_project_root(file_dir)

    formatter_fn(file_path, project_root)

    # spec-105 D-105-09: re-stage the safe intersection after formatting.
    # The formatter may have rewritten the file; the user's staged commit
    # should reflect the formatted state without leaking unrelated files.
    _maybe_restage_after_format(project_root)

    passthrough_stdin(data)


if __name__ == "__main__":
    with contextlib.suppress(Exception):
        main()
    sys.exit(0)
