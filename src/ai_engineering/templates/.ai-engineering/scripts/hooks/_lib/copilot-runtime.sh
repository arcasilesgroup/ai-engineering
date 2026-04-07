#!/usr/bin/env bash
# Shared runtime launcher for Copilot hook helpers.
# Resolves an explicit project runtime instead of inheriting host python/python3.

set -euo pipefail

_copilot_framework_python_path() {
    local project_root="${1:?project_root required}"

    if [ -x "$project_root/.venv/bin/python" ]; then
        printf '%s\n' "$project_root/.venv/bin/python"
        return 0
    fi

    if [ -x "$project_root/.venv/Scripts/python.exe" ]; then
        printf '%s\n' "$project_root/.venv/Scripts/python.exe"
        return 0
    fi

    if [ -x "$project_root/.venv/Scripts/python" ]; then
        printf '%s\n' "$project_root/.venv/Scripts/python"
        return 0
    fi

    return 1
}

copilot_framework_python_script() {
    local project_root="${1:?project_root required}"
    local script_path="${2:?script_path required}"
    shift 2

    local venv_python=""
    if venv_python="$(_copilot_framework_python_path "$project_root")"; then
        "$venv_python" "$script_path" "$@"
        return $?
    fi

    if command -v uv >/dev/null 2>&1; then
        (cd "$project_root" && uv run python "$script_path" "$@")
        return $?
    fi

    return 127
}

copilot_framework_python_inline() {
    local project_root="${1:?project_root required}"
    shift 1

    local venv_python=""
    if venv_python="$(_copilot_framework_python_path "$project_root")"; then
        "$venv_python" - "$@"
        return $?
    fi

    if command -v uv >/dev/null 2>&1; then
        (cd "$project_root" && uv run python - "$@")
        return $?
    fi

    return 127
}
