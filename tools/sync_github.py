#!/usr/bin/env python3
"""
Synchronize .ai/ content to .github/ for GitHub Copilot.

This script generates GitHub Copilot configuration files from the
.ai/ source of truth structure.

Usage:
    python sync_github.py [--force] [--dry-run]
"""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

# ANSI color codes for terminal output
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
GRAY = "\033[90m"
RESET = "\033[0m"


def get_paths() -> tuple[Path, Path, Path]:
    """Get the relevant paths for the sync operation."""
    script_dir = Path(__file__).parent
    ai_root = script_dir.parent
    repo_root = ai_root.parent
    github_dir = repo_root / ".github"
    return ai_root, repo_root, github_dir


def build_copilot_instructions(ai_root: Path) -> str:
    """Generate the copilot-instructions.md content."""
    logger.info(f"{YELLOW}Generating copilot-instructions.md...{RESET}")

    lines = [
        "# Copilot Instructions",
        "",
        "> Auto-generated from .ai/ structure. Do not edit directly.",
        "",
    ]

    # Include system prompt
    system_prompt = ai_root / "prompts" / "system.md"
    if system_prompt.exists():
        lines.append(system_prompt.read_text(encoding="utf-8"))
        lines.append("")

    # Include global standards
    global_standards = ai_root / "standards" / "global.md"
    if global_standards.exists():
        lines.append("## Global Standards")
        lines.append("")
        lines.append(global_standards.read_text(encoding="utf-8"))
        lines.append("")

    # Include learnings
    learnings_global = ai_root / "learnings" / "global.md"
    if learnings_global.exists():
        lines.append("## Learnings")
        lines.append("")
        lines.append(learnings_global.read_text(encoding="utf-8"))

    return "\n".join(lines)


def sync_stack_instructions(ai_root: Path, github_dir: Path, dry_run: bool) -> None:
    """Sync stack-specific instructions to .github/instructions/."""
    logger.info(f"{YELLOW}Syncing stack-specific instructions...{RESET}")

    standards_dir = ai_root / "standards"
    instructions_dir = github_dir / "instructions"

    stacks = ["dotnet", "typescript", "python", "infrastructure", "scripting", "cicd", "linters", "security"]

    for stack in stacks:
        stack_dir = standards_dir / stack
        if not stack_dir.exists():
            continue

        output_file = instructions_dir / f"{stack}.instructions.md"

        lines = [
            f"# {stack.upper()} Instructions",
            "",
            f"> Auto-generated from .ai/standards/{stack}/. Do not edit directly.",
            "",
        ]

        # Combine all .md files in the stack directory
        for md_file in sorted(stack_dir.rglob("*.md")):
            section_title = md_file.stem.replace("-", " ").upper()
            lines.append("")
            lines.append(f"## {section_title}")
            lines.append("")
            lines.append(md_file.read_text(encoding="utf-8"))

        content = "\n".join(lines)

        if not dry_run:
            output_file.write_text(content, encoding="utf-8")
            logger.info(f"   {GREEN}Created: {stack}.instructions.md{RESET}")
        else:
            logger.info(f"   {MAGENTA}[DryRun] Would create: {stack}.instructions.md{RESET}")


def sync_prompt_templates(ai_root: Path, github_dir: Path, dry_run: bool) -> None:
    """Sync prompt templates to .github/prompts/."""
    logger.info(f"{YELLOW}Syncing prompt templates...{RESET}")

    templates_dir = ai_root / "prompts" / "templates"
    github_prompts_dir = github_dir / "prompts"

    if not templates_dir.exists():
        return

    for template_file in templates_dir.glob("*.md"):
        output_file = github_prompts_dir / template_file.name

        if not dry_run:
            shutil.copy(template_file, output_file)
            logger.info(f"   {GREEN}Copied: {template_file.name}{RESET}")
        else:
            logger.info(f"   {MAGENTA}[DryRun] Would copy: {template_file.name}{RESET}")


@click.command()
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files without confirmation")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be done without making changes")
def main(force: bool, dry_run: bool) -> None:
    """Synchronize .ai/ content to .github/ for GitHub Copilot."""
    ai_root, repo_root, github_dir = get_paths()

    logger.info(f"{CYAN}Syncing .ai/ to .github/ for GitHub Copilot...{RESET}")
    logger.info(f"   {GRAY}Source: {ai_root}{RESET}")
    logger.info(f"   {GRAY}Target: {github_dir}{RESET}")

    # Ensure .github directory structure exists
    if not dry_run:
        github_dir.mkdir(parents=True, exist_ok=True)
        (github_dir / "instructions").mkdir(exist_ok=True)
        (github_dir / "prompts").mkdir(exist_ok=True)

    # Generate copilot-instructions.md
    copilot_instructions = build_copilot_instructions(ai_root)
    copilot_instructions_path = github_dir / "copilot-instructions.md"

    if not dry_run:
        copilot_instructions_path.write_text(copilot_instructions, encoding="utf-8")
        logger.info(f"   {GREEN}Created: copilot-instructions.md{RESET}")
    else:
        logger.info(f"   {MAGENTA}[DryRun] Would create: copilot-instructions.md{RESET}")

    # Sync stack-specific instructions
    sync_stack_instructions(ai_root, github_dir, dry_run)

    # Sync prompt templates
    sync_prompt_templates(ai_root, github_dir, dry_run)

    logger.info("")
    logger.info(f"{GREEN}Sync complete!{RESET}")

    if dry_run:
        logger.info(f"{YELLOW}This was a dry run. No files were modified.{RESET}")


if __name__ == "__main__":
    main()
