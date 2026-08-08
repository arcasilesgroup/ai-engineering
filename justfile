# What `check` means here. CI never learns a language: it runs `just check`.

linked:
    @command -v ai-eng >/dev/null || echo "ai-eng is not installed on this machine: this repository has no floor here. Run: uv tool install ai-engineering && ai-eng init"
    @git config --get core.hooksPath >/dev/null || echo "git hooks are not wired in this clone. Run: ai-eng init"

build:
    uv build

lint:
    uv run ruff check .
    uv run ruff format --check .

test:
    uv run pytest -q
    uv run python tests/adversarial/run.py

security:
    gitleaks dir . --redact --no-banner --exit-code 1
    semgrep scan --config policy/semgrep.yml --error --quiet
    trivy fs --scanners vuln,license --exit-code 1 --severity CRITICAL,HIGH,MEDIUM .

counts:
    @echo "RAN lint=$(git ls-files '*.py' | wc -l | tr -d ' ')"
    @echo "RAN tests=$(uv run pytest -q --collect-only 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1)"

check: linked build lint test security counts
