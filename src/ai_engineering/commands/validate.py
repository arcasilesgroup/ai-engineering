#!/usr/bin/env python3
"""
Validate the .ai/ framework structure and content.

This command checks the .ai/ framework for:
- Required files and directories
- YAML syntax validity
- Markdown structure consistency
- Cross-references between files
- Missing or broken links
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import List

import click
import yaml

from ai_engineering.utils import colors, find_ai_root

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class ValidationResult:
    """Holds validation results."""

    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []


def test_required_directories(ai_root: Path, result: ValidationResult, fix: bool) -> None:
    """Check required directories exist."""
    logger.info(f"\n{colors.yellow}📁 Checking required directories...{colors.reset}")

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
            logger.info(f"   {colors.green}✅ {dir_name}{colors.reset}")
        else:
            logger.info(f"   {colors.red}❌ {dir_name} (missing){colors.reset}")
            result.errors.append(f"Missing required directory: {dir_name}")

            if fix:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"      {colors.cyan}→ Created{colors.reset}")


def test_required_files(ai_root: Path, result: ValidationResult) -> None:
    """Check required files exist."""
    logger.info(f"\n{colors.yellow}📄 Checking required files...{colors.reset}")

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
            logger.info(f"   {colors.green}✅ {file_name}{colors.reset}")
        else:
            logger.info(f"   {colors.red}❌ {file_name} (missing){colors.reset}")
            result.errors.append(f"Missing required file: {file_name}")


def test_yaml_files(ai_root: Path, result: ValidationResult) -> None:
    """Validate YAML files."""
    logger.info(f"\n{colors.yellow}📋 Validating YAML files...{colors.reset}")

    for yaml_file in ai_root.rglob("*.yaml"):
        relative_path = yaml_file.relative_to(ai_root)

        try:
            content = yaml_file.read_text(encoding="utf-8")

            # Check for tabs (YAML should use spaces)
            if "\t" in content:
                logger.info(f"   {colors.yellow}⚠️ {relative_path} (contains tabs){colors.reset}")
                result.warnings.append(f"YAML file contains tabs: {relative_path}")
            else:
                # Try to parse YAML
                yaml.safe_load(content)
                logger.info(f"   {colors.green}✅ {relative_path}{colors.reset}")

        except yaml.YAMLError as e:
            logger.info(f"   {colors.red}❌ {relative_path} (invalid YAML){colors.reset}")
            result.errors.append(f"Invalid YAML: {relative_path} - {e}")
        except Exception as e:
            logger.info(f"   {colors.red}❌ {relative_path} (error reading){colors.reset}")
            result.errors.append(f"Error reading: {relative_path} - {e}")


def test_cross_references(ai_root: Path, result: ValidationResult) -> None:
    """Check cross-references between files."""
    logger.info(f"\n{colors.yellow}🔗 Checking cross-references...{colors.reset}")

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
                logger.info(f"   {colors.green}✅ All agent skill references valid{colors.reset}")
            else:
                for ref in broken_refs:
                    logger.info(f"   {colors.red}❌ Broken skill reference: {ref}{colors.reset}")
                    result.errors.append(f"Agent references unknown skill: {ref}")

        except Exception as e:
            logger.info(f"   {colors.yellow}⚠️ Could not check cross-references: {e}{colors.reset}")
            result.warnings.append(f"Could not check cross-references: {e}")
    else:
        logger.info(f"   {colors.gray}Skipped: index files not found{colors.reset}")


def test_markdown_links(ai_root: Path, result: ValidationResult) -> None:
    """Check markdown internal links."""
    logger.info(f"\n{colors.yellow}🔗 Checking markdown internal links...{colors.reset}")

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
                    logger.info(f"   {colors.yellow}⚠️ {relative_path} → {link_path} (broken){colors.reset}")
                    result.warnings.append(f"Broken link in {relative_path}: {link_path}")
                    broken_links_found = True

    if not broken_links_found:
        logger.info(f"   {colors.green}✅ All internal links valid{colors.reset}")


def test_linter_configs(ai_root: Path, result: ValidationResult) -> None:
    """Check linter configuration files."""
    logger.info(f"\n{colors.yellow}🔧 Checking linter configurations...{colors.reset}")

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
            logger.info(f"   {colors.green}✅ {config}{colors.reset}")
        else:
            logger.info(f"   {colors.yellow}⚠️ {config} (missing){colors.reset}")
            result.warnings.append(f"Missing linter config: {config}")


def test_cicd_configs(ai_root: Path, result: ValidationResult) -> None:
    """Check CI/CD configuration files."""
    logger.info(f"\n{colors.yellow}🚀 Checking CI/CD configurations...{colors.reset}")

    cicd_dir = ai_root / "standards" / "cicd"

    expected_configs = [
        "azure-pipelines.md",
        "quality-gates.md",
        "dependabot.md",
    ]

    for config in expected_configs:
        config_path = cicd_dir / config
        if config_path.exists():
            logger.info(f"   {colors.green}✅ {config}{colors.reset}")
        else:
            logger.info(f"   {colors.yellow}⚠️ {config} (missing){colors.reset}")
            result.warnings.append(f"Missing CI/CD config: {config}")


def test_security_configs(ai_root: Path, result: ValidationResult) -> None:
    """Check security configuration files."""
    logger.info(f"\n{colors.yellow}🔒 Checking security configurations...{colors.reset}")

    security_dir = ai_root / "standards" / "security"

    expected_configs = [
        "owasp-top10.md",
        "snyk.md",
        "codeql.md",
    ]

    for config in expected_configs:
        config_path = security_dir / config
        if config_path.exists():
            logger.info(f"   {colors.green}✅ {config}{colors.reset}")
        else:
            logger.info(f"   {colors.yellow}⚠️ {config} (missing){colors.reset}")
            result.warnings.append(f"Missing security config: {config}")


@click.command("validate")
@click.option("--fix", "-f", is_flag=True, help="Attempt to fix issues where possible")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed validation results")
def validate_cmd(fix: bool, verbose: bool) -> None:
    """Validate the .ai/ framework structure and content.

    This command checks the .ai/ framework for structural integrity,
    valid YAML syntax, working cross-references, and required files.

    \b
    Examples:
        ai-engineering validate           # Basic validation
        ai-engineering validate --fix     # Validate and fix issues
        ai-engineering validate -v        # Verbose output
    """
    ai_root = find_ai_root()
    if not ai_root:
        logger.error(f"{colors.red}❌ No .ai/ directory found. Run 'ai-engineering init' first.{colors.reset}")
        raise SystemExit(1)

    logger.info(f"{colors.cyan}🔍 Validating .ai/ framework structure...{colors.reset}")
    logger.info(f"   {colors.gray}Path: {ai_root}{colors.reset}")

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
    logger.info(f"\n{colors.gray}{'=' * 50}{colors.reset}")
    logger.info(f"{colors.cyan}Validation Summary{colors.reset}")
    logger.info(f"{colors.gray}{'=' * 50}{colors.reset}")

    if not result.errors and not result.warnings:
        logger.info(f"\n{colors.green}✅ All validations passed!{colors.reset}")
        sys.exit(0)

    if result.errors:
        logger.info(f"\n{colors.red}❌ Errors: {len(result.errors)}{colors.reset}")
        for error in result.errors:
            logger.info(f"   {colors.red}- {error}{colors.reset}")

    if result.warnings:
        logger.info(f"\n{colors.yellow}⚠️ Warnings: {len(result.warnings)}{colors.reset}")
        for warning in result.warnings:
            logger.info(f"   {colors.yellow}- {warning}{colors.reset}")

    if result.errors:
        sys.exit(1)
