# Manual Branch Policy Setup (Azure DevOps)

1. Open Repos -> Branches -> `main` -> Branch policies.
2. Enable minimum reviewers policy.
3. Add build validation checks: `ci`, `ai-pr-review`, `ai-eng-gate`.
4. Block direct pushes to protected branch.
