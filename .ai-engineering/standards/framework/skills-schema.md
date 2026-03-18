# Skills & Agents Schema Standard

## Update Metadata

- Rationale: formalize skill directory format, gating metadata, and agent frontmatter for multi-agent interoperability and token efficiency.
- Expected gain: AgentSkills-compatible skills; machine-parseable agent metadata; progressive disclosure reducing token overhead by ~70%.
- Potential impact: all 47 skills migrate from flat files to directories; all 6 agents gain structured frontmatter.

## Purpose

Definitive schema reference for skill directories, skill gating metadata, agent structured frontmatter, and token budget guidelines. This standard ensures consistency across all governance content and enables future interoperability with external frameworks (AgentSkills.io, A2A Agent Cards, MCP tool manifests).

## Skill Directory Schema

### Layout

```
skills/<name>/
├── SKILL.md              (required)
├── scripts/              (optional)
│   └── <script-name>.sh|.py
├── references/           (optional)
│   └── <topic>.md
└── assets/               (optional)
    └── <resource-file>
```

Skills use a flat organization (no category subdirectories). Skills are discovered by `tags` rather than directory hierarchy.

### SKILL.md Frontmatter

#### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Kebab-case skill identifier. Must match directory name. |
| `description` | string | One-line summary: what the skill does AND when to use it. This is the primary triggering mechanism — AI reads this to decide whether to invoke the skill. |
| `version` | string | Semantic version (e.g., `1.0.0`). |
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
name: review
version: 1.0.0
scope: read-only
capabilities: [sast, secret-detection, dependency-audit, owasp-review, quality-gate, governance-lifecycle]
inputs: [file-paths, diff, repository, dependency-list, spec, governance-content]
outputs: [findings-report, audit-report, gate-verdict, compliance-report]
tags: [review, security, quality, governance, audit, compliance, verification]
references:
  skills:
    - skills/security/SKILL.md
    - skills/quality/SKILL.md
    - skills/governance/SKILL.md
  standards:
    - standards/framework/core.md
    - standards/framework/quality/core.md
---
```

## Token Budget Guidelines

> Canonical progressive disclosure rules: `standards/framework/core.md`. This section provides implementation detail.

### Budget by Loading Level

| Level | When Loaded | Budget Target |
|-------|-------------|---------------|
| **Metadata** (name + description) | Always in session | ≤ 50 tokens per skill |
| **Body** (SKILL.md content) | On-demand when invoked | ≤ 1,500 tokens per skill |
| **Resources** (scripts, references) | On-demand by AI decision | No hard limit (not in context window) |
| **Agent persona** | On-demand when activated | ≤ 500 tokens per agent |

## Behavioral Patterns

All agents and skills must adopt these behavioral norms:

1. **Escalation Ladder** — max 3 attempts, different approach each time, never loop silently.
2. **Confidence Signaling** — read-only agents include HIGH/MEDIUM/LOW confidence with justification.
3. **Post-Edit Validation** — run linter (code) or integrity-check (governance) after every modification.
4. **Headless Fallback** — interactive skills default to standard options when no user input available.
5. **When NOT to Use** — high-confusion skills route to correct alternative.
6. **Holistic Analysis** — analyze dependencies and downstream impact before modifying files.
7. **Exhaustiveness** — all N issues addressed or explicitly deferred with rationale.
8. **Parallel-First** — batch independent operations; sequential only on data dependency.

## Migration Guide

### Adding a New Skill

1. Create directory: `skills/<name>/`
2. Create `skills/<name>/SKILL.md` with required frontmatter.
3. The `name` field must match the directory name.
4. Add `metadata.ai-engineering` block if the skill has specific requirements.
5. Optionally add `scripts/`, `references/`, `assets/` subdirectories.
6. Register in manifest and update instruction files.

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
- `skills/lifecycle/SKILL.md` — skill and agent creation procedure.
- `skills/lifecycle/SKILL.md` — skill and agent deletion procedure.

## Update Contract

This file is framework-managed and can be updated by framework migrations.
