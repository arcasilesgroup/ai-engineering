# Changelog

Rule 4 of `AGENTS.md`: there are no compatibility shims here, so every hard rename and
every hard delete is written down in this file, in the words somebody upgrading would
search for.

## [Unreleased]

### Breaking changes

- `redact` is gone from `[observability]` in `.ai/config.toml`, and the exporter always
  redacts. It accepted `"strict"` and `"none"`, and `"none"` sent every field outside the
  two allow-lists to the collector verbatim — free text, guard reasons, whatever a payload
  happened to carry. A configuration value that disables a privacy control is a control
  whoever runs the exporter can switch off, and nothing downstream could tell a machine
  that had redacted from one that had been told not to. What changes for you: **if your pin
  says `redact = "none"`, that line now does nothing and your exports are redacted.** The
  key is simply ignored rather than rejected, so nothing breaks on upgrade; delete it when
  convenient. Recorded as D-014-08 in `specs/014-security-baseline-no-false-pass`.

- `policy/surfaces.toml` has no `proven` column. It was a field somebody typed, and
  OpenCode's row said `true` with no denial ever executed there — so `ai-eng doctor`'s
  coverage line printed "a denial has executed here" on the strength of it. The word is now
  read from that surface's enforcement receipt under `.ai/receipts/surface`, and the table
  has no way to assert it. What changes for you: **every surface that can deny reads
  `UNPROVEN` until a denial is receipted on it**, including ones that deny perfectly
  well today. The two instruction-only surfaces still read `ADVISES`, which is what
  they always were. Nothing lost a
  capability; the claim lost its evidence. A repository carrying a hand-written
  `surfaces.toml` with that field keeps working — the field is ignored, and it is ignored
  rather than honoured on purpose.

- The repository owner delegated approval of this wave's records, in the session that
  closed P0, in these words: "Cierra el P0 automáticamente rellenando tú lo que haga falta.
  Arregla eso también porque debe ser siempre automático." Recorded here because MADRs
  0005, 0006 and 0007 name this entry as the reference for their approval, and an approval
  reference that points at nothing a reader can open is not a reference. The role recorded
  in those three records is `repository owner`; no model supplied it, and the schema refuses
  a role that names an agent or a reviewer for exactly that reason.

- The guard that used to be `hooks/design_gate.py` is now `hooks/change_scope_guard.py`.
  Nothing answers to the old path: if you referred to it in a settings file, a script or a
  document, that line now points at a file that is not there, and a hook whose file is
  missing does not run. The old name said "design" for a check that has never looked at a
  design — it counts how many files a change touches and stops one that has outgrown its
  plan. The name it had sent people looking for a design document that does not exist. The
  operator-facing setting is still spelled `design_budget`, so that one line does not move
  under you; it will be renamed in its own release, and this file will say so.

- `ai-eng plan` is now `ai-eng exception`, and `src/ai_engineering/plan.py` is gone,
  replaced by `src/ai_engineering/exception.py`. The verb never planned anything. It asks a
  person at a keyboard to grant one fifteen-minute bypass of a flow guard, which is an
  exception to the rules and not a plan for anything. It was also the word printed at
  somebody every time a guard denied them, which meant the product's own error messages
  advertised a verb that did something else.

- `ai-eng digest` is now `ai-eng report digest`, and `src/ai_engineering/digest.py` is gone,
  replaced by `src/ai_engineering/report.py`. `ai-eng report issue` joins it. The old verb
  did one thing and had a name that promised a category, and the second thing it was going
  to have to do had nowhere to live.

- `ai-eng decide --adr` is now `ai-eng decide --madr`. It writes the same file in the same
  place. The record it writes is a Structured MADR — a specific documented format with
  required fields — and calling the flag `--adr` invited the loose kind, which is prose
  with a heading. There is no alias: the old spelling is refused, so a script that passes
  it stops rather than silently deciding nothing.

- An accepted risk is no longer a block of text inside a spec. It is published as one file
  at `specs/NNN-slug/acceptance-r-NNN-NN/record.json`, created by a rename that fails if
  something is already there, and never rewritten afterwards. `spec.md` is not opened for
  writing at all any more. The blocks written by earlier versions are still read, exactly as
  they were written, and are never altered in place: renewing one publishes a new record and
  leaves the old text alone. What changed for you: accepting a risk no longer edits a file
  you are also editing, and two acceptances racing each other can no longer overwrite one
  another, because the second rename loses instead of winning.

- `ai-eng doctor` reports the eight production-ready boxes and how old the proof of each
  one is. It reads a declaration you commit at `.ai/readiness.json` and one receipt per box
  under `.ai/receipts`, and a box with no receipt, a stale receipt or a receipt that does not
  match what you declared reads `INCOMPLETE` — unproven, which is not the same as passed and
  is never shown as green. The receipts are this machine's and stay ignored; the declaration
  is reviewed, and `ai-eng doctor` fails a repository that has receipts and has not committed
  one. Nothing here is gated on it yet; doctor tells you, and does not decide whether
  anything gets a URL.

- If this repository was set up by an earlier release, its `.ai/.gitignore` ignores
  everything under `.ai/` except three names, and the readiness declaration is not one of
  them — so a declaration written there is dropped by `git add -A` without a word. Add
  `!readiness.json` to `.ai/.gitignore` and commit it. There is no command that does this
  for you: that file is written once when a project is set up and deliberately never
  rewritten, because rewriting it is how a tuned ignore file gets reset under somebody.
  `ai-eng doctor` names the line to add when it finds receipts without a declaration.

- Three things that used to carry on now stop. The installer refuses to write git's
  configuration when the command line tool it is about to point git at cannot be run — a
  wired repository whose hooks resolve to nothing is worse than an unwired one, because it
  looks configured. `ai-eng uninstall` ends `INCOMPLETE` and lists what it could not place,
  instead of exiting 0 with guards still wired. And the release workflow refuses to publish
  a tag whose commit `origin/main` does not contain, so a tag pushed from any branch can no
  longer ship code the default branch never held. This is the direction the whole framework
  fails in: a guard that cannot decide fails closed, and only telemetry fails open.

- `ai-eng doctor` and the installer now run their own command line tool with `PYTHONSAFEPATH`
  set. Without it, Python puts the current directory at the front of its import path, so a
  repository that happens to contain a folder named `ai_engineering` had *its* copy executed
  by the check that was supposed to be diagnosing it — and could print whatever answer it
  liked. If you keep a package by that name in a repository, the diagnosis now reads the
  installed product instead of yours.

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

- `ai-eng doctor` assertion 9 reports "could not evaluate" instead of a failure when the
  adversarial suite's real-model half has never run on this machine, and still fails when
  it ran and the result is more than seven days old. Never run and gone stale are different
  answers and it gave the second for both — and nothing on a runner or a fresh machine can
  write that field, because that half needs an API key and somebody's spend, which is a
  risk this repository accepted and dated. So `ai-eng doctor --ci` could not pass anywhere,
  which is what the first CI run on this branch reported. Not evaluated is still never
  green: it is printed, counted separately, and says what it could not ask.

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
