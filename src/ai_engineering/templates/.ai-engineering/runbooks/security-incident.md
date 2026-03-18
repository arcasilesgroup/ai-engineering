---
owner: operate
---

# Runbook: Security Incident

## Purpose

Structured response to security incidents: leaked secrets, unauthorized access, vulnerability exploitation.

## Procedure

1. **Contain immediately**: Rotate compromised credentials. Revoke access tokens.
2. **Assess scope**: What was exposed? For how long? Who had access?
3. **Audit trail**: Check `state/audit-log.ndjson` and git history for unauthorized changes.
4. **Remediate**: Fix the vulnerability. Deploy the fix.
5. **Notify**: Inform stakeholders per compliance requirements.
6. **Document**: Full timeline, impact assessment, remediation steps.
7. **Harden**: Add detection rules to prevent recurrence.

## Secret Leak Protocol

1. Immediately rotate the leaked secret.
2. Search git history: `gitleaks detect --source . --no-banner`.
3. Check if the secret was pushed to any remote.
4. If pushed: force-remove from history or accept the leak and rotate.
5. Add the pattern to `.gitleaks.toml` allowlist if false positive, or fix the code.
6. Record risk acceptance in `state/decision-store.json` if needed.

## Vulnerability Disclosure

1. Assess CVSS score and exploitability.
2. Apply patch or workaround immediately.
3. Update dependencies: `pip-audit` + `uv lock --upgrade`.
4. Verify fix: `ai-eng verify security`.
