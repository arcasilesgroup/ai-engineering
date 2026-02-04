# Bash Standards

> Conventions for Bash scripts.

---

## Script Structure

### Standard Header

```bash
#!/usr/bin/env bash
#
# script-name.sh - Brief description
#
# Usage: ./script-name.sh [options] <arguments>
#
# Options:
#   -h, --help     Show this help message
#   -v, --verbose  Enable verbose output
#   -e, --env      Environment (dev, staging, prod)
#
# Examples:
#   ./script-name.sh --env prod
#   ./script-name.sh -v input.txt
#
# Author: Team Name
# Version: 1.0.0

set -euo pipefail
IFS=$'\n\t'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
VERBOSE=false
ENVIRONMENT="dev"
```

---

## Shell Options

```bash
# Recommended options (set at top of script)
set -e          # Exit on error
set -u          # Error on undefined variables
set -o pipefail # Exit on pipe failures
set -x          # Debug mode (print commands)

# Combined
set -euo pipefail

# For debugging
set -x  # Enable
set +x  # Disable
```

---

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Scripts | kebab-case | `deploy-app.sh`, `run-tests.sh` |
| Functions | snake_case | `process_file`, `get_config` |
| Variables (local) | snake_case | `file_path`, `user_name` |
| Variables (export) | UPPER_SNAKE | `API_KEY`, `DATABASE_URL` |
| Constants | UPPER_SNAKE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |

---

## Variables

### Declaration

```bash
# Local variables (lowercase)
local file_path="/tmp/data.txt"
local count=0

# Environment variables (uppercase)
export API_URL="https://api.example.com"
export DEBUG_MODE=true

# Constants (readonly)
readonly MAX_RETRIES=3
readonly CONFIG_FILE="${SCRIPT_DIR}/config.json"
```

### Default Values

```bash
# Use default if unset
name="${1:-default_name}"

# Use default if unset or empty
name="${1:-}"

# Error if unset
name="${1:?Error: name is required}"

# Assign default if unset
: "${LOG_LEVEL:=info}"
```

### String Manipulation

```bash
# Length
length=${#string}

# Substring
sub=${string:0:5}  # First 5 chars

# Replace
new=${string/old/new}      # First occurrence
new=${string//old/new}     # All occurrences

# Remove prefix/suffix
filename=${path##*/}       # Remove path
extension=${file##*.}      # Get extension
basename=${file%.*}        # Remove extension
```

---

## Functions

```bash
# Function definition
process_file() {
    local file="$1"
    local output="${2:-/tmp/output.txt}"

    if [[ ! -f "$file" ]]; then
        echo "Error: File not found: $file" >&2
        return 1
    fi

    # Process file
    cat "$file" > "$output"
    
    return 0
}

# Usage
if process_file "input.txt" "output.txt"; then
    echo "Success"
else
    echo "Failed"
fi
```

---

## Conditionals

### Test Syntax

```bash
# Preferred: Double brackets
if [[ "$string" == "value" ]]; then
    echo "Match"
fi

# File tests
[[ -f "$file" ]]   # Is regular file
[[ -d "$dir" ]]    # Is directory
[[ -e "$path" ]]   # Exists
[[ -r "$file" ]]   # Is readable
[[ -w "$file" ]]   # Is writable
[[ -x "$file" ]]   # Is executable
[[ -s "$file" ]]   # Is non-empty

# String tests
[[ -z "$var" ]]    # Is empty
[[ -n "$var" ]]    # Is not empty
[[ "$a" == "$b" ]] # Equals
[[ "$a" != "$b" ]] # Not equals
[[ "$a" =~ ^[0-9]+$ ]]  # Regex match

# Numeric comparisons
[[ "$a" -eq "$b" ]]  # Equal
[[ "$a" -ne "$b" ]]  # Not equal
[[ "$a" -lt "$b" ]]  # Less than
[[ "$a" -le "$b" ]]  # Less or equal
[[ "$a" -gt "$b" ]]  # Greater than
[[ "$a" -ge "$b" ]]  # Greater or equal

# Logical operators
[[ "$a" && "$b" ]]   # AND
[[ "$a" || "$b" ]]   # OR
[[ ! "$a" ]]         # NOT
```

### Case Statement

```bash
case "$environment" in
    dev|development)
        url="https://dev.example.com"
        ;;
    staging|stg)
        url="https://staging.example.com"
        ;;
    prod|production)
        url="https://example.com"
        ;;
    *)
        echo "Unknown environment: $environment" >&2
        exit 1
        ;;
esac
```

---

## Loops

```bash
# For loop (array)
for item in "${array[@]}"; do
    echo "$item"
done

# For loop (range)
for i in {1..10}; do
    echo "$i"
done

# For loop (C-style)
for ((i=0; i<10; i++)); do
    echo "$i"
done

# While loop
while read -r line; do
    echo "$line"
done < "$file"

# While with command
while IFS= read -r line; do
    process "$line"
done < <(find . -name "*.txt")
```

---

## Error Handling

```bash
# Trap for cleanup
cleanup() {
    rm -f "$temp_file"
    echo "Cleaned up"
}
trap cleanup EXIT

# Error handler
error_handler() {
    echo "Error on line $1" >&2
    exit 1
}
trap 'error_handler $LINENO' ERR

# Check command success
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed" >&2
    exit 1
fi
```

---

## Logging

```bash
# Log functions
log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $*"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2
}

log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo "[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') $*"
    fi
}

# Usage
log_info "Starting deployment"
log_error "Failed to connect"
```

---

## Argument Parsing

```bash
# Simple parsing
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done
```

---

## Best Practices

### Do

```bash
# ✅ Quote variables
echo "$variable"
rm -rf "${dir}/"

# ✅ Use [[ ]] instead of [ ]
if [[ "$var" == "value" ]]; then

# ✅ Use $() instead of backticks
result=$(command)

# ✅ Check exit codes
if ! command; then
    echo "Command failed"
    exit 1
fi

# ✅ Use local in functions
local my_var="value"
```

### Don't

```bash
# ❌ Unquoted variables
echo $variable     # Word splitting issues
rm -rf $dir/       # Dangerous!

# ❌ Single brackets
if [ "$var" == "value" ]; then

# ❌ Backticks
result=`command`

# ❌ Parse ls output
for file in $(ls); do  # Wrong!

# ✅ Use glob instead
for file in *; do
```

---

## Portability

```bash
# Use /usr/bin/env for portability
#!/usr/bin/env bash

# Check bash version
if [[ "${BASH_VERSION%%.*}" -lt 4 ]]; then
    echo "Bash 4+ required" >&2
    exit 1
fi

# Check for required commands
for cmd in curl jq docker; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "Required command not found: $cmd" >&2
        exit 1
    fi
done
```
