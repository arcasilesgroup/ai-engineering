#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 1. Check uv
if ! command -v uv &>/dev/null; then
    echo "ERROR: uv not found. Install: https://docs.astral.sh/uv/"
    exit 1
fi

# 2. Editable install as global tool
echo "Installing ai-eng globally (editable)..."
uv tool install --editable "$REPO_ROOT" --force

# 3. Verify
if ! command -v ai-eng &>/dev/null; then
    echo "WARNING: ai-eng not in PATH."
    echo "Add to your shell: export PATH=\"\$HOME/.local/bin:\$PATH\""
    exit 1
fi

# 4. Done
echo ""
echo "ai-eng $(ai-eng version 2>/dev/null || echo 'installed')"
echo ""
echo "Usage from any directory:"
echo "  ai-eng install .          # Initialize a project"
echo "  ai-eng doctor             # Health check"
echo "  ai-eng update --apply     # Update framework files"
echo ""
echo "Code changes in $REPO_ROOT/src/ are reflected immediately."
