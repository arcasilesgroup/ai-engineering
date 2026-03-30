# Handler: Dedup Check

## Purpose

Shared deduplication handler for all item-creating runbooks. Receives a set of Findings and decides for each one whether to: (1) comment on an existing consolidated issue, (2) skip as a duplicate of an existing individual issue, or (3) create a new issue.

Every item-creating runbook MUST route its findings through this handler before creating work items.

## Finding Contract

Each runbook maps its domain-specific data to this standard structure before invoking the handler:

```yaml
Finding:
  domain_label: string    # Required. Exactly one. e.g., "tech-debt", "architecture-drift"
  title: string           # Required. Human-readable summary for issue title
  file_path: string?      # Optional. Source file involved
  rule_id: string?        # Optional. Linter rule, CVE ID, drift type
  symbol: string?         # Optional. Function/class name
  package_name: string?   # Optional. Package name (dependency-health)
  severity: string        # Required. "low" | "medium" | "high" | "critical"
  body: string            # Required. Full issue body (used for creation or comment)
```

One Finding = one `domain_label`. Runbooks with multiple domain labels emit separate Finding objects per domain.

## Procedure

### Step 1 -- Batch query open issues

Before iterating findings, fetch all relevant issues once per unique `domain_label` in the finding set. This avoids per-finding API calls.

**GitHub:**

```bash
# For each unique domain_label in the finding set:
CONSOLIDATED=$(gh issue list --state open --label "consolidated" --label "$DOMAIN_LABEL" --sort created --order desc --json number,title,body --limit 50)
INDIVIDUAL=$(gh issue list --state open --label "$DOMAIN_LABEL" --json number,title,body --limit 200 --jq '[.[] | select(.labels | map(.name) | any(. == "consolidated") | not)]')
```

**Azure DevOps:**

```bash
# Consolidated query
az boards query --wiql "SELECT [System.Id], [System.Title], [System.Description] FROM WorkItems WHERE [System.State] <> 'Closed' AND [System.Tags] CONTAINS 'consolidated' AND [System.Tags] CONTAINS '$DOMAIN_LABEL' ORDER BY [System.CreatedDate] DESC" --output json

# Individual query (exclude consolidated)
az boards query --wiql "SELECT [System.Id], [System.Title], [System.Description] FROM WorkItems WHERE [System.State] <> 'Closed' AND [System.Tags] CONTAINS '$DOMAIN_LABEL' AND NOT [System.Tags] CONTAINS 'consolidated' ORDER BY [System.CreatedDate] DESC" --output json
```

Store results as `consolidated_cache[$DOMAIN_LABEL]` and `individual_cache[$DOMAIN_LABEL]`.

### Step 2 -- Process each Finding through the cascade

For each Finding in the set, apply the following cascade. Stop at the first match.

#### Level 1: Consolidated check

Look up `consolidated_cache[finding.domain_label]`.

If one or more consolidated issues exist for this domain:
- Select the **first** result (most recently created).
- Add a comment to the consolidated issue with the finding details.

**GitHub:**

```bash
gh issue comment "$CONSOLIDATED_NUMBER" --body "## New finding ($(date -u +%Y-%m-%d)) — $RUNBOOK_NAME runbook

$FINDING_TITLE

$FINDING_BODY

---
*Appended by dedup-check handler. Original finding not filed as individual issue.*"
```

**Azure DevOps:**

```bash
az boards work-item update --id "$CONSOLIDATED_ID" \
  --discussion "## New finding ($(date -u +%Y-%m-%d)) — $RUNBOOK_NAME runbook

$FINDING_TITLE

$FINDING_BODY

---
*Appended by dedup-check handler.*"
```

- Record: `"appended to #$CONSOLIDATED_NUMBER"`
- **NEXT** finding.

#### Level 2: Individual duplicate check

Look up `individual_cache[finding.domain_label]`.

Match criteria — **ALL non-null finding fields must match** (conjunction):
- `file_path`: issue title or body contains the file path (if provided)
- `rule_id`: issue title or body contains the rule ID (if provided)
- `symbol`: issue title or body contains the symbol name (if provided)
- `package_name`: issue title or body contains the package name (if provided)

If a matching issue is found:
- Record: `"skipped, duplicate of #$MATCH_NUMBER"`
- **NEXT** finding.

#### Level 3: Create new issue

No consolidated or individual match found. Create a new issue.

**GitHub:**

```bash
gh issue create \
  --title "$FINDING_TITLE" \
  --label "$DOMAIN_LABEL" \
  --body "$FINDING_BODY"
```

**Azure DevOps:**

```bash
az boards work-item create --type Task \
  --title "$FINDING_TITLE" \
  --description "$FINDING_BODY" \
  --fields "System.Tags=$DOMAIN_LABEL"
```

- Record: `"created #$NEW_NUMBER"`

### Step 3 -- Report results

After processing all findings, emit a summary to stdout:

```
=== Dedup Check Results ===
Findings processed: N
  Appended to consolidated: N (issues: #X, #Y)
  Skipped (individual duplicate): N (issues: #A, #B)
  Created new: N (issues: #C, #D)
```

## Invocation Pattern

Runbooks reference this handler in their item-creation step. Example:

```markdown
### Step N -- Create work items

Map each finding to the Finding contract:
- domain_label: "tech-debt"
- title: "tech-debt: $FUNCTION_NAME exceeds $METRIC ($VALUE/$THRESHOLD)"
- file_path: $FILE_PATH
- rule_id: $RUFF_RULE
- symbol: $FUNCTION_NAME
- severity: based on threshold exceedance
- body: <full issue body>

Follow `handlers/dedup-check.md` to process all findings through the dedup cascade.
```

## Guardrails

1. **Never bypasses the cascade.** All item-creating runbooks must route through this handler. Direct `gh issue create` / `az boards work-item create` is prohibited for findings.
2. **Respects mutation caps.** The handler does not enforce its own cap — the calling runbook's cap applies. The handler processes up to the cap and stops.
3. **Read-only for consolidated.** The handler only adds comments to consolidated issues. It never modifies titles, bodies, labels, or assignments.
4. **Provider-agnostic contract.** The Finding structure is the same for GitHub and Azure DevOps. The handler selects the correct CLI commands based on `manifest.yml` `work_items.provider`.
5. **Deterministic matching.** No semantic or NLP-based similarity. Matching is label-based (Level 1) and field-based string containment (Level 2).
