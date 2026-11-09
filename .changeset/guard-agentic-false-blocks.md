---
"ai-engineering": patch
---

The guards stop blocking everyday agent commands for reasons that were not true.

- The word `ai-engineering` (the repo slug, a checkout folder, the npm package) no longer counts as the `ai-eng` binary. It still counts when it is the command itself, or when a runner such as `npx`, `bunx` or `bun` starts it.
- `2>&1` is no longer read as a write to a file.
- `git -C <repo>` is a working folder, like `cd`.
- The text of `gh pr`, `gh issue` and `gh release` (titles, bodies, comments) is prose, not code.
- The command-scope policy no longer reads `/usr/bin/git` or a `NAME=value` prefix as a system write.

What the guards protected before is still protected, and some gaps are closed too:

- `npx ai-engineering@<version> uninstall` is blocked.
- So is the package fed to a runner through `xargs`.
- So is a command stored in `gh config set editor|pager|browser` or in `GH_BROWSER`, `GH_EDITOR` or `GH_PAGER`.
- So is a write hidden after a `$(…)`, a shell keyword or a redirect glued to `2>&1`.

A heredoc's lines are still judged as commands, whoever reads them. To pass a commit message or a PR body that names system paths, write it to a file first (`git commit -F <file>`, `gh pr create --body-file <file>`).
