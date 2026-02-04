#!/usr/bin/env bash
# =============================================================================
# AI Engineering Framework - Installation Script
# =============================================================================
# Installs the AI Engineering Framework into a target project directory.
#
# Usage:
#   ./install.sh --name "MyProject" --stacks dotnet,typescript --cicd github
#   ./install.sh --name "MyProject" --stacks dotnet --cicd azure
#   ./install.sh --name "MyProject" --stacks dotnet,typescript --cicd both
#
# Options:
#   --name      Project name (required)
#   --stacks    Comma-separated list: dotnet,typescript,python,terraform (required)
#   --cicd      CI/CD platform: github, azure, both (default: github)
#   --target    Target directory (default: current directory)
#   --help      Show this help message
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (where the framework lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Defaults
PROJECT_NAME=""
STACKS=""
CICD="github"
TARGET_DIR="."

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
  case $1 in
    --name)
      PROJECT_NAME="$2"
      shift 2
      ;;
    --stacks)
      STACKS="$2"
      shift 2
      ;;
    --cicd)
      CICD="$2"
      shift 2
      ;;
    --target)
      TARGET_DIR="$2"
      shift 2
      ;;
    --help)
      head -20 "$0" | tail -15
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# --- Validate arguments ---
if [[ -z "$PROJECT_NAME" ]]; then
  echo -e "${RED}Error: --name is required${NC}"
  echo "Usage: ./install.sh --name \"MyProject\" --stacks dotnet,typescript --cicd github"
  exit 1
fi

if [[ -z "$STACKS" ]]; then
  echo -e "${RED}Error: --stacks is required${NC}"
  echo "Available stacks: dotnet, typescript, python, terraform"
  exit 1
fi

if [[ "$CICD" != "github" && "$CICD" != "azure" && "$CICD" != "both" ]]; then
  echo -e "${RED}Error: --cicd must be github, azure, or both${NC}"
  exit 1
fi

# Convert stacks to array
IFS=',' read -ra STACK_ARRAY <<< "$STACKS"

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   AI Engineering Framework - Installation    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Project:  ${GREEN}$PROJECT_NAME${NC}"
echo -e "  Stacks:   ${GREEN}${STACKS}${NC}"
echo -e "  CI/CD:    ${GREEN}${CICD}${NC}"
echo -e "  Target:   ${GREEN}$(realpath "$TARGET_DIR")${NC}"
echo ""

# --- Create directory structure ---
echo -e "${YELLOW}Creating directory structure...${NC}"

mkdir -p "$TARGET_DIR/.claude/commands/dotnet"
mkdir -p "$TARGET_DIR/.claude/agents"
mkdir -p "$TARGET_DIR/standards"
mkdir -p "$TARGET_DIR/context/decisions"
mkdir -p "$TARGET_DIR/learnings"

# --- Copy core files ---
echo -e "${YELLOW}Copying core files...${NC}"

# CLAUDE.md
cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
sed -i.bak "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" "$TARGET_DIR/CLAUDE.md" && rm -f "$TARGET_DIR/CLAUDE.md.bak"

# Settings
cp "$SCRIPT_DIR/.claude/settings.json" "$TARGET_DIR/.claude/settings.json"

# --- Copy standards ---
echo -e "${YELLOW}Copying standards...${NC}"

# Always copy these
for file in global.md security.md quality-gates.md testing.md cicd.md api-design.md; do
  if [[ -f "$SCRIPT_DIR/standards/$file" ]]; then
    cp "$SCRIPT_DIR/standards/$file" "$TARGET_DIR/standards/$file"
  fi
done

# Copy stack-specific standards
for stack in "${STACK_ARRAY[@]}"; do
  stack=$(echo "$stack" | xargs) # trim whitespace
  if [[ -f "$SCRIPT_DIR/standards/${stack}.md" ]]; then
    cp "$SCRIPT_DIR/standards/${stack}.md" "$TARGET_DIR/standards/${stack}.md"
    echo -e "  ${GREEN}✓${NC} standards/${stack}.md"
  fi
done

# --- Copy commands ---
echo -e "${YELLOW}Copying commands...${NC}"

# Always copy these commands
for cmd in commit pr review test fix refactor security-audit document create-adr blast-radius deploy-check quality-gate validate learn setup-project; do
  if [[ -f "$SCRIPT_DIR/.claude/commands/${cmd}.md" ]]; then
    cp "$SCRIPT_DIR/.claude/commands/${cmd}.md" "$TARGET_DIR/.claude/commands/${cmd}.md"
  fi
done

# Stack-specific commands
for stack in "${STACK_ARRAY[@]}"; do
  stack=$(echo "$stack" | xargs)
  case "$stack" in
    dotnet)
      cp "$SCRIPT_DIR/.claude/commands/add-endpoint.md" "$TARGET_DIR/.claude/commands/add-endpoint.md" 2>/dev/null || true
      cp "$SCRIPT_DIR/.claude/commands/migrate-api.md" "$TARGET_DIR/.claude/commands/migrate-api.md" 2>/dev/null || true
      for cmd in "$SCRIPT_DIR/.claude/commands/dotnet/"*.md; do
        [[ -f "$cmd" ]] && cp "$cmd" "$TARGET_DIR/.claude/commands/dotnet/"
      done
      ;;
    typescript)
      cp "$SCRIPT_DIR/.claude/commands/add-component.md" "$TARGET_DIR/.claude/commands/add-component.md" 2>/dev/null || true
      ;;
  esac
done

# --- Copy agents ---
echo -e "${YELLOW}Copying agents...${NC}"

for agent in "$SCRIPT_DIR/.claude/agents/"*.md; do
  [[ -f "$agent" ]] && cp "$agent" "$TARGET_DIR/.claude/agents/"
done

# --- Copy context templates ---
echo -e "${YELLOW}Setting up context...${NC}"

for ctx in project.md architecture.md stack.md glossary.md; do
  cp "$SCRIPT_DIR/context/$ctx" "$TARGET_DIR/context/$ctx"
  sed -i.bak "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" "$TARGET_DIR/context/$ctx" && rm -f "$TARGET_DIR/context/$ctx.bak"
done

cp "$SCRIPT_DIR/context/decisions/_template.md" "$TARGET_DIR/context/decisions/_template.md"

# --- Copy learnings ---
echo -e "${YELLOW}Setting up learnings...${NC}"

cp "$SCRIPT_DIR/learnings/global.md" "$TARGET_DIR/learnings/global.md"
for stack in "${STACK_ARRAY[@]}"; do
  stack=$(echo "$stack" | xargs)
  if [[ -f "$SCRIPT_DIR/learnings/${stack}.md" ]]; then
    cp "$SCRIPT_DIR/learnings/${stack}.md" "$TARGET_DIR/learnings/${stack}.md"
  fi
done

# --- Copy CI/CD ---
echo -e "${YELLOW}Setting up CI/CD...${NC}"

if [[ "$CICD" == "github" || "$CICD" == "both" ]]; then
  mkdir -p "$TARGET_DIR/.github/workflows"
  mkdir -p "$TARGET_DIR/.github/instructions"

  for wf in ci.yml security.yml quality-gate.yml; do
    [[ -f "$SCRIPT_DIR/.github/workflows/$wf" ]] && cp "$SCRIPT_DIR/.github/workflows/$wf" "$TARGET_DIR/.github/workflows/$wf"
  done

  [[ -f "$SCRIPT_DIR/.github/copilot-instructions.md" ]] && cp "$SCRIPT_DIR/.github/copilot-instructions.md" "$TARGET_DIR/.github/copilot-instructions.md"

  for stack in "${STACK_ARRAY[@]}"; do
    stack=$(echo "$stack" | xargs)
    [[ -f "$SCRIPT_DIR/.github/instructions/${stack}.instructions.md" ]] && \
      cp "$SCRIPT_DIR/.github/instructions/${stack}.instructions.md" "$TARGET_DIR/.github/instructions/"
  done
  [[ -f "$SCRIPT_DIR/.github/instructions/security.instructions.md" ]] && \
    cp "$SCRIPT_DIR/.github/instructions/security.instructions.md" "$TARGET_DIR/.github/instructions/"

  echo -e "  ${GREEN}✓${NC} GitHub Actions workflows"
  echo -e "  ${GREEN}✓${NC} GitHub Copilot instructions"
fi

if [[ "$CICD" == "azure" || "$CICD" == "both" ]]; then
  mkdir -p "$TARGET_DIR/pipelines/templates"

  for pipeline in ci.yml security.yml quality-gate.yml; do
    [[ -f "$SCRIPT_DIR/pipelines/$pipeline" ]] && cp "$SCRIPT_DIR/pipelines/$pipeline" "$TARGET_DIR/pipelines/$pipeline"
  done

  for tmpl in "$SCRIPT_DIR/pipelines/templates/"*.yml; do
    [[ -f "$tmpl" ]] && cp "$tmpl" "$TARGET_DIR/pipelines/templates/"
  done

  echo -e "  ${GREEN}✓${NC} Azure Pipelines"
fi

# --- Summary ---
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Installation complete!                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Edit ${BLUE}context/project.md${NC} with your project details"
echo -e "  2. Edit ${BLUE}context/architecture.md${NC} with your architecture"
echo -e "  3. Edit ${BLUE}context/stack.md${NC} with your technology versions"
echo -e "  4. Review ${BLUE}CLAUDE.md${NC} and customize critical rules"
echo -e "  5. Run ${BLUE}/validate${NC} in Claude Code to verify setup"
echo ""
echo -e "  For CI/CD setup:"
if [[ "$CICD" == "github" || "$CICD" == "both" ]]; then
  echo -e "  - Set ${BLUE}SONAR_TOKEN${NC} in GitHub repository secrets"
  echo -e "  - Set ${BLUE}SNYK_TOKEN${NC} in GitHub repository secrets (optional)"
fi
if [[ "$CICD" == "azure" || "$CICD" == "both" ]]; then
  echo -e "  - Create ${BLUE}SonarCloud${NC} service connection in Azure DevOps"
  echo -e "  - Create ${BLUE}common-variables${NC} variable group"
fi
echo ""
