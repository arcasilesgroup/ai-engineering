---
"ai-engineering": minor
---

`ai-eng <command> --help` now answers about that command — its usage, its flags and the one thing the flags cannot say — and `ai-eng --help` groups the verbs under two headers, for people and for hooks, CI and agents, with a closing line on how to ask for one verb's help; every claim in that text now matches the command it describes, so `--surface` describes the flag instead of listing hosts and `--ci` names the providers the binary accepts, both read from the constant that validates them; and `.ai-engineering/reviews/` now ignores itself through a file ai-eng owns, so a repo governed before a review report could land there commits nothing from that folder on its next update.
