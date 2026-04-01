```markdown
# ai-engineering Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the core development patterns, coding conventions, and key workflows for contributing to the `ai-engineering` codebase. The repository is Python-based, with a strong focus on multi-IDE compatibility (Claude, Copilot, Codex, Gemini), template synchronization, and robust configuration management. You'll learn how to maintain consistency across mirrored files, update CLI commands, manage runbooks, and keep CI/CD pipelines and hooks in sync.

---

## Coding Conventions

**File Naming:**  
- Use `camelCase` for Python files and skill/agent documentation.
  - Example: `syncCommandMirrors.py`, `validateAgentSchema.py`

**Import Style:**  
- Prefer **relative imports** within the package.
  - Example:
    ```python
    from .utils import validate_manifest
    ```

**Export Style:**  
- Use **named exports** (explicitly declare what is exported).
  - Example:
    ```python
    __all__ = ["sync_command_mirrors", "validate_manifest"]
    ```

**Commit Patterns:**  
- Prefix commits with `feat`, `fix`, `chore`, `docs`, or `refactor`.
  - Example: `feat: add agent schema validation (65 chars avg)`

---

## Workflows

### skill-or-agent-addition-or-update
**Trigger:** When a new skill or agent is created, or an existing one is updated, and needs to be reflected across all supported IDEs and templates.  
**Command:** `/ai-eng-sync`

1. Edit or create the canonical skill/agent file in `.claude/skills/` or `.claude/agents/`.
2. Run the sync command:
    ```bash
    ai-eng sync
    # or
    python scripts/sync_command_mirrors.py
    ```
3. Update `manifest.yml` and instruction files (`CLAUDE.md`, `AGENTS.md`, `copilot-instructions.md`).
4. Update or create handler files as needed (e.g., `handlers/validate.md`).
5. Update or create relevant tests (e.g., `test_agent_schema_validation.py`).
6. Commit all affected files across all mirrors and templates.

---

### mirror-sync-and-validation
**Trigger:** When skills/agents/handlers are added or updated, or when parity validation is required before a release or after bulk changes.  
**Command:** `/ai-eng-sync-check`

1. Run the sync command to synchronize mirrors:
    ```bash
    ai-eng sync --check
    # or
    python scripts/sync_command_mirrors.py
    ```
2. Run validation tests:
    ```bash
    pytest tests/unit/test_sync_mirrors.py
    pytest tests/unit/test_handler_routing_completeness.py
    pytest tests/unit/test_template_prompt_parity.py
    ```
3. Fix any reported drift or missing files.
4. Commit all synchronized files and test results.

---

### runbook-catalog-redesign-or-normalization
**Trigger:** When runbook templates are changed for normalization, new runbooks are added, or the contract/schema is updated.  
**Command:** _(manual)_

1. Edit or create runbook(s) in `.ai-engineering/runbooks/`.
2. Update frontmatter fields (e.g., `owner`, `cadence`, `hosts`) and section structure.
3. Sync changes to `src/ai_engineering/templates/.ai-engineering/runbooks/`.
4. Update or create relevant tests (e.g., `test_runbook_contracts.py`).
5. Commit all affected runbook and template files.

---

### manifest-schema-or-ownership-update
**Trigger:** When manifest fields, schema, or ownership rules are added/changed, or when new file categories are introduced.  
**Command:** _(manual)_

1. Edit `.ai-engineering/manifest.yml` and/or `src/ai_engineering/state/defaults.py`.
2. Update `src/ai_engineering/templates/.ai-engineering/manifest.yml`.
3. Update or create schema files (e.g., `schemas/manifest.schema.json`).
4. Update relevant code consuming manifest or ownership.
5. Update or create relevant tests (e.g., `test_manifest.py`, `test_state.py`).
6. Commit all affected files.

---

### cli-command-redesign-or-hardening
**Trigger:** When CLI UX is improved, commands are added/removed/renamed, or output is standardized.  
**Command:** _(manual)_

1. Edit or refactor CLI command files in `src/ai_engineering/cli_commands/`.
2. Update `src/ai_engineering/cli_ui.py` and/or `src/ai_engineering/cli_factory.py` as needed.
3. Update or create relevant tests (e.g., `test_cli_*.py`, `test_cli_ui.py`).
4. Update documentation (`README.md`, `copilot-instructions.md`) if command names/UX change.
5. Commit all affected files.

---

### multi-ide-hooks-and-telemetry-sync
**Trigger:** When new hooks are introduced, telemetry is updated, or parity is needed across IDEs.  
**Command:** _(manual or via sync)_

1. Edit or create hook scripts in `.ai-engineering/scripts/hooks/`.
2. Update `hooks.json`/`settings.json` in `.github/`, `.claude/`, `.codex/`, `.gemini/` as needed.
3. Sync changes to `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/`.
4. Update or create relevant tests (e.g., `test_telemetry_canary.py`).
5. Commit all affected files.

---

### ci-cd-pipeline-or-workflow-redesign
**Trigger:** When CI/CD workflows are split, hardened, or new supply chain security features are added.  
**Command:** _(manual)_

1. Create or update workflow files in `.github/workflows/` (e.g., `ci-check.yml`, `ci-build.yml`, `release.yml`).
2. Remove or deprecate old monolithic workflows (e.g., `ci.yml`).
3. Update `scripts/check_workflow_policy.py` and other workflow policy scripts.
4. Update `README.md` CI badge and documentation references.
5. Update or create relevant tests (e.g., `test_check_workflow_policy.py`).
6. Commit all affected workflow and reference files.

---

## Testing Patterns

- **Framework:** Unknown (likely `pytest` for Python, but `.test.ts` pattern suggests some TypeScript tests as well).
- **Test File Naming:**  
  - Python: `test_*.py` (e.g., `test_sync_mirrors.py`)
  - TypeScript: `*.test.ts`
- **Location:**  
  - Python: `tests/unit/` and `tests/integration/`
- **Example (Python):**
    ```python
    def test_manifest_schema_validation():
        result = validate_manifest_schema(sample_manifest)
        assert result is True
    ```
- **Best Practice:**  
  - Write tests for every new or updated skill, agent, handler, CLI command, runbook, or manifest schema change.

---

## Commands

| Command           | Purpose                                                        |
|-------------------|----------------------------------------------------------------|
| /ai-eng-sync      | Propagate skill/agent changes across all IDE mirrors and templates |
| /ai-eng-sync-check| Validate mirror parity and report drift/missing files           |

> For other workflows, run the relevant scripts or follow manual steps as described above.
```