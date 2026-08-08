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
mutate:
    #!/usr/bin/env bash
    set -euo pipefail
    # Outside the working copy, and this is not tidiness. mutmut puts its sandbox in
    # ./mutants, which is inside the repository, so `repo_root()` walks up out of the
    # sandbox and finds the real .git — and `init` then rewrites the developer's own
    # justfile and leaves timestamped backups beside it. Measured: it happened three times
    # in one run before this line existed. A test tool that can edit the tree it is
    # judging is the failure this product exists to cure, wearing a lab coat.
    here="$PWD"
    away="$(mktemp -d)"
    trap 'rm -rf "$away"' EXIT
    rsync -a --exclude=.git --exclude=.venv --exclude=dist --exclude=mutants \
          --exclude=.pytest_cache --exclude=.ruff_cache ./ "$away/"
    cd "$away"
    uv run --no-project --with {{mutmut}} --with {{pytest}} mutmut run
    uv run --no-project --with {{mutmut}} --with {{pytest}} mutmut export-cicd-stats
    uv run --no-project python - <<'PY'
    import json, sys
    FLOOR = 59  # what landed. Raise it in a commit that says why, as with the line ceiling.
    s = json.load(open("mutants/mutmut-cicd-stats.json"))
    score = round(100 * s["killed"] / s["total"])
    print(f"RAN mutants={s['total']}  killed={s['killed']}  survived={s['survived']}  {score}%")
    if score < FLOOR:
        sys.exit(f"mutation: {score}% of deliberate defects caught, under {FLOOR}%.")
    PY
    # The guards, back in the real tree, because their suite builds git repositories and
    # the line-ceiling test counts with `git ls-files`, neither of which a copy can answer.
    # This half edits the tree on purpose and restores each file in a finally, then checks
    # the sha256 matches before moving on — that is the difference between the two halves.
    cd "$here"
    uv run --with {{pytest}} python tests/mutation.py

# The counts come from the tools themselves: a file list prints the same number whether
# the linter ran or was replaced by `true`, which is the theatre this contract catches.
# So each number is one a tool can only print by having read the files it counts.
counts:
    @echo "RAN lint=$(uv run --with {{ruff}} ruff format --check . | grep -oE '^[0-9]+')"
    @echo "RAN tests=$(uv run --with {{pytest}} pytest -q --collect-only 2>/dev/null | grep -cE '::')"

check: build lint test cover security counts
