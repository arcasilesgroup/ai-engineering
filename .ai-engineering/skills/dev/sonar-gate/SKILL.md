---
name: sonar-gate
description: "Run SonarCloud/SonarQube quality gate locally before push; silently skips when SONAR_TOKEN is not configured."
version: 1.0.0
category: dev
tags: [quality, sonar, gate, pre-push]
metadata:
  ai-engineering:
    requires:
      bins: [sonar-scanner]
    scope: read-only
    token_estimate: 850
---

# Sonar Gate

## Purpose

Run a SonarCloud / SonarQube quality gate analysis locally before push. Catches quality gate failures early — before CI/CD — by running `sonar-scanner` with `qualitygate.wait=true`. Silently skips when Sonar is not configured, following the framework principle that optional integrations never block teams that don't use them (D024-002).

## Trigger

- Command: agent invokes sonar-gate skill or user requests local Sonar analysis.
- Context: pre-push hook, quality audit, release readiness check.
- Automatic: integrated as an optional step in `audit-code` and `release-gate` skills.

## When NOT to Use

- **Full quality audit** (coverage, lint, type checks, security) — use `quality:audit-code` instead. Sonar-gate runs the Sonar-specific analysis only.
- **Setting up Sonar credentials** — use `ai-eng setup sonar` instead.
- **CI/CD Sonar integration** — this skill covers local/pre-push only.

## Procedure

1. **Check prerequisites** — verify Sonar is configured.
   - Read `tools.json` for `sonar.configured` flag.
   - Check `SONAR_TOKEN` environment variable or keyring entry.
   - If neither is available: **silent skip** — emit info log and return SKIP.

2. **Resolve configuration** — gather Sonar analysis parameters.
   - Read `sonar-project.properties` for `sonar.projectKey`, `sonar.host.url`.
   - Override with `tools.json` values if present.
   - Determine token source: env var `SONAR_TOKEN` → keyring entry.

3. **Execute Sonar scanner** — run analysis with quality gate wait.
   - Set `SONAR_TOKEN` environment variable from keyring if needed.
   - Execute the appropriate cross-OS script:
     - Bash: `scripts/sonar-pre-gate.sh`
     - PowerShell: `scripts/sonar-pre-gate.ps1`
   - Pass parameters: `-Dsonar.qualitygate.wait=true`

4. **Parse result** — evaluate quality gate outcome.
   - Parse scanner exit code: 0 = PASS, non-zero = FAIL.
   - If quality gate wait is supported, parse the gate status from output.

5. **Report** — emit structured result.
   - **PASS**: Sonar quality gate passed.
   - **FAIL**: Sonar quality gate failed — list violations.
   - **SKIP**: Sonar not configured — no action taken.

## Threshold Mapping

The Sonar quality gate should mirror the framework quality contract:

| Framework Metric      | Sonar Property                   | Threshold         |
| --------------------- | -------------------------------- | ----------------- |
| Coverage (overall)    | `sonar.coverage`                 | ≥ 90%             |
| Duplicated lines      | `sonar.duplicated_lines_density` | ≤ 3%              |
| Blocker issues        | `sonar.blocker_violations`       | 0                 |
| Critical issues       | `sonar.critical_violations`      | 0                 |
| Cyclomatic complexity | `sonar.complexity`               | ≤ 10 per function |
| Cognitive complexity  | `sonar.cognitive_complexity`     | ≤ 15 per function |

See `references/sonar-threshold-mapping.md` for detailed mapping.

## Output Contract

```markdown
## Sonar Gate Result

| Field   | Value                          |
| ------- | ------------------------------ |
| Status  | **PASS** / **FAIL** / **SKIP** |
| Reason  | <gate status or skip reason>   |
| Server  | <sonar URL>                    |
| Project | <project key>                  |

### Violations (if FAIL)

| Severity | Count | Description |
| -------- | ----- | ----------- |
```

## Governance Notes

- Sonar gate is **optional** — never blocks teams that don't use Sonar (D024-002).
- Silent skip when not configured — no error, no warning interrupting workflows.
- Token is retrieved from OS keyring, never from files or environment by default.
- This skill provides the Sonar-specific procedure; `audit-code` orchestrates it.
- Threshold alignment is the team's responsibility via `sonar-project.properties`.

## References

- `skills/quality/audit-code/SKILL.md` — orchestrator skill that invokes this gate.
- `skills/quality/release-gate/SKILL.md` — release readiness that includes this gate.
- `skills/quality/install-check/SKILL.md` — validates Sonar setup is operational.
- `skills/dev/sonar-gate/references/sonar-threshold-mapping.md` — detailed threshold mapping.
- `standards/framework/quality/core.md` — quality contract (source thresholds).
