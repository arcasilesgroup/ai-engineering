#!/usr/bin/env bash
# =============================================================================
# AI Engineering Framework (ai-engineering) Installer
# =============================================================================
# This script installs ai-engineering CLI tool on Linux and macOS.
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/install.sh | bash
#
# Or with a specific version:
#   curl -sSL https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/install.sh | bash -s -- --version 1.0.0
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PACKAGE_NAME="ai-engineering"
MIN_PYTHON_VERSION="3.9"
GITHUB_REPO="arcasilesgroup/ai-engineering"

# Parse arguments
VERSION=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --version|-v)
            VERSION="$2"
            shift 2
            ;;
        --help|-h)
            echo "AI Engineering Framework Installer"
            echo ""
            echo "Usage: install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --version, -v VERSION  Install a specific version"
            echo "  --help, -h             Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)     OS="linux";;
        Darwin*)    OS="macos";;
        CYGWIN*|MINGW*|MSYS*)
            echo -e "${YELLOW}For Windows, please use install.ps1 instead:${NC}"
            echo "  iwr -useb https://raw.githubusercontent.com/${GITHUB_REPO}/main/install.ps1 | iex"
            exit 1
            ;;
        *)
            echo -e "${RED}Unsupported operating system: $(uname -s)${NC}"
            exit 1
            ;;
    esac
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Compare Python versions
version_gte() {
    # Returns 0 if $1 >= $2
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# Find suitable Python
find_python() {
    local python_cmd=""

    # Try python3 first
    if command_exists python3; then
        python_cmd="python3"
    elif command_exists python; then
        python_cmd="python"
    fi

    if [ -n "$python_cmd" ]; then
        local version
        version=$($python_cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

        if version_gte "$version" "$MIN_PYTHON_VERSION"; then
            echo "$python_cmd"
            return 0
        fi
    fi

    return 1
}

# Install Python if not found
install_python() {
    echo -e "${YELLOW}Python $MIN_PYTHON_VERSION or higher not found.${NC}"
    echo ""

    if [ "$OS" = "macos" ]; then
        if command_exists brew; then
            echo -e "${CYAN}Installing Python via Homebrew...${NC}"
            brew install python@3.11
        else
            echo -e "${YELLOW}Homebrew not found. Please install Python manually:${NC}"
            echo "  1. Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            echo "  2. Install Python: brew install python@3.11"
            exit 1
        fi
    elif [ "$OS" = "linux" ]; then
        # Detect package manager
        if command_exists apt-get; then
            echo -e "${CYAN}Installing Python via apt...${NC}"
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv
        elif command_exists dnf; then
            echo -e "${CYAN}Installing Python via dnf...${NC}"
            sudo dnf install -y python3 python3-pip
        elif command_exists yum; then
            echo -e "${CYAN}Installing Python via yum...${NC}"
            sudo yum install -y python3 python3-pip
        elif command_exists pacman; then
            echo -e "${CYAN}Installing Python via pacman...${NC}"
            sudo pacman -S --noconfirm python python-pip
        elif command_exists zypper; then
            echo -e "${CYAN}Installing Python via zypper...${NC}"
            sudo zypper install -y python3 python3-pip
        else
            echo -e "${RED}Could not detect package manager. Please install Python $MIN_PYTHON_VERSION+ manually.${NC}"
            exit 1
        fi
    fi
}

# Ensure pip is available
ensure_pip() {
    local python_cmd="$1"

    if ! $python_cmd -m pip --version >/dev/null 2>&1; then
        echo -e "${YELLOW}pip not found. Installing...${NC}"
        $python_cmd -m ensurepip --upgrade 2>/dev/null || {
            curl -sSL https://bootstrap.pypa.io/get-pip.py | $python_cmd
        }
    fi
}

# Install ai-engineering
install_ai_engineering() {
    local python_cmd="$1"
    local pip_args=("install" "--upgrade" "$PACKAGE_NAME")

    if [ -n "$VERSION" ]; then
        pip_args=("install" "--upgrade" "${PACKAGE_NAME}==${VERSION}")
    fi

    echo -e "${CYAN}Installing ai-engineering...${NC}"
    $python_cmd -m pip "${pip_args[@]}"
}

# Verify installation
verify_installation() {
    if command_exists ai-engineering; then
        local installed_version
        installed_version=$(ai-engineering --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
        echo ""
        echo -e "${GREEN}✅ ai-engineering installed successfully!${NC}"
        echo -e "   Version: ${CYAN}${installed_version}${NC}"
        echo ""
        echo -e "${CYAN}Quick Start:${NC}"
        echo "   ai-engineering init --name \"MyProject\" --stack dotnet"
        echo "   ai-engineering sync github"
        echo "   ai-engineering validate"
        echo ""
        echo -e "${CYAN}For help:${NC}"
        echo "   ai-engineering --help"
    else
        echo ""
        echo -e "${YELLOW}⚠️  ai-engineering installed but not found in PATH.${NC}"
        echo ""
        echo "You may need to add Python's bin directory to your PATH:"
        echo ""
        if [ "$OS" = "macos" ]; then
            echo '  echo '\''export PATH="$HOME/Library/Python/3.11/bin:$PATH"'\'' >> ~/.zshrc'
            echo '  source ~/.zshrc'
        else
            echo '  echo '\''export PATH="$HOME/.local/bin:$PATH"'\'' >> ~/.bashrc'
            echo '  source ~/.bashrc'
        fi
        echo ""
        echo "Then run: ai-engineering --help"
    fi
}

# Main installation flow
main() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║        AI Engineering Framework (ai-engineering) Installer     ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Detect OS
    detect_os
    echo -e "Detected OS: ${CYAN}${OS}${NC}"

    # Find or install Python
    local python_cmd
    if python_cmd=$(find_python); then
        local version
        version=$($python_cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        echo -e "Found Python: ${CYAN}${python_cmd}${NC} (${version})"
    else
        install_python
        python_cmd=$(find_python) || {
            echo -e "${RED}Failed to install Python. Please install manually.${NC}"
            exit 1
        }
    fi

    # Ensure pip
    ensure_pip "$python_cmd"

    # Install ai-engineering
    install_ai_engineering "$python_cmd"

    # Verify
    verify_installation
}

main
