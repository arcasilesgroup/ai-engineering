# Handler: Python Build Resolver

## Purpose

Resolves Python import errors, package installation failures, type checking violations, and linting issues. Covers the full diagnostic chain from `pip check` through `mypy`, `ruff check`, and import isolation analysis. Focuses on module resolution, virtual environment integrity, and dependency conflict resolution. Targets Python 3.10+ with pip or uv as the package manager.

## Activation

Activate this handler when:

- The project contains `pyproject.toml`, `setup.py`, `setup.cfg`, or `requirements.txt`
- Source files have the `.py` extension
- Errors reference `ModuleNotFoundError`, `ImportError`, `SyntaxError`, or `IndentationError`
- The user reports issues with `pip install`, `python -m`, `mypy`, or `ruff`
- Type checking or linting failures block the build pipeline

## Diagnostic Sequence (Phase 2 -- Reproduction)

Run these commands in order. Stop at the first failure and diagnose before continuing.

```bash
# 1. Verify Python version and environment
python --version
which python
echo $VIRTUAL_ENV

# 2. Verify virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "WARNING: No virtual environment active"
    # Check for common venv locations
    ls -d .venv venv .env env 2>/dev/null
fi

# 3. Check for dependency conflicts
pip check 2>&1

# 4. List installed packages with versions
pip list --format=columns 2>&1

# 5. Verify the project is installed in development mode
pip show $(basename $(pwd)) 2>/dev/null || echo "Project not installed as package"

# 6. Run ruff linter
ruff check . 2>&1

# 7. Run ruff formatter check
ruff format --check . 2>&1

# 8. Run mypy type checker (if configured)
mypy . 2>&1

# 9. Run the test suite to confirm behavioral correctness
python -m pytest --tb=short 2>&1
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'X'` | The module `X` is not installed in the active Python environment, or the package name differs from the import name. | Install the package: `pip install X`. If the package name differs (e.g., `pip install Pillow` for `import PIL`), check PyPI for the correct package name. Verify the virtual environment is active. |
| `ImportError: cannot import name 'Y' from 'X'` | The symbol `Y` does not exist in module `X`. Version mismatch (API changed), typo, or circular import. | Check the installed version: `pip show X`. Verify the symbol exists in that version's API. Check for circular imports by examining the import chain. |
| `SyntaxError: invalid syntax` | Python syntax error. Common causes: missing colon, unmatched parentheses, Python 2 syntax in Python 3, f-string issues in older Python versions. | Read the exact line and character position. Check for match/case syntax (3.10+), walrus operator (3.8+), or type union syntax `X \| Y` (3.10+). Verify the Python version supports the syntax used. |
| `IndentationError: unexpected indent` | Inconsistent use of tabs and spaces, or wrong indentation level. | Configure the editor to use 4 spaces (PEP 8). Run `ruff format` to auto-fix. Check for mixed tabs and spaces: `python -tt script.py`. |
| `pip dependency conflict: X requires Y==1.0, but you have Y==2.0` | Two installed packages require incompatible versions of the same dependency. | Run `pip check` to see all conflicts. Use `pip install X --dry-run` to preview resolution. Consider pinning compatible versions in `pyproject.toml`. Use `pip install --force-reinstall X` as last resort. |
| `ModuleNotFoundError: No module named 'X.Y'` | Submodule `Y` does not exist in package `X`, or `X` is a namespace package without proper `__init__.py`. | Verify the submodule exists in the installed package: `python -c "import X; print(X.__path__)"`. Check for missing `__init__.py` in local packages. |
| `ImportError: attempted relative import with no known parent package` | A relative import (`from .module import X`) is used in a script that is run directly instead of as a module. | Run as a module: `python -m package.module` instead of `python package/module.py`. Ensure the package has `__init__.py`. |
| `AttributeError: module 'X' has no attribute 'Y'` | The attribute `Y` was removed or renamed in a newer version of `X`, or a local file shadows the installed module. | Check for local files named `X.py` that shadow the installed module. Verify the installed version: `pip show X`. Check the migration guide for API changes. |
| `TypeError: X() got an unexpected keyword argument 'Y'` | Function signature changed between versions, or wrong function is being called. | Check the function signature in the installed version: `python -c "import X; help(X.func)"`. Pin the dependency version if needed. |
| `ValueError: attempted relative import beyond top-level package` | Relative import goes above the package root. | Restructure imports to stay within the package boundary. Use absolute imports instead. |

## Virtual Environment Troubleshooting

```bash
# Check if a virtual environment is active
echo "VIRTUAL_ENV=$VIRTUAL_ENV"
which python
python -c "import sys; print(sys.prefix); print(sys.executable)"

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Verify packages are installed in the venv, not globally
pip list --path $(python -c "import site; print(site.getusersitepackages())") 2>/dev/null

# Check for system Python contamination
python -c "import sys; print([p for p in sys.path if 'site-packages' in p])"

# Recreate the virtual environment from scratch
deactivate 2>/dev/null
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"   # or: pip install -r requirements.txt

# Using uv (faster alternative)
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Check for PATH issues (wrong Python binary)
which -a python python3
```

## Import Resolution Troubleshooting

```bash
# Trace the import chain for a specific module
python -v -c "import X" 2>&1 | tail -20

# Find where a module is loaded from
python -c "import X; print(X.__file__)"

# Check for local files shadowing installed packages
find . -name "X.py" -not -path "./.venv/*" -not -path "./venv/*"

# List the Python path (import search order)
python -c "import sys; print('\n'.join(sys.path))"

# Verify package entry points
pip show -f X | head -20

# Check for circular imports (trace the import order)
python -c "
import sys
original_import = __builtins__.__import__
def tracing_import(name, *args, **kwargs):
    print(f'Importing: {name}')
    return original_import(name, *args, **kwargs)
__builtins__.__import__ = tracing_import
import your_module
" 2>&1 | head -30

# Verify editable install is working
pip show -e $(basename $(pwd)) 2>/dev/null
```

## Type Checking Troubleshooting

```bash
# Run mypy with verbose output
mypy --verbose . 2>&1

# Check mypy configuration
mypy --config-file pyproject.toml --warn-unused-configs . 2>&1

# Run mypy on a single file
mypy path/to/file.py 2>&1

# Show mypy's understanding of a type
mypy --show-error-codes --show-column-numbers path/to/file.py 2>&1

# Install type stubs for third-party packages
mypy --install-types . 2>&1

# Use reveal_type() for debugging (remove before commit)
# Add to code: reveal_type(variable)  then run mypy
```

## Hard Rules

- **NEVER** install packages to the system Python. Always use a virtual environment.
- **NEVER** add `# type: ignore` comments to bypass mypy errors. Fix the type annotation or refactor the code.
- **NEVER** add `# noqa` comments to bypass ruff findings. Fix the code.
- **NEVER** use `sys.path.insert()` or `sys.path.append()` hacks to fix import errors. Fix the package structure.
- **NEVER** use `pip install --break-system-packages` or `--user` as a workaround for environment issues.
- **ALWAYS** use a virtual environment (`.venv` by convention).
- **ALWAYS** run `pip check` after installing or upgrading packages to verify consistency.
- **ALWAYS** verify the correct Python version is active before diagnosing import errors.
- **ALWAYS** check for local file shadowing before concluding a package is not installed.

## Stop Conditions

- The error requires a Python version upgrade that affects the entire project (e.g., Python 3.12 syntax used in a 3.10 project). Escalate with the version requirement.
- The dependency conflict is unresolvable with the current version constraints (two packages require mutually exclusive versions of a third). Document the conflict tree and escalate.
- Two fix attempts have failed for the same import or type error. Provide the root cause analysis and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | ruff check | ruff format --check | mypy | pytest
```
