#!/usr/bin/env bash
# scaffold-skill.sh -- Create the directory structure for a new ai-engineering skill.
#
# Usage:
#   bash scaffold-skill.sh <skill-name>
#
# Example:
#   bash scaffold-skill.sh deploy
#   -> creates the skill directory for the current surface
#   -> writes SKILL.md with the correct surface-specific frontmatter
#
# Cross-platform: bash 4+, macOS/Linux/WSL.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scaffold-skill.sh <skill-name>" >&2
  echo "Example: bash scaffold-skill.sh deploy" >&2
  exit 1
fi

SKILL_NAME="$1"
# Strip leading "ai-" if the user accidentally includes it
SKILL_NAME="${SKILL_NAME#ai-}"

SCRIPT_PATH="$(cd -- "$(dirname "$0")" && pwd)"
case "$SCRIPT_PATH" in
  */.claude/*)
    SKILL_DIR=".claude/skills/ai-${SKILL_NAME}"
    SKILL_FRONTMATTER_NAME="ai-${SKILL_NAME}"
    ;;
  */.github/*)
    SKILL_DIR=".github/skills/ai-${SKILL_NAME}"
    SKILL_FRONTMATTER_NAME="ai-${SKILL_NAME}"
    ;;
  */.codex/*)
    SKILL_DIR=".codex/skills/ai-${SKILL_NAME}"
    SKILL_FRONTMATTER_NAME="ai-${SKILL_NAME}"
    ;;
  *)
    echo "Error: could not determine target surface from script path: ${SCRIPT_PATH}" >&2
    exit 1
    ;;
esac

if [[ -d "$SKILL_DIR" ]]; then
  echo "Error: Skill directory already exists: ${SKILL_DIR}" >&2
  exit 1
fi

# Create directory structure
mkdir -p "${SKILL_DIR}/handlers" "${SKILL_DIR}/scripts"

# Create stub SKILL.md with frontmatter template
cat > "${SKILL_DIR}/SKILL.md" << TEMPLATE
---
name: ${SKILL_FRONTMATTER_NAME}
description: "Use when [describe triggering conditions]. Trigger for '[example user phrases]'."
effort: medium
argument-hint: "[expected arguments]"
---

# ${SKILL_NAME}

## Purpose

TODO: 2-3 lines describing what this skill does.

## Trigger

- Command: /ai-${SKILL_NAME}
- Context: TODO describe when this skill should activate.

## Procedure

1. TODO: Step 1
2. TODO: Step 2
3. TODO: Step 3

## When NOT to Use

- TODO: Differentiation from similar skills.

## Quick Reference

/ai-${SKILL_NAME} [args]

\$ARGUMENTS
TEMPLATE

echo "Scaffolded skill at ${SKILL_DIR}/"
echo "  SKILL.md    -- edit frontmatter and procedure"
echo "  handlers/   -- add handler markdown files"
echo "  scripts/    -- add helper scripts"
echo ""
echo "Next steps:"
echo "  1. Edit ${SKILL_DIR}/SKILL.md with your skill's procedure"
echo "  2. CSO-optimize the description field (triggering conditions, not summary)"
echo "  3. Register in .ai-engineering/manifest.yml"
echo "  4. Run: python scripts/sync_command_mirrors.py"
