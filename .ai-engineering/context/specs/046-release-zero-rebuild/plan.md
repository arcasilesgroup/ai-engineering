---
spec: "046"
approach: "serial-phases"
---

# Plan — Release Zero-Rebuild

## Architecture

### Modified Files

| File | Purpose |
|------|---------|
| `.github/workflows/release.yml` | Eliminar build inline, descargar artefacto de CI |
| `.github/workflows/ci.yml` | Añadir `retention-days` al upload de `dist/` |
| `scripts/check_workflow_policy.py` | Actualizar si tiene reglas sobre release workflow |

### New Files

Ninguno.

### Key Design Decisions

**Cross-workflow artifact download**: GitHub Actions no permite `actions/download-artifact` entre workflows distintos directamente. Opciones:

1. **`dawidd6/action-download-artifact@v6`** — acción de terceros popular para cross-workflow download.
2. **`gh run download`** — CLI nativa, requiere `GH_TOKEN`.
3. **`actions/upload-artifact` + `actions/download-artifact` v4 con `run-id`** — v4 soporta `run-id` para cross-workflow.

**Recomendación**: opción 3 (`actions/download-artifact@v4` con `run-id`) — es nativa, sin dependencias de terceros, y v4 ya soporta el parámetro `run-id` para descargar artefactos de otro workflow run.

**CI status verification**: Usar `gh api` para consultar el combined status del commit antes de proceder. Step separado con `if: failure()` para mensaje claro.

## Session Map

### Phase 0: Scaffold [S]
- Crear spec, plan, tasks.
- Activar en `_active.md`.

### Phase 1: Implement [M]
- Modificar `ci.yml`: añadir `retention-days: 5` al artifact upload.
- Reescribir `release.yml`:
  - Job `verify-ci`: consultar CI status del commit del tag.
  - Job `publish`: descargar artefacto cross-workflow, publicar a PyPI.
  - Job `github-release`: descargar artefacto, crear release.
- Verificar `check_workflow_policy.py`.

### Phase 2: Validate [S]
- Ejecutar `actionlint` sobre los workflows modificados.
- Ejecutar `check_workflow_policy.py`.
- Dry-run mental del flujo: tag push → verify CI → download artifact → publish.

## Patterns

- Commits atómicos por fase: `spec-046: Phase N — description`.
- Gate verification antes de cada merge.
