---
spec: "021"
approach: "mixed"
---

# Plan — Governance + CI/CD Evolution

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `context/specs/021-governance-cicd-evolution/spec.md` | Spec WHAT document |
| `context/specs/021-governance-cicd-evolution/plan.md` | Spec HOW document |
| `context/specs/021-governance-cicd-evolution/tasks.md` | Spec DO document |
| `agents/orchestrator.md` | Session orchestrator persona |
| `agents/navigator.md` | Strategic next-spec analysis persona |
| `agents/devops-engineer.md` | CI/CD, deps, migration persona |
| `agents/docs-writer.md` | Docs generation/simplification persona |
| `agents/governance-steward.md` | Governance lifecycle persona |
| `agents/pr-reviewer.md` | Headless CI PR review persona |
| `skills/workflows/self-improve/SKILL.md` | Analyze → plan → execute → learn workflow |
| `skills/dev/data-modeling/SKILL.md` | Data modeling procedure |
| `skills/review/data-security/SKILL.md` | Data security review procedure |
| `skills/docs/simplify/SKILL.md` | Governance docs simplification procedure |
| `skills/govern/adaptive-standards` | Adaptive standards review procedure |
| `src/ai_engineering/installer/tools.py` | OS-aware tool install orchestration |
| `src/ai_engineering/installer/auth.py` | VCS auth checks and guidance |
| `src/ai_engineering/installer/cicd.py` | Stack-aware CI/CD generation logic |
| `src/ai_engineering/installer/branch_policy.py` | Policy apply and manual-guide fallback |
| `src/ai_engineering/cli_commands/review.py` | `ai-eng review pr` command group |
| `src/ai_engineering/cli_commands/cicd.py` | `ai-eng cicd regenerate` command group |
| `src/ai_engineering/templates/pipeline/github/*` | GitHub CI/PR review/gate templates |
| `src/ai_engineering/templates/pipeline/azure/*` | Azure DevOps CI/PR review/gate templates |
| `src/ai_engineering/templates/project/guides/branch-policy-*.md` | Manual setup guides for fallback mode |

### Modified Files

| File | Change |
|------|--------|
| `agents/architect.md` | Absorb mapper phase, add data-modeling references |
| `agents/security-reviewer.md` | Add data-security scope |
| `agents/quality-auditor.md` | Add explicit test-gap usage |
| `agents/platform-auditor.md` | Align orchestration with new agent set |
| `codebase-mapper` agent | Remove file and references |
| `skills/dev/cicd-generate/SKILL.md` | Add AI PR review step and stack-aware generation details |
| `skills/quality/audit-code/SKILL.md` | Merge audit-report output template |
| `skills/quality/install-check/SKILL.md` | Include platform detect + doctor readiness pattern |
| `skills/**/references/*` | Add domain-specific pattern references |
| `manifest.yml` | Agent/skill registrations and counters |
| `context/product/product-contract.md` | Active spec pointer update |
| `context/specs/_active.md` | Activate spec-021 |
| `src/ai_engineering/installer/service.py` | Expand install phases |
| `src/ai_engineering/detector/readiness.py` | Add stack-aware system/tool/auth checks |
| `src/ai_engineering/doctor/service.py` | Add CI/CD + branch-policy readiness diagnostics |
| `src/ai_engineering/pipeline/injector.py` | Move from snippet-only to workflow generation support |
| `src/ai_engineering/pipeline/compliance.py` | Add AI PR review and required gate checks |
| `src/ai_engineering/vcs/protocol.py` | Extend provider contract (policy/auth/review methods) |
| `src/ai_engineering/vcs/github.py` | Branch protection + PR review API support |
| `src/ai_engineering/vcs/azure_devops.py` | Policy/build validation + PR review support |
| `src/ai_engineering/vcs/factory.py` | API fallback selection support |
| `src/ai_engineering/state/models.py` | InstallManifest additions (auth, policies, cicd state) |
| `src/ai_engineering/cli_factory.py` | Register new `review` command group |
| `src/ai_engineering/cli_factory.py` | Register new `cicd` command group with `regenerate` subcommand |
| `.claude/commands/agent/*.md` | Add wrappers for new agents and remove mapper |
| `.github/agents/*.md` | Add wrappers for new agents and remove mapper |
| `.github/prompts/*.prompt.md` | Add new skills, remove deprecated ones |
| `AGENTS.md`, `CLAUDE.md`, `codex.md`, `.github/copilot-instructions.md` | Agent/skill inventory updates |

### Mirror Copies

| Canonical | Template Mirror |
|-----------|----------------|
| `.ai-engineering/agents/**` | `src/ai_engineering/templates/.ai-engineering/agents/**` |
| `.ai-engineering/skills/**` | `src/ai_engineering/templates/.ai-engineering/skills/**` |
| `.ai-engineering/manifest.yml` | `src/ai_engineering/templates/.ai-engineering/manifest.yml` |
| `.claude/commands/**` | `src/ai_engineering/templates/project/.claude/commands/**` |
| `.github/agents/**` | `src/ai_engineering/templates/project/agents/**` |
| `.github/prompts/**` | `src/ai_engineering/templates/project/prompts/**` |
| `.github/copilot-instructions.md` | `src/ai_engineering/templates/project/copilot-instructions.md` |

## File Structure

```text
context/specs/021-governance-cicd-evolution/
  spec.md
  plan.md
  tasks.md

agents/
  orchestrator.md
  navigator.md
  devops-engineer.md
  docs-writer.md
  governance-steward.md
  pr-reviewer.md
  architect.md (updated)
  security-reviewer.md (updated)
  quality-auditor.md (updated)
  platform-auditor.md (updated)
  [codebase-mapper.md removed]

skills/
  workflows/self-improve/SKILL.md
  dev/data-modeling/SKILL.md
  review/data-security/SKILL.md
  docs/simplify/SKILL.md
  govern/adaptive-standards
  [patterns/** removed and migrated into references/]

src/ai_engineering/
  installer/tools.py
  installer/auth.py
  installer/cicd.py
  installer/branch_policy.py
  cli_commands/review.py
  cli_commands/cicd.py
```

## Session Map

| Phase | Name | Size | Scope | Dependencies |
|-------|------|------|-------|--------------|
| 0 | Scaffold + Activation | S | Spec files, `_active.md`, product pointer, branch | None |
| 1 | Agent Surface Evolution | L | Add 6 agents, remove mapper, update agent references/wrappers | Phase 0 |
| 2 | Skill Surface Evolution | L | Add 5 skills, remove patterns category, merge audit-report | Phase 1 |
| 3 | Reference Consolidation | M | Introduce domain references and wire to perspective agents | Phase 2 |
| 4 | Installer Runtime Expansion | L | Tool install/auth/cicd/policy/verification phases in runtime | Phase 2 |
| 5 | VCS + Pipeline Enforcement | L | Provider contract expansion, PR review posting, policy APIs, pipeline checks | Phase 4 |
| 6 | CLI + State Model Integration | M | New review command and manifest/state model extensions | Phases 4-5 |
| 7 | Docs + Pointer Synchronization | M | AGENTS/CLAUDE/Copilot pointers and template mirror parity | Phases 1-6 |
| 8 | Test, Integrity, Closure | M | Unit/integration updates, gates, integrity-check, done.md | Phase 7 |

## Patterns

- **No multi-model implementation**: all execution remains single-platform deterministic.
- **Perspective agents + domain references**: avoid role-agent explosion; add domain capability through references and focused skills.
- **Install-to-operational default**: install must leave CI/CD and PR governance configured, or provide exact manual fallback path.
- **Stack-aware by contract**: generated pipelines run only checks relevant to installed stacks.
- **API-first resilience**: if CLIs or policy permissions fail, shift to direct API mode and generate deterministic guidance.
- **Provider-aware VCS setup**: GitHub installs/uses `gh`; Azure DevOps installs/uses `az`; both support API-direct fallback.
- **Surface target lock**: final outcome must match 14 agents + 44 skills + 6 categories + 0 skill orphans.
- **Self-improve orchestration**: `workflows/self-improve` executes analyze→plan→execute→verify→learn with navigator + governance-steward continuity.
- **One phase, one atomic commit**: `spec-021: Phase N — <description>`.
