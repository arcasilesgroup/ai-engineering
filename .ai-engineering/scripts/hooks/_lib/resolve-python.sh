#!/usr/bin/env bash
# spec-154 — shared >=3.11 interpreter resolver for IDE hook dispatch.
#
# The hook libraries legitimately require Python >=3.11 (datetime.UTC,
# etc.). Bare `python3` on a host may resolve to <3.11 (e.g. macOS system
# 3.9.6), which raises `ImportError: cannot import name 'UTC'`. This
# resolver SELECTS a >=3.11 interpreter; it does NOT shim the hook
# libraries for 3.9 (forbidden — CONSTITUTION Prohibition 4).
#
# Stdlib + bash only. Source this file and call:
#     resolve_python "$project_root"
# It prints the resolved interpreter (or the literal `uv` sentinel) on
# stdout and returns 0, or returns 1 when no >=3.11 interpreter exists.

set -uo pipefail

# Resolution order is hot-path driven (deviates from spec D-154-03 which
# listed `uv` before the named interpreters):
#   1. cached resolution (instant re-read)
#   2. project venv (no spawn; version implied by the venv)
#   3. named python3.13 / 3.12 / 3.11 (version-known by name; no spawn)
#   4. `uv` sentinel — retained as a fallback (NOT dropped) to preserve
#      Copilot's venv-less path (AC5); `uv run` spawns and is hot-path
#      hostile, so it ranks below named interpreters.
#   5. bare `python3` ONLY when it gates >=3.11 (one spawn, last resort).
resolve_python() {
    local root="${1:?project_root required}"
    local cache="$root/.ai-engineering/runtime/resolved-python.txt"

    # 1. Cache read — honour a still-executable cached interpreter.
    # `read` returns nonzero at EOF-without-delimiter (a newline-less
    # cache) even though it still populated `cached`; ignore that exit
    # status so such a cache is honoured. Behaviour is identical for the
    # normal newline-terminated cache written by this resolver.
    if [ -f "$cache" ]; then
        local cached=""
        IFS= read -r cached < "$cache" 2>/dev/null || true
        if [ -n "$cached" ] && [ -x "$cached" ]; then
            printf '%s\n' "$cached"
            return 0
        fi
    fi

    local resolved=""

    # 2. Project virtualenv (POSIX + Windows layouts).
    if [ -x "$root/.venv/bin/python" ]; then
        resolved="$root/.venv/bin/python"
    elif [ -x "$root/.venv/Scripts/python.exe" ]; then
        resolved="$root/.venv/Scripts/python.exe"
    elif [ -x "$root/.venv/Scripts/python" ]; then
        resolved="$root/.venv/Scripts/python"
    fi

    # 3. Named interpreters — version-known, no spawn. Prefer higher.
    if [ -z "$resolved" ]; then
        local candidate=""
        for name in python3.13 python3.12 python3.11; do
            if candidate="$(command -v "$name" 2>/dev/null)" && [ -n "$candidate" ]; then
                resolved="$candidate"
                break
            fi
        done
    fi

    # 4. uv sentinel — preserves the venv-less Copilot path (AC5).
    if [ -z "$resolved" ]; then
        if command -v uv >/dev/null 2>&1 && [ -f "$root/pyproject.toml" ]; then
            printf '%s\n' "uv"
            return 0
        fi
    fi

    # 5. Bare python3 — last resort, gated on >=3.11 via a single spawn.
    if [ -z "$resolved" ]; then
        if command -v python3 >/dev/null 2>&1 \
            && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
            resolved="$(command -v python3)"
        fi
    fi

    if [ -z "$resolved" ]; then
        return 1
    fi

    # Best-effort atomic cache write — never fail the function on a write
    # error (read-only runtime dir, race, etc.).
    local cache_dir="$root/.ai-engineering/runtime"
    if mkdir -p "$cache_dir" 2>/dev/null; then
        local tmp=""
        if tmp="$(mktemp "$cache_dir/resolved-python.XXXXXX" 2>/dev/null)"; then
            if printf '%s\n' "$resolved" >"$tmp" 2>/dev/null; then
                mv -f "$tmp" "$cache" 2>/dev/null || rm -f "$tmp" 2>/dev/null
            else
                rm -f "$tmp" 2>/dev/null
            fi
        fi
    fi

    printf '%s\n' "$resolved"
    return 0
}
