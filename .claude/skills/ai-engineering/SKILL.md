```markdown
# ai-engineering Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill introduces the core development patterns and workflows used in the `ai-engineering` Python codebase. It covers conventions for file organization, code style, and collaborative workflows for managing skills, agents, handlers, state models, pipelines, runbooks, and CI/CD automation. By following these patterns, contributors can ensure consistency, maintainability, and seamless integration across multiple IDEs and template surfaces.

---

## Coding Conventions

### File Naming

- **CamelCase** is used for file names.
  - Example: `InstallPipeline.py`, `ManifestLoader.py`

### Import Style

- **Relative imports** are preferred within the package.
  - Example:
    ```python
    from .phases import detect
    from ..state import models
    ```

### Export Style

- **Named exports** are used; avoid default or wildcard exports.
  - Example:
    ```python
    # In manifest.py
    class ManifestConfig(BaseModel):
        ...
    ```

### Commit Patterns

- Commit types: `feat`, `fix`, `chore`, `docs`, `refactor`
- Prefixes are used at the start of commit messages.
- Average commit message length: ~66 characters.
  - Example: `feat(installer): add autodetect phase to install pipeline`

---

## Workflows

### sync-ide-mirrors

**Trigger:** When a skill, agent, or handler is added/modified, or mirror drift is detected.  
**Command:** `ai-eng sync`

1. Edit or add canonical skill/agent/handler files in `.claude/`.
2. Run or update `scripts/sync_command_mirrors.py` to propagate changes.
3. Regenerate all mirror files in `.agents/`, `.github/`, `.codex/`, `.gemini/`, `templates/project/`, etc.
4. Update or create corresponding handler files in all mirrors.
5. Run `tests/integration/test_sync_mirrors.py` to verify mirror parity.

**Example:**
```bash
ai-eng sync
```

---

### add-or-update-skill-or-agent

**Trigger:** When a new workflow, capability, or agent is needed, or an existing one is enhanced.  
**Command:** `/add-skill` or `/add-agent`

1. Create or update `SKILL.md` and handler files in `.claude/skills/` or `.claude/agents/`.
2. Update frontmatter fields (name, description, effort, etc.) in `SKILL.md`.
3. If new handlers are added, create them in canonical and all mirror directories.
4. Run `scripts/sync_command_mirrors.py` to propagate to `.agents/`, `.github/`, templates, etc.
5. Update `manifest.yml` if the skill/agent count changes.
6. Update `CLAUDE.md`, `AGENTS.md`, `copilot-instructions.md` as needed.
7. Run or update relevant tests.

**Example:**
```bash
/add-skill
```

---

### install-pipeline-redesign-or-upgrade

**Trigger:** When the install flow, state model, or pipeline phases need to be improved or migrated.  
**Command:** `ai-eng install --plan` or `ai-eng install --reconfigure`

1. Refactor or add code in `src/ai_engineering/installer/phases/*.py`.
2. Update `src/ai_engineering/installer/service.py` and/or `ui.py`.
3. Modify or add `autodetect.py` and `wizard.py` for improved detection or UX.
4. Update or migrate state models in `src/ai_engineering/state/models.py` and `config/manifest.py`.
5. Update or create `manifest.yml`, `install-state.json`, and related template files.
6. Update or add tests in `tests/unit/installer/` and `tests/integration/`.
7. Update documentation/specs as needed.

---

### mirror-skill-or-agent-handler-addition

**Trigger:** When expanding a skill/agent with a new handler.  
**Command:** `/add-handler`

1. Create the new handler file in `.claude/skills/<skill>/handlers/` or `.claude/agents/`.
2. Run `scripts/sync_command_mirrors.py` to copy the handler to all mirrors.
3. Update `SKILL.md` or `AGENT.md` with reference to the new handler.
4. Update or create corresponding prompt files if needed for IDEs.
5. Run tests to ensure handler routing completeness.

---

### ci-cd-pipeline-and-release-automation-update

**Trigger:** When release automation, CI/CD workflow, or branch/tag protection policies change.  
**Command:** _(Manual or via PR)_

1. Edit `.github/workflows/*.yml` (e.g., `ci-build.yml`, `release.yml`).
2. Update release logic in `src/ai_engineering/release/`.
3. Modify `pyproject.toml` for semantic-release or versioning.
4. Update `CHANGELOG.md`, `README.md`, and documentation.
5. Update or add tests for release/version bumping.

---

### runbook-catalog-redesign-or-update

**Trigger:** When new runbooks are added, runbook schema/sections change, or normalization is needed.  
**Command:** `/add-runbook`

1. Edit or add runbook files in `.ai-engineering/runbooks/*.md`.
2. Update template copies in `src/ai_engineering/templates/.ai-engineering/runbooks/*.md`.
3. Update or create runbook contract tests.
4. Update validator logic if contract schema changes.
5. Sync mirrors/templates as needed.

---

### state-model-migration-or-unification

**Trigger:** When state/configuration schema changes, or state files are unified/migrated.  
**Command:** _(Manual or via migration script)_

1. Edit or add models in `src/ai_engineering/config/manifest.py` and `src/ai_engineering/state/models.py`.
2. Update loader logic in `src/ai_engineering/config/loader.py`.
3. Refactor consumers in installer, doctor, validator, etc.
4. Update or migrate state files (`manifest.yml`, `install-state.json`, etc.).
5. Update or add tests in `tests/unit/config/`, `tests/unit/state/`, and integration tests.
6. Update documentation/specs as needed.

---

### test-suite-expansion-or-hardening

**Trigger:** When new features are added, refactors are made, or coverage reports indicate gaps.  
**Command:** `pytest`

1. Add or update test files in `tests/unit/`, `tests/integration/`, or `tests/e2e/`.
2. Ensure new/changed code paths are covered.
3. Update test mapping or scope rules if necessary.
4. Run the full test suite and verify all tests pass.
5. Update CI configuration if test selection or coverage logic changes.

**Example:**
```bash
pytest
```

---

## Testing Patterns

- **Framework:** Not explicitly specified; likely uses `pytest` for Python.
- **Test file organization:**
  - Unit tests: `tests/unit/**/*.py`
  - Integration tests: `tests/integration/**/*.py`
  - End-to-end tests: `tests/e2e/**/*.py`
- **Test file naming:** Follows `test_*.py` pattern.
- **Test coverage:** Tests are updated or expanded with every new feature, refactor, or when coverage gaps are identified.
- **CI Integration:** Tests are run via GitHub Actions workflows (e.g., `ci.yml`).

**Example test:**
```python
def test_manifest_loading():
    from ..config import loader
    manifest = loader.load_manifest("path/to/manifest.yml")
    assert manifest is not None
```

---

## Commands

| Command      | Purpose                                                      |
|--------------|--------------------------------------------------------------|
| ai-eng sync  | Synchronize canonical skill/agent files to all IDE mirrors   |
| /add-skill   | Add a new skill across all supported IDEs/templates          |
| /add-agent   | Add a new agent across all supported IDEs/templates          |
| /add-handler | Add a new handler to a skill/agent and propagate to mirrors  |
| ai-eng install --plan | Plan install pipeline redesign or upgrade           |
| ai-eng install --reconfigure | Reconfigure install pipeline                 |
| /add-runbook | Add or update a runbook in the catalog                      |
| pytest       | Run the full test suite                                      |

---
```