# Plan 001: AI-Engineering Framework — Rewrite from Scratch

## Environment

- **Python**: 3.11.4 (user-level install, no proxy)
- **Package manager**: `uv` (no pip direct usage)
- **Linter/formatter**: `ruff` (line-length 100)
- **Type checker**: `ty`
- **Testing**: `pytest` + `pytest-cov`
- **Security**: `gitleaks`, `semgrep`, `pip-audit`
- **OS**: Windows primary, cross-OS support required (Bash + PowerShell hooks)
- **VCS**: GitHub (provider-first), Azure DevOps (future phase)
- **Distribution**: PyPI (`py3-none-any` wheel)
- **Branch**: `rewrite/v2` from `origin/main`

## Architecture Overview

```
Mega-Phase A: Governance Foundation (Content-First)
├── Phase 0: Branch + Scaffold (specs/)
├── Phase 1: Context Architecture Migration
├── Phase 2: Standards Review
├── Phase 3: Skills — Workflows (3 files)
├── Phase 4: Skills — SWE (12 files)
├── Phase 5: Skills — Quality (2 files)
├── Phase 6: Agents (8 files)
└── Phase 7: Stack Instructions + Copilot Integration (7 files)

Mega-Phase B: Python Rewrite from Scratch
├── Phase 8: Python Scaffold (clean slate)
├── Phase 9: State Layer (models, io, defaults, decisions)
├── Phase 10: Installer (service, templates, operations)
├── Phase 11: Hooks (manager, cross-OS scripts)
├── Phase 12: Doctor (service, remediation)
├── Phase 13: Updater (ownership-safe)
├── Phase 14: Detector + Policy (readiness, gates)
├── Phase 15: Skills + Maintenance (service, reports)
├── Phase 16: Commands + Workflows (helper functions, NOT CLI)
└── Phase 17: CLI (Typer app, entry points — no workflow commands)

Mega-Phase C: Mirror + CI + E2E
├── Phase 18: Templates Mirror
├── Phase 19: CI/CD (GitHub Actions)
└── Phase 20: E2E + Closure
```

## File Structure

### Governance content created in Mega-Phase A

```
.ai-engineering/
├── context/
│   ├── product/
│   │   ├── framework-contract.md      # UPDATED (absorb vision + roadmap)
│   │   └── product-contract.md        # NEW (project-managed)
│   ├── specs/
│   │   ├── _active.md                 # NEW (pointer to active spec)
│   │   └── 001-rewrite-v2/
│   │       ├── spec.md                # NEW (WHAT)
│   │       ├── plan.md                # NEW (HOW)
│   │       └── tasks.md              # NEW (DO)
│   └── learnings.md                   # KEEP
├── standards/
│   └── framework/
│       ├── core.md                    # REVIEWED
│       ├── stacks/python.md           # REVIEWED
│       └── quality/{core,python,sonarlint}.md  # REVIEWED
├── skills/
│   ├── utils/                         # KEEP (2 existing files)
│   ├── validation/                    # KEEP (1 existing file)
│   ├── workflows/
│   │   ├── commit.md                  # NEW
│   │   ├── pr.md                      # NEW
│   │   └── acho.md                    # NEW
│   ├── dev/
│   │   ├── debug.md                   # NEW
│   │   ├── refactor.md                # NEW
│   │   ├── code-review.md             # NEW
│   │   ├── test-strategy.md           # NEW
│   │   ├── deps-update.md             # NEW
│   │   └── migration.md               # NEW
│   ├── review/
│   │   ├── architecture.md            # NEW
│   │   ├── performance.md             # NEW
│   │   └── security.md                # NEW
│   ├── docs/
│   │   ├── changelog.md               # NEW
│   │   ├── explain.md                 # NEW
│   │   ├── writer.md                  # NEW
│   │   └── prompt-design.md           # NEW
│   └── quality/
│       ├── audit-code.md              # NEW
│       └── audit-report.md            # NEW
├── agents/
│   ├── principal-engineer.md          # NEW
│   ├── debugger.md                    # NEW
│   ├── architect.md                   # NEW
│   ├── quality-auditor.md             # NEW
│   ├── security-reviewer.md           # NEW
│   ├── codebase-mapper.md             # NEW
│   ├── code-simplifier.md             # NEW
│   └── verify-app.md                 # NEW
└── state/                             # KEEP (runtime-generated)

.github/
├── copilot-instructions.md            # UPDATED
├── copilot/
│   ├── code-generation.md             # UPDATED
│   ├── code-review.md                 # UPDATED
│   ├── test-generation.md             # UPDATED
│   └── commit-message.md             # UPDATED
├── instructions/
│   ├── python.instructions.md         # NEW (applyTo: "**/*.py")
│   ├── testing.instructions.md        # NEW (applyTo: "**/tests/**")
│   └── markdown.instructions.md       # NEW (applyTo: "**/*.md")
└── workflows/
    ├── ci.yml                         # NEW
    └── release.yml                    # NEW

AGENTS.md                              # UPDATED
CLAUDE.md                              # UPDATED
```

### Python modules rewritten in Mega-Phase B

```
src/ai_engineering/
├── __init__.py
├── __version__.py
├── cli.py                             # Thin entrypoint
├── cli_factory.py                     # Typer app builder
├── paths.py                           # Path utilities
├── state/
│   ├── __init__.py
│   ├── models.py                      # Pydantic schemas
│   ├── io.py                          # JSON/NDJSON I/O
│   ├── defaults.py                    # Bootstrap payloads
│   └── decision_logic.py             # Decision reuse
├── installer/
│   ├── __init__.py
│   ├── service.py                     # Install orchestrator
│   ├── templates.py                   # Template discovery
│   └── operations.py                 # Stack/IDE add/remove
├── hooks/
│   ├── __init__.py
│   └── manager.py                    # Hook generation + install
├── doctor/
│   ├── __init__.py
│   └── service.py                    # Diagnostic + remediation
├── updater/
│   ├── __init__.py
│   └── service.py                    # Ownership-safe update
├── detector/
│   ├── __init__.py
│   └── readiness.py                  # Tool detection
├── policy/
│   ├── __init__.py
│   └── gates.py                      # Gate checks
├── skills/
│   ├── __init__.py
│   └── service.py                    # Remote skills sync
├── maintenance/
│   ├── __init__.py
│   └── report.py                     # Report + PR creation
├── commands/
│   ├── __init__.py
│   └── workflows.py                  # Commit/PR/Acho helper functions (NOT CLI)
└── cli_commands/
    ├── __init__.py
    ├── core.py                        # install, update, doctor, version
    ├── gate.py                        # gate pre-commit/commit-msg/pre-push
    ├── stack_ide.py                   # stack/ide add/remove/list
    ├── skills.py                      # skill list/sync
    └── maintenance.py                # maintenance report/pr
```

## Key Patterns

### Content-First Execution Order

Every Copilot session during Mega-Phase B must:
1. Read `.ai-engineering/context/specs/_active.md` → find active spec
2. Read `spec.md` → understand problem and scope
3. Read `tasks.md` → find next unchecked task
4. Read relevant agent/skill → follow its patterns
5. Write code following `standards/framework/stacks/python.md`
6. Run quality checks per `standards/framework/quality/python.md`

### Python Code Patterns

- **Type hints everywhere**: All public APIs annotated, `from __future__ import annotations`
- **Pydantic for schemas**: All state models use Pydantic v2 `BaseModel`
- **Typer for CLI**: Thin CLI layer, business logic in service modules
- **Cross-OS**: Bash + PowerShell hook scripts, `pathlib.Path` throughout
- **Create-only semantics**: Installer never overwrites existing files
- **Ownership safety**: Updater only touches framework/system-managed paths
- **Google-style docstrings**: All public functions documented
- **Small focused functions**: <50 lines, single responsibility
- **Dependency injection**: Services receive deps through constructors

### Testing Patterns

- **Unit tests**: One test file per module, AAA pattern, `tmp_path` for FS
- **Integration tests**: Real `git init`, CliRunner, actual file operations
- **E2E tests**: Full install/doctor cycle on clean repos
- **Coverage**: ≥80% overall, ≥90% for governance-critical paths
- **Naming**: `test_<unit>_<scenario>_<expected_outcome>`
- **Fixtures**: Shared in `conftest.py`, scoped appropriately

### Session Recovery

When starting a new session:
1. AI reads `_active.md` → finds `001-rewrite-v2`
2. AI reads `tasks.md` → counts `[x]` vs `[ ]` checkboxes
3. AI reads `decision-store.json` → avoids re-asking decided questions
4. AI synthesizes context → presents summary → confirms next task

## Agentic Execution Model

### Branch Strategy (Multi-Agent Safe)

Single integration branch `rewrite/v2` from `origin/main`.
Parallel agents work on **phase branches** that merge to `rewrite/v2`:

```
origin/main
  └── rewrite/v2                          (integration branch)
        ├── rewrite/v2-phase-1            (serial: context migration)
        ├── rewrite/v2-phase-2            (serial: standards review)
        ├── rewrite/v2-phase-3            (parallel: workflow skills)
        ├── rewrite/v2-phase-4            (parallel: SWE skills)
        ├── rewrite/v2-phase-5            (parallel: quality skills)
        ├── rewrite/v2-phase-6            (parallel: agents)
        ├── rewrite/v2-phase-7            (serial: integration, depends on 3-6)
        ├── rewrite/v2-phase-9            (serial: state layer)
        ├── rewrite/v2-phase-10           (parallel: installer)
        ├── rewrite/v2-phase-11           (parallel: hooks)
        ├── ...                           (one branch per parallel phase)
        └── rewrite/v2-phase-20           (closure)
```

Rules:
- **Serial phases**: work directly on `rewrite/v2` (no phase branch needed).
- **Parallel phases**: each agent creates `rewrite/v2-phase-N`, merges to `rewrite/v2` on completion.
- **Conflict resolution**: phase branches rebase from `rewrite/v2` before merge.
- **Phase branch lifespan**: created at phase start, deleted after merge to `rewrite/v2`.

### Parallelism Map

```
Mega-Phase A (Content):
  SERIAL:     Phase 0 ──► Phase 1 ──► Phase 2
  PARALLEL:   Phase 3 ║ Phase 4 ║ Phase 5 ║ Phase 6   (independent content)
  SERIAL:     ──► Phase 7                               (integrates 3-6)

Mega-Phase B (Python):
  SERIAL:     Phase 8 ──► Phase 9
  PARALLEL:   Phase 10 ║ Phase 11 ║ Phase 12 ║ Phase 13 ║ Phase 14 ║ Phase 15
  SERIAL:     ──► Phase 16 ──► Phase 17                 (depends on 10-15)

Mega-Phase C (Finalize):
  SERIAL:     Phase 18 ──► Phase 19 ──► Phase 20
```

### Phase Gate Protocol

A phase is **complete** when ALL of the following are true:
1. All `[x]` checkboxes marked in `tasks.md` for that phase.
2. Phase branch merged to `rewrite/v2` (if parallel phase).
3. Quality checks pass for affected files:
   - Content phases (A): markdown lint, link validation, no broken refs.
   - Python phases (B): `ruff check` + `ruff format --check` + `ty check` + `pytest --cov`.
4. No unresolved decisions — all new decisions recorded in `decision-store.json`.

A **serial phase** cannot start until its predecessor's gate passes.
**Parallel phases** can start as soon as their shared prerequisite gate passes.

### Session Map

Each session is assigned to one agent instance. Sessions have explicit scope, dependencies, and estimated size.

| Session | Agent Slot | Phases              | Tasks           | Size | Dependencies | Branch Strategy       |
|---------|------------|----------------------|-----------------|------|-------------|-----------------------|
| S1      | Agent-1    | Phase 1              | 1.1–1.7         | M    | Phase 0 ✓   | Direct on rewrite/v2  |
| S2      | Agent-1    | Phase 2              | 2.1–2.3         | S    | S1          | Direct on rewrite/v2  |
| S3      | Agent-1    | Phase 3 (workflows)  | 3.1–3.3         | S    | S2          | rewrite/v2-phase-3    |
| S4      | Agent-2    | Phase 4 (SWE 1-10)   | 4.1–4.10        | L    | S2          | rewrite/v2-phase-4    |
| S5      | Agent-3    | Phase 4 (SWE 11-12)  | 4.11–4.12       | L    | S2          | rewrite/v2-phase-4    |
| S6      | Agent-4    | Phase 5 + 6          | 5.1–5.2, 6.1–6.8| L   | S2          | rewrite/v2-phase-5-6  |
| S7      | Agent-1    | Phase 7 (integration)| 7.1–7.7         | M    | S3+S4+S5+S6 | Direct on rewrite/v2  |
| S8      | Agent-1    | Phase 8 (scaffold)   | 8.1–8.5         | S    | S7          | Direct on rewrite/v2  |
| S9      | Agent-1    | Phase 9 (state)      | 9.1–9.5         | M    | S8          | Direct on rewrite/v2  |
| S10     | Agent-1    | Phase 10 (installer) | 10.1–10.4       | M    | S9          | rewrite/v2-phase-10   |
| S11     | Agent-2    | Phase 11 (hooks)     | 11.1–11.3       | M    | S9          | rewrite/v2-phase-11   |
| S12     | Agent-3    | Phase 12 (doctor)    | 12.1–12.2       | S    | S9          | rewrite/v2-phase-12   |
| S13     | Agent-4    | Phase 13 (updater)   | 13.1–13.2       | S    | S9          | rewrite/v2-phase-13   |
| S14     | Agent-5    | Phase 14 (detect+pol)| 14.1–14.3       | M    | S9          | rewrite/v2-phase-14   |
| S15     | Agent-6    | Phase 15 (skills+mnt)| 15.1–15.3       | M    | S9          | rewrite/v2-phase-15   |
| S16     | Agent-1    | Phase 16+17 (cmd+CLI)| 16.1–17.3       | L    | S10–S15     | Direct on rewrite/v2  |
| S17     | Agent-1    | Phase 18 (mirror)    | 18.1–18.2       | S    | S16         | Direct on rewrite/v2  |
| S18     | Agent-1    | Phase 19 (CI/CD)     | 19.1–19.3       | M    | S17         | Direct on rewrite/v2  |
| S19     | Agent-1    | Phase 20 (E2E+close) | 20.1–20.3       | M    | S18         | Direct on rewrite/v2  |

Size legend: **S** = 1-3 tasks (~30 min), **M** = 4-7 tasks (~1h), **L** = 8+ tasks or complex content (~2h+).

### Agent Coordination Protocol

When multiple agents work in parallel:

1. **Claim**: Agent marks its session tasks as `in-progress` in `tasks.md` (if using shared branch) or works on its own phase branch.
2. **Isolate**: Each parallel agent works exclusively on its phase branch. No cross-phase file edits.
3. **Checkpoint**: On completing all tasks, agent opens a PR from phase branch → `rewrite/v2`.
4. **Merge**: Integration agent (Agent-1 by convention) reviews and merges phase PRs.
5. **Gate**: Integration agent runs phase gate checks before starting next serial phase.

### Agent Session Contract

Every agent session MUST:

1. **Start** by reading: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`.
2. **Announce** scope: "Session SN — Phase P — Tasks T.x–T.y".
3. **Work** only within assigned tasks. If blocked, record decision in `decision-store.json` and stop.
4. **Commit** atomically: 1 task = 1 commit with message `spec-001: Task N.M — <description>`.
5. **Close** by marking all completed tasks as `[x]` in `tasks.md` and updating completed count in frontmatter.
6. **Report** summary: tasks done, files changed, decisions made, blockers found.

### Decision D10 Clarification

`/commit`, `/pr`, `/acho` are **skills-only** — markdown documents the AI reads and follows, not Python CLI commands. Phase 16's `commands/workflows.py` provides helper functions (stage, format, lint, commit, push) that the AI may call if available, but they are NOT exposed as CLI entry points. The `cli_commands/workflow.py` module should be removed from the Python file structure. The manifest `commands:` section remains as a schema reference for skill behavior, not as CLI command definitions.

## Document Templates

### Skill Template

All skill files in `skills/` must follow this structure:

```markdown
# {Descriptive Skill Name}

## Purpose

1-3 sentences: what this skill does and when to use it.

## Trigger

What user action or agent invocation activates this skill.
- Command: `/command` or agent reference
- Context: when this skill applies automatically

## Procedure

Numbered steps with bash/powershell snippets where applicable.

1. Step one — description
2. Step two — description
3. ...

## Output Contract

What the skill produces:
- Format (report, code changes, PR, terminal output)
- Required fields or structure
- Success/failure criteria

## Governance Notes

Non-negotiables and safety boundaries:
- Things to never do
- Mandatory checks before/after
- Policy constraints

## References

- Related standards: `standards/framework/...`
- Related skills: `skills/...`
- Related agents: `agents/...`
```

### Agent Template

All agent files in `agents/` must follow this structure:

```markdown
# {Agent Name}

## Identity

Who this agent is: role, expertise, perspective. 1-3 sentences defining the persona.

## Capabilities

Bullet list of what this agent can do:
- Capability 1
- Capability 2
- ...

## Activation

When and how to invoke this agent:
- User command or prompt trigger
- Automated trigger conditions
- Required context or inputs

## Behavior

Step-by-step protocol the agent follows:

1. Step one — what the agent does first
2. Step two — analysis or action
3. ...
4. Final step — output delivery

## Referenced Skills

Skills this agent reads and executes during its workflow:
- `skills/dev/...` — purpose
- `skills/quality/...` — purpose

## Referenced Standards

Standards this agent enforces:
- `standards/framework/core.md` — governance rules
- `standards/framework/quality/...` — quality thresholds

## Output Contract

What the agent delivers:
- Format (review comments, report, code changes, PR)
- Structure and required sections
- Verdict or pass/fail criteria

## Boundaries

What the agent must NOT do:
- Actions outside its scope
- Decisions it must escalate
- Safety constraints
```

## Testing Strategy

```
tests/
├── __init__.py
├── conftest.py                        # Shared fixtures
├── unit/
│   ├── __init__.py
│   ├── test_state.py                  # models, io, defaults, decisions
│   ├── test_installer.py              # install, templates, operations
│   ├── test_hooks.py                  # hook generation, conflicts
│   ├── test_doctor.py                 # remediation paths
│   ├── test_updater.py                # ownership safety
│   ├── test_gates.py                  # gate checks, branch blocking
│   ├── test_skills_maintenance.py     # sync, reports
│   └── test_workflows.py             # commit, PR, acho
├── integration/
│   ├── __init__.py
│   ├── test_hooks_git.py             # Real git init
│   └── test_cli.py                   # CliRunner full cycle
└── e2e/
    ├── __init__.py
    ├── test_install_clean.py          # Empty repo
    └── test_install_existing.py       # Repo with code
```

## CI Pipeline

```yaml
# Python 3.11 / 3.12 / 3.13 × Ubuntu / Windows / macOS
steps:
  - uv sync
  - uv run ruff check src/
  - uv run ruff format --check src/
  - uv run ty check src/
  - uv run pytest tests/ -v --cov=ai_engineering --cov-fail-under=80
  - uv run pip-audit
  - uv build
```

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Session context loss | Medium | specs/ with `_active.md` + `tasks.md` checkboxes enable recovery |
| Template mirror drift | Medium | Phase 18 explicit sync + future automated drift check |
| Cross-OS hook failures | High | Test on Windows (primary) + CI matrix with Ubuntu/macOS |
| Large PR size | Medium | Ultra-granular commits, but single branch merge |
| Skills/agents quality | Medium | Dogfood on own repo, iterate before merge |
