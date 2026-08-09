---
id: "003"
slug: guards-that-never-fired
status: draft
date: 2026-08-08
ref: ""
supersedes: ""
---

# The guards that never fired, and the install that was never ours

## Context and problem

v1.0.0 ships eight guards, ten verbs and three git hooks, and its own adversarial suite is
green. This spec exists because a reading of a peer product went looking for features to
borrow and came back instead with nine failures of our own, each one an instance of the
second word in the mission: doing nothing silently.

The peer is karajan-code, a multi-agent orchestrator under AGPL-3.0. It was read the way
an engineer reads a competitor — for the shape of a solution, never for its text. Nothing
here is copied from it: no code, no configuration schema, no prompt wording. Where an idea
of theirs survives below, it survives as a description reimplemented from scratch against
our own tree, and the two candidates whose entire value was their prose were dropped for
that reason alone.

Fifty-seven candidates came out of that reading. Ground-truthing them against this
repository killed most of them, and the killing is the useful half: it is written down in
the Decisions block so nobody re-proposes them in six months. What it turned up on the way
is what follows. Each fact below was observed by running something, not by reading.

**One. `loop_guard` has never once accumulated state.** The loop cache on this machine
holds 358 files, every one of them 48 bytes and one entry long, because `_emit.session_id()`
mints a fresh identifier in every hook process, so the state file a call writes is a state
file the next call never reads. Fixing that alone is not enough: `chain.py` folds
`tool_use_id` into the fingerprint that `loop_guard` counts, and a real surface sends a
distinct `tool_use_id` per call, so `state["recent"].count(fingerprint)` cannot reach three
however long a session runs. A guard that sits in the dispatcher table, passes the
adversarial suite and cannot fire in production is exactly the failure this rebuild was
supposed to end. It is also the reason to distrust the suite as evidence: the harness
injects a stable session into the environment and sends payloads with no `tool_use_id`, so
it exercises a shape production never produces.

**Two. Whether an entry is ours is an accident of how the tool was installed.**
`wiring.MARK` is the string `ai-engineering`, hyphenated, and an entry is judged ours when
that string appears anywhere in its JSON. The entry is built from `sys.executable` and the
dispatcher's path, and under a wheel the package directory is spelled with an underscore.
For three of the five surfaces the hyphen therefore arrives from one place only: `uv tool`
and `pipx` happen to put the hyphenated project name into the interpreter's path. Install
with `pip` into a venv named anything else and `ours()` is false for Claude Code, Cursor
and VS Code Copilot — the first two then gain a duplicate row on every `init`, `uninstall`
reports it had no entry of ours and leaves those guards wired, and `doctor` reports no
entry against a live installation. Codex survives by a second accident: the mark is also
its status message, so the hyphen is written into the entry deliberately. OpenCode does
not survive at all, which is failure six below. This is the only defect on the list that
silently breaks a stranger's machine, and the CI matrix cannot see it because the matrix
installs the one way that makes the accident hold.

**Three. A malformed record block disappears instead of failing.** `text.yaml_blocks`
catches `ValueError` and continues to the next block. An acceptance whose YAML is a little
wrong is therefore invisible to the expiry check that both `pre-push` and `doctor` read —
so the gate reports green over a risk that has expired. A false green in the exact
mechanism this product is sold on is worse than no mechanism.

**Four. No guard has ever been executed from the built wheel.** The install matrix proves
a great deal — it builds the wheel, installs it with `uv tool`, and runs `init`, `doctor`,
`spec new` and `audit verify` in a repository the tool has never seen, on three operating
systems. What it never does is run a hook. `release.yml` opens the zip and asserts the
dispatcher is inside it, which proves the file shipped and nothing about whether it still
denies. The guards' own relative walk to `policy/` is identical in both layouts — that was
checked rather than assumed — so this is not a prediction that something is broken. It is
the plainer statement that the artifact a stranger installs has never had a guard run in
it, and the only evidence we have that it denies is that the same file denies somewhere
else.

**Five. Self-protection has fallen behind the wiring it claims it cannot fall behind.**
The docstring says the protected list is read from the wiring table so it cannot drift.
Two skill directories that `wiring` writes to appear in no protect entry, and the shell
branch fires only when the command also contains one of seven operators, so anything that
writes by another spelling walks past it. Fed to the real dispatcher, six ways of
overwriting a surface's settings file exit zero today: a copy, an `install`, a `truncate`,
a `dd`, a one-line Python program, and a redirection written with the home directory left
as a tilde, which the guard stores only in its expanded form. The wheel's own `policy/` and
`git-hooks/` directories are unprotected as well: a single edit to the IOC catalogue
disarms the injection guard.

The opposite failure was then observed in a real Claude Code session. A read-only command
used `cat` on `~/.claude/skills/ai-spec/SKILL.md`, redirected only stderr to `/dev/null`,
and then listed the same directory. `self_protect` found the protected path anywhere in the
command and the `>` from `2>/dev/null` anywhere else, joined the two unrelated facts and
reported that the command wrote to the skills directory. It did not. A guard that misses
six writes and refuses an ordinary read is wrong in both directions, and “use the read
tool” is a workaround rather than a defence of the decision.

It reproduced a second time with a wider command: one line only listed `.git/hooks/`, while
a later, independent line ran `gitleaks version 2>&1 | head -1`. The guard paired the
protected path from the first command with the redirect from the later command and again
reported a write to the protected directory. This narrows the cause: the decision is made
over the whole Bash string, across newlines and command separators, rather than over the
operator and destination of one command. A fix that merely blesses `cat` leaves this `ls`
case broken; the check has to preserve the boundary between shell commands.

**Six. `ai-eng uninstall` crashes on any machine that has OpenCode.** The installer records
the OpenCode plugin as a guard row, so uninstall sends it to the routine that strips JSON
entries; that routine finds the mark inside the TypeScript, hands the TypeScript to a JSON
parser and raises. The exception is uncaught and it happens mid-loop, so every surface
after it is left wired too. The verb whose entire pitch is that governance can be removed
cleanly is the verb that dies halfway. This one was found while checking failure two and is
not on anybody's candidate list.

**Seven. A renewal has never once retired what it renews.** An acceptance in spec 001
expires 2026-09-08, thirty-one days from today, and when it does every push and every CI
`doctor` in this repository goes red from a markdown file. Renewing it in a later spec does
not help because the expiry reader returns the expired original and the newer renewal as
independent findings. This spec discovered the defect by trying to use the mechanism.

**Eight. A correct denial can end the agent's turn without a handoff.** The false positive
above produced an error tool result in Claude Code 2.1.226 and was followed immediately by
the turn-duration record. There was no next assistant message, explanation or alternative
call; work resumed only after the person asked why it had stopped almost two minutes later.
The second false positive reproduced the whole sequence: denied tool result, immediate
turn-duration record, no assistant event, then a user message ten minutes and thirty-five
seconds later. This is now two observed denials with two silent stops, not one ambiguous UI
pause.
The dispatcher prints a cross-surface JSON denial and exits 2. Claude Code documents that
JSON is ignored on exit 2, and `anthropics/claude-code#24327` records the intermittent
behaviour we observed: the model can treat an automated hook denial like a person's
permission refusal and wait. The contract in `surfaces/opencode.ts` says Claude continues
after a denial; the observed transcript disproves it. A guard blocks one operation. It
does not silently turn an autonomous task back into a person typing “continue”.

**Nine. The mutation gate rewired the operator's real machine from a disposable mutant.**
A scoped mutation run over `init` and `wiring` copied the repository away from its working
tree but kept the process's real `HOME`. One mutant reached the global installer and wrote
Claude Code and Copilot entries containing its own temporary uv interpreter and its
temporary `mutants/hooks/chain.py`. The mutation sandbox was then deleted. Every later
Read, Edit and Bash call tried both pre- and post-tool hooks at paths that no longer
existed, printed a non-blocking error and continued without any guard running. The recipe's
comment says the copy exists because mutation once edited the developer's repository; it
moved the sandbox and left the developer's machine inside it. A test process that can
install itself globally is not isolated, however temporary its checkout is.

One smaller thing belongs in the same sweep because leaving it is choosing a misleading
gate later. The adversarial harness holds a literal saying the bar is twelve of twelve
while thirteen cases are registered; it only prints on failure, which is why nobody has
seen it.

## Options considered

1. **Take the council's package as written** — six adoptions and four adaptations, priced
   at roughly 120 lines. Rejected on evidence, item by item, in the Decisions block. Half
   of it is already shipped here, a quarter of it breaks a control this repository already
   owns, and two pieces contradict the constitution in writing. Adopting it would have
   bought a branch-name gate that cannot express a live spec, a normalisation that turns
   three ordinary file reads into a denial, and an environment variable that hands an agent
   the key to every gate.
2. **Fix nothing until a user reports it.** The honest option, and the cheapest. Rejected
   because six of the nine failures are silent by construction: a guard that never fires
   produces no complaint, a duplicate wiring entry produces no complaint, and a swallowed
   record block produces a green. The only report they can generate is the one that arrives
   after the harm.
3. **Ground-truth every candidate against this tree, then fix what this tree actually gets
   wrong, whether or not the peer product mentioned it.** More work up front, and it makes
   the reading of the peer look like a poor investment in candidates while making it an
   excellent one in mirrors. Chosen.

## Decision

Fix every failure observed above. Take from the council only what survived contact with
the tree — two adoptions in full, one in a narrowed form — and write down the rejections
with their reasons so the same fifty-seven candidates cannot come back unexamined.

Pay with the payers that were found rather than invented, measured by deleting the lines
and running the formatter rather than by counting them in an editor: the dead banner
constant with the blank line the formatter then collapses, six; the `doctor` check that
duplicates a test running in the same CI job, twenty; the state write that is never
persisted with its now-unused import, two; the unreachable `raise`, one; the five protect
literals that become one derived expression, one net; and a helper that ignores its only
argument, three. Thirty-three lines, and the work is larger than that.

So the ceiling moves for the third time — 5,000 to 5,600, 5,600 to 5,610, and now — in one
commit whose message carries the whole table, and it is raised generously rather than
tightly, because the one prior estimate on file in this project overran by ninety per cent
and a ceiling that goes red two thirds of the way through a branch stops every commit after
it. The closing commit takes it back down to the count that actually landed, which costs
nothing because that commit exists anyway, and slack that does not survive a branch is not
slack.

Rule 10, one line each, because a spec is where these are supposed to earn their keep:
**KISS** — the loop guard is revived by two edits, not by a fingerprint algorithm.
**YAGNI** — the escape ledger, the replay engine and the assertion-density gate are all
built for a problem nobody here has had, and all three are rejected.
**DRY** — `doctor`'s line-budget check and the ceiling test are the same assertion in the
same job; one of them goes.
**SOLID** — self-protection stops holding its own copy of the surface list and reads the
table that already owns it.
**TDD** — every task below names the check that is red before it and green after; three of
them exist only to make a number that was prose into a number that is an exit code.
**Clean Code** — the shell branch stops enumerating verbs, which is a list nobody can
finish, and starts asking the one question that has an answer.
**Clean Architecture** — the guards keep their dependency direction: hooks read policy and
never import the package, and nothing added here changes that.

The context-engineering guidance for this model generation points the same way and is worth
naming, because it is what kills the largest candidates rather than the smallest: the fix
for an agent doing the wrong thing is a better interface, not another sentence of rules.
Two candidates proposed exactly that sentence — one in a skill, one in the digest — and
both are refused under rule 12, which says the third identical judgement becomes a script
and the prompt goes away with it. Nothing in this spec adds a line to `AGENTS.md`, and no
skill grows.

## Decisions

```yaml
decision: A mutation worker runs with a disposable home, not merely a disposable checkout
date: 2026-08-09
rationale: A real mutation run wrote Claude Code and Copilot hook entries whose interpreter and dispatcher both lived under temporary directories that were deleted when the run ended. The existing recipe isolates the git tree but inherits HOME, USERPROFILE and AI_ENGINEERING_HOME, so a mutant that reaches global init can rewrite the operator's machine while the test suite still believes its fixture owns the paths. The worker receives a fresh home and framework home before mutmut starts, and the gate compares the real surface files before and after the run. A test tool that changes governance outside its sandbox fails even if every mutant was killed.
```

```yaml
decision: A guard denial blocks one operation, not the agent's turn
date: 2026-08-08
rationale: A real Claude Code 2.1.226 transcript records the whole failure: self_protect denied a harmless read, the client returned an error tool result, and the turn ended three milliseconds later with no assistant response until the person prompted again. The current dispatcher mixes a JSON denial with exit 2 even though Claude Code ignores JSON on that exit path, and an upstream issue records the same intermittent stop. The response becomes surface-specific: Claude receives its documented structured PreToolUse denial, the surfaces that enforce by process status keep their status, and the task is not complete until a live denial either produces the next assistant action or a visible handoff without another user prompt. If structured denial alone does not meet that check, a one-shot Stop recovery is the fallback; hoping the model interprets stderr differently is not.
```

```yaml
decision: A renewal that does not retire what it renews is not a renewal
date: 2026-08-08
rationale: This spec tried to use the renewal mechanism on the acceptance that expires in thirty-one days, and discovered by doing it that renewing changes nothing: the expiry reader returns every block whose date has passed, across every spec, with no notion that a later block with a higher renewal count supersedes an earlier one with the same finding. So the push gate and the doctor check both stay red on the old block, and no renewal anybody has ever recorded has retired anything. The reader keeps the highest renewal per finding and ignores the rest, which is one line and makes a documented feature true for the first time. The alternative was editing the date inside spec 001, which is a smaller diff and a worse answer: it rewrites the record of what was decided then, and the whole argument for a renewal block is that the history stays legible.
```
```yaml
decision: Denying by mention is refused in favour of finishing the operator test
date: 2026-08-08
rationale: The council's shape was to deny any command whose text names a governing path and carve out the read-shaped forms. Measured against the real dispatcher, the carve-out is not a small list: staging, diffing, showing, restoring and stashing the pin are all the same verb as the ones that write, so the carve-out has to be verb-plus-subcommand, which is a longer list that falls behind faster than the one it replaces. Worse, the sweeping spellings mention no path at all, so the guard would deny the honest form and allow the broad one. Completing the operator test closes all six measured write paths, costs less, and breaks nothing a person types every day. This reverses the recommendation the operator chose from the summary; it is reversed on evidence gathered afterwards, and the evidence is the six commands and the carve-out list in the plan.
```
```yaml
decision: What the peer product proposed, and what this repository refuses
date: 2026-08-08
rationale: Recorded so the same candidates cannot return unexamined. A global disable variable and an escape ledger are refused because the denial text deliberately withholds the bypass recipe from a model that may already be compromised, and a variable is that recipe, settable from the same shell the guard is protecting against, which would also redirect the ledger meant to record it: escalation is a person at a keyboard, and the constitution says so. A gate that demands the working tree moved before green is refused because the end-of-session hook is telemetry by contract and by test, so it would need a new blocking guard to bite, and it is a CI property being implemented in a session hook. A branch-name-must-name-a-live-spec gate is refused because shipped is terminal here, so there is no live state to test, and the hook lands in every consumer repository without the managed exit that would let them opt out. Replaying guards over recorded events is refused because no event records the tool input, and recording it would both red the signal-ratio check by construction and create the exfiltration surface the telemetry allow-list exists to prevent. An assertion-density gate is refused because every test function in the corpus already carries an assertion, and rule 12 is about a judgement that has resolved the same way three times, not one that has never resolved otherwise. Validating a risk acceptance against the secret scanner namespace is refused because an acceptance suppresses nothing here: the scanners run unconditionally, so it would forbid a no-op. Scanning the built wheel and adding a second install path are refused as re-measurements of what is already measured. Two candidates whose entire enforcement was one more sentence in a skill are refused under rule 12 and under the context-engineering guidance for this model generation, which both say the same thing from opposite ends: the answer to an agent doing the wrong thing is a better interface, not more rules in a file that is loaded every session.
```
```yaml
decision: Three numbers this repository states as prose become exit codes
date: 2026-08-08
rationale: Eight skills, ten verbs and twenty-one assertions are stated in the installer, the README and the doctrine file, and nothing asserts any of them, so any of the three can drift while the build stays green. The test derives rather than declares: the verb table is already the only literal there is, the modules that expose an entry point are discoverable, and the skills directory can be counted. Rule 5 forbids the shape the council proposed here, which was a new module holding two literals for one consumer. Two doctor checks join them for the same reason: that the configured hooks path is the one we installed rather than merely a path with a hook in it, and that the framework's own files are not swallowed by an ignore rule a parent directory owns, which is a first-five-minutes failure on somebody else's machine that leaves them with no governance and a green doctor.
```
```yaml
decision: Uninstall restores what init overwrote, and init stops offering to overwrite what the constitution protects
date: 2026-08-08
rationale: The wiring writes the git hooks path without reading what was there, and uninstall unsets it, so a repository that had its own hooks path before us does not get it back: the no-lock-in promise is a command that leaves the repository different from how it found it. Uninstall also deletes two files by name from a hardcoded tuple with no record that we ever wrote them, so a project instruction file a person wrote by hand is removed on a verb whose whole pitch is that it is safe. The receipt is the place that answer belongs, because it already records what was written, where and at which version. In the same area, the project half of init still offers to overwrite the two files the constitution says never to touch after writing them once, and a prompt that offers a forbidden action is a rule that only holds while somebody reads carefully.
```
```yaml
decision: The record verbs stop lying in three small ways
date: 2026-08-08
rationale: spec show prints only the first directory that matches the identifier and says nothing about the others, which is the same first-match bug that made a peer product reject branches that did reference a live card. Acceptance identifiers are numbered by counting every block in the repository, so the first risk recorded against this spec is numbered eight; the number is supposed to read as the nth risk of this spec and it reads as the nth risk of the project. And the block renderer writes a rationale of any length onto one physical line, which is why the decisions in this very spec are unreadable in a diff, and a governance record nobody can read in a diff is a record nobody reviews. Three edits, all in the half of the tree that is allowed to import freely.
```
```yaml
decision: The ceiling rises once, and closes at the count that landed
date: 2026-08-08
rationale: Thirty-three lines were found as payers, and the work is several times that, so the ceiling moves for the third time in this project's life — 5,000 to 5,600, 5,600 to 5,610, and now. The commit that moves it carries the arithmetic in its message, which is the mechanism this repository chose over discipline. Two things it must not omit: the acceptance in spec 001 whose justification says the ceiling held without a raise becomes false the moment it lands, so it is renewed in the same sweep with the new arithmetic; and the raise is a prediction, so the last commit of the branch sets the constant to the number that actually landed rather than leaving slack behind. Slack under a ceiling is how the ceiling stops meaning anything, and this project has the 436,091-line receipt to prove it.
```
```yaml
decision: doctor stops checking the line ceiling, because the test plane already owns it
date: 2026-08-08
rationale: The doctor check and the ceiling test compute the same number from the same function and compare it to the same constant, and CI runs both in the same job eleven lines apart. The doctor one also refuses to evaluate anywhere outside this repository, so it has never told a user anything. Eighteen lines of duplicated assertion, deleted, and the two prose counts that say twenty-one assertions become twenty in the same commit. Keeping the test rather than the check is the right way round: the test fails the build, the check only prints, and the count it prints is derived from the table so nothing else drifts.
```
```yaml
decision: Self-protection is derived from the wiring table, and the shell branch denies by mention
date: 2026-08-08
rationale: The docstring claims the protected list cannot fall behind the wiring because it is read from the same table the installer wires from. It has fallen behind: two skill directories the installer writes to are in no protect entry, and the wheel's own policy and git-hooks directories are unprotected, so one edit to the IOC catalogue disarms the injection guard. Deriving the settings and skills columns from the table deletes five literals and closes both holes, and it makes the docstring true instead of aspirational. The shell branch stops enumerating write verbs, which is a list nobody can finish and which a copy, a dd, an install, a truncate or a one-line Python program already walks past, and starts denying any command whose raw text names a governing path. A short carve-out keeps the read-shaped forms allowed, and the carve-out falls behind towards denying too much rather than too little, which is the direction a guard is allowed to fail in.
```
```yaml
decision: A packaged guard denies in CI, and the payload is the cheapest guard we own
date: 2026-08-08
rationale: The install matrix builds the wheel, installs it and runs five verbs on three operating systems, so the CLI half is genuinely proven from the artifact. No guard has ever been executed from it. That matters because the layout under site-packages is not the layout in the checkout: the shipped-path helper resolves differently and the IOC catalogue is reached by a different relative walk, so the packaged guard is the one configuration nobody has ever run. The no-verify guard is the payload because it is pure pattern matching, needs no fixture, no network and no scanner, and it sits second in the pre-tool table so only self-protection runs ahead of it. The guards path is already printed by the doctor call the matrix makes and thrown away; it stops being thrown away.
```
```yaml
decision: A record block that cannot be parsed is undecidable, never invisible
date: 2026-08-08
rationale: The block reader catches a parse failure and continues to the next block, so an acceptance with slightly wrong YAML vanishes from the expiry check that pre-push and doctor both read, and the gate goes green over an expired risk. Silence on a parse failure is the exact shape of a false green, and this product is sold on not producing them. The reader raises, the callers that already know how to say could-not-evaluate say it, and doctor reports undecidable rather than ok. The alternative considered was a schema, which is a validator for a file format we also own and would have cost ten times as much for the same one bit of information.
```
```yaml
decision: The install signature is the dispatcher's own path, not the project's name
date: 2026-08-08
rationale: An entry is judged ours by looking for the hyphenated project name inside its JSON, and that string can only arrive from the interpreter path, which spells the package with an underscore under a wheel. It works today because uv tool and pipx put the hyphenated name in the path of the interpreter they create; it is false everywhere at once for anyone who installs with pip into a venv named something else, and then init duplicates its row on every run, uninstall leaves every guard wired while reporting there was nothing of ours, and doctor reports no entry against a live install. The signature becomes the dispatcher file name and nothing more — the basename, never the absolute path, because the check that catches an entry pointing at another install works by asking whether the mark is present while the install path is not, and a mark that contains the install path makes that check unable to fire, which would be deleting a control while claiming to fix one. There are five comparison sites and one place the old string is rendered into text a person reads, where a surface hashes the handler it approved, so the display string stays where it is under its own name and only the comparison moves. Rule 4 applies to the swap: hard, no dual-marker fallback, and it is named in the release notes for the tag, this repository having no changelog file to write it in.
```
```yaml
decision: Reviving the loop guard is two edits, and the fingerprint stays as it is everywhere else
date: 2026-08-08
rationale: The loop cache on this machine holds 358 state files, each 48 bytes and one entry long, because session_id is minted per process; and even with a stable session the repeat arm counts a fingerprint that carries tool_use_id, which a real surface varies on every call, so three identical calls are three distinct keys. The dispatcher adopts the session the surface already sends and the repeat arm keys on the tool and its input instead. What is refused is the normalisation the council proposed on top: collapsing digit runs and path tokens would make three ordinary file reads one signature and deny the third, which is the negative control this repository already ships. Two edits, and the fingerprint keeps carrying tool_use_id everywhere else, because that was a deliberate decision in spec 001 and nothing here reverses it.
```
<!-- ai-eng decide writes yaml blocks here -->

## Accepted risks

```yaml
id: R-003-04
finding: install-path-coverage-is-one-of-two
severity: medium
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2026-11-08
renewals: 0
justification: The matrix installs one way, and that is the way under which the identity bug in this spec cannot appear, so the fix for it is verified by a unit test rather than by the matrix. Adding a second install leg costs more than the signal it buys while the package declares no dependencies.
follow_up: Add the second install leg the first time a user reports anything that differs between the two, and until then keep the unit test that pins the signature.
```
```yaml
id: R-003-03
finding: dispatcher-payload-dialects-untested
severity: medium
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2026-11-08
renewals: 0
justification: The dispatcher normalises three spellings of the same payload and the adversarial harness only ever emits one of them, so two thirds of that translation layer is unexercised. Driving the real surfaces is what would actually prove it, and three of them report unproven for the same honest reason already recorded against spec 001.
follow_up: Fold the three spellings into the dispatcher test that already spawns the dispatcher five times, and flip a surface to proven only when a denial has actually executed there.
```
```yaml
id: R-003-02
finding: zero-lines-of-margin-under-the-ceiling
severity: low
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2026-11-08
renewals: 1
justification: The ceiling moves a second time in this spec, which makes the previous acceptance's line about it holding without a raise false, so it is renewed here rather than edited there. The payers were found rather than invented and are named in the plan, and the closing commit sets the constant to the count that landed so no slack is carried.
follow_up: The next commit that needs lines deletes first. The named candidate remains the OTLP exporter, which is dormant until somebody configures a destination.
```
```yaml
id: R-003-01
finding: read-carve-out-is-a-list
severity: low
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2027-02-08
renewals: 0
justification: Denying by mention needs a short list of read-shaped forms so that reading and staging a governed file stay possible, and any list of forms can fall behind the shells people actually type. It fails towards denying a read that should have been allowed, which is a person told to use the read tool, rather than towards allowing a write that should have been denied.
follow_up: Delete the carve-out entirely if the read tools cover every case in practice, and never widen it to a verb that can write.
```
```yaml
id: R-003-05
finding: structured-denial-not-observed-live
severity: medium
accepted_by: the maintainer
accepted: 2026-08-09
expires: 2026-11-09
renewals: 0
justification: The denial protocol is now surface-specific and Claude Code receives the structured
  PreToolUse decision on exit 0 rather than JSON it ignores under exit 2, which is the documented
  answer for that surface and the one the observed silent stops point at. What has not been done is
  the live check: driving one real Claude Code session into a denial and recording that the next
  event is an assistant action rather than a turn ending. The test plane proves the shape of the
  reply and cannot prove what the model does with it.
follow_up: Run one live denial on the minimum supported Claude Code and on the version that produced
  the report, and record the next event. If either still stops, add a one-shot Stop recovery tied to
  that session and prove it cannot loop — never another instruction in stderr called continuation.
```
<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
