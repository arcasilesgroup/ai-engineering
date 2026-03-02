# Sonar Threshold Mapping

Maps the ai-engineering quality contract to SonarCloud/SonarQube quality gate conditions.

## Quality Contract → Sonar Properties

| Framework Metric | Framework Threshold | Sonar Metric Key | Sonar Condition | Direction |
|-----------------|--------------------|--------------------|-----------------|-----------|
| Coverage (overall) | ≥ 90% | `new_coverage` | ≥ 90.0 | ≥ is better |
| Duplicated lines | ≤ 3% | `new_duplicated_lines_density` | ≤ 3.0 | ≤ is better |
| Blocker issues | 0 | `new_blocker_violations` | = 0 | 0 is required |
| Critical issues | 0 | `new_critical_violations` | = 0 | 0 is required |
| Cyclomatic complexity | ≤ 10 per function | `complexity` | N/A (manual review) | ≤ is better |
| Cognitive complexity | ≤ 15 per function | `cognitive_complexity` | N/A (manual review) | ≤ is better |

## Notes

### New Code Period

SonarCloud/SonarQube applies quality gate conditions to **new code** by default (metrics prefixed with `new_`). This aligns with the framework principle of evaluating changed code, not legacy code.

### Complexity Metrics

Sonar reports complexity at the file level, not per-function. The framework thresholds (cyclomatic ≤ 10, cognitive ≤ 15 per function) cannot be directly enforced via Sonar quality gate conditions. Use `ruff` for per-function complexity enforcement and Sonar for aggregate visibility.

### Custom Quality Gate

To align a SonarCloud/SonarQube quality gate with the framework contract, create a custom quality gate with these conditions:

```
Condition on New Code:
  Coverage < 90%                       → Blocker
  Duplicated Lines (%) > 3%            → Critical
  Blocker Issues > 0                   → Blocker
  Critical Issues > 0                  → Blocker
  Security Hotspots Reviewed < 100%    → Critical
  Reliability Rating worse than A      → Critical
  Security Rating worse than A         → Critical
```

### Silent Skip Logic

The sonar-gate skill follows this decision tree:

1. `tools.json` → `sonar.configured == false` → **SKIP** (silent).
2. `SONAR_TOKEN` env var not set AND keyring entry absent → **SKIP** (silent).
3. `sonar-scanner` not on PATH → **SKIP** with info message.
4. `sonar-project.properties` not found → **SKIP** with info message.
5. All present → **RUN** analysis with `qualitygate.wait=true`.

### Environment Variable Precedence

Token resolution order:
1. `SONAR_TOKEN` environment variable (CI/CD and local override).
2. OS keyring entry at `ai-engineering/sonar` / `token`.
3. If neither: silent skip.
