---
spec: spec-107
title: MCP Sentinel Hardening + IDE Parity + Hash-Chained Audit Trail (S5)
status: approved
effort: large
refs:
  - .ai-engineering/notes/adoption-s5-mcp-sentinel-ide-parity.md
  - .ai-engineering/specs/spec-105.md
  - .ai-engineering/specs/spec-106.md
---

# Spec 107 — MCP Sentinel Hardening + IDE Parity + Hash-Chained Audit Trail

## Summary

MCP Sentinel audit (Wave 1 Agent A5, 2026-04-24) emitió verdict YELLOW: 1 MEDIUM (env-var RCE surface en `mcp-health.py:178` — lee `AIE_MCP_CMD_<SERVER>` de env y ejecuta vía `shlex.split + subprocess.run` sin allowlist de binarios; compromiso de env → RCE en cada Claude session) y 1 LOW (`.claude/settings.json` tiene `allow: ["*"]` demasiado permisivo). En paralelo, paridad IDE muestra 3 gaps: `.github/agents/explore.agent.md:2` declara `name: "Explorer"` mientras Claude/Codex/Gemini usan `ai-explore` (usuarios migrating no encuentran el agent en Copilot autocomplete), `templates/project/GEMINI.md:110` hardcodea `## Skills (44)` cuando real disk count es 47 (template hand-maintained, no auto-regen), y no existe `.github/chatmodes/` para crear alias slash-command `/ai-explore` Claude-style en Copilot. Adicionalmente, integración del NotebookLM "Securing Claude MCP Tools with Sentinel AI" (2026-04-25) identificó 6 controles deeper (H1-M4) cuyo ROI mayor para audiencia regulada (banking/finance/healthcare per memoria del usuario) son H1 Rug-pull detection (SHA256 hash de `required_tools.<stack>.<tool>` specs; mismatch = silent tampering del manifest tipo Postmark/XZ) y H2 Hash-chained audit trail (`prev_event_hash` per entry en `framework-events.ndjson` y `decision-store.json` para tamper-evident audit logs). spec-107 cierra los 5 items del note S5 + entrega los 2 controles deeper en arquitectura coherente con la división canónica de capas: hot-path determinístico (PreToolUse hook, $0 cost, inmune a prompt-injection del propio attack) + cold-path LLM (skill `/ai-mcp-sentinel` invocado on-demand para coherence analysis + rug-pull diff) + audit-trail tamper-evident. Reutiliza machinery existente: spec-105 risk-acceptance lifecycle (escape hatch universal), spec-106 `_shared/` skill pattern, spec-104 schema versioning. Cero nuevas governance surfaces; solo wiring + 1 nuevo skill + 1 catalog data file vendored desde `claude-mcp-sentinel` (proven upstream). Beneficio medible: imposible RCE via env-var injection (binary allowlist con escape hatch trazable), audit logs verificables criptográficamente (hash-chain detecta truncation/injection), tool-spec tampering visible al instante (Postmark/XZ-class attacks), Copilot users tienen paridad de invocación con Claude/Codex/Gemini (`@ai-explore` + `/ai-explore` ambos funcionan), `/ai-platform-audit` previene futuros drift de naming/counts en cualquier IDE.

## Goals

- G-1: `.ai-engineering/scripts/hooks/mcp-health.py` declara `_ALLOWED_MCP_BINARIES = frozenset({"npx","node","python3","bunx","deno","cargo","go","dotnet"})`; rechaza ejecución de binarios fuera del allowlist; permite extensión vía `ai-eng risk accept --finding-id mcp-binary-<name> ...` (DEC entry con TTL severidad-default). Verificable por `tests/integration/test_mcp_binary_allowlist.py` (8 allowed PASS, 5 malicious DENIED) + `tests/integration/test_mcp_binary_risk_accept.py` (DEC active concedes execution; expired DEC rejects).
- G-2: `src/ai_engineering/templates/.claude/settings.json` ships con narrow explicit `allow:` list (Read, Write, Edit, MultiEdit, Bash, Agent, Glob, Grep, Skill, TaskCreate, TaskUpdate, mcp__context7__*, mcp__notebooklm-mcp__*); cero modificación automática a `.claude/settings.json` en proyectos ya instalados. Verificable por `tests/integration/test_settings_template_narrow.py`.
- G-3: `ai-eng doctor` añade advisory check `permissions-wildcard-detected` que emite WARN (no FAIL) cuando detecta `["*"]` en `.claude/settings.json` `allow:`, con remediation pointer a `contexts/permissions-migration.md`. Verificable por `tests/integration/test_doctor_permissions_advisory.py`.
- G-4: `.github/agents/ai-explore.agent.md` (renamed from `explore.agent.md`) declara `name: ai-explore`; `.github/chatmodes/ai-explore.chatmode.md` provee slash invocation. Migration documentada en CHANGELOG con flag `BREAKING-LIKELY: Copilot agent renamed Explorer → ai-explore`. `scripts/sync_command_mirrors.py` AGENT_METADATA actualizado. Verificable por `tests/integration/test_copilot_explorer_rename.py`.
- G-5: `templates/project/GEMINI.md` reemplaza `## Skills (44)` por `## Skills (__SKILL_COUNT__)` y similar para agent count placeholder. `scripts/sync_command_mirrors.py` añade `write_gemini_md(canonical_skills, canonical_agents)` que renderiza placeholders con counts canónicos en cada sync. Verificable por `tests/unit/test_gemini_md_placeholders.py`.
- G-6: `/ai-platform-audit` SKILL.md añade Check 6 (agent naming consistency cross-IDE — extract `name:` de cada IDE agent file, flag cuando `name ≠ slug`), Check 7 (GEMINI.md skill count freshness — extract N de `## Skills (N)` y compare con disk), Check 8 (generic instruction-file count scan — recorre TODOS los CLAUDE.md/AGENTS.md/copilot-instructions.md/GEMINI.md y valida `## Skills (N)` y `## Agents (N)` headers vs canonical count). Verificable por `tests/integration/test_platform_audit_new_checks.py`.
- G-7: `.ai-engineering/references/iocs.json` vendored verbatim desde `claude-mcp-sentinel/references/iocs.json` con preservación de schema (sensitive_paths, sensitive_env_vars, malicious_domains, shell_patterns); `IOCS_ATTRIBUTION.md` registra source URL + commit hash + license. Verificable por `tests/unit/test_iocs_vendor_provenance.py`.
- G-8: `.ai-engineering/scripts/hooks/prompt-injection-guard.py` extendido con `load_iocs()` (fail-open si missing), matching contra 4 categorías IOC, decision values `allow|deny|warn`. Match sin DEC → deny; match con DEC active → warn (allow execution + log audit event). Verificable por `tests/integration/test_sentinel_runtime_iocs.py` (25+ fixtures cubriendo cada categoría) + `tests/integration/test_sentinel_risk_accept.py`.
- G-9: User allowlist usa risk-acceptance entries (NO archivo separado): `ai-eng risk accept --finding-id sentinel-<category>-<pattern_normalized> --justification "..." --spec ...`. DEC entries listables vía `ai-eng risk list --filter "sentinel-*"`. TTL severidad-default + renewal cap honored. Verificable parte de G-8 tests.
- G-10: New skill `/ai-mcp-sentinel` ships en `.claude/skills/ai-mcp-sentinel/SKILL.md` con 3 modes documentados: (a) `scan` — LLM coherence analysis de skills/MCP servers instalados, output VERDE/ROJO verdicts; (b) `audit-update <skill>` — diff baseline vs current, rug-pull pattern detection (Postmark-class threats); (c) `baseline set` — snapshot a `.ai-engineering/state/sentinel-baseline.json`. Skill propagado a 4 IDEs via sync. Verificable por `tests/integration/test_mcp_sentinel_skill_modes.py`.
- G-11: H1 — `state/manifest.py.load_required_tools` calcula SHA256 de cada tool spec entry; `install-state.json` schema añade `tool_spec_hashes: dict[str, str]` field. Cada `ai-eng install` compare current hash con baseline; mismatch → CLI banner CRITICAL + lookup `find_active_risk_acceptance(finding_id="tool-spec-mismatch-<tool>")`. DEC active permite + actualiza baseline; sin DEC → bloquea hasta acceptance/remediation. Verificable por `tests/integration/test_h1_rugpull_detection.py`.
- G-12: H2 — `framework-events.ndjson` y `decision-store.json` schemas añaden `prev_event_hash: str | None` field (additive backward-compat). Cada nueva entry computa SHA256 de la entry anterior y persiste. New module `state/audit_chain.py` provee `verify_audit_chain(file_path) → AuditChainVerdict` walker. `ai-eng doctor` añade advisory checks `audit-chain-events` y `audit-chain-decisions` (WARN, no FAIL). New CLI `ai-eng audit verify [--file events|decisions|all]` para invocación explícita. Verificable por `tests/unit/test_audit_chain_verify.py`.
- G-13: `ai-eng sync --check` PASS post-cambios; espejos en `.claude/`, `.github/`, `.codex/`, `.gemini/` regenerados consistentes con renamed agent + chatmode + GEMINI.md placeholders + new skill `/ai-mcp-sentinel` + extended `/ai-platform-audit`.
- G-14: 0 secrets, 0 vulnerabilities, 0 lint errors introducidos; pre-existing failures unchanged.
- G-15: Coverage ≥80% on new modules (`state/audit_chain.py`, IOC matching logic en `prompt-injection-guard.py`).

## Non-Goals

- NG-1: Migración automática (force-rewrite) de `.claude/settings.json` existentes en proyectos ya instalados. Templates ship narrow; existing files quedan untouched (decisión Q3-C).
- NG-2: Deprecation banners + sunset window para `@Explorer`. Rename es immediate breaking-change documentado en CHANGELOG (decisión Q4-D, scope acotado).
- NG-3: H1 graduated escalation (warn → block tras 3 missed renewals). Solo warn + risk-accept escape hatch (decisión Q7-1B, consistencia con Q2-D + Q6-2B pattern).
- NG-4: H2 chain en `install-state.json`. Solo `framework-events.ndjson` + `decision-store.json` (decisión Q7-2B; install-state mutates frecuentemente, audit value bajo).
- NG-5: M1 typosquatting Levenshtein detection in validate manifest. Defer.
- NG-6: M2 coherence/behavioral mismatch en CLI verify. Coherence analysis live solo en `/ai-mcp-sentinel scan` mode. Defer del CLI integration.
- NG-7: M3 cross-tool attack-path graphing (MCPhound-style). Research project; defer indefinidamente.
- NG-8: M4 Sentinel suppression-banner ("if these N suppressions removed, grade would be X"). Defer; overlaps con `/ai-governance` reporting.
- NG-9: IOC schema redesign. Vendor verbatim de claude-mcp-sentinel (decisión Q6-1A); cero diseño schema nuevo.
- NG-10: Automated IOC update mechanism (cron, webhook, etc.). Manual PR refresh quarterly documentado en `contexts/sentinel-iocs-update.md`.
- NG-11: Hard-gate enforcement de platform-audit checks 6/7/8. Advisory only en spec-107 (consistente con spec-106 D-106-04 advisory-first pattern). Hard-gate landed cuando ≥90% projects pasan.
- NG-12: PR creation in this spec. Branch consolidation final post spec-107 done.
- NG-13: Modificación del verify/review boundary. Spec-106 NG-7 honored.
- NG-14: Touching CLAUDE.md Don't rules. CLAUDE.md Don't #7 ("NEVER disable or modify `.claude/settings.json` deny rules") respetado: spec-107 AMPLIA narrow allow + extiende deny si necesario, jamás borra deny rules existentes.

## Decisions

### D-107-01: MCP binary allowlist conservadora + escape hatch via risk-accept

`.ai-engineering/scripts/hooks/mcp-health.py` declara `_ALLOWED_MCP_BINARIES = frozenset({"npx", "node", "python3", "bunx", "deno", "cargo", "go", "dotnet"})` (8 runtimes managed por package managers reconocidos). Cuando lee `AIE_MCP_CMD_<SERVER>` de env y `shlex.split` produce primer token fuera del allowlist:

1. Lookup `find_active_risk_acceptance(finding_id=f"mcp-binary-{token}", store)` en `decision-store.json` (reuse spec-105 D-105-07 lookup primitive).
2. DEC active → permite execution + emit telemetry event `category="mcp-sentinel", control="binary-allowed-via-dec"`.
3. DEC missing/expired → reject execution, log WARN con remediation hint: `MCP cmd binary 'X' not in allowlist. To enable, run: ai-eng risk accept --finding-id mcp-binary-X --severity low --justification "..." --spec spec-107 --follow-up "..."`.

Template hook (`src/ai_engineering/templates/.ai-engineering/scripts/hooks/mcp-health.py`) byte-equivalent.

**Rationale**: Q2-D. Allowlist conservadora cubre 8 stacks principales (Python/Node/Bun/Deno/.NET/Go/Rust) sin permitir RCE arbitrario via `bash -c "..."` injection. Escape hatch via spec-105 risk-accept reusa machinery existente — cero nuevo storage, audit trail completo (auditor lista exceptions vía `ai-eng risk list --filter "mcp-binary-*"`), TTL fuerza re-justification periódica. Patrón de "default-conservador + escape-trazable" se aplica consistentemente en D-107-02, D-107-03, D-107-08, D-107-09.

### D-107-02: settings.json narrow template + doctor advisory + cero force-rewrite

`src/ai_engineering/templates/.claude/settings.json` ships con narrow explicit allow list:

```json
"permissions": {
  "allow": [
    "Read", "Write", "Edit", "MultiEdit", "Bash", "Agent",
    "Glob", "Grep", "Skill", "TaskCreate", "TaskUpdate",
    "mcp__context7__*", "mcp__notebooklm-mcp__*"
  ],
  "deny": [...existing deny rules unchanged...]
}
```

`ai-eng doctor` añade advisory check `permissions-wildcard-detected`:
- Lee `.claude/settings.json` del proyecto target
- Si `allow` contiene `["*"]` → emit WARN advisory: `Permissions wildcard detected. Recommended: migrate to narrow explicit list. See contexts/permissions-migration.md.`
- Cero advisory si `allow` es lista explícita
- Severidad WARN, no FAIL — never blocks

Cero modificación automática de `.claude/settings.json` existentes. `ai-eng install` y `ai-eng update` no rewrite el archivo. User decide cuándo migrar.

`.ai-engineering/contexts/permissions-migration.md` documenta el por qué + cómo migrar + canonical narrow list + ejemplo de extensión via añadir nuevos tools al allow array.

**Rationale**: Q3-C. A (hard break) viola el pitfall del note ("NO break existing allowlists"); B (30-day deprecation con force-rewrite) introduce machinery compleja para minoría que se beneficia; D (escape hatch via risk-accept) mezcla semantics (settings.json es Claude Code config, no ai-engineering runtime; risk-accept aplicaría a runtime decisions, no static config); E (banner persistente) adds noise. C es lo mínimo necesario: nuevos proyectos seguros por default, cero forced disruption a existing, visibility/educación via doctor, user mantiene autonomy total.

### D-107-03: `/ai-explore` Copilot canonical rename + chatmode alias

Rename `.github/agents/explore.agent.md` → `.github/agents/ai-explore.agent.md`; update front-matter `name: ai-explore`. `scripts/sync_command_mirrors.py` `AGENT_METADATA["explore"]["name"]` actualizado de "Explorer" a "ai-explore" — único source of truth para naming cross-IDE.

Crear `.github/chatmodes/ai-explore.chatmode.md`:
```markdown
---
name: /ai-explore
description: Alias for @ai-explore agent (Claude-compatible slash invocation)
handler: agent:ai-explore
---
```

Resultado:
- `@ai-explore` funciona ✅ (autocomplete lo sugiere; aligned con Claude/Codex/Gemini convention)
- `/ai-explore` funciona ✅ (slash command pattern Claude-style)
- `@Explorer` rompe ❌ (small user surface; documentation cubre via CHANGELOG `BREAKING-LIKELY:` flag)

CHANGELOG entry: `BREAKING-LIKELY (Copilot only): Agent @Explorer renamed to @ai-explore for cross-IDE consistency. Slash command /ai-explore added.`

**Rationale**: Q4-D. A (rename solo) deja sin slash invocation; B (chatmode solo) no arregla autocomplete display; C (dual-name 30d) añade machinery para audiencia muy pequeña (Copilot Chat manual users); E (status quo + docs) entrega zero parity. D entrega paridad completa con dos vías de invocación + un documentation hit en CHANGELOG; cero machinery nueva (no banners, no sunset tracking, no dual files).

### D-107-04: GEMINI.md placeholders + 3 platform-audit checks (defense en profundidad)

`src/ai_engineering/templates/project/GEMINI.md`:
- Línea 110 `## Skills (44)` → `## Skills (__SKILL_COUNT__)`
- Si existe `## Agents (N)` header → similar treatment con `__AGENT_COUNT__`

`scripts/sync_command_mirrors.py` añade función `write_gemini_md(canonical_skills, canonical_agents)`:
1. Lee template
2. Reemplaza `__SKILL_COUNT__` con `len(canonical_skills)`
3. Reemplaza `__AGENT_COUNT__` con `len(canonical_agents)`
4. Aplica `translate_refs()` (Gemini-specific path translation)
5. Escribe a `.gemini/GEMINI.md`

`.claude/skills/ai-platform-audit/SKILL.md` añade 3 checks (advisory only):
- **Check 6 — Agent naming consistency cross-IDE**: extract `name:` de `.{claude,github,codex,gemini}/agents/*.md`. Flag cuando `name ≠ basename(file).removesuffix(".agent.md")`. Catch futuros Explorer-style mismatches.
- **Check 7 — GEMINI.md skill count freshness**: extract N de `## Skills (N)` en `.gemini/GEMINI.md`. Compare con `len(glob(".gemini/skills/ai-*/SKILL.md"))`. Flag mismatch.
- **Check 8 — Generic instruction-file count scan**: recorre `[CLAUDE.md, AGENTS.md, .github/copilot-instructions.md, .gemini/GEMINI.md]`. Para cada archivo, regex `^## Skills \((\d+)\)$` y `^## Agents \((\d+)\)$`. Compare cada N capturado con canonical count. Flag mismatches; defense en profundidad para cualquier futuro IDE adapter.

**Rationale**: Q5-D. A (solo SKILL_COUNT) deja agent count drift; B (placeholders + 2 checks) cubre el note exacto pero solo detecta drift en GEMINI.md específicamente; C (full generation) overlaps con validate "All instruction files list 47 skills"; D extiende B con check generic 8 que cubre TODOS los IDE files con un solo pattern, dando defense en profundidad para futuros IDE adapters sin coste runtime extra. Cero machinery nueva (regex + count comparison).

### D-107-05: IOC catalog vendored desde claude-mcp-sentinel

`.ai-engineering/references/iocs.json` vendored verbatim desde `https://github.com/<org>/claude-mcp-sentinel/blob/<commit>/references/iocs.json`:
- Schema preservado: `schema_version`, `description`, `last_updated`, `sensitive_paths`, `sensitive_env_vars`, `malicious_domains`, `shell_patterns` (4 categorías).
- Cero modificaciones — adopt verbatim para reducir maintenance surface.

`.ai-engineering/references/IOCS_ATTRIBUTION.md` documenta:
- Source URL upstream
- Vendor commit hash (immutable reference)
- Vendor date
- License terms (MIT or upstream license)
- Contact info para upstream PR-back updates

`.ai-engineering/contexts/sentinel-iocs-update.md` documenta refresh cadence:
- Quarterly manual PR (Q1, Q2, Q3, Q4 review windows)
- Process: fetch latest upstream, diff vs vendored, document changes, commit con CHANGELOG entry
- Hot security fixes pueden hacer refresh out-of-band con `security:` commit prefix

Template `src/ai_engineering/templates/.ai-engineering/references/iocs.json` byte-equivalent al vendored.

**Rationale**: Q6-1A. claude-mcp-sentinel ya tiene 5 categorías curadas en producción; copiar y vendor es 0-effort, 0-design risk. Adapt (1B) introduce diseño nuevo + tests sin claro beneficio. Hybrid (1C) añade merge logic prematura para casos uso enterprise no validados aún. 1A es ship-rápido battle-tested; refresh manual quarterly es razonable cadence para datos que cambian raras veces.

### D-107-06: prompt-injection-guard IOC extension + 3-valued decision

`.ai-engineering/scripts/hooks/prompt-injection-guard.py` extendido:

```python
def load_iocs() -> dict:
    """Fail-open: if missing/corrupt, return empty dict (no IOC matching)."""
    candidates = [
        Path(__file__).parent.parent.parent / "references" / "iocs.json",
        Path.cwd() / ".ai-engineering" / "references" / "iocs.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                continue
    return {}

def evaluate_against_iocs(payload: dict, iocs: dict, store: DecisionStore) -> Decision:
    """Returns one of: 'allow', 'deny', 'warn' with reason."""
    # 1. Match payload contra 4 categorías IOC
    matches = []
    for category in ("sensitive_paths", "sensitive_env_vars", "malicious_domains", "shell_patterns"):
        for pattern in iocs.get(category, {}).get("patterns", []):
            if pattern_matches(payload, pattern):
                matches.append((category, pattern))
    
    if not matches:
        return Decision(action="allow")
    
    # 2. Para cada match, lookup risk-acceptance
    blocking = []
    accepted = []
    for category, pattern in matches:
        finding_id = canonical_finding_id(category, pattern)  # e.g., "sentinel-sensitive_paths-~_.ssh"
        if find_active_risk_acceptance(finding_id, store):
            accepted.append((category, pattern, finding_id))
        else:
            blocking.append((category, pattern, finding_id))
    
    # 3. Decision: deny if any blocking, warn if all accepted
    if blocking:
        return Decision(action="deny", reason=f"Blocked: {blocking[0]}")
    return Decision(action="warn", reason=f"Risk-accepted: {accepted[0][2]} (DEC active)")
```

Decision propagated to PreToolUse hook output JSON: `{"decision": "deny|warn|allow", "reason": "..."}` per claude-mcp-sentinel protocol.

Template byte-equivalent.

**Rationale**: Q6-1A + Q6-2B integration. Match contra IOC sin DEC = deny (default deny stance). Match con DEC active = warn (allow execution but log audit event for compliance trace). No match = allow silently. Patrón consistent con prior whitelist (spec-105 D-105-10) que ya usa claude-mcp-sentinel-style decision JSON. Fail-open en `load_iocs()` garantiza que si IOC file está corrupto/missing, hook no rompe Claude Code (per claude-mcp-sentinel design philosophy: "missed detection annoying, broken Claude Code worse").

### D-107-07: User allowlist via risk-acceptance entries (cero new file format)

User exceptions a IOC matching usan spec-105 risk-accept entries directamente:

```bash
ai-eng risk accept \
  --finding-id sentinel-sensitive_paths-~/.ssh/config \
  --severity low \
  --justification "I deploy via SSH; ~/.ssh/config access is operational" \
  --spec spec-107 \
  --follow-up "Migrate to ssh-agent forwarding by Q3 2026"
```

Canonical `finding_id` format: `f"sentinel-{category}-{pattern_normalized}"` donde `pattern_normalized` lower-case + replace `/`→`_`. Garantiza idempotencia + lookup determinístico.

`ai-eng risk list --filter "sentinel-*"` muestra exceptions actuales del proyecto.

Cero archivo nuevo (`.security/sentinel-allowlist.json` rejected). Audit trail via decision-store; TTL severidad-default (low → 90d) fuerza re-justification.

**Rationale**: Q6-2B. 2A (`.security/sentinel-allowlist.json` per-dev gitignored) carece de audit trail — atacante puede modificar sin detection. 2C (hybrid) duplica mechanism. 2B reusa toda la spec-105 machinery: lifecycle (accept/renew/resolve/revoke), TTL, expiry warnings, audit-chain protection (D-107-12). Compliance officer puede listar todas las allowlist exceptions de cualquier proyecto via single CLI command. Self-service con accountability built-in.

### D-107-08: New skill `/ai-mcp-sentinel` con 3 modes (cold-path LLM)

`.claude/skills/ai-mcp-sentinel/SKILL.md` ships con front-matter:
```yaml
---
name: ai-mcp-sentinel
description: "On-demand MCP/skill security audit using LLM coherence analysis. Use for: skill installation review, post-update rug-pull detection, baseline-vs-current diff. Cold-path LLM (NOT runtime); for runtime protection see prompt-injection-guard hook (Capa 1)."
effort: high
---
```

3 modes documentados:

**Mode 1 — `scan`**: invocado como `/ai-mcp-sentinel scan [--target <path-or-skill-name>]`.
- LLM analiza skills/MCP servers instalados localmente
- Coherence analysis: compara declared `description` vs observed code behavior
- Output VERDE/ROJO verdicts per skill (e.g., GREEN = "markdown formatter only reads markdown files"; RED = "skill claims markdown formatter but reads `~/.ssh/`")
- Output structured JSON + human report

**Mode 2 — `audit-update <skill>`**: invocado para detectar rug-pull patterns post-update.
- Lee snapshot de baseline (de `state/sentinel-baseline.json`)
- Compara con current files del skill
- Flags semantic changes (e.g., new network calls, new file accesses, new env reads) que aparecen sin justification clear
- Postmark-class threat detection

**Mode 3 — `baseline set [--target <skill-or-all>]`**: invocado para anchor un point-in-time snapshot.
- Lee skills/MCP files actuales
- Calcula content hashes + extracted capabilities (network calls, file accesses, env reads)
- Persiste a `.ai-engineering/state/sentinel-baseline.json`
- Sin baseline, audit-update no puede comparar

Skill propagado a 4 IDEs (`.claude/`, `.github/`, `.codex/`, `.gemini/`) via `ai-eng sync`.

**Rationale**: Q6-3B. 3A (scan only) deja rug-pull detection (#1 threat MCP ecosystem 2026) sin cobertura. 3C (scan + audit-update + baseline + report) añade reporting que ya existe en `/ai-governance`. 3B es sweet spot: 3 modes cubren los 3 casos uso distintos sin duplicar functionality existente. Cold-path LLM apropiado para análisis costoso/raro (post-install, pre-merge, ad-hoc). Hot-path runtime cubierto por D-107-06 (prompt-injection-guard determinístico).

### D-107-09: H1 Tool spec hash + warn + risk-accept escape

`src/ai_engineering/state/manifest.py.load_required_tools` calcula SHA256 de cada tool spec entry:

```python
def compute_tool_spec_hash(spec: dict) -> str:
    """Canonical-JSON hash of a tool spec entry."""
    canonical = json.dumps(spec, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

`InstallState` model (`state/models.py`) añade:
```python
class InstallState(BaseModel):
    # ... existing fields ...
    tool_spec_hashes: dict[str, str] = Field(default_factory=dict)
    # Maps "stack:tool" → SHA256
```

`installer/service.py` flow:
1. Lee current `manifest.required_tools.<stack>.<tool>` per tool installed
2. Calcula `current_hash = compute_tool_spec_hash(spec)`
3. Compare con `state.tool_spec_hashes.get(f"{stack}:{tool}", None)`
4. **First run** (baseline empty): populate `state.tool_spec_hashes[key] = current_hash`, no alert
5. **Subsequent run, mismatch detected**:
   - Lookup `find_active_risk_acceptance(finding_id=f"tool-spec-mismatch-{stack}-{tool}", store)`
   - DEC active → permite + actualiza baseline + log telemetry event
   - DEC missing → CLI banner CRITICAL + remediation hint:
     ```
     ⚠ TOOL SPEC MISMATCH detected for {stack}:{tool}
       Baseline hash: {old_hash[:12]}
       Current hash:  {new_hash[:12]}
     This may indicate: legitimate manifest update OR silent tampering.
     To accept this change consciously:
       ai-eng risk accept --finding-id tool-spec-mismatch-{stack}-{tool} \
         --severity high --justification "..." --spec spec-107 \
         --follow-up "..."
     ```
   - Bloquea `ai-eng install` continuation hasta acceptance/manual fix

**Rationale**: Q7-1B. 1A (warn only) es laxo — silent acceptance del cambio. 1C (block + CODEOWNERS review only) es draconiano: upstream npm pkg update legítimo bloquea equipo entero hasta CODEOWNERS humano + rompe el pattern coherente que establecimos en Q2-D + Q6-2B (risk-accept como universal escape hatch). 1D (graduated) needs tracking de "renewal count missed" inexistente. 1B reusa machinery existente con audit defendible — "alguien aprobó cambio en X tool spec el día Y para spec-Z con justification W".

### D-107-10: H2 Hash-chained audit trail (events + decisions)

Schema additions:

`framework-events.ndjson` cada entry adds optional field:
```python
class ControlOutcomeEvent(BaseModel):
    # ... existing fields ...
    prev_event_hash: str | None = Field(default=None, alias="prevEventHash")
```

`Decision` model (`state/models.py`) adds:
```python
class Decision(BaseModel):
    # ... existing fields including spec-105 finding_id, batch_id ...
    prev_event_hash: str | None = Field(default=None, alias="prevEventHash")
```

Both fields backward-compat (`default=None` accommodates legacy entries).

Hash computation logic in `state/audit_chain.py` (new module):

```python
def compute_entry_hash(entry: dict) -> str:
    """SHA256 of canonical-JSON entry (excluding the prev_event_hash field itself)."""
    payload = {k: v for k, v in entry.items() if k != "prev_event_hash"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_audit_chain(file_path: Path) -> AuditChainVerdict:
    """Walk entries; verify each entry's prev_event_hash matches sha256 of prior entry."""
    # ... walks entries in order, validates chain, returns verdict + first_break_index if any ...
```

`emit_control_outcome()` y `decision_logic.create_risk_acceptance()` updated:
1. Read last entry from target file
2. Compute `prev_hash = compute_entry_hash(last_entry)` (or None if file empty)
3. Set new entry `prev_event_hash = prev_hash`
4. Append to file

`ai-eng doctor` adds advisory checks:
- `audit-chain-events`: runs `verify_audit_chain(framework-events.ndjson)`; if break → WARN (not FAIL)
- `audit-chain-decisions`: runs `verify_audit_chain(decision-store.json)`; if break → WARN

New CLI: `ai-eng audit verify [--file events|decisions|all]` para invocación explícita con detailed report.

**Rationale**: Q7-2B. 2A (events only) deja decision-store sin protección — atacante que comprometa repo puede borrar DEC entries históricos para ocultar suppressions previas. 2C (events + decisions + install-state) añade overhead a install-state mutations frecuentes sin valor adicional para auditor (install-state es mecánico, no legal evidence). 2B cubre los 2 surfaces que importan al auditor: "qué pasó cuando" (events) + "qué decisiones se tomaron" (DEC). WARN-only en doctor (no FAIL) preserva ergonomy — un broken chain debe ser investigated explícitamente, no auto-block toda operación.

### D-107-11: TDD bundled GREEN+RED commit pattern (mirror spec-105/106)

Same workflow as spec-105 + spec-106: cada phase commit bundla GREEN code (current phase) + RED tests for next phase, marked `@pytest.mark.spec_107_red` y excluded from CI default run. CI command: `pytest -m 'not spec_105_red and not spec_106_red and not spec_107_red'` post-spec-107 lifecycle. Phase 6 final: zero residual markers.

**Rationale**: Spec-105 + spec-106 muscle memory confirmado. Same audit trail benefits. Same CI-green discipline.

### D-107-12: 6 phases (smaller scope than spec-105's 8, mirror spec-106 pattern)

| Phase | Scope |
|---|---|
| 1 | MCP binary allowlist (D-107-01) + escape hatch wiring + Phase 2 RED tests |
| 2 | settings.json narrow template (D-107-02) + doctor advisory + Phase 3 RED tests |
| 3 | Explorer rename + chatmode (D-107-03) + GEMINI.md placeholders (D-107-04) + 3 platform-audit checks + Phase 4 RED tests |
| 4 | IOC catalog vendored (D-107-05) + prompt-injection-guard extension (D-107-06) + risk-accept user allowlist (D-107-07) + Phase 5 RED tests |
| 5 | New skill `/ai-mcp-sentinel` (D-107-08) + H1 tool-spec hash detection (D-107-09) + Phase 6 RED tests |
| 6 | H2 audit chain (D-107-10) + verify+review convergence + history update |

**Rationale**: 7 deliverables sustantivos vs spec-105's 11 vs spec-106's 5. 6-phase rhythm mirror spec-106 que demostró ser sustainable.

## Risks

- **R-1 — MCP binary allowlist breaks legitimate user flows**. Algunos usuarios pueden tener MCP servers ejecutándose via binarios fuera del 8-list (`java`, `mvn`, `php`, `pwsh`). *Mitigación*: D-107-01 escape hatch via risk-accept + CHANGELOG entry alerta al cambio. CLI hint en error message guía al user a la solución.
- **R-2 — narrow `allow:` template impacts new installs unexpectedly**. Usuarios que dependen de tools fuera del narrow list ven denials inesperados en proyectos nuevos. *Mitigación*: NG-1 mantiene existing settings.json untouched; nuevos installs reciben `contexts/permissions-migration.md` documenting la lista + cómo extender.
- **R-3 — Explorer rename breaks existing Copilot Chat workflows**. Users con muscle memory `@Explorer`. *Mitigación*: D-107-03 CHANGELOG `BREAKING-LIKELY:` flag; small user surface; autocomplete sugiere `@ai-explore` post-rename.
- **R-4 — GEMINI.md placeholders break sync_command_mirrors.py orden**. Si `translate_refs()` se ejecuta antes/después de `__SKILL_COUNT__` substitution, output puede ser malformado. *Mitigación*: explicit ordering in `write_gemini_md()` — placeholders first, translate_refs after; integration test cover ambos.
- **R-5 — IOC catalog vendor goes stale silently**. Upstream `claude-mcp-sentinel/iocs.json` puede actualizar IOCs y nuestro vendor queda atrás. *Mitigación*: `IOCS_ATTRIBUTION.md` registra vendor commit hash; `contexts/sentinel-iocs-update.md` documenta quarterly refresh process; future spec puede automatizar via CI dependabot-style.
- **R-6 — prompt-injection-guard FALSE POSITIVES on legitimate workflows**. User legítimamente trabaja con `~/.aws/credentials` para configurar AWS CLI. *Mitigación*: D-107-07 escape hatch via risk-accept; doctor reports allowlist exceptions activas; documentation con ejemplo común.
- **R-7 — `/ai-mcp-sentinel scan` LLM cost explodes**. 47 skills + N MCP servers = many LLM calls. *Mitigación*: cold-path invocation (no auto-trigger); usuario decide cuándo ejecutar; mode `scan --target <specific>` permite focused audit; cost estimate displayed pre-execution.
- **R-8 — H1 tool-spec hash baseline lost on `install-state.json` corruption**. Si state file pierde, baseline desaparece, all tools appear as first-run. *Mitigación*: spec-101 already has install-state backup mechanism (`.legacy-*` files visibles en current state); H2 chain detects tampering; first-run handling populates baseline gracefully.
- **R-9 — H2 audit chain breaks on legitimate ops** (e.g., manual JSON edit, file truncation by sysadmin). *Mitigación*: doctor checks emit WARN not FAIL — never blocks operations; `ai-eng audit verify` detailed report identifies exact break index para investigation; documentation explica cómo validar/reparar chain manualmente si necesario.
- **R-10 — H2 chain `prev_event_hash` field breaks legacy event consumers**. External tools que parsean `framework-events.ndjson` pueden romper si ven field desconocido. *Mitigación*: field es additive; pydantic models con `extra="ignore"` lo manejan transparentemente (spec-105 D-105-08 pattern); CHANGELOG documents schema evolution.
- **R-11 — Phase 3 mirror sync conflicts post-Explorer rename**. `ai-eng sync` debe re-generar 4 IDE espejos consistente con renamed agent + nuevos chatmodes. *Mitigación*: T-3.7 + T-3.8 (sync + sync --check) ejecutan secuencialmente; integration test `test_copilot_explorer_rename.py` valida mirror parity preserved.
- **R-12 — Pre-existing parallel-flake regressions**. spec-107 phases pueden re-introducir flake patterns en tests nuevos. *Mitigación*: spec-105 fix landed (auto_stage `_refresh_index` + serial stack-tests); todos los nuevos tests siguen el patrón establecido.
- **R-13 — Risk-accept lookup performance degrada con muchos DEC entries**. spec-107 puede inflar decision-store con `mcp-binary-*`, `sentinel-*`, `tool-spec-mismatch-*` entries. *Mitigación*: in-memory filter es O(N), N≤500 → <50ms median; bound natural via `_MAX_RENEWALS=2`; resolved/revoked entries marked SUPERSEDED no inflan active-set lookups.
- **R-14 — IOC catalog license incompatibility con ai-engineering license**. claude-mcp-sentinel puede ser GPL/AGPL while ai-engineering es MIT. *Mitigación*: IOCS_ATTRIBUTION.md verifica license terms upfront; si incompatible, abandon vendor strategy y escalate a designing IOC catalog from scratch (would be Q6 1B fallback).

## References

- `.ai-engineering/notes/adoption-s5-mcp-sentinel-ide-parity.md` — origen del spec.
- `.ai-engineering/specs/spec-105.md` — provides risk-accept lifecycle + decision-store machinery reused throughout.
- `.ai-engineering/specs/spec-106.md` — provides `_shared/` skill pattern + `/ai-platform-audit` extension target.
- `claude-mcp-sentinel` (`/Users/soydachi/repos/claude-mcp-sentinel`) — IOC catalog source (D-107-05) + 3-valued decision protocol model (D-107-06).
- NotebookLM: "Securing Claude MCP Tools with Sentinel AI" (notebook ID `e0dc5212-7418-467d-98c1-6178e6f622d8`) — H1 + H2 deeper controls source.
- `.ai-engineering/scripts/hooks/mcp-health.py` — extended by D-107-01.
- `.ai-engineering/scripts/hooks/prompt-injection-guard.py` — extended by D-107-06.
- `.claude/settings.json` template + doctor — modified by D-107-02.
- `.github/agents/explore.agent.md` → renamed to `ai-explore.agent.md` per D-107-03.
- `templates/project/GEMINI.md` — placeholders per D-107-04.
- `scripts/sync_command_mirrors.py` — `write_gemini_md()` + `AGENT_METADATA` per D-107-04 + D-107-03.
- `.claude/skills/ai-platform-audit/SKILL.md` — Checks 6/7/8 per D-107-04.
- `state/manifest.py` — `compute_tool_spec_hash()` per D-107-09.
- `state/models.py` — `tool_spec_hashes` field on InstallState per D-107-09; `prev_event_hash` field on Decision per D-107-10.
- `state/observability.py` — `prev_event_hash` populated per D-107-10.
- `state/audit_chain.py` (new module) — `verify_audit_chain()` per D-107-10.
- CLAUDE.md Don't #7 — preserved (D-107-02 narrows allow but does NOT modify deny rules).
- LESSONS:
  - "Stable framework orchestration should not become per-project config by default" → D-107-04 Checks advisory-first; D-107-08 LLM cold-path on-demand.
  - "manifest.yml es la fuente de verdad absoluta" → D-107-04 GEMINI.md auto-gen via canonical data.
  - "Elimination is simplification, not migration" → D-107-07 reuse risk-accept (cero new file format).

## Open Questions

- **OQ-1**: ¿IOC catalog refresh cadence quarterly es suficiente? Tentative: yes (IOCs no cambian semanalmente); if telemetry shows missed novel attacks, escalate to monthly. Decision en post-Phase 6 review.
- **OQ-2**: ¿`/ai-mcp-sentinel scan` debería invocar automáticamente post-`ai-eng install`? Tentative: NO (cold-path mantra; user-driven only). Si la dashboard de adoption muestra que users no recuerdan ejecutarlo, considerar opt-in post-install hook en spec-future.
- **OQ-3**: ¿H2 chain debería incluir entries de `install-state.json` mutations? Tentative: NO per Q7-2B (NG-4); revisitar si compliance audit team lo requiere.
- **OQ-4**: ¿Skill `/ai-mcp-sentinel` Mode 1 `scan` debería poder analizar MCP servers remotos (no solo locales)? Tentative: solo locales en spec-107. Remote analysis adds complexity (network IO, auth) sin claro ROI inicial.
- **OQ-5**: ¿`ai-eng audit verify` debería bloquear (exit 1) en chain break o solo warn? Tentative: warn (consistente con doctor advisory pattern); future hard-gate spec puede escalate.
