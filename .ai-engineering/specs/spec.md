---
spec: spec-093
title: "Design Skill Pack: 3 skills + 1 reviewer specialist"
status: done
effort: large
---

# Spec 093 - Design Skill Pack: 3 skills + 1 specialist sub-agent

## Summary

ai-engineering carece de una superficie explícita para diseño de interfaces, motion design y artefactos visuales. Los skills existentes (ai-slides, ai-media, ai-video-editing) cubren presentación, generación multimedia y edición de vídeo, pero no diseño frontend, criterio UI/UX, animación como disciplina, ni composición visual estática. Se integran 5 fuentes externas (frontend-design, ui-ux-pro-max, emil-design-eng, canvas-design, web-interface-guidelines) mediante absorción completa (sin resumir) en 3 nuevos skills + 1 nuevo specialist agent, llevando el framework de 44 a 47 skills. reviewer-design se añade como specialist sub-agent (como los existentes reviewer-frontend, reviewer-security, etc.) sin incrementar el count de agents principales (10).

## Goals

- Crear 3 nuevos skills: `ai-design`, `ai-animation`, `ai-canvas`
- Crear 1 nuevo specialist agent: `reviewer-design` (dispatched por ai-review)
- Absorber el contenido COMPLETO de las 5 fuentes (sin resumir) usando el patrón Skills + Handlers
- Cada skill tiene SKILL.md (proceso/orquestación) + handlers/ (conocimiento detallado)
- Registrar en manifest.yml (47 skills, 10 agents principales — reviewer-design es sub-agent)
- Ejecutar mirror sync (.codex/, .gemini/, .github/skills/)
- Pasar skill-creator eval para verificar triggering, output quality y distinción
- Mirror sync produce copias en .codex/, .gemini/, .github/skills/ verificadas por pytest
- Framework-agnostic con ejemplos React como stack por defecto
- Compatibilidad multi-IDE por defecto

## Non-Goals

- No modificar ai-slides, ai-media, ai-video-editing — solo definir integration points
- No crear context files compartidos en .ai-engineering/contexts/ — cada skill owns sus handlers
- No wrappear ni depender de skills standalone instalados vía skills.sh (frontend-design, ui-ux-pro-max)
- No incluir shadcn/ui — descartado por no ser skill de diseño
- No escribir el contenido final de los SKILL.md/handlers en esta spec — solo definir la arquitectura, estructura de archivos, y distribución de fuentes

## Decisions

### D-093-01: 3 skills + 1 agent, no 4 skills ni 5 skills

La combinación óptima es 3 skills invocables + 1 specialist agent:
- **ai-design** (skill): dirección estética + design systems + componentes
- **ai-animation** (skill): motion design como disciplina independiente
- **ai-canvas** (skill): artefactos visuales estáticos (posters, banners, PDFs)
- **reviewer-design** (agent): specialist de ai-review para compliance UI

**Rationale**: ai-animation justifica skill propio porque la animación es una disciplina con superficie de invocación propia ("anima esto", "revisa las transiciones") y se usa fuera de diseño (ai-slides, ai-code). reviewer-design no es skill porque el usuario ya invoca `/ai-review` — añadir otro punto de entrada duplicaría invocación. Canvas es caso de uso único (arte visual ≠ UI). Un solo ai-design con handlers separados (aesthetics.md vs design-system.md) logra separación de concerns sin fragmentar la superficie de invocación — el usuario piensa "diseño", no "tokens vs estética".

### D-093-02: Absorción completa, no resumen

El contenido de las 5 fuentes se integra COMPLETO en los handlers sin resumir ni condensar. Las reglas, ejemplos de código, tablas de decisión, y checklists se preservan íntegramente.

**Rationale**: El valor de estas fuentes está en el detalle — curvas de easing específicas, duraciones exactas, anti-patterns concretos. Resumir pierde precisión y degrada la calidad del output.

### D-093-03: Patrón Skills + Handlers (Approach B)

Cada skill sigue la estructura:
```
.claude/skills/ai-{name}/
  SKILL.md              → proceso, triggering, integration points
  handlers/
    {topic}.md          → conocimiento detallado absorbido
```

**Rationale**: Patrón validado en ai-brainstorm, ai-verify, ai-skill-evolve. Permite contenido extenso sin degradar la legibilidad del SKILL.md principal. Cada handler es actualizable independientemente.

### D-093-04: Distribución de fuentes por skill/agent

| Fuente | Destino | Qué absorbe |
|--------|---------|-------------|
| Frontend Design (Anthropic) | **ai-design** handlers/ | Design thinking framework, aesthetics guidelines, anti-patterns, typography, color, motion, spatial composition, backgrounds |
| UI/UX Pro Max | **ai-design** handlers/ | 50+ estilos, 161 paletas, 57 font pairings, 99 UX guidelines, priority rules (a11y P1, touch P2, perf P3), pre-delivery checklist, product type patterns |
| Emil Design Engineering | **ai-animation** handlers/ | Animation decision framework, spring animations, component principles, CSS transforms, clip-path, gestures/drag, performance rules, Sonner principles, stagger, debugging |
| Emil Design Engineering | **reviewer-design** | Review checklist (Before/After/Why table), anti-patterns de animación |
| Web Interface Guidelines (Vercel) | **reviewer-design** | Todas las reglas: a11y, focus states, forms, animation, typography, content handling, images, performance, navigation, touch, safe areas, dark mode, locale, hydration, hover states, anti-patterns |
| Canvas Design (Anthropic) | **ai-canvas** handlers/ | Filosofía creation process, canvas creation requirements, typography rules, craftsmanship standard, conceptual reference integration, refinement, multi-page |

### D-093-05: Estructura detallada de cada pieza

**ai-design** (skill — effort: high):
```
.claude/skills/ai-design/
  SKILL.md
  handlers/
    aesthetics.md        → Frontend Design completo (design thinking, tone, differentiation)
    design-system.md     → UI/UX Pro Max completo (styles, palettes, fonts, UX rules)
    checklist.md         → Pre-delivery quality checklist (merged de ambas fuentes)
```
- Triggering: "diseña una interfaz", "crea un design system", "dirección visual para", "estilo para esta página", "paleta de colores", "typography para"
- Invoca ai-animation cuando el diseño necesita motion
- Invoca ai-canvas cuando se necesitan artefactos visuales
- Consumido por ai-slides para dirección estética

**ai-animation** (skill — effort: high):
```
.claude/skills/ai-animation/
  SKILL.md               → Animation decision framework (frecuencia→propósito→easing→duración)
  handlers/
    motion-principles.md → Spring animations, easing strategy, durations, perceived performance
    components.md        → Buttons, popovers, tooltips, blur transitions, @starting-style
    clip-path.md         → Tabs, hold-to-delete, image reveals, comparison sliders
    gestures.md          → Momentum dismissal, damping, pointer capture, multi-touch, friction
    performance.md       → transform/opacity only, CSS variables, Framer Motion hw accel, WAAPI
    sonner-principles.md → DX, good defaults, naming, edge cases, cohesion, asymmetric timing
```
- Triggering: "anima este componente", "transiciones para", "micro-interacciones", "gesture de swipe", "spring animation", "revisa el motion"
- Standalone: se usa sin ai-design cuando el trabajo es puramente motion
- Consumido por ai-design, ai-slides, ai-code (frontend)

**ai-canvas** (skill — effort: high):
```
.claude/skills/ai-canvas/
  SKILL.md
  handlers/
    philosophy.md        → Philosophy creation process, naming movements, articulation
    canvas-creation.md   → Visual standards, typography rules, craftsmanship, refinement
    examples.md          → "Concrete Poetry", "Chromatic Language", "Analog Meditation", etc.
```
- Triggering: "crea un poster", "diseña un banner", "composición visual", "cartel para", "pieza de branding", "material de marketing visual"
- Consumido por ai-media para dirección visual
- Consumido por ai-slides para aesthetic philosophy

**reviewer-design** (agent — dispatched por ai-review):
```
.claude/agents/reviewer-design.md
```
- Contiene: Vercel Web Interface Guidelines completas + Emil's review checklist (Before/After/Why)
- Dispatched automáticamente cuando ai-review detecta código frontend
- Output format: `file:line` terse findings (Vercel format)
- Categorías de review: a11y, focus states, forms, animation, typography, performance, navigation, touch, dark mode, hydration

### D-093-06: Integraciones con skills existentes

| Skill existente | Integración | Tipo |
|-----------------|-------------|------|
| ai-brainstorm | Produce design specs que ai-design consume | optional |
| ai-code | Carga handlers de ai-animation cuando hace frontend work | optional |
| ai-review | Dispatcha reviewer-design como specialist en frontend | mandatory |
| ai-slides | Puede invocar ai-design para dirección estética, ai-animation para transitions | optional |
| ai-media | Puede invocar ai-canvas para dirección visual de generated assets | optional |
| ai-dispatch | Routea a ai-design/ai-animation/ai-canvas según el trabajo | mandatory |
| ai-verify | Valida compliance de diseño via reviewer-design rules | optional |

### D-093-07: Effort levels y tipo en manifest

| Pieza | Type | Tags | Effort |
|-------|------|------|--------|
| ai-design | design | [design, ui, ux, aesthetic] | high |
| ai-animation | design | [animation, motion, interaction] | high |
| ai-canvas | design | [visual, art, composition, marketing] | high |

Nuevo tipo `design` en manifest — no existe actualmente. Los 3 skills de media existentes (ai-slides, ai-media, ai-video-editing) permanecen como `writing`.

### D-093-08: skill-creator eval como gate obligatorio

Cada skill pasa por skill-creator eval antes de registrarse:
1. Triggering eval: ¿se activa con los prompts correctos y NO con los incorrectos?
2. Output quality eval: ¿el output es distintivo vs baseline sin skill?
3. Distinction eval: ¿ai-design, ai-animation y ai-canvas no se confunden entre sí?

**Rationale**: Las 3 skills tienen superficies cercanas ("diseño"). Sin eval, el riesgo de overtrigger/undertrigger es alto.

### D-093-09: Framework-agnostic con ejemplos React

Las reglas de diseño (easing, a11y, spatial composition) son agnósticas. Los ejemplos de código usan React/CSS como stack por defecto. Cuando el proyecto usa otro framework, el skill se adapta via context loading del proyecto.

**Rationale**: Las fuentes originales usan React (Framer Motion, Radix UI). Mantener los ejemplos originales preserva fidelidad. El context loading del proyecto ya permite adaptación.

## Risks

| Riesgo | Mitigación |
|--------|-----------|
| ai-design y ai-animation se confunden ("anima este botón" ¿es diseño o animación?) | CSO descriptions claras: ai-design = "qué construir", ai-animation = "cómo se mueve". Eval de distinction con skill-creator |
| ai-canvas undertriggers (caso de uso nicho) | Description CSO con triggers explícitos: "poster", "banner", "cartel", "composición visual", "branding piece" |
| reviewer-design duplica reviewer-frontend | reviewer-design = compliance visual (Vercel rules + Emil polish). reviewer-frontend = React patterns, hooks, state, TypeScript. Complementarios, no duplicados |
| Handlers muy grandes por absorción completa | Cada handler es un archivo independiente. El SKILL.md los carga on-demand según la tarea |
| Mirror sync de handlers en 4 IDEs | sync_command_mirrors.py ya maneja subdirectorios. Verificar con test |
| Nuevo tipo "design" en manifest rompe parsing | Tipo es string libre en el schema actual — sin riesgo de breaking change |

## References

- Frontend Design: https://skills.sh/anthropics/skills/frontend-design
- UI/UX Pro Max: https://skills.sh/nextlevelbuilder/ui-ux-pro-max-skill/ui-ux-pro-max
- Emil Design Engineering: https://github.com/emilkowalski/skill/blob/main/skills/emil-design-eng/SKILL.md
- Canvas Design: https://skills.sh/anthropics/skills/canvas-design
- Web Interface Guidelines: https://github.com/vercel-labs/web-interface-guidelines/main/command.md
- ai-create skill: `.claude/skills/ai-create/SKILL.md`
- ai-review skill: `.claude/skills/ai-review/SKILL.md`
- skill-creator: Anthropic skill-creator (installed via skills.sh)
