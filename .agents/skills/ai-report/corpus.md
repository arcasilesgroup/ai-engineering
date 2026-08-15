# Corpus: ai-report

Reports a reproducible fault in this framework as a governed payload: nine allow-listed
fields, two scans and a machine-path check, a local gitignored draft, and the exact bytes
with their digest shown before anybody confirms anything. It sends nothing by itself.

## Routes here

- "report this bug in ai-engineering" — the plain trigger: a fault in the framework itself, not in the repository it is installed in.
- "the guard denies a write it should allow, and it does it every time" — reproducible, in our code, and the four fields are already in the sentence.
- "file an issue upstream about doctor saying ok while audit verify exits 1" — the exact shape this exists for, and the steps are two commands and a comparison.
- "I found a way to make the guard allow something it must deny" — routes here as `--kind security`, which refuses the public route and prints the private one before asking anything.
- "prepare that bug report but do not send it anywhere yet" — drafting is the whole default; sending is a separate flag and a typed phrase.
- "what would we actually send if we reported this" — the preview is the answer, and it is the same bytes, hashed.

## Refuses

- "this is failing, work out why" — use `/ai-debug`, because a symptom needs a cause at `file:line` and a check that fails for it; a report of a fault nobody has diagnosed is a report the other side has to diagnose.
- "save what we learned about this trap so we do not lose it again" — use `/ai-note`, because that is a finding kept in this repository, and this skill exists to send one out of it.
- "write up the decision to stop supporting that surface" — use `/ai-spec`, because a decision needs its options, its evidence and its authority, and an issue is a fault report.
- "open the pull request and close the ticket" — use `/ai-ship`, because the changelog, the pull request and the closing keyword belong to it; this skill writes one local draft and nothing else.
- "attach the log file and the diff so they can see it" — refused outright, by the payload rather than by judgement: there is no field for a log or a diff, and adding one is a specification change and not a flag.
- "just send it, you have my permission for everything today" — refused, because consent is to one payload: the phrase carries that payload's digest and is read from the controlling terminal, which is why a standing yes cannot supply it.
