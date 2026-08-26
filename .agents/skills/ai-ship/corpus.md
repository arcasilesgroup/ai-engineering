# Corpus: ai-ship

Lands the work: one commit per change, the changelog entry, a pull request that opens with
what changed in plain words, the production-ready boxes ticked with the command that ticked
each, the work item closed by a keyword in the body, and the branch cleaned up afterwards.

## Routes here

- "ship it" — the work is done and judged, and what is left is commits, changelog, pull request and cleanup.
- "commit this and open a PR" — the commits get the shape the change actually has, one commit per change, and never with the hooks skipped.
- "I'm ready for review" — the pull request opens with what changed in plain words, then the spec link, then what you are least confident about.
- "merge it and close the ticket" — the closing keyword goes in the body, and the pull request has to target the default branch or nothing gets linked or closed.
- "rewrite my README before the release" — use `/ai-write`, because a document written against the tree is not part of landing this change unless it is the changelog, which is.
- "the changelog and the production-ready boxes still need doing before this goes out" — each box is ticked beside the command that ticked it, or it fails the gate.
- "it merged, tidy the branch up" — the branch is deleted and one line says what is now true that was not true before.

## Refuses

- "is this safe to merge?" — use `/ai-review`, because judging the diff happens before landing it, and this skill does not review the change it is committing.
- "the gate is red, push it anyway and we'll fix it after" — use `/ai-debug`, because a red gate is a failure with a cause to name, and this skill stops at the gate rather than landing over it or passing `--no-verify`.
- "fold the review fix into the original commit so the history looks clean" — use `/ai-review`, because a finding gets its own commit so the fix can be read on its own, and whether a finding is worth fixing is that skill's call, not this one's.
- "there's no spec for this, write one into the PR body" — use `/ai-spec`, because the pull request links a decision that already exists; this skill never writes the decision it lands.
- "split what's left into tasks before I commit" — use `/ai-plan`, because a numbered task list with a file, a check and a rollback each is its output, and it needs approval first.
- "CI went red after the merge" — use `/ai-debug`, because the next thing needed is a cause at `file:line`, not another commit.
- "write down the trap we hit while landing this" — use `/ai-note`, because a finding that cost real time belongs in `docs/notes/` with a commit stamp, not in a pull request body.
