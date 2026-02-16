# Speech Script — ai-engineering: Gobernanza para el Desarrollo Asistido por IA

**Presentation**: 18 slides, 20 minutes
**Language**: Spanish with English technical terms preserved
**Audience**: Authority Board + Architecture Board

---

## SECTION 1: HOOK & CONTEXT (Slides 1-4, ~4 min)

---

### Slide 1 — Title (30s)

**Title**: "ai-engineering: Gobernanza para el Desarrollo Asistido por IA"
**Subtitle**: "Simple. Eficiente. Práctico. Robusto. Seguro."

**Talking Points:**

> Buenos días. Hoy les presento ai-engineering — un framework de gobernanza para desarrollo asistido por IA.
>
> No es una plataforma que comprar. No es un pipeline que gestionar. Es un framework de contenido — Markdown, YAML, JSON, Bash — que convierte la asistencia de IA en entrega gobernada.
>
> Open source, licencia MIT, Python 3.11+, compatible con cualquier sistema operativo.

---

### Slide 2 — Estado Actual de la IA (1.5min)

**SVG**: `01-evolution-timeline.svg`

**Talking Points:**

> Para entender por qué necesitamos gobernanza, veamos cómo hemos llegado hasta aquí.
>
> En 2022 teníamos code completion — Copilot, TabNine — sugiriendo línea por línea. En 2023 llegó chat-in-IDE: conversaciones con la IA dentro del editor. En 2024, agentic coding — herramientas como Claude Code o Devin que ejecutan tareas completas de forma autónoma.
>
> En 2025 explotó el ecosistema multi-agent: MCP — Model Context Protocol — para integración de herramientas, y A2A — Agent-to-Agent — para coordinación entre agentes.
>
> Pero aquí está el punto crítico: **toda esta capacidad se ha desarrollado sin una capa de gobernanza**. Más poder sin más control.
>
> Quiero definir cuatro conceptos que usaré durante la presentación:
> - **Skills**: procedimientos reutilizables escritos en Markdown que cualquier agente IA puede leer y ejecutar.
> - **Agents**: personas especializadas — contratos de comportamiento, no procesos ejecutándose.
> - **MCP**: Model Context Protocol — el estándar para que los modelos se conecten con herramientas externas.
> - **A2A**: Agent-to-Agent — coordinación entre múltiples agentes.
>
> ai-engineering NO usa MCP ni A2A directamente — pero se posiciona en este ecosistema como **la capa de gobernanza** que falta.

---

### Slide 3 — El Problema: Sin Gobernanza (1.5min)

**SVG**: `02-chaos-diagram.svg`

**Talking Points:**

> Esto es lo que pasa cuando usas IA para codificar sin gobernanza.
>
> Cuatro agentes IA, mismo codebase, cero coordinación. El resultado:
>
> - **Secrets en commits** — la IA genera código con credenciales y nadie lo detecta antes del push.
> - **Quality gates bypassed** — sin enforcement local, la IA omite tests, ignora linting.
> - **Architectural drift** — cada agente toma decisiones arquitectónicas diferentes, sin coherencia.
> - **Decisiones repetidas** — la IA pregunta lo mismo en cada sesión porque no tiene memoria.
>
> Para los boards, esto se traduce en cuatro riesgos concretos:
> - **Compliance gaps**: sin audit trail, sin registro de qué se decidió ni por qué.
> - **Security exposure**: secrets en el historial de git, sin SAST scanning local.
> - **Quality degradation**: sin umbrales de cobertura, sin control de complejidad.
> - **Knowledge loss**: decisiones que se pierden entre sesiones.
>
> Como dijo un colega: *"Cada equipo usando IA para codificar hoy está ejecutando un experimento sin gobernar."*

---

### Slide 4 — El Viaje: 5 Reescrituras (1min)

**SVG**: `03-convergence-funnel.svg`

**Talking Points:**

> No llegamos a ai-engineering a la primera. Exploramos cuatro frameworks existentes:
>
> - **SpecKit**: buena gestión de specs, pero sin enforcement — las reglas son sugerencias.
> - **BMAD Method**: excelente orquestación multi-agente, pero heavyweight — demasiada ceremonia para equipos reales.
> - **GSD**: pragmático y rápido, pero sin backbone de gobernanza — sin gates, sin risk management, sin audit.
> - **OpenSpec**: aspiraciones de estándar abierto, pero sin tooling práctico — no lo puedes instalar hoy.
>
> Después de 5 iteraciones internas, la conclusión fue clara: necesitamos **gobernanza content-first** que sea simple de adoptar, estricta para enforcement, y flexible para escalar entre equipos.
>
> Eso es ai-engineering.

---

## SECTION 2: SOLUCIÓN (Slides 5-7, ~4 min)

---

### Slide 5 — Qué es ai-engineering (1.5min)

**SVG**: `04-architecture-overview.svg`

**Talking Points:**

> Entonces, ¿qué es ai-engineering exactamente?
>
> **NO es una plataforma**. NO es un pipeline CI/CD. NO es otra herramienta que gestionar ni otra licencia que pagar.
>
> Es un **content framework**. Markdown, YAML, JSON y Bash definen todo el comportamiento. El directorio `.ai-engineering/` es la fuente de verdad canónica, instalada por repositorio.
>
> Cinco subdirectorios:
> - **standards/** — reglas del framework y del equipo, con layering de precedencia.
> - **skills/** — 31 procedimientos reutilizables en 7 categorías.
> - **agents/** — 8 personas especializadas con contratos de comportamiento.
> - **context/** — specs de entrega, contratos de producto, learnings institucionales.
> - **state/** — decision store, audit log, manifests de instalación.
>
> El CLI es mínimo: `ai-eng install`, `update`, `doctor`, `validate`. Cuatro comandos.
>
> Y funciona con cualquier AI provider: Claude Code con 37 slash commands, GitHub Copilot con copilot-instructions, OpenAI Codex con codex.md. Un framework, cada provider.
>
> Piensen en ello como **una constitución para el repositorio asistido por IA**.

---

### Slide 6 — Cómo Funciona: Developer Experience (1.5min)

**SVG**: `05-developer-pipeline.svg`

**Talking Points:**

> Veamos la experiencia del desarrollador. Esto es lo que pasa en menos de 5 minutos:
>
> `ai-eng install .` — crea el governance root, configura git hooks, genera state files. Listo.
>
> A partir de ese momento, cada commit pasa por quality gates automáticamente:
>
> **Pre-commit**: ruff format y lint para código limpio, gitleaks para detección de secrets.
> **Commit-msg**: validación de formato, protección de branch — no puedes hacer commit directo a main.
> **Pre-push**: semgrep para SAST y OWASP, pip-audit para CVEs en dependencias, pytest para tests, ty para type checking.
>
> Si falla algún gate: **el push se bloquea**. No hay bypass. No hay --no-verify. El código no sale de la máquina del desarrollador hasta que cumple todos los umbrales.
>
> Esto es enforcement local, sin dependencia de CI para calidad baseline. Los problemas se detectan antes de que el código llegue al repositorio remoto.
>
> `ai-eng doctor` verifica que todo esté operativo. `ai-eng validate` valida la integridad de los archivos de gobernanza.
>
> **Tu siguiente commit después del install ya está gobernado.**

---

### Slide 7 — Modelo de Ownership (1min)

**SVG**: `06-ownership-layers.svg`

**Talking Points:**

> Uno de los problemas más comunes con la gobernanza es: ¿quién es dueño de qué?
>
> ai-engineering define cuatro boundaries claros:
>
> 1. **Framework-managed**: standards del framework, skills, agents. Actualizables con `ai-eng update`. Dry-run por defecto — revisas antes de aplicar.
>
> 2. **Team-managed**: standards del equipo en `standards/team/`. **NUNCA sobrescrito** por updates del framework. El equipo puede ser más estricto, pero nunca más débil que el framework.
>
> 3. **Project-managed**: specs de entrega, contratos de producto, learnings. **NUNCA sobrescrito**. Es la memoria institucional del proyecto.
>
> 4. **System-managed**: state files de runtime — decision store, audit log, install manifest. Mantenidos automáticamente.
>
> Los iconos de lock que ven son reales: ni el framework ni la CLI pueden sobrescribir contenido del equipo o del proyecto. **Ownership boundaries son non-negotiable.**

---

## SECTION 3: DEEP DIVE (Slides 8-12, ~6 min)

---

### Slide 8 — Skills: 31 Procedimientos Reutilizables (1.5min)

**SVG**: `07-skills-hexgrid.svg`

**Talking Points:**

> Hablemos del motor principal: los skills.
>
> 31 skills organizados en 7 categorías. Cada skill es un archivo Markdown con estructura definida: Purpose, Trigger, Procedure, Output Contract, Governance Notes.
>
> Las categorías:
> - **Workflows** (4): commit, PR, acho, pre-implementation — los flujos del día a día.
> - **Dev** (6): debug, refactor, code review, test strategy, migration, dependency updates.
> - **Review** (3): architecture, performance, security.
> - **Docs** (4): changelog, explain (estilo Feynman), writer, prompt design.
> - **Govern** (9): create/delete specs, skills, agents + risk lifecycle (accept, resolve, renew).
> - **Quality** (3): audit code, audit report, install check.
> - **Utils** (3): git helpers, platform detection, Python patterns.
>
> Lo importante: **NO son código**. Son especificaciones de comportamiento. Cualquier agente IA los lee y ejecuta. El mismo skill funciona en Claude Code, Copilot, y Codex sin modificación.
>
> Cuando un desarrollador ejecuta `/commit`, no está corriendo un script — está activando un skill que define paso a paso qué debe hacer el agente IA: stage, validate, commit, push, con todos los gates intermedios.

---

### Slide 9 — Agents: 8 Personas Especializadas (1min)

**SVG**: `08-agent-network.svg`

**Talking Points:**

> Los agents complementan a los skills. Son **contratos de comportamiento** — no procesos corriendo.
>
> 8 agentes especializados:
> - **Principal Engineer**: code review a nivel senior, enforcement de standards.
> - **Architect**: análisis arquitectónico, patterns, escalabilidad.
> - **Security Reviewer**: assessment de seguridad, OWASP, threat modeling.
> - **Debugger**: diagnóstico sistemático, root cause analysis.
> - **Quality Auditor**: enforcement de quality gates, coverage, complejidad.
> - **Verify App**: verificación end-to-end, smoke tests.
> - **Codebase Mapper**: mapeo de estructura, análisis de dependencias.
> - **Code Simplifier**: reducción de complejidad, mejora de legibilidad.
>
> Cada agente tiene: Identity, Capabilities, Activation rules, Behavior protocol, Referenced Skills, Output Contract, y Boundaries.
>
> Un desarrollador puede activar `/agent:verify-app` y obtener una verificación completa del aplicativo, o `/agent:security-reviewer` para un assessment de seguridad — ejecutados por la IA pero con contrato de comportamiento definido.

---

### Slide 10 — Spec-Driven Delivery (1.5min)

**SVG**: `09-spec-lifecycle.svg`

**Talking Points:**

> Todo cambio no-trivial en ai-engineering sigue un ciclo de 4 documentos:
>
> - **spec.md** — el QUÉ: requisitos, scope, criterios de aceptación.
> - **plan.md** — el CÓMO: decisiones arquitectónicas, approach, trade-offs.
> - **tasks.md** — el HACER: lista ordenada de tareas, asignables, rastreables.
> - **done.md** — el HECHO: log de completación, learnings registrados.
>
> Esto **NO es burocracia**. Es **recuperación de sesión IA**. Cualquier agente puede retomar cualquier spec en cualquier punto. La IA lee spec.md, consulta tasks.md, verifica decision-store, y continúa exactamente donde se quedó.
>
> Para el Architecture Board: la ejecución multi-agente es paralela. Las fases sin dependencias corren simultáneamente en ramas separadas — Agent A en feat/spec-012-phase1, Agent B en feat/spec-012-phase2. Cada fase pasa por un phase gate antes de la siguiente.
>
> El formato de commit es determinístico: `spec-NNN: Task X.Y — description`. Cada commit es trazable a un spec y una tarea.

---

### Slide 11 — State Management y Decision Continuity (1min)

**No SVG — verbal slide or minimal visual**

**Talking Points:**

> La memoria institucional vive en 5 state files:
>
> - **install-manifest.json**: qué se instaló, cuándo, qué versión.
> - **ownership-map.json**: quién es dueño de cada path.
> - **sources.lock.json**: remote skills con checksums verificables.
> - **decision-store.json**: decisiones con context hash SHA-256. Hoy tenemos 10 decisiones reales registradas.
> - **audit-log.ndjson**: log append-only. Tenemos 183 eventos registrados — gates passed, commands created, lifecycle events.
>
> La **decision continuity** es clave: cuando un Agent A toma una decisión en la sesión 1, genera un context hash SHA-256. Cuando Agent B llega en la sesión 5, lee el decision store y **no vuelve a preguntar**. Solo re-prompts si: expired, scope changed, severity changed, policy changed, o context hash changed.
>
> Esto resuelve uno de los problemas más frustrantes de la IA: las preguntas repetidas.

---

### Slide 12 — Quality Gates y Security (1min)

**SVG**: `10-gate-pipeline.svg`

**Talking Points:**

> Entremos en detalle en los quality gates.
>
> 3 stages, todos mandatorios:
> - **Pre-commit**: ruff format, ruff lint, gitleaks.
> - **Commit-msg**: formato válido, branch protection.
> - **Pre-push**: semgrep SAST/OWASP, pip-audit CVE, pytest, ty type checking.
>
> Umbrales: Coverage ≥80% (≥90% governance-critical), Duplication ≤3%, Cyclomatic complexity ≤10, Cognitive complexity ≤15.
>
> Para seguridad: el risk acceptance es estructurado. No puedes ignorar un finding — tienes que registrar una aceptación de riesgo con severidad y expiración: Critical 15 días, High 30 días, Medium 60 días, Low 90 días. Máximo 2 renovaciones.
>
> **No puedes mergear con un blocker finding. No puedes dismiss un issue de seguridad sin risk acceptance trackeado.**

---

## SECTION 4: VALOR (Slides 13-15, ~3 min)

---

### Slide 13 — Valor por Rol (1.5min)

**No SVG — use PowerPoint matrix layout**

**Talking Points:**

> El valor de ai-engineering depende de quién lo mire:
>
> **Engineers**: Workflows rápidos — 37 slash commands. Quality gates capturan problemas antes del push, no después en CI. Menos ida y vuelta.
>
> **Governance/Compliance**: audit-log.ndjson con 183 eventos trazables. Decision store con 10 decisiones reales. Risk lifecycle con expiración. Enforcement non-bypassable. Esto es auditable.
>
> **Security/AppSec**: gitleaks + semgrep + pip-audit en cada push. Clasificación por severidad. No puedes dismissear sin risk acceptance. Máximo 2 renovaciones. Detección antes de que el código llegue al repo remoto.
>
> **Quality/DevEx**: Quality gates tipo Sonar — coverage, duplication, complejidad — **SIN servidor SonarQube**. Sin licencias, sin infraestructura adicional. Integridad en 6 categorías. Setup en menos de 5 minutos.
>
> **Architecture**: Standards con layering (framework > stack > team). Ownership boundaries. Agent personas para review consistente — el mismo Architect agent revisa con los mismos criterios siempre.

---

### Slide 14 — Business Case: ROI y Risk Reduction (1min)

**No SVG — use PowerPoint metric cards**

**Talking Points:**

> El business case es directo:
>
> **Risk reduction**: 0 operaciones sin gate. 100% de gate execution. Secrets detectados antes del commit, no en producción.
>
> **Cost avoidance**: 0 licencias SonarQube. Sin infraestructura CI/CD adicional para calidad baseline. El framework es MIT — coste de licencia cero.
>
> **Consistencia**: mismo framework en todos los repos, equipos, AI providers. Un install, un estándar.
>
> **Time savings**: menos de 5 minutos desde install hasta primer commit gobernado. Decisiones no se repiten entre sesiones.
>
> **Compliance readiness**: audit log append-only, risk acceptance con expiración, decision store con context hashing SHA-256. Si compliance pregunta "¿quién decidió esto y por qué?", la respuesta está en el state.

---

### Slide 15 — Multi-IDE: Un Framework, Cada Provider (30s)

**No SVG — use PowerPoint with IDE logos**

**Talking Points:**

> Un punto clave para Architecture: sin vendor lock-in.
>
> Claude Code usa CLAUDE.md más 37 slash commands en `.claude/commands/`. Copilot usa copilot-instructions.md más prompts en `.github/copilot/`. Codex usa codex.md. Terminal usa el CLI directamente.
>
> Cambias de provider, mantienes la gobernanza. Los skills y agents son Markdown IDE-agnóstico — la misma skill funciona en cualquier proveedor.

---

## SECTION 5: DIFERENCIACIÓN (Slides 16-17, ~2 min)

---

### Slide 16 — ¿Por qué no IA a secas con instrucciones simples? (1min)

**SVG**: `11-comparison-table.svg`

**Talking Points:**

> La pregunta obvia: "¿Por qué no simplemente escribimos un archivo de instrucciones y ya?"
>
> Las instrucciones simples funcionan para tareas individuales. Se rompen a escala:
>
> - Sin enforcement: las instrucciones son sugerencias. La IA puede ignorarlas.
> - Sin estado: cada sesión empieza de cero. Las decisiones se re-preguntan.
> - Sin ownership model: cualquiera sobrescribe cualquier cosa.
> - Sin audit trail: sin registro de qué se decidió, cuándo, por qué.
> - Sin security scanning: dependes 100% del CI.
> - Sin risk management: no hay proceso para aceptar, trackear, o expirar riesgos.
> - Sin delivery lifecycle: el trabajo es ad-hoc, no spec-driven.
>
> Como ven en la tabla: instrucciones simples, 0 de 8 capacidades enforced. ai-engineering, 8 de 8.
>
> **Las instrucciones le dicen a la IA qué hacer. ai-engineering asegura que realmente lo haga.**

---

### Slide 17 — ¿Por qué ai-engineering vs alternativas? (1min)

**SVG**: `12-radar-chart.svg`

**Talking Points:**

> Frente a las alternativas del mercado, la diferencia está en el radar:
>
> - vs **SpecKit**: gestiona specs — ai-engineering gestiona el ciclo completo gobernado con enforcement.
> - vs **BMAD Method**: fuerte en multi-agent, pero heavyweight. ai-engineering es lighter, content-first, provider-agnostic.
> - vs **GSD**: pragmático pero sin backbone de gobernanza — sin gates, sin risk, sin decisions, sin audit.
> - vs **OpenSpec**: estándar abierto aspiracional. ai-engineering es un framework instalable y práctico hoy.
>
> Los cinco diferenciadores clave:
> 1. Content-first — no hay servidor, no hay runtime, solo archivos.
> 2. Enforcement non-bypassable — git hooks mandatorios.
> 3. Risk lifecycle — accept, resolve, renew, con expiración y límite de renovaciones.
> 4. Cross-IDE day one — Claude, Copilot, Codex desde el primer install.
> 5. Ownership model — boundaries claros que ni el framework puede violar.

---

## SECTION 6: CIERRE (Slide 18, ~1 min)

---

### Slide 18 — Call to Action (1min)

**No SVG — use PowerPoint roadmap visual**

**Talking Points:**

> El ask es claro: **aprobar ai-engineering como estándar de gobernanza para desarrollo AI-asistido en la organización.**
>
> **Plan piloto**: 2-3 repositorios el próximo quarter. Mediremos cuatro métricas:
> - Gate execution rate — ¿qué porcentaje de operaciones pasan por gates?
> - Time to governed commit — ¿cuánto tarda un equipo nuevo en hacer su primer commit gobernado?
> - Security catch rate — ¿cuántos issues de seguridad se capturan antes del push?
> - Decision reuse rate — ¿cuántas decisiones se reutilizan vs se re-preguntan?
>
> **Roadmap por fases**:
> - **Phase 1 (ahora)**: GitHub + Python + Claude/Copilot/Codex.
> - **Phase 2**: Azure DevOps + más stacks + signature verification.
> - **Phase 3**: Multi-agent orchestration at scale + docs site.
>
> **Inversión**: 0 coste de licencias — MIT open source. Tooling mínimo — Python y git hooks. La inversión principal es tiempo de adopción del equipo, compensado por gobernanza automatizada.
>
> **Next step**: Aprobar el scope del piloto. El framework está listo para instalar hoy.
>
> Gracias. ¿Preguntas?

---

## Appendix: Verified Data Points

| Claim | Verified Value | Source |
|-------|---------------|--------|
| Skills count | 31 across 7 categories | `.ai-engineering/skills/` directory scan |
| Agents count | 8 specialized personas | `.ai-engineering/agents/` directory scan |
| Decisions recorded | 10 real decisions | `.ai-engineering/state/decision-store.json` |
| Audit log entries | 183 governance events | `.ai-engineering/state/audit-log.ndjson` |
| Slash commands | 37 command wrappers | `.claude/commands/` directory scan |
| Quality thresholds | Coverage ≥80%, Dup ≤3%, CC ≤10, CogC ≤15 | `.ai-engineering/standards/framework/core.md` |
| Risk expiry | Critical=15d, High=30d, Medium=60d, Low=90d | `.ai-engineering/standards/framework/core.md` |
| Framework version | 0.1.0 (schema 1.1) | `.ai-engineering/manifest.yml` |
| License | MIT | `framework-contract.md` |
| Required Python | 3.11+ | `stacks/python.md` |
