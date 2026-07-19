---
name: ai-mcp-audit
description: "Audits MCP servers and skills on demand using LLM coherence analysis to catch capability drift and rug-pulls. Trigger for 'audit this skill', 'is this MCP safe', 'check coherence', 'detect rug-pull', 'snapshot baseline', 'mcp audit'. Three modes: scan (declared-vs-observed), audit-update (post-update diff), baseline set (anchor known-good). Not for runtime payload inspection; use prompt-injection-guard hook instead. Not for CVE scanning; use /ai-security instead."
effort: high
argument-hint: "scan|audit-update [skill]|baseline set [--target skill-or-all]"
tags: [security, mcp, audit, governance]
---

# MCP Audit — On-Demand Skill & MCP Server Security Audit

Audits MCP servers and skills on demand using LLM coherence analysis to
catch capability drift and rug-pulls. Use it to scan declared-vs-observed
behavior, diff post-update files, or set a known-good baseline.

## Workflow

Cold-path LLM-driven security audit (spec-107 D-107-08). Principles applied: §10.1 KISS
(the deterministic $0 hot path stays separate from the on-demand LLM cold path — no single
over-complex gate straddling both threat models).

Two tiers:

| Tier | Mechanism | Cost | Role |
| --- | --- | --- | --- |
| Hot path (Capa 1) | `prompt-injection-guard.py` PreToolUse hook — deterministic IOC matching, injection-immune (D-107-06) | $0 | runtime payload control |
| Cold path (Capa 2, this skill) | on-demand LLM analysis | per-run (confirm first) | post-install review, pre-merge audit |

Three modes:

1. **scan** — coherence: declared `description` vs observed code behavior.
2. **audit-update** — rug-pull: diff post-update files against the trusted baseline.
3. **baseline set** — anchor a tamper-evident reference for future audits.

Does NOT replace `/ai-security` (CVE/SBOM), `/ai-governance` (compliance), or `/ai-verify` (quality).

## Modes

### Mode 1 — `scan` (coherence analysis)

`ai-mcp-audit scan [--target <path-or-skill-name>]`

- LLM compares declared `description` vs actual code (handlers, scripts, references).
- Per surface: **GREEN (VERDE)** = coherent, or **RED (ROJO)** = suspicious (capability creep, malicious injection, rug-pull).
- Output: structured JSON at `.ai-engineering/state/sentinel-scan-report.json` + human-readable stdout.
- `--target` scopes to a single surface (cost-saving). Cost estimate shown pre-run; user must confirm.

### Mode 2 — `audit-update <skill>` (rug-pull detection)

`ai-mcp-audit audit-update <skill-name>`

- Reads baseline from `.ai-engineering/state/sentinel-baseline.json` (Mode 3 must run first; without it, errors with a hint pointing to Mode 3).
- Walks current files + computes semantic-capability diff: new network calls, file accesses outside scope, env reads, subprocess invocations, SKILL.md frontmatter capability claims.
- Each delta: severity HIGH/MEDIUM/LOW + exact diff + remediation hint.
- Postmark-class threat detection: silent semantic drift that bypasses CVE/SBOM scanning.

### Mode 3 — `baseline set` (anchoring)

`ai-mcp-audit baseline set [--target <skill-name>|all]`

- Anchors a snapshot to `.ai-engineering/state/sentinel-baseline.json`.
- Per skill: SHA256 of every file + extracted capabilities (network/file/env/subprocess + frontmatter claims).
- `--target all` regenerates the entire baseline (confirmation prompt). Without a baseline, Mode 2 errors.
- Canonical-JSON `sort_keys=True` for stability; candidate for H2 hash-chained audit trail (D-107-10).

## Non-Goals

- No automatic invocation (Q6-3B + OQ-2) — cold-path on-demand only.
- No remote MCP server analysis (OQ-4) — local-only in spec-107.
- No auto-fix of flagged skills.
- No replacement for `/ai-security` (different threat models).

## State Files

- `.ai-engineering/state/sentinel-baseline.json` — trusted snapshot (Mode 3 writes; Mode 2 reads).
- `.ai-engineering/state/sentinel-scan-report.json` — most recent Mode 1 output.
- `.ai-engineering/state/decision-store.json` — risk-acceptance entries for accepted ROJO verdicts (`sentinel-coherence-<skill>` finding-id, spec-105 lifecycle).

## Integration

Complements `/ai-security` (CVE/SBOM/secrets) with coherence/rug-pull; feeds VERDE/ROJO verdicts to `/ai-governance`; pairs with `/ai-ide-audit` (platform vs. behavior). Cold-path counterpart to the `prompt-injection-guard` hot-path hook (D-107-06).

## Examples

### Example — coherence scan after installing a new skill

User: "I just installed a new skill from a third-party repo, audit it"

```
/ai-mcp-audit scan --target ai-foo-bar
```

Runs LLM coherence analysis comparing the declared `description` against actual handler code; emits VERDE / ROJO per surface; ROJO triggers the risk-acceptance flow.

## References

- `.ai-engineering/specs/spec.md` — D-107-08 design rationale.
- `.ai-engineering/scripts/hooks/prompt-injection-guard.py` — hot-path runtime counterpart.
- `.ai-engineering/security/iocs/IOCS_ATTRIBUTION.md` — IOC catalog provenance.
- `.ai-engineering/reference/mcp-binary-policy.md` — MCP binary allowlist policy (spec-107).
