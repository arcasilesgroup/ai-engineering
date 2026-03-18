---
id: "052"
slug: plan-tdd-acceptance
title: "Interrogación Profunda, TDD Two-Agent, y Acceptance Criteria Ejecutables"
status: draft
created: "2026-03-15"
size: "L"
tags: ["planning", "tdd", "testing", "acceptance-criteria", "agents", "skills"]
branch: "spec/052-plan-tdd-acceptance"
pipeline: "full"
decisions: []
---

# Spec 052 — Interrogación Profunda, TDD Two-Agent, y Acceptance Criteria Ejecutables

## Problem

El spec-051 (Architecture v3) demostró 3 fallos sistémicos en el flujo plan→implement→verify:

1. **Plan sin interrogación** — El plan agent aceptó el request literal sin cuestionar asunciones, explorar el codebase, ni challenge vague language. Resultado: spec definió 10 agentes/40 skills, se implementaron 8/38, y nadie detectó la divergencia.

2. **Acceptance criteria en prosa** — Los 12 ACs del spec-051 eran frases ("All Python tests pass") sin comandos ejecutables. Los tests pasaron pero validaban agentes fantasma (execute, ship, observe, write). El AC "Template mirror byte-identical" nunca se verificó — encontramos 28 fails de mirror-sync meses después.

3. **Tests que testan fixtures, no realidad** — 71% de los unit tests (47 de 66) crean su propio mundo en tmp_path. Pueden pasar con una arquitectura completamente diferente a la real. No hay separación test-writer/implementer — el mismo agente que escribe código puede debilitar los tests.

ai-engineering es un framework para **múltiples equipos de engineers** que desarrollan apps y soluciones. La separación de roles (quien escribe tests vs quien implementa) es crítica para garantizar integridad.

## Solution

Tres cambios estructurales al flujo plan→implement→verify:

### 1. Interrogation Phase en el Plan Agent

Antes de clasificar o producir specs, el plan agent DEBE:
- Lanzar explorers para entender el codebase actual
- Preguntar ONE AT A TIME (no batching)
- Challenge vague language ("mejorar" → "¿qué específicamente?")
- Mapear KNOWN/ASSUMED/UNKNOWN — no proceder con UNKNOWNs
- Identificar second-order consequences
- Surface constraints no mencionados

Inspirado en el pattern de superpowers/brainstorming: "Leave no stone unturned. Challenge vague language ruthlessly."

### 2. Acceptance Criteria Ejecutables en spec.md

Los ACs pasan de prosa a tabla con **Verification Command** + **Expected**:

```markdown
| # | Criterion | Verification Command | Expected |
|---|----------|---------------------|----------|
| 1 | Mirrors in sync | `python scripts/sync_command_mirrors.py --check` | exit 0 |
| 2 | Integrity passes | `uv run ai-eng validate` | exit 0 |
```

Cualquiera puede ejecutar el comando y verificar. No ambigüedad.

### 3. TDD Two-Phase (RED→GREEN separation in build agent)

El build agent ejecuta TDD en dos fases separadas, enforced por dispatch:
- **Phase RED**: build escribe failing tests + produce Implementation Contract
- **Phase GREEN**: build implementa sin tocar tests (inmutables desde RED)

Dispatch envía dos tasks separadas: T-RED (write tests) y T-GREEN (implement). Los test files de T-RED son inmutables en T-GREEN. Verify mantiene su scope read-only — no participa en TDD.

Iron Law: si los tests están mal, escalar al usuario — NUNCA debilitar tests.

### 4. Test Skill Multi-Stack

Reescribir `skills/test/SKILL.md` como skill detallado multi-stack (20 stacks) con:
- TDD cycle (RED-GREEN-REFACTOR)
- Fakes over mocks (Protocol-based)
- AAA pattern obligatorio
- Rationalization table (del superpowers/tdd skill)
- Flaky test diagnostic (6 categorías)
- Coverage strategy (80% core, branch coverage)

## Scope

### In Scope

- Modificar `agents/plan.md` — añadir Interrogation Phase
- Modificar `agents/build.md` — añadir TDD Protocol (RED+GREEN phases)
- NO modificar `agents/verify.md` — mantiene read-only scope
- Reescribir `skills/test/SKILL.md` — multi-stack, TDD, fakes, flaky guide
- Modificar `skills/spec/SKILL.md` — AC ejecutables en scaffold
- Modificar `skills/plan/SKILL.md` — añadir PLAN-R5 Interrogation rule
- Sincronizar mirrors tras cambios
- Actualizar templates

### Out of Scope

- Refactorizar tests existentes (test_validator.py etc.) — tracked como spec separado
- Crear acceptance.py ejecutable — ACs son verificables manualmente con comandos
- Nuevo agente TDD — verify agent asume el rol
- Cambios al código Python de src/ — solo governance files

## Acceptance Criteria

| # | Criterion | Verification Command | Expected |
|---|----------|---------------------|----------|
| 1 | Plan agent tiene Interrogation Phase | `grep -c "Interrogation Phase" .ai-engineering/agents/plan.md` | ≥1 |
| 2 | Plan skill tiene PLAN-R5 | `grep -c "PLAN-R5" .ai-engineering/skills/plan/SKILL.md` | ≥1 |
| 3 | Build agent tiene TDD Protocol | `grep -c "TDD Protocol" .ai-engineering/agents/build.md` | ≥1 |
| 4 | Build agent tiene Iron Law | `grep -c "Iron Law" .ai-engineering/agents/build.md` | ≥1 |
| 5 | Test skill tiene Iron Law | `grep -c "Iron Law\|NO PRODUCTION CODE WITHOUT" .ai-engineering/skills/test/SKILL.md` | ≥1 |
| 6 | Test skill tiene multi-stack (≥5 stacks) | `grep -c "### Python\|### TypeScript\|### .NET\|### React\|### Rust" .ai-engineering/skills/test/SKILL.md` | ≥5 |
| 7 | Spec skill tiene Verification Command | `grep -c "Verification Command" .ai-engineering/skills/spec/SKILL.md` | ≥1 |
| 8 | Mirrors in sync | `python scripts/sync_command_mirrors.py --check` | exit 0 |
| 9 | Integrity passes | `uv run pytest tests/unit/test_real_project_integrity.py -v` | 6 passed |
| 10 | All existing tests pass | `uv run pytest tests/unit/ -x -q` | 0 failures |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Interrogation phase too verbose → user fatigue | Medium | Medium | Limit to 5-7 questions max per session |
| TDD two-agent adds coordination overhead | Low | Low | Clear Implementation Contract format |
| Test skill too long (>500 lines) | Medium | Low | Progressive disclosure: core + stack references |
| ACs become busywork if too granular | Low | Medium | Focus on commands that catch real drift |
