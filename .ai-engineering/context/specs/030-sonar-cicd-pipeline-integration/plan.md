---
spec: "030"
approach: "serial-phases"
---

# Plan - Sonar CI/CD Pipeline Integration

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/templates/pipeline/github-sonar-step.yml` | Reusable GitHub Sonar snippet template (Cloud/Qube guidance). |
| `src/ai_engineering/templates/pipeline/azure-sonar-task.yml` | Reusable Azure Sonar task template (Prepare/Analyze/Publish guidance). |
| `src/ai_engineering/templates/pipeline/sonar-project.properties` | Create-only baseline Sonar project properties template. |
| `tests/unit/test_cicd_sonar.py` | CI rendering coverage for Sonar enabled/disabled and provider branches. |

### Modified Files

| File | Change |
|------|--------|
| `src/ai_engineering/credentials/models.py` | Add `organization` to `SonarConfig`. |
| `src/ai_engineering/cli_commands/setup.py` | Add `--organization`, property reader, and persistence wiring. |
| `src/ai_engineering/state/models.py` | Add `SonarCicdConfig` and `CicdStatus.sonar`. |
| `src/ai_engineering/installer/cicd.py` | Accept/render Sonar config for GitHub/Azure CI generation. |
| `src/ai_engineering/installer/service.py` | Resolve Sonar config, pass to generation, update manifest, generate properties file. |
| `src/ai_engineering/cli_commands/cicd.py` | Resolve Sonar config and pass through regenerate flow. |
| `src/ai_engineering/pipeline/compliance.py` | Add informational Sonar analysis detection for primary `ci.yml`. |
| `src/ai_engineering/pipeline/injector.py` | Add Sonar snippet generation and type-aware suggestion support. |
| `src/ai_engineering/policy/gates.py` | Add advisory `_check_sonar_gate()` and pre-push ordering integration. |
| `.ai-engineering/skills/cicd/SKILL.md` | Document optional Sonar integration and create-only caveat. |
| `src/ai_engineering/templates/.ai-engineering/skills/cicd/SKILL.md` | Mirror sync for updated skill docs. |
| `tests/unit/test_credentials.py` | Validate Sonar `organization` in model round-trip. |
| `tests/unit/test_setup_cli.py` | Cover `--organization` parsing and property reader. |
| `tests/unit/test_state.py` | Cover `SonarCicdConfig` behavior and `CicdStatus.sonar` serialization. |
| `tests/unit/test_pipeline_compliance.py` | Cover informational Sonar compliance checks and injector snippets. |
| `tests/unit/test_gates.py` | Cover advisory Sonar gate skip/fail/pass behavior. |
| `tests/unit/test_installer.py` | Cover sonar passthrough argument in install orchestration. |

### Mirror Copies

| Canonical | Mirror |
|----------|--------|
| `.ai-engineering/skills/cicd/SKILL.md` | `src/ai_engineering/templates/.ai-engineering/skills/cicd/SKILL.md` |

## Session Map

| Phase | Description | Size |
|------|-------------|------|
| 0 | Scaffold spec and persist decisions | M |
| 1 | Models + setup extension | M |
| 2 | Pipeline generation rendering + wiring | L |
| 3 | Compliance/injector/templates + docs | M |
| 4 | Advisory pre-push Sonar gate | M |
| 5 | Tests + verification | L |

## Patterns

- Silent-skip for optional Sonar integration (`D024-002`).
- Hostname parsing via `urllib.parse.urlparse` for SonarCloud detection.
- Create-only semantics preserved for generated files.
- No token material written to repository files.
- Keep CI insertion ordering deterministic: stack checks -> Sonar -> security checks.
