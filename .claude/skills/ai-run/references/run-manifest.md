# AI Run Manifest Contract

## Directory Layout

```text
.ai-engineering/runs/<run-id>/
  manifest.md
  items/
    <item-id>/
      spec.md
      plan.md
      report.md
```

## Manifest Sections

`manifest.md` is the run source of truth. At minimum it records:

- run metadata
  - run id
  - created at
  - invocation
  - mode
  - source provider
  - delivery provider
- source inventory
- baseline exploration summary
- normalized items
- overlap matrix summary
- DAG and waves
- branch and worktree map
- promotion history
- review and verify outcomes
- blocker log
- resume pointer
- final delivery state

## Suggested Skeleton

```markdown
# Run Manifest: <run-id>

## Run
- Status: intake|planning|orchestrating|executing|delivering|completed|blocked|deferred
- Mode: single-item|multi-item
- Source: github|azure|markdown
- Delivery: github|azure_devops

## Baseline Exploration
- Architecture:
- Hot spots:
- Shared artifacts:

## Items
| Item | Status | Risk | Branch | Wave | Close Policy |

## Overlap Matrix
| A | B | Relation | Notes |

## Waves
| Wave | Items | Status |

## Promotions
| Time | Item | Target | Result |

## Quality
| Scope | Review | Verify | Notes |

## Blockers
- none

## Resume
- Re-enter at:
```

## Rules

- Update the manifest after every phase transition.
- Update it after every promotion.
- Never rely on agent memory for resume.
- Do not store implementation logic in the manifest; store state and evidence.
