---
name: ai-pr
description: >-
  Open or finish a pull request from the current branch in the current checkout
  or selected worktree. Detect the target branch without assuming a forge or
  branch name, keep the published diff explicit, watch checks and review, and
  merge only when the request says to finish, land, or merge.
license: Apache-2.0
---

# ai-pr — publish the current branch safely

Run this skill only when the person asks for a pull request. It publishes the
current branch from its current checkout or selected worktree; it does not move
work to another checkout or branch. Read `AGENTS.md` and `CONTRIBUTING.md` for
local branch, title, and changeset rules.

## The ask

- **Open only** means open the pull request, create it, and stop with no merge.
- **Finish**, **land**, or **merge** means run the whole loop through merge.
- If the wording is ambiguous, open only. A green check is not the person's request to merge.
- Invoking this skill with a finish verb is the person's request to finish the PR.
  Never merge merely because checks passed; merge only on the human's explicit request.
- Other branches and optional artifacts do not block this flow. A dirty current
  checkout does: name its changed paths and stop rather than publishing an
  uncertain diff.

## Resolve the base

Read sources in this order; keep the first valid result:

1. An explicit base ref or branch supplied by the person.
2. `[git] base` in `.ai-engineering/config.toml`.
3. The default remote branch from
   `git symbolic-ref --quiet refs/remotes/<remote>/HEAD`, using the current
   branch's upstream remote or `origin`.
4. Only when opening a PR, ask the forge: `gh repo view --json defaultBranchRef`
   or `az repos show --query defaultBranch`.
5. If none resolves, ask once and offer to save the answer in `[git] base`.

Keep the selected Git revision as `$base_ref` for comparisons. Resolve the
forge target separately as `$base_branch`, a short branch name: strip
`refs/remotes/<remote>/` (or its `<remote>/` prefix) from a remote-tracking
ref, strip `refs/heads/` from a local full ref, and keep an already-short
branch name. Never pass a full ref or remote prefix as a forge target.

A repository without a remote cannot publish a PR: offer a local merge or ask
once. If the selected base equals the current branch, ask once for a different
base; do not create a self-targeting PR.

## Check and publish

Resolve the current branch and remote, then inspect the clean status and exact
commits before publishing. Fetch the selected remote and compare the selected
base to the current tip; uncommitted changes are never included or committed by
this skill. Show the person the proposed base, branch, title, and commit list.
Stop if the branch is detached, the diff is empty, the remote moved unexpectedly,
or the person has not asked to publish.

```bash
git status --porcelain
git fetch "$remote"
git log --merges --oneline "$base_ref"..HEAD
git diff --stat "$base_ref"..HEAD
```

Build the PR body from the merge commits the branch carries, in order, and include
the checkpoint evidence and any deferred decision. Never paste secrets or
credential-bearing output. Check for an open PR on this branch before creating:
reuse its number and skip creation; only the provider's explicit no-result means
none exists. Any other read failure is reported and stops the run.

```bash
gh pr view "$branch" --json number,state
az repos pr list --source-branch "$branch" --status active --output json
```

Only in this explicitly requested PR flow, push the selected source branch to
the selected remote before creating a PR. This publishes a local-only branch
without pushing as a side effect of another task. Use a normal, non-force push,
then verify the remote branch tip matches local `HEAD`; stop on a push failure,
missing ref, or mismatch. With no remote, do not push or create a PR; retain
the local-merge-or-ask path above.

```bash
git push "$remote" "$branch"
git rev-parse HEAD
git ls-remote --heads "$remote" "refs/heads/$branch"
```

Compare the `git rev-parse HEAD` commit with the hash returned by
`git ls-remote` before either create command.

Create a PR with the normalized branch name, never a literal target:

```bash
gh pr create --base "$base_branch" --head "$branch" --title "$title" --body-file "$body_file"
az repos pr create --target-branch "$base_branch" --source-branch "$branch" --title "$title" --description "$body"
```

After creation, read back its number and state. A rerun reuses the same open PR;
it never creates a second one for the same branch.

## Watch and fix

Read required checks from branch protection, not from a guessed list:

```bash
gh api "repos/{owner}/{repo}/branches/<base_branch>/protection" --jq '.required_status_checks.contexts'
gh pr checks "$number" --required
gh pr view "$number" --json reviewDecision,reviews
gh pr view "$number" --comments
gh run list --branch "$branch" --limit 1 --json databaseId,status,conclusion
```

The required contexts block; other workflows and checks are advisory and only
inform. Read review states and comments on every poll. `REVIEW_REQUIRED`,
`CHANGES_REQUESTED`, or a blocking comment stops the loop. Poll every 30 seconds,
up to 30 minutes. Exit 8 from `gh pr checks` means pending; other failed reads
are errors, not passing checks. At the time limit, report the check and its last
state and stop.

Fix only obvious mechanical failures (formatting, lint, import, or type errors).
Report logic, test-expectation, flaky, and infrastructure failures without
guessing. Make the smallest fix, commit it, push the current branch, and watch
again. The cap is **5 iterations**; when reached, stop and report the last state.
Do not delete remote branches, force-push, edit tests to silence a failure, or
run the whole suite locally to replace CI.

## Merge only when asked

Select a supported merge method from the forge's allowed methods; prefer merge
commit, then squash, then rebase. Never guess a method the repository disallows.
For GitHub, read the allowed methods and arm auto-merge by default:

```bash
gh api "repos/{owner}/{repo}" --jq '{squash:.allow_squash_merge,merge:.allow_merge_commit,rebase:.allow_rebase_merge}'
gh pr merge "$number" --merge --auto
```

The command above illustrates the preferred method; use the supported method
selected from the API result. Auto-merge may be disabled when the person wants to
review first (`gh pr merge "$number" --disable-auto`). Azure DevOps uses its PR
completion command only after the same approval and gate checks.

A rejected merge is reported with the forge's message; leave the PR open and
never retry blindly. After a successful request to merge, wait for the provider
to report `MERGED` before reporting completion. Keep the current checkout and
branch; this skill does not level another checkout.

## Lifecycle

Lane: light
Writes: nothing
Read by: the person who asked for the pull request
Dies: on completion
Next: none
