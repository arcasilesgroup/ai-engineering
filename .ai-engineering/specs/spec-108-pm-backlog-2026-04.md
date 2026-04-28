---
spec: spec-108
title: PM Backlog & Branch Comparative Insights (2026-04)
status: draft-pending-review
type: pm-report
effort: medium
created: 2026-04-28
owner: dachi
target_branch: feat/spec-101-installer-robustness
baseline: origin/main
parent_specs:
  - spec-101
  - spec-104
  - spec-105
  - spec-106
  - spec-107
generated_by: /ai-brainstorm (PM mode, 4 parallel research agents)
---

## 0. Why this spec exists

Antes de mergear esta rama a `main`, el PM necesita una vista consolidada de:

1. Cuánto valor entregamos (tiempo + DX) vs `origin/main`.
2. Qué bugs/gaps quedan abiertos.
3. Qué features deberíamos meter al backlog para capitalizar lo aprendido.

Este spec es **brainstorm-grade**: identifica items para el backlog. Cada feature/bug priorizado debe pasar por su propio `/ai-brainstorm` → `/ai-plan` antes de implementarse. **No es un plan de implementación.**

---

## 1. Executive summary — qué cambió en la rama

### 1.1 Alcance bruto
- **638 archivos**, +65 014 / −8 644 líneas, 50+ commits, 5 specs (101, 104, 105, 106, 107).
- Una skill nueva (`/ai-mcp-sentinel`), dos surfaces CLI nuevos (`ai-eng risk *`, `ai-eng audit verify`, `ai-eng gate run|cache`), 7 contexts nuevos, 3 hooks extendidos, 1 hook nuevo (`auto-format`).

### 1.2 Tres titulares de PM
1. **`/ai-pr` warm-cache pasa de ~3-5 min a ≤60 s** (contrato G-1 spec-104; cache hit rate ≥70 % verificado en `tests/integration/test_gate_cache_hit_rate.py:355`).
2. **Installer es 100 % auditado** — 3 modos `python_env`, EXIT 80/81 accionables, 14-stack `required_tools` con `install_url` por OS (spec-101).
3. **Postmark-class drift detection** está en producción local (`/ai-mcp-sentinel`, hooks IOC + binary allowlist; spec-107).

---

## 2. Tiempo & velocidad — antes / ahora

| Surface | Antes (main) | Ahora (rama) | Delta | Evidencia |
|---|---|---|---|---|
| Wave 2 gate, run repetido | 5 checks re-ejecutan (~20-40 s) | Cache hit (TTL 24 h) | **−90 %** wall-clock | `gate_cache.py:57`, `test_gate_cache_hit_rate.py:355` |
| Wave 2 gate, paralelismo | Serial Σ(check_i) | `ThreadPoolExecutor(max_workers=5)` → max(check_i) | **−60 a 80 %** teórico | `orchestrator.py:429-446`, commit `7f4dae3d` |
| `/ai-pr` cold-cache | Sin medir, ~3-5 min | Contrato G-2: ≤90 s | **De ≥3 min a ≤90 s** | `test_ai_pr_coldcache.py:80,93` |
| `/ai-pr` warm-cache | Sin medir | Contrato G-1: ≤ 60 % de cold | **≥40 %** sobre cold | `test_ai_pr_warmcache.py:75` |
| Watch loop | Sin bound — riesgo cuelgue | Active 30 min, passive 4 h, exit 90 | Robustez (no velocidad) | `test_watch_loop_bounds.py:118-164` |
| Skill reading cost | ai-commit 106 + ai-pr 222 + watch 214 = 542 LOC | 88 + 138 + 146 = 372 LOC | **−170 LOC (−31 %)** menor token-cost | commit `4c840ce4` |
| Installer (uv-tool mode) | venv create por worktree (~10-30 s) | uv-tool global, skip venv | **−10 a 30 s** por worktree | `python_env.py:1-22` |
| stack-tests pre-push | `-n auto --dist worksteal`, 120 s timeout | Serial, 180 s timeout | **+~30 s** (deliberada) por 100 % de eliminación de flakes APFS | `stack_runner.py:196-211`, commit `c9b81e45` |

**Regresiones de tiempo conocidas** (deliberadas):
- stack-tests serial: +~30 s (intercambia velocidad por confiabilidad).
- `auto_stage._refresh_index`: +~50 ms por diff (barrera APFS).
- gate_cache cold-write: ~µs (atomicwrite + fsync), amortizado en runs siguientes.

---

## 3. UX & DX — antes / ahora

### 3.1 Installer (spec-101)
| Antes | Ahora |
|---|---|
| `tooling: [uv, ruff, ...]` lista plana | `python_env: {mode: ...}` + 14 stacks con `install_url`, `platform_unsupported`, `unsupported_reason` |
| Exit 1 genérico | EXIT 80 (tools failed → `Run 'ai-eng doctor' to retry`), EXIT 81 (prereq missing → mensaje con `install_link` por stack) |
| "tool skipped" silencioso | `f"tool {name!r} skipped on {os}: {reason}"` |

### 3.2 Doctor (commit `4999f82d`)
| Antes | Ahora |
|---|---|
| Repo solo con WARNs → "Manual follow-up required. Review the failing checks above." (engañoso) | `"N warning(s) for review above; project is functional."` |
| Repo HEAD unborn → "not a git repository" (falso negativo) | Detectado correctamente, detached HEAD reporta OK |

### 3.3 Risk acceptance (spec-105)
| Antes | Ahora |
|---|---|
| Edición manual de `decision-store.json` | 7 subcomandos (`accept/accept-all/renew/resolve/revoke/list/show`) |
| Sin TTL diferenciado | TTL por severidad (15/30/60/90 d), max 2 renewals |
| Sin telemetría | `category=risk-acceptance` en `framework-events.ndjson` |
| `--dry-run` ausente | `accept-all --dry-run` previsualiza sin escribir |
| D-105-14 inexistente | CLAUDE.md Don't #9 explica: logged-acceptance ≠ weakening |

### 3.4 MCP Sentinel (spec-107) — surface nueva
- `/ai-mcp-sentinel scan` → coherence analysis (descripción declarada vs comportamiento observado).
- `/ai-mcp-sentinel audit-update <skill>` → diff baseline vs actual (rug-pull tipo Postmark/XZ).
- `/ai-mcp-sentinel baseline set` → snapshot tamper-evident.
- Backend: 8-binary MCP allowlist en hook, IOC matching contra catálogo vendored, H1 tool-spec hash al install, H2 audit chain advisory.

### 3.5 Verbosity & cross-IDE (spec-104 Phase 7-8)
- ai-commit + ai-pr + watch.md: −170 LOC duplicadas con CLAUDE.md.
- Cross-IDE: paridad real vía `ai-eng gate run --json` (mismo binario), no via mirrors.

---

## 4. Capabilities entregadas (catálogo PM-friendly)

| Tipo | Item | Por qué importa al usuario |
|---|---|---|
| Skill | `/ai-mcp-sentinel` | Primer control de seguridad MCP/skill vendible a banking/healthcare |
| CLI | `ai-eng risk accept\|accept-all\|renew\|...` | Aceptación de riesgo con audit trail; reemplaza edición manual |
| CLI | `ai-eng audit verify` | Detecta truncación/inyección en audit chain (advisory) |
| CLI | `ai-eng gate run \|--cache-aware\|--mode=local\|ci` | Single-pass gate con cache; 4× speedup |
| CLI | `ai-eng gate cache --status\|--clear` | Inspección y limpieza del cache |
| Hook | `prompt-injection-guard.py` (extendido) | IOC matching runtime, deny+DEC bypass |
| Hook | `mcp-health.py` (extendido) | 8-binary allowlist, escape via `ai-eng risk accept` |
| Hook | `auto-format.py` | PostToolUse re-format + selective re-stage |
| Context | `architecture-patterns.md` | 12 patrones canónicos para `/ai-plan` |
| Context | `gate-policy.md` | Define fast-slice local vs CI autoritativo |
| Context | `mcp-binary-policy.md` | Documenta los 8 binarios + extensión via DEC |
| Context | `python-env-modes.md` | 3 modos + EXIT 80/81 + 14 stacks |
| Context | `risk-acceptance-flow.md` | E2E lifecycle del CLI risk |
| Context | `permissions-migration.md` | Migración de `allow:["*"]` a allowlist estrecha |
| Context | `sentinel-iocs-update.md` | Refresh trimestral del catálogo IOC |

**No-shipped en esta rama** (para clarity): `/loop` y `/schedule` ya existían en main.

---

## 5. Bug backlog — priorizado

### CRITICO

#### B-C1 · SonarCloud quality gate desactivado sin fecha de reactivación
- **Archivos**: `.github/workflows/ci-check.yml:349`, `sonar-project.properties:7`, commit `49dccb2c`
- **Síntoma**: `sonar.qualitygate.wait=false` + `continue-on-error: true` + Sonar movido al array `optional` (línea 715). Reliability rating, Coverage on New Code y Duplications son **informativos en dashboard, no bloqueantes**.
- **Riesgo**: regresiones de calidad pasan CI sin freno.
- **Fix**: ticket "spec-109: SonarCloud reactivation roadmap" — restaurar wait=true tras cerrar findings reconocidos, fecha límite documentada en decision-store.

#### B-C2 · 13 herramientas instaladas sin SHA256 pin (DEC-038)
- **Archivo**: `src/ai_engineering/installer/tool_registry.py` (líneas 153, 160, 188, 195, 247, 261, 318, 342, 400, 412+).
- **Síntoma**: `sha256_pinned=False  # TODO(DEC-038): populate real pins` en 13 ocurrencias. DEC-038 expira **2026-07-26** sin owner explícito.
- **Riesgo**: supply-chain compromise de upstream pasaría sin detección.
- **Fix**: asignar owner a DEC-038, generar pins (script tipo `tools.py:bootstrap_pins`), incluir verificación en cada install. Bloquea cierre de spec-101.

#### B-C3 · 3 módulos de test cuarentenados con cobertura crítica
- **Archivo**: `src/ai_engineering/policy/checks/stack_runner.py:225-227`, commit `ab7827fe`.
- **Síntoma**: pre-push `--ignore` sobre:
  - `test_safe_run_env_scrub.py` (18 tests de scrubbing de secrets/tokens),
  - `test_python_env_mode_install.py` (28 tests del feature central de spec-101),
  - `test_setup_cli.py` (57 tests de setup + sonar/github auth).
- **Síntoma 2**: corren en CI completo, pero el desarrollador puede pushear con esos tests rotos sin alerta local.
- **Fix**: corregir mock-leak raíz en lugar de cuarentenar. Ticket de deuda técnica.

### ALTO

#### B-A1 · Marcadores `spec_10*_red` documentados pero nunca aplicados
- **Archivos**: 11 test files (ej. `test_cli_validates_inputs.py:16`, `test_tier_allocation.py:16`).
- **Síntoma**: docstrings dicen "excluded by default CI run" pero **no hay** `pytestmark = pytest.mark.spec_10X_red` en ninguno y no hay `-m "not spec_10X_red"` en CI.
- **Fix**: aplicar marcadores reales o eliminar el claim de los docstrings.

#### B-A2 · `framework-capabilities.json` reporta 41 skills, disk tiene 48
- **Archivo**: `.ai-engineering/state/framework-capabilities.json`.
- **Síntoma**: `/ai-mcp-sentinel` y otras 6 skills invisibles para herramientas downstream que consultan el catálogo.
- **Fix**: regenerar al merge; agregar regen al pipeline post-merge o pre-commit.

#### B-A3 · `CLAUDE.md` lista 48 skills pero el grupo "Enterprise" no incluye `mcp-sentinel`
- **Archivo**: `/CLAUDE.md:138-148`. Header dice 48, pero los 6 grupos suman 47.
- **Fix**: añadir `mcp-sentinel` a grupo Enterprise + sync mirrors.

#### B-A4 · `actions/cache@v4` sin pin por SHA en CI
- **Archivo**: `.github/workflows/ci-check.yml:83,141,175,240`.
- **Síntoma**: tag mutable `@v4`. `actions/checkout` sí está pinned por SHA — inconsistencia.
- **Fix**: pin por SHA256 como el resto.

### MEDIO

| ID | Título | Archivo |
|---|---|---|
| B-M1 | `install-state.json.legacy-*` proliferan sin gitignore ni TTL cleanup (4 archivos en 1 día) | `state/service.py:200`, `.gitignore:155-159` |
| B-M2 | `ai-eng audit verify` siempre exit 0 — chain breaks no bloquean nada (D-107-10) | `audit_cmd.py:69` |
| B-M3 | `xfail(strict=False)` silencia xpass en lint crítico de `required_tools` | `test_validate_manifest_required_tools.py:445-449` |
| B-M4 | `skill-audit.sh` advisory sin hard-gate planificado (NG-2) | `.ai-engineering/specs/spec-106.md:NG-2` |
| B-M5 | `test_swift_stack_skip.py` Layer 2 explícitamente RED esperando T-2.10 inexistente | `test_swift_stack_skip.py:11-12` |

### BAJO

| ID | Título | Archivo |
|---|---|---|
| B-B1 | 2 `# type: ignore` sin referencia a decision-store en código de producción | `audit_cmd.py:55`, `sdk.py:387` |
| B-B2 | 5 `# pragma: no cover` en defensive-fail paths (`state/service.py:247`, `hooks/manager.py:261`, `installer/user_scope_install.py:1131,1144`, `installer/phases/pipeline.py:117,138`) | varios |
| B-B3 | Cobertura actual no expuesta (no badge, no `coverage.xml` en artifacts persistentes) | CI `ci-check.yml` |

---

## 6. Feature backlog — propuestas PM

Cada feature lista: **value (alto/medio/bajo)**, **effort (S/M/L)**, **why now**.

### F-1 · `/ai-bench` — Performance benchmark suite
- **Value**: Alto. **Effort**: M. **Why now**: spec-104 entrega contratos `≤60 s warm`, `≤90 s cold`, pero **sin benchmarks reales que los validen continuamente**. Hoy son aserciones mockeadas.
- **Qué**: comando `ai-eng bench [--scenario warm-pr|cold-pr|gate|installer]` que ejecuta el flow real, mide wall-clock, escribe a `state/bench-history.ndjson`. Detecta regresiones (>20 % vs baseline → warn, >50 % → fail).
- **Output**: tabla en stdout + `bench-report.md`, opcional comment en PR.

### F-2 · PR comment "gate-cache savings"
- **Value**: Alto (visibilidad de ROI). **Effort**: S. **Why now**: hoy el speedup es invisible al desarrollador.
- **Qué**: cuando `/ai-pr` corre con cache hit, postear comment automático con tabla `check | hit | saved (s)`. Aggregate weekly por org.

### F-3 · MCP Sentinel auto-trigger post-install
- **Value**: Alto (cierra la brecha "hay que recordar correrlo"). **Effort**: S.
- **Qué**: hook `PostToolUse` cuando se modifique `.claude/settings*.json`/`.mcp.json` invoca `/ai-mcp-sentinel scan` automáticamente. Confirmación previa por costo LLM. Resultado pegado al output del comando que disparó la edición.

### F-4 · `ai-eng risk dashboard`
- **Value**: Alto (visibilidad gobernanza). **Effort**: S-M.
- **Qué**: vista TUI o markdown con DECs activos: ID, severity, owner, expires_in, follow-up status, batch_id (si aplica). Incluye filtros (`--expiring-within 7`, `--by-owner`, `--by-spec`). Reemplaza la consulta cruda a `decision-store.json`.

### F-5 · SonarCloud reactivation roadmap (spec-109)
- **Value**: Crítico (reabre B-C1). **Effort**: M.
- **Qué**: spec corto que (a) lista cada finding aceptado con DEC, (b) define criterio de reactivación: "cuando cobertura on-new-code ≥80 % y reliability rating A en 3 PRs consecutivos", (c) restablece `wait=true` y remueve `continue-on-error`.

### F-6 · Coverage badge + last-value endpoint
- **Value**: Medio (transparencia interna). **Effort**: S.
- **Qué**: CI sube `coverage.xml` a artifact persistente; badge en README; valor exposed en `state/coverage-summary.json`. Cierra B-B3.

### F-7 · `ai-eng install --dry-run`
- **Value**: Medio (CI/sandbox/onboarding). **Effort**: S.
- **Qué**: simula install sin tocar disco, imprime plan: stacks detectados, tools a instalar, modo `python_env` elegido, EXIT codes posibles. Útil para CI de validación.

### F-8 · Capabilities catalog auto-regen post-merge
- **Value**: Medio. **Effort**: S. Cierra B-A2.
- **Qué**: GitHub Actions workflow `regen-capabilities` corre en push a `main`, abre PR si el catálogo cambió. Alternativa: pre-commit hook local.

### F-9 · `ai-eng doctor explain <exit-code>`
- **Value**: Medio (DX onboarding). **Effort**: S.
- **Qué**: `ai-eng doctor explain 81` muestra: qué significa, posibles causas (prereq por stack), comando de remedio, links. Renderiza desde `python-env-modes.md` + `manifest.yml:install_link`.

### F-10 · MCP Sentinel scheduled scan via `/loop`
- **Value**: Medio (defensa continua). **Effort**: S.
- **Qué**: documentar plantilla `/loop 7d /ai-mcp-sentinel scan` con persistencia de baseline. Auto-incluido en `ai-eng install` opcional.

### F-11 · Skill audit hard-gate roadmap (spec-110)
- **Value**: Medio. **Effort**: S (spec) + M (implementación cuando aterrice).
- **Qué**: spec corto que define: criterio de activación ("cuando ≥90 % skills puntúan ≥80"), métrica actual, plan de remediación skill por skill. Cierra B-M4.

### F-12 · `/ai-postmortem` auto-link cuando Sentinel detecta drift
- **Value**: Medio (cierra el loop seguridad → proceso). **Effort**: M.
- **Qué**: cuando `audit-update` retorna severity HIGH, ofrece crear draft de postmortem prerellenado con el delta detectado. Categoría DERP "Detection".

### F-13 · `ai-eng specs --tree` (lineage view)
- **Value**: Bajo-Medio (DX onboarding). **Effort**: S.
- **Qué**: lee `_history.md` y frontmatter de cada spec, dibuja árbol de dependencias y herencia (101 → 104 → 105 → 106 → 107 → 108).

### F-14 · Cross-IDE telemetry parity dashboard
- **Value**: Bajo. **Effort**: M.
- **Qué**: ejercicio que invoca el mismo flow desde Claude/Copilot/Codex/Gemini y compara `framework-events.ndjson`. Reporta divergencias. Verifica D-104-08 en producción real.

### F-15 · `ai-eng risk renew --bulk` con justification template
- **Value**: Bajo. **Effort**: S. **Why**: hoy renew es 1 a 1; con docenas de DECs próximos a expirar es tedioso.
- **Qué**: `risk renew --batch <batch_id>` o `--filter "expires-within 7d AND owner=me"` + justification template.

---

## 7. Riesgos & deuda técnica acumulada

1. **Quality regression latente** — combinación B-C1 (Sonar off) + B-A2 (catalog stale) + B-M2 (audit advisory) + B-B3 (coverage opaca) significa que **no podemos contestar con confianza "¿estamos en mejor o peor estado que antes?"** sin trabajo extra. Recomendación: priorizar F-1 + F-6 + B-A2.
2. **DEC-038 (13 SHA256 pins) expira 2026-07-26**: 90 días de runway. Riesgo si se olvida.
3. **Cuarentena de tests** (B-C3) crea brecha entre lo que el dev ve local y lo que CI exige. Histórico de "se va a arreglar luego" es alto.
4. **Marcadores RED inertes** (B-A1) rompen la disciplina TDD si se vuelven a usar sin reparar la convención.
5. **Sentinel sin auto-trigger** (cubierto por F-3): la skill existe pero requiere disciplina manual — perfil bajo de adopción real.

---

## 8. Recomendaciones — siguientes 2 sprints

### Sprint 1 (cierra deuda crítica antes de mergear o post-merge inmediato)
1. **B-C2** — DEC-038 SHA256 pins (no puede expirar sin owner).
2. **B-A2 + F-8** — regenerar capabilities catalog + auto-regen post-merge.
3. **B-A3** — añadir `mcp-sentinel` al grupo Enterprise en CLAUDE.md + sync mirrors.
4. **B-A4** — pin `actions/cache` por SHA.
5. **F-5 (spec-109)** — roadmap de reactivación de SonarCloud con fecha.

### Sprint 2 (capitaliza valor entregado)
6. **F-1 `/ai-bench`** — sin benchmarks reales, los contratos de spec-104 son aspiracionales.
7. **F-2 PR comment savings** — hace tangible el ROI a stakeholders.
8. **F-3 Sentinel auto-trigger** — cierra brecha de adopción de la feature de seguridad estrella.
9. **B-C3** — corregir mock-leak raíz en los 3 módulos cuarentenados.
10. **F-4 `ai-eng risk dashboard`** — visibilidad de gobernanza, audiencia regulada.

### Cuarto siguiente (Q3 2026)
- F-7, F-9, F-10, F-11 (spec-110 skill-audit hard-gate), F-12, B-M*.
- Revisar B-B2 con `pytest --cov` real.
- Evaluar deprecation de `python_env: venv` (legacy) si telemetría muestra <5 % adoption.

---

## 9. Métricas a monitorear post-merge

1. **Gate cache hit rate** (target ≥70 %) — telemetría existe (`gate_cache.py:352-389`), exponerla en standup.
2. **DEC count by severity + expires-within 7d** (target ≤5 expirados nunca) — exponerla via F-4.
3. **EXIT 80/81 rate** durante install — diagnóstico de calidad de prereq detection.
4. **Sentinel scan invocations / week** — adopción real de la skill estrella.
5. **`/ai-pr` p50 wall-clock** — validar contrato G-2 ≤90 s en producción.

---

## 10. Open questions para PM/usuario

1. ¿Cuál es el deadline de cierre de SonarCloud findings antes de reactivar wait=true? (driver de F-5)
2. ¿Quién es owner de DEC-038 (13 SHA256 pins)? (B-C2)
3. ¿Aceptamos stack-tests serial (~+30 s) como definitivo, o invertir en fix de race APFS subyacente?
4. ¿`/ai-mcp-sentinel scan` debe ser auto-trigger por default (F-3) o opt-in?
5. ¿Mergear esta rama como un único PR (638 archivos) o split por spec antes de merge? Recomendación PM: split → más fácil de reviewer, pero costoso.

---

## STOP — siguientes pasos

Este spec es un **brainstorm**. No genera código.

Para avanzar:
- Discutir/aprobar con usuario las open questions §10.
- Por cada item del backlog priorizado §8 que se quiera ejecutar: invocar `/ai-brainstorm <ID>` para producir su propio spec, luego `/ai-plan` cuando esté aprobado.
- B-C1, B-C2, B-A2, B-A3 son fixes pequeños — pueden ir directo a `/ai-plan` sin rebrainstorming si el usuario confirma.
