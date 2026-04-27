---
spec: spec-105
title: Unified Gate + Generalized Risk Acceptance — CLI, Orchestrator Lookup, Prototyping Mode, Auto-Stage
status: approved
effort: large
refs:
  - .ai-engineering/notes/adoption-s3-unified-gate-risk-accept.md
  - .ai-engineering/specs/spec-104.md
  - .ai-engineering/notes/adoption-s2-commit-pr-speed.md
  - .ai-engineering/notes/spec-101-frozen-pr463.md
  - .ai-engineering/contexts/python-env-modes.md
  - .ai-engineering/contexts/gate-policy.md
---

# Spec 105 — Unified Gate + Generalized Risk Acceptance

## Summary

`/ai-commit` y `/ai-pr` cierran el loop "acepto todos los riesgos actuales y publico" solo a medias hoy: spec-104 entregó single-pass collector + `gate-findings.json` v1 + memoización + watch bounds, pero la válvula de escape sigue rota en cinco gaps entrelazados. (1) Aceptar una CVE en `decision-store.json` no evita que `pip-audit`/`gitleaks`/`semgrep`/`ty` la vuelvan a flagear: el único read en `policy/checks/risk.py` es `check_expired_risk_acceptances()` (bloquea si la decisión ya expiró) y `check_expiring_risk_acceptances()` (warning a 7d), pero NO existe lookup `finding_is_accepted(rule_id, store)` que cruce findings con decisiones activas; resultado: governance en silos. (2) `decision_logic.create_risk_acceptance()` existe en `src/ai_engineering/state/decision_logic.py:221` con lifecycle completo (`renew_decision`, `revoke_decision`, `mark_remediated`) pero no está expuesto vía CLI: skills le piden al AI editar JSON crudo de `decision-store.json` con prompts manuales, contradiciendo audit-trail defensible. (3) `/ai-pr/handlers/watch.md:104` y `/ai-pr/SKILL.md:50` referencian `ai-eng risk accept-all .ai-engineering/state/gate-findings.json --justification "..."` como flujo canónico, **pero el comando no existe** — forward-reference rota. (4) `ruff format` modifica archivos durante Wave 1 del orchestrator pero no los re-stagea; el commit incluye solo el código pre-fix y el dev recibe `git status` con modificaciones unstaged post-commit. El hook Claude `auto-format.py` tiene el mismo gap edit-time. (5) No hay `manifest.yml.gates.mode` que permita modo prototipo: dev en spike acumula DECs en cada iteración (ruido en decision-store) o desactiva governance del todo (peligroso). spec-105 cierra los cinco gaps con: nuevo namespace CLI `ai-eng risk {accept, accept-all, renew, resolve, revoke, list, show}` (7 subcomandos cableados a las funciones existentes en `decision_logic.py`, cero duplicación), lookup `apply_risk_acceptances(findings, store, now) → (blocking, accepted)` orchestrator-level con telemetría a `framework-events.ndjson`, schema `gate-findings.json` v1.1 additive con `accepted_findings` array y `expiring_soon` field, modo `gates.mode: regulated|prototyping` (default `regulated`) con salvaguarda branch-aware + CI override + always-block tier (Tier 0+1: branch_protection/hook_integrity/gitleaks/expired-risks/ruff/ty/pytest-smoke jamás se saltan), y utility compartida `auto_stage.py` con safety estricta `S_pre ∩ M_post` invocada por orchestrator y hook Claude. Beneficio medible: el dev que dice "acepto todos los riesgos para publicar este push" lo hace con un comando, audit completo, mientras audiencia regulada (banking/finance/healthcare) preserva trazabilidad granular per-finding y nunca puede leak prototyping mode a producción.

## Goals

- G-1: `ai-eng risk accept-all .ai-engineering/state/gate-findings.json --justification "X" --spec 105 --follow-up "Y"` E2E: lee findings, crea N `DEC-*` entries (una por finding) con `batch_id` compartido, persiste en `decision-store.json`, retorna exit 0. Verificable por `tests/integration/test_risk_accept_all_e2e.py` que ejecuta el flujo completo sobre fixture project.
- G-2: Tras `accept-all`, el siguiente `ai-eng gate run` clasifica esos findings como `accepted` (no `blocking`); CLI imprime tabla compact "✓ ACCEPTED" + telemetry event emitido a `framework-events.ndjson`. Verificable por `tests/integration/test_gate_skip_accepted.py`.
- G-3: `manifest.yml.gates.mode: prototyping` reduce wall-clock de `ai-eng gate run` ≥40% sobre regulated en baseline python single-stack (skip Tier 2: ai-eng validate, spec verify, docs gate, risk-expiry). Verificable por `tests/perf/test_prototyping_mode_speedup.py`: sobre `tests/fixtures/perf_single_stack/`, regulated mode con warm gate-cache, 5-run median wall-clock (no CPU); aserción exacta `prototyping_p50_ms ≤ 0.6 × regulated_p50_ms` (variance bound: ambos sigma ≤15% del mean para que la run sea válida; rerun si flaky). Mirrors spec-104 perf test convention.
- G-4: Branch-aware escalation: cuando `current_branch ∈ protected_branches` (default `main|master|release/*`), `gate.py` ignora `manifest.gates.mode = prototyping` y ejecuta tier completo regulated; CLI imprime banner explícito `[REGULATED MODE — escalated from prototyping due to: protected branch]`. Verificable por `tests/integration/test_mode_escalation.py` con fixtures de branch.
- G-5: CI override: cuando `os.environ.get("CI") == "true"` (GitHub Actions, Azure Pipelines, GitLab CI), gate ejecuta regulated regardless of manifest. Verificable por `tests/integration/test_ci_override.py` con env mock.
- G-6: Tier allocation matrix invariante: Tier 0 (branch_protection, hook_integrity, gitleaks, expired_risk_acceptances) y Tier 1 (ruff format, ruff check --fix, ty check src/, pytest -m smoke) BLOQUEAN en cualquier mode (incluido prototyping); Tier 2 (ai-eng validate, ai-eng spec verify, docs gate, risk-expiry-warning) skip en prototyping, BLOQUEAN en regulated. Verificable por `tests/integration/test_tier_allocation.py` con matriz mode × tier.
- G-7: Schema `ai-engineering/gate-findings/v1.1` backward-compat con spec-104 v1 readers (additive only): nuevos fields `accepted_findings: [{check, rule_id, file, line, severity, message, dec_id, expires_at}]` y `expiring_soon: [dec_id]` opcionales; consumers v1 que ignoren campos desconocidos siguen funcionando. Verificable por `tests/unit/test_gate_findings_schema_v1_1.py` validando v1 fixtures + v1.1 fixtures + reader compat.
- G-8: Auto-stage utility `S_pre ∩ M_post` estricta: tras Wave 1 fixers (orchestrator) o tras `Edit`/`Write` (Claude hook), solo se re-stagean archivos que estaban en `git diff --cached --name-only` ANTES del fix. Archivos nuevos creados por fixers o archivos modificados pero no-staged jamás se stagean automáticamente. Verificable por `tests/unit/test_auto_stage_safety.py` con 8 fixtures cubriendo combinatorias S_pre/M_post.
- G-9: `ai-eng sync --check` PASS post-cambios; espejos en `.claude/`, `.github/`, `.codex/`, `.gemini/` regenerados consistentes con nuevo CLI surface y skill updates. Verificable en CI job existente.
- G-10: Cross-IDE parity — `ai-eng risk *` y `ai-eng gate run` producen output funcionalmente idéntico invocados desde 4 entornos IDE-emulados. Verificable por `tests/integration/test_risk_cross_ide.py` extendiendo el patrón spec-104.
- G-11: Telemetry observable: cada lookup que aplica una risk-acceptance emite `emit_control_outcome(category="risk-acceptance", control="finding-bypassed", metadata={dec_id, finding_id, expires_at, severity, check})` a `framework-events.ndjson`. Verificable por `tests/integration/test_telemetry_emission.py` validando event count + structure.
- G-12: prompt-injection-guard hook whitelist: `ai-eng risk accept-all` no es bloqueado por el guard cuando el JSON contiene patterns reconocidos como CRITICAL severity (e.g., gitleaks rule names que matchean keyword "secret"/"key"/"token"). Verificable por `tests/integration/test_prompt_guard_whitelist.py`.
- G-13: `/ai-commit` + `/ai-pr` SKILL.md actualizados: la línea forward-ref `ai-eng risk accept-all (spec-105)` reemplazada por reference real al CLI; ejemplos de error path actualizados. Verificable por `tests/unit/test_skill_forward_refs_resolved.py`.
- G-14: ≥80% test coverage en módulos nuevos (`cli_commands/risk_cmd.py`, `policy/checks/_accept_lookup.py`, `policy/auto_stage.py`, `policy/mode_dispatch.py`); cobertura agregada del repo no decrece. Verificable en CI coverage gate.
- G-15: 0 secrets (gitleaks), 0 vulnerabilities ≥medium (pip-audit + semgrep), 0 ruff/ty errors en código spec-105. Verificable en CI authoritative gate.
- G-16: Spec-101 + spec-104 contracts intactos: install-state, python_env modes (3), required_tools (14 stacks), gate_cache schema, watch loop bounds, gate-findings v1 readers continúan PASS. Verificable por test suite completa pre-existente.

## Non-Goals

- NG-1: Migración de OTROS skills (`ai-security`, `ai-governance`, `ai-release-gate`, `ai-skill-evolve`, `ai-platform-audit`, `ai-docs/handlers/solution-intent-*`) que mencionan "risk acceptance" en texto o tablas — esos solo lo referencian, no manipulan JSON. Sweep en spec-106 (S4) con `/skill-sharpen`. Solo `/ai-commit` y `/ai-pr` se actualizan en spec-105 porque tienen forward-refs rotas a comandos inexistentes.
- NG-2: `ai-eng risk export` (CSV/XLSX para compliance reports). Out of scope v1; `ai-eng risk list --format json` cubre 95% del caso uso, downstream tooling puede formatear.
- NG-3: Multi-actor approval workflow (sign-off de N revisores antes de aceptar un riesgo). Out of scope v1; `accepted_by` single-actor + `spec` reference + `justification` cubren defensa-en-profundidad para auditor.
- NG-4: Cross-machine decision-store sharing (local↔CI sync). Per spec-101 D-101-12 lesson: storage per-cwd, worktree-friendly. CI tiene su propio store si lo necesita; sin sync forzado.
- NG-5: Notifications externas (Slack/email/webhook) para DECs expirando. Fuera de framework — usuarios cron'ean `ai-eng risk list --expires-within 7 --format json` + tooling propio. Cross-ref: D-105-07 emite per-acceptance telemetry events a `framework-events.ndjson`; este es el integration point para notification tooling (consumers tail el ndjson + trigger Slack/email externamente).
- NG-6: Auto-renewal silencioso (renovar DEC sin intervención humana al llegar a expiry). Diseño explícito: cada renewal es decisión humana consciente con `justification` nueva. `_MAX_RENEWALS=2` mantenido.
- NG-7: Web UI dashboard para risk acceptance. Out of scope completo; framework es CLI-first por design.
- NG-8: spec-104 fallback `AIENG_LEGACY_PIPELINE=1` NO recibe lookup `finding_is_accepted`. Sunset signal: legacy es safety-net para rollback, no normal-use. Devs que necesitan risk-accept usan canonical orchestrator path.
- NG-9: Reescritura completa de `policy/gates.py`. spec-105 añade módulo `policy/mode_dispatch.py` para tier allocation y branch escalation; el dispatch existente en `gates.py` se invoca desde mode_dispatch sin modificación funcional.
- NG-10: Soporte para `gates.mode = prototyping` permanente sin salvaguarda. Branch-aware + CI override son no-configurables (hardcoded en framework). Manifest puede declarar `mode: prototyping` libremente; el código nunca lo honra cuando importa (protected branch o CI).
- NG-11: Migración de DECs existentes en `decision-store.json` para añadir `finding_id` y `batch_id`. Esos campos son opcionales en el schema; reads backward-compat. Solo nuevas decisiones (post-spec-105) los pueblan.
- NG-12: Cambios en `/skill-sharpen`, `MCP Sentinel security audit`, ni consolidación skills/agents — esos son spec-106 (S4) y spec-107 (S5) respectivamente.
- NG-13: Adición de `manifest.yml.gates.protected_branches` field. spec-105 reutiliza la Python constant `PROTECTED_BRANCHES` en `src/ai_engineering/git/operations.py` (existing, ya consumida por `policy/checks/branch_protection.py`); NO añade manifest-level override en spec-105. Si emerge necesidad de per-project customization, será spec separado.
- NG-14: TTL configurable per `risk_category` (e.g., risk-acceptance vs flow-decision con TTLs distintos). Out of scope v1; `_SEVERITY_EXPIRY_DAYS` constants en `decision_logic.py` se mantienen (15/30/60/90 days).
- NG-15: Migrar `ai-eng decision *` (existing namespace) a deprecation. Decisión Q5-A: ambos namespaces coexisten; `decision *` para architecture-decision/flow-decision genéricas, `risk *` para risk-acceptance lifecycle.

## Decisions

### D-105-01: Bulk-accept permisivo todas las severidades + audit trail per-finding

`ai-eng risk accept-all <findings.json>` acepta findings de cualquier severidad (incluyendo `critical`) en una sola pasada, sin flag adicional ni prompt interactivo. Cada finding se persiste como un `DEC-*` entry separado con TTL severity-default (`_SEVERITY_EXPIRY_DAYS`: critical=15d, high=30d, medium=60d, low=90d). Justification + spec_id + follow_up son mandatory non-empty (CLI rechaza vacíos con exit 2).

**Rationale**: el flujo user-meaningful es "acepto todos los riesgos actuales para publicar este push" — un solo comando, sin fricción artificial. CLAUDE.md Don't #9 (NEVER weaken gate severity) se respeta NO porque la severidad baje, sino porque cada acceptance es un fact discreto en el log con TTL, owner (`accepted_by`), spec reference, follow-up plan. Severity NO se modifica; el finding sigue clasificado como `critical`. La diferencia es: existe un fact "DEC-XXX activo cubriendo este finding hasta YYYY-MM-DD" que el lookup orchestrator-level (D-105-07) honra. Auditor puede listar todos los DECs critical activos en cualquier momento via `ai-eng risk list --severity critical`. Per-finding granularity (D-105-06) habilita renew/resolve independientes — pygments parchado resuelve solo ese DEC, los otros 16 continúan activos. Permisivo + granular + auditable es la combinación mínima para satisfacer el flujo "acepto todo y push" sin romper governance.

### D-105-02: `manifest.yml.gates.mode: regulated|prototyping` (default `regulated`)

Nuevo field en `.ai-engineering/manifest.yml`:

```yaml
gates:
  mode: regulated  # default; alternatives: prototyping
```

`regulated` (default): comportamiento actual + spec-104. Todos los gates ejecutan; gate-findings.json puede contener accepted_findings (D-105-07).

`prototyping`: skip Tier 2 checks (D-105-04); orchestrator + Claude hook + `ai-eng gate run` honran el mode SOLO cuando salvaguarda (D-105-03) no escala. CLI imprime banner top en cada gate run: `[PROTOTYPING MODE — Tier 2 governance checks skipped. Switch to regulated before merge.]`.

Mode change: el dev edita `manifest.yml`, commitea (commit pasa porque branch-protection no aplica para feature branches). En cuanto pushea a protected o abre PR target main, salvaguarda (D-105-03) escalа automáticamente.

**Rationale**: Q2-C eligió persistencia en manifest (vs flag ephemeral o auto-detect por branch) porque audiencia mixta — algunos proyectos son spike-permanente (research orgs, hackathon pre-incorporation), otros son production-only (banca). Persistencia en manifest es la realidad observable: si el proyecto entero es prototype, dev no quiere recordar `--prototyping` cada commit; si es regulated, default cubre. La fricción ilusoria de "olvidar volver a regulated" se anula con D-105-03 (branch+CI escalan independiente del manifest). LESSONS principle "stable framework orchestration should not become per-project config by default" se respeta porque el campo es estrictamente binario (regulated|prototyping), no un toggle libre que permite skipping arbitrario de checks.

### D-105-03: Salvaguarda branch-aware escalation + CI override + always-block tier

Tres mecanismos independientes que fuerzan `regulated` execution sin importar `manifest.gates.mode`:

1. **Branch-aware escalation** (`policy/mode_dispatch.py:resolve_mode()`):
   - Lee `current_branch = git symbolic-ref --short HEAD`.
   - Lee `protected_branches` desde Python constant `PROTECTED_BRANCHES` en `src/ai_engineering/git/operations.py` (existing constant, ya consumida por `policy/checks/branch_protection.py`). spec-105 NO añade nuevo campo a manifest; reutiliza la constant. Si en el futuro se requiere override per-project, será spec separado.
   - Si `current_branch` matchea cualquier pattern en `PROTECTED_BRANCHES` (fnmatch) → return `regulated` regardless of manifest.
   - CLI imprime: `[REGULATED MODE — escalated from prototyping due to: current branch '<branch>' matches protected pattern '<pattern>']`.

2. **CI environment override** (mismo `resolve_mode()`):
   - Si `os.environ.get("CI") == "true"` OR `os.environ.get("GITHUB_ACTIONS") == "true"` OR `os.environ.get("TF_BUILD") == "True"` (Azure Pipelines) → return `regulated` regardless of manifest y branch.
   - CLI imprime: `[REGULATED MODE — escalated from prototyping due to: CI environment detected (CI=true)]`.

3. **Pre-push target branch check** (`policy/checks/branch_protection.py:check_push_target()`):
   - En pre-push hook, parse `git rev-parse --abbrev-ref @{u}` (upstream) o el ref pasado al hook.
   - Si target ref matchea protected_branches → escalate to regulated.
   - Adicional al branch-aware (current_branch) — caso uso: dev en feature branch X pero pushing a `origin/main` directo.

Las tres salvaguardas son independientes y aditivas: cualquiera escalа. Manifest puede declarar `mode: prototyping` libremente; el código solo lo honra cuando NINGUNA de las tres triggers.

**Rationale**: Q3-A+D eligió defense-in-depth simple sobre date-management (B). Tres salvaguardas son no-configurables para preservar la garantía: ningún proyecto puede leak prototyping a producción. Branch-aware cubre el flow "olvidé revertir el manifest"; CI override cubre "CI ejecuta el manifest tal cual"; pre-push target cubre "dev pushing directo a main desde feature branch". Combinadas, blast radius de un manifest mal configurado se limita a feature branches privadas — exactly el scope donde prototyping es válido. Tier always-block (D-105-04) es el cuarto mecanismo (gitleaks + branch_protection + hook_integrity + expired_risks bloquean siempre).

### D-105-04: Tier allocation matrix (Tier 0 + Tier 1 always, Tier 2 mode-sensitive)

Tres tiers de checks invariantes en cualquier mode + un cuarto delegado a CI por spec-104:

| Tier | Checks | Wall-clock typ | Prototyping | Regulated | CI authoritative |
|---|---|---|---|---|---|
| **Tier 0 — Inviolable** | `branch_protection`, `hook_integrity`, `gitleaks --staged`, `expired_risk_acceptances` | ≤2s | ✅ block | ✅ block | ✅ block |
| **Tier 1 — Code health (TDD/clean code)** | `ruff format`, `ruff check --fix`, `ty check src/`, `pytest -m smoke` | ≤15s | ✅ block | ✅ block | ✅ block |
| **Tier 2 — Governance + ship-time** | `ai-eng validate`, `ai-eng spec verify`, `docs gate (LLM)`, `risk-expiry-warning` | ~25-40s | ⏭ skip | ✅ block | ✅ block (excepto docs gate, no determinista en CI) |
| **Tier 3 — Slow/network (spec-104 ya delegó)** | `pip-audit`, `semgrep`, `pytest full + matrix` | 30-120s | n/a | n/a | ✅ block |

Tier assignments hardcoded en `policy/mode_dispatch.py:_TIER_ALLOCATION` constant. NO configurable via manifest (LESSONS principle). Si proyecto necesita custom allocation, fork del context (out-of-scope v1).

Prototyping skip-list (`_TIER_2_CHECKS = ["ai-eng-validate", "ai-eng-spec-verify", "docs-gate", "risk-expiry-warning"]`) verificado por `tests/unit/test_tier_allocation_invariants.py`: todos los Tier 0+1 deben aparecer en `_ALWAYS_BLOCK`; ningún Tier 0+1 puede aparecer en skip-list bajo penalty de test failure.

**Rationale**: Q4-A reframed prototyping como "speed + clean code preserved" (no "todo vale"). Tier 0 protege secrets + branch + hook integrity (compliance básica que NO debe negociarse). Tier 1 protege TDD discipline + code health (clean code, type safety, smoke tests — los principios YAGNI/DRY/SOLID/KISS no son automatizables, pero sus síntomas obvios sí: lint errors, type errors, test failures). Tier 2 contiene checks ship-time (governance integrity, spec coherence, docs sync, risk-expiry) — estos solo importan al cruzar el boundary "voy a publicar"; durante exploration son ruido. Skipping ahorra ~25-40s wall-clock por gate run en prototyping (~G-3 ≥40% reduction). El user en spike obtiene fast-iteration con todos los safety nets que importan; cuando cambia a regulated antes del PR (o salvaguarda escalа), el surface completo se ejerce.

### D-105-05: Two CLI namespaces — `ai-eng risk *` + `ai-eng decision *` coexisten

Nuevo módulo `src/ai_engineering/cli_commands/risk_cmd.py` con 7 subcomandos especializados en risk-acceptance lifecycle:

| Comando | Función backend (existente) | Surface principal |
|---|---|---|
| `ai-eng risk accept` | `decision_logic.create_risk_acceptance()` | `--finding-id`, `--severity`, `--justification`, `--spec`, `--follow-up`, `--expires-at?`, `--accepted-by?` |
| `ai-eng risk accept-all <findings.json>` | `create_risk_acceptance()` × N | positional `<findings.json>`, `--justification`, `--spec`, `--follow-up`, `--max-severity?`, `--expires-at?`, `--dry-run`, `--accepted-by?` |
| `ai-eng risk renew <DEC-ID>` | `decision_logic.renew_decision()` | positional `<DEC-ID>`, `--justification`, `--spec`, `--actor?` |
| `ai-eng risk resolve <DEC-ID>` | `decision_logic.mark_remediated()` | positional `<DEC-ID>`, `--note`, `--actor?` |
| `ai-eng risk revoke <DEC-ID>` | `decision_logic.revoke_decision()` | positional `<DEC-ID>`, `--reason`, `--actor?` |
| `ai-eng risk list` | nuevo wrapper sobre `DecisionStore.risk_decisions()` | `--status (active\|expired\|superseded\|revoked\|all)`, `--severity?`, `--expires-within?`, `--format (table\|json\|markdown)` |
| `ai-eng risk show <DEC-ID>` | nuevo wrapper sobre `DecisionStore.find_by_id()` | positional `<DEC-ID>`, `--format (human\|json)` |

Existing `ai-eng decision {record, list, expire-check}` (en `cli_commands/decisions_cmd.py`) **intacto** — mismo storage (`decision-store.json`), namespace separado. `ai-eng risk list` filtra automáticamente a `risk_category == risk-acceptance`; `ai-eng decision list` muestra todas las categorías.

Toda la lógica de creación/renovación/revocación/remediation reside en `decision_logic.py` — los CLI commands son wiring + input validation + output formatting. Cero duplicación funcional.

**Acceptance criteria delegada a Phase 3 GREEN**: G-1 (E2E para `accept-all`) es el goal headline; per-command unit tests + smoke E2E para `accept`, `renew`, `resolve`, `revoke`, `list`, `show` se entregan en Phase 3 GREEN como `tests/integration/test_risk_cli_per_command.py` (7 happy-path E2Es + edge cases). Cada subcomando tiene gate de coverage individual ≥80%.

**Rationale**: Q5-A. Two namespaces alinea con mental model dominante: "risk acceptance" es el flujo diario (CVE flagged, dev acepta, push); "decision recording" es el flujo raro (architecture decision a documentar). Separarlos es kindness al user. `decision *` mantiene backward-compat (cero ruptura para scripts existentes); `risk *` es la nueva canonical namespace. Ambos comparten el mismo `DecisionStore` via `StateService`, garantizando consistency. La forward-ref `ai-eng risk accept-all` en `/ai-pr` y `/ai-commit` (línea 50 y 104 respectivamente) deja de estar rota: spec-105 entrega el comando real al mismo tiempo que sus consumers.

### D-105-06: N DEC entries per bulk-accept con `batch_id` + `finding_id` (additive schema)

Schema de `Decision` (en `state/models.py`) recibe dos fields opcionales NUEVOS:

```python
class Decision(BaseModel):
    # ... existing fields ...
    finding_id: str | None = Field(default=None, alias="findingId")
    batch_id: str | None = Field(default=None, alias="batchId")
```

`ai-eng risk accept-all <findings.json>` con N findings:
1. Genera `batch_id = uuid4()` (string).
2. Para cada finding f en findings.json:
   - Crea DEC entry: `id = f"DEC-{date}-{short_uuid}"`, `finding_id = f.rule_id`, `batch_id = batch_id_compartido`, `severity = f.severity`, `expires_at` calculado por severity-default.
   - `context = f"finding:{f.rule_id}"` (canonical format para lookup en D-105-07).
   - `decision = justification`, `follow_up_action = follow_up`, `accepted_by = git config user.email | --accepted-by override`.
   - `risk_category = RISK_ACCEPTANCE`, `status = ACTIVE`.
3. Persiste store atómicamente via `StateService.save_decisions()`.
4. Retorna N DEC entries creadas.

`ai-eng risk renew DEC-XXX` opera per-DEC (unaffected by batch_id); `ai-eng risk list --batch-id <uuid>` permite query batch view post-hoc.

DECs existentes (pre-spec-105) sin `finding_id`/`batch_id` siguen siendo legibles (fields opcionales). Nuevas DECs los pueblan; viejas no migran (NG-11).

**Rationale**: Q6-A. Granular per-finding satisface auditor regulado (cada finding aceptado = un fact discreto en log, defendible per-CVE). `batch_id` shared permite query "qué se aceptó en bloque el día X" sin perder atomicidad. `_MAX_RENEWALS=2` cap aplica per-DEC, evitando que un batch eternamente-renovado bypasse el cap implícitamente. Schema additive (2 fields opcionales) garantiza backward-compat: spec-104 readers que parsearon `Decision` sin finding_id continúan funcionando; pydantic `default=None` hace explícita la intención.

### D-105-07: Lookup orchestrator-level `apply_risk_acceptances` + telemetry

Nuevo módulo `src/ai_engineering/policy/checks/_accept_lookup.py`:

```python
def finding_is_accepted(
    finding: GateFinding,
    store: DecisionStore,
    *,
    now: datetime | None = None,
) -> Decision | None:
    """Return the active risk-acceptance Decision for finding.rule_id, or None.

    Matches by canonical context format 'finding:<rule_id>'.
    Filters: status==ACTIVE, risk_category==RISK_ACCEPTANCE, expires_at>now.
    """
    now = now or datetime.now(tz=UTC)
    canonical_hash = compute_context_hash(f"finding:{finding.rule_id}")
    return next(
        (d for d in store.decisions
         if d.context_hash == canonical_hash
         and d.status == DecisionStatus.ACTIVE
         and d.risk_category == RiskCategory.RISK_ACCEPTANCE
         and (d.expires_at is None or d.expires_at > now)),
        None,
    )


def apply_risk_acceptances(
    findings: list[GateFinding],
    store: DecisionStore,
    *,
    now: datetime | None = None,
    project_root: Path | None = None,
) -> tuple[list[GateFinding], list[AcceptedFinding]]:
    """Partition findings into (blocking, accepted).

    For each accepted finding, emit a telemetry event to framework-events.ndjson.
    """
    now = now or datetime.now(tz=UTC)
    blocking: list[GateFinding] = []
    accepted: list[AcceptedFinding] = []
    for f in findings:
        decision = finding_is_accepted(f, store, now=now)
        if decision is None:
            blocking.append(f)
        else:
            accepted.append(AcceptedFinding(finding=f, dec_id=decision.id, expires_at=decision.expires_at))
            if project_root is not None:
                emit_control_outcome(
                    project_root,
                    category="risk-acceptance",
                    control="finding-bypassed",
                    component=f.check,
                    outcome="bypassed",
                    source="orchestrator",
                    metadata={
                        "dec_id": decision.id,
                        "finding_id": f.rule_id,
                        "expires_at": decision.expires_at.isoformat() if decision.expires_at else None,
                        "severity": f.severity,
                        "file": f.file,
                        "line": f.line,
                    },
                )
    return blocking, accepted
```

Wiring: `policy/orchestrator.py:run_gate()` invoca `apply_risk_acceptances(wave2_findings, store, now=now, project_root=project_root)` después de Wave 2 collect, antes de emit `gate-findings.json`. El resultado `(blocking, accepted)` alimenta el output JSON (D-105-08) y el CLI display.

Legacy `AIENG_LEGACY_PIPELINE=1` fallback NO recibe lookup (NG-8) — sunset signal.

**Rationale**: Q7-D. Orchestrator-level es single point of integration: imposible olvidar el lookup en un check nuevo, todo finding pasa por el filtro central. Test surface mínimo: una función pura `apply_risk_acceptances(findings, store, now)` exhaustivamente unit-testable sin mocks de orchestrator/checks. Telemetry per-finding emitida via `emit_control_outcome` (ya existe en `state/observability.py`) garantiza audit observable: compliance officer queries `framework-events.ndjson` para "todos los bypass de Q1" sin parsear N gate-findings.json. Bounded por finding count (max ~100/run reasonable; R-9), zero impact en wall-clock.

### D-105-08: CLI output compact + expiring banner + schema v1.1 con `accepted_findings` + dual-version emit

CLI output de `ai-eng gate run` (default, sin `--verbose` ni `--json`):

```
⚠ EXPIRING SOON (1 of 3 active acceptances):
  DEC-2026-04-27-A1B2 expires in 4 days · gitleaks:aws-access-token
  Renew: ai-eng risk renew DEC-2026-04-27-A1B2 --justification "..."

Gate run: 5 findings (2 blocking, 3 accepted via decision-store)

✗ BLOCKING (2):
  gitleaks · stripe-secret-key · src/billing.py:89
  ruff · F841 · src/baz.py:12

✓ ACCEPTED (3) — audit logged to framework-events.ndjson:
  gitleaks · aws-access-token · src/legacy.py:45 → DEC-A1B2 (expires 2026-05-12)
  ruff · E501 · src/foo.py:42 → DEC-C3D4 (expires 2026-07-26)
  ruff · E501 · src/bar.py:88 → DEC-C3D4 (expires 2026-07-26)

Next: fix blockers OR ai-eng risk accept-all .ai-engineering/state/gate-findings.json --justification "..." --spec 105
```

Flags:
- `--verbose`: per-check inline (alternativa A de Q8). Útil debugging.
- `--json`: machine-readable JSON (gate-findings.json v1.1 schema directo). Para CI/scripts.
- `--no-color`: strip color codes (TTY auto-detect default ON; `FORCE_COLOR=1` override).

**Schema model relax (Phase 2 GREEN sub-task)**: `state/models.py:GateFindingsDocument` actualmente declara `schema_: Literal["ai-engineering/gate-findings/v1"]` y models hijos (`GateFinding`, `AutoFixedEntry`, `WallClockMs`) usan `ConfigDict(extra="forbid", frozen=True)`. spec-105 modifica:
1. `GateFindingsDocument.schema_` broadens a `Literal["ai-engineering/gate-findings/v1", "ai-engineering/gate-findings/v1.1"]` (Union).
2. `GateFindingsDocument.model_config` adds `extra="ignore"` para permitir consumers v1 leer docs v1.1 con `accepted_findings`/`expiring_soon` sin error (silent drop fields desconocidos).
3. `GateFindingsDocument` añade fields opcionales: `accepted_findings: list[AcceptedFinding] = Field(default_factory=list)` y `expiring_soon: list[str] = Field(default_factory=list)`.
4. Nuevo model `AcceptedFinding(BaseModel)` con fields `check, rule_id, file, line, severity, message, dec_id, expires_at`; `model_config = ConfigDict(frozen=True)` (extra forbidden por seguridad — spec-105 owna este nuevo schema).

**Dual-version emit logic** (`policy/orchestrator.py:_emit_findings()`): el producer chequea si `accepted_findings` Y `expiring_soon` están ambos empty. Si ambos empty → emite con `schema: "ai-engineering/gate-findings/v1"` (preserva binary-equivalent output para spec-104 producers/consumers que aún no esperan v1.1). Si cualquiera non-empty → emite con `schema: "ai-engineering/gate-findings/v1.1"`. Reader logic (`state/io.py:read_gate_findings()`) acepta ambas versiones via Literal Union. Test `test_emit_schema_version.py` valida ambos paths.

Schema `gate-findings.json` v1.1 (additive only, post-relax):

```json
{
  "schema": "ai-engineering/gate-findings/v1.1",
  "session_id": "<uuid4>",
  "produced_by": "ai-commit|ai-pr|watch-loop",
  "produced_at": "<ISO-8601 UTC>",
  "branch": "<git branch>",
  "commit_sha": "<HEAD sha or null>",
  "findings": [...],  // BLOCKING only (per spec-104 v1)
  "accepted_findings": [  // NEW in v1.1
    {
      "check": "gitleaks",
      "rule_id": "aws-access-token",
      "file": "src/legacy.py",
      "line": 45,
      "severity": "critical",
      "message": "AWS access key found",
      "dec_id": "DEC-2026-04-27-A1B2",
      "expires_at": "2026-05-12T00:00:00Z"
    }
  ],
  "expiring_soon": ["DEC-2026-04-27-A1B2"],  // NEW in v1.1; DECs used + expiring within 7 days
  "auto_fixed": [...],  // unchanged from v1
  "cache_hits": [...],
  "cache_misses": [...],
  "wall_clock_ms": {...}
}
```

v1 readers post-relax (con `extra="ignore"`) siguen leyendo v1.1 sin error — silent drop de `accepted_findings`/`expiring_soon`. Fixtures canónicas: `tests/fixtures/gate_findings_v1.json` (intacta), `tests/fixtures/gate_findings_v1_1.json` (nueva).

**Rationale**: Q8-E. Compact default es scannable (vs A verbose que satura con 50 findings); separación visual blocking vs accepted reduce cognitive load. Expiring banner top-of-output es defensa proactiva: devs no descubren expiry el día que el gate de pronto bloquea. Aprovecha `_WARN_BEFORE_EXPIRY_DAYS=7` constant ya en `decision_logic.py`. Schema v1.1 con dual-version emit (v1 cuando empty arrays, v1.1 cuando populated) preserva binary-equivalent output para spec-104 producers/consumers que no necesiten los nuevos fields — zero impact post-merge para consumers que no migraron. Field `expiring_soon` separado de `accepted_findings` permite alerts independientes (consumers que solo importa expiry no parsean el array completo). Model relax es Phase 2 GREEN sub-task explícito: sin él, G-7 backward-compat es imposible de satisfacer (verified contra current code: `Literal["...v1"]` strict mode rejects v1.1; `extra="forbid"` rejects unknown fields).

### D-105-09: Auto-stage shared utility default ON, ambas capas, `S_pre ∩ M_post` estricta

Nuevo módulo `src/ai_engineering/policy/auto_stage.py`:

```python
def capture_staged_set(repo_root: Path) -> set[str]:
    """Snapshot files currently staged: result of 'git diff --cached --name-only'."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z"],
        cwd=repo_root, capture_output=True, text=False, check=True,
    )
    return {p.decode("utf-8") for p in result.stdout.split(b"\x00") if p}


def capture_modified_set(repo_root: Path) -> set[str]:
    """Snapshot files currently modified: result of 'git diff --name-only'."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "-z"],
        cwd=repo_root, capture_output=True, text=False, check=True,
    )
    return {p.decode("utf-8") for p in result.stdout.split(b"\x00") if p}


def restage_intersection(
    repo_root: Path,
    s_pre: set[str],
    *,
    log_warning_for_unstaged: bool = True,
) -> AutoStageResult:
    """Re-stage S_pre ∩ M_post; warn for M_post \\ S_pre.

    Never stages files that were not previously staged.
    """
    m_post = capture_modified_set(repo_root)
    to_restage = sorted(s_pre & m_post)
    unstaged_modifications = sorted(m_post - s_pre)
    if to_restage:
        subprocess.run(
            ["git", "add", "--", *to_restage],
            cwd=repo_root, check=True,
        )
    return AutoStageResult(
        restaged=to_restage,
        unstaged_modifications=unstaged_modifications,
    )
```

Capa 1 — Orchestrator (`policy/orchestrator.py:run_wave1()`):
- Antes de Wave 1: `s_pre = capture_staged_set(repo_root)`.
- Tras Wave 1 fixers: `result = restage_intersection(repo_root, s_pre)`.
- CLI imprime tras Wave 1: `Re-staged 3 files modified by ruff: src/foo.py, src/bar.py, src/baz.py (disable: gates.pre_commit.auto_stage=false)`.
- Si `result.unstaged_modifications`: warning visible: `⚠ 2 files modified by fixers but not staged: src/qux.py, .ai-engineering/specs/_history.md. They remain unstaged. Stage manually if intended.`.

Capa 2 — Claude Code hook (`.ai-engineering/scripts/hooks/auto-format.py`):
- Antes de format: `s_pre = capture_staged_set(repo_root)`.
- Tras `ruff format <edited_file>`: `restage_intersection(repo_root, s_pre)`.
- Hook imports the same shared utility: `from ai_engineering.policy.auto_stage import capture_staged_set, restage_intersection`.
- **Template paridad mandatory**: `src/ai_engineering/templates/.ai-engineering/scripts/hooks/auto-format.py` debe actualizarse al mismo tiempo (template propaga a nuevos installs via `ai-eng install`); test `tests/unit/test_hook_template_parity.py` asserta byte-equivalence entre live hook y template.

Manifest field NEW: `gates.pre_commit.auto_stage: bool` (default `true`).

Override flags:
- `ai-eng gate run --no-auto-stage` (per-invocation override).
- `/ai-commit --no-auto-stage` (skill-level forwarding).

**Rationale**: Q9-E. Default ON resuelve gap 4 del note out-of-the-box; visibility (CLI warning + line en output) evita sorpresa. Safety estricta `S_pre ∩ M_post` cubre el pitfall del note: jamás staging de archivos nuevos accidentalmente. Shared utility en `policy/auto_stage.py` garantiza zero divergencia entre orchestrator + Claude hook (DRY honesto). Test `tests/integration/test_auto_stage_orchestrator_hook_parity.py` ejecuta el mismo fixture en ambos paths y asserta resultado idéntico. CHANGELOG migration note prominente para usuarios existentes (default flip de implicit-off a explicit-on).

### D-105-10: prompt-injection-guard whitelist `ai-eng risk accept-all`

`.ai-engineering/scripts/hooks/prompt-injection-guard.py` (existente) puede bloquear comandos cuyo argv contiene patterns CRITICAL (e.g., gitleaks rule names "aws-secret", "private-key" en el JSON pasado a accept-all). spec-105 añade whitelist:

```python
# .ai-engineering/scripts/hooks/prompt-injection-guard.py
WHITELISTED_COMMANDS = {
    "ai-eng risk accept-all",
    "ai-eng risk accept",
}
```

**Template paridad mandatory**: `src/ai_engineering/templates/.ai-engineering/scripts/hooks/prompt-injection-guard.py` debe actualizarse al mismo tiempo; test `tests/unit/test_hook_template_parity.py` cubre.

Detección: si el comando completo (sin flags) matchea exactamente un whitelisted, skip injection-pattern check pero log a `framework-events.ndjson` event `category="security", control="prompt-guard-whitelisted", metadata={command, argv_hash}`.

**Rationale**: Pitfall del note explícitamente. Sin whitelist, `ai-eng risk accept-all gate-findings.json` se rompe en práctica porque el JSON contiene secrets-related rule names que el guard interpreta como injection attempt. Whitelisting con audit log es la defensa balanceada: comando explícito del user (no injection) pasa; cualquier intento de injection vía OTROS comandos (e.g., `bash -c "...secret..."`) sigue bloqueado; whitelisted invocations dejan trail observable.

### D-105-11: Updates a `/ai-commit` + `/ai-pr` SKILL.md (forward-ref → real-ref)

Cambios mínimos en dos SKILL.md (NG-1 limita scope a estas dos, no las otras 12 que solo mencionan risk-accept en texto):

`.claude/skills/ai-commit/SKILL.md`:
- Sección "Process": añadir step después de gate failure: "If gate emits blocking findings and override appropriate, run `ai-eng risk accept-all .ai-engineering/state/gate-findings.json --justification \"<reason>\" --spec <spec-id> --follow-up \"<plan>\"`."
- Mirror sync regenera `.github/`, `.codex/`, `.gemini/` espejos.

`.claude/skills/ai-pr/SKILL.md`:
- Línea 50 actualizada: `ai-eng risk accept-all` ya no es forward-ref (spec-105) sino reference real.
- Ejemplo de error path en línea 127 actualizado.

`.claude/skills/ai-pr/handlers/watch.md`:
- Línea 104 (mensaje al user en wall-clock cap): `ai-eng risk accept-all .ai-engineering/state/watch-residuals.json` ya funciona; comando real disponible.
- Test `tests/unit/test_skill_forward_refs_resolved.py` asserta: ningún SKILL.md en `.claude/skills/` contiene la string `(spec-105)` después del merge (spec-105 está vivo, no es forward).

**Rationale**: Mínimo viable para cerrar las forward-refs rotas. Otros skills (ai-security, ai-governance, etc.) que mencionan risk-accept en texto sin invocarlo NO se modifican aquí (NG-1 → spec-106). Mirror sync mandatory por LESSONS principle "manifest.yml es la fuente de verdad absoluta" — un cambio en `.claude/skills/` requiere `ai-eng sync` para propagar a 4 IDEs.

### D-105-12: TDD single-shot delivery, 8 phases (Approach 2 per spec-104 _history pattern)

Delivery sigue exactly el muscle memory de spec-104 (commits 7325ab27→71d38d9d en `_history.md`):

| Phase | Commit pattern | Trabajo |
|---|---|---|
| **Phase 1 GREEN + Phase 2 RED** | `feat(spec-105): Phase 1 GREEN schema additions + Phase 2 RED orchestrator/CLI tests` | Phase 1 GREEN: minimal schema additions (`finding_id`, `batch_id` opcionales en `Decision` model — backward-compat); pydantic round-trip tests pass. Phase 2 RED: tests fallidos para CLI surface + orchestrator lookup + telemetry (~30-40 tests, marked `pytest.mark.spec_105_red` para ser excluidos del default CI run; CI green se preserva). Pattern mirrors spec-104 commit 7325ab27 / 718a0cd2: cada commit bundla GREEN code + next-phase RED tests; pure-RED commits no existen. CI continúa green. |
| **Phase 2 GREEN + Phase 3 RED** | `feat(spec-105): Phase 2 GREEN apply_risk_acceptances + schema relax + Phase 3 RED CLI tests` | Phase 2 GREEN: módulo `policy/checks/_accept_lookup.py`; `GateFindingsDocument` model relax (Literal Union v1+v1.1, `extra="ignore"`); `AcceptedFinding` model nuevo con `model_config = ConfigDict(frozen=True)` + pydantic round-trip test (mirror spec-104 pattern para `GateFindingsDocument`); tests Phase 1 cluster "schema + lookup + AcceptedFinding round-trip" pass. Phase 3 RED: tests CLI surface (~25 tests). |
| **Phase 3 GREEN + Phase 4 RED** | `feat(spec-105): Phase 3 GREEN CLI + Phase 4 RED orchestrator wiring tests` | Phase 3 GREEN: `cli_commands/risk_cmd.py` con 7 subcomandos (typer); per-command unit tests (accept/accept-all/renew/resolve/revoke/list/show) + smoke E2E para cada uno; tests "CLI" pass. Phase 4 RED: tests para orchestrator wiring + telemetry + dual-version emit (~20 tests). |
| **Phase 4 GREEN + Phase 5 RED** | `feat(spec-105): Phase 4 GREEN orchestrator + Phase 5 RED mode tests` | Phase 4 GREEN: wiring de `apply_risk_acceptances` en `orchestrator.py:run_gate()`; emit telemetry; dual-version emit logic; CLI output compact + expiring banner; tests "orchestrator + output" pass. Phase 5 RED: tests para mode + escalation + tier (~25 tests). |
| **Phase 5 GREEN + Phase 6 RED** | `feat(spec-105): Phase 5 GREEN mode + Phase 6 RED auto-stage tests` | Phase 5 GREEN: manifest field `gates.mode`; `policy/mode_dispatch.py`; branch-aware + CI override + pre-push target; tier matrix invariants; tests "mode + escalation + tier" pass. Phase 6 RED: tests para auto-stage shared utility (~15 tests). |
| **Phase 6 GREEN + Phase 7 RED** | `feat(spec-105): Phase 6 GREEN auto-stage + Phase 7 RED skills/docs tests` | Phase 6 GREEN: `policy/auto_stage.py`; integración orchestrator (Wave 1); integración hook + template parity; manifest field `gates.pre_commit.auto_stage`; override flags; tests "auto-stage parity" pass. Phase 7 RED: tests para forward-ref resolution + mirror sync + CLAUDE.md update (~10 tests). |
| **Phase 7 GREEN** | `feat(spec-105): Phase 7 GREEN whitelist + skills + docs + mirrors` | prompt-injection-guard whitelist (live + template); `/ai-commit` + `/ai-pr` SKILL.md updates; `contexts/gate-policy.md` update; new `contexts/risk-acceptance-flow.md`; CLAUDE.md Don't #9 clarification; `ai-eng sync` regenerate `.github/`/`.codex/`/`.gemini/` mirrors; CHANGELOG entry. Tests "skills/docs" pass. |
| **Phase 8** | `feat(spec-105): Phase 8 — verify+review convergence` | Run `/ai-verify --full` (4 specialists); fix any deterministic failures; run `/ai-review --full` (3 macro-agents); fix governance/architecture/feature concerns; iterate hasta convergencia (≤3 rounds). Coverage ≥80% módulos nuevos. Final phase elimina los markers `pytest.mark.spec_105_red` (todos los tests RED han sido GREENed). |

Cada phase commit es CI-green: pattern es bundling de GREEN code (current phase) + RED tests (next phase) en mismo commit. Tests RED están marked con `pytest.mark.spec_105_red` y son **excluidos por default** de CI runs (CI corre `pytest -m 'not spec_105_red'`); cada GREEN commit subsecuente remueve el marker correspondiente y los tests pasan al baseline normal. Phase 8 elimina cualquier marker residual. Pattern verified contra spec-104 commits 7325ab27 (Phase 1 GREEN gate_cache + Phase 2 RED orchestrator) y 718a0cd2 (Phase 2 GREEN orchestrator + Phases 3-8 RED). Cero CI bypasses, cero `--no-verify`, cero suppression.

**Rationale**: Approach 2 confirmado. Precedent directo (spec-104 mismo pattern, ya merged-with-CI-green workflow). RED-bundled-with-prior-GREEN establece contrato defendible para audit (cada commit shows "I closed X and committed to Y"; auditor lee commits secuencialmente para reconstruir contract evolution). Marker-based exclusion preserve CI green sin `--no-verify` o suppression — explícito y revocable (Phase 8 limpia markers). Cohesivo en un PR para revisor. Verify+review loop es práctica spec-104 ya internalizada.

### D-105-13: Branch consolidation `feat/specs-101-104-105-adoption`

Antes de PR, branch actual `feat/spec-101-installer-robustness` se renombra a `feat/specs-101-104-105-adoption` reflejando los 3 specs que entrega:
- spec-101 (installer robustness) — Frozen PR #463 reanudado
- spec-104 (commit/PR pipeline speed) — orchestrator + cache + bounded watch
- spec-105 (unified gate + risk-accept) — este spec

Procedimiento (orden importante para preservar PR #463 history):
1. Crear branch local nuevo: `git branch feat/specs-101-104-105-adoption feat/spec-101-installer-robustness`.
2. Push nuevo branch: `git push origin -u feat/specs-101-104-105-adoption`.
3. **Re-pointear PR #463** al nuevo branch ANTES de eliminar el viejo: `gh pr edit 463 --base <base-branch> --head feat/specs-101-104-105-adoption` (si #463 head era el viejo branch). Verificar PR sigue operacional.
4. Eliminar branch viejo solo si #463 está cerrado/mergeado o re-pointeado: `git push origin --delete feat/spec-101-installer-robustness` (solo si paso 3 confirmó). Si #463 aún open en old branch, **NO** eliminar — dejar stale.

PR title: `feat(adoption): specs-101+104+105 — installer + pipeline + risk-accept`. PR body sintetiza los 3 specs con sus respectivos goals; reviewer puede leer specs en orden (101 → 104 → 105) para entender la cadena.

**Rationale**: Q10 branch (a). Multi-spec PR es atypical pero alineado con R-14 spec-104 ("ambos spec-104 y spec-105 entregan juntos"). Branch rename es zero-cost (un comando), preserve commit history. PR body con ToC por spec facilita review (cada reviewer puede focus en su área de expertise: governance/CLI/orchestrator/installer).

### D-105-14: CLAUDE.md Don't #9 clarification one-liner

Cambio quirúrgico en `CLAUDE.md` Don't #9 (línea actual):

> 9. **NEVER** weaken a gate, threshold, or severity level without the full protocol: warn user of impact, generate a remediation patch, require explicit risk acceptance, persist to `state/decision-store.json`, and emit the outcome to `state/framework-events.ndjson`.

Añadir clarification al final:

> Note: risk-acceptance via `ai-eng risk accept` o `accept-all` NO es weakening — es logged-acceptance con TTL severity-default, owner (`accepted_by`), spec reference, y follow-up plan. Auditor puede listar todos los DECs activos via `ai-eng risk list`. Weakening sería cambiar `_SEVERITY_EXPIRY_DAYS`, suprimir checks (`# noqa`), o disable hooks — nada de eso es lo que `risk *` hace.

**Rationale**: Sin clarification, lectores de CLAUDE.md interpretan que `risk accept-all` viola Don't #9. La clarification deja explícito el threshold conceptual: weakening = bajar la barra; risk-acceptance = pasar la barra UNA vez con audit completo. Defensa contra mis-reading que future skills/agents podrían hacer.

## Risks

- **R-1 — `gates.mode = prototyping` leak a producción**. Dev configura prototyping, olvida revertir, mergea a main, broken/insecure code ship. *Mitigación*: D-105-03 triple salvaguarda (branch-aware + CI override + pre-push target). Manifest puede declarar prototyping libremente; código nunca lo honra cuando importa. Test `tests/integration/test_mode_escalation.py` cubre los 3 trigger paths.
- **R-2 — Schema v1.1 rompe consumers spec-104 v1**. Dashboard/CI tooling parsea gate-findings.json strict-mode y rompe con campos nuevos. *Verified state actual*: `state/models.py:898` declara `Literal["ai-engineering/gate-findings/v1"]` strict — el real blocker; un doc v1.1 unmodified rompería v1 readers por mismatch del Literal. `GateFindingsDocument.model_config` actualmente solo declara `populate_by_name=True, frozen=True` (sin `extra="forbid"` explícito; usa el pydantic default `extra="ignore"`). *Mitigación*: D-105-08 explicit Phase 2 GREEN sub-task relaja el model: `Literal[v1, v1.1]` Union (load-bearing fix) + `extra="ignore"` explícito (defense-in-depth contra future regression que añada `extra="forbid"`). Dual-version emit garantiza producers que NO pueblan los nuevos fields siguen emitting `schema: v1` (binary-equivalent, zero impact). v1 readers post-relax leen v1.1 con silent drop de fields desconocidos. Fixtures `tests/fixtures/gate_findings_v1.json` (intacta) + `gate_findings_v1_1.json` (nueva); integration test `test_v1_consumer_reads_v1_1.py` confirma compat post-relax.
- **R-3 — Bulk-accept con justification vacía bypassa governance**. CLI permite `--justification ""` y se persiste basura en decision-store. *Mitigación*: typer validator rechaza string vacío (length ≥10 chars mínimo razonable); spec_id mandatory; follow-up mandatory; test `test_cli_validates_inputs.py` cubre 8 edge cases (empty, whitespace-only, missing flag).
- **R-4 — prompt-injection-guard bloquea `ai-eng risk accept-all`**. JSON con rule names "aws-secret", "private-key" trigger injection patterns. *Mitigación*: D-105-10 whitelist; audit log de cada whitelisted invocation; test `test_prompt_guard_whitelist.py` valida que el comando real-world (con findings.json fixture) pasa el guard.
- **R-5 — Auto-stage stagea archivos no esperados**. Dev manualmente unstaged un archivo que ruff luego modifica; auto-stage podría re-stagear. *Mitigación*: D-105-09 estricta `S_pre ∩ M_post`. Si archivo NO está en S_pre (capturado ANTES de Wave 1), jamás se stagea — el flujo "manual unstage" es respected. Test `test_auto_stage_safety.py` con 8 fixtures combinatorias cubre edge cases (file unstaged-then-modified, file new-modified, file staged-then-modified, etc.).
- **R-6 — Migración de DECs existentes sin `finding_id`/`batch_id`**. `decision-store.json` en proyectos consumers tiene DECs viejos (legacy schema). *Mitigación*: NG-11 + fields opcionales (`default=None`). Reads backward-compat. Solo nuevas DECs (post-spec-105 `accept`/`accept-all`) los pueblan. Test `test_legacy_decision_read.py` valida read de fixtures pre-spec-105.
- **R-7 — Tier 2 skip en prototyping pierde governance issue ship-time**. Dev en prototyping no ejecuta `ai-eng validate`, `spec verify`, etc. Si pushea a feature branch (no protected), surface no se ejerce. *Mitigación*: CI authoritative ejecuta antes de merge (spec-104 D-104-02 pattern). Pre-push hook al targetear protected branch escalа a regulated (D-105-03). PR merge bloqueado hasta CI green. Issue ship-time se captura en CI antes de merge a main.
- **R-8 — Branch-aware escalation no detecta edge case "detached HEAD"**. `git symbolic-ref --short HEAD` falla en detached HEAD; `resolve_mode()` no sabe qué branch es. *Mitigación*: catch `subprocess.CalledProcessError` → fallback a `regulated` (más conservador siempre). Test `test_resolve_mode_detached_head.py` valida fallback.
- **R-9 — Telemetry events explosion**. Run con 1000 findings genera 1000 ndjson events, file size balloons. *Mitigación*: bound práctico de findings per gate run (~100 max razonable; >100 indica deeper issue, not normal flow). Configurable hard cap en `state/observability.py` ya existe (`_MAX_EVENTS_PER_RUN = 1000`); telemetry per finding cae bajo cap natural. ndjson rotation (out-of-scope spec-105) maneja file size si necesario en future.
- **R-10 — CLI flags/argv UX confuso**. Multitud de flags (`--justification`, `--spec`, `--follow-up`, `--max-severity`, `--expires-at`, `--accepted-by`, `--dry-run`...) intimidan al user. *Mitigación*: typer auto-generated `--help` para cada subcomando; defaults razonables (`--accepted-by` defaultea a `git config user.email`); `ai-eng risk --help` muestra resumen de namespace; doc `contexts/risk-acceptance-flow.md` con ejemplos paso-a-paso.
- **R-11 — Rebase risk con spec-101 + spec-104 in-flight**. Conflictos en `manifest.yml`, `policy/orchestrator.py`, `policy/gates.py`. *Mitigación*: spec-105 alcance ortogonal a spec-101 (verificado: spec-101 toca installer/python_env, spec-105 toca risk-accept/gates.mode). Spec-104 toca orchestrator/cache; spec-105 EXTIENDE orchestrator (additive). Rebase final trivial: spec-105 fields nuevos en manifest no chocan con spec-101 fields. Si conflicto surge, resolver favor de spec-105 newer fields (preserve both add).
- **R-12 — Skill updates rompen mirror sync**. `ai-eng sync --check` fail post-cambios. *Mitigación*: `ai-eng sync` se ejecuta en Phase 7 antes de PR; mandatory CI job que falla en mirror drift. Test `test_skill_mirror_consistency.py` cubre.
- **R-13 — Schema v1.1 spec-104 producers emit silently sin upgrade**. spec-104 emit code no fue actualizado para v1.1; sigue emitiendo v1. *Mitigación*: D-105-08 promotes la dual-version emit logic a decision explícita: `policy/orchestrator.py:_emit_findings()` emite v1 cuando `accepted_findings` Y `expiring_soon` ambos empty (binary-equivalent output, zero impact para spec-104 readers); emite v1.1 cuando cualquiera non-empty. Test `test_emit_schema_version.py` valida ambos paths.
- **R-14 — Existing consumers de gate-findings.json en producción**. CI scripts, dashboards externos, compliance tooling. *Mitigación*: schema additive (NG sólo añade, nunca remueve); `schema` field versionado; CHANGELOG entry "spec-105: gate-findings schema v1.1 (additive, backward-compat)"; consumer libraries pueden detectar version y branch. Communication: PR body lists v1→v1.1 changes explícitamente.
- **R-15 — `ai-eng risk list` performance con decision-store grande**. Proyecto con 500+ DECs activos podría tardar en filter/sort. *Mitigación*: in-memory filter es O(N), N≤500 → <50ms median. Si el problema surge en práctica, indexed lookup es spec-future. Bound natural: `_MAX_RENEWALS=2` evita acumulación eterna; resolve/revoke marca SUPERSEDED.
- **R-16 — Auto-stage hook break in Codex/Gemini IDE**. Capa 2 hook `auto-format.py` es Claude Code-specific (`.claude/hooks/`). Otros IDEs no tienen este hook. *Mitigación*: hook integration es opt-in per IDE (Claude Code only); orchestrator-level auto-stage (Capa 1) corre en cualquier IDE via `ai-eng gate run`. Cross-IDE parity preservada en CLI layer (D-104-08 pattern). Test `test_cross_ide_auto_stage.py` confirma orchestrator-level funciona idéntico en 4 IDEs (sin requerir Claude hook).
- **R-17 — `ai-eng risk accept-all` con findings.json malformed**. Schema invalid, missing campos, JSON parse error. *Mitigación*: pydantic strict validation contra `GateFindingsDocument` schema v1 OR v1.1; error claro con línea/column; exit 2 (input error, distinguible de exit 1 = gate failure). Test `test_accept_all_input_validation.py` cubre 6 malformed fixtures.

## References

- `.ai-engineering/notes/adoption-s3-unified-gate-risk-accept.md` — origen del spec (5 gaps documentados, code examples, pitfalls).
- `.ai-engineering/specs/spec-104.md` — predecessor archive: contrato `gate-findings.json` v1 + orchestrator + gate-cache + watch loop bounds. spec-105 EXTIENDE este surface.
- `.ai-engineering/notes/adoption-s2-commit-pr-speed.md` — sibling: speed concerns que motivaron spec-104; consumer del schema v1.
- `.ai-engineering/notes/spec-101-frozen-pr463.md` — sibling: installer robustness (3 modes, 14 stacks). spec-105 ortogonal.
- `.ai-engineering/contexts/python-env-modes.md` — spec-101 contract (worktree-friendly storage que spec-105 respeta).
- `.ai-engineering/contexts/gate-policy.md` — spec-104 documentation; spec-105 actualiza con risk-acceptance flow.
- `CLAUDE.md` Don't #9 — gate-weakening prohibition; spec-105 D-105-14 clarifies scope.
- `.ai-engineering/LESSONS.md`:
  - "Stable framework orchestration should not become per-project config by default" → D-105-04 tier hardcoded; D-105-02 mode field es binario estricto, no toggle libre.
  - "manifest.yml es la fuente de verdad absoluta" → D-105-11 mirror sync mandatory.
  - "Elimination is simplification, not migration" → D-105-05 no deprecate `decision *` namespace; coexisten.
- `src/ai_engineering/state/decision_logic.py:221` — `create_risk_acceptance()` existing function reused by D-105-05.
- `src/ai_engineering/state/decision_logic.py:279` — `renew_decision()` existing.
- `src/ai_engineering/state/decision_logic.py:358` — `revoke_decision()` existing.
- `src/ai_engineering/state/decision_logic.py:379` — `mark_remediated()` existing.
- `src/ai_engineering/state/models.py:849-906` — `GateFinding` + `GateFindingsDocument` (spec-104 v1 schema) extended to v1.1 by D-105-08.
- `src/ai_engineering/state/observability.py` — `emit_control_outcome` reused by D-105-07 telemetry.
- `src/ai_engineering/policy/orchestrator.py` — spec-104 orchestrator extended by D-105-07 wiring.
- `src/ai_engineering/policy/gates.py` — existing dispatch invoked from new `mode_dispatch.py` per D-105-04.
- `src/ai_engineering/policy/checks/risk.py` — existing expiry checks; D-105-07 adds `_accept_lookup.py` sibling module.
- `src/ai_engineering/cli_commands/decisions_cmd.py` — existing `decision *` namespace (intacto per D-105-05).
- `.ai-engineering/scripts/hooks/auto-format.py` — existing post-Edit hook extended by D-105-09 Capa 2.
- `.ai-engineering/scripts/hooks/prompt-injection-guard.py` — existing guard extended by D-105-10 whitelist.

## Open Questions

- **OQ-1**: ¿Qué ocurre si `ai-eng risk accept-all` recibe un finding con `rule_id` NULL/empty/whitespace? Tentative: skip el finding con warning visible; retornar exit 0 si todos los demás se aceptaron OK; emit telemetry event `category="risk-acceptance", control="invalid-rule-id-skipped"`. Decisión final en Phase 1 RED test design.
- **OQ-2**: ¿`prototyping` mode emite `gate-findings.json` con `accepted_findings: []` siempre, o lo omite del JSON? Tentative: omit cuando empty (preserve v1 readers que no esperan el field). Decisión final en Phase 4 GREEN.
- **OQ-3**: Cap de telemetría per gate run (max events emitidos a ndjson). Tentative: respeta `_MAX_EVENTS_PER_RUN = 1000` ya existente en `state/observability.py`. Si emerge presión de findings ≫1000, scope para spec-future (rotation).
- **OQ-4**: ¿Branch pattern `release/*` configurable o hardcoded en salvaguarda D-105-03? Decisión: hardcoded en spec-105 — reutiliza `PROTECTED_BRANCHES` Python constant en `src/ai_engineering/git/operations.py`. Si surge demanda per-project customization, spec-future añade manifest override. NG-13 lo deja explícito.
- **OQ-5**: ¿Auto-stage shared utility (`policy/auto_stage.py`) se publica como API pública (importable por external scripts) o internal only? Tentative: internal — el surface público externo es `ai-eng gate run`. Si hook Claude lo importa, hace via internal Python module path (`ai_engineering.policy.auto_stage`) — acceptable internal use.
- **OQ-6**: ¿`ai-eng risk show <DEC-ID> --format json` debe incluir history (renewal_count, renewed_from chain)? Tentative: yes, completar full history para auditor. Decisión final en Phase 3 GREEN.
- **OQ-7**: ¿Pre-push target check (D-105-03) parse el ref del hook stdin (git provide refs as `<local-ref> <local-sha> <remote-ref> <remote-sha>` líneas) o usa `git rev-parse --abbrev-ref @{u}`? Decisión: stdin parse es canonical path en POSIX (Linux/macOS); `@{u}` es fallback cuando `sys.stdin.isatty()` returns True OR stdin está empty (typical en hook invocations bypassed). Windows-via-Git-Bash usa stdin parsing (Git for Windows pipes hooks normalmente). PowerShell native git invocations sin hook NO triggern este path. Decided early para evitar Phase 5 thrash; documented en `policy/checks/branch_protection.py:check_push_target` docstring.
