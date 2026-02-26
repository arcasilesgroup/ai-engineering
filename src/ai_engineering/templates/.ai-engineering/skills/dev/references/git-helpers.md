# Git Helpers

On-demand reference for git operations, branch management, and merge strategies.

## Branch Management

### Protected Branch Detection

```bash
# Get default branch name
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'
# Fallback: check for main or master
git branch -r | grep -qE 'origin/(main|master)$'
```

### Safe Branch Deletion

```bash
# Local: safe delete (fails if not fully merged)
git branch -d <branch>

# Local: force delete (only when remote tracking is gone)
git branch -D <branch>

# Remote: explicit targeting
git push origin --delete <branch>
```

### Branch Cleanup

```bash
# Prune remote tracking branches
git fetch --prune

# List merged branches (safe to delete)
git branch --merged main | grep -v 'main\|master\|\*'

# List branches with no remote tracking
git branch -vv | grep ': gone]' | awk '{print $1}'
```

## Worktree Operations

```bash
# Create worktree for parallel work
git worktree add ../<name> -b <branch>

# List worktrees
git worktree list

# Remove worktree after work is done
git worktree remove ../<name>
```

## Merge Strategies

| Strategy | When | Command |
|----------|------|---------|
| Squash merge | Feature branches to main | `git merge --squash <branch>` |
| Rebase | Keep linear history | `git rebase main` |
| Merge commit | Preserve branch history | `git merge --no-ff <branch>` |
| Fast-forward | Simple, clean updates | `git merge --ff-only <branch>` |

### Conflict Resolution

- Prefer resolving conflicts over discarding changes.
- Use `git mergetool` or IDE merge resolution.
- After resolving: `git add <resolved-files>` → `git rebase --continue` or `git merge --continue`.
- Never use `git checkout --theirs .` or `git checkout --ours .` without understanding impact.

## Commit Conventions

### Message Format

```
spec-NNN: Task X.Y — <description>

<optional body explaining why, not what>

Co-Authored-By: <name> <email>
```

### Staging Best Practices

- Stage specific files: `git add <file1> <file2>`.
- Avoid `git add -A` or `git add .` (may include sensitive files).
- Interactive staging for partial changes: `git add -p <file>`.
- Review staged changes before commit: `git diff --cached`.

## Pre-Commit Validation

```bash
# Check for unstaged changes
git diff --quiet || echo "Unstaged changes exist"

# Check for staged changes
git diff --cached --quiet && echo "Nothing staged"

# Verify clean worktree
git status --porcelain | wc -l  # 0 = clean
```

## Remote Operations

```bash
# Update tracking and prune
git fetch --all --prune

# Check if branch is up to date with remote
git status -sb  # Shows ahead/behind count

# Push new branch with tracking
git push -u origin <branch>
```

## Stashing

```bash
# Stash with description
git stash push -m "WIP: description"

# List stashes
git stash list

# Apply and drop most recent
git stash pop

# Apply specific stash
git stash apply stash@{2}
```
