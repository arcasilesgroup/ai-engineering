```markdown
# ai-engineering Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches the core development patterns, coding conventions, and operational workflows for the `ai-engineering` Python codebase. The repository is focused on AI engineering automation, skill/agent mirror management, manifest/state schema evolution, CLI and CI/CD standardization, and robust template synchronization across multiple IDEs and environments. The guide covers how to contribute, synchronize, and validate changes efficiently, ensuring consistency and reliability across all supported surfaces.

---

## Coding Conventions

**File Naming:**  
- Use `camelCase` for file names (e.g., `syncCommandMirrors.py`, `testRunbookContracts.py`).

**Import Style:**  
- Use relative imports within modules.
    ```python
    from .config import ManifestConfig
    from ..state import models
    ```

**Export Style:**  
- Use named exports; avoid wildcard (`*`) exports.
    ```python
    __all__ = ["ManifestConfig", "InstallState"]
    ```

**Commit Messages:**  
- Prefix with `feat`, `fix`, `chore`, `docs`, or `refactor`.
- Keep messages concise (~65 characters).
    ```
    feat: add support for multi-IDE mirror sync
    fix: correct manifest schema validation error
    ```

**Example Directory Structure:**
```
src/ai_engineering/
    cli_commands/
    config/
    state/
    updater/
    templates/
.ai-engineering/
    runbooks/
    manifest.yml
    state/
.claude/
    skills/
    agents/
```

---

## Workflows

### sync-skill-and-agent-mirrors
**Trigger:** When a skill or agent definition is added, updated, or deleted in `.claude/`, or when a new handler is introduced  
**Command:** `/sync`

1. Edit or add skill/agent/handler files in `.claude/` directory.
2. Run the sync script:
    ```bash
    ai-eng sync
    ```
3. Propagate changes to all mirrors: `.agents/`, `.github/`, and `templates/project/` directories.
4. Stage and commit all changed files.
5. Update instruction files (`CLAUDE.md`, `AGENTS.md`, `copilot-instructions.md`) if skill/agent count or structure changes.
6. Run tests to verify mirror sync and handler routing completeness.

---

### multi-surface-runbook-update
**Trigger:** When a runbook is added, updated, normalized, or contract/schema changes  
**Command:** `/update-runbooks`

1. Edit or add runbook(s) in `.ai-engineering/runbooks/`.
2. Sync changes to `src/ai_engineering/templates/.ai-engineering/runbooks/`.
3. If the runbook contract/schema changes, update all runbooks to match new sections/fields.
4. Update or create associated tests (e.g., `test_runbook_contracts.py`).
5. Stage and commit all changed runbook and template files.

---

### manifest-and-state-schema-migration
**Trigger:** When manifest schema changes, state model is unified, or new fields are added/removed  
**Command:** `/update-manifest`

1. Edit `.ai-engineering/manifest.yml` and/or state files.
2. Update corresponding Pydantic models in `src/ai_engineering/config/manifest.py` and `src/ai_engineering/state/models.py`.
3. Update loader/service logic for manifest and state.
4. Update template mirrors of `manifest.yml`.
5. Update any CLI commands, installer phases, or validators that consume these models.
6. Update or add migration logic if old state files are being replaced.
7. Update or add tests for new schema/model behavior.

---

### cli-command-and-ui-standardization
**Trigger:** When CLI UX or output contract is updated, or new commands/flags are added  
**Command:** `/doctor`, `/install`, `/verify`

1. Edit CLI command modules in `src/ai_engineering/cli_commands/`.
2. Update shared CLI UI logic (`cli_ui.py`, `cli_factory.py`).
3. Update or add tests for CLI output and behavior.
4. If output contract changes, update documentation and README sections.
5. Sync any template mirrors if CLI output is referenced in instruction files.

**Example CLI Command:**
```bash
ai-eng doctor
```

---

### ci-cd-pipeline-and-workflow-refactor
**Trigger:** When CI/CD pipeline structure changes, security hardening is applied, or release automation is updated  
**Command:** `/release`, `/doctor`

1. Edit or split `.github/workflows/*.yml` files.
2. Update `scripts/check_workflow_policy.py` and related policy checks.
3. Update `pyproject.toml` for semantic-release or tool configuration.
4. Update branch/tag protection rules and `CODEOWNERS` as needed.
5. Update or add supply chain security steps (SBOM, checksums, SLSA).
6. Update or add tests for CI/CD policy enforcement.
7. Update documentation (README.md CI badge, docs/solution-intent.md).

---

### multi-ide-hook-script-sync-and-hardening
**Trigger:** When a hook script is added, updated, moved, or permissions/cross-IDE compatibility is improved  
**Command:** `/doctor --phase hooks`

1. Edit or add hook scripts in `.ai-engineering/scripts/hooks/`.
2. Sync changes to `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/`.
3. Update settings and configuration files as needed.
4. Update installer phases and doctor checks for hooks.
5. Update or add tests for hook presence, permissions, and health.
6. Stage and commit all changed hook and config files.

---

### skill-frontmatter-and-schema-standardization
**Trigger:** When a new frontmatter field is introduced, removed, or standardized across skills/agents  
**Command:** `/sync --check`

1. Edit frontmatter in `.claude/skills/*/SKILL.md` and `.claude/agents/*.md`.
2. Sync changes to all mirrors using the sync script.
3. Update schema files if schema changes.
4. Update or add tests for frontmatter validation.
5. Update documentation and instruction files if skill/agent counts or fields change.

**Example Frontmatter:**
```yaml
---
name: "Data Ingestion"
effort: "medium"
model: "gpt-4"
color: "blue"
tags: ["etl", "pipeline"]
---
```

---

### template-and-mirror-directory-structure-migration
**Trigger:** When directory structure for skills/agents/hooks changes to support new IDEs or to simplify layout  
**Command:** `/sync`

1. Move or rename directories (e.g., `.agents/` → `.codex/`, `.gemini/`, `.github/`).
2. Update sync logic and installer logic to use new structure.
3. Update validator logic and tests for new directory layout.
4. Update all instruction files and documentation to reflect new structure.
5. Sync all mirrors and verify with tests.

---

## Testing Patterns

- **Framework:** Not explicitly detected; likely uses `pytest`.
- **File Naming:** Test files use `*.test.ts` for TypeScript, and `test_*.py` for Python.
- **Location:** Tests are placed under `tests/unit/` and `tests/integration/`.
- **Typical Test Example:**
    ```python
    def test_manifest_schema_validation():
        from src.ai_engineering.config.manifest import ManifestConfig
        # ... test logic ...
    ```
- **Run Tests:**
    ```bash
    pytest tests/
    ```

---

## Commands

| Command                | Purpose                                                          |
|------------------------|------------------------------------------------------------------|
| /sync                  | Propagate skill/agent changes to all mirrors                     |
| /sync --check          | Validate skill/agent frontmatter and mirror parity               |
| /update-runbooks       | Update and normalize runbooks across all surfaces                |
| /update-manifest       | Migrate and update manifest/state schema and consumers           |
| /doctor                | Run CLI doctor checks and output standardization                 |
| /doctor --phase hooks  | Check and validate IDE hook scripts and permissions              |
| /install               | Run installer and setup commands                                |
| /verify                | Run verification commands for CLI and schema validation          |
| /release               | Trigger release automation and CI/CD pipeline                    |

---
```