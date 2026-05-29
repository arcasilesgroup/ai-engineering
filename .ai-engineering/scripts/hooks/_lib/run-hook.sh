#!/usr/bin/env bash
# spec-154 — transparent launcher for IDE hook dispatch.
#
# Usage: run-hook.sh <script.py> [args...]
#
# Resolves a >=3.11 interpreter (via resolve-python.sh) and execs the
# PASSED script under it. The exec is transparent: the process that runs
# is the `.py` arg itself, NOT this launcher — `run_hook_safe` verifies
# integrity via the script's own `__file__`, so the launcher must never
# insert itself into argv.
#
# When no >=3.11 interpreter exists, it prints exactly one stderr line
# and exits 0 (hooks are fail-open / advisory on the hot path).

set -uo pipefail

_run_hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$_run_hook_dir/resolve-python.sh"

# Resolve the project root: prefer the IDE-provided var, else walk up
# from cwd to the nearest directory containing `.ai-engineering`.
_resolve_root() {
    if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
        printf '%s\n' "$CLAUDE_PROJECT_DIR"
        return 0
    fi
    local dir
    dir="$(pwd)"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.ai-engineering" ]; then
            printf '%s\n' "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    printf '%s\n' "$(pwd)"
}

root="$(_resolve_root)"

py=""
if py="$(resolve_python "$root")"; then
    :
else
    printf '%s\n' \
        "ai-engineering hooks require Python >=3.11; activate .venv or install 3.11+" >&2
    exit 0
fi

if [ "$py" = "uv" ]; then
    # Pin the uv-resolved interpreter to >=3.11 so the venv-less path
    # cannot silently land on a <3.11 env (the exact ImportError this
    # spec prevents). uv honours the version request via --python.
    exec uv run --python '>=3.11' --project "$root" python "$@"
fi

exec "$py" "$@"
