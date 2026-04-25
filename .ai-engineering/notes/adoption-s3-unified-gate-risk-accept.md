# Adoption Sub-Spec S3 — Unified Gate + Generalized Risk Acceptance

**Discovery Date**: 2026-04-24
**Context**: Diagnóstico ai-engineering v4 adoption. Usuario quiere: "acepto todos los riesgos actuales, déjame push". Hoy un CVE aceptado en `decision-store.json` NO bypasea `pip-audit` — decision-store solo se lee para expiry check. No hay CLI `ai-eng risk accept`. Backlog post-S1.
**Spec**: backlog — pendiente spec formal

## Problem

Cinco gaps entrelazados que rompen el loop governance-con-escape-válvula:

1. **Risk-accept no bypasea check**: aceptar una CVE en `decision-store.json` no evita que `pip-audit` bloquee. El único read es `check_expired_risk_acceptances()` que bloquea si expiró, pero nunca permite pasar por finding-id.
2. **No CLI `ai-eng risk accept`**: `create_risk_acceptance()` existe en `src/ai_engineering/state/decision_logic.py:221` pero no está expuesto como subcomando. Skills le piden al AI editar JSON crudo.
3. **No bulk-accept surface**: no existe `ai-eng gate all --accept-all --justification "..."` one-shot para aceptar N findings con una sola decisión.
4. **Auto-fix no estagea**: `ruff format` corre `--check` en pre-commit (falla, no arregla). El hook Claude `auto-format.py` arregla post-Edit pero no hace `git add -u`.
5. **Cero memoización**: cada `git commit` re-ejecuta todos los checks aunque no haya cambiado nada.

## Findings

### Schema `decision-store.json` (pydantic en `src/ai_engineering/state/models.py:192`)
```json
{
  "id": "DEC-025",
  "context": "CVE-2026-4539 in pygments",
  "decision": "Accept until patched version available",
  "decidedAt": "2026-03-24T00:00:00Z",
  "expiresAt": "2026-04-23T00:00:00Z",
  "spec": "064",
  "contextHash": "<sha256hex>",
  "riskCategory": "risk-acceptance",
  "severity": "low",
  "acceptedBy": "ai-engineering-cli",
  "followUpAction": "...",
  "status": "active",
  "renewedFrom": null,
  "renewalCount": 0
}
```

### TTL por severidad (`decision_logic.py:26`)
- Critical 15d, High 30d, Medium 60d, Low 90d
- Max 2 renovaciones (`_MAX_RENEWALS=2`)
- Warning 7d antes de expiry

### Flujo gate actual (`policy/gates.py`)
- pre-commit ✅ acumula todos los errores antes de exit (ya está bien)
- pre-push pytest `-x` fails-fast **interno** pero acumula checks externos
- **NO** hay lookup "¿este finding tiene risk-accept activo?"

## Code Examples

### 1. CLI risk accept (wired a la función existente)
```bash
ai-eng risk accept \
  --finding-id CVE-2026-4539 \
  --severity high \
  --justification "Upstream patch 2026-06-01" \
  --spec 075 \
  --expires-at 2026-06-15

ai-eng gate all --json > findings.json
ai-eng risk accept-all findings.json \
  --justification "Sprint cut-over: backlog acepted, ticket #123 follow-up"

ai-eng risk renew DEC-025 --justification "Patch delayed 2 weeks"
ai-eng risk resolve DEC-025 --note "Patched in pygments 2.20.0"
```

### 2. Gate ↔ risk-accept lookup
```python
# src/ai_engineering/policy/checks/_accept_lookup.py (nuevo)
def finding_is_accepted(finding_id: str, store: DecisionStore) -> Decision | None:
    now = datetime.now(UTC)
    return next(
        (d for d in store.decisions
         if d.status == "active"
         and d.id == finding_id
         and (d.expires_at or now) > now),
        None,
    )

# En cada check (pip-audit, gitleaks, semgrep, ty, ...):
for raw in check_output.findings:
    if accepted := finding_is_accepted(raw.id, store):
        result.warnings.append(f"{raw.id} (risk-accepted DEC-{accepted.id}, expires {accepted.expires_at})")
    else:
        result.failures.append(raw)
```

### 3. Ruff auto-fix + stage (opt-in)
```yaml
# .ai-engineering/manifest.yml
gates:
  pre_commit:
    auto_fix: true  # default false
```
```bash
# Comportamiento con auto_fix=true
ruff format . && ruff check . --fix
git add -u $(ruff format --check . --quiet 2>&1 | cut -f1)
# solo re-stage archivos ya staged previamente (no archivos nuevos)
```

### 4. One-shot "acepto todo y push"
```bash
ai-eng gate all --json --no-exit > findings.json
ai-eng risk accept-all findings.json --justification "...." --spec 076
git push  # pre-push re-ejecuta gate, pero cada finding ya tiene accept activo → warning, no block
```

## Pitfalls

- Risk-accept lookup debe ser por **finding-id estable**: CVE-XXXX, semgrep rule-id, gitleaks rule-id. NO por mensaje humano.
- Bulk-accept DEBE exigir justification no-vacía + spec-id → sin esto es agujero de governance.
- `git add -u` auto-fix debe operar **solo sobre archivos ya staged** — no debe estagear nuevos archivos accidentalmente.
- Memoización NO debe cachear resultados de pre-push cuando la rama remota cambió.
- Respetar CLAUDE.md Don't #9: "NEVER weaken a gate severity…". Bulk-accept NO baja severidad — crea `DEC-*` entries trazables con TTL.
- El prompt-injection-guard hook puede bloquear `ai-eng risk accept-all` si el JSON contiene patterns CRITICAL → whitelist el comando.

## Related

- Diagnóstico Wave 1 Agent A3 en brainstorm 2026-04-24.
- Overlap con `adoption-s2-commit-pr-speed.md` (memoización).
- Files candidatos:
  - `src/ai_engineering/cli_commands/risk.py` (nuevo)
  - `src/ai_engineering/state/decision_logic.py` (ya existe `create_risk_acceptance`)
  - `src/ai_engineering/policy/gates.py` (wire lookup)
  - `src/ai_engineering/policy/checks/*.py` (añadir `_accept_lookup`)
  - `.claude/settings.json` hook `auto-format.py` (+ git add -u)
  - `.ai-engineering/manifest.yml` (flag `gates.pre_commit.auto_fix`)
- Constraint: CLAUDE.md Don't #9 — risk-accept NO es weakening; es logged acceptance con TTL y owner.
