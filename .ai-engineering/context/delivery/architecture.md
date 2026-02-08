# System Architecture

## Overview

This document defines the complete system architecture for the ai-engineering framework, including module boundaries, ownership model, data flows, security architecture, and integration points.

**Last Updated:** 2026-02-08 (Phase 0)
**Status:** Complete for Phase 1 MVP scope

---

## System Modules and Boundaries

| Module | Responsibility | Phase | Dependencies | Interfaces |
|--------|----------------|-------|--------------|------------|
| **CLI** | Command routing, user interaction, help system | 1 | Installer, State Manager | `ai <command>` shell interface |
| **Installer** | Bootstrap `.ai-engineering/` structure, detect existing config | 1 | Standards Resolver | File system, git hooks |
| **State Manager** | Session lifecycle, change history, status queries | 1 | Storage Layer | File-based state API |
| **Standards Resolver** | Layered config resolution (local→repo→team→org→default) | 1 | Manifest Parser | Standards lookup API |
| **Gate Engine** | Pre-commit, pre-push, merge gate enforcement | 1 | Standards Resolver | Git hook callbacks |
| **Manifest Parser** | Load, validate, merge manifest files | 1 | None | YAML parsing API |
| **Context Optimizer** | Token-aware file selection, ignore patterns, caching | 1 | Manifest Parser | Context loading API |
| **Provider Adapters** | Translate framework commands to provider-specific format | 2 | Command Model | Provider SDK interfaces |
| **Skill Manager** | Fetch, validate, cache, execute remote skills | 2 | Remote Skill Registry | HTTP, local cache |
| **Branch Governor** | Branch-specific standards, merge gate logic | 2 | Standards Resolver, Gate Engine | Git branch API |
| **Agent Orchestrator** | Route tasks to appropriate agent, manage handoffs | 3 | Capability Model | Agent execution API |
| **Maintenance Agent** | Detect stale context, flag conflicts, synthesize learnings | 3 | Context Optimizer, State Manager | Background job scheduler |
| **Audit Logger** | Immutable log of all operations, approvals, outcomes | 1 | State Manager | Append-only log API |

---

## Ownership Model (Authoritative)

The framework uses **layered precedence** for configuration resolution. Lower layers override higher layers.

### Precedence Hierarchy (Lowest to Highest)

```
1. Framework Defaults (built-in)
   ↓ (overridden by)
2. Organization Standards (.ai-engineering-org/ repo, remote)
   ↓ (overridden by)
3. Team Standards (.ai-engineering-team/ repo, remote)
   ↓ (overridden by)
4. Repository Standards (.ai-engineering/manifest.yml, committed)
   ↓ (overridden by)
5. Local Overrides (.ai-engineering/local.yml, gitignored)
```

### Resolution Logic

```python
def resolve_standard(key: str) -> Any:
    """Resolve standard value using layered precedence."""
    return (
        local_config.get(key)
        or repo_manifest.get(key)
        or team_standards.get(key)
        or org_standards.get(key)
        or framework_defaults.get(key)
    )
```

### Ownership Table

| Config Type | Source | Committed | Who Owns | Example Use Case |
|-------------|--------|-----------|----------|------------------|
| **Framework Defaults** | Packaged with CLI | N/A | Framework maintainers | Sensible defaults for all repos |
| **Org Standards** | `.ai-engineering-org/manifest.yml` | Yes (org repo) | Platform Engineering | Company-wide security gates, linting rules |
| **Team Standards** | `.ai-engineering-team/manifest.yml` | Yes (team repo) | Team Lead | Team-specific conventions (e.g., frontend vs backend) |
| **Repo Standards** | `.ai-engineering/manifest.yml` | Yes (this repo) | Repo Maintainers | Project-specific architecture rules |
| **Local Overrides** | `.ai-engineering/local.yml` | No (gitignored) | Individual Developer | Personal preferences (e.g., skip certain gates for testing) |

### Merge Semantics

- **Scalars:** Lower layer replaces higher layer (e.g., `max_tokens: 5000` overrides `max_tokens: 10000`)
- **Lists:** Lower layer **extends** higher layer (e.g., team `ignore_patterns` + org `ignore_patterns`)
- **Dicts:** Deep merge with lower layer precedence for conflicts

---

## Standards Layering Precedence (Examples)

### Example 1: Ignore Patterns (List Extension)

```yaml
# Framework Defaults
ignore_patterns:
  - "*.pyc"
  - "__pycache__"

# Org Standards
ignore_patterns:
  - "*.log"
  - ".env"

# Repo Standards
ignore_patterns:
  - "node_modules/"

# RESULT: All patterns combined
# ["*.pyc", "__pycache__", "*.log", ".env", "node_modules/"]
```

### Example 2: Max Tokens (Scalar Replacement)

```yaml
# Framework Defaults
max_tokens: 10000

# Org Standards
max_tokens: 8000

# Repo Standards
max_tokens: 5000

# RESULT: Repo value wins
# max_tokens: 5000
```

### Example 3: Gates (Dict Deep Merge)

```yaml
# Org Standards
gates:
  pre_commit:
    destructive_ops: mandatory
    secret_scan: mandatory

# Repo Standards
gates:
  pre_commit:
    destructive_ops: warn  # Override to warn instead of block
    lint: mandatory        # Add repo-specific gate

# RESULT: Merged with repo precedence
gates:
  pre_commit:
    destructive_ops: warn      # Repo overrides org
    secret_scan: mandatory     # Inherited from org
    lint: mandatory            # Added by repo
```

---

## Installer and Updater Design

### Installation Flow

```
1. User runs: `ai install`
2. Detect existing config:
   - Check for .ai-engineering/ (already installed?)
   - Check for ADO .azuredevops/
   - Check for .github/CLAUDE.md
   - Check for .cursorrules
3. Prompt user:
   - "Existing config detected. Migrate? (y/n)"
   - If yes: Parse and merge into manifest.yml
4. Create .ai-engineering/ structure:
   - manifest.yml (merged from detected config + defaults)
   - context/ (empty, ready for population)
   - state/ (session.json, history.json)
   - standards/ (optional, for complex repos)
5. Install git hooks:
   - .git/hooks/pre-commit
   - .git/hooks/pre-push
   - .git/hooks/post-commit (session tracking)
6. Display success message with next steps
```

### Update Flow

```
1. User runs: `ai update`
2. Check for framework updates (pip / GitHub releases)
3. If new version available:
   - Download and install
   - Run migration scripts if breaking changes
   - Validate manifest schema compatibility
4. Display changelog and migration notes
```

### Uninstall Flow

```
1. User runs: `ai uninstall`
2. Prompt: "Remove .ai-engineering/ and hooks? (y/n)"
3. If yes:
   - Remove git hooks
   - Remove .ai-engineering/state/ (preserve context/ and manifest.yml)
   - Display manual cleanup instructions for org/team remotes
```

---

## Detection Strategy

### Existing Config Detection

| Source | Detection Method | Migration Strategy |
|--------|------------------|-------------------|
| **ADO (.azuredevops/)** | Check for `.azuredevops/ai-engineering.yml` | Parse YAML, map to manifest schema |
| **GitHub CLAUDE.md** | Check for `.github/CLAUDE.md` | Parse markdown, extract standards as YAML |
| **Cursor Rules** | Check for `.cursorrules` | Parse JSON, map to standards section |
| **Generic README** | Check for `AI_INSTRUCTIONS.md` or similar | Prompt user to manually extract |

### Git Hook Conflict Detection

```python
def detect_hook_conflicts():
    """Detect existing git hooks before installation."""
    hooks = ["pre-commit", "pre-push", "post-commit"]
    conflicts = []

    for hook in hooks:
        path = f".git/hooks/{hook}"
        if os.path.exists(path):
            conflicts.append(hook)

    if conflicts:
        warn(f"Existing hooks detected: {conflicts}")
        prompt("Chain with ai-engineering hooks? (y/n)")
```

---

## Hooks Architecture

### Git Hook Integration

```bash
# .git/hooks/pre-commit (installed by framework)
#!/bin/bash
# ai-engineering pre-commit hook

# Source any existing hooks first (chaining)
if [ -f .git/hooks/pre-commit.local ]; then
    .git/hooks/pre-commit.local || exit 1
fi

# Run framework gate checks
ai gate pre-commit || exit 1
```

### Gate Types and Triggers

| Gate Type | Trigger | Purpose | Override? |
|-----------|---------|---------|-----------|
| **pre-commit** | `git commit` | Lint, format, secret scan, standards validation | Yes (with justification) |
| **pre-push** | `git push` | Integration tests, branch protection, merge conflicts | Yes (emergency only) |
| **pre-merge** | PR merge | Architecture review, security review, approval count | No (mandatory) |
| **session-start** | `ai session start` | Validate manifest, load context | No |
| **session-end** | `ai session end` | Commit state, log session summary | No |

### Gate Override Protocol

```bash
# Developer wants to skip gate for legitimate reason
git commit --no-verify  # Standard git bypass

# Framework records override in audit log
{
  "timestamp": "2026-02-08T12:34:56Z",
  "gate": "pre-commit",
  "operation": "commit",
  "override": true,
  "justification": "Emergency hotfix, will fix in follow-up PR",
  "user": "soydachi",
  "commit": "abc123"
}
```

---

## Command Contract (Final)

### Core Commands (Phase 1)

```bash
# Installation and Setup
ai install [--org <url>] [--team <url>]  # Bootstrap .ai-engineering/
ai update                                 # Update framework and manifest schema
ai uninstall                              # Remove hooks and state (preserve context)

# Session Management
ai session start [--branch <name>]        # Start new AI session
ai session end                            # End current session, log summary
ai session pause                          # Pause session (resume later)
ai session resume [--id <session-id>]     # Resume paused session
ai session status                         # Show current session state

# State Queries
ai status                                 # Show framework status (session, gates, standards)
ai history [--limit <n>]                  # Show change history
ai context [--show] [--optimize]          # Show/optimize context to be loaded

# Gate Management
ai gate pre-commit                        # Run pre-commit gates (used by hook)
ai gate pre-push                          # Run pre-push gates (used by hook)
ai gate list                              # Show all configured gates
ai gate override <gate-id> <reason>       # Request gate override (logged)

# Standards Management
ai standards validate                     # Validate manifest.yml schema
ai standards show [--layer <org|team|repo|local>]  # Show resolved standards
ai standards diff <layer1> <layer2>       # Diff standards between layers

# Help and Diagnostics
ai help [<command>]                       # Show help for command
ai version                                # Show framework version
ai doctor                                 # Diagnose common issues
```

### Extended Commands (Phase 2+)

```bash
# Remote Skills
ai skill list                             # List available skills
ai skill add <url> [--verify]             # Add remote skill with integrity check
ai skill remove <id>                      # Remove cached skill
ai skill run <id> [--args]                # Execute skill manually

# Branch Governance
ai branch protect <branch> [--policy]     # Apply protection policy to branch
ai branch validate                        # Validate current branch against policy

# Agent Orchestration (Phase 3)
ai agent route <task-description>         # Auto-route task to appropriate agent
ai agent list                             # Show available agents and capabilities
```

---

## Remote Skills and Integrity Model

### Skill Addressing

```yaml
# In manifest.yml
skills:
  - id: org-python-test
    url: https://github.com/acme-org/.ai-engineering-org/skills/python-test.yml
    checksum: sha256:abc123...
    cache_ttl: 3600  # 1 hour

  - id: team-frontend-lint
    url: https://github.com/frontend-team/.ai-engineering-team/skills/lint.yml
    checksum: sha256:def456...
    cache_ttl: 7200  # 2 hours
```

### Integrity Checking (Phase 2)

```python
def fetch_skill(skill_id: str) -> Skill:
    """Fetch skill with integrity validation."""
    config = manifest.skills[skill_id]

    # Check cache first
    cached = skill_cache.get(skill_id)
    if cached and not expired(cached, config.cache_ttl):
        return cached

    # Fetch from remote
    content = http_get(config.url)

    # Verify checksum
    actual_checksum = sha256(content)
    if actual_checksum != config.checksum:
        raise IntegrityError(f"Checksum mismatch for skill {skill_id}")

    # Parse and cache
    skill = parse_skill(content)
    skill_cache.set(skill_id, skill, ttl=config.cache_ttl)
    return skill
```

### Skill Schema

```yaml
# Example: python-test.yml
id: org-python-test
name: "Python Test Suite"
description: "Run pytest with coverage and type checking"
version: "1.0.0"
author: "Platform Engineering"

parameters:
  - name: test_path
    type: string
    default: "tests/"
    description: "Path to test directory"

commands:
  - name: Run pytest
    shell: |
      pytest {{ test_path }} \
        --cov=src \
        --cov-report=term-missing \
        --mypy

gates:
  - type: pre-push
    condition: "all tests must pass"
```

---

## Security and Governance Workflows

### Sensitive Operation Detection

```python
SENSITIVE_OPERATIONS = {
    "destructive": [
        r"git reset --hard",
        r"git push --force",
        r"rm -rf",
        r"DROP TABLE",
    ],
    "sensitive_files": [
        r"\.env$",
        r"\.pem$",
        r"credentials\.json$",
        r"secrets\.yml$",
    ],
    "infrastructure": [
        r"terraform apply",
        r"kubectl delete",
        r"aws.*delete",
    ],
}

def is_sensitive_operation(command: str, files: List[str]) -> bool:
    """Detect if operation requires gate approval."""
    for pattern in SENSITIVE_OPERATIONS["destructive"]:
        if re.search(pattern, command):
            return True

    for file in files:
        for pattern in SENSITIVE_OPERATIONS["sensitive_files"]:
            if re.search(pattern, file):
                return True

    return False
```

### Approval Workflow

```
1. AI agent requests operation (e.g., `git push --force`)
2. Gate engine detects sensitive operation
3. Framework prompts user:
   "⚠️  Sensitive operation detected: git push --force
    Branch: feature/xyz
    Justification required. Proceed? (y/n/why)"
4. User options:
   - y: Approve and log justification
   - n: Block operation
   - why: Show detailed risk explanation
5. Log approval in audit trail:
   {
     "operation": "git push --force",
     "gate": "destructive_ops",
     "approved": true,
     "justification": "Force push required after rebase",
     "timestamp": "...",
     "user": "..."
   }
```

---

## Context Optimization Architecture

### Token Budget Model

```yaml
# In manifest.yml
context_optimization:
  max_tokens: 8000           # Hard limit for context loading
  priority_files:            # Always include (highest priority)
    - ".ai-engineering/manifest.yml"
    - "README.md"
    - "ARCHITECTURE.md"

  ignore_patterns:           # Never include
    - "*.pyc"
    - "__pycache__/"
    - "node_modules/"
    - ".git/"
    - "*.log"

  conditional_includes:      # Include based on task type
    - pattern: "tests/**"
      when: "task.type == 'testing'"
    - pattern: "docs/**"
      when: "task.type == 'documentation'"

  caching:
    enabled: true
    ttl: 3600                # 1 hour
    invalidate_on:
      - "git commit"
      - "manifest update"
```

### Progressive Context Loading

```python
def load_context(task_type: str, max_tokens: int) -> Context:
    """Load context progressively within token budget."""
    context = Context()
    remaining_tokens = max_tokens

    # Phase 1: Always include (priority files)
    for file in config.priority_files:
        content = read_file(file)
        tokens = estimate_tokens(content)
        if tokens < remaining_tokens:
            context.add(file, content)
            remaining_tokens -= tokens

    # Phase 2: Task-specific includes
    for rule in config.conditional_includes:
        if eval(rule.when, {"task": {"type": task_type}}):
            files = glob(rule.pattern)
            for file in files:
                content = read_file(file)
                tokens = estimate_tokens(content)
                if tokens < remaining_tokens:
                    context.add(file, content)
                    remaining_tokens -= tokens
                else:
                    break  # Budget exceeded

    # Phase 3: Fill remaining with most recently modified files
    recent_files = git_recent_files(limit=50)
    for file in recent_files:
        if file in context:
            continue
        content = read_file(file)
        tokens = estimate_tokens(content)
        if tokens < remaining_tokens:
            context.add(file, content)
            remaining_tokens -= tokens
        else:
            break

    return context
```

---

## Manifest Schema (Provider-Agnostic + ADO-Ready)

```yaml
# .ai-engineering/manifest.yml (Complete Schema)

version: "1.0"  # Manifest schema version

metadata:
  name: "ai-engineering"
  description: "Context-first AI governance framework"
  owner: "Platform Engineering"
  created: "2026-02-08"
  updated: "2026-02-08"

# Ownership and remote standards
ownership:
  org:
    url: "https://github.com/acme-org/.ai-engineering-org"
    branch: "main"
  team:
    url: "https://github.com/frontend-team/.ai-engineering-team"
    branch: "main"

# Standards and conventions
standards:
  linting:
    python:
      tool: "ruff"
      config: ".ruff.toml"
    typescript:
      tool: "eslint"
      config: ".eslintrc.json"

  formatting:
    python: "black"
    typescript: "prettier"

  commit_messages:
    pattern: "^(feat|fix|docs|refactor|test|chore)\\(.*\\): .{10,72}"
    require_issue_ref: true

  branch_naming:
    pattern: "^(feature|bugfix|hotfix|release)/[a-z0-9-]+$"

# Gates and approvals
gates:
  pre_commit:
    lint: mandatory
    format: mandatory
    secret_scan: mandatory
    destructive_ops: mandatory

  pre_push:
    tests: mandatory
    integration_tests: warn
    type_check: mandatory

  pre_merge:
    approval_count: 2
    architecture_review: conditional  # Triggered by file patterns
    security_review: conditional       # Triggered by sensitive files

# Context optimization
context_optimization:
  max_tokens: 8000
  priority_files:
    - ".ai-engineering/manifest.yml"
    - "README.md"
    - ".ai-engineering/context/product/vision.md"

  ignore_patterns:
    - "*.pyc"
    - "__pycache__/"
    - "node_modules/"
    - ".git/"
    - "*.log"
    - ".ai-engineering/state/"

  conditional_includes:
    - pattern: "tests/**"
      when: "task.type == 'testing'"
    - pattern: "src/**/*.py"
      when: "task.type == 'implementation'"

# Remote skills
skills:
  - id: org-python-test
    url: "https://github.com/acme-org/.ai-engineering-org/skills/python-test.yml"
    checksum: "sha256:abc123..."
    cache_ttl: 3600

# Provider-specific extensions (optional)
providers:
  azure_devops:
    organization: "acme-org"
    project: "engineering"
    work_item_integration: true

  github:
    repository: "acme-org/ai-engineering"
    enable_actions: true

  claude:
    model: "claude-sonnet-4-5"
    temperature: 0.7

# Security and compliance
security:
  sensitive_patterns:
    - "\.env$"
    - "\.pem$"
    - "credentials\.json$"

  allowed_destructive_ops:
    - pattern: "git push --force-with-lease"
      justification_required: true

  audit_log:
    enabled: true
    retention_days: 90

# Agent orchestration (Phase 3)
agents:
  - id: code-writer
    capabilities: ["read", "write", "test"]
    restrictions:
      - "no infrastructure changes"
      - "no secret modifications"

  - id: reviewer
    capabilities: ["read", "comment"]
    restrictions:
      - "read-only access"
```

---

## Data Flows

### Session Lifecycle Flow

```
1. Developer: `ai session start --branch feature/xyz`
   ↓
2. CLI → State Manager: create_session()
   ↓
3. State Manager → File System: write state/session.json
   ↓
4. CLI → Context Optimizer: load_context(task_type="implementation")
   ↓
5. Context Optimizer → Standards Resolver: get_standards()
   ↓
6. Standards Resolver: merge layers (local → repo → team → org → defaults)
   ↓
7. Context Optimizer: select files based on token budget
   ↓
8. CLI: display context summary to user
   ↓
9. Developer works with AI agent...
   ↓
10. Developer: `ai session end`
    ↓
11. CLI → State Manager: end_session()
    ↓
12. State Manager → Audit Logger: log session summary
    ↓
13. CLI: display session summary (commits, gates, overrides)
```

### Gate Enforcement Flow

```
1. Developer: `git commit -m "..."`
   ↓
2. Git Hook (.git/hooks/pre-commit): execute `ai gate pre-commit`
   ↓
3. CLI → Gate Engine: run_gate("pre-commit")
   ↓
4. Gate Engine → Standards Resolver: get_gate_config("pre-commit")
   ↓
5. Gate Engine: detect sensitive operations in staged files
   ↓
6. Gate Engine → User: prompt for approval if sensitive
   ↓
7. User: approves or denies
   ↓
8. Gate Engine → Audit Logger: log approval/denial
   ↓
9. Gate Engine: return exit code (0=pass, 1=fail)
   ↓
10. Git: proceed or abort commit based on exit code
```

---

## Integration Points

### Git Integration
- **Hooks:** pre-commit, pre-push, post-commit
- **State Tracking:** Session boundaries aligned with commits
- **Audit Trail:** Correlate framework operations with git commits

### AI Provider Integration
- **Adapters:** Translate framework commands to provider-specific format
- **Context Injection:** Provide optimized context via provider SDK
- **Gate Responses:** Standardized gate prompts across providers

### CI/CD Integration (Phase 2+)
- **GitHub Actions:** Validate manifest on PR, run gates in CI
- **Azure DevOps Pipelines:** Work item integration, compliance checks
- **Generic CI:** Shell script wrappers for `ai gate` commands

---

## Next Steps

1. **Validate architecture:** Review with stakeholders
2. **Refine module boundaries:** Ensure clear separation of concerns
3. **Prototype installer:** Validate detection and migration logic
4. **Design state schema:** Finalize session.json and history.json formats
5. **Security review:** Validate gate logic and audit trail design

---

## References

- [Discovery Findings](./discovery.md)
- [Product Vision](../product/vision.md)
- [Planning Document](./planning.md)
- [Verification Strategy](./verification.md)
