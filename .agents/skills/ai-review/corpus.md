# Corpus: ai-review

Judges a diff the way a staff engineer would: does it do what it claims, is it correct at its
boundaries, is it safe, is it tested, and is there a smaller version of it. It never claims
the result of a mechanical gate, because those ran in CI, and it says so.

## Routes here

- "review this" — a diff exists and somebody wants a judgement on it, each finding at `file:line` with the smallest change that resolves it.
- "is this PR safe to merge" — the question is whether the change is correct, safe and tested, and the answer separates what blocks from what does not.
- "any issues with this before I open it" — same judgement, asked earlier, and the spec and plan get read first because half of all real findings are "this is not what was agreed".
- "what would you change here" — an invitation to look for the smaller version of the change, not to rewrite it.
- "does this break anybody still on the old version" — the compatibility lens: shipped signatures, output shapes, config keys and data written by the old version.
- "is there anything unsafe in this diff" — the security lens, which files a finding only when it can name the source, the sink and the missing control.
- "we added this without tests, is that a problem" — the testing lens; a check that fails without the change either exists or the change is untested whatever coverage says.

- "is this the right call, we ranked it with RICE" — judge the decision against its named framework and say which one before the verdict, so the ranking is the argument.

## Refuses

- "we ranked by impact and picked this, just review it" — use `/ai-spec`, because a ranking with no named method is a decision without its authority, and a review is not where a decision gets made.

- "CI is failing on this branch, find out why" — use `/ai-debug`, because that is a failure with a cause to name at `file:line`, not a diff to judge.
- "this used to work last week and now it doesn't" — use `/ai-debug`, whose first step is reproducing it and whose output is a check that fails for that reason.
- "run the repo's gate and tell me whether it's green" — use `/ai-ship`, which runs the gate and shows its output; this skill never stands in for a gate it did not see.
- "looks good, commit it and open the PR" — use `/ai-ship`, because landing the work is commits, a changelog entry, a pull request and a closed work item, not a judgement.
- "the review shows the whole approach is wrong, redesign it" — use `/ai-spec`, because that is a decision with options and authority behind it, and this skill is not a rewrite.
- "where is this function called from" — use `/ai-explore`, because reading the repository to answer a question is its job, and this skill only reads the diff and what surrounds it.
- "a finding claims a version of a dependency that contradicts what is installed" — `versions.verify_against_installed` decides: a contradicting claim is dropped or marked `unverified`, never trusted from memory.
