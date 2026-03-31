# manifest.yml como source of truth global

**Discovery Date**: 2026-03-31
**Context**: Multiple components hardcode config instead of reading from manifest.yml
**Spec**: spec-C

## Problem

TODO el proyecto (CLI, validators, hooks, skills, agents) debe consultar manifest.yml para config. Actualmente varios componentes hardcodean valores que deberian venir del manifiesto, violando el principio de single source of truth.

## Findings

Problemas actuales identificados:

1. **`_BASE_INSTRUCTION_FILES` en `_shared.py:116-148`** -- hardcodea CLAUDE.md sin consultar `ai_providers.enabled`
2. **`_PATH_REF_PATTERN` en `_shared.py:103-108`** -- tiene branch `context/` obsoleto
3. **`mirror_sync.py:422`** -- hardcodea CLAUDE.md
4. **`ManifestConfig.ai_providers`** -- existe como modelo Pydantic pero el validator lo ignora

IMPORTANTE: esto no es solo un issue de validate/verify -- es un principio de diseno: manifest.yml es la fuente de verdad para TODA configuracion en el framework. Cualquier componente que lea config de otro sitio o hardcodee valores que existen en el manifiesto es un bug de arquitectura.

## Code Examples

Locations to fix:
- `_shared.py:116-148` -- `_BASE_INSTRUCTION_FILES` hardcodes CLAUDE.md
- `_shared.py:103-108` -- `_PATH_REF_PATTERN` has obsolete `context/` branch
- `mirror_sync.py:422` -- hardcodes CLAUDE.md
- `ManifestConfig.ai_providers` -- Pydantic model exists but is unused by validator

## Pitfalls

- This is NOT just a validation issue -- it is a design principle affecting the entire framework
- Simply adding validation checks misses the point; every component must actively read from manifest.yml
- The Pydantic model for `ai_providers` already exists but is dead code -- activate it, do not recreate

## Related

- `.ai-engineering/manifest.yml` -- the manifest itself
- `ManifestConfig` Pydantic model
- `ai-eng validate` and `ai-eng verify` commands
