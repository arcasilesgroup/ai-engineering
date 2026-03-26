---
id: "079"
title: "Install & Contexts Cleanup — Project Identity, Hooks, Orgs, Enforcement, README"
status: approved
type: feature
scope: framework
effort: max
sub_specs: 6
autopilot_ready: true
created: 2026-03-26
review_iteration: 1
---

# spec-079: Install & Contexts Cleanup

## Problem Statement

La capa `.ai-engineering/` tiene deuda técnica acumulada en 6 áreas que afectan la experiencia de instalación, la efectividad de los contextos, y la coherencia del framework:

1. **Templates zombie**: `framework-contract.md` y `product-contract.md` fueron eliminados del repo activo (spec-055) pero **sobreviven en templates** y se copian a repos nuevos con datos específicos del proyecto ai-engineering.
2. **Hooks con ruido**: `.ai-engineering/scripts/hooks/` tiene 6+ archivos muertos de migración (telemetry-*.sh/.ps1 sin prefijo copilot-) y un directorio fantasma en `scripts/hooks/` top-level.
3. **contexts/orgs: MUERTO**: Stub de 1 línea con promesa de "auto-detected from git remote" que nunca se implementó. Cero skills, cero agentes, cero CLI lo usan.
4. **Contexts sin enforcement**: Solo 7/15 lenguajes tienen handlers dedicados. El resto depende de una instrucción genérica que el modelo puede ignorar. `universal.md` tiene 0 referencias. `cpp.md` está referenciado pero no existe. CLAUDE.md no dispara carga de contexts.
5. **Install no crea team/**: `governance.py:127` hace hard-skip de todo bajo `contexts/team/`. Los 4 seed files nunca llegan al proyecto. Tampoco se crea `specs/`.
6. **README.md inútil**: Dice "30 skills / 8 agents" (real: 37/9). No tiene getting started, no explica manifest.yml, no documenta workflows.

## Evidence Summary

| Área | Hallazgo | Severidad |
|------|----------|-----------|
| Templates contract | `src/ai_engineering/templates/.ai-engineering/contexts/product/` vivo con 804 líneas | HIGH |
| Templates contract | `product-contract.md` contiene datos específicos del proyecto (nombre, versión, KPIs) | HIGH |
| Templates contract | `copilot-instructions.md` referencia path antiguo `context/` (sin `s`) | MEDIUM |
| Templates contract | Contradicción ownership: archivo dice `framework-managed`, defaults.py dice `TEAM_MANAGED/DENY` | MEDIUM |
| Hooks | `telemetry-skill.sh`, `telemetry-session.sh`, `telemetry-agent.sh` + `.ps1` = código muerto | LOW |
| Hooks | `scripts/hooks/` top-level = directorio fantasma con solo `_lib/__pycache__/` | LOW |
| contexts/orgs | 0 skills, 0 agents, 0 CLI commands, 0 handlers lo referencian | HIGH |
| contexts/orgs | README promete "Auto-detected from git remote" — no existe en ningún código | MEDIUM |
| Contexts efficiency | 7 lenguajes ACTIVOS (con handler dedicado), 8 REFERENCIADOS_PERO_NO_LEÍDOS | MEDIUM |
| Contexts efficiency | `universal.md` (281 líneas) = MUERTO, 0 referencias | LOW |
| Contexts efficiency | `cpp.md` referenciado por handler pero archivo no existe | MEDIUM |
| Contexts efficiency | Mecanismo de carga es trust-based, sin enforcement | HIGH |
| Install team/ | `governance.py:127-128` hard-skip de `contexts/team/` — nunca se crea | HIGH |
| Install specs/ | No hay templates para `specs/` — nunca se crea el directorio | MEDIUM |
| README | Counts stale (30/8 vs 37/9), sin getting started, sin manifest docs | MEDIUM |

## Orchestration (3 waves)

```
Wave 1: B + C       (paralelo — cero overlap de archivos)
Wave 2: A + E       (secuencial — ambos tocan governance.py, A primero luego E)
         + D        (paralelo con A+E — D toca languages/CLAUDE.md, sin overlap con governance.py)
Wave 3: F           (README — consolida estado final de todo)
```

Justificación de dependencias:
- B y C: totalmente independientes, no comparten archivos
- A debe ir antes que E: ambos modifican `governance.py` — A añade project-identity seed, E cambia lógica de team/
- A debe ir antes que D: ambos tocan `copilot-instructions.md`
- D no toca `governance.py` → puede ejecutarse en paralelo con E (después de A)
- F necesita el estado final de todo → siempre última

Dentro de Wave 2, orden secuencial: A → (D + E en paralelo)

---

## Sub-specs

### Sub-spec A: Project Identity (Wave 2, primero)

**Objetivo**: Reemplazar `framework-contract.md` + `product-contract.md` con `project-identity.md` — un documento liviano que captura la esencia del proyecto consumidor. Crear skill `/ai-project-identity` para generarlo.

**Qué es `project-identity.md`**: La esencia del proyecto donde vive ai-engineering. NO duplica manifest.yml (config técnica) ni CLAUDE.md (reglas del AI) ni solution-intent (arquitectura completa). Captura lo que ningún otro documento cubre:
- Qué es el proyecto, para qué existe, por qué
- Servicios, APIs, frontales que consume o expone
- Dependencias críticas y consumidores downstream
- Boundaries que no se pueden romper
- A quién notificar si cambian ciertas cosas

**Tamaño**: ~30-50 líneas. Liviano para cargarse siempre en contexto sin presión.

**Carga**: Via instrucción centralizada en CLAUDE.md y copilot-instructions.md (NO modificar cada SKILL.md individualmente — la instrucción raíz cubre todos los skills). Además, lectura explícita en brainstorm y plan handlers donde se necesita para diseño.

**Diferencia con solution-intent**: `docs/solution-intent.md` es el documento de arquitectura completo (500+ líneas). Solo se carga bajo demanda explícita del usuario. `project-identity.md` es el resumen ejecutivo que cabe en contexto.

**Cambios**:

1. **Eliminar** `src/ai_engineering/templates/.ai-engineering/contexts/product/framework-contract.md`
2. **Eliminar** `src/ai_engineering/templates/.ai-engineering/contexts/product/product-contract.md`
3. **Eliminar** el directorio `contexts/product/` de los templates
4. **Verificar y eliminar** `.ai-engineering/contexts/product/` del dogfood si existe (la governance mirror requiere paridad)
5. **Crear** `src/ai_engineering/templates/.ai-engineering/contexts/project-identity.md` — template con secciones:
   - Project (nombre, propósito en 1-2 frases, por qué existe)
   - Services & APIs (qué expone, qué consume)
   - Dependencies & Consumers (quién depende de esto, de quién depende)
   - Boundaries (qué NO se puede romper, a quién notificar)
6. **Actualizar** `governance.py` para copiar `project-identity.md` como template seed (create-only, modo FRESH)
7. **Actualizar** handlers de diseño para lectura explícita de `project-identity.md`:
   - `.claude/skills/ai-brainstorm/SKILL.md` — paso 1 load context
   - `.claude/skills/ai-brainstorm/handlers/interrogate.md` — preguntar si identity necesita actualización
   - `.claude/skills/ai-plan/SKILL.md`
   - Mirrors en `.github/` y `.agents/`
8. **Actualizar** CLAUDE.md — añadir instrucción en sección principal:
   ```
   Before writing code or reviewing changes, read `.ai-engineering/contexts/project-identity.md` if it exists.
   ```
   Esto cubre automáticamente todos los skills sin modificar 30+ archivos individuales.
9. **Actualizar** copilot-instructions.md — misma instrucción + fix del path `context/` → `contexts/` + eliminar referencia a `framework-contract.md`
10. **Actualizar** ai-governance para validar contra `project-identity.md` (boundaries de negocio) + `CLAUDE.md` + manifest (reglas técnicas):
    - `.claude/skills/ai-governance/SKILL.md`
    - `src/ai_engineering/templates/project/.github/skills/ai-governance/SKILL.md`
    - `src/ai_engineering/templates/project/.agents/skills/governance/SKILL.md`
11. **Actualizar** `defaults.py` — reemplazar `contexts/product/**` ownership con `contexts/project-identity.md` como `TEAM_MANAGED/DENY`
12. **Migrar** lógica de pointer-count de `instruction_consistency.py` a `counter_accuracy.py` (la validación que CLAUDE.md dice "Skills (N)" debe coincidir con manifest). Luego eliminar `instruction_consistency.py`.
13. **Actualizar** tests:
    - `tests/unit/test_state.py` — eliminar `test_contexts_product_denied`, añadir `test_contexts_project_identity_denied`
    - `tests/unit/test_validator.py` — eliminar fixtures de `product-contract.md`
    - `tests/integration/test_gap_fillers4.py` — actualizar fixtures
    - `tests/e2e/test_install_clean.py` — reemplazar `contexts/product` por `project-identity.md` en expected
14. **Decisión DEC-nuevo**: Documentar en decision-store.json la migración de contracts a project-identity
15. **Crear skill `/ai-project-identity`**: Skill dedicada para generar y rellenar el documento
    - Auto-detect: escanea manifest.yml, package.json/pyproject.toml, estructura del proyecto
    - Q&A: pregunta lo que no puede inferir (propósito, boundaries, stakeholders)
    - `.claude/skills/ai-project-identity/SKILL.md`
    - Effort: medium
    - Mirrors en `.github/skills/ai-project-identity/` y `.agents/skills/project-identity/`
16. **Actualizar counts** en todos los archivos que dicen "37 skills":
    - `manifest.yml` → `total: 38`
    - `manifest.yml` → añadir `ai-project-identity: { type: meta, tags: [governance] }` al registry
    - CLAUDE.md → `## Skills (38)` + añadir ai-project-identity en tabla Meta + effort table medium count 11→12
    - Template CLAUDE.md en `src/ai_engineering/templates/project/CLAUDE.md`
    - AGENTS.md si tiene count
    - Template copilot-instructions.md si tiene count

---

### Sub-spec B: Hooks Cleanup (Wave 1)

**Objetivo**: Eliminar archivos muertos de migración en hooks sin romper el mecanismo activo.

**Archivos a ELIMINAR** (lista exhaustiva):
- `telemetry-skill.sh`
- `telemetry-session.sh`
- `telemetry-agent.sh`
- `telemetry-skill.ps1`
- `telemetry-session.ps1`
- `telemetry-agent.ps1`

**Archivos a NO TOCAR** (hooks activos):
- `telemetry-skill.py` — Claude Code active hook, referenciado en `.claude/settings.json`
- `copilot-telemetry-skill.sh` — Copilot active hook, referenciado en `.github/hooks/hooks.json`
- Todos los demás `.py` (observe.py, prompt-injection-guard.py, auto-format.py, etc.)
- Todos los demás `copilot-*.sh` y `copilot-*.ps1`

**Cambios**:

1. **Eliminar** los 6 archivos listados de `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/`
2. **Eliminar** los 6 archivos listados de `.ai-engineering/scripts/hooks/` (dogfood)
3. **Eliminar** `scripts/hooks/` directorio top-level (fantasma de migración, solo `_lib/__pycache__/`)
4. **Actualizar** `test_template_parity.py` si verifica estos archivos
5. **Verificar** que `.claude/settings.json` no referencia ningún archivo eliminado

---

### Sub-spec C: Eliminar contexts/orgs (Wave 1)

**Objetivo**: Eliminar el stub muerto `contexts/orgs/` de templates, instalación, y código.

**Cambios**:

1. **Eliminar** `src/ai_engineering/templates/.ai-engineering/contexts/orgs/` (directorio completo)
2. **Eliminar** `.ai-engineering/contexts/orgs/` (dogfood)
3. **Actualizar** `src/ai_engineering/state/defaults.py` — eliminar regla ownership de `contexts/orgs/**`
4. **Actualizar** `tests/unit/test_state.py` — eliminar test de DENY para `contexts/orgs/`
5. **Actualizar** `.ai-engineering/README.md` — eliminar `orgs/` del árbol de directorios
6. **Decisión DEC-nuevo**: Documentar en decision-store.json: "contexts/orgs eliminado — stub aspiracional sin implementación. Si se necesita compartir convenciones org-wide, usar contexts/team/ o un paquete npm/pip compartido."

---

### Sub-spec D: Context Loading Enforcement + Language Cleanup (Wave 2, paralelo con E, después de A)

**Objetivo**: Fortalecer el mecanismo de carga de contextos añadiendo instrucciones explícitas en CLAUDE.md y un handler genérico de fallback. Eliminar lenguajes no soportados.

**Limitación reconocida**: El mecanismo sigue siendo instruction-based (el modelo lee y decide seguir la instrucción). No hay enforcement programático. Esto es una mejora significativa respecto a "sin instrucción alguna" pero no es una garantía.

#### D.1 — Eliminar ruby y elixir (no soportados)

Eliminar de TODOS los sitios:
1. **Eliminar** `contexts/languages/ruby.md` (template + dogfood)
2. **Eliminar** `contexts/languages/elixir.md` (template + dogfood)
3. **Eliminar** handlers `lang-ruby.md` y `lang-elixir.md` si existen en `.claude/skills/ai-review/handlers/` y mirrors
4. **Eliminar** cualquier referencia a ruby/elixir en skills, agents, README, tests

#### D.2 — Eliminar código muerto

5. **Eliminar** `contexts/languages/universal.md` y su template (0 referencias, 281 líneas muertas)

#### D.3 — Crear archivos faltantes

6. **Crear** `contexts/languages/cpp.md` y su template — contenido mínimo con estructura de secciones (Naming, Memory Management, Modern C++ Guidelines, Common Pitfalls) siguiendo el patrón de los context files existentes (~200 líneas). Si el contenido requiere más expertise, crear stub con TODOs marcados.

#### D.4 — Handler genérico reutilizable

7. **Crear** `lang-generic.md` en `.claude/skills/ai-review/handlers/` y mirrors
8. **Actualizar** `ai-review/handlers/review.md` para añadir instrucción de dispatch explícita:
   ```
   For each language detected in the diff:
   1. If a dedicated handler exists (lang-{language}.md), use it
   2. Otherwise, use lang-generic.md with the detected language
   ```
   El handler genérico: detecta extensiones de archivo → mapea a nombre de context file → lee `contexts/languages/{lang}.md` → aplica las reglas del context file al review.

#### D.5 — Enforcement en instrucciones raíz

9. **Actualizar CLAUDE.md** — añadir instrucción explícita de carga de contextos antes de escribir código. Actualizar skill count a 38 si no lo hizo Sub-spec A.
10. **Actualizar `copilot-instructions.md`** con la misma instrucción (Sub-spec A ya habrá limpiado las refs a framework-contract)
11. **Actualizar agent `ai-build.md`** — hacer el paso de carga de contextos más explícito con lista enumerada de los lenguajes disponibles:
    ```
    Available language contexts (14): bash, cpp, csharp, dart, go, java, javascript, kotlin, php, python, sql, swift, typescript
    Available framework contexts (15): android, api-design, aspnetcore, backend-patterns, bun, claude-api, deployment-patterns, django, flutter, ios, mcp-sdk, nextjs, nodejs, react, react-native
    ```

**Lenguajes finales después de cleanup**: bash, cpp, csharp, dart, go, java, javascript, kotlin, php, python, sql, swift, typescript = **13 lenguajes**

---

### Sub-spec E: Install Fixes — team/, specs/ (Wave 2, paralelo con D, después de A)

**Objetivo**: Que `ai-eng install` cree todas las carpetas necesarias con seed files.

**Cambios**:

1. **Actualizar** `src/ai_engineering/installer/phases/governance.py`:
   - Cambiar lógica de `_TEAM_OWNED` en método `_classify`: en modo `FRESH`, copiar los seed files de `contexts/team/` como templates iniciales. En modos `REPAIR`/`UPDATE`, mantener el skip actual (no sobrescribir)
   - Solo 2 seed files: `README.md` y `lessons.md`
   - **Nota**: Sub-spec A ya habrá modificado governance.py para project-identity.md. Esta modificación es en una sección diferente (`_classify` para team/ vs la lista de archivos para project-identity).
2. **Actualizar** templates de team/:
   - `src/ai_engineering/templates/.ai-engineering/contexts/team/README.md` — hacer genérico ("Add your team conventions here. Files in this directory are loaded by the AI build agent.")
   - `src/ai_engineering/templates/.ai-engineering/contexts/team/lessons.md` — mantener vacío con header (placeholder para `/ai-learn`)
   - **Eliminar** `cli.md` y `mcp-integrations.md` del template (contenido específico de ai-engineering)
3. **Crear** templates para `specs/`:
   - `src/ai_engineering/templates/.ai-engineering/specs/spec.md` (placeholder: "# No active spec\n\nRun /ai-brainstorm to start a new spec.")
   - `src/ai_engineering/templates/.ai-engineering/specs/plan.md` (placeholder: "# No active plan\n\nRun /ai-plan after spec approval.")
4. **Actualizar** GovernancePhase para crear `specs/` directory en modo FRESH
5. **Actualizar** tests de install para verificar que `contexts/team/` (2 files) y `specs/` (directory exists) se crean

---

### Sub-spec F: README.md Overhaul (Wave 3)

**Objetivo**: Reescribir `.ai-engineering/README.md` como guía post-install completa. En inglés.

**Estructura** (basada en investigación de patrones de Backstage, LangChain, Dagger, Nx):

1. **Header**: Nombre + versión + "This directory governs your AI workspace"
2. **Quick Start**: First workflow in 4 lines (`/ai-brainstorm` → `/ai-plan` → `/ai-dispatch` → `/ai-commit`)
3. **Skills (38)**: Table grouped by workflow (Design, Build, Deliver, Verify, Document, Sprint, Meta) — includes ai-project-identity
4. **Agents (9)**: Table with Role + "Activated by" (skills orchestrate them)
5. **Your project, your control**: 3 ownership blocks (YOURS / FRAMEWORK / AUTOMATIC) — critical for regulated industries
6. **Configuration — manifest.yml**: What fields to edit and their effect
7. **Contexts**: Hierarchy languages/ (13) → frameworks/ (15) → team/ + project-identity.md with customization example
8. **Common workflows**: New feature, bug fix, security audit, sprint review
9. **Multi-IDE**: Claude Code / GitHub Copilot / Codex — where skills live and how to invoke
10. **CLI quick reference**: 5-7 most used commands
11. **Troubleshooting**: 3-5 common problems with 1-line solutions

**Update BOTH**: template `src/ai_engineering/templates/.ai-engineering/README.md` AND `.ai-engineering/README.md` (dogfood).

---

## Decisions (APPROVED)

| ID | Decisión | Resolución |
|----|----------|------------|
| D1 | ¿Cómo crear/rellenar el documento? | **Skill dedicada `/ai-project-identity`** — auto-detect del proyecto + Q&A para lo que no puede inferir |
| D2 | ¿Dónde poner el documento? | **`contexts/project-identity.md`** — raíz de contexts, eliminar `product/` completamente |
| D3 | ¿Handlers para lenguajes sin handler? | **Handler genérico reutilizable** `lang-generic.md` como fallback — carga el context file del lenguaje detectado |
| D4 | ¿Nombre del documento? | **`project-identity.md`** |
| D5 | ¿Qué contiene? | **Esencia del proyecto**: qué es, servicios, dependencias, consumidores, boundaries. NO duplica manifest ni CLAUDE.md |
| D6 | ¿Dónde se carga? | **Centralizado en CLAUDE.md/copilot-instructions.md** + lectura explícita en brainstorm/plan handlers |
| D7 | ¿Seed files de team/? | **Solo `README.md` + `lessons.md`** — eliminar cli.md y mcp-integrations.md del template |
| D8 | ¿Validator instruction_consistency? | **Migrar pointer-count logic a counter_accuracy.py**, luego eliminar instruction_consistency.py |
| D9 | ¿ai-governance contra qué valida? | **project-identity.md** (boundaries negocio) + **CLAUDE.md + manifest** (reglas técnicas) |
| D10 | ¿README en qué idioma? | **Inglés** |
| D11 | ¿Nombre de la skill? | **`/ai-project-identity`** |
| D12 | ¿Eliminar ruby y elixir? | **Sí** — de todo el framework |

## Migration Path (existing installations)

Instalaciones existentes que ya tienen `contexts/product/`:
- `ai-eng update` NO elimina archivos existentes (solo crea/actualiza)
- Los archivos `framework-contract.md` y `product-contract.md` quedarán huérfanos
- **Fix**: Añadir paso de migración en `updater/service.py` que elimine `contexts/product/` en update si existe, y cree `project-identity.md` si no existe
- Alternativa: documentar en README que usuarios deben `rm -rf .ai-engineering/contexts/product/` tras update

## Out of Scope

- Reescritura de los archivos de contexto en sí (languages/*.md, frameworks/*.md) — excepto eliminar ruby/elixir/universal
- Cambios en la lógica de hooks activos (solo limpieza de muertos)
- Implementación de auto-detección de org desde git remote (fue un stub y se descarta)
- Cambios en el root README.md del repo (solo el `.ai-engineering/README.md`)
- Carga automática de `docs/solution-intent.md` — solo bajo demanda explícita del usuario
- Enforcement programático de carga de contextos (fuera de alcance, se mejora con instrucciones explícitas)

## Risks

| Risk | Mitigation |
|------|------------|
| Blast radius de Sub-spec A (~40+ archivos) | Instrucción centralizada en CLAUDE.md evita tocar 30+ SKILL.md. Reducido a ~15 archivos. |
| governance.py modificado por A y E | Orden secuencial obligatorio: A primero, E después. E debe ser consciente de cambios de A. |
| Instalaciones existentes con contexts/product/ | Paso de migración en updater o documentación en README. |
| Enforcement sigue siendo trust-based | Reconocido como limitación. Mejora significativa vs no tener instrucción. |
| cpp.md requiere contenido de calidad | Crear con estructura mínima siguiendo patrón existente. Stub con TODOs si necesita más expertise. |

## Acceptance Criteria

- [ ] `ai-eng install` en directorio vacío crea: `contexts/team/` (2 files), `contexts/project-identity.md`, `specs/` (directory)
- [ ] No existen `framework-contract.md` ni `product-contract.md` en templates ni dogfood
- [ ] No existe `contexts/product/` en templates ni dogfood
- [ ] No existe `contexts/orgs/` en templates ni dogfood
- [ ] No existen estos 6 archivos en hooks: `telemetry-skill.sh`, `telemetry-session.sh`, `telemetry-agent.sh`, `telemetry-skill.ps1`, `telemetry-session.ps1`, `telemetry-agent.ps1`
- [ ] `telemetry-skill.py` y `copilot-telemetry-skill.sh` siguen existiendo (hooks activos preservados)
- [ ] No existe `scripts/hooks/` directorio top-level
- [ ] No existen `ruby.md`, `elixir.md`, ni `universal.md` en contexts/languages
- [ ] `contexts/languages/cpp.md` existe con contenido (template + dogfood)
- [ ] Lenguajes finales: bash, cpp, csharp, dart, go, java, javascript, kotlin, php, python, sql, swift, typescript (13 total)
- [ ] Handler genérico `lang-generic.md` existe con dispatch routing en `review.md`
- [ ] `ai-review/handlers/review.md` contiene instrucción de fallback a lang-generic.md
- [ ] Skill `/ai-project-identity` existe y registrada en manifest con `total: 38`
- [ ] CLAUDE.md dice "Skills (38)" y contiene instrucción de carga de project-identity.md y contexts
- [ ] CLAUDE.md effort table: medium = 12 (includes ai-project-identity)
- [ ] copilot-instructions.md actualizado (instrucción de carga + fix path + sin ref a framework-contract)
- [ ] ai-governance valida contra project-identity.md + CLAUDE.md + manifest.yml
- [ ] `counter_accuracy.py` contiene lógica migrada de `instruction_consistency.py`
- [ ] `instruction_consistency.py` eliminado
- [ ] README.md (inglés) tiene 38 skills, 9 agents, 13 languages, getting started, manifest docs, workflows
- [ ] Todos los tests pasan (incluyendo tests actualizados para product→identity, orgs removal, team seed)
- [ ] `ai-eng doctor` pasa sin errores
