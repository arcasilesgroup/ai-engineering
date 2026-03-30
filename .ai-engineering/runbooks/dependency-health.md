---
name: dependency-health
description: "Scan dependencies for outdated versions, known CVEs, and license compliance issues; owns all dependency-graph vulnerability findings"
type: operational
cadence: weekly
---

# Dependency Health

## Objetivo

This runbook is the **single owner** of all CVE and vulnerability findings originating from the dependency graph. It scans for outdated versions, known CVEs, and license compliance issues on a weekly cadence. The companion `security-scan` runbook handles SAST and secrets detection only -- it never duplicates dependency vulnerability work.

## Precondiciones

- Package ecosystem detection: at least one of `pyproject.toml`, `requirements.txt`, `uv.lock`, `package.json`, or `Cargo.toml` must exist.
- `pip-audit` installed for Python CVE scanning. Install via `uv tool install pip-audit`.
- `uv` installed for outdated package checks and license inspection.
- `gh` or `az` CLI authenticated for work item creation and updates.
- For Node ecosystems: `npm` available on PATH.
- For Rust ecosystems: `cargo-audit` and `cargo-outdated` installed.

## Procedimiento

### Step 1 -- Detect Package Ecosystem

```bash
test -f pyproject.toml || test -f requirements.txt || test -f uv.lock && echo "python"
test -f package.json && echo "node"
test -f Cargo.toml && echo "rust"
```

All subsequent steps run only for detected ecosystems.

### Step 2 -- Vulnerability Scan

**Python**
```bash
pip-audit --format=json
# Alternative: uv run pip-audit --format=json
```

**Node** (if present)
```bash
npm audit --json > dep-audit-node.json 2>&1
```

**Rust** (if present)
```bash
cargo audit --json > dep-audit-rust.json 2>&1
```

Extract from each report: package name, installed version, fixed version, CVE ID(s), severity.

### Step 3 -- Outdated Package Check

**Python**
```bash
uv pip list --outdated --format=json
```

**Node** (if present)
```bash
npm outdated --json > dep-outdated-node.json 2>&1
```

**Rust** (if present)
```bash
cargo outdated --format=json > dep-outdated-rust.json 2>&1
```

Flag packages where the latest release is more than 90 days newer than the installed version.

### Step 4 -- License Compliance

**Python**
```bash
uv pip list --format=json | python3 -c "
import json, sys, subprocess
for pkg in json.load(sys.stdin):
    r = subprocess.run(['pip', 'show', pkg['name']], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith('License:'):
            val = line.split(':', 1)[1].strip()
            if any(t in val.upper() for t in ['GPL', 'AGPL', 'UNKNOWN', 'PROPRIETARY']):
                print(f\"{pkg['name']}: {val}\")
"
```

**Node** (if present)
```bash
npx license-checker --json --failOn "GPL-2.0;GPL-3.0;AGPL-3.0;UNKNOWN"
```

Flag copyleft, unknown, or proprietary licenses for manual review.

### Step 5 -- Map findings and deduplicate via handler

For each finding at or above `medium` severity, map to the Finding contract and route through the shared dedup handler.

**Finding mapping:**

```yaml
domain_label: "dependency-update"
title: "dep: upgrade $PKG from $CURRENT to $LATEST"
file_path: null
rule_id: $CVE_ID (or "outdated" for non-CVE findings, "license" for license issues)
symbol: null
package_name: $PKG
severity: $SEVERITY (critical | high | medium)
body: |
  **Package:** $PKG  **Ecosystem:** $ECO
  **Current:** $CURRENT  **Latest:** $LATEST
  **CVE(s):** $CVE_IDS or 'none'  **Severity:** $SEVERITY
  *Created by dependency-health runbook*
```

Follow `handlers/dedup-check.md` to process all findings through the dedup cascade (max 20 per run). The handler labels new issues with `dependency-update` and `sev-$SEVERITY`.

### Step 6 -- Update Existing Issues

For open `dependency-update` issues where a newer version is now available, add an update comment.

**GitHub**
```bash
gh issue comment <NUMBER> --body "**Update:** <NEW_LATEST> now available (was <OLD_LATEST>).
*Updated by dependency-health runbook*"
```

**Azure DevOps**
```bash
az boards work-item update --id <ID> \
  --discussion "Update: version <NEW_LATEST> now available."
```

### Step 7 -- Generate Report

```
=== Dependency Health Report ===
Date:       <TIMESTAMP>
Ecosystems: <DETECTED_LIST>

CVE Summary:
  Critical: <N>   High: <N>   Medium: <N>   Low: <N>

Outdated (>90 days): <N>
License Issues:      <N>
Items Created:       <N>
Items Updated:       <N>
Deferred:            <N>
================================
```

Write to stdout. In CI, capture as a job artifact.

## CVE Ownership

This runbook is the **sole authority** for dependency-graph CVE findings across all ecosystems. There is no overlap with `security-scan`:

| Domain | Owner | Tools |
|--------|-------|-------|
| Dependency CVEs | `dependency-health` | pip-audit, npm audit, cargo audit |
| License compliance | `dependency-health` | pip show, license-checker |
| SAST findings | `security-scan` | semgrep, CodeQL |
| Secrets detection | `security-scan` | gitleaks |

If a vulnerability surfaces in both SAST and dependency analysis, the dependency-health finding takes precedence and the SAST duplicate is closed with a cross-reference.

## Output

Summary report to stdout. Work items created for CVEs, outdated packages, and license violations. No local files are written.

## Guardrails

- **Max 20 work items per run.** Excess findings logged in the report, deferred to next run.
- **Never auto-upgrades dependencies.** Creates issues for human review only.
- **Never creates pull requests.** Upgrade PRs are authored by developers after triage.
- **Mutations enabled by default.** All qualifying findings are created immediately.
- **Protected labels/states untouched.** `p1-critical`, `pinned`, `closed`, `resolved` items are skipped.
