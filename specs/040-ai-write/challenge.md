# Challenge: specs/040-ai-docs/spec.md

Attacked on 2026-08-26 against the tree at `main`, by the ai-challenge rule: every
checkable sentence got a command and the verdict on what it printed. 4 WRONG, 3 UNPROVEN,
11 OK. Nothing here edits the specification.

The 040 fixture, the ai-docs skill and the capability entry do not exist yet — the spec is
a draft and most of its receipts are runnable only after its own build — so the challenge
focuses on what the tree already decides: the citations, the counts, the routing corpus and
the two instruments the spec leans on (`just map`, `tests/skill_eval.py`).

## WRONG — "roadmap rows 8/10 folded here"

Spec, "Who this is for": "The repository owner (roadmap rows 8/10 folded here)".

Command: `sed -n '189,205p' specs/037-model-router-and-intake-validation/spec.md`

```text
| 8 | code-simplifier/refactor | P2 — skill de refactor KISS/DRY/YAGNI, no hook auto | spec candidata |
...
| 10 | large-codebases CLAUDE.md | P2 — template por-área si onboarding | spec candidata |
```

The rows exist and neither is a documentation row: 8 is a refactor skill, 10 an onboarding
CLAUDE.md template. Nothing in either row folds into a docs surface. Spec 039's challenge
flagged the same anchor ("roadmap rows 8/10; this is the documentation half" — UNPROVEN:
"row 8 is a refactor skill, row 10 a CLAUDE.md template") and its council recommended
"correct the roadmap citation (rows 8/10 are not documentation rows) or drop it"
(`specs/039-documentation-discipline/council.md`). 040 repeats the citation without the
correction.

## WRONG — "The count is not pinned (no test asserts a skill ceiling; the audit audits what exists)"

Spec, "Challenged once": "The count is not pinned (no test asserts a skill ceiling; the
audit audits what exists)."

Command: `sed -n '886,935p' tests/test_contracts.py`

```text
COUNTED = (
    ("skills", "README.md", "{Word} written procedures"),
    ("skills", "AGENTS.md", "carries {word} skills"),
    ...
)
    counts = {
        "skills": len([p for p in paths.skills().glob("ai-*") if p.is_dir()]),
        ...
    }
    for what, name, phrase in COUNTED:
        number = counts[what]
        said = phrase.format(n=number, word=WORDS[number], Word=WORDS[number].capitalize())
        body = (ROOT / name).read_text(encoding="utf-8")
        assert said in body, f"{name} does not say {said!r}: there are {number} {what}"
```

Command: `grep -n "written procedures\|carries .* skills" README.md AGENTS.md`

```text
README.md:15:Seventeen written procedures, four guards, and a command-line tool with ten verbs. `init`
AGENTS.md:34:A wheel on PyPI that carries seventeen skills, four guards and a ten-verb CLI. One command
```

The count IS pinned by a test, just not as a ceiling. The derived count is 17 (the audit
counts `ai-*` directories) and the test asserts README.md and AGENTS.md prose equals it;
adding ai-docs makes the count 18 and this test goes red until both files say "eighteen".
So the half "no test asserts a skill ceiling" is true, but "the count is not pinned" is
contradicted by the tree, and the spec's own cost line — "one skill directory + one
capability entry + the routing cases that move the `skill_eval` baseline" (B-040-2) — omits
the README/AGENTS prose update this test forces. (There is no test asserting a numeric
ceiling — 17 or 18 or any bound — that half checks out.)

## WRONG — "exits `not-covered: <reason>` … exactly as 036/039 do"

Spec, "Challenged once": "anything unverifiable — a forward-looking post, a product claim —
exits `not-covered: <reason>` with the reason recorded, exactly as 036/039 do."

Command: `grep -rn "not-covered\|NOT COVERED" specs/ | grep -v 040-ai-docs`

```text
specs/038-design-accessibility-guard/approval.md:24:…or exits `INCOMPLETE: a11y not-covered <reason>`;
specs/038-design-accessibility-guard/approval.md:26:(the concrete checks and the `not-covered` rule, …)
specs/038-design-accessibility-guard/challenge.md:306:112:- **B-035-2 — Verifier isolation.** … `NOT COVERED` is reported, never a silent `PASS` …
```

The `not-covered` exit's home is 035 (B-035-2, "NOT COVERED is reported, never a silent
PASS") and 038 (the a11y reference's `not-covered` rule). Specs 036 and 039 contain no
`not-covered`/`NOT COVERED` at all. The citation names the two specs that do not carry the
rule.

## WRONG — "the `skill_map`'s accepted/reference bookkeeping absorbs the new skill's references … ai-docs's references point at real files"

Spec, "Assumptions and unresolved risks": "the `skill_map`'s accepted/reference bookkeeping
absorbs the new skill's references (the map's prohibition on broken references applies;
ai-docs's references point at real files)."

Command: `just map` (runs `sm scan` then `uv run python -m ai_engineering.skillmap`; `sm --version` → `1.12.2`)

```text
skillmap: 313 findings | 12 template holes declared, 77 accepted, 208 real-and-unaccepted
  REAL  '.agents/skills/ai-plan/corpus.md' -> '.agents/skills/ai-plan/references/documentation-writer.md'
  REAL  '.agents/skills/ai-spec/corpus.md' -> '.agents/skills/ai-spec/references/documentation-writer.md'
  REAL  'specs/039-documentation-discipline/spec.md' -> 'specs/039-documentation-discipline/references/documentation-writer.md'
  REAL  'specs/040-ai-docs/spec.md' -> 'specs/040-ai-docs/references/documentation-writer.md'
  REAL  'specs/040-ai-docs/spec.md' -> 'specs/040-ai-docs/claude-agents/product/technical-writer.md'
  REAL  'specs/040-ai-docs/spec.md' -> 'specs/040-ai-docs/corpus.md'
REAL_AND_UNACCEPTED=208
error: recipe `map` failed on line 262 with exit code 1
```

Three things the tree says here. (1) The map gate is red on `main` today — 208 real
unaccepted references — so the "bookkeeping absorbs" is not what the mechanism does:
absorption is an exact accepted `(node, target)` pair for each reference, never automatic.
(2) The very corpus routes the spec calls the writing standard ("`ai-spec`, `ai-plan` and
`ai-report` route their own authoring to it") are themselves flagged REAL today, because a
bare `references/documentation-writer.md` resolves relative to each skill directory and the
real file lives at `.agents/skills/ai-report/references/documentation-writer.md`. (3) The
040 spec's own text contributes three REAL entries right now, using exactly the bare-path
shape it promises to ship. "The map's prohibition applies" is real and enforced (exit 1);
"ai-docs's references point at real files" is what the map will decide, and the pattern the
spec writes does not.

## UNPROVEN — "the research classifies claude-agents as adopt-the-pattern-not-the-content"

Spec, "Context": "the research classifies claude-agents as adopt-the-pattern-not-the-
content" — listed under "What is true today, measured in this tree on 2026-08-26".

Command: `grep -rn "claude-agents\|claude agents" .ai/research/`; `grep -n "Adoptar el patrón" .ai/research/SINTESIS.md`

```text
(no matches under .ai/research/)

156:- Contenido de dominio: salones (Loop-Eng), Next.js (cc-creators/SkillSpector), shadcn components (al-ds), KPIs/pre-prompt de contains-studio. Adoptar el patrón, no el contenido.
```

Nothing in this tree's research names claude-agents. The "adopt the pattern, not the
content" line is a general principle about domain-heavy content in other repositories; the
only in-tree classification of claude-agents is spec 037's roadmap row 1, rejected with a
different reason ("contenido inflado, tools decorativos, KISS ❌ — research hoja 12"). Spec
039's challenge marked this same claim UNPROVEN; 040 repeats it as a fact.

## UNPROVEN — "The candidate tool, `claude-agents/product/technical-writer.md`" is a claim "measured in this tree"

Spec, "Context": the claude-agents bullet sits inside "**What is true today, measured in
this tree on 2026-08-26:**".

Command: `git ls-files | grep -c claude-agents`; `ls the owner/repos/claude-agents/product/technical-writer.md`

```text
0
the owner/repos/claude-agents/product/technical-writer.md
```

The file is not in this tree (git tracks nothing under `claude-agents`); it exists on the
owner's machine at the sibling repository path. Spec 038's challenge flagged the same shape
("a bullet labelled 'measured in this tree' cites a file that is not in this tree").
The *content* claims check out at the external path — `grep -n "model:\|memory:"` →
`4:model: sonnet` / `8:memory: project`; `grep -c "STE100\|Simplified Technical English"` →
`0` — so the non-portability description is accurate, but the in-tree measurement label is
not supported, and a stranger fork cannot reproduce the receipt.

## UNPROVEN — the four Example receipts cannot run

Spec, "Examples somebody can check": `uv run --with pytest==9.1.1 pytest -q
tests/test_040_ai_docs.py -k verified` → `1 passed` (and `-k no_cache`, `-k not_covered`,
`-k routing`).

Command: `test -f tests/test_040_ai_docs.py; echo $?`; `uv run --with pytest==9.1.1 pytest -q tests/test_040_ai_docs.py -k verified`

```text
1
no tests ran in 0.00s
ERROR: file or directory not found: tests/test_040_ai_docs.py
```

The fixture does not exist, so none of the four receipts can produce its promised verdict
today. Same status as 039 at draft time; the tree decides only that the commands fail at
collection, not what the fixture would assert. The "routing" receipt additionally depends
on routes no corpus carries yet.

## OK — `ai-ship` owns "Update the changelog" (`.agents/skills/ai-ship/SKILL.md:31`)

Command: `sed -n '31p' .agents/skills/ai-ship/SKILL.md`

```text
3. Update the changelog. A breaking change is written as a breaking change, in the words
```

## OK — `ai-report`'s "one local draft and nothing else", and its log/diff refusal

Command: `grep -n "one local draft\|no field for a log" .agents/skills/ai-report/corpus.md`

```text
"open the pull request and close the ticket" — use `/ai-ship`, because the changelog, the pull request and the closing keyword belong to it; this skill writes one local draft and nothing else.
"attach the log file and the diff so they can see it" — refused outright, by the payload rather than by judgement: there is no field for a log or a diff, and adding one is a specification change and not a flag.
```

Both halves of the "Challenged once" quote are verbatim; the corpus also pushes changelog/PR
to ai-ship as the spec says. The "README can be written by ai-report today" counter is
answered by the tree: forced through ai-report, a README hits the "nothing else" refusal.

## OK — ai-note / ai-report / ai-ship capability entries exist; no ai-docs entry

Command: `grep -n 'id = "ai-note"\|id = "ai-report"\|id = "ai-ship"' policy/capabilities.toml`; `grep -c '^id = "ai-' policy/capabilities.toml`; `grep -n 'ai-docs' policy/capabilities.toml`

```text
320:id = "ai-note"
335:id = "ai-report"
428:id = "ai-ship"
19
(no output)
```

All three route-owned skills are declared (ai-note write-root `docs/notes`; ai-report with
digest/intent/blocked/issue modes; ai-ship with commit/pull-request modes). The manifest
carries 19 capabilities and none is ai-docs, matching the spec's "no capability declaration
in `policy/capabilities.toml`" for the docs surface. (Also OK: `tests/test_contracts.py`
`test_every_declared_capability_has_a_skill_or_names_where_its_work_went` enforces the
manifest↔skill symmetry the "one skill + one capability entry" shape satisfies.)

## OK — the writing standard exists: `references/documentation-writer.md` beside ai-report (spec 039)

Command: `test -f .agents/skills/ai-report/references/documentation-writer.md; echo $?`; `grep -n "^## \|^[0-9]\. \|^[0-9]\. \*\*" .agents/skills/ai-report/references/documentation-writer.md`

```text
0
## Writing for the agent — the levers
1. **Context pointer** … 2. **The two loads** … 4. **Completion criterion** … 5. **Leading word** … 7. **Pruning**
## Writing in controlled language — ASD-STE100
```

The reference exists and names context pointers, the two loads, leading words, pruning,
completion criteria and STE100 — the levers the spec lists. The three corpus routes also
exist (`tests/test_039_documentation.py` asserts ai-spec/ai-plan/ai-report corpora name
`documentation-writer.md` and refuse a vague bound; the routes are data-verified there).
Caveat recorded in the map finding: those same routes are REAL broken references under `sm`
because the bare path resolves relative to each skill directory.

## OK — `.agents/skills/ai-docs` is absent

Command: `ls .agents/skills`; `test -d .agents/skills/ai-docs; echo $?`

```text
ai-report/ ai-design/ ai-review/ ai-note/ ai-security/ ai-verify/ ai-ship/ ai-spec/
ai-plan/ ai-goal/ ai-explore/ ai-cycle/ ai-debug/ ai-council/ ai-build/ ai-challenge/ ai-research/
1
```

Seventeen skills; no ai-docs. (So ai-docs would be the eighteenth — the "seventeenth/
eighteenth skill" framing is the right order of magnitude.)

## OK — `tests/test_040_ai_docs.py` is absent

Command: `test -f tests/test_040_ai_docs.py; echo $?`

```text
1
```

## OK — `docs/tools.md` exists (the human inventory the build will update)

Command: `test -f docs/tools.md; echo $?`

```text
0
```

The file exists; the update is the spec's build's job and is not claimed done — consistent
with the "Unresolved" framing.

## OK — "ai-spec + `ai-eng decide` own specs/ADRs, `ai-note` owns findings, `ai-report` owns issues"

Commands: `grep -n '"decide"' src/ai_engineering/cli.py`; headers of
`.agents/skills/ai-note/corpus.md` and `.agents/skills/ai-report/corpus.md`

```text
30:    "decide": "Add a decision to the spec, or promote it to an MADR with --madr.",
# Corpus: ai-note — Saves a finding that took real time to reach …
# Corpus: ai-report — Reports a reproducible fault in this framework as a governed payload …
```

The routing map the spec draws matches the tree.

## OK — the instruments the Production-ready boxes name exist (the ticks themselves are future)

Commands: `grep -n "just check" .github/workflows/check.yml`; `grep -n "skilleval\|map:\|security:" justfile`; `test -f tests/skill_eval.py; echo $?`

```text
run: just check | tee "$RUNNER_TEMP/check.log"
skilleval: … tests/skill_eval.py … / map: … sm scan … / security: … gitleaks … semgrep … trivy …
0
```

`check.yml` runs `just check` on push/PR/merge_group; `just check` chains `test cover …
skilleval … map`; `just security` version-checks gitleaks/semgrep/trivy; `tests/skill_eval.py`
exists with the fork rule the spec leans on ("no situation claimed twice and no refusal
naming a place that is not there") and a baseline gate against
`policy/pilot-register.toml` (`skill-routing`) that refuses a silent case-count move — the
"baseline moves in the same commit" claim is mechanically enforced. All the boxes are
unchecked in the spec and the wiring they name exists; nothing in the tree contradicts them.

## OK — a session model has no docs route today ("no route, no standard and no gate")

Command: `grep -rn "README\|/ai-docs" .agents/skills/*/corpus.md`

```text
(no matches)
```

No corpus case routes README/wiki/docs-anywhere, and no skill or capability owns the
surface. The measured gap the spec describes is real.

## OK — ADR 0025 and the inherited `madr.validate` red are recorded state

Commands: `ls docs/adr/ | grep 0025`; `test -f tests/test_madr.py; echo $?`

```text
0025-the-maps-real-broken-references-are-accepted-as-a-dated-record.md
0
```

ADR 0025 exists (it is the mastery record behind the skill-map accepted set) and
`tests/test_madr.py` exists; the "gate runs 2365 passed with only the four inherited
test_madr.py failures (ADR 0025)" state is what `.ai/intent.md` records. The spec's claim
that it "does not authorise rewriting that history" is consistent with the tree.

## What I could not test

- **The four example receipts' expected behaviour** (`-k verified / no_cache / not_covered /
  routing`): the fixture does not exist, so the commands fail at collection. What the
  fixture would assert is undecidable in the tree.
- **Whether a real `ai-docs` skill's references would pass `just map`**: the skill does not
  exist. I tested the mechanism instead — the gate is red at 208 unaccepted on `main`,
  absorption is by explicit accepted `(node, target)` pairs, and the bare
  `references/documentation-writer.md` pattern the spec writes is already flagged REAL in
  the 039 corpora — which is why the absorption sentence reads as WRONG rather than OK.
- **The README/AGENTS "eighteen" update**: not executed (no edits here), but
  `test_the_counts_this_repository_states_about_itself_are_the_counts_it_has` derives the
  count from the skills directory, so the failure after adding ai-docs is guaranteed by its
  mechanics, not inferred.
- **The `madr.validate` red itself**: not re-run — the four test_madr failures are the
  recorded baseline in `.ai/intent.md`, and re-running the suite here is out of scope for a
  read-only challenge; only the artifacts' existence was verified.
- **The Logs/Traces/Errors boxes**: they are "not applicable" claims about a change that
  does not exist yet; nothing new emits a line, hops a process or adds a dependency, so
  there is no new behaviour to execute (`ai-eng report digest` and its JSON line predate
  this spec).
- **The four-to-ai-docs reverse routes and the "never a fork" claim**: no corpus carries
  any of the routes yet; the fork rule in `tests/skill_eval.py` exists and was read, but
  the distinct phrasings that must avoid it are future deliverables.
- **What the craft lanes (`contract.audit`) would say about a new skill**: no skill to
  audit; the audit's rules were not enumerated here.