# Python pyproject.toml Standard

> Ruff + Black + mypy configuration for Python projects with strict type checking.

---

## Installation

```bash
pip install ruff black mypy pytest pytest-cov
```

Or in `requirements-dev.txt`:
```
ruff>=0.5.0
black>=24.0.0
mypy>=1.10.0
pytest>=8.0.0
pytest-cov>=5.0.0
```

---

## pyproject.toml Template

```toml
# pyproject.toml

[project]
name = "project-name"
version = "1.0.0"
description = "Project description"
requires-python = ">=3.11"
authors = [{ name = "Team", email = "team@example.com" }]
readme = "README.md"
license = { text = "MIT" }

dependencies = [
    # Production dependencies
]

[project.optional-dependencies]
dev = [
    "ruff>=0.5.0",
    "black>=24.0.0",
    "mypy>=1.10.0",
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "pre-commit>=3.0.0",
]

# =============================================================================
# RUFF - Linter and Import Sorter
# =============================================================================
[tool.ruff]
target-version = "py311"
line-length = 120
exclude = [
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "build",
    "dist",
    "node_modules",
    "migrations",
]

[tool.ruff.lint]
select = [
    # Pyflakes
    "F",
    # pycodestyle
    "E",
    "W",
    # isort
    "I",
    # pep8-naming
    "N",
    # pydocstyle
    "D",
    # pyupgrade
    "UP",
    # flake8-bugbear
    "B",
    # flake8-simplify
    "SIM",
    # flake8-comprehensions
    "C4",
    # flake8-bandit (security)
    "S",
    # flake8-unused-arguments
    "ARG",
    # flake8-use-pathlib
    "PTH",
    # flake8-return
    "RET",
    # flake8-raise
    "RSE",
    # flake8-self
    "SLF",
    # flake8-type-checking
    "TCH",
    # Ruff-specific
    "RUF",
    # flake8-annotations
    "ANN",
    # flake8-async
    "ASYNC",
    # flake8-logging
    "LOG",
    # Perflint
    "PERF",
]

ignore = [
    # Line too long (handled by formatter)
    "E501",
    # Missing docstring in public module
    "D100",
    # Missing docstring in __init__
    "D104",
    # Missing type annotation for self
    "ANN101",
    # Missing type annotation for cls
    "ANN102",
    # Dynamically typed expressions (Any)
    "ANN401",
    # First line should be in imperative mood
    "D401",
    # assert detected (ok in tests)
    "S101",
]

# Per-file ignores
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "S101",    # assert allowed in tests
    "ARG001",  # Unused function argument (fixtures)
    "ARG002",  # Unused method argument
    "D103",    # Missing docstring in public function
    "ANN",     # Type annotations not required in tests
]
"__init__.py" = [
    "D104",    # Missing docstring in public package
]
"conftest.py" = [
    "ARG001",  # Unused function argument (fixtures)
]

# Import sorting (replaces isort)
[tool.ruff.lint.isort]
known-first-party = ["src", "app", "project_name"]
force-single-line = false
lines-after-imports = 2
combine-as-imports = true

# Docstring convention
[tool.ruff.lint.pydocstyle]
convention = "google"

# Formatting (replaces Black, optional - can use Ruff as formatter)
[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
docstring-code-format = true
docstring-code-line-length = "dynamic"

# =============================================================================
# BLACK - Code Formatter (alternative to ruff format)
# =============================================================================
[tool.black]
line-length = 120
target-version = ["py311", "py312"]
include = '\.pyi?$'
exclude = '''
/(
    \.git
    | \.venv
    | venv
    | __pycache__
    | \.mypy_cache
    | \.pytest_cache
    | build
    | dist
    | migrations
)/
'''

# =============================================================================
# MYPY - Type Checker
# =============================================================================
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
warn_redundant_casts = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_any_generics = true
no_implicit_optional = true
no_implicit_reexport = true
strict_equality = true
extra_checks = true
show_error_codes = true
show_column_numbers = true
pretty = true
exclude = [
    "build",
    "dist",
    ".venv",
    "venv",
    "__pycache__",
    "migrations",
]

# Allow untyped in tests
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
disallow_incomplete_defs = false

# Ignore missing imports for third-party libraries without stubs
[[tool.mypy.overrides]]
module = [
    "third_party_library.*",
    "legacy_module.*",
]
ignore_missing_imports = true

# =============================================================================
# PYTEST - Testing
# =============================================================================
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_functions = ["test_*"]
python_classes = ["Test*"]
addopts = [
    "-v",
    "--strict-markers",
    "--strict-config",
    "-ra",
    "--tb=short",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow running tests",
]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning",
]

# =============================================================================
# COVERAGE
# =============================================================================
[tool.coverage.run]
branch = true
source = ["src"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/migrations/*",
    "*/.venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
    "@overload",
]
fail_under = 80
show_missing = true
skip_covered = true
```

---

## Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: []
        args: [--ignore-missing-imports]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements
```

---

## Makefile for Common Commands

```makefile
# Makefile
.PHONY: lint format typecheck test all

lint:
	ruff check .

lint-fix:
	ruff check --fix .

format:
	ruff format .

format-check:
	ruff format --check .

typecheck:
	mypy .

test:
	pytest

test-cov:
	pytest --cov --cov-report=html --cov-report=xml

all: lint-fix format typecheck test
```

---

## Verification Commands

```bash
# Linting (CI/CD)
ruff check .

# Fix linting locally
ruff check --fix .

# Formatting (CI/CD)
ruff format --check .
# or
black --check .

# Type checking (CI/CD)
mypy .

# Run tests with coverage
pytest --cov --cov-report=xml --cov-fail-under=80
```
