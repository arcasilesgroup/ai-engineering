# Shell Script Best Practices

- Use idiomatic bash patterns and features whenever possible

**Script safety:**

- Always use `set -e` to exit on errors
- Use `set -u` to catch undefined variables
- Use `set -o pipefail` to catch errors in pipelines
- Quote variables to prevent word splitting: `"$var"`

**Shebang patterns:**

- Use `#!/usr/bin/env bash` for scripts requiring bash 4.0+ features
  (associative arrays, `${var,,}`, etc.)
- Use `#!/bin/bash` for scripts compatible with older bash (3.2+)
- Never use `#!/bin/sh` for bash-specific features
- Avoid bashisms if targeting POSIX sh
- Check script with `shellcheck` for common issues

**Why `#!/usr/bin/env bash`:**

- Finds bash in PATH (may be newer version on macOS where `/bin/bash` is 3.2)
- Required for associative arrays (`declare -A`) which need bash 4.0+
- Better for systems with custom bash installations

**Bash 4.0+ features:**

- Associative arrays: `declare -A map; map[key]=value`
- Case modification: `${var,,}` (lowercase), `${var^^}` (uppercase)
- `**` globbing: `shopt -s globstar; for f in **/*.sh`

## Portability (macOS vs Linux)

**Commands that differ:**

- `date +%s%N` - nanoseconds not supported on BSD date (outputs literal `%N`)
- `md5sum` doesn't exist on macOS (use `md5` or `openssl md5`)
- `sed -i` requires empty string on macOS: `sed -i '' 's/old/new/'`
- `grep -P` (Perl regex) not available on macOS BSD grep
- `readlink -f` not available on macOS (use `realpath` or custom function)

**Portable alternatives:**

```bash
# Random hex (instead of: date +%s%N | md5sum | head -c 8)
printf '%04x%04x' $RANDOM $RANDOM

# In-place sed that works on both
sed -i.bak 's/old/new/' file && rm file.bak

# MD5 hash portable
if command -v md5sum >/dev/null 2>&1; then
    echo "test" | md5sum | cut -d' ' -f1
else
    echo "test" | md5 -q
fi
```

## Error Handling

**Defensive scripting:**

- Check command exit codes explicitly when needed
- Use `command -v` instead of `which` for checking commands
- Provide meaningful error messages with context
- Use `trap` for cleanup on exit

**Pattern:**

```bash
if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq is required but not installed" >&2
    exit 1
fi
```bash

## Variable Handling

**Critical patterns:**

- Always quote variables: `"$variable"`
- Use `${var}` for clarity when concatenating
- Use `${var:-default}` for default values
- Use `${var:?error}` to require variables
- Avoid global variables - pass parameters to functions

**Anti-patterns:**

- Unquoted variables (causes word splitting)
- Using backticks `` `cmd` `` instead of `$(cmd)`
- Using `eval` (security risk)
- Unnecessary use of `cat` (useless use of cat)

## File Operations

**Safe patterns:**

- Check file existence: `[ -f "$file" ]`
- Use absolute paths or validate relative paths
- Use `mktemp` for temporary files
- Clean up temporary files with `trap`

**Common mistakes:**

- Not checking if files exist before operations
- Using `ls` output in scripts (use globbing instead)
- Race conditions with temp files

## Input Validation

**Security critical:**

- Validate and sanitize all user input
- Use `readonly` for constants
- Avoid constructing commands from user input
- Use arrays for command arguments, not string concatenation

**Pattern:**

```bash
readonly CONFIG_FILE="/etc/app/config"

if [[ ! "$user_input" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo "Invalid input" >&2
    exit 1
fi
```bash

## Arrays and Loops

**Use arrays for lists:**

```bash
files=("file1.txt" "file2.txt" "file with spaces.txt")
for file in "${files[@]}"; do
    process "$file"
done
```bash

**Safe empty array handling with `set -u`:**

When using `set -u` (fail on unbound variables), checking array length on
empty arrays will fail. Use this pattern:

```bash
# WRONG: Fails with "unbound variable" on empty arrays
if [ "${#array[@]}" -gt 0 ]; then
    echo "Has items"
fi

# CORRECT: Safe pattern for set -u
if [ -n "${array[@]+"${array[@]}"}" ]; then
    count="${#array[@]}"
    echo "Has $count items"
fi
```bash

This pattern uses parameter expansion with alternate value to safely test
if an array has elements.

**Reading files:**

```bash
while IFS= read -r line; do
    process "$line"
done < file.txt
```bash

**Anti-patterns:**

- Parsing `ls` output
- Using `for` with word splitting
- Not preserving whitespace in loops
- Checking `${#array[@]}` directly when using `set -u` with potentially empty arrays

## Script Initialization and Ordering

**Get context before initialization:**

When scripts need external context (git repo, environment, etc.), gather it
before initializing subsystems:

```bash
# WRONG: Initialize before getting context
init_debug "unknown" "unknown"
org=$(get_git_org)
repo=$(get_git_repo)

# CORRECT: Get context first, then initialize
org=$(get_git_org)
repo=$(get_git_repo)
init_debug "$org" "$repo"
```bash

**Conditional sourcing:**

Only source helper scripts when needed to avoid errors and improve performance:

```bash
# Check prerequisites before sourcing
if git rev-parse --git-dir > /dev/null 2>&1; then
    source "$SCRIPT_DIR/git-helpers.sh"
    org=$(get_git_org_repo)
else
    org="unknown"
fi
```bash

## Functions

**Good practices:**

- Use `local` for function variables
- Return status codes, output to stdout
- Document function purpose and parameters
- Keep functions focused and small

**Pattern:**

```bash
process_file() {
    local file="$1"
    local output="$2"

    if [ ! -f "$file" ]; then
        return 1
    fi

    # Process and output
    transform "$file" > "$output"
}
```bash

## Command Substitution

**Modern syntax:**

- Use `$(command)` not backticks
- Quote command substitution: `"$(command)"`
- Check exit status separately if needed

**Pattern:**

```bash
result=$(command) || {
    echo "Command failed" >&2
    exit 1
}
```bash

## Testing and Conditions

**Use `[[` for conditions:**

- `[[ ]]` is more powerful than `[ ]`
- Safer with variables and patterns
- Supports `&&` and `||` inside

**Common tests:**

- `[[ -f $file ]]` - file exists
- `[[ -d $dir ]]` - directory exists
- `[[ -n $var ]]` - variable is not empty
- `[[ -z $var ]]` - variable is empty
- `[[ $a == $b ]]` - string equality
- `[[ $a =~ regex ]]` - regex match

## Logging and Output

**Standard practices:**

- Write errors to stderr: `echo "Error" >&2`
- Use consistent log format
- Don't create custom logging if not needed
- Use `echo` for simple output

**Pattern:**

```bash
log_error() {
    echo "ERROR: $*" >&2
}

log_info() {
    echo "INFO: $*"
}
```bash

**Stream separation (stdout vs stderr):**

Be careful when mixing streams. Avoid `2>&1` unless you specifically need
both streams combined:

```bash
# WRONG: Mixes debug output into data stream
result=$(command 2>&1)
echo "$result" | jq .  # Fails if debug messages mixed in

# CORRECT: Keep streams separate
result=$(command 2>/dev/null)  # Suppress stderr
result=$(command)  # Keep stderr separate (shows in console)

# CORRECT: Capture stderr separately if needed
result=$(command 2>"$error_file")
```bash

**When to use `2>&1`:**
- Only when you need to capture/parse both stdout and stderr together
- When redirecting all output to a log file
- Not for data pipelines where stdout contains structured data (JSON, CSV, etc.)

**Stderr handling policy:**

Use consistent patterns for different scenarios:

```bash
# Pattern 1: Expected failures (e.g., checking git repo status)
# Suppress stderr when failure is normal and expected
git_data=$(get_git_org_repo 2>/dev/null || echo "unknown|unknown")

# Pattern 2: Errors should be visible to user
# No redirection - errors show in console for debugging
parse_result=$("$SCRIPT_DIR/parse-review-arg.sh" "$arg" "$file_pattern")

# Pattern 3: Optional data where failure is acceptable
# Suppress stderr and provide empty fallback
diff_content=$("$SCRIPT_DIR/git-diff-filter.sh" 2>/dev/null || echo "")

# Pattern 4: Capture stderr for analysis
# Redirect to file or variable (rare - only when you need to parse errors)
stderr_output=$(command 2>&1 >/dev/null)
```bash

**Never:**
- Mix stderr into stdout for data pipelines (breaks JSON/CSV parsing)
- Silently swallow errors without fallback values
- Use `2>&1` by default "just in case"

## Performance

**Avoid common pitfalls:**

- Don't parse command output repeatedly
- Use built-in string operations instead of `sed`/`awk`
- Minimize subshells and external commands
- Use `read` built-in instead of external tools
- Avoid O(n²) array membership checks in loops

**Efficient patterns:**

- `${var#pattern}` - remove shortest prefix match
- `${var##pattern}` - remove longest prefix match
- `${var%pattern}` - remove shortest suffix match
- `${var%%pattern}` - remove longest suffix match
- `${var//pattern/replacement}` - replace all occurrences
- `${var,,}` - convert to lowercase (bash 4.0+)
- `${var^^}` - convert to uppercase (bash 4.0+)

**String splitting without external commands:**

```bash
# Split on delimiter (e.g., "org|repo")
data="posthog|posthog-js"
org="${data%|*}"      # Everything before last |
repo="${data#*|}"     # Everything after first |

# Better than: echo "$data" | cut -d'|' -f1
```bash

**Pattern matching for extraction:**

```bash
# Extract from URL paths
url="https://github.com/org/repo/pull/123"

# Use regex matching
if [[ "$url" =~ ^https?://[^/]+/([^/]+)/([^/]+)/pull/([0-9]+) ]]; then
    org="${BASH_REMATCH[1]}"
    repo="${BASH_REMATCH[2]}"
    pr="${BASH_REMATCH[3]}"
fi

# Or use sed for substitution
org=$(echo "$url" | sed -E 's|https?://[^/]+/([^/]+)/.*|\1|')
```bash

**Use associative arrays for O(1) lookups (bash 4.0+):**

```bash
# SLOW: O(n²) - checking membership in loop
languages=()
for item in "${items[@]}"; do
    [[ ! " ${languages[@]} " =~ " $item " ]] && languages+=("$item")
done

# FAST: O(n) - using associative array
declare -A seen_languages
for item in "${items[@]}"; do
    seen_languages[$item]=1
done
languages=("${!seen_languages[@]}")
```bash

## Dependencies

**Check before use:**

- Verify required commands exist
- Specify minimum versions if needed
- Provide clear error messages for missing deps
- Consider portability (GNU vs BSD tools)

## Quality Checklist

**Before committing:**

- Run `shellcheck` to catch common issues
- Test with `set -euo pipefail`
- Verify with different inputs
- Check quoting is correct
- Ensure cleanup happens (use `trap`)

## Common Anti-Patterns

**Avoid these:**

- `ls | grep` - use globbing instead
- `cat file | grep` - use `grep file`
- Unquoted `$@` - use `"$@"`
- `which command` - use `command -v`
- `==` in `[ ]` - use `=` or upgrade to `[[ ]]`
- Ignoring command failures silently

## Security Considerations

**Critical checks:**

- Never use `eval` on untrusted input
- Validate file paths (prevent path traversal)
- Use absolute paths for critical commands
- Don't trust `$PATH` for security-sensitive scripts
- Avoid command injection via variable expansion
- Use `readonly` for sensitive variables
