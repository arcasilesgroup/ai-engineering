# Challenge — specs/027-standard-skills-contract/spec.md

Challenger executed every checkable sentence in the specification against the tree.
Read only `spec.md` and the tree. Worst first.

---

## 1. WRONG (undercount) — "`ai-council` states **6** statistics without a source (66.5%, 10.3%, 14 vs 9, 22%, .70, .51) and `ai-challenge` states 1 ('four of twenty')"

Each is unsourced, so the substance holds — but the *six* is an undercount.

Command: `grep -nE '66\.5|10\.3|14|9|22%|0\.70|5\.3|70%|0\.34|0\.511|0\.82|0\.97' .agents/skills/ai-council/SKILL.md`

Printed (verbatim lines):
```
35|… a right answer turns wrong 66.5% of the time, against 10.3% for a plain re-ask.
38|… raise 14 issues a session against 9.
39|And 70% of what they find is seen by one reader only.
51|… One judge falls from 0.70 to 0.34 moving from pairs to a list.
55|False alarms fall from 22% to 5.3%, and no true finding is lost.
68|…a judge's bias for its own text moves from 0.511 to between 0.82 and 0.97…
```

Command: `grep -n "report|arXiv|source|study|paper|003|from https|D-0" .agents/skills/ai-council/SKILL.md .agents/skills/ai-challenge/SKILL.md`

Printed: nothing. No in-file citation anchors any number in either file.

Command: `grep -n "four of twenty\|specs that carry" .agents/skills/ai-challenge/SKILL.md`
Printed: `30|…Measured on this repository: four of twenty specs carry that section…`

Verdict: The claim "no source in-file" is **true**. But ai-council carries **at least eleven** unsourced numbers (66.5%, 10.3%, 14 vs 9, 70%, 0.70, 0.34, 22%, 5.3%, 0.511, 0.82, 0.97), not the claimed six. The six named are present; the enumeration is incomplete. ai-challenge's "four of twenty" is present and attributed only to "Measured on this repository" — a self-reference with no checkable file, so it is unsourced in the sense claimed. **Count WRONG (undercount); the unsourced substance holds.**

---

## WRONG (composition) — "9 skills have a weak or absent forced-output exit … ai-build, ai-plan, ai-explore, ai-design, ai-review, ai-research, ai-debug, ai-challenge, ai-spec are the weak nine"

Of the nine named, **ai-challenge has a committed-artifact exit**, so it does not belong in the weak set.

Command: `grep -n "Done when\|committed\|specs/NNN-slug/challenge" .agents/skills/ai-challenge/SKILL.md`
Printed:
```
21|`specs/NNN-slug/challenge.md`, a list of findings…
54|## Done when
56|…the untested ones are named, and the file is committed in the same branch as the specification it attacks.
```

Command (audit of all 16 "Done when"/"What it produces"):
`grep -n "^##\|Done when\|committed\|council.md\|draft.json\|output is shown\|output is in the conversation" .agents/skills/*/SKILL.md`

Result — the forced-artifact exits in the tree are: ai-council (council.md/council.html, counts agreed by `just council`), ai-ship ("output is in the conversation"), ai-verify ("every box carries a command and its output"), ai-report (`.ai/issue/draft.json`), ai-note (`docs/notes/<slug>.md`, committed), ai-cycle (green-gate output or "a page saying why not"), and **ai-challenge (`challenge.md` committed)**. The rest (ai-build, ai-plan, ai-explore, ai-design, ai-debug, ai-research, ai-review, ai-spec) lack a named printed/committed artifact: ai-plan is the exact weak pattern ("The person has approved it. That approval is the gate", line 51).

Verdict: the count "9" restates the spec's own enumeration, but the membership is grounded in error — ai-challenge demonstrably forces a committed artifact. ai-review and ai-debug are also boundary (ai-review: findings in the conversation only; ai-debug: "a check exists that fails without the fix and passes with it" is the closest thing to an artifact). **The "weak nine" predicate is WRONG as applied to ai-challenge**; the rest of the list is accurate.

---

## UNPROVEN — "contract.py already enforces fog ceiling, description distinctness and the fork/background rule" (claim: Contract D-027-01 input)

Two of the three are enforced by `contract.py` itself; the fog ceiling is defined there but enforced **outside** it — by a test, not by `contract.audit`.

Command: `grep -n "SKILL_FOG_CEILING\|def fog(\|fog(" src/ai_engineering/contract.py`
Printed:
```
251|def fog(body: str) -> float:
273|SKILL_FOG_CEILING = 11.03
```
No call site inside the module.

Command: `grep -rn "SKILL_FOG_CEILING\|fog(" src tests`
Printed (only): definition/constant in `contract.py`; enforcement in `tests/test_contracts.py:2094-2107` ("scored … for skill in … if score > contract.SKILL_FOG_CEILING").

Command: `grep -n "Not for\|context.*fork\|background" src/ai_engineering/contract.py`
Printed: `116` (`"Not for" not in description` → error), `121-126` (`context: fork` without `background: false` → error). These two are applied inside `audit_one`.

Verdict: "description (with 'Not for' negative) and fork/background" are enforced inside `contract.py.audit`. "Fog ceiling" is instrumented (constant + scorer) in `contract.py` but is not applied by `contract.py`'s own audit — the ratchet lives in the test suite. So "contract.py enforces the fog ceiling" is UNPROVEN as stated: the ceiling is defined there, applied elsewhere.

---

## OK (with a caveat) — "6 skills pin `just check`/`just council`/`just security`"

Command: `grep -rn "just (check|council|security)" .agents/skills/*/SKILL.md`
Printed: five files — ai-review (line 8, "that is just check in CI"), ai-ship (line 23 "Run `just check`"), ai-verify (line 27 "Run `just check` and `just security`"), ai-council (lines 91/98 "`just council`"), ai-security (lines 38/45 "`just security`").

Command: `grep -rn "just\b" .agents/skills/*/SKILL.md` adds a sixth: ai-cycle (line 52 "`just` stops at the first failing recipe").

Verdict: six skills do reference a `just` command requiring a Justfile, but only five name the specific recipes check/council/security; ai-cycle's is a generic `just` dependency and ai-review's is a "not-for" mention, not a requirement. The "six" count is therefore only defensible counting ai-cycle. **OK-if-broad / the specific-recipe count is five.**

## OK — claim 12: ai-ship/ai-verify/ai-council/ai-security contain `just check`/`just security`/`just council`

Commands (above) confirm the strings literally in all four: ai-ship `just check`, ai-verify `just check` + `just security`, ai-council `just council`, ai-security `just security` (grep lines cited). The further inference — that these assume a Justfile with that recipe — is an assertion about the stranger's repo and is not testable against this tree. **OK for the string presence; the "assumes a Justfile" half is outside the tree.**

## OK — all 16 skills already have `SKILL.md` + `corpus.md`

Command: `for d in .agents/skills/*/; do … done`
Printed: every one of the 16 (`ai-build, ai-challenge, ai-council, ai-cycle, ai-debug, ai-design, ai-explore, ai-note, ai-plan, ai-report, ai-research, ai-review, ai-security, ai-ship, ai-spec, ai-verify`) `SKILL=Y corpus=Y`. **OK.**

## OK — 8 skills pin `ai-eng` verbs

Command: `grep -rln "ai-eng" .agents/skills/*/SKILL.md` → exactly eight files: ai-build, ai-council, ai-cycle, ai-plan, ai-report, ai-security, ai-spec, ai-verify. **OK.**

## OK — ai-security also pins `semgrep`, `gitleaks`, `trivy`

Command: `grep -n "semgrep\|gitleaks\|trivy" .agents/skills/ai-security/SKILL.md`
Printed line 39: "…gitleaks at its exact version, semgrep against `policy/semgrep.yml`, and trivy." **OK.**

## OK — ai-note pins `git grep`

Command: `grep -n "git grep" .agents/skills/ai-note/SKILL.md`
Printed line 41: "Searching: `git grep` over `docs/notes/`…". **OK.**

## OK — six skills reference another file without an existence check; only ai-spec checks

Commands (grep across the six): ai-build line 37 references `hooks/no_verify_guard.py` with no fail-closed sentence; ai-cycle line 25 references `policy/skill-sequence.toml` with none; ai-security lines 25/39 reference `policy/threat-model.toml` and `policy/semgrep.yml` with none; ai-verify line 44 references `ai-review/references/testing.md` with none; ai-review line 32 references `references/` with none; ai-plan (line 19) references the spec file with none. In every case the reference is stated as fact with no "if absent → refuse" beside it. ai-spec alone has a fail-closed existence handling: "If `CONSTITUTION.md` is absent or empty, …Never overwrite one" (grep "CONSTITUTION" → line 25 + line with "absent"). **OK** — the six are un-checked, `ai-spec` checks.

## OK — all six referenced paths exist

Commands and result: `hooks/no_verify_guard.py` EXISTS, `policy/skill-sequence.toml` EXISTS, `policy/threat-model.toml` EXISTS, `policy/semgrep.yml` EXISTS, `CONSTITUTION.md` EXISTS, and `ai-review/references/` (with `testing.md`) EXISTS at the skill-relative location `.agents/skills/ai-review/references/testing.md` (checked `ls -la` / glob list showing testing.md). Note: under the spec's literal spelling `ai-review/references/` at repo root the path is MISSING; the real location is inside the packaged tree `.agents/skills/ai-review/references/`. **OK** (paths exist where the skills would resolve them).
rest

## OK — `.agents/skills/` is force-packed into `ai_engineering/skills`

Command: `grep -n "force-include\|skills" pyproject.toml`
Printed: line 51 `".agents/skills" = "ai_engineering/skills"`. **OK.**

## OK — `just`-strings in ai-ship/ai-verify/ai-council/ai-security

Commands above. **OK** for the presence of `just check`/`just security`/`just council` in all four skill bodies.

---

## What could not be tested

- **"The 16 skills will be repaired in one pass"** (Options 1 cost) — a decision about future edits, no current fact to check.
- **"the only portable command the wheel guarantees (`ai-eng`) is not the only command the skills name"** — future-tense intent, not a claim about the present tree.
- **Whether each `just `recipe actually exists in a Justfile the skills can reach** — the skills assume it; the tree ships no per-skill Justfile guarantee, so "the stranger's repo has no Justfile" is asserted, not verifiable here.
- **Fog ratchet enforcement** — the claim "(contract.py) already enforces fake ceiling" is partially wrong; the enforcement is in the test suite, so whether it blocks `ai-eng doctor` output (vs. pytest) I did not run a full gate; I verified the definition site only.
- **"all six referenced paths"** — `ai-review/references/` resolves only skill-relative, not repo-root; confirmed present at the packaged location.

Verge: no sentence was deleted or edited; none of this is an approval or rejection.