# What `check` means here. CI never learns a language: it runs `just check`.
# Tools are pinned at the call site: this project declares no dependencies, so an
# unpinned `uv run ruff` resolves from a .venv somebody happened to build, which is why
# CI could never have run this file.

ruff := "ruff==0.16.2"
pytest := "pytest==9.1.1"
semgrep := "semgrep==1.172.0"
# The two engines that are not installed by `uv run --with`, and therefore the two that
# could be any version the machine happens to carry. CI downloads exactly these releases;
# `security` below asks each one what it is before it trusts what it says, because a
# scanner whose version we did not test is a scanner whose answer we cannot read — a local
# green from an older engine, or a local red CI cannot reproduce. A test holds these equal
# to the workflow's own pins, so drift on either side turns the build red naming the engine.
gitleaks_version := "8.30.1"
trivy_version := "0.74.0"
coverage := "coverage==7.15.4"
# `sm` (skill-map.ai) is the same kind of pin as gitleaks and trivy above: a binary this
# project does not install, whose version the machine may carry differently. Spec 026 makes
# it the reference-integrity instrument; `map` below asks it what it is before trusting it.
sm := "1.12.2"
# The suite runs across the machine's cores. Measured on this tree: 158.89 s serial against
# 61.80-66.05 s at the detected count over three runs, the same passed/skipped/failed counts,
# and a coverage total that does not move. Never a literal above the core count — sixteen
# workers on eight cores produced two failures nobody could name, and buying ten seconds with
# a gate people learn to rerun is the trade this repository already refused once for the
# latency bound.
#
# The `psutil` extra is what makes that rule true rather than intended. Without it `auto`
# counts logical CPUs, so on any machine with SMT it starts exactly the sixteen-on-eight
# configuration the sentence above says produced failures nobody could name — and the machine
# that measured this has no SMT, so it could never have noticed. A reviewer found it by
# reading xdist's own resolver instead of our comment.
xdist := "pytest-xdist[psutil]==3.8.0"
# The same pin the workflow carries, and a test holds the two equal.
mypy := "mypy==2.3.0"

build:
    uv build

# The SBOM beside the wheel, from the wheel. `EP-047` and `EP-280` were filed under "no
# local work can move this" because they name a published release — and the published half
# does. This is the other half: a document exists, it is well formed, and it names the same
# bytes `uv build` just wrote. It runs inside `just check` because an emitter nothing runs
# is the defect this repository is named after, and it costs nothing: `build` ran already.
sbom: build
    uv run python -m ai_engineering.sbom dist/*.whl

lint:
    uv run --with {{ruff}} ruff check .
    uv run --with {{ruff}} ruff format --check .

# The one shipped file no Python tool can read. `ai-eng init` writes surfaces/opencode.ts
# into the user's OpenCode plugin directory as text with three paths filled in, so until
# this recipe existed nothing in this repository had ever compiled it — and OpenCode drops
# a plugin it cannot load with no error, no warning and no log. A typo in it therefore
# failed on a stranger's machine, silently, and enforcement stopped there.
# The versions are pinned in package.json for the same reason every other tool here is
# pinned at its call site. The modules land at the root and never under surfaces/, because
# `surfaces` is force-included into the wheel and a node_modules there would ship to PyPI.
typecheck:
    # Python first, and here rather than only in CI. `AGENTS.md` says this file is what CI
    # runs; for the whole life of this branch it was not, because mypy existed in the
    # workflow alone — so the local gate went green over 45 type errors and the first
    # anybody could know was the first time the branch reached CI, 253 commits in.
    uv run --no-project --python 3.11 --with {{mypy}} \
        --with "rich>=13.0,<16.0" --with "questionary>=2.0,<3.0" mypy src hooks
    npm install --silent --no-audit --no-fund
    npm exec -- tsc --noEmit
    # Compiling it proves it parses. This runs it: the plugin's own deny path, driven the
    # way OpenCode drives it, once with a working dispatcher and once with none. The second
    # is the case spec 010 wrote down twice and left open — a guard that allows because it
    # could not run.
    #
    # Here rather than in `test`, because this is the recipe that owns the TypeScript
    # surface and the one place node is guaranteed. AI_ENG_REQUIRE_NODE turns that suite's
    # skip into a failure: a runner whose node cannot strip types would otherwise skip
    # silently, and a proof that stops running without saying so is worth less than no
    # proof, because it still reads green.
    AI_ENG_REQUIRE_NODE=1 uv run --with {{pytest}} pytest -q tests/test_opencode_plugin.py
    # And the receipt, because the suite above proves the behaviour and cannot prove that a
    # denial happened on *this* machine. Until this line, the only executed denial receipt in
    # the tree came out of `install-matrix.yml`, so the one surface `report surfaces` could
    # read as proven was the one CI happened to prove — every other row read unproven whether
    # or not it was provable. This one is, and its adapter is a plugin we ship.
    #
    # It refuses rather than writing when the plugin does not deny or does not name the guard
    # that decided, so a green here is a denial and not a file.
    uv run python tests/surface_receipt.py opencode

# The whole suite runs once, under coverage, in `cover`. What runs here is the part that
# cannot: coverage instrumentation moves a latency measurement, so the guards' start-up
# bound is deselected there and measured here, uninstrumented, which is the only way the
# number means anything. Running the other 2,228 a second time bought a coverage total that
# `cover` already prints, at about two minutes of every gate — and a gate people wait six
# minutes for is a gate people learn to run less often, which is how a check stops being a
# check without anybody deciding to remove it.
test:
    uv run --with {{pytest}} --with {{xdist}} pytest -q -n auto -k "fast_enough"

security:
    @test "$(gitleaks version)" = "{{gitleaks_version}}" || { echo "gitleaks is $(gitleaks version) and this gate is written for {{gitleaks_version}}. An untested scanner's answer is not evidence."; exit 1; }
    @trivy --version | head -1 | grep -qx "Version: {{trivy_version}}" || { echo "trivy is not {{trivy_version}}. An untested scanner's answer is not evidence."; exit 1; }
    # Through the lane contract rather than as three bare commands: a missing engine, missing
    # rules, a crash, a timeout or zero inputs each read as INCOMPLETE, and INCOMPLETE fails
    # this gate exactly as a finding does. Three bare commands could not tell those apart.
    uv run --with {{semgrep}} python -c "import sys; from pathlib import Path; from ai_engineering import scan; sys.exit(scan.baseline(Path('.')))"

# Its own recipe, and not folded into `test`: instrumenting the interpreter adds startup
# cost to every subprocess, and the dispatcher latency assertion is a security property
# measured in milliseconds. Deselecting it here is the only relaxation allowed — moving
# the floor down instead is the thing this recipe exists to make impossible.
# The floor is 80, which is the number the operator asked for. Measured today is 86, so
# there are six points of slack and that is deliberate: this gate answers "did we keep
# the promise", and a floor pinned to today's measurement answers "did anything move",
# which is the ceiling's job and not this one.
cover:
    #!/usr/bin/env bash
    set -euo pipefail
    export COVERAGE_FILE="$PWD/.coverage"
    # Clean both ends so a red run does not leave the parallel data-files behind: they are
    # consumed by combine, and a run that dies before the find has no right to litter 139
    # one-run files on the machine. EXIT keeps it true whether cover green, red or killed.
    trap 'find . -maxdepth 1 -name ".coverage.*" -delete' EXIT
    rm -f "$COVERAGE_FILE"*
    uv run --with {{coverage}} --with {{pytest}} --with {{xdist}} coverage run --parallel -m pytest -q -n auto -k "not fast_enough"
    # The count this gate owes anti_theatre. `cover` is the only full pass now, so the line
    # comes from the run that happened rather than from a second one bought to print it.
    uv run --with {{coverage}} coverage run --parallel tests/adversarial/run.py
    uv run --with {{coverage}} coverage combine
    # The parallel data-files are consumed by combine; the EXIT trap removes any that remain,
    # so keep only the combined .coverage the report below reads.
    uv run --with {{coverage}} coverage report --fail-under=80

# Coverage says a line ran. It never says anything would have noticed the line being
# wrong, and this repository has the receipt: a guard measured at 89% whose only rule had
# never fired. So the number that means something is how many deliberate defects the suite
# catches, and it is a number, so it is a script.
#
# Sixteen deliberate defects: eleven in the four guards that decide whether an action is
# allowed, five in the verbs that write the record. This used to say "it points at the
# guards and nowhere else", which was five rows short of true — the sentence outlived the
# table, which is the defect class `docs/adr/0014` is about, in the recipe whose whole job
# is catching it. A test now reads `chain.TABLE` and fails if a blocking guard has no row,
# so the aim is asserted rather than described.
#
# A floor of 89 across the whole tree was never once met — the last recorded run read 78 —
# and its rows named no security guard at all, so the most expensive instrument in the
# repository was aimed at the least dangerous code. The floor here is 100 over a surface
# small enough to mean it, and a single survivor fails.
#
# Not in `check`, and in CI as its own job: 6 min 07 s for all sixteen rows against the
# gate's 20-minute budget. The halves are in cost order and stop at the first red, which is
# where that number comes from — eleven rows are settled by `tests/test_hooks.py` in under
# two seconds each, and the whole suite only runs for a row nothing cheaper caught.
guards *filter:
    uv run --with {{pytest}} python tests/mutation.py {{ if filter != "" { "-k " + filter } else { "" } }}

# The counts come from the tools themselves: a file list prints the same number whether
# the linter ran or was replaced by `true`, which is the theatre this contract catches.
# So each number is one a tool can only print by having read the files it counts.
counts:
    @echo "RAN lint=$(uv run --with {{ruff}} ruff format --check . | grep -oE '^[0-9]+')"
    @echo "RAN tests=$(uv run --with {{pytest}} pytest -q --collect-only 2>/dev/null | grep -cE '::')"

# The page a person reads, and the one control that keeps it worth reading. It reports and
# writes nothing: a gate that regenerated the document it was about to check would find it
# fresh every time and assert nothing at all. Before `ran`, because that recipe writes the
# receipt last and a check after it would record a run that had not finished.
intent-page:
    @uv run python -m ai_engineering.solution_intent --check

# The thirteen indicators and the fourteen prohibitions, read out of `policy/` and printed
# with every row that has no instrument named. Inside `check` and not beside it: the reader
# refuses a P5 completion claim, and a refusal nobody runs is a refusal that never happens.
register:
    @uv run python tests/pilot_register.py

# The routing evaluation over the skill corpus. `ai-reliability-eval` was absorbed with the
# instruction to become a CI harness, because an evaluation that always decides the same way
# is code and not a prompt — and until this recipe existed, `check` evaluated a skill's
# format and nothing about what it routes. It prints what it did not measure, because a
# green from something named evaluation reads as an evaluation of the writing.
skilleval:
    @uv run python tests/skill_eval.py

# The review-skills evaluation (spec 029 B-029-1): plant a graded defect pack outside the
# tree, run each review skill's reporter, and report recall/precision over the three tiers
# (gimmes, near-misses, traps) with a clean control that must stay quiet. A skill reporting
# nothing on a non-empty pack, or firing on clean code or a trap, is a FAIL. Its own checks
# are tests/test_evals_harness.py.
evals:
    @uv run python tests/evals/score.py

# Where things stand, from the tree, with no model doing the arithmetic. Not in `check`:
# it asserts nothing and a report inside a gate is a report people read as a gate.
stats:
    @uv run python tests/stats.py

# The two numbers `EP-195` asked for, recomputed rather than read back. `docs/adr/0019` closes
# by saying no benchmark defines the improvement a council shows; this is the instrument, and it
# is a script because a model printing its own score is what rule 11 refuses. It counts the
# entries under the round-two headings itself and refuses when its count and the run's stated
# total disagree — which is the only lie this can catch and the one worth catching. Before
# `ran`, because that recipe writes the receipt last.
council:
    @uv run python tests/council_counts.py

# The last step, and the only one that leaves anything behind. Everything above is an
# ephemeral process writing ignored receipts, which is why `PO-10` and `PO-14` — did the
# removed practices stay removed, and did each commit run its module's suite — were both
# graded on no evidence at all. A commit trailer is the one place a run can be recorded
# where git will still have it a month later, and `commit-msg` writes it from this receipt
# only when the content it names is the content being committed.
ran suite="check" base="main":
    @uv run python tests/ran_receipt.py record {{suite}}
    # And the answer nobody was reading. The trailer's absence is the whole of its value, and
    # on 2026-08-19 it correctly marked a commit pushed over a red gate while nothing printed
    # it. A control whose answer nobody consumes is the same defect as one that cannot decide.
    @uv run python tests/ran_receipt.py unrun {{base}}

# The cheap half, and the one `PO-14` actually asks for. That row says every commit runs its
# module's immediate suite *instead of* the whole gate, and until this recipe existed the
# only thing that recorded anything was `check` — so every trailer named the gate, which is
# the practice the row says was removed. One module, its own suite, its own receipt.
#
# It records only on a pass. `set -e` is not enough here: the recipe would still reach the
# record line under a shell that continued, and a receipt written after a red suite is worse
# than none, because the trailer then says a suite ran over these bytes and passed.
quick module:
    @uv run --with {{pytest}} pytest -q tests/test_{{module}}.py
    @uv run python tests/ran_receipt.py record quick:{{module}}

# Which review lens this range routes to. In `check` because the table is only worth having
# if something reads it — the reader refuses a lens file with no row, which is the state all
# ten were in until `EP-251` was measured, and a table nothing validates drifts from the
# directory it describes on the first lens somebody adds.
lenses base="main":
    @uv run python tests/review_lenses.py --base {{base}}

# Which commits no closed block review covers, derived rather than written — the approved
# plan forbids a commit message or metadata field from carrying that word. It reports and
# never blocks: unreviewed is the ordinary state of work in flight, and a gate that failed on
# it would demand a review before the block it belongs to has closed, which is the
# amplification the block cadence exists to remove.
unreviewed base="main":
    @uv run python tests/unreviewed.py --since {{base}}

homes base="main":
    @uv run python tests/one_home.py --since {{base}}

# The reference-integrity instrument (spec 026). `sm scan` feeds the digest in
# `src/ai_engineering/skillmap.py`; `map` is where the gate meets it. Every other external
# engine here is version-checked before it is trusted; same rule: ask `sm` what it is first,
# because a map from an engine whose findings shape we did not test is a map whose green is
# an assertion. A machine with no `sm` (a stranger install of the wheel) is bracketed the
# same way the security engines are: print the gap and stay green, because the instrument is
# the maintainer's habit and not a dependency the stranger must carry.
map:
    @if ! command -v sm >/dev/null 2>&1; then \
        echo "map not exercised; sm missing"; exit 0; fi
    @test "$(sm --version)" = "{{sm}}" || { echo "sm is $(sm --version) and this gate is written for {{sm}}. An untested map engine's answer is not evidence."; exit 1; }
    # `sm scan` reports every issue in the tree — the accepted references and the declared
    # template holes included — so its exit code can never be green here. The scan is only
    # the sidecar-DB refresh; the gate is the digest below, which re-runs `sm check --json`
    # and subtracts the accepted set and the template holes before it decides.
    -sm scan
    uv run python -m ai_engineering.skillmap
check: build sbom lint typecheck test cover security register skilleval evals counts intent-page lenses council map ran
