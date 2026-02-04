#!/usr/bin/env bash
# PreToolUse hook: Block editing sensitive/secret files.
#
# Reads stdin JSON to extract the file path being edited and rejects
# writes to files that typically contain secrets or credentials.
#
# Blocked patterns:
#   .env           - Environment variable files
#   .env.*         - Environment variant files (.env.local, .env.production)
#   *.env          - Files ending in .env
#   credentials.*  - Credential files
#   *.pem          - SSL/TLS certificates
#   *.key          - Private key files
#   *secret*       - Any file with "secret" in the name
#
# Exit codes:
#   0 = allow the edit
#   2 = block the edit (reason printed to stderr)

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse stdin JSON
# ---------------------------------------------------------------------------
INPUT="$(cat)"

# Extract tool_name -- only act on Edit and Write tools
TOOL_NAME="$(echo "$INPUT" | grep -o '"tool_name"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

if [[ "$TOOL_NAME" != "Edit" && "$TOOL_NAME" != "Write" ]]; then
    exit 0
fi

# Extract file_path from the JSON
FILE_PATH="$(echo "$INPUT" | grep -o '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Get just the filename for pattern matching
FILENAME="$(basename "$FILE_PATH")"
# Lowercase for case-insensitive matching on certain patterns
FILENAME_LOWER="$(echo "$FILENAME" | tr '[:upper:]' '[:lower:]')"

# ---------------------------------------------------------------------------
# Check for sensitive file patterns
# ---------------------------------------------------------------------------

# Exact match: .env
if [[ "$FILENAME" == ".env" ]]; then
    echo "BLOCKED: Editing .env files is prohibited. Secrets must not be managed through Claude Code." >&2
    exit 2
fi

# .env.* pattern (e.g., .env.local, .env.production)
if [[ "$FILENAME" == .env.* ]]; then
    echo "BLOCKED: Editing .env.* files is prohibited. Secrets must not be managed through Claude Code." >&2
    exit 2
fi

# *.env pattern (e.g., production.env)
if [[ "$FILENAME" == *.env ]]; then
    echo "BLOCKED: Editing *.env files is prohibited. Secrets must not be managed through Claude Code." >&2
    exit 2
fi

# credentials.* pattern (case insensitive)
if [[ "$FILENAME_LOWER" == credentials.* ]]; then
    echo "BLOCKED: Editing credential files is prohibited. Secrets must not be managed through Claude Code." >&2
    exit 2
fi

# *.pem pattern
if [[ "$FILENAME" == *.pem ]]; then
    echo "BLOCKED: Editing .pem certificate files is prohibited. Secrets must not be managed through Claude Code." >&2
    exit 2
fi

# *.key pattern
if [[ "$FILENAME" == *.key ]]; then
    echo "BLOCKED: Editing .key private key files is prohibited. Secrets must not be managed through Claude Code." >&2
    exit 2
fi

# *secret* pattern (case insensitive)
if [[ "$FILENAME_LOWER" == *secret* ]]; then
    echo "BLOCKED: Editing files containing 'secret' in the name is prohibited. Secrets must not be managed through Claude Code." >&2
    exit 2
fi

# ---------------------------------------------------------------------------
# File is allowed
# ---------------------------------------------------------------------------
exit 0
