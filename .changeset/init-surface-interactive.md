---
"ai-engineering": minor
---

`ai-eng init --surface` now works on its own, on both paths, instead of only on a fresh `--yes` install. On a first install the flag no longer waits for `--yes` to mean anything: the hosts it names start ticked in the picker, so Enter accepts them and `--yes` still takes them as given. On a repo that is already governed, `--surface` naming hosts other than the declared set goes straight to the surface step — ticked with those hosts, or applied without a question when `--yes` is passed — instead of being silently dropped, which is what it did before while `--ci` and `--global` honoured their flags on the same command line. A `--surface` id this release does not know, or one that cannot govern, is refused before any question is asked on either path, so a typo never reaches `.ai-engineering/config.toml`. The help text and the verb note that used to say the flag took effect only with `--yes` on a first install now describe what it does.
