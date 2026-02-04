#!/usr/bin/env python3
"""
Initialize the .ai/ framework in a new project.

This command sets up the .ai/ framework structure in a new project,
copying templates and creating necessary directories.
"""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path
from typing import Literal, Optional

import click

from ai_engineering.utils import colors, get_templates_dir

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

StackType = Literal["dotnet", "typescript", "python", "terraform", "multi"]


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
        logger.info(f"   {colors.gray}📁 Created: {dir_name}{colors.reset}")


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

### Using ai-engineering CLI (Recommended)

```bash
# Sync to GitHub Copilot
ai-engineering sync github

# Sync to Claude
ai-engineering sync claude

# Validate Framework
ai-engineering validate

# Update framework to latest version
ai-engineering update
```

### Using Python scripts directly

```bash
python .ai/tools/sync_github.py
python .ai/tools/sync_claude.py
python .ai/tools/validate.py
```

## Configuration

Edit `config.yaml` to customize the framework behavior.
"""
    (ai_dir / "README.md").write_text(content, encoding="utf-8")
    logger.info(f"   {colors.green}📄 Created: README.md{colors.reset}")


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
    logger.info(f"   {colors.green}📄 Created: config.yaml{colors.reset}")


def create_context_files(ai_dir: Path, project_name: str, stack: StackType) -> None:
    """Create context files."""
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
    logger.info(f"   {colors.green}📄 Created: context/project.md{colors.reset}")


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
    logger.info(f"   {colors.green}📄 Created: standards/global.md{colors.reset}")

    # Create _index.yaml
    index_content = """# Standards Index

standards: []
"""
    (ai_dir / "standards" / "_index.yaml").write_text(index_content, encoding="utf-8")
    logger.info(f"   {colors.green}📄 Created: standards/_index.yaml{colors.reset}")


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
    logger.info(f"   {colors.green}📄 Created: prompts/system.md{colors.reset}")

    index_content = """# Prompt Templates Index

templates:
  - id: code-review
    name: "Code Review"
    file: "templates/code-review.md"
"""
    (ai_dir / "prompts" / "_index.yaml").write_text(index_content, encoding="utf-8")
    logger.info(f"   {colors.green}📄 Created: prompts/_index.yaml{colors.reset}")


def create_skills_files(ai_dir: Path) -> None:
    """Create skills index."""
    index_content = """# Skills Index

skills: []
"""
    (ai_dir / "skills" / "_index.yaml").write_text(index_content, encoding="utf-8")
    logger.info(f"   {colors.green}📄 Created: skills/_index.yaml{colors.reset}")


def create_agents_files(ai_dir: Path) -> None:
    """Create agents index."""
    index_content = """# Agents Index

agents: []
"""
    (ai_dir / "agents" / "_index.yaml").write_text(index_content, encoding="utf-8")
    logger.info(f"   {colors.green}📄 Created: agents/_index.yaml{colors.reset}")


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
    logger.info(f"   {colors.green}📄 Created: learnings/global.md{colors.reset}")


def copy_from_templates(ai_dir: Path, templates_dir: Path, stack: StackType) -> None:
    """Copy template files if available."""
    # Copy linter configs
    linters_source = templates_dir / "standards" / "linters"
    linters_target = ai_dir / "standards" / "linters"

    if linters_source.exists():
        for config_file in linters_source.glob("*.md"):
            shutil.copy(config_file, linters_target / config_file.name)
            logger.info(f"   {colors.green}📄 Copied: standards/linters/{config_file.name}{colors.reset}")

    # Copy CI/CD configs
    cicd_source = templates_dir / "standards" / "cicd"
    cicd_target = ai_dir / "standards" / "cicd"

    if cicd_source.exists():
        for config_file in cicd_source.glob("*.md"):
            shutil.copy(config_file, cicd_target / config_file.name)
            logger.info(f"   {colors.green}📄 Copied: standards/cicd/{config_file.name}{colors.reset}")

    # Copy security configs
    security_source = templates_dir / "standards" / "security"
    security_target = ai_dir / "standards" / "security"

    if security_source.exists():
        for config_file in security_source.glob("*.md"):
            shutil.copy(config_file, security_target / config_file.name)
            logger.info(f"   {colors.green}📄 Copied: standards/security/{config_file.name}{colors.reset}")

    # Copy stack-specific standards
    stack_source = templates_dir / "standards" / stack
    stack_target = ai_dir / "standards" / stack

    if stack_source.exists() and stack != "multi":
        stack_target.mkdir(parents=True, exist_ok=True)
        for md_file in stack_source.rglob("*.md"):
            rel_path = md_file.relative_to(stack_source)
            target_file = stack_target / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(md_file, target_file)
            logger.info(f"   {colors.green}📄 Copied: standards/{stack}/{rel_path}{colors.reset}")


def copy_legacy_tools(ai_dir: Path, templates_dir: Path) -> None:
    """Copy legacy Python tool scripts for backwards compatibility."""
    tools_source = templates_dir / "tools"
    tools_target = ai_dir / "tools"

    if not tools_source.exists():
        # If running from installed package, tools might not be in templates
        # Create minimal wrapper scripts instead
        create_wrapper_scripts(tools_target)
        return

    tool_files = [
        "sync_github.py",
        "sync_github_simple.py",
        "sync_claude.py",
        "validate.py",
    ]

    for tool_file in tool_files:
        source = tools_source / tool_file
        if source.exists():
            shutil.copy(source, tools_target / tool_file)
            logger.info(f"   {colors.green}📄 Copied: tools/{tool_file}{colors.reset}")


def create_wrapper_scripts(tools_dir: Path) -> None:
    """Create wrapper scripts that call ai-engineering CLI."""
    tools_dir.mkdir(parents=True, exist_ok=True)

    # sync_github.py wrapper
    sync_github = '''#!/usr/bin/env python3
"""Wrapper script for ai-engineering sync github command."""
import subprocess
import sys

if __name__ == "__main__":
    sys.exit(subprocess.call(["ai-engineering", "sync", "github"] + sys.argv[1:]))
'''
    (tools_dir / "sync_github.py").write_text(sync_github, encoding="utf-8")

    # sync_claude.py wrapper
    sync_claude = '''#!/usr/bin/env python3
"""Wrapper script for ai-engineering sync claude command."""
import subprocess
import sys

if __name__ == "__main__":
    sys.exit(subprocess.call(["ai-engineering", "sync", "claude"] + sys.argv[1:]))
'''
    (tools_dir / "sync_claude.py").write_text(sync_claude, encoding="utf-8")

    # validate.py wrapper
    validate = '''#!/usr/bin/env python3
"""Wrapper script for ai-engineering validate command."""
import subprocess
import sys

if __name__ == "__main__":
    sys.exit(subprocess.call(["ai-engineering", "validate"] + sys.argv[1:]))
'''
    (tools_dir / "validate.py").write_text(validate, encoding="utf-8")

    logger.info(f"   {colors.green}📄 Created: tools/sync_github.py (wrapper){colors.reset}")
    logger.info(f"   {colors.green}📄 Created: tools/sync_claude.py (wrapper){colors.reset}")
    logger.info(f"   {colors.green}📄 Created: tools/validate.py (wrapper){colors.reset}")


@click.command("init")
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
@click.option("--force", "-f", is_flag=True, help="Overwrite existing .ai/ directory without confirmation")
def init_cmd(name: str, stack: str, include_examples: bool, target: str, force: bool) -> None:
    """Initialize the .ai/ framework in a new project.

    This command creates the complete .ai/ directory structure with all necessary
    files and configurations for AI-assisted development.

    \b
    Examples:
        ai-engineering init --name "MyAPI" --stack dotnet
        ai-engineering init --name "WebApp" --stack typescript --target ./my-project
        ai-engineering init -n "DataPipeline" -s python -e
    """
    target_dir = Path(target).resolve()
    ai_dir = target_dir / ".ai"
    templates_dir = get_templates_dir()

    logger.info(f"{colors.cyan}🚀 Initializing .ai/ framework for {name}...{colors.reset}")
    logger.info(f"   {colors.gray}Stack: {stack}{colors.reset}")
    logger.info(f"   {colors.gray}Target: {ai_dir}{colors.reset}")

    # Check if already exists
    if ai_dir.exists():
        if not force and not click.confirm(f"\n{colors.yellow}.ai/ already exists. Overwrite?{colors.reset}"):
            logger.info("Aborted.")
            sys.exit(0)
        shutil.rmtree(ai_dir)

    # Create structure
    logger.info(f"\n{colors.yellow}Creating directory structure...{colors.reset}")
    create_directory_structure(ai_dir, stack)

    # Create base files
    logger.info(f"\n{colors.yellow}Creating base files...{colors.reset}")
    create_readme(ai_dir, name)
    create_config(ai_dir, name, stack)
    create_context_files(ai_dir, name, stack)
    create_standards_files(ai_dir)
    create_prompts_files(ai_dir)
    create_skills_files(ai_dir)
    create_agents_files(ai_dir)
    create_learnings_files(ai_dir)

    # Copy from templates if available
    if templates_dir.exists():
        logger.info(f"\n{colors.yellow}Copying template configurations...{colors.reset}")
        copy_from_templates(ai_dir, templates_dir, stack)

    # Create/copy tools
    logger.info(f"\n{colors.yellow}Setting up tools...{colors.reset}")
    copy_legacy_tools(ai_dir, templates_dir)

    # Summary
    logger.info(f"\n{colors.green}✅ .ai/ framework initialized successfully!{colors.reset}")
    logger.info(f"\n{colors.cyan}Next steps:{colors.reset}")
    logger.info(f"   1. Edit {colors.gray}.ai/context/project.md{colors.reset} with your project details")
    logger.info(f"   2. Add stack-specific standards in {colors.gray}.ai/standards/{stack}/{colors.reset}")
    logger.info(f"   3. Run {colors.gray}ai-engineering sync github{colors.reset} to sync to GitHub Copilot")
    logger.info(f"   4. Run {colors.gray}ai-engineering sync claude{colors.reset} to sync to Claude")
