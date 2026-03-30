# Auditoría integral de ai-engineering (arquitectura + operación)

> Nota de vigencia: este documento contiene una auditoría histórica previa a `spec-082`. Donde aparezcan `observe`, `signals` o `.ai-engineering/state/audit-log.ndjson`, deben leerse como antecedentes del diseño retirado. La superficie soportada hoy es `.ai-engineering/state/framework-events.ndjson` + `.ai-engineering/state/framework-capabilities.json`, con `agentsview` instalado y abierto independientemente por el usuario.

## Alcance y método

Auditoría estática y funcional del repositorio `ai-engineering` con foco en:

- arquitectura de producto y de código
- gobernanza y enforcement local
- dependencias internas/externas
- mapa de funcionalidades por comandos
- operación end-to-end real (desde instalación hasta release/observabilidad)

Base analizada:

- `src/ai_engineering/**` (CLI, servicios, policy engine, estado, VCS)
- `.ai-engineering/**` (manifest, skills, agentes, runbooks, estándares, contexto, estado)
- `scripts/**`, `tests/**`, `README.md`, `pyproject.toml`

## Resumen ejecutivo

- `ai-engineering` es un **framework de gobernanza local-first** operado por CLI (`ai-eng`) y reforzado por git hooks.
- El núcleo operativo se divide en: `installer`, `policy/gates`, `doctor`, `validator`, `updater`, `release`, `state`.
- El **single source of truth** operativo es contenido en repo (`.ai-engineering/**`) + eventos en `.ai-engineering/state/framework-events.ndjson` y `.ai-engineering/state/framework-capabilities.json`.
- El diseño es **provider-aware** (GitHub/Azure DevOps y múltiples AI providers) con fallback de API/CLI.
- Se observan dos gaps operativos de entorno en esta sesión:
  - `pytest` no ejecuta por dependencia faltante (`pydantic`) en el entorno actual.
  - `ty check` reporta múltiples diagnósticos en el repo (no bloqueantes para documentar, pero relevantes para salud técnica).

## Inventario técnico observado

- Módulos Python en `src/ai_engineering`: 33 áreas funcionales.
- Comandos CLI: núcleo + subgrupos operativos (`stack`, `ide`, `gate`, `skill`, `maintenance`, `provider`, `vcs`, `review`, `cicd`, `setup`, `decision`, `spec`, `scan-report`, `metrics`, `workflow`, `work-item`).
- Skills: 34 (flat organization).
- Agentes: 7.
- Runbooks: 14.
- Tests: 82 archivos, 124 tests detectados.

## Diagrama 1: Alto nivel (producto/sistema)

```mermaid
flowchart TB
    U[Usuario / Equipo] --> CLI[ai-eng CLI\nTyper app]
    CLI --> GOV[.ai-engineering\nGovernance Root]
    CLI --> HOOKS[Git Hooks\npre-commit / commit-msg / pre-push]
    CLI --> STATE[State Store\nJSON + NDJSON]
    CLI --> VCS[VCS Provider\nGitHub / Azure DevOps]
    CLI --> PIPE[CI/CD Templates\nGitHub Actions / Azure Pipelines]

    GOV --> STANDARDS[standards/]
    GOV --> SKILLS[skills/]
    GOV --> AGENTS[agents/]
    GOV --> CONTEXT[context/]
    GOV --> RBS[runbooks/]

    STATE --> DS[decision-store.json]
    STATE --> AUDIT[framework-events.ndjson]
    STATE --> CAPS[framework-capabilities.json]
    STATE --> MANIFEST[install-manifest.json]
    STATE --> OWN[ownership-map.json]
    STATE --> CHECK[session-checkpoint.json]

    HOOKS --> GATES[Policy Gate Engine]
    GATES --> AUDIT
```

## Diagrama 2: Arquitectura lógica del código (nivel arquitectura)

```mermaid
flowchart LR
    CLI[cli.py + cli_factory.py] --> CMDS[cli_commands/*]

    CMDS --> INST[installer.service]
    CMDS --> DOC[doctor.service]
    CMDS --> UPD[updater.service]
    CMDS --> VAL[validator.service]
    CMDS --> REL[release.orchestrator]
    CMDS --> POL[policy.gates]
    CMDS --> OBS[framework events + agentsview contract]
    CMDS --> SKS[skills.service]
    CMDS --> MAINT[maintenance.*]
    CMDS --> VCSF[vcs.factory]

    INST --> TPL[installer.templates + cicd + branch_policy]
    INST --> HOOKM[hooks.manager]
    INST --> STIO[state.io + defaults]
    POL --> CHK[policy.checks/* + stack_runner]
    REL --> VPROTO[vcs.protocol + providers]
    OBS --> AUD[state.audit + framework-events]
    VAL --> CAT[validator.categories/*]

    STIO --> MODELS[state.models]
    VCSF --> GH[vcs.github]
    VCSF --> AZ[vcs.azure_devops]
    VCSF --> APIF[vcs.api_fallback]
```

## Diagrama 3: Flujo técnico de enforcement (nivel técnico)

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant CLI as ai-eng install/doctor/update
    participant Inst as installer.service
    participant Hooks as hooks.manager
    participant Gate as policy.gates
    participant Checks as stack/security checks
    participant State as state/*.json
    participant Audit as framework-events.ndjson

    Dev->>CLI: ai-eng install .
    CLI->>Inst: install(target, stacks, providers, vcs)
    Inst->>State: create manifests + ownership + decision store
    Inst->>Hooks: install managed git hooks
    Inst->>Audit: emit framework operation

    Dev->>Dev: git commit / git push
    Hooks->>Gate: run_gate(pre-commit / commit-msg / pre-push)
    Gate->>Checks: ruff/ty/pytest/pip-audit/semgrep/gitleaks + commit policy
    Gate->>Audit: emit git_hook outcome

    Dev->>CLI: ai-eng doctor
    CLI->>State: validate layout/state/tools/hooks/platform auth

    Dev->>CLI: ai-eng update --apply
    CLI->>State: ownership-aware update + rollback safety + framework event
```

## Diagrama 4: Dependencias (nivel dependencias)

```mermaid
flowchart TB
    subgraph Runtime
        TY[typer]
        YAML[pyyaml]
        PDM[pydantic]
        KR[keyring]
        RICH[rich]
    end

    subgraph External CLIs
        GIT[git]
        GH[gh]
        AZ[az]
        RUFF[ruff]
        TYC[ty]
        PYTEST[pytest]
        GITLEAKS[gitleaks]
        SEMGREP[semgrep]
        PIPA[pip-audit]
    end

    subgraph Core Modules
        CCLI[CLI Factory + Commands]
        INST[Installer]
        GATE[Policy Gates]
        DOC[Doctor]
        VAL[Validator]
        REL[Release]
        OBS[Observe/Signals]
        VCS[VCS Providers]
        ST[state.models/io]
    end

    CCLI --> INST
    CCLI --> GATE
    CCLI --> DOC
    CCLI --> VAL
    CCLI --> REL
    CCLI --> OBS
    CCLI --> VCS

    INST --> ST
    GATE --> ST
    DOC --> ST
    VAL --> ST
    REL --> ST
    OBS --> ST

    INST --> GIT
    INST --> GH
    INST --> AZ
    GATE --> RUFF
    GATE --> TYC
    GATE --> PYTEST
    GATE --> GITLEAKS
    GATE --> SEMGREP
    GATE --> PIPA

    CCLI --> TY
    ST --> PDM
    INST --> YAML
    CCLI --> RICH
    DOC --> KR
```

## Diagrama 5: Mapa de funcionalidades (nivel funcionalidades)

```mermaid
mindmap
  root((ai-engineering))
    Instalacion y bootstrap
      ai-eng install
      providers/stack/ide
      template seeding
      hooks setup
    Gobernanza y enforcement
      gate pre-commit
      gate commit-msg
      gate pre-push
      branch protection checks
      risk expiry checks
    Salud y diagnostico
      ai-eng doctor
      fix-hooks
      fix-tools
      readiness por stack
    Actualizacion segura
      ai-eng update
      ownership-aware changes
      dry-run por defecto
      rollback en fallo
    Integridad de contenido
      ai-eng validate
      7 categorias de integridad
      mirror/counters/frontmatter/references
    Flujo release
      ai-eng release
      semver + changelog
      PR + tag + pipeline monitor
    VCS y plataformas
      github
      azure devops
      setup github/sonar/azure-devops/sonarlint
    Observabilidad
      framework-events.ndjson
      framework-capabilities.json
      agentsview companion viewer
    Operacion de conocimiento
      spec verify/catalog/list/compact
      decision list/record/expire-check
      checkpoint save/load
    Ecosistema AI
      35 skills
      7 agents
      5 runbooks
      multi-provider adapters
```

## Diagrama 6: Diagrama de lujo (operación completa 100% E2E)

```mermaid
flowchart TD
    A[Start: Repo sin framework] --> B[ai-eng install]
    B --> C{Template + State bootstrapped?}
    C -- no --> X1[Abort + diagnóstico]
    C -- yes --> D[Hook installation + integrity hashes]
    D --> E[Tooling/auth/cicd readiness phases]
    E --> F[Developer workflow]

    F --> G[Create/change code + specs + context]
    G --> H[git commit]
    H --> I[pre-commit gate]
    I --> I1[ruff/gitleaks + stack checks]
    I1 --> J[commit-msg gate]
    J --> J1[policy format + trailer]
    J1 --> K[pre-push gate]
    K --> K1[tests/types/semgrep/pip-audit/risk expiry]
    K1 --> L{All gates pass?}

    L -- no --> M[Block push + actionable output]
    M --> N[Remediate + retry]
    N --> H

    L -- yes --> O[Push branch]
    O --> P[ai-eng review/pr/release flows]
    P --> Q[VCS provider API/CLI]
    Q --> R[PR + optional auto-complete]
    R --> S[Tag + release orchestration]
    S --> T[CI/CD pipelines generated/enforced]

    subgraph Observability & Governance Memory
      U1[framework-events.ndjson event stream]
      U5[framework-capabilities.json catalog]
      U2[decision-store lifecycle]
      U3[session-checkpoint recovery]
      U4[manifest + ownership map]
    end

    I --> U1
    J --> U1
    K --> U1
    P --> U1
    S --> U1
    B --> U4
    B --> U5
    F --> U2
    F --> U3

    T --> V[agentsview]
    V --> W[Sessions / transcripts / framework events]
    W --> Y[Continuous improvement loop]
    Y --> G
```

## Hallazgos de auditoría

1. El diseño es coherente con la promesa del README: gobernanza local con enforce por hooks y estado auditable.
2. La arquitectura separa correctamente responsabilidades:
   - entrada CLI,
   - orquestadores de dominio,
   - estado tipado,
   - proveedores VCS pluggable,
   - validación de integridad.
3. El modo `update` aplica patrón seguro (dry-run + ownership + backup/rollback).
4. `framework-events.ndjson` y `framework-capabilities.json` son ahora la base canónica de observabilidad del framework; las sesiones y transcripts viven en `agentsview`.
5. Hay inconsistencia de entorno/comando en sesión:
   - La guía pide `ai-eng checkpoint load`; el binario ejecutado respondió “No such command 'checkpoint'”.
   - El código fuente sí registra subcomando `checkpoint` en `cli_factory.py`.
   - Esto sugiere desalineación entre instalación activa y árbol fuente actual.
6. La salud técnica local no está completamente verde en este entorno:
   - `pytest` no ejecuta por dependencia ausente (`pydantic`).
   - `ty check` reporta 84 diagnósticos.

## Recomendaciones priorizadas

1. Alinear binario activo vs código fuente (`ai-eng version`, reinstall editable/local, validar `ai-eng --help`).
2. Corregir baseline de tipos en `ty` y fijar política de severidad/ci para evitar drift.
3. Asegurar entorno dev reproducible (lock de deps dev y bootstrap único para tests).
4. Añadir un comando de “self-diagnostic contract” que valide explícitamente paridad entre comandos documentados y comandos registrados.
