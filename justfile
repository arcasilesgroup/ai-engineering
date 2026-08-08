# What `check` means here. CI never learns a language: it runs `just check`.
# Tools are pinned at the call site: this project declares no dependencies, so an
# unpinned `uv run ruff` resolves from a .venv somebody happened to build, which is why
# CI could never have run this file.

ruff := "ruff==0.16.2"
pytest := "pytest==9.1.1"
semgrep := "semgrep==1.172.0"

linked:
    @command -v ai-eng >/dev/null || echo "ai-eng is not installed here. Run: ai-eng init"
    @git config --get core.hooksPath >/dev/null || echo "git hooks are not wired. Run: ai-eng init"

build:
    uv build

lint:
    uv run --with {{ruff}} ruff check .
    uv run --with {{ruff}} ruff format --check .

test:
    uv run --with {{pytest}} pytest -q
    uv run python tests/adversarial/run.py

security:
    gitleaks dir . --redact --no-banner --exit-code 1
    uv run --with {{semgrep}} semgrep scan --config policy/semgrep.yml --error --quiet
    trivy fs --scanners vuln,license,misconfig --exit-code 1 --severity CRITICAL,HIGH,MEDIUM .

# The counts come from the tools themselves: a file list prints the same number whether
# the linter ran or was replaced by `true`, which is the theatre this contract catches.
counts:
    @echo "RAN lint=$(uv run --with {{ruff}} ruff check . --show-files | wc -l | tr -d ' ')"
    @echo "RAN format=$(uv run --with {{ruff}} ruff format --check . 2>&1 | grep -oE '^[0-9]+' | head -1)"
    @echo "RAN tests=$(uv run --with {{pytest}} pytest -q --collect-only 2>/dev/null | grep -cE '::')"

check: linked build lint test security counts
