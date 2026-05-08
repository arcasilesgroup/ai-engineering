---
name: ai-mcp-audit
description: "Audits MCP servers and skills on demand using LLM coherence analysis to catch capability drift and rug-pulls. Trigger for 'audit this skill', 'is this MCP safe', 'check coherence', 'detect rug-pull', 'snapshot baseline', 'mcp audit'. Three modes: scan (declared-vs-observed), audit-update (post-update diff), baseline set (anchor known-good). Not for runtime payload inspection; use prompt-injection-guard hook instead. Not for CVE scanning; use /ai-security instead."
effort: high
argument-hint: "scan|audit-update [skill]|baseline set [--target skill-or-all]"
tags: [security, mcp, audit, governance]
mirror_family: gemini-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-mcp-audit/SKILL.md
edit_policy: generated-do-not-edit
---


# MCP Audit — On-Demand Skill & MCP Server Security Audit

## Quick start

```
/ai-mcp-audit scan                          # coherence analysis (all surfaces)
/ai-mcp-audit scan --target <skill-name>    # scoped scan (cost-saving)
/ai-mcp-audit audit-update <skill-name>     # rug-pull detection vs baseline
/ai-mcp-audit baseline set --target all     # anchor known-good snapshot
```

## Workflow

Cold-path LLM-driven security audit (spec-107 D-107-08). Three modes:

1. **Coherence analysis** — declared `description` vs observed code behavior.
2. **Rug-pull detection** — diff post-update files against trusted baseline.
3. **Baseline anchoring** — tamper-evident reference for future audits.

Counterpart to **hot-path** runtime control:
- **Hot path (Capa 1)** — `prompt-injection-guard.py` PreToolUse hook, $0 cost, deterministic IOC matching, immune to prompt injection of payload (D-107-06).
- **Cold path (Capa 2, this skill)** — on-demand LLM analysis. Apt for post-install review, pre-merge audit.

Does NOT replace `/ai-security` (CVE/SBOM), `/ai-governance` (compliance), `/ai-verify` (quality).

## When to Use

- After installing a new skill or MCP server (`scan`).
- After updating an existing skill, especially auto-update (`audit-update <skill>`).
- After fresh-cloning or anchoring known-good state (`baseline set`).
- Before merging PRs touching `.gemini/skills/`, `.codex/skills/`, `.gemini/skills/`, `.github/skills/`.
- NOT for runtime payload inspection (use prompt-injection-guard hook).
- NOT for CVE/dependency vulnerabilities (use `/ai-security`).

## Modes

### Mode 1 — `scan` (Coherence Analysis)

`ai-mcp-audit scan [--target <path-or-skill-name>]`

LLM compares declared `description` vs actual code (handlers, scripts, references). Per surface emits **GREEN (VERDE)** = coherent, or **RED (ROJO)** = suspicious (capability creep, malicious injection, rug-pull). Outputs structured JSON at `.ai-engineering/state/sentinel-scan-report.json` + human-readable stdout. `--target` scopes to single surface (cost-saving). Cost estimate displayed pre-execution; user must confirm.

### Mode 2 — `audit-update <skill>` (Rug-Pull Detection)

`ai-mcp-audit audit-update <skill-name>`

Reads baseline from `.ai-engineering/state/sentinel-baseline.json` (Mode 3 must run first; without baseline, errors with hint pointing to Mode 3). Walks current files + computes semantic-capability diff: new network calls, new file accesses outside scope, new env reads, new subprocess invocations, new SKILL.md frontmatter capability claims. Each delta flagged with severity (HIGH/MEDIUM/LOW), exact diff, remediation hint. **Postmark-class threat detection pattern** — silent semantic drift that bypasses CVE/SBOM scanning.

### Mode 3 — `baseline set` (Anchoring)

`ai-mcp-audit baseline set [--target <skill-name>|all]`

Anchors snapshot to `.ai-engineering/state/sentinel-baseline.json`. Per skill: SHA256 of every file + extracted capabilities (network/file/env/subprocess + frontmatter claims). Without baseline, Mode 2 errors. `--target all` regenerates entire baseline (confirmation prompt). Canonical-JSON sort_keys=True for stability + candidate for H2 hash-chained audit trail (D-107-10).

## Triggering Patterns

| User intent | Mode |
|-------------|------|
| "audit this skill", "is this safe?", "check coherence" | `scan` |
| post-install of new skill or MCP server | `scan --target <new-skill>` |
| "did this rug-pull?", "what changed semantically?" | `audit-update <skill>` |
| post-update of existing skill (especially auto-update) | `audit-update <skill>` |
| "anchor baseline", "snapshot known-good" | `baseline set` |
| post-fresh-clone | `baseline set --target all` |

## Integration

`/ai-security` adds CVE/SBOM/secrets; MCP-audit adds coherence/rug-pull. `/ai-governance` consumes VERDE/ROJO verdicts. `/ai-ide-audit` verifies platform support; MCP-audit verifies skill behavior. `prompt-injection-guard` hook (D-107-06) hot-path runtime; MCP-audit cold-path counterpart.

## Non-Goals

- No automatic invocation (Q6-3B + OQ-2). Cold-path on-demand only.
- No remote MCP server analysis (OQ-4). Local-only in spec-107.
- No auto-fix of flagged skills.
- No replacement for `/ai-security` (different threat models).

## State Files

- `.ai-engineering/state/sentinel-baseline.json` — trusted snapshot (Mode 3 writes; Mode 2 reads).
- `.ai-engineering/state/sentinel-scan-report.json` — most recent Mode 1 output.
- `.ai-engineering/state/state.db.decisions` — risk-acceptance entries for accepted ROJO verdicts (`sentinel-coherence-<skill>` finding-id, spec-105 lifecycle).

## Examples

### Example 1 — coherence scan after installing a new skill

User: "I just installed a new skill from a third-party repo, audit it"

```
/ai-mcp-audit scan --target ai-foo-bar
```

Runs LLM coherence analysis comparing the declared `description` against actual handler code. Emits VERDE / ROJO verdict per surface; ROJO triggers risk-acceptance flow.

### Example 2 — rug-pull detection after auto-update

User: "did the latest update to ai-skill-x silently change capabilities?"

```
/ai-mcp-audit audit-update ai-skill-x
```

Diffs the current files against the trusted baseline. Reports new network calls, file accesses, env reads, or capability claims with severity HIGH / MEDIUM / LOW.

## References

- `.ai-engineering/specs/spec.md` — D-107-08 design rationale.
- `.ai-engineering/scripts/hooks/prompt-injection-guard.py` — hot-path runtime counterpart.
- `.ai-engineering/security/iocs/IOCS_ATTRIBUTION.md` — IOC catalog provenance.
- `.ai-engineering/contexts/sentinel-iocs-update.md` — refresh process.
