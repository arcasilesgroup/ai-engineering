# Quick command guide
This is the cheat sheet for installing, understanding and running this repository without
having to read the code.
> Run everything from the root. Use `uv run ai-eng` for the local code; once the tool is
> installed you can write just `ai-eng`.

## 1. Setup
You need **Python 3.11+**, `uv` and `just`; `just security`/`just check` also need
`gitleaks` and `trivy`. On macOS: `brew install uv just gitleaks trivy`.

```bash
uv sync                    # prepare the local environment
uv tool install --editable .  # optional: makes `ai-eng` available on the PATH
uv run ai-eng --help       # shows the project's CLI
just --list                # shows the development tasks
```
> Typical path: set up once with `uv sync` → work with `just quick MODULE` → before the PR
> run `just check` and `just guards`.

## 2. How it works
`ai-eng` installs or writes the configuration and the record; `hooks/chain.py` receives the
agent's actions and calls the guards; the Git hooks protect commits and pushes; CI runs the
same `just` recipes you run locally.

## 3. All `ai-eng` commands
| Command | What it is for |
|---|---|
| `uv run ai-eng init [--global] [--no-global] [--project [PATH]] [--no-project] [--harness IDS] [--overwrite FILES\|all] [--dry-run] [-y]` | Sets up the machine and, if you choose, the repository. Writes `.github/workflows/check.yml` and a `justfile` with the commands for the stacks it finds. Start with `--dry-run`; it installs no binaries and makes no commits. |
| `uv run ai-eng doctor [--ci] [--paths] [--fix]` | Runs the health diagnosis. `--ci` skips what a runner cannot check; `--paths` shows where each file class lives; `--fix` runs only the cures the failures themselves declare and re-checks. |
| `uv run ai-eng update [--to VERSION] [--force]` | Migrates the project's pin interactively. `--force` **only reports** what would be discarded; it never overwrites local changes. |
| `uv run ai-eng spec new SLUG [--ref owner/repo#45]` | Creates `specs/NNN-slug/spec.md`; `--ref` only annotates the work item in the frontmatter and fills nothing in. |
| `uv run ai-eng spec list [--all]` · `uv run ai-eng spec show ID` | Lists specifications or shows one; `--all` includes the replaced ones. |
| `uv run ai-eng decide "DECISION" [--supersede NNNN]` · `uv run ai-eng decide --list` · `uv run ai-eng decide --accept NNNN` | Creates or lists an ADR in `docs/adr/`. It no longer writes inside the spec: that half was deleted with `--why` and `--madr`, because nothing read what it wrote. `--accept` moves a MADR out of `proposed` taking the authority of the approved Solution Intent; it does not invent it or ask again, and if the Intent does not validate or is still draft it grants nothing. The commit is yours. |
| `uv run ai-eng accept --finding ID --expires YYYY-MM-DD --by PERSON --justification TEXT [--severity LEVEL] [--follow-up TEXT] [--spec ID]` · `uv run ai-eng accept --expired` | Records a risk with an owner and an expiry, or lists the expired ones. The first four are required: an acceptance with no name and no reason is not an acceptance. |
| `uv run ai-eng audit [verify\|replay] [--anchors] [--session ID] [--anchor]` | Verifies or replays the audit chain. `--anchors` cross-checks Git; `--anchor` is for the `commit-msg` hook. |
| `uv run ai-eng report digest [--weeks N]` | Summarises sessions, blocks, bypasses, errors and coverage for the period; marks the summary as read. `ai-eng report issue` exists as a subcommand but returns `INCOMPLETE`: it is not implemented in P0 and sends nothing. |
| `uv run ai-eng exception --skip "REASON" [--guard loop_guard]` | With human confirmation, grants **one** 15-minute bypass and records it. It does not work without an interactive terminal. |
| `uv run ai-eng uninstall [--project] [-y]` | Removes what was installed according to the receipt, and prints one line per row: what it removes and, for what it keeps, why. Without `--project` it enters no repository and names them. It always keeps `specs/`, `CONSTITUTION.md`, `AGENTS.md`, `docs/adr/` and the external record. |
| `uv run ai-eng --version` · `uv run ai-eng <command> --help` | Shows the version or all the real options of a command. |

## 4. All `just` recipes
| Recipe | What it runs and when to use it |
|---|---|
| `just build` | Builds the wheel and the source package with `uv build`. |
| `just lint` | Runs Ruff: code rules and formatting check. |
| `just test` | Runs the whole Pytest suite. For one file: `uv run --with pytest==9.1.1 pytest -q tests/test_doctor.py`. |
| `just security` | Finds secrets with Gitleaks, analyses rules with Semgrep and reviews vulnerabilities/licences/configuration with Trivy. |
| `just cover` | Measures branch coverage over the package, hooks and adversarial suite; requires at least 80 %. |
| `just guards [FILTER]` | Introduces deliberate defects into the guards and fails if the tests do not catch them. Two halves: fifteen hand-written rows with a floor of 100, and the mutants generated over the blocking surface, with a floor of 90. It is the slowest recipe. |
| `just quick MODULE` | One module's suite and its receipt, which is what the commit hook writes into the `Ai-Eng-Ran:` trailer. **It is no substitute** for the full gate. |
| `just counts` | Prints verifiable proof of how many files Ruff formatted and how many tests Pytest collected. |
| `just council` | The critic step. Recounts, over each `specs/*/council.md` and each `## Council` section inside `specs/*/spec.md`, how many gaps appeared only after cross-reading and how many findings were deleted, refuses a declared critic section that carries the template's prompt, an empty heading that never said `none`, a malformed `ran:` round line or a grill question without its answer, and rejects when its count does not match the total the run wrote. |
| `just stats` | Shows repository metrics; it is a report, not a gate. Use `uv run python tests/stats.py --json` for JSON. |
| `just check` | Local/CI gate, sixteen steps in order: `build sbom lint typecheck test cover security register skilleval evals counts intent-page lenses council map ran`. It does not include `just guards`, which is a separate lane and blocks from `ci-result`. |

## 5. Direct scripts and automation
| Execution | Use |
|---|---|
| `uv run python tests/adversarial/run.py` | Launches every attack and a clean control that must not block. |
| `uv run python tests/mutation.py [-k FILTER]` | The mutation lane under the recipe; normally use `just guards`. |
| `uv run python tests/anti_theatre.py LOG [ROOT] [names,comma-separated]` | CI: confirms that a log proves the gates really ran. |
| `uv run python tests/stats.py [--json]` | Generates the governance, quality and security report. |
| `SONAR_TOKEN=... uv run python tests/quality_gate.py [project-key]` | CI: compares the real SonarCloud Quality Gate with `policy/quality-gate.toml`. |
| `uv run python migrations/0.13..1.0/unvendor.py [ROOT] [HOME]` | Internal migration from 0.13; normally `ai-eng update` calls it, not a person. |

| Automatic | What it does |
|---|---|
| `git-hooks/` | `pre-commit` finds secrets; `commit-msg` validates the subject and adds the run receipt; `pre-push` blocks protected branches, outgoing secrets and expired risks. |
| `hooks/chain.py` | Dispatches `self_protect`, `no_verify_guard`, `injection_guard`, `loop_guard`, `autoformat` and `session`; they are not run by hand. |
| `hooks/_emit.py`, `_otlp.py`, `_wrap.py` | Keep the record, export OTLP and define the fail-closed/fail-open behaviour; they are internal helpers. |
| `tests/test_*.py` · `surfaces/opencode.ts` | Pytest collects the tests and OpenCode loads its plugin. |
| `.agents/skills/ai-*` | The agent invokes `ai-debug`, `ai-explore`, `ai-note`, `ai-plan`, `ai-research`, `ai-review`, `ai-ship` and `ai-spec`; they are not shell commands. |
| `.github/workflows/` | GitHub runs check, attacks, mutation, mypy, Sonar, Snyk, cross-platform install and publication; locally it uses the recipes above. |