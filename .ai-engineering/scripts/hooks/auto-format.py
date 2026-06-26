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
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin, read_stdin
from _lib.hook_common import run_hook_safe

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

# spec-139 M5.T4: per-process debounce. The PostToolUse hook fires after
# every Edit/Write/MultiEdit, so rapid back-to-back edits to the same
# file otherwise pay the full formatter cost N times. We track the wall-
# clock time of the last format per absolute file path and short-circuit
# when the next invocation lands inside the debounce window. Default 1 s;
# overridable via ``AIENG_AUTOFORMAT_DEBOUNCE_SEC`` so test suites can
# tighten or widen the window deterministically.
_AUTOFORMAT_DEBOUNCE_DEFAULT_SEC = 1.0
_LAST_FORMAT_TIMES: dict[str, float] = {}


def _autoformat_debounce_window_sec() -> float:
    """Return the debounce window in seconds (env-overridable).

    Reads ``AIENG_AUTOFORMAT_DEBOUNCE_SEC`` per call (cheap env lookup).
    Negative / unparseable values fall back to the 1 s default so a stray
    env var never disables the debounce silently.
    """
    raw = (os.environ.get("AIENG_AUTOFORMAT_DEBOUNCE_SEC") or "").strip()
    if not raw:
        return _AUTOFORMAT_DEBOUNCE_DEFAULT_SEC
    try:
        value = float(raw)
    except ValueError:
        return _AUTOFORMAT_DEBOUNCE_DEFAULT_SEC
    if value < 0:
        return _AUTOFORMAT_DEBOUNCE_DEFAULT_SEC
    return value


def _should_debounce(file_path: str, *, now: float | None = None) -> bool:
    """Return True when ``file_path`` was formatted within the debounce window.

    Lookup key is the absolute path so a relative-vs-absolute mismatch
    does NOT cause a false debounce. ``now`` is parameterised so tests
    can drive deterministic windows without monkey-patching ``time``.
    Returns False when the path has never been formatted or the window
    setting is zero (explicit disable).
    """
    window = _autoformat_debounce_window_sec()
    if window <= 0:
        return False
    last = _LAST_FORMAT_TIMES.get(file_path)
    if last is None:
        return False
    reference = now if now is not None else time.monotonic()
    return (reference - last) < window


def _record_format(file_path: str, *, now: float | None = None) -> None:
    """Stamp the per-process last-format map for ``file_path``."""
    _LAST_FORMAT_TIMES[file_path] = now if now is not None else time.monotonic()


def _is_under_pinned_scripts(path: Path) -> bool:
    """True when ``path`` lives under ``.ai-engineering/scripts/``.

    Those files are sha256-pinned in ``hooks-manifest.json`` for integrity
    (spec-179 D-179-01), so they must stay byte-stable. Reformatting them with
    the consumer repo's ruff width would reflow them and break hook integrity
    for the whole tree -- so this hook skips them. ``as_posix`` normalizes
    separators so the match holds for absolute/relative/Windows inputs.
    """
    return ".ai-engineering/scripts/" in path.as_posix()


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


def _maybe_restage_after_format(project_root: Path) -> str | None:
    """Best-effort re-stage of ``S_pre & M_post`` after the formatter ran.

    spec-105 D-105-09: the hook captures S_pre once per invocation, runs
    the formatter, and re-stages exactly the intersection.

    spec-147 G1 T-1.11/1.12: a re-stage failure is no longer swallowed
    silently. Re-staging is NOT a security gate, so the hook stays
    non-blocking (it never breaks the user's edit flow), but it returns a
    one-line warning string that ``main`` surfaces via ``hookSpecificOutput``
    so the operator can see that the index may not reflect the formatted
    bytes. Returns ``None`` on the happy path (and when there is nothing
    staged to re-stage).
    """
    try:
        s_pre = capture_staged_set(project_root)
    except Exception as exc:
        return (
            "[auto-format] could not read the staged set after formatting "
            f"({type(exc).__name__}); the index may not reflect formatter output"
        )
    if not s_pre:
        return None
    try:
        restage_intersection(project_root, s_pre)
    except Exception as exc:
        return (
            "[auto-format] failed to re-stage formatted files "
            f"({type(exc).__name__}); run `git add` to stage the formatted bytes"
        )
    return None


def _emit_hook_warning(event_name: str, message: str, data: dict) -> None:
    """Emit a visible, non-blocking ``hookSpecificOutput`` warning.

    Mirrors the runtime-guard contract: Claude Code reads exactly one JSON
    object per hook, so when we have something to surface we write the
    ``hookSpecificOutput`` envelope INSTEAD of the bare stdin passthrough.
    """
    try:
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": event_name,
                        "additionalContext": message,
                    }
                },
                separators=(",", ":"),
            )
        )
        sys.stdout.flush()
    except Exception:
        passthrough_stdin(data)


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

    # spec-179 D-179-01: never reformat sha-pinned framework hook scripts.
    # They are byte-locked in hooks-manifest.json; reformatting with the
    # consumer's ruff width would break hook integrity for the whole tree.
    resolved = file_path_obj.resolve() if file_path_obj.exists() else file_path_obj
    if _is_under_pinned_scripts(resolved):
        passthrough_stdin(data)
        return

    formatter_fn = _EXTENSION_FORMATTERS.get(extension)
    if formatter_fn is None:
        passthrough_stdin(data)
        return

    file_dir = file_path_obj.parent if file_path_obj.parent.is_dir() else Path.cwd()
    project_root = _find_project_root(file_dir)

    # spec-139 M5.T4: debounce repeated formats of the same path inside the
    # 1 s default window. Lookup key is the absolute path so relative-vs-
    # absolute callsites can never produce a false debounce. When debounced
    # we still pass stdin through so hook chaining stays intact.
    abs_path = str(file_path_obj.resolve()) if file_path_obj.exists() else file_path
    if _should_debounce(abs_path):
        passthrough_stdin(data)
        return

    formatter_fn(file_path, project_root)
    _record_format(abs_path)

    # spec-105 D-105-09: re-stage the safe intersection after formatting.
    # The formatter may have rewritten the file; the user's staged commit
    # should reflect the formatted state without leaking unrelated files.
    # spec-147 G1 T-1.11/1.12: a re-stage failure is surfaced as a visible
    # (non-blocking) warning instead of being swallowed.
    warning = _maybe_restage_after_format(project_root)
    if warning is not None:
        _emit_hook_warning("PostToolUse", warning, data)
        return

    passthrough_stdin(data)


if __name__ == "__main__":
    run_hook_safe(
        main, component="hook.auto-format", hook_kind="post-tool-use", script_path=__file__
    )
