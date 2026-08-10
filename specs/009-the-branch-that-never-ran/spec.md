---
id: "009"
slug: the-branch-that-never-ran
status: shipped
date: 2026-08-10
ref: ""
supersedes: ""
---

# The branch that never ran, and the twenty-one things a survey found in it

## Context and problem

`v1` is a hundred and twelve commits of finished code that never left one laptop. Both
workflows are written to fire on a push to this branch and no push has happened, so `just
check`, the install matrix on three platforms, the packaged-guard denial, `doctor --ci` and
`audit verify` have only ever run where they were written. Rule 6 asks for the output of the
gate before anything is called done, and the only output anyone can show is local.

A survey read the tree against its own record and found twenty-one things still open. Some
were defects with an alarm already on them — three strict xfails, which is this repository's
way of committing to a bug rather than forgetting it. Some were sentences that had become
false: the README describing a file `init` writes as a file `init` prints, a doctrine file
saying "eight guards" eight lines above "five guards", a constitution pointing at a §11 that
does not exist. Some were risk acceptances whose stated reason the tree contradicted. And
one was the arithmetic: the line ceiling sat at exactly zero headroom, so no fix could land
without the conversation the ceiling exists to force.

The version already reads 1.0.0 in three files while the changelog still called every
breaking change since spec 002 "Unreleased".

## Options considered

1. **Push first, then fix what CI says.** The gate is the point, and everything on the list
   is a prediction until a runner agrees. Against it: the list is already known and most of
   it is not something CI can see — a false sentence in a README passes every check ever
   written, and so does a risk acceptance justified by something that is not true.
2. **Fix the list, then push once.** One green to read instead of a sequence of reds that
   each need a commit to interpret. Against it: everything stays a prediction for longer,
   and a fix nobody has run on Linux, macOS and Windows is a fix on somebody's word.
3. **Fix only what blocks, defer the rest to another spec.** Cheapest. Against it: eleven of
   the twenty-one are records that are wrong, and a record left wrong on purpose is the
   thing this project sells against.

## Decision

Option 2, and then the push, in that order. The list is closed here, the ceiling moves once
with its arithmetic written down, and `v1` goes to `origin` as the branch that becomes
`main`.

One item on the list was argued about twice and the runner settled it. The survey called
`extractions/setup-just` a blocker. A review pass refuted that — `main` runs `dorny/*` and
`open-policy-agent/*`, neither GitHub-owned nor verified, and its workflows start — so the
change was cut and this paragraph originally said the premise was false. Then the branch was
pushed, and `check` came back `startup_failure` with no jobs and no logs while `install`, on
the same runner with three fewer actions, ran green. The policy is
`github_owned_allowed: true`, `verified_allowed: false`, and nine patterns by name:
`pypa/*`, `astral-sh/*`, `SonarSource/*`, `CycloneDX/*`, `EndBug/*`, `dorny/*`,
`open-policy-agent/*`, `step-security/*`, `ossf/*`. `dorny/*` works on `main` because it is
on that list, not because it is verified, and the refutation read one as the other. The
survey was right. `just` now comes from PyPI through the uv already set up — here and in the
workflow `init` writes into other people's repositories, because an action our own gate
cannot start is not something to hand a stranger.

## Decisions

```yaml
adr: 0004
title: No document mould from another repository enters this framework
```
```yaml
decision: The line ceiling rises to 17,011
date: 2026-08-10
rationale: It stood at 16,803 against a total of 16,803 — zero headroom, so the first line of any fix failed the build. The 208 lines buy, with the last twenty of them the paragraph in contract.py that records this move: 44 for the buffer stamp that closes the tamper defect and the test that proves it, 43 for the Unicode fold and the twelve-variant recall measurement R-001-04's follow-up demanded, 34 for the install matrix finally exercising doctor --fix, the closing report, the copy branch of wiring.link and an uninstall assertion that is not also true of a run that removed nothing, 30 for the changelog entries rule 4 requires of three breaking changes, 21 for the guard-count pin and the payload-dialect case, and 16 for the doctor and justfile fixes. The two fixes that cost nothing are stated too: audit.read and spec.next_number came to net zero because the strict-xfail markers they retire are longer than the guards that replace them.
```
```yaml
decision: The live-denial check stays a prompt and is not written as a flag
date: 2026-08-10
rationale: Rule 12 says a judgement that cannot fail closed stays a prompt with the reason written down. `run.py --live-claude` cannot run inside `just check`, spends a person's credentials, hard-codes six flags of a third-party binary that are true this week, and — worst — writes the field doctor assertion 9 reads, so it would turn that assertion green on the word of whoever typed the command with nothing recording that they did. That is the earned-green failure this project exists to cure, built by hand. R-003-05 stays open with its follow-up unchanged.
```
```yaml
decision: The buffer stamp is shipped with its ceiling stated rather than implied
date: 2026-08-10
rationale: A buffered event now carries an HMAC keyed from a 0600 file outside every clone, and a line that arrives without this machine's mark is sealed as the error that says so instead of as a decision. The key is a file, so anything running as the same user can read it and stamp what it likes: this detects the agent that edited the buffer without reading the key, which is the attack in the defect report, and raises the bar against nothing that did. That sentence is in the changelog and in the risk block rather than only in a docstring, because a security control described better than it behaves is worse than no control.
```
```yaml
decision: docs/tools.md is unlinked from the user-facing documentation rather than corrected
date: 2026-08-10
rationale: Three places described it as the list of per-stack binaries `init` does not install, and it is a Spanish contributor cheat-sheet for running `just check` in this repository. The README list is the PyPI long description, read by a stranger who does not have this repository, so a corrected line would still send them to a page in a language the rest of that page is not written in. The bullet is deleted and the two sentences `init` printed stop naming the file; the file stays where it is, for the contributors it was written for. Delete before you abstract.
```
```yaml
decision: v1 replaces main rather than merging into it
date: 2026-08-10
rationale: `git merge-base main v1` exits 1. This branch was written from an empty folder with its own root commit, so the two histories share nothing and there is no merge to make: any attempt produces a diff of every file in both trees. The old history is not destroyed by this, it is left reachable by tag, and the wheel on PyPI is unaffected until a release runs. This is the one step here that is not reversible by `git revert`, so it is the operator's to authorise and it happens after the first green CI, never before.
```
<!-- ai-eng decide writes yaml blocks here -->

## Accepted risks

```yaml
id: R-009-01
finding: buffer-stamp-key-is-readable-by-the-same-user
severity: medium
accepted_by: soydachi
accepted: 2026-08-10
expires: 2026-11-08
renewals: 0
justification: the stamp that closes the buffer-tamper defect is an HMAC keyed from ~/.ai-engineering/buffer.key, written 0600 outside every clone. self_protect denies writes to that directory and not reads, and the agent runs as the same user, so `cat` on that file is enough to forge any stamp. What this detects is a buffer edited by something that did not read the key — the attack in the defect report and the one an agent actually performs — and it raises the bar against nothing that did. Nothing here defends the durable chain against a process already writing freely in the application folder either; the git anchors are what do that, and they are unchanged.
follow_up: renew with the reason, or close it by moving the seal off the machine — an anchor written at emit time rather than at flush, or a second party — and never by widening the file's permissions, which are already as narrow as a file gets.
```
```yaml
id: R-009-02
finding: the-fixes-are-green-on-one-machine-only
severity: medium
accepted_by: soydachi
accepted: 2026-08-10
expires: 2026-09-10
renewals: 0
justification: every change in this spec was gated with `just check` on one macOS laptop, and the install matrix that would run it on Linux, macOS and Windows has still never executed, because that is the last step of this spec rather than a step inside it. The install-matrix changes in particular are the ones no local run can exercise: a pre-created skills root, `doctor --fix` on a torn settings file, and an uninstall assertion, all written against code that was read rather than against a runner that ran.
follow_up: read the first CI on this branch and close this at that run, or fix what it says and close it at the run after; this expires in a month because a month is longer than it should take to press push.
```
**R-009-02 `the-fixes-are-green-on-one-machine-only` was closed on 2026-08-10, not
renewed.** The first run found the lockfile missing from a clean checkout and eight Sonar
flows; the next exposed a stale two-call assumption in the repository's own Quality Gate
reader. At `bece5b4a`, [install run 31415890269](https://github.com/arcasilesgroup/ai-engineering/actions/runs/31415890269)
passed on Ubuntu, macOS and Windows, and [check run 31415890187](https://github.com/arcasilesgroup/ai-engineering/actions/runs/31415890187)
passed `check`, suite, mutation, mypy, SonarCloud, Snyk and the aggregate CI Result. The
checks are `gh run view 31415890269` and `gh run view 31415890187`; both read `success`.
<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [x] CI/CD — `just check` green locally at 817 tests and `python tests/adversarial/run.py` at 14 of 14; `gh run view 31415890187` reads success for all seven check jobs and `gh run view 31415890269` reads success for the Ubuntu, macOS and Windows install matrix. R-009-02 is closed at those runs
- [x] Logs — `ai-eng digest`: every verb still emits one JSON line per run, and this spec adds an event nobody could write before — the seal of a buffered line that arrived edited, as class `error`
- [x] Traces — not applicable, and that is the rule: one process, no second hop, no trace
- [x] Errors — `ai-eng audit verify` no longer dies on a truncated line, it names the link and exits 1; `cli.main` is unchanged and still emits the event `ai-eng digest` reads before it re-raises
- [x] Health and data age — `ai-eng doctor`: assertion 19 reads this list, assertion 8 now reports a cut chain instead of walking one and calling it intact, and `ai-eng audit verify` is the age of the chain
- [x] External check — `.github/workflows/install-matrix.yml`, which this spec taught to pre-create a skills root, run `ai-eng doctor --fix` against a settings file it deleted, and assert after `uninstall` that the copies and the guard entry are gone. What it cannot check is a real symlink failure, which is R-008-01's remainder
- [x] Second path — the guard count is now derived from the dispatcher table and compared against the sentence in each doctrine file, which is `tests/test_contracts.py::test_the_counts_this_repository_states_about_itself_are_the_counts_it_has`; before this spec three sentences stated it and nothing recomputed it
- [x] Security — `just security`: gitleaks, semgrep and trivy on every push, plus the new recall measurement in `tests/test_contracts.py::test_the_catalogue_reads_obfuscated_text_the_way_a_model_reads_it`, which fails the build if the catalogue stops catching nine of twelve obfuscated variants
