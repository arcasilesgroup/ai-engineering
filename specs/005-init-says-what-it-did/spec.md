---
id: "005"
slug: init-says-what-it-did
status: draft
date: 2026-08-08
ref: ""
supersedes: ""
---

# What `init` says it did, and what it did

## Context and problem

A stranger ran `ai-eng init` inside a git repository created thirty seconds earlier, with
nothing in it. The installer wrote four files, printed a tick beside each one, and then,
four lines further down the same screen, offered to overwrite all four because they
"already exist and are not ours". Both halves of that screen cannot be true. The second
one is the wrong half, and it is the wrong half in the one prompt in this product that
destroys a file.

The cause is one line in the wrong place. `project_step` writes the offers that are
missing, and only afterwards asks the disk which offers already existed, so every file it
has just created answers yes. This is already known: `tests/test_mut_init.py:494` carries
a strict `xfail` naming the defect and its cause in one sentence. Nothing else in the
suite is red, which is the point — the defect is pinned, dated and shipped.

That is where the report from the user stopped, and it is not where the problem stops.
Reading the verb properly, and running it, turned up six more, and every fact below was
observed by running something rather than by reading it.

**One. The overwrite prompt loses input silently.** Driven directly, `1, 2` — two files
named, with the comma the same command's own `--overwrite CLAUDE.md,justfile` teaches —
selects only the second file and says nothing. `1,2` selects nothing. `all` selects
nothing, though `--overwrite all` is a valid spelling of the same intent in the same
command. `1 9` selects the first file and drops the nine without a word. The parser is
`input().split()` filtered by `isdigit()`, and the two spellings of one intent resolve
differently five lines apart in the same function.

**Two. `--dry-run` claims writes it did not make.** Its help says "print the checklist,
write nothing". The writes are guarded; the printing is not. A dry run emits
`✓ CLAUDE.md backup → CLAUDE.md.bak-… written` and `✓ CLAUDE.md written` having written
neither. The test asserts the files are absent and never that the output stopped saying
otherwise. On a repository with nothing in it, the mode whose entire promise is a
checklist is the one mode that prints no checklist at all, because the offers it would
list were never written.

**Three. The pin is rewritten in silence.** `ai-eng init --project <path>` asks nothing —
the question is short-circuited when the flag carries a value — and rewrites
`.ai/config.toml` and `.ai/.gitignore` unconditionally. A hand-edited pin goes back to
defaults with no backup and no line of its own in the output. The four root files each get
a dated backup; the one file this project's own vocabulary calls *the pin* gets none.
`CONSTITUTION.md` line 37 says a change of governance is never silent, and this is the
file that names which version governs a repository.

**Four. The installer advertises a `doctor` feature that does not exist.** When you
decline to overwrite, it prints "`doctor` lists them as unmanaged, which is a valid
state". The word *unmanaged* appears zero times in `doctor.py`, and none of the twenty-one
assertions looks at those four files. It is the sentence a person reads in order to decide
not to overwrite, and it describes a check nobody wrote.

**Five. Four of the eight surfaces detect themselves.** A surface is found when its detect
path exists. Linking the skills creates the parent of the skills root. For OpenCode the
detect path is `~/.config/opencode` and the skills root is `~/.config/opencode/skills`;
for pi it is `~/.pi` against `~/.pi/agent/skills`; for Zed it is `~/.agents` against
`~/.agents/skills`; and VS Code Copilot's detect path is `~/.claude/settings.json`, a file
we write ourselves. So one `init` makes the next `init` find surfaces that were never
installed, writes an OpenCode plugin onto a machine that has never had OpenCode, and then
`doctor` reports that plugin as never having loaded — which is true, and which turns the
doctor permanently red on a machine whose only sin was running the installer twice. The
doctor's own docstring says a doctor that comes out red by construction is a doctor
somebody silences forever.

**Six. Three checks pass by iterating an empty list.** Decline the machine half, or pass
`--no-global`, and the project half still wires the repository: `core.hooksPath` is set,
`ai.managed` is set to true. The receipt is never created. The three assertions that read
the receipt and the detected surfaces then loop over nothing and report ok. The result is
a governed repository on a machine with no guards installed, and a green wiring section
that earned nothing.

**Seven. The repository is left one commit away from a wall it is not told about.**
Wiring a project sets `ai.managed=true`, and the shipped `pre-commit` exits 1 when that
flag is set and `gitleaks` is not on the path. So `ai-eng init` on a machine without
gitleaks refuses every commit in that repository from then on, and the first the person
hears of it is their next commit. Nothing in `init` looks for the binary, and no assertion
in `doctor` asks whether the tools this repository needs are present.

Underneath the seven sits the complaint that started the reading: that the previous
version of this product felt better to install. Measured, the shape of that feeling is not
what it looks like. The old installer asked **one** question — a checkbox over surfaces,
plus a second one only when it could not tell which forge you used. This one asks three.
What the old one had and this one does not is the last screen: a panel that said how many
files were created, how many hooks were installed, what was still pending, and a numbered
list of what to run next. This installer ends by pasting a block of YAML at the reader and
stopping. The thing being missed is the report, not the picker.

## Options considered

**1. Port the old installer's shape.** An arrow-key selection widget, a `doctor --fix`,
and the offer to install missing binaries. Ground-truthed against both trees, this costs
roughly four hundred to six hundred lines and buys three problems. The widget is a
general primitive with exactly one caller, over a list capped at four rows, whose
Windows branch no job in this repository would ever execute — an unproven green by
construction. `doctor --fix` is worse than expensive: two of its four plausible repairs
are writes `init --project` already performs, and the third rewrites the pin, which is
`ai-eng update` with all three of its consent gates — a pinned repository, a clean tree,
and a keyboard — removed, wearing a diagnostic verb's name. Installing a binary requires
guessing between four package managers on four platforms, and a guess that goes wrong
either changes somebody's machine unasked or does nothing quietly. It is also a contract
this module states it does not have, in its own first paragraph.

**2. Fix only what is observably false, and add the one screen the old one had.** Every
item above is a statement the software makes that is not true, or a green that was not
earned. Correcting them is small and local: one line moved, one parser unified with the
one beside it, one sentence deleted, one data file edited, three checks taught to say
*could not evaluate* instead of *ok*, and two `which`-shaped warnings. The report is
fifteen lines of the same output primitives the banner already uses. Against the estimate
in option 1 this lands between one hundred and eighty and two hundred and forty lines
including tests, and it deletes a strict `xfail` and its reason on the way.

**3. Fold it into spec 003 and write nothing here.** Spec 003 already decides that init
stops offering to overwrite the two files the constitution protects, that uninstall
restores what init overwrote, and that the ceiling rises once and closes at the number
that landed. Three of the seven failures above touch code 003 is opening anyway. This
option is real and it is cheap, and it loses because 003 is a sweep of seven guards that
never fired and its subject is enforcement; four of the seven items here are about what
the installer *says*, which is a different failure with a different reader, and burying
them inside a spec about guards is how the second half of the mission — doing nothing
silently — stops having a home of its own.

## Decision

Option 2, with 003 as a hard dependency rather than a sibling.

Every item is a false statement the product makes about itself, and the mission names both
halves of that: doing harm silently, and doing nothing silently. Four of the seven are the
second half exactly — a checklist that lists files it wrote, a dry run that reports writes,
an installer that cites a check nobody built, three assertions that pass on an empty set.
Two are the first half: a pin rewritten with no record, and a repository wired into a wall
it is never told about. One, the self-detection, is both at once: it manufactures the
surface and then reports the surface it manufactured as broken.

Option 1 is refused in full and in writing, so the same four candidates do not come back
in six months. **No selection widget**: the list is four rows and is structurally capped at
four, the default already destroys nothing, an overwrite is already copied to a dated
backup first, and the demonstrated defect is a parser that loses input — which one line
fixes and a widget merely hides. **No `doctor --fix`**: `doctor` is twenty-one assertions
and a coverage line, and a doctor that mutates is `init` and `update` behind a third door
with the consent removed. What the `--fix` proposal was actually reaching for is that no
check message in the file names a command to run; appending the command to the four
messages that have one delivers the whole of the user-facing value for four words apiece.
**No binary installation**: a control you cannot watch fire is not a control, and four
package-manager branches nobody runs is that. The honest half of the same idea — say what
is missing, and say what it will cost you — is decision seven. **No per-surface uninstall**:
nobody has asked for it, and it cannot be built correctly today because the receipt has no
delete path, so removing one surface would leave it recorded forever and turn the receipt
into a record that misstates the present.

Two things this spec does not do, deliberately. It does not touch `uninstall` — the
OpenCode crash and the hooks-path restoration are 003's, and duplicating them is how two
branches produce one conflict. And it does not raise the ceiling: 003 already decides the
ceiling rises once and closes at the count that landed, so this work is arithmetic inside
that raise and its numbers go into that commit's table, not into a second one.

Rule 10, one line each. **KISS** — the reported bug is one line moved, and the fix is
allowed to stay that size. **YAGNI** — the widget, the `--fix` flag, the tool registry and
the per-surface uninstall are four features built for a problem nobody here has had, and
all four are refused above. **DRY** — the typed reply and `--overwrite` stop being two
parsers for one intent, and self-detection stops being a second opinion about which
surfaces exist. **SOLID** — the detect paths move in `policy/surfaces.toml`, which the
table already owns, and no code learns a special case. **TDD** — each task names the check
that is red before it and green after; the first one deletes a strict `xfail` whose XPASS
is itself the proof. **Clean Code** — three checks stop answering a question they were
never asked, and say *could not evaluate*, which this doctor already has a state for.
**Clean Architecture** — nothing here crosses the line: `hooks/` is untouched, and every
change lands in the half of the tree that may import freely, or in a data file.

## Decisions

```yaml
adr: 0002
title: Diagnostics never repair; a check names the command that fixes it
```
```yaml
adr: 0001
title: A surface is detected only by a path we never write
```
```yaml
decision: init stops describing a repository it just wrote
date: 2026-08-08
rationale: existing() is called after the loop that writes the missing offers, so on a new repository all four skeletons are classified as files that already existed and are not ours and are offered for overwrite on the same screen that reported writing them, which is a strict xfail in the suite today and is deleted in the same commit as the fix; the typed reply joins the same parser as --overwrite so that a comma stops selecting one file in silence and all stops meaning nothing, one line names whatever it ignored, the sentence promising that doctor lists these files as unmanaged is deleted because the word appears nowhere in doctor, and the backup name gains sub-second resolution so two overwrites inside one second stop destroying the first backup.
```
```yaml
decision: A dry run stops claiming writes it did not make
date: 2026-08-08
rationale: The writes are guarded by the flag and the printing is not, so a dry run reports a backup written and a file written having written neither, and the test that covers it asserts the files are absent rather than that the output stopped saying otherwise; on a repository with nothing in it the mode whose whole promise is a checklist is also the one mode that prints no checklist, because after the ordering fix the offers it would list are the ones it declined to write.
```
```yaml
decision: The pin is never rewritten without a record
date: 2026-08-08
rationale: init --project with a value asks nothing and rewrites .ai/config.toml and .ai/.gitignore unconditionally, so a hand-edited pin returns to defaults with no backup and no line of its own, while the four root instruction files each get a dated backup; the file this project's own vocabulary calls the pin is the file that names which version governs a repository, and the constitution says a change of governance is never silent, so a re-run over an existing pin backs it up and names it on its own line, or leaves it and says which value it kept.
```
```yaml
decision: The install ends by saying what it did and what to do next
date: 2026-08-08
rationale: The installer that was felt to be better asked one question and this one asks three, so the thing being missed is not the picker but the last screen: how many files were written, how many guard entries were placed, what is still waiting on a person, and a numbered list of what to run next, where this one pastes a block of YAML at the reader and stops; the first thing that list has to say is that the skeleton it just wrote carries TODO markers on purpose and that doctor fails on them until a person fills them in, because the alternative is a stranger pasting the CI block and watching their first build go red for a reason nobody named.
```
```yaml
decision: Three assertions that pass on an empty set stop passing
date: 2026-08-08
rationale: Declining the machine half still wires the project, so core.hooksPath and ai.managed are set on a machine with no receipt and no guards, and the three checks that read the receipt and the detected surfaces then iterate nothing and report ok; an empty loop is not a passing check, it is a question that was never asked, and this doctor already has the state for that answer, so they raise Undecidable with the reason and the run reports could not evaluate, which is never green and never red.
```
```yaml
decision: The machine is told what it is missing, and never repaired for it
date: 2026-08-08
rationale: Wiring a project sets ai.managed=true and the shipped pre-commit exits 1 when that flag is set and gitleaks is absent, so init leaves a repository that refuses every commit and says nothing about it; a which lookup at the moment the flag is written, printing the install line and stating plainly that commits are refused until the binary exists, observes one thing and claims nothing else, while guessing between brew, apt, winget and scoop is four branches no job here executes and therefore a control nobody can watch fire; the same paragraph offers git init in a directory that is not a repository, with a literal false as its default rather than the terminal test, because -y returns the default and a default of isatty would create a repository in whatever directory the person happened to be standing in.
```
<!-- ai-eng decide writes yaml blocks here -->

## Accepted risks

```yaml
id: R-005-17
finding: new-output-unproven-off-linux
severity: medium
accepted_by: soydachi
accepted: 2026-08-08
expires: 2026-10-07
renewals: 0
justification: the closing report, the gitleaks warning and the git init offer are all interactive or terminal-shaped, and the only job that runs init on macOS and Windows drives it with -y, which returns before every prompt, so these paths ship exercised on Linux alone; the coverage line already reads UNPROVEN for surfaces in the same situation and this is the same honesty applied to output
follow_up: either the install matrix grows one non-interactive assertion per platform for the report, or this is renewed once with the reason and then fixed
```
```yaml
id: R-005-16
finding: backup-files-accumulate-untracked
severity: medium
accepted_by: soydachi
accepted: 2026-08-08
expires: 2026-10-07
renewals: 0
justification: every overwrite leaves a dated .bak file at the repository root, nothing ignores them, no verb removes them and git add -A commits them, and this spec only makes the name collision-proof rather than cleaning them up; the blast radius is clutter in somebody's first commit rather than lost work, because the backup is the recovery path and deleting it automatically would be worse
follow_up: decide whether the managed .gitignore covers the pattern or uninstall removes them, and record it as a decision here
```
```yaml
id: R-005-15
finding: init-overwrite-all-bypasses-constitution
severity: high
accepted_by: soydachi
accepted: 2026-08-08
expires: 2026-09-07
renewals: 0
justification: init --project --overwrite all -y still overwrites AGENTS.md and CONSTITUTION.md with no typed confirmation, which the constitution forbids after they have been written once, and this spec deliberately does not fix it because spec 003 already decides that init stops offering to overwrite the two files the constitution protects; the risk is that 003 slips and the violation ships with this work
follow_up: spec 003 lands, or this spec absorbs the two-file refusal and this acceptance is withdrawn rather than renewed
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
