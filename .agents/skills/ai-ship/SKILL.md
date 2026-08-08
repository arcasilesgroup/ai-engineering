---
name: ai-ship
description: >-
  Lands the work: one commit per change, the changelog entry, a pull request that opens
  with what changed in plain words, the production-ready boxes ticked with the command that
  ticked each, the work item closed by a keyword in the body, and the branch cleaned up
  afterwards. Trigger for "ship it", "open a PR", "I'm ready for review", "commit this",
  "merge it". Not for judging the diff — use /ai-review first. Not for writing the spec —
  use /ai-spec. Not for finding the bug — use /ai-debug.
license: Apache-2.0
compatibility: needs git; needs gh for the pull request
disable-model-invocation: true
---

# Land the work

## What it produces

Commits, a changelog entry, a pull request, and a branch that gets deleted after it merges.

## Steps

1. Run `just check` and show its output. Not a summary of it — the output. If it is red,
   stop here; nothing below this line is worth doing.
2. Commit in the shape the change actually has: one commit, one change. A commit that
   needs the word "and" in its subject is two commits. Subject is
   `<type>(<scope>): <what changed>`, imperative, and the body says why rather than what.
   Never `--no-verify`: the hooks are the floor, and what they would have said is the thing
   that needs fixing.
3. Update the changelog. A breaking change is written as a breaking change, in the words
   somebody upgrading would search for.
4. Tick the production-ready boxes in the spec, and beside each one write the command that
   proves it. A box ticked without a command is the failure this whole framework exists to
   catch, committed by us.
5. Open the pull request. The first paragraph is what changed, in plain words, for somebody
   who does not code. Then the spec link, then what to look at first, then what you are not
   confident about — that last section is the one reviewers use most.
6. If the spec's frontmatter has a `ref`, append the closing keyword to the body:
   `Closes owner/repo#45` on GitHub, `Fixes #45` on Azure Repos, `AB#45` where the Azure
   Boards app bridges the two. One constraint catches people: the pull request must target
   the default branch, or the keyword is ignored and nothing is linked or closed.
7. After it merges, delete the branch, and say in one line what is now true that was not
   true before.

## Done when

- The gate is green and its output is in the conversation.
- The pull request explains itself to somebody who was not here.
- Every production-ready box is ticked, each beside the command that ticked it.

## What this is not

Not a place to fix review findings quietly. A finding gets its own commit, with its own
message, so the diff of the fix can be read on its own.
