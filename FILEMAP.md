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
scripts/
  gen-assets.ts                Generate embedded assets from their source files
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
      azure-signals.mjs        Normalize scoped Azure evidence, sources and coverage
      azure-signals.d.mts      Signal normalization types
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
  skills.spec.ts               Skill contracts, including the local recap handoff
  generated-payload.test.ts   Assert generated assets match their source files
  triage-*.spec.ts             Synthetic GitHub, Azure, routing and report contract tests
templates/
  recap.html.tpl               Self-contained HTML recap shell and styles
agents/                        Specialist agents for the feature workflow
.ai-engineering/workflow/playwright/  Sign-in sessions and review screenshots (gitignored)
```

<!-- Add the app's own files below as they're created. -->
