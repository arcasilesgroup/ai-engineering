# Anti-Patterns: Las 3 Formas de Fracasar

> Adapted from "Tres formas de fracasar" -- Codemotion Madrid 2026-04 platform engineering keynote (Kaspar von Grünberg, PlatformCon 2022 + 2024).
> Reframed for ai-engineering as a self-critique mirror.

This document is a deliberate counter-narrative to the rest of the framework's documentation. The skills, agents, and gates described elsewhere are how ai-engineering is supposed to behave. The patterns below are how ai-engineering fails when nobody is watching: portal-shaped governance theater, registered-but-rotting skill catalogs, and mandates that nobody reads. Each section names the failure mode in deck-style framing, applies it to this codebase, surfaces a concrete telemetry symptom, and prescribes the corrective practice.

## Portal ≠ Plataforma → Hooks instalados ≠ enforcement

Instalar hooks no es lo mismo que aplicarlos. ai-engineering puede dejar `block-dangerous.sh`, `gitleaks protect --staged` y los gates de cobertura cosidos al `pre-commit` de cada repo, pero si los developers se acostumbran a saltarlos -- con `--no-verify`, ignorando los warnings, o con un CI que no replica las mismas reglas -- lo único que queda es un portal vistoso encima de un proceso vacío. La plataforma deja de ser plataforma y vuelve a ser un script de instalación. **Síntoma**: la métrica `gate-failure rate` sube en `.ai-engineering/state/framework-events.ndjson` mientras el conteo de `skill_invoked` se queda plano o incluso baja; significa que la gente toca el sistema cada vez menos, pero cuando lo toca, los gates fallan, y el equipo sigue mergeando igual. **Práctica correctiva**: replicar los mismos gates en CI (no solo en pre-commit), tratar cada `--no-verify` como una señal de governance que merece investigación -- nunca como error humano aislado -- y persistir los bypasses en `state/decision-store.json` con TTL y owner para que sean auditables.

## Proyecto ≠ Producto → Skill registrada ≠ skill mantenida

Tener 49 skills publicados no convierte a ai-engineering en un producto: lo convierte en un catálogo. Una skill es producto solo cuando se invoca, se mide, se afila y -- cuando deja de aportar -- se deprecia con honestidad. Si la mitad de los skills llevan más de 180 días sin un commit y reciben menos de una invocación al mes, son lastre: aumentan la superficie de mantenimiento, contaminan los resultados de búsqueda interna, y hacen que los developers desconfíen de los que sí funcionan. **Síntoma**: la cola larga de `skill_invoked` en `framework-events.ndjson` muestra skills con cero invocaciones en el último trimestre, y el coverage report de `tests/skills/` revela archivos `SKILL.md` que ningún test cubre porque nadie los usa. **Práctica correctiva**: pasar `/skill-evolve` o un sharpen pass sobre cada skill cada trimestre con telemetría de uso real; si una skill se queda en cero invocaciones dos trimestres seguidos, deprecarla explícitamente -- aviso, ventana, eliminación con commit firmado -- nunca por silenciosa atrofia.

## Mandato ≠ Adopción → CLAUDE.md obligatorio ≠ developer la lee

Convertir `CLAUDE.md`, `AGENTS.md` y la `CONSTITUTION.md` en puntos de entrada obligatorios para los agentes IDE no garantiza que se respeten: garantiza que existen. La adopción real exige que esos archivos sean cortos, accionables y auditables; si crecen sin freno se vuelven invisibles, y un mandato invisible es indistinguible de un mandato ausente. Peor: cuando los agentes violan reglas que sí están escritas, el problema no es el agente -- es la legibilidad del documento. **Síntoma**: incidentes recurrentes en los que un agente repite una regla violada (por ejemplo, modifica un test para que pase, o usa `--no-verify`) sobre algo que CLAUDE.md prohíbe explícitamente; o `LESSONS.md` acumula la misma corrección en sesiones diferentes. **Práctica correctiva**: tratar CLAUDE.md y AGENTS.md como interfaces de producto -- presupuesto de líneas estricto, links a la fuente canónica en lugar de duplicar contenido, y métricas de adopción basadas en señales voluntarias (skills invocados sin que el usuario los pida, lessons capturadas tras corrección) en lugar de en la mera presencia del archivo.

## See Also

- [CONSTITUTION.md](../CONSTITUTION.md) -- the non-negotiable governance document
- [AGENTS.md](../AGENTS.md) -- canonical cross-IDE entry point
- spec-110 governance v3 harvest -- the spec that motivated this document
