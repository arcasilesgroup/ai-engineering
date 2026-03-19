---
id: "053"
slug: full-ide-adapted-mirrors
title: "Full IDE-Adapted Mirrors — Eliminar agents/ y skills/ de .ai-engineering/"
status: draft
created: "2026-03-16"
size: "L"
tags: ["architecture", "mirrors", "ide-integration", "sync", "agents", "skills"]
branch: "spec/053-full-ide-adapted-mirrors"
pipeline: "full"
decisions: []
---

# Spec 053 — Full IDE-Adapted Mirrors

## Problem

El spec-052 implementó Interrogation Phase, TDD Protocol e Iron Law en los archivos canónicos (`.ai-engineering/agents/plan.md`, `.ai-engineering/agents/build.md`, `.ai-engineering/skills/test/SKILL.md`), pero estos comportamientos **no se ejecutan** en ningún IDE.

**Root cause**: Los mirrors en `.claude/`, `.github/`, `.agents/` son thin wrappers de 7-9 líneas que dicen "Read file at .ai-engineering/agents/plan.md". Los IDEs (Claude Code, GitHub Copilot, Gemini, Codex) **no siguen estas redirecciones** — priorizan responder al usuario sobre seguir una cadena de redirects. Resultado: 8 agentes y 38 skills tienen comportamiento definido pero nunca ejecutado.

**Evidencia**: Ejecutar `/ai-plan` en Claude Code no produce Interrogation Phase. El agente va directo al análisis sin preguntar. El contenido existe en `.ai-engineering/agents/plan.md` línea 77 pero nunca llega a leerse.

**Duplicación innecesaria**: `.ai-engineering/agents/` y `.ai-engineering/skills/` son copias de `src/ai_engineering/templates/.ai-engineering/agents/` y `src/ai_engineering/templates/.ai-engineering/skills/`. La fuente real está en el package Python — las copias en `.ai-engineering/` del repo son redundantes.

## Solution

Eliminar `.ai-engineering/agents/` y `.ai-engineering/skills/` de TODOS los repos (framework y targets). El contenido se copia FULL IDE-adapted directamente a los directorios de cada IDE:

1. **Claude Code**: `.claude/agents/ai-plan.md` (200+ líneas + frontmatter: model, tools, maxTurns)
2. **GitHub Copilot**: `.github/agents/plan.agent.md` (200+ líneas + frontmatter: model, color, tools)
3. **Generic IDEs**: `.agents/agents/ai-plan.md` (200+ líneas)

Lo mismo para skills: de thin wrappers a full content IDE-adapted.

La ÚNICA fuente canónica es `src/ai_engineering/templates/.ai-engineering/` (dentro del package Python). El sync script lee de ahí, transforma cross-references al formato IDE correcto, y genera FULL content en todas las superficies.

### Cross-Reference Translation

El sync script traduce paths internos al formato de cada IDE:

| Canonical | Claude | Copilot | Generic |
|---|---|---|---|
| `skills/plan/SKILL.md` | `.claude/skills/ai-plan/SKILL.md` | `.github/prompts/ai-plan.prompt.md` | `.agents/skills/plan/SKILL.md` |
| `agents/build.md` | `.claude/agents/ai-build.md` | `.github/agents/build.agent.md` | `.agents/agents/ai-build.md` |
| `standards/...` | `.ai-engineering/standards/...` | igual | igual |

## Scope

### In Scope

- Reescribir 6 funciones de generación en `sync_command_mirrors.py` (thin → full embed)
- Nueva función `generate_claude_agent()` (reemplaza validate-only)
- Nuevas funciones: `read_canonical_body()`, `transform_cross_references()`
- Cambiar canonical source: `.ai-engineering/` → `src/ai_engineering/templates/.ai-engineering/`
- Eliminar `.ai-engineering/agents/` y `.ai-engineering/skills/` del framework repo
- Añadir `exclude` param a `copy_template_tree()` en installer
- Actualizar ownership patterns en `defaults.py`
- Actualizar 5 validator categories para escanear IDE dirs
- Actualizar skills service y CLI
- Actualizar instruction files templates (CLAUDE.md, AGENTS.md, copilot-instructions.md)
- Migración automática en `ai-eng update` para targets legacy
- Actualizar tests (unit, integration, e2e)

### Out of Scope

- Cambiar la estructura de `src/ai_engineering/templates/.ai-engineering/` (se mantiene como canonical)
- Modificar `.ai-engineering/state/`, `context/`, `standards/`, `manifest.yml` (se mantienen)
- Cambios al formato de los canonical files (frontmatter, body structure)
- Refactorizar tests existentes que no se ven afectados

## Acceptance Criteria

| # | Criterion | Verification Command | Expected |
|---|----------|---------------------|----------|
| 1 | No agents/ en .ai-engineering/ | `test ! -d .ai-engineering/agents` | exit 0 |
| 2 | No skills/ en .ai-engineering/ | `test ! -d .ai-engineering/skills` | exit 0 |
| 3 | Canonical en templates | `test -f src/ai_engineering/templates/.ai-engineering/agents/plan.md` | exit 0 |
| 4 | Claude agent FULL | `wc -l < .claude/agents/ai-plan.md` | ≥150 |
| 5 | Interrogation Phase en Claude | `grep -c "Interrogation Phase" .claude/agents/ai-plan.md` | ≥1 |
| 6 | TDD Protocol en Claude | `grep -c "TDD Protocol" .claude/agents/ai-build.md` | ≥1 |
| 7 | Copilot agent FULL | `wc -l < .github/agents/plan.agent.md` | ≥150 |
| 8 | Generic agent FULL | `wc -l < .agents/agents/ai-plan.md` | ≥150 |
| 9 | Claude skill FULL (no redirect) | `grep -c "Read and execute the skill" .claude/skills/ai-commit/SKILL.md` | 0 |
| 10 | Cross-refs translated (Claude) | `grep -c "\.claude/skills/" .claude/agents/ai-plan.md` | ≥1 |
| 11 | Cross-refs translated (Copilot) | `grep -c "\.github/prompts/" .github/agents/plan.agent.md` | ≥1 |
| 12 | Sync check passes | `python scripts/sync_command_mirrors.py --check` | exit 0 |
| 13 | All tests pass | `uv run pytest tests/unit/ -x -q` | 0 failures |
| 14 | Integrity passes | `uv run pytest tests/unit/test_real_project_integrity.py -v` | all passed |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Cross-reference regex edge cases | Medium | Medium | Exhaustive test suite with all known path patterns |
| Template size explosion (~16K lines) | Low | Low | Generated files, not maintained by hand |
| Migration breaks existing targets | Low | High | Auto-detection + audit log + ownership-aware |
| CLAUDE.md loses references | Low | Medium | Phase 2 translates refs to IDE-specific |
| Sync script complexity increases | Medium | Low | Pure functions, well-tested |
