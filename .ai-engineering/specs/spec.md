---
spec: spec-104
title: Commit/PR Pipeline Speed — Single-Pass Collector + Memoization + Bounded Watch
status: approved
effort: medium
refs:
  - .ai-engineering/notes/adoption-s2-commit-pr-speed.md
  - .ai-engineering/notes/adoption-s3-unified-gate-risk-accept.md
  - .ai-engineering/notes/spec-101-frozen-pr463.md
---

# Spec 104 — Commit/PR Pipeline Speed: Single-Pass Collector + Memoization + Bounded Watch

## Summary

`/ai-commit` y `/ai-pr` son medium-slow a slow porque ejecutan secuencialmente 6 checks (`ruff format` → `ruff check` → `gitleaks staged` → docs gate LLM → `ai-eng validate` → `ai-eng spec verify`), repiten el bloque pre-push completo (~30-120s `semgrep` + `pytest` + `pip-audit` + `ty`) que la matriz CI ya cubre, dispachan dos subagentes `/ai-docs` síncronos antes de crear el PR, llaman `ai-eng spec verify` dos veces sin invalidación, y mantienen un watch loop sin tope global de iteraciones (`fix_attempts>=3` por check pero `iteration_count` ilimitado). Cero memoización: cada re-run ejecuta todo desde cero aunque ningún input haya cambiado. Verbosity acumulada en 532 líneas (`ai-commit/SKILL.md` 126 + `ai-pr/SKILL.md` 221 + `ai-pr/handlers/watch.md` 185) duplicando reglas que ya viven en `CLAUDE.md` y `.ai-engineering/contexts/languages/`. Resultado: tiempo total `/ai-pr` ~3-5 min en cold-cache, fricción de adopción en GitHub Copilot, Codex y Gemini idéntica porque la lentitud está en la capa CLI/hook (IDE-agnóstica). spec-104 reescribe el pipeline como dos olas (fixers serial → checkers paralelo) con caché de gate por hash + max-age 24h, mueve `semgrep`/`pip-audit`/`pytest full` a CI authoritative manteniendo shift-left (CI ejecuta antes de merge; watch loop autofixea), paraleliza dispatch de docs con la ola de checkers, acota el watch loop por wall-clock (30 min active / 4h passive), emite `gate-findings.json` v1 como contrato hacia spec-105 (S3 risk-accept), y poda 30% de verbosity quirúrgicamente eliminando solo duplicados verificados. Beneficio medible: warm-cache `/ai-pr` ≥40% más rápido, cold-cache ≤90s, watch loop nunca se cuelga en bucles ilimitados, una sola fuente CLI funciona idéntica para los cuatro IDEs.

## Goals

- G-1: `/ai-pr` warm-cache wall-clock reduce ≥40% sobre baseline python single-stack — verificable por `tests/perf/test_ai_pr_warmcache.py` que ejecuta `/ai-pr` dos veces sobre branch sin cambios y compara wall-clock vs grabación pre-cambios.
- G-2: `/ai-pr` cold-cache wall-clock ≤90s sobre baseline python single-stack (vs 3-5 min actuales) — verificable por mismo perf test con cache cleared.
- G-3: gate-cache hit rate ≥70% en runs consecutivos con inputs idénticos — verificable por `AIENG_CACHE_DEBUG=1` log assertions en `tests/integration/test_gate_cache_hit_rate.py`.
- G-4: Single-pass collector emite `gate-findings.json` schema v1 cubriendo los 6 checks; salida JSON valida contra fixture — verificable por `tests/unit/test_gate_findings_schema.py`.
- G-5: Watch loop active wall-clock cap 30 min, passive 4h, exit code 90 al cap; emite `watch-residuals.json` con mismo schema — verificable por `tests/integration/test_watch_loop_bounds.py` con CI timing mockeado.
- G-6: Reducción neta SKILL.md ≥30% (≥160 líneas) entre `ai-commit/SKILL.md` + `ai-pr/SKILL.md` + `ai-pr/handlers/watch.md` sin remover contrato — verificable por `tests/unit/test_skill_line_budget.py` y `tests/unit/test_skill_contract_completeness.py`.
- G-7: `ai-eng sync --check` PASS post-cambios; espejos en `.claude/`, `.github/`, `.codex/`, `.gemini/` regenerados consistentes — verificable en CI job existente.
- G-8: Cross-IDE parity — `ai-eng gate run --json` produce salida idéntica invocado directamente en 4 entornos IDE-emulados — verificable por `tests/integration/test_gate_cross_ide.py`.
- G-9: Contrato spec-101 intacto — gate-cache respeta `python_env.mode`, `required_tools`, registro de 14 stacks, `--force` re-corre todo; install-smoke CI continúa pasando.

## Non-Goals

- NG-1: `ai-eng risk accept` CLI y subcomandos (`accept`, `accept-all`, `renew`, `resolve`) — alcance spec-105 (S3).
- NG-2: Wiring gate↔risk-accept lookup en `policy/gates.py` y `policy/checks/*.py` — alcance spec-105.
- NG-3: Auto-fix `git add -u` post-`ruff format` (re-stage de archivos modificados por el fixer) — alcance spec-105 sub-feature `gates.pre_commit.auto_fix`.
- NG-4: `/skill-sharpen` global sweep sobre las 47 skills — alcance spec-106 (S4).
- NG-5: MCP Sentinel security audit de skills/agents/MCP servers — alcance spec-107 (S5).
- NG-6: Política de gate configurable per-project en `manifest.yml` (LESSONS: "stable orchestration should not become per-project config by default"). Local fast-slice y CI authoritative son fijos en framework.
- NG-7: Migrar generación de docs a follow-up commit post-PR (mantenemos sync paralelo con pre-push gate; LESSONS regulated audience prefiere historia limpia).
- NG-8: Nuevos comandos públicos en `ai-eng` CLI más allá de extender `ai-eng gate run` con `--cache-aware`, `--no-cache`, `--force`, `--json`. Sin nuevos `ai-eng <subcommand>` standalone.
- NG-9: Cache content cross-machine sharing (local↔CI). Solo schema de hash idéntico; storage físico independiente.
- NG-10: Reescritura completa de `policy/gates.py`. spec-104 añade orchestrator y cache; el gate dispatch existente queda como fallback bajo `AIENG_LEGACY_PIPELINE=1`.

## Decisions

### D-104-01: Single-pass collector con dos olas (fixers serial → checkers paralelo)

`src/ai_engineering/policy/orchestrator.py` (nuevo) reemplaza el flujo secuencial actual de `/ai-commit` step 2-6 y `/ai-pr` step 7. Estructura:

- **Wave 1 — Fixers (serial)**: `ruff format` → `ruff check --fix` → `ai-eng spec verify --fix`. Serial porque `format` modifica archivos que `check` lee y porque `spec verify --fix` puede tocar `_history.md` que otros checkers leen. Wall-clock estimado 5-15s.
- **Wave 2 — Checkers (paralelo)**: `gitleaks protect --staged`, `ai-eng validate`, docs gate (LLM dispatch), `ty check src/`, `pytest -m smoke`. Independientes entre sí. Wall-clock estimado 20-40s (limitado por el más lento — pytest smoke o ty).
- **Salida**: `.ai-engineering/state/gate-findings.json` con todos los failures de Wave 2 (Wave 1 falla solo si los fixers no convergen tras un re-run automático intra-wave). Schema en D-104-06.
- **Comportamiento en falla**: si Wave 2 produce findings con `severity >= medium`, `ai-eng gate run` exit 1 sin proceder a commit; spec-105 conectará risk-accept para permitir override consciente.
- **Fallback de emergencia**: `AIENG_LEGACY_PIPELINE=1` env restaura el flujo secuencial pre-spec-104; documentado en CHANGELOG migration.

**Rationale**: Wave 1 serial elimina races sin sacrificar velocidad real (los tres fixers son rápidos). Wave 2 paralelo es donde el wall-clock paga: 5 checks independientes corren en `min(35s, max-individual)` en lugar de `sum=~70-100s`. Recolección completa en una sola pasada (no fail-fast) entrega al usuario todo el panorama de problemas — necesario para el flujo S3 "acepto todos los riesgos y push".

### D-104-02: Local fast-slice + CI authoritative (política fija de framework)

`/ai-commit` y `/ai-pr` pre-push solo ejecutan checks rápidos que protegen integridad mínima:

| Check | Local fast-slice (≤60s budget) | CI authoritative |
|---|---|---|
| `gitleaks protect --staged` | ✅ | ✅ (full-source en CI security job) |
| `ruff format` + `ruff check --fix` | ✅ | ✅ (lint job) |
| `ty check src/` | ✅ | ✅ (typecheck job) |
| `pytest -m smoke` (subset rápido) | ✅ | — (smoke ya cubierto por unit job en CI) |
| `ai-eng validate` | ✅ (si `.ai-engineering/` cambió) | ✅ (content-integrity job) |
| docs gate (LLM) | ✅ | — (no determinista en CI) |
| `semgrep` | ❌ removido | ✅ (security job — full-source con tiempo holgado) |
| `pip-audit` | ❌ removido | ✅ (security job — network access disponible) |
| `pytest` full + matrix | ❌ removido | ✅ (test job — 3 OS × 3 Py matrix) |

Watch loop autofixea fallos de CI authoritative (mecanismo existente, sin cambios funcionales). Política documentada en `.ai-engineering/contexts/gate-policy.md` (nuevo); no configurable por `manifest.yml`.

**Rationale**: shift-left se preserva porque CI ejecuta antes de merge (con auto-complete bloqueado hasta CI green); los checks que se delegan son los que (a) tardan ≥30s, (b) requieren network o (c) replican exactamente lo que CI matrix ya hace. Wall-clock local cae 3-5 min → ≤90s. Política fija (no configurable) sigue LESSONS "stable framework orchestration should not become per-project config by default" — un fintech que necesite más checks locales puede customizar via fork del context, pero no via manifest, evitando mirror drift entre Claude/Copilot/Codex/Gemini.

### D-104-03: gate-cache con clave hash + max-age 24h

`src/ai_engineering/policy/gate_cache.py` (nuevo) implementa caché por check con las siguientes invariantes:

- **Cache key**: `sha256(tool_name ‖ tool_version ‖ sorted(staged_blob_shas) ‖ sorted(config_file_hashes) ‖ sorted(args))` (definición precisa en D-104-09).
- **Storage**: `.ai-engineering/state/gate-cache/<cache-key>.json` per-cwd; per-worktree natural (alineado con `python_env.mode=uv-tool` de spec-101 D-101-12).
- **Hit semantics**:
  - Hit en PASS → skip run, replay PASS, log `cache_hit=true` en findings JSON.
  - Hit en FAIL → skip run, replay FAIL con findings originales, mantiene exit 1.
- **Miss handling**: ejecuta el check, persiste resultado completo (`{result, findings, verified_at, verified_by_version, key_inputs}`).
- **Invalidación**: cualquier input cambia el hash (entrada miss naturalmente) **OR** `now() - verified_at > 24h`.
- **Override flags**: `ai-eng gate run --no-cache` (lookup skipped, fresh run, persiste); `--force` (lookup skipped, clears matching entry, fresh run, persiste); `AIENG_CACHE_DISABLED=1` env-level kill switch.
- **CI integration**: `actions/cache@v4` con key schema idéntico al local; cross-PR reuse cuando blobs+config+versions coinciden; storage independiente (CI no monta el cache local del dev).
- **Robustez**: write atómico via `tempfile + os.rename`; lectura corrupta → log warn, treat as miss, regenera.
- **Bound de tamaño**: LRU prune a 256 entries cada `_persist`; cap disco ≤16 MB total (256 × 64 KB max por entrada).

**Rationale**: hash-based primario porque captura correctness (un input cambia → key cambia → re-run). Max-age 24h es defensa en profundidad para drift que escapa al hash (e.g., upgrade implícito de uv runtime, regla nueva en `~/.config/<tool>/`). 300s TTL de la propuesta original era demasiado agresivo (re-runs cada 5 min sin razón). Per-cwd storage es trivial y worktree-friendly. Bound LRU evita disco creciente sin tope.

### D-104-04: Async paralelo docs + pre-push (sync, no fire-and-forget)

`/ai-pr` step 6.5 (docs subagentes) y step 7 (pre-push gate Wave 2) ejecutan **simultáneamente** en lugar de secuencialmente:

- 3 tareas concurrentes lanzadas: docs Agent 1 (CHANGELOG+README), docs Agent 2 (docs-portal+quality-gate), pre-push Wave 2 (los 5 checkers paralelos de D-104-01).
- Wave 1 fixers (serial) ya completaron antes de este punto.
- Block conjunto: espera `max(docs_a1, docs_a2, prepush_w2)`.
- Wall-clock: `max(~30-60s docs, ~20-40s pre-push)` ≈ 30-60s en lugar de `~30-60 + 20-40 = 50-100s` sumados.
- PR description sigue siendo coherente al momento de `gh pr create` (CHANGELOG/README ya generados y staged).
- Sin follow-up commits automáticos al PR para docs (mantenemos historia limpia).

**Rationale**: ahorro de 20-50s sin sacrificar coherencia del PR ni introducir follow-up commits que ensucia auditoría regulatoria. Fire-and-forget post-PR (alternativa B descartada en brainstorm Q5) tenía el problema de que durante la ventana de generación el reviewer ve un PR body referenciando entries de CHANGELOG inexistentes. Para target audience banca/healthcare, coherencia > velocidad marginal.

### D-104-05: Watch loop bounded por wall-clock (active 30min / passive 4h)

`.claude/skills/ai-pr/handlers/watch.md` y mirror equivalents añaden state:

- `watch_started_at: ISO-8601` capturado en step 1 inicial.
- `last_active_action_at: ISO-8601` actualizado cada vez que el loop aplica un fix (step 4) o resuelve un conflict (step 5).
- **Active phase cap**: `now() - last_active_action_at > 30 min` → STOP. Refleja "30 min sin progreso desde última acción de fix" — distinto de "30 min totales".
- **Passive phase cap**: `now() - watch_started_at > 4h` → STOP. El loop pasivo solo espera review humano; 4h es una cota generosa para una sesión laboral.
- Per-check `fix_attempts >= 3` se mantiene (no cambia).
- **On cap**:
  1. Emite `.ai-engineering/state/watch-residuals.json` con mismo schema que `gate-findings.json` (D-104-06) — findings residuales de checks que aún fallan.
  2. Print mensaje accionable:
     ```
     Watch loop hit <active|passive> wall-clock cap (<minutes> min).
     <N> checks still failing: <names>
     Run: ai-eng risk accept-all .ai-engineering/state/watch-residuals.json --justification "..."
     Or fix manually and re-invoke /ai-pr.
     ```
  3. Exit code **90** (distinto de exit 80/81 de spec-101 D-101-11).

**Rationale**: wall-clock es métrica user-meaningful (30 min, no 30 iteraciones — el usuario piensa en tiempo, no en polls). Active vs passive distinto refleja que esperar review es legítimo y no debe truncar. Exit 90 permite a CI scripts distinguir "watch timed out" de "real failure". El emit de `watch-residuals.json` con schema unificado conecta naturalmente al spec-105 risk-accept-all flow del usuario.

### D-104-06: gate-findings.json schema v1 (contrato spec-104 → spec-105)

Schema canónico emitido por orchestrator (gate-findings.json) y watch loop (watch-residuals.json):

```json
{
  "schema": "ai-engineering/gate-findings/v1",
  "session_id": "<uuid4>",
  "produced_by": "ai-commit|ai-pr|watch-loop",
  "produced_at": "<ISO-8601 UTC>",
  "branch": "<git branch name>",
  "commit_sha": "<HEAD sha or null if uncommitted>",
  "findings": [
    {
      "check": "gitleaks|ruff|ty|pytest|semgrep|pip-audit|validate|docs-gate",
      "rule_id": "<stable-id>",
      "file": "<path-relative-to-repo>",
      "line": <int>,
      "column": <int|null>,
      "severity": "critical|high|medium|low|info",
      "message": "<short human-readable>",
      "auto_fixable": <bool>,
      "auto_fix_command": "<cli-cmd|null>"
    }
  ],
  "auto_fixed": [{"check": "<name>", "files": ["<path>"], "rules_fixed": ["<rule-id>"]}],
  "cache_hits": ["<check-name>"],
  "cache_misses": ["<check-name>"],
  "wall_clock_ms": {"wave1_fixers": <int>, "wave2_checkers": <int>, "total": <int>}
}
```

Constraints:
- `rule_id` MUST ser estable (CVE-XXXX, semgrep rule-id, gitleaks rule-id, ruff code E501, ty error code). NUNCA mensaje humano.
- `schema` field versionado; consumers (spec-105 risk-accept) leen y rechazan versiones desconocidas con mensaje accionable.
- Fixture JSON canónica en `tests/fixtures/gate_findings_v1.json` valida schema en CI.

**Rationale**: stable-id-keyed schema permite a spec-105 hacer lookup `finding_is_accepted(finding.rule_id, store)` determinístico. Versión explícita en `schema` field habilita evolución no-breaking (v2 puede añadir campos opcionales). Telemetría `wall_clock_ms` facilita medir impacto real de spec-104 post-merge sin instrumentación adicional.

### D-104-07: Verbosity reduction conservadora (solo duplicados verificados)

Cambios precisos en los 3 archivos en alcance:

| Archivo | Líneas removidas | Razón |
|---|---|---|
| `.claude/skills/ai-commit/SKILL.md:110-119` | -10 | Tabla "Common Mistakes" duplicada con CLAUDE.md Don't section. Reemplazada por una línea: "See CLAUDE.md Don't section for governance constraints." |
| `.claude/skills/ai-pr/SKILL.md:53-63` | -11 | Stack-detection block; vive en `.ai-engineering/contexts/languages/<lang>.md` y se carga via `manifest.yml` providers.stacks. Reemplazada por: "Stack-aware checks are dispatched from the language context loaded per `manifest.yml`." |
| `.claude/skills/ai-pr/SKILL.md:199-205` y `.claude/skills/ai-pr/handlers/watch.md:169-185` | -22 (consolida en watch.md) | Behavioral negatives + anti-patterns duplicados. Consolidar en una sola sección en watch.md; ai-pr/SKILL.md la referencia con un puntero. |

Total estimado: ~43 líneas directas + ~120 líneas adicionales por simplificar el surrounding boilerplate (encabezados huérfanos, separadores) que pierden razón al perder contenido. Target ≥160 líneas removidas (≥30% del bloque combinado).

Constraints:
- `tests/unit/test_skill_contract_completeness.py` (nuevo) verifica que cada SKILL.md tocado mantiene secciones obligatorias: `## Process`, `## Integration`, `## Quick Reference`, `argument-hint` en frontmatter.
- `tests/unit/test_skill_line_budget.py` (nuevo) asserta line count post-spec-104 ≤ baseline pre-spec-104 menos 160.
- `ai-eng sync --check` debe PASS tras los cambios (espejos GH/Codex/Gemini regenerados consistentes).

**Rationale**: aplicación quirúrgica de la lección "Elimination is simplification, not migration". Solo duplicados verificados (cross-referenced contra CLAUDE.md y `contexts/languages/`). Quick Reference y Common Mistakes (no las que duplican Don'ts) sobreviven porque tienen alta densidad informativa por línea y los IDEs no-Claude (Codex, Gemini) no auto-cargan CLAUDE.md por defecto — el skill markdown es la única instrucción que el agente recibe.

### D-104-08: Cross-IDE parity vía CLI-layer caching

Toda la lógica de speed-up vive en módulos Python invocables via CLI:

- `src/ai_engineering/policy/orchestrator.py` (nuevo) — `run_gate(checks, mode)` orquesta Wave 1 + Wave 2.
- `src/ai_engineering/policy/gate_cache.py` (nuevo) — lookup, persist, invalidate, prune.
- `src/ai_engineering/cli_commands/gate.py` (extendido) — añade `--cache-aware`, `--no-cache`, `--force`, `--json`.

Skills mirrors `.claude/skills/ai-commit/SKILL.md`, `.github/skills/ai-commit/SKILL.md`, `.codex/skills/ai-commit/SKILL.md`, `.gemini/skills/ai-commit/SKILL.md` (regenerados por `ai-eng sync`) instruyen al agente a invocar `ai-eng gate run --cache-aware --json` en lugar de ejecutar herramientas individuales (`ruff check`, `gitleaks protect`...) directamente.

Test cross-IDE en `tests/integration/test_gate_cross_ide.py`:
1. Crea fixture project con cambios staged determinísticos.
2. Invoca `ai-eng gate run --json` 4 veces simulando entornos `claude_code`, `github_copilot`, `codex`, `gemini` (env vars y cwd configurados per-IDE).
3. Asserta JSON output byte-idéntico (después de normalizar `session_id` y timestamps).

**Rationale**: el bottleneck spec-104 está en el flujo CLI/hook/Python, no en la capa de skill markdown. Centralizar cache + orchestrator en CLI garantiza beneficio idéntico independiente del IDE driver. Skills mirrors actúan solo como "instrucciones al agente para llamar al CLI"; el sync existente (LESSONS "manifest.yml es la fuente de verdad absoluta") propaga cualquier cambio a los 4 espejos.

### D-104-09: Definición precisa de inputs del cache key

`gate_cache._compute_cache_key(check_name, args)` calcula sha256 sobre el join de:

| Input | Fuente | Cómo |
|---|---|---|
| `check_name` | parámetro | string literal, e.g., `"ruff-check"`, `"gitleaks-staged"` |
| `tool_version` | comando canónico | output de `<tool> --version`, parseado a semver string |
| `staged_blob_shas` | git | `git ls-files --staged -z \| xargs -0 git hash-object`; lista ordenada |
| `config_file_hashes` | filesystem | sha256 de cada archivo en `_CONFIG_FILE_WHITELIST` (per check) |
| `args` | parámetro | argv pasado al check, ordenado |

`_CONFIG_FILE_WHITELIST` (constante en `gate_cache.py`):
```python
_CONFIG_FILE_WHITELIST = {
    "ruff-format":   ["pyproject.toml", ".ruff.toml", "ruff.toml"],
    "ruff-check":    ["pyproject.toml", ".ruff.toml", "ruff.toml"],
    "gitleaks":      [".gitleaks.toml", "gitleaks.toml"],
    "ty":            ["pyproject.toml", ".ai-engineering/manifest.yml"],
    "pytest-smoke":  ["pyproject.toml", "pytest.ini", "conftest.py"],
    "validate":      [".ai-engineering/manifest.yml"],
    "spec-verify":   [".ai-engineering/specs/spec.md", ".ai-engineering/specs/plan.md"],
    "docs-gate":     [".ai-engineering/manifest.yml"],
    # semgrep, pip-audit, pytest-full no aplican (no corren local en spec-104)
}
```

Hash function: `hashlib.sha256`, hex digest 64 chars truncado a primeros 32 chars como nombre de archivo (cache filename).

**Rationale**: whitelist explícita evita re-runs por archivos volátiles (timestamps, generados); whitelist conservadora (incluye solo configs que afectan el output del check). Cap de 32 chars en filename suficiente para colisión-resistance práctica (2^128). Fácil de auditar y de extender (añadir un check = añadir una entrada).

### D-104-10: Override flags y kill switch

CLI surface adicional, sin nuevos comandos top-level:

- `ai-eng gate run --cache-aware`: ON por defecto en orchestrator; lookup + miss-handling normal.
- `ai-eng gate run --no-cache`: skip lookup, fresh run, persiste resultado para próximo call. Use case: debug, audit, "no confío en el cache hoy".
- `ai-eng gate run --force`: skip lookup, **clear** entrada matching, fresh run, persiste. Use case: "sé que el cache es incorrecto, fuérzalo".
- `AIENG_CACHE_DISABLED=1` env: equivalente a `--no-cache` global; útil en CI para experiments o si el storage está corrupto.
- `ai-eng gate cache --status`: lista entries actuales + max-age + tamaño total. Read-only.
- `ai-eng gate cache --clear`: borra todo `.ai-engineering/state/gate-cache/`. Confirmación interactiva o `--yes`.

**Rationale**: regulated audience demanda audit override; los flags son CLI-flag-only sin nuevos subcommands top-level (NG-8 — surface mínima). Env var es belt-and-suspenders para CI scenarios donde el flag puede no llegar al subprocess. `gate cache --status/--clear` son sub-flags de un comando ya existente, no nuevos comandos.

## Risks

- **R-1 — Cache poisoning por config no-whitelisted**. Un archivo de configuración fuera de `_CONFIG_FILE_WHITELIST` cambia y el cache devuelve resultado obsoleto. *Mitigación*: max-age 24h techo; whitelist documentada y revisada per check; `--no-cache`/`--force` disponibles; integration test que muta archivos no-whitelisted y verifica que NO afectan el cache (comportamiento esperado, documentado).
- **R-2 — Stale cache tras `uv tool upgrade` manual**. Tool binary actualizado, version hash cambia → invalidación natural. *Mitigación*: `tool_version` es input del key; `<tool> --version` se ejecuta cada llamada (cheap); `--force` disponible.
- **R-3 — Cache size unbounded sin LRU**. Disco crece sin tope. *Mitigación*: LRU prune a 256 entries on every `_persist`; cap disco ≤16 MB; `gate cache --clear` para reset; integration test asserta cap respetado tras 1000 inserts simulados.
- **R-4 — Schema drift gate-findings.json entre spec-104 y spec-105**. spec-105 podría ampliar el schema y romper consumers. *Mitigación*: `schema` field versionado; fixture canónica en `tests/fixtures/gate_findings_v1.json`; spec-105 brainstorm referenciará este spec y debe mantener back-compat o emitir v2 (additive only).
- **R-5 — Race entre Wave 1 fixers y Wave 2 checkers**. Si Wave 2 arrancara antes de Wave 1 terminar, fixers escribiendo archivos que checkers leen. *Mitigación*: orchestrator espera explícitamente `wave1.return_code == 0` antes de spawnear Wave 2; integration test con sleep injection en Wave 1 verifica Wave 2 no arranca.
- **R-6 — Watch loop wall-clock false positive en CI lento**. Runner sobrecargado tarda >30 min en active phase. *Mitigación*: 30 min es cota conservadora (median CI run en este repo ≤10 min); on cap, exit 90 + watch-residuals.json + mensaje accionable; user re-invoca `/ai-pr` (sin penalización), historial documenta el evento.
- **R-7 — Verbosity cuts rompen un IDE no-Claude**. Codex o Gemini consumían sección removida. *Mitigación*: `tests/unit/test_skill_contract_completeness.py` asserta secciones obligatorias mantenidas; `ai-eng sync --check` mandatory en CI; alcance D-104-07 limitado a duplicados verificados (no contenido único).
- **R-8 — Local fast-slice missing CVE que `semgrep`/`pip-audit` capturan**. Dev pushea sin saber. *Mitigación*: CI authoritative ejecuta antes de merge; auto-complete bloqueado hasta CI green (mecanismo existente intacto); watch loop autofixea CI failures; never-weaken-gates respetado (gate ejecuta pre-merge, solo cambia el momento).
- **R-9 — gate-cache file corrupto (process killed mid-write)**. JSON inválido en disco. *Mitigación*: write atómico via `tempfile + os.rename`; corruption detection on read → log warn, treat as miss, regenerate; integration test que SIGKILL durante write y verifica recuperación.
- **R-10 — spec-101 aún en flight en esta misma rama**. Conflictos en `manifest.yml` o `policy/checks/stack_runner.py`. *Mitigación*: alcance spec-104 ortogonal a archivos spec-101 (verificado: spec-101 NO toca `ai-commit/SKILL.md`, `ai-pr/SKILL.md`, `watch.md`, ni añade nada en `policy/orchestrator.py`/`gate_cache.py`); install-smoke CI continúa corriendo unchanged; `manifest.yml` add-only (sección `gates.policy_doc_ref` nueva, no modifica `required_tools`); rebase final si surge conflicto resuelve trivialmente.
- **R-11 — CI cache miss rate alto por inputs volátiles**. Timestamps en CHANGELOG, generated files, etc. *Mitigación*: `_CONFIG_FILE_WHITELIST` excluye generated/timestamp; OQ-2 tracked para tuning post-merge basado en telemetría real (`wall_clock_ms` field en findings JSON).
- **R-12 — Single-pass collector miss una sutil dependencia entre checks**. E.g., `spec verify --fix` renombra archivo que `pytest -m smoke` carga. *Mitigación*: Wave 1 fixers serial mantiene ordering; integration test ejercita la secuencia completa con fixture realista; fallback `AIENG_LEGACY_PIPELINE=1` env restaura flujo secuencial pre-spec-104 (audit trail), documentado en CHANGELOG migration.
- **R-13 — `pytest -m smoke` no existe en proyectos consumers**. La marca smoke es convención, no estándar. *Mitigación*: si `pytest --collect-only -m smoke` retorna 0 tests, el check se skip-passes con info-level note; documentación explica cómo definir el marker (decorate fast unit tests).
- **R-14 — Watch loop emite watch-residuals.json mientras spec-105 risk-accept aún no existe**. User no puede ejecutar `ai-eng risk accept-all` referenciado en el mensaje. *Mitigación*: mensaje accionable incluye fallback "or fix manually and re-invoke `/ai-pr`"; spec-105 brainstorm (próximo) priorizará el CLI risk-accept para cerrar el loop; en este branch ambos spec-104 y spec-105 entregan juntos.

## References

- `.ai-engineering/notes/adoption-s2-commit-pr-speed.md` — predecessor finding y brainstorm (2026-04-24 + 2026-04-26).
- `.ai-engineering/notes/adoption-s3-unified-gate-risk-accept.md` — consumer del schema gate-findings.json v1 (próximo spec-105).
- `.ai-engineering/notes/spec-101-frozen-pr463.md` — spec-101 (S1) en mismo branch, frozen mientras coexiste.
- `.ai-engineering/LESSONS.md`:
  - "Stable framework orchestration should not become per-project config by default" (D-104-02 fundamento de no-configurable).
  - "Elimination can be the simplification, not migration" (D-104-07 fundamento de cuts quirúrgicos).
  - "manifest.yml es la fuente de verdad absoluta" (D-104-08 fundamento de CLI-layer central).
- `.ai-engineering/contexts/python-env-modes.md` — spec-101 D-101-12 contrato worktree-friendly que `gate-cache` storage respeta.
- CLAUDE.md Don't #1-9 — never-weaken-gates intacto bajo D-104-02 (gate ejecuta, solo cambia el momento; CI es shift-left de prod).
- Brainstorm 2026-04-26 sesión `/ai-brainstorm` — Q1-Q8 decisiones resumidas en `notes/adoption-s2-commit-pr-speed.md`.

## Open Questions

- **OQ-1**: ¿`pytest -m smoke` marker debe ser auto-decorado por `ai-eng install` (selecciona unit tests rápidos < 100ms) o esperado como project-owned? Default direction: project-owned con doc en README; revisitar si surge fricción de adopción.
- **OQ-2**: CI cache hit rate post-merge necesitará tuning del `_CONFIG_FILE_WHITELIST` basado en telemetría real (`wall_clock_ms` en findings JSON). Tracker: revisar tras primer mes de adopción.
- **OQ-3**: `watch-residuals.json` schema es idéntico a `gate-findings.json` v1; cuando watch loop emite findings de checks que solo corren en CI (semgrep, pip-audit), ¿el schema necesita campo `source: local|ci`? Tentative: añadir como campo opcional en schema v1.1 si spec-105 lo requiere; versionado lo permite sin breakage.
- **OQ-4**: ¿Debe orchestrator soportar resume tras crash mid-Wave-2? E.g., guardar estado parcial en `.ai-engineering/state/orchestrator-state.json` y skip checks ya completados al re-run. Default: NO en spec-104 (complica caché y debugging); el cache cubre el 95% del beneficio. Tracked para spec-105+ si surge necesidad real.
- **OQ-5**: ¿LRU prune a 256 entries es suficiente para repos grandes con muchas branches? Para repos con 50+ branches activos y 6 checks, son ~300 entries esperados. Tentative: 256 cubre la mayoría; bump a 512 si telemetría muestra eviction excesivo. Tracked.
