### Autonomous orchestrators must define consolidation, not only execution

**Context**: When proposing an autonomous multi-branch orchestrator, the initial design described issue intake, worker branches, and validation loops but did not explicitly define how changes converge back into a stable branch and then promote safely to `main`.
**Learning**: Parallel execution is incomplete without a consolidation strategy. In autonomous systems, branch topology, integration points, and promotion rules are first-class design concerns, not implementation details.
**Rule**: When designing any autonomous runbook, skill, or agent that fans work out across branches or subagents, always specify the full consolidation path: worker branch/worktree -> integration branch or PR layer -> final promotion PR/merge queue -> protected main branch.

### Baseline exploration must happen before DAG and wave planning

**Context**: In the first `ai-run` orchestration sketch, dependency and wave planning happened before the repository had been explored with `ai-explore`, which would have forced overlap decisions to rely only on issue metadata and assumptions.
**Learning**: Safe parallelism depends on architectural evidence, not just backlog text. Baseline exploration has to precede overlap prediction, dependency classification, and batch sizing.
**Rule**: For any autonomous orchestrator that normalizes multiple work items, always run a repository-wide baseline exploration before item enrichment, DAG construction, or wave assignment.
