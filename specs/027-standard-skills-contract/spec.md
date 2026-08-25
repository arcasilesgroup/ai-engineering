---
id: "027"
slug: standard-skills-contract
status: draft
date: 2026-08-25
ref: ""
supersedes: ""
---

# Standard skills contract

## Who this is for, and what it is worth to them

The maintainer who dogfoods the governed cycle and has been told, from the NotebookLM
research on SKILL.md standardization and skill smells, that the corpus should be
"estándar y bien definido" — each skill knowing exactly what it does. Today the corpus is
close to the standard but not pinned to it: the checking that exists is spread across a
manual audit, and four measured smell classes (concrete commands, un-checked
cross-references, weak exit gates, unsourced statistics) live in the shipped trees
without a gate that refuses them on sight.

The stranger who installs the wheel. Each `SKILL.md` in `.agents/skills/` is force-packed
into `ai_engineering/skills` and lands in the stranger's repo verbatim. A skill that says
`just check` assumes the stranger has a Justfile with that recipe; a skill that references
`policy/threat-model.toml` without checking it exists assumes the stranger's repo has one.
Those assumptions are how a shipped skill silently stops fitting — the exact failure the
standard exists to prevent.

When this is done, the four smell classes are refused by `ai-eng doctor` (or a sibling
check the gate already runs), each of the 16 skills says what it must not do in the two
list slots the contract already reads, and no shipped skill tells a downstream repo to run
a command only this repo has.

## Context and problem

Verified this session (report 012): all 16 skills already have `SKILL.md` + `corpus.md`,
frontmatter YAML, description with trigger and negative. The contract already enforces
description distinctness and the fork/background rule; the fog ceiling is instrumented in
`contract.py` (constant + scorer) but enforced by the test suite rather than by the
audit itself. So the corpus is
partially standardized — the surprise is not how much is missing but how the remaining
gaps map one-to-one onto the smell taxonomy of arXiv:2607.01456 (26 smells, 10 categories,
found in >99% of public skills):

  wheel installs them); 5 pin the `just check`/`just council`/`just security` recipes and
  a sixth (`ai-cycle`) depends on `just` generally — none portable; `ai-security`
  also pins `semgrep`, `gitleaks`, `trivy`; `ai-note` pins `git grep`. The standard's rule
  against "Series of Commands" exists because a concrete toolchain command dies the moment
  the tree it was written for is not the tree it runs in.
  wheel installs them); 6 pin `just check/council/security` (not portable); `ai-security`
  also pins `semgrep`, `gitleaks`, `trivy`; `ai-note` pins `git grep`. The standard's rule
  against "Series of Commands" exists because a concrete toolchain command dies the moment
  the tree it was written for is not the tree it runs in.
- **6 skills reference another file without checking it exists.** `ai-build`, `ai-cycle`,
  `ai-review`, `ai-security`, `ai-verify`, `ai-plan`. All six referenced paths exist in
  this repo — so this is not broken links, it is missing guardrails: the skill does not
  fail closed when its dependency is absent. Only `ai-spec` checks (`CONSTITUTION.md`).
- **8 skills have a weak or absent forced-output exit.** They say the check "passes" or
  "the approval is the gate" without requiring a visible artifact. The standard's
  "Forced-Output Verification Gate" exists because a mere "verify" instruction is skipped.
  (The audited tree already forces an artifact in `ai-council`, `ai-ship`, `ai-verify`,
  `ai-report`, `ai-note`, `ai-cycle` and `ai-challenge`; the weak eight are `ai-build`,
  `ai-plan`, `ai-explore`, `ai-design`, `ai-review`, `ai-research`, `ai-debug`, `ai-spec`.)
- **`ai-council` states at least 11 statistics without a source** (66.5%, 10.3%, 14 vs 9,
  70%, 0.70→0.34, 22%→5.3%, 0.511, 0.82, 0.97) and **`ai-challenge` states 1**
  ("four of twenty"). Each is `UNPROVEN` until anchored or deleted.

The problem in one sentence: the corpus meets the SKILL.md shape but not the smell
standard, no gate refuses a skill that carries one of the four classes, and the only
portable command the wheel guarantees (`ai-eng`) is not the only command the skills name.

## Options considered

1. **Extend the checked contract and repair the 16 skills: new contract rules make the
   four smell classes fail `ai-eng doctor`, and each shipped skill is edited to comply —
   commands narrowed to `ai-eng` verbs or bracketed, cross-references gain an existence
   check, weak gates gain a printed artifact, and the eleven-plus unsourced statistics
   get their source reference or are deleted.** The standardization becomes reproducible: the gate refuses
   a skill that reintroduces a class, and the one-pass edit converges. Costs: editing 16
   files, extending `contract.audit` with a new rule, one test per new rule, and the
   `just check` green ceiling must still hold.

2. **Edit the 16 skills by hand and leave the contract alone.** Cheapest to ship, fixes
   today's seven smells, but nothing refuses a skill that regresses — the one-pass
   edit is exactly what "vibe coding" the standard warns about-run-again. Loses on
   reproducibility, which is the whole point of a contract checked by a script.

3. **Do nothing — the corpus is "close enough".** This is the status quo that let six
   skills ship un-checked references and eight weak gates. Loses both ways.

## Decision

Option 1. The standardization is a *contract*, not a cleanup: `contract.py` already
audits each skill by script — we extend the audit with the smell checks, and edit the 16
skill pairs until the audit is green. The repair surface is `SKILL.md` **and**
`corpus.md`: both files ship verbatim with the wheel, and `corpus.md` today carries the
same concrete verbs (`ai-review/corpus.md` runs `just check`, `ai-note/corpus.md` uses
`git grep`) that the rules eliminate from `SKILL.md`. Concretely:

- **Command rule**: a skill names only portable commands — an `ai-eng` verb, or the
  output of a tool kept as the gate's evidence. A repo-specific motor that the wheel
  does not guarantee (`just <recipe>` as a requirement, bare `semgrep`/`gitleaks`/
  `trivy`, `git grep`) is replaced by the portable verb, or kept only where the output
  it prints is the evidence the gate keeps. `just check` remains the maintainer's local
  orchestrator and is never named by a shipped skill.
- **Existence-check rule**: every cross-file reference a skill body makes to another
  path (policy/, hooks/, ai-*/references/, specs/) must be accompanied by a check that
  the path exists and a fail-closed sentence when it does not. `ai-spec`'s handling of
  CONSTITUTION.md is the pattern to generalise.
- **Forced-output rule**: every skill must end with a "Done when" clause naming the
  killed artifact it produces or the exact command whose output it keeps — a status
  table, a printed digest, a committed file. A mere "verify" is a fail.
- **Sourcing rule**: any statistic in a skill body carries the source (or is deleted).
  `ai-council`'s eleven numbers and `ai-challenge`'s one are anchored to their evidence
  (each resolves in `.ai/reports/003-council-peer-review-evidence.html`) or struck.

Because this decides how every future skill in the wheel is authored and checked, record
it as a decision with its own ADR once approved: propose
`ai-eng decide --madr "the standard skills contract: systemizar el corpus SKILL.md contra la taxonomía de smells"`,
a proposal, not this spec's own approval.

## Challenged once

**The stranger install looks worse under Option 1, not better.** The rules demand a
forced artifact of most of the sixteen, but the whole point of a shipped skill is that a
downstream surface yields to the stranger's repo. If a skill ends with "print a digest"
in a marketplace that produces nothing, the gate is not failed-closed on the machine it
is a verb on; it is a ceiling that an instruction-only corpus (category T3) was never
required to meet — the four classes we repair are instruction-layer, guard layer is
wire. So narrowing commands might bid exactly the command the stranger needed.

This is real and it does not defeat the decision. The standard (NotebookLM research and
2607.01456) applies to the skill as shipped, and the portability rule is precisely what
says "the same skill must resolve across repos" — a forced artifact that only this repo's
surface emits is a case of the very smell the rule removes. The unknown — which surfaces
yield an artifact in practice — is recorded under risks, not silently accepted.

The second strongest failure: a `just`-reference repaired by fancy bracketing becomes
"do nothing inside the gate," which the stranger install, with no `just`, reads as a
way of saying is truly optional. So the repair is not "when `just` exists, run it" —
that is a silent pass. It is "use the portable verb `ai-eng`; if a tool is genuinely
absent, the skill itself says fail-closed and refuses to pass." That keeps the
guarantee without a repo-specific gate.

## Assumptions and unresolved risks

Assumed without proof: the 16 skills will be edited in one plan pass once approved; the
contract's new rules are encoded in `contract.audit_one` and fail `ai-eng doctor` when
broken; and every required output artifact is a printed command output, which any of the
supported surfaces can print.

Open: whether the eleven-plus `ai-council`/`ai-challenge` statistics anchor to report 003
or get struck; which exact command string is allowed as portable (an `ai-eng` verb) in the
skill namespace; whether one of the 16 is better served by a slot abstract in
`undoing` than by a concrete verb; and whether the contract audit extends to `corpus.md`
the same four rules it applies to `SKILL.md` — the council's finding is that `corpus.md`
ships the same smells while no rule reads it, so the repair names both files. None of
these stops the decision; all are review-visible.

Two further risks surface the gate's own dependence on the portability it forbids.
First, `just check` orchestrates the green ceiling in this repo (`Justfile` line
`check: … council map ran`), so a stranger who installs the wheel and wants the gate
must run a `just` recipe while the shipped skills are forbidden from naming `just`.
That is resolved by the split: `just` is the maintainer's local orchestrator, the
wheel never installs a Justfile, and the skills' portable verb is `ai-eng` — the
stranger's surface loads the skills, not a `just` recipe. Second, a forced-artifact
rule presumes the downstream surface can print; a marketplace that produces nothing
would turn "print a digest" into theatre. The rule therefore demands the artifact be
the skill's own committed file or a printed command output the surface can keep, and
the residual unknown — which surfaces cannot print — is recorded here rather than
silently accepted.

## Examples somebody can check

Given the shipped skill `ai-ship`, When it is run on a repo with no Justfile, Then it runs
`ai-eng audit verify` and prints its output, and fails closed with the printed digest —
not by returning a green that its command is unused. Checked by the skill's own exit
clause naming the output it keeps.

Given the gate, When any `SKILL.md` references `policy/threat-model.toml`
or `ai-review/references/testing.md` without an existence check and a fail-closed
sentence at the reference's use, Then `ai-eng doctor` fails that skill's audit line.
Checked by re-running the doctor after the edit and against the edited skill.

Given a skill that names `semgrep` or `git grep` a bare command, When the contract audit
runs, Then the skill is reported as a violation of the portable-command rule. Checked by `contract.audit`'s new
output naming the file and the smell class.

## Decisions

forced-output clause, sourced-statistic), applied to both `SKILL.md` and `corpus.md`,
and the sixteen shipped skill pairs are repaired until the gate is green.
forced-output clause, sourced-statistic), and the sixteen shipped skills are repaired
until the gate is green.

**Rationale:** the corpus already meets the SKILL.md shape; what is missing is the four
smell classes, and a contract that refuses them is the only way the standardization
does not unravel on the next edit.

**D-027-02 — a shipped skill names only portable commands.**
The portable command is an `ai-eng` verb, or the output of a tool kept only as the
gate's evidence. A repo-specific tool (a `just` recipe this repo added, bare `semgrep`,
`gitleaks`, `trivy`, `git grep`) is replaced by the portable verb, or left only where
the output it prints is the evidence the gate keeps.

**Rationale:** every skill ships to a repo whose surface lists the wheel guarantees; a
concrete command that assumes a Justfile or motor of this repo is a skill that silently
breaks on the stranger machine — the smell the taxonomy names "Series of Commands".

## Accepted risks

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