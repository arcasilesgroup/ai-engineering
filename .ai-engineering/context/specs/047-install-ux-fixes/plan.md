---
spec: "047"
approach: "serial-phases"
---

# Plan — Fix `ai-eng install` UX

## Architecture

### Modified Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/cli_commands/core.py` | T1: VCS alias + normalization; T2: clean output |
| `src/ai_engineering/cli_commands/setup.py` | T3a: VCS-filtered platform prompts; T3b: sonar prompt hint |
| `src/ai_engineering/platforms/sonar.py` | T3b: URL normalization + error message |
| `src/ai_engineering/vcs/factory.py` | T1: add `azdo` key to `_PROVIDERS` dict |
| `src/ai_engineering/cli_commands/vcs.py` | T1: add `azdo` to `_VALID_PROVIDERS` |
| `tests/unit/test_setup_cli.py` | T4: new/updated tests |

### New Files

None.

## Session Map

### Phase 1: VCS Alias + Output Cleanup [M]

**T1 — VCS alias `azdo`:**
- `core.py` — update `--vcs` flag help: `"github or azdo (alias for azure_devops)"`
- `core.py` — prompt choices: `["github", "azdo"]`
- `core.py:_resolve_vcs_provider()` — normalize: `if choice in ("azdo", "azure_devops"): return "azure_devops"`
- `core.py` — display: show `"azdo"` if `resolved_vcs == "azure_devops"`
- `factory.py` — add `"azdo": AzureDevOpsProvider` to `_PROVIDERS`
- `vcs.py` — add `"azdo"` to `_VALID_PROVIDERS` tuple

**T2 — Clean install output:**
- `core.py` — remove `header("Branch Policy Setup Guide")` + `print_stdout(result.guide_text)` block
- `core.py` — add `typer.echo("")` before "Manual steps required"
- `core.py` — add `typer.echo("")` before `suggest_next()`

### Phase 2: Platform Filtering + Sonar URL [M]

**T3a — Platform filtering:**
- `setup.py:setup_platforms_cmd` — add `vcs_provider: str | None = None` parameter
- `setup.py` — after computing `undetected`, filter out opposite VCS
- `core.py` — pass `resolved_vcs` when calling platform setup from install flow

**T3b — Sonar URL normalization:**
- `sonar.py` — normalize URL before `urljoin`: extract `scheme + netloc` only
- `sonar.py` — same normalization in `_validate_token_urllib`
- `sonar.py` — wrap `response.json()` in try/except `json.JSONDecodeError`
- `setup.py` — update prompt: `"Sonar server base URL (e.g. https://sonarcloud.io)"`

### Phase 3: Tests + Verification [S]

- Add/update unit tests for all 4 fixes
- Run full test suite + linter

## Execution Plan

| Phase | Agent | Tasks | Gate |
|-------|-------|-------|------|
| 1 | build | T1 + T2 | Linter pass |
| 2 | build | T3a + T3b | Linter pass |
| 3 | build | Tests | All tests green |
