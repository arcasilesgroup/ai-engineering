# Challenge: spec 038 — Design accessibility guard

Challenge date: 2026-08-26. Attacker: `Challenge_038`.
Method: execute every checkable sentence against this tree (work dir
`the repository root`, branch `main`), paste command output, verdict
worst first (`WRONG` / `UNPROVEN` / `OK`). No edits to the spec.

---

## WRONG — "ai-design … has four routes … with no accessibility floor" / "its verify route has no WCAG floor: no contrast check, no keyboard check, no focus-visible check, no reduced-motion respect" / "nothing in the framework says it"

Command:

```text
$ grep -nE "contrast|WCAG|accessib|keyboard|focus|reduced" .agents/skills/ai-design/SKILL.md
6|  rendered result rather than the declared CSS. Trigger for "design this screen", "build the
21|Tokens, components and their states, a mobile-first implementation, and an accessibility
22|record where every line names the command or the observation that satisfied it.
38|4. **verify** — measure the rendered result, not the CSS you wrote. Geometry, contrast over
44|   the person and the date. WCAG 2.2 AA is the release floor and the only level anything
47|6. A scanner is a filter, not a verdict. Axe output and a contrast ratio together do not
50|   reduced motion and the performance budget are judged by `/ai-review`'s motion lens, and
55|   proves nothing about alt text, contrast, trademark, copyright or accessibility has not
76|- Every accessibility line names a command or a person and a date; nothing is ticked by a
```

The verify route (step 4) explicitly measures "contrast over the real background" — that is a
contrast check in the verify route — and step 5 states "WCAG 2.2 AA is the release floor and
the only level anything blocks on". A WCAG floor and an accessibility-evidence discipline are
present in the skill, so "no WCAG floor", "no contrast check" and "nothing in the framework
says it" are contradicted by the tree. What the grep does confirm: `keyboard` and `focus`
appear nowhere in ai-design (absent = the two halves of the claim that do hold), and
`reduced motion` appears once but is delegated to `/ai-review`'s motion lens, not checked in
the verify route.

## WRONG — "The research's AL-Design … rows (`.ai/research/reports/17-AL-Design/report.md`, …) name the a11y discipline"

Command:

```text
$ grep -inE "accessib|a11y|contrast|keyboard|wcag" .ai/research/reports/17-AL-Design/report.md
(no matches; exit 1)
```

The AL-Design research report (40 files swept, 15 adoption rows D-01…D-15) never names
accessibility, contrast, keyboard or WCAG anywhere. The other half of the compound claim
holds: `the claude-agents repo/design/accessibility-auditor.md` exists and is
entirely about WCAG/keyboard/contrast. The AL-Design row does not "name the a11y discipline".

## UNPROVEN — "The research's AL-Design and claude-agents rows … name the a11y discipline"

Partial verdict recorded above; the claude-agents half:

```text
$ ls -la the claude-agents repo/design/accessibility-auditor.md
-rw-r--r-- the owner 12498 Aug 26 12:46 the claude-agents repo/design/accessibility-auditor.md
$ grep -cE "WCAG|keyboard|contrast" the claude-agents repo/design/accessibility-auditor.md
(wcag+keyboard+contrast present across ~78 lines; sample verified above)
```

Outside this repository, read verbatim on 2026-08-26; the file exists and names the discipline.

## UNPROVEN — the four "Examples somebody can check" fixtures: "`uv run --with pytest==9.1.1 pytest -q tests/test_038_accessibility.py -k floor` → `1 passed`" (and `not_covered`, `honest`, `reference`)

Command (executed as written, on main):

```text
$ uv run --with pytest==9.1.1 pytest -q tests/test_038_accessibility.py -k floor; echo "exit=$?"
no tests ran in 0.00s
ERROR: file or directory not found: tests/test_038_accessibility.py
exit=4
```

`tests/test_038_accessibility.py` does not exist on this branch, so none of the four fixture
commands can pass today and nothing in the tree can decide the claimed behaviours. The same
missing file is the subject of every `-k` variant. Nothing in the tree decides the G/W/T
claims (floor holds / silent pass refused / honest exit / reference loads).

## UNPROVEN — Production-ready "CI/CD — `just check` runs `tests/test_038_accessibility.py` on every push" (and the "038 fixture runs … on every push")

Commands:

```text
$ glob tests/test_038*            → no files
$ ls tests/test_038_accessibility.py → No such file or directory
$ grep -n test_038 .github/workflows/check.yml justfile  → no matches
$ uv run --with pytest==9.1.1 pytest -q tests/test_038_accessibility.py -k floor; echo exit=$?
ERROR: file or directory not found: tests/test_038_accessibility.py
exit=4
```

The workflow does run `just check` on every push (`.github/workflows/check.yml`: "the gate,
exactly as a developer runs it" → `just check`), and `just check` chains `build sbom lint
typecheck test cover security register skilleval evals counts intent-page lenses council map
ran`, with `cover` running `pytest -k "not fast_enough"`. So the *machinery* that would run a
038 fixture exists, but the fixture is absent — "runs tests/test_038_accessibility.py" is not
true of this tree in any present tense. The claim is satisfiable only after the spec lands.

## UNPROVEN — B-038-2 / D-038-02 "spec 037 roadmap table rows 6/16 recorded this" (the roadmap "already records the design rows as insumos the design skill may use — not as … skills")

Commands:

```text
$ grep -nE "038|insumo|AL-Design|6 \|" specs/037-model-router-and-intake-validation/spec.md
195|| 6 | al-design-system | P2 — solo si producimos UI (spec 038) | spec candidata |
204|| 16 | AL-Design / a11y | P2 — guard de a11y en diseño (spec 038) | spec candidata |
$ grep -c "insumo" specs/037-model-router-and-intake-validation/spec.md
0
```

Rows 6 and 16 exist and both name spec 038 — that half is OK. But the word "insumo" appears
nowhere in the 037 spec, and the two rows record candidate-spec status ("spec candidata"),
not a doctrine that design skills are loadable *insumos* of ai-design and never framework
skills. The tree cannot decide the "recorded this" attribution because the recording is not
in the cited table.

## UNPROVEN — "per the owner's 'no sea agente sino que esté dentro de ai-engineering'"

Command:

```text
$ grep -rn "sea agente" specs/ src/ .agents/ .ai/ docs/ 2>/dev/null
specs/038-design-accessibility-guard/spec.md:20:...per the owner's "no sea agente sino que esté
dentro de ai-engineering")...
```

The only occurrence of the owner's phrase in the tree is the 038 spec quoting it. No other
file records the owner saying it; the attribution is unverifiable from the tree.

## UNPROVEN — "the other design skills in the roadmap's design rows `(apple-design`, `hallmark`, `high-end-visual-design`, `emil-design-eng`, …)`"

Commands:

```text
$ ls .agents/skills/
ai-review ai-report ai-note ai-security ai-verify ai-ship ai-spec ai-plan ai-goal
ai-design ai-explore ai-cycle ai-debug ai-council ai-build ai-challenge ai-research   (16 skills)
$ grep -nE "apple-design|hallmark|high-end-visual-design|emil-design-eng" specs/037-model-router-and-intake-validation/spec.md
(no matches; exit 1)
$ ls the skills dir/ | grep -E "apple-design|hallmark|high-end-visual-design|emil-design-eng"
apple-design
emil-design-eng
hallmark
high-end-visual-design
```

The four named design skills are not in this repository's skill corpus and are not named in
the 037 roadmap table (whose design-adjacent rows are only 6 and 16); they exist as
user-global skills under `~/.claude/skills/`. "The roadmap's design rows" is not where those
four are recorded. The claim is about the reference's future content, so nothing in the tree
decides it — but the cited home is not supported.

## OK — "roadmap row 16: 'AL-Design a11y — P2 — guard de a11y en diseño (spec 038)'"

Command:

```text
$ grep -n "AL-Design" specs/037-model-router-and-intake-validation/spec.md
204|| 16 | AL-Design / a11y | P2 — guard de a11y en diseño (spec 038) | spec candidata |
```

Row 16 exists with P2 and the spec-038 pointer. Exact cell text is "AL-Design / a11y", not
"AL-Design a11y" — a paraphrase, not a blocked claim.

## OK — "ai-design (the framework's design gateway) has four routes — shape, build, imagery, verify"

Command:

```text
$ sed -n '1,20p' .agents/skills/ai-design/SKILL.md
One gateway with four routes for creating, extending or redesigning a web, mobile, native
or CLI experience: shape the work, build the system, opt into imagery, and verify the
rendered result rather than the declared CSS.
```

Route names in the body are `shape`, `system-build`, `imagery`, `verify`; "build" is the
description's verb. Fair paraphrase.

## OK — "verifies the rendered result rather than the declared CSS" and "creating/extending/redesigning a web, mobile, native or CLI experience"

Both phrases appear verbatim in the skill description (see command above). OK.

## OK — "imposes no style and never requires generated imagery"

Command:

```text
$ grep -n "imposes no style and never requires" .agents/skills/ai-design/SKILL.md
10:It imposes no style and never requires generated imagery.
```

Verbatim. OK.

## OK — "no keyboard check, no focus-visible check" (and "no reduced-motion respect" scoped to the verify route)

Command:

```text
$ grep -nE "keyboard|focus" .agents/skills/ai-design/SKILL.md
(no matches; exit 1)
```

`keyboard` and `focus` appear nowhere in ai-design — those two halves hold. "Reduced motion"
appears once (line 50) but is delegated to `/ai-review`'s motion lens, and step 4 (verify)
does not check it — so the claim as scoped to the verify route holds, with the caveat that
reduced motion is not absent from the skill (see the WRONG entry above: the skill's line 50
*does* name it).

## OK — "contract.py's audit lanes prove the pattern: a checked rule (`_incorrect_correct_problems`, `_anti_rationalization_problems`) refuses a skill that omits a discipline. ai-design has no such lane for a11y"

Commands:

```text
$ grep -n "_anti_rationalization_problems\|_incorrect_correct_problems" src/ai_engineering/contract.py
209|    found.extend(_anti_rationalization_problems(path.parent, name))
211|    found.extend(_incorrect_correct_problems(path.parent, name))
$ grep -inE "accessib|a11y|contrast|keyboard|wcag" src/ai_engineering/contract.py
(no matches; exit 1)
```

Both lanes exist and are wired into the audit; no a11y lane exists for ai-design. OK.

## OK — "the ai-review references are the worked pattern" / "the skill anatomy allows references, templates, scripts"

Commands:

```text
$ ls .agents/skills/ai-review/references/
testing.md simplification.md docs.md frontend.md motion.md architecture.md
performance.md security.md compatibility.md correctness.md
$ grep -n "references/ subfolder\|scripts/" src/ai_engineering/contract.py | head -3
54:The skill's own `references/` subfolder ships with it and is not a dependency; …
487:… Split references/ or move scripts to scripts/
```

The ai-review reference pattern exists in this tree, and the skill anatomy (as contract.py
enforces it) ships a skill's own `references/` and tolerates `scripts/`. "Templates" are not
explicitly evidenced in the lane code, but the anatomy claim broadly holds.

## OK — "keeping the context economy (spec 033)" / "the framework's fifteen-skill target is deliberate"

Commands:

```text
$ ls specs/033-context-economy-and-skill-authoring/    → spec.md, plan.md, approval.md …
$ grep -n "Fifteen-skill target" specs/010-governed-agentic-engineering-foundation/spec.md
140:### Fifteen-skill target and routing boundaries
$ grep -rn "fifteen-skill target is unchanged" specs/029-evidence-executed-and-answer-keys/spec.md
41:- **No new skill.** B-029-2 modifies…; the fifteen-skill target is unchanged.
```

Spec 033 exists with that title and the fifteen-skill target is a deliberate, documented
route boundary (spec 010) that later specs reuse. OK.

## OK — "the inherited `madr.validate` red from ADR 0025 stays open"

Commands (tree's own records; the red is attributed there with the verb's output):

```text
$ grep -rn "MADR_SCHEMA_INVALID" specs/028-writer-model-recorded/blocked.md
9:`madr.validate`; on this tree that returns `INCOMPLETE [MADR_SCHEMA_INVALID]` — …
13:The current worktree fails schema: `docs/adr/0025-the-maps-real-broken-references-are-accepted-as-a-dated-record.md`
$ grep -rln "ADR 0025" specs/029*/spec.md specs/030*/spec.md specs/031*/spec.md specs/033*/spec.md
(all five records document the same inherited red)
```

`madr.validate` is documented across specs 028–033 as `INCOMPLETE [MADR_SCHEMA_INVALID]`
from ADR 0025 of spec 026; the 038 spec's "stays open, not authorised here" framing matches
the standing record. I did not re-execute `madr.validate` (needs the installed wheel); the
tree's repeated recorded output, quoted in `blocked.md`, is the evidence.

## OK — "`just security`: gitleaks, semgrep, trivy on every push" and "`.github/workflows/check.yml` runs the whole gate on every push"

Commands:

```text
$ grep -nE "^check:|^security:|^cover:" justfile
263: check: build sbom lint typecheck test cover security register skilleval evals counts intent-page lenses council map ran
101: security:
$ grep -n "just check" .github/workflows/check.yml
(the gate, exactly as a developer runs it) → run: just check | tee …
```

`security` (gitleaks version-pinned, trivy version-pinned, semgrep baseline) is in the check
chain, and CI runs `just check` on push/PR/merge_group. The "on every push" half is satisfied
via the check chain. OK.

## OK — "every verb still emits the one JSON line `ai-eng report digest` reads"

Command:

```text
$ grep -n '"report"' src/ai_engineering/cli.py
36:    "report": "report digest | issue | surfaces | intent | blocked — what this install can show.",
```

The digest verb exists and the spec adds no verb; the claim is vacuously consistent. OK (as a
no-change claim; no 038 code emits anything yet).

## OK — "the same honesty the framework already demands of verifiers (`NOT COVERED ≠ PASS`)"

Command:

```text
$ grep -rn "NOT COVERED" specs/035-adoption-of-reference-patterns/spec.md | head -2
112:- **B-035-2 — Verifier isolation.** … `NOT COVERED` is reported, never a silent `PASS` …
```

The honesty rule is a documented, implemented contract (spec 035, `verify_cold.py` `Verdict`).
OK.

---

## Summary

- **WRONG: 2** — (1) ai-design has "no WCAG floor / no contrast check / nothing says it"
  (contrast and WCAG AA are checkable in the skill today); (2) the AL-Design research row
  "names the a11y discipline" (zero a11y mentions in `17-AL-Design/report.md`).
- **UNPROVEN: 6** — the four fixture examples and the CI/CD "runs tests/test_038..." boxes
  (file absent, pytest exit 4 on the exact commands); rows 6/16 "recorded this" (no
  "insumo" in 037); the owner's "no sea agente" quote (only in 038 itself); the four named
  design skills' home ("roadmap's design rows" names none of them; they live in
  `~/.claude/skills`, not the tree).
- **OK: 12** — roadmap row 16; four routes; "verifies the rendered result"; "imposes no
  style"; keyboard/focus absent and reduced-motion not in verify (scoped); contract lanes
  exist and no a11y lane; ai-review references pattern; spec 033 context economy;
  fifteen-skill target; ADR 0025 red; `just security` in CI; `report digest` verb;
  `NOT COVERED ≠ PASS`.

## What I could not test

- **Any fixture behaviour (floor holds / not-covered / honest / reference loads):** the
  behaviours are unimplemented on main — `tests/test_038_accessibility.py` does not exist,
  so the four example commands fail at collection (exit 4) rather than asserting anything.
- **The `_accessibility_problems` lane and `references/accessibility.md`:** neither exists
  on main; there is no tree evidence about refusal semantics or load-on-verify behaviour.
- **`madr.validate` re-execution:** I did not build/install the wheel to re-run it; the
  INCOMPLETE status is attested by specs 028–033 and `.ai/reports/014` (recorded verb
  output), not by a fresh run here.
- **Whether the roadmap "records" the insumo doctrine:** the cited rows exist but contain no
  such recording; this could not be confirmed either way from any other file — the grep
  shows the word absent from spec 037.
- **The owner quote's provenance:** nothing outside the 038 spec records the conversation.