---
id: "008"
slug: the-receipt-that-only-grows
status: shipped
date: 2026-08-09
ref: ""
supersedes: ""
---

# The receipt that only grows, and the machine that says it is ready

## Context and problem

The operator ran `ai-eng uninstall`, answered `y`, and then ran `ai-eng init`. The second
command printed this:

```
◇ Global   ready · v1.0.0
   skills      8  /Users/soydachi/.ai-engineering/skills
   links       4  one skills root per surface found
   guards      4  one entry in each surface's own settings file
   receipt        /Users/soydachi/.ai-engineering/machine.json
  Project ready — .ai/config.toml, spec chain wired

  Nothing to do. `ai-eng doctor` for the full check.
```

Measured on that machine at that moment: **zero** guard entries — the string `chain.py`
appears zero times in `~/.claude/settings.json`, `~/.codex/hooks.json` and
`~/.copilot/hooks/ai-eng.json`, and `~/.config/opencode/plugins/ai-engineering.ts` does not
exist. **Zero** of our symlinks in all four skills roots. The eight skills in the store are
real, and they are the only true number on that screen.

So the install verb reported a wired machine over a machine with no guards on it, and then
declined to do anything about it. That is the failure this product exists to refuse, in the
two verbs that are its promise: `uninstall` is the no-lock-in claim as a command, and `init`
is the first screen anybody sees.

It is one cause with four faces.

**The receipt cannot shrink.** `wiring.record` deduplicates by `(path, kind)` and appends;
there is no retraction. `uninstall.py` contains no write to `machine.json` at all. After a
full, successful uninstall the receipt still listed all thirty-two rows, unchanged.

**`init` reads that log as the state of the machine.** `global_ready()` is
`bool(data.get("wrote")) and data.get("version") == __version__` — the receipt is non-empty
and the version matches, therefore ready. Nothing on the disk is consulted. And because only
`--global` forces past that gate, a plain `ai-eng init` can never repair a machine in this
state: the verb whose job is to install has been told there is nothing to install.

**The numbers on that screen come from two different places, and the docstring says
otherwise.** `already()` counts skills by globbing the store on disk, and counts links and
guards with `Counter(row["kind"] for row in data["wrote"])` — the receipt. Its docstring,
written in spec 007, says *"Every number here is now counted from what is on the disk."* That
is true of one number in three. Spec 007 was closed as shipped with that sentence in it.

**`uninstall` takes consent for work it does not do.** It prints every row in the receipt
under `32 things were written by this install, and every one is listed here`, asks
`Remove them?`, and then runs a loop with branches for `kind == "guard"` and `kind == "link"`
and no branch for anything else. Nineteen `project` rows, four `repo` rows and one `skills`
row fell through: no `✓`, no `→ kept`, no line at all. The project half needs `--project`, and
even with the flag it reaches `paths.repo_root()` — the repository you happen to be standing
in — while the receipt listed four different repositories.

**And `doctor` agrees with the receipt rather than with the disk.** Run against that same
uninstalled machine, assertion 13 — *Every symlink resolves and the doctrine is loaded* —
reports `ok`. It reads the link rows from the receipt and asks whether
`Path(row["path"]).exists()`, which is the skills *root directory*: `~/.claude/skills` still
exists, because it holds skills that belong to the user. Every symlink we put in it was gone.
Eight assertions passed on that machine.

## Five more, found by looking rather than by reading

Reading the verb explained the screen. Running the machine in the state the operator left it
in — uninstalled, guards at zero — turned up five more, and each one below was observed rather
than inferred. The last of them is the one that decides which option this spec takes.

**The coverage block says `BLOCKS` on a machine with no guards.** This is the worst of them,
because that block is the product's headline claim: *where a call can actually be stopped, and
where it cannot*. On the uninstalled machine it printed `T2 claude-code BLOCKS`,
`T2 opencode BLOCKS` and `T2 copilot-cli UNPROVEN installed and wired`. It derives each word
from `wiring.detect()` — whether the vendor's own directory exists — and a static `proven=`
field in `policy/surfaces.toml`. It never opens the settings file. So the row says a denial has
executed here, on a surface that has no entry to execute one.

**Assertion 13 passes with every symlink deleted.** *Every symlink resolves and the doctrine is
loaded* reads the link rows from the receipt and asks `Path(row["path"]).exists()` — the skills
root directory. `~/.claude/skills` exists because it holds three skills that belong to the
operator. Ours were gone; the check was green.

**`uninstall --project` can delete files in a repository you are not in.**

```python
mine = [row for row in rows if row["kind"] == "project" and row["path"].startswith(str(root))]
for row in mine:
    Path(row["path"]).unlink(missing_ok=True)
```

`str(root)` carries no trailing separator, so standing in `~/repos/tests` matches every
`project` row under `~/repos/tests-backup`, `~/repos/tests2` and anything else sharing the
prefix, and unlinks them. The operator's receipt happens to hold no such pair today. That is
luck, not a control.

**A receipt nobody can parse is silently a receipt with nothing in it, and the next write makes
that permanent.**

```python
def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
```

Every reader inherits that `ValueError`: `receipt()`, `record()`, assertion 13,
`global_ready()`, `already()`. A file that cannot be read and a file that does not exist give
the same answer, and the answer is "nothing was ever installed". Measured, in a sandbox, on a
receipt holding two project rows and one guard row:

```
before      : 3 rows
after trunc : {}                     <- read_json swallowed ValueError
after record: 1 rows - ['~/.claude/settings.json']
```

One interrupted write, and `record` reads `{}`, appends, and stores it. The two project rows
are gone for good — and those rows are the only thing that tells `uninstall` which `justfile`
this tool wrote and which one the user did. After that the file is neither removed nor
protected, forever, and nothing ever said a word.

And the receipt is not the only file behind that line. `json_claude`, `json_cursor` and
`json_codex` all open with `data = read_json(path)`, mutate, and write back — so a
`~/.claude/settings.json` this tool cannot parse is read as `{}` and **replaced**. Measured:

```
before: {"permissions": {...}, "model": "opus", // a comment somebody added }
after : {"hooks": { … ours, and nothing else … }}
```

The user's permissions and model are gone, from an `ai-eng init` that printed
`✓ guards → ~/.claude/settings.json (merged)`. Three lines above that function the docstring
says *"Foreign entries are preserved: this merges, it never replaces."* A JSONC comment is
enough to trigger it, and comments in that file are ordinary.

This repository has already ruled on exactly this shape, one file over. `text.yaml_blocks`
was changed to raise rather than skip a malformed block, and the reason it gives is the
argument against `read_json` verbatim: *"Silence on a parse failure is the exact shape of a
false green, and this product is sold on not producing them: undecidable is an answer,
invisible is not."* The record verbs got that rule. The install record did not.

`hooks/_emit.machine_id()` sits downstream of the same corruption — it catches bare
`Exception` and writes `{"machine_id": …, "wrote": []}` over the file rather than merging —
but it is a second way to lose the rows, not the cause. Fixing it without fixing `read_json`
leaves the loss reachable through `record` alone.

**And the receipt is wrong in the other direction too.** `ai-eng update` rewrites the guard
entries on every detected surface — `wiring.install_guards(...)` at `update.py:101` — and never
calls `wiring.record`. So a surface first wired by `update` has a guard entry that the receipt
does not list, and `uninstall` cannot see it to remove it. The log over-reports after an
uninstall and under-reports after an update.

That last fact is what settles the decision below. A receipt that only ever over-reports could
be fixed by teaching it to shrink. One that is wrong in both directions is not a description of
the machine at all, and no amount of bookkeeping turns it into one.

## What a sweep of every receipt reader added

Fifty candidates were raised across five lenses and each was handed to an independent reader
told to refute it. Thirty-four died, most of them as restatements of what is already written
above; sixteen survived. After removing the four that are the same defect reported from
different files, these are the ones not already named:

**The `opencode` row escapes INERT on a heartbeat that outlives the file it attests to.**
`~/.ai-engineering/cache/opencode-heartbeat` has an 86,400-second freshness window and
`uninstall` does not clear it, so for a day after the plugin is deleted the coverage block
reports OpenCode as blocking. That is a different hole from the `proven=` flag above and it
needs its own line.

**`update` rewires surfaces the operator deliberately unticked.** It calls `install_guards`
over everything `detect()` finds, not over what the receipt says was chosen. Declining Cursor
at install and running `ai-eng update` later wires it — with `failClosed: true`, which is what
Cursor needs to deny rather than advise — and records nothing. The same path can leave an
orphan OpenCode plugin shelling out to a `chain.py` in a wheel that has been uninstalled.

**A second `init --project` poisons the row `uninstall` restores from.** The `repo` row stores
the hooks path that was configured *before us*, read by `prior_hooks_path`. On the second run
that value is our own hooks directory, so `uninstall` "restores" the repository to the thing it
was supposed to be removing.

**One unwritable settings file leaves every surface after it wired.** `strip_entries` guards
the read and the parse, and then calls `write_json` outside any `try`. It is the same shape as
the OpenCode parse crash spec 003 closed — mid-loop, uncaught, in the verb whose whole pitch is
that governance comes out cleanly — in the one line that fix did not cover.

**Assertion 21 names a cure that cannot work.** It tells you to type `/hooks` in Codex to
approve a guard entry that, on an unwired machine, is not there to approve. It is ADR 0003's
rule failing on the shape spec 007 wrote it for.

**The link branch removes `ai-*` symlinks this install never wrote.** It globs the surface's
skills root and unlinks every symlink matching `ai-*`, rather than the rows the receipt names.
A skill somebody else installed under that prefix is collateral.

Two more were confirmed and are already on the record rather than new: the Windows copy that
`uninstall` cannot remove is a strict `xfail` in `tests/test_install.py`, and spec 007's plan
carries one sentence about the already-wired summary that this spec makes false.

None of this is a case nobody considered. Spec 005 refused per-surface uninstall in writing,
and the reason it gave is this one: *"it cannot be built correctly today because the receipt
has no delete path, so removing one surface would leave it recorded forever and turn the
receipt into a record that misstates the present."* The hole was seen, named, and scoped
around — and then `global_ready()`, `already()` and assertion 13 were built on top of the
record that was known to be unable to shrink.

## Options considered

**1. Make the receipt shrink, and leave both verbs reading it.** Give `wiring` a retraction
path and have `uninstall` retract exactly the rows it removed. It is the smallest change that
makes the reported screen correct, and it is the wrong fix. The receipt is a log of writes,
and the defect is asking a log what is true now: any machine whose state moves without this
tool moving it — a settings file edited by hand, a surface removed by its own installer, a
`~/.claude` restored from a backup, a second machine sharing a dotfiles repository — walks
straight back into the same screen with a receipt this option has just certified as accurate.
It buys the demonstrated bug and none of the class.

**2. Ask the disk, and leave the receipt the one job it is good at.** `global_ready()` and
`already()` count what is actually wired, by the same route assertion 2 already walks. The
receipt keeps the job its own docstring names — *"Probing the disk can prove a file exists;
it can never prove that we wrote it"* — which is ownership, and is what `uninstall` needs and
what nothing else does. It gains the retraction path anyway, because a row describing a file
we wrote and then removed misstates ownership just as badly. Costs more than option 1, and is
the only option under which a machine somebody else broke still reports honestly.

**3. Delete `machine.json` on uninstall.** Cheapest to type and the worst. The receipt is the
only record of which project files this tool wrote, across every repository it has ever
touched. Deleting it strands the nineteen `project` rows, and the next
`ai-eng uninstall --project` inside one of those repositories can no longer tell a `justfile`
we wrote from a `justfile` somebody wrote by hand — which is the exact defect spec 003 closed
when it made uninstall read the receipt instead of a hardcoded tuple.

## Decision

Option 2, and the retraction path from option 1 comes with it rather than instead of it.

The rule: **a verb reports the machine by looking at the machine.** The receipt answers one
question — did we write this? — and it is never asked a second one. Where a screen states a
count, that count is read from the thing being counted, and the two are not allowed to drift
because there is only ever one of them.

Three things follow, and none is optional.

`uninstall` **prints one line for every row it was shown**. A `✓` for what it removed, a
`→ kept, and why` for what it did not, and no consent taken for work it will not do. It names
the repositories in the receipt it is not entering and the command to run inside each, because
listing four repositories under "Remove them?" and unwiring one is worse than not listing them.

`init` **stops trusting the receipt for readiness**. `global_ready()` asks whether the guards
are on the surfaces that are here, which is a question assertion 2 already knows how to ask;
`already()` counts links and guards from the disk, which is what its own docstring has claimed
since spec 007 and what this spec makes true.

Assertion 13 **checks the links, not the directory that holds them**. A skills root that
exists because it holds somebody else's skills is not evidence that ours are in it.

Rule 10, one line each. **KISS** — one question ("what is on this machine?") asked in one
place, instead of two answers that can disagree. **YAGNI** — no per-surface uninstall, no
repair flag, no receipt migration format: the rows keep their shape and gain a way out.
**DRY** — `global_ready()` and assertion 2 stop being two opinions about whether this machine
is wired. **SOLID** — `wiring` owns both writing and retracting; `uninstall` stops knowing how
the receipt is stored. **TDD** — the first task is the round-trip test nothing in this suite
has: install, uninstall, and assert the next `init` sees an unwired machine. **Clean Code** —
a loop with a branch per kind gets the missing branches rather than a comment explaining the
silence. **Clean Architecture** — nothing crosses into `hooks/`; every change is in the half
of the tree that may import freely.

## Decisions

```yaml
decision: A verb reports the machine by looking at the machine
date: 2026-08-09
rationale: the rule the fifteen tasks are drawn from: where a screen states a count, that count
  is read from the thing being counted, and there is only ever one answer so there is nothing
  for two to disagree about. global_ready and doctor assertion 2 now make the same call, the
  coverage block opens the settings file it reports on rather than reading a static flag,
  assertion 13 looks inside the skills root rather than at it, and init's last screen counts its
  guard entries the same way; uninstall is only the loudest way a machine stops matching a log,
  and a settings file edited by hand, a surface removed by its own installer and a home restored
  from a backup all get the same wrong answer out of one.
```
```yaml
decision: A file that is there and cannot be read is undecidable, never empty
date: 2026-08-09
rationale: read_json answered {} to a missing file and to an unparseable one alike and every
  caller inherited it, so an interrupted write made the install record empty to every reader and
  the next record() stored that emptiness, and the same line under the three settings writers
  replaced a settings file carrying a JSONC comment with our hooks block alone under a line of
  output reading merged; this repository already made that ruling for text.yaml_blocks in the
  words its docstring still carries — silence on a parse failure is the exact shape of a false
  green, undecidable is an answer and invisible is not — and the record verbs got the rule while
  the files the installer reads did not.
```
```yaml
decision: The receipt answers ownership, and is never asked a second question
date: 2026-08-09
rationale: it is a log of writes, and both install verbs read it as the state of the machine:
  uninstall never wrote it so it could not shrink, and update wrote entries it never recorded so
  it under-reported too, which is why teaching it to shrink was refused as the fix. Its one real
  job is the one its own docstring names — probing the disk can prove a file exists and can
  never prove that we wrote it — so it keeps that and nothing else, and it gains a retraction
  path because a row describing a file we wrote and then removed misstates ownership just as
  badly as one that was never there.
```
<!-- ai-eng decide writes yaml blocks here -->

## Accepted risks

```yaml
id: R-008-02
finding: update-goes-quiet-on-a-lost-receipt
severity: low
accepted_by: soydachi
accepted: 2026-08-09
expires: 2026-11-08
renewals: 0
justification: ai-eng update now rewires the surfaces the receipt records as chosen rather than
  everything detect finds, which is what stops it wiring a surface somebody declined; the cost
  is that a machine whose receipt was lost or emptied — by the read_json defect this same spec
  closes, or by hand — updates nothing and prints one line naming ai-eng init --global, where it
  used to silently rewire whatever was there; that is a visible instruction rather than an
  unrecorded write, and it is the safer half of the trade
follow_up: if a real machine hits it, init --global is the cure and the line already says so;
  watch for it before adding any fallback to detect()
```
```yaml
id: R-008-01
finding: windows-uninstall-path-unproven
severity: medium
accepted_by: soydachi
accepted: 2026-08-09
expires: 2026-11-08
renewals: 0
justification: strip_links now honours the copy the receipt records, which is what wiring.link
  writes where symlinks are unavailable, and the strict xfail that had marked that defect since
  it was found comes off in the same commit; what has not happened is a run of uninstall on
  Windows, because the install matrix builds and installs the wheel on three platforms and never
  uninstalls on any of them, so the branch ships exercised by a unit test that fakes the copy
  and by nothing else
follow_up: the install matrix grows an uninstall step after its doctor step on all three
  platforms, or this is renewed once with the reason and then fixed
```
<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [x] CI/CD — `just check`, run by `.github/workflows/check.yml` on every push; nothing here is deployed, and `.github/workflows/release.yml` is what publishes the wheel
- [x] Logs — `ai-eng digest`: every verb emits one JSON line per run, and `cli.main` now emits an error event for the refusal this spec added before it exits 2
- [x] Traces — not applicable, and that is the rule: one process, no second hop, no trace
- [x] Errors — `cli.main` catches `wiring.Unreadable`, names the file, writes nothing and exits 2, and emits the event `ai-eng digest` reads; every other uncaught exception still re-raises after the same emit
- [x] Health and data age — `ai-eng doctor`, whose coverage block and assertions 13 and 21 are three of the fifteen tasks, and `ai-eng audit verify` for the age of the chain
- [x] External check — `.github/workflows/install-matrix.yml` installs the built wheel on three platforms and runs `init` and `doctor`; what it cannot check is R-008-01, because it never uninstalls on any of them
- [x] Second path — the round trip is the second path, and it is what nothing had: `tests/test_install.py` installs the machine half, runs `uninstall`, and asks `init` and `doctor` what they see, with every count read off the disk by `stripped()` rather than out of the record under test
- [x] Security — `just security`: gitleaks, semgrep and trivy on every push, and `python tests/adversarial/run.py` at 14 of 14 including the negative control
