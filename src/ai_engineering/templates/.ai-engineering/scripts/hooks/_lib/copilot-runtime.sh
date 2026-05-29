#!/usr/bin/env bash
# Shared runtime launcher for Copilot hook helpers.
# Resolves an explicit project runtime instead of inheriting host python/python3.
#
# spec-154: path resolution is delegated to the shared `resolve-python.sh`
# resolver so Copilot dispatch enforces the same >=3.11 gate as Claude
# Code and Codex. The public functions `copilot_framework_python_script`
# and `copilot_framework_python_inline` keep their signatures and the
# happy venv path unchanged (AC5); the only net-new behaviour is the
# >=3.11 gate inherited from the resolver.

set -euo pipefail

_copilot_runtime_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$_copilot_runtime_dir/resolve-python.sh"

copilot_framework_python_script() {
    local project_root="${1:?project_root required}"
    local script_path="${2:?script_path required}"
    shift 2

    local resolved=""
    if ! resolved="$(resolve_python "$project_root")"; then
        return 127
    fi

    if [ "$resolved" = "uv" ]; then
        # Pin uv to >=3.11 so the venv-less path cannot land on a <3.11 env.
        (cd "$project_root" && uv run --python '>=3.11' python "$script_path" "$@")
        return $?
    fi

    "$resolved" "$script_path" "$@"
    return $?
}

copilot_framework_python_inline() {
    local project_root="${1:?project_root required}"
    shift 1

    local resolved=""
    if ! resolved="$(resolve_python "$project_root")"; then
        return 127
    fi

    if [ "$resolved" = "uv" ]; then
        # Pin uv to >=3.11 so the venv-less path cannot land on a <3.11 env.
        (cd "$project_root" && uv run --python '>=3.11' python - "$@")
        return $?
    fi

    "$resolved" - "$@"
    return $?
}
