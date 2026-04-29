---
spec: spec-110
title: Governance v3 Harvest — CONSTITUTION + AGENTS.md Cross-IDE + Supply Chain + Dual-Plane MVP
status: approved
effort: large
refs:
  - .ai-engineering/specs/_history.md
  - .ai-engineering/specs/spec-109-installer-first-install-robustness.md
  - .claude/skills/ai-constitution/SKILL.md
  - .claude/skills/ai-governance/SKILL.md
  - src/ai_engineering/state/audit_chain.py
  - src/ai_engineering/templates/project/AGENTS.md
  - src/ai_engineering/templates/project/CLAUDE.md
  - src/ai_engineering/templates/project/GEMINI.md
  - src/ai_engineering/templates/project/copilot-instructions.md
---

# Spec 110 — Governance v3 Harvest

## Summary

`ai-engineering` carece de constitución formalizada como "primera ley" no-negociable: las reglas duras viven dispersas en `CLAUDE.md > Don't` (9 prohibiciones) y en frontmatter de skills, lo que permite drift entre IDEs y dificulta auditoría. La auditoría del experimento `ai-engineering-v3` (alpha 27 abr 2026) revela 4 patrones que aplican al current sin requerir rewrite arquitectónico: (1) **CONSTITUTION.md** con 10 artículos como contrato no-negociable consumido en Step 0 por toda skill/agent — ya tenemos `/ai-constitution` skill que genera el doc pero el contenido v3-style nunca se ha producido; (2) **AGENTS.md como entry point canónico cross-IDE** alineado con el open standard adoptado en abril 2026 por Codex CLI (`developers.openai.com/codex/guides/agents-md`), Cursor, Claude Code y Gemini CLI — actualmente tenemos `AGENTS.md` como template en `src/ai_engineering/templates/project/AGENTS.md` pero NO como entry point real con la lógica de Step 0, available skills y hard rules unificadas; `CLAUDE.md`, `GEMINI.md`, `copilot-instructions.md` duplican reglas en lugar de delegar a AGENTS.md; (3) **Supply chain hardening del framework propio** — los workflows en `.github/workflows/*.yml` usan `uses: actions/checkout@v4` (mutable tag) en lugar de SHAs inmutables, no generan SBOM CycloneDX en CI, y cualquier `npm install` o `bun install` en CI no pasa `--ignore-scripts` (vector Shai-Hulud 2.0 documentado en NotebookLM cybersec briefing 2026); (4) **Hash-chain del audit log existe parcialmente**: `state/audit_chain.py` ya escribe `prev_event_hash` pero solo el 16.3% de los 15,393 eventos en `framework-events.ndjson` lo contienen, y vive en `detail.prev_event_hash` (anidado) en lugar de raíz, lo que dificulta validación end-to-end y bloquea el cumplimiento del Article III del v3 ("immutable audit log"). spec-110 importa selectivamente del v3 SIN adoptar piezas que requieren marketplace (descartado), Identity Broker (deferido), Input Guard ML-based (deferido) ni OTel exporter (deferido): formaliza CONSTITUTION.md vía `/ai-constitution` con 10 artículos adaptados al current scale; promueve AGENTS.md a entry point canónico con `CLAUDE.md`/`GEMINI.md`/`copilot-instructions.md` como overlays minimales que delegan; aplica SHA-pinning + SBOM + ignore-scripts a los workflows del framework; extiende hash-chain SHA-256 al 100% de eventos en raíz del evento. Beneficio medible: cualquier skill/agent puede leer `CONSTITUTION.md` para Step 0 con reglas idénticas en los 4 IDEs; auditoría externa puede validar hash-chain del NDJSON con un solo comando; CI bloquea actions con SHA mutable; dependencias internas de bun/npm en CI no ejecutan post-install scripts maliciosos.

## Goals

- G-1: `CONSTITUTION.md` existe en root del proyecto con 10 artículos numerados (I-X) generados vía `/ai-constitution`. Contenido adaptado al current (no marketplace, sí spec-driven + TDD + dual-plane MVP). Verificable por `tests/integration/test_constitution_present.py::test_constitution_has_all_articles` que valida presencia de cada Article I-X y que cada uno tenga al menos un `1.` numbered rule.
- G-2: `AGENTS.md` en root es el entry point canónico cross-IDE: contiene Step 0 instructions, available skills table (con triggers), agents list, hard rules (referenciando CONSTITUTION.md). `CLAUDE.md`, `.gemini/GEMINI.md` (o `GEMINI.md` root), `.github/copilot-instructions.md` y `.codex/AGENTS.md` (si existe) son overlays que (a) referencian AGENTS.md explícitamente con un link relativo, y (b) NO duplican las hard rules — solo añaden specifics del IDE. Verificable por `tests/integration/test_entry_points_consistency.py::test_overlays_reference_agents_md` que parsea cada overlay y confirma presencia de link a `AGENTS.md` y ausencia de duplicación de las 9 hard rules de CONSTITUTION.
- G-3: Todos los `uses:` en `.github/workflows/*.yml` apuntan a un SHA hex de 40 caracteres (no `@v1`, `@main`, no tag mutable). Excepción permitida: actions del propio org `arcasilesgroup` (self-references). Verificable por `tests/integration/test_workflow_sha_pinning.py::test_all_actions_pinned_to_sha` que parsea cada workflow YAML y aplica regex `^[a-f0-9]{40}$` a cada `uses:` no-self-ref.
- G-4: CI workflow `.github/workflows/sbom.yml` (nuevo) genera `sbom.cdx.json` en formato CycloneDX 1.6 vía `cyclonedx-py environment` para Python deps + `cyclonedx-bun` (o equivalente) para Bun/npm si aplica, y sube el archivo como artifact `sbom-${{ github.sha }}`. Workflow corre en cada PR + push a main. Verificable por presencia del workflow file + `tests/integration/test_sbom_workflow.py::test_sbom_artifact_uploaded_in_pr` (test que mockea action env vars).
- G-5: Cualquier paso de CI que use `npm`, `bun`, `pnpm` o `yarn install` pasa `--ignore-scripts` o equivalente. Verificable por `tests/integration/test_ignore_scripts_in_ci.py::test_no_install_without_ignore_scripts` que parsea workflows y aplica regex.
- G-6: Hash-chain SHA-256 al 100% de eventos en `framework-events.ndjson`. Cada evento incluye `prev_event_hash` en raíz del JSON (no `detail.prev_event_hash`). `src/ai_engineering/state/audit_chain.py` se extiende con (a) `compute_event_hash(event_dict) -> str` que serializa canonicalmente y aplica SHA-256, (b) reader `iter_validate_chain(path) -> Iterator[ValidationResult]` que valida integridad end-to-end. Migración: durante 30 días post-spec, `audit_chain.read_event` lee tanto raíz como `detail.prev_event_hash` con warning log; tras 30 días, solo raíz. Verificable por `tests/unit/state/test_audit_chain.py::test_validate_chain_integrity` con fixtures (chain válida, chain con tampering, chain con missing event).
- G-7: 3 policy files Rego-style en `.ai-engineering/policies/` (creado): `branch_protection.rego`, `commit_conventional.rego`, `risk_acceptance_ttl.rego`. Cada uno contiene `package <name>` + `default allow := false` + reglas explícitas. Evaluador local Python en `src/ai_engineering/governance/policy_engine.py` (nuevo) que parsea sintaxis Rego restringida (subset: `package`, `default`, `allow if`, `deny if`, basic comparisons) sin requerir OPA daemon externo. `/ai-governance` skill consume el evaluator. Verificable por `tests/unit/governance/test_policy_engine.py::test_<policy>_pass_and_fail_cases` con 6 casos (2 por policy: allow + deny).
- G-8: `docs/anti-patterns.md` documenta las 3 formas de fracasar del deck Codemotion Madrid 2026-04 slide 32 (Portal ≠ plataforma · Proyecto ≠ producto · Mandato ≠ adopción) aplicadas a ai-engineering. Verificable por presencia del archivo + lint de markdown (3 secciones h2).
- G-9: 0 secrets, 0 vulnerabilities (gitleaks + pip-audit), 0 lint errors (ruff) introducidos por este spec.
- G-10: Coverage ≥80% en módulos nuevos: `src/ai_engineering/governance/policy_engine.py`, extensiones a `src/ai_engineering/state/audit_chain.py`. Validado por `pytest --cov`.

## Non-Goals

- NG-1: Identity Broker / OBO tokens / OAuth scope-per-action. Defer indefinidamente — no aplica sin marketplace ni multi-tenant.
- NG-2: Input Guard ML-based con detección PII via embeddings. Mantenemos `prompt-injection-guard.py` actual basado en regex; cualquier mejora ML va en spec separado.
- NG-3: OTel exporter desde day-zero (OTLP). NDJSON sigue siendo fuente de verdad; OTel es aditivo y se añade post-spec si hay demanda externa.
- NG-4: Marketplace de plugins 3-tier (OFFICIAL/VERIFIED/COMMUNITY) con Sigstore + SLSA + SBOM + Scorecard. Descartado por user en pregunta 2 del brainstorm; supply chain en este spec aplica SOLO al framework mismo, no a un futuro ecosistema de plugins.
- NG-5: Regulated industry profiles (banking/healthcare/fintech/airgapped). Defer.
- NG-6: TrueFoundry / LiteLLM bridge para BYOK CI. Subscription piggyback se documenta en CONSTITUTION (Article IV) pero sin implementación BYOK.
- NG-7: Rewrite a TypeScript+Bun. El framework permanece Python-only; la opción TS+Python hybrid es del v3 experimental.
- NG-8: Hexagonal architecture / bounded contexts / DDD layers. Confirmed out por user en pregunta 4.
- NG-9: Skill consolidación 49 → ~33 ni agent reduction 26 → 7. Defer a spec-113 tras ≥14 días de datos limpios post-spec-112.
- NG-10: PR creation in this spec.

## Decisions

### D-110-01: 10 artículos adaptados al current, no copiados verbatim del v3

`/ai-constitution` genera CONSTITUTION.md con los 10 artículos del v3 PERO el contenido se adapta al current scale: Article III (Dual-Plane Security) lista solo OPA policy engine + immutable audit log + injection-guard hook (sin Identity Broker ni Input Guard ML); Article IV (Subscription Piggyback) documenta el patrón pero no requiere BYOK CI; Article VI (Supply Chain Integrity) aplica SOLO al framework propio (no a plugins, que están out-of-scope); el resto (I/II/V/VII/VIII/IX/X) se adoptan con mínimo cambio.

**Rationale**: copiar verbatim del v3 introduce contradicciones — el v3 menciona marketplace, Identity Broker, TrueFoundry y BYOK que no aplican al current. Adaptar evita un CONSTITUTION inconsistente con el código real.

### D-110-02: AGENTS.md como single source of truth, otros como overlays

`AGENTS.md` en root contiene la lógica completa de Step 0 (read CONSTITUTION → read manifest → no-implementation-without-spec), tabla de skills (con triggers), tabla de agents, hard rules (referenciando CONSTITUTION). `CLAUDE.md`, `GEMINI.md` (o `.gemini/GEMINI.md`), `.github/copilot-instructions.md`, `.codex/AGENTS.md` (si Codex requiere su propio path) son overlays minimales: link relativo a `AGENTS.md` + sección de specifics del IDE (e.g., Claude hooks config, Gemini stdin/stdout JSON contract, Copilot agent skills format).

**Rationale**: el AGENTS.md open standard fue adoptado por los 4 IDEs principales en abril 2026 (Codex CLI lo confirma como entry point primario); duplicar reglas crea drift inevitable. Mantener una source y delegar es la práctica que el v3 ya aplica.

### D-110-03: Hash-chain en raíz del evento, con migración de 30 días

`prev_event_hash` se escribe en la raíz del JSON event a partir de spec-110 merge. Lectores tienen un periodo de migración de 30 días: `audit_chain.read_event` busca primero en raíz, fallback a `detail.prev_event_hash` con `logger.warning("legacy hash location detected, migrate by date X")`. Tras 30 días, fallback se elimina. La parte ya escrita en `detail.prev_event_hash` (2,509 eventos) se preserva tal cual — la migración aplica solo a eventos nuevos. Si spec-112 ejecuta el reset del NDJSON dentro del periodo, el legacy fallback se elimina al hacer el reset.

**Rationale**: 16.3% de eventos legacy + nueva escritura en raíz = soporte dual durante migración. Si spec-112 resetea el NDJSON antes que termine el periodo, el problema se evapora limpiamente; si no, 30 días es suficiente para que cualquier consumidor externo se actualice.

### D-110-04: Policy files Rego-style con evaluator Python local, NO daemon OPA externo

`.ai-engineering/policies/*.rego` contiene archivos en Rego restringido (subset: `package`, `default`, `allow if`, `deny if`, comparaciones básicas). El evaluator vive en `src/ai_engineering/governance/policy_engine.py` y parsea sintaxis sin invocar `opa eval` (binary externo). Tres policies MVP: `branch_protection.rego` (no push a main/master), `commit_conventional.rego` (subject pattern `<type>(<scope>): <subject>`), `risk_acceptance_ttl.rego` (TTL no expirado).

**Rationale**: instalar OPA daemon (descarga ~30MB, requiere binary distribution multi-OS) es overkill para 3 policies. Un parser Python de subset Rego es ~150 LOC, evaluable en <1ms, portable. Si el set crece a docenas de policies o requiere lógica compleja (joins, recursion), se migra a OPA real en spec futuro.

### D-110-05: Supply chain hardening solo del framework propio

SHA-pinning + SBOM + `--ignore-scripts` aplica a `.github/workflows/*.yml` del repo `arcasilesgroup/ai-engineering`. NO aplica a workflows de proyectos que usen ai-engineering (eso lo hereda cada proyecto en su propia CI). NO aplica a un futuro marketplace (out of scope).

**Rationale**: el alcance del spec es el framework, no su ecosistema. Aplicar reglas a downstream sería overreach y queda como ejemplo en `docs/` (best practice, no enforcement).

### D-110-06: docs/anti-patterns.md como artefacto cultural

`docs/anti-patterns.md` documenta las 3 formas de fracasar del deck con framing aplicado al framework: "Portal ≠ plataforma" → "Hooks instalados ≠ enforcement"; "Proyecto ≠ producto" → "Skill registrada ≠ skill mantenida"; "Mandato ≠ adopción" → "CLAUDE.md obligatorio ≠ developer la lee". Sin código asociado — es documentación deliberadamente cultural.

**Rationale**: el deck identifica patrones de fracaso del platform engineering; aplicarlos al framework como espejo crítico ayuda a auto-corregir antes de que ocurran. Costo: un archivo Markdown.

## Risks

- R-1: **Migrar hash-chain a raíz puede romper consumers externos** que parseen `framework-events.ndjson` esperando `detail.prev_event_hash`. _Mitigation_: dual-read durante 30 días con warning log; documentar el cambio en `CHANGELOG.md`; si spec-112 resetea NDJSON dentro del periodo (probable), la migración se simplifica.
- R-2: **AGENTS.md vs CLAUDE.md duplicación residual** — refactorizar overlays mal puede dejar reglas inconsistentes (ej: una regla en CLAUDE.md no en AGENTS.md). _Mitigation_: `/ai-platform-audit` skill existente detecta duplicación y discrepancias; correrlo como gate post-merge.
- R-3: **SHA-pinning rompe CI cuando una action upstream se actualiza** — si dependabot no está habilitado, las actions se quedan obsoletas. _Mitigation_: añadir `.github/dependabot.yml` con schedule weekly para `github-actions` ecosystem (nuevo en este spec si no existe).
- R-4: **Policy engine subset Rego es incompleto** — algunas policies del v3 quizá usen `import data.<x>` u otras features no soportadas en MVP. _Mitigation_: scope a 3 policies simples; cualquier policy futura que requiera Rego full triggerea migración a OPA daemon.
- R-5: **`--ignore-scripts` rompe instalaciones legítimas** — algunos paquetes Bun/npm requieren post-install scripts (e.g., compiling native bindings). _Mitigation_: el framework no usa Bun/npm en runtime; solo en algunos templates / docs. Si encontramos paquete legítimo que rompe, lo whitelist'eamos en config explícita.
- R-6: **CONSTITUTION.md adaptado puede divergir del v3** y crear confusión cuando el v3 madure. _Mitigation_: documentar en CONSTITUTION footer "adapted from ai-engineering-v3 alpha 0.0; may diverge as v3 evolves"; spec separado para sync futuro si v3 alcanza GA.

## References

- Brainstorm session: research multi-fuente sobre `ai-engineering-v3` (alpha 27 abr 2026), deck Codemotion Madrid 2026-04 (`/Users/soydachi/repos/arcasiles-events/data/decks/codemotion-madrid-2026-04/deck.pptx`), NotebookLM cybersec briefing 2026 (notebook `ab8b9f75-f355-4a8f-8859-24a38c4cc5f7`).
- v3 ADRs consultados: `0001-hexagonal-architecture.md` (no adoptado), `0002-dual-plane-architecture.md` (MVP adoptado), `0005-subscription-piggyback.md` (documentado en Article IV), `0006-plugin-3-tier-distribution.md` (no adoptado), `0009-otel-from-day-zero.md` (deferido).
- v3 CONSTITUTION fuente: `/Users/soydachi/repos/ai-engineering-v3/CONSTITUTION.md` (10 artículos referencia).
- AGENTS.md open standard: `developers.openai.com/codex/guides/agents-md`.
- Codex CLI hooks (estables abril 2026): `developers.openai.com/codex/hooks`.
- Gemini CLI hooks (v0.26.0+): `geminicli.com/docs/hooks/`.
- VS Code Copilot agent hooks (preview): `code.visualstudio.com/docs/copilot/customization/hooks`.
- Related specs: spec-109 (installer robustness — base estable); spec-111 (próximo en cadena, ai-research skill); spec-112 (próximo en cadena, telemetry foundation).
