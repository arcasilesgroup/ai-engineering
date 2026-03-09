---
spec: "038"
total: 17
completed: 0
last_session: "2026-03-09"
next_session: "Phase 1"
---

# Tasks — SonarCloud Quality Gate Integration

### Phase 0: Scaffold [S]
- [ ] 0.1 Scaffold spec files and activate

### Phase 1: Properties Template + Action Migration [M]
- [ ] 1.1 Actualizar template sonar-project.properties con propiedades completas (qualitygate.wait, timeout, sources, tests, exclusions, coverage paths por stack)
- [ ] 1.2 Migrar _render_github_sonar_steps en installer/cicd.py: sonarcloud-github-action@v3 → sonarqube-scan-action@v4 para SonarCloud
- [ ] 1.3 Extender _render_github_ci para generar coverage report por stack antes del Sonar step
- [ ] 1.4 Extender _render_azure_ci para generar coverage report por stack antes del Sonar step
- [ ] 1.5 Tests: test_cicd_sonar.py — verificar nueva action, properties template, coverage steps por stack

### Phase 2: CI Real del Repo [M]
- [ ] 2.1 Crear sonar-project.properties en raíz del repo con valores para arcasilesgroup/ai-engineering
- [ ] 2.2 Añadir --cov-report=xml:coverage.xml al coverage step en .github/workflows/ci.yml
- [ ] 2.3 Añadir job sonarcloud al CI real: sonarqube-scan-action@v4, SONAR_TOKEN secret, fork guard, depende del coverage job
- [ ] 2.4 Documentar: SONAR_TOKEN debe configurarse como GitHub secret manualmente

### Phase 3: Release Gate + Observe [M]
- [ ] 3.1 Extender check_sonar_gate (policy/checks/sonar.py) para consultar SonarCloud Web API /api/qualitygates/project_status cuando token disponible
- [ ] 3.2 Añadir Sonar QG status al release gate verdict como dimensión advisory
- [ ] 3.3 Añadir métricas Sonar al observe dashboard engineer (coverage %, QG status, issues count) — silent-skip si no configurado
- [ ] 3.4 Tests: API mock, observe rendering, gate consultation

### Phase 4: Tests + Close [S]
- [ ] 4.1 Verificar cobertura >=90% con los cambios
- [ ] 4.2 Todos los tests pasan (unit + integration)
- [ ] 4.3 Crear done.md, actualizar counters
