# What `check` means here. CI never learns a language: it runs `just check`.
# Tools are pinned at the call site: this project declares no dependencies, so an
# unpinned `uv run ruff` resolves from a .venv somebody happened to build, which is why
# CI could never have run this file.

ruff := "ruff==0.16.2"
pytest := "pytest==9.1.1"
semgrep := "semgrep==1.172.0"
coverage := "coverage==7.15.4"
mutmut := "mutmut==3.7.0"

build:
    uv build

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

test:
    uv run --with {{pytest}} pytest -q

security:
    gitleaks dir . --redact --no-banner --exit-code 1
    uv run --with {{semgrep}} semgrep scan --config policy/semgrep.yml --error --quiet
    trivy fs --scanners vuln,license,misconfig --exit-code 1 --severity CRITICAL,HIGH,MEDIUM .

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
    # 89 is what landed, closed at the measurement with no margin, as with the line ceiling.
    # The target is 95 and the payer is named: `update` and `uninstall` have no suite of
    # their own, and their 197 survivors are almost exactly the six points missing. Every
    # other module is between 93% and 98%. Raise this in the commit that writes that file.
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

# Where things stand, from the tree, with no model doing the arithmetic. Not in `check`:
# it asserts nothing and a report inside a gate is a report people read as a gate.
stats:
    @uv run python tests/stats.py

check: build lint typecheck test cover security counts
