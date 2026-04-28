---
spec: spec-112
title: Telemetry Foundation — Fix + Cross-OS + Multi-IDE Unified + Reset + DRY + Hot-Path SLO + Clean Code Audit
status: approved
effort: large
refs:
  - .ai-engineering/specs/spec-110-governance-v3-harvest.md
  - .ai-engineering/specs/spec-111-ai-research-skill.md
  - .ai-engineering/specs/spec-109-installer-first-install-robustness.md
  - .ai-engineering/scripts/hooks/telemetry-skill.py
  - .ai-engineering/scripts/hooks/prompt-injection-guard.py
  - .ai-engineering/scripts/hooks/instinct-observe.py
  - .ai-engineering/scripts/hooks/instinct-extract.py
  - .ai-engineering/scripts/hooks/observe.py
  - .ai-engineering/scripts/hooks/mcp-health.py
  - .ai-engineering/scripts/hooks/strategic-compact.py
  - .ai-engineering/scripts/hooks/auto-format.py
  - .ai-engineering/scripts/hooks/_lib/
  - .claude/settings.json
  - .codex/hooks.json
  - .gemini/settings.json
  - src/ai_engineering/state/audit_chain.py
  - src/ai_engineering/state/observability.py
---

# Spec 112 — Telemetry Foundation

## Summary

La telemetría actual de `ai-engineering` tiene 5 fallos verificados que invalidan cualquier audit basado en datos: (1) **Bug de captura en `telemetry-skill.py`**: el hook registrado en `.claude/settings.json` con `UserPromptSubmit matcher='/ai-'` debería capturar el nombre del skill desde el prompt, pero `detail.skill` contiene literalmente `"ai-engineering"` (nombre del proyecto, no del skill) — auditoría de los 196 eventos `skill_invoked` en 32 días (27 mar → 28 abr 2026) confirma que TODOS muestran `detail.skill="ai-engineering"`, lo que significa que durante un mes no hemos sabido qué skills se invocaron realmente; (2) **Multi-IDE NO unificado**: en abril 2026 los 4 IDEs principales tienen hook systems estables (`.claude/settings.json` Claude Code, `.codex/hooks.json` Codex CLI estable desde abril 2026, `.gemini/settings.json` Gemini CLI desde v0.26.0+, VS Code Copilot agent hooks Preview en v1.110+), y el repo YA contiene templates por IDE (`.codex/`, `.gemini/`, `.github/`) más 12 pares shell+PowerShell de adapters Copilot en `.ai-engineering/scripts/hooks/copilot-*.{sh,ps1}` — pero los 4 sistemas NO emiten al mismo `framework-events.ndjson` con schema unificado: `.codex/hooks.json` (1722 bytes) puede no estar conectado al NDJSON, `.gemini/settings.json` (4262 bytes) requiere stdin/stdout JSON contract específico que no hemos verificado; (3) **Cross-platform parity incompleto**: los 12 adapters Copilot tienen pares `.sh` (macOS/Linux) y `.ps1` (Windows) pero los 8 hooks principales en Python (`telemetry-skill.py`, `prompt-injection-guard.py`, `instinct-observe.py`, `instinct-extract.py`, `observe.py`, `mcp-health.py`, `strategic-compact.py`, `auto-format.py`) son portables en teoría pero no tenemos CI matrix Windows que lo verifique; (4) **DRY violation masiva en adapters**: los 12 pares `copilot-*.{sh,ps1}` duplican lógica de NDJSON append, lectura de stdin, computación de duration, schema serialization — ~24 archivos con ~80% código común; (5) **Hot-path no instrumentado**: ningún hook emite `detail.duration_ms` consistente; el v3 declara SLO `<1s` para PreToolUse pero current no tiene métrica para detectar violations. Adicionalmente, el audit del NDJSON revela que el hash-chain (Article III v3, también en spec-110 D-110-03) existe en solo 16.3% de eventos y vive en `detail.prev_event_hash` (anidado) — spec-110 cubre la migración a raíz, spec-112 cubre el reset que finaliza la migración limpiamente. spec-112 es **fundación de telemetría limpia y multi-plataforma**: arregla el bug de captura (T1), garantiza paridad cross-OS con CI matrix (T2), audita y unifica los 4 IDEs al mismo NDJSON con schema consistente (T3), resetea el NDJSON archivando el legacy (T4), aplica DRY pass extrayendo `_lib/` shared para shell/PowerShell y Python (T5), instrumenta hot-path SLO con violations detection (T6), y aplica clean code audit (T7) a los archivos modificados. **No borra ningún skill ni agent** — la consolidación se difiere a spec-113 una vez que ≥14 días de datos limpios estén disponibles para usar `/skill-sharpen` (skill nativo de la harness Claude Code) sobre cada uno de los 49 skills basado en feedback real recolectado, sin riesgo de eliminar algo solo porque el bug de telemetría lo escondió. Beneficio medible: cada `/ai-<name>` registrado correctamente con engine identificado; cualquier audit posterior puede confiar en los datos; hot-path violations visibles al user; refactor DRY reduce ~40% de LOC en adapters; clean code audit produce diff homogéneo aplicable como gate en `/ai-review` futuro.

## Goals

### T1 — Fix telemetry-skill capture

- G-1: `telemetry-skill.py` extrae el nombre del skill desde el prompt body con regex `^/ai-([a-zA-Z0-9_-]+)` aplicado a `payload.prompt` recibido vía stdin. `detail.skill` contiene el nombre extraído (e.g., `"ai-brainstorm"`, `"ai-plan"`) sin slash, sin sufijos, sin el string `"ai-engineering"` hardcoded. Casos edge: prompt vacío, prompt sin `/ai-`, prompt con argumentos (`/ai-brainstorm topic`), prompt con flags (`/ai-research --depth=deep query`). Verificable por `tests/unit/hooks/test_telemetry_skill.py::test_skill_name_extraction` con 12 fixtures (10 prompts válidos + 2 edge cases que deben emitir `detail.skill: null` con `kind: skill_invoked_malformed`).

### T2 — Cross-platform parity

- G-2: GitHub Actions workflow `.github/workflows/test-hooks-matrix.yml` (nuevo) ejecuta la suite e2e de hooks en runners `ubuntu-latest`, `macos-latest`, `windows-latest`. Cada matrix cell ejecuta: (a) `pytest tests/integration/test_hooks_e2e.py` que lanza cada hook script con stdin JSON fixture y valida output NDJSON; (b) verificación de paridad `.sh` ↔ `.ps1` para los 12 pares Copilot via comparación de output NDJSON dado mismo input. Verificable por presencia del workflow + 3 matrix cells passing.
- G-3: Los 8 hooks Python (`telemetry-skill.py`, `prompt-injection-guard.py`, `instinct-observe.py`, `instinct-extract.py`, `observe.py`, `mcp-health.py`, `strategic-compact.py`, `auto-format.py`) usan `pathlib.Path` para todo path handling (no concat string con `/` ni `\`). Line endings: lectura de stdin con `newline=None` (universal newline mode); escritura a NDJSON con `\n` literal explícito. Verificable por `tests/unit/hooks/test_path_portability.py::test_hooks_use_pathlib` (AST scan que falla si encuentra `os.path.join` o string concat con separators) y `tests/unit/hooks/test_line_endings.py::test_ndjson_uses_lf_only`.

### T3 — Multi-IDE hook unification

- G-4: Schema unificado de evento NDJSON tipado en `src/ai_engineering/state/event_schema.py` (nuevo o extensión de `models.py`):
    ```python
    class FrameworkEvent(TypedDict):
        kind: str                        # "skill_invoked" | "agent_dispatched" | "ide_hook" | "git_hook" | "framework_operation" | "context_load" | "control_outcome" | "hot_path_violation" | "framework_error"
        engine: str                      # "claude_code" | "codex" | "gemini" | "copilot"
        timestamp: str                   # ISO 8601 UTC
        prev_event_hash: str | None      # SHA-256 of canonical previous event JSON; null only for first event
        component: str                   # producer (e.g., "hook.telemetry-skill")
        outcome: str                     # "success" | "fail" | "warn"
        correlationId: str               # UUID per session/turn
        sessionId: str | None
        schemaVersion: str               # "2.0" (post-spec-112 reset)
        project: str
        source: str | None
        detail: dict                     # event-specific payload; for skill_invoked: {skill: str, args: list, duration_ms: int}
    ```
  Validation: parser valida cada evento contra TypedDict; eventos malformados se loguean a stderr y NO se escriben al NDJSON (silently dropping is bug; explicit error is feature). Verificable por `tests/unit/state/test_event_schema.py::test_validate_minimal_event` y `test_reject_missing_required_field`.
- G-5: `.codex/hooks.json` configurado con hooks que emiten al mismo NDJSON via wrapper Python compartido. Hooks habilitados: `PreToolUse`, `UserPromptSubmit`, `Stop`. El wrapper `codex-hook-bridge.py` (nuevo en `.ai-engineering/scripts/hooks/`) recibe stdin JSON conforme al contract de Codex (`developers.openai.com/codex/hooks`), normaliza al schema unificado, escribe al NDJSON. Verificable por `tests/integration/test_codex_hooks.py::test_codex_hook_emits_unified_event` con stdin fixture conforme al contract Codex.
- G-6: `.gemini/settings.json` configurado con hooks via stdin/stdout JSON contract de Gemini CLI (`geminicli.com/docs/hooks/reference.md`): events `BeforeTool`, `AfterTool`, `BeforeAgent`, `AfterAgent`, `SessionStart/End`. Wrapper `gemini-hook-bridge.py` recibe stdin JSON contract Gemini, normaliza al schema unificado, escribe al NDJSON, y devuelve por stdout JSON requerido por Gemini (no plain text — el contract es estricto). Verificable por `tests/integration/test_gemini_hooks.py::test_gemini_hook_returns_valid_json_response`.
- G-7: Copilot adapters (12 pares `.sh` + 12 `.ps1`) emiten al mismo NDJSON via `_lib/copilot-common.{sh,ps1}` (creado en T5). Engine field = `"copilot"`. Eventos generados desde Copilot agent skills (VS Code v1.110+ Preview) se mappean al schema unificado. Verificable por `tests/integration/test_copilot_hooks_emit_unified.py::test_copilot_sh_and_ps1_produce_identical_events` (mismo input → ambos generan el mismo evento JSON modulo `engine` field).
- G-8: `ai-eng doctor --check telemetry-coverage` reporta cobertura por engine: cuántos eventos por `engine` value en últimas 24h, cuáles hooks no han emitido nada. Verificable por `tests/integration/test_doctor_telemetry_coverage.py::test_reports_per_engine_breakdown`.

### T4 — Reset NDJSON

- G-9: Comando `ai-eng state reset-events --confirm` (nuevo, requiere flag explícito): (a) verifica que T1+T2+T3 están passing (ejecuta los tests críticos); (b) archiva `framework-events.ndjson` actual a `.ai-engineering/state/framework-events.ndjson.legacy-<YYYY-MM-DD>.gz` con compresión gzip; (c) crea nuevo `framework-events.ndjson` vacío con primer evento `kind: state_reset` con `detail: {previous_archive: <path>, previous_event_count: <N>, schema_version_old: "1.0", schema_version_new: "2.0"}`. NO se ejecuta en CI; solo runs locales con flag `--confirm` explícito. Verificable por `tests/integration/test_state_reset.py::test_reset_archives_and_creates_empty_with_marker_event`.
- G-10: Documentación `docs/telemetry-reset-2026-04.md` describe: (a) por qué se reseteó (los 5 fallos), (b) cómo recuperar datos del legacy archive (`gunzip -c .legacy-...gz | python3 ...`), (c) baseline post-reset (qué esperar en las primeras 24h tras reset). Verificable por presencia del archivo.

### T5 — DRY pass en handlers

- G-11: `_lib/copilot-common.sh` y `_lib/copilot-common.ps1` (creados; existe `.ai-engineering/scripts/hooks/_lib/` ya en el repo) extraen funciones compartidas: `emit_event()` (NDJSON append + hash-chain compute), `read_input_json()` (stdin parse), `setup_env()` (resolve project root, NDJSON path), `compute_duration()` (timer wrap), `validate_schema()` (basic JSON shape check). Cada uno de los 12 pares `copilot-*.{sh,ps1}` se reduce a ~10-25 LOC: source/import del lib + lógica específica del hook. Verificable por `tests/unit/hooks/test_copilot_lib_shared.py` (LOC count antes/después: ≥40% reduction agregada) y `tests/integration/test_copilot_lib_emits_correctly.py` (los 12 hooks emiten eventos válidos post-refactor).
- G-12: `_lib/hook-common.py` extrae funciones compartidas por los 8 hooks Python: `emit_event(event_dict)`, `read_stdin_json()`, `compute_event_hash(prev_hash, current_dict)`, `get_correlation_id()`, `get_session_id()`, `validate_event_schema(dict)`. Cada hook Python pasa de ~80-150 LOC a ~30-60 LOC + import del lib. Verificable por reduction LOC + `tests/unit/hooks/test_hook_common_lib.py` con 6 funciones × 3 casos cada una = 18 test cases.

### T6 — Hot-path SLO instrumentation

- G-13: Cada hook script (Python + shell + PowerShell, vía `_lib`) emite `detail.duration_ms` (timer wrap alrededor de la función principal del hook). `kind` permanece igual (no es un nuevo tipo de evento; es un campo añadido a los existentes). Verificable por `tests/integration/test_duration_ms_present.py::test_all_hooks_emit_duration` que ejecuta cada hook y valida `detail.duration_ms` presente y >0.
- G-14: SLO targets configurables en `.ai-engineering/manifest.yml` bajo `[telemetry.slo]`:
    ```yaml
    [telemetry.slo]
    pre_tool_use_p95_ms = 1000
    pre_commit_gate_p95_ms = 1000
    skill_invocation_overhead_p95_ms = 200
    enabled = true
    ```
  Cuando un hook excede su SLO target, emite evento adicional `kind: hot_path_violation` con `detail: {hook_name, duration_ms, slo_target_ms, slo_dimension}`. Hot-path violations son non-blocking (no fallan el hook; solo se registran). Verificable por `tests/integration/test_hot_path_slo.py::test_emits_violation_when_exceeds_target` con fixture que inyecta sleep 1500ms en hook stub.
- G-15: `ai-eng doctor --check hot-path` lee NDJSON post-reset, calcula p50/p95/p99 por hook por engine, compara contra SLO, reporta violations agregadas (e.g., "hook.observe p95: 1340ms (exceeds 1000ms in 12 of 200 invocations)"). Verificable por `tests/integration/test_doctor_hot_path.py::test_reports_p95_violations`.
- G-16: SLO violations en CI son skip-emitted: cuando `os.environ.get("CI") == "true"`, el hook NO emite `hot_path_violation` (CI runners pueden ser lentos por razones no actionables; ruido innecesario). Verificable por `tests/unit/hooks/test_slo_skip_in_ci.py`.

### T7 — Clean code audit

- G-17: Funciones con LOC > 30 (excluyendo docstrings y blank lines) en `.ai-engineering/scripts/hooks/*.py`, `_lib/hook-common.py`, `src/ai_engineering/state/*.py` modificadas por este spec son refactoreadas a sub-funciones. Verificable por `pylint --disable=all --enable=R0915 --max-statements=30` o equivalente ruff rule (ej: `PLR0915`); 0 violations en archivos modificados.
- G-18: Naming inconsistencies en archivos modificados: snake_case en Python (no PascalCase para funciones), no `_temp`, `_old`, `_new`, `_TODO` legacy names en código merged. Verificable por ruff con reglas `N802` (function naming), `N803` (argument naming), grep custom para legacy markers.
- G-19: Comentarios obvios eliminados. Reglas: comentarios que repiten el nombre de la función/variable son removidos (`# increment counter` antes de `counter += 1`); comentarios `# TODO` con TTL > 30 días convertidos a issues GitHub o eliminados; docstrings preservados intactos. Verificable manualmente como gate en code review (subjective rule, no test automatizado en este spec).

### Universal

- G-20: 0 secrets nuevos, 0 vulns nuevas (gitleaks + pip-audit), 0 lint errors (ruff) introducidos por este spec.
- G-21: Coverage ≥80% en módulos modificados o creados: `_lib/hook-common.py`, `_lib/copilot-common.{sh,ps1}` (via shellcheck + bats coverage proxy), extensiones a `src/ai_engineering/state/` y `src/ai_engineering/cli_commands/state.py` (si es donde vive `state reset-events`).
- G-22: Spec-110 hash-chain migration (D-110-03) consolidada por T4: el reset elimina el periodo dual-read; post-T4, todos los eventos nuevos usan `prev_event_hash` en raíz. Verificable por `tests/integration/test_audit_chain_post_reset.py::test_no_legacy_detail_hash_in_new_events`.

## Non-Goals

- NG-1: **Borrar skills ni agents**. Confirmado por user en pregunta 8 del brainstorm: preservar todos los 49 skills y 26 agents hasta tener datos limpios. Cualquier delete está fuera de spec-112.
- NG-2: **Skill audit / consolidación / sharpen iterativo**. Defer a **spec-113** separado, ejecutado tras ≥14 días de datos limpios post-T4. spec-113 usará `/skill-sharpen` (skill nativo de la harness Claude Code) sobre cada skill basado en feedback real, no `/ai-skill-evolve`.
- NG-3: Agent count consolidation 26 → 7. Defer.
- NG-4: Clean Architecture lite (separación core/adapters/cli). Defer; sin telemetría de duplicación, no podemos justificar la separación.
- NG-5: Hexagonal architecture / DDD bounded contexts. Confirmed out.
- NG-6: OTel exporter desde NDJSON. Defer (también en NG de spec-110).
- NG-7: Nuevos skills en este spec, EXCEPTO el fix del existing `telemetry-skill.py`. spec-111 introduce `/ai-research`; spec-112 no introduce skills.
- NG-8: Migración del NDJSON legacy a un nuevo storage (e.g., SQLite). Mantenemos NDJSON file-based.
- NG-9: Real-time dashboard sobre NDJSON. spec separado si se requiere.
- NG-10: PR creation in this spec.
- NG-11: Modificar `.claude/skills/` o `.gemini/skills/` o `.codex/skills/` o `.github/skills/` (los skill mirrors). spec-112 toca solo hooks, no skill content.

## Decisions

### D-112-01: Fix bug ANTES de reset NDJSON

T1 (fix `telemetry-skill.py`) y T3 (multi-IDE unification) deben estar passing y mergeados antes de ejecutar T4 (reset). Si reseteamos primero, generamos data corrupta nueva inmediatamente y perdemos la oportunidad de medir el impacto del fix vs el bug.

**Rationale**: el reset es one-shot y caro (legacy archive); ejecutarlo prematuramente requiere otro reset después. Hacerlo último garantiza que post-reset todo el data nuevo es válido.

### D-112-02: Schema unificado con `engine` requerido en raíz

`engine: str` es requerido en raíz del evento (no en `detail`) para detectar mismatch entre IDEs en cualquier query. Values permitidos: `"claude_code"`, `"codex"`, `"gemini"`, `"copilot"`. Eventos sin `engine` válido se rechazan en validation y se loguean a stderr.

**Rationale**: con 4 IDEs emitiendo, el primer query útil es "cuántos eventos por engine"; tenerlo en raíz hace queries triviales (`jq 'select(.engine == "codex")'`).

### D-112-03: gzip del archive legacy

`framework-events.ndjson` actual pesa 6.4MB descomprimido. Gzip reduce a <1MB con compression ratio típico ~6:1. Preservamos el archive en disco, no remoto, para que forensic queries (e.g., "cuándo se invocó X skill antes del reset") sean accesibles offline.

**Rationale**: 1MB local vs 6MB es trivial; gzip es estándar; cualquier usuario puede `gunzip -c | jq` para queries históricos. Si en el futuro el legacy es estorbo, se puede mover a `archive/` o eliminar.

### D-112-04: `_lib/` como shared scripts (no paquete pip)

Los hooks shell `.sh` y PowerShell `.ps1` no pueden importar paquetes Python. La opción es: (a) `_lib/` con archivos source/dot-source'eados (`source _lib/copilot-common.sh` desde `copilot-skill.sh`), o (b) hacer un paquete Python y que los `.sh` invoquen el paquete via subprocess. La opción (a) tiene cero overhead de proceso; la opción (b) tiene latencia de cold-start Python (~50-100ms) por invocación, lo que viola el SLO de hot-path para hooks frecuentes.

**Rationale**: shared scripts via source/dot-source es la práctica estándar en bash/PowerShell, zero overhead, cross-OS si el lib está bien escrito. Los Python hooks tienen su propio `_lib/hook-common.py` con import normal.

### D-112-05: Hot-path SLO emite evento, no falla el hook

Cuando un hook excede su SLO target, emite `kind: hot_path_violation` adicional pero el hook continúa y completa normalmente. La violation NO falla el commit / la ejecución / el push.

**Rationale**: el SLO es señal alerting, no enforcement bloqueante. Si fuera bloqueante, una sola sesión con disco lento bloquearía el dev flow del usuario por una métrica que no es accionable inmediatamente. El reporte agregado en `ai-eng doctor --check hot-path` es donde el equipo decide si actuar.

### D-112-06: spec-113 separado para sharpen iterativo, no T8 en spec-112

`/skill-sharpen` × 49 skills requiere ≥14 días de datos limpios post-reset (T4) para que las observaciones sean estadísticamente válidas. Embeber esta dependencia temporal en spec-112 forzaría el spec a estar `in-progress` durante 2-3 semanas sin avance perceptible al user. Mejor: spec-112 cierra con T7, spec-113 abre con T8 cuando los datos estén disponibles. Marker: `LESSONS.md` recibe entry "spec-113 ready when framework-events.ndjson has ≥14 days post-reset data".

**Rationale**: scope discipline. Cada spec debe ser shippable en un horizonte continuo de trabajo activo. spec-113 trigger es checkable por cron (job que valida age de NDJSON).

### D-112-07: SLO skip en CI

Hooks corriendo en CI (`os.environ.get("CI") == "true"`) NO emiten `hot_path_violation`. El motivo: CI runners varían dramáticamente en performance (free-tier GitHub Actions vs self-hosted vs Codespaces), las violations son ruido no accionable, y el SLO está pensado para dev local.

**Rationale**: noise reduction. Si en el futuro se quiere SLO para CI, se añade `[telemetry.slo.ci]` separado con targets más relajados.

### D-112-08: Wrapper bridges para Codex y Gemini

Codex CLI envía un JSON contract específico (definido en `developers.openai.com/codex/hooks`); Gemini CLI envía otro contract (stdin/stdout JSON con shape específico). En lugar de modificar nuestros hooks Python para hablar 4 contracts, usamos `codex-hook-bridge.py` y `gemini-hook-bridge.py` como adapters que normalizan al schema unificado interno y delegan a `_lib/hook-common.py`. Para Claude el bridge es trivial (ya emite el shape esperado); para Copilot el bridge vive en `_lib/copilot-common.{sh,ps1}`.

**Rationale**: separation of concerns. Cada IDE habla su contract con su bridge; el core de telemetría habla su schema unificado.

## Risks

- R-1: **Codex y Gemini hook contracts pueden cambiar** — son features Preview/recientes (Codex hooks estables abril 2026, Gemini desde v0.26.0+). Si el contract cambia, los bridges se rompen. _Mitigation_: tests integration con fixtures basadas en docs oficiales; CI matrix corre suite contra version-pinned CLIs si están disponibles; documentation `docs/telemetry-bridges.md` describe el contract version expected.
- R-2: **Reset del NDJSON pierde contexto histórico** que algún query externo dependiera. _Mitigation_: gzipped legacy archive preserva 100% del data; query histórico es `gunzip -c | jq`; `ai-eng state list-archives` (mini comando si vale la pena, opcional) lista archives disponibles.
- R-3: **DRY pass (T5) puede romper hooks vivos durante refactor** — refactorizar 12 pares + 8 Python hooks tiene blast radius. _Mitigation_: tests-first per archivo (commit por archivo refactoreado, cada commit con tests verde); feature flag opcional `AI_ENG_USE_LEGACY_HOOKS=true` para rollback si CI rompe (preserva los archivos viejos en `.legacy/` por 30 días post-merge).
- R-4: **Hot-path SLO falsos positivos** en máquinas lentas (laptops viejos del user, Macs del 2018, etc.) — el SLO 1000ms para PreToolUse puede ser alcanzable en M3 pero no en Intel Mac 2018. _Mitigation_: SLO configurable en `manifest.yml`; si user reporta noise, suggest aumentar el target en su config local; en CI ya está skipped (D-112-07).
- R-5: **Clean code audit (T7) puede tocar archivos ya mergeados de otros specs** (104/106/107/109). _Mitigation_: scope strict — solo archivos modificados POR T1-T6 se auditan en T7. Lista explícita en plan de la spec.
- R-6: **Telemetry bridges para Codex/Gemini pueden requerir auth/permissions** que no controlamos — algunos hooks Gemini requieren config en `.gemini/settings.json` user-scope. _Mitigation_: documentación detallada en `docs/telemetry-bridges.md` con setup steps; `ai-eng doctor --check telemetry-coverage` detecta gaps y suggesta fix.
- R-7: **Schema migration spec-110 → spec-112 deberá coordinarse**. spec-110 introduce `prev_event_hash` en raíz con dual-read 30 días; spec-112 ejecuta reset que elimina el dual-read. Si spec-110 merge → spec-112 merge en <30 días, todo OK. Si spec-112 merge primero (race condition), el reset crea NDJSON con schema 2.0 antes que spec-110 termine la migración. _Mitigation_: dependency order explícita en plan: spec-110 merge BEFORE spec-112 T4 ejecuta. Add gate en `state reset-events`: lee CHANGELOG.md / git log para confirmar spec-110 merged; falla si no.
- R-8: **DRY shared `_lib/copilot-common.{sh,ps1}` cross-OS bash compatibility** — algunas features de bash 4+ no están en bash 3.x del macOS pre-Catalina; PowerShell Core (cross-platform) y Windows PowerShell tienen syntax diffs. _Mitigation_: shellcheck CI; PowerShell ScriptAnalyzer CI; lib escrito al subset común (POSIX-ish bash + PS Core compatible).
- R-9: **`_lib/hook-common.py` import circulares** si los hooks lo importan y el lib importa state modules que importan hooks indirectamente. _Mitigation_: lib es sealed (no imports de `src/ai_engineering/`); solo stdlib + `pathlib` + `json` + `hashlib` + `time`.

## References

- Telemetry audit data (brainstorm session pregunta 8): `framework-events.ndjson` 15,393 events 32 days, only 196 `skill_invoked` con `detail.skill="ai-engineering"` (bug confirmado).
- Hook docs oficiales:
  - Claude Code hooks: ya documentados internamente en `.claude/settings.json` (existing).
  - Codex CLI hooks: `developers.openai.com/codex/hooks` (estables abril 2026).
  - Gemini CLI hooks: `geminicli.com/docs/hooks/` (v0.26.0+).
  - VS Code Copilot agent hooks: `code.visualstudio.com/docs/copilot/customization/hooks` (Preview v1.110+).
  - AGENTS.md open standard: `developers.openai.com/codex/guides/agents-md`.
- Existing infrastructure que se aprovecha: `.ai-engineering/scripts/hooks/copilot-*.{sh,ps1}` (12 pares), `.codex/hooks.json`, `.gemini/settings.json`, `.claude/settings.json`, `src/ai_engineering/state/audit_chain.py`, `src/ai_engineering/state/observability.py`.
- Related specs:
  - **spec-110** (governance v3 harvest) — D-110-03 hash-chain root migration; spec-112 T4 finaliza la migración con el reset.
  - **spec-111** (ai-research skill) — Tier 0 local depende de NDJSON limpio post-reset para ser útil.
  - **spec-109** (installer first-install robustness) — base estable; este spec asume installer sano.
  - **spec-113** (futuro) — `/skill-sharpen` × 49 skills basado en datos limpios post-T4.
- Brainstorm session: pregunta 7 (scope C confirmado), pregunta 8 (telemetry concerns y multi-signal audit refactorizado a multi-IDE unification), pregunta 9 (β + 2 + DRY/SLO/clean-code todos in), pregunta 10 (drafting these specs).
