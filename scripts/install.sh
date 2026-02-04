#!/usr/bin/env bash
# =============================================================================
# AI Engineering Framework - Installation & Update Script
# =============================================================================
# Installs or updates the AI Engineering Framework in a target project.
#
# Install (new project):
#   ./install.sh --name "MyProject" --stacks dotnet,typescript --cicd github
#   ./install.sh --name "MyProject" --stacks dotnet --cicd azure
#   ./install.sh --name "MyProject" --stacks dotnet,typescript --cicd both
#
# Update (existing project):
#   ./install.sh --update --target /path/to/project
#
# Options:
#   --name      Project name (required for install, ignored for update)
#   --stacks    Comma-separated list: dotnet,typescript,python,terraform (required for install)
#   --cicd      CI/CD platform: github, azure, both (default: github)
#   --target    Target directory (default: current directory)
#   --update    Update existing installation (preserves customizations)
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
UPDATE_MODE=false

# Framework version
FRAMEWORK_VERSION="$(cat "$SCRIPT_DIR/VERSION" 2>/dev/null || echo "unknown")"

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
    --update)
      UPDATE_MODE=true
      shift
      ;;
    --help)
      head -25 "$0" | tail -20
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# =============================================================================
# UPDATE MODE
# =============================================================================
if [[ "$UPDATE_MODE" == true ]]; then
  TARGET_DIR="$(realpath "$TARGET_DIR")"

  # Check for existing installation
  if [[ ! -f "$TARGET_DIR/.ai-version" ]]; then
    echo -e "${RED}Error: No .ai-version found in $TARGET_DIR${NC}"
    echo -e "This doesn't appear to be an AI Engineering Framework project."
    echo -e "Use --name and --stacks for a fresh install instead."
    exit 1
  fi

  CURRENT_VERSION="$(cat "$TARGET_DIR/.ai-version")"

  echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║   AI Engineering Framework - Update           ║${NC}"
  echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  Current:    ${YELLOW}$CURRENT_VERSION${NC}"
  echo -e "  Available:  ${GREEN}$FRAMEWORK_VERSION${NC}"
  echo -e "  Target:     ${GREEN}$TARGET_DIR${NC}"
  echo ""

  if [[ "$CURRENT_VERSION" == "$FRAMEWORK_VERSION" ]]; then
    echo -e "${GREEN}Already up to date.${NC}"
    exit 0
  fi

  echo -e "${YELLOW}Updating framework files...${NC}"

  # --- Update skills (preserve custom/) ---
  echo -e "${YELLOW}Updating skills...${NC}"
  # Remove old framework skills (not custom)
  find "$TARGET_DIR/.claude/skills" -maxdepth 2 -name "SKILL.md" -not -path "*/custom/*" -delete 2>/dev/null || true
  find "$TARGET_DIR/.claude/skills" -maxdepth 2 -name "*.md" -not -path "*/custom/*" -not -name ".gitkeep" -delete 2>/dev/null || true
  # Copy new skills
  if [[ -d "$SCRIPT_DIR/.claude/skills" ]]; then
    rsync -a --exclude='custom/' "$SCRIPT_DIR/.claude/skills/" "$TARGET_DIR/.claude/skills/"
  fi
  echo -e "  ${GREEN}✓${NC} Skills updated (custom/ preserved)"

  # --- Update hooks ---
  echo -e "${YELLOW}Updating hooks...${NC}"
  if [[ -d "$SCRIPT_DIR/.claude/hooks" ]]; then
    mkdir -p "$TARGET_DIR/.claude/hooks"
    cp "$SCRIPT_DIR/.claude/hooks/"*.sh "$TARGET_DIR/.claude/hooks/" 2>/dev/null || true
    chmod +x "$TARGET_DIR/.claude/hooks/"*.sh 2>/dev/null || true
  fi
  echo -e "  ${GREEN}✓${NC} Hooks updated"

  # --- Update agents (preserve custom/) ---
  echo -e "${YELLOW}Updating agents...${NC}"
  find "$TARGET_DIR/.claude/agents" -maxdepth 1 -name "*.md" -not -path "*/custom/*" -delete 2>/dev/null || true
  if [[ -d "$SCRIPT_DIR/.claude/agents" ]]; then
    for agent in "$SCRIPT_DIR/.claude/agents/"*.md; do
      [[ -f "$agent" ]] && cp "$agent" "$TARGET_DIR/.claude/agents/"
    done
    mkdir -p "$TARGET_DIR/.claude/agents/custom"
    [[ -f "$SCRIPT_DIR/.claude/agents/custom/.gitkeep" ]] && cp "$SCRIPT_DIR/.claude/agents/custom/.gitkeep" "$TARGET_DIR/.claude/agents/custom/"
  fi
  echo -e "  ${GREEN}✓${NC} Agents updated (custom/ preserved)"

  # --- Update standards ---
  echo -e "${YELLOW}Updating standards...${NC}"
  for file in "$SCRIPT_DIR/standards/"*.md; do
    [[ -f "$file" ]] && cp "$file" "$TARGET_DIR/standards/"
  done
  echo -e "  ${GREEN}✓${NC} Standards updated"

  # --- Update workshop ---
  echo -e "${YELLOW}Updating workshop...${NC}"
  if [[ -d "$SCRIPT_DIR/workshop" ]]; then
    mkdir -p "$TARGET_DIR/workshop"
    for file in "$SCRIPT_DIR/workshop/"*.md; do
      [[ -f "$file" ]] && cp "$file" "$TARGET_DIR/workshop/"
    done
  fi
  echo -e "  ${GREEN}✓${NC} Workshop updated"

  # --- Update Copilot instructions ---
  echo -e "${YELLOW}Updating Copilot instructions...${NC}"
  if [[ -d "$TARGET_DIR/.github" ]]; then
    [[ -f "$SCRIPT_DIR/.github/copilot-instructions.md" ]] && \
      cp "$SCRIPT_DIR/.github/copilot-instructions.md" "$TARGET_DIR/.github/copilot-instructions.md"
    if [[ -d "$SCRIPT_DIR/.github/instructions" ]]; then
      mkdir -p "$TARGET_DIR/.github/instructions"
      for file in "$SCRIPT_DIR/.github/instructions/"*.md; do
        [[ -f "$file" ]] && cp "$file" "$TARGET_DIR/.github/instructions/"
      done
    fi
    echo -e "  ${GREEN}✓${NC} Copilot instructions updated"
  fi

  # --- Deep merge settings.json (preserve custom permissions, update hooks) ---
  echo -e "${YELLOW}Updating settings.json...${NC}"
  if [[ -f "$TARGET_DIR/.claude/settings.json" && -f "$SCRIPT_DIR/.claude/settings.json" ]]; then
    # Backup current settings
    cp "$TARGET_DIR/.claude/settings.json" "$TARGET_DIR/.claude/settings.json.bak"
    # Copy new settings (user should manually merge custom permissions)
    cp "$SCRIPT_DIR/.claude/settings.json" "$TARGET_DIR/.claude/settings.json"
    echo -e "  ${GREEN}✓${NC} Settings updated (backup: settings.json.bak)"
    echo -e "  ${YELLOW}⚠${NC}  Review settings.json and merge any custom permissions from settings.json.bak"
  fi

  # --- Update version ---
  echo "$FRAMEWORK_VERSION" > "$TARGET_DIR/.ai-version"

  # --- Remove old commands directory if it exists ---
  if [[ -d "$TARGET_DIR/.claude/commands" ]]; then
    echo -e "${YELLOW}Removing deprecated .claude/commands/ directory...${NC}"
    rm -rf "$TARGET_DIR/.claude/commands"
    echo -e "  ${GREEN}✓${NC} Old commands removed (migrated to skills)"
  fi

  # --- Remove deprecated agents ---
  for deprecated in build-validator.md test-runner.md security-scanner.md quality-checker.md; do
    if [[ -f "$TARGET_DIR/.claude/agents/$deprecated" ]]; then
      rm "$TARGET_DIR/.claude/agents/$deprecated"
    fi
  done

  echo ""
  echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║   Update complete! ($CURRENT_VERSION → $FRAMEWORK_VERSION)${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${YELLOW}Review:${NC}"
  echo -e "    1. Check ${BLUE}.claude/settings.json${NC} — merge custom permissions from .bak"
  echo -e "    2. Review ${BLUE}CLAUDE.md${NC} — add new sections if desired (see UPGRADING.md)"
  echo -e "    3. Run ${BLUE}/validate${NC} to verify the update"
  echo ""
  exit 0
fi

# =============================================================================
# INSTALL MODE
# =============================================================================

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
echo -e "${BLUE}║   Version: $FRAMEWORK_VERSION                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Project:  ${GREEN}$PROJECT_NAME${NC}"
echo -e "  Stacks:   ${GREEN}${STACKS}${NC}"
echo -e "  CI/CD:    ${GREEN}${CICD}${NC}"
echo -e "  Target:   ${GREEN}$(realpath "$TARGET_DIR")${NC}"
echo ""

# --- Create directory structure ---
echo -e "${YELLOW}Creating directory structure...${NC}"

mkdir -p "$TARGET_DIR/.claude/skills/dotnet"
mkdir -p "$TARGET_DIR/.claude/skills/utils"
mkdir -p "$TARGET_DIR/.claude/skills/custom"
mkdir -p "$TARGET_DIR/.claude/agents/custom"
mkdir -p "$TARGET_DIR/.claude/hooks"
mkdir -p "$TARGET_DIR/standards"
mkdir -p "$TARGET_DIR/context/decisions"
mkdir -p "$TARGET_DIR/learnings"
mkdir -p "$TARGET_DIR/workshop"

# --- Copy core files ---
echo -e "${YELLOW}Copying core files...${NC}"

# CLAUDE.md
cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
sed -i.bak "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" "$TARGET_DIR/CLAUDE.md" && rm -f "$TARGET_DIR/CLAUDE.md.bak"

# Settings
cp "$SCRIPT_DIR/.claude/settings.json" "$TARGET_DIR/.claude/settings.json"

# CLAUDE.local.md example
cp "$SCRIPT_DIR/CLAUDE.local.md.example" "$TARGET_DIR/CLAUDE.local.md.example"

# Version file
echo "$FRAMEWORK_VERSION" > "$TARGET_DIR/.ai-version"

# --- Copy skills ---
echo -e "${YELLOW}Copying skills...${NC}"

# Always copy these skills
for skill in commit commit-push-pr pr review test fix refactor security-audit document create-adr blast-radius deploy-check quality-gate validate learn setup-project; do
  if [[ -d "$SCRIPT_DIR/.claude/skills/${skill}" ]]; then
    mkdir -p "$TARGET_DIR/.claude/skills/${skill}"
    cp "$SCRIPT_DIR/.claude/skills/${skill}/SKILL.md" "$TARGET_DIR/.claude/skills/${skill}/SKILL.md"
  fi
done

# Copy utils
for util in "$SCRIPT_DIR/.claude/skills/utils/"*.md; do
  [[ -f "$util" ]] && cp "$util" "$TARGET_DIR/.claude/skills/utils/"
done

# Copy custom .gitkeep
cp "$SCRIPT_DIR/.claude/skills/custom/.gitkeep" "$TARGET_DIR/.claude/skills/custom/.gitkeep"

# Stack-specific skills
for stack in "${STACK_ARRAY[@]}"; do
  stack=$(echo "$stack" | xargs) # trim whitespace
  case "$stack" in
    dotnet)
      [[ -d "$SCRIPT_DIR/.claude/skills/add-endpoint" ]] && \
        mkdir -p "$TARGET_DIR/.claude/skills/add-endpoint" && \
        cp "$SCRIPT_DIR/.claude/skills/add-endpoint/SKILL.md" "$TARGET_DIR/.claude/skills/add-endpoint/SKILL.md"
      [[ -d "$SCRIPT_DIR/.claude/skills/migrate-api" ]] && \
        mkdir -p "$TARGET_DIR/.claude/skills/migrate-api" && \
        cp "$SCRIPT_DIR/.claude/skills/migrate-api/SKILL.md" "$TARGET_DIR/.claude/skills/migrate-api/SKILL.md"
      # Dotnet sub-skills
      for cmd in add-provider add-http-client add-error-mapping; do
        if [[ -d "$SCRIPT_DIR/.claude/skills/dotnet/${cmd}" ]]; then
          mkdir -p "$TARGET_DIR/.claude/skills/dotnet/${cmd}"
          cp "$SCRIPT_DIR/.claude/skills/dotnet/${cmd}/SKILL.md" "$TARGET_DIR/.claude/skills/dotnet/${cmd}/SKILL.md"
        fi
      done
      echo -e "  ${GREEN}✓${NC} .NET skills"
      ;;
    typescript)
      [[ -d "$SCRIPT_DIR/.claude/skills/add-component" ]] && \
        mkdir -p "$TARGET_DIR/.claude/skills/add-component" && \
        cp "$SCRIPT_DIR/.claude/skills/add-component/SKILL.md" "$TARGET_DIR/.claude/skills/add-component/SKILL.md"
      echo -e "  ${GREEN}✓${NC} TypeScript skills"
      ;;
  esac
done

# --- Copy hooks ---
echo -e "${YELLOW}Copying hooks...${NC}"

for hook in "$SCRIPT_DIR/.claude/hooks/"*.sh; do
  [[ -f "$hook" ]] && cp "$hook" "$TARGET_DIR/.claude/hooks/"
done
chmod +x "$TARGET_DIR/.claude/hooks/"*.sh 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} Hook scripts (auto-format, security guards, notifications)"

# --- Copy agents ---
echo -e "${YELLOW}Copying agents...${NC}"

for agent in "$SCRIPT_DIR/.claude/agents/"*.md; do
  [[ -f "$agent" ]] && cp "$agent" "$TARGET_DIR/.claude/agents/"
done
cp "$SCRIPT_DIR/.claude/agents/custom/.gitkeep" "$TARGET_DIR/.claude/agents/custom/.gitkeep"

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

# --- Copy context templates ---
echo -e "${YELLOW}Setting up context...${NC}"

for ctx in project.md architecture.md stack.md glossary.md; do
  cp "$SCRIPT_DIR/context/$ctx" "$TARGET_DIR/context/$ctx"
  sed -i.bak "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" "$TARGET_DIR/context/$ctx" && rm -f "$TARGET_DIR/context/$ctx.bak"
done

cp "$SCRIPT_DIR/context/decisions/_template.md" "$TARGET_DIR/context/decisions/_template.md"

# Copy hooks documentation
[[ -f "$SCRIPT_DIR/context/hooks.md" ]] && cp "$SCRIPT_DIR/context/hooks.md" "$TARGET_DIR/context/hooks.md"

# --- Copy learnings ---
echo -e "${YELLOW}Setting up learnings...${NC}"

cp "$SCRIPT_DIR/learnings/global.md" "$TARGET_DIR/learnings/global.md"
for stack in "${STACK_ARRAY[@]}"; do
  stack=$(echo "$stack" | xargs)
  if [[ -f "$SCRIPT_DIR/learnings/${stack}.md" ]]; then
    cp "$SCRIPT_DIR/learnings/${stack}.md" "$TARGET_DIR/learnings/${stack}.md"
  fi
done

# --- Copy workshop ---
echo -e "${YELLOW}Copying workshop...${NC}"

for module in "$SCRIPT_DIR/workshop/"*.md; do
  [[ -f "$module" ]] && cp "$module" "$TARGET_DIR/workshop/"
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

  for inst in "$SCRIPT_DIR/.github/instructions/"*.md; do
    [[ -f "$inst" ]] && cp "$inst" "$TARGET_DIR/.github/instructions/"
  done

  # Stack-specific Copilot instructions
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

# --- Detect platform ---
echo -e "${YELLOW}Detecting platform...${NC}"

PLATFORM="unknown"
if [[ -d "$TARGET_DIR/.git" ]]; then
  REMOTE_URL="$(cd "$TARGET_DIR" && git remote get-url origin 2>/dev/null || echo "")"
  if [[ "$REMOTE_URL" == *"github.com"* ]]; then
    PLATFORM="github"
    echo -e "  ${GREEN}✓${NC} Detected GitHub"
    if command -v gh &>/dev/null; then
      echo -e "  ${GREEN}✓${NC} gh CLI available"
    else
      echo -e "  ${YELLOW}⚠${NC}  gh CLI not found — install for PR creation"
    fi
  elif [[ "$REMOTE_URL" == *"dev.azure.com"* || "$REMOTE_URL" == *"visualstudio.com"* ]]; then
    PLATFORM="azure"
    echo -e "  ${GREEN}✓${NC} Detected Azure DevOps"
    if command -v az &>/dev/null; then
      echo -e "  ${GREEN}✓${NC} az CLI available"
    else
      echo -e "  ${YELLOW}⚠${NC}  az CLI not found — install for PR creation"
    fi
  else
    echo -e "  ${YELLOW}⚠${NC}  Platform not detected from remote URL"
  fi
else
  echo -e "  ${YELLOW}⚠${NC}  Not a git repository — platform detection skipped"
fi

# --- Update .gitignore ---
echo -e "${YELLOW}Updating .gitignore...${NC}"

if [[ -f "$TARGET_DIR/.gitignore" ]]; then
  for entry in "CLAUDE.local.md" ".ai-version" ".claude/settings.local.json"; do
    if ! grep -qF "$entry" "$TARGET_DIR/.gitignore"; then
      echo "$entry" >> "$TARGET_DIR/.gitignore"
    fi
  done
else
  cat > "$TARGET_DIR/.gitignore" << 'GITIGNORE'
# AI Engineering Framework - Local files
CLAUDE.local.md
.ai-version
.claude/settings.local.json
GITIGNORE
fi
echo -e "  ${GREEN}✓${NC} .gitignore updated"

# --- Summary ---
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Installation complete! (v$FRAMEWORK_VERSION)${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Edit ${BLUE}context/project.md${NC} with your project details"
echo -e "  2. Edit ${BLUE}context/architecture.md${NC} with your architecture"
echo -e "  3. Edit ${BLUE}context/stack.md${NC} with your technology versions"
echo -e "  4. Review ${BLUE}CLAUDE.md${NC} and customize critical rules"
echo -e "  5. Copy ${BLUE}CLAUDE.local.md.example${NC} to ${BLUE}CLAUDE.local.md${NC} for personal context"
echo -e "  6. Run ${BLUE}/validate${NC} in Claude Code to verify setup"
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
