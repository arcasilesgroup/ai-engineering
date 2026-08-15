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
REPO_CEILING = 47_882

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
