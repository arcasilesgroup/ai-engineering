# Corpus: ai-note

Saves a finding that took real time to reach — a non-obvious behaviour, an integration trap,
a workaround and the reason it is needed — as committed markdown stamped with the commit and
the files it describes, so it can be detected as stale later. It searches those notes too.

## Routes here

- "save this" — the shortest form of the trigger, and the thirty-minute bar decides whether it is worth a file at all.
- "write down what we learned, that cost us the whole afternoon" — exactly the bar: a finding that will cost the same again if nobody writes it down.
- "note that the settings writer merges instead of replacing, we lost an hour to that" — a non-obvious behaviour, written as what you expected, what happened, and what to do about it.
- "remember this workaround and why we still need it" — a workaround also records what would remove the need for it and where that fix would live.
- "do we have notes on the plugin loader" — searching the notes is part of this skill, and `git grep` over `docs/notes/` is the whole query engine.
- "what did we find about the hook timeout last time" — the same search, and the answer starts by checking the note's `still_true_when` before anybody acts on it.

## Refuses

- "write down the decision and the options we turned down" — use `/ai-spec`, because a decision needs its evidence, its two real options and its authority, and a note is a finding, not a decision.
- "onboard me on this module" — use `/ai-explore`, because that is a tour read out of the repository for somebody who has just arrived, not a warning saved from a lost afternoon.
- "check whether the vendor fixed this in the new release" — use `/ai-research`, because that answer is outside this repository and has to come back cited; a note only records what we already found here.
- "this is failing again, work out why" — use `/ai-debug`, because a symptom needs a cause at `file:line` and a check that fails for it, not a file in `docs/notes/`.
- "open the PR with this note in it and close the ticket" — use `/ai-ship`, because the changelog, the pull request and the closing keyword belong to it; this skill writes and commits the note and nothing else.
- "look over the diff that came out of this investigation" — use `/ai-review`, because judging a change is a separate pass from recording what we learned making it.
