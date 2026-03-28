---
runbook: dependency-health
version: 1
purpose: "Scan dependencies for outdated versions, known CVEs, and license compliance issues; owns all dependency-graph vulnerability findings"
type: operational
cadence: weekly
hosts:
  - codex-app-automation
  - claude-scheduled-tasks
  - github-agents
  - azure-foundry
provider_scope:
  read: [issues, labels, code]
  write: [comments, work-items, labels]
feature_policy: read-only
hierarchy_policy:
  create: [task]
  mutate: [task]
scan_targets:
  - pyproject.toml / requirements.txt / uv.lock
  - package.json / package-lock.json (if present)
  - Cargo.toml / Cargo.lock (if present)
tool_dependencies:
  - gh
  - az
  - pip-audit
  - uv
thresholds:
  severity: medium
  outdated_days: 90
  max_findings_per_run: 20
outputs:
  work_items: true
  comments: true
  labels: true
  report: detailed
handoff:
  marker: "dependency-update"
  lifecycle_phase: triage
guardrails:
  max_mutations: 20
  protected_labels: [p1-critical, pinned]
  protected_states: [closed, resolved]
  dry_run_default: true
---

# Dependency Health

## Purpose

This runbook is the **single owner** of all CVE and vulnerability findings originating from the dependency graph. It scans for outdated versions, known CVEs, and license compliance issues on a weekly cadence. The companion `security-scan` runbook handles SAST and secrets detection only -- it never duplicates dependency vulnerability work.

## Procedure

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
pip-audit --format=json --output=dep-audit-python.json
# Alternative: uv run pip-audit --format=json --output=dep-audit-python.json
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
uv pip list --outdated --format=json > dep-outdated-python.json
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

### Step 5 -- Create Work Items for New Findings

For each finding at or above `medium` severity, check for an existing open issue before creating.

**GitHub**
```bash
gh issue list --state open --label "dependency-update" --search "in:title <PKG>" --json number,title

gh issue create \
  --title "dep: upgrade <PKG> from <CURRENT> to <LATEST>" \
  --label "dependency-update,severity:<SEVERITY>" \
  --body "**Package:** <PKG>  **Ecosystem:** <ECO>
**Current:** <CURRENT>  **Latest:** <LATEST>
**CVE(s):** <CVE_IDS or 'none'>  **Severity:** <SEVERITY>
*Created by dependency-health runbook*"
```

**Azure DevOps**
```bash
az boards work-item create --type Task \
  --title "dep: upgrade <PKG> from <CURRENT> to <LATEST>" \
  --description "Package: <PKG> | CVEs: <CVE_IDS> | Severity: <SEVERITY>" \
  --fields "System.Tags=dependency-update;severity:<SEVERITY>"
```

Stop after 20 work items per run. Remaining findings are deferred to the next run.

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

## Provider Notes

**GitHub** -- Uses `gh issue` for work item CRUD. Issues labeled `dependency-update` and `severity:<level>`. Requires `gh` authenticated with repo scope.

**Azure DevOps** -- Uses `az boards` for work item CRUD. Tasks tagged `dependency-update`, assigned to the area path from `manifest.yml`. Requires `az` authenticated with the target organization.

Both providers are always configured in the manifest. Switching is a one-field change (`work_items.provider`).

## Host Notes

| Host | Considerations |
|------|----------------|
| `codex-app-automation` | Full toolchain pre-installed. Network access for registry queries. |
| `claude-scheduled-tasks` | Verify pip-audit on PATH; may need `uv tool install pip-audit` on first run. |
| `github-agents` | Runs in Actions runner. Install tools via action steps. `gh` pre-authenticated. |
| `azure-foundry` | Managed identity for `az`. Install pip-audit into task venv. Egress must allow PyPI/npm. |

## Safety

- **Max 20 work items per run.** Excess findings logged in the report, deferred to next run.
- **Never auto-upgrades dependencies.** Creates issues for human review only.
- **Never creates pull requests.** Upgrade PRs are authored by developers after triage.
- **Dry-run by default.** Set `dry_run_default: false` to enable mutations.
- **Protected labels/states untouched.** `p1-critical`, `pinned`, `closed`, `resolved` items are skipped.
