# Council — 040 ai-docs

A five-lens read of `spec.md`, then a cross-read, then a chairman. The lenses never see
each other in round one; in round two each sees the four others relabelled and not its own.
Every finding and every refutation carries a command that was run; its output is written
down below it. Nothing here grants anything.

## Round one — five lenses, each alone

### Cost

What does this change cost, and is the cost claim measurable at the moment of signing?

- **Finding A1 — the advertised cost is a promise over three objects that do not exist.**
  The chosen shape prices "one skill directory + one capability entry + the routing cases",
  but none of the three is in the tree: no `.agents/skills/ai-docs/`, no
  `tests/test_040_ai_docs.py`, no ai-docs capability in `policy/capabilities.toml`. The only
  cost a reader can actually pay today is exit 4 per receipt checked.
  Command: `ls -d .agents/skills/ai-docs tests/test_040_ai_docs.py 2>&1; echo "---"; grep -c "ai-docs" policy/capabilities.toml`
    ```
    ls: cannot access '.agents/skills/ai-docs': No such file or directory
    ls: cannot access 'tests/test_040_ai_docs.py': No such file or directory
    ---
    0
    ```

- **Finding A2 — the "External check" box is ticked today over a corpus move that does not
  exist.** The Production-ready section marks `[x] External check` because "the routing
  refusals are asserted by `tests/skill_eval.py` once the corpus move lands" — but the move
  has not landed: none of the four corpora that B-040-2 says gain the reverse route mentions
  `ai-docs` at all. A ticked box whose substance is conditional on unshipped work is a cost
  the spec has already collected.
  Command: `grep -c "ai-docs" .agents/skills/ai-ship/corpus.md .agents/skills/ai-spec/corpus.md .agents/skills/ai-note/corpus.md .agents/skills/ai-report/corpus.md`
    ```
    .agents/skills/ai-ship/corpus.md:0
    .agents/skills/ai-spec/corpus.md:0
    .agents/skills/ai-note/corpus.md:0
    .agents/skills/ai-report/corpus.md:0
    ```

### Reversibility

What is hard to un-write?

- **Finding B1 — a document verified at write time ages false, and the age box measures
  the fixture, not any written document.** B-040-3 verifies the document "before done"; the
  "Health and data age" box then defers to "the 040 fixture runs in `just cover`'s pytest
  half once it exists" — which measures the fixture's synthetic documents, never a README
  the skill actually wrote. The guarantee is a snapshot; nothing re-checks a written
  document against the changed tree, so the guarantee unwinds silently with no scheduled
  repair.
  Command: `grep -n "Health and data age" specs/040-ai-docs/spec.md`
    ```
    190:- [ ] Health and data age — ticked by the plan's gate: the 040 fixture runs in `just cover`'s pytest half once it exists
    ```

- **Finding B2 — D-040-01's ground lives in another repository, outside every check this
  tree runs.** The decision "the agent stays an insumo" is pinned to
  `claude-agents/product/technical-writer.md`, and 039's challenge verified it only as a
  file in the owner's separate repository. The framework's own gates read this tree only;
  if the vendor repo moves, is renamed or dies, nothing here notices, and the decision's
  ground becomes unpinnable without a record that says so.
  Command: `sed -n '187,188p' specs/039-documentation-discipline/challenge.md`
    ```
    $ ls the owner/repos/claude-agents/product/technical-writer.md
    -rw-r--r--  the owner 12095  the owner/repos/claude-agents/product/technical-writer.md
    ```

### The undecidable path

Which claim cannot be decided from the spec as written?

- **Finding C1 — B-040-2's four reverse routes fork the harness the spec says asserts
  them.** "Those four skills' corpora gain the reverse route" is one composite sentence; all
  four corpora already carry `## Routes here` sections, and `tests/skill_eval.py` reds two
  skills taking the same quoted case. One identical route sentence added to all four is six
  fork pairs; the containment clause reds near-misses too ("update the wiki" is contained in
  "update the wiki page"). The spec's "so the routing harness sees distinct cases, never a
  fork" is a conclusion with no stated mechanism: nothing says the four routes must be
  worded differently, or how distinct they must be under the containment rule.
  Command: `python3 -c "routes=['update the wiki']*4; sk=['ai-ship','ai-spec','ai-note','ai-report']; [print(f'{sk[i]} and {sk[j]} both take the case \"update the wiki\"') for i in range(4) for j in range(i+1,4)]"`
    ```
    ai-ship and ai-spec both take the case "update the wiki"
    ai-ship and ai-note both take the case "update the wiki"
    ai-ship and ai-report both take the case "update the wiki"
    ai-spec and ai-note both take the case "update the wiki"
    ai-spec and ai-report both take the case "update the wiki"
    ai-note and ai-report both take the case "update the wiki"
    ```
  The containment rule, shown for the near-miss shape: `'update the wiki' in 'update the
  wiki page': True`.

- **Finding C2 — the no-cache refusal has no decision procedure.** B-040-3 refuses a doc
  that "restates what the environment already says (no-cache)", but nothing in the tree
  defines the boundary between "documents a command" and "restates the environment":
  `no-cache` appears in zero `src/` or `tests/` files. The fixture — which does not exist —
  will author the boundary by hand; until then, whether a passage gets refused is the
  reader's judgment, not the spec's.
  Command: `grep -rn "no-cache" src/ tests/ | wc -l`
    ```
    0
    ```

- **Finding C3 — the verification root for "a wiki dir" is unstated.** B-040-1 names the
  homes "README.md, docs/, a wiki dir"; B-040-3 verifies "every named file in the document
  exists in the tree". A wiki is commonly a separate repository with no path into this
  tree; the spec never says which tree a wiki home verifies against, or against what root
  the document's relative file names resolve.
  Command: `sed -n '103,104p' specs/040-ai-docs/spec.md; grep -n "a wiki dir" specs/040-ai-docs/spec.md`
    ```
    `ai-docs`'s procedure verifies before done: every named file in the document exists in the
    tree, no passage restates what the environment already says (no-cache), and each section
    ---
    89:names (README.md, docs/, a wiki dir) and none other without consent; a document it cannot
    ```

### Taken on trust

What is asserted that a reader is asked to take without checking?

- **Finding D1 — "roadmap rows 8/10 folded here" cites rows that are not this surface.**
  The opening line folds roadmap rows 8 and 10 into this spec. Row 8 is
  code-simplifier/refactor (a refactor skill, KISS/DRY/YAGNI) and row 10 is large-codebases
  CLAUDE.md (an onboarding template); neither is the README/wiki/product-docs surface
  B-040-1 builds. The folding claim is not checkable from the roadmap table the spec points
  at.
  Command: `sed -n '197p;199p' specs/037-model-router-and-intake-validation/spec.md`
    ```
    | 8 | code-simplifier/refactor | P2 — skill de refactor KISS/DRY/YAGNI, no hook auto | spec candidata |
    | 10 | large-codebases CLAUDE.md | P2 — template por-área si onboarding | spec candidata |
    ```

- **Finding D2 — "the research classifies claude-agents as adopt-the-pattern-not-the-
  content" is repeated as fact after a sibling challenge marked it UNPROVEN.** 039's
  challenge already checked this exact sentence and recorded
  "### UNPROVEN — the research already classifies claude-agents as
  adopt-the-pattern-not-the-content", with the reason "The research tree never names
  claude-agents". No research file in this tree contains the classification. The spec 040
  restates it as the grounds for D-040-01.
  Command: `sed -n '109,112p' specs/039-documentation-discipline/challenge.md; echo "---"; grep -rln "adopt-the-pattern" .ai/research/ | wc -l`
    ```
    ### UNPROVEN — "the research already classifies claude-agents as adopt-the-pattern-not-the-content"

    Spec: D-039-01 rationale and Decision. The research tree never names claude-agents. The
    closest text is a generic principle about domain content.
    ---
    0
    ```

- **Finding D3 — the `not-covered` exit is cited to 036/039, and neither file contains
  it.** The spec says anything unverifiable "exits `not-covered: <reason>` ... exactly as
  036/039 do". No file under specs/036 or specs/039 contains the word `not-covered`; the
  exit vocabulary the tree actually uses is `INCOMPLETE` (and `FAIL`), so the precedent
  cited for the honest exit does not exist.
  Command: `grep -rn "not-covered" specs/036-validate-adoption-and-close-boundary-delta/ specs/039-documentation-discipline/ | wc -l`
    ```
    0
    ```

- **Finding D4 — the single standard's path does not resolve from the skill's home.** The
  skill's body is told to use `.agents/skills/ai-report/references/documentation-writer.md` (spec 039), and the
  unresolved risk asserts "ai-docs's references point at real files". The file is real only
  at `.agents/skills/ai-report/.agents/skills/ai-report/references/documentation-writer.md`; from
  `.agents/skills/ai-docs/`, the path as written is a 404, and the skill-map instrument
  counts a broken reference rather than forgiving it. The assertion is true only if the
  body writes the cross-skill relative path the spec never writes.
  Command: `test -f .agents/skills/ai-docs/.agents/skills/ai-report/references/documentation-writer.md; echo $?; test -f .agents/skills/ai-report/.agents/skills/ai-report/references/documentation-writer.md; echo $?`
    ```
    1
    0
    ```

### The example nobody wrote

Which example is asserted but not written?

- **Finding E1 — all four receipts run against `tests/test_040_ai_docs.py`, which does not
  exist.** "Success, verified doc", "Denial, no-cache", "Honest exit" and "Routing" each
  promise a `-k <case>` receipt from the same file; the literal Success command exits 4,
  and the other three share the file.
  Command: `uv run --with pytest==9.1.1 pytest -q tests/test_040_ai_docs.py -k verified`
    ```
    no tests ran in 0.00s
    ERROR: file or directory not found: tests/test_040_ai_docs.py

    === exit: 4
    ```

- **Finding E2 — the routing examples cover ai-docs's own corpus only; the four reverse
  routes have no receipt.** All four examples are `-k` cases against the one fixture (four
  of them), while B-040-2's contract is the reverse route added to four skills' corpora —
  each of which already has a `## Routes here` section the harness parses. The fixture case
  in ai-docs's own test file cannot exercise the other four corpora's new routes, and no
  example names them; the routing half that B-040-2 is about is asserted, never demonstrated.
  Command: `grep -c -- "-k " specs/040-ai-docs/spec.md; grep -c "## Routes here" .agents/skills/ai-ship/corpus.md .agents/skills/ai-spec/corpus.md .agents/skills/ai-note/corpus.md .agents/skills/ai-report/corpus.md`
    ```
    4
    .agents/skills/ai-ship/corpus.md:1
    .agents/skills/ai-spec/corpus.md:1
    .agents/skills/ai-note/corpus.md:1
    .agents/skills/ai-report/corpus.md:1
    ```

## Round two — the cross-read, relabelled, and none sees its own

Each lens sees the other four answers, shuffled, and is asked two things: which finding is
a false alarm (and what command shows it), and what did all of us miss. Rankings were not
taken. Refutations carry commands that were run.

### What the cross-read struck through

- ~~**R1 — D2's strong form: "the technical-writer's claimed frontmatter (`model: sonnet`,
  `memory: project`) and its zero STE100 are asserted with nothing checkable".**~~ Refuted
  by the executed record at specs/039-documentation-discipline/challenge.md:187-196, which
  ran the checks against the owner's separate repository: the file exists (12095 bytes),
  carries `model: sonnet` and `memory: project`, and greps empty for STE100. The frontmatter
  claims were verified; what survives is the narrower core D2 already states: the research
  *classification* is UNPROVEN, and 040 repeats it as fact.
  Command: `sed -n '187,196p' specs/039-documentation-discipline/challenge.md`
    ```
    $ ls the owner/repos/claude-agents/product/technical-writer.md
    -rw-r--r--  the owner 12095  the owner/repos/claude-agents/product/technical-writer.md

    $ grep -n "model:\|tools:\|memory:" the owner/repos/claude-agents/product/technical-writer.md
    model: sonnet
    tools: Write, Read, Edit, Grep, Glob, WebSearch
    memory: project

    $ grep -n "STE100\|Simplified Technical English" the owner/repos/claude-agents/product/technical-writer.md
    (no output)
    ```

- ~~**R2 — C2's strong form: "the no-cache refusal has no decision procedure, so nothing
  can ever be refused".**~~ Refuted by the standard's own completion-criterion machinery:
  `.agents/skills/ai-report/references/documentation-writer.md` requires every step to end on a condition that is
  "checkable and exhaustive", and hand-authored fixture cases are exactly how the framework
  pins judgment boundaries — the 037 and 038 fixtures did this. What survives is the
  narrower core: the boundary between "documents a command" and "restates the environment"
  is never written down; the fixture authors it silently.
  Command: `sed -n '23,25p' .agents/skills/ai-report/.agents/skills/ai-report/references/documentation-writer.md`
    ```
    4. **Completion criterion** — every step ends on a condition that is *checkable and
       exhaustive*. A vague bound ("understanding reached") invites premature completion:
       sharpen the bound first; hide later steps only across a real context boundary.
    ```

### What the cross-read caught

The misses, written down so the count can be recomputed rather than believed (listed under
their own heading below). Two of them — the absorbed skill name and the schema-shaped
capability — were found only because the four corpora, the contract suite, spec 010 and the
manifest schema were read alongside the spec; none of the five single-lens reads opened
those files.

## Round three — the chairman wrote this

Nobody here knows which lens said what. This is new text, not a ranking.

**What the lenses agree on.** The need is real and measured: seventeen skills ship in
`.agents/skills/`, none owns README, wiki or product documentation; `ai-report`'s own corpus
refuses everything but its one draft — "there is no field for a log or a diff"; and the 039
standard exists (`.agents/skills/ai-report/references/documentation-writer.md` beside ai-report), carrying the
context pointer, the two loads, leading words, pruning, completion criteria and STE100. The
chosen shape — one skill reusing that standard, one capability entry, routing refusals, one
fixture — is the right size, and declining to port the claude-agents agent is supported:
its frontmatter was executed and verified by 039's challenge (`model: sonnet`,
`memory: project`, no STE100). The `not-covered` honest exit points the right way: refuse
rather than print a false green.

**Where they clash.** Whether the change costs "one skill directory + one capability entry"
or is a promise over three nonexistent objects whose single standard's path does not
resolve from the skill's home. Whether the four reverse routes land green or red: "the
routing harness sees distinct cases, never a fork" is asserted, while the harness's fork
rule reds an identical case six times and its containment rule reds near-misses. Whether
the honest exit has precedent ("exactly as 036/039 do") or invents its vocabulary. And
whether the verification of a finished document is a check with a second reader or a
procedure the writing model follows once and nothing reads again.

**Blind spots the cross-read caught.** Only by reading the findings together did these
surface: `ai-docs` is a name the framework has already tried and recorded as absorbed —
spec 010's table lists it among the nineteen absorbed skills, and `tests/test_contracts.py`'s
EP-344 record pins "a docs lens in ai-review and docs tasks in ai-ship, and the lens was the
empty half" — yet the spec resurrects the exact name and its rebuttal answers ai-report,
never that record. The roadmap anchor (rows 8/10) repeats a citation an earlier council
already flagged, and the research classification a sibling challenge marked UNPROVEN is
repeated here as fact. The capability entry, priced as a one-liner, omits two of the nine
mode fields the manifest schema requires and every existing capability carries. And the
exit the whole honest half of the spec leans on is a vocabulary the tree has never seen.

**Verdict.** The direction — a checked, routed home for the one writing kind the framework
does not govern — is right, and declining to port the vendor agent is backed by evidence.
But the spec is written over three artifacts that do not exist (skill, fixture, capability),
names its single standard at a path that does not resolve from the skill's home, resurrects
a skill name the framework recorded as absorbed, cites a roadmap anchor and a research
classification that do not support it, and proposes a capability entry that does not meet
the manifest schema. The verification it promises for finished documents has no second
reader. Nothing here grants anything.

**Recommendation.** Before signing, land the skill directory, its corpus and
`tests/test_040_ai_docs.py` together, with the capability entry filled to all nine schema
fields (`enforcement` and `proof_requirements` included) and the 039 standard referenced at
the path that resolves (`../ai-report/.agents/skills/ai-report/references/documentation-writer.md`); word the four
reverse routes distinctly and run them through `tests/skill_eval.py`'s fork and containment
rules before landing; address the absorbed-name record, either acknowledging the lineage or
choosing a fresh name; correct or drop the rows 8/10 anchor and the research classification;
and define the `not-covered` exit against the existing `INCOMPLETE` vocabulary rather than
citing 036/039.

**One first step.** Write `.agents/skills/ai-docs/SKILL.md` and its corpus with the
standard referenced at the path that resolves, then `tests/test_040_ai_docs.py` carrying
the three states, and run `tests/skill_eval.py` against four distinctly-worded reverse
routes before touching `policy/capabilities.toml`.

The three sections below are the only ones a script reads. Their bullet counts must equal
the two totals stated at the bottom; the counts were recomputed rather than believed.

### Gaps no single lens named

- **M1 — `ai-docs` is a recorded absorbed skill name, and the spec resurrects it without
  a word about the record.** No single lens read spec 010 or the contract suite. Spec 010's
  absorption table lists `ai-docs` among the nineteen skills absorbed "into target skill or
  deterministic code", and `tests/test_contracts.py`'s EP-344 pins record what became of
  it: "`ai-docs` was absorbed as 'a docs lens in ai-review and docs tasks in ai-ship', and
  the lens was the empty half". This spec proposes a fresh skill under the exact absorbed
  name, and its "Challenged once" rebuttal answers ai-report while never answering the
  framework's own prior absorption of the docs skill. The cost lens priced a new directory;
  the example lens saw only the missing fixture; nobody saw the name was already tried and
  recorded dead.
  Command: `grep -n "ai-docs" specs/010-governed-agentic-engineering-foundation/spec.md tests/test_contracts.py`
    ```
    414:| Absorb into target skill or deterministic code (19) | `ai-advise`, `ai-brainstorm`, `ai-commit`, `ai-constitution`, `ai-docs`, `ai-explain`, `ai-governance`, `ai-ide-audit`, `ai-learn`, `ai-mcp-audit`, `ai-onboard`, `ai-pipeline`, `ai-pr`, `ai-reliability-eval`, `ai-resolve-conflicts`, `ai-simplify`, `ai-spec-draft`, `ai-start`, `ai-visual` |
    tests/test_contracts.py:1335:    # Two more absorptions that named two homes each and filled one. `ai-docs` was absorbed as
    ```
  Command: `sed -n '1336,1337p' tests/test_contracts.py`
    ```
        # "a docs lens in ai-review and docs tasks in ai-ship", and the lens was the empty half.
        # `ai-resolve-conflicts` as "resolution by intent belongs to ai-ship and ai-debug", and
    ```

- **M2 — the capability entry is under-specified against the manifest schema.** The
  manifest's mode object requires `id`, `read_roots`, `write_roots`, `exec_allowlist`,
  `network`, `secrets`, `human_gate`, `enforcement` and `proof_requirements`; the spec's
  "(read the repo, write `docs/` + `README.md`, `before_write`)" names three of the nine.
  All nineteen existing capabilities carry both `enforcement` and `proof_requirements`
  (twenty-five of each — one per mode), so an entry built from the description alone would
  be the first that fails the schema. No lens opened the schema; the cost lens priced the
  entry as a one-liner.
  Command: `python3 -c "import json; s=json.load(open('policy/capability-manifest.schema.json')); print(s['\$defs']['mode']['required'])"; grep -c "^\[\[capabilities\]\]" policy/capabilities.toml; grep -c "enforcement = " policy/capabilities.toml`
    ```
    ['id', 'read_roots', 'write_roots', 'exec_allowlist', 'network', 'secrets', 'human_gate', 'enforcement', 'proof_requirements']
    19
    25
    ```

- **M3 — the honest exit's vocabulary is invented in the same commit that claims it.** The
  `not-covered` exit is cited to 036/039, which contain the word nowhere, while the tree's
  actual exit vocabulary is `FAIL` and `INCOMPLETE` (CONSTITUTION.md). The example lens saw
  only a missing file; the taken-on-trust lens saw only the false citation; the synthesis is
  that even the exit's shape is unestablished — the fixture's `-k not_covered` case will
  define the vocabulary by fiat as it writes it, which is exactly the "receipt promises a
  vocabulary that must be invented" pattern the small print forbids.
  Command: `grep -n "INCOMPLETE\|FAIL" CONSTITUTION.md | head -2`
    ```
    57:`FAIL`, `INCOMPLETE` and missing authority block; prose, metadata or a reviewer's
    ```

- **M4 — the finished document has no second reader.** B-040-3's verification is performed
  by the skill's own procedure — the model following skill text, at write time. The only
  verifier-shaped instrument in the tree, `ai-verify`, walks a spec's examples against real
  commands; it does not read finished documents. The fixture proves the skill's procedure
  on a synthetic document, and nothing reads the written README again. The cost lens saw
  "no new machinery" as a virtue; the reversibility lens saw the ageing snapshot; the
  synthesis is that the machinery-free verification is precisely a procedure, unmeasured,
  which is the "checked, or it rots" failure the spec's own problem section names.
  Command: `sed -n '4,5p' .agents/skills/ai-verify/SKILL.md`
    ```
      Runs the gate and the security lane and ticks each production-ready box beside the command
      that ticked it, or walks a spec's examples and marks each one against a real command.
    ```

### Findings cut for carrying no command

- **Cut1 — "a post is never refused for being a post" (the second challenge answer) is a
  statement of intent about what the skill will do, not a gap a command can show.** A claim
  about the refusal's philosophy, with no artifact to run; cut in round one.
- **Cut2 — "`docs/tools.md` (the human inventory) is updated by this spec's build" names a
  file that exists; whether it gains an ai-docs row is a build sequencing choice, not a gap
  a command can demonstrate.** A scheduling claim about a present file; cut.

### Findings the cross-read refuted, with the command that refuted them

- ~~**R1 — D2's strong form: "the technical-writer's claimed frontmatter (`model: sonnet`,
  `memory: project`) and its zero STE100 are asserted with nothing checkable".**~~ — refuted
  by `sed -n '187,196p' specs/039-documentation-discipline/challenge.md`, which shows the
  executed verification against the owner's separate repository: the file exists (12095
  bytes), carries `model: sonnet` and `memory: project`, and greps empty for STE100 — so the
  frontmatter claims were checked; the surviving core is that the research classification is
  UNPROVEN and 040 repeats it as fact.
    ```
    $ ls the owner/repos/claude-agents/product/technical-writer.md
    -rw-r--r--  the owner 12095  the owner/repos/claude-agents/product/technical-writer.md

    $ grep -n "model:\|tools:\|memory:" the owner/repos/claude-agents/product/technical-writer.md
    model: sonnet
    tools: Write, Read, Edit, Grep, Glob, WebSearch
    memory: project

    $ grep -n "STE100\|Simplified Technical English" the owner/repos/claude-agents/product/technical-writer.md
    (no output)
    ```

- ~~**R2 — C2's strong form: "the no-cache refusal has no decision procedure, so nothing
  can ever be refused".**~~ — refuted by
  `sed -n '23,25p' .agents/skills/ai-report/.agents/skills/ai-report/references/documentation-writer.md`, which shows
  the standard's completion-criterion machinery ("every step ends on a condition that is
  checkable and exhaustive") — the checkable-section rule is the procedure the refusal sits
  on, and the framework pins judgment boundaries with hand-authored fixture cases (the 037
  and 038 fixtures did this); the surviving core is that the boundary between "documents a
  command" and "restates the environment" is never written down and the fixture authors it
  silently.
    ```
    4. **Completion criterion** — every step ends on a condition that is *checkable and
       exhaustive*. A vague bound ("understanding reached") invites premature completion:
       sharpen the bound first; hide later steps only across a real context boundary.
    ```

## The two counts

- Gaps that appeared only after the cross-read: **4**
- Findings deleted, for carrying no command or for being refuted: **4**