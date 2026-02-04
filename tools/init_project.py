#!/usr/bin/env python3
"""
Initialize the .ai/ framework in a new project.

This script sets up the .ai/ framework structure in a new project,
copying templates and creating necessary directories.

Usage:
    python init_project.py --name "MyProject" --stack dotnet [--include-examples]
"""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path
from typing import Literal

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
GRAY = "\033[90m"
RESET = "\033[0m"

StackType = Literal["dotnet", "typescript", "python", "terraform", "multi"]


def get_template_root() -> Path:
    """Get the template .ai/ root directory (current framework)."""
    script_dir = Path(__file__).parent
    return script_dir.parent


def create_directory_structure(ai_dir: Path, stack: StackType) -> None:
    """Create the directory structure."""
    directories = [
        "context",
        "context/decisions",
        "standards",
        f"standards/{stack}" if stack != "multi" else "standards/dotnet",
        "standards/cicd",
        "standards/linters",
        "standards/security",
        "prompts",
        "prompts/templates",
        "skills",
        f"skills/{stack}" if stack != "multi" else "skills/dotnet",
        "skills/cross-cutting",
        "agents",
        "learnings",
        "learnings/by-stack",
        "assets",
        "assets/svg",
        "tools",
    ]

    for dir_name in directories:
        dir_path = ai_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"   {GRAY}📁 Created: {dir_name}{RESET}")


def create_readme(ai_dir: Path, project_name: str) -> None:
    """Create README.md."""
    content = f"""# .ai/ Framework - {project_name}

This directory contains the AI-assisted development framework configuration.

## Structure

- **context/** - Project context and architecture documentation
- **standards/** - Coding standards by technology stack
- **prompts/** - Reusable prompt templates
- **skills/** - Procedural skills for common tasks
- **agents/** - Complex multi-step workflow orchestrators
- **learnings/** - Accumulated knowledge and patterns
- **tools/** - Synchronization and utility scripts

## Usage

### Sync to GitHub Copilot
```bash
python .ai/tools/sync_github.py
```

### Sync to Claude
```bash
python .ai/tools/sync_claude.py
```

### Validate Framework
```bash
python .ai/tools/validate.py
```

## Configuration

Edit `config.yaml` to customize the framework behavior.
"""
    (ai_dir / "README.md").write_text(content, encoding="utf-8")
    logger.info(f"   {GREEN}📄 Created: README.md{RESET}")


def create_config(ai_dir: Path, project_name: str, stack: StackType) -> None:
    """Create config.yaml."""
    content = f"""# .ai/ Framework Configuration
version: "1.0"

project:
  name: "{project_name}"
  stack: "{stack}"

sync:
  github:
    enabled: true
    target: ".github"
  claude:
    enabled: true
    target: ".claude"

validation:
  require_descriptions: true
  require_examples: true
"""
    (ai_dir / "config.yaml").write_text(content, encoding="utf-8")
    logger.info(f"   {GREEN}📄 Created: config.yaml{RESET}")


def create_context_files(ai_dir: Path, project_name: str, stack: StackType) -> None:
    """Create context files."""
    # project.md
    project_content = f"""# {project_name}

## Overview

[Brief description of the project]

## Goals

- [Goal 1]
- [Goal 2]

## Scope

[What's in scope and out of scope]
"""
    (ai_dir / "context" / "project.md").write_text(project_content, encoding="utf-8")
    logger.info(f"   {GREEN}📄 Created: context/project.md{RESET}")


def create_standards_files(ai_dir: Path) -> None:
    """Create standards files."""
    global_content = """# Global Standards

> Cross-stack rules applicable to all code.

## Core Principles

1. **Security First** - Never hardcode secrets
2. **Quality by Design** - Write tests alongside code
3. **Consistency** - Follow existing patterns
4. **Maintainability** - Prefer explicit over implicit
"""
    (ai_dir / "standards" / "global.md").write_text(global_content, encoding="utf-8")
    logger.info(f"   {GREEN}📄 Created: standards/global.md{RESET}")


def create_prompts_files(ai_dir: Path) -> None:
    """Create prompts files."""
    system_content = """# System Prompt

You are an expert software engineering assistant.

## Your Role

- Provide high-quality, production-ready code
- Follow established patterns and standards
- Prioritize security, maintainability, and performance
"""
    (ai_dir / "prompts" / "system.md").write_text(system_content, encoding="utf-8")
    logger.info(f"   {GREEN}📄 Created: prompts/system.md{RESET}")

    index_content = """# Prompt Templates Index

templates:
  - id: code-review
    name: "Code Review"
    file: "templates/code-review.md"
"""
    (ai_dir / "prompts" / "_index.yaml").write_text(index_content, encoding="utf-8")
    logger.info(f"   {GREEN}📄 Created: prompts/_index.yaml{RESET}")


def create_skills_files(ai_dir: Path) -> None:
    """Create skills index."""
    index_content = """# Skills Index

skills: []
"""
    (ai_dir / "skills" / "_index.yaml").write_text(index_content, encoding="utf-8")
    logger.info(f"   {GREEN}📄 Created: skills/_index.yaml{RESET}")


def create_agents_files(ai_dir: Path) -> None:
    """Create agents index."""
    index_content = """# Agents Index

agents: []
"""
    (ai_dir / "agents" / "_index.yaml").write_text(index_content, encoding="utf-8")
    logger.info(f"   {GREEN}📄 Created: agents/_index.yaml{RESET}")


def create_learnings_files(ai_dir: Path) -> None:
    """Create learnings files."""
    global_content = """# Global Learnings

This file captures cross-cutting learnings that apply across all technology stacks.

## Format

```markdown
### [Date] Learning Title

**Context:** Brief description of when this applies
**Learning:** What was learned
**Rationale:** Why this matters
```

## Learnings

[Add learnings here as the project evolves]
"""
    (ai_dir / "learnings" / "global.md").write_text(global_content, encoding="utf-8")
    logger.info(f"   {GREEN}📄 Created: learnings/global.md{RESET}")


def copy_tools(ai_dir: Path, template_root: Path) -> None:
    """Copy tool scripts from template."""
    tools_source = template_root / "tools"
    tools_target = ai_dir / "tools"

    tool_files = [
        "sync_github.py",
        "sync_claude.py",
        "validate.py",
        "init_project.py",
    ]

    for tool_file in tool_files:
        source = tools_source / tool_file
        if source.exists():
            shutil.copy(source, tools_target / tool_file)
            logger.info(f"   {GREEN}📄 Copied: tools/{tool_file}{RESET}")


def copy_linter_configs(ai_dir: Path, template_root: Path) -> None:
    """Copy linter configurations from template."""
    linters_source = template_root / "standards" / "linters"
    linters_target = ai_dir / "standards" / "linters"

    if linters_source.exists():
        for config_file in linters_source.glob("*.md"):
            shutil.copy(config_file, linters_target / config_file.name)
            logger.info(f"   {GREEN}📄 Copied: standards/linters/{config_file.name}{RESET}")


def copy_cicd_configs(ai_dir: Path, template_root: Path) -> None:
    """Copy CI/CD configurations from template."""
    cicd_source = template_root / "standards" / "cicd"
    cicd_target = ai_dir / "standards" / "cicd"

    if cicd_source.exists():
        for config_file in cicd_source.glob("*.md"):
            shutil.copy(config_file, cicd_target / config_file.name)
            logger.info(f"   {GREEN}📄 Copied: standards/cicd/{config_file.name}{RESET}")


def copy_security_configs(ai_dir: Path, template_root: Path) -> None:
    """Copy security configurations from template."""
    security_source = template_root / "standards" / "security"
    security_target = ai_dir / "standards" / "security"

    if security_source.exists():
        for config_file in security_source.glob("*.md"):
            shutil.copy(config_file, security_target / config_file.name)
            logger.info(f"   {GREEN}📄 Copied: standards/security/{config_file.name}{RESET}")


@click.command()
@click.option("--name", "-n", required=True, help="Name of the project")
@click.option(
    "--stack",
    "-s",
    required=True,
    type=click.Choice(["dotnet", "typescript", "python", "terraform", "multi"]),
    help="Primary technology stack",
)
@click.option("--include-examples", "-e", is_flag=True, help="Include example files for reference")
@click.option("--target", "-t", default=".", help="Target directory (default: current)")
def main(name: str, stack: str, include_examples: bool, target: str) -> None:
    """Initialize the .ai/ framework in a new project."""
    target_dir = Path(target).resolve()
    ai_dir = target_dir / ".ai"
    template_root = get_template_root()

    logger.info(f"{CYAN}🚀 Initializing .ai/ framework for {name}...{RESET}")
    logger.info(f"   {GRAY}Stack: {stack}{RESET}")
    logger.info(f"   {GRAY}Target: {ai_dir}{RESET}")

    # Check if already exists
    if ai_dir.exists():
        if not click.confirm(f"\n{YELLOW}.ai/ already exists. Overwrite?{RESET}"):
            logger.info("Aborted.")
            sys.exit(0)
        shutil.rmtree(ai_dir)

    # Create structure
    logger.info(f"\n{YELLOW}Creating directory structure...{RESET}")
    create_directory_structure(ai_dir, stack)

    # Create base files
    logger.info(f"\n{YELLOW}Creating base files...{RESET}")
    create_readme(ai_dir, name)
    create_config(ai_dir, name, stack)
    create_context_files(ai_dir, name, stack)
    create_standards_files(ai_dir)
    create_prompts_files(ai_dir)
    create_skills_files(ai_dir)
    create_agents_files(ai_dir)
    create_learnings_files(ai_dir)

    # Copy tools
    logger.info(f"\n{YELLOW}Copying tools...{RESET}")
    copy_tools(ai_dir, template_root)

    # Copy configurations
    logger.info(f"\n{YELLOW}Copying linter configurations...{RESET}")
    copy_linter_configs(ai_dir, template_root)

    logger.info(f"\n{YELLOW}Copying CI/CD configurations...{RESET}")
    copy_cicd_configs(ai_dir, template_root)

    logger.info(f"\n{YELLOW}Copying security configurations...{RESET}")
    copy_security_configs(ai_dir, template_root)

    # Summary
    logger.info(f"\n{GREEN}✅ .ai/ framework initialized successfully!{RESET}")
    logger.info(f"\n{CYAN}Next steps:{RESET}")
    logger.info(f"   1. Edit {GRAY}.ai/context/project.md{RESET} with your project details")
    logger.info(f"   2. Add stack-specific standards in {GRAY}.ai/standards/{stack}/{RESET}")
    logger.info(f"   3. Run {GRAY}python .ai/tools/sync_github.py{RESET} to sync to GitHub Copilot")


if __name__ == "__main__":
    main()
