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
   - `ownership` va en FRAMEWORK MANAGED porque los paths son definidos por el framework
   - `quality` va en USER CONFIGURATION porque los umbrales son decisiones del equipo

2. **Seccion comentada en `pyproject.toml`**: bloque `[[tool.uv.index]]` documentado, listo para descomentarla
   - Insertar despues de `[dependency-groups]` y antes de `[project.scripts]` (linea 27 del pyproject.toml actual)
   - Instrucciones claras de como rellenar URL y nombre
   - Explicar que `default = true` reemplaza PyPI como fuente por defecto
   - Indicacion de que auth va por keyring
   - Ejemplo para Azure Artifacts, JFrog, Nexus
   - Sin entrada de `pypi.org` (distribution lock estricto)
   - Cabecera tipo `# === USER CONFIGURATION ===` igual que en manifest

3. **Validacion en `ai-eng doctor`**: nuevo modulo `src/ai_engineering/doctor/checks/feeds.py` con 4 checks:
   - `feed-lock-leak`: feed privado configurado sin PyPI en indexes, PERO `pypi.org` encontrado en `uv.lock` → ERROR (distribution lock roto)
   - `feed-mixed-sources`: feed privado configurado Y `pypi.org` tambien presente como index → WARNING (distribution lock no enforced)
   - `feed-keyring`: feed privado configurado → verificar keyring accesible. Tres niveles:
     - `keyring` CLI no encontrado → ERROR con instruccion de instalacion
     - `keyring` CLI encontrado pero sin backend disponible → WARNING con link a docs de headless setup
     - `keyring` CLI encontrado, backend disponible, pero sin credencial para la URL → WARNING con instruccion `keyring set`
   - `feed-lock-freshness`: feed configurado → verificar que `uv.lock` existe y no es mas viejo que `pyproject.toml`
     - Si `uv.lock` no existe → WARNING ("run `uv lock` to generate lockfile")
     - Si `uv.lock` no existe, `feed-lock-leak` → SKIP (no se puede validar sin lockfile)

4. **Documentar incompatibilidad Dependabot**: ejemplo comentado de seccion `registries` en `dependabot.yml`
   - Solo aplica cuando `providers.vcs: github` (Dependabot es GitHub-only)

### Out of scope

- Configuracion de feeds para npm, NuGet, Maven (futuro, cuando se soporten mas stacks)
- Integracion con `/ai-onboard` o `/ai-guide` para setup guiado
- Cambios en `pip-audit` o CI workflow
- Incluir feed config en template de proyecto
- Autenticacion en CI (CI no tiene keyring; los equipos usan `UV_INDEX_<NAME>_PASSWORD` como secret — esto es configuracion de pipeline, no del framework)

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
  azure_devops:
    area_path: "Project\\TeamName"
  github:
    team_label: "team:core"
  hierarchy:
    feature: never_close
    user_story: close_on_pr
    task: close_on_pr
    bug: close_on_pr

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
  total: 31
  prefix: "ai-"
  registry:
    # ... (current registry content unchanged)

# Agents (8)
agents:
  total: 8
  names: [plan, build, verify, guard, review, explore, guide, simplify]

# Ownership
ownership:
  framework: [".claude/skills/**", ".claude/agents/**", ".ai-engineering/**"]
  team: [".ai-engineering/contexts/team/**"]
  system: [".ai-engineering/state/**"]

# Tooling
tooling: [uv, ruff, gitleaks, pytest, ty, pip-audit]

# Telemetry
telemetry:
  consent: strict-opt-in
  default: disabled
```

### pyproject.toml — seccion de feeds

Insertar despues de `[dependency-groups]` (linea 27) y antes de `[project.scripts]` (linea 28):

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
# Setup:
#   1. Store credentials: keyring set <feed-url> <username>
#   2. Enable uv keyring: export UV_KEYRING_PROVIDER=subprocess
#   3. Uncomment ONE of the provider blocks below and fill in your values.
#
# In CI (no keyring available), use environment variables instead:
#   UV_INDEX_CORPORATE_USERNAME=<user>
#   UV_INDEX_CORPORATE_PASSWORD=<token>
#
# --- Azure Artifacts ---
# [[tool.uv.index]]
# name = "corporate"
# url = "https://pkgs.dev.azure.com/ORG/PROJECT/_packaging/FEED/pypi/simple/"
# default = true  # replaces PyPI as the default package source
#
# --- JFrog Artifactory ---
# [[tool.uv.index]]
# name = "corporate"
# url = "https://COMPANY.jfrog.io/artifactory/api/pypi/REPO/simple/"
# default = true  # replaces PyPI as the default package source
#
# --- Nexus Repository ---
# [[tool.uv.index]]
# name = "corporate"
# url = "https://nexus.company.com/repository/REPO/simple/"
# default = true  # replaces PyPI as the default package source
#
# IMPORTANT: Do NOT add a pypi.org entry. Omitting it enforces distribution
# lock — uv will only resolve from your private feed.
#
# === END USER CONFIGURATION ===
```

### ai-eng doctor — nuevos checks

Nuevo fichero: `src/ai_engineering/doctor/checks/feeds.py`

```
Check: feed-lock-leak
  Trigger: [[tool.uv.index]] present WITHOUT pypi.org entry
  Validate: uv.lock does not contain 'registry = "https://pypi.org/simple"'
  If uv.lock missing: SKIP
  Severity: ERROR if violated (distribution lock broken — regenerate with `uv lock`)

Check: feed-mixed-sources
  Trigger: [[tool.uv.index]] present WITH non-pypi URL AND pypi.org also present as index
  Validate: n/a (presence alone triggers)
  Severity: WARNING ("distribution lock not enforced — remove pypi.org entry to lock")

Check: feed-keyring
  Trigger: [[tool.uv.index]] present with non-pypi URL
  Validate (graduated):
    1. `keyring` CLI found in PATH → if not: ERROR ("install keyring: pip install keyring")
    2. keyring backend available → if not: WARNING ("no keyring backend — see docs")
    3. credential stored for feed URL → if not: WARNING ("run: keyring set <url> <user>")
  CI detection: if CI=true or GITHUB_ACTIONS=true → SKIP (CI uses env vars, not keyring)
  Severity: ERROR or WARNING per level above

Check: feed-lock-freshness
  Trigger: [[tool.uv.index]] present
  Validate: uv.lock exists and mtime >= pyproject.toml mtime
  If uv.lock missing: WARNING ("run `uv lock` to generate lockfile")
  Severity: WARNING if stale
```

### dependabot.yml — ejemplo comentado

Aplica solo cuando `providers.vcs: github`.

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
| `pyproject.toml` | Add commented `[[tool.uv.index]]` section after `[dependency-groups]`, before `[project.scripts]`. |
| `.github/dependabot.yml` | Add commented `registries` example. |
| `src/ai_engineering/doctor/checks/feeds.py` | New file. 4 checks: feed-lock-leak, feed-mixed-sources, feed-keyring, feed-lock-freshness. |
| `src/ai_engineering/doctor/service.py` | Register new feeds checks module. |
| `tests/test_doctor_feeds.py` | Tests for the 4 new checks. |

## Acceptance criteria

- [ ] `manifest.yml` has clear `USER CONFIGURATION` / `FRAMEWORK MANAGED` separation
- [ ] `pyproject.toml` has commented feed section with instructions for 3 providers (Azure, JFrog, Nexus)
- [ ] `ai-eng doctor` detects broken distribution lock (PyPI in uv.lock when private feed configured without PyPI index)
- [ ] `ai-eng doctor` warns when PyPI coexists with private feed (mixed sources)
- [ ] `ai-eng doctor` validates keyring with 3 graduated levels (not installed, no backend, no credential)
- [ ] `ai-eng doctor` skips keyring check in CI environments
- [ ] `ai-eng doctor` warns when uv.lock is missing or stale
- [ ] `dependabot.yml` has commented registries example
- [ ] All existing tests pass (no regression)

## Refs

- uv index docs: tool.uv.index in pyproject.toml
- DEC-010: Dual VCS provider support
- Target audience: banking, finance, healthcare enterprises
