"""The contract every SKILL.md meets, checked by a script rather than by taste.

The open standard defines six portable fields and treats anything else as a hard error
on the packaged-distribution path. This allows those six plus exactly three Claude Code
extensions and nothing else. The portability cost is paid deliberately and named in the
README: these files are not uploadable to claude.ai as-is, and the alternative is a
per-surface rewrite layer, which is the machinery this product exists to delete.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ai_engineering import text

SPEC_FIELDS = {"name", "description", "license", "compatibility", "allowed-tools", "version"}
EXTENSIONS = {"disable-model-invocation", "context", "background"}
JARGON = (
    "leverage",
    "utilise",
    "utilize",
    "synergy",
    "robust",
    "seamless",
    "delve",
    "holistic",
    "best-in-class",
    "cutting-edge",
)
CEILING = 80
DESCRIPTION_MAX = 1000

# The line ceiling, in one place so raising it is a single reviewable edit. 5,000 to 5,600 in
# specs/001; 5,600 to 5,610 for the test plane named in that commit, while the product itself
# lost nine lines; 5,610 to 5,764 for four controls that reported green while doing nothing —
# a plan gate any plan ever written satisfied, a repeat rule counting an identifier that is
# unique per call, two dispatcher rows naming a payload key no guard read, and a git hook that
# refused every push when an older CLI answered on the PATH — plus the measurement plane that
# stops the next one hiding; and 5,764 to 8,441 for the test plane the operator asked for, at
# his own decision and after being shown the counter-argument. That last move is 2,660 lines,
# nearly half this repository, and the honest accounting is that it bought 95% branch coverage
# rather than the 80% asked for, and nine defects nothing else had found — one of which put a
# broken CI workflow in front of every user this tool has ever initialised. The test plane is
# now larger than the product. That is a fact about this ceiling, not a defence of it: the next
# commit that needs lines deletes a test that kills no mutant — and there is now a command that
# says which those are. 8,441 to 8,661 for it: mutmut over the package, a hand-written runner
# over the guards mutmut cannot import, and a floor that fails the build. It bought the number
# the coverage percentage was hiding — 95% of lines run, 59% of deliberate defects caught.
# 8,661 to 11,587 to answer that number: five suites, 2,549 lines, which took the mutation
# score from 59% to 89% and found four more defects on the way, including a mutation gate
# configured by a list of four filenames that silently excluded every test file written
# after it. Two of the fifteen modules have no suite yet, and their 197 survivors are the
# six points between 89 and the 95 that was asked for. The test fails the build on the
# line after.
#
# 11,587 to 12,017 happened with no line here: the last figure this comment named and the
# constant under it disagreed by 430, which is this comment's own failure mode, one level up.
# 12,017 to 12,686 for spec 005 — thirteen defects in `init` and `doctor`, every one of them a
# statement the software made about itself that was not true, or a green nobody had earned.
# 466 of those lines are test against 154 of product, three to one inside a branch on a tree
# the ratio gate caps at two to one, and that shape is the work: four of the seven reported
# defects had a test sitting beside them asserting the wrong half, and one carried a strict
# xfail this branch deleted. 116 of the 466 were not planned at all — the mutation floor went
# red at 88%, and what it had caught was two new screens asserted by fragment, where every line
# the fragment did not name could be emptied with the suite still green. The other 35 lines are
# package.json and tsconfig.json, an in-flight lane of the operator's that this branch's first
# commit swept up out of an index that already held them — named here rather than absorbed,
# because a ceiling quietly carrying somebody else's lines has already stopped meaning anything.
#
# 12,686 to 13,671 for spec 006, which is the screen rather than the truth on it: the
# operator installed 005, ran the two verbs in a terminal and said it was still just as
# ugly, and he was right — 005 changed what the software claimed and nothing about how any
# of it is drawn. Measured against the version he prefers, the gap was 1,368 lines of
# presentation layer that version has and this one did not, so this buys the two
# dependencies it used and one module that owns the ticks, the widths, the theme and the
# two streams. 139 of the total is uv.lock, which the first runtime dependencies this wheel
# has ever had brought with them, and 409 is that module and its suite. What it also bought
# is a defect: doctor was printing nine section headings for six families, which is not
# taste and was most of what "ugly" meant. 176 of the total are the tests the mutation
# floor asked for after going red at 86%: a renderer's mutants are style names, and the
# suite drives the undecorated path where a style name is invisible.
#
# 13,671 to 14,590 for spec 007, and 31 of those are not spec 007's: the tree carried spec
# 003's uncommitted work when this branch started, and a ceiling that quietly absorbs
# somebody else's lines has stopped meaning anything. 879 is this spec, measured, and 9 is
# this paragraph. 006 drew the screens and this one makes them answerable: the operator ran
# the two verbs again and asked, of six screens in turn, what he was supposed to do about
# what they said. A cure stops being a sentence at the end of a message and becomes a field,
# which is what lets `--fix` invoke the verb that already carries the consent — ADR 0003,
# superseding 0002 three days after it.
#
# 552 of the 879 are tests against 327 of product, and where they came from is the part
# worth keeping. 106 were planned. The mutation floor found 358 more, nearly all of one
# shape: a style name and a stream flag are invisible to a suite that reads undecorated
# stdout, so every line of new screen could be emptied of its colour or written to stderr
# with the whole thing green. An adversarial review of the finished branch found the last
# 88, and two of those were defects rather than gaps — a last screen promising the guards
# were loaded over its own row reading `0 guard entries`, and `--fix` reaching `init`'s
# unconditional rewrite of `.ai/config.toml`, which is `update` with its three consent
# gates removed and is the exact objection ADR 0002 raised. The pin is written once now
# and never rewritten, which reverses a decision spec 005 made in the other direction.
#
# 14,590 to 15,100 for specs 002 and 003 together, and this is the fourth move. 68 of it
# has already landed: the work-item paste deleted with its four tests, a changelog this
# repository has owed rule 4 since rule 4 was written, the renewal that retires what it
# renews, three lines in the hooks that never ran, the session the dispatcher now adopts
# and the loop guard's two arms. 205 more is predicted for what is left — the false green
# on a malformed record block, the install signature that is an accident of how the tool
# was installed, uninstall's crash on any machine with OpenCode, self-protection derived
# from the wiring table, a denial that does not end the agent's turn, a mutation run that
# cannot reach the operator's home, a packaged guard exercised in CI, and the three numbers
# this repository states as prose. 237 is slack, and it is deliberate rather than sloppy:
# the one prior estimate on file in this project overran by ninety per cent, and a ceiling
# that goes red two thirds of the way through a branch blocks every commit after it with
# this project's own gate. The closing commit of that branch sets this constant to the
# count that actually landed, so none of the slack survives it. 15 of the 68 are this
# paragraph.
#
# 15,100 to 15,700, four commits later, and the honest note is that the estimate above was
# short. 457 of the 205 predicted had landed by the time the record verbs were reached —
# the guards' own tests are most of it, and they are the half of that work nothing else
# would have caught. What is left is the denial protocol, the mutation worker's disposable
# home, uninstall restoring what init overwrote, the record verbs, the packaged guard in
# CI and the three numbers this repository states as prose. This raise is measured against
# the same overrun rather than against the same optimism: 250 predicted, and the rest is
# slack the closing commit takes back.
#
# Closed at the count that landed: 15,615 against the 14,590 those two specs started from,
# so 1,025 for work priced at 273 across two raises. No slack survives the branch, which is
# the only thing that keeps a ceiling meaning anything, and this repository has the
# 436,091-line receipt for the alternative. Where the other 750 went is one sentence, and it
# is the same sentence both times: the five guards had almost no tests of their own — they
# were attacked by the adversarial suite and asserted nowhere else — so eighteen measured
# shell commands against self-protection, ten hooks-path spellings, three loop arms and two
# denial protocols are most of the overrun. The honest reading is that the estimate priced
# the fixes and not the evidence for them.
#
# 15,615 to 15,663, and this one is a correction rather than a spec: closing 003 at the
# measured count did not mean 003 was finished. An audit of every spec in the tree found
# two things it had left — the adversarial harness's docstring still said twelve attacks
# over a registry of fourteen, which was a named task in its own plan; and `just mutate`
# was red at 13 of 14 because moving the repeat arm off `signature()` left that function's
# only rule, truncating a path from its tail, with nothing behind it. A rule with no test
# is the shape this whole spec was about, so the test is the payer's opposite: 48 lines,
# nine of them this paragraph, and the ceiling says so rather than absorbing them.
#
# 15,663 to 15,689, and the payer is spec 006's one unmet check finally being met. That
# spec added the first runtime dependencies this wheel has ever had, and its plan said the
# lane that scans them had to be seen to fail on a planted advisory or the mitigation in
# its accepted risk was itself an unproven claim. It never was: the workflow still carried
# "zero declared dependencies today, so this finds nothing today" over seven packages, and
# the Snyk job still explained its SAST-only shape by an empty requirements file. Both
# comments are now what is true, and the audit step gained the assertion the observation
# argued for — `pip-audit --strict` over an empty export exits 0, so the export is checked
# against the declared dependencies before the audit is allowed to report anything. Fifteen
# lines of workflow, eleven of this paragraph, and no slack.
#
# 15,689 to 15,712, and this one is rule 4 being paid rather than a feature. Spec 007 removed
# two behaviours a person could have been relying on — `init --project` rewriting the pin on
# every run, and the CI workflow being printed at the reader to paste — and neither was ever
# written down in CHANGELOG.md, whose own first paragraph says every hard delete goes in it in
# the words somebody upgrading would search for. Fifteen lines of changelog, eight of this
# paragraph. The dependencies spec 006 added are not in there, and that is deliberate: adding
# one is neither a rename nor a delete, and that file says what it covers.
#
# 15,712 to 16,803 for spec 008. The payer is what `ai-eng uninstall` followed by `ai-eng
# init` prints: "Global ready · 8 skills, 4 links, 4 guards" over a machine measured at zero
# guards and zero of our symlinks. The receipt is an append-only log of writes that both
# verbs read as the state of the machine — it cannot shrink because uninstall never wrote
# it, and it under-reported too, because `update` rewired surfaces and recorded nothing.
# Underneath sat the one that loses data rather than lying about it: read_json returned {}
# on a parse error, so an interrupted write made the receipt empty to every reader and the
# next record() stored that emptiness — measured, three rows in and one row out — and the
# same line under the three settings writers replaced a ~/.claude/settings.json carrying a
# JSONC comment with our hooks block alone, under a line of output reading `(merged)`.
#
# 1,092 landed against 840 predicted — thirty per cent over, against 005's eight hundred and
# seventy and 007's seven hundred and thirty. 27 of it is four breaking-change entries rule 4
# had been owed since the first of them landed, and 175 is the mutation floor, which the plan
# named as the binding gate with nothing to give and which went red at 88%. Of the 543
# survivors 96 were in `uninstall`, at 74% against a tree at 89: the new code was a third of
# the survivors on a twelfth of the lines. What killed them is what killed spec 006's: the
# screen asserted whole rather than by fragment, a count asserted as a number rather than as
# a line that has one, and a fate table with a row for every kind there is. What could not be
# killed left instead — `timeout=10` and `capture_output=True` written at three call sites
# are six mutants no honest test can reach, so they became one function, which is the same
# exit spec 006 took for `soft_wrap=True`. Nine of the fifteen tasks changed a test
# that was pinning the defect rather than adding one — fixtures made of paths that never
# existed (`/a`, `/b`, `/c`, `/somewhere/settings.json`), vendors' directories standing in
# for wired surfaces, and one passing assertion that an install destroys a settings file
# whose own docstring said "this pins the loss; it does not bless it".
# 16,803 to 17,011 for spec 009, and this is the first raise bought entirely by things that
# were already wrong. The total sat at exactly the ceiling, so the first line of the first fix
# failed the build — which is the ceiling working, and the reason this paragraph exists rather
# than a quiet edit. 44 is the buffer stamp: an event written by a guard sat unhashed in the
# clone until the session ended, so an agent that had just been blocked could rewrite its own
# denial into an allow and `ai-eng audit verify` reported the chain intact. 43 is the Unicode
# fold and the twelve-variant recall measurement R-001-04's follow-up asked for by name, at 9
# of 12 caught where the raw catalogue caught 0. 34 is the install matrix finally running
# `doctor --fix`, the closing report, the copy branch of `wiring.link` and an uninstall
# assertion that is not also true of a run that removed nothing — four accepted risks whose
# cures had been written down and never wired. 30 is changelog, which is rule 4 being paid for
# three breaking changes in the same batch. 21 is the guard count pinned against the dispatcher
# table, after "eight guards" and "five guards" had lived eight lines apart in the same
# doctrine file with nothing asserting either, and one attack sent through the real dispatcher
# in all three payload dialects. 16 is `doctor --fix` no longer typing a person's answer and
# `just changed` no longer dropping five of eleven suites in silence. Twenty is this paragraph.
#
# Two fixes cost nothing and are worth naming for it: `audit.read` and `spec.next_number` came
# to net zero, because the strict-xfail markers they retire are longer than the guards that
# replace them. That is what a defect with an alarm on it is supposed to cost when it is paid.
#
# 17,011 to 17,041, and the payer is the mutation floor, which went to 88% against 89 and
# named the five survivors: `parents=True` in the new backup path, which every test reached
# with `.ai/` already there, and the `len(words) > 1` guard in `unattended`, which nothing
# handed a one-word or a two-word cure. Twenty-three lines of test for five mutants is the
# floor doing exactly what it is for — the survivors were both in code written this week, and
# seven of the thirty are this paragraph saying so.
#
# 17,041 to 17,063, and this one was bought by being wrong in public. Spec 009 recorded, as
# a decision, that the survey's claim about `extractions/setup-just` was false and that the
# branch had simply never been pushed. The branch was then pushed and `check` came back
# startup_failure with no jobs and no logs, while `install` — the same runner, three actions
# fewer — ran green. This repository allows GitHub-owned actions and nine explicit patterns,
# `verified_allowed` is false, and `extractions/*` is not among them; `dorny/*` works on main
# because it is listed by name. `just` now arrives from PyPI through the uv that is already
# set up, here and in the workflow `init` writes into other people's repositories, because
# shipping an action our own gate cannot run is shipping a startup_failure to a stranger.
#
# 17,063 to 17,115, and the same runner found the next one. The Windows leg of the install
# matrix — also running for the first time — ended `ai-eng spec new` in a UnicodeEncodeError
# with the spec already on disk: Windows hands a bare `print()` a cp1252 stream and the tick
# in that verb's success line is not in cp1252. Eleven print() calls across six verbs carry a
# glyph, and the styled screens never had the problem, which is why every local run and every
# Linux job was green. The streams are reconfigured once at the CLI's entry rather than at
# eleven call sites, and the regression test builds a cp1252 stream and reproduces the exact
# traceback without it. Both of these were found by pressing push, which is the argument the
# spec makes for pressing it before the list is perfect rather than after.
#
# 17,115 to 17,149, and the third and fourth things the first CI found. The `typecheck` job —
# required by CI Result and never once executed — reported nineteen errors, eighteen older than
# this branch. Five were ui.py failing to import `rich` and `questionary`, because the job ran
# mypy with `--no-project` and never installed them: a type check that had never seen the
# types. The rest were real and are fixed rather than silenced, which rule 3 does not leave as
# a choice: five assertions annotated `-> str | None` that return a cure alongside the
# message, two containers with no element type, a `re.search` result indexed as a list, an
# `except ... as why` whose name Python deletes and a loop below it that read it anyway, and a
# spec that was `Path | None` on a path that cannot take None. Nineteen of the twenty-nine
# lines are that work; twelve are this paragraph. The fourth is one line: actionlint runs
# shellcheck over every run: block and is a step only CI has, so an `ls` piped into `head`
# in the install matrix — there since the first commit — had never been read by anything.
#
# 17,149 to 17,175, and the fifth. `ai-eng doctor --ci` cannot pass on a runner, and could
# never have: assertion 9 demanded a dated result from the adversarial suite's real-model
# half, which needs an API key and somebody's spend and is accepted as not shipping under
# R-001-02, so the field it reads can never exist there. It said "no dated green result in
# the last 7 days" for a half that had never run at all. Never run and gone stale are
# different answers, and this file already has the state for the first one. Eight of the
# twenty-six lines are the changelog entry, because softening a gate is a thing a person
# upgrading has to be told, and eight more are the note under the risk that grew it.
#
# 17,175 to 17,588 for the npm lockfile the clean-checkout mutation proof requires. The
# package manifest was tracked while its dependency graph was ignored, so local npm used a
# file CI never received and the proof stopped before it tested any mutant. 408 lines of
# generated lockfile minus the deleted ignore is 407; these six lines record the move. It
# buys reproducible installs and makes the audit see the same graph everywhere. No slack.
#
# 17,588 to 17,746 for the receipt boundary the first remote security scan found. A receipt
# could name any file or directory and uninstall treated that claim as ownership, including
# rows the screen said it would keep when another valid row let the loop run. 68 lines make
# destinations a closed set and restore git config with an option boundary; 84 test them.
# These six lines account for the move. No slack survives the fix.
#
# 17,746 to 17,754 for three data writes the remote analyzer read as path construction. Its
# flows trace document content, not the destination, into Path.write_text and report the
# content as a path argument. Writing through an already-open handle keeps the exact bytes
# while making that boundary unambiguous. Three product lines and these five; no slack.
#
# 17,754 to 17,810 for the gate reader the first passing Sonar scan finally reached. The
# assignment endpoint now requires an organization and returns the gate identity without
# its conditions; the old one-call reader received HTTP 400 and could never prove the live
# policy. 24 script lines, 27 test lines and these five record the repair. No slack.
#
# 37,807 and 42,807 are history only: each was the approved limit before the one below.
#
# The acceptance wave replaces the embedded-YAML risk writer with immutable published
# records. Its budget is measured, not guessed, and every rate below names the commits it
# came from:
#   789 per commit — the native transaction wave, 3,154 lines over 0683cdec..75939c75.
#   304 per commit — this wave's own measured rate, 3,642 lines over e4c118bd..d916e0ae,
#                    which is twelve observations of exactly this kind of work and is
#                    therefore better evidence than the 789 the plan forecast from.
#   284 per task   — Tasks 17-39, 6,530 lines over 23 tasks.
#   393 per repair — the three landed ledger repairs, 575 + 425 + 180.
#     1 per record  — Task 39a, which rewrote this comment and added one line.
#
# Measured base at this commit's parent: 38,534. Recomputed from it:
#   5 remaining wave commits at 304        = 1,520
#   Tasks 40-52, 13 at 284                 = 3,692
#   Tasks 52a-52c, 3 at 284                =   852
#   Task 53 at 284                         =   284
#   5 block reviews, 2 repairs each at 393 = 3,930
# 38,534 + 1,520 + 3,692 + 852 + 284 + 3,930 = 48,812, which is 6,005 above the 42,807
# this replaces. Measured at the close: 42,579 — 6,233 under that forecast and 228 under
# the 42,807 it replaced. The arithmetic over-predicted by an eighth, and recording that
# is the only thing that makes the next forecast worth reading.
# The approved budget was anchored to the original baseline:
# 17,807 + 38,000 = 55,807, approved against a 54,695 forecast before the wave was
# measured. The wave then came in far under it, and 13,000 lines of unspent contingency
# is not a budget, it is a licence — so the final candidate transaction does what the
# plan said it would and closes the ceiling onto the tree it measured, with zero slack.
#
# What that costs, stated plainly because a future reader will meet it as an obstacle:
# the next line added anywhere in this repository fails the build. That is the point. A
# ceiling with room in it never has to be argued for, and the argument is the control.
# Raising it is a commit whose message says why, and that commit is the conversation
# this file exists to force.
#
# 43,824 to 45,406, and this one is a forecast that was wrong in a way worth naming. The
# raise below budgeted three tasks and one repair and forgot that a wave also writes its
# own spec and plan: those two files are 342 lines, which is most of the overrun. The rate
# table measures tasks, so anything forecast from it and not itemised beside it is missing.
# Remaining Block A work at the same rates: 3 tasks at 284 = 852, one review round at 393.
# 44,161 + 852 + 393 = 45,406. The records are now counted where they were skipped.
#
# 42,579 to 43,824, and this is that conversation. P0 closed with no verb that transitions
# a record: a MADR moves from proposed to accepted only by hand-editing YAML frontmatter,
# and the validator additionally requires the transition to be its own commit. That is not
# a missing convenience. It is the reason this repository sat blocked for six turns waiting
# for nine values a person had to type, and it is the opposite of what the product claims
# to be for. The operator asked for it to be automatic, and the specification already names
# the shape: authority comes from an authorized human "or preapproved policy".
#
# Forecast from this file's own measured rates rather than a guess:
#   3 tasks at 284   = 852   the closed policy schema, this repository's instance, the verb
#   1 repair at 393  = 393   one review round, at the measured repair rate
# 42,579 + 852 + 393 = 43,824. The rates over-predicted by an eighth last time and are
# expected to again; the final commit of this work closes the ceiling back onto the tree
# it measures, exactly as Task 53 did, so the slack is borrowed and not kept.
# 45,406 to 45,440, and the smallest raise this file records. Block C's
# re-review reached round eleven and found that every test of the commit-msg hook set
# `AI_ENG`, so the branch that resolves the CLI from `git config --get ai.eng` — the one a
# real commit takes, and one of the two candidate causes an entire section of specs/011
# exists to account for — had no coverage at all. The test that closes it is eleven lines
# and its seam in the helper is seven; twenty-one with the docstring, and thirteen more
# for this paragraph, which is the argument the raise is required to carry and is counted
# rather than exempted.
#
# No forecast, because this is not forecast work: it is the ceiling doing what it is for.
# The alternative was to delete something else to fit, which is the failure the number
# exists to prevent, and the operator's standing instruction is to present the arithmetic
# rather than scope the work down to the figure.
# 45,440 to 45,535 for Block R Task 12, the first repair to the record's own fail-open.
# 53 lines of test, 35 of product and docstring, 6 for this paragraph. The defect it closes
# was measured on the operator's machine: `stamp()` keys off `home()/buffer.key`, which
# `AI_ENGINEERING_HOME` redirects, while the buffer is repository-local and does not — so
# every test that isolates a home wrote into the operator's real buffer with a key their
# machine could not verify, and the seal classified 22 such lines as tampering. `ai-eng
# audit verify` failed permanently and `audit --anchor` stopped emitting a footer, so no
# commit on that machine could be anchored. The one command that detects a real edit had
# been spent on an edit that never happened.
#
# Most of the 88 is the test, and that ratio is the point: the product change is a branch,
# and what it is worth is the executed proof that a foreign line no longer breaks a chain.
# 45,535 to 45,678 for Block R Task 13, which is what makes Task 12 survivable. Task 12
# stops new poisoning; it cannot touch links already sealed, because rewriting them is the
# act the chain exists to detect. So the chain still had no way back: one link sealed as
# edited and `verify` fails for good, `anchor_line` raises, and no commit on that machine
# can ever be anchored again. Measured here at 22 links, all written by this repository's
# own test suite.
#
# `audit account` answers for a named range as a *new* link, behind the same controlling
# terminal ceremony a risk acceptance asks for. Nothing is erased: the break is still
# printed, with the account beside it, and a chain whose only findings are accounted breaks
# reports WARN and anchors again. 45 of the lines are the test, 94 the verb and the
# reasoning, 5 this paragraph.
# 45,678 to 45,761 for Block R Task 14, the last of the three and the one that would have
# caught the other two. Half of "survives losing the laptop" is the seal, and nothing
# measured whether it still runs: `flush()` has one caller outside the suite, on
# `SessionEnd`/`Stop`, and when that path stopped firing this machine accumulated 4,500
# events inside the clone, outside the chain, for three days, with twenty-one assertions
# passing over it. Assertion 22 reports a buffer whose oldest line has been waiting longer
# than any session lasts. 31 lines of test, 46 of assertion and reasoning, 5 for the four
# prose counts an added assertion moves, and 6 for this paragraph.
# 45,761 to 45,812 for assertion 23. `policy/capabilities.toml` declares fifteen
# capabilities with read roots, write roots, exec allowlists, network hosts, secrets and
# human gates; `capability.preflight` validates every field and then refuses, because no
# executor exists. That refusal is honest and a test already pins it. What nothing did was
# say so — no assertion, no README line, no verb — so a reader of six governed fields per
# capability had no way to learn that none of them stops anything. A declaration nobody
# enforces and nobody flags is the shape this constitution names first among the things to
# expose. 16 lines of test, 26 of assertion and reasoning, 6 for this paragraph.
# 45,812 to 45,871 for the front door. `init` copies the skills into `home()/skills` and
# links every surface root at that store, and its own safety check recognised only
# `paths.skills()` — the source tree in a checkout, site-packages in a wheel. Neither can
# equal the store `init` just created, so `_global_paths_safe` returned False on every
# second run on every machine and the verb printed INCOMPLETE with no surface table, no
# reason and no cure. Measured on the operator's machine minutes after a successful
# install, on the exact command that had worked. 39 lines of test, 6 of fix and reasoning,
# 5 for this paragraph.
# 45,871 to 45,959 for two observability defects the P4 and P5 drafts found while measuring
# the tree, both of them a control that reads as stronger than it is.
#
# `_otlp.redact` kept the first two whitespace-separated tokens of `command`, written after
# the hashing pass so the prefix survived strict mode. The second token is the argument on
# any command that takes one: `curl https://host/?token=…` is two tokens. The one test
# guarding it used `git push <canary>`, where the canary is the third token and falls
# outside the cut — the sixth time this session a suite agreed with a defect by choosing
# the input that could not see it. The first token is the program, never an argument.
#
# And the latency check said p95 in its name and its docstring and took the median of five
# samples. Twenty samples and a real p95; the max was tried first and rejected because this
# suite runs under `-n auto` and one scheduling spike tripped it, and a bound the machine's
# load can trip is a test people learn to rerun. Measured alone: 37-45 ms.
#
# 66 lines of test and docstring, 5 of fix, 6 for this paragraph.
# 45,959 to 45,997 for the third defect the P4 draft found. `release.yml` said attestations
# ship "so `ai-eng doctor` can verify that the running wheel is the one this tag produced",
# and `grep -rn attest src/ai_engineering/` returns nothing: the workflow described a
# capability that had never existed. A header comment is where a claim hides longest — no
# test reads one, no reviewer diffs it twice, and the sentence outlives everybody who could
# contradict it. The constitution's line is "never claim a gate result this code did not
# observe", and this was our own. 18 lines of test, 7 of corrected comment, 6 here.
# 45,997 to 46,008 for rule 3, which this repository was breaking in two of its own files.
# `tests/stats.py` counts suppressions and prints the number; it is deliberately outside
# `just check`, so the repository counted its own violations and gated on none of them. It
# printed 2. `tests/conftest.py` carried an E402 exemption because it inserted `src` and
# `hooks` on `sys.path` and then imported the package underneath — pytest has had a
# `pythonpath` option since 7.0, so the ordering is configuration now and the exemption is
# gone. `tests/test_readiness.py` carried a coverage-exemption pragma on a platform branch
# in a test file, and coverage measures only `src` and `hooks`, so it suppressed nothing.
# 46,008 to 46,240 for the requirement-by-requirement audit and one defect it found.
#
# 162 of the lines are `docs/audit-2026-08-15.md`, which is what the standing goal asked
# for: five independent auditors over 27 process-optimization commitments and 385
# evolution-proposal requirements, under one rule — PROVEN only if somebody ran a command
# and can paste its decisive output. It reports that the proposal is not implemented and
# names twenty FAILED requirements, which is a larger delivery than a percentage.
#
# The rest is the first of those twenty. `doctor.surfaces_alive` returns `(message, cure)`
# as soon as any surface is unwired, and the coverage block did `surfaces_alive(root) or
# ""` — a tuple is not a string, so `surface["name"] in inert` stopped being a substring
# test and became an exact-element test that is never true. The block could therefore never
# print INERT while any surface was unwired, and the two surfaces that fail *silently* —
# Codex without its trust ceremony, OpenCode whose plugin was dropped with no error and no
# log — printed as `installed and wired` on the operator's machine while assertion 21 was
# telling them both were dead. Nothing reached it: every existing case had all surfaces
# wired or none, and the bug needs one of each.
# 46,240 to 46,360 for two more of the twenty the audit found, both of them a control
# that computes the right answer and then loses it.
#
# `hooks/session.py` is the one place that actually exports to a collector. `_otlp.probe`
# already decides the hard part — a 2xx carrying rejected records is not a delivery — and
# session.py called `send_tail` and threw the tuple away. Silent partial loss is the worst
# shape it can take: the collector says 200, the dashboard is missing events, and nothing
# in the record says a line failed to land. It now emits an `error` event and says one line
# on stderr, because the event alone tells the operator a day late and the line alone
# vanishes with the terminal.
#
# And `update --dry-run` reported PASS on an already-pinned repository: "the requested
# operation and all applicable checks completed", for a run that deliberately did nothing.
# The already-pinned branch sits above the dry-run branch and returned before it.
# 46,360 to 46,416 for the fourth of the twenty, and the one with the largest audience.
# `ai-eng doctor` printed "the hash chain is intact and writable" while `ai-eng audit
# verify` exited 1 on 22 broken links in the same file. Assertion 6 walked `prev` and
# `hash` only, so a link sealed as `outcome: "edited"` — the tamper marker, whose hashes
# match precisely because it was sealed truthfully — passed it. A test pinned the split
# and its own docstring named the tension it was documenting. Doctor is the summary screen
# and the verifier is what somebody runs when they already suspect something, so a false
# green here is the expensive direction. Assertion 6 asks the verifier now rather than
# re-implementing half of it, which is the plugin's three-copies finding one file over.
# 46,416 to 46,458 for the fifth of the twenty, and the one the constitution names first.
# The eight surface ids were written out four times — `policy/surfaces.toml`, the adapter
# schema's enum, `surface.SURFACES`, and a test — and only the schema and the test were
# tied to each other. Nothing tied either to the wiring table that decides what actually
# gets installed, so a ninth surface added there would have left three copies behind and
# the module that reports coverage would have carried on reporting eight. "Never create
# mirrors of guards, skills, templates or policy homes" is the first line of the Never
# list, and this was the product breaking it about its own data. The list derives from the
# table now, and the schema enum is checked against it rather than maintained beside it.
# 46,458 to 46,506 for the sixth of the twenty. A check object in the JSON envelope was
# `{id, status, summary, detail}` and nothing else, so the machine-readable half told a
# consumer that something failed and withheld the one field that says what to do — while
# the human half had it on screen, computed by the same function, three lines earlier.
# A contract poorer than the screen it mirrors is a contract nobody uses twice. `detail`
# was already the evidence; `cure` is what was missing, it is optional because most facts
# have none, and an empty one is stored as absent rather than as "".
# 46,506 to 46,644 for the seventh of the twenty, and the one that was hiding the most.
# Thirteen attacks shared a single negative control, and five of the nine guards were not
# in its fixtures at all — so a guard that started firing on ordinary input was caught only
# if it happened to fire on a control somebody had written for a different guard. A control
# that does not name its guard is a control for whichever guard you were lucky about.
#
# Each control now declares what it is clean for, five were written for the guards that had
# none — an ordinary repeat under the loop guard, three files inside the scope budget, a
# commit that merely mentions `--no-verify`, somebody else's file with our filename, and a
# plugin that did report loading — and the run refuses to go green while any attacked guard
# lacks one. The suite is 19 cases over 9 guards, and it named `doctor-21` as uncontrolled
# the moment the check existed, which is how I knew the check worked.
# 46,644 to 46,669 for the eighth, which is the latency check finally measuring what it
# is named for. It said p95 and took the median of five samples; it was corrected to a real
# p95 earlier today and still asserted 200 ms against a stated requirement of 50, four
# times looser than the thing it is named for, with nothing saying so.
#
# The number it asserts now is ours rather than Python's. Measured: a bare interpreter that
# does nothing costs ~18 ms here, the whole dispatcher start ~42 ms, so our share is ~24 ms
# against the stated 50. Asserting 50 on the total would leave 8 ms of headroom and flake
# under `-n auto`, and a bound the machine's load can trip is a test people learn to rerun.
# Subtracting the floor measures the part this repository is accountable for, which is what
# the proposal's `guard_p95_ms` indicator is asking for. Green three times under parallel
# load before it was believed.
# 46,669 to 46,722 for the operator's two decisions on the audit's findings.
#
# MADR 0008 approves specifications 011 to 015 at exact digests. The status vocabulary is
# closed at draft/shipped/superseded and stays that way: approval is not a state of the
# work, it is a fact about a person and a moment, and a status word carries no authority,
# no date and no digest. The record names all three, and a test recomputes the five hashes
# — because the audit found the same mechanism rotting in specification 010's own plan,
# where an invalidated digest sat beside an approved one and no check read either.
#
# And specification 010 goes back to `draft`. Its plan reserves `shipped` until a candidate
# proves exact-HEAD CI receipts; the branch has never been pushed, so those runs cannot
# exist. `doctor` assertion 19 said so and the audit recorded it FAILED. The Intent's
# relation digest and its "Spec 010 is shipped" fact moved in the same commit, which is the
# transition working: changing the file invalidated the relation and something noticed.
# 46,722 to 46,806 for spec 012's first decision, D-012-01: no skill lands without a case
# it must take and a case it must refuse.
#
# Everything `audit_one` checked before this was shape — fields, line ceiling, description
# length, the "Not for" clause, a jargon list. None of it can tell a skill that routes
# correctly from one that fires on everything, so a skill whose description overlapped its
# neighbour's passed every gate this repository had, and the audit's verdict on all eight
# was that not one has an executed check demonstrating a refusal.
#
# The refusal half is the one that matters: "what it does" is in every description ever
# written, and "what it must not do" is what stops the wrong skill firing. Each corpus takes
# its refusals from the neighbour's positive territory and names that skill, so the day two
# descriptions drift into each other a file somebody else wrote goes red. Plain markdown in
# the skill's own directory, not a registry — one more home is one more thing to keep in
# sync, and this week's audit already found four copies of a list.
# 46,809 to 47,045 for Task 7's deferral ending and the task it uncovered.
#
# `policy/surface-adapter-v1.schema.json` was frozen in Block A with no instance, and the
# amendment said an adapter lands when a reader needs one. Blocks D onward do, so
# `claude-code` gets the first — the only surface whose denial an executed run has produced.
#
# The rest is the honest half. `surface.py` still proves only that a receipt exists, names
# its own state, ran and is fresh; binding it to a requirement was attempted three times and
# each attempt fought an existing contract. `protocol_id` is forbidden on an automated
# receipt by the check-evidence schema. `input_digest` already means the payload that was
# checked. `command` carries an absolute path, so no two machines match. A fourth guess at
# the end of a long session would have been the worst of the four, so the binding is
# Task 16 with its own done-when, and this repository has enough half-designed controls
# already — the audit found twenty.
# 47,045 to 47,106 for spec 014 D-014-08, now that it is approved: `redact = "none"` is
# deleted. It was a supported value in the pin and it sent every field outside the two
# allow-lists to the collector verbatim. A configuration value that disables a privacy
# control is a control whoever runs the exporter can switch off, and nothing downstream
# could tell a machine that had redacted from one that had been told not to. Hard delete,
# no shim, written in the CHANGELOG — and an unrecognised mode redacts like every other,
# because the safe reading of a word nobody knows is the strict one.
# 47,106 to 47,114 for what the first P4 sitting learned, recorded in specs/014 rather
# than attempted. D-014-05 is blocked on two numbers that are not in this repository — the
# official SHA-256 of the gitleaks and Trivy releases — and learning them is a network call
# with its own consent; the mechanism is one line per download. D-014-07 is blocked on a
# caller, not an executor: `grep -rn "preflight(" src/ hooks/` finds two hits and both are a
# different function with the same name, so teaching the capability one to return PASS would
# produce a permission that stops nothing — a green nobody earned, inside the function
# written to prevent them.
# 47,114 to 47,157 for the first P4 sitting's findings, and for where they had to go.
#
# I wrote them into specification 014, which is approved at an exact digest, and the check
# written three hours earlier caught it within a minute: "approved at d19fbeff… and now
# hashes to 774454a4… — either revert the edit or take the approval again". It offered two
# honest moves and I took the first. Implementation findings are not the specification;
# they are what happened when somebody tried to build from it, so they live in the audit
# record, which nobody has approved and which exists for exactly this.
#
# The two findings: D-014-05 is blocked on two SHA-256 values that are not in this
# repository, which is a network call and its own consent. D-014-07 is blocked on a caller
# — nothing calls `capability.preflight`, so a PASS from it would stop nothing.
# 47,157 to 47,167: three lines the formatter wrote and the seven of this paragraph.
# Specification 016 is 342 lines and costs nothing here, because `specs/` is not the
# product. What costs is `tests/adversarial/run.py`: the `controls=` argument pushed the
# decorator over the width and `ruff format` split it across five lines, which the gate
# caught rather than a person. A ten-line raise is the smallest this file has recorded and
# it is argued for like the large ones, because a ceiling that moves quietly is not a
# ceiling — including when what moved it is the sentence explaining the move.
# 47,167 to 47,633 for the first capability of P2, and the only one whose exit criterion is
# an exit code. `report issue` printed "planned for P2 and is not implemented" and returned
# INCOMPLETE, which was honest and became a lie the moment anything half-built it.
#
# The 466: a closed payload schema in `policy/`, the module that builds against it, the
# subcommand, and the three red fixtures — machine path, personal datum, secret — written
# before the code that rejects them. The allow-list is the control and the scanners are the
# backstop: logs, diffs, environment, paths, hosts and remotes have no field to arrive in,
# so the only route left is a person pasting one into the prose, and that is what is
# scanned. Nothing sends. The draft is one local file under `.ai/`, shown as the exact bytes
# with their digest, and a refused payload leaves no file at all — the artefact somebody can
# still send is the one that matters.
# 47,633 to 47,882 for the half of `report issue` that could ever send, and for the two
# refusals that stand between a person and that. The security route refuses before the
# terminal is read rather than after: a control that asks first and declines second has
# already put the wrong route in front of somebody at the end of a long day, and the test
# asserts on what was offered rather than on what was answered. The typed phrase carries
# the payload's own digest, so consent is to one payload and not to a screen. And a
# confirmed submit still ends INCOMPLETE, naming the destination that does not exist,
# because there is no transport here and PASS for work that did not happen is the exact
# defect `update --dry-run` was fixed for two waves ago.
# 47,882 to 47,935 for two literals in `init.py`, and for a correction to what I thought
# they were. I called them unguarded; they were not. `COUNTED` in the contract suite bound
# "Writes 8 skills into" to this repository's own skill directory, and it turned red inside
# a minute of the edit. The real defect is one level up: both sentences are output about the
# machine in front of somebody, and bound to our count they printed eight over a store
# holding three. The plan line counts the wheel, the receipt line counts what landed, and
# `tests/test_mut_init.py` stands a three-skill wheel in front of both — which the literal
# and its gate together could not do. The entry leaves `COUNTED`; everything still on that
# list is prose, where there is nothing to count.
# 47,935 to 48,045 for the ninth skill, which is the first one this repository has admitted
# through a gate rather than by writing a file. `ai-report` lands last of its wave and not
# first: the verb it documents exists, the three fixtures that stop it exist, and its corpus
# takes every refusal from a neighbour's positive territory and names that skill — so the
# day two descriptions drift into each other, a file somebody else wrote goes red.
#
# Two things came with it. `policy/capabilities.toml` declared that the issue mode writes
# nowhere while the code writes one draft, and nothing enforces the declaration yet, so the
# two could have disagreed until the day an executor arrived and denied the command for
# doing its job; a test binds the declared write root to `issue.draft_path` now. And the
# skill count moved in two sentences of prose, which `COUNTED` caught, which is the half of
# that gate that is doing exactly what it was built for.
# 48,045 to 48,336 for D-012-06: two flags and the proof that the three renderings agree.
#
# The proof came first and it is three real processes, because "the same run in all three"
# cannot be shown by three calls into one interpreter that caches its console after the
# first. It also found what it was pointed at: nothing in this repository compared what a
# person sees with what a script parses, and one of them being wrong is the whole failure
# this product is about. The envelope carries no `exit_code` field, which is EP-090's and
# an unapproved specification's, so the test reads the outcome-to-code mapping instead and
# says in the file that it is doing that rather than quietly asserting less.
#
# `--debug` is now the only route a traceback reaches a person. It is the fastest way to put
# an absolute path and a username onto a screen that is about to be pasted into an issue,
# and `report issue` exists two commits earlier to stop exactly that. What is recorded did
# not change: the exception's repr still goes to the chain, because that is the half a
# maintainer reads. A crashed run also emits its `command` event for the first time — the
# re-raise used to take the process out before the dispatcher could record what had run.
#
# `--non-interactive` lives in `accept`, because what it changes is consent and not
# appearance, and the consent reader refuses without opening the device at all: a mode that
# promises not to ask has to be observable as not asking. `init`'s question returns no
# rather than its default, which is yes.
#
# One line was written and then deleted. I added `force_terminal` to the console, with a
# comment saying rich re-decided what `plain()` had already decided; I then ran the same
# command with and without it and got identical bytes. The test had been failing because
# the suite exports `NO_COLOR` for every test and the child inherited it. A no-op with a
# confident comment is the defect this repository keeps finding, so it is not in the diff.
# 48,336 to 48,452 for `ai-build`, the tenth skill, and for the check that makes its two
# hard refusals worth writing. It says it does not widen scope and does not bypass the
# gate, and it names `change_scope_guard.py` and `no_verify_guard.py` rather than promising
# to behave — so a test reads every skill file for a `hooks/<name>.py` citation, requires it
# to be in the dispatcher table, and requires anything cited in a refusal list to be a guard
# on a blocking event. Proved red by pointing one citation at a telemetry hook. Delete
# either guard and the sentence that leans on it goes red with the file's name on it.
# 48,452 to 48,744 to close P2's catalogue: two capabilities land, three do not, and the
# three are the part worth the lines.
#
# `ai-security` reasons about a boundary and runs the scanners this repository already
# pins, and it refuses the two things it has no standing to do — accepting a risk, which is
# `ai-eng accept` with a named person and an expiry, and declaring compliance, which is a
# claim about an organisation. `ai-design` is one gateway with four routes, an AA floor and
# evidence measured off the rendered result rather than the CSS somebody wrote.
#
# `ai-test`, `ai-verify` and `ai-animation` do not exist as files. Each was to survive only
# if a routing evaluation showed it distinct; specification 012 already recorded that the
# comparison has no baseline, no sample and no margin and that no evaluation runner exists
# here. No evidence is not weak evidence — the condition is unmet, and fail-closed is the
# only reading this repository allows itself. Their work has a home: test design is step 2
# of `ai-build`, mechanical verification is the gate and `references/testing.md`, and motion
# judgement is the new `references/motion.md` beside the new `references/frontend.md`, which
# are EP-125 and EP-126. A test asserts both halves, so adding one of the three back without
# an evaluation turns the build red naming it.
#
# Four of the lines are a fixture that stopped testing what it says. `test_install` planted
# a skill "somebody else installed" and called it `ai-design`, so the day `ai-design`
# shipped, the foreign skill in the test became one of ours and `uninstall` was right to
# refuse it. The name is asserted not to be ours now, rather than assumed.
# 48,744 to 48,787 for the first row of P3 and the fifth of the audit's twenty:
# `grep -c merge_group .github/workflows/check.yml` returned zero, so nothing here had ever
# checked the tree that is about to exist. Two branches that each pass alone can fail
# together, and the only gate was the pull request. The test reads the `on:` block rather
# than the file, and asserts the other half too — no job may be conditioned on the event
# name, because a lane the queue skips is a lane `CI Result` counts as a failure.
# 48,787 to 49,137 for the claim, which is P3's first executable obligation: one task, one
# work item, one writer, decided by the remote rather than by either side.
#
# Two things were measured before any of it was written. `git push --force-with-lease=<ref>:`
# is not a compare-and-swap when both writers push the same value — both are told
# "Everything up-to-date" and both believe they won — so the claim ref points at an object
# unique to the claimant, and the loser is refused by git's own fast-forward rule. And a
# commit takes its author from whoever is sitting at the machine, so the claim object is
# written with an identity that belongs to this framework and to nobody: a coordination
# record carrying a person's address has published a person to everyone who can fetch.
#
# `spec claim` is the caller, and it cost the will an honest line. The check that derives
# which verbs touch the network knew about sockets opened in this process and nothing about
# a verb that hands the work to git — so a command could have pushed to a server while
# printing `network none`, which is the same false green that check already exists to
# prevent, one process boundary away instead of one indirection. It follows sibling imports
# and reads the git subcommands that talk to a remote now.
# 49,137 to 49,421 for the sixth guard, and for the half of EP-188 that this is not.
#
# A claim says which paths one writer may change while it is held, and the guard enforces
# that where the write happens rather than where the conflict appears. Three shapes of
# refusal, each one measured: outside the claimed paths, outside the repository entirely,
# and a claim file that exists and cannot be parsed — which denies, because "unreadable"
# and "absent" must not be the same answer when somebody else may hold the work. The path
# is resolved and not compared as text: `src/thing.py/../../elsewhere.py` is inside the
# claim by string and outside it by path, and the string is the one an attacker writes.
#
# The local file is written only after the remote agreed, so the writer who lost the race
# is not left holding a file that says it owns the work.
#
# What this is not: `claimed_paths` is also to be enforced by CI over the pushed diff,
# against the claim held on the remote. That does not exist, so EP-188 stays open and the
# test file says so in its own docstring rather than reading as though the requirement had
# closed.
# 49,421 to 49,789 for the DAG, and for two fixtures that were proving the wrong thing.
#
# Three sources of edge and no fourth invented: two claims over one path, a claim over a
# file another claim's file imports, and the resources that cannot be shared at all. Where
# the direction is genuinely arbitrary the work item decides, because two machines deriving
# the plan have to derive the same plan and "arbitrary" is fine as long as it is identical.
#
# Both fixtures had to be corrected after the code passed them. The exclusive-resource case
# gave both tasks `uv.lock`, which is an overlap, so the overlap rule ordered them and
# deleting the exclusive rule changed nothing — measured by deleting it. It uses two
# migrations and two schemas now, where nothing about the paths says the tasks collide. And
# the determinism case looped inside one interpreter, where set iteration is stable: it runs
# the ordering in three subprocesses with three hash seeds now, and pins the exact order.
# Both are the same defect this repository keeps finding in its own tests — the input that
# cannot see the thing the test is named after.
# 49,789 to 50,210 for the checkpoint's three receipts, one of which this cannot produce.
#
# The audit measured what existed: `git-hooks/pre-push` covered secrets only, and
# `acceptance_privacy.py` had never seen a staged diff. It sees one now — and the first
# version of that scan reported on git's own punctuation, because a unified diff's header
# carries `--- /dev/null` for every new file and the machine-path scanner is right to call
# that an absolute path. It reads the added lines and nothing else: removals are already in
# history, and this receipt is about what is being published.
#
# The third receipt is read, never produced. A check nobody ran is INCOMPLETE, a receipt
# older than its own `max_age_seconds` is the same answer, and a receipt that ran and said
# FAIL is a failure rather than an absence — the strongest evidence here, and reading it as
# "no receipt" would turn the clearest answer into the vaguest one.
#
# The hook is gated on a claim being held. Demanding a gate receipt on every commit in every
# repository that has never coordinated would put a wall between a person and their own
# working tree, and the wall would be this framework's.
# 50,210 to 50,358 for four non-goals that had no check, and for the two patterns that
# were wrong on their first run. A non-goal with no check is a sentence, and the shape
# arrives six months later in a commit that looked reasonable on its own.
#
# Every scan plants the shape first and asserts the scan finds it: a scan that finds nothing
# and a scan that looked at nothing print the same result. The bare-force pattern flagged
# `uv tool install --force`, which is neither a push nor destructive to anybody else's work,
# so it reads per line and only where a push is. The ownership pattern flagged the word
# "settle", because bare `ttl` is inside it, and it flagged `checkpoint`'s prose about an
# expired receipt — which is a required control two files over, so `expire` is deliberately
# not in the list and the comment says why.
# 50,358 to 50,583 for the merge gate, and for a defect the fixture found by being real.
#
# The gate cannot take the writer's word for what was claimed: that file lives on the
# machine being judged, and rewriting it to cover everything is one command. `--item` reads
# the claim from the remote instead, which is the one copy both sides can see, and a test
# widens the local file to `["."]` and asserts nothing changes.
#
# The defect: the local claim file was stripped of its trailing slash and the list read from
# the remote was not, so `alpha/` became `alpha//` and every path inside the claim read as
# outside it. That gate would have failed the writer who had done exactly what they claimed
# — the most expensive kind of false positive, because the cure it suggests is to stop
# claiming. Normalised in one place now, and the fixture that caught it is two disjoint
# claims that both have to pass.
#
# A work item nobody claimed is INCOMPLETE and not a pass: reading it as "no violation
# found" would let an unclaimed branch through the one gate that exists to notice it.
# 50,583 to 50,646 to close what P3 can close on this machine. The Intent schema is
# asserted not to have grown a claim, a base SHA, a lease or a branch: a long-lived record
# carrying the state of one afternoon's run is wrong by the next morning without anybody
# editing it. And CI verifies the branch against the claim held on the remote, saying "not
# applicable" out loud where no claim exists — a quiet pass and a real one look identical in
# a log six weeks later.
#
# What P3 cannot close here is written down rather than left to be discovered: EP-183 and
# EP-186 need a draft pull request and a merge queue actually running, EP-180 needs a plan
# schema this version does not have, and the fixtures prove git's file transport rather than
# the network one. Each is a consent or a specification away, not a line of code away.
# 50,646 to 50,717 for EP-045: the two sides of the gate pinned the same, and each engine
# asked what it is before it is trusted. CI downloaded exact releases of five engines while
# `just security` ran whatever gitleaks and trivy the machine carried — so a local green
# could come from an older engine that no longer looks for the thing, and a local red could
# be one CI cannot reproduce. Both checks were proved by moving the pin and watching the
# recipe stop. A test holds the justfile's pins equal to the workflow's, so drift on either
# side turns the build red naming the engine.
# 50,717 to 51,038 for EP-050 and EP-265: the five ways a scanner lane reports nothing
# without having looked, each one INCOMPLETE and each one with its own fixture. A missing
# engine, missing rules, a crash, a timeout and zero inputs all print the same thing on a
# terminal — no findings — and every one of them is a green that means the opposite.
#
# It has a caller, which is the whole reason it is here rather than in a drawer: `just
# security` runs its three engines through the contract now instead of as three bare
# commands, and INCOMPLETE fails that gate exactly as a finding does. Proved by moving
# `policy/semgrep.yml` aside and watching the gate go red on LANE_RULES_MISSING while the
# other two lanes stayed green — which is precisely the case three bare commands could not
# tell apart from a clean run.
#
# The fixtures drive real subprocesses. A lane runner tested against a stubbed runner proves
# its branches; it does not prove that a missing binary raises what the code catches.
# 51,038 to 51,169 for EP-051 at the one artefact this repository can pin today, and for
# EP-277's four fields.
#
# A rule deleted from the middle of a rules file leaves an engine that runs, exits zero and
# no longer looks for the thing it was deleted for — a clean scan and a blind one, printing
# the same words. So the semantic lane pins the bytes of `policy/semgrep.yml`, the fixture
# flips one bit and watches the lane refuse, and a test holds the pin equal to the file so
# that editing the rules without moving the pin turns the build red. Same discipline as this
# ceiling, one directory over. The wheel and SBOM halves of EP-051 need a release, and the
# scanner-binary half needs two checksums that are a network call away; both are recorded
# rather than claimed.
#
# EP-277: `surface_id`, `surface_version`, `adapter_version` and `deny_protocol` leave in
# clear now instead of as sixteen-character hashes, because every one of them names software
# rather than a person or a place — and a hash of "claude-code" answers no question anybody
# exports observability to ask. A new test asserts no field naming a person, a host or a
# path is on that list, because the list growing once is how it grows twice.
# 51,169 to 51,227 for the audit's own addendum: thirty-three requirements that have moved
# since it was measured, each row naming the executed proof rather than the commit that
# claims it. The audit is the document this work is judged against, and an audit that goes
# stale is a measurement somebody will quote next month as though it were current — which is
# the first correction the audit itself had to make about the report above it.
# 51,227 to 51,694 for P5's register, which is the one artefact that makes an unequipped
# wave readable instead of merely unfinished.
#
# Thirteen indicator rows and fourteen prohibition rows, as data in `policy/`, read by one
# file in `tests/` that `just check` runs. Seven indicators carry a command and a bound;
# six carry `no_instrument` and the reason, and the reader names all six every run rather
# than printing how many — a count is a thing you round, a list is a thing you answer.
#
# A bound beside `no_instrument` is an error, and so is a command with no bound: the first
# is a number nobody can measure and somebody will quote, the second is a number printed
# into a log. The reader refuses a P5 completion claim while any row is unequipped and names
# every one of them in the refusal, which is the only thing in this repository that can stop
# a wave closing on work nobody did.
#
# Every case in its test mutates the register and asserts the reader says no. A reader
# tested only on the register that already passes is a reader nobody has seen refuse.
# 51,694 to 51,742 for PO-24, the fifth of the process failures the audit measured and the
# last of them that code can answer. Specification 010's plan named an approved digest and
# an invalidated one, and nothing in `src/`, `tests/` or `hooks/` read either — so editing
# the file it gated changed nothing anybody would notice.
#
# A check reads both now, and it made the record tell the truth on the way: `spec.md` no
# longer hashes to what was approved, because `status` went back to `draft` under the audit.
# The plan says so in a sentence, beside the approved digest rather than over it, and the
# check fails when the two disagree. Proved by appending one comment to the specification
# and watching it name the new hash. What a gate can honestly do here ends there: the
# approval itself belongs to a person, and no test can grant one.
# 51,742 to 51,981 for specification 011's Task 16, deferred once with three attempts
# recorded and none taken. The three are still true: `protocol_id` is forbidden on an
# automated receipt, `input_digest` already means the payload that was checked, and
# `command` carries an absolute path. What was left is the field none of them looked at —
# the receipt id, which is machine-independent, already required to match, and free for the
# adapter to declare instead of for this module to compose.
#
# So the adapter declares it, `surface.py` reads it where an adapter exists, and a receipt
# that satisfies every other rule while naming the id a superseded version required is
# INCOMPLETE. A version bump beyond 1 has to appear in that id, held by a test, so
# supersession is mechanical rather than remembered.
#
# The docstring stops saying the same thing about both cases. Where an adapter exists a PASS
# now means "this ran the thing we require"; where none exists it still means "this ran and
# said so", and the file says which claim it had rather than printing one word for two.
# 51,981 to 52,036 for the cadence report measured against the session that used it, and
# for the one rule this session broke while reading the audit that recorded it broken.
#
# One primary home per commit: measured across nineteen commits, the widest touches five and
# four touch four or more. The reason is structural — a capability here is a file in
# `.agents/`, a declaration in `policy/`, a count in two prose files that `COUNTED` holds
# equal to the tree, and a line in this one — so the rule and this repository's own drift
# gates pull opposite ways. The gates are right; a count nobody updates is a count that
# lies. The tension is recorded as open rather than resolved by a commit guessing at
# somebody else's rule.
# 52,036 to 52,102 for the owner's three answers, taken in one sitting.
#
# The cadence's fourth activation step: both current digests approved, recorded in MADR 0009
# rather than inside the file it approves — a paragraph naming its own file's digest changes
# it by existing, so the number in the file would never be the one anybody agreed to. The
# one-primary-home rule gains the exception the owner chose: a commit may move the counts and
# ceilings another check forces it to move, and nothing else.
#
# And D-014-05, which was blocked on two numbers that are not in this repository. With
# consent for that one network call they are here, from each publisher's own checksum file.
# actionlint was the only download whose bytes were ever checked, on a workflow that also
# pulls the two engines whose entire job is to find things — a mirror or a compromised
# release could have handed either of them a binary that finds nothing, and the gate would
# have gone green having scanned with it. All five downloads are checked now, and a test
# reads the workflow rather than a list, so the sixth is caught for never being named.
# 52,102 to 52,168 for 45 type errors nobody could see, and for the reason nobody could.
#
# `AGENTS.md` says `just check` is what CI runs. It was not: `typecheck` ran `tsc` and the
# plugin suite, and mypy existed in the workflow alone — so the local gate went green over
# 45 errors in 15 files for the whole life of this branch, and the first anybody could know
# was the first time it reached CI, 253 commits in. Pushing was what found it.
#
# None of the 45 is silenced. Two were mine. Three were the same platform guard written as
# `os.name` instead of `sys.platform`, which is the same answer at runtime and opaque to a
# type checker, so every Windows-only symbol read as missing everywhere else. Four were a
# regex `fullmatch` whose `None` four call sites treated as impossible — a malformed id
# would have raised an AttributeError from inside the parser whose whole job is refusing
# malformed input. And several were one name meaning two things in one function: `low` and
# `high` as both strings and version tuples, `commands` as both a subparser and a counter,
# `expected` as both a settings list and one handler.
#
# mypy is in the local recipe now, pinned to the workflow's version, and a test holds the
# two equal. The next divergence of this shape costs one run, not one branch.
# 52,168 to 52,199 for the two things CI found that no local run could.
#
# A `TypeError` on every Windows run of the native transaction path: the structure field is
# `LPWSTR` and `create_unicode_buffer` answers a `c_wchar_Array`, which ctypes converts for
# a function argument and refuses in a structure. Three tests failed on that leg alone, and
# the fix has to be verified there because no other platform executes the block.
#
# And the install matrix counted verbs with a regex that required each description to start
# with a capital. Two of the ten open with their own subcommands, so it counted eight and
# called a correct wheel wrong. The case of a sentence is not evidence of anything, and
# making it evidence is how a check ends up wrong about something that is right.
# 52,199 to 52,327 for the deepest thing this push found: every pull request this
# repository could ever open was INCOMPLETE, and nothing local could see it.
#
# GitHub checks out `refs/pull/N/merge` — a merge of the branch into its base — and the MADR
# validator walked that merge's edges as transitions. The edge from the base parent leaps
# over every state each decision passed through on the branch, and each of those was
# validated where it was made. Judged as a transition, the leap fails. Reproduced by
# building the same merge shape locally with `commit-tree`, which is the only way to see it:
# nothing in a linear checkout ever validates a merge commit.
#
# The rule is about content, not shape. A merge whose decisions are one parent's decisions
# introduced none of its own. A merge that resolved to a set neither parent holds is work no
# line has reviewed, and every one of its edges still has to be legal — with a fixture that
# jumps a decision from proposed straight to superseded and is refused.
#
# And one identity: the DAG test's own merge ran without the author every other write in
# that file carries, so it passed for everyone with a configured git user and for no CI
# runner.
# 52,327 to 52,351 for the last two CI-only failures, both of them a test that inherited
# its environment instead of naming it.
#
# The JSON envelope test asserted twenty-four surface rows and got none under the mutation
# harness, whose sandbox is a copied tree with no history: no repository means no surface
# block, so the test held in every environment that happened to be a checkout and failed in
# the one that runs it most. It names its root now.
#
# And the install smoke ran `ai-eng audit verify` expecting exit zero on a stranger's
# machine, where one commit exists from before this tool did and nothing is anchored.
# INCOMPLETE is the true answer there; exit zero would have meant the verifier said PASS
# over a chain with no anchors. The step asserts the word now, so a crash or a PASS both
# fail and the honest answer passes.
# 52,351 to 52,500 for the command a stranger types first, which no test had ever run
# whole. The suite covered the machine half and the repository half separately, each with
# the other switched off, so `init --global --project . -y` — the exact argv the install
# matrix runs on three operating systems — had never been executed by anything that could
# read its outcome. The first run anybody watched was on a CI runner.
#
# What it found: `intent.validate` answered `INTENT_SCHEMA_INVALID` over a file nobody had
# written. Absent and malformed were one answer, which is the reading `claim_scope_guard`
# refuses one directory over — and it sends a person looking for a mistake in a document
# that does not exist. A missing Intent says `INTENT_MISSING` now.
#
# What it did not change: the verdict. A repository without its canonical Intent is not a
# governed repository and this verb will not say PASS over one; that decision is already
# held by a test and it stands. The install matrix reads the outcome word now instead of
# demanding exit zero, which is the same shape as the `doctor || true` two lines above it —
# a fresh machine is red on purpose, and the step says which red it expects.
# 52,500 to 52,591 for a refusal that said nothing, in the first verb anybody runs.
#
# `init` has three early returns, and every one of them printed the will, four stage lines
# and INCOMPLETE — no reason, no cure, no surface table. On a CI runner it fired on all
# three operating systems and the step failed two lines later with "the pin was never
# written", which is a symptom and not the cause.
#
# The cause: the install matrix creates `~/.claude/skills/ai-*` before installing, on
# purpose, to force the copy path Windows takes everywhere. Those empty directories were
# read as somebody else's, so a fresh machine whose editor had already made the folder
# could never be initialised at all. An empty directory has nothing in it to lose; one
# holding a file this install did not write is still refused — and now says which and why.
# 52,591 to 52,643 for the next verb in the same sentence. `init` closes by recommending
# `ai-eng spec new <slug>`, and on the machine `init` had just set up that command answered
# "the spec transaction could not prove an unchanged safe filesystem state" — because the
# transaction anchors on `.ai/intent.md`, which does not exist there.
#
# True about a path and useless about a decision. A spec is a decision inside a Solution
# Intent; a repository on its first day has none, and `init` does not write one because it
# is the user's to write. The refusal names the Intent and what to do about it now, the
# install matrix asserts that wording, and a fixture asserts no spec is published anyway.
# 52,643 to 52,695 for a step that could never pass, and for a decision I moved and put
# back. `uninstall` requires a person at a keyboard and `-y` does not substitute for one —
# `test_uninstall_is_explicit` owns that, and it said no when I changed it. So the matrix
# changed instead: the removal runs under a pty where one can be made, and the refusal is
# what is asserted where one cannot. A step that cannot pass on any platform proves nothing
# in either direction, which is worse than either answer.
# 52,695 to 52,707 for a step that broke the step after it. The pin check edits
# `.ai/config.toml` to prove `doctor` refuses a mismatched version, and left it edited — so
# `uninstall` met a recorded target whose bytes somebody had changed and refused to remove
# it, saying exactly that. The verb was right both times; the job was reading the second
# refusal as a bug in removal. The mutation is undone where it was made.
# 52,707 to 52,765 for three checks that had never run and one that could not be right.
# actionlint and zizmor sat after `just check` in the same job, so on a branch that had
# never been green they had never executed once; their first run found two SC2086 splits
# and a `${{ github.base_ref }}` pasted straight into a shell — a branch name is
# attacker-supplied text. Both are fixed and the pair now runs before the gate, because a
# reader that only speaks once everything else passes is silent on the days it is needed.
# The third is `--non-interactive spec list` asserted to exit 0: true here, false in the
# mutation sandbox, which has no `.git` and where that verb correctly answers INCOMPLETE.
# It now compares the flagged run against the unflagged one, which is the actual claim.
# And the fourth: `read` opened a second handle to the file this writer had locked.
# `LockFileEx` is mandatory and per-handle on Windows, so the process was blocked by its
# own lock; on POSIX the same lock is advisory, which is why it had always looked fine.
# 52,777 to 52,813 for the number the last raise bought. `_win_error` now carries its
# native code on every class, and the code was 87 — ERROR_INVALID_PARAMETER, three times,
# from `SetFileInformationByHandle` with a `RootDirectory` handle set. That entry point
# documents the field as "must be NULL"; the handle-relative rename lives below Win32, at
# `NtSetInformationFile`. Passing a full path instead would have satisfied the call and
# thrown away the anchoring the whole transaction exists for.
# 52,813 to 52,829 for a check that counted occurrences in a file mutmut had rewritten.
# The single-writer test read `claim.py` as text and required exactly one `"push"`; the
# mutation harness runs the suite over a copy where every function is a dispatcher plus a
# dict of variants, so it counted the variants and reported "more than one place publishes
# a claim" about code that publishes from one. It reads the tree the mutants were generated
# from now, which is the tree the assertion was always about.
# 52,829 to 52,849 for a guard on a T2 surface that could never have run. The Codex entry
# was written with `handlers`, `timeout_ms` and `status_message`; Codex CLI 0.147.0
# declares the group as `matcher` and `hooks` and the handler fields as `type`, `command`,
# `commandWindows`, `timeout`, `async` and `statusMessage`, and the word `handlers` appears
# in that binary only as Rust module paths. Read off the shipped binary and off a machine
# where every hook another tool had written used the vendor spelling and only ours did not.
# It can be attempted now. It is still unproven, and no line here says otherwise.
# 52,849 to 52,893 for a register that answered PASS over nothing. The fenced-block
# recogniser required a bare newline after ```yaml, so a spec file written on Windows —
# CRLF, which is what that platform writes — read as having no acceptances at all. Not a
# refusal: a clean PASS over an empty register for a file holding a live risk acceptance.
# Every fixture in the suite wrote LF, so nothing could see it until three Windows tests
# did. The fence now takes an optional carriage return, the bound span is measured off what
# matched rather than off an assumed length, and a CRLF fixture holds it down everywhere.
# 52,893 to 52,941 for the last step in the gate, which could never pass. `doctor --ci`
# counts every check a runner cannot answer as unanswered and unanswered is INCOMPLETE, so
# taking its exit code as the verdict was a step no commit could satisfy — unnoticed
# because every earlier failure in that job ran out of road first. It now gates on the
# other half of the same report: nothing FAILED. And assertion 23 stops calling itself a
# failure. Nothing executed there — the executor is what is missing — so it is undecidable,
# which prints the same warning under a heading that reads "None of these is a pass."
# 52,941 to 52,957 for the step after it, wrong in both directions at once. Events sit in
# an in-flight buffer until a session ends; on a runner no session ends, so no chain was
# ever created and `audit verify` answered CHAIN_MISSING on every commit — a step that
# could not pass, and one that would have verified nothing if it had. `SessionEnd` now goes
# through the real dispatcher first, exactly as a surface fires it, so verify reads a chain
# holding this job's own links.
# 52,957 to 53,024 for the first SonarCloud run this branch ever had. It had been skipped
# on every commit — it needs the coverage artefact from a job that was failing — so 253
# commits of new code met it at once, and four of the twelve findings were real. One is a
# path traversal in our own record verb: `--accept` put command-line text straight into a
# glob, `..` is a legal glob segment, and the rewrite that follows would have edited a file
# outside `docs/adr`. The other three: an acceptance schema whose patterns are compiled
# against text a person wrote and whose bytes nothing pinned, a redundant alternative that
# made a lone dot look special when it never was, and an alternation left to precedence.
# 53,032 to 53,112 for the two that a validated argument does not settle. The traversal
# fix was right and the scanner still reported it, because a promise about one call is not
# a property of the code: `accept` now reads `docs/adr` and compares names, so every path
# it handles comes from that directory and the argument never reaches path construction at
# all. The same shape one file over: the acceptance contract's seven expressions are
# written out in source and `_pattern` refuses one it does not hold, so nothing compiles an
# expression out of a file's contents. The digest pin stays; it is the promise, and this is
# the property. A test holds the two sides together in both directions.
# 53,112 to 53,149 for a forgery the scanner found by pointing at the wrong thing. It kept
# reporting `accept`'s write after the traversal was gone, and the flow it drew ran through
# the file's own bytes into the header — not a path fault, and a real one underneath it.
# The role and the reference come from `.ai/intent.md`, which a person edits, and they were
# interpolated between bare quotes: a role holding a newline wrote its own frontmatter, so
# `status`, `supersedes` and `spec` were each one newline away from being forged by editing
# the Intent. In the file whose whole purpose is to be the thing that cannot be forged.
# Both are quoted through `json.dumps` now, as every other field of that header already
# was, and a fixture writes `status: "rejected"` through the old code and fails.
# 53,158 to 53,181 for a number that lived only in a sentence. `specs/015` says eleven of
# the fourteen prohibitions are decidable by absence and names the three that are not; the
# register shipped with seven arguing their case, and nothing compared the two. `just
# register` prints the split from the register on every run now, and the test reads the
# expected numbers off the register rather than writing them down — a number typed into a
# test is the same defect one file further along. The sentence in the specification is
# still wrong: correcting it moves an approved digest, and the gate refused the edit,
# which is the gate working. It is on the list of things owed to the operator.
# 53,189 to 53,543 — 354 lines, the largest raise in this file, and all of it one document.
# `docs/audit-2026-08-16.md` is the goal's terminal deliverable: every one of the 385
# requirements in the evolution proposal classified against this tree, the 192 proven ones
# as ranges and each of the 193 that are not proven on its own line with the reason. The
# arithmetic: 137 lines of finding and argument, 217 of appendix, and the appendix is the
# part that cannot be compressed further without deleting the demonstration itself — a
# table where a row says "measured elsewhere" proves nothing to the person reading it.
# `docs/adr/` is excluded from this count and `docs/` is not, so an audit pays where a
# decision does not. That asymmetry is worth an argument; it is not worth shrinking the
# audit to avoid having it.
# 53,553 to 53,676 for the gate nobody had ever seen the output of. Measured: a whole-tree
# mutation run is 20,816 mutants and 121 minutes, against a job capped at 30 — so it never
# finished, never printed a score, and was reported as `cancelled` on every commit for
# weeks. The score, when it finally printed, is 71% against a floor of 89: the floor was
# earned on a 42,000-line tree and P1 to P5 added 11,000 whose tests kill fewer mutants.
# The whole tree now runs on a schedule and blocks nothing; the pull request runs over its
# own diff and blocks on the floor. `anti_theatre` accepts the scoped run only against a
# receipt showing a whole-tree run that completed inside four days — read from the server,
# because the branch is what is being judged. Not "and passed": requiring green there would
# mean nothing merges until the whole standing backlog is cleared, which is a different
# decision and not this one's to take.
REPO_CEILING = 53_687

# The shape of that total, not just its size. This began as a sentence in the comment above
# saying the test plane was three times the product; it was written from no measurement and
# it was wrong — the ratio is 1.68. An unmeasured number in a governance file is the defect
# this product is about, so the sentence is deleted and the measurement is a gate instead.
#
# 2.0 and not 1.7: there is no industry law here, the working heuristic is one to two lines
# of test per line of product, and the ceiling above already caps the total. This one catches
# the shape the ceiling cannot see — tests padded to chase a mutation number, or a product
# that shrank while its tests did not.
TEST_RATIO_MAX = 2.0
PRODUCT = ("src/", "hooks/")
TESTS = ("tests/",)


def audit(root: Path) -> list[str]:
    skills = sorted(root.glob("ai-*/SKILL.md"))
    if not skills:
        return [f"no skills found under {root}"]
    return [problem for skill in skills for problem in audit_one(skill)]


def audit_one(path: Path) -> list[str]:
    name = path.parent.name
    found: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) > CEILING:
        found.append(
            f"{name}: {len(lines)} lines. Over {CEILING} means it is a procedure "
            f"that should be a script."
        )
    try:
        header = text.frontmatter(path)
    except ValueError as why:
        return [*found, f"{name}: {why}"]

    unknown = set(header) - SPEC_FIELDS - EXTENSIONS
    if unknown:
        found.append(
            f"{name}: {sorted(unknown)} are not in the contract. Every extra field "
            f"is hidden behaviour in a file nobody re-reads."
        )
    if header.get("name") != name:
        found.append(f"{name}: the name field says {header.get('name')!r}")
    description = header.get("description", "")
    if not description:
        found.append(f"{name}: no description. That field is the routing decision.")
    if len(description) > DESCRIPTION_MAX:
        found.append(
            f"{name}: the description is {len(description)} characters, over {DESCRIPTION_MAX}"
        )
    if "Not for" not in description:
        found.append(
            f"{name}: the description has no 'Not for X — use /ai-Y' clause, which is "
            f"the line that stops the wrong skill from firing."
        )
    if header.get("context") == "fork" and header.get("background") != "false":
        found.append(
            f"{name}: context: fork without background: false. A forked skill runs in "
            f"the background by default, so its verdict lands out of order and /rewind "
            f"will not undo its edits."
        )
    if "when_to_use" in header:
        found.append(f"{name}: when_to_use shares the description's character budget")
    body = "\n".join(lines).lower()
    for word in JARGON:
        if word in body:
            found.append(f"{name}: {word!r} — write it so somebody who does not code can follow")
    found.extend(_corpus_problems(path.parent, name))
    return found


ROUTES = "## Routes here"
REFUSES = "## Refuses"


def _corpus_problems(folder: Path, name: str) -> list[str]:
    """The two lists a skill is judged by, in the skill's own directory.

    Everything above this checks the file's *shape* — its fields, its length, its
    vocabulary. None of it can tell a skill that routes correctly from one that fires on
    everything, so a skill whose description overlapped its neighbour's passed every gate
    this repository had. Spec 012 D-012-01: no skill file lands before a case it must take
    and a case it must refuse.

    Plain markdown beside the skill, not a registry: one more home is one more thing to
    keep in sync, and the audit has already found four copies of a list this week. The
    refusal half is the one that matters — "what it does" is in every description ever
    written, and "what it must not do" is the half that stops the wrong skill firing."""

    corpus = folder / "corpus.md"
    if not corpus.exists():
        return [
            f"{name}: no corpus.md. A skill needs a case it must take and a case it must "
            f"refuse, or nothing can tell it apart from the skill beside it."
        ]
    text_ = corpus.read_text(encoding="utf-8")
    problems = []
    for heading in (ROUTES, REFUSES):
        section = text_.partition(heading)[2].partition("\n## ")[0]
        if heading not in text_ or not [
            line for line in section.splitlines() if line.strip().startswith("- ")
        ]:
            problems.append(f"{name}: corpus.md has no cases under {heading!r}")
    return problems


# Not the product, so not counted, and these two reasons are the only ones that qualify:
# the record grows by design every time a decision is written down, and nobody here wrote
# the licence or can shorten it. Everything we chose to write, documentation included, counts.
NOT_THE_PRODUCT = ("specs/", "docs/adr/", "LICENSE", "NOTICE")


def tracked(root: Path) -> list[str]:
    names = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, timeout=30
    ).stdout.split()
    if not names:
        raise ValueError(f"git listed no files under {root}, so this counted zero lines")
    return names


def count(root: Path, names: list[str]) -> int:
    total = 0
    for name in names:
        try:
            total += len((root / name).read_bytes().decode("utf-8", "replace").splitlines())
        except OSError:
            continue
    return total


def repo_lines(root: Path) -> int:
    """Every committed line of the product. The ceiling is the mechanism that prevents a
    second 436,091: not discipline, an exit code."""
    names = [n for n in tracked(root) if not n.startswith(NOT_THE_PRODUCT)]
    return count(root, names)


def test_ratio(root: Path) -> tuple[int, int]:
    """Test lines against product lines. Both halves are counted the same way and from the
    same index, so the answer cannot drift the way a hand-written number does."""
    names = tracked(root)
    tests = count(root, [n for n in names if n.startswith(TESTS)])
    product = count(root, [n for n in names if n.startswith(PRODUCT)])
    if not product:
        raise ValueError(f"no product files under {root}, so this ratio measured nothing")
    return tests, product
