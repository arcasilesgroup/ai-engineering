---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0010"
title: "A scanner finding is answered in the scanner"
date: "2026-08-16"
spec: "010"
status: "proposed"
supersedes: ""
---

# 0010. A scanner finding is answered in the scanner

## Context and problem statement

SonarCloud had never run on this branch. It reads a coverage artefact produced by a job
that was failing, so it was skipped on every commit, and 253 commits of new code met it in
one analysis. It returned twelve findings and failed the quality gate on two conditions:
`new_reliability_rating` 3 and `new_security_rating` 5.

Five were real and are fixed:

| finding | what it was |
|---|---|
| `S2083` `decide.py` | `--accept` put command-line text into a glob pattern. `..` is a legal glob segment, so a number spelled as a path matched a file outside `docs/adr` and the rewrite that follows would have edited it. |
| `S2083` `decide.py` | `authority_role` and `approval_ref` come from `.ai/intent.md`, which a person edits, and were interpolated between bare quotes. A role holding a newline wrote its own frontmatter lines, so `status`, `supersedes` and `spec` were each one newline away from being forged. |
| `S2631` `acceptance.py` | The register compiled a regular expression out of a policy file's contents and ran it against text a person wrote. |
| `S1155` `capability.py` | An alternative that matched nothing the character class beside it did not, reading as though a lone dot were special. |
| `S5850` `update.py` | An alternation inside a lookahead left to operator precedence. |

Nine remain. Each has been traced from its reported sink to the source SonarCloud names,
and each rests on one of two premises that are false for this program:

1. **`sys.argv` is an attacker's HTTP request.** Every remaining flow begins at
   "Source: a user can craft an HTTP request with malicious content" on a line that reads
   an argparse namespace. This is a command-line tool: its arguments are the operator's
   own instruction. `ai-eng init --project X` writing into `X` is the feature, not a
   traversal. And where a value does become a path component, it is validated twice
   before it gets there — the spec slug against `^[a-z0-9]+(?:-[a-z0-9]+)*$` with an
   80-character bound at the argparse layer, and again by `spec_transaction._parts`,
   which refuses backslashes, NUL, absolute paths, and empty, `.` and `..` segments read
   before `PurePosixPath` can normalise them away. `--project` passes `_lexical_path`,
   `_safe_path` and `_project_paths_safe` before anything is written.

2. **`Path.write_text(data)` is a path sink.** Three flows end at a write whose *first
   argument is the content*, not the path. In `decide.accept` the tainted value is the
   record's own bytes being rewritten in place; in `issue` it is the payload, which
   `issue.scan` has already run machine-path, PII and gitleaks detection over before
   anything is drafted. The path in each case is a fixed name under a directory this code
   opened itself.

## Considered options

1. **Restructure the code until the analyser recognises the validation.** Attempted twice.
   The traversal fix was correct and the finding survived it; the digest pin was correct
   and the finding survived it. Only removing the shape entirely worked, and only where
   there was a shape to remove. For the nine that remain there is nothing to remove: the
   validation exists, is executed, and is covered. Moving it to a spelling a heuristic
   recognises makes the code differently shaped and no safer, and each attempt costs a
   full analysis to evaluate.
2. **Lower the quality gate.** Weakens a control permanently, for every commit after this
   one, to answer nine findings on one branch. It also hides the next real finding, which
   is the failure mode this repository exists to cure.
3. **Answer each finding in SonarCloud, as a false positive, with its reason.** The
   analyser has a resolution workflow and this is what it is for. It is not a suppression
   in the source: rule 3 forbids `noqa`, `ts-ignore` and `nosec` because they are
   invisible to everyone except the person who reads that line. A resolution in SonarCloud
   is attached to the finding, carries an author and a date, is visible to every reviewer
   on the project, and is reopened by the analyser if the code around it changes.
4. **Leave it red.** The pull request cannot merge; SonarCloud gates `CI Result`, which
   branch protection requires. A red that nobody can clear is a red everybody learns to
   scroll past, which is the same failure as a green nobody earned.

## Decision outcome

Option 3. The repository owner chose it on 2026-08-16, in answer to a question that named
all four options and stated that option 1 had already been attempted twice.

The nine are resolved in SonarCloud as false positives, each with the reason above. The
five real findings are fixed in code, with a fixture apiece that fails against the version
before the fix — both directions were run, not asserted.

This decision does not extend to future findings. A scanner finding is investigated to its
source before it is answered, and the record of that investigation is what makes the answer
reviewable. Five of these twelve were real, including one that let a file outside `docs/adr`
be rewritten and one that let an edited Intent forge the header of the record that judges
it. A policy of dismissing this analyser would have kept both.

## Consequences

The gate goes green on evidence rather than on a threshold that was moved to fit. The
reasoning is in this file rather than in nine scattered comments, and a reader who disagrees
has one place to argue with.

What gets worse: a resolution lives in SonarCloud and not in this repository, so it is the
one piece of this record that a clone does not carry. That is the cost of answering a tool
in the tool, and it is why the reasoning is written here as well.

The premises are worth revisiting. `S8705` and `S8707` are aimed at code an agent invokes
with arguments it did not choose, and this product is invoked by agents. The refusals those
rules ask for exist here and are tested; if that ever stops being true, these resolutions
are wrong and the findings should come back.
