---
id: "003"
slug: guards-that-never-fired
---

# Plan — the order that keeps every commit green

## The base this is measured from

Every per-task number below is against `9d532dbf`, where `contract.repo_lines` was 5,610
against a ceiling of 5,610. Deletion figures were produced by deleting the lines and running
the formatter, not by counting them in an editor, because the formatter collapses the blank
runs a deletion leaves behind and that is worth two to three lines on its own. Each task's
own figure survives the move — a deletion of twenty lines deletes twenty lines whatever the
total is — but **the total does not**, and section 3 has been restated against the committed
base of 12,017 rather than patched.

**This worktree is not at that base either.** The session that was mid-edit on the guards
committed; what is uncommitted now is a different lane of the operator's — a TypeScript
typecheck recipe and a rewritten `docs/tools.md` — and the count is sixty-six lines over the
ceiling because of it, so the gate is red before this branch starts. Nothing here can be
started until that work is committed or dropped, and if it is committed the base and the
table in section 3 are recomputed from it. This is the first task.

One task, one commit. The arithmetic each task carries is a prediction; the closing task
replaces it with the count that landed.

Two orderings are constraints rather than preferences. Deriving the protected list lands
before the wheel's directories become protected, or the file that must be edited is no
longer editable. And on a machine where this checkout is the wired install — which is what
an editable install makes it, and what dogfooding means — the guards directory is already
self-protected, so sections 4 and 5 edit files a wired session may not touch. Do that work
in a session that is not wired to this checkout, or unwire it at a keyboard first. Nothing
here asks a guard to be weakened to let its own repair through.

## 1. The base, and the two gates already scheduled to fail

- **file** the second session's work · **check** `git status --porcelain` is empty and
  `contract.repo_lines` is at or under the ceiling · **rollback** none · **done when**
  the tree this branch starts from is committed, green, and measured, and the figures below
  are restated against it if it moved. Net 0.
- **file** `src/ai_engineering/accept.py`, `specs/003-guards-that-never-fired/spec.md` ·
  **check** a test that forces the date to 2026-09-09 and asserts `expired()` returns
  nothing, which fails today and would keep failing if the renewal block alone were added ·
  **rollback** revert the reader · **done when** the expiry reader keeps only the
  highest-renewal block per finding, so the renewal this spec records actually retires the
  one that expires 2026-09-08 and the push gate stops being scheduled to fail. **+3.**
- **file** `tests/adversarial/run.py` · **check** `grep -q "12 of 12" tests/adversarial/run.py`
  finds nothing · **rollback** revert · **done when** the bar is derived from the number of
  registered cases. The three prose sites that say twelve — the harness docstring, the CI
  step name and the doctrine file — are corrected in the same commit, because leaving them
  is the same defect one layer out. Note the second session has already edited two of them.
  Net 0.

## 2. The payers, before anything is spent

Split along the architectural seam so a reviewer can revert one half without the other.

- **file** `src/ai_engineering/cli.py` · **check** `git grep BANNER` returns nothing and the
  CLI's own output is unchanged · **rollback** revert · **done when** the banner constant
  no reader has ever referenced is gone, along with the blank line the formatter then
  collapses. **−7.**
- **file** `hooks/loop_guard.py`, `hooks/_wrap.py` · **check** `pytest -q` and the
  adversarial suite unchanged · **rollback** revert · **done when** the state write that
  happens after the last save and is never persisted, its now-unused import, and the
  `raise` that follows a call which always exits are gone. **−3.**
- **file** `src/ai_engineering/doctor.py` · **check**
  `python -c "from ai_engineering import doctor; assert len(doctor.CHECKS) == 20"` ·
  **rollback** revert · **done when** the line-budget check is deleted. The assertion
  survives in the test plane, which is where it can fail a build rather than print a line,
  and it never evaluated outside this repository anyway. The prose that counts assertions
  is left alone here and corrected once, in section 12, because this branch changes that
  number twice. **−20.**
- **file** `src/ai_engineering/wiring.py` · **check** `pytest -q` unchanged · **rollback**
  revert · **done when** the helper that ignores its only argument and returns a constant
  is inlined at its two call sites. It implies a per-repository hooks path the code does not
  support. **−3.**

## 3. The ceiling

Restated on 2026-08-08. The figures in this section were arithmetic against a repository
that no longer exists: they read from 5,610, and the constant now reads 12,017 because the
test plane and the mutation plane landed in between. The base below is the committed one,
measured rather than remembered, and spec 005's prediction is in the same table because 005
deliberately raises nothing of its own and its arithmetic has to land somewhere.

| | lines |
|---|---|
| committed base, `contract.repo_lines` at `HEAD` | 12,017 |
| this plan, sections 1–2 and 4–13, net of the deletions | +165 |
| spec 005, its thirteen tasks and the comment this constant carries | +75 |
| predicted total | 12,257 |

- **file** `src/ai_engineering/contract.py` · **check** the ceiling test passes and the
  commit message carries the table, gross and net, per item · **rollback** revert ·
  **done when** `REPO_CEILING` reads **12,400**. That is the 12,225 predicted above plus
  about eight per cent, raised generously on purpose: the one prior estimate on file in
  this project overran by ninety per cent, and a ceiling that goes red two thirds of the
  way through a branch blocks every commit after it with the project's own gate. The
  closing task takes it back to the measured count, so the headroom does not survive the
  branch. The comment above the constant records the move. **+1.**
- **not in the table, and named rather than absorbed.** The working copy this was restated
  in measures 12,083 — sixty-six lines over the committed base — and none of them belong to
  either spec: they are an in-flight lane of the operator's, a TypeScript typecheck recipe
  and a rewritten `docs/tools.md`. Whichever branch commits them raises the ceiling by that
  much in its own commit, with its own reason. A raise that quietly carries somebody else's
  lines is a ceiling that has already stopped meaning anything.

## 4. The guard that never fired

- **file** `hooks/chain.py` · **check** two dispatcher runs carrying the same session
  identifier in the payload leave one file in the loop cache, not two; and a second delivery
  of the same tool call returns the verdict the guard wrote rather than the placeholder ·
  **rollback** revert · **done when** the dispatcher writes the session the surface sent
  into the environment variable the record layer already reads, before anything computes a
  fingerprint. Threading a new key through the payload does not fix it: the loop state file
  and the verdict cache both call the record layer's own session function. The precedence is
  payload if non-empty, then the environment, then mint — non-empty, because one surface
  sends an empty string rather than omitting the field. Landing this switches on a verdict
  cache that has never executed, which is why its message is in the check. **+18.**
- **file** `hooks/loop_guard.py`, `tests/adversarial/run.py` · **check** three identical
  calls with three distinct tool identifiers deny on the third; three *different* shell
  commands in one session do not; the three-file read control stays quiet · **rollback**
  revert · **done when** the repeat arm keys on the tool name and a hash of the whole tool
  input. Not on the existing coarse signature, which is the tool plus the first token and
  would collapse every git command in a session into one key — measured, on the second
  session's in-flight version: the third git command of a session is denied. The negative
  control gains the case that catches it. **+8.**
- **file** `hooks/loop_guard.py` · **check** after many distinct failing signatures the
  failure map holds only the most recent few, and five failures of one signature with an
  unrelated failure interleaved still denies · **rollback** revert · **done when** the
  failure map is bounded by number of distinct signatures. Not by the call window: five
  failures inside six calls is a threshold the failure arm can never reach once anything
  else happens. Everything else this task used to claim — the second signal, the reset on
  success, no subprocess on the hot path — is already true today. **+2.**

## 5. Self-protection, in the order that does not lock the branch out

- **file** `hooks/self_protect.py`, `policy/surfaces.toml` · **check** an edit to a skills
  directory under the OpenCode tree and one under the agent tree both exit 2; an ordinary
  edit to an unrelated file still exits 0 · **rollback** revert both files together ·
  **done when** the settings and skills columns are read from the wiring table and the five
  literals that duplicated them are deleted. Three things this must get right: empty values
  are filtered, because the protected test is a substring test and an empty string matches
  everything, which would deny every write on the machine while passing the check as
  written; where our settings file lives inside a directory we own, the derived value is
  that directory, not the filename, or two surfaces lose protection they have today; and
  the two entries that are already directories stay literal. **−1.**
- **file** `hooks/self_protect.py` · **check** an edit to the IOC catalogue exits 2 on a
  wheel install, and a checkout of this repository is still editable · **rollback** revert ·
  **done when** the wheel's own `policy`, `git-hooks` and `surfaces` directories are
  protected as siblings of the guards directory, skipped when that parent is a working copy
  of this project — which is exactly what it is in a checkout, and protecting it would deny
  every edit in this repository. **+4.**
- **file** `hooks/self_protect.py`, `tests/adversarial/run.py` · **check** all six write
  paths measured in the spec exit 2, including the tilde spelling, while
  `cat ~/.claude/skills/ai-spec/SKILL.md 2>/dev/null; ls ~/.claude/skills/ai-spec` and the
  multiline `ls .git/hooks/; gitleaks version 2>&1 | head -1` both exit 0, together with the
  ordinary staging, diff, show, restore and stash forms · **rollback** revert · **done
  when** the operator test is complete rather than replaced: the copy, the install, the
  `dd`, the truncate and the two Python one-liner spellings join it; the command text has
  its home directory expanded before comparison; and an operator in one shell command
  cannot turn a protected-path read in another into a write. Denying on mention alone was
  the council's shape and is refused in the spec: the carve-out it needs is one verb with
  both readable and writable subcommands, and the sweeping spellings name no path at all,
  so it would deny the honest command and allow the broad one. **+4.**
- **file** `hooks/no_verify_guard.py`, `tests/adversarial/run.py` · **check** pointing the
  hooks path at another directory exits 2, unsetting it exits 2, and pointing it at the
  directory we install exits 0 whether it is written as a relative or an absolute path ·
  **rollback** revert · **done when** the guard covers the configuration form as well as the
  per-command override, decides on the value rather than the verb, and resolves that value
  against the repository root before comparing — this repository's own bootstrap writes the
  relative form. The scoped, unset and add spellings are covered too. **+18.**

## 6. A blocked call is not a silent stop

- **file** `hooks/_wrap.py`, `hooks/chain.py`, `tests/test_hooks.py` · **check**
  `pytest -q tests/test_hooks.py` includes a Claude-shaped `PreToolUse` denial that exits 0
  with `hookSpecificOutput.permissionDecision: deny`, contains no universal
  `continue: false`,
  and gives Claude the reason; the same denial on OpenCode and the status-driven surfaces
  still exits 2 and names the guard · **rollback** revert the response split · **done when**
  each surface receives one denial protocol rather than the current JSON-plus-exit mixture,
  and a surface cannot mistake an automated gate for a person's permission refusal. Do not
  infer the surface from an install path: use payload fields the surface itself sends.
  **+14.**
- **file** `tests/adversarial/run.py`, `surfaces/opencode.ts` · **check**
  `python tests/adversarial/run.py --live-claude` asks one live Claude Code session for a
  harmless call that a fixture guard denies, then records either a subsequent assistant
  action or an explicit visible handoff before `turn_duration`, with no second user prompt;
  OpenCode's existing throw still kills only the call · **rollback**
  revert the live case and response split · **done when** the comment claiming parity is
  evidence rather than prose. Run this check on the minimum supported Claude Code and the
  installed version that produced the report. If structured denial still stops either one,
  add a one-shot `Stop` recovery tied to that session and prove it cannot loop; do not ship
  another instruction in stderr and call it continuation. **+6 predicted; restate after the
  live branch chooses structured denial alone or the fallback.**

## 7. Mutation runs on no one's machine

- **file** `justfile`, `tests/test_contracts.py` · **check** hash the live Claude Code and
  Copilot settings, run `just mutate src/ai_engineering/init.py`, and assert both hashes
  are unchanged while any settings a mutant writes exist only under the run's temporary
  home · **rollback** revert the environment isolation · **done when** the mutmut process
  receives disposable `HOME`, `USERPROFILE`, `AI_ENGINEERING_HOME` and XDG config roots
  before Python imports the package, while uv keeps an explicit cache outside that home;
  the cleanup removes only the disposable tree; and a before/after receipt makes any future
  escape fail the gate rather than merely print hook errors in the next session. **+12.**

## 8. The false green

- **file** `src/ai_engineering/text.py`, `src/ai_engineering/accept.py`,
  `src/ai_engineering/doctor.py` · **check** a spec holding one malformed acceptance block
  makes `doctor` report could-not-evaluate and `git push` refuse, where both report ok
  today; every block in `specs/` and `docs/` still parses · **rollback** revert the three ·
  **done when** the block reader raises and names the file, and all four callers — the
  expiry reader, the doctor check, the push hook and the write path of `accept` itself —
  either handle it or let it become undecidable. The write path matters: without it,
  recording a new acceptance would traceback on a malformed neighbour. **+10.**

## 9. The install that was never ours

- **file** `src/ai_engineering/wiring.py`, `uninstall.py`, `doctor.py`,
  `tests/test_contracts.py` · **check** a unit test builds an entry from an interpreter path
  spelled with an underscore and asserts it is recognised as ours, and the assertion that
  catches an entry pointing at another install still fires · **rollback** revert all six
  edits together · **done when** the comparison mark is the dispatcher's basename at the
  five sites that compare, and the string rendered into the status message a person reads
  keeps its own name and its old value. Basename only: a mark containing the install path
  makes the other-install assertion unable to fire, and the status message is inside the
  hash one surface stores when a person approves the hook, so moving it would silently
  make that surface inert. **+10.**
- **file** `src/ai_engineering/uninstall.py`, `src/ai_engineering/init.py` · **check**
  `ai-eng uninstall` on a machine with the OpenCode plugin installed completes and unwires
  every surface, where today it raises a parse error and leaves the rest wired ·
  **rollback** revert · **done when** the entry stripper refuses anything that is not JSON
  instead of handing TypeScript to a JSON parser, and the plugin row removes the file it
  wrote. **+4.**
- **file** `src/ai_engineering/uninstall.py`, `wiring.py`, `init.py` · **check** a temporary
  repository that had its own hooks path configured has that exact value back after `init`
  then `uninstall`, and nothing outside the receipt's rows was deleted · **rollback**
  revert · **done when** the prior hooks path is read before it is overwritten, recorded in
  the receipt, and restored rather than unset. The project half of `init` records nothing
  today, which is why it is in this task's file list: without that, uninstall has no
  ownership record to consult and deletes four files by name on faith. The check is not
  byte-identical repositories — the constitution requires three things to survive — it is
  the configured value and the file list. **+25.**
- **file** `src/ai_engineering/init.py` · **check** a second `init` over an unchanged
  repository writes nothing and says so; a fresh `init` still creates both protected files,
  which the install matrix asserts · **rollback** revert · **done when** the offer compares
  what it would render against what is on disk, and the two files the constitution says
  never to touch after writing them once are excluded from the overwrite set only — not
  from the create set, which is the same table, and dropping them from it would stop them
  ever being written. **+8.**

## 10. The record verbs

- **file** `src/ai_engineering/spec.py`, `accept.py`, `text.py`,
  `specs/003-guards-that-never-fired/spec.md` · **check** an identifier matching two
  directories prints both; a rationale of four hundred characters survives a render and
  re-read unchanged; the first acceptance recorded against a spec is numbered one ·
  **rollback** revert · **done when** the record is readable in a diff, its numbering reads
  as the nth risk of its spec, and the four blocks this spec already holds are renumbered in
  the same commit — they were minted by the old counter and would otherwise collide with the
  new one. The folded form is the indented continuation the reader already supports, so the
  check is a round trip rather than a look. **+7.**
- **file** `src/ai_engineering/decide.py`, `accept.py` · **check** recording a decision while
  a newer spec directory exists writes to the spec you named, and refuses rather than
  guessing when you named none and more than one is a draft · **rollback** revert ·
  **done when** the record verbs stop resolving to whichever spec sorts last. This is not
  theoretical: writing this spec, two decisions landed in another session's spec because a
  fourth directory appeared between two commands. **+6.**

## 11. CI — the wheel, actually exercised

Neither mandatory task class applies: this spec deploys nothing and gives nothing a URL,
so there is no new pipeline and no new signal to observe. What follows is CI work because
the artifact is the thing under test.

- **file** `.github/workflows/install-matrix.yml` · **check** the leg fails when the
  installed console script reports a version other than the one the wheel carries ·
  **rollback** revert · **done when** the version that is printed is compared rather than
  discarded. Worth three lines only because it catches a force-install that silently kept an
  older tool; the tag-versus-package comparison is already covered elsewhere. **+3.**
- **file** `.github/workflows/install-matrix.yml` · **check** a payload that must block,
  fed to the dispatcher at the path `doctor` prints, exits 2 **and** stderr names the guard
  that denied · **rollback** revert the step · **done when** a guard has been executed from
  the installed tree for the first time. Naming the guard is the whole value: the dispatcher
  fails closed, so a crashed guard, a failed import and a correct denial all exit 2, and
  without the name the step would pass most loudly in the case it exists to catch. The step
  captures the exit code rather than letting the shell's error flag abort on it, and pins an
  interpreter new enough for the record layer. **+7.**

## 12. The numbers that were prose

- **file** `tests/test_contracts.py`, `src/ai_engineering/doctor.py`,
  `src/ai_engineering/cli.py` · **check** adding a ninth skill directory or an eleventh verb
  turns the build red naming the file whose prose disagrees · **rollback** revert ·
  **done when** each count is compared against the number written in the prose that claims
  it, in both digits and words, rather than against another derivation of itself — a test
  that derives both sides cannot fail. The assertion count is written once here, after this
  branch has changed it twice. Note the second session is deleting some of these literals
  outright, which is the other valid answer; if that lands, this task shrinks to the
  literals that remain. **+18.**
- **file** `src/ai_engineering/doctor.py` · **check** a repository whose hooks path points
  at a directory that merely contains a `pre-commit` fails, where it passes today ·
  **rollback** revert · **done when** doctor stops accepting a hooks path on the evidence
  that something lives at it. The ignore-rule half of this task is dropped: git already
  excludes tracked paths from `check-ignore`, so the failure it was written for cannot be
  observed the way the council described, and the two existing checks cover most of what
  remains. This check must run outside CI mode, where the surrounding check is skipped, or
  the CI leg proves nothing. **+11.**

## 13. Closing

- **file** `src/ai_engineering/contract.py`, `specs/003-guards-that-never-fired/spec.md` ·
  **check** `contract.repo_lines(root) == contract.REPO_CEILING`, `just check` piped to a
  log outside the repository and read by the anti-theatre harness, and `ai-eng doctor` ·
  **rollback** revert the constant · **done when** the ceiling equals the landed count
  exactly, each production-ready box is relabelled to name the evidence it actually has —
  including "not applicable, and that is the rule" where that is the truth, which is how
  spec 001 handled the same problem — and the status is flipped to shipped, which is what
  makes the doctor assertion over those boxes fire at all. **0.**

## Not doing

- **The escape ledger and a global disable variable.** The denial text withholds the bypass
  recipe on purpose, and a variable is that recipe, settable from the shell the guard is
  defending against.
- **A green gate that requires the working tree to have moved.** Forty lines to implement a
  CI property inside a session hook that is telemetry by contract and by test.
- **A branch name that must reference a live spec.** No live state to test against here, and
  the hook would land in every consumer repository without an opt-out.
- **Replaying guards over recorded events.** No event records the tool input; recording it
  would red the signal-ratio check by construction and build the exfiltration surface the
  telemetry allow-list exists to prevent.
- **Denying by mention.** Refused in the spec on measurement, not on taste: the carve-out is
  larger than the rule and the rule misses the sweeping spellings entirely.
- **An assertion-density gate, a namespace check on risk acceptances, a second install leg,
  a scan of the built wheel, and moving the session count onto the line beside the block
  count.** Each measures something already measured, forbids something that is already a
  no-op, or is a re-layout of a number that is already on screen.
- **The three payload spellings the dispatcher normalises.** An accepted risk with a date,
  because the honest fix is driving a real surface.
- **An audit of the eight skills against the context-engineering guidance for this model
  generation.** Real work, and a different spec. This one adds no line to any skill and no
  line to the doctrine file, which is the part of that guidance it is bound by today.
