# Handler: docs-portal

## Purpose

Update an external documentation portal (separate repository or local directory) with project documentation changes. Handles both local paths and remote URLs, creates PRs or pushes directly based on configuration.

## Pre-conditions

1. Read `.ai-engineering/manifest.yml` -- check `documentation.external_portal`.
2. If `enabled: false`, skip silently and report "external portal disabled".
3. If `enabled: true`, read `source` (local path or remote URL) and `update_method` ("pr" or "push").

## Procedure

### 1. Determine source type

- **Local path**: `source` starts with `/`, `./`, `../`, or `~`
- **Remote URL**: `source` starts with `https://` or `git@`

### 2. Local path flow

1. Verify the directory exists and is a git repository
2. Detect default branch: `git -C <path> symbolic-ref refs/remotes/origin/HEAD` (parse branch name from `refs/remotes/origin/<branch>`)
   - Fallback if symbolic-ref fails: `git -C <path> remote show origin | grep 'HEAD branch'`
3. Checkout default branch and pull latest: `git -C <path> checkout <default> && git -C <path> pull`
4. Create feature branch: `git -C <path> checkout -b docs/update-from-<our-branch>-<timestamp>`
5. Copy or update documentation files into the portal directory
6. Commit changes: `git -C <path> add . && git -C <path> commit -m "docs: sync from <project> (<our-branch>)"`
7. Based on `update_method`:
   - **"pr"**: Push branch, create PR using `gh pr create` or `az repos pr create`
   - **"push"**: Push directly to default branch (only if allowed)

### 3. Remote URL flow

1. Clone to a temporary directory: `git clone <url> <temp-dir>`
2. Detect default branch: `git -C <temp-dir> symbolic-ref refs/remotes/origin/HEAD`
   - Fallback: `git -C <temp-dir> remote show origin | grep 'HEAD branch'`
3. Create feature branch: `git -C <temp-dir> checkout -b docs/update-from-<our-branch>-<timestamp>`
4. Copy or update documentation files into the cloned directory
5. Commit changes: `git -C <temp-dir> add . && git -C <temp-dir> commit -m "docs: sync from <project> (<our-branch>)"`
6. Push feature branch: `git -C <temp-dir> push -u origin docs/update-from-<our-branch>-<timestamp>`
7. Create PR: `gh pr create` or `az repos pr create` (detect from remote URL)

### 4. Error handling

**On PR creation failure**:
1. Clean up local branches: delete the feature branch in the external repo
2. Do NOT leave orphaned branches in external repos
3. Add a comment to our PR body noting the failure:
   ```
   > **Docs portal update failed**: Could not create PR in <portal-repo>. Error: <message>.
   > Manual sync required.
   ```

**On success**:
1. Add cross-reference to our PR body:
   ```
   > **Docs portal**: Updated via <portal-repo>#<pr-number>
   ```

### 5. Cleanup

- For remote URL flow: remove the temporary clone directory
- Never leave orphaned branches in external repos

## Output

- PR or push to external documentation portal
- Cross-reference added to source PR body
- Report: portal updated successfully / portal update failed with reason
