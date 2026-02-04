#!/usr/bin/env python3
"""
Update the ai-engineering package and optionally the .ai/ framework.

This command handles:
- Updating the ai-engineering CLI to the latest version
- Updating framework templates in existing projects
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import click

from ai_engineering import __version__
from ai_engineering.utils import colors, find_ai_root

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def get_latest_version() -> str | None:
    """Get the latest version from PyPI."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "index", "versions", "ai-engineering"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            # Parse output to get latest version
            output = result.stdout
            if "Available versions:" in output:
                versions_line = output.split("Available versions:")[1].strip()
                latest = versions_line.split(",")[0].strip()
                return latest
    except Exception:
        pass
    return None


def update_pip_package() -> bool:
    """Update ai-engineering package via pip."""
    logger.info(f"{colors.yellow}Updating ai-engineering package...{colors.reset}")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "ai-engineering"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            logger.info(f"   {colors.green}✅ Package updated successfully{colors.reset}")
            return True
        else:
            logger.info(f"   {colors.red}❌ Failed to update package{colors.reset}")
            logger.info(f"   {colors.gray}{result.stderr}{colors.reset}")
            return False
    except subprocess.TimeoutExpired:
        logger.info(f"   {colors.red}❌ Update timed out{colors.reset}")
        return False
    except Exception as e:
        logger.info(f"   {colors.red}❌ Error: {e}{colors.reset}")
        return False


@click.command("update")
@click.option("--check", "-c", is_flag=True, help="Only check for updates, don't install")
@click.option("--framework", "-f", is_flag=True, help="Also update framework templates in current project")
def update_cmd(check: bool, framework: bool) -> None:
    """Update ai-engineering to the latest version.

    This command updates the ai-engineering CLI tool to the latest version
    from PyPI. Optionally, it can also update framework templates
    in the current project.

    \b
    Examples:
        ai-engineering update              # Update CLI to latest
        ai-engineering update --check      # Check for updates only
        ai-engineering update --framework  # Update CLI and project templates
    """
    logger.info(f"{colors.cyan}🔄 AI Engineering Framework Update{colors.reset}")
    logger.info(f"   {colors.gray}Current version: {__version__}{colors.reset}")

    # Check for updates
    latest = get_latest_version()

    if latest:
        logger.info(f"   {colors.gray}Latest version: {latest}{colors.reset}")

        if latest == __version__:
            logger.info(f"\n{colors.green}✅ You are already on the latest version!{colors.reset}")
            if not framework:
                return
        elif check:
            logger.info(f"\n{colors.yellow}Update available: {__version__} → {latest}{colors.reset}")
            logger.info(f"   Run {colors.cyan}ai-engineering update{colors.reset} to install")
            return
        else:
            logger.info(f"\n{colors.yellow}Updating: {__version__} → {latest}{colors.reset}")
            if not update_pip_package():
                sys.exit(1)
    else:
        logger.info(f"   {colors.yellow}Could not check PyPI for latest version{colors.reset}")

        if check:
            return

        # Still try to update
        if not update_pip_package():
            sys.exit(1)

    # Update framework templates if requested
    if framework:
        ai_root = find_ai_root()
        if ai_root:
            logger.info(f"\n{colors.yellow}Updating framework templates...{colors.reset}")
            logger.info(f"   {colors.gray}Project: {ai_root}{colors.reset}")
            # TODO: Implement template update logic
            logger.info(f"   {colors.yellow}⚠️ Framework template updates not yet implemented{colors.reset}")
            logger.info(f"   {colors.gray}For now, please re-run 'ai-engineering init' with --force{colors.reset}")
        else:
            logger.info(f"\n{colors.yellow}No .ai/ directory found in current project{colors.reset}")

    logger.info(f"\n{colors.green}✅ Update complete!{colors.reset}")
