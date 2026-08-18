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
trivy_version := "0.73.0"
coverage := "coverage==7.15.4"
mutmut := "mutmut==3.7.0"
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

test:
    uv run --with {{pytest}} pytest -q

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
# The floor is 80, which is the number the operator asked for. Measured today is 95, so
# there are fifteen points of slack and that is deliberate: this gate answers "did we keep
# the promise", and a floor pinned to today's measurement answers "did anything move",
# which is the ceiling's job and not this one.
cover:
    #!/usr/bin/env bash
    set -euo pipefail
    export COVERAGE_FILE="$PWD/.coverage"
    rm -f "$COVERAGE_FILE"*
    uv run --with {{coverage}} --with {{pytest}} coverage run --parallel -m pytest -q -k "not fast_enough"
    uv run --with {{coverage}} coverage run --parallel tests/adversarial/run.py
    uv run --with {{coverage}} coverage combine
    uv run --with {{coverage}} coverage report --fail-under=80

# Coverage says a line ran. It never says anything would have noticed the line being
# wrong, and this repository has the receipt: a guard measured at 89% whose only rule had
# never fired. So the number that means something is how many deliberate defects the suite
# catches, and it is a number, so it is a script.
#
# `mutmut run` exits 0 whether or not a mutant lived — measured, 1,306 survivors and exit
# zero — so the run is not the gate; the stats file is. Two halves because one tool cannot
# reach both: mutmut mutates the package, tests/mutation.py mutates the guards, which
# mutmut cannot import without making hooks/ a package.
#
# `just mutate` is everything and is what the pull request runs. `just mutate <file>...`
# is the same two halves over the files you name, and that is the whole of the local
# saving: one module is 12 seconds against ten minutes for the tree, measured today.
mutate *paths:
    #!/usr/bin/env bash
    set -euo pipefail
    here="$PWD"
    # A file is not a filter. mutmut names every mutant after the module path it imports
    # under, so src/ai_engineering/accept.py is `ai_engineering.accept.*` — and the `.*`
    # is not decoration, a bare prefix raises "nothing matches" and mutates nothing.
    scoped=""; globs=""; guards=""
    for p in {{paths}}; do
        scoped=1
        case "$p" in src/*.py) g="${p#src/}"; g="${g%.py}"; globs="$globs ${g//\//.}.*" ;; esac
        # The guards half is hand-written rows, not an engine, so a file has mutants
        # there only if a row names it — and handed a file no row names it prints
        # "14 of 14 killed" over a run that mutated nothing. So ask the file itself.
        grep -qF "\"$p\"" tests/mutation.py && guards="$guards $p" || true
    done
    if [ -z "$scoped" ] || [ -n "$globs" ]; then
        # Outside the working copy, and this is not tidiness. mutmut puts its sandbox in
        # ./mutants, which is inside the repository, so `repo_root()` walks up out of the
        # sandbox and finds the real .git — and `init` then rewrites the developer's own
        # justfile and leaves timestamped backups beside it. Measured: it happened three
        # times in one run before this line existed. A test tool that can edit the tree it
        # is judging is the failure this product exists to cure, wearing a lab coat.
        # A disposable checkout is not isolation. A scoped run over init and wiring reached
        # the global installer from inside a mutant and wrote Claude Code and Copilot hook
        # entries naming this run's temporary interpreter and its temporary dispatcher. The
        # sandbox was then deleted, and every Read, Edit and Bash call in the next session
        # tried hooks at paths that no longer existed, printed a non-blocking error and ran
        # no guard at all. So the worker gets a home of its own as well as a tree of its
        # own, before Python imports anything, and the four watched files are hashed either
        # side of the run: "the sandbox was temporary" is exactly what was believed the last
        # time one escaped. uv's cache is read from the real home first and kept, or every
        # run re-downloads an interpreter into a directory it is about to delete.
        real="$HOME"
        away="$(mktemp -d)"
        house="$(mktemp -d)"
        trap 'rm -rf "$away" "$house"' EXIT
        watched="$real/.claude/settings.json $real/.copilot/hooks/ai-eng.json"
        watched="$watched $real/.cursor/hooks.json $real/.codex/hooks.json"
        before="$(cksum $watched 2>/dev/null || true)"
        export UV_CACHE_DIR="${UV_CACHE_DIR:-$(uv cache dir)}"
        export HOME="$house" USERPROFILE="$house" AI_ENGINEERING_HOME="$house/.ai-engineering"
        # One test spawns child processes that import the package. Inside the sandbox that
        # import resolves to the instrumented copy, whose shim then looks for mutmut's
        # config relative to the child's working directory — a throwaway repository that
        # has none — and the baseline died there, so the whole gate collected nothing.
        # The children read the real tree instead. It costs that one test its reach over
        # mutants in spec.py, which is a trade worth making against a gate that is dead.
        export AI_ENG_REAL_SRC="$here/src"
        export XDG_CONFIG_HOME="$house/.config" XDG_DATA_HOME="$house/.local/share"
        rsync -a --exclude=.git --exclude=.venv --exclude=dist --exclude=mutants \
              --exclude=.pytest_cache --exclude=.ruff_cache ./ "$away/"
        cd "$away"
        set -f  # $globs holds `module.*`; unset, the shell tries to expand it as a path
        uv run --no-project --with {{mutmut}} --with {{pytest}} mutmut run $globs
        set +f
        uv run --no-project --with {{mutmut}} --with {{pytest}} mutmut export-cicd-stats
        # Out of the sandbox before the trap deletes it. Without this the run reports a
        # score and destroys the only record of which mutants lived, so "which ones
        # survived" costs another full run to ask — measured, it cost several.
        cp mutants/mutmut-cicd-stats.json "$here/mutants-stats.json" 2>/dev/null || true
        # The score says how much is unproven; only the names say what. The stats file
        # carries counts alone, so the list comes out beside it or the next person pays
        # another full run to learn which defects nobody would notice.
        uv run --no-project --with {{mutmut}} --with {{pytest}} mutmut results \
            > "$here/mutants-survivors.txt" 2>/dev/null || true
        # Before the score, never after it: an escape has to be reported even on the
        # run that was going to fail for its own reasons.
        if [ "$before" != "$(cksum $watched 2>/dev/null || true)" ]; then
            echo "mutation: a mutant changed a real surface settings file. The run is not" >&2
            echo "isolated, and every mutant it killed is beside the point." >&2
            exit 1
        fi
        # The heredoc body sits at the recipe's indentation and not this block's: `just`
        # strips one level, and anything deeper reaches python as an IndentationError.
        uv run --no-project python - "$scoped" <<'PY'
    import json, sys
    # Raised rather than lowered, on 2026-08-17, and by the owner: "es importante que los tests
    # sean buenos, si vemos que no pasan entonces tenemos que mejorar los tests". First pass
    # measured — scan 67 to 80, spec 67 to 74, uninstall 78 to 81, update 60 to 63, the last of
    # which had no test file at all. Almost every survivor was a sentence a person reads when
    # something refuses, not a branch: the fixtures asserted the machine code and never the
    # words, so a cure could be rewritten into nonsense and nothing noticed. Refusals are pinned
    # whole now and whole output blocks are compared.
    #
    # 89 is a target and not a measurement, and this comment used to say the opposite. It
    # read "89 is what landed, closed at the measurement with no margin... every other module
    # is between 93% and 98%", and `.github/workflows/mutation-nightly.yml` says in its own
    # header that "the standing whole-tree score is 71% against a floor of 89" and names
    # roughly 3,700 mutants as the distance. Two files of ours, one number, and they
    # disagreed. Measured on 2026-08-17 to settle it: `scan.py` alone scores 67%, `spec.py`
    # 67%, and the five modules one branch changed 74% together — consistent with 71 across
    # the tree and not with 93-98 a module. The nightly's number is the true one.
    #
    # What that means for this floor, said out loud because the arithmetic is not obvious:
    # nothing has met it. A scoped run of any real diff fails here, a diff too wide for the
    # scoped lane defers to a whole-tree receipt that only has to have *finished*, and the
    # nightly is deliberately not a required check. So a branch touching seven modules is
    # waved through and a branch touching six is refused — which is the shape `check.yml`'s
    # own comment calls "a gate you can escape by touching more files". Recorded here rather
    # than repaired by lowering the number: what the floor should be for a subset is a
    # decision, and lowering a floor to go green is the defect this repository is named for.
    #
    # The published guidance is 70-80% in general and 80%+ on the core, so 89 across the
    # package is already past both. The core here is not a layer of this package at all —
    # it is hooks/, the five guards that decide whether an action is allowed — and mutmut
    # cannot reach it, so its number comes from tests/mutation.py below. That number is a
    # checklist of fourteen hand-written rows and not a score over every possible mutant,
    # and calling it 100% would be the kind of green this product exists to refuse.
    FLOOR = 89
    scoped = bool(sys.argv[1])
    s = json.load(open("mutants/mutmut-cicd-stats.json"))
    # `total` counts every mutant in the tree even when you asked for one module —
    # measured, 3,199 against the 276 that ran — so a scoped run divided by it scores
    # 5% and fails for arithmetic reasons. The denominator is the mutants that ran.
    ran = s["killed"] + s["survived"] if scoped else s["total"]
    score = round(100 * s["killed"] / ran) if ran else 0
    # RAN is the word tests/anti_theatre.py reads as proof a gate ran over everything.
    # A partial run must not be able to write it, or one mutated file stands in for all.
    # It gets its own line with nothing after the number: that reader anchors the pattern
    # to the end of the line, so a count with detail trailing it matched nothing at all
    # and the proof this recipe thought it was writing was never readable.
    head = "PARTIAL" if scoped else "RAN"
    print(f"  killed={s['killed']}  survived={s['survived']}  {score}%")
    print(f"{head} mutants={ran}")
    if score < FLOOR:
        sys.exit(f"mutation: {score}% of deliberate defects caught, under {FLOOR}%.")
    PY
    fi
    # The guards, back in the real tree, because their suite builds git repositories and
    # the line-ceiling test counts with `git ls-files`, neither of which a copy can answer.
    # This half edits the tree on purpose and restores each file in a finally, then checks
    # the sha256 matches before moving on — that is the difference between the two halves.
    cd "$here"
    if [ -z "$scoped" ]; then
        uv run --with {{pytest}} python tests/mutation.py
    else
        for p in $guards; do uv run --with {{pytest}} python tests/mutation.py -k "$p"; done
    fi
    [ -n "$scoped" ] && [ -z "$globs$guards" ] &&
        echo "mutate: nothing in '{{paths}}' has mutants, so nothing was measured." >&2 || true

# Locally, only what this session changed. On the pull request, everything: the workflow
# runs `just check` and `just mutate` whole, and neither of them learned a flag here.
#
# Mutation is the only thing this makes cheaper, because it is the only expensive thing.
# The suite stays whole: 540 tests in 6.3 seconds, measured. A changed-file-to-test map
# would save four of those seconds and would be wrong the first time somebody renamed a
# module — and a wrong map does not fail, it skips, quietly, which is the whole disease.
changed:
    #!/usr/bin/env bash
    set -euo pipefail
    # The same three questions hooks/change_scope_guard.py asks, in the same order and with the
    # same fallbacks: the branch against its merge base, the dirty tree, the untracked
    # files. Two controls that disagree about what a change is are one control and a bug.
    ref="$(git symbolic-ref --quiet refs/remotes/origin/HEAD || true)"
    head="${ref##*/}"; head="${head:-main}"
    base="$(git merge-base HEAD "$head" 2>/dev/null || git merge-base HEAD "origin/$head" 2>/dev/null || true)"
    files="$({ [ -n "$base" ] && git diff --name-only "$base" HEAD || true
               git diff --name-only HEAD
               git ls-files --others --exclude-standard; } | sort -u)"
    [ -n "$files" ] || {
        echo "changed: nothing differs from $head. That ran over zero files, which is not a pass." >&2
        exit 1
    }
    # A changed test earns its mutants too: editing tests/test_mut_accept.py and mutating
    # nothing proves the new test is green, never that it would notice anything. The modules
    # are the ones the file imports, not the one its name spells: by name, five of the eleven
    # suites resolved to a module that does not exist and were dropped without a word, so
    # `update` and `uninstall` — the debt the mutation floor names — had no suite pointed at
    # them at all. A hook is listed only where a row in tests/mutation.py names it, as in
    # `mutate`; a suite naming none of ours says so on stderr rather than vanishing.
    mutable="$(printf '%s\n' "$files" | while read -r f; do
        case "$f" in
            src/*.py) echo "$f"; continue ;;
            tests/test_*.py) { sed -n 's/^ *from ai_engineering import //p' "$f" 2>/dev/null | tr ',' '\n'
                               sed -n 's/^ *import //p' "$f" 2>/dev/null; } | tr -d ' ' | while read -r m; do
                                 for c in "src/ai_engineering/$m.py" "hooks/$m.py"; do
                                     case "$c" in hooks/*) grep -qF "\"$c\"" tests/mutation.py || continue ;; esac
                                     [ -f "$c" ] && echo "$c" || true
                                 done
                             done | grep . || echo "  $f names no module of ours, so none was mutated" >&2
                             continue ;;
        esac
        grep -qF "\"$f\"" tests/mutation.py && echo "$f" || true
    done | sort -u)"
    printf 'changed: %s files against %s\n' "$(printf '%s\n' "$files" | wc -l | tr -d ' ')" "$head"
    printf '%s\n' "$files" | sed 's/^/      /'
    echo "  will run: ruff over the whole tree, the whole suite, and the mutants of —"
    printf '%s\n' "${mutable:-(nothing you touched has mutants)}" | sed 's/^/      /'
    cat <<'LEDGER'
      will NOT run, and is therefore not known to be true:
          the mutants of every file this branch did not touch
          coverage --fail-under=80, gitleaks, semgrep, trivy, the wheel build
          what the pull request adds: sonar, snyk, pip-audit, mypy, actionlint, zizmor
      `just check` is the gate, and this is not it.
    LEDGER
    uv run --with {{ruff}} ruff check .
    uv run --with {{ruff}} ruff format --check .
    uv run --with {{pytest}} pytest -q
    [ -z "$mutable" ] || {{just_executable()}} mutate $mutable
    echo "changed: green over the files named above, and silent about every file that is not."

# The counts come from the tools themselves: a file list prints the same number whether
# the linter ran or was replaced by `true`, which is the theatre this contract catches.
# So each number is one a tool can only print by having read the files it counts.
counts:
    @echo "RAN lint=$(uv run --with {{ruff}} ruff format --check . | grep -oE '^[0-9]+')"
    @echo "RAN tests=$(uv run --with {{pytest}} pytest -q --collect-only 2>/dev/null | grep -cE '::')"

# Close the line ceiling onto the tree, which is a fixed point and was being solved by hand.
# The ceiling counts every committed line and is itself a committed line, so writing a value
# changes what the value describes — measure, write, measure again, adjust. Fifty times in
# one session, three or four calls each. This is that arithmetic, and it converges in two or
# three passes. `--check` is the read-only half, for anybody who wants to know before they
# find out from the suite.
seal:
    @uv run python tests/seal_ceiling.py

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

# Where things stand, from the tree, with no model doing the arithmetic. Not in `check`:
# it asserts nothing and a report inside a gate is a report people read as a gate.
stats:
    @uv run python tests/stats.py

# The last step, and the only one that leaves anything behind. Everything above is an
# ephemeral process writing ignored receipts, which is why `PO-10` and `PO-14` — did the
# removed practices stay removed, and did each commit run its module's suite — were both
# graded on no evidence at all. A commit trailer is the one place a run can be recorded
# where git will still have it a month later, and `commit-msg` writes it from this receipt
# only when the content it names is the content being committed.
ran suite="check":
    @uv run python tests/ran_receipt.py record {{suite}}

check: build sbom lint typecheck test cover security register skilleval counts ran
