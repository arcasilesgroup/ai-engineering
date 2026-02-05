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
# With tool installation:
#   ./install.sh --name "MyProject" --stacks dotnet,typescript --cicd github --install-tools
#   ./install.sh --name "MyProject" --stacks typescript --cicd github --install-tools --exec
#
# Update (existing project):
#   ./install.sh --update --target /path/to/project
#
# Options:
#   --name           Project name (required for install, ignored for update)
#   --stacks         Comma-separated list: dotnet,typescript,python,terraform (required for install)
#   --cicd           CI/CD platform: github, azure, both (default: github)
#   --target         Target directory (default: current directory)
#   --update         Update existing installation (preserves customizations)
#   --install-tools  Install required development tools (gitleaks, gh, az, etc.)
#   --skip-sdks      Skip SDK verification (dotnet, node, python, terraform)
#   --exec           Run npm install / pip install after setup
#   --help           Show this help message
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
INSTALL_TOOLS=false
SKIP_SDKS=false
EXEC_INSTALL=false

# Error tracking for reporting
INSTALL_ERRORS=()
SYSTEM_INFO=""

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
    --install-tools)
      INSTALL_TOOLS=true
      shift
      ;;
    --skip-sdks)
      SKIP_SDKS=true
      shift
      ;;
    --exec)
      EXEC_INSTALL=true
      shift
      ;;
    --help)
      head -30 "$0" | tail -25
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# =============================================================================
# TOOL INSTALLATION FUNCTIONS
# =============================================================================

# --- System Detection ---
detect_os() {
    case "$(uname -s)" in
        Darwin)
            echo "macos"
            ;;
        Linux)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                echo "wsl"
            else
                echo "linux"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

detect_package_manager() {
    local os="$1"

    case "$os" in
        macos)
            if command -v brew &>/dev/null; then
                echo "brew"
            else
                echo "manual"
            fi
            ;;
        linux|wsl)
            if command -v apt-get &>/dev/null; then
                echo "apt"
            elif command -v dnf &>/dev/null; then
                echo "dnf"
            elif command -v yum &>/dev/null; then
                echo "yum"
            elif command -v pacman &>/dev/null; then
                echo "pacman"
            else
                echo "manual"
            fi
            ;;
        *)
            echo "manual"
            ;;
    esac
}

collect_system_info() {
    local os="$1"
    local pkg_mgr="$2"

    SYSTEM_INFO="**OS:** $(uname -s) $(uname -r) ($(uname -m))"$'\n'
    SYSTEM_INFO+="**Package Manager:** $pkg_mgr"$'\n'
    SYSTEM_INFO+="**Shell:** $SHELL"$'\n'
    SYSTEM_INFO+="**Framework version:** $FRAMEWORK_VERSION"$'\n'
    SYSTEM_INFO+="**Stacks:** $STACKS"$'\n'
    SYSTEM_INFO+="**Platform:** $CICD"
}

# --- Error Reporting ---
collect_error_report() {
    local tool="$1"
    local error_msg="$2"

    INSTALL_ERRORS+=("$tool:$error_msg")
}

prompt_report_issue() {
    if [[ ${#INSTALL_ERRORS[@]} -eq 0 ]]; then
        return 0
    fi

    echo ""
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  ⚠️  Some tool installations failed                           ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    for error in "${INSTALL_ERRORS[@]}"; do
        local tool="${error%%:*}"
        echo -e "  • ${RED}$tool${NC} installation failed"
    done

    echo ""

    # Only offer to create issue if gh is available and authenticated
    if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
        echo -e "Would you like to report this issue to GitHub?"
        echo -e "This will create an issue with diagnostic information."
        echo ""
        read -r -p "Report issue? [y/N] " response

        if [[ "$response" =~ ^[Yy]$ ]]; then
            create_github_issue
        fi
    else
        local repo_url_hint
        repo_url_hint="$(git -C "$SCRIPT_DIR" remote get-url origin 2>/dev/null | sed -E 's|.*github.com[:/]([^/]+/[^/.]+)(\.git)?.*|\1|' || echo "")"
        if [[ -n "$repo_url_hint" ]]; then
            echo -e "To report this issue, please create an issue at:"
            echo -e "  ${BLUE}https://github.com/${repo_url_hint}/issues${NC}"
        else
            echo -e "To report this issue, please create an issue in the framework repository."
        fi
    fi
}

create_github_issue() {
    local title="Tool Installation Failure Report"
    local body="## Tool Installation Failure Report"$'\n\n'

    body+="### Failed Tools"$'\n'
    for error in "${INSTALL_ERRORS[@]}"; do
        local tool="${error%%:*}"
        local msg="${error#*:}"
        body+="- **$tool**: $msg"$'\n'
    done
    body+=$'\n'

    body+="### System Info"$'\n'
    body+="$SYSTEM_INFO"$'\n'

    body+="### Steps to Reproduce"$'\n'
    body+='```bash'$'\n'
    body+="./install.sh --name \"Test\" --stacks $STACKS --cicd $CICD --install-tools"$'\n'
    body+='```'$'\n\n'

    body+="---"$'\n'
    body+="*Auto-generated by AI Engineering Framework install.sh*"

    # Try to create issue in the framework repo
    local repo_url
    repo_url="$(git -C "$SCRIPT_DIR" remote get-url origin 2>/dev/null || echo "")"

    if [[ "$repo_url" == *"github.com"* ]]; then
        # Extract owner/repo from URL
        local repo
        repo=$(echo "$repo_url" | sed -E 's|.*github.com[:/]([^/]+/[^/.]+)(\.git)?.*|\1|')

        if gh issue create --repo "$repo" --title "$title" --body "$body" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Issue created successfully"
        else
            echo -e "${YELLOW}Could not create issue automatically${NC}"
            echo -e "Please create an issue manually with the information above"
        fi
    else
        echo -e "${YELLOW}Framework repo not detected as GitHub${NC}"
        echo -e "Please create an issue manually"
    fi
}

# --- Global Tool Installation ---
install_gitleaks() {
    echo -e "  Checking gitleaks..."

    if command -v gitleaks &>/dev/null; then
        echo -e "    ${GREEN}✓${NC} gitleaks already installed ($(gitleaks version 2>/dev/null || echo 'unknown'))"
        return 0
    fi

    local os="$1"
    local pkg_mgr="$2"

    case "$pkg_mgr" in
        brew)
            echo -e "    Installing via Homebrew..."
            if brew install gitleaks 2>&1; then
                echo -e "    ${GREEN}✓${NC} gitleaks installed"
            else
                echo -e "    ${RED}✗${NC} Failed to install gitleaks"
                collect_error_report "gitleaks" "brew install failed"
            fi
            ;;
        apt)
            echo -e "    Installing via GitHub releases..."
            install_gitleaks_from_github "$os"
            ;;
        *)
            echo -e "    Installing via GitHub releases..."
            install_gitleaks_from_github "$os"
            ;;
    esac
}

install_gitleaks_from_github() {
    local os="$1"
    local arch
    local platform

    arch="$(uname -m)"
    case "$arch" in
        x86_64) arch="x64" ;;
        aarch64|arm64) arch="arm64" ;;
    esac

    case "$os" in
        macos) platform="darwin" ;;
        linux|wsl) platform="linux" ;;
        *) platform="linux" ;;
    esac

    local version
    version=$(curl -sL "https://api.github.com/repos/gitleaks/gitleaks/releases/latest" | grep '"tag_name"' | sed -E 's/.*"v([^"]+)".*/\1/' || echo "8.18.0")

    local url="https://github.com/gitleaks/gitleaks/releases/download/v${version}/gitleaks_${version}_${platform}_${arch}.tar.gz"
    local tmp_dir
    tmp_dir=$(mktemp -d)

    if curl -sL "$url" | tar xz -C "$tmp_dir" 2>/dev/null; then
        if sudo mv "$tmp_dir/gitleaks" /usr/local/bin/ 2>/dev/null || mv "$tmp_dir/gitleaks" ~/.local/bin/ 2>/dev/null; then
            chmod +x /usr/local/bin/gitleaks 2>/dev/null || chmod +x ~/.local/bin/gitleaks 2>/dev/null
            echo -e "    ${GREEN}✓${NC} gitleaks installed"
        else
            echo -e "    ${RED}✗${NC} Failed to install gitleaks (permission denied)"
            collect_error_report "gitleaks" "Failed to copy binary to /usr/local/bin or ~/.local/bin"
        fi
    else
        echo -e "    ${RED}✗${NC} Failed to download gitleaks"
        collect_error_report "gitleaks" "Failed to download from GitHub releases"
    fi

    rm -rf "$tmp_dir"
}

install_gh() {
    echo -e "  Checking gh (GitHub CLI)..."

    if command -v gh &>/dev/null; then
        echo -e "    ${GREEN}✓${NC} gh already installed ($(gh --version 2>/dev/null | head -1 || echo 'unknown'))"
        return 0
    fi

    local pkg_mgr="$1"

    case "$pkg_mgr" in
        brew)
            echo -e "    Installing via Homebrew..."
            if brew install gh 2>&1; then
                echo -e "    ${GREEN}✓${NC} gh installed"
                echo -e "    ${YELLOW}!${NC} Run 'gh auth login' to authenticate"
            else
                echo -e "    ${RED}✗${NC} Failed to install gh"
                collect_error_report "gh" "brew install failed"
            fi
            ;;
        apt)
            echo -e "    Installing via apt..."
            if (type -p curl >/dev/null || sudo apt install curl -y) && \
               curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null && \
               sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg && \
               echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
               sudo apt update && sudo apt install gh -y 2>&1; then
                echo -e "    ${GREEN}✓${NC} gh installed"
                echo -e "    ${YELLOW}!${NC} Run 'gh auth login' to authenticate"
            else
                echo -e "    ${RED}✗${NC} Failed to install gh"
                collect_error_report "gh" "apt install failed"
            fi
            ;;
        dnf|yum)
            echo -e "    Installing via $pkg_mgr..."
            if sudo $pkg_mgr install 'dnf-command(config-manager)' -y 2>/dev/null && \
               sudo $pkg_mgr config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo && \
               sudo $pkg_mgr install gh -y 2>&1; then
                echo -e "    ${GREEN}✓${NC} gh installed"
            else
                echo -e "    ${RED}✗${NC} Failed to install gh"
                collect_error_report "gh" "$pkg_mgr install failed"
            fi
            ;;
        *)
            echo -e "    ${YELLOW}⚠${NC}  Manual installation required"
            echo -e "    ${BLUE}https://github.com/cli/cli#installation${NC}"
            ;;
    esac
}

install_az() {
    echo -e "  Checking az (Azure CLI)..."

    if command -v az &>/dev/null; then
        echo -e "    ${GREEN}✓${NC} az already installed ($(az version --query '"azure-cli"' -o tsv 2>/dev/null || echo 'unknown'))"
        return 0
    fi

    local os="$1"
    local pkg_mgr="$2"

    case "$pkg_mgr" in
        brew)
            echo -e "    Installing via Homebrew..."
            if brew install azure-cli 2>&1; then
                echo -e "    ${GREEN}✓${NC} az installed"
                echo -e "    ${YELLOW}!${NC} Run 'az login' to authenticate"
            else
                echo -e "    ${RED}✗${NC} Failed to install az"
                collect_error_report "az" "brew install failed"
            fi
            ;;
        apt)
            echo -e "    Installing via Microsoft script..."
            if curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash 2>&1; then
                echo -e "    ${GREEN}✓${NC} az installed"
                echo -e "    ${YELLOW}!${NC} Run 'az login' to authenticate"
            else
                echo -e "    ${RED}✗${NC} Failed to install az"
                collect_error_report "az" "Microsoft install script failed"
            fi
            ;;
        dnf|yum)
            echo -e "    Installing via Microsoft RPM repo..."
            if sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc 2>/dev/null && \
               sudo $pkg_mgr install -y https://packages.microsoft.com/config/rhel/8/packages-microsoft-prod.rpm 2>/dev/null && \
               sudo $pkg_mgr install azure-cli -y 2>&1; then
                echo -e "    ${GREEN}✓${NC} az installed"
            else
                echo -e "    ${RED}✗${NC} Failed to install az"
                collect_error_report "az" "$pkg_mgr install failed"
            fi
            ;;
        *)
            echo -e "    ${YELLOW}⚠${NC}  Manual installation required"
            echo -e "    ${BLUE}https://docs.microsoft.com/en-us/cli/azure/install-azure-cli${NC}"
            ;;
    esac
}

install_tflint() {
    echo -e "  Checking tflint..."

    if command -v tflint &>/dev/null; then
        echo -e "    ${GREEN}✓${NC} tflint already installed ($(tflint --version 2>/dev/null | head -1 || echo 'unknown'))"
        return 0
    fi

    local pkg_mgr="$1"

    case "$pkg_mgr" in
        brew)
            echo -e "    Installing via Homebrew..."
            if brew install tflint 2>&1; then
                echo -e "    ${GREEN}✓${NC} tflint installed"
            else
                echo -e "    ${YELLOW}⚠${NC}  Failed to install tflint (optional)"
            fi
            ;;
        *)
            echo -e "    Installing via install script..."
            if curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash 2>&1; then
                echo -e "    ${GREEN}✓${NC} tflint installed"
            else
                echo -e "    ${YELLOW}⚠${NC}  Failed to install tflint (optional)"
            fi
            ;;
    esac
}

# --- SDK Verification ---
# Generic SDK verification: verify_sdk <command> <display_name> <install_url> [version_cmd]
verify_sdk() {
    local cmd="$1"
    local name="$2"
    local install_url="$3"
    local version_cmd="${4:-$cmd --version}"

    echo -e "  Checking ${name}..."

    if command -v "$cmd" &>/dev/null; then
        local version
        version=$(eval "$version_cmd" 2>/dev/null || echo "unknown")
        echo -e "    ${GREEN}✓${NC} ${name} $version"
    else
        echo -e "    ${YELLOW}⚠${NC}  ${name} not found"
        echo -e "    ${BLUE}Install: ${install_url}${NC}"
    fi
}

verify_dotnet_sdk() {
    verify_sdk "dotnet" ".NET SDK" "https://dotnet.microsoft.com/download" "dotnet --version"
}

verify_node_sdk() {
    verify_sdk "node" "Node.js" "https://nodejs.org/ or use nvm" "node --version"
    if command -v npm &>/dev/null; then
        local npm_version
        npm_version=$(npm --version 2>/dev/null || echo "unknown")
        echo -e "    ${GREEN}✓${NC} npm $npm_version"
    fi
}

verify_python_sdk() {
    verify_sdk "python3" "Python" "https://python.org/ or use pyenv" "python3 --version"
    if command -v pip3 &>/dev/null || command -v pip &>/dev/null; then
        local pip_version
        pip_version=$(pip3 --version 2>/dev/null || pip --version 2>/dev/null || echo "unknown")
        echo -e "    ${GREEN}✓${NC} pip $(echo "$pip_version" | awk '{print $2}')"
    fi
}

verify_terraform_sdk() {
    verify_sdk "terraform" "Terraform" "https://terraform.io/downloads or use tfenv" \
        "terraform version -json 2>/dev/null | grep -o '\"terraform_version\":\"[^\"]*\"' | cut -d'\"' -f4 || terraform version 2>/dev/null | head -1"
}

# --- Project-Local Configuration ---
configure_typescript_tools() {
    local target="$1"

    echo -e "  Generating TypeScript tool configuration..."

    # Create .ai-tools-npm.json for reference
    if [[ -f "$SCRIPT_DIR/scripts/tool-configs/typescript.json" ]]; then
        cp "$SCRIPT_DIR/scripts/tool-configs/typescript.json" "$target/.ai-tools-npm.json"
        echo -e "    ${GREEN}✓${NC} Created .ai-tools-npm.json (merge devDependencies into package.json)"
    fi
}

configure_python_tools() {
    local target="$1"

    echo -e "  Generating Python tool configuration..."

    # Create requirements-dev.txt if it doesn't exist
    if [[ ! -f "$target/requirements-dev.txt" ]]; then
        if [[ -f "$SCRIPT_DIR/scripts/tool-configs/python.txt" ]]; then
            cp "$SCRIPT_DIR/scripts/tool-configs/python.txt" "$target/requirements-dev.txt"
            echo -e "    ${GREEN}✓${NC} Created requirements-dev.txt"
        fi
    else
        echo -e "    ${YELLOW}⚠${NC}  requirements-dev.txt already exists (not overwritten)"
    fi
}

configure_terraform_tools() {
    local target="$1"

    echo -e "  Generating Terraform tool configuration..."

    # Create .tflint.hcl if it doesn't exist
    if [[ ! -f "$target/.tflint.hcl" ]]; then
        if [[ -f "$SCRIPT_DIR/scripts/tool-configs/tflint.hcl" ]]; then
            cp "$SCRIPT_DIR/scripts/tool-configs/tflint.hcl" "$target/.tflint.hcl"
            echo -e "    ${GREEN}✓${NC} Created .tflint.hcl"
        fi
    else
        echo -e "    ${YELLOW}⚠${NC}  .tflint.hcl already exists (not overwritten)"
    fi
}

# --- Git Hooks Configuration ---
configure_git_hooks() {
    local target="$1"
    local hooks_dir="$target/.git/hooks"

    echo -e "  Configuring git hooks..."

    if [[ ! -d "$target/.git" ]]; then
        echo -e "    ${YELLOW}⚠${NC}  Not a git repository, skipping hook installation"
        return 0
    fi

    if [[ ! -d "$hooks_dir" ]]; then
        mkdir -p "$hooks_dir"
    fi

    # Install pre-commit hook for secret scanning
    if [[ -f "$SCRIPT_DIR/scripts/hooks/pre-commit" ]]; then
        cp "$SCRIPT_DIR/scripts/hooks/pre-commit" "$hooks_dir/pre-commit"
        chmod +x "$hooks_dir/pre-commit"
        echo -e "    ${GREEN}✓${NC} Pre-commit secret scanning hook installed"
    fi

    # Install pre-push hook for vulnerability checking
    if [[ -f "$SCRIPT_DIR/scripts/hooks/pre-push" ]]; then
        cp "$SCRIPT_DIR/scripts/hooks/pre-push" "$hooks_dir/pre-push"
        chmod +x "$hooks_dir/pre-push"
        echo -e "    ${GREEN}✓${NC} Pre-push vulnerability check hook installed"
    fi
}

# --- Execute Package Installs ---
execute_package_installs() {
    local target="$1"

    echo -e "${YELLOW}Executing package installations...${NC}"

    # TypeScript/Node
    if [[ -f "$target/package.json" ]]; then
        echo -e "  Running npm install..."
        if (cd "$target" && npm install 2>&1); then
            echo -e "    ${GREEN}✓${NC} npm install complete"
        else
            echo -e "    ${YELLOW}⚠${NC}  npm install failed"
        fi
    fi

    # Python
    if [[ -f "$target/requirements-dev.txt" ]]; then
        echo -e "  Running pip install..."
        if (cd "$target" && pip install -r requirements-dev.txt 2>&1); then
            echo -e "    ${GREEN}✓${NC} pip install complete"
        else
            echo -e "    ${YELLOW}⚠${NC}  pip install failed"
        fi
    fi

    # .NET
    if ls "$target"/*.csproj "$target"/*.sln 1>/dev/null 2>&1; then
        echo -e "  Running dotnet restore..."
        if (cd "$target" && dotnet restore 2>&1); then
            echo -e "    ${GREEN}✓${NC} dotnet restore complete"
        else
            echo -e "    ${YELLOW}⚠${NC}  dotnet restore failed"
        fi
    fi
}

# --- Tool Summary ---
verify_all_tools() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Tool Installation Summary                                  ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Global tools
    echo -e "  ${YELLOW}Global Tools:${NC}"
    if command -v gitleaks &>/dev/null; then
        echo -e "    ${GREEN}✓${NC} gitleaks"
    else
        echo -e "    ${RED}✗${NC} gitleaks"
    fi

    if command -v gh &>/dev/null; then
        if gh auth status &>/dev/null 2>&1; then
            echo -e "    ${GREEN}✓${NC} gh (authenticated)"
        else
            echo -e "    ${YELLOW}⚠${NC} gh (not authenticated - run 'gh auth login')"
        fi
    else
        echo -e "    ${RED}✗${NC} gh"
    fi

    if command -v az &>/dev/null; then
        if az account show &>/dev/null 2>&1; then
            echo -e "    ${GREEN}✓${NC} az (authenticated)"
        else
            echo -e "    ${YELLOW}⚠${NC} az (not authenticated - run 'az login')"
        fi
    else
        echo -e "    ${YELLOW}-${NC} az (not required for GitHub)"
    fi

    echo ""
}

# =============================================================================
# SHARED COPY FUNCTIONS (used by both install and update)
# =============================================================================

# Copy skills from framework source to target.
# Args: $1=target_dir  $2=preserve_custom (true/false)
copy_skills() {
    local target="$1"
    local preserve_custom="${2:-true}"

    if [[ "$preserve_custom" == true ]]; then
        # Remove old framework skills (not custom)
        find "$target/.claude/skills" -maxdepth 2 -name "SKILL.md" -not -path "*/custom/*" -delete 2>/dev/null || true
        find "$target/.claude/skills" -maxdepth 2 -name "*.md" -not -path "*/custom/*" -not -name ".gitkeep" -delete 2>/dev/null || true
    fi

    if [[ -d "$SCRIPT_DIR/.claude/skills" ]]; then
        rsync -a --exclude='custom/' "$SCRIPT_DIR/.claude/skills/" "$target/.claude/skills/"
    fi
}

# Copy hooks from framework source to target.
# Args: $1=target_dir
copy_hooks() {
    local target="$1"

    mkdir -p "$target/.claude/hooks"
    if [[ -d "$SCRIPT_DIR/.claude/hooks" ]]; then
        cp "$SCRIPT_DIR/.claude/hooks/"*.sh "$target/.claude/hooks/" 2>/dev/null || true
        chmod +x "$target/.claude/hooks/"*.sh 2>/dev/null || true
    fi
}

# Copy agents from framework source to target.
# Args: $1=target_dir  $2=preserve_custom (true/false)
copy_agents() {
    local target="$1"
    local preserve_custom="${2:-true}"

    if [[ "$preserve_custom" == true ]]; then
        find "$target/.claude/agents" -maxdepth 1 -name "*.md" -not -path "*/custom/*" -delete 2>/dev/null || true
    fi

    if [[ -d "$SCRIPT_DIR/.claude/agents" ]]; then
        for agent in "$SCRIPT_DIR/.claude/agents/"*.md; do
            [[ -f "$agent" ]] && cp "$agent" "$target/.claude/agents/"
        done
        mkdir -p "$target/.claude/agents/custom"
        [[ -f "$SCRIPT_DIR/.claude/agents/custom/.gitkeep" ]] && cp "$SCRIPT_DIR/.claude/agents/custom/.gitkeep" "$target/.claude/agents/custom/"
    fi
}

# Copy standards from framework source to target.
# Args: $1=target_dir
copy_standards() {
    local target="$1"

    for file in "$SCRIPT_DIR/standards/"*.md; do
        [[ -f "$file" ]] && cp "$file" "$target/standards/"
    done
}

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
  copy_skills "$TARGET_DIR" true
  echo -e "  ${GREEN}✓${NC} Skills updated (custom/ preserved)"

  # --- Update hooks ---
  echo -e "${YELLOW}Updating hooks...${NC}"
  copy_hooks "$TARGET_DIR"
  echo -e "  ${GREEN}✓${NC} Hooks updated"

  # --- Update agents (preserve custom/) ---
  echo -e "${YELLOW}Updating agents...${NC}"
  copy_agents "$TARGET_DIR" true
  echo -e "  ${GREEN}✓${NC} Agents updated (custom/ preserved)"

  # --- Update standards ---
  echo -e "${YELLOW}Updating standards...${NC}"
  copy_standards "$TARGET_DIR"
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

  # --- Update CLAUDE.md (section-aware) ---
  echo -e "${YELLOW}Updating CLAUDE.md...${NC}"
  if [[ -f "$TARGET_DIR/CLAUDE.md" ]]; then
    if grep -q "<!-- BEGIN:AI-FRAMEWORK" "$TARGET_DIR/CLAUDE.md"; then
      # Has markers: extract team section, replace framework section
      echo -e "  ${GREEN}✓${NC} Found section markers, performing section-aware update"

      # Extract team section (everything between BEGIN:TEAM and END:TEAM)
      TEAM_SECTION=$(sed -n '/<!-- BEGIN:TEAM -->/,/<!-- END:TEAM -->/p' "$TARGET_DIR/CLAUDE.md")

      # If no team section found, create a default one
      if [[ -z "$TEAM_SECTION" ]]; then
        TEAM_SECTION='<!-- BEGIN:TEAM -->
## Project Overview

See [context/project.md](context/project.md) for full details.

<!-- Add team-specific rules, danger zones, or overrides below -->

<!-- END:TEAM -->'
      fi

      # Get framework section from source
      FRAMEWORK_SECTION=$(sed -n '/<!-- BEGIN:AI-FRAMEWORK/,/<!-- END:AI-FRAMEWORK -->/p' "$SCRIPT_DIR/CLAUDE.framework.md")

      # Combine: framework section + newline + team section
      {
        echo "$FRAMEWORK_SECTION"
        echo ""
        echo "$TEAM_SECTION"
      } > "$TARGET_DIR/CLAUDE.md"

      echo -e "  ${GREEN}✓${NC} CLAUDE.md updated (team section preserved)"
    else
      # No markers: warn, don't touch
      echo -e "  ${YELLOW}⚠${NC}  CLAUDE.md has no section markers"
      echo -e "  ${YELLOW}⚠${NC}  Run /migrate-claude-md to add markers, then re-run update"
      echo -e "  ${YELLOW}⚠${NC}  CLAUDE.md was NOT updated"
    fi
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
copy_hooks "$TARGET_DIR"
echo -e "  ${GREEN}✓${NC} Hook scripts (auto-format, security guards, notifications)"

# --- Copy agents ---
echo -e "${YELLOW}Copying agents...${NC}"
copy_agents "$TARGET_DIR" false

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

# =============================================================================
# TOOL INSTALLATION (when --install-tools is specified)
# =============================================================================
if [[ "$INSTALL_TOOLS" == true ]]; then
  echo ""
  echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║   Tool Installation                                          ║${NC}"
  echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
  echo ""

  # Detect system
  DETECTED_OS=$(detect_os)
  DETECTED_PKG_MGR=$(detect_package_manager "$DETECTED_OS")

  echo -e "  Detected: ${GREEN}$DETECTED_OS${NC} with ${GREEN}$DETECTED_PKG_MGR${NC}"
  echo ""

  # Check for Windows without WSL
  if [[ "$DETECTED_OS" == "windows" ]]; then
    echo -e "${RED}Error: Windows detected without WSL${NC}"
    echo -e "Git hooks require bash. Please install WSL and run this script from WSL."
    echo -e "  ${BLUE}https://docs.microsoft.com/en-us/windows/wsl/install${NC}"
    exit 1
  fi

  # Collect system info for error reporting
  collect_system_info "$DETECTED_OS" "$DETECTED_PKG_MGR"

  # --- Install Global Tools ---
  echo -e "${YELLOW}Installing global tools...${NC}"

  # gitleaks (always)
  install_gitleaks "$DETECTED_OS" "$DETECTED_PKG_MGR"

  # gh CLI (for GitHub platform)
  if [[ "$CICD" == "github" || "$CICD" == "both" || "$PLATFORM" == "github" ]]; then
    install_gh "$DETECTED_PKG_MGR"
  fi

  # az CLI (for Azure platform)
  if [[ "$CICD" == "azure" || "$CICD" == "both" || "$PLATFORM" == "azure" ]]; then
    install_az "$DETECTED_OS" "$DETECTED_PKG_MGR"
  fi

  echo ""

  # --- Verify SDKs ---
  if [[ "$SKIP_SDKS" != true ]]; then
    echo -e "${YELLOW}Verifying SDKs...${NC}"

    for stack in "${STACK_ARRAY[@]}"; do
      stack=$(echo "$stack" | xargs)
      case "$stack" in
        dotnet)
          verify_dotnet_sdk
          ;;
        typescript)
          verify_node_sdk
          ;;
        python)
          verify_python_sdk
          ;;
        terraform)
          verify_terraform_sdk
          install_tflint "$DETECTED_PKG_MGR"
          ;;
      esac
    done

    echo ""
  fi

  # --- Configure Project-Local Tools ---
  echo -e "${YELLOW}Configuring project-local tools...${NC}"

  for stack in "${STACK_ARRAY[@]}"; do
    stack=$(echo "$stack" | xargs)
    case "$stack" in
      typescript)
        configure_typescript_tools "$TARGET_DIR"
        ;;
      python)
        configure_python_tools "$TARGET_DIR"
        ;;
      terraform)
        configure_terraform_tools "$TARGET_DIR"
        ;;
    esac
  done

  echo ""

  # --- Configure Git Hooks ---
  echo -e "${YELLOW}Configuring git hooks...${NC}"
  configure_git_hooks "$TARGET_DIR"
  echo ""

  # --- Execute package installs (if --exec) ---
  if [[ "$EXEC_INSTALL" == true ]]; then
    execute_package_installs "$TARGET_DIR"
    echo ""
  fi

  # --- Tool Summary ---
  verify_all_tools

  # --- Error Reporting ---
  prompt_report_issue
fi

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
if [[ "$INSTALL_TOOLS" == true ]]; then
  echo ""
  echo -e "  For tool setup:"
  echo -e "  - Run ${BLUE}gh auth login${NC} to authenticate GitHub CLI"
  if [[ "$CICD" == "azure" || "$CICD" == "both" ]]; then
    echo -e "  - Run ${BLUE}az login${NC} to authenticate Azure CLI"
  fi
  echo -e "  - Pre-commit hook will scan for secrets before each commit"
  echo -e "  - Pre-push hook will check for vulnerabilities before each push"
fi
echo ""
