# Challenge — spec 039 (documentation-discipline)

Date: 2026-08-26. Challenger: independent critic. Read only the 039 spec, the
ai-challenge skill, and the tree. Every finding names the spec sentence, the command that
tested it, and what it printed.

## Findings, worst first

### WRONG — "CI/CD — `just check` runs `tests/test_039_documentation.py` on every push (`.github/workflows/check.yml`)"

Spec: Production-ready, first box, ticked `[x]` — and the success example beneath it
promises `uv run --with pytest==9.1.1 pytest -q tests/test_039_documentation.py -k
reference` → `1 passed`.

The fixture does not exist, and nothing anywhere runs it.

```
$ glob tests/test_039_documentation.py
Skipped missing paths: tests/test_039_documentation.py

$ grep -n "test_039\|039" .github/workflows/check.yml justfile
No matches found

$ uv run --with pytest==9.1.1 pytest -q tests/test_039_documentation.py -k reference
ERROR: file or directory not found: tests/test_039_documentation.py
no tests ran in 0.00s
exit=4
```

Three further ticked Production-ready boxes rest on the same absent file: "the 039
fixture runs in the gate's pytest half (`just cover`) on every push; the reference is
asserted by its fixture" and "the reference is read by its fixture" (Second path). A
draft may ship deliverables later — but these boxes are ticked as *done*, and the
"Examples somebody can check" section presents the `1 passed` as an executed fact.

### WRONG — "`just doctor` and the `homes` recipe pass" (Honest home example)

Spec: "When `ai-eng doctor` runs, Then it still prints one line per file class with its
exact path (`just doctor` and the `homes` recipe pass; no home moved)."

There is no `doctor` recipe in the justfile. The command the spec prints fails.

```
$ just doctor
error: justfile does not contain recipe `doctor`
exit=1
```

`just homes` does pass (`no commit differs from main, so there is nothing to measure`,
exit 0), and `uv run ai-eng doctor` runs (exit 1 on this machine, but not for homes:
assertion 18 is `ok`). The recipe named in the example is wrong either way.

### WRONG — "`ai-eng doctor` prints one line per file class with its exact home"

Spec: File governance — "File governance is already machine-listed: `ai-eng doctor`
prints one line per file class with its exact home … and the `homes` recipe +
`test_contract_craft` assert it".

Doctor's homes assertion is one aggregate line covering three homes, not one line per
file class, and it never names `policy/`, `.agents/skills/`, `references/` or `docs/`
— four of the seven classes the spec's own governance list enumerates.

```
$ uv run ai-eng doctor | grep -in "inventoried\|Intent home"
18 ok  Your data is yours: every framework file has a declared home
      455 tracked files inventoried, 1 Intent home, none outside .ai/, specs/, docs/adr/

$ grep -n 'homes = ' src/ai_engineering/doctor.py
homes = (".ai/", "specs/", "docs/adr/")
```

Doctor machine-lists three homes. The "one line per file class" in the example is not
what the command prints.

### WRONG — "the `homes` recipe + `test_contract_craft` assert it"

Spec: same governance paragraph. `test_contract_craft.py` is the spec-032 skill-craft
suite (anti-rationalization, output contract, Incorrect/Correct pairs, load tiers) and
contains no homes assertion at all. The homes machinery is `just homes` →
`tests/one_home.py`, which asserts PO-16 (one primary home per commit) — a commit
discipline, not the file-class governance table.

```
$ grep -n "homes\|one_home\|doctor\|tracked" tests/test_contract_craft.py
No matches found

$ grep -n "^homes" justfile
homes base="main":
    @uv run python tests/one_home.py --since {{base}}
```

The `homes` recipe half checks out; the `test_contract_craft` half does not exist.

### WRONG — "no mention of controlled language (ASD-STE100) exists anywhere in the repo (grep zero, verified this session)"

Executed now, the grep is not zero — the spec's own committed file carries the term
eight times. It is zero *outside* spec 039.

```
$ grep -rn "STE100\|Simplified Technical English" . --include="*.md" | grep -v "specs/039-documentation-discipline/spec.md"
(no output)
```

The substance ("absent before this spec") is likely true, but the sentence as written
claims a zero that the spec itself falsifies the moment it lands.

## UNPROVEN

### UNPROVEN — "the research already classifies claude-agents as adopt-the-pattern-not-the-content"

Spec: D-039-01 rationale and Decision. The research tree never names claude-agents. The
closest text is a generic principle about domain content.

```
$ grep -rn "claude-agents\|claude agents" .ai/research/
No matches found

$ grep -n "Adoptar el patrón" .ai/research/SINTESIS.md
156|Contenido de dominio: salones (Loop-Eng), Next.js (cc-creators/SkillSpector), shadcn
   components (al-ds), KPIs/pre-prompt de contains-studio. Adoptar el patrón, no el contenido.
```

The "adopt the pattern, not the content" line is a general finding about domain-heavy
content in other repos; it never mentions claude-agents. The only place claude-agents is
classified in-tree is spec 037's roadmap table, and it is rejected there with a *different*
reason ("contenido inflado, tools decorativos, KISS ❌ — research hoja 12") whose sheet
citation is itself suspect: sheet 12 (`12-contains-studio-agents`) is not a claude-agents
report. Nothing in the research decides this claim.

### UNPROVEN — "the `writing-for-agents` skill the owner pasted codifies the agent-document levers"

Spec: Context — "the `writing-for-agents` skill the owner pasted codifies the agent-document
levers". The skill is not in this tree (`grep -rn "writing-for-agents" .` matches only
039's spec.md), so its content cannot be checked here. It is an external input the spec
takes on trust.

### UNPROVEN — "roadmap rows 8/10; this is the documentation half"

Spec: "Who this is for" — "The repository owner (roadmap rows 8/10; this is the
documentation half)". The rows exist in the committed 037 roadmap (D-037-04), but calling
both "the documentation half" over-reads them: row 8 is a refactor skill, row 10 a CLAUDE.md
template.

```
| 8 | code-simplifier/refactor | P2 — skill de refactor KISS/DRY/YAGNI, no hook auto |
| 10 | large-codebases CLAUDE.md | P2 — template por-área si onboarding |
```

Row 10 is documentation-shaped; row 8 is not. The citation resolves, the label is the
author's.

## OK — checked and it holds

### Craft lanes exist and fire — "`contract.py` audits fog ceiling (`fog`), load tiers (`_load_tier_problems`), output contract (`_output_contract_problems`)"

```
$ grep -n "def fog\|SKILL_FOG_CEILING\|def _load_tier_problems\|def _output_contract_problems\|def _anti_rationalization_problems\|def _incorrect_correct_problems\|def _appendix_problems" src/ai_engineering/contract.py
def _anti_rationalization_problems
def _output_contract_problems
def _incorrect_correct_problems
def _load_tier_problems
def _appendix_problems
def fog(body: str) -> float:
SKILL_FOG_CEILING = 11.03

$ uv run python -c "from pathlib import Path; from ai_engineering import contract; print('problems', len(contract.audit(Path('.agents/skills'))))"
problems 0
```

Nuance: `contract.audit()` never calls `fog` — the fog ceiling is scored by
`tests/test_contracts.py:2094-2107` (`contract.fog(contract.prose(...))` per SKILL.md).
"Already pass mechanical limits" is true; "contract.py audits" is true only for the
function's home, not the audit path.

### STE100 / writing-for-agents absent outside the spec — "The discipline exists in the wild … but is not in this tree"

```
$ grep -rn "writing-for-agents" . | grep -v "specs/039-documentation-discipline/spec.md"
(no output)
$ grep -rn "STE100" . | grep -v "specs/039-documentation-discipline/spec.md"
(no output)
```

### technical-writer.md exists, is a general documentation agent, has the claimed frontmatter, contains no STE100

```
$ ls /Users/soydachi/repos/claude-agents/product/technical-writer.md
-rw-r--r--  the owner 12095  /Users/soydachi/repos/claude-agents/product/technical-writer.md

$ grep -n "model:\|tools:\|memory:" /Users/soydachi/repos/claude-agents/product/technical-writer.md
model: sonnet
tools: Write, Read, Edit, Grep, Glob, WebSearch
memory: project

$ grep -n "STE100\|Simplified Technical English" /Users/soydachi/repos/claude-agents/product/technical-writer.md
(no output)

$ grep -c "API Documentation\|Changelog and Release Notes\|README Structure\|Architecture Decision Records" /Users/soydachi/repos/claude-agents/product/technical-writer.md
4
```

API refs, changelogs (Keep a Changelog), READMEs and ADRs are all present; STE100 is
absent. "It contains no STE100" checks out.

### ai-spec / ai-plan / ai-report corpus.md files exist

```
$ glob .agents/skills/ai-spec/corpus.md .agents/skills/ai-plan/corpus.md .agents/skills/ai-report/corpus.md
# .agents/skills/ai-spec/corpus.md
# .agents/skills/ai-plan/corpus.md
# .agents/skills/ai-report/corpus.md
```

(No `documentation-writer` route exists in any of them yet — expected for a draft; the
B-039-2 route is a deliverable, and the "routes are asserted by `tests/skill_eval.py`"
claim names a file that does exist: `tests/skill_eval.py`.)

### `.agents/skills/ai-report/references/` does not exist

```
$ glob .agents/skills/ai-report/references/*
Skipped missing paths: .agents/skills/ai-report/references/*
```

`ai-report/` holds `corpus.md` only. The B-039-1 home is therefore empty today — the
deliverable, not a contradiction.

### The dossier doctor 'homes' recipe exists and runs

```
$ grep -n "homes" justfile
homes base="main":
    @uv run python tests/one_home.py --since {{base}}

$ just homes
  no commit differs from main, so there is nothing to measure.
exit=0
```

`doctor` itself (the CLI verb) also runs and assertion 18 (`Your data is yours`) is `ok`.

### `docs/tools.md` exists

```
$ glob docs/tools.md
docs/tools.md
```

### NotebookLM is degraded — "not reachable from this machine (`degraded-tool: notebooklm`)"

`notebooklm doctor` passes (exit 0, "All checks passed"), but the real session is dead —
exactly the recorded state.

```
$ notebooklm list
Unexpected error: Authentication expired or invalid. Redirected to: https://accounts.google.com/…
Run 'notebooklm login' to re-authenticate.

$ grep -n "degraded-tool: notebooklm" .ai/reports/019-criticos-paralelo-loop-spec-madr.html
…degraded-tool: notebooklm (doctor pasa, pero la sesión real expiró: requiere notebooklm login)
```

### The inherited `madr.validate` red stays open — "the inherited `madr.validate` red from ADR 0025 stays open"

```
$ uv run --with pytest==9.1.1 pytest -q tests/test_madr.py
5 failed, 32 passed in 29.45s
exit=1
```

The red is real and still open (five failures now, four in the dated reports — the class
is unchanged: repository-wide `madr.validate(...) == PASS` assertions failing).

### "context economy, spec 033" exists

```
$ glob specs/033-*
specs/033-context-economy-and-skill-authoring/
```

## What I could not test

- **The reference and the routes** (`references/documentation-writer.md`, the three corpus
  routes, the fixture). They are the deliverables and do not exist yet; their example
  commands (`-k reference`, `-k bare_bound`) cannot run — see the first WRONG finding. The
  "no shared line" between fixture and `skill_eval.py` is likewise untestable until both
  halves exist.
- **The `writing-for-agents` skill's content** — external, not in this tree; the spec's
  description of what it "codifies" is taken on trust.
- **The NotebookLM research content** — the notebook is genuinely unreachable (auth
  expired), so the claim that it "may contain STE100 workbook specifics" can neither be
  confirmed nor denied.
- **The fifteen-skill target arithmetic** — the spec calls the target "deliberate" (option
  2's cost), and the current tree holds **17** skill directories, not 15:
  `ai-build ai-challenge ai-council ai-cycle ai-debug ai-design ai-explore ai-goal ai-note
  ai-plan ai-report ai-research ai-review ai-security ai-ship ai-spec ai-verify`. Whether
  the fifteenth-skill catalogue (spec 010) is still the live ceiling is a governance
  question, not a testable sentence.
- **A full `just check`** — the whole gate needs gitleaks/trivy and ~20 minutes; every
  component the spec cites was exercised individually instead.
