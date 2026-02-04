#!/usr/bin/env python3
"""
Synchronize .ai/ content to .claude/ for Claude/Anthropic integration.

This script generates Claude configuration files from the
.ai/ source of truth structure.

Usage:
    python sync_claude.py [--force] [--dry-run]
"""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path

import click

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

# ANSI color codes
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
    claude_dir = repo_root / ".claude"
    return ai_root, repo_root, claude_dir


def build_claude_doc(ai_root: Path) -> str:
    """Generate the CLAUDE.md content."""
    logger.info(f"{YELLOW}📝 Generating CLAUDE.md...{RESET}")

    lines = [
        "# CLAUDE.md - Project Documentation",
        "",
        "> Auto-generated from .ai/ structure. Do not edit directly.",
        "> Run `.ai/tools/sync_claude.py` to regenerate.",
        "",
    ]

    # Include project context
    project_context = ai_root / "context" / "project.md"
    if project_context.exists():
        lines.append("## Project Context")
        lines.append("")
        lines.append(project_context.read_text(encoding="utf-8"))
        lines.append("")

    # Include architecture
    architecture = ai_root / "context" / "architecture.md"
    if architecture.exists():
        lines.append("## Architecture")
        lines.append("")
        lines.append(architecture.read_text(encoding="utf-8"))
        lines.append("")

    # Include system prompt
    system_prompt = ai_root / "prompts" / "system.md"
    if system_prompt.exists():
        lines.append("## Working Guidelines")
        lines.append("")
        lines.append(system_prompt.read_text(encoding="utf-8"))
        lines.append("")

    # Include global standards
    global_standards = ai_root / "standards" / "global.md"
    if global_standards.exists():
        lines.append("## Coding Standards")
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


def sync_commands(ai_root: Path, claude_dir: Path, dry_run: bool) -> None:
    """Sync prompt templates as Claude commands."""
    logger.info(f"{YELLOW}📋 Syncing commands...{RESET}")

    templates_dir = ai_root / "prompts" / "templates"
    commands_dir = claude_dir / "commands"

    if not templates_dir.exists():
        logger.info(f"   {GRAY}No templates found{RESET}")
        return

    for template_file in templates_dir.glob("*.md"):
        output_file = commands_dir / template_file.name

        if not dry_run:
            shutil.copy(template_file, output_file)
            logger.info(f"   {GREEN}Copied: {template_file.name}{RESET}")
        else:
            logger.info(f"   {MAGENTA}[DryRun] Would copy: {template_file.name}{RESET}")


def sync_stack_docs(ai_root: Path, claude_dir: Path, dry_run: bool) -> None:
    """Sync stack-specific documentation."""
    logger.info(f"{YELLOW}📚 Syncing stack documentation...{RESET}")

    standards_dir = ai_root / "standards"
    docs_dir = claude_dir / "docs"

    stacks = ["dotnet", "typescript", "python", "infrastructure", "scripting"]

    for stack in stacks:
        stack_dir = standards_dir / stack
        if not stack_dir.exists():
            continue

        output_file = docs_dir / f"{stack}-standards.md"

        lines = [
            f"# {stack.upper()} Standards",
            "",
            f"> Auto-generated from .ai/standards/{stack}/",
            "",
        ]

        for md_file in sorted(stack_dir.rglob("*.md")):
            section_title = md_file.stem.replace("-", " ").title()
            lines.append(f"## {section_title}")
            lines.append("")
            lines.append(md_file.read_text(encoding="utf-8"))
            lines.append("")

        content = "\n".join(lines)

        if not dry_run:
            output_file.write_text(content, encoding="utf-8")
            logger.info(f"   {GREEN}Created: {stack}-standards.md{RESET}")
        else:
            logger.info(f"   {MAGENTA}[DryRun] Would create: {stack}-standards.md{RESET}")


@click.command()
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files without confirmation")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be done without making changes")
def main(force: bool, dry_run: bool) -> None:
    """Synchronize .ai/ content to .claude/ for Claude/Anthropic."""
    ai_root, repo_root, claude_dir = get_paths()

    logger.info(f"{CYAN}🔄 Syncing .ai/ to .claude/ for Claude/Anthropic...{RESET}")
    logger.info(f"   {GRAY}Source: {ai_root}{RESET}")
    logger.info(f"   {GRAY}Target: {claude_dir}{RESET}")

    # Ensure .claude directory structure exists
    if not dry_run:
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / "commands").mkdir(exist_ok=True)
        (claude_dir / "docs").mkdir(exist_ok=True)

    # Generate CLAUDE.md
    claude_doc = build_claude_doc(ai_root)
    claude_doc_path = claude_dir / "CLAUDE.md"

    if not dry_run:
        claude_doc_path.write_text(claude_doc, encoding="utf-8")
        logger.info(f"   {GREEN}Created: CLAUDE.md{RESET}")
    else:
        logger.info(f"   {MAGENTA}[DryRun] Would create: CLAUDE.md{RESET}")

    # Sync commands
    sync_commands(ai_root, claude_dir, dry_run)

    # Sync stack documentation
    sync_stack_docs(ai_root, claude_dir, dry_run)

    logger.info("")
    logger.info(f"{GREEN}✅ Sync complete!{RESET}")

    if dry_run:
        logger.info(f"{YELLOW}This was a dry run. No files were modified.{RESET}")


if __name__ == "__main__":
    main()
