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
  assets.ts                    Embedded core skill, pack, template and runtime asset registry
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
  gen-assets.ts                Generate embedded assets from skills/, packs/, agents/ and templates/
  bench-chain.ts               `bun run bench`: prints the chain's p95 latency; never a gate
  tokens.ts                    `bun run tokens`: report skill-frontmatter and AGENTS-template byte/4 counts
  .embed/packs/                 Generated text payloads for pack scripts and eval fixtures
skills/                        Installed skill canon
  ai-brainstorm/SKILL.md       Interview, classify and record approved feature intent
  ai-orchestrator/SKILL.md     Gated feature workflow in the selected checkout
  ai-pr/SKILL.md               Provider-neutral PR base selection and review loop
  ai-git-cleanup/SKILL.md      Native-Git preview and safe local cleanup
  ai-verify/                   Core verification router and setup guide; optional tiers live in packs/
packs/                         Optional specialist skills, embedded separately from the core canon
  triage/                      Provider-neutral GitHub and Azure backlog analysis
  design-md-planner/           Product taste interview and DESIGN.md creation
  audit-design/                Measured browser-based interface audit
  visual-recap/                User-invoked HTML recap procedure and assets
  writing-behavior/            Agent behavior specification and calibration
  stress-test/                 Adversarial stress-test planning
  verify-tiers/
    tiers/                     Standalone, embedded and chain verification skills
    evals/                     Bug fixtures and verifier scoring tools
tests/
  worktree-command.spec.ts     Managed worktree rebase, merge, hook and recovery tests
  skills.spec.ts               Skill contracts, including the local recap handoff
  ceremony-contract.spec.ts    Every skill, agent, script and template ai-orchestrator cites exists and ships embedded
  generated-payload.test.ts   Assert generated assets match their source files
  triage-*.spec.ts             Synthetic GitHub, Azure, routing and report contract tests for packs/triage
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
  checkpoint-planner.md        Checkpoint plan schema and initial lifecycle
.ai-engineering/workflow/playwright/  Sign-in sessions and review screenshots (gitignored)
```

<!-- Add the app's own files below as they're created. -->
