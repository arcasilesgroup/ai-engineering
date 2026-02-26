# Skills & Agents Schema Standard

## Update Metadata

- Rationale: formalize skill directory format, gating metadata, and agent frontmatter for multi-agent interoperability and token efficiency.
- Expected gain: AgentSkills-compatible skills; machine-parseable agent metadata; progressive disclosure reducing token overhead by ~70%.
- Potential impact: all 49 skills migrate from flat files to directories; all 19 agents gain structured frontmatter.

## Purpose

Definitive schema reference for skill directories, skill gating metadata, agent structured frontmatter, and token budget guidelines. This standard ensures consistency across all governance content and enables future interoperability with external frameworks (AgentSkills.io, A2A Agent Cards, MCP tool manifests).

## Skill Directory Schema

### Layout

```
skills/<category>/<name>/
├── SKILL.md              (required)
├── scripts/              (optional)
│   └── <script-name>.sh|.py
├── references/           (optional)
│   └── <topic>.md
└── assets/               (optional)
    └── <resource-file>
```

### Categories

| Category | Purpose | Example Skills |
|----------|---------|----------------|
| `workflows` | Git and branch lifecycle operations | commit, pr, acho, pre-implementation, cleanup |
| `dev` | Development lifecycle and code improvement | debug, code-review, refactor, test-strategy, multi-agent |
| `review` | Specialized assessment and audit | architecture, security, performance, dast, container-security |
| `quality` | Quality gates and metrics | audit-code, release-gate, test-gap-analysis, sbom |
| `govern` | Governance, risk, and compliance | integrity-check, create-spec, accept-risk, ownership-audit |
| `docs` | Documentation and communication | changelog, explain, writer, prompt-design |

### SKILL.md Frontmatter

#### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Kebab-case skill identifier. Must match directory name. |
| `description` | string | One-line summary: what the skill does AND when to use it. This is the primary triggering mechanism — AI reads this to decide whether to invoke the skill. |
| `version` | string | Semantic version (e.g., `1.0.0`). |
| `category` | string | One of: `workflows`, `dev`, `review`, `quality`, `govern`, `docs`. |
| `tags` | list | Discovery keywords for search and filtering. |

#### Optional Fields (Gating Metadata)

```yaml
metadata:
  ai-engineering:
    requires:
      stacks: [python, dotnet, nextjs]     # eligible only for these stacks
      bins: [ruff, uv]                      # all must exist on PATH
      anyBins: [pytest, vitest]             # at least one must exist
      env: [GITHUB_TOKEN]                   # env vars that must be set
      config: [providers.vcs.primary]       # manifest keys that must be truthy
    os: [darwin, linux, win32]              # eligible platforms
    always: false                           # true = skip all gating
    scope: read-only                        # read-only | read-write
    token_estimate: 1200                    # estimated tokens for body
```

#### Gating Logic

```
IF metadata.ai-engineering.always == true:
  → skill is always eligible (skip all other gates)

IF metadata.ai-engineering.requires.stacks is set:
  → skill eligible only if detected project stack is in the list

IF metadata.ai-engineering.requires.bins is set:
  → ALL listed binaries must exist on PATH

IF metadata.ai-engineering.requires.anyBins is set:
  → AT LEAST ONE listed binary must exist on PATH

IF metadata.ai-engineering.requires.env is set:
  → ALL listed env vars must be non-empty

IF metadata.ai-engineering.requires.config is set:
  → ALL listed manifest keys must be truthy

IF metadata.ai-engineering.os is set:
  → current platform must be in the list

IF NO metadata.ai-engineering block:
  → skill is always eligible (no gating)
```

Gating is advisory in the content-first model. The AI evaluates eligibility and filters skills from its working set. Runtime enforcement is deferred to the Python module.

### SKILL.md Body

The body follows the existing skill template structure:

```markdown
# <Skill Title>

## Purpose
<What the skill does and why>

## Trigger
<When to invoke and in what context>

## When NOT to Use
<Explicit exclusions to prevent misuse>

## Procedure
<Step-by-step execution instructions>

## Output Contract
<What the skill produces>

## Governance Notes
<Enforcement rules and compliance requirements>

## References
<Links to standards, other skills, agents>
```

Keep SKILL.md body under 500 lines. For longer content, split into `references/` files and link from the body.

### Bundled Resources

#### scripts/

Executable scripts for deterministic tasks. Benefits:

- **Token efficient**: scripts run directly, not loaded into context.
- **Deterministic**: same result every time, no AI re-interpretation.
- **Testable**: scripts can be validated independently.

Use for: pre-commit checks, format validation, file generation, data transformation.

Do NOT use for: decision-making, context-dependent logic, tasks requiring AI judgment.

#### references/

Documentation the AI loads on-demand. Benefits:

- **Progressive disclosure**: loaded only when needed, not at session start.
- **Keeps SKILL.md lean**: detailed content lives here, not in the body.

Use for: OWASP checklists, API documentation, schema references, pattern catalogs.

Structure references with clear headings so the AI can selectively read sections.

#### assets/

Files used in output, not loaded into context. Benefits:

- **Zero token cost**: copied or modified, never read into context.

Use for: templates, boilerplate, configuration files, icons.

## Agent Frontmatter Schema

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Kebab-case agent identifier. Must match filename (without `.md`). |
| `version` | string | Semantic version (e.g., `1.0.0`). |
| `scope` | string | `read-only` (analyzes, reports) or `read-write` (modifies files). |
| `capabilities` | list | Machine-readable capability tokens for orchestrator selection. |
| `inputs` | list | What the agent needs to start work. |
| `outputs` | list | What the agent produces. |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `tags` | list | Discovery keywords. |
| `references.skills` | list | Skills this agent uses (relative paths). |
| `references.standards` | list | Standards this agent enforces (relative paths). |

### Capability Tokens (standardized vocabulary)

| Domain | Tokens |
|--------|--------|
| Security | `sast`, `secret-detection`, `dependency-audit`, `owasp-review`, `dast`, `container-scan`, `sbom` |
| Quality | `coverage-analysis`, `complexity-analysis`, `duplication-analysis`, `lint`, `type-check`, `quality-gate` |
| Architecture | `dependency-mapping`, `coupling-analysis`, `cohesion-analysis`, `boundary-analysis`, `drift-detection` |
| Code | `code-review`, `refactoring`, `debugging`, `test-design`, `migration` |
| Governance | `integrity-check`, `contract-compliance`, `ownership-audit`, `risk-management` |
| Docs | `changelog`, `explanation`, `documentation`, `prompt-engineering` |
| Operations | `install-verification`, `cli-testing`, `hook-verification`, `state-validation` |
| Mapping | `structure-mapping`, `api-mapping`, `dependency-flow` |
| Simplification | `complexity-reduction`, `dead-code-removal`, `abstraction-evaluation` |
| Orchestration | `multi-dimension-audit`, `release-gate`, `cross-domain-synthesis` |

### Input/Output Vocabulary

**Inputs**: `file-paths`, `diff`, `repository`, `spec-hierarchy`, `codebase`, `module`, `changeset`, `configuration`, `test-results`, `dependency-list`.

**Outputs**: `findings-report`, `quality-verdict`, `dependency-graph`, `coupling-assessment`, `tech-debt-catalog`, `improvement-plan`, `drift-matrix`, `decision-records`, `audit-report`, `codebase-map`, `refactoring-plan`, `test-strategy`, `explanation`, `documentation`, `release-verdict`.

### Example Agent Frontmatter

```yaml
---
name: security-reviewer
version: 1.0.0
scope: read-only
capabilities: [sast, secret-detection, dependency-audit, owasp-review, dast, container-scan, sbom]
inputs: [file-paths, diff, repository, dependency-list]
outputs: [findings-report]
tags: [security, owasp, vulnerabilities, sast]
references:
  skills:
    - skills/review/security/SKILL.md
    - skills/review/dast/SKILL.md
    - skills/review/container-security/SKILL.md
    - skills/quality/sbom/SKILL.md
  standards:
    - standards/framework/core.md
---
```

## Token Budget Guidelines

### Measurement Formula

Token estimates use the approximation: **1 token ≈ 4 characters** (conservative for English text with markdown formatting).

```
skill_tokens = len(frontmatter_chars) / 4 + len(body_chars) / 4
agent_tokens = len(frontmatter_chars) / 4 + len(body_chars) / 4
```

### Budget by Loading Level

| Level | When Loaded | Budget Target |
|-------|-------------|---------------|
| **Metadata** (name + description) | Always in session | ≤ 50 tokens per skill |
| **Body** (SKILL.md content) | On-demand when invoked | ≤ 1,500 tokens per skill |
| **Resources** (scripts, references) | On-demand by AI decision | No hard limit (not in context window) |
| **Agent persona** | On-demand when activated | ≤ 500 tokens per agent |

### Session Token Budget

| Scenario | Metadata Load | On-Demand Load | Total Budget |
|----------|--------------|----------------|-------------|
| **Session start** (spec work) | ~500 tokens (CLAUDE.md compact + spec + decision-store) | 0 | ~500 |
| **Single skill invocation** | +50 (skill metadata) | +1,500 (skill body) | ~2,050 |
| **Agent activation + 2 skills** | +200 (agent + 2 skill metadata) | +2,500 (agent + skill bodies) | ~3,200 |
| **Platform audit (8 dimensions)** | +450 (9 skills metadata) | +12,000 (bodies loaded serially) | ~12,950 |

### Detailed Token Inventory

#### Skills by Category

| Category | Skills | Total Tokens | Avg Tokens | Min | Max |
|----------|--------|-------------|------------|-----|-----|
| workflows | 6 | 4,830 | 805 | 530 (self-improve) | 1,400 (pr) |
| dev | 13 | 10,200 | 785 | 525 (data-modeling) | 1,125 (multi-agent) |
| review | 7 | 5,250 | 750 | 650 (performance) | 900 (security) |
| quality | 6 | 5,981 | 997 | 307 (install-check) | 1,603 (docs-audit) |
| govern | 12 | 18,500 | 1,542 | 900 (resolve-risk) | 2,200 (integrity-check, create-spec) |
| docs | 5 | 3,800 | 760 | 600 (prompt-design) | 1,050 (writer) |
| **Total** | **49** | **48,561** | **991** | **307** | **2,200** |

#### Agents

| Agent | Est. Tokens | Capabilities | Scope |
|-------|------------|-------------|-------|
| architect | 932 | 6 | read-only |
| code-simplifier | 763 | 8 | read-write |
| debugger | 668 | 2 | read-write |
| devops-engineer | 165 | 5 | read-write |
| docs-writer | 185 | 4 | read-write |
| governance-steward | 215 | 4 | read-write |
| navigator | 230 | 6 | read-only |
| orchestrator | 840 | 5 | read-write |
| platform-auditor | 1,056 | 3 | read-only |
| pr-reviewer | 160 | 3 | read-only |
| principal-engineer | 787 | 7 | read-only |
| quality-auditor | 726 | 4 | read-only |
| security-reviewer | 1,024 | 8 | read-only |
| test-master | 400 | 3 | read-write |
| verify-app | 795 | 4 | read-only |
| api-designer | 1,231 | 5 | read-write |
| database-engineer | 1,209 | 5 | read-write |
| frontend-specialist | 1,263 | 6 | read-only |
| infrastructure-engineer | 1,176 | 6 | read-write |
| **Total** | **12,825** | — | — |
| **Average** | **675** | **5.1** | — |

#### Token Efficiency Score

```
efficiency = session_start_tokens / total_available_tokens
           = 500 / (48,561 + 12,825)
           = 500 / 61,386
           = 0.81% loaded at session start (99.19% deferred)
```

### Compared to Previous Model

| Metric | Before (flat loading) | After (progressive disclosure) |
|--------|----------------------|-------------------------------|
| Session start overhead | ~3,000-5,000 tokens | ~500 tokens |
| Multi-agent (3 parallel) start | ~9,000-15,000 tokens | ~1,500 tokens |
| Single skill invocation | ~3,000-5,000 + skill | ~500 + 1,550 = ~2,050 |

## Behavioral Patterns

Standard behavioral patterns that agents and skills should adopt. These patterns were identified through cross-industry analysis of 35+ AI tool system prompts (Claude Code, Cursor, Windsurf, Devin, Manus, Kiro, Amp, Google Antigravity, RooCode, Bolt, v0, Same.dev, Orchids) and codified as framework norms.

### Escalation Ladder

All agents and procedural skills must implement iteration limits:

- **Max 3 attempts** to resolve the same issue before escalating to the user.
- Each attempt must try a **different approach** — repeating the same action is not a valid retry.
- **Escalation format**: present what was tried, what failed, and options for the user.
- **Never loop silently**: if stuck, surface the problem immediately.

Agents implement this in `## Boundaries → ### Escalation Protocol`. Skills implement this in `## Governance Notes → ### Iteration Limits`.

### Confidence Signaling

Read-only audit and review agents include a confidence signal in their output:

- **Confidence**: HIGH (0.8-1.0) | MEDIUM (0.5-0.79) | LOW (0.0-0.49) — with brief justification.
- **Blocked on user**: YES/NO — whether user input is needed to proceed.

Applicable agents: platform-auditor, verify-app, quality-auditor, security-reviewer, pr-reviewer, architect.

### Post-Edit Validation

Read-write agents and skills must validate after every file modification:

- **Code files**: run applicable linter (`ruff check` + `ruff format --check` for Python).
- **Governance files** (`.ai-engineering/`): run `integrity-check`.
- **Never proceed** to the next step if validation fails — fix first, then continue.

Agents implement this as an explicit behavior step. Skills implement this in `## Governance Notes → ### Post-Action Validation`.

### Headless Mode

Interactive skills that normally prompt for user input must provide a headless fallback:

- **Default to standard options** when no user input is available (e.g., Standard depth, complete output).
- **Skip interactive follow-up** prompts and generate complete output directly.
- **Note assumptions** made in headless mode so the user can adjust after the fact.

### When NOT to Use (Routing)

Skills with high confusion risk must include a `## When NOT to Use` section that routes users to the correct skill:

- List 2-4 common misuse scenarios with the correct alternative skill.
- Format: `**<Scenario>** — use \`<correct-skill>\` instead. <Brief reason>.`
- This prevents skill confusion and reduces wasted execution.

### Holistic Analysis Before Action

Agents and skills must analyze the full system context before modifying any file:

- **Read affected dependencies**: before editing a file, identify its importers/consumers and assess downstream impact.
- **Anticipate cascading changes**: if modifying a shared module, enumerate all callers and verify none will break.
- **No isolated edits**: treat each change as part of a system, not a standalone fix.
- **Implementation**: agents add a "Map context" or "Analyze dependencies" step before any edit step in their Behavior section.

Derived from audit patterns: Leap.new (holistic thinking protocol), Manus (event stream analysis), Google Antigravity (Knowledge Item context).

### Exhaustiveness Requirement

When a skill or agent identifies N issues, ALL N must be addressed or explicitly deferred with rationale:

- **No partial solutions**: if a review finds 5 issues, all 5 must appear in the output — not just the first 3.
- **No early exits**: complete all procedure steps. If a step is not applicable, state why and proceed.
- **Explicit deferral**: if an issue cannot be resolved in the current scope, log it with rationale and severity.
- **Implementation**: skills include "Enumerate all findings before proceeding" in their procedure. Agents include "Validate completeness against initial scope" in their final steps.

Derived from audit patterns: Comet (no early exits), Same.dev (complete resolution required), Trae (task state completion enforcement).

### Parallel-First Tool Execution

When multiple independent operations are needed, execute them in parallel by default:

- **Default to parallel**: when checks, scans, or reads have no data dependencies, batch them.
- **Sequential only on dependency**: explicitly document why sequential execution is needed when used.
- **Batch operations**: minimize tool round-trips. Group related file reads, lint checks, and scan operations.
- **Implementation**: agents structure their Behavior steps to identify parallelizable operations. Skills document parallelizable vs sequential steps in their procedure.

Derived from audit patterns: Same.dev (emphatic parallel execution), Cursor (parallel tool calls), Lovable (batch tool operations).

## Migration Guide

### Migrating a Flat Skill to Directory

1. Create directory: `skills/<category>/<name>/`
2. Move `<name>.md` → `skills/<category>/<name>/SKILL.md`
3. Update frontmatter: add `description` field (one-line summary of what + when).
4. Add `metadata.ai-engineering` block if the skill has specific requirements.
5. Optionally extract large content sections into `references/` files.
6. Update all cross-references pointing to the old path.

### Adding Frontmatter to an Agent

1. Add YAML frontmatter block before the `# <Agent Name>` heading.
2. Fill required fields: `name`, `version`, `scope`, `capabilities`, `inputs`, `outputs`.
3. Map existing "Capabilities" section bullets to machine-readable `capabilities` tokens.
4. Map existing "Referenced Skills" to `references.skills` paths.
5. Map existing "Referenced Standards" to `references.standards` paths.
6. Keep all existing markdown content unchanged.

## Governance Notes

- Skill directories are framework-managed content. Team layers cannot weaken them.
- Skills without `SKILL.md` are invalid and will be ignored by the framework.
- The `name` field in frontmatter MUST match the directory name.
- Gating metadata is advisory in the content-first model. Do not rely on it for security enforcement.
- Token estimates are guidelines, not hard limits. Optimize for clarity over brevity.
- This standard is referenced by `standards/framework/core.md` and governs all skill/agent content.

## References

- `standards/framework/core.md` — skill and agent base rules, progressive disclosure.
- `context/product/framework-contract.md` — content-first product model, token efficiency principle.
- `skills/govern/create-skill/SKILL.md` — skill registration procedure.
- `skills/govern/create-agent/SKILL.md` — agent registration procedure.

## Update Contract

This file is framework-managed and can be updated by framework migrations.
