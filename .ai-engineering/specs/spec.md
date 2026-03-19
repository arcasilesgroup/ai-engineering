# Spec-055: Rediseño Radical de ai-engineering

## Context

ai-engineering ha crecido orgánicamente hasta 37 skills, 8 agents, 65 standards, 76K+ líneas de instrucciones para 24K líneas de Python. Ratio instrucciones:código = 3:1. El framework debe ser 1000% funcional, eficiente, efectivo y optimizado para la AI actual.

Rediseño basado en 4 repos de referencia:
- **Superpowers** (Jesse Vincent): 15 skills de disciplina de workflow, brainstorming con hard-gate, TDD para skills
- **review-code** (Phil Haack): handler-as-workflow, 8 agents paralelos, self-challenge protocol, continuous improvement
- **dotfiles/ai** (Phil Haack): 12 skills + 10 agents, agent selection matrix, filesystem-based state
- **autoresearch** (Karpathy): radical simplicity, git-as-state-machine, immutable metrics

Naming: Prefijo `/ai-` obligatorio en todos los skills y agents (marca de ai-engineering).

---

## Principios de Rediseño

### De Superpowers
1. **Hard-gate brainstorming**: NO implementación hasta diseño aprobado
2. **Skills auto-triggered**: si aplica, DEBES usarlo — no negociable
3. **TDD para skills**: test de presión con subagents antes de publicar
4. **CSO (Claude Search Optimization)**: description = triggering conditions
5. **Spec review loop**: dispatch reviewer subagent, max 3 iteraciones
6. **"Every project goes through this"**: no atajos

### De review-code
7. **Handler-as-workflow**: SKILL.md = router, handlers/ = workflows
8. **Agents paralelos especializados**: contexto fresco por agent
9. **Self-challenge protocol**: argumentar CONTRA propios findings
10. **Continuous improvement**: learn → analyze outcomes → feed back
11. **Bash para heavy-lifting**: scripts para parsing, AI para razonamiento

### De dotfiles/ai
12. **Agent selection matrix**: tabla "task → agent → invoke" en CLAUDE.md
13. **Implementation flow**: test-first → simplify → review
14. **Filesystem-based state**: planes y notas en archivos
15. **Full SDLC coverage**: standup, sprint, postmortem, support, ops

### De autoresearch
16. **"Program the researcher"**: meta-instrucciones como artefacto principal
17. **Fixed evaluation con métricas inmutables**: gates no se bypassean
18. **Simplicity criterion**: simpler is better

### Del usuario (Workflow Orchestration)
19. **Plan mode default**: para tarea no-trivial (3+ pasos)
20. **Subagent strategy**: offload research, one task per subagent
21. **Self-improvement loop**: corrección → update lessons.md
22. **Verification before done**: probar que funciona antes de declarar completo
23. **Demand elegance**: "is there a more elegant way?"
24. **Autonomous bug fixing**: diagnosticar y resolver sin hand-holding
25. **Prompt optimization internal**: mejorar prompts antes de ejecutar

---

## Skills: 37 → ~28

### CORE WORKFLOW (7 — de Superpowers)

| # | Skill | Qué hace |
|---|-------|----------|
| 1 | **/ai-brainstorm** | Design interrogation. Hard-gate. ONE question at a time. Challenge assumptions. Spec review loop con subagent. Explore edge cases. Push back. |
| 2 | **/ai-plan** | Implementation planning. Bite-sized tasks (2-5 min). Agent assignments. Phase ordering. Gate criteria. |
| 3 | **/ai-dispatch** | Execution. Subagent per task. Two-stage review (spec compliance + code quality). Progress tracking. |
| 4 | **/ai-test** | TDD enforcement. RED-GREEN-REFACTOR. Write failing test → implement minimal → refactor. Anti-patterns doc. |
| 5 | **/ai-debug** | Systematic debugging. Symptom Analysis → Reproduction → Root Cause (5 Whys) → Solution Design. NEVER symptom fixes. |
| 6 | **/ai-verify** | Evidence before claims. Run → read → verify. Forbidden: "should", "probably", "done!". Quality + security scanning (7 modes en paralelo). |
| 7 | **/ai-review** | Parallel specialized agents. Self-challenge. Confidence scoring. Cross-agent corroboration. Handler-based (find/review/learn). |

### DELIVERY (4 — simplificados)

| # | Skill | Qué hace |
|---|-------|----------|
| 8 | **/ai-commit** | Stage + lint + secret-scan + commit + push. Gitleaks pre-commit. |
| 9 | **/ai-pr** | Commit pipeline + create PR. Auto-complete squash merge. |
| 10 | **/ai-release** | GO/NO-GO gate. Aggregate quality dimensions. |
| 11 | **/ai-cleanup** | Repo hygiene: branch cleanup, migration to default branch. |

### ENTERPRISE/COMPLIANCE (4 — para banca/finanzas/salud)

| # | Skill | Qué hace |
|---|-------|----------|
| 12 | **/ai-security** | SAST, dependency audit, SBOM. Compliance regulatoria. |
| 13 | **/ai-governance** | Compliance validation. Absorbe integrity. Modos: compliance, ownership, risk. |
| 14 | **/ai-pipeline** | CI/CD generation. Handlers: generate/evolve/validate. |
| 15 | **/ai-schema** | Database engineering, migrations, query optimization. |

### TEACHING + WRITING (3)

| # | Skill | Qué hace |
|---|-------|----------|
| 16 | **/ai-explain** | Engineer-grade technical explanations. Code, concepts, patterns, architecture. 3-tier depth. ASCII diagrams. Execution traces. |
| 17 | **/ai-guide** | Project onboarding, architecture tours, decision archaeology. How-to guides. Para entrar en proyecto nuevo. |
| 18 | **/ai-write** | Comprehensive writing: docs, README, changelog, pitch, sprint-review, presentation, article, architecture board, solution intent, wiki, post, etc. Handlers por tipo de contenido. |

### SDLC (de dotfiles — generalizados) (6)

| # | Skill | Inspirado en | Qué hace |
|---|-------|-------------|----------|
| 19 | **/ai-note** | dotfiles note | Knowledge management. Discovery notes, technical findings. Filesystem-based. |
| 20 | **/ai-standup** | dotfiles standup | Generate standup notes from PR/commit activity. |
| 21 | **/ai-sprint** | dotfiles sprint-planning | Sprint planning, retro, goals. Compare planned vs shipped. |
| 22 | **/ai-postmortem** | dotfiles postmortem | Incident postmortem. DERP model (Detection, Escalation, Recovery, Prevention). |
| 23 | **/ai-support** | dotfiles support | Customer support investigation. Ticket tracking, note organization. |
| 24 | **/ai-resolve-conflicts** | dotfiles resolve-conflicts | Git conflict resolution. Handles rebase, merge, cherry-pick. Lock file regeneration. |

### META (4)

| # | Skill | Qué hace |
|---|-------|----------|
| 25 | **/ai-create** | Create skills and agents: `/ai-create skill my-skill` o `/ai-create agent my-agent`. TDD for skills (Superpowers writing-skills pattern): write pressure test → run WITHOUT skill → write skill → run WITH skill → iterate until bulletproof. CSO-optimized descriptions. |
| 26 | **/ai-learn** | Continuous improvement. Analyze outcomes → feed back to skills/agents. Update lessons.md. Cross-reference AI findings with what was actually changed post-PR (review-code learn pattern). |
| 27 | **/ai-prompt** | Prompt optimizer/creator. Se ejecuta automáticamente SOLO en skills clave (brainstorm, plan, write, explain). También invocable manualmente: `/ai-prompt 'mi texto'`. Cialdini principles. CSO optimization. No en CADA interacción — solo donde el prompt quality tiene alto impacto. |
| 28 | **/ai-onboard** | Framework bootstrap + enforcement. Se ejecuta al inicio de cada sesión (via SessionStart hook). **Qué hace exactamente**: (1) Detecta qué skills están disponibles en el proyecto, (2) Lee el contexto activo (spec, tasks, lessons), (3) Enforce la regla: "Si un skill aplica a tu tarea, DEBES usarlo — no es negociable", (4) Muestra red flags table con 12 patrones de racionalización que los agentes usan para saltarse skills (como Superpowers' using-superpowers). Ejemplo: si detecta que el usuario pide implementar algo → force brainstorm primero. Si detecta un bug → force systematic-debugging. Es el "policía del workflow". |

---

## Agents: 8

| # | Agent | Rol | Model |
|---|-------|-----|-------|
| 1 | **ai-plan** | Relentless interrogator (@LLMJunky). Extraer cada detalle y blind spot. ONE question at a time. Challenge vague language. Solo planifica, NUNCA implementa. | opus |
| 2 | **ai-build** | Implementation coordinator. Test-first. Subagent per task. Two-stage review. | opus |
| 3 | **ai-verify** | Quality + security scanning. Dispatch specialized reviewers in parallel. Self-challenge. Confidence scoring. | opus |
| 4 | **ai-guard** | Governance advisory for regulated industries. Compliance, risk, ownership. Always advisory, never blocks. | sonnet |
| 5 | **ai-review** | Specialized code review. **8** parallel focus areas: security, performance, correctness, maintainability, testing, compatibility, architecture, **frontend**. Cross-agent corroboration. Siempre ejecuta /ai-explore ANTES del review para architectural context gathering (como review-code's context-explorer). | opus |
| 6 | **ai-explore** | Deep codebase research. Architecture mapping. Context gathering. Read-only. También se ejecuta pre-review. | sonnet |
| 7 | **ai-guide** | Project onboarding, architecture tours, decision archaeology. Teaching. Explain complex code to newcomers. | sonnet |
| 8 | **ai-simplify** | Code simplification + refactoring. Guard clauses, extract methods, flatten nesting, remove dead code. Refactor internals sin cambiar API externa. Runs post-build or on-demand. | sonnet |

---

## Standards: 65 → `.ai-engineering/contexts/` (estructura de review-code)

### Estructura jerárquica de contexts (de review-code + dotfiles)

```
.ai-engineering/contexts/
├── languages/                   # Stack-specific conventions (de review-code)
│   ├── python.md                # Merge best of review-code (164 lín) + dotfiles (82 lín)
│   ├── typescript.md            # De review-code (200 lín)
│   ├── javascript.md            # De review-code (423 lín)
│   ├── rust.md                  # Merge review-code (205 lín) + dotfiles (82 lín)
│   ├── go.md                    # De review-code (230 lín)
│   ├── java.md                  # De review-code (264 lín)
│   ├── kotlin.md                # De review-code (381 lín)
│   ├── csharp.md                # De review-code (188 lín)
│   ├── swift.md                 # De review-code (352 lín)
│   ├── dart.md                  # De review-code (458 lín)
│   ├── ruby.md                  # De review-code (249 lín)
│   ├── php.md                   # De review-code (384 lín)
│   ├── elixir.md                # De review-code (285 lín)
│   ├── bash.md                  # De review-code (445 lín)
│   └── sql.md                   # De review-code (152 lín)
├── frameworks/                  # Framework-specific (de review-code)
│   ├── django.md                # 240 lín
│   ├── react.md                 # 231 lín (incluye WCAG 2.1 AA accessibility)
│   ├── nodejs.md                # 545 lín
│   ├── aspnetcore.md            # 513 lín
│   ├── flutter.md               # 753 lín
│   ├── android.md               # 587 lín
│   ├── ios.md                   # 574 lín
│   ├── react-native.md          # 552 lín
│   └── kea.md                   # 136 lín (PostHog — evaluar si mantener o generalizar)
├── orgs/                        # Organization-wide (de review-code orgs/ pattern)
│   └── {org-name}/              # Se usa el nombre de la org de GitHub/AzDO
│       ├── org.md               # Convenciones org-wide (infra, security, UI patterns)
│       └── repos/
│           └── {repo-name}.md   # Convenciones repo-specific
└── team/                        # Team-specific customizations (propiedad del equipo)
    ├── payments-api.md           # "En pagos, siempre usar X pattern"
    └── mobile-app.md             # "En la app, preferimos Y approach"
```

### Cómo funciona la carga de contexts (auto-detección)

Basado en review-code's `code-language-detect.sh` + `load-review-context.sh`:

1. **Detección automática**: Script analiza el diff/archivos para detectar languages y frameworks
   - `.py` → python, `import django` → django
   - `.ts/.tsx` → typescript, `import.*react` → react
   - `.rs` → rust, `use actix_web` → actix
2. **Carga jerárquica**: language → framework → org → repo → team
   - Cada nivel añade especificidad sin duplicar
3. **Inyección en context**: Se pasa a los agents como contexto adicional
4. **Org/repo auto-detectados**: Del git remote URL

### Python context = merge de review-code + dotfiles

El context de Python para ai-engineering será el merge de ambos repos:
- Base: review-code's python.md (164 lín — más completo)
- Añadir de dotfiles: bulk ops & signals caveat, FK auto-indexing, `time.monotonic()`, quality checklist (ruff, pytest)
- **Crítico**: ai-engineering está basado en Python — este context debe ser el primero en estar perfecto

### Qué pasa con los 65 archivos de standards/

- Stack guidelines → `contexts/languages/` y `contexts/frameworks/`
- Quality rules → manifest.yml (quality gates)
- CICD rules → ai-pipeline skill
- Security rules → ai-security skill
- Review rules → ai-review skill
- Cross-cutting → absorber en skills o eliminar si ruff/pytest ya enforce

---

## User Flow Completo: Download → Production

### Paso 1: Instalación

```bash
pip install ai-engineering    # o: uv add ai-engineering
cd my-project/
ai-eng install
```

`ai-eng install` pregunta interactivamente:

```
🔧 ai-engineering setup

VCS provider?
  [x] GitHub
  [ ] Azure DevOps

IDE / AI assistant?
  [x] Claude Code
  [x] GitHub Copilot
  [ ] Cursor
  [ ] Codex
  [ ] Gemini CLI

Tech stacks? (select all that apply)
  [x] Python
  [ ] TypeScript
  [x] Rust
  [ ] .NET
  [ ] Go
  [ ] Java/Kotlin

Features?
  [x] Git hooks (pre-commit, commit-msg, pre-push)
  [x] Security scanning (gitleaks, semgrep)
  [x] Quality gates (ruff, pytest)
  [ ] CI/CD pipeline generation
  [ ] Sprint/standup/postmortem skills
  [ ] Support ticket management
```

**Resultado de install**:

```
my-project/
├── CLAUDE.md                    # Si Claude Code seleccionado
├── AGENTS.md                    # Si Copilot/Codex/Gemini seleccionado
├── .claude/                     # Si Claude Code
│   ├── skills/ai-*/SKILL.md     # Skills seleccionados
│   ├── agents/ai-*.md           # Agents
│   └── settings.json            # Permissions + hooks
├── .github/                     # Si Copilot (AUTO-GENERADO desde .claude/)
│   ├── prompts/ai-*.prompt.md
│   ├── agents/*.agent.md
│   └── copilot-instructions.md
├── .agents/                     # Si Codex/Gemini (AUTO-GENERADO desde .claude/)
│   ├── skills/*/SKILL.md
│   └── agents/ai-*.md
├── .ai-engineering/
│   ├── manifest.yml             # Config + skill registry + ownership + gates
│   ├── contexts/                # Stack guidelines (solo los stacks seleccionados)
│   │   ├── python.md
│   │   ├── rust.md
│   │   └── team/               # Vacío, para customizaciones del equipo
│   └── state/
│       ├── decision-store.json  # Compliance
│       └── audit-log.ndjson     # Compliance
├── scripts/hooks/               # Git hooks
├── .gitleaks.toml               # Si security scanning seleccionado
├── .semgrep.yml                 # Si security scanning seleccionado
└── tasks/
    ├── todo.md                  # Task tracking
    └── lessons.md               # Self-improvement
```

### Paso 2: Primera sesión — Onboarding

El usuario abre su IDE con AI assistant. El AI lee CLAUDE.md:

```
AI: Veo que ai-engineering está instalado. Antes de empezar:
    1. ¿Es tu primera vez con este proyecto?
       → /ai-guide para un tour de la arquitectura
    2. ¿Ya conoces el proyecto y quieres trabajar?
       → Describe lo que necesitas y empezamos con /ai-brainstorm
```

### Paso 3: Discovery — Entender el proyecto

```
User: Necesito entender cómo funciona el sistema de pagos

AI invoca: /ai-guide
→ Explorer agent mapea la arquitectura
→ Guide agent hace un tour interactivo:
  - "El sistema de pagos tiene 3 componentes principales..."
  - "Las transacciones fluyen por este pipeline..."
  - "Los tests se ejecutan con..."
→ Si el usuario tiene preguntas específicas:
  /ai-explain "explica cómo funciona el retry en el payment gateway"
```

### Paso 4: Brainstorm — Diseñar la solución

```
User: Quiero añadir soporte para pagos en crypto

AI invoca: /ai-brainstorm (auto-triggered por ser tarea no-trivial)

Step 1: EXPLORE - Lee el código actual del payment system
Step 2: ASK - Una pregunta a la vez:
  Q1: "¿Qué criptomonedas necesitan soporte? (BTC, ETH, USDT, todas?)"
  Q2: "¿Qué exchange/gateway para settlements? (Coinbase Commerce, BitPay, custom?)"
  Q3: "¿Los montos se muestran en crypto o se convierten a fiat?"
  Q4: "¿Hay requisitos regulatorios específicos? (KYC/AML para crypto)"
  Q5: "¿Qué pasa si el precio de la crypto cambia entre orden y settlement?"
  ... challenge assumptions, explore edge cases, push back ...

Step 3: PROPOSE 2-3 approaches con trade-offs
Step 4: WRITE spec to docs/specs/YYYY-MM-DD-crypto-payments-design.md
Step 5: DISPATCH spec-reviewer subagent → fix → re-dispatch
Step 6: USER reviews spec

HARD GATE: No se escribe código hasta que el spec esté aprobado.
```

### Paso 5: Plan — Crear plan de implementación

```
AI invoca: /ai-plan (after brainstorm approved)

→ Creates implementation plan:
  Phase 1: Crypto gateway adapter (3 tasks)
    - Task 1.1: Define CryptoGateway interface [2 min]
    - Task 1.2: Implement CoinbaseAdapter [5 min]
    - Task 1.3: Write integration tests [3 min]
  Phase 2: Payment flow integration (4 tasks)
    ...
  Phase 3: Settlement reconciliation (3 tasks)
    ...

→ Agent assignments:
  - build agent: all implementation tasks
  - verify agent: after each phase
  - guard agent: compliance check (crypto regulations)

→ User approves plan
```

### Paso 6: Execute — Implementar

```
AI invoca: /ai-dispatch (after plan approved)

→ Para cada task:
  1. Dispatch subagent (build agent)
  2. Subagent usa /ai-test (TDD): write failing test → implement → refactor
  3. /ai-verify: evidence that it works
  4. Two-stage review:
     a. Spec compliance: ¿hace lo que dice el plan?
     b. Code quality: ¿está bien escrito?
  5. Commit task con /ai-commit

→ Si algo falla:
  - /ai-debug para root cause analysis
  - Si se complica: STOP, re-plan

→ Progress tracked en tasks/todo.md
→ Lessons captured en tasks/lessons.md
```

### Paso 7: Review — Revisión de código

```
AI invoca: /ai-review (after implementation)

→ Dispatch 7 agents en paralelo:
  - Security agent: ¿vulnerabilidades en crypto handling?
  - Performance agent: ¿N+1 queries en settlements?
  - Correctness agent: ¿maneja edge cases de precio?
  - Maintainability agent: ¿código legible?
  - Testing agent: ¿coverage suficiente?
  - Compatibility agent: ¿rompe algo existente?
  - Architecture agent: ¿encaja en el diseño?

→ Self-challenge: cada agent argumenta CONTRA sus findings
→ Cross-agent corroboration: findings de 2+ agents = high confidence
→ User reviews findings, approves or requests changes
```

### Paso 8: Ship — Entregar

```
AI invoca: /ai-pr

→ /ai-commit pipeline (lint, secrets, tests)
→ Create PR con summary auto-generated
→ /ai-release checks:
  - Coverage ≥80% ✓
  - Zero medium+ security findings ✓
  - Zero secret leaks ✓
  - Tests green ✓
  → GO/NO-GO: GO ✓
```

### Paso 9: Learn — Mejora continua

```
After PR merged:

AI invoca: /ai-learn

→ Analiza outcomes:
  - ¿Los reviewers humanos encontraron algo que la AI no?
  - ¿Hubo false positives en la review?
  - ¿El plan estimó correctamente?
→ Updates lessons.md con patterns
→ Feeds back a skills/agents para mejorar
```

---

## Eliminaciones

### Se eliminan COMPLETAMENTE

| Categoría | Qué | Razón |
|-----------|-----|-------|
| Standards | 65 archivos | Reemplazados por contexts/ + tool configs + skill protocols |
| Contracts | product-contract.md, framework-contract.md | Absorbidos por CLAUDE.md + manifest.yml |
| State files | ownership-map, install-manifest, health-history, session-checkpoint | ownership → manifest, install → manifest, health → audit-log, checkpoint → no se usa |
| Skills redundantes | ai-refactor, ai-simplify, ai-code, ai-integrity, ai-architecture, ai-performance, ai-accessibility, ai-api, ai-infra, ai-ops, ai-contract, ai-dashboard, ai-evolve, ai-explore-skill, ai-guide-skill, ai-gap, ai-migrate, ai-triage, ai-document | Absorbidos en nuevos skills o convertidos en agent capabilities |
| Template copies | .agents/, .github/prompts/ en templates | Auto-generados durante install |
| Runbooks | Si no se usan | Evaluar con datos |

### Skills anteriores → dónde va la capacidad

| Skill eliminado | Nueva ubicación |
|----------------|-----------------|
| ai-code | ai-dispatch (build agent ejecuta código) |
| ai-refactor | ai-simplify agent (simplification + refactoring) |
| ai-simplify | ai-simplifier agent |
| ai-integrity | ai-governance modo integrity |
| ai-architecture | ai-brainstorm (architecture decisions) |
| ai-performance | ai-review (performance agent) |
| ai-accessibility | ai-review (frontend agent) |
| ai-api | ai-brainstorm (API design) |
| ai-infra | ai-dispatch modo infra |
| ai-ops | ai-debug modo ops |
| ai-contract | ai-governance |
| ai-dashboard | `ai-eng observe` CLI command |
| ai-evolve | ai-learn |
| ai-explore (skill) | ai-explorer agent (direct dispatch) |
| ai-gap | ai-verify |
| ai-migrate | ai-dispatch modo migrate |
| ai-triage | `ai-eng triage` CLI command |
| ai-document | ai-write |

---

## Estructura de Templates e Instalación

### Canonical source: `.claude/` (repo root de ai-engineering)

```
.claude/
├── skills/ai-*/SKILL.md     # 28 skills (source of truth)
├── agents/ai-*.md            # 8 agents (source of truth)
└── settings.json
```

### Templates: `src/ai_engineering/templates/`

```
templates/
├── project/
│   ├── .claude/              # SINGLE copy (from canonical)
│   │   ├── skills/           # All 28 skills
│   │   └── agents/           # All 8 agents
│   ├── CLAUDE.md
│   ├── AGENTS.md
│   ├── scripts/hooks/
│   ├── .gitleaks.toml
│   ├── .semgrep.yml
│   └── tasks/
│       ├── todo.md
│       └── lessons.md
├── contexts/                 # Stack-specific context files
│   ├── python.md
│   ├── typescript.md
│   ├── dotnet.md
│   └── rust.md
├── pipeline/                 # CI/CD templates
│   ├── github/
│   └── azure/
└── .ai-engineering/          # Governance scaffold (sin skills/agents)
    ├── manifest.yml
    ├── contexts/
    │   └── team/             # Empty placeholder for team customizations
    └── state/
        ├── decision-store.json
        └── audit-log.ndjson
```

### Install flow (mejorado con patrones de dotfiles + review-code)

```python
# Pseudo-code del install mejorado

def install(target_dir, options):
    # 1. Interactive prompts (si no se pasan options)
    vcs = prompt_choice("VCS?", ["github", "azure_devops"])
    ides = prompt_multi("IDE/AI?", ["claude_code", "github_copilot", "cursor", "codex", "gemini"])
    stacks = prompt_multi("Stacks?", ["python", "typescript", "rust", "dotnet", "go"])
    features = prompt_multi("Features?", ["hooks", "security", "quality", "cicd", "sdlc"])

    # 2. Copy governance scaffold
    copy_tree("templates/.ai-engineering/", target / ".ai-engineering/")

    # 3. Copy .claude/ (always — canonical format)
    if "claude_code" in ides:
        copy_tree("templates/project/.claude/", target / ".claude/")
        copy_file("templates/project/CLAUDE.md", target / "CLAUDE.md")

    # 4. GENERATE other IDE mirrors on-the-fly (not from pre-built copies)
    if "github_copilot" in ides:
        generate_copilot_mirrors(target / ".claude/", target / ".github/")
        copy_file("templates/project/AGENTS.md", target / "AGENTS.md")

    if any(ide in ides for ide in ["codex", "gemini", "cursor"]):
        generate_generic_mirrors(target / ".claude/", target / ".agents/")
        copy_file("templates/project/AGENTS.md", target / "AGENTS.md")

    # 5. Copy stack contexts (only selected stacks)
    for stack in stacks:
        copy_file(f"templates/contexts/{stack}.md", target / f".ai-engineering/contexts/{stack}.md")

    # 6. Copy features
    if "hooks" in features:
        copy_tree("templates/project/scripts/hooks/", target / "scripts/hooks/")
        install_git_hooks(target)

    if "security" in features:
        copy_file("templates/project/.gitleaks.toml", target / ".gitleaks.toml")
        copy_file("templates/project/.semgrep.yml", target / ".semgrep.yml")

    # 7. Copy task management
    copy_tree("templates/project/tasks/", target / "tasks/")

    # 8. Generate manifest with selections
    generate_manifest(target, vcs=vcs, ides=ides, stacks=stacks, features=features)

    # 9. Validate tooling
    validate_tools(stacks)  # ruff for python, etc.

    # 10. Report
    print_summary(installed_skills, installed_agents, ides, stacks)
```

### Sync flow (dev repo only)

```
# In ai-engineering repo (development):
ai-eng sync

# Reads: .claude/skills/ + .claude/agents/ (canonical)
# Generates: .agents/, .github/, templates/project/.claude/
# Validates: manifest counts match
```

---

## Manifest simplificado (~80 líneas)

```yaml
name: ai-engineering
version: "1.0.0"

providers:
  vcs: github
  ides: [claude_code, github_copilot]
  stacks: [python, rust]

skills:
  total: 28
  prefix: "ai-"
  registry:
    ai-brainstorm: {type: workflow, tags: [planning]}
    ai-plan: {type: workflow, tags: [planning]}
    ai-dispatch: {type: workflow, tags: [execution]}
    ai-test: {type: workflow, tags: [quality]}
    ai-debug: {type: workflow, tags: [quality]}
    ai-verify: {type: workflow, tags: [quality]}
    ai-review: {type: workflow, tags: [quality]}
    ai-commit: {type: delivery, tags: [git]}
    ai-pr: {type: delivery, tags: [git]}
    ai-release: {type: delivery, tags: [release]}
    ai-cleanup: {type: delivery, tags: [git]}
    ai-security: {type: enterprise, tags: [security]}
    ai-governance: {type: enterprise, tags: [compliance]}
    ai-pipeline: {type: enterprise, tags: [cicd]}
    ai-schema: {type: enterprise, tags: [database]}
    ai-explain: {type: teaching, tags: [learning]}
    ai-guide: {type: teaching, tags: [onboarding]}
    ai-write: {type: writing, tags: [docs]}
    ai-note: {type: sdlc, tags: [knowledge]}
    ai-standup: {type: sdlc, tags: [reporting]}
    ai-sprint: {type: sdlc, tags: [planning]}
    ai-postmortem: {type: sdlc, tags: [incident]}
    ai-support: {type: sdlc, tags: [customer]}
    ai-resolve-conflicts: {type: sdlc, tags: [git]}
    ai-create: {type: meta, tags: [framework]}
    ai-learn: {type: meta, tags: [improvement]}
    ai-prompt: {type: meta, tags: [optimization]}
    ai-onboard: {type: meta, tags: [bootstrap]}

agents:
  total: 8
  names: [plan, build, verify, guard, review, explore, guide, simplify]

quality:
  coverage: 80
  duplication: 3
  cyclomatic: 10
  cognitive: 15

ownership:
  framework: [".claude/skills/**", ".claude/agents/**", ".ai-engineering/**"]
  team: [".ai-engineering/contexts/team/**", "tasks/**"]
  system: [".ai-engineering/state/**"]

tooling: [uv, ruff, gitleaks, pytest, ty, pip-audit]
```

---

## Fases de Implementación

### Fase 1: Spec + Branch
- Branch: `spec/055-radical-simplification`
- Scaffold spec files, commit Phase 0

### Fase 2: Escribir 28 skills
- 7 core workflow (brainstorm, plan, dispatch, test, debug, verify, review)
- 4 delivery (commit, pr, release, cleanup)
- 4 enterprise (security, governance, pipeline, schema)
- 3 teaching+writing (explain, guide, write)
- 6 SDLC (note, standup, sprint, postmortem, support, resolve-conflicts)
- 4 meta (lifecycle, learn, prompt, onboard)
- Handler pattern donde aplique (brainstorm, review, pipeline, governance, write)
- CSO-optimized descriptions

### Fase 3: Escribir 8 agents
- Con self-challenge protocol (de review-code)
- Con agent selection matrix (de dotfiles)
- Specialization clara

### Fase 4: Nuevo CLAUDE.md + AGENTS.md
- CLAUDE.md ~120 líneas (workflow orchestration + agent matrix + gates)
- AGENTS.md ~80 líneas (multi-IDE, no duplicación)

### Fase 5: Eliminar lo que sobra
- 19 skills antiguos
- standards/ (65 archivos)
- contracts
- 4 state files

### Fase 6: Contexts
- Crear contexts/ con stack guidelines lean
- Team customization placeholder

### Fase 7: Manifest simplificado
- ~80 líneas

### Fase 8: Templates + installer
- Single source .claude/ → auto-generate mirrors
- Interactive install con prompts inteligentes
- Feature-based installation

### Fase 9: Sync script
- Canonical = .claude/
- Generar .agents/, .github/ from .claude/

### Fase 10: Tasks + lessons system
- tasks/todo.md + tasks/lessons.md

### Fase 11: Verificación end-to-end
- Tests, linting, gates, sync, install en repo limpio
- Cada skill invocable
- Full workflow: brainstorm → plan → dispatch → review → commit → pr

---

## Documentación auto-update en /ai-pr

En cada PR, el skill /ai-pr debe actualizar automáticamente:

1. **README.md** — Si los cambios afectan la API, la instalación, o el uso
2. **CHANGELOG.md** — Entry con el cambio (conventional commits → changelog entry)
3. **docs/solution-intent.md** — Reemplaza product-contract.md. Es el "architecture + product view" del proyecto:
   - Qué hace el proyecto
   - Arquitectura de alto nivel
   - Decisiones técnicas clave
   - Stack y dependencias
   - Se actualiza incrementalmente con cada PR significativo

### External documentation portal (manifest.yml)

```yaml
documentation:
  auto_update:
    readme: true              # Update README.md on API/install/usage changes
    changelog: true           # Generate CHANGELOG entries from commits
    solution_intent: true     # Update docs/solution-intent.md on architecture changes
  external_portal:
    enabled: false
    source: null              # path o URL Git
    update_method: "pr"       # "pr" = branch + PR | "push" = direct push
```

El skill /ai-write se encarga de la generación de contenido. /ai-pr lo orquesta durante el PR workflow.

---

## /ai-architect — Decisión

/ai-architect NO es un skill separado. La capacidad de architecture review se distribuye en:

1. **/ai-brainstorm** — Cuando la tarea es una decisión arquitectónica, brainstorm lo detecta y entra en modo architecture: evalúa alternativas, trade-offs, fitness functions, boundaries
2. **/ai-review** — El agent de architecture review (1 de los 8 agents paralelos) detecta drift, coupling, cohesion, boundaries en el código
3. **/ai-explore** — Architecture mapping cuando se necesita entender la arquitectura actual
4. **/ai-explain** — Explicar decisiones arquitectónicas existentes

Si en el futuro se necesita un /ai-architect dedicado, se puede crear con /ai-create. Pero por ahora, la capacidad está cubierta por la combinación de brainstorm + review + explore + explain.

---

## Specs y Tasks — Organización

### Specs (project-level architecture decisions)

```
.ai-engineering/
├── specs/
│   ├── _active.md                    # Pointer al spec activo
│   ├── 055-radical-simplification/   # Spec actual
│   │   ├── spec.md
│   │   ├── plan.md
│   │   └── tasks.md
│   └── archive/                      # Specs completados
│       ├── 001-initial/
│       ├── ...
│       └── 054-hooks-security/
```

### Tasks (session-level execution tracking)

```
.ai-engineering/
├── tasks/
│   ├── todo.md         # Current tasks with checkboxes [x]
│   └── lessons.md      # Self-improvement learnings (persistent across sessions)
```

**Diferencia clave**:
- **Specs** = "QUÉ vamos a construir y POR QUÉ" — decisiones arquitectónicas, diseño, scope
- **Tasks** = "QUÉ queda por hacer AHORA" — checklist de ejecución, progreso de la sesión actual
- **Lessons** = "QUÉ aprendimos" — errores corregidos, patterns descubiertos, reglas nuevas

Los specs viven dentro de `.ai-engineering/` porque son parte de la gobernanza del proyecto.
Los tasks también, porque su tracking persiste entre sesiones.

---

## Métricas de éxito

| Métrica | Antes | Después |
|---------|-------|---------|
| Skills | 37 (overlap, bloat) | 28 (focused, handler-based) |
| Agents | 8 | 8 (better defined) |
| Standards | 65 archivos | 0 (→ contexts/ + tool configs) |
| Contracts | 2 archivos | 0 (→ CLAUDE.md + manifest) |
| State files | 6 | 2 |
| Template copies | 3-4x | 1x + auto-generate |
| Total instruction lines | 76K | ~20-25K |
| Ratio instrucciones:código | 3:1 | ~1:1 |
| Brainstorming before code | Optional | MANDATORY (hard-gate) |
| Self-challenge in review | None | Every agent |
| Continuous improvement | Manual | Automated (ai-learn) |
| Prompt optimization | None | Built-in (ai-prompt) |
