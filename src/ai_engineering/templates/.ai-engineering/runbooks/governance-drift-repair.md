# Runbook: Governance Drift Repair

## Purpose

Detect and repair drift between governance decisions and implementation.

## Schedule

Weekly (Monday 4AM) via `ai-eng-governance-drift.yml`.

## Procedure

1. **Validate content integrity**: `ai-eng validate` — check all 7 categories.
2. **Check governance diff**: `ai-eng governance diff` — compare canonical vs mirrors.
3. **Check risk acceptances**: `ai-eng gate risk-check` — identify expired decisions.
4. **Mirror sync**: Verify all adapter locations (.claude, .github, .agents) match canonical.
5. **Counter accuracy**: Verify counts in AGENTS.md, CLAUDE.md, copilot-instructions.md match actual files.
6. **Repair**: For each drift found:
   - If mirror desync: regenerate from canonical (`ai-eng update`).
   - If counter mismatch: update the instruction file.
   - If expired decision: notify for renewal or archive.
7. **Report**: Create issue with drift findings and repairs applied.

## Common Drift Patterns

| Pattern | Detection | Fix |
|---------|-----------|-----|
| Agent renamed but mirrors not updated | counter-accuracy check | Regenerate agent cards |
| Skill added but not mirrored | mirror-sync check | Run `ai-eng update` |
| Decision expired | risk-check | Renew or archive |
| Instruction file stale | instruction-consistency | Update counts/lists |
