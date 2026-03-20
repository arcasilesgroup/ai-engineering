# spec-056: Enterprise Artifact Feed & Manifest Reorganization

## Status: DRAFT

## Problem

1. **No hay soporte para feeds privados**: ai-engineering resuelve todas las dependencias desde PyPI publico. En entornos enterprise (banca, finanzas, sanidad), el acceso a PyPI esta bloqueado por politica de red. Solo se permite acceso a feeds privados (Azure Artifacts, JFrog Artifactory, Nexus).

2. **manifest.yml mezcla secciones**: no hay separacion clara entre lo que el usuario debe configurar y lo que el framework gestiona automaticamente. Un usuario nuevo no sabe que tocar.

3. **Sin validacion de coherencia**: si un usuario configura un feed privado pero deja restos de PyPI en `uv.lock`, nada lo detecta.

## Decisions

- Config real de feeds en `pyproject.toml` (`[tool.uv.index]`), manifest solo como puntero
- Distribution lock estricto: sin fallback a PyPI publico
- Auth via keyring del sistema (cross-platform: Windows/macOS/Linux)
- Manifest reorganizado con separador de comentarios (user config arriba, managed abajo)
- `ai-eng doctor` valida coherencia de feeds
- Documentar incompatibilidad de Dependabot con feeds privados
- No incluir feed config en el template de proyecto (repos existentes ya tienen pyproject.toml)
- `pip-audit` fuera de scope (feeds privados hacen mirror de publicos, CVEs siguen detectandose)

## Scope

### In scope

1. **Reorganizar `manifest.yml`**: dos bloques con comentario separador
   - Arriba: `# === USER CONFIGURATION ===` (providers, work_items, quality, documentation, puntero a feeds)
   - Abajo: `# === FRAMEWORK MANAGED (do not edit) ===` (skills, agents, ownership, tooling, telemetry)

2. **Seccion comentada en `pyproject.toml`**: bloque `[[tool.uv.index]]` documentado, listo para descomentarla
   - Instrucciones claras de como rellenar URL y nombre
   - Indicacion de que auth va por keyring
   - Ejemplo para Azure Artifacts, JFrog, Nexus
   - Sin entrada de `pypi.org` (distribution lock estricto)
   - Cabecera tipo `# === USER CONFIGURATION ===` igual que en manifest

3. **Validacion en `ai-eng doctor`**: nuevos checks
   - Si `[[tool.uv.index]]` configurado sin PyPI: verificar que `uv.lock` no contenga `source = { registry = "https://pypi.org/simple" }`
   - Si feed privado configurado: verificar que keyring responde para la URL (`keyring get <url> <username>`)
   - Warning si feed configurado pero distribution lock incompleto (PyPI aun presente como index)

4. **Documentar incompatibilidad Dependabot**: ejemplo comentado de seccion `registries` en `dependabot.yml`

### Out of scope

- Configuracion de feeds para npm, NuGet, Maven (futuro, cuando se soporten mas stacks)
- Integracion con `/ai-onboard` o `/ai-guide` para setup guiado
- Cambios en `pip-audit` o CI workflow
- Incluir feed config en template de proyecto

## Design

### manifest.yml — nueva estructura

```yaml
# === USER CONFIGURATION ===
# Edit this section to match your project and organization.

schema_version: "2.0"
framework_version: "0.4.0"
name: ai-engineering
version: "1.0.0"

# Providers
providers:
  vcs: github
  ides: [claude_code, github_copilot]
  stacks: [python]

# Artifact feeds — configure your private feed in pyproject.toml [tool.uv.index]
# See the commented section in pyproject.toml for instructions.
artifact_feeds:
  python: pyproject.toml  # pointer to actual config location

# Work items
work_items:
  provider: github
  # ...

# Quality gates
quality:
  coverage: 80
  duplication: 3
  cyclomatic: 10
  cognitive: 15

# Documentation auto-update
documentation:
  auto_update:
    readme: true
    changelog: true
    solution_intent: true
  external_portal:
    enabled: false
    source: null
    update_method: "pr"

# === FRAMEWORK MANAGED (do not edit below this line) ===
# These sections are maintained by ai-engineering automatically.

# Skills registry (31 skills)
skills:
  # ...

# Agents (8)
agents:
  # ...

# Ownership
ownership:
  # ...

# Tooling
tooling: [uv, ruff, gitleaks, pytest, ty, pip-audit]

# Telemetry
telemetry:
  consent: strict-opt-in
  default: disabled
```

### pyproject.toml — seccion de feeds

```toml
# === USER CONFIGURATION: Enterprise Artifact Feed ===
#
# If your organization uses a private package feed (Azure Artifacts, JFrog
# Artifactory, Nexus), uncomment and configure the section below.
#
# This enables "distribution lock": ALL packages resolve from your private
# feed only — no fallback to public PyPI.
#
# Authentication: uses system keyring (cross-platform).
#   macOS:   Keychain Access
#   Windows: Credential Manager
#   Linux:   Secret Service (GNOME Keyring / KWallet)
#
# Setup keyring credentials:
#   keyring set <feed-url> <username>
#
# Enable uv keyring integration:
#   export UV_KEYRING_PROVIDER=subprocess
#
# --- Azure Artifacts ---
# [[tool.uv.index]]
# name = "corporate"
# url = "https://pkgs.dev.azure.com/ORG/PROJECT/_packaging/FEED/pypi/simple/"
# default = true
#
# --- JFrog Artifactory ---
# [[tool.uv.index]]
# name = "corporate"
# url = "https://COMPANY.jfrog.io/artifactory/api/pypi/REPO/simple/"
# default = true
#
# --- Nexus Repository ---
# [[tool.uv.index]]
# name = "corporate"
# url = "https://nexus.company.com/repository/REPO/simple/"
# default = true
#
# IMPORTANT: Do NOT add a pypi.org entry. Omitting it enforces distribution
# lock — uv will only resolve from your private feed.
#
# === END USER CONFIGURATION ===
```

### ai-eng doctor — nuevos checks

```
Check: feed-coherence
  Trigger: [[tool.uv.index]] present in pyproject.toml without pypi.org entry
  Validate: uv.lock does not contain 'registry = "https://pypi.org/simple"'
  Severity: ERROR if violated (distribution lock broken)

Check: feed-keyring
  Trigger: [[tool.uv.index]] present with non-pypi URL
  Validate: UV_KEYRING_PROVIDER=subprocess is set, keyring responds for feed URL
  Severity: WARNING if keyring not accessible

Check: feed-lock-freshness
  Trigger: [[tool.uv.index]] present
  Validate: uv.lock exists and is not older than pyproject.toml
  Severity: WARNING if stale
```

### dependabot.yml — ejemplo comentado

```yaml
# NOTE: With distribution lock (private feed only, no PyPI), Dependabot
# requires registry configuration to authenticate against your feed.
# Uncomment and configure the section below.
#
# registries:
#   corporate-feed:
#     type: python-index
#     url: https://pkgs.dev.azure.com/ORG/PROJECT/_packaging/FEED/pypi/simple/
#     username: az
#     password: ${{ secrets.AZURE_ARTIFACTS_TOKEN }}
#
# Then reference it in the update entry:
#   updates:
#     - package-ecosystem: pip
#       registries:
#         - corporate-feed
```

## Files to modify

| File | Change |
|------|--------|
| `.ai-engineering/manifest.yml` | Reorganize: user config above, managed below. Add `artifact_feeds` pointer. |
| `pyproject.toml` | Add commented `[[tool.uv.index]]` section with instructions. |
| `.github/dependabot.yml` | Add commented `registries` example. |
| `src/ai_engineering/cli/doctor.py` | Add feed-coherence, feed-keyring, feed-lock-freshness checks. |
| `src/ai_engineering/templates/project/.ai-engineering/manifest.yml` | Same manifest reorganization for template. |

## Acceptance criteria

- [ ] `manifest.yml` has clear `USER CONFIGURATION` / `FRAMEWORK MANAGED` separation
- [ ] `pyproject.toml` has commented feed section with instructions for 3 providers
- [ ] `ai-eng doctor` detects broken distribution lock (PyPI in uv.lock when feed is private)
- [ ] `ai-eng doctor` warns when keyring is not configured for feed URL
- [ ] `dependabot.yml` has commented registries example
- [ ] Template manifest matches the same reorganization
- [ ] All existing functionality unchanged (no regression)

## Refs

- uv index docs: tool.uv.index in pyproject.toml
- DEC-010: Dual VCS provider support
- Target audience: banking, finance, healthcare enterprises
