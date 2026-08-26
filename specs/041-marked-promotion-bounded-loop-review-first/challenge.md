# Challenge: specs/041-marked-promotion-bounded-loop-review-first/spec.md

Attacked on 2026-08-26 against the tree at `main`, by the ai-challenge rule: every
checkable sentence got a command and the verdict on what it printed. 1 WRONG, 2 UNPROVEN,
4 OK. Nothing here edits the specification.

The 041 fixtures (`tests/test_spec_marker.py`, `tests/test_skill_bounds.py`) do not exist
yet — the spec is a draft and its receipts are runnable only after its own build — so the
challenge focuses on what the tree already decides: the stale command in the skill the
spec's trigger leans on, the loopgate absence, the cycle policy and the build cap the bound
mirrors.

## WRONG — "the promotion criterion lives only in prose: the `decide.py` docstring and ai-spec paso 10", and that prose names a command the CLI refuses

Spec, "Context and problem": the criterion "lives only in prose — the `decide.py`
docstring and ai-spec paso 10". The sentence is true about *where* the criterion lives,
but the prose it points at is stale in a way that matters: ai-spec paso 10 instructs
`ai-eng decide --madr "<title>"`, and `--madr` was hard-deleted (CHANGELOG: "`--madr` is
an unrecognised argument because there is no longer a choice to make"; the
`install-matrix.yml` gate asserts `! ai-eng decide --madr x`).

Command: `uv run ai-eng decide --madr x`

```text
usage: ai-eng decide [-h] [--supersede NNNN] [--list] [--accept NNNN]
                     [--spec SPEC]
                     [title]
ai-eng decide: error: unrecognized arguments: --madr
exit=2
```

The skill instructs a command the verb refuses with exit 2 and no state written. The plan
already fixes this (task 4 drops the stale spelling and names `ai-eng decide "<title>"`),
so this finding is recorded as the plan's ground, not as an omission of the plan.

## UNPROVEN — the example receipts for `tests/test_spec_marker.py` cannot run today

Spec, "Examples somebody can check": `uv run --with pytest==9.1.1 pytest -q
tests/test_spec_marker.py` → `3 passed` (and the `-k decide` receipt → `1 passed`).

Command: `test -f tests/test_spec_marker.py; echo $?`

```text
1
```

The fixture does not exist, so neither receipt can produce its promised verdict today.
Same status as specs 039 and 040 at draft time; the tree decides only that the commands
fail at collection, not what the fixture will assert. Red until plan task 1.

## UNPROVEN — "the `[X]` line is the promotion's second reader"

Spec, "Challenged once": the marker "is now visible in the spec's own diff, next to the
decision it is about, reviewed with it". The mechanism is real — the marker sits in the
same file, in the same diff, as the decision — but "reviewed" is a process claim: no
command in this tree decides that a marked decision's diff was read by a second reader.
The claim is a property of the review workflow, which this repository does not gate
mechanically. Kept marked, and the spec's own B-041-1 wording ("the promotion's second
reader") is understood as intent, not as an executed control.

## OK — "no skill in the cycle uses `loopgate`"

Spec, "Context and problem": "no skill in the cycle uses it: the spec↔challenge/council
loop runs without a ceiling on any SKILL.md".

Command: `grep -rl loopgate .agents/skills/`

```text
(no matches)
```

None of the eighteen skills names loopgate; B-041-2's premise — the terminator is code
that no skill-layer loop invokes — is what the tree says.

## OK — the `[parallel] policy` today records no order between the post-build critics

Spec, "Context and problem": the policy "records no order between the post-build critics".

Command: `sed -n '/^\[parallel\]/,$p' policy/skill-sequence.toml`

```text
[parallel]
# What concurrency the cycle allows, recorded as data instead of prose. Stage-level
# parallelism is refused: one writer owns the commits, and the critics run apart for
# independence rather than for speed. The only concurrency is fork contexts, plus the
# task-level parallelism the approved plan allows inside ai-build.
policy = "fork contexts only; task-level parallelism inside ai-build per the approved plan"
```

Fork contexts only, ai-build parallelism, nothing about which critic precedes which.
B-041-3's premise verified.

## OK — the build cap the bound mirrors exists

Spec, "Challenged once": "It mirrors the existing build cap on the same loop (two attempts
per task and failing recipe, ai-goal)".

Command: `grep -n "Two attempts" .agents/skills/ai-goal/SKILL.md`

```text
58:Every red is a chance to build again, not an infinite chase. Two attempts per task and
```

The cap is prose in ai-goal today, and the spec's own option 1 records that the loop bound
is the same kind of instruction — a skill enforcing a rule by following it, not a runtime
check. The mirror is honest.

## OK — "a decision is born inside its spec" is the verb's own doctrine

Spec, "Decision" D-041-01: "a decision is born in its spec and is promoted only when the
spec marks it `[X]`".

Command: `sed -n '1,5p' src/ai_engineering/decide.py`

```text
"""A decision is born inside its spec, and is promoted only when it earns it.

The single question that decides promotion: does this decision constrain specs that do
not exist yet? If the answer is no it stays a block inside its spec, which is where it
has its context and where it is reviewed in the same diff.
```

The marker formalizes the verb's own opening line; the filter enforces what the docstring
declares. The spec and its product agree on the doctrine.

**Count: 1 WRONG, 2 UNPROVEN, 4 OK.**
