# File map

What each file and folder is for. Update it whenever files are added, moved, or removed.

```
AGENTS.md                      Project instructions + Project config read by skills/agents
DECISIONS.md                   Standing decisions (## D-NNN)
CHANGELOG.md                   User-facing change log
LEARNINGS.md                   Append-only failure log + promoted Rules
FILEMAP.md                     This file
PERMISSIONS.md                 Endpoint × role access matrix (n/a until the product has endpoints)
.ai-engineering/
  PRD.html                     Product scope, roles, business rules
  DESIGN.md                    Design system (created by /ai-design-md-planner)
  design/
    audits/                    /ai-audit-design HTML reports (NNN-<name>.html)
  workflow/
    checkpoints/               /ai-orchestrator plans (<slug>.json) + viewer.html
    test-plans/                /ai-test-planner plans (<slug>.json)
    reviews/                   /ai-adversarial-loop debate threads
    prototypes/                /ai-prototype HTML mockups + <name>.states.json scenarios
src/
  assets.ts                    Embedded skill, template and runtime asset registry
  payload.ts                   Normalized tool payloads and shared call fingerprints
  commands/
    worktree.ts                CLI parser for new, list, merge, request-changes and rm
  git/
    run.ts                     The one Git runner: status, raw stdout/stderr, optional global/system-config isolation
    context.ts                 resolveContext: root, branch or detached, linked worktree, base and its source (6.7)
    merge.ts                   Reviewed-SHA merge transaction, exact parents/tree, base-ref CAS and safe checkout refresh
  workflow/
    checkpoint.ts              Checkpoint schema, lifecycle transitions, legacy normalization and brainstorm approval
  guards/
    checkpoint.ts              Checkpoint schema, lifecycle, gate order and Stop enforcement in the chain
  shared-worktree.ts           Worktree inventory, creation, lifecycle SHA-CAS, listing and safe removal
  shared-hash.ts               Shared SHA-256 file hashing helper
tests/
  git-context.spec.ts          Git runner and context resolver over real temp repos with isolated config
  worktree-command.spec.ts     CLI contracts for worktree creation, registered-source merge, lifecycle and safe removal
scripts/
  gen-assets.ts                Generate embedded assets from their source files
  bench-chain.ts               `bun run bench`: prints the chain's p95 latency; never a gate
  .embed/ai-triage/scripts/    Generated text payloads for triage scripts and declarations
skills/                        Installed skill canon
  ai-triage/
    SKILL.md                   Single entry point; routes to the selected provider
    references/
      azure-devops.md          Azure DevOps Services scope, reads and report contract
      github.md                GitHub inventory, ranking and report procedure
    scripts/
      collect-azure.mjs        Scoped Azure backlog collector
      collect-azure.d.mts      Collector types
      azure-signals.mjs        Normalize evidence; validate claims and derive recommendations
      azure-signals.d.mts      Signal, claim, assessment and recommendation types
      render-report.mjs        Safe report rendering and atomic write
      render-report.d.mts      Report writer types
      resolve-target.mjs       Explicit provider and target resolution
      resolve-target.d.mts     Target resolver types
  ai-visual-recap/
    SKILL.md                   Local HTML recap procedure used during app review
    references/
      wireframe.md             Guidance for recap visuals
    assets/
      highlight.mjs            Syntax highlighting for code excerpts
tests/
  worktree-command.spec.ts     Managed worktree rebase, merge, hook and recovery tests
  skills.spec.ts               Skill contracts, including the local recap handoff
  ceremony-contract.spec.ts    Every skill, agent, script and template ai-orchestrator cites exists and ships embedded
  generated-payload.test.ts   Assert generated assets match their source files
  triage-*.spec.ts             Synthetic GitHub, Azure, routing and report contract tests
  test-hygiene.spec.ts         No suite writes under tests/; sandboxed suites restore env and cwd
  receipts-retention.spec.ts   Daily, batched receipt retention triggered by the chain
  fixtures/
    env-snapshot.preload.ts    Records env and cwd before and after every suite for test-hygiene.spec.ts
    sandbox-env.ts             Snapshot/restore of AI_ENG_HOME, PI_CODING_AGENT_DIR, GIT_CONFIG_GLOBAL for sandboxed suites
    private-stdin.ts           A suite-owned stdin for prompt-driving suites, so runner input never answers a prompt
    triage-azure-signals-preview.mjs  Synthetic writer preview on loopback, memory-only reports
templates/
  recap.html.tpl               Self-contained HTML recap shell and styles
agents/                        Specialist agents for the feature workflow
.ai-engineering/workflow/playwright/  Sign-in sessions and review screenshots (gitignored)
```

<!-- Add the app's own files below as they're created. -->
