---
id: sub-006
parent: spec-127
milestone: M5
title: "Hexagonal seams (skill_domain / skill_app / skill_infra)"
status: planning
files:
  - tools/skill_domain/
  - tools/skill_app/
  - tools/skill_app/ports/
  - tools/skill_infra/
  - tests/architecture/test_layer_isolation.py
  - .claude/skills/ai-create/SKILL.md
  - .claude/skills/ai-skill-tune/SKILL.md
  - .claude/skills/ai-prompt/SKILL.md
  - .claude/skills/ai-ide-audit/SKILL.md
depends_on:
  - sub-001
  - sub-002
---

# Sub-Spec 006: M5 — Hexagonal seams

## Scope

Per D-127-09, enforce hexagonal layer isolation via test (not custom lint
plugin). Ship `tests/architecture/test_layer_isolation.py` asserting any
`tools.skill_domain` module attempting `import tools.skill_infra` raises
`ImportError`.

Move pure-Python skill/agent dataclasses + validators into
`tools/skill_domain/` (zero deps). Move use-case orchestrators (linter,
evaluator, optimizer, audit) into `tools/skill_app/` calling only ports.
Define ports in `tools/skill_app/ports/`: `SkillPort`, `AgentPort`,
`HookPort`, `BoardPort`, `MemoryPort`, `TelemetryPort`. Move existing hook
bytes / mirror sync / MCP clients / Engram / NotebookLM / Context7 /
GitHub-ADO board into `tools/skill_infra/` adapter modules implementing
one port each.

Refactor `/ai-create`, `/ai-skill-tune`, `/ai-prompt`, `/ai-ide-audit` to
consume the application layer only (no infra imports). M5 is file moves +
import rewrites only — no behavior change. Per-commit `git diff --stat`
≤200 LOC enforced as CI size cap.

## Exploration

### Current state (pre-M5)

- `tools/` does not exist at repo root yet. M1 (sub-002) scaffolds the three
  empty packages with `__init__.py`: `tools/skill_domain/`, `tools/skill_app/`,
  `tools/skill_app/ports/`, `tools/skill_infra/`. M5 fills them — does not
  create them.
- `tests/architecture/` directory does not exist. M5 creates it and ships
  exactly one file: `test_layer_isolation.py`.
- Repo precedent for ports-style decoupling lives in `src/ai_engineering/state/`.
  Modules being moved live in `src/ai_engineering/` and `scripts/` — M5
  relocates by copy-then-delete-then-import-rewrite, never edits module bodies.
- Four post-M4-rename skills: `/ai-create`, `/ai-prompt`, `/ai-skill-tune`
  (post-rename of `/ai-skill-evolve`), `/ai-ide-audit` (post-rename of
  `/ai-platform-audit`). Per umbrella DAG, M5 (P6) depends on P2 only, but the
  four-skill body rewrites (T-6.6.x) gated on M4 completion.
- "Infra" inside SKILL.md bodies today is shell-out to Python scripts (e.g.
  `python scripts/sync_command_mirrors.py`), not Python imports. M5 "import
  rewrite" for skill bodies = swap the reference for the app-layer entry point.

### Module inventory — what moves where

#### tools/skill_domain/ (zero deps; stdlib + typing only)

| Source path                                            | Target path                                |
| `src/ai_engineering/state/event_schema.py`             | `tools/skill_domain/event_schema.py`       |
| `src/ai_engineering/state/models.py`                   | `tools/skill_domain/models.py`             |
| `src/ai_engineering/state/decision_logic.py`           | `tools/skill_domain/decision_logic.py`     |
| `src/ai_engineering/standards.py`                      | `tools/skill_domain/standards.py`          |
| `src/ai_engineering/validator/categories/skill_frontmatter.py` | `tools/skill_domain/validators/skill_frontmatter.py` |
| `src/ai_engineering/validator/categories/cross_references.py`  | `tools/skill_domain/validators/cross_references.py`  |
| `src/ai_engineering/validator/categories/counter_accuracy.py`  | `tools/skill_domain/validators/counter_accuracy.py`  |

#### tools/skill_app/ (use cases; depends on domain + ports only)

| Source path                                                    | Target path                                  |
| `src/ai_engineering/skills/service.py`                         | `tools/skill_app/skill_service.py`           |
| `src/ai_engineering/validator/service.py`                      | `tools/skill_app/lint_service.py`            |
| `src/ai_engineering/validator/_shared.py`                      | `tools/skill_app/_lint_shared.py`            |
| `src/ai_engineering/validator/categories/manifest_coherence.py`| `tools/skill_app/manifest_coherence.py`      |
| `src/ai_engineering/validator/categories/required_tools.py`    | `tools/skill_app/tool_audit.py`              |
| `src/ai_engineering/validator/categories/file_existence.py`    | `tools/skill_app/file_existence_audit.py`    |
| `src/ai_engineering/governance/policy_engine.py`               | `tools/skill_app/policy_engine.py`           |
| `src/ai_engineering/governance/decision_log.py`                | `tools/skill_app/decision_log_service.py`    |
| `src/ai_engineering/work_items/service.py`                     | `tools/skill_app/work_item_service.py`       |

#### tools/skill_app/ports/ (8 ports; ABCs / Protocols; no I/O)

| Port              | File                                  | Source of truth (current impl) |
| `SkillPort`       | `tools/skill_app/ports/skill.py`      | `src/ai_engineering/skills/`   |
| `AgentPort`       | `tools/skill_app/ports/agent.py`      | `src/ai_engineering/templates/`|
| `HookPort`        | `tools/skill_app/ports/hook.py`       | `.ai-engineering/scripts/hooks/` |
| `BoardPort`       | `tools/skill_app/ports/board.py`      | `src/ai_engineering/platforms/{azure_devops,github}.py` |
| `MemoryPort`      | `tools/skill_app/ports/memory.py`     | Engram MCP client |
| `TelemetryPort`   | `tools/skill_app/ports/telemetry.py`  | `src/ai_engineering/state/audit_*.py` |
| `MirrorPort`      | `tools/skill_app/ports/mirror.py`     | `scripts/sync_command_mirrors.py` |
| `ResearchPort`    | `tools/skill_app/ports/research.py`   | NotebookLM + Context7 MCP clients |

(Spec lists 6 ports as required minimum. Plan adds `MirrorPort` + `ResearchPort`
because adapter inventory in spec body needs ports to land on. If reviewers
prefer stricter 6-port surface, fold mirror into `HookPort` and research into
`MemoryPort`.)

#### tools/skill_infra/ (one adapter per file; depends on app/ports + external libs)

14 adapter files; mapping in plan.md.

### Skill-body rewrites — the four post-M4 skills

| Skill              | Pre-M5 reference                                          | Post-M5 reference                                       | Port            |
| `/ai-create`       | `python scripts/sync_command_mirrors.py`                  | `python -m tools.skill_app.mirror_service --sync-all`   | `MirrorPort`    |
| `/ai-prompt`       | `python scripts/sync_command_mirrors.py`                  | `python -m tools.skill_app.mirror_service --sync-all`   | `MirrorPort`    |
| `/ai-skill-tune`   | engram observation read (currently shell-MCP)             | `python -m tools.skill_app.tune_service --read-engram`  | `MemoryPort`    |
| `/ai-ide-audit`    | hook-byte reads, mirror-tree walks                        | `python -m tools.skill_app.ide_audit --full`            | `HookPort`+`MirrorPort` |

### Behavior-change ban — what M5 must NOT do

- Do not edit any moved module's behavior. Acceptable diff per move = file
  rename + import path rewrites at call sites + (if needed) one-line
  re-export shim at the old path.
- Do not introduce new tests beyond `test_layer_isolation.py`.
- Do not rewrite skill body prose beyond the literal CLI/import lines listed.
- Per umbrella T-6.8: every M5 commit must satisfy `git diff --stat` ≤200 LOC.
