# Handler: validate

Check CI/CD pipeline compliance against governance standards.

## Process

1. **Lint workflows**:
   - GitHub Actions: `actionlint` on all `.github/workflows/*.yml`.
   - Azure Pipelines: YAML schema validation.

2. **Check SHA pinning**:
   - Run `python scripts/check_workflow_policy.py` (or manual scan).
   - Every third-party action must use SHA pin with tag comment.
   - First-party (`actions/*`) may use major tags.
   - Prohibited: mutable tags like `@v2` on third-party actions.

3. **Check timeouts**:
   - Every job must have `timeout-minutes`.
   - Default should not exceed 30 minutes for standard jobs.

4. **Check concurrency**:
   - Workflows must define `concurrency` group to prevent parallel runs.
   - Typical: `group: ${{ github.workflow }}-${{ github.ref }}`.

5. **Check security**:
   - No hardcoded secrets in workflow files.
   - OIDC preferred over long-lived credentials.
   - `permissions` block is minimal (principle of least privilege).
   - No `permissions: write-all`.

6. **Check environment protection**:
   - Production deployments use protected environments.
   - Approval gates configured for production.

7. **Check stack coverage**:
   - For each declared stack, verify corresponding lint/test/security jobs exist.
   - Cross-reference with `manifest.yml` enforcement checks.

## Output

```markdown
## Pipeline Compliance Report

| Check | Status | Detail |
|-------|--------|--------|
| SHA Pinning | PASS/FAIL | N actions pinned, M unpinned |
| Timeouts | PASS/FAIL | N jobs with timeout, M without |
| Concurrency | PASS/FAIL | Groups defined / missing |
| Security | PASS/FAIL | Hardcoded secrets / OIDC status |
| Stack Coverage | PASS/FAIL | Stacks covered / missing |
| Lint (actionlint) | PASS/FAIL | N warnings, M errors |
```
