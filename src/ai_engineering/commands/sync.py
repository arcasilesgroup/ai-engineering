#!/usr/bin/env python3
"""
Synchronize .ai/ content to various AI tool configurations.

This command syncs the .ai/ framework content to:
- .github/ for GitHub Copilot
- .claude/ for Claude/Anthropic
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import click

from ai_engineering.utils import colors, find_ai_root, find_repo_root

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def build_copilot_instructions(ai_root: Path) -> str:
    """Generate the copilot-instructions.md content."""
    logger.info(f"{colors.yellow}Generating copilot-instructions.md...{colors.reset}")

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
    logger.info(f"{colors.yellow}Syncing stack-specific instructions...{colors.reset}")

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
            logger.info(f"   {colors.green}Created: {stack}.instructions.md{colors.reset}")
        else:
            logger.info(f"   {colors.magenta}[DryRun] Would create: {stack}.instructions.md{colors.reset}")


def sync_prompt_templates(ai_root: Path, github_dir: Path, dry_run: bool) -> None:
    """Sync prompt templates to .github/prompts/."""
    logger.info(f"{colors.yellow}Syncing prompt templates...{colors.reset}")

    templates_dir = ai_root / "prompts" / "templates"
    github_prompts_dir = github_dir / "prompts"

    if not templates_dir.exists():
        return

    for template_file in templates_dir.glob("*.md"):
        output_file = github_prompts_dir / template_file.name

        if not dry_run:
            shutil.copy(template_file, output_file)
            logger.info(f"   {colors.green}Copied: {template_file.name}{colors.reset}")
        else:
            logger.info(f"   {colors.magenta}[DryRun] Would copy: {template_file.name}{colors.reset}")


def sync_github(ai_root: Path, repo_root: Path, dry_run: bool) -> None:
    """Synchronize .ai/ content to .github/ for GitHub Copilot."""
    github_dir = repo_root / ".github"

    logger.info(f"{colors.cyan}Syncing .ai/ to .github/ for GitHub Copilot...{colors.reset}")
    logger.info(f"   {colors.gray}Source: {ai_root}{colors.reset}")
    logger.info(f"   {colors.gray}Target: {github_dir}{colors.reset}")

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
        logger.info(f"   {colors.green}Created: copilot-instructions.md{colors.reset}")
    else:
        logger.info(f"   {colors.magenta}[DryRun] Would create: copilot-instructions.md{colors.reset}")

    # Sync stack-specific instructions
    sync_stack_instructions(ai_root, github_dir, dry_run)

    # Sync prompt templates
    sync_prompt_templates(ai_root, github_dir, dry_run)


def build_claude_doc(ai_root: Path) -> str:
    """Generate the CLAUDE.md content."""
    logger.info(f"{colors.yellow}📝 Generating CLAUDE.md...{colors.reset}")

    lines = [
        "# CLAUDE.md - Project Documentation",
        "",
        "> Auto-generated from .ai/ structure. Do not edit directly.",
        "> Run `ai-engineering sync claude` to regenerate.",
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
    logger.info(f"{colors.yellow}📋 Syncing commands...{colors.reset}")

    templates_dir = ai_root / "prompts" / "templates"
    commands_dir = claude_dir / "commands"

    if not templates_dir.exists():
        logger.info(f"   {colors.gray}No templates found{colors.reset}")
        return

    for template_file in templates_dir.glob("*.md"):
        output_file = commands_dir / template_file.name

        if not dry_run:
            shutil.copy(template_file, output_file)
            logger.info(f"   {colors.green}Copied: {template_file.name}{colors.reset}")
        else:
            logger.info(f"   {colors.magenta}[DryRun] Would copy: {template_file.name}{colors.reset}")


def sync_stack_docs(ai_root: Path, claude_dir: Path, dry_run: bool) -> None:
    """Sync stack-specific documentation."""
    logger.info(f"{colors.yellow}📚 Syncing stack documentation...{colors.reset}")

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
            logger.info(f"   {colors.green}Created: {stack}-standards.md{colors.reset}")
        else:
            logger.info(f"   {colors.magenta}[DryRun] Would create: {stack}-standards.md{colors.reset}")


def sync_claude(ai_root: Path, repo_root: Path, dry_run: bool) -> None:
    """Synchronize .ai/ content to .claude/ for Claude/Anthropic."""
    claude_dir = repo_root / ".claude"

    logger.info(f"{colors.cyan}🔄 Syncing .ai/ to .claude/ for Claude/Anthropic...{colors.reset}")
    logger.info(f"   {colors.gray}Source: {ai_root}{colors.reset}")
    logger.info(f"   {colors.gray}Target: {claude_dir}{colors.reset}")

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
        logger.info(f"   {colors.green}Created: CLAUDE.md{colors.reset}")
    else:
        logger.info(f"   {colors.magenta}[DryRun] Would create: CLAUDE.md{colors.reset}")

    # Sync commands
    sync_commands(ai_root, claude_dir, dry_run)

    # Sync stack documentation
    sync_stack_docs(ai_root, claude_dir, dry_run)


@click.group("sync")
def sync_cmd() -> None:
    """Synchronize .ai/ content to AI tool configurations.

    This command syncs the .ai/ framework content to various AI tool
    configurations like GitHub Copilot and Claude.

    \b
    Examples:
        ai-engineering sync github          # Sync to GitHub Copilot
        ai-engineering sync claude          # Sync to Claude
        ai-engineering sync all             # Sync to all supported tools
        ai-engineering sync github --dry-run  # Preview changes
    """
    pass


@sync_cmd.command("github")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files without confirmation")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be done without making changes")
def sync_github_cmd(force: bool, dry_run: bool) -> None:
    """Sync .ai/ content to .github/ for GitHub Copilot.

    Generates copilot-instructions.md and stack-specific instruction files
    from the .ai/ framework content.
    """
    ai_root = find_ai_root()
    if not ai_root:
        logger.error(f"{colors.red}❌ No .ai/ directory found. Run 'ai-engineering init' first.{colors.reset}")
        raise SystemExit(1)

    repo_root = find_repo_root()
    if not repo_root:
        repo_root = ai_root.parent

    sync_github(ai_root, repo_root, dry_run)

    logger.info("")
    logger.info(f"{colors.green}✅ Sync complete!{colors.reset}")

    if dry_run:
        logger.info(f"{colors.yellow}This was a dry run. No files were modified.{colors.reset}")


@sync_cmd.command("claude")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files without confirmation")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be done without making changes")
def sync_claude_cmd(force: bool, dry_run: bool) -> None:
    """Sync .ai/ content to .claude/ for Claude/Anthropic.

    Generates CLAUDE.md and command files from the .ai/ framework content.
    """
    ai_root = find_ai_root()
    if not ai_root:
        logger.error(f"{colors.red}❌ No .ai/ directory found. Run 'ai-engineering init' first.{colors.reset}")
        raise SystemExit(1)

    repo_root = find_repo_root()
    if not repo_root:
        repo_root = ai_root.parent

    sync_claude(ai_root, repo_root, dry_run)

    logger.info("")
    logger.info(f"{colors.green}✅ Sync complete!{colors.reset}")

    if dry_run:
        logger.info(f"{colors.yellow}This was a dry run. No files were modified.{colors.reset}")


@sync_cmd.command("all")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files without confirmation")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be done without making changes")
def sync_all_cmd(force: bool, dry_run: bool) -> None:
    """Sync .ai/ content to all supported AI tools.

    Syncs to both GitHub Copilot (.github/) and Claude (.claude/).
    """
    ai_root = find_ai_root()
    if not ai_root:
        logger.error(f"{colors.red}❌ No .ai/ directory found. Run 'ai-engineering init' first.{colors.reset}")
        raise SystemExit(1)

    repo_root = find_repo_root()
    if not repo_root:
        repo_root = ai_root.parent

    sync_github(ai_root, repo_root, dry_run)
    logger.info("")
    sync_claude(ai_root, repo_root, dry_run)

    logger.info("")
    logger.info(f"{colors.green}✅ All syncs complete!{colors.reset}")

    if dry_run:
        logger.info(f"{colors.yellow}This was a dry run. No files were modified.{colors.reset}")
