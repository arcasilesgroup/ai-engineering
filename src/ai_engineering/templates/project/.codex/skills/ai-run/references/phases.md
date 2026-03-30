# AI Run Phases

## Phase Map

| Phase | Name | Output |
|-------|------|--------|
| 1 | Intake and baseline explore | run manifest + normalized items |
| 2 | Item deepening and mini-plans | per-item `spec.md` + `plan.md` |
| 3 | DAG, waves, and packets | overlap matrix + DAG + packets |
| 4 | Execute and promote | item reports + integration state |
| 5 | Deliver and resume | PR, merge, or blocker report |

## Expanded Flow

1. Intake raw items from GitHub, Azure Boards, or markdown.
2. Run repository-wide `ai-explore` before overlap analysis.
3. Enrich items with architectural evidence.
4. Deepen ambiguous items with scoped exploration.
5. Write per-item spec and plan files under `.ai-engineering/runs/<run-id>/items/`.
6. Build overlap matrix and dependency DAG.
7. Execute through `ai-build`.
8. Review and verify each item.
9. Promote locally into the delivery surface.
10. Review and verify the integrated result.
11. Delegate final PR delivery to `ai-pr`.
12. Resume from manifest state if interrupted.

## Serialize-on-Uncertainty Rule

If any of the following are uncertain, do not parallelize:

- file ownership
- hidden coupling
- migration ordering
- shared config impact
- generated artifact impact
- lockfile impact

Correct serialization is better than speculative parallelism.
