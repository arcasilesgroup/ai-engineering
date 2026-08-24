# Challenge: `specs/023-council-that-reads-itself/spec.md`

Executed against the tree at `461435fb`. Every command below was run in `the repository root`.

---

## 1. WRONG — the denial path the spec says it is "most likely to have got wrong" does not exist today, and cannot be reached by *relaxing* anything

**Sentence (line 219-221):** "**when** it writes `approved`, a `PASS`, a gate result or an accepted risk, **then** the suite fails."

**Command** — the live regex from `tests/test_contracts.py:2158-2164`, run against those four strings:

```
'approved'                                     -> refused=[]
'PASS'                                         -> refused=[]
'This run is a PASS for the gate.'             -> refused=[]
'Risk accepted: R-023-01'                      -> refused=[]
'Recommendation: sign it after the two counts' -> refused=['recommendation']
'Verdict: the spec is answerable'              -> refused=['verdict']
```

`COUNCIL_VERDICT` only fires on `^[ \t>*-]*<word>\b[ \t]*[:=]`. A bare `approved`, a bare `PASS`, "a gate result" and "an accepted risk" are **not detected now**. So D-023-03's "relaxed to forbid granted authority" is not a relaxation — it is a rewrite that must *add* detection for three of the four things the example promises will fail, and the spec never says so. The example as written is unrunnable in either direction: today `Recommendation:` fails (it should pass) and `approved` passes (it should fail).

## 2. WRONG — the chairman writes a "verdict", and `verdict` is on the same blocklist as `recommendation`

**Sentence (line 132-133):** "The test that today forbids the *word* recommendation is relaxed to forbid *granted authority*."

**Command:** `sed -n '2158,2164p' tests/test_contracts.py`

```python
COUNCIL_VERDICT = re.compile(
    r"^[ \t>*-]*(approved|approval|verdict|decision|vote|votes|voted|score|scores|"
    r"consensus|ranking|ranked|recommendation)\b[ \t]*[:=]",
    re.M | re.I,
)
COUNCIL_TALLY = re.compile(r"^[ \t>*-]*\d+\s*(of|/)\s*\d+\s+(members|lenses|agree)", re.M | re.I)
```

The test forbids **eleven** words, not one. D-023-03 says the chairman "writes a verdict and a recommendation" and line 128 says it "writes a verdict, the disagreements, the blind spots, a recommendation and one first step". Run against a plausible chairman page:

```
['- 2 of 5 lenses', 'verdict']
```

`**Verdict:**` is refused, and so is any line of the form "2 of 5 lenses agree" — which is exactly how "the disagreements" get written. The spec names only `recommendation` as the word in the way. Two more (`verdict`, and the tally form) are also in the way and are unmentioned.

## 3. WRONG — `/ai-council` is not permitted to write `.ai/reports/`

**Sentence (line 135-136):** "**Two files.** `specs/NNN-slug/council.md`, the transcript, and `.ai/reports/NNN-name.html`, the page a person reads."

**Command:** parse `policy/capabilities.toml`:

```
ai-council     default      write_roots=['specs']
ai-report      digest       write_roots=['.ai/reports']
ai-cycle       default      write_roots=['specs', '.ai']
```

`ai-council` may write `specs` and nothing else, and `tests/test_capabilities.py:287-295` asserts every non-empty dimension carries its `preflight.*` enforcement plus non-empty `allow`/`deny` proofs (`policy/capabilities.toml:123` — `ai-council.default.allow`, `ai-council.default.deny`). The second file therefore requires a capability-manifest change plus new proof artifacts. The spec mentions neither `policy/capabilities.toml` nor the proofs anywhere:

```
$ grep -c "capabilit" specs/023-council-that-reads-itself/spec.md
0
```

## 4. WRONG — a labelled corpus case refuses precisely what D-023-03 decides to build

**Sentence (D-023-03, line 250):** "The chairman writes a verdict and a recommendation."

**Command:** `cat .agents/skills/ai-council/corpus.md`

```
- "have the members vote and tell me the verdict" — refused: there is no field to disagree
  in, and a council that agrees is one agent speaking twice.
```

That case is scored by `just skilleval` (it is part of the 326). After this change the council *does* tell you the verdict, so this refusal becomes a false label. The spec never mentions `corpus.md`, and the SKILL.md description itself carries the same claim (`It has no vote, no verdict and no field in which the word approved could be written`) — that sentence is inside the `description:` block that `skill_eval` reads as the routing claim.

## 5. WRONG — "nine checks … are listed in Examples somebody can check with the command that shows each one"

**Sentence (line 57-59).**

**Command:**

```
$ awk '/^## Examples somebody can check/,/^## Decisions/' spec.md | grep -c '^\*\*Given\*\*'
6
```

Six examples, not nine, and only three carry an executable command (`python -c …skill_eval…`, `just skilleval`, `wc -l …`). The other three assert future test behaviour. Nine checks red on the pasted file is **UNPROVEN** besides — the pasted file is not in the tree, so nothing here can be run against it.

## 6. WRONG (minor) — `docs/adr/0019` was accepted on 2026-08-21, not 2026-08-20, and does not "close with" the quoted sentence

**Sentence (line 35-37):** "Decision record `docs/adr/0019` accepted that design on 2026-08-20 … and it closes with a sentence…"

**Command:** `head -14 docs/adr/0019-*.md` and `git log -1 --format=%h\ %cd 8eeb13d1`

```
status: "accepted"
date: "2026-08-21"
approval_ref: "no-hitl-2026-08-20"
approved_at: "2026-08-21T00:00:00Z"
8eeb13d1 2026-08-21 feat(skills): let somebody other than the author read a specification
```

Status `accepted` ✓. The date is 2026-08-21; 2026-08-20 is the *authority reference*, not the acceptance. And the quoted sentence — "there is still no benchmark that defines the improvement a council shows" — is verbatim correct but sits in **Decision outcome**, not at the close; the record closes with the `EP-171` grading paragraph.

## 7. UNPROVEN — D-023-05's "two counts" have no instrument anywhere in the tree

**Sentence (line 138-142):** "Every run prints two counts … Those are a measurable gap rather than a manufactured consensus."

**Commands:**

```
$ ls specs/*/council.md
zsh: no matches found
$ grep -rn "council" tests/*.py | grep -v test_contracts.py
(nothing)
```

`tests/test_contracts.py:2206` globs `specs/*/council.md` and there is no such file, so the only council check in the repository has never run against real output. Nothing counts, stores or asserts the two numbers; the spec describes them as printed by a prompt. Under rule 12 ("a decision that always comes out the same is code, not a prompt") that is the same shape `EP-195` complained about. Note also the deleted-count half already exists in the skill today (`.agents/skills/ai-council/SKILL.md`: "Delete every finding that carries no command. Say how many were deleted."), so only one of the two counts is new.

## 8. UNPROVEN / incomplete — deleting `contract.CEILING` touches a third file the spec's arithmetic never names

**Sentence (D-023-06, line 272).**

**Command:** `grep -rn "CEILING" --include="*.py" src tests hooks policy`

```
src/ai_engineering/contract.py:32:CEILING = 80
src/ai_engineering/contract.py:68,70            (audit_one)
tests/test_record.py:853-857                    (test_a_skill_over_the_line_cap_…)
tests/mutation.py:92-93                         ("the skill cap" row, FLOOR = 90)
tests/stats.py:154,226                          ("skill_ceiling", printed as "longest N / M")
```

Five sites in four files. `tests/stats.py` is the one nobody lists. Deleting the `tests/mutation.py` row also removes one row from the guards lane (`RAN guards=<len(rows)>`, `FLOOR = 90` at `tests/mutation.py:278`) — the score denominator moves, which is a number the spec is silent on.

## 9. UNPROVEN — `.ai/reports/NNN-name.html` collides with the existing report numbering

**Sentence (line 135).**

**Command:** `ls .ai/reports/`

```
001-evolution-proposal.html
002-process-optimization-research.html
003-council-peer-review-evidence.html   ← this spec's own evidence report
```

`.agents/skills/ai-research/SKILL.md:22` fixes the form as "`.ai/reports/NNN-a-name.html`, three digits". The numbering is sequential per report, not per spec. If a council run for spec 023 writes `023-…` it breaks the sequence; if it writes the next free number it is not `NNN` in the spec's sense. The spec does not say which, and nothing in the tree decides it.

## 10. UNPROVEN — every bracketed citation, and the artifact claims about `karpathy/llm-council`

Lines 43-49, 61-68, 104-126, 152-157, 174-193 rest on `.ai/reports/003` refs [1] [3] [4] [5] [6] [7] [8] [9] [12] [16] [19] [20]. `.ai/reports/003-council-peer-review-evidence.html` exists (30.4K). I was instructed not to read `.ai/reports/`, so every number in the Context, Options and Decision sections — 56%, 14 v 9, 22% v 5.3%, 66.5% v 10.3%, 70.7% v 71.7%, +5.1pp, +9.2pp, 0.70→0.34, 0.511 v 0.82-0.97, 162 roles / 2,410 questions — is **unverified by me**. The claims about the upstream repository (five commits, all 2025-11-22, no tests, labels never shuffled, chairman re-attaches names) need the network and were not tested.

---

## What agreed with the tree

Each of these was executed, not re-read.

| Sentence | Command | Output |
|---|---|---|
| `wc -l .agents/skills/ai-council/SKILL.md` prints `58` | that command | `58` |
| `contract.CEILING` is `80` | `grep -n CEILING src/ai_engineering/contract.py` | `CEILING = 80` |
| "sixteen skills" | `ls -d .agents/skills/*/ \| wc -l` | `16` |
| "the largest raw file is 80 lines" and the cap is binding on exactly one file | per-file `wc -l`, sorted | `80 ai-spec`, then `74 ai-design`; ai-spec is the only file at the cap (the cap is inclusive — `if len(lines) > CEILING`, so nothing is *over*) |
| "the largest prose count is 52" | non-blank lines below the frontmatter | `52 (ai-spec)` — matches under that definition; the no-headings count is 46 and the with-frontmatter count is 66, so the definition is load-bearing and unstated |
| `description()` parses only the folded form | the spec's own `python -c …` line, verbatim | `''` — and `tests/skill_eval.py:64` is `if "description: >-" not in body: return ""` |
| `_TRIGGER` matches only double-quoted phrases | `sed -n '47p' tests/skill_eval.py` | `_TRIGGER = re.compile(r'"([^"]+)"')` |
| `just skilleval` prints `RAN skilleval=326` and `baseline 326, delta +0, margin 0` | `just skilleval` | exactly those two lines; `policy/pilot-register.toml:327-331` holds `measured = 326`, `margin = 0` |
| `tests/test_contracts.py` requires the exact string `No vote and no ranking` and fails with that message | `sed -n '2216,2220p'` | `assert "No vote and no ranking" in skill and "approved" in skill` — the spec quotes the first required string and the message, but **omits the second required substring `"approved"`**, and the message continues `", which is the instruction this test enforces the output of"` |
| `CONSTITUTION.md` forbids granting authority, not recommending | `sed -n '53p' CONSTITUTION.md` | "Models may investigate, propose and review; they never grant authority or accept risk." — exact, and it says nothing about recommending |
| `EP-195`'s words | `sed -n '212,213p' specs/013-origin-first-coordination/spec.md` | "A second model must find a measurable gap, not manufacture consensus, and no benchmark defines the improvement it would show." The spec quotes the first clause accurately |
| `ai-eng decide --supersede` exists | `uv run ai-eng decide --help` | `[--supersede NNNN]` |
| `SKILL_FOG_CEILING` is a live instrument | `contract.SKILL_FOG_CEILING`, scored | ceiling `11.03`; `ai-design 10.99`, `ai-spec 10.85`, `ai-council 8.48`. It exists — but it is a *rate*, so it bounds no file's length; the spec's "readability already has a direct instrument" is true and does not substitute for the cap |
| The two council tests are green today | `pytest tests/test_contracts.py -k "council or critic" -q` | `2 passed, 167 deselected` |
| `just skilleval` is inside the gate | `grep -n '^check:' justfile` | `check: build sbom lint typecheck test cover security register skilleval counts intent-page lenses ran` |

Files mentioning `ai-council` (12, excluding `__pycache__` and `.ai/reports`): `.agents/skills/ai-council/{SKILL.md,corpus.md}`, `.agents/skills/ai-challenge/corpus.md`, `.agents/skills/ai-cycle/{SKILL.md,corpus.md}`, `AGENTS.md:59`, `docs/adr/0019`, `docs/solution-intent.html`, `policy/capabilities.toml:109`, `policy/capability-manifest.schema.json`, `policy/pilot-register.toml:343,351`, `src/ai_engineering/solution_intent.py:459,625`, `tests/test_capabilities.py:264`, `tests/test_contracts.py:2216,2223`. **No rename is proposed by this spec**, so none of them break on a rename; the ones that break on the *content* change are items 3, 4 and 2 above, plus `policy/pilot-register.toml` (the 326 baseline, which the spec does acknowledge).

---

## What I could not test

- **Everything behind `.ai/reports/003`.** Instructed not to read it. That is roughly every quantitative sentence in Context, Options, Decision, Challenged once and the Rationales — twelve bracketed refs. The file exists; whether it says what the spec says it says is untested by me.
- **The upstream artifact.** `karpathy/llm-council`'s commit count, dates, absence of tests, label shuffling, ranking prompt and chairman prompt — needs the network.
- **Every behavioural claim about the new design.** Three rounds, shuffling per run, the chairman never learning who said what, "it says so and prints `0` for both counts" — no code, no `council.md`, no fixture exists. There is nothing in the tree that can decide them; they are prompt text that has not been written yet.
- **`just check` end to end.** I ran `skilleval` and the two council tests only; I did not run the full gate, so I cannot say what else this change would red.
- **Whether the `.ai/reports` page gets read**, which is the spec's own problem two. Nothing in the repository measures it, as the spec itself says at line 55 — so its "readable by the person it is for" claim has no comparator either before or after.
