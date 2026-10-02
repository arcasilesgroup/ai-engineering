---
name: ai-github-triage
description: >-
  Reads every open issue and pull request of a repository and writes one ranked, actionable
  page at .ai-engineering/triage.html: what is broken, what is already answered, what to
  close, and the three things to start on first, each claim backed by a permalink at a
  commit SHA. Read-only: it never comments, labels, closes, merges or reviews anything on
  GitHub. With no argument it triages this repository; given a URL or owner/repo it triages
  that backlog instead. Trigger for "triage", "triage the issues", "go through the
  backlog", "what should we work on next". Not for diagnosing one failure (/ai-debug), not
  for reporting a fault (/ai-issue-report), not for judging a diff (/ai-verify).
license: Apache-2.0
---

# ai-github-triage — read the backlog, rank it, touch nothing

One page that answers "what should we work on next", built from every open issue and pull
request, with each claim pinned to the line of code that proves it. The output is a
decision surface: a ranked queue at the top, the evidence behind it below, the commands to
start at the end. Nothing this skill does reaches GitHub.

## What it produces

One file, `.ai-engineering/triage.html`, rewritten in place by every run of the same
repository. It is a slot, not a numbered folder: the page is the backlog's current state,
and git keeps what the last run said.

## The absolute rule: read-only

The page is the only artifact. Every mutation of GitHub state is a failure of this skill,
not a shortcut in it.

| Forbidden | Allowed |
|---|---|
| `gh issue comment`, `gh issue close`, `gh issue edit` | `gh issue view`, `gh issue list` |
| `gh pr comment`, `gh pr merge`, `gh pr review`, `gh pr edit`, `gh pr checkout` | `gh pr view`, `gh pr list`, `gh pr diff` |
| `gh api -X POST`, `-X PUT`, `-X PATCH`, `-X DELETE` | `gh api` without a method (GET) |
| `git checkout`, `git switch`, `git fetch`, `git pull` on a branch under review | `git log`, `git show`, `git blame`, `git rev-parse` |
| Labeling, assigning, reopening, transferring | Reading the tree, the diff and the history |

No subagent gets a verb from the left column. A PR row says `MERGE` or `BLOCKED`; a human
merges. The single tempting exception, "just close the duplicate", is the rule's own
example of a violation.

## Which repository (the scope rule, decided before anything else)

- **No URL** — the current repository: `gh repo view --json nameWithOwner -q .nameWithOwner`.
  If the directory is not a git repository or `gh` has no repo, say which of the two failed
  and stop.
- **A URL, `owner/repo`, or a path to another checkout** — that backlog: `https://github.com/owner/repo/issues`,
  `https://github.com/owner/repo/pulls`, the bare slug, or a directory that has a remote.
- One run, one repository. Never merge two backlogs into one page, even when the same
  project owns both. State the target on the page (`ai-triage-repo`) so the next run knows
  which backlog this was.

## Steps

1. Resolve the scope from the argument, and say out loud which repository is being read.
2. Read the whole open backlog, not a sample:
   `gh issue list --state open --limit 1000 --json number,title,labels,milestone,reactionGroups,comments,createdAt,updatedAt,author,closedByPullRequestsReferences,body`
   and `gh pr list` with the same fields plus `mergeStateStatus`, `mergeable`,
   `reviewDecision`, `headRefName`, `closingIssuesReferences`, `isDraft`. Above 1000
   items, page with `--search "created:<oldest-in-page"` until a page comes back
   empty. A truncated backlog is a wrong page: an item nobody read is an item the
   ranking silently dropped. **Write down the count you fetched and make the page
   agree with it.** An active repository carries several times more open items than
   its newest page shows; reading the first page and calling it the backlog is the
   commonest way this page goes wrong, and it fails silently.
3. Join the two halves before classifying. `closedByPullRequestsReferences` on an
   issue and `closingIssuesReferences` on a pull request are one edge read from both
   ends: they are how a row knows it is already fixed, and how the page shows one
   item in two sections without the reader wondering whether it is two items. Keep
   labels, milestone, reaction count, comment count and age as the item's SIGNALS;
   they are the tie breaks.
4. Classify each item: question, bug, feature, pull request, or other. Do it from the
   title, the labels and the body, in that order.
5. One subagent per item, five in flight at a time. Each reads its own item and returns
   one analysis block (§The analysis block), in the conversation. When the backlog runs
   past a few dozen items, hand each subagent a batch of at most five neighbouring
   items and require one block per item - the block is the contract, not the messenger.
   No subagent writes a file, and a subagent that was handed no item reports that
   instead of inventing one.
6. Rank what came back (§Ranking) and write the page (§The page). An item nobody
   assessed is still on the page, with `UNASSESSED` as its verdict: the reader must be
   able to see the whole backlog, and a section that silently omits the tail is a
   worse lie than a row that says it was not read.
7. Close with the answer in the conversation: the three first moves, and the `file://` URL
   of the page. The page is the artifact; the reply is the summary.

## The analysis block

Every subagent returns exactly this shape, one per item, so the ranking is arithmetic over
uniform input instead of prose to re-read:

```
ITEM: #<number> <title>
KIND: ISSUE | PR
TYPE: BUG | QUESTION | FEATURE | PR_BUGFIX | PR_OTHER | OTHER
VERDICT: CONFIRMED_BUG | NOT_A_BUG | ALREADY_FIXED | NEEDS_INFO | ANSWERED | FEATURE | PR_READY | PR_BLOCKED | UNASSESSED
SEVERITY: CRITICAL | HIGH | MEDIUM | LOW | NONE
SEVERITY_BASIS: <the sentence in the thread that earns that level, or the fact that admits none>
EFFORT: HOURS | DAY | WEEK | UNKNOWN
REPRO: YES | PARTIAL | NO
DEPENDS: <the #numbers or PRs this waits on, or none>
SIGNALS: <reactions, comments, labels, milestone, linked PR, age - counts only, no prose>
CONTEXT: <2-4 sentences of plain language for an engineer who has read nothing: what the item is about, what it breaks or unblocks, what happens if nobody touches it. No jargon the title did not already introduce. Never a restatement of the title.>
EVIDENCE: <permalink per claim, one per line; a claim with no permalink is [UNVERIFIED]>
ROOT_CAUSE: <file:line for CONFIRMED_BUG, else none>
DRAFT_ANSWER: <the reply to send verbatim, or NEEDS_MANUAL_REVIEW>
FIRST_MOVE: <the one command or edit that starts this item>
```

`CONTEXT` is what the page's expandable body shows, and it is the field a reader
actually uses: the title says what changed, `CONTEXT` says what it means. Write it
for someone who joined today and cannot open the issue.

Subagents may read the tree, search history for the fixing commit
(`git log --oneline --grep=<keyword> -i --all`, then `git show`), and read GitHub with
the allowed verbs above. Nothing else.

## Verdict and severity: earned, never assumed

This skill ranks; it does not diagnose. It never runs /ai-debug, never reproduces a
bug and never runs the product, so a verdict is a claim about the evidence in the
thread, and it is only as strong as what the thread shows:

- `CONFIRMED_BUG` requires the report or an owner comment to name the failing
  behaviour with a file, a line, a log or a reproduction step. Without one the
  verdict is `NEEDS_INFO`, never `CONFIRMED_BUG`.
- `ALREADY_FIXED` requires a linked pull request or commit that names the issue.
- `UNASSESSED` is the verdict for an item the run catalogued but did not read. It
  is honest and it is allowed; inventing a verdict to fill a column is not. The
  page's Method section states how many items got each treatment, so a thin run
  cannot pass for a complete one.

Severity is relative to the person using the software, never to the size of the
diff:

| Level | Means |
|---|---|
| CRITICAL | Unusable or unsafe: crash on start, data loss, a security hole, or a block with no way back |
| HIGH | A core path is broken or silently wrong with no workaround the user can find, or it holds a release |
| MEDIUM | A real defect with a workaround, a flaky gate that burns a re-run, or a wrong value the user can see |
| LOW | Cosmetic, a documentation gap, or a wrong value nobody acts on |
| NONE | Not a defect: a feature request, a question, a maintenance task |

`SEVERITY_BASIS` names the sentence that earns the level, so a reader can disagree
with the ranking instead of guessing at it.

## Evidence rule

A claim without a permalink carries no weight: it is written as `[UNVERIFIED]` or it is not
written. A permalink points at a commit, never at a branch:

```
https://github.com/<owner>/<repo>/blob/<commit-sha>/<path>#L<start>-L<end>
https://github.com/<owner>/<repo>/commit/<fix-sha>
```

`git rev-parse HEAD` gives the commit for a claim about the tree as it stands. A branch name
in a permalink is the mistake that makes a report argue with its own evidence a week later.

## Ranking: what to start on first

The top of the page is a queue, and the order is stated, not felt. Band first, then the tie
breaks.

| Band | Criteria | First move |
|---|---|---|
| P0 | Build red, data loss, security, or `ALREADY_FIXED` | Verify the fix on today's tree and close it: the cheapest win on the page |
| P1 | `CONFIRMED_BUG` with a reproduction and severity HIGH or CRITICAL | Open the file the permalink names and fix the root cause |
| P2 | `CONFIRMED_BUG` without a reproduction, or severity MEDIUM | Reproduce it first; the repro is the work |
| P3 | `ANSWERED` question, `NEEDS_INFO`, `PR_BLOCKED` on the author | Send the draft answer, ask the one question, or ping the review |
| P4 | `FEATURE` assessed as EASY or MODERATE, `PR_READY` | Review the PR or write the one-file change |
| P5 | Stale, duplicate, out of scope, `NOT_A_BUG` | Close it, or park it with the reason on the page |

Tie breaks, in order: severity, how many people the item blocks (reaction count,
duplicate reports, linked threads), then age. The band is a chip on the row
(`.band-p0` .. `.band-p5`) and the order of the rows is the rank, so there is no
ordinal column to fall out of date. The page's `.legend` carries the band key: a
colour the reader cannot look up is decoration, not a ranking.

## The page

Start from [templates/triage.html.tpl](../../templates/triage.html.tpl), fill it, and keep
its structure: the working page is that template with the `{{placeholders}}` replaced.

- `<header class="hero">` carries the stamp `Triage · <owner/repo> · <date>`, the h1
  `What to work on next`, a `.sub` with the count of open items and the date of the last
  item read, and a `.meta` line with the commit, the scope and the tools used.
- The sections, in the template's order: Snapshot (the counts and the `.legend` that keys
  every chip), Start here (the ranked queue), Fix now, Answer, Close or park, Feature
  requests, Pull requests, Catalogued (the items this run did not read, so the backlog is
  whole), First moves, Method. A section with nothing in it is deleted and the survivors
  are renumbered `01` to `N`, so the nav has no hole: an empty heading reads as "we found
  nothing", which is a different claim from "we did not look". Number the sections from
  the surviving list, never from a hard-coded map, or the `also in` links point one
  section too far the moment a section is dropped.
- Sticky `<nav>` with one `<a>` per surviving section, `<main id="main">`, `<footer>` with
  the `{ai}` mark.
- Two `<meta>` tags in `<head>`, so a later run can tell one triage from another:
  `<meta name="ai-triage-repo" content="<owner/repo>">` and
  `<meta name="ai-triage-sha" content="<commit>">`.
- Every item on the page is the same `.item`: a native `<details>` whose `summary`
  carries the chips, the linked `#id` and the title, and whose body carries the
  `CONTEXT`, the evidence and the `also in` cross-refs. Native disclosure, not a
  script, so keyboard, find-in-page and print keep working.
- Section 02 is the page's job: the ranked queue, one `.item` per ranked entry,
  best first, each id linking to the issue, each row carrying the band chip. A
  reader who stops after section 02 must already know what to open first.
- The id is the link. `#2497` in a row is an `<a>` to the issue, in every section,
  because the id is what the reader wants to click.
- Cross-section duplicates are shown, not hidden: an issue that is already fixed
  sits in Close or park *and* in the queue, both rows carry `id="i<number>"`, and
  the evidence line names the other sections. The page must let a reader see it is
  one item, not two.
- The shell is copied, never retyped: the `{ai}` favicon, the `<nav>`, the CSS
  block and the scroll-spy script come from the template byte for byte. A
  hand-rolled scroll-spy is how the nav stops marking the section in view;
  `bun test tests/artifact-scroll-spy.spec.ts` is the gate that catches it.
- The `<title>` leads with the artifact and the repository
  (`Triage · <owner/repo> · <date>`) so a narrow browser tab still says which page
  it is and which backlog it read.

## Design: one family, four lenses

The page is an ai-engineering artifact, so its style is the artifact design system and its
carrier is the template, never a stylesheet invented for the report:
[ai-brainstorm › references/artifact-design.md](../ai-brainstorm/references/artifact-design.md).

The template carries the canonical CSS block, the `{ai}` favicon and the scroll-spy script
verbatim. Copy the file and fill it; do not write a `<style>` block, and do not add a
colour, a font or a component the block does not have. The layout gate fails a page whose
prose is centred or capped, or whose sections sit outside `.container`.

Hierarchy, spacing and reading order are a separate craft, and when those skills are
installed they are the ones to hand the page to: **impeccable** (visual polish and
anti-slop), **apple-design** (materials, restraint, spring feel), **design-taste-frontend**
(typography and editorial hierarchy) and **emil-design-eng** (component detail and animation
decisions). They work inside the artifact design system, not around it: they may reorder a
row, tighten a table, sharpen an empty state; they may not replace the tokens, and a diff
in a token is a defect rather than a preference. When none of them is installed, the
template is the whole design and the run does not degrade.

## The ai-engineering seam

1. Output path: `.ai-engineering/triage.html`, rendered from
   [templates/triage.html.tpl](../../templates/triage.html.tpl) with the artifact design
   system. It is written with the file tools; `rm`, `mv` and `tee` into `.ai-engineering/`
   are denied, because a verb that can act on several paths is judged as a whole command.
2. The page is a slot like `recap.html`: the next triage of the same repository replaces
   it, and nothing cites it as a governor. It never blocks or opens a milestone.
3. Grounding duty: never cite a file, a line or an API that was not opened in this run.
   The permalink is that duty made checkable, and a subagent's report is a claim, not an
   instruction.
4. The ranking is the handoff: an item the human picks from section 02 becomes a
   brainstorm, and the analysis block for that item is its first input.

## Done when

- Every open item is on the page, and the counts add up to the size of the backlog
  you fetched. An item the run did not read says `UNASSESSED`; it is never dropped
  and never given a verdict it did not earn.
- Every claim carries a permalink at a commit SHA, or is marked `[UNVERIFIED]` and stays
  marked.
- Every chip on the page has its key in the `.legend`, and every duplicate is
  visible as one item through its `also in` line.
- Scrolling marks the nav link of the section in view, because the script is the
  template's, copied byte for byte.
- The page opens from `file://` with no sideways scroll, section 02 names what to start on,
  and section 08 holds the commands to start it.
- Nothing was written to GitHub: no comment, no label, no close, no merge, no review.
- The reply names the `file://` URL of the page and the three first moves.

## What this is not

- Not a diagnosis of the client's own tree: a fault with a cause at `file:line` is
  /ai-debug, and triage stops at ranking it.
- Not a report sent anywhere: drafting an issue for an upstream project is
  /ai-issue-report, and this skill never crosses from reading to publishing.
- Not a merge decision: a PR row says `MERGE` or `BLOCKED` with the check that says so, and
  the human merges.
- Not a backlog for two repositories at once, and not a sample of one.
- Not a second design system: the page reads as one family with the brainstorm, the
  research pages and the recap, because it is built from the same block.

## Routing

In scope: "triage the backlog", "what should we work on next", "go through the open issues",
"is anything ready to close", "triage this repo" with a URL attached.

Not for: one failure in your own code (/ai-debug), filing a fault (/ai-issue-report),
judging a finished diff (/ai-verify), deciding what to build (/ai-brainstorm), evidence from
outside the repository (/ai-research).

## Lifecycle

Lane: any
Writes: .ai-engineering/triage.html
Read by: the human who decides what to work on next; ai-brainstorm once a triaged item becomes work
Dies: replaced by the next triage of the same repository; git keeps the history
Next: ai-brainstorm when the human picks an item to build; none when the page only closed items

Source: ai-engineering (own), Apache-2.0.
