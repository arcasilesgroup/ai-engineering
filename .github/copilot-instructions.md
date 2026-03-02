# GitHub Copilot Instructions

Project instructions are canonical in `.ai-engineering/`.

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks.
2. **Read decision store** — `.ai-engineering/state/decision-store.json`.
3. **Run cleanup** — sync repo (status, git pull, prune, branch cleanup).
4. **Verify tooling** — ruff, gitleaks, pytest, ty.

## Skills (44)

Path: `.ai-engineering/skills/<category>/<name>/SKILL.md`

| Category | Count | Skills |
|----------|-------|--------|
| workflows | 4 | commit, pr, cleanup, self-improve |
| dev | 16 | debug, refactor, code-review, data-modeling, test-runner, test-strategy, migration, deps-update, cicd-generate, cli-ux, multi-agent, api-design, infrastructure, database-ops, sonar-gate, discovery-interrogation |
| review | 5 | architecture, performance, security, specialized-security, accessibility |
| docs | 5 | changelog, explain, writer, simplify, prompt-design |
| govern | 8 | integrity-check, contract-compliance, ownership-audit, adaptive-standards, create-spec, agent-lifecycle, skill-lifecycle, risk-lifecycle |
| quality | 6 | audit-code, docs-audit, install-check, release-gate, test-gap-analysis, sbom |

## Agents (19)

Path: `.ai-engineering/agents/<name>.md`

| Agent | Purpose |
|-------|---------|
| principal-engineer | Code review |
| debugger | Bug diagnosis |
| architect | Architecture analysis |
| quality-auditor | Quality gate enforcement |
| security-reviewer | Security assessment |
| orchestrator | Multi-phase execution |
| navigator | Strategic spec analysis |
| devops-engineer | CI/CD automation |
| test-master | Testing specialist |
| docs-writer | Documentation |
| governance-steward | Governance lifecycle |
| pr-reviewer | Headless CI review |
| code-simplifier | Complexity reduction |
| platform-auditor | Full-spectrum audit |
| verify-app | E2E verification |
| infrastructure-engineer | IaC provisioning |
| database-engineer | Database engineering |
| frontend-specialist | Frontend/UI architecture |
| api-designer | Contract-first API design |

## Command Contract

- `/commit` → stage + commit + push
- `/commit --only` → stage + commit
- `/pr` → stage + commit + push + PR + auto-complete (`--auto --squash --delete-branch`)
- `/pr --only` → create PR; warn if unpushed, propose auto-push
- `/acho` → stage + commit + push
- `/acho pr` → stage + commit + push + PR + auto-complete

## Quality Contract

Coverage 90%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15, zero blocker/critical, 100% gate pass.

## Security Contract

Zero medium/high/critical findings, zero leaks, zero dependency vulns, hook hash verification, cross-OS enforcement.
