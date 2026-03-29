---
name: performance
description: "Detect performance regressions, test suite slowdowns, build time increases, and bundle size growth"
type: operational
cadence: weekly
---

# Performance Runbook

## Objetivo

Detect performance regressions across CI pipelines, test suites, and build artifacts on a weekly cadence. The runbook compares recent metrics against historical baselines, flags regressions that exceed configured thresholds, and creates task work items for each finding. It never modifies code, tests, or build configuration -- it only observes and reports.

## Precondiciones

- `gh` or `az` CLI authenticated for fetching CI run data and creating work items.
- `pytest` installed for test suite timing (optional; Step 3 is skipped if unavailable).
- `python3` available for manifest parsing in Step 7.
- `git` available for causal commit analysis in Step 6.

## Procedimiento

### Step 1 -- Fetch recent CI run times

Pull the last 20 workflow runs to establish current performance data.

```bash
gh run list --limit 20 \
  --json databaseId,conclusion,createdAt,updatedAt \
  --jq '[.[] | {id: .databaseId, conclusion: .conclusion, started: .createdAt, ended: .updatedAt, duration_s: (((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)))}]'
```

Store the result as `$RECENT_RUNS`. Filter to successful runs only (`conclusion == "success"`) -- failed runs skew timing data due to early exits.

### Step 2 -- Calculate CI duration trend

Split `$RECENT_RUNS` into two buckets: last 7 days and previous 7 days. Compute the average duration for each bucket.

```
avg_current  = mean(duration_s for runs in last 7 days)
avg_previous = mean(duration_s for runs in previous 7 days)
ci_delta_pct = ((avg_current - avg_previous) / avg_previous) * 100
```

If `ci_delta_pct` exceeds `build_time_increase_pct` (15%), flag as a CI-level regression. Record `avg_current`, `avg_previous`, and `ci_delta_pct` for the final report.

### Step 3 -- Run test suite with timing

Execute the test suite with duration reporting to identify the slowest individual tests.

```bash
pytest tests/ --durations=20 -q 2>&1
```

Parse the `slowest 20 durations` output. For each test, extract the module path, test name, and duration in seconds. Store as `$TEST_TIMINGS`.

If `pytest` is unavailable on the host (see Precondiciones), skip this step and note the gap in the report.

### Step 4 -- Compare test timing against baseline

Check for a stored baseline from the previous run or CI artifact.

```bash
gh run download --name perf-baseline --dir /tmp/perf-baseline 2>/dev/null
```

If a baseline file exists at `/tmp/perf-baseline/test-timings.json`, compare each test in `$TEST_TIMINGS` against its baseline entry:

```
test_delta_pct = ((current_duration - baseline_duration) / baseline_duration) * 100
```

Tests without a baseline entry are recorded as "new -- no comparison available" and excluded from regression analysis.

### Step 5 -- Check build artifact sizes

If the repository produces build artifacts, compare the latest sizes against the previous run.

```bash
gh run download --name build-artifacts --dir /tmp/build-current 2>/dev/null
gh run download --name build-artifacts-previous --dir /tmp/build-previous 2>/dev/null
```

For each artifact present in both directories, compute the size delta:

```
size_delta_pct = ((current_size - previous_size) / previous_size) * 100
```

Flag any artifact where `size_delta_pct` exceeds `build_time_increase_pct` (15%). If no artifacts are available, skip this step and note it in the report.

### Step 6 -- Identify regressions above threshold

Collect all findings from Steps 2-5 that exceed their respective thresholds:

| Source | Threshold | Field |
|--------|-----------|-------|
| CI duration | `build_time_increase_pct` (15%) | `ci_delta_pct` |
| Individual test | `test_slowdown_pct` (20%) | `test_delta_pct` |
| Build artifact | `build_time_increase_pct` (15%) | `size_delta_pct` |

Sort findings by delta percentage descending. Cap at `max_findings_per_run` (10) to respect the mutation guardrail. If more regressions exist than the cap allows, include only the top 10 and note the overflow count in the report.

For each finding, identify likely causal commits by inspecting the git log for the affected module within the measurement window:

```bash
git log --oneline --since="14 days ago" -- "<module_path>"
```

### Step 7 -- Create task work items

Before creating any work items, detect which provider is configured in the project manifest:

```bash
WORK_ITEM_PROVIDER=$(python3 - <<'EOF'
import sys, pathlib
try:
    import yaml
    manifest = pathlib.Path(".ai-engineering/manifest.yml")
    data = yaml.safe_load(manifest.read_text()) if manifest.exists() else {}
    print(data.get("work_items", {}).get("provider", "github"))
except Exception:
    print("github")
EOF
)
```

If `python3 -c "import yaml"` fails (PyYAML absent), fall back to a plain-text grep:

```bash
WORK_ITEM_PROVIDER=$(grep -E '^\s*provider:' .ai-engineering/manifest.yml 2>/dev/null \
  | head -1 | sed 's/.*provider:[[:space:]]*//' | tr -d '"' | tr -d "'" || echo "github")
```

For each regression finding (up to `max_findings_per_run`), create a task work item using the detected provider.

**GitHub** (`WORK_ITEM_PROVIDER=github`):

```bash
gh issue create \
  --title "perf-regression: $TEST_OR_MODULE slowed by ${DELTA_PCT}%" \
  --body "## Performance Regression

- **Target:** $TEST_OR_MODULE
- **Old duration:** ${OLD_DURATION}s
- **New duration:** ${NEW_DURATION}s
- **Increase:** ${DELTA_PCT}%
- **Threshold:** ${THRESHOLD}%
- **Likely commits:**
$COMMIT_LIST

<!-- performance-runbook:regression -->" \
  --label "perf-regression,bug"
```

**Azure DevOps** (`WORK_ITEM_PROVIDER=azure_devops`):

```bash
az boards work-item create \
  --type Task \
  --title "perf-regression: $TEST_OR_MODULE slowed by ${DELTA_PCT}%" \
  --description "Old: ${OLD_DURATION}s | New: ${NEW_DURATION}s | Delta: ${DELTA_PCT}% | Threshold: ${THRESHOLD}% | Commits: $COMMIT_LIST" \
  --fields "System.Tags=perf-regression"
```

If `WORK_ITEM_PROVIDER` is unrecognised, default to GitHub.

### Step 8 -- Create weekly summary work item

Always create one summary work item regardless of whether regressions were found. This is the single source of truth for the weekly scan result on the board.

**GitHub** (`WORK_ITEM_PROVIDER=github`):

```bash
gh issue create \
  --title "perf: weekly scan $(date -u +%Y-%m-%d) — ${REGRESSION_COUNT} regression(s)" \
  --body "## Weekly Performance Scan

**Date:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
**CI avg duration (current / previous):** ${AVG_CURRENT}s / ${AVG_PREVIOUS}s (${CI_DELTA_PCT}%)
**Regressions found:** ${REGRESSION_COUNT}
**Work items created:** ${ITEMS_CREATED}
**Overflow (not created):** ${OVERFLOW_COUNT}

### Slowest tests
$SLOWEST_TESTS_LIST

### Notes
$NOTES_LIST

<!-- performance-runbook:weekly-summary -->" \
  --label "perf-weekly,tracking"
```

**Azure DevOps** (`WORK_ITEM_PROVIDER=azure_devops`):

```bash
az boards work-item create \
  --type Task \
  --title "perf: weekly scan $(date -u +%Y-%m-%d) — ${REGRESSION_COUNT} regression(s)" \
  --description "CI avg: ${AVG_CURRENT}s / ${AVG_PREVIOUS}s (${CI_DELTA_PCT}%) | Regressions: ${REGRESSION_COUNT} | Items created: ${ITEMS_CREATED} | Overflow: ${OVERFLOW_COUNT} | Slowest: $SLOWEST_TESTS_LIST | Notes: $NOTES_LIST" \
  --fields "System.Tags=perf-weekly"
```

## Output

Performance summary to stdout. One weekly summary work item plus regression work items. No local files are written.

## Guardrails

- **Mutations enabled by default.** All qualifying work items are created automatically.
- **Mutation cap.** Maximum 10 work item creations per run (`max_mutations`). If the cap is reached, stop creating items and report the remaining findings in the summary.
- **Never modifies code or tests.** This runbook does not edit source files, test files, CI configuration, or build scripts. It only reads timing data and creates tracking items.
- **Never closes or modifies existing issues.** Items labeled `p1-critical` or `pinned` are never relabeled. Issues in `closed` or `resolved` state are never touched.
- **Never re-runs tests destructively.** The `pytest` invocation is read-only -- it runs the suite but does not modify fixtures, databases, or external services. If the test suite has side effects, the host must provide an isolated environment.
- **Idempotent within cadence.** Running the procedure multiple times in the same week produces duplicate work items. Hosts should gate execution to once per cadence period.
- **Threshold integrity.** The `test_slowdown_pct` and `build_time_increase_pct` thresholds are never weakened at runtime. To adjust them, update this runbook and commit the change through the normal review process.
