# File map

What each file and folder is for. Update it whenever files are added, moved, or removed.

```
AGENTS.md                      Project instructions + Project config read by skills/agents
DECISIONS.md                   Standing decisions (## D-NNN)
CHANGELOG.md                   User-facing change log
LEARNINGS.md                   Promoted rules; its append-only log lives in docs/history/learnings-log.md
FILEMAP.md                     This file
PERMISSIONS.md                 Azure DevOps triage read routes and scope boundaries
.gitattributes                 Keeps LF line endings on every checkout, Windows included
brand/
  components.css               Style body spliced between the brand CSS markers
  components.js                The page script: scroll-spy, tabs, copy, filters, expand all
  gallery.html.tpl             The reference page: every component live, its markup and its do and don't
  mark.svg                     The {ai} mark, copied byte for byte from the website's favicon; the README hero draws it as an image
docs/
  global-carriers.md           Host carrier paths and their machine/repository scope
  surface-capability-matrix.md What each host can enforce, measured; the table doctor and the README follow
  install.md                   Install edge cases: from source, no administrator rights, the Windows gitleaks fallback
  cli.md                       Every CLI verb, by who runs it, and how to read a findings check
  lanes.md                     One task, one lane: list, tidy, park, drop, worktrees
  configuration.md             config.toml tables, the command-scope policy, the surface tiers
  troubleshooting.md           Symptom, cause, fix
  skills.md                    The build loop, its triggers and the catalogue of all 27 skills
  history/                     Records, never rewritten: the early blueprint, the recap, the learnings log
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
  payload.ts                   Normalized tool payloads and shared call fingerprints
  commands/
    findings.ts                CLI parser and Git-backed runner for `ai-eng findings check`
    worktree.ts                CLI parser for new, list, merge, request-changes and rm
  git/
    run.ts                     The one Git runner: status, raw stdout/stderr, optional global/system-config isolation, commit identity
    context.ts                 resolveContext: root, branch or detached, linked worktree, base and its source (6.7)
    merge.ts                   Reviewed-SHA merge transaction, exact parents/tree, base-ref CAS and safe checkout refresh
    worktree.ts                Shared worktree reads: root, registered list, status, in-progress operation
    shared-worktree.ts         Worktree inventory, creation, lifecycle SHA-CAS, listing and safe removal
  workflow/
    checkpoint.ts              Checkpoint schema, lifecycle transitions, legacy normalization and brainstorm approval
  guards/
    checkpoint.ts              Checkpoint schema, lifecycle, gate order and Stop enforcement in the chain
  shared-findings.ts           Pure review-finding signal checks, tallies and round parsing
  shared-hash.ts               Shared SHA-256 file hashing helper
  shared-project-fs.ts         Guarded project-path reads and writes: refuse links and paths that leave the repository
tests/
  git-context.spec.ts          Git runner and context resolver over real temp repos with isolated config
  checkpoint-guard.spec.ts     Checkpoint schema, lifecycle gates and Stop enforcement
  workflow-checkpoint.spec.ts  Checkpoint codec, legacy normalization and lifecycle transitions
  readme-assets.spec.ts        Every README image exists and is used; alt text, captions and text versions match the figures
  docs-lint.spec.ts             CLI verb citations and relative Markdown/HTML link integrity
  worktree-command.spec.ts     CLI contracts for worktree creation, registered-checkout lifecycle and safe removal
  skills-lint.spec.ts           Skill frontmatter, Lifecycle, relative links and workflow contracts
  token-budget.spec.ts          Core token budgets and silent successful-hook output
scripts/
  artifact-a11y.ts             The static accessibility gate: markup rules WCAG lets a test prove
  artifact-axe.ts              The browser gate `bun run a11y`: axe-core in system Chrome, keys, reflow, no script
  chain-bundle.ts              Build the chain module the in-process plugin hosts import (into generated/)
  readme-assets.ts             Renders the README's hero, headings, buttons, cards, guard and receipt panels, skills grid and figures from brand/tokens.json (no image model)
  readme-badges.ts             The README badge row as SVG: version, npm name and licence read from package.json and LICENSE (no shields.io)
  readme-figures.ts            The five figures as data and drawing: nodes, one-anchor edges, captions and text versions
  readme-diagrams.ts           Renders the older skill-chain and guard-flow SVGs, which the README no longer embeds
  bench-chain.ts               `bun run bench`: prints the chain's p95 latency; never a gate
  tokens.ts                    `bun run tokens`: report skill-frontmatter and AGENTS-template byte/4 counts
  package-consumer-smoke.ts    Pack (or take `--tarball`), install in temp npm and Bun consumers, run `ai-eng --version`
  first-install-probe.ts       Init every surface, run each written hook line in the host's shells (CI job first-install)
  release-sbom.ts              Runtime-only CycloneDX SBOM for a packed tarball, named by its sha256
  release-policy.ts            Release gate: signed annotated tag on the dispatched SHA by an allowlisted key, verified NOTICE.md rights
  sync-ci-template-pins.ts     `bun run version-packages` step: rewrite AI_ENG_VERSION in both CI templates from package.json
skills/                        Installed skill canon
  ai-brainstorm/SKILL.md       Interview, classify and record approved feature intent
  ai-orchestrator/SKILL.md     Gated feature workflow in the selected checkout
  ai-pr/SKILL.md               Provider-neutral PR base selection and review loop
  ai-verify/                   Verification router, setup guide and shared review conventions
  ai-triage/                   Provider-neutral GitHub and Azure backlog analysis
  ai-design-md-planner/        Product taste interview and DESIGN.md creation
  ai-audit-design/             Measured browser-based interface audit
  ai-visual-recap/             User-invoked HTML recap procedure and assets
  ai-writing-behavior/         Agent behavior specification and calibration
  ai-stress-test/              Adversarial stress-test planning
  <skill-name>/                Every other shipped skill and its resources
tests/
  brand-templates.spec.ts      Exact-byte brand marker splice, drift and parity line
  artifact-a11y.spec.ts        The static accessibility gate on every page, and one failing fixture per rule
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
  findings-check.spec.ts       Both-sided signal checks, counter invariants, round selection and Git-fact contracts
  receipts-retention.spec.ts   Daily, batched receipt retention triggered by the chain
  fixtures/
    findings/                  Captured multi-round review fixture (`rounds-hardening.json`) for findings checks
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
  *.html.tpl                   Page shells; install copies them to ~/.ai-engineering/templates/
  recap.html.tpl               Self-contained HTML recap shell and styles
agents/                        Specialist agents for the feature workflow
  checkpoint-planner.md        Checkpoint plan schema and initial lifecycle
.ai-engineering/workflow/playwright/  Sign-in sessions and review screenshots (gitignored)
```

<!-- Add the app's own files below as they're created. -->
