# Adoption Sub-Spec S2 — Commit/PR Speed Optimization

**Discovery Date**: 2026-04-24
**Context**: Diagnóstico ai-engineering v4 adoption. `/ai-commit` medium-slow, `/ai-pr` con watch loop unbounded es el peor. Duplicación local↔CI masiva. Priorizamos S1 (installer robustness) primero; este spec va a la cola.
**Spec**: backlog — pendiente spec formal

## Problem

- 532 líneas entre `.claude/skills/ai-commit/SKILL.md` (126), `ai-pr/SKILL.md` (221) y `ai-pr/handlers/watch.md` (185).
- Toda la barra de quality tools (ruff, gitleaks, pytest, ty, pip-audit, semgrep) corre **local Y en CI** sin coordinación.
- `ai-eng spec verify` se llama dos veces en una sesión de `/ai-pr` con el mismo spec sin cambios.
- Dos subagentes `/ai-docs` **síncronos** bloquean el critical path antes de crear el PR.
- Cero memoización: cada re-run ejecuta todo from scratch aunque ninguno de los inputs haya cambiado.

## Findings

### Inventario `/ai-commit` (12 pasos)
auto-branch → spec read → `/ai-instinct --review` → stage → ruff format → ruff check --fix → `gitleaks protect --staged` → doc-gate (LLM) → `ai-eng validate` → `ai-eng spec verify` → compose msg → push.

### Inventario `/ai-pr` (14 pasos + watch loop)
Pasos 0-6 = **ai-commit completo re-ejecutado** → step 6.5: **2 `/ai-docs` subagentes síncronos** (CHANGELOG+README; docs-portal+quality-gate) → 6.7: `/ai-instinct --review` otra vez → 7: semgrep ~30-120s + gitleaks full-repo + pytest + ty + pip-audit → 8: **`ai-eng spec verify` segunda vez** → 9 commit+push → 10-13 PR ops → 14 watch loop (poll 60/180s, fix, re-run 0-6, push, bucle sin bound).

### Duplicación local ↔ CI
| Check | Local (commit) | Local (PR) | CI job |
|---|---|---|---|
| ruff check+format | ✅ | ✅ | `lint` |
| gitleaks | ✅ (staged) | ✅ | `security` (full-source) |
| pytest | — | ✅ (single-env) | matriz 3 OS × 3 Py |
| ty | — | ✅ | `typecheck` |
| pip-audit | — | ✅ | `security` |
| semgrep | — | ✅ (~30-120s) | `security` |
| `ai-eng validate` | ✅ | ✅ | `content-integrity` |

### Verbosity hotspots (restatement de reglas ya en CLAUDE.md)
- `ai-commit/SKILL.md:110-119` duplica la tabla Don't
- `ai-pr/SKILL.md:53-63` repite stack-detection que ya vive en `.ai-engineering/contexts/languages/`
- `ai-pr/SKILL.md:199-205` y `watch.md:169-185` se duplican entre sí

## Code Examples

### Quick win 1 — eliminar semgrep local en `/ai-pr`
```markdown
# .claude/skills/ai-pr/SKILL.md step 7
# ANTES: "Run semgrep --config auto ."
# DESPUÉS: eliminar línea; CI security job cubre scope completo.
```

### Quick win 2 — docs dispatch async post-PR
```markdown
# .claude/skills/ai-pr/SKILL.md step 6.5
# Antes: 2 subagentes síncronos en critical path
# Después: 1 subagente async fire-and-forget, ejecutado DESPUÉS de crear PR.
#         docs se mergean en commit follow-up, no bloquean PR creation.
```

### Quick win 3 — dedup `ai-eng spec verify`
```markdown
# Eliminar del step 6 de ai-commit cuando el caller es ai-pr (pasar flag IS_NESTED)
# O simplemente eliminar del step 6 siempre; mantener solo en ai-pr step 8 con --fix.
```

### Quick win 4 — memoización gate-cache
```json
// .ai-engineering/state/gate-cache.json (nuevo)
{
  "session": "2026-04-24T14:00:00Z",
  "checks": {
    "ruff-format": {
      "inputs_hash": "sha256:of-staged-blobs",
      "config_hash": "sha256:of-ruff-toml",
      "result": "pass",
      "ts": "2026-04-24T14:00:15Z",
      "ttl_seconds": 300
    }
  }
}
```
Invalidar en: cambios a `.ruff.toml`, `.gitleaks.toml`, `manifest.yml`, `pyproject.toml`.

## Pitfalls

- NO quitar `gitleaks` del pre-commit local — riesgo real de commit con secret. Mantener en hook.
- NO borrar pytest local entero → mantener smoke rápido (`pytest tests/unit -q`), matriz full solo en CI.
- Memoización debe invalidar por **config hash**, no solo por timestamp.
- `ai-eng spec verify` tiene side-effect (`--fix`) → si se ejecuta dos veces, el segundo run debe ser idempotente.
- Watch loop unbounded es peligroso — añadir `max_iterations: 3` configurable.

## Related

- Diagnóstico Wave 1 Agent A2 en la sesión de brainstorm 2026-04-24.
- Overlap con `adoption-s3-unified-gate-risk-accept.md` (memoización + gate unification).
- Files candidatos:
  - `.claude/skills/ai-commit/SKILL.md`
  - `.claude/skills/ai-pr/SKILL.md`
  - `.claude/skills/ai-pr/handlers/watch.md`
  - `src/ai_engineering/policy/gate_cache.py` (nuevo)
  - `.ai-engineering/manifest.yml` (flag `gates.cache.ttl_seconds`)
