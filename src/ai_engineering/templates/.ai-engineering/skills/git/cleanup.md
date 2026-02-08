# Git Cleanup Skill

## Purpose

Identify and safely clean stale or merged branches in local and remote repositories.

## Default Mode

- Always run in preview mode first.
- Apply deletions only after explicit confirmation.

## Command

```bash
ai git cleanup --remote
```

Apply mode:

```bash
ai git cleanup --apply --remote
```

## Behavior

- fetch and prune remotes,
- detect default branch,
- list local merged branches eligible for deletion,
- list local branches whose upstream is gone,
- optionally list remote merged branches eligible for deletion,
- preserve protected/compliance branches,
- write cleanup report to `.ai-engineering/state/branch-cleanup-report.json`.

## Safety Rules

- never delete protected branches,
- never force delete by default,
- never use force push,
- emit audit events for preview and apply runs.

## Expected Output

- machine-readable JSON report,
- candidate branches by category,
- deleted branches summary when apply mode is used,
- explicit errors for branches that cannot be deleted.
