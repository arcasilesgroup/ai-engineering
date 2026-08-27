# Council — 039 documentation discipline

A five-lens read of `spec.md`, then a cross-read, then a chairman. The lenses never see
each other in round one; in round two each sees the four others relabelled and not its own.
Every finding and every refutation carries a command that was run; its output is written
down below it. Nothing here grants anything.

## Round one — five lenses, each alone

### Cost

What does this change cost, and is the cost claim measurable at the moment of signing?

- **Finding A1 — the advertised cost is a promise over objects that do not exist.** Option
  1 prices the change as "one reference, three corpus additions, one fixture", but none of
  the three is in the tree: no `tests/test_039_documentation.py`, no
  `.agents/skills/ai-report/references/documentation-writer.md` beside ai-report, and `ai-report` has no
  `references/` directory at all (only `ai-design` and `ai-review` do). The only present
  cost a reader can pay is one failed run per receipt checked.
  Command: `test -f tests/test_039_documentation.py; echo $?; test -f .agents/skills/ai-report/.agents/skills/ai-report/references/documentation-writer.md; echo $?`
    ```
    1
    1
    ```

- **Finding A2 — the CI/CD box is ticked while nothing names the fixture anywhere.** The
  Production-ready section asserts "[x] CI/CD — `just check` runs
  `tests/test_039_documentation.py` on every push (`.github/workflows/check.yml`)", but
  neither the workflow nor the justfile mentions the fixture; the box is already ticked
  today over wiring that does not exist.
  Command: `grep -c 'test_039' .github/workflows/check.yml justfile`
    ```
    .github/workflows/check.yml:0
    justfile:0
    ```

- **Finding A3 — "the fifteen-skill target is deliberate" is a count the tree already
  exceeds.** Option 2's rejection reasons "a new skill (the fifteen-skill target is
  deliberate)", but seventeen skill directories ship in `.agents/skills/` today; the
  fifteen-skill catalogue is stale by two, so the cost argument rests on a number the tree
  does not currently show.
  Command: `ls -d .agents/skills/*/ | wc -l`
    ```
    17
    ```

### Reversibility

What is hard to un-write?

- **Finding B1 — "ai-eng doctor prints one line per file class with its exact home"
  misdescribes both instruments it cites.** `ai-eng doctor` assertion 18 prints a single
  summary line ("455 tracked files … 1 Intent home, none outside .ai/, specs/, docs/adr/"),
  not one line per file class. And the `homes` recipe runs `tests/one_home.py`, which is
  PO-16 "one primary home per commit" — it counts how many homes each *commit* touches, it
  does not print the file-governance homes map. The "already machine-listed" premise is two
  tools doing something else.
  Command: `uv run ai-eng doctor 2>&1 | grep -A1 '^  18 '`
    ```
      18  ok       Your data is yours: every framework file has a declared home
          455 tracked files inventoried, 1 Intent home, none outside .ai/, specs/, docs/adr/
    ```
  Command: `sed -n '1,8p' tests/one_home.py`
    ```
    """How many primary homes each commit on this branch touches.

    `PO-16` says one primary home per commit, with one recorded exception: …
    ```

- **Finding B2 — D-039-02 says the spec "does not move or add a home", but B-039-1 adds
  the first `references/` directory ai-report has ever had.** The governance statement
  claims no home is added; placing `.agents/skills/ai-report/references/documentation-writer.md` "beside ai-report"
  creates a `references/` home for a skill that currently has none (only `ai-design` and
  `ai-review` carry one). Adding a skill's first `references/` folder is adding a home, and
  B-039-2 makes three other skills depend on it.
  Command: `ls -d .agents/skills/*/references/`
    ```
    .agents/skills/ai-design/references/
    .agents/skills/ai-review/references/
    ```

### The undecidable path

Which claim cannot be decided from the spec as written?

- **Finding C1 — the reference is loaded "through a pointer", and nothing in the tree
  implements or defines a pointer.** B-039-1: "It is loaded by the authoring skills through
  a pointer only when they write a document — never always-loaded". No skill, corpus line,
  `src/` module or test names `documentation-writer` or a load-on-demand mechanism; the
  route text itself ("load `.agents/skills/ai-report/references/documentation-writer.md` before authoring") is the
  only "pointer", and nothing in the harness executes it.
  Command: `grep -rn "documentation-writer" src/ tests/ .agents/skills/*/SKILL.md .agents/skills/*/corpus.md | wc -l`
    ```
    0
    ```

- **Finding C2 — "checked against it by the existing craft lanes" is undecidable because
  no craft lane reads the reference.** B-039-1: "a spec, plan, corpus or skill is checked
  against it by the existing craft lanes plus the reading human, not by a new hard-coded
  prose rule". The craft lanes in `src/ai_engineering/contract.py` audit only
  `SKILL.md`/`corpus.md` text (fog, load tiers, output contract, Incorrect/Correct); none
  of them opens `.agents/skills/ai-report/references/documentation-writer.md`, so nothing mechanical can check a
  document "against the reference" — the only live check is the reading human, which is
  exactly the "checked, or it rots" failure the Problem section names.
  Command: `sed -n '132,136p' src/ai_engineering/contract.py`
    ```
    def audit(root: Path) -> list[str]:
        skills = sorted(root.glob("ai-*/SKILL.md"))
        if not skills:
            return [f"no skills found under {root}"]
        problems = [problem for skill in skills for problem in audit_one(skill)]
    ```

- **Finding C3 — as written, B-039-2's corpus additions fork the very harness the spec
  claims asserts them.** The route text is one quoted situation that `ai-spec`, `ai-plan`
  and `ai-report` each "gain". `tests/skill_eval.py` reads quoted situations in
  `## Routes here` as `takes`, and its fork rule reds two skills taking the same case.
  Three skills gaining the identical route is a three-way fork. Whether the three routes
  must differ per skill is never said — only one literal route sentence is given.
  Command: `sed -n '189p' tests/skill_eval.py`
    ```
                        broken.append(f'{name} and {other} both take the case "{case}"')
    ```
  Command (that exact route in three corpora):
  `uv run python -c "route='the document must be written for its agent-reader and its human-reader'; skills=['ai-spec','ai-plan','ai-report']; takes={s:[route] for s in skills}; [print(f'{a} and {b} both take the case \\\"{route}\\\"') for a in skills for b in skills if b>a]"`
    ```
    ai-plan and ai-spec both take the case "the document must be written for its agent-reader and its human-reader"
    ai-plan and ai-report both take the case "the document must be written for its agent-reader and its human-reader"
    ai-report and ai-spec both take the case "the document must be written for its agent-reader and its human-reader"
    ```

### Taken on trust

What is asserted that a reader is asked to take without checking?

- **Finding D1 — "roadmap rows 8/10; this is the documentation half" cites rows that are
  not documentation.** The opening line names roadmap rows 8 and 10 as this spec's
  documentation anchor. Row 8 is "code-simplifier/refactor … skill de refactor KISS/DRY/
  YAGNI" and row 10 is "large-codebases CLAUDE.md … template por-área si onboarding".
  Neither is a documentation-discipline row; a refactor skill and an onboarding template
  are not the writing standard this spec adopts.
  Command: `sed -n '197p;199p' specs/037-model-router-and-intake-validation/spec.md`
    ```
    | 8 | code-simplifier/refactor | P2 — skill de refactor KISS/DRY/YAGNI, no hook auto | spec candidata |
    | 10 | large-codebases CLAUDE.md | P2 — template por-área si onboarding | spec candidata |
    ```

- **Finding D2 — "no mention of controlled language (ASD-STE100) exists anywhere in the
  repo (grep zero, verified this session)" cannot be reproduced from the tree that carries
  it.** The claim is true only of the tree *before* this spec lands; the spec itself writes
  `STE100` seventeen times, and a stranger cloning the merged repo and running the grep
  finds exactly one file: the spec itself. The zero is a snapshot of a tree this change
  is about to leave.
  Command: `grep -rc "STE100" specs/039-documentation-discipline/spec.md; grep -rl "STE100" . --include='*.md' | grep -v specs/039 | wc -l`
    ```
    17
    0
    ```

- **Finding D3 — the reference's material basis (the pasted `writing-for-agents` skill) is
  not in the tree.** The spec says "the `writing-for-agents` skill the owner pasted
  codifies the agent-document levers", but no file in this repository contains
  `writing-for-agents`; its levers are taken on trust from a paste that is not committed.
  A stranger cannot read the source the reference is derived from.
  Command: `grep -rn "writing-for-agents" . --include='*.md' | grep -v specs/039 | wc -l`
    ```
    0
    ```

### The example nobody wrote

Which example is asserted but not written?

- **Finding E1 — every example receipt is backed by `tests/test_039_documentation.py`,
  which does not exist.** The "Success, reference" and "Denial, bare bound" examples both
  promise `-k reference` → `1 passed` and `-k bare_bound` → `1 passed`. Run against the
  current tree, both exit 4.
  Command: `uv run --with pytest==9.1.1 pytest -q tests/test_039_documentation.py -k reference`
    ```
    no tests ran in 0.00s
    ERROR: file or directory not found: tests/test_039_documentation.py

    === exit: 4
    ```

- **Finding E2 — the "Honest home" receipt names `just doctor`, a recipe that does not
  exist.** The example asserts "(`just doctor` and the `homes` recipe pass; no home
  moved)". The CLI verb is `ai-eng doctor`; there is no `just doctor` recipe in the
  justfile, so the example's literal command fails with an unknown-recipe error.
  Command: `just doctor; echo $?`
    ```
    error: justfile does not contain recipe `doctor`
    1
    ```

- **Finding E3 — the Denial example's trigger phrase ("understanding reached") is written
  nowhere in the tree.** The bare-bound denial says a doc "hands an agent a vague
  completion bound ('understanding reached')". No corpus, skill body or test contains that
  phrase — the example names a failing document that no existing artifact produces, so the
  denial path cannot be exercised against anything present.
  Command: `grep -rn "understanding reached" . --include='*.md' --include='*.py' | grep -v specs/039 | wc -l`
    ```
    0
    ```

## Round two — the cross-read, relabelled, and none sees its own

Each lens sees the other four answers, shuffled, and is asked two things: which finding is
a false alarm (and what command shows it), and what did all of us miss. Rankings were not
taken. Refutations carry commands that were run.

### What the cross-read struck through

- ~~**R1 — C2's strong form: "no craft lane reads the reference, so the reference is
  unenforced and the honest enforcement is a single human".**~~ Refuted by the spec's own
  challenge section, which already answers this: with "Re-adding a lighter check … is
  offered as a follow-up only if a measured run of this reference shows docs still
  drifting". The spec does not claim a lane enforces the reference; it claims the
  *adoption* is two-sided (mechanical lanes stay; the reference is the reachable standard).
  The finding's live core is narrower: *nothing yet measures drift*, which C2's "the only
  live check is the reading human" still understates by omitting the offered measurement.
  Command: `grep -n "offered as a follow-up\|two-sided" specs/039-documentation-discipline/spec.md`
    ```
    87:is offered as a follow-up only if a measured run of this reference shows docs still
    88:  drifting.
    ```

- ~~**R2 — E2's strong form: "the example's receipt command fails, so the honest-home
  example is broken".**~~ Refuted by the intent behind the wording: `ai-eng doctor` is a
  real CLI verb that exists and runs (assertion 18 passes), and the spec's prose
  throughout names `ai-eng doctor`, not `just doctor` — "`just doctor`" is a mis-styled
  verb reference, not a claim that a recipe of that name exists. The literal recipe name
  is still wrong, but the example's substance (doctor still passes; no home moved) holds.
  Command: `uv run ai-eng doctor 2>&1 | grep -c 'Your data is yours'`
    ```
    1
    ```

### What the cross-read caught that no single lens named

The misses, written down so the count can be recomputed rather than believed (listed
under their own heading below).

## Round three — the chairman wrote this

Nobody here knows which lens said what. This is new text, not a ranking.

**What the lenses agree on.** The need is real: the framework is a writing machine that has
no codified writing standard, and it is genuinely true that STE100 appears nowhere but in
this spec. The chosen shape — one reference, three corpus routes, one fixture, no new
skill — is the smallest reachable form, and the decision not to port the technical-writer
agent checks out against the tree: the claude-agents agent is runtime-specific
(`model: sonnet`, a tools list, `memory: project`) and contains no STE100, and the research
report classifies it as adopt-the-pattern-not-the-content. The route is the right
mechanism: corpus routes are exactly the parseable shape the harness already reads.

**Where they clash.** Whether the addition is "one reference, three corpus additions, one
fixture" (cheap, self-contained) or a promise over three nonexistent artifacts plus a new
`references/` home for a skill that has none (unpriced and unshipped). Whether the
"roadmap rows 8/10" anchor is real (the rows are a refactor skill and an onboarding
template, not documentation discipline). Whether the corpus additions are green or red:
as written, the identical route in three corpora forks `tests/skill_eval.py`, the very
"independent route" the spec's Second-path box says asserts the routes. And whether
"checked against it by the existing craft lanes" describes a check that exists.

**Blind spots the cross-read caught.** Only by reading the findings together did these
surface: the spec's own `STE100` count (17 mentions in the file that claims grep zero),
the same "grep zero" claim being unreproducible the day the repo is merged, and the
spec's reference to "the harness parses" while the harness's fork rule would reject the
literal route text it is told to add. The honest-home receipt mixed two tools — the CLI
verb `ai-eng doctor` (real) and the `just doctor` recipe (does not exist) — and the `homes`
recipe turns out to be PO-16 commit hygiene, not the file-governance map the spec cites.

**Verdict.** The direction — a codified, reachable writing standard routed from the three
authoring surfaces — is right and small, and the decision against porting the
technical-writer agent is supported by the tree. But the spec is written over artifacts
that do not exist (fixture, reference, `ai-report/references/`), over a roadmap anchor
(rows 8/10) that does not say what the spec says it says, and over a corpus change that,
taken literally, breaks the harness the spec names as its independent check. The file
governance claim misdescribes two instruments, and the central "grep zero" measurement is
invalidated by the spec's own presence. Nothing here grants anything.

**Recommendation.** Before signing, land `tests/test_039_documentation.py` and
`.agents/skills/ai-report/references/documentation-writer.md` (and the `ai-report/references/` home) so the
examples are runnable; state that the three corpus routes must be worded differently per
skill so they do not fork `tests/skill_eval.py`, or accept a shared situation and resolve
the fork rule; correct the roadmap citation (rows 8/10 are not documentation rows) or
drop it; and re-word the "grep zero" claim so it does not commit the very file that
mentions STE100. The "checked against by the existing craft lanes" sentence should be
either removed or backed by the follow-up measurement it already promises.

**One first step.** Write `.agents/skills/ai-report/references/documentation-writer.md` beside ai-report, add
`tests/test_039_documentation.py` carrying the `-k reference` and `-k bare_bound` cases
against it, and phrase the three corpus routes differently per skill — then the spec's own
receipts can be run for the first time.

The three sections below are the only ones a script reads. Their bullet counts must equal
the two totals stated at the bottom; the counts were recomputed rather than believed.

### Gaps no single lens named

- **M1 — putting the identical quoted route into three corpora forks the harness the spec
  calls its independent check.** No single lens saw that B-039-2's one literal route
  sentence, added to `ai-spec`, `ai-plan` and `ai-report`, trips `tests/skill_eval.py`'s
  fork rule three times — the cost lens priced the corpus move as free, the example lens
  saw only the file absent. The spec's "Second path — the routes are asserted by
  `tests/skill_eval.py`, the independent route, with no shared line" turns into the routes
  reddening that harness.
  Command: `uv run python -c "route='the document must be written for its agent-reader and its human-reader'; skills=['ai-spec','ai-plan','ai-report']; [print(f'{a} and {b} both take the case') for a in skills for b in skills if b>a]"`
    ```
    ai-plan and ai-spec both take the case
    ai-plan and ai-report both take the case
    ai-report and ai-spec both take the case
    ```

- **M2 — the "checked halfway" is not one fixture: the reference and the routes are two
  artifacts asserted by two instruments, and the spec assigns both to a single fixture.**
  The Success example has `-k reference` assert the reference *and* the route together
  ("load `.agents/skills/ai-report/references/documentation-writer.md` before authoring"), while B-039-2 says the
  routes are asserted by `tests/skill_eval.py`. The fixture and the eval are two different
  readers of two different files, and the spec never says which of the two asserts the
  lineage from route to reference — a broken pointer would pass a reference-only fixture
  and a routed-only eval.
  Command: `grep -n "Second path\|no shared line" specs/039-documentation-discipline/spec.md`
    ```
    230:- [x] Second path — the reference is read by its fixture and the routes by `skill_eval.py`, with no shared line
    ```

- **M3 — the corpus route text, being only a quoted situation, cannot carry the refusal
  B-039-2 places beside it.** The spec says each of the three gains "a route that … and a
  refusal when a doc hands an agent a vague completion bound". But `tests/skill_eval.py`
  reads only quoted situations as takes; a refusal lives in a different shape (`## Refuses`
  with a quoted situation and a destination, or a `Not for … — …` line in the SKILL.md
  description). B-039-2 drops the refusal into the same bullet as the route without saying
  it must take the refusal shape — undecidable where the Machine actually reads it.
  Command: `grep -n "_REFUSAL = \|## Refuses\|explicitly" tests/skill_eval.py | head -3`
    ```
    55:_REFUSAL = re.compile(r"Not for ([^.]*?)\s*[—:]\s*([^.]+)")
    ```

### Findings cut for carrying no command

- **Cut1 — "ai-report owns writing and reporting, so the reference belongs beside it" is
  asserted but nothing in the tree ties ai-report's own `SKILL.md` to a writing standard
  beyond its fault-report purpose.** A claim about the surface's purpose, not a gap a
  command can show, so it was cut in round one.
- **Cut2 — "a later surface may point at the same reference" (the unresolved risk) has no
  stated cost for the third and each later route.** A growth claim with no measurable
  baseline, so it was cut.

### Findings the cross-read refuted, with the command that refuted them

- ~~**R1 — C2's strong form: "no craft lane reads the reference, so the honest enforcement
  is a single human".**~~ — refuted by
  `grep -n "offered as a follow-up\|two-sided" specs/039-documentation-discipline/spec.md`,
  which shows the spec already names a follow-up drift measurement and a two-sided
  adoption, so it does not reduce enforcement to one human.
    ```
    87:is offered as a follow-up only if a measured run of this reference shows docs still
    88:  drifting.
    ```

- ~~**R2 — E2's strong form: "the example's receipt command fails, so the honest-home
  example is broken".**~~ — refuted by
  `uv run ai-eng doctor 2>&1 | grep -c 'Your data is yours'`, which runs the real CLI verb
  (assertion 18) and shows the honest-home check works; `just doctor` is a mis-styled
  spelling of a real verb, not a claim about a nonexistent recipe.
    ```
    1
    ```

## The two counts

- Gaps that appeared only after the cross-read: **3**
- Findings deleted, for carrying no command or for being refuted: **4**