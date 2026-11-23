# CLI

Every `ai-eng` verb, by who runs it. The lanes have their own page: [lanes.md](lanes.md).

Six commands for people:

```bash
ai-eng init        # install the contract here (--global: this machine only)
ai-eng doctor      # run every check, plus one real attack payload
ai-eng config      # change the surfaces or the CI provider
ai-eng update      # install a newer version if you agree, then sync this repo
ai-eng work        # list the lanes; tidy, park or drop one
ai-eng uninstall   # remove everything it installed, keep your files
```

Five commands for hooks, CI and agents:

```bash
echo "$PAYLOAD" | ai-eng chain PreToolUse   # judge one tool call: JSON in, JSON out
ai-eng git pre-commit                       # the pre-commit, commit-msg and pre-push checks
ai-eng wrap test -- <command>               # run tests, print only the failures
ai-eng worktree new <branch>                # start a lane checkout (also: list, merge, rm, request-changes)
ai-eng findings check <rounds.json|->       # annotate the review findings a program can disprove
```

### Reading a findings check

`ai-eng findings check` reads one run's review rounds (`no-mistakes axi rounds --step review --json`,
or a `{findings: […]}` file with `--base` and `--head`) and prints one count line (followed by any
annotations): how many findings the round produced, how many carry a signal, how many are clean, and
— of the annotated ones — how many were selected for fixing in that round or a later one. An
annotation means the evidence for that signal was found and is printed under the finding; it is a
note attached to a finding, not a verdict about it, and it never removes one. It does not mean the
finding is wrong — no signal here is provably false on its own, and real findings trip all of them —
it does not mean the reviewer was careless, and it is not a gate, because the verb exits 0 with a
hit. Read it as "a check against the diff or earlier rounds matched, and here is where it looked",
then judge the finding exactly as you would without it.
