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
  workflow/
    checkpoints/               /ai-orchestrator plans (<slug>.json) + viewer.html
    test-plans/                /ai-test-planner plans (<slug>.json)
    reviews/                   /ai-adversarial-loop debate threads
skills/                        Installed skill canon
agents/                        Specialist agents for the feature workflow
prototypes/                    /ai-prototype HTML mockups + <name>.states.json scenarios
.playwright/                   Sign-in sessions and review screenshots (gitignored)
```

<!-- Add the app's own files below as they're created. -->
