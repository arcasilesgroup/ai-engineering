---
id: "038"
slug: "sonarcloud-quality-gate-integration"
status: "in-progress"
created: "2026-03-09"
size: "M"
tags: ["sonar", "cicd", "quality-gate", "coverage", "governance"]
branch: "feat/038-sonarcloud-quality-gate-integration"
pipeline: "full"
decisions: []
---

# Spec 038 — SonarCloud Quality Gate Integration

## Problem

La integración Sonar actual (specs 024, 030) genera steps de CI/CD pero tiene 4 gaps críticos:
1. **No exporta coverage reports** — SonarCloud muestra 0% coverage porque no recibe `coverage.xml`
2. **No verifica el Quality Gate** — el scan corre pero nadie comprueba si el QG pasa o falla
3. **Usa `sonarcloud-github-action@v3` que está deprecated** — SonarSource recomienda `sonarqube-scan-action`
4. **Dashboards y release gate no consultan SonarCloud** — las métricas existen pero no se consumen

El repo `arcasilesgroup/ai-engineering` tiene organización en SonarCloud pero no está wired al CI.

## Solution

`sonar-project.properties` como single source of truth con `sonar.qualitygate.wait=true`. El scanner polls el Quality Gate y falla si no pasa — funciona idénticamente en GitHub Actions, Azure Pipelines, y cualquier otro runner sin config específica de CI. Migrar action deprecated. Exportar coverage XML. Wiring del repo real. Release gate y observe consultan SonarCloud API.

Todo preserva silent-skip: si Sonar no está configurado, nada cambia, nada falla.

## Scope

### In Scope
1. Template `sonar-project.properties` completo con `sonar.qualitygate.wait=true` y coverage paths por stack
2. Migración `sonarcloud-github-action@v3` (deprecated) → `sonarqube-scan-action@v4` (unificada Cloud+Server)
3. Coverage report generation (Cobertura XML) en CI
4. Wiring del repo real `arcasilesgroup/ai-engineering` a SonarCloud
5. Release gate consultation de SonarCloud Quality Gate status (advisory)
6. Observe dashboard con métricas Sonar (silent-skip si no configurado)
7. Stack-aware coverage paths (Python, dotnet, nextjs)

### Out of Scope
- SonarQube self-hosted deployment/management
- Custom quality profiles en SonarCloud
- SonarLint rule customization (cubierto en spec 024)
- Sonar scanner local installation automation

## Acceptance Criteria

1. `sonar-project.properties` template incluye `sonar.qualitygate.wait=true`, `sonar.qualitygate.timeout=300`, y coverage paths por stack
2. `_render_github_sonar_steps` usa `sonarqube-scan-action@v4` (no la deprecated)
3. CI del repo real exporta `coverage.xml` y lo envía a SonarCloud
4. Si el Quality Gate de SonarCloud falla, el CI falla (scanner exit code != 0)
5. `ai-eng observe engineer` muestra métricas Sonar cuando están disponibles, skip silencioso si no
6. Release gate incluye Sonar QG status como dimensión advisory
7. Todos los tests pasan con cobertura >=90%
8. Equipos sin Sonar configurado no ven ningún cambio de behavior

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D038-001 | `sonar.qualitygate.wait=true` en `sonar-project.properties` | Universal: un fichero, funciona en cualquier CI/scanner/plataforma sin config específica |
| D038-002 | `sonar.qualitygate.timeout=300` (5 min) | Suficiente para proyectos medianos; alineado con `pollingTimeoutSec` de Azure |
| D038-003 | Migrar `sonarcloud-github-action@v3` → `sonarqube-scan-action@v4` | Deprecated por SonarSource; la nueva unifica Cloud + Server |
| D038-004 | Coverage format: Cobertura XML | Universal: pytest-cov, coverlet, istanbul/c8 |
| D038-005 | Sonar QG en release gate: advisory (no blocking) | Consistent con D030-003; equipos pueden promover a blocking |
| D038-006 | Fork guard en CI Sonar steps | Evita exposición de `SONAR_TOKEN` en PRs de forks |
