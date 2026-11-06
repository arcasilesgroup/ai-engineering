# File map

What each file and folder is for. Update it whenever files are added, moved, or removed.

```
AGENTS.md                      Project instructions + Project config read by skills/agents
DECISIONS.md                   Standing decisions (## D-NNN)
CHANGELOG.md                   User-facing change log
LEARNINGS.md                   Append-only failure log + promoted Rules
FILEMAP.md                     This file
PERMISSIONS.md                 Azure DevOps triage read routes and scope boundaries
.gitattributes                 Keeps LF line endings on every checkout, Windows included
docs/
  blueprint.html               Product design context and decisions
  recap.html                   Historical product snapshot; use README.md and the source tree for current guidance
  global-carriers.md           Host carrier paths and their machine/repository scope
.changeset/
  <slug>.md                    Pending package version and release summary
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
    run.ts                     The one Git runner: status, raw stdout/stderr, optional global/system-config isolation, commit identity
    context.ts                 resolveContext: root, branch or detached, linked worktree, base and its source (6.7)
    merge.ts                   Reviewed-SHA merge transaction, exact parents/tree, base-ref CAS and safe checkout refresh
    worktree.ts                Shared worktree reads: root, registered list, status, in-progress operation
  workflow/
    checkpoint.ts              Checkpoint schema, lifecycle transitions, legacy normalization and brainstorm approval
  guards/
    checkpoint.ts              Checkpoint schema, lifecycle, gate order and Stop enforcement in the chain
  shared-worktree.ts           Worktree inventory, creation, lifecycle SHA-CAS, listing and safe removal
  shared-hash.ts               Shared SHA-256 file hashing helper
  shared-project-fs.ts         Guarded project-path reads and writes: refuse links and paths that leave the repository
tests/
  git-context.spec.ts          Git runner and context resolver over real temp repos with isolated config
  checkpoint-guard.spec.ts     Checkpoint schema, lifecycle gates and Stop enforcement
  workflow-checkpoint.spec.ts  Checkpoint codec, legacy normalization and lifecycle transitions
  docs-lint.spec.ts             CLI verb citations and relative Markdown/HTML link integrity
  worktree-command.spec.ts     CLI contracts for worktree creation, registered-checkout lifecycle and safe removal
  skills-lint.spec.ts           Skill frontmatter, Lifecycle, relative links and workflow contracts
  token-budget.spec.ts          Core token budgets and silent successful-hook output
scripts/
  gen-assets.ts                Generate embedded assets from skills/, agents/ and templates/
  bench-chain.ts               `bun run bench`: prints the chain's p95 latency; never a gate
  tokens.ts                    `bun run tokens`: report skill-frontmatter and AGENTS-template byte/4 counts
  package-consumer-smoke.ts    Pack (or take `--tarball`), install in temp npm and Bun consumers, run `ai-eng --version`
  release-sbom.ts              Runtime-only CycloneDX SBOM for a packed tarball, named by its sha256
  release-policy.ts            Release gate: signed annotated tag on the dispatched SHA by an allowlisted key, verified NOTICE.md rights
  .embed/<skill-name>/scripts/  Generated text payloads for skill scripts
skills/                        Installed skill canon
  ai-brainstorm/SKILL.md       Interview, classify and record approved feature intent
  ai-orchestrator/SKILL.md     Gated feature workflow in the selected checkout
  ai-pr/SKILL.md               Provider-neutral PR base selection and review loop
  ai-git-cleanup/SKILL.md      Native-Git preview and safe local cleanup
  ai-verify/                   Verification router, setup guide and shared review conventions
  ai-triage/                   Provider-neutral GitHub and Azure backlog analysis
  ai-design-md-planner/        Product taste interview and DESIGN.md creation
  ai-audit-design/             Measured browser-based interface audit
  ai-visual-recap/             User-invoked HTML recap procedure and assets
  ai-writing-behavior/         Agent behavior specification and calibration
  ai-stress-test/              Adversarial stress-test planning
  <skill-name>/                Every other shipped skill and its resources
tests/
  skills.spec.ts               Skill contracts, including the local recap handoff
  ceremony-contract.spec.ts    Every skill, agent, script and template ai-orchestrator cites exists and ships embedded
  generated-payload.test.ts   Assert generated assets match their source files
  triage-*.spec.ts             Synthetic GitHub, Azure, routing and report contract tests for skills/ai-triage
  fixtures/verify-tiers/evals/ Test-only verifier scoring tools and evaluation fixtures
  test-hygiene.spec.ts         No suite writes under tests/; sandboxed suites restore env and cwd
  package-consumer.spec.ts     The packed tarball installs and reports its version, Bun-only PATH included
  release-sbom.spec.ts         The SBOM lists only the installed runtime graph, deterministically
  release-workflow.spec.ts     release.yml builds from the dispatched SHA, packs once and publishes that tarball
  release-policy.spec.ts       Tag, signer and NOTICE.md refusals of the release policy
  chain-contract.spec.ts       Dispatcher receipts, repo resolution, verdict cache and malformed-payload denial
  checkpoint-guard-contract.spec.ts  Exact checkpoint-guard refusals and allowed writes
  self-protect-contract.spec.ts  Exact self-protect verdict per shell shape and the layer that gives it
  shell-guard-contract.spec.ts  The shared shell reader: segments, quoting, redirects and substitutions
  guards-contract.spec.ts      Exact verdicts of the smaller guards and the override switch
  floor-contract.spec.ts       Uninstall's git-template restore and pre-push through the hook entry
  receipts-retention.spec.ts   Daily, batched receipt retention triggered by the chain
  fixtures/
    env-snapshot.preload.ts    Records env and cwd before and after every suite for test-hygiene.spec.ts
    sandbox-env.ts             Snapshot/restore of AI_ENG_HOME, PI_CODING_AGENT_DIR, GIT_CONFIG_GLOBAL for sandboxed suites
    private-stdin.ts           A suite-owned stdin for prompt-driving suites, so runner input never answers a prompt
    fake-command.ts            Writes a PATH stand-in for a tool: shell script on POSIX, batch file on Windows
    git-recorder.ts            Records the git commands a test's code starts, on every platform
    gitleaks-shim.ts           Compiles and configures a `gitleaks` stand-in the floor finds on PATH
    gitleaks-shim-main.ts      The program behind gitleaks-shim.ts; answers from gitleaks-shim.json
    worktree-command.ts        In-process worktree command harness with isolated cwd, env and captured output
    triage-azure-signals-preview.mjs  Synthetic writer preview on loopback, memory-only reports
templates/
  recap.html.tpl               Self-contained HTML recap shell and styles
agents/                        Specialist agents for the feature workflow
  checkpoint-planner.md        Checkpoint plan schema and initial lifecycle
.ai-engineering/workflow/playwright/  Sign-in sessions and review screenshots (gitignored)
```

<!-- Add the app's own files below as they're created. -->
