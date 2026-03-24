# SPEC: GitHub Copilot Subagent Orchestration — Full Parity with Claude Code

## Status: APPROVED

## Refs

- Official docs: https://code.visualstudio.com/docs/copilot/customization/custom-agents (Mar 2026)
- Inspiration: returngis.net — "Haz que tus custom agents sean subagents de GitHub Copilot" (Feb 2026)
- Decisions: DEC-022 (GitHub Agentic Workflows), DEC-023 (Autopilot invocation-as-approval)
- Manifest: `.ai-engineering/manifest.yml` → `providers.ides: [claude_code, github_copilot]`

---

## Problem Statement

ai-engineering tiene **paridad 100% en lógica** entre Claude Code y GitHub Copilot (9 agentes, 37 skills, hooks configurados). Sin embargo, los agentes de Copilot **no orquestan subagentes** porque:

1. **Ningún agente orquestador tiene el tool `agent`** en su frontmatter — requerido por Copilot para delegar a subagentes.
2. **Ningún agente orquestador declara la propiedad `agents`** — la lista explícita de subagentes permitidos que Copilot necesita para el routing.
3. **No hay `handoffs` configurados** — la funcionalidad nativa de Copilot para transiciones guiadas entre agentes (Plan → Build → Verify) no se aprovecha.
4. **Las instrucciones usan sintaxis genérica** (`Dispatch Agent(Build)`) sin referenciar el mecanismo nativo de delegación de Copilot.
5. **No hay documentación** sobre cómo usar subagentes en los 3 entornos (VS Code, CLI terminal, Coding Agent cloud).
6. **No se usa `hooks` per-agent** — Copilot soporta hooks scoped al agente (e.g., auto-format en Build) via `chat.useCustomAgentHooks`.

### Hallazgo clave de la documentación oficial

La propiedad `infer` está **DEPRECATED**. Las propiedades correctas son:

| Propiedad | Default | Propósito |
|-----------|---------|-----------|
| `user-invocable` | `true` | Visible en el picker de agentes |
| `disable-model-invocation` | `false` | Permite/bloquea invocación como subagente |
| `agents` | (none) | Lista explícita de subagentes permitidos |
| `handoffs` | (none) | Transiciones guiadas entre agentes |

La propiedad `isSticky` **NO EXISTE** en Copilot.

**Nota sobre defaults**: Los 9 agentes usan los valores por defecto de `user-invocable` (true) y `disable-model-invocation` (false). No se necesitan overrides porque todos los agentes deben ser: (a) visibles en el picker para invocación directa, y (b) invocables como subagentes por agentes orquestadores. La delegación se controla via la propiedad `agents` del orquestador (allowlist explícita), no bloqueando el subagente.

## Goal

Alcanzar **paridad funcional completa** con Claude Code en orquestación multi-agente, usando las APIs nativas de Copilot (`agents`, `handoffs`, `agent` tool, per-agent `hooks`), en los tres entornos: VS Code, Copilot CLI terminal, y Coding Agent (cloud).

## Non-Goals

- Modificar la lógica de los skills (ya son idénticos cross-platform)
- Cambiar agentes de Claude Code (`.claude/agents/`)
- Crear nuevos agentes (los 9 existentes cubren todos los roles)
- Implementar hooks globales de Claude en Copilot (scope de otro spec)
- Añadir `infer` (deprecated) — usar las propiedades modernas
- Modificar `AGENTS.md` o `CLAUDE.md` (root instruction files)
- Modificar `.agents/agents/` mirror (propiedades `agents`, `handoffs` y `hooks` son Copilot-específicas)

---

## Sync Architecture (Critical Context)

**El flujo de cambios es unidireccional**:

```
.claude/ (CANONICAL)
    │
    │  scripts/sync_command_mirrors.py
    │  + AGENT_METADATA dict (static mapping)
    │
    ├──▶ .agents/     (generic mirror — tools stripped, refs translated)
    ├──▶ .github/     (Copilot mirror — tools translated, skills flattened)
    └──▶ templates/   (install templates)
```

**Regla fundamental**: NUNCA editar mirrors directamente. Todos los cambios van a:
1. `.claude/` (para lógica de agentes/skills — body text, instrucciones)
2. `scripts/sync_command_mirrors.py` (para metadata platform-specific — `agents`, `handoffs`, `hooks`)

El sync script tiene:
- `AgentMeta` dataclass (line 63-72) — metadata per-agent
- `AGENT_METADATA` dict (line 76-236) — `copilot_tools`, `claude_tools` per agent
- `generate_copilot_agent()` (line 584-600) — genera frontmatter Copilot

**Las propiedades `agents`, `handoffs`, `hooks` son Copilot-only** — se inyectan SOLO en la generación de `.github/agents/` via el sync script.

---

## Requirements

### R1: Extender `AgentMeta` dataclass con propiedades Copilot subagent

**Archivo**: `scripts/sync_command_mirrors.py` (line 63-72)

Añadir campos opcionales a `AgentMeta`:

```python
@dataclass(frozen=True)
class AgentMeta:
    display_name: str
    description: str
    model: str
    color: str
    copilot_tools: tuple[str, ...]
    claude_tools: tuple[str, ...]
    # NEW: Copilot subagent orchestration
    copilot_agents: tuple[str, ...] = ()      # Allowed subagent names
    copilot_handoffs: tuple[dict, ...] = ()    # Handoff transitions
    copilot_hooks: dict | None = None          # Per-agent hooks
```

### R2: Actualizar `AGENT_METADATA` con datos de subagentes

**Archivo**: `scripts/sync_command_mirrors.py` (line 76-236)

Actualizar las entradas de los 5 agentes orquestadores:

| Agente | `copilot_agents` | `copilot_handoffs` | `copilot_hooks` |
|--------|-------------------|--------------------|-----------------| 
| `autopilot` | `('Build', 'Explorer', 'Verify', 'Plan', 'Guard')` | `[{label: "📋 Create PR", agent: "agent", ...}]` | None |
| `build` | `('Guard', 'Explorer')` | `[{label: "✅ Verify", agent: "Verify", ...}, {label: "🔍 Review", agent: "Review", ...}]` | `{PostToolUse: [{type: command, command: "ruff format --quiet"}]}` |
| `plan` | `('Explorer', 'Guard')` | `[{label: "▶ Dispatch", agent: "Autopilot", ...}]` | None |
| `review` | `('Explorer',)` | `[{label: "🔧 Fix Issues", agent: "Build", ...}]` | None |
| `verify` | `('Explorer',)` | None | None |

Los 4 agentes leaf (explore, guard, guide, simplify) mantienen defaults vacíos.

### R3: Actualizar `generate_copilot_agent()` para serializar nuevas propiedades

**Archivo**: `scripts/sync_command_mirrors.py` (line 584-600)

Modificar la función para:
1. Añadir `agent` al array de `tools` cuando `copilot_agents` no está vacío
2. Serializar `agents: [...]` en frontmatter cuando `copilot_agents` existe
3. Serializar `handoffs: [...]` en frontmatter cuando `copilot_handoffs` existe
4. Serializar `hooks: {...}` en frontmatter cuando `copilot_hooks` existe

Considerar migrar de frontmatter manual a usar `_serialize_frontmatter()` para mantener consistencia.

### R4: Actualizar body del autopilot CANONICAL con orquestación explícita

**Archivo**: `.claude/agents/ai-autopilot.md` (CANONICAL)

Añadir sección "Subagent Orchestration" al body:

```markdown
## Subagent Orchestration

You coordinate specialized agents for multi-phase delivery:

1. **Research**: Use the Explorer agent to gather codebase context
2. **Implement**: Use the Build agent for code changes (fresh context per sub-spec)
3. **Verify**: Use the Verify agent for anti-hallucination gates
4. **Govern**: Use the Guard agent for governance advisory (optional)
5. **Plan**: Use the Plan agent for sub-spec decomposition (optional)
```

El sync script traducirá los nombres automáticamente para cada plataforma.

### R5: Actualizar body del build CANONICAL con delegación

**Archivo**: `.claude/agents/ai-build.md` (CANONICAL)

Actualizar dos puntos:

1. **Step 2 (guard.advise)**: Cambiar a referencia de subagente
2. **Step 6 (Dispatch Pattern)**: Añadir Explorer como subagente consultable

### R6: Unificar sintaxis de delegación en CANONICAL

**Archivos**: `.claude/agents/ai-autopilot.md`, `.claude/agents/ai-build.md` (CANONICAL)

Reemplazar TODAS las referencias legacy `Dispatch Agent(X)` por la sintaxis "Use the X agent to..." en los archivos canónicos. El sync propagará el cambio a todos los mirrors.

### R7: Fix bug de path cruzado en autopilot CANONICAL

**Archivo**: `.claude/skills/ai-autopilot/SKILL.md` (CANONICAL)

Verificar y corregir cualquier referencia que cause el bug descubierto en la investigación (`.claude/` path en skill que debería usar path relativo a la plataforma). El sync script traduce paths automáticamente — el bug está en el CANONICAL si el sync lo genera mal, o en el sync script si no traduce correctamente.

### R8: Actualizar dispatch skill CANONICAL con nombres de agentes

**Archivo**: `.claude/skills/ai-dispatch/SKILL.md` (CANONICAL)

Actualizar las referencias genéricas de `Agent(Build)`, `Agent(Verify)`, etc. para usar nombres descriptivos que el sync pueda traducir correctamente.

### R9: Ejecutar sync y verificar mirrors

Después de todos los cambios en canonical + sync script:

```bash
python scripts/sync_command_mirrors.py --verbose
ai-eng sync --check  # Debe pasar (exit 0)
```

Verificar que los `.github/agents/*.agent.md` generados tienen:
- `agent` en tools (orquestadores)
- `agents: [...]` con nombres correctos
- `handoffs: [...]` donde aplique
- `hooks: {...}` en build

### R10: Documentación de subagentes

Crear `docs/copilot-subagents.md` con guía que incluya:
- Cómo funciona el sync (canonical → mirrors)
- Propiedades Copilot-specific inyectadas por el sync
- Patrones de orquestación por entorno (VS Code, CLI, Coding Agent)
- Matriz de capacidades
- Al menos 1 ejemplo por entorno

### R11: Actualizar copilot-instructions.md

Añadir sección "Subagent Orchestration" en `.github/copilot-instructions.md` documentando la capacidad de delegación.

### R12: Decisión en decision-store.json

Registrar como DEC-024:
- Title: "Copilot subagent orchestration via sync pipeline"
- Rationale: Propiedades Copilot-only (`agents`, `handoffs`, `hooks`) se inyectan via `AGENT_METADATA` en el sync script, manteniendo `.claude/` como canonical source sin contaminar con propiedades platform-specific
- Status: active
- Criticality: high

### R13: Actualizar mirror_sync validator si necesario

**Archivo**: `src/ai_engineering/validator/categories/mirror_sync.py`

Verificar que el parity validator (spec-006) NO flagee drift por las propiedades Copilot-only (`agents`, `handoffs`, `hooks`) que solo existen en `.github/agents/`. Si flagea, ajustar la lógica de comparación.

> **Nota sobre interacción de hooks**: Los per-agent hooks y los global hooks (`.github/hooks/hooks.json`) son pipelines independientes. El hook global `postToolUse` (telemetría) y el per-agent hook (auto-format) se ejecutan ambos sin bloquearse mutuamente.

> **Requisito VS Code**: Per-agent hooks requieren `chat.useCustomAgentHooks: true` en VS Code settings. Esto es **opcional** — la delegación de subagentes (R1-R3) funciona SIN este setting.

---

## Architecture

### Change Flow (Sync Pipeline)

```
┌──────────────────────────────────────────────────────┐
│  STEP 1: Edit canonical sources                       │
│                                                       │
│  .claude/agents/ai-autopilot.md   (body text)        │
│  .claude/agents/ai-build.md      (body text)         │
│  .claude/skills/ai-dispatch/     (skill logic)       │
│  .claude/skills/ai-autopilot/    (fix path bug)      │
│                                                       │
│  scripts/sync_command_mirrors.py  (AGENT_METADATA)   │
│    ├── AgentMeta: +copilot_agents, +copilot_handoffs │
│    ├── AGENT_METADATA: per-agent subagent config     │
│    └── generate_copilot_agent(): serialize new props  │
└───────────────────────┬──────────────────────────────┘
                        │
                        ▼  python scripts/sync_command_mirrors.py
┌──────────────────────────────────────────────────────┐
│  STEP 2: Auto-generated mirrors                       │
│                                                       │
│  .github/agents/autopilot.agent.md  ← agents, handoffs│
│  .github/agents/build.agent.md     ← agents, handoffs, hooks│
│  .github/agents/plan.agent.md      ← agents, handoffs│
│  .github/agents/review.agent.md    ← agents, handoffs│
│  .github/agents/verify.agent.md    ← agents          │
│  .github/prompts/ai-dispatch.prompt.md  ← updated refs│
│  .github/prompts/ai-autopilot.prompt.md ← fixed path │
│                                                       │
│  .agents/agents/ai-*.md            ← body only (no   │
│  .agents/skills/*/SKILL.md           Copilot props)   │
└───────────────────────┬──────────────────────────────┘
                        │
                        ▼  ai-eng sync --check
┌──────────────────────────────────────────────────────┐
│  STEP 3: Validation                                   │
│                                                       │
│  ✓ SHA-256 parity check (canonical vs mirrors)       │
│  ✓ Manifest coherence (37 skills, 9 agents)          │
│  ✓ Cross-reference validation (no broken paths)      │
│  ✓ CI gate: exit 0 = all mirrors in sync             │
└──────────────────────────────────────────────────────┘
```

### Delegation Model (3 entornos)

```
┌──────────────────────────────────────────────────────────┐
│                      VS Code Chat                         │
│                                                           │
│  User → @Autopilot (tools: [agent], agents: [Build,...]) │
│           ├── Build agent (implementation)                │
│           │     └── handoff → Verify                     │
│           ├── Verify agent (anti-hallucination gates)    │
│           ├── Explorer agent (codebase research)         │
│           └── Guard agent (governance advisory)          │
│                                                           │
│  Handoffs: Plan ──▶ Autopilot ──▶ PR                    │
│            Build ──▶ Verify / Review                     │
│            Review ──▶ Build (fix issues)                 │
│                                                           │
│  No special VS Code setting needed — works by default    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                   Copilot CLI Terminal                     │
│                                                           │
│  User → /ai-autopilot → task tool delegation              │
│           ├── task(agent_type: "build", ...)              │
│           ├── task(agent_type: "verify", ...)             │
│           └── task(agent_type: "explore", ...)            │
│                                                           │
│  Agents auto-registered from .github/agents/*.agent.md   │
│  Handoffs not applicable (CLI uses task tool directly)    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                Coding Agent (Cloud)                        │
│                                                           │
│  Issue → Coding Agent → repo .agent.md discovery          │
│           ├── Discovers agents from .github/agents/       │
│           ├── Uses agents property for delegation         │
│           └── Handoffs available for workflow transitions  │
│                                                           │
│  No config needed — agents discovered from repo           │
└──────────────────────────────────────────────────────────┘
```

### Orchestration Flow (Autopilot with subagents)

```
autopilot.agent.md
  tools: [agent, codebase, githubRepo, readFile, runCommands, search]
  agents: [Build, Explorer, Verify, Plan, Guard]
    │
    ├── Split Phase: decompose spec into sub-specs
    │
    ├── Explore Phase: delegate to Explorer agent (parallel)
    │     └── Explorer reads codebase, returns findings
    │
    ├── Execute Loop (per sub-spec):
    │     ├── Plan: read sub-spec + skill SKILL.md
    │     ├── Implement: delegate to Build agent (fresh context)
    │     │     └── Build.hooks.PostToolUse: auto-format via ruff
    │     ├── Verify: delegate to Verify agent (anti-hallucination)
    │     └── Commit: if verify passes, incremental commit
    │
    ├── Deliver: handoff → PR creation
    │
    └── Handoff buttons:
          └── [📋 Create PR] → default agent with PR prompt
```

### Handoff Chain (VS Code)

```
@Plan ──[▶ Dispatch Implementation]──▶ @Autopilot
                                          │
                        ┌─────────────────┼─────────────────┐
                        ▼                 ▼                 ▼
                   @Explorer          @Build            @Verify
                                        │
                              ┌─────────┼─────────┐
                              ▼                   ▼
                   [✅ Verify Changes]    [🔍 Review Changes]
                         │                      │
                         ▼                      ▼
                      @Verify              @Review
                                              │
                                    [🔧 Fix Issues]
                                              │
                                              ▼
                                           @Build
```

---

## Acceptance Criteria

### Sync Pipeline (R1-R3)
1. `AgentMeta` dataclass tiene campos `copilot_agents`, `copilot_handoffs`, `copilot_hooks`
2. `AGENT_METADATA` tiene subagent data para los 5 orquestadores (autopilot, build, plan, review, verify)
3. `generate_copilot_agent()` serializa `agents`, `handoffs`, `hooks` en frontmatter generado

### Generated Mirrors (R9 — verificado post-sync)
4. Los 5 `.github/agents/*.agent.md` generados tienen `agent` en `tools`
5. Los 5 `.github/agents/*.agent.md` generados tienen `agents: [...]` correctos
6. Los 4 con handoffs tienen `handoffs: [...]` (plan, autopilot, build, review)
7. `build.agent.md` generado tiene `hooks: {PostToolUse: ...}`
8. `ai-eng sync --check` pasa (exit 0) después de regenerar mirrors

### Canonical Body Changes (R4-R8)
9. `.claude/agents/ai-autopilot.md` tiene sección "Subagent Orchestration"
10. `.claude/agents/ai-build.md` referencia Guard y Explorer como subagentes
11. No coexisten `Dispatch Agent(X)` y "Use the X agent" en ningún archivo canonical
12. El bug de path `.claude/` en la skill autopilot está corregido en canonical

### Documentation & Governance (R10-R13)
13. `docs/copilot-subagents.md` existe con ≥1 ejemplo por entorno
14. `.github/copilot-instructions.md` tiene sección "Subagent Orchestration"
15. `decision-store.json` tiene DEC-024
16. Mirror sync validator no flagea drift por propiedades Copilot-only

### Negative Checks
17. Los 4 leaf agents (explore, guard, guide, simplify) NO tienen `agent` en tools, `agents`, `handoffs`, ni `hooks`
18. `.claude/agents/` no contiene propiedades Copilot-only (`agents`, `handoffs`, `hooks`)
19. `.agents/agents/` no contiene propiedades Copilot-only
20. Linters pasan: `ruff check src/ scripts/` y `gitleaks detect`

---

## Rollback Plan

Si la delegación de subagentes causa mis-routing (agentes incorrectos reciben tareas):

1. Revertir los cambios de frontmatter (git revert del commit)
2. Los agentes siguen funcionando como invocación directa sin delegación
3. Los handoffs desaparecen — no hay side effects
4. Los per-agent hooks se desactivan al revertir

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Copilot CLI no soporta `agents` property | Media | Bajo | CLI usa `task` tool directamente; `agents` es solo para VS Code routing |
| Handoffs no soportados en Coding Agent | Baja | Bajo | Fail-open: agentes siguen delegando via `agents` property |
| `chat.useCustomAgentHooks` deshabilitado por defecto | Alta | Bajo | Documentar en guide; hooks son enhancement, no requisito |
| Agente incorrecto recibe delegación | Baja | Medio | `agents` property es allowlist explícita — limita routing |
| Coding Agent ignora per-agent hooks | Alta | Bajo | Hooks son VS Code-only enhancement; no bloquea funcionalidad core |
| Parity validator (spec-006) flag drift en `.agents/` mirror | Media | Bajo | Si el validator flagea drift por `agents`/`handoffs`/`hooks` (propiedades Copilot-specific), ajustar la lógica de comparación del validator para ignorar estas propiedades. Esto es un fix menor, no un spec separado |

---

## Out of Scope

- Hooks globales de seguridad (prompt-injection-guard para Copilot)
- Cost tracking para Copilot
- Instinct extraction para Copilot
- Nuevos agentes o skills
- Editar `.github/agents/` o `.github/prompts/` directamente (son mirrors auto-generados)
- Editar `.agents/agents/` directamente (es mirror auto-generado)
- Añadir propiedades Copilot-only a `.claude/` canonical (se inyectan via sync script)
- Cambios en `AGENTS.md` o `CLAUDE.md` (root instruction files)
- Cambios en `manifest.yml` (agent count y names no cambian)
- Crear `.vscode/settings.json` (subagentes funcionan por defecto)
