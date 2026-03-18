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

**Race condition con `ai-eng release`**: Cuando se usa `ai-eng release` sin `--wait`, el tag se crea inmediatamente después del merge a main. CI en main puede no haber terminado aún. El job `verify-ci` del release.yml debe:
1. Buscar el CI workflow run para el commit del tag.
2. Si está `in_progress` o `queued`, esperar con backoff (max ~5 min).
3. Si `completed` + `success`, proceder.
4. Si `completed` + `failure`, fallar con mensaje claro.
5. Si no existe run (edge case), fallar.

**Compatibilidad con `ai-eng release` orchestrator**: No se requieren cambios en `src/ai_engineering/release/orchestrator.py`. El orchestrator:
- Crea el tag vía `_create_tag` → dispara release.yml (trigger no cambia)
- Monitorea vía `_monitor_pipeline` por nombre "Release" + SHA (contrato no cambia)
- El flujo validate→prepare→PR→merge→tag→monitor sigue intacto

## Session Map

### Phase 0: Scaffold [S]
- Crear spec, plan, tasks.
- Activar en `_active.md`.

### Phase 1: Implement [M]
- Modificar `ci.yml`: añadir `retention-days: 5` al artifact upload.
- Reescribir `release.yml`:
  - Job `verify-ci`: consultar CI status con retry/backoff para race condition.
  - Job `download-artifact`: buscar CI run-id y descargar `dist/` cross-workflow.
  - Job `publish`: publicar a PyPI usando artefacto descargado.
  - Job `github-release`: crear release con artefacto descargado.
- Verificar `check_workflow_policy.py`.

### Phase 2: Validate [S]
- Ejecutar `actionlint` sobre los workflows modificados.
- Ejecutar `check_workflow_policy.py`.
- Verificar flujo completo: `ai-eng release` (con `--wait`) → tag → verify-ci → download → publish.
- Verificar flujo sin `--wait`: tag inmediato → verify-ci retry → download → publish.

## Patterns

- Commits atómicos por fase: `spec-046: Phase N — description`.
- Gate verification antes de cada merge.
