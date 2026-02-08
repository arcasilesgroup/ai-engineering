# Testing Strategy

## Purpose

This document defines the **comprehensive testing strategy** for the ai-engineering framework, including test types, coverage requirements, test matrix, and quality standards.

**Last Updated:** 2026-02-08 (Phase 0)

---

## Testing Philosophy

### Principles

1. **Test Behaviors, Not Implementation:** Focus on what the code does, not how it does it
2. **Fail Fast:** Tests should catch regressions immediately
3. **Clear Failures:** Test failures should pinpoint the problem quickly
4. **Fast Feedback:** Unit tests run in <5s, full suite in <2 min
5. **Deterministic:** No flaky tests; same input always produces same output
6. **Isolated:** Tests don't depend on each other or external state

---

## Test Pyramid

```
       /\
      /  \  E2E Tests (10%)
     /----\  - Cross-OS validation
    /      \ - Full workflow tests
   /--------\ Integration Tests (30%)
  /          \ - Module interactions
 /            \ - Git hook integration
/--------------\ Unit Tests (60%)
                 - Pure functions
                 - Business logic
```

### Test Distribution Targets

| Test Type | Coverage Target | Execution Time Target |
|-----------|----------------|----------------------|
| **Unit Tests** | >80% of code | <5 seconds total |
| **Integration Tests** | >70% of module interactions | <30 seconds total |
| **E2E Tests** | >90% of user workflows | <2 minutes total |
| **Security Tests** | 100% of security-critical paths | <30 seconds total |

---

## Unit Testing Requirements

### What to Unit Test

**Must Unit Test:**
- Pure functions (no side effects)
- Business logic (standards resolution, gate detection)
- Data transformations (manifest parsing, schema validation)
- Error handling paths

**Don't Unit Test:**
- Trivial getters/setters
- Framework glue code (Typer decorators)
- Third-party library wrappers (mock instead)

### Unit Test Structure

```python
# tests/unit/test_standards_resolver.py

import pytest
from ai_engineering.standards_resolver import resolve_standards

def test_resolve_standards_with_local_override():
    """Local override should take precedence over repo standard."""
    # Arrange
    defaults = {"max_tokens": 10000}
    org_standards = {"max_tokens": 8000}
    repo_standards = {"max_tokens": 5000}
    local_overrides = {"max_tokens": 3000}

    # Act
    result = resolve_standards(
        "max_tokens",
        local=local_overrides,
        repo=repo_standards,
        org=org_standards,
        defaults=defaults
    )

    # Assert
    assert result == 3000, "Local override should win"

def test_resolve_standards_list_extension():
    """Lists should extend across layers, not replace."""
    # Arrange
    defaults = {"ignore_patterns": ["*.pyc"]}
    org_standards = {"ignore_patterns": ["*.log"]}
    repo_standards = {"ignore_patterns": ["node_modules/"]}

    # Act
    result = resolve_standards(
        "ignore_patterns",
        repo=repo_standards,
        org=org_standards,
        defaults=defaults
    )

    # Assert
    assert result == ["*.pyc", "*.log", "node_modules/"]

def test_resolve_standards_missing_key_uses_default():
    """Missing keys should fall back to defaults."""
    # Arrange
    defaults = {"max_tokens": 10000}
    repo_standards = {}  # Key not defined

    # Act
    result = resolve_standards(
        "max_tokens",
        repo=repo_standards,
        defaults=defaults
    )

    # Assert
    assert result == 10000
```

### Test Fixtures and Mocks

```python
# tests/conftest.py (shared fixtures)

import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    # Initialize git repo
    (repo_dir / ".git").mkdir()
    return repo_dir

@pytest.fixture
def sample_manifest():
    """Sample manifest.yml for testing."""
    return {
        "version": "1.0",
        "standards": {
            "gates": {
                "pre_commit": {
                    "lint": "mandatory",
                    "secret_scan": "mandatory"
                }
            }
        },
        "context_optimization": {
            "max_tokens": 8000,
            "ignore_patterns": ["*.pyc", "node_modules/"]
        }
    }

@pytest.fixture
def mock_git_hooks(mocker):
    """Mock git hook installation."""
    return mocker.patch("ai_engineering.installer.install_git_hooks")
```

---

## Integration Testing Approach

### What to Integration Test

- **Module Interactions:** How modules work together (e.g., Installer → Manifest Parser → Standards Resolver)
- **Git Integration:** Hooks calling gate engine, session tracking with commits
- **File System Operations:** Reading/writing state, manifest, audit logs
- **Error Propagation:** Errors from one module handled correctly by calling module

### Integration Test Examples

```python
# tests/integration/test_install_flow.py

import pytest
from ai_engineering.cli import app
from typer.testing import CliRunner

runner = CliRunner()

def test_install_creates_structure_and_hooks(temp_repo):
    """Full install flow should create directory structure and install hooks."""
    # Arrange
    os.chdir(temp_repo)

    # Act
    result = runner.invoke(app, ["install"])

    # Assert
    assert result.exit_code == 0
    assert (temp_repo / ".ai-engineering" / "manifest.yml").exists()
    assert (temp_repo / ".ai-engineering" / "state").is_dir()
    assert (temp_repo / ".git" / "hooks" / "pre-commit").exists()
    assert "Installation successful" in result.stdout

def test_install_detects_existing_ado_config(temp_repo):
    """Install should detect and offer to migrate existing ADO config."""
    # Arrange
    os.chdir(temp_repo)
    ado_dir = temp_repo / ".azuredevops"
    ado_dir.mkdir()
    (ado_dir / "ai-engineering.yml").write_text("standards:\n  max_tokens: 5000\n")

    # Act
    result = runner.invoke(app, ["install"], input="y\n")  # Auto-approve migration

    # Assert
    assert result.exit_code == 0
    assert "Existing config detected" in result.stdout
    manifest = yaml.safe_load((temp_repo / ".ai-engineering" / "manifest.yml").read_text())
    assert manifest["context_optimization"]["max_tokens"] == 5000
```

---

## E2E Testing Strategy

### E2E Test Matrix (from verification.md)

E2E tests validate complete user workflows across different scenarios. See [verification.md](./verification.md) for full test matrix.

### E2E Test Framework

```python
# tests/e2e/test_session_workflow.py

import pytest
import subprocess

def test_complete_session_workflow(temp_repo):
    """Test full workflow: install → session start → commit → session end → history."""
    # Setup
    os.chdir(temp_repo)
    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

    # Step 1: Install
    result = subprocess.run(["ai", "install"], capture_output=True, text=True)
    assert result.returncode == 0

    # Step 2: Start session
    result = subprocess.run(["ai", "session", "start"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Session started" in result.stdout

    # Step 3: Make changes and commit
    (temp_repo / "test.txt").write_text("Hello, world!")
    subprocess.run(["git", "add", "test.txt"], check=True)
    result = subprocess.run(["git", "commit", "-m", "Add test file"], capture_output=True, text=True)
    assert result.returncode == 0  # Pre-commit hook should pass

    # Step 4: End session
    result = subprocess.run(["ai", "session", "end"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Session ended" in result.stdout

    # Step 5: Verify history
    result = subprocess.run(["ai", "history"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "test.txt" in result.stdout
```

---

## Cross-OS Testing Matrix

### Platform-Specific Considerations

| Feature | macOS | Linux | Windows (Phase 3) | Special Notes |
|---------|-------|-------|-------------------|---------------|
| **Path Separators** | `/` | `/` | `\` | Use `pathlib.Path` everywhere |
| **Git Hooks** | Shell scripts | Shell scripts | Shell scripts or PowerShell | Test hook execution |
| **File Permissions** | Unix permissions | Unix permissions | Windows ACLs | Test hook executability |
| **Line Endings** | LF | LF | CRLF | Git handles this, but test |
| **Case Sensitivity** | Configurable | Yes | No | Test file name collisions |

### Cross-OS Test Setup

```python
# tests/conftest.py

import pytest
import platform

@pytest.fixture
def current_os():
    """Detect current operating system."""
    return platform.system()  # "Darwin", "Linux", "Windows"

@pytest.mark.skipif(platform.system() == "Windows", reason="Not yet supported on Windows")
def test_git_hook_installation(temp_repo):
    """Test that git hooks are installed and executable."""
    # Test implementation...
```

### CI/CD Matrix

```yaml
# .github/workflows/test.yml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest]
    python-version: ['3.9', '3.10', '3.11', '3.12']
```

---

## Security Testing

### Security Test Checklist

- [ ] **Sensitive File Detection:** Test that gates block commits with `.env`, `.pem`, credentials
- [ ] **Command Injection:** Test that user input is sanitized (shell escaping)
- [ ] **Path Traversal:** Test that file paths are validated (no `../../../etc/passwd`)
- [ ] **Secret Scanning:** Test that secrets in code/logs are detected
- [ ] **Audit Log Integrity:** Test that audit log cannot be tampered with
- [ ] **Gate Bypass Detection:** Test that `--no-verify` is logged

### Security Test Examples

```python
# tests/security/test_gate_security.py

def test_gate_blocks_env_file_commit(temp_repo):
    """Pre-commit gate must block commits with .env files."""
    # Arrange
    os.chdir(temp_repo)
    subprocess.run(["ai", "install"], check=True)
    (temp_repo / ".env").write_text("API_KEY=secret123")
    subprocess.run(["git", "add", ".env"], check=True)

    # Act
    result = subprocess.run(
        ["git", "commit", "-m", "Add env file"],
        capture_output=True,
        text=True
    )

    # Assert
    assert result.returncode != 0, "Gate should block sensitive file"
    assert "secret" in result.stderr.lower() or "sensitive" in result.stderr.lower()

def test_gate_override_is_logged(temp_repo):
    """Gate overrides with --no-verify must be logged in audit trail."""
    # Arrange
    os.chdir(temp_repo)
    subprocess.run(["ai", "install"], check=True)
    (temp_repo / ".env").write_text("API_KEY=secret123")
    subprocess.run(["git", "add", ".env"], check=True)

    # Act
    subprocess.run(
        ["git", "commit", "-m", "Add env file", "--no-verify"],
        check=True
    )

    # Assert
    audit_log = (temp_repo / ".ai-engineering" / "state" / "audit.log").read_text()
    assert "gate_override" in audit_log
    assert ".env" in audit_log
```

---

## Performance and Load Testing

### Performance Benchmarks

```python
# tests/performance/test_context_load_time.py

import pytest
import time
from ai_engineering.context_optimizer import load_context

def test_context_load_time_small_repo(temp_repo_small, benchmark):
    """Context load time should be <5s for small repo (<50 files)."""
    result = benchmark(load_context, temp_repo_small, max_tokens=8000)
    assert result is not None
    # benchmark.stats.mean should be <5s (pytest-benchmark tracks this)

def test_context_load_time_large_repo(temp_repo_large, benchmark):
    """Context load time should be <15s for large repo (500+ files)."""
    result = benchmark(load_context, temp_repo_large, max_tokens=8000)
    assert result is not None
    # benchmark.stats.mean should be <15s

@pytest.fixture
def temp_repo_large(tmp_path):
    """Create large repo with 500 files for load testing."""
    repo = tmp_path / "large_repo"
    repo.mkdir()
    for i in range(500):
        (repo / f"file_{i}.py").write_text(f"# File {i}\nprint('hello')\n" * 100)
    return repo
```

---

## Test Automation Requirements

### CI/CD Test Pipeline

```bash
# .github/workflows/test.yml (or equivalent)

# Stage 1: Fast feedback (runs on every commit)
- name: Lint
  run: ruff check src/ tests/

- name: Type Check
  run: mypy src/

- name: Unit Tests
  run: pytest tests/unit/ -v --cov=src --cov-report=term-missing

# Stage 2: Integration tests (runs on every commit)
- name: Integration Tests
  run: pytest tests/integration/ -v

# Stage 3: E2E tests (runs on PR, pre-release)
- name: E2E Tests
  run: pytest tests/e2e/ -v

# Stage 4: Security tests (runs on PR, pre-release)
- name: Security Tests
  run: pytest tests/security/ -v

# Stage 5: Performance benchmarks (runs weekly, pre-release)
- name: Performance Tests
  run: pytest tests/performance/ --benchmark-only
```

### Pre-Commit Hooks (for Developers)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ruff
        name: Ruff linter
        entry: ruff check
        language: system
        types: [python]

      - id: mypy
        name: Type checking
        entry: mypy
        language: system
        types: [python]

      - id: pytest-unit
        name: Unit tests
        entry: pytest tests/unit/ -q
        language: system
        pass_filenames: false
        always_run: true
```

---

## Test Coverage Requirements

### Coverage Targets by Module

| Module | Unit Test Coverage | Integration Test Coverage | E2E Coverage |
|--------|-------------------|---------------------------|--------------|
| **CLI Scaffolding** | >80% | N/A (tested via E2E) | 100% of commands |
| **State Manager** | >85% | >70% | 100% of session workflows |
| **Manifest Parser** | >90% | >70% | 100% of manifest scenarios |
| **Standards Resolver** | >85% | >70% | 100% of precedence cases |
| **Installer** | >80% | >80% | 100% of install scenarios |
| **Gate Engine** | >85% | >80% | 100% of gate types |
| **Context Optimizer** | >80% | >70% | 100% of token budget cases |
| **Audit Logger** | >85% | >70% | 100% of logged events |

### Measuring Coverage

```bash
# Run with coverage reporting
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html

# Enforce minimum coverage (fail if <80%)
pytest tests/ --cov=src --cov-fail-under=80
```

---

## Test Data Management

### Test Fixtures

Use pytest fixtures for reusable test data:

```python
# tests/fixtures/manifests.py

@pytest.fixture
def minimal_manifest():
    """Minimal valid manifest for testing."""
    return {
        "version": "1.0",
        "standards": {}
    }

@pytest.fixture
def full_manifest():
    """Complete manifest with all sections."""
    return {
        "version": "1.0",
        "metadata": {
            "name": "test-repo",
            "owner": "Test Team"
        },
        "standards": {
            "gates": {
                "pre_commit": {
                    "lint": "mandatory",
                    "secret_scan": "mandatory"
                }
            }
        },
        "context_optimization": {
            "max_tokens": 8000,
            "ignore_patterns": ["*.pyc"],
            "priority_files": ["README.md"]
        }
    }
```

### Test Repositories

Create template repositories for E2E testing:

```
tests/fixtures/repos/
  ├── empty_repo/           # Fresh git repo, no files
  ├── small_repo/           # ~10 files, typical structure
  ├── large_repo/           # 500+ files for load testing
  ├── ado_migrated_repo/    # Has .azuredevops/ config
  └── claude_md_repo/       # Has .github/CLAUDE.md
```

---

## References

- [Verification Strategy](./verification.md) - E2E test matrix
- [Architecture Document](./architecture.md) - System design
- [Planning Document](./planning.md) - Module implementation plan
- [Review Criteria](./review.md) - Quality gates
