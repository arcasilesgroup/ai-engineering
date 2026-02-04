#!/usr/bin/env python3
"""
Synchronize .ai/ content to .github/ for GitHub Copilot.
Simple version without external dependencies.

Usage:
    python sync_github_simple.py [--dry-run]
"""

import sys
import shutil
from pathlib import Path


def get_paths():
    """Get the relevant paths for the sync operation."""
    script_dir = Path(__file__).parent
    ai_root = script_dir.parent
    repo_root = ai_root.parent
    github_dir = repo_root / ".github"
    return ai_root, repo_root, github_dir


def build_copilot_instructions(ai_root: Path) -> str:
    """Generate the copilot-instructions.md content."""
    print("  Generating copilot-instructions.md...")

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
    print("  Syncing stack-specific instructions...")

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
            print(f"    Created: {stack}.instructions.md")
        else:
            print(f"    [DryRun] Would create: {stack}.instructions.md")


def sync_prompt_templates(ai_root: Path, github_dir: Path, dry_run: bool) -> None:
    """Sync prompt templates to .github/prompts/."""
    print("  Syncing prompt templates...")

    templates_dir = ai_root / "prompts" / "templates"
    github_prompts_dir = github_dir / "prompts"

    if not templates_dir.exists():
        return

    for template_file in templates_dir.glob("*.md"):
        output_file = github_prompts_dir / template_file.name

        if not dry_run:
            shutil.copy(template_file, output_file)
            print(f"    Copied: {template_file.name}")
        else:
            print(f"    [DryRun] Would copy: {template_file.name}")


def main():
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    ai_root, repo_root, github_dir = get_paths()

    print("Syncing .ai/ to .github/ for GitHub Copilot...")
    print(f"  Source: {ai_root}")
    print(f"  Target: {github_dir}")

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
        print("    Created: copilot-instructions.md")
    else:
        print("    [DryRun] Would create: copilot-instructions.md")

    # Sync stack-specific instructions
    sync_stack_instructions(ai_root, github_dir, dry_run)

    # Sync prompt templates
    sync_prompt_templates(ai_root, github_dir, dry_run)

    print("")
    print("Sync complete!")

    if dry_run:
        print("This was a dry run. No files were modified.")


if __name__ == "__main__":
    main()
