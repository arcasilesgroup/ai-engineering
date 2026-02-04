#!/usr/bin/env python3
"""
Validate the .ai/ framework structure and content.

This script checks the .ai/ framework for:
- Required files and directories
- YAML syntax validity
- Markdown structure consistency
- Cross-references between files
- Missing or broken links

Usage:
    python validate.py [--fix] [--verbose]
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click
import yaml

if TYPE_CHECKING:
    pass

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
RED = "\033[91m"
GRAY = "\033[90m"
RESET = "\033[0m"


class ValidationResult:
    """Holds validation results."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []


def get_ai_root() -> Path:
    """Get the .ai/ root directory."""
    script_dir = Path(__file__).parent
    return script_dir.parent


def test_required_directories(ai_root: Path, result: ValidationResult, fix: bool) -> None:
    """Check required directories exist."""
    logger.info(f"\n{YELLOW}📁 Checking required directories...{RESET}")

    required_dirs = [
        "context",
        "context/decisions",
        "standards",
        "standards/cicd",
        "standards/linters",
        "standards/security",
        "prompts",
        "prompts/templates",
        "skills",
        "agents",
        "learnings",
        "tools",
    ]

    for dir_name in required_dirs:
        dir_path = ai_root / dir_name
        if dir_path.exists():
            logger.info(f"   {GREEN}✅ {dir_name}{RESET}")
        else:
            logger.info(f"   {RED}❌ {dir_name} (missing){RESET}")
            result.errors.append(f"Missing required directory: {dir_name}")

            if fix:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"      {CYAN}→ Created{RESET}")


def test_required_files(ai_root: Path, result: ValidationResult) -> None:
    """Check required files exist."""
    logger.info(f"\n{YELLOW}📄 Checking required files...{RESET}")

    required_files = [
        "README.md",
        "config.yaml",
        "context/project.md",
        "standards/global.md",
        "prompts/system.md",
        "prompts/_index.yaml",
        "skills/_index.yaml",
        "agents/_index.yaml",
        "learnings/global.md",
    ]

    for file_name in required_files:
        file_path = ai_root / file_name
        if file_path.exists():
            logger.info(f"   {GREEN}✅ {file_name}{RESET}")
        else:
            logger.info(f"   {RED}❌ {file_name} (missing){RESET}")
            result.errors.append(f"Missing required file: {file_name}")


def test_yaml_files(ai_root: Path, result: ValidationResult) -> None:
    """Validate YAML files."""
    logger.info(f"\n{YELLOW}📋 Validating YAML files...{RESET}")

    for yaml_file in ai_root.rglob("*.yaml"):
        relative_path = yaml_file.relative_to(ai_root)

        try:
            content = yaml_file.read_text(encoding="utf-8")

            # Check for tabs (YAML should use spaces)
            if "\t" in content:
                logger.info(f"   {YELLOW}⚠️ {relative_path} (contains tabs){RESET}")
                result.warnings.append(f"YAML file contains tabs: {relative_path}")
            else:
                # Try to parse YAML
                yaml.safe_load(content)
                logger.info(f"   {GREEN}✅ {relative_path}{RESET}")

        except yaml.YAMLError as e:
            logger.info(f"   {RED}❌ {relative_path} (invalid YAML){RESET}")
            result.errors.append(f"Invalid YAML: {relative_path} - {e}")
        except Exception as e:
            logger.info(f"   {RED}❌ {relative_path} (error reading){RESET}")
            result.errors.append(f"Error reading: {relative_path} - {e}")


def test_cross_references(ai_root: Path, result: ValidationResult) -> None:
    """Check cross-references between files."""
    logger.info(f"\n{YELLOW}🔗 Checking cross-references...{RESET}")

    agents_index = ai_root / "agents" / "_index.yaml"
    skills_index = ai_root / "skills" / "_index.yaml"

    if agents_index.exists() and skills_index.exists():
        try:
            agents_content = agents_index.read_text(encoding="utf-8")
            skills_content = skills_index.read_text(encoding="utf-8")

            # Extract skill IDs from skills index
            skill_ids = set(re.findall(r"^\s*-\s*id:\s*(.+)$", skills_content, re.MULTILINE))

            # Extract skill references from agents (lines with /)
            agent_skill_refs = set(
                ref
                for ref in re.findall(r"^\s*-\s*([\w/-]+)\s*$", agents_content, re.MULTILINE)
                if "/" in ref
            )

            broken_refs = agent_skill_refs - skill_ids

            if not broken_refs:
                logger.info(f"   {GREEN}✅ All agent skill references valid{RESET}")
            else:
                for ref in broken_refs:
                    logger.info(f"   {RED}❌ Broken skill reference: {ref}{RESET}")
                    result.errors.append(f"Agent references unknown skill: {ref}")

        except Exception as e:
            logger.info(f"   {YELLOW}⚠️ Could not check cross-references: {e}{RESET}")
            result.warnings.append(f"Could not check cross-references: {e}")
    else:
        logger.info(f"   {GRAY}Skipped: index files not found{RESET}")


def test_markdown_links(ai_root: Path, result: ValidationResult) -> None:
    """Check markdown internal links."""
    logger.info(f"\n{YELLOW}🔗 Checking markdown internal links...{RESET}")

    link_pattern = re.compile(r"\[.+?\]\(([^http][^\)]+)\)")
    broken_links_found = False

    for md_file in ai_root.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        file_dir = md_file.parent

        for match in link_pattern.finditer(content):
            link_path = match.group(1)
            # Remove anchors
            link_path = link_path.split("#")[0]

            if link_path and not link_path.startswith("mailto:"):
                absolute_path = (file_dir / link_path).resolve()

                if not absolute_path.exists():
                    relative_path = md_file.relative_to(ai_root)
                    logger.info(f"   {YELLOW}⚠️ {relative_path} → {link_path} (broken){RESET}")
                    result.warnings.append(f"Broken link in {relative_path}: {link_path}")
                    broken_links_found = True

    if not broken_links_found:
        logger.info(f"   {GREEN}✅ All internal links valid{RESET}")


def test_linter_configs(ai_root: Path, result: ValidationResult) -> None:
    """Check linter configuration files."""
    logger.info(f"\n{YELLOW}🔧 Checking linter configurations...{RESET}")

    linters_dir = ai_root / "standards" / "linters"

    expected_configs = [
        "dotnet-editorconfig.md",
        "eslint-config.md",
        "python-pyproject.md",
        "yamllint.md",
        "tflint.md",
    ]

    for config in expected_configs:
        config_path = linters_dir / config
        if config_path.exists():
            logger.info(f"   {GREEN}✅ {config}{RESET}")
        else:
            logger.info(f"   {YELLOW}⚠️ {config} (missing){RESET}")
            result.warnings.append(f"Missing linter config: {config}")


def test_cicd_configs(ai_root: Path, result: ValidationResult) -> None:
    """Check CI/CD configuration files."""
    logger.info(f"\n{YELLOW}🚀 Checking CI/CD configurations...{RESET}")

    cicd_dir = ai_root / "standards" / "cicd"

    expected_configs = [
        "azure-pipelines.md",
        "quality-gates.md",
        "dependabot.md",
    ]

    for config in expected_configs:
        config_path = cicd_dir / config
        if config_path.exists():
            logger.info(f"   {GREEN}✅ {config}{RESET}")
        else:
            logger.info(f"   {YELLOW}⚠️ {config} (missing){RESET}")
            result.warnings.append(f"Missing CI/CD config: {config}")


def test_security_configs(ai_root: Path, result: ValidationResult) -> None:
    """Check security configuration files."""
    logger.info(f"\n{YELLOW}🔒 Checking security configurations...{RESET}")

    security_dir = ai_root / "standards" / "security"

    expected_configs = [
        "owasp-top10.md",
        "snyk.md",
        "codeql.md",
    ]

    for config in expected_configs:
        config_path = security_dir / config
        if config_path.exists():
            logger.info(f"   {GREEN}✅ {config}{RESET}")
        else:
            logger.info(f"   {YELLOW}⚠️ {config} (missing){RESET}")
            result.warnings.append(f"Missing security config: {config}")


@click.command()
@click.option("--fix", "-f", is_flag=True, help="Attempt to fix issues where possible")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed validation results")
def main(fix: bool, verbose: bool) -> None:
    """Validate the .ai/ framework structure and content."""
    ai_root = get_ai_root()

    logger.info(f"{CYAN}🔍 Validating .ai/ framework structure...{RESET}")
    logger.info(f"   {GRAY}Path: {ai_root}{RESET}")

    result = ValidationResult()

    # Run all validations
    test_required_directories(ai_root, result, fix)
    test_required_files(ai_root, result)
    test_yaml_files(ai_root, result)
    test_cross_references(ai_root, result)
    test_markdown_links(ai_root, result)
    test_linter_configs(ai_root, result)
    test_cicd_configs(ai_root, result)
    test_security_configs(ai_root, result)

    # Summary
    logger.info(f"\n{GRAY}{'=' * 50}{RESET}")
    logger.info(f"{CYAN}Validation Summary{RESET}")
    logger.info(f"{GRAY}{'=' * 50}{RESET}")

    if not result.errors and not result.warnings:
        logger.info(f"\n{GREEN}✅ All validations passed!{RESET}")
        sys.exit(0)

    if result.errors:
        logger.info(f"\n{RED}❌ Errors: {len(result.errors)}{RESET}")
        for error in result.errors:
            logger.info(f"   {RED}- {error}{RESET}")

    if result.warnings:
        logger.info(f"\n{YELLOW}⚠️ Warnings: {len(result.warnings)}{RESET}")
        for warning in result.warnings:
            logger.info(f"   {YELLOW}- {warning}{RESET}")

    if result.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
