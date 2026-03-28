---
runbook: security-scan
version: 1
purpose: "Scan for secrets, OWASP/SAST code patterns, and compliance gaps; does NOT scan dependency CVEs (owned by dependency-health)"
type: operational
cadence: weekly
hosts:
  - codex-app-automation
  - claude-scheduled-tasks
  - github-agents
  - azure-foundry
provider_scope:
  read: [issues, labels, code, pull-requests]
  write: [comments, work-items, labels]
feature_policy: read-only
hierarchy_policy:
  create: [task]
  mutate: [task]
scan_targets:
  - src/
  - config files (.env*, *.yml, *.json)
  - CI/CD workflows (.github/workflows/)
  - scripts/
tool_dependencies:
  - gh
  - az
  - gitleaks
  - semgrep
thresholds:
  severity: medium
  max_findings_per_run: 20
outputs:
  work_items: true
  comments: true
  labels: true
  report: detailed
handoff:
  marker: "security-finding"
  lifecycle_phase: triage
guardrails:
  max_mutations: 20
  protected_labels: [p1-critical, pinned]
  protected_states: [closed, resolved]
  dry_run_default: true
---

# Security Scan Runbook

## Purpose

Detect leaked secrets, SAST/OWASP code-level vulnerabilities, and compliance gaps across source code, configuration files, CI/CD workflows, and scripts. Findings above the severity threshold are filed as task work items with full remediation context.

This runbook does **not** scan for dependency CVEs or vulnerable package versions. That responsibility belongs to the `dependency-health` runbook, which owns the supply-chain surface. The boundary is strict: if the finding originates from a project dependency rather than authored code or configuration, it is out of scope here.

## Procedure

### Step 1 -- Secret detection

Run gitleaks against the full working tree to detect leaked credentials, API keys, tokens, and private keys.

```bash
gitleaks detect --source . --no-git --report-format json --report-path /tmp/gitleaks-report.json
```

Parse the output and store findings as `$SECRET_FINDINGS`. Each entry contains the file path, line number, rule ID, and a redacted match preview. Record the count for the final report.

### Step 2 -- SAST scan

Run semgrep with its auto configuration to detect code-level vulnerabilities across all scan targets.

```bash
semgrep scan --config auto --json --output /tmp/semgrep-report.json src/
```

Parse the JSON output. Each finding includes the rule ID, CWE reference, severity, file path, line range, and a message describing the vulnerability. Store as `$SAST_FINDINGS`.

### Step 3 -- Config file credential scan

Run gitleaks a second pass with extended rules targeting connection strings and inline API keys in config files (`.env*`, `*.yml`, `*.json`). Use a custom `--config` that extends the default ruleset with `hardcoded-connection-string` and `hardcoded-api-endpoint-with-key` rules.

```bash
gitleaks detect --source . --no-git --report-format json --report-path /tmp/gitleaks-config-report.json \
  --config .ai-engineering/runbooks/gitleaks-extended.toml
```

Merge results into `$SECRET_FINDINGS`. Deduplicate by file path and line number against Step 1 results.

### Step 4 -- CI/CD workflow security audit

Scan CI/CD workflow files for security anti-patterns.

```bash
# Check for unpinned third-party actions (should use SHA, not tag)
grep -rn 'uses:' .github/workflows/ | grep -v '@[a-f0-9]\{40\}' | grep -v 'actions/\(checkout\|setup-\|cache\)' > /tmp/unpinned-actions.txt || true

# Check for overly permissive workflow permissions
grep -rn 'permissions:' .github/workflows/ | grep -i 'write-all\|contents: write' > /tmp/broad-permissions.txt || true

# Check for secrets exposed in logs or env
grep -rn 'echo.*\${{.*secrets\.' .github/workflows/ > /tmp/secret-echo.txt || true

# Check for pull_request_target with checkout of PR head (code injection risk)
grep -rn -A5 'pull_request_target' .github/workflows/ | grep 'ref:.*head' > /tmp/pr-target-risk.txt || true
```

Consolidate findings into `$CICD_FINDINGS`. Classify each by sub-category: `unpinned-action`, `broad-permissions`, `secret-exposure`, or `pr-injection-risk`.

### Step 5 -- OWASP pattern detection

Extend the semgrep scan to check explicitly for OWASP Top 10 patterns in application code.

```bash
semgrep scan --config "p/owasp-top-ten" --json --output /tmp/semgrep-owasp-report.json src/ scripts/
```

Map each finding to its OWASP category and CWE (SQL injection/CWE-89, XSS/CWE-79, path traversal/CWE-22, command injection/CWE-78, insecure deserialization/CWE-502, SSRF/CWE-918). Store as `$OWASP_FINDINGS`. Deduplicate against `$SAST_FINDINGS` from Step 2 by file, line, and rule ID.

### Step 6 -- Deduplicate against existing open issues

For each finding above the severity threshold (`medium`), check whether an open issue already tracks it.

```bash
# GitHub -- search for existing security-finding issues matching file and rule
gh issue list --state open --label "security-finding" --limit 200 --json number,title,body \
  --jq ".[] | select(.body | contains(\"$FILE_PATH\")) | select(.body | contains(\"$RULE_ID\"))"
```

```bash
# Azure DevOps -- search for open tasks with the security-finding tag
az boards query --wiql "SELECT [System.Id], [System.Title], [System.Description] FROM WorkItems WHERE [System.State] <> 'Closed' AND [System.State] <> 'Resolved' AND [System.Tags] CONTAINS 'security-finding' AND [System.Description] CONTAINS '$FILE_PATH' AND [System.Description] CONTAINS '$RULE_ID'" --output json
```

If a match is found, skip work-item creation and mark the finding as `pre-existing` in the report. If no match is found, mark as `new` and proceed to Step 7.

### Step 7 -- Create task work items for new findings

For each new finding above severity threshold, create a task work item. The title follows the pattern `security-finding: $RULE_ID in $FILE_PATH:$LINE`. The body includes: file path, line number, finding type, severity, rule ID, CWE/OWASP reference, description, and remediation guidance. Tag with `security-finding` and `severity/$SEVERITY`.

```bash
# GitHub
gh issue create \
  --title "security-finding: $RULE_ID in $FILE_PATH:$LINE" \
  --label "security-finding,severity/$SEVERITY" \
  --body "$FORMATTED_BODY"
```

```bash
# Azure DevOps
az boards work-item create --type Task \
  --title "security-finding: $RULE_ID in $FILE_PATH:$LINE" \
  --fields "System.Tags=security-finding; severity/$SEVERITY" \
  --description "$FORMATTED_BODY"
```

Each work-item body ends with the HTML comment `<!-- security-scan:finding -->` for programmatic identification in Step 6 deduplication.

### Step 8 -- Generate detailed report

Produce a detailed report with findings by category, severity distribution, and new-vs-existing breakdown.

```bash
echo "=== Security Scan Report $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo ""
echo "--- Findings by Category ---"
echo "  Secrets:               $COUNT_SECRETS"
echo "  SAST (code patterns):  $COUNT_SAST"
echo "  Config credentials:    $COUNT_CONFIG"
echo "  CI/CD anti-patterns:   $COUNT_CICD"
echo "  OWASP patterns:        $COUNT_OWASP"
echo "  Total:                 $COUNT_TOTAL"
echo ""
echo "--- Severity Distribution ---"
echo "  critical:              $COUNT_CRITICAL"
echo "  high:                  $COUNT_HIGH"
echo "  medium:                $COUNT_MEDIUM"
echo "  low:                   $COUNT_LOW (logged, not escalated)"
echo "  info:                  $COUNT_INFO (logged, not escalated)"
echo ""
echo "--- New vs Pre-existing ---"
echo "  New findings:          $COUNT_NEW"
echo "  Pre-existing:          $COUNT_PREEXISTING"
echo "  Work items created:    $COUNT_CREATED"
echo "  Skipped (duplicate):   $COUNT_SKIPPED"
echo ""
echo "Mutations applied:       $MUTATION_COUNT / 20"
```

## Scope Boundary

This runbook owns the **authored-code and configuration** security surface. The boundary with `dependency-health` is explicit and non-overlapping:

| Concern | Owner | Examples |
|---------|-------|---------|
| Leaked secrets in code/config | `security-scan` | API keys in `.env`, tokens in YAML |
| SAST code patterns | `security-scan` | SQL injection, XSS, path traversal |
| CI/CD workflow anti-patterns | `security-scan` | Unpinned actions, secret exposure |
| Hardcoded credentials | `security-scan` | Passwords in config files |
| Dependency CVEs | `dependency-health` | Known vulnerabilities in pip/npm packages |
| Outdated packages | `dependency-health` | Packages behind latest security patch |
| License compliance | `dependency-health` | Copyleft or restricted licenses |

If a semgrep rule fires on an import statement but the root cause is a vulnerable library version, defer to `dependency-health`. This runbook only acts on patterns in code the team authored or configuration the team maintains.

## Provider Notes

| Concern | GitHub (`gh`) | Azure DevOps (`az boards`) |
|---------|---------------|---------------------------|
| Create work item | `gh issue create --label --body` | `az boards work-item create --type Task --fields --description` |
| Search existing | `gh issue list --label --json` with `--jq` filter | `az boards query --wiql` with CONTAINS predicate |
| Add label | `gh issue edit --add-label` | `az boards work-item update --fields "System.Tags=..."` |
| Comment | `gh issue comment --body` | `az boards work-item update --discussion` |
| Auth | `GH_TOKEN` env var or `gh auth login` | `az login` or service principal via `AZURE_DEVOPS_EXT_PAT` |
| Hierarchy | Issues with labels (flat) | Tasks linked under User Stories via parent relation |
| Rate limits | 5000 requests/hour (authenticated) | 200 requests/minute (per PAT) |

## Host Notes

- **codex-app-automation** -- Both gitleaks and semgrep must be pre-installed in the Codex container image. If semgrep is unavailable, fall back to gitleaks-only mode and log the gap. Timeout budget is 10 minutes; large repositories may need `--max-target-bytes` on semgrep to stay within limits. All API calls must go through `gh` or `az` CLI (Codex network sandbox prohibits raw HTTP).
- **claude-scheduled-tasks** -- The agent reads this runbook from the filesystem at invocation. gitleaks is typically available; semgrep availability depends on the session environment. If semgrep is missing, execute Steps 1, 3, 4 only and note the degraded coverage in the report. Reports go to stdout; persist to `state/security-scan-report.json` if write access is available.
- **github-agents** -- Runs as a GitHub Actions workflow. Install gitleaks and semgrep via their official actions (`gitleaks/gitleaks-action`, `semgrep/semgrep-action`). Authenticate with `${{ secrets.GITHUB_TOKEN }}`. Issue creation requires `issues: write` permission in the workflow YAML. Azure DevOps commands are unavailable in this host.
- **azure-foundry** -- Runs as an Azure AI Foundry agent or Azure Automation runbook. Install gitleaks and semgrep via pip or binary download during setup phase. Authenticate via managed identity or service principal. GitHub commands require a PAT stored in Key Vault. Use `az extension add --name azure-devops` if the extension is not pre-installed.

## Safety

This runbook enforces strict guardrails to prevent unintended side effects:

- **Never** modifies source code, configuration files, or CI/CD workflows -- this is a detection-only runbook.
- **Never** auto-remediates findings -- remediation is a human or implementation-agent responsibility.
- **Never** exceeds 20 work-item mutations per run -- the `max_mutations` guardrail halts execution and reports remaining findings in the summary without creating work items.
- **Never** modifies items labeled `p1-critical` or `pinned` -- these are protected labels.
- **Never** modifies items in `closed` or `resolved` state -- these are protected states.
- **Never** creates or mutates feature-level work items -- `feature_policy: read-only` and `hierarchy_policy` restrict mutations to tasks only.
- **Never** escalates findings below `medium` severity to work items -- low and info findings are logged in the report for awareness but do not generate issues or tasks.
- **Dry-run is the default.** All write operations are echoed to stdout unless the caller explicitly passes `--arm` or sets `DRY_RUN=false`. In dry-run mode, the runbook produces the full report and logs every command it would execute, but writes nothing.
