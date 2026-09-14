---
"ai-engineering": minor
---

A gate whose check prints nothing is no longer ticked: `test -f X` and `ls X >/dev/null` exit 0 while saying nothing, so the box rested on an exit code and the ledger carried the silence as evidence. The executor now leaves such a gate UNMET and writes the remedy into its `EVIDENCE` line, and `templates/spec.html.tpl` + the ai-proof canon teach the alternative in place of the existence probe they used to show.

What an existing install will notice: a milestone that already had gates of this shape reports them UNMET on the next `ai-eng spec run`. The fix is one line per gate — make the check print what it found (`test -f X && echo "X $(wc -c < X) bytes"`), or assert its output with `EXPECT: <text|/regex/>`. Nothing is unticked by the tool: the box stays as its author set it and the evidence is what stops counting, which is the same rule the executor already applied to a check that fails.
