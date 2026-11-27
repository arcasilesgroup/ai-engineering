---
"ai-engineering": minor
---

`ai-eng <command> --help` now answers about that command — its usage, its flags and the one thing the flags cannot say — and `ai-eng --help` groups the verbs under two headers, for people and for hooks, CI and agents, with a closing line on how to ask for one verb's help; every claim in that text now matches the command it describes, so `--surface` names only the hosts `init` accepts and `--ci` names `github-actions`, `azure-pipelines` and `none`.
