# Audit Prompt Catalog — ai-engineering Framework

> **Version**: 1.0.0 | **Framework**: ai-engineering v0.2.0 | **Total prompts**: 62 (6 agents + 33 skills + 4 standards + 18 cross-cutting + 1 rollup)
>
> Cada prompt es auto-contenido y ejecutable en Claude Code, GitHub Copilot, Codex o Gemini.

---

## Plantilla Universal de Output

Todos los prompts producen el mismo formato de salida:

```
## Audit: [Component Name]

**Score**: 0-100
**Verdict**: PASS (≥80) | WARN (60-79) | FAIL (<60)

### Findings

| # | Severity | Category | Finding | File:Line | Recommendation |
|---|----------|----------|---------|-----------|----------------|
| 1 | CRITICAL/HIGH/MEDIUM/LOW | ... | ... | ... | ... |

### Strengths
- ...

### Proposals
| # | Priority | Proposal | Effort | Impact |
|---|----------|----------|--------|--------|
| 1 | P1/P2/P3 | ... | S/M/L | HIGH/MEDIUM/LOW |
```

Severity scale: CRITICAL (blocker, must fix) > HIGH (should fix before release) > MEDIUM (fix in next sprint) > LOW (nice to have).

---

## Sección 1: Agentes (A1–A6)

### A1: Agente `plan`

```
You are auditing the `plan` agent of the ai-engineering framework. Read the following files:

1. `.ai-engineering/agents/plan.md`
2. `.ai-engineering/manifest.yml` (section: governance_surface.agents)
3. `.ai-engineering/standards/framework/core.md` (sections: behavioral baselines, progressive disclosure)
4. `.ai-engineering/standards/framework/skills-schema.md` (section: agent frontmatter)
5. `.ai-engineering/context/product/framework-contract.md` (section: 2. Agentic Model)

Perform these checks:

1. **Frontmatter compliance**: Verify all required fields (name, version, scope, capabilities, inputs, outputs) are present and valid per skills-schema.md.
2. **Scope correctness**: Confirm scope is `read-write` and matches the agent's actual responsibilities.
3. **Capability tokens**: Verify capabilities use valid domain tokens (Orchestration, Governance, Mapping, etc.) and cover the agent's purpose.
4. **Lifecycle coverage**: Check that the agent addresses all lifecycle phases it owns (Discovery → Architecture → Planning) per framework-contract.md section 2.
5. **Pipeline strategy**: Verify the agent handles all 4 pipeline types (full, standard, hotfix, trivial) as defined in manifest.yml.
6. **Session recovery**: Check for checkpoint save/load integration.
7. **Behavioral baselines**: Verify alignment with the 7 baselines in core.md (escalation ladder, post-change validation, confidence signaling, headless fallback, holistic analysis, exhaustiveness, parallel-first).
8. **Parallel execution**: Confirm the agent supports governed parallel execution per framework-contract.md section 2.
9. **Token budget**: Verify persona fits within ≤500 tokens as per skills-schema.md.
10. **Cross-references**: Check that all referenced skills, files, and paths exist in the repository.

Output using the Universal Output Template (Score 0-100, Verdict, Findings table, Strengths, Proposals).
```

### A2: Agente `build`

```
You are auditing the `build` agent of the ai-engineering framework. Read the following files:

1. `.ai-engineering/agents/build.md`
2. `.ai-engineering/manifest.yml` (section: governance_surface.agents)
3. `.ai-engineering/standards/framework/core.md` (sections: behavioral baselines, spec-first enforcement)
4. `.ai-engineering/standards/framework/skills-schema.md` (section: agent frontmatter)
5. `.ai-engineering/context/product/framework-contract.md` (sections: 2. Agentic Model, 4. Security and Quality)
6. `.ai-engineering/standards/framework/stacks/` (all 14 stack files)

Perform these checks:

1. **Frontmatter compliance**: Verify all required fields (name, version, scope, capabilities, inputs, outputs) are present and valid.
2. **Scope correctness**: Confirm scope is `read-write` — this is the ONLY code-write agent.
3. **Stack coverage**: Verify the agent references or handles all 14 stacks: astro, azure, bash-powershell, database, dotnet, infrastructure, nestjs, nextjs, node, python, react-native, react, rust, typescript.
4. **Skill dispatch**: Check that the agent can dispatch to all implementation skills (build, test, debug, refactor, code-simplifier, api, cli, db, infra, cicd, migrate).
5. **Spec-first enforcement**: Verify the agent checks for an active spec before non-trivial work (>3 files, new features, refactors).
6. **Quality gates**: Confirm integration with linting (ruff), formatting, type checking (ty), and test running (pytest).
7. **Security checks**: Verify the agent invokes gitleaks, semgrep, and dependency checks where applicable.
8. **Behavioral baselines**: Verify alignment with all 7 baselines (escalation ladder, post-change validation, etc.).
9. **Token budget**: Verify persona fits within ≤500 tokens.
10. **Exclusivity**: Confirm no other agent has code-write capabilities that overlap.

Output using the Universal Output Template.
```

### A3: Agente `scan`

```
You are auditing the `scan` agent of the ai-engineering framework. Read the following files:

1. `.ai-engineering/agents/scan.md`
2. `.ai-engineering/manifest.yml` (section: governance_surface.agents)
3. `.ai-engineering/standards/framework/core.md` (sections: behavioral baselines, content integrity)
4. `.ai-engineering/standards/framework/skills-schema.md` (section: agent frontmatter)
5. `.ai-engineering/standards/framework/quality/core.md`
6. `.ai-engineering/standards/framework/security/owasp-top10-2025.md`
7. `.ai-engineering/context/product/framework-contract.md` (section: 4. Security and Quality)

Perform these checks:

1. **Frontmatter compliance**: Verify all required fields are present and valid.
2. **Scope correctness**: Confirm scope is `read-write` limited to work items only (no code changes).
3. **7-mode coverage**: Verify the agent supports all 7 assessment modes: governance, security, quality, performance, accessibility, feature-gap, architecture.
4. **Skill mapping**: Check that the agent dispatches to the correct skills (security, quality, governance, architecture, perf, a11y, feature-gap).
5. **Quality thresholds**: Verify alignment with quality/core.md targets (coverage 90%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15, zero blocker/critical).
6. **Security standards**: Confirm alignment with OWASP Top 10 2025 and security/core requirements (zero medium/high/critical findings).
7. **Confidence signaling**: Verify the agent emits HIGH/MEDIUM/LOW confidence per core.md baseline.
8. **Work item creation**: Check that findings can generate work items (GitHub Issues/Projects).
9. **Behavioral baselines**: Verify alignment with all 7 baselines.
10. **Token budget**: Verify persona fits within ≤500 tokens.

Output using the Universal Output Template.
```

### A4: Agente `release`

```
You are auditing the `release` agent of the ai-engineering framework. Read the following files:

1. `.ai-engineering/agents/release.md`
2. `.ai-engineering/manifest.yml` (sections: governance_surface.agents, commands)
3. `.ai-engineering/standards/framework/core.md` (sections: behavioral baselines, enforcement rules)
4. `.ai-engineering/standards/framework/skills-schema.md` (section: agent frontmatter)
5. `.ai-engineering/context/product/framework-contract.md` (sections: 2. Agentic Model, 5. Distribution Model)

Perform these checks:

1. **Frontmatter compliance**: Verify all required fields are present and valid.
2. **Scope correctness**: Confirm scope is `read-write`.
3. **Command contract**: Verify the agent implements the exact command contract: `/ai:commit` (stage+commit+push), `/ai:commit --only` (stage+commit), `/ai:pr` (stage+commit+push+PR+auto-complete), `/ai:pr --only` (create PR, warn if unpushed).
4. **Skill dispatch**: Check coverage of release skills (commit, pr, release, changelog, work-item).
5. **Gate enforcement**: Verify pre-commit and pre-push gates are enforced (gitleaks, semgrep, stack checks).
6. **Protected branch safety**: Confirm the agent blocks direct commits/pushes to main/master.
7. **SemVer compliance**: Check alignment with the distribution model's release/SemVer standards.
8. **Behavioral baselines**: Verify alignment with all 7 baselines.
9. **Hook hash verification**: Confirm the agent respects hook integrity (no --no-verify).
10. **Token budget**: Verify persona fits within ≤500 tokens.

Output using the Universal Output Template.
```

### A5: Agente `write`

```
You are auditing the `write` agent of the ai-engineering framework. Read the following files:

1. `.ai-engineering/agents/write.md`
2. `.ai-engineering/manifest.yml` (section: governance_surface.agents)
3. `.ai-engineering/standards/framework/core.md` (sections: behavioral baselines, non-negotiables)
4. `.ai-engineering/standards/framework/skills-schema.md` (section: agent frontmatter)
5. `.ai-engineering/context/product/framework-contract.md` (section: 3. Ownership Model)

Perform these checks:

1. **Frontmatter compliance**: Verify all required fields are present and valid.
2. **Scope correctness**: Confirm scope is `read-write` limited to docs only.
3. **Mode coverage**: Verify the agent supports generate and simplify modes.
4. **Skill dispatch**: Check that the agent dispatches to the `docs` skill.
5. **Ownership boundaries**: Verify the agent respects the ownership model (framework-managed vs team-managed vs project-managed).
6. **Non-negotiable**: Confirm docs updates are required for user-visible changes as per core.md.
7. **Behavioral baselines**: Verify alignment with all 7 baselines.
8. **Cross-references**: Verify all internal links and file references resolve correctly.
9. **Progressive disclosure**: Check that documentation follows the 3-level loading model.
10. **Token budget**: Verify persona fits within ≤500 tokens.

Output using the Universal Output Template.
```

### A6: Agente `observe`

```
You are auditing the `observe` agent of the ai-engineering framework. Read the following files:

1. `.ai-engineering/agents/observe.md`
2. `.ai-engineering/manifest.yml` (sections: governance_surface.agents, observability)
3. `.ai-engineering/standards/framework/core.md` (sections: behavioral baselines)
4. `.ai-engineering/standards/framework/skills-schema.md` (section: agent frontmatter)
5. `.ai-engineering/context/product/framework-contract.md` (sections: 2. Agentic Model)

Perform these checks:

1. **Frontmatter compliance**: Verify all required fields are present and valid.
2. **Scope correctness**: Confirm scope is `read-only` — this agent must NOT modify code or state.
3. **5-mode coverage**: Verify the agent supports all 5 observability modes (engineer, team, ai, dora, health).
4. **4-audience tiers**: Confirm support for all audience tiers per manifest.yml.
5. **DORA metrics**: Verify integration with DORA metrics (deployment frequency, lead time, change failure rate, MTTR).
6. **Health scoring**: Check that the agent produces health scores with a defined methodology.
7. **Event store integration**: Verify the agent reads from `state/audit-log.ndjson`.
8. **Behavioral baselines**: Verify alignment with all 7 baselines.
9. **Confidence signaling**: Verify HIGH/MEDIUM/LOW confidence emission for read-only analysis.
10. **Token budget**: Verify persona fits within ≤500 tokens.

Output using the Universal Output Template.
```

---

## Sección 2: Skills (Plantilla Parametrizada)

### Plantilla de Auditoría de Skill

Reemplazar `{SKILL_NAME}` con el nombre del skill de la tabla inferior.

```
You are auditing the `{SKILL_NAME}` skill of the ai-engineering framework. Read the following files:

1. `.ai-engineering/skills/{SKILL_NAME}/SKILL.md`
2. `.ai-engineering/standards/framework/skills-schema.md`
3. `.ai-engineering/standards/framework/core.md` (sections: behavioral baselines, progressive disclosure)
4. `.ai-engineering/manifest.yml` (section: governance_surface.skills)

If the skill has additional resources, also read:
- `.ai-engineering/skills/{SKILL_NAME}/scripts/` (if exists)
- `.ai-engineering/skills/{SKILL_NAME}/references/` (if exists)
- `.ai-engineering/skills/{SKILL_NAME}/assets/` (if exists)

Perform these checks:

1. **Frontmatter compliance**: Verify all required fields (name, version, description, tags) are present. Name must be kebab-case and match directory name `{SKILL_NAME}`.
2. **Description quality**: Check that the description is a one-line "what + when" that serves as the primary AI trigger mechanism.
3. **Gating metadata**: If present, verify `requires.stacks`, `requires.bins`, `requires.anyBins`, `requires.env`, `requires.config`, `os`, `scope`, and `token_estimate` are valid.
4. **Body sections**: Verify presence and quality of all required sections: Purpose, Trigger, When NOT to Use, Procedure, Output Contract, Governance Notes, References.
5. **Procedure completeness**: Check that the procedure has numbered, actionable steps with clear inputs/outputs.
6. **Output contract**: Verify the skill defines a concrete output format (not vague).
7. **Token budget**: Verify body fits within ≤1,500 tokens as per skills-schema.md.
8. **Cross-references**: Check that all referenced files, skills, agents, and paths exist.
9. **Behavioral baselines**: Verify alignment with applicable baselines (escalation, validation, confidence, headless, holistic, exhaustiveness, parallel-first).
10. **Governance notes**: Verify security, quality, or governance constraints are documented where applicable.

Output using the Universal Output Template (Score 0-100, Verdict, Findings table, Strengths, Proposals).
```

### Tabla de 33 Skills

| # | `{SKILL_NAME}` | Domain | Owner Agent |
|---|-----------------|--------|-------------|
| 1 | `a11y` | Scan | scan |
| 2 | `api` | Build | build |
| 3 | `architecture` | Scan | scan |
| 4 | `build` | Build | build |
| 5 | `changelog` | Release | release |
| 6 | `cicd` | Build | build |
| 7 | `cleanup` | Planning | plan |
| 8 | `cli` | Build | build |
| 9 | `code-simplifier` | Build | build |
| 10 | `commit` | Release | release |
| 11 | `create` | Governance | plan |
| 12 | `db` | Build | build |
| 13 | `debug` | Build | build |
| 14 | `delete` | Governance | plan |
| 15 | `discover` | Planning | plan |
| 16 | `docs` | Write | write |
| 17 | `explain` | Planning | plan |
| 18 | `feature-gap` | Scan | scan |
| 19 | `governance` | Scan | scan |
| 20 | `infra` | Build | build |
| 21 | `migrate` | Build | build |
| 22 | `observe` | Observe | observe |
| 23 | `perf` | Scan | scan |
| 24 | `pr` | Release | release |
| 25 | `quality` | Scan | scan |
| 26 | `refactor` | Build | build |
| 27 | `release` | Release | release |
| 28 | `risk` | Governance | plan |
| 29 | `security` | Scan | scan |
| 30 | `spec` | Planning | plan |
| 31 | `standards` | Governance | plan |
| 32 | `test` | Build | build |
| 33 | `work-item` | Release | release |

---

## Sección 3: Standards (S1–S4)

### S1: Core Framework + Skills Schema

```
You are auditing the core framework standards and skills schema of ai-engineering. Read the following files:

1. `.ai-engineering/standards/framework/core.md`
2. `.ai-engineering/standards/framework/skills-schema.md`
3. `.ai-engineering/manifest.yml`
4. `.ai-engineering/context/product/framework-contract.md`

Perform these checks:

1. **Non-negotiables completeness**: Verify core.md covers all enforcement rules: mandatory local hooks, gitleaks, semgrep, dependency checks, protected branch blocking, remote skill restrictions, docs requirements.
2. **Progressive disclosure**: Verify the 3-level model (metadata → body → resources) is well-defined with token budgets (≤50, ≤1500, unlimited).
3. **Behavioral baselines**: Verify all 7 baselines are defined with actionable criteria: escalation ladder (max 3 attempts), post-change validation, confidence signaling, headless fallback, holistic analysis, exhaustiveness, parallel-first.
4. **Content integrity**: Verify 7 integrity categories are defined: file existence, mirror sync, counter accuracy, cross-reference integrity, instruction consistency, manifest coherence, skill frontmatter.
5. **Skills schema completeness**: Verify required frontmatter fields (name, version, description, tags), optional gating metadata, body sections, and token budgets are all well-defined.
6. **Agent schema completeness**: Verify required agent fields (name, version, scope, capabilities, inputs, outputs) and token budget (≤500) are defined.
7. **Consistency**: Check that core.md and skills-schema.md do not contradict each other or the manifest.
8. **Spec-first enforcement**: Verify criteria for requiring a spec (>3 files, new features, refactors, governance changes).
9. **Auto-remediation**: Verify the detect → install → configure → re-run flow is documented.
10. **Pipeline classification**: Verify all 4 pipeline types (full, standard, hotfix, trivial) have clear criteria.

Output using the Universal Output Template.
```

### S2: Quality + Security Standards

```
You are auditing the quality and security standards of ai-engineering. Read the following files:

1. `.ai-engineering/standards/framework/quality/core.md`
2. `.ai-engineering/standards/framework/quality/sonarlint.md`
3. `.ai-engineering/standards/framework/security/owasp-top10-2025.md`
4. `.ai-engineering/standards/framework/core.md` (sections: enforcement, non-negotiables)
5. `.ai-engineering/manifest.yml` (sections: enforcement, tooling)
6. `.ai-engineering/context/product/framework-contract.md` (section: 4. Security and Quality)

Perform these checks:

1. **Quality thresholds**: Verify coverage ≥90%, duplication ≤3%, cyclomatic complexity ≤10, cognitive complexity ≤15, zero blocker/critical, 100% gate pass are all defined.
2. **Security targets**: Verify zero medium/high/critical findings, zero leaks, zero dependency vulns are specified.
3. **OWASP alignment**: Check that OWASP Top 10 2025 categories are mapped to actionable checks.
4. **SonarLint rules**: Verify sonarlint.md provides concrete rule sets per language/stack.
5. **Tool chain**: Confirm all required tools are specified: ruff (lint/format), ty (types), pip-audit (deps), gitleaks (secrets), semgrep (SAST).
6. **Gate integration**: Verify quality and security checks are integrated into pre-commit and pre-push hooks.
7. **Cross-OS enforcement**: Check that security and quality gates work on Windows, macOS, and Linux.
8. **Risk acceptance**: Verify the decision-store.json workflow for security finding risk acceptance is documented.
9. **Consistency**: Ensure quality/core.md, security/owasp-top10-2025.md, and framework-contract.md section 4 do not contradict.
10. **Remediation guidance**: Check that each quality/security rule includes fix guidance or references.

Output using the Universal Output Template.
```

### S3: Stack Standards (14 Stacks)

```
You are auditing all 14 stack standards of ai-engineering. Read the following files:

1. `.ai-engineering/standards/framework/stacks/astro.md`
2. `.ai-engineering/standards/framework/stacks/azure.md`
3. `.ai-engineering/standards/framework/stacks/bash-powershell.md`
4. `.ai-engineering/standards/framework/stacks/database.md`
5. `.ai-engineering/standards/framework/stacks/dotnet.md`
6. `.ai-engineering/standards/framework/stacks/infrastructure.md`
7. `.ai-engineering/standards/framework/stacks/nestjs.md`
8. `.ai-engineering/standards/framework/stacks/nextjs.md`
9. `.ai-engineering/standards/framework/stacks/node.md`
10. `.ai-engineering/standards/framework/stacks/python.md`
11. `.ai-engineering/standards/framework/stacks/react-native.md`
12. `.ai-engineering/standards/framework/stacks/react.md`
13. `.ai-engineering/standards/framework/stacks/rust.md`
14. `.ai-engineering/standards/framework/stacks/typescript.md`
15. `.ai-engineering/standards/framework/core.md` (for cross-reference)
16. `.ai-engineering/manifest.yml` (section: standards)

Perform these checks for EACH stack:

1. **Structure consistency**: Verify all 14 stacks follow the same document structure/sections.
2. **Tool specification**: Each stack must specify its linter, formatter, type checker, test runner, and package manager.
3. **Quality thresholds**: Verify stack-specific quality targets align with or exceed framework minimums (coverage 90%, cyclomatic ≤10, etc.).
4. **Security rules**: Check for stack-specific security guidance (e.g., SQL injection for database, XSS for react/nextjs).
5. **Naming conventions**: Verify each stack defines naming conventions for files, functions, classes, variables.
6. **Project structure**: Check that each stack defines expected project layout.
7. **Dependency management**: Verify dependency management and vulnerability scanning guidance.
8. **Cross-stack consistency**: Ensure common patterns (error handling, logging, testing) are consistent across stacks.
9. **Version currency**: Check that referenced tool/framework versions are reasonably current (not outdated by >1 major version).
10. **Completeness**: Compare the 14 stacks against the manifest to ensure no stack is missing.

Output using the Universal Output Template. Include a per-stack mini-scorecard in the Findings section.
```

### S4: CI/CD + Team Standards

```
You are auditing the CI/CD and team standards of ai-engineering. Read the following files:

1. `.ai-engineering/standards/framework/cicd/core.md`
2. `.ai-engineering/manifest.yml` (sections: pipelines, enforcement, commands)
3. `.ai-engineering/standards/framework/core.md` (sections: enforcement, non-negotiables)
4. `.ai-engineering/context/product/framework-contract.md` (sections: 1. Core Mandates, 5. Distribution Model)

Also check if these exist and read them:
- `.ai-engineering/standards/team/` (any team-managed standards)

Perform these checks:

1. **Pipeline definition**: Verify CI/CD pipelines are defined for all 4 types (full, standard, hotfix, trivial).
2. **Gate stages**: Check that pre-commit, pre-push, and CI gates are properly sequenced with no gaps.
3. **Provider support**: Verify support for GitHub Actions and Azure DevOps pipelines.
4. **Workflow generation**: Confirm the `ai-eng cicd regenerate` command produces valid workflow files.
5. **Hook enforcement**: Verify local hooks (pre-commit, pre-push) are mandatory and non-bypassable.
6. **Team standards boundary**: Check that team-managed standards don't conflict with framework-managed standards.
7. **Auto-remediation**: Verify CI/CD failures include remediation guidance.
8. **Cross-OS**: Check pipeline definitions work across Windows, macOS, Linux runners.
9. **SemVer release flow**: Verify the release pipeline follows SemVer and the distribution model.
10. **Command integration**: Confirm CLI commands (`ai-eng gate`, `ai-eng cicd regenerate`) align with the pipeline definitions.

Output using the Universal Output Template.
```

---

## Sección 4: Cross-Cutting (X1–X18)

### X1: Content Integrity

```
You are auditing the content integrity enforcement of ai-engineering. Read:

1. `.ai-engineering/standards/framework/core.md` (section: content integrity enforcement)
2. `.ai-engineering/manifest.yml`
3. `src/ai_engineering/validator/service.py` (if exists)
4. `.ai-engineering/state/` (all state files)

Perform these checks:

1. **7 categories defined**: File existence, mirror sync, counter accuracy, cross-reference integrity, instruction file consistency, manifest coherence, skill frontmatter.
2. **Validator implementation**: Check if `ai-eng validate` is implemented and covers all 7 categories.
3. **State file integrity**: Verify all system-managed files exist: install-manifest.json, ownership-map.json, sources.lock.json, decision-store.json, audit-log.ndjson, session-checkpoint.json.
4. **Manifest coherence**: Verify manifest.yml counters (agents: 6, skills: 33) match actual file counts.
5. **Mirror sync**: Check for any defined mirrors and verify sync status.
6. **Instruction consistency**: Verify CLAUDE.md, manifest.yml, and framework-contract.md do not contradict each other.
7. **Automated enforcement**: Check if integrity validation runs automatically (hooks, CI, or scheduled).
8. **Error reporting**: Verify integrity failures produce actionable error messages.

Output using the Universal Output Template.
```

### X2: Cross-Reference Integrity

```
You are auditing the cross-reference integrity of ai-engineering. Read:

1. `.ai-engineering/manifest.yml`
2. `.ai-engineering/standards/framework/core.md`
3. `.ai-engineering/context/product/framework-contract.md`
4. `CLAUDE.md`
5. A sample of 5 agent files (plan.md, build.md, scan.md, release.md, observe.md)
6. A sample of 5 skill files (commit, pr, security, quality, discover)

Perform these checks:

1. **Internal links**: Verify all internal file references (relative paths) resolve to existing files.
2. **Agent-skill mapping**: Verify every skill listed in agents has a corresponding SKILL.md.
3. **Manifest-to-files**: Verify every agent/skill listed in manifest.yml has a corresponding file.
4. **Files-to-manifest**: Verify every agent/skill file on disk is listed in the manifest.
5. **CLAUDE.md alignment**: Verify CLAUDE.md accurately reflects the current state of agents, skills, and commands.
6. **Orphaned references**: Identify any references to files, skills, or agents that no longer exist.
7. **Circular references**: Check for circular dependencies between skills or agents.
8. **Version consistency**: Verify version numbers across manifest, agents, and skills are consistent.

Output using the Universal Output Template.
```

### X3: Ownership Model

```
You are auditing the ownership model of ai-engineering. Read:

1. `.ai-engineering/manifest.yml` (section: ownership)
2. `.ai-engineering/context/product/framework-contract.md` (section: 3. Ownership Model)
3. `.ai-engineering/standards/framework/core.md`

Perform these checks:

1. **4 boundaries defined**: framework-managed, team-managed, project-managed, system-managed with exact paths.
2. **Framework-managed**: Verify `standards/framework/**`, `skills/**`, `agents/**` are correctly scoped.
3. **Team-managed**: Verify `standards/team/**` boundary and update rules.
4. **Project-managed**: Verify `context/**` boundary.
5. **System-managed**: Verify all state files (install-manifest.json, ownership-map.json, sources.lock.json, decision-store.json, audit-log.ndjson, session-checkpoint.json) are listed.
6. **Conflict resolution**: Check that ownership conflicts have a defined resolution order.
7. **Update rules**: Verify each boundary has clear rules for who/what can modify files.
8. **Enforcement**: Check if ownership boundaries are enforced (hooks, validation, or policy).

Output using the Universal Output Template.
```

### X4: Security Posture

```
You are auditing the end-to-end security posture of ai-engineering. Read:

1. `.ai-engineering/standards/framework/security/owasp-top10-2025.md`
2. `.ai-engineering/standards/framework/quality/core.md` (security sections)
3. `.ai-engineering/standards/framework/core.md` (sections: enforcement, non-negotiables)
4. `.ai-engineering/manifest.yml` (sections: enforcement, tooling, risk_acceptance)
5. `.ai-engineering/context/product/framework-contract.md` (section: 4. Security and Quality)
6. `.ai-engineering/state/decision-store.json`

Perform these checks:

1. **Secret scanning**: Verify gitleaks is configured for pre-commit with correct flags (`gitleaks protect --staged`).
2. **SAST**: Verify semgrep integration and rule sets.
3. **Dependency scanning**: Verify pip-audit (Python), npm audit or equivalent for JS stacks.
4. **OWASP coverage**: Map each OWASP Top 10 2025 category to a concrete framework check.
5. **Risk acceptance workflow**: Verify decision-store.json structure supports security risk acceptance with expiry.
6. **AI permissions**: Verify the allow/guardrailed/restricted permission model per framework-contract.md.
7. **Hook integrity**: Verify hook hash verification prevents tampering.
8. **Zero tolerance**: Confirm zero medium/high/critical policy is enforced, not just documented.
9. **Cross-OS**: Verify security tools work on Windows, macOS, Linux.
10. **Telemetry privacy**: Verify strict opt-in telemetry mode per manifest.yml.

Output using the Universal Output Template.
```

### X5: Quality Gates

```
You are auditing the quality gate system of ai-engineering. Read:

1. `.ai-engineering/standards/framework/quality/core.md`
2. `.ai-engineering/standards/framework/core.md` (sections: enforcement, non-negotiables)
3. `.ai-engineering/manifest.yml` (sections: enforcement, tooling)
4. `src/ai_engineering/cli_commands/gate.py` (if exists)
5. `scripts/hooks/` (all hook scripts)

Perform these checks:

1. **Gate stages**: Verify pre-commit and pre-push gates are defined with specific checks per stage.
2. **Threshold enforcement**: Confirm coverage ≥90%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15, zero blocker/critical.
3. **Tool chain**: Verify ruff (lint+format), ty (types), pytest (tests), pip-audit (deps) integration.
4. **Gate CLI**: Verify `ai-eng gate pre-commit|pre-push|all` covers all checks.
5. **Failure handling**: Confirm gate failures block operations and provide actionable remediation.
6. **No bypass**: Verify `--no-verify` is blocked at all levels (hooks, CLI, agent behavior).
7. **Hook installation**: Verify `scripts/install.sh` correctly installs hooks to `.git/hooks/`.
8. **100% pass rate**: Verify the "100% gate pass" requirement is enforced, not aspirational.
9. **Stack-specific gates**: Check if different stacks have additional quality gates.
10. **Reporting**: Verify gate results are logged to the audit trail.

Output using the Universal Output Template.
```

### X6: Agentic Model

```
You are auditing the agentic execution model of ai-engineering. Read:

1. `.ai-engineering/context/product/framework-contract.md` (section: 2. Agentic Model)
2. `.ai-engineering/manifest.yml` (sections: governance_surface, agentic)
3. `.ai-engineering/standards/framework/core.md` (sections: behavioral baselines)
4. `.ai-engineering/agents/plan.md` (orchestration agent)

Perform these checks:

1. **Session contract**: Verify session start protocol is defined (read spec, decision store, checkpoint, cleanup, verify tooling).
2. **Parallel execution**: Verify governed parallel execution is defined with coordination rules.
3. **Phase gates**: Check that lifecycle transitions require explicit gate passage.
4. **Agent coordination**: Verify how agents communicate and hand off work.
5. **Context threading**: Check how context is maintained across agent transitions.
6. **Capability-task matching**: Verify the orchestrator selects agents based on capability tokens.
7. **Task tracking**: Confirm task progress is tracked and observable.
8. **6 agents complete**: Verify all 6 agents (plan, build, scan, release, write, observe) are fully integrated.
9. **Scope enforcement**: Verify read-only agents cannot write, docs-only agents cannot modify code, etc.
10. **Error recovery**: Check agent failure handling and escalation paths.

Output using the Universal Output Template.
```

### X7: Pipeline Strategy

```
You are auditing the pipeline classification and execution strategy. Read:

1. `.ai-engineering/manifest.yml` (section: pipelines)
2. `.ai-engineering/context/product/framework-contract.md`
3. `.ai-engineering/standards/framework/core.md`
4. `.ai-engineering/agents/plan.md`
5. `CLAUDE.md` (section: Pipeline Strategy)

Perform these checks:

1. **4 types defined**: full, standard, hotfix, trivial with clear classification criteria.
2. **Auto-classification**: Verify `git diff --stat` + change type drives automatic selection.
3. **User override**: Verify `/ai:plan --pipeline=<type>` override mechanism.
4. **Step sequences**: Verify each pipeline type has a complete, ordered step sequence.
5. **Gate integration**: Check that each pipeline type enforces appropriate gates.
6. **File count thresholds**: Verify >3 files → standard/full, <3 files → hotfix, 1 line → trivial.
7. **Consistency**: Ensure CLAUDE.md, manifest.yml, and plan.md agree on pipeline definitions.
8. **Edge cases**: Check handling of mixed change types (e.g., feature + fix in same PR).
9. **Metrics**: Verify pipeline execution is tracked for DORA metrics.
10. **Fallback**: Check what happens when auto-classification is ambiguous.

Output using the Universal Output Template.
```

### X8: Observability

```
You are auditing the observability system of ai-engineering. Read:

1. `.ai-engineering/manifest.yml` (section: observability)
2. `.ai-engineering/agents/observe.md`
3. `.ai-engineering/skills/observe/SKILL.md`
4. `.ai-engineering/standards/framework/core.md`
5. `.ai-engineering/state/audit-log.ndjson` (first 20 lines for format)
6. `src/ai_engineering/cli_commands/signals_cmd.py` (if exists)

Perform these checks:

1. **Event store**: Verify audit-log.ndjson format, schema, and append-only semantics.
2. **5 modes**: Verify engineer, team, ai, dora, health dashboards are defined.
3. **4 audiences**: Verify audience tiers are mapped to specific data views.
4. **DORA metrics**: Verify deployment frequency, lead time, change failure rate, MTTR collection.
5. **Health scoring**: Check methodology for computing health scores.
6. **Signal emission**: Verify `ai-eng signals emit|query` works for event capture and retrieval.
7. **CLI integration**: Verify `ai-eng observe [mode]` produces correct dashboards.
8. **Data retention**: Check if there's a retention policy for audit-log.ndjson.
9. **Privacy**: Verify no PII or secrets are logged in the event store.
10. **Metrics collection**: Verify `ai-eng metrics collect` aggregates signals into dashboard data.

Output using the Universal Output Template.
```

### X9: Decision Store

```
You are auditing the decision store system of ai-engineering. Read:

1. `.ai-engineering/state/decision-store.json`
2. `.ai-engineering/manifest.yml` (section: risk_acceptance)
3. `.ai-engineering/standards/framework/core.md`
4. `.ai-engineering/context/product/framework-contract.md` (section: 4. Security and Quality)
5. `src/ai_engineering/cli_commands/decisions_cmd.py` (if exists)

Perform these checks:

1. **Schema**: Verify decision-store.json has a well-defined schema (id, type, description, rationale, date, expiry, status).
2. **Risk acceptance**: Verify security findings can be accepted with mandatory rationale and expiry date.
3. **Expiry enforcement**: Check if `ai-eng decision expire-check` actually flags expired decisions.
4. **CLI integration**: Verify `ai-eng decision list|expire-check` covers basic management.
5. **Audit trail**: Verify decisions are logged in the audit-log.ndjson.
6. **No silent dismissal**: Confirm security findings cannot be dismissed without a decision record.
7. **CLAUDE.md alignment**: Verify CLAUDE.md's prohibition on dismissing findings without decision-store is enforced.
8. **Read-across**: Check if decisions from one context are visible/applicable to related contexts.

Output using the Universal Output Template.
```

### X10: Installation & Setup

```
You are auditing the installation and setup system of ai-engineering. Read:

1. `.ai-engineering/manifest.yml` (sections: tooling, providers)
2. `scripts/install.sh` (if exists)
3. `src/ai_engineering/cli_commands/` (relevant setup commands)
4. `.ai-engineering/standards/framework/core.md` (section: auto-remediation)
5. `.ai-engineering/state/install-manifest.json` (if exists)

Perform these checks:

1. **Provider-aware install**: Verify installation detects VCS provider (GitHub, Azure DevOps).
2. **Tool installation**: Verify ruff, ty, gitleaks, semgrep, pip-audit are installed or guided.
3. **Hook installation**: Verify git hooks are installed to `.git/hooks/` with hash verification.
4. **Cross-OS**: Verify installation works on Windows, macOS, Linux.
5. **Idempotency**: Verify running install multiple times is safe.
6. **Doctor command**: Verify `ai-eng doctor --fix-tools --fix-hooks` diagnoses and fixes issues.
7. **Install manifest**: Check if install-manifest.json tracks installed components and versions.
8. **Error messages**: Verify installation failures produce actionable guidance.
9. **Stack detection**: Check if `ai-eng stack list` correctly detects project stacks.
10. **IDE support**: Verify `ai-eng ide add|remove|list` configures IDE-specific settings.

Output using the Universal Output Template.
```

### X11: Command Surface

```
You are auditing the CLI command surface of ai-engineering. Read:

1. `CLAUDE.md` (section: Python CLI)
2. `.ai-engineering/manifest.yml` (section: commands)
3. `src/ai_engineering/cli_commands/` (all command files)
4. `.ai-engineering/context/product/framework-contract.md`

Perform these checks:

1. **Command inventory**: Verify all commands listed in CLAUDE.md exist as implemented code.
2. **Command contract**: Verify `/ai:commit` and `/ai:pr` contracts match implementation.
3. **Help text**: Check that each CLI command has clear help/usage text.
4. **Error handling**: Verify commands produce actionable error messages on failure.
5. **Slash commands**: Verify `.claude/commands/ai/` slash commands map to all 33 skills + 6 agents.
6. **Deterministic vs AI**: Verify CLI commands (ai-eng) are deterministic (no AI tokens), while slash commands use AI.
7. **Cross-OS**: Check command compatibility with Windows (PowerShell), macOS, Linux.
8. **Consistency**: Verify CLAUDE.md, manifest.yml, and actual implementations are in sync.
9. **Exit codes**: Verify commands return proper exit codes for scripting/CI use.
10. **Composability**: Check if commands can be chained or piped effectively.

Output using the Universal Output Template.
```

### X12: Context Optimization

```
You are auditing the context optimization strategy of ai-engineering. Read:

1. `.ai-engineering/manifest.yml` (section: context_optimization)
2. `.ai-engineering/standards/framework/core.md` (section: progressive disclosure)
3. `.ai-engineering/standards/framework/skills-schema.md` (section: token budgets)
4. `.ai-engineering/context/` (directory structure)
5. `CLAUDE.md` (section: Progressive Disclosure)

Perform these checks:

1. **3-level model**: Verify metadata (≤50 tok) → body (≤1,500 tok) → resources (unlimited) is enforced.
2. **Session start budget**: Verify ~500 tokens for session initialization.
3. **Single skill budget**: Verify ~2,050 tokens per skill invocation.
4. **Agent + skills budget**: Verify ~3,200 tokens for agent + 2 skills.
5. **Audit budget**: Verify ~10,500 tokens for 7-dimension platform audit.
6. **Lazy loading**: Check that context files are loaded on-demand, not eagerly.
7. **Active spec pattern**: Verify `_active.md` → `spec.md` → `tasks.md` → `decision-store.json` loading chain.
8. **Token savings**: Verify the ~38% savings claim from deterministic CLI execution.
9. **Consistency**: Ensure all budget figures match across CLAUDE.md, manifest.yml, core.md, and skills-schema.md.
10. **Measurement**: Check if actual token usage is measured and compared against budgets.

Output using the Universal Output Template.
```

### X13: Token Efficiency

```
You are auditing the token efficiency of the ai-engineering framework. Read:

1. `.ai-engineering/manifest.yml` (section: context_optimization)
2. `.ai-engineering/standards/framework/skills-schema.md` (token budgets)
3. `.ai-engineering/standards/framework/core.md` (progressive disclosure)
4. A sample of 5 skill files: discover, commit, security, build, observe

For each sampled skill, estimate actual token count and compare to budget.

Perform these checks:

1. **Skill body compliance**: Verify sampled skills fit within ≤1,500 token body budget.
2. **Agent persona compliance**: Verify agent personas fit within ≤500 token budget.
3. **Metadata brevity**: Verify frontmatter metadata is ≤50 tokens per skill.
4. **Redundancy**: Identify repeated content across skills that could be factored out.
5. **Verbosity**: Flag overly verbose sections that could be compressed without losing meaning.
6. **Progressive loading**: Verify resources are truly deferred and not embedded in body.
7. **Deterministic offloading**: Verify deterministic logic is in CLI (ai-eng) not in AI prompts.
8. **Context window impact**: Estimate total tokens for a typical full-pipeline session.

Output using the Universal Output Template.
```

### X14: Multi-IDE Support

```
You are auditing multi-IDE support in ai-engineering. Read:

1. `.ai-engineering/manifest.yml` (section: providers)
2. `.ai-engineering/context/product/framework-contract.md` (section: 1.1 Core Mandates)
3. `.ai-engineering/standards/framework/core.md`
4. `.claude/` directory structure (Claude Code configuration)

Perform these checks:

1. **4-IDE support**: Verify framework supports Claude Code, GitHub Copilot, Codex, and Gemini.
2. **Claude Code integration**: Verify `.claude/commands/ai/` slash commands are properly configured.
3. **Copilot integration**: Check for Copilot-specific configuration or instructions.
4. **Codex compatibility**: Verify prompts and skills work with Codex.
5. **Gemini compatibility**: Verify prompts and skills work with Gemini.
6. **IDE-agnostic skills**: Verify SKILL.md files don't contain IDE-specific logic in their core procedures.
7. **IDE CLI**: Verify `ai-eng ide add|remove|list` manages IDE configurations.
8. **Common format**: Check that the output contract works across all IDEs.

Output using the Universal Output Template.
```

### X15: Cross-OS Compatibility

```
You are auditing cross-OS compatibility of ai-engineering. Read:

1. `.ai-engineering/manifest.yml`
2. `.ai-engineering/standards/framework/core.md`
3. `scripts/` (all scripts)
4. `src/ai_engineering/` (CLI implementation)
5. `.ai-engineering/standards/framework/stacks/bash-powershell.md`

Perform these checks:

1. **3-OS support**: Verify Windows, macOS, Linux support is claimed and tested.
2. **Shell scripts**: Check scripts for bash-isms that won't work on Windows.
3. **Path handling**: Verify paths use OS-agnostic separators or cross-platform libraries.
4. **Tool availability**: Verify tool installation instructions cover all 3 OS.
5. **Hook scripts**: Verify git hooks work on Windows (Git Bash, PowerShell).
6. **CI runners**: Verify CI/CD workflows include multi-OS matrix.
7. **Python CLI**: Verify `ai-eng` CLI uses cross-platform Python patterns (pathlib, os.path).
8. **Line endings**: Check for `.gitattributes` handling LF/CRLF.

Output using the Universal Output Template.
```

### X16: VCS Provider Support

```
You are auditing VCS provider support in ai-engineering. Read:

1. `.ai-engineering/manifest.yml` (section: providers.vcs)
2. `src/ai_engineering/cli_commands/vcs.py` (if exists)
3. `.ai-engineering/standards/framework/core.md`
4. `.ai-engineering/context/product/framework-contract.md`

Perform these checks:

1. **Provider detection**: Verify automatic detection of GitHub vs Azure DevOps.
2. **Primary provider**: Verify `ai-eng vcs set-primary` sets the active VCS provider.
3. **GitHub support**: Verify full GitHub support (Actions, Issues, Projects, PRs).
4. **Azure DevOps support**: Verify Azure DevOps support (Pipelines, Boards, Repos, PRs).
5. **Provider abstraction**: Check if VCS operations are abstracted (not hardcoded to one provider).
6. **Hook compatibility**: Verify git hooks work identically across providers.
7. **CI/CD generation**: Verify `ai-eng cicd regenerate` produces provider-specific workflows.
8. **Status command**: Verify `ai-eng vcs status` shows current provider configuration.

Output using the Universal Output Template.
```

### X17: Remote Skills

```
You are auditing the remote skills system of ai-engineering. Read:

1. `.ai-engineering/manifest.yml` (section: remote_skills)
2. `.ai-engineering/standards/framework/core.md` (section: remote skill restrictions)
3. `.ai-engineering/context/product/framework-contract.md` (section: 5. Distribution Model)
4. `.ai-engineering/state/sources.lock.json` (if exists)

Perform these checks:

1. **Content-only**: Verify remote skills are content-only with no remote code execution.
2. **Source lock**: Verify sources.lock.json pins remote skill versions.
3. **Integrity verification**: Check if remote skills are hash-verified on fetch.
4. **Update mechanism**: Verify `ai-eng skill sync` fetches and validates remote skills.
5. **Skill management**: Verify `ai-eng skill add|remove|list|status` manages the skill catalog.
6. **Namespace isolation**: Check that remote skills don't conflict with local skills.
7. **Fallback behavior**: Verify what happens when a remote skill is unavailable.
8. **Security**: Verify remote skills cannot bypass local security checks.

Output using the Universal Output Template.
```

### X18: Full Framework Rollup

```
You are performing a full framework rollup audit of ai-engineering. This is the final audit that synthesizes all previous findings.

Read the following summary files:
1. `.ai-engineering/manifest.yml`
2. `.ai-engineering/context/product/framework-contract.md`
3. `.ai-engineering/standards/framework/core.md`
4. `CLAUDE.md`

You should have access to previous audit results (A1-A6, S1-S4, X1-X17, and all 33 skill audits). If not, read a representative sample of agents and skills.

Synthesize across ALL previous audits:

1. **Core Mandate compliance**: Rate framework alignment with the 8 core mandates (simple, efficient, practical, robust, secure, governed, cross-IDE, cross-OS).
2. **Agent coverage**: Summarize agent audit scores (A1-A6) and identify the weakest agent.
3. **Skill health**: Summarize skill audit scores and identify patterns (lowest-scoring skills, common issues).
4. **Standards completeness**: Summarize S1-S4 findings and identify gaps.
5. **Security posture**: Roll up X4 (security), S2 (quality+security), and skill-level security findings.
6. **Quality gates**: Roll up X5 (gates), S2 (quality), and skill-level quality findings.
7. **Cross-cutting risks**: Identify systemic issues that appear across multiple audits.
8. **Top 10 priorities**: Rank the top 10 findings by severity × impact across all audits.
9. **Maturity assessment**: Rate framework maturity on a 5-level scale (Initial → Repeatable → Defined → Managed → Optimized).
10. **Roadmap proposals**: Propose top 5 improvements with effort/impact analysis.

Output format (extended):

## Full Framework Rollup

**Overall Score**: 0-100
**Overall Verdict**: PASS/WARN/FAIL
**Maturity Level**: 1-5 (Initial/Repeatable/Defined/Managed/Optimized)

### Component Scores
| Component | Score | Verdict |
|-----------|-------|---------|
| A1: plan | ... | ... |
| ... | ... | ... |

### Top 10 Priorities
| # | Severity | Component | Finding | Recommendation |
|---|----------|-----------|---------|----------------|

### Systemic Issues
- ...

### Maturity Assessment
- ...

### Roadmap (Top 5)
| # | Proposal | Effort | Impact | Dependencies |
|---|----------|--------|--------|--------------|
```

---

## Orden de Ejecución Recomendado

| Fase | Prompts | Sesiones | Objetivo |
|------|---------|----------|----------|
| 1. Foundation | S1, X3 | 1 | Validar que los cimientos (core standards, ownership) son sólidos |
| 2. Governance | X1, X2 | 1 | Verificar integridad y cross-references del framework |
| 3. Agents | A1–A6 | 2 | Auditar los 6 agentes (3 por sesión) |
| 4. Security + Quality | S2, X4, X5 | 1 | Verificar postura de seguridad y gates de calidad |
| 5. Skills (batches) | Template ×33 | 6 | Auditar los 33 skills en batches de 5-6 |
| 6. Standards | S3, S4 | 1 | Auditar stacks (14) y CI/CD + team standards |
| 7. Cross-cutting | X6–X17 | 4 | Auditar las 12 dimensiones transversales (3 por sesión) |
| 8. Rollup | X18 | 1 | Síntesis final con priorización de hallazgos |
| **Total** | **62** | **~17** | **Auditoría completa del framework** |

### Atajo MVP (70% del valor en 6 sesiones)

| Fase | Prompts | Sesiones |
|------|---------|----------|
| 1. Foundation | S1, X3 | 1 |
| 2. Governance | X1, X2 | 1 |
| 3. Agents | A1–A6 | 2 |
| 4. Security + Quality | S2, X4, X5 | 1 |
| 8. Rollup | X18 | 1 |
| **Total MVP** | **14** | **6** |

### Skill Batches (Fase 5)

| Batch | Skills |
|-------|--------|
| 5a | discover, spec, cleanup, explain, build, test |
| 5b | debug, refactor, code-simplifier, api, cli, db |
| 5c | infra, cicd, migrate, security, quality, governance |
| 5d | architecture, perf, a11y, feature-gap, commit, pr |
| 5e | release, changelog, work-item, docs, observe, risk |
| 5f | standards, create, delete |

### Cross-cutting Batches (Fase 7)

| Batch | Prompts |
|-------|---------|
| 7a | X6 (agentic model), X7 (pipeline), X8 (observability) |
| 7b | X9 (decisions), X10 (install), X11 (commands) |
| 7c | X12 (context), X13 (tokens), X14 (multi-IDE) |
| 7d | X15 (cross-OS), X16 (VCS), X17 (remote skills) |
