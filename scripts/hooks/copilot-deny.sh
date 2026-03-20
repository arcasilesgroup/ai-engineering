#!/usr/bin/env bash
# Copilot preToolUse deny-list hook.
# Blocks dangerous CLI operations matching the project deny-list.
# Fail-open: exit 0 on any error — never blocks the IDE.
#
# Input:  JSON on stdin (Copilot preToolUse event)
# Output: JSON on stdout only when denying; silent when allowing
#
# Deny patterns (13):
#   1.  rm -rf with dangerous targets (/, *, ~, .)
#   2.  git push --force
#   3.  git push -f
#   4.  git reset --hard
#   5.  git checkout -- .
#   6.  git checkout .
#   7.  git restore .
#   8.  git clean -f
#   9.  git commit --no-verify
#   10. git push --no-verify
#   11. git merge --no-verify
#   12. git rebase --no-verify
#   13. any command with --no-verify flag (catch-all)

set -euo pipefail

# Fail-open: any unhandled error allows the operation
trap 'exit 0' ERR

# ── Input parsing ──────────────────────────────────────────────

INPUT=$(cat) || exit 0
command -v jq >/dev/null 2>&1 || exit 0

TOOL_NAME=$(jq -r '.toolName // empty' 2>/dev/null <<< "$INPUT") || exit 0
[[ "${TOOL_NAME:-}" == "bash" ]] || exit 0

COMMAND=$(jq -r '
    if (.toolArgs | type) == "string" then
        (.toolArgs | fromjson | .command // empty)
    else
        (.toolArgs.command // empty)
    end' 2>/dev/null <<< "$INPUT") || exit 0
[[ -n "${COMMAND:-}" ]] || exit 0

# ── Helpers ────────────────────────────────────────────────────

deny() {
    local reason="$1"
    printf '{"permissionDecision":"deny","permissionDecisionReason":"Blocked: %s"}\n' "$reason"
    exit 0
}

# Remove content inside quotes to prevent false-positive flag detection.
# E.g. git commit -m "about --no-verify" → git commit -m
strip_quoted_strings() {
    sed -E "s/\"[^\"]*\"//g; s/'[^']*'//g" <<< "$1"
}

# Return 0 (true) when the rm target is a broad/destructive path.
is_dangerous_rm_target() {
    local t="$1"
    [[ "$t" == "/" ]]  && return 0
    [[ "$t" == "/*" ]] && return 0
    [[ "$t" == "*" ]]  && return 0
    [[ "$t" == "~" ]]  && return 0
    # shellcheck disable=SC2088
    [[ "$t" == "~/" ]] && return 0
    [[ "$t" == "." ]]  && return 0
    [[ "$t" == "./" ]] && return 0
    [[ "$t" == ".." ]] && return 0
    return 1
}

# ── Deny checks ───────────────────────────────────────────────

# Pattern 1: rm -rf with dangerous targets
# Block: rm -rf /, rm -rf *, rm -rf ~
# Allow: rm -rf node_modules/, rm -rf dist/, rm -rf .cache/
check_rm_rf() {
    local cmd="$1"

    # Combined flags (-rf, -fr, -rfv, etc.) with optional -- separator
    local re='rm[[:space:]]+(-[[:alpha:]]*r[[:alpha:]]*f[[:alpha:]]*|-[[:alpha:]]*f[[:alpha:]]*r[[:alpha:]]*)[[:space:]]+(--[[:space:]]+)?([^[:space:]]+)'
    if [[ "$cmd" =~ $re ]]; then
        if is_dangerous_rm_target "${BASH_REMATCH[3]}"; then
            deny "destructive operation 'rm -rf ${BASH_REMATCH[3]}'"
        fi
    fi

    # Separate flags: -r ... -f
    local re_rf='rm[[:space:]]+-[[:alpha:]]*r[[:alpha:]]*[[:space:]]+-[[:alpha:]]*f[[:alpha:]]*[[:space:]]+(--[[:space:]]+)?([^[:space:]]+)'
    if [[ "$cmd" =~ $re_rf ]]; then
        if is_dangerous_rm_target "${BASH_REMATCH[2]}"; then
            deny "destructive operation 'rm -rf ${BASH_REMATCH[2]}'"
        fi
    fi

    # Separate flags: -f ... -r
    local re_fr='rm[[:space:]]+-[[:alpha:]]*f[[:alpha:]]*[[:space:]]+-[[:alpha:]]*r[[:alpha:]]*[[:space:]]+(--[[:space:]]+)?([^[:space:]]+)'
    if [[ "$cmd" =~ $re_fr ]]; then
        if is_dangerous_rm_target "${BASH_REMATCH[2]}"; then
            deny "destructive operation 'rm -rf ${BASH_REMATCH[2]}'"
        fi
    fi
}

# Patterns 2-3: git push --force / -f
# Allows --force-with-lease and --force-if-includes (safe variants).
check_git_force_push() {
    local cmd="$1"
    local re_force='git[[:space:]]+(.*[[:space:]])?push[[:space:]]+(.*[[:space:]])?--force([[:space:]]|$)'
    local re_f='git[[:space:]]+(.*[[:space:]])?push[[:space:]]+(.*[[:space:]])?-f([[:space:]]|$)'
    if [[ "$cmd" =~ $re_force ]] || [[ "$cmd" =~ $re_f ]]; then
        deny "force push 'git push --force'"
    fi
}

# Pattern 4: git reset --hard
check_git_reset_hard() {
    local cmd="$1"
    local re='git[[:space:]]+(.*[[:space:]])?reset[[:space:]]+(.*[[:space:]])?--hard([[:space:]]|$)'
    if [[ "$cmd" =~ $re ]]; then
        deny "destructive reset 'git reset --hard'"
    fi
}

# Patterns 5-6: git checkout [--] .
check_git_checkout_dot() {
    local cmd="$1"
    local re_dd='git[[:space:]]+(.*[[:space:]])?checkout[[:space:]]+(.*[[:space:]])?--[[:space:]]+\.([[:space:]]|$)'
    local re_dot='git[[:space:]]+(.*[[:space:]])?checkout[[:space:]]+(.*[[:space:]])?\.([[:space:]]|$)'
    if [[ "$cmd" =~ $re_dd ]] || [[ "$cmd" =~ $re_dot ]]; then
        deny "destructive checkout 'git checkout .'"
    fi
}

# Pattern 7: git restore .
check_git_restore_dot() {
    local cmd="$1"
    local re='git[[:space:]]+(.*[[:space:]])?restore[[:space:]]+(.*[[:space:]])?\.([[:space:]]|$)'
    if [[ "$cmd" =~ $re ]]; then
        deny "destructive restore 'git restore .'"
    fi
}

# Pattern 8: git clean -f
check_git_clean_f() {
    local cmd="$1"
    local re='git[[:space:]]+(.*[[:space:]])?clean[[:space:]]+(.*[[:space:]])?-[[:alpha:]]*f[[:alpha:]]*([[:space:]]|$)'
    if [[ "$cmd" =~ $re ]]; then
        deny "destructive clean 'git clean -f'"
    fi
}

# Patterns 9-13: --no-verify as a standalone flag (not inside quoted strings)
check_no_verify() {
    local cmd="$1"
    local stripped
    stripped=$(strip_quoted_strings "$cmd") || return
    if [[ "$stripped" =~ (^|[[:space:]])--no-verify([[:space:]]|$) ]]; then
        deny "verification bypass '--no-verify'"
    fi
}

# ── Execute all checks ────────────────────────────────────────

check_rm_rf "$COMMAND"
check_git_force_push "$COMMAND"
check_git_reset_hard "$COMMAND"
check_git_checkout_dot "$COMMAND"
check_git_restore_dot "$COMMAND"
check_git_clean_f "$COMMAND"
check_no_verify "$COMMAND"

# All checks passed — allow the operation
exit 0
