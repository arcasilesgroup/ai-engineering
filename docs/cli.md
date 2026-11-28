# CLI

Every `ai-eng` verb, by who runs it. The lanes have their own page: [lanes.md](lanes.md).

`ai-eng --help` lists the verbs in two groups. `ai-eng <command> --help` prints that verb's own
usage, its flags and the one thing the flags cannot say; the global menu is only the answer when no
verb was named.

Six commands for people:

```bash
ai-eng init        # install the contract here (--global: this machine only)
ai-eng doctor      # run every check, plus one real attack payload
ai-eng config      # change the surfaces or the CI provider
ai-eng update      # install a newer version if you agree, then sync this repo
ai-eng work        # list the lanes; tidy, park or drop one
ai-eng uninstall   # remove everything it installed, keep your files
```

Four commands for hooks, CI and agents:

```bash
echo "$PAYLOAD" | ai-eng chain PreToolUse   # judge one tool call: JSON in, JSON out
ai-eng git pre-commit                       # the pre-commit, commit-msg and pre-push checks
ai-eng wrap test --base64 <encoded command> # run tests, print only the failures
ai-eng worktree new <branch>                # start a lane checkout (also: list, merge, rm, request-changes)
```

Only the `wrap` guard writes its form: it encodes a recognised test command and hands the agent
`ai-eng wrap test --base64 <encoded test command>`, which runs the real runner and prints the
failures. The encoded form is the whole command as one shell-safe token, so nothing is re-quoted and
nothing is escaped twice.
