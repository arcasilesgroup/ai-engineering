# Changelog

Rule 4 of `AGENTS.md`: there are no compatibility shims here, so every hard rename and
every hard delete is written down in this file, in the words somebody upgrading would
search for.

## 1.0.0 — 2026-08-10

### Breaking changes

- Events buffered in `.ai/events.jsonl` carry a `stamp`: an HMAC over the event, made with
  a key written 0600 to `~/.ai-engineering/buffer.key`, outside every clone. The flush at
  the end of a session checks it, and a line that does not carry this machine's stamp —
  edited, truncated, or no longer JSON — is sealed into the chain as an `error` reading
  `outcome: edited`, with whatever the line claimed kept beside it under `claimed`, and
  `ai-eng audit verify` names that link and exits 1. It used to be hashed in as genuine, so
  an agent that had just been blocked could rewrite its own denial into an allow and the
  chain still reported intact. The bound, stated plainly: the key is a file readable by
  anything running as you, so this detects a buffer edited by something that did not read
  it and raises the bar against nothing that did — the git anchors are what defend the
  chain against a writer already inside your account. A buffer written before this change
  seals as edited on the first flush after upgrading, and so does every unflushed line if
  that key file is deleted: end your sessions before you upgrade.

- Every verb now writes UTF-8 with replacement rather than whatever encoding the shell
  handed it. On Windows a bare `print()` gets a cp1252 stream, and the tick in `ai-eng spec
  new`'s success line is not in cp1252, so that verb ended in a `UnicodeEncodeError`
  traceback with the spec already written — work done, crash reported. The styled screens
  were never affected, which is why this survived every local run.

- The `.github/workflows/check.yml` that `ai-eng init` writes gets `just` with
  `uv tool install rust-just` instead of the `extractions/setup-just` action. A repository
  that restricts which actions may run — GitHub's "allow select actions" — never starts a
  workflow naming one outside its list, and the failure has no job and no log to read. The
  uv this file already sets up is enough. Nothing changes for a repository that allows all
  actions; re-run `ai-eng init --project` to take the new file, or delete the one line.

- The dated backup `ai-eng init` writes before it overwrites one of your files now lands in
  `.ai/backups/` instead of beside the original. At the repository root nothing ignored
  those files, no verb removed them and `git add -A` committed them; the managed
  `.ai/.gitignore` ignores everything under `.ai/` and a `.gitignore` cannot reach out of
  its own directory, so the file moved rather than the ignore widening. `uninstall` touches
  nothing under `.ai/`, so the recovery path still outlives the framework. Backups written
  before this change stay where they are and are still yours to delete.

- `ai-eng doctor --fix` no longer runs `ai-eng update`. Assertion 12 still names that
  command when the wheel and the pin disagree, and still prints it, but `--fix` runs its
  cures with nobody in front of them and `update` asks for a typed `y` before it migrates:
  at a terminal the repair stopped in the middle and waited for a keystroke, and with no
  keyboard `update`'s own refusal exited 1, took the rest of the repair with it and skipped
  the second diagnosis. Whether the pin moves is a person's decision, which is what that
  question is for. Run `ai-eng update` yourself; `--fix` now counts assertion 12 under
  "needs a person" instead of under "fixable now".

- A JSON file this tool has to read and cannot parse now stops the verb with the file
  named and exit 2, where it used to be read as an empty document. Two things were losing
  data behind that: `wiring.record` read the install receipt, appended and wrote, so one
  interrupted write emptied the record of every file this tool had installed; and the
  settings writers read, merged and wrote back, so a `~/.claude/settings.json` carrying a
  `//` comment — which VS Code and Cursor write as a matter of course — was replaced by our
  hooks block alone. A file that is simply absent still reads as empty. If a verb now
  refuses, the named file is unparseable and nothing was written.

- `ai-eng uninstall` removes the skills store at `~/.ai-engineering/skills`, prints one
  line per row in the receipt including the reason for anything it keeps, and retracts what
  it removed from the receipt. It used to list every row, ask "Remove them?", and run a loop
  with branches for two of the five kinds — so the store and every repository row survived
  with no line printed, and the record still claimed all of them afterwards. It exits 1 when
  it could not change a file, instead of 0.

- `ai-eng uninstall --project` no longer touches repositories other than the one you are
  standing in. It compared recorded paths by string prefix, so `~/repos/app` reached
  `~/repos/app-backup`. Repositories in the receipt that are not this one are named with the
  command to run inside each.

- `ai-eng update` rewrites the guard entries the receipt records as chosen, not every
  surface it can detect, and records what it writes. Declining a surface at `ai-eng init`
  and running `update` later used to wire it — Cursor with `failClosed: true` — with no
  receipt row, so `uninstall` could not find it afterwards. On a machine with no recorded
  guard entry, `update` now writes none and names `ai-eng init --global`.

- `ai-eng init --project` no longer rewrites `.ai/config.toml` or `.ai/.gitignore`. It
  writes them when they are absent, says on its own line which one it left alone, and
  names `ai-eng update` as the only verb that changes the pin. It used to rewrite both on
  every run — taking a dated backup and printing a line — which reset the pinned version,
  the guard windows and the observability endpoint on every re-run, and made `ai-eng
  update`'s three consent gates reachable around. If you were re-running `init` to refresh
  the pin, run `ai-eng update`: it refuses on a dirty tree, refuses without a keyboard, and
  asks for a typed `y`.

- `ai-eng init` no longer prints `.github/workflows/check.yml` at you to paste. It writes
  the file, which means it is offered for overwrite like the other four when one is already
  there, and it lands in the receipt, so `ai-eng uninstall` removes the one we wrote and
  leaves the one you wrote. There is no flag to get the old paste-it-yourself behaviour
  back.

- `ai-eng accept` now requires `--by` and `--justification`. It used to write
  `TODO: a person, by name` and `TODO: why this is acceptable, in one sentence` into the
  record when they were omitted, and assertion 16 compared only the expiry date — so an
  accepted risk with no owner and no reason passed every gate this product has. An
  omitted `--follow-up` is now an empty field rather than a third marker. There is no
  shim and no deprecation period: the command exits 2 and names the four flags it needs.

- What makes a hook entry ours is now the dispatcher's own filename, `chain.py`, and no
  longer the hyphenated project name. The old mark could only reach an entry through the
  interpreter's path, which spells this package with an underscore under a wheel, so it
  worked under `uv tool` and `pipx` and was false everywhere at once under `pip` into a
  venv named anything else. If you installed that way, `ai-eng init` has been writing a
  duplicate guard entry on every run and `ai-eng uninstall` has been leaving your guards
  wired; run `ai-eng init --global --no-project` once after upgrading and both stop. There
  is no dual-marker fallback: entries written before 1.0.0 are recognised by the new
  signature because the dispatcher's path was always in them.

- `ai-eng spec new --ref` no longer prefills the spec. The flag still records the work
  item in the frontmatter and `/ai-ship` still closes it, but the heading is the slug and
  the problem statement is the author's to write. Nothing fetches the work item any more.
