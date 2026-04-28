---
spec: spec-111
title: AI Research Skill — Multi-Tier Multi-Source with NotebookLM Persistence
status: approved
effort: large
refs:
  - .ai-engineering/specs/spec-110-governance-v3-harvest.md
  - .claude/skills/ai-brainstorm/SKILL.md
  - .claude/skills/ai-brainstorm/handlers/interrogate.md
  - .claude/skills/ai-brainstorm/handlers/prompt-enhance.md
  - .ai-engineering/contexts/spec-schema.md
  - src/ai_engineering/templates/project/.claude/skills
---

# Spec 111 — AI Research Skill

## Summary

`ai-engineering` carece de skill formal para research multi-fuente. Cuando `/ai-brainstorm` necesita evidencia externa para responder preguntas tipo "qué patrones usa la industria para X", "qué dice el state of the art de Y", o "qué bibliotecas resuelven Z" — situaciones que el handler `interrogate.md` declara explícitamente ("when the user's input requires research to understand the current state... gather data first") — el agente improvisa: invocaciones ad-hoc de `WebSearch`, sin citas estructuradas, sin reuso entre sesiones, y sin aprovechar fuentes ya disponibles que costarían cero: Context7 MCP (library docs autoritativos), Microsoft Learn MCP (Azure/.NET docs), `gh search code/repos` (patterns de código real), NotebookLM (deep research persistente con citas; ya tenemos cuenta autenticada). El research no se persiste — cada sesión repite el trabajo, y los specs producidos por brainstorm no enlazan a fuentes verificables. La industria 2026 converge en un patrón claro (Firecrawl/Tavily/Exa/ZenML "steerable deep research"): arquitectura 3-capas (retrieval / orchestration / reasoning) con tiered escalation (cheap-first), citation-first synthesis (Index-RAG pattern), y persistencia para reuso. spec-111 introduce `/ai-research` como skill formal multi-tier: Tier 0 local (grep repo + LESSONS.md + research artifacts previos) → Tier 1 MCPs gratis paralelos (Context7 + Microsoft Learn + `gh search`) → Tier 2 web (WebSearch + WebFetch) → Tier 3 NotebookLM persistente (1 notebook por invocación con flag opt-in `--reuse-notebook`). Citation hard-rule: todo claim externo trae `[N]` o se marca `[unsourced]` literal. Persistencia automática en `.ai-engineering/research/<topic-slug>-<YYYY-MM-DD>.md` cuando Tier 3 se invoca o flag `--persist`. Integración con `/ai-brainstorm`: el handler `interrogate.md` añade un step opcional que invoca `/ai-research --depth=standard <subquery>` cuando detecta evidencia externa requerida, y la spec resultante referencia el research artifact en su sección References. Beneficio medible: research se reutiliza entre sesiones (cero re-trabajo); specs traen citas verificables; brainstorm produce salidas con grounding empírico, no solo intuición del modelo.

## Goals

- G-1: `.claude/skills/ai-research/SKILL.md` existe con frontmatter (`name: ai-research`, `effort: high`, `triggers: ['research', 'investigate', 'find sources', 'state of the art', 'compare options']`), descripción, y sección Process. Handlers en `.claude/skills/ai-research/handlers/`: `classify-query.md`, `tier0-local.md`, `tier1-free-mcps.md`, `tier2-web.md`, `tier3-notebooklm.md`, `synthesize-with-citations.md`, `persist-artifact.md`. Mirrors regenerados para `.codex/skills/ai-research/`, `.gemini/skills/ai-research/`, `.github/skills/ai-research/` vía `ai-eng sync-mirrors`. Verificable por presencia de archivos + `tests/integration/test_ai_research_skill_present.py::test_skill_and_mirrors_exist`.
- G-2: Tier 0 (local) implementado en `tier0-local.md` — handler ejecuta: (a) glob `.ai-engineering/research/*.md` y match topic-slug similarity ≥0.7; (b) grep `LESSONS.md` por keywords del query; (c) parse `framework-events.ndjson` últimos 30 días filtrando por `kind: skill_invoked` con `detail.skill = ai-research` para detectar queries previas. Si Tier 0 produce ≥3 hits relevantes, skill puede shortcut sin escalar a tiers superiores (decisión del LLM agent). Verificable por `tests/integration/test_ai_research_tier0.py::test_local_match_short_circuits_when_sufficient` con fixture de research artifact previo.
- G-3: Tier 1 (MCPs gratis paralelos) — handler `tier1-free-mcps.md` invoca **en paralelo** las 3 fuentes: (a) Context7 vía `mcp__context7__resolve-library-id` + `query-docs` cuando query menciona library/framework/SDK/CLI; (b) Microsoft Learn vía `mcp__claude_ai_Microsoft_Learn__microsoft_docs_search` + `microsoft_code_sample_search` cuando query toca Azure/.NET/Microsoft; (c) `gh search code <query> --json repository,path,textMatches` + `gh search repos <topic>` para patterns de código real. Resultados se deduplicate por URL/path. Verificable por `tests/integration/test_ai_research_tier1.py::test_three_mcps_called_in_parallel` con mocks que verifiquen invocación concurrente (timestamp delta <100ms entre llamadas).
- G-4: Tier 2 (web) — handler `tier2-web.md` invoca WebSearch (raw results) y WebFetch (URL específica conocida) en paralelo cuando aplica. Default depth `standard` triggerea Tier 2 después de Tier 1 si éste produce <5 hits relevantes. WebSearch domain filtering opcional vía flag `--allowed-domains` y `--blocked-domains`. Verificable por `tests/integration/test_ai_research_tier2.py::test_websearch_invoked_with_filters`.
- G-5: Tier 3 (NotebookLM persistente) — handler `tier3-notebooklm.md` ejecuta secuencia: (a) `mcp__notebooklm-mcp__notebook_create` con name `ai-research/<topic-slug>-<YYYY-MM-DD>-<hash6>` donde `topic-slug` deriva del query (lowercase, alphanumeric + dashes, ≤40 chars) y `hash6` son los primeros 6 chars de SHA-256(query+timestamp); (b) `source_add` por cada URL recolectada en Tier 2 (max 20 sources para no exceder límites de NotebookLM); (c) `notebook_query` con el query original + instruction "answer with citations to the provided sources, using `[N]` notation"; (d) capturar `notebook_id` y `conversation_id` para persistencia. Triggerea solo cuando flag `--depth=deep` o cuando agent decide explícitamente que la respuesta amerita persistencia (heuristica: query es comparativa, multi-fuente, o el user invoca con `--persist`). Verificable por `tests/integration/test_ai_research_tier3.py::test_notebooklm_creation_and_query_with_citations` con mock del MCP server.
- G-6: Citation hard-rule — handler `synthesize-with-citations.md` produce output donde todo claim que NO sea derivable del local context trae notación `[N]` con N índice numérico, donde la sección Sources al final mapea N → `(title, url, accessed_at)`. Claims sin fuente verificable se marcan literalmente `[unsourced]` en el texto (forzar honestidad cuando el LLM rellena de su training). Validation: parser regex `\[\d+\]|\[unsourced\]` debe match al menos una vez por párrafo de claim externo. Verificable por `tests/unit/skills/ai_research/test_citation_validator.py::test_output_passes_citation_validation` con fixtures (output con citas válidas, output sin citas → fail, output con `[unsourced]` → pass).
- G-7: Persistencia — handler `persist-artifact.md` escribe `.ai-engineering/research/<topic-slug>-<YYYY-MM-DD>.md` con frontmatter (`query`, `depth`, `tiers_invoked: [0,1,2,3]`, `sources_used: [...]`, `notebook_id` si Tier 3, `created_at`, `slug`) + body con secciones `## Question`, `## Findings` (con citas inline), `## Sources` (numbered list), `## Notebook Reference` (URL si aplica). Persistencia automática SIEMPRE que Tier 3 se invoca; opt-in via `--persist` para depth quick/standard. Verificable por `tests/unit/skills/ai_research/test_persist.py::test_artifact_format_complete`.
- G-8: Integración con `/ai-brainstorm` — modificar `.claude/skills/ai-brainstorm/handlers/interrogate.md` para añadir step explícito: "Si la pregunta del usuario requiere evidencia externa que el modelo no puede confirmar (e.g., 'qué patrones usa la industria', 'qué dice el state of the art', 'qué bibliotecas resuelven X'), invocar `/ai-research --depth=standard <subquery>` y consumir el artifact resultante; citar el artifact en la spec resultante en sección References". Modificar `.ai-engineering/contexts/spec-schema.md` para permitir entries en `## References` con formato `- research: .ai-engineering/research/<artifact>.md`. Verificable por `tests/integration/test_brainstorm_research_integration.py::test_interrogation_invokes_research_when_evidence_required`.
- G-9: CLI flags — `/ai-research <query> [--depth quick|standard|deep] [--reuse-notebook=<id>] [--persist] [--allowed-domains a,b] [--blocked-domains x,y]`. Defaults: `--depth=standard`, no `--reuse-notebook`, `--persist` solo si Tier 3. Verificable por `tests/unit/skills/ai_research/test_cli_args.py` con 8 casos.
- G-10: Resilience — si MCP server (Context7, Microsoft Learn, NotebookLM) falla con timeout/auth/network, skill degrada al siguiente tier disponible y emite warning visible al usuario. NotebookLM auth check: invocar `mcp__notebooklm-mcp__server_info` antes de `notebook_create`; si auth expirada, suggest `nlm login` y degrada Tier 3 → Tier 2 only. Verificable por `tests/integration/test_ai_research_resilience.py::test_degraded_modes` con 4 escenarios (Context7 down, MS Learn down, NotebookLM auth expired, all down).
- G-11: 0 secrets, 0 vulns, 0 lint errors. Coverage ≥80% en handlers + tests.

## Non-Goals

- NG-1: Tier 4 academic (arxiv API, Semantic Scholar, PubMed). Defer; el use case primario es research técnico/de patrón, no investigación científica.
- NG-2: Tier 5 BYOK enterprise providers (Tavily, Exa, Perplexity Sonar, Brave Search, Firecrawl, You.com). Defer; el actual stack zero-cost cubre el 80% del valor. Cuando se necesite, se implementa via `ai-eng llm add-provider` interface (no incluida en este spec).
- NG-3: Survey mode `--mode=survey` (5 preguntas/mes a developers reales). DX measurement descartado por user en pregunta 2.
- NG-4: Auto-detection de "this query needs research" en otros skills (`/ai-debug`, `/ai-explain`, `/ai-plan`). Solo `/ai-brainstorm` integration en este spec; otros skills pueden invocar manualmente pero sin trigger automático.
- NG-5: Reranking ML-based o dedup vía embeddings. Síntesis usa el LLM del IDE host (subscription piggyback) para ordenar/deduplicar — no añadimos ML pipeline propia.
- NG-6: Multi-language support beyond Markdown. Artifacts solo Markdown UTF-8.
- NG-7: Auto-update de research artifacts cuando fuentes cambian. Artifacts son snapshots con `created_at`; refresh es manual via re-invocación.
- NG-8: Search en Slack, Linear, Notion, Confluence o cualquier sistema interno enterprise. Defer.
- NG-9: Resumen ejecutivo / TL;DR autogenerado al inicio del artifact. La sección Findings ya cubre esto; añadir TL;DR sería duplicación.
- NG-10: PR creation in this spec.

## Decisions

### D-111-01: 1 notebook por invocación, con `--reuse-notebook` opt-in

Default = crear nuevo notebook por cada invocación de `/ai-research` (alineado con input explícito del user en brainstorm). Naming `ai-research/<topic-slug>-<YYYY-MM-DD>-<hash6>`: el hash6 evita colisiones cuando hay múltiples invocaciones en mismo día con mismo topic-slug. Flag `--reuse-notebook=<id>` permite follow-up queries sobre un notebook existente (workflow iterativo cuando user quiere profundizar sobre research previo sin duplicar el corpus de sources).

**Rationale**: política simple y predecible es preferible a heurísticas de "find similar notebook" que pueden equivocarse y mezclar contextos. El opt-in para reuso es explícito — user controla.

### D-111-02: Tiers 0-3 in MVP, Tiers 4-5 out

Tier 0 (local) es free, rápido, y crítico para no repetir trabajo. Tier 1 (MCPs gratis) es free porque las 3 fuentes ya están conectadas (Context7, Microsoft Learn, gh search via Bash). Tier 2 (web) es free vía WebSearch/WebFetch built-in. Tier 3 (NotebookLM) es free porque la cuenta del user ya está autenticada (`nlm login`). Tier 4 (academic) requiere integración nueva con arxiv/Semantic Scholar APIs y es nicho. Tier 5 (BYOK enterprise) requiere `ai-eng llm add-provider` interface y trae costos $.

**Rationale**: maximizar valor/complejidad ratio en MVP. Tier 4-5 se añaden cuando hay demanda real medida en telemetría (qué porcentaje de invocaciones falla por insuficiencia de Tiers 0-3).

### D-111-03: Citation hard-rule con `[unsourced]` literal

El output NO permite claims externos sin notación `[N]` o `[unsourced]`. Esto es enforced por validator en `synthesize-with-citations.md` que rechaza outputs sin citas y forza al LLM a re-invocar. `[unsourced]` literal cuando el modelo "rellena" sin fuente — esto es deliberadamente fricción visible para que el lector vea que esa parte del output no tiene grounding.

**Rationale**: Index-RAG citation-first pattern (research findings 2026) muestra que la diferencia entre "research útil" y "hallucination plausible" es la presencia de citas. Hacer la ausencia de cita visible (no oculta) es la forma honesta de reportar incertidumbre. Sin esta regla, el skill produce respuestas que parecen autoritativas pero no son verificables.

### D-111-04: Persistencia automática SOLO si Tier 3 invocado, opt-in para resto

Quick/standard depth raras veces necesitan reuso (son lookups puntuales: "qué versión de pandas soporta Python 3.13"). Deep depth implica research que costó tiempo construir el corpus en NotebookLM — merece artifact archivable. Para casos intermedios donde el user sabe que lo va a reusar, flag `--persist` activa el archivo manualmente.

**Rationale**: evitar generar centenares de artifacts triviales en `.ai-engineering/research/` que ahogan el Tier 0 local. Solo persistir lo que vale la pena reusar.

### D-111-05: Integración con brainstorm via prompt-enhance handler, no via runtime hook

`/ai-brainstorm` invoca `/ai-research` desde su handler `interrogate.md` cuando detecta que la siguiente pregunta requiere evidencia. Esto es explícito en el flujo del skill, no un hook mágico. La spec resultante cita el research artifact via la sección `## References` con prefijo `research:`.

**Rationale**: hook automático sería intrusivo y opaco — el user no sabría cuándo `/ai-brainstorm` está investigando vs interrogando. Invocación explícita en handler es predecible y auditable en transcript.

### D-111-06: Naming pattern `ai-research/<topic-slug>-<YYYY-MM-DD>-<hash6>` para notebooks

`topic-slug` es la query lowercased, alphanumeric + dashes, ≤40 chars (truncate o hash si excede). `<YYYY-MM-DD>` es la fecha de creación. `<hash6>` son los primeros 6 hex chars de SHA-256(query + timestamp_iso). El hash6 evita colisiones cuando user invoca dos veces el mismo día con queries similares (e.g., "react state management" y "react state management 2026"). El prefix `ai-research/` permite filtrar notebooks del framework de notebooks personales en NotebookLM.

**Rationale**: humano-legible (puede grep'earlo) + único + ordenable cronológicamente. El prefix es importante para no contaminar el espacio personal del user.

## Risks

- R-1: **NotebookLM auth puede expirar** durante la sesión — `nlm login` token tiene TTL que el user no controla directamente. Si MCP falla con `auth_expired`, todo Tier 3 cae. _Mitigation_: probe `server_info` al inicio del handler Tier 3; si falla, degrade automático a Tier 2 only + warning visible "NotebookLM auth expired; run `nlm login` to enable deep research"; spec NO bloquea el resto del skill.
- R-2: **`gh search` rate limits** — GitHub API tiene 60 req/h sin auth, 5000 req/h con auth. Heavy usage del Tier 1 puede agotar. _Mitigation_: cache local de `gh search` results en `.ai-engineering/state/cache/gh-search/` con TTL 24h por query exacto; respeta `If-None-Match` headers cuando GitHub los provee.
- R-3: **Citation parsing puede fallar en outputs largos** — el LLM ocasionalmente formatea `[N]` mal (`(N)`, `^N`, `[N=1]`). _Mitigation_: validator es regex tolerante (`\[\d+\]|\[unsourced\]`) PERO si validation falla, skill hace re-invocación con system message endurecido; max 2 retries antes de devolver output con warning "citations malformed".
- R-4: **NotebookLM Deep Research auto-import puede traer sources off-topic** — la feature ingiere sources sin validation manual. _Mitigation_: usar solo el path `source_add` con URLs específicas que recolectamos en Tier 2 (no usar el "Deep Research" feature autónomo); user mantiene control sobre el corpus.
- R-5: **Topic-slug colisiones** entre invocaciones rápidas — dos `/ai-research` consecutivos con queries muy similares pueden generar slugs parecidos. _Mitigation_: hash6 al final del nombre garantiza unicidad; si user quiere reuso explícito, usar `--reuse-notebook=<id>`.
- R-6: **Skill puede inflar context window** del IDE — si Tier 1+2+3 retornan mucho contenido, el LLM agent de síntesis recibe miles de tokens. _Mitigation_: cap por tier (Tier 1: 5 results × 500 tokens = 2.5K; Tier 2: 10 results × 200 tokens = 2K; Tier 3: response del notebook query, max 4K tokens); total cap ~8K tokens en context window.
- R-7: **El `--allowed-domains` / `--blocked-domains`** son flags pasthrough a WebSearch — si el user los confunde, results pueden ser zero. _Mitigation_: warning visible cuando filters dejan zero results; suggest sin filters.

## References

- Industry research 2026 (synthesis from brainstorm web search): Firecrawl "best deep research APIs", Tavily / Exa / Perplexity comparisons, ZenML "steerable deep research" pattern, asinghcsu/AgenticRAG-Survey taxonomy, Index-RAG citation-first paper.
- Existing skill that influences design: `.claude/skills/ai-brainstorm/handlers/interrogate.md` (research-first clause); `/ai-explain` (3-tier depth pattern).
- MCPs disponibles confirmadas: `mcp__context7__*`, `mcp__claude_ai_Microsoft_Learn__*`, `mcp__notebooklm-mcp__*`. WebSearch + WebFetch built-in en Claude Code; Bash para `gh search`.
- v3 ai-engineering ADR-0010 `clear-framework-evals.md` (relacionado pero out of scope: evals miden reliability del agente, research recolecta evidencia).
- Brainstorm session: pregunta 6 (MVP scope tiers); pregunta 6 confirmation (las 4 decisiones adicionales accepted).
- Related specs: spec-110 (governance harvest, no dependencia hard); spec-112 (telemetry foundation, ai-research necesita telemetría limpia para Tier 0 local de framework-events).
