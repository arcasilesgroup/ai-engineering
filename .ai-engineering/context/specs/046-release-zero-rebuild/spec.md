---
id: "046"
slug: "release-zero-rebuild"
status: "in-progress"
created: "2026-03-10"
size: "S"
tags: ["cicd", "release", "security"]
branch: "feat/046-release-zero-rebuild"
pipeline: "hotfix"
decisions:
  - id: D-046-01
    decision: "Zero-rebuild: release descarga artefacto de CI, no recompila"
    rationale: "Garantiza que lo publicado es exactamente lo que CI validó — elimina drift entre build de CI y build de release"
---

# Spec 046 — Release Zero-Rebuild

## Problem

El workflow `release.yml` recompila el paquete desde cero cuando se pushea un tag `v*`. Este build de release:

1. **No hereda las garantías de CI** — ejecuta un subset mínimo de validaciones (solo ruff check + pytest genérico) vs las 11 gates de CI (lint, typecheck, 3 tiers de tests en multi-OS/multi-Python, SonarCloud, security audit, framework smoke, content integrity, workflow sanity).
2. **Puede producir un artefacto diferente** — el build ocurre en un momento distinto con posibles diferencias en resolución de dependencias, cache state, o entorno.
3. **Duplica trabajo** — CI ya produce y sube el artefacto `dist/` validado.

## Solution

Eliminar el build y las validaciones inline de `release.yml`. En su lugar:

1. **Verificar que CI pasó** en el commit del tag antes de proceder.
2. **Descargar el artefacto `dist/`** producido por CI en main.
3. **Publicar exactamente ese artefacto** a PyPI y GitHub Releases.

Esto garantiza: lo que se publica = lo que CI validó. Zero rebuild, zero drift.

## Scope

### In Scope

- Modificar `release.yml` para descargar artefacto de CI en vez de rebuild.
- Añadir verificación de CI status check antes de release.
- Modificar `ci.yml` para retener artefactos el tiempo suficiente (retention-days).
- Actualizar policy checks si aplica (`check_workflow_policy.py`).

### Out of Scope

- Cambios en la lógica de CI (gates, matrices, etc.).
- Migración a otro sistema de release (no GitHub Actions).
- Signed releases o attestations (posible spec futuro).

## Acceptance Criteria

1. `release.yml` NO contiene steps de `uv build`, `ruff check`, ni `pytest`.
2. `release.yml` descarga el artefacto `dist` producido por el workflow CI.
3. Si CI no pasó en el commit del tag, el release falla con mensaje claro.
4. El artefacto publicado en PyPI es bit-identical al producido por CI.
5. `check_workflow_policy.py` pasa sin errores.
6. GitHub Release se crea correctamente con los archivos de `dist/`.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-046-01 | Zero-rebuild: release descarga artefacto de CI | Garantiza paridad entre lo validado y lo publicado |
| D-046-02 | Usar `gh run download` o `actions/download-artifact` cross-workflow | Mecanismo nativo de GitHub Actions para compartir artefactos entre workflows |
| D-046-03 | Verificar CI status via GitHub API antes de proceder | Gate explícito: si CI no pasó, release no continúa |
