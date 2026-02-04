# Python Scripting Standards

> Conventions for Python CLI scripts, automation tools, and DevOps scripting.

---

## Overview

Python is the preferred language for:
- CLI tools and automation scripts
- DevOps and infrastructure automation
- Data processing and transformation
- CI/CD helper scripts

---

## Script Structure

### Standard Script Template

```python
#!/usr/bin/env python3
"""
Script description.

Brief description of what this script does and how to use it.

Usage:
    python script_name.py --option value

Examples:
    python script_name.py --env dev --verbose
    python script_name.py --help
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from collections.abc import Sequence

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--env", "-e", type=click.Choice(["dev", "staging", "prod"]), default="dev", help="Environment name")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.version_option(version="1.0.0")
def main(env: str, verbose: bool, dry_run: bool) -> None:
    """Main entry point for the script."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting script with env=%s, dry_run=%s", env, dry_run)

    try:
        # Script logic here
        pass
    except Exception:
        logger.exception("Script failed")
        sys.exit(1)

    logger.info("Script completed successfully")


if __name__ == "__main__":
    main()
```

---

## CLI Frameworks

### Click (Recommended)

```python
"""Example Click CLI with subcommands."""
import click


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """Main CLI entry point."""
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug


@cli.command()
@click.argument("name")
@click.option("--count", "-c", default=1, type=int, help="Number of greetings")
@click.pass_context
def hello(ctx: click.Context, name: str, count: int) -> None:
    """Say hello NAME times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")
    if ctx.obj["DEBUG"]:
        click.echo("Debug mode is on")


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Force operation")
@click.confirmation_option(prompt="Are you sure you want to proceed?")
def deploy(force: bool) -> None:
    """Deploy the application."""
    if force:
        click.echo("Force deploying...")
    else:
        click.echo("Deploying...")


if __name__ == "__main__":
    cli()
```

### Typer (Alternative - Type-Hint Based)

```python
"""Example Typer CLI."""
from enum import Enum
from typing import Annotated

import typer

app = typer.Typer(help="My awesome CLI tool")


class Environment(str, Enum):
    dev = "dev"
    staging = "staging"
    prod = "prod"


@app.command()
def deploy(
    env: Annotated[Environment, typer.Option(help="Target environment")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Force deployment")] = False,
) -> None:
    """Deploy to specified environment."""
    typer.echo(f"Deploying to {env.value}...")
    if force:
        typer.echo("Force mode enabled")


@app.command()
def status() -> None:
    """Check deployment status."""
    typer.echo("Status: OK")


if __name__ == "__main__":
    app()
```

---

## Rich Output

### Progress Bars and Tables

```python
"""Rich console output examples."""
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


def show_progress() -> None:
    """Show progress bar for long operations."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing...", total=100)
        for _ in range(100):
            # Do work
            progress.advance(task)


def show_table(data: list[dict]) -> None:
    """Display data in a formatted table."""
    table = Table(title="Results")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Duration", justify="right")

    for item in data:
        table.add_row(item["name"], item["status"], item["duration"])

    console.print(table)


def show_status(success: bool, message: str) -> None:
    """Show status with color."""
    if success:
        console.print(f"[green]✓[/green] {message}")
    else:
        console.print(f"[red]✗[/red] {message}")
```

---

## File Operations

### Path Handling

```python
"""File operations using pathlib."""
from pathlib import Path


def process_files(root_dir: Path, pattern: str = "*.md") -> list[Path]:
    """Process files matching pattern recursively."""
    return list(root_dir.rglob(pattern))


def read_file_safe(file_path: Path, encoding: str = "utf-8") -> str | None:
    """Read file with error handling."""
    try:
        return file_path.read_text(encoding=encoding)
    except FileNotFoundError:
        logger.warning("File not found: %s", file_path)
        return None
    except PermissionError:
        logger.error("Permission denied: %s", file_path)
        return None


def write_file_safe(file_path: Path, content: str, encoding: str = "utf-8") -> bool:
    """Write file with parent directory creation."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding=encoding)
        return True
    except OSError:
        logger.exception("Failed to write file: %s", file_path)
        return False
```

---

## YAML/JSON Handling

```python
"""Configuration file handling."""
import json
from pathlib import Path
from typing import Any

import yaml


def load_yaml(file_path: Path) -> dict[str, Any]:
    """Load YAML configuration file."""
    with file_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(file_path: Path, data: dict[str, Any]) -> None:
    """Save data to YAML file."""
    with file_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def load_json(file_path: Path) -> dict[str, Any]:
    """Load JSON configuration file."""
    with file_path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(file_path: Path, data: dict[str, Any], indent: int = 2) -> None:
    """Save data to JSON file."""
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
```

---

## Logging Configuration

### Structured Logging

```python
"""Logging configuration examples."""
import logging
import sys
from pathlib import Path


def setup_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
    json_format: bool = False,
) -> logging.Logger:
    """Configure logging with optional file output."""
    logger = logging.getLogger()
    logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if json_format:
        # JSON format for CI/CD
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(module)s", "message": "%(message)s"}'
        )
    else:
        # Human-readable format
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
```

---

## Error Handling

### Custom Exceptions

```python
"""Custom exception hierarchy."""


class ScriptError(Exception):
    """Base exception for script errors."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class ConfigurationError(ScriptError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Configuration error: {message}", exit_code=2)


class ValidationError(ScriptError):
    """Raised when validation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Validation error: {message}", exit_code=3)


def main() -> None:
    """Main with exception handling."""
    try:
        # Script logic
        pass
    except ConfigurationError as e:
        logger.error(str(e))
        sys.exit(e.exit_code)
    except ValidationError as e:
        logger.error(str(e))
        sys.exit(e.exit_code)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    except Exception:
        logger.exception("Unexpected error")
        sys.exit(1)
```

---

## Project Structure

```
scripts/
├── pyproject.toml           # Project configuration
├── requirements.txt         # Dependencies (or use pyproject.toml)
├── src/
│   └── tools/
│       ├── __init__.py
│       ├── cli.py           # Main CLI entry point
│       ├── sync_github.py   # Sync tool
│       ├── validate.py      # Validation tool
│       └── utils/
│           ├── __init__.py
│           ├── files.py     # File utilities
│           └── logging.py   # Logging setup
└── tests/
    ├── __init__.py
    └── test_cli.py
```

---

## Dependencies

### Recommended Packages

```toml
# pyproject.toml [project.dependencies]
[project]
dependencies = [
    "click>=8.0.0",      # CLI framework
    "rich>=13.0.0",      # Beautiful terminal output
    "pyyaml>=6.0",       # YAML parsing
    "pydantic>=2.0",     # Data validation (optional)
]

[project.optional-dependencies]
dev = [
    "ruff>=0.5.0",
    "mypy>=1.10.0",
    "pytest>=8.0.0",
]
```

---

## Best Practices

### Do

- ✅ Use type hints everywhere
- ✅ Use `pathlib.Path` instead of string paths
- ✅ Use `logging` module, not `print()`
- ✅ Use Click or Typer for CLI
- ✅ Handle errors explicitly
- ✅ Support `--dry-run` for destructive operations
- ✅ Support `--verbose` for debugging
- ✅ Use `if __name__ == "__main__"`
- ✅ Exit with appropriate codes (0=success, non-zero=error)

### Don't

- ❌ Use `os.path` (use `pathlib` instead)
- ❌ Use `print()` for logs (use `logging`)
- ❌ Hardcode paths
- ❌ Catch bare `Exception` without re-raising
- ❌ Use mutable default arguments
- ❌ Mix tabs and spaces
