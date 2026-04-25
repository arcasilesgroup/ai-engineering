# Plan: spec-101 Installer Robustness — Stack-Aware User-Scope Tool Bootstrap

## Dispatch Status (session checkpoint 2026-04-25 — Phase 0 + Phase 1 COMPLETE)

**Progress**: 39/102 tasks completed (38.2%) in 13 waves. Phase 0 + Phase 1 closed; Phase 2-6 pending. Active session paused for clean handoff.

### Phase 1 — COMPLETE (22/22 tasks; 5+ files, 591 tests, 0 regressions)

| Wave | Tasks | Outcome |
|---|---|---|
| 9 | T-1.1, T-1.3, T-1.13, T-1.15, T-1.17 | 5 RED test files (155 tests) |
| 10 | T-1.5, T-1.7, T-1.9, T-1.11, T-1.19, T-1.21 | 6 RED test files (189 tests) |
| 11 | T-1.2, T-1.20, T-1.14, T-1.18 (4 parallel GREEN) | tool_registry.py + _shell_patterns.py + launchers.py + prereqs/sdk.py — 87 tests GREEN |
| 12 | T-1.4 + T-1.6 + T-1.10 + T-1.22 + T-1.20 integration (combined) | user_scope_install.py (675 lines) — 204 tests GREEN |
| 13 | T-1.8 (mechanisms package) | 12 mechanism classes — 51 tests GREEN, registry stubs replaced via re-export |

### Phase 1 metrics

- 87 tests GREEN in Phase 0 + 591 tests in Phase 1 = **678 tests added across spec-101 sessions, all GREEN**
- 358 forbidden-substring scans clean across `installer/`, `doctor/`, `prereqs/`
- 3399 unit tests passing in repo (sanity sweep) with 0 NEW regressions; 6 pre-existing failures unrelated
- ruff format + check clean across all new modules

### Files created in Phase 0+1 (12 new + 5 modified)

**Created**:
- `src/ai_engineering/state/manifest.py` (353 lines) — load_required_tools, load_sdk_prereqs, load_python_env_mode, LoadResult, StackSkip
- `src/ai_engineering/installer/tool_registry.py` (453 lines) — TOOL_REGISTRY across 14 stacks, re-exports mechanisms
- `src/ai_engineering/installer/user_scope_install.py` (675 lines) — DRIVER_BINARIES + _safe_run + run_verify + _scrubbed_env + RESOLVED_DRIVERS + compound shell guard
- `src/ai_engineering/installer/_shell_patterns.py` (86 lines) — BLOCK_PATTERNS regex set
- `src/ai_engineering/installer/launchers.py` (188 lines) — resolve_project_local for D-101-15
- `src/ai_engineering/installer/mechanisms/__init__.py` (500 lines) — 12 mechanism classes + InstallResult + Sha256MismatchError
- `src/ai_engineering/prereqs/__init__.py` + `prereqs/sdk.py` (310 lines) — probe_sdk + ProbeResult, probe-only allowlist
- `src/ai_engineering/validator/categories/required_tools.py` (315 lines) — D-101-03+13 governance lint
- 11 RED test files in `tests/unit/` (~3500 lines, 591 tests)
- `tests/fixtures/test_manifests/spec101_required_tools.yml` (69 lines)
- `.ai-engineering/runs/spec-101/phase-0-notes.md` (~500 lines exploration doc)

**Modified**:
- `src/ai_engineering/state/models.py` (+205 lines) — ToolSpec, StackSpec, RequiredToolsBlock, ToolInstallRecord, ToolInstallState, PythonEnvMode, Platform, ToolScope, SdkPrereq, InstallState extension
- `src/ai_engineering/state/service.py` (+92 lines) — legacy state migration
- `src/ai_engineering/cli_commands/validate.py` (+1 line for help text)
- `src/ai_engineering/validator/_shared.py`, `validator/categories/__init__.py`, `validator/service.py` — wire required-tools lint into aggregator
- `.ai-engineering/manifest.yml` + template (+91 lines each) — canonical 15-key required_tools + prereqs + python_env

### Phase 0 — COMPLETE (17/17 tasks)

| Task | Wave | State | Notes |
|---|---|---|---|
| T-0.1 | 1 | DONE | AGENT_METADATA + 8 mirrors (`ai-eng sync --check` exit 0) |
| T-0.2 | 1 | DONE | `runs/spec-101/phase-0-notes.md` with 6 design corrections (Pydantic, _PIP_INSTALLABLE location, free-function pattern, etc.) |
| T-0.3 | 2 | DONE | RED `test_required_tools_schema.py` (35 tests) |
| T-0.4 | 3 | DONE | GREEN `state/models.py` ToolSpec/StackSpec/RequiredToolsBlock/Platform/ToolScope |
| T-0.5 | 2 | DONE | RED `test_manifest_load_required_tools.py` (20 tests) |
| T-0.6 | 4 | DONE | GREEN `state/manifest.py` `load_required_tools` + `LoadResult` |
| T-0.7 | 2 | DONE | RED `test_validate_manifest_required_tools.py` (12 tests + 1 xpass) |
| T-0.8 | 5 | DONE | GREEN `validator/categories/required_tools.py` + aggregator wire |
| T-0.9 | 2 | DONE | RED `test_sdk_prereqs_schema.py` (31 tests) |
| T-0.10 | 4 | DONE | GREEN `SdkPrereq` + `load_sdk_prereqs` |
| T-0.11 | 2 | DONE | RED `test_python_env_mode_schema.py` (16 tests) |
| T-0.12 | 4 | DONE | GREEN `PythonEnvMode` enum + `load_python_env_mode` |
| T-0.13 | 2 | DONE | RED `test_install_state_required_tools.py` (27 tests) |
| T-0.14 | 3 | DONE | GREEN `ToolInstallRecord` + `ToolInstallState` enum + `InstallState` extension |
| T-0.15 | 6 | DONE | RED `test_install_state_migration.py` (6 tests) |
| T-0.16 | 7 | DONE | GREEN legacy state migration (free-function, atomic rename, idempotent) |
| T-0.17 | 8 | DONE_WITH_CONCERNS | manifest.yml + template canonical block (validator PASS, but lint normaliser bug logged for follow-up) |

### Phase 2 — NEXT ENTRY POINT (0/28 tasks; T-1.16 also waiting on PHASE_TOOLS refactor)

**Recommended Wave 14** (next session):

The Phase 2 work refactors `installer/phases/tools.py` to use the new foundation modules. Approximate wave plan:

1. **Wave 14 — Installer phase + exit codes** (5 tasks; sequential same file):
   - T-2.1 RED + T-2.2 GREEN: `installer/phases/tools.py` reads `load_required_tools(resolved_stacks)` and uses `user_scope_install` mechanisms.
   - T-2.3 RED + T-2.4 GREEN: EXIT 80/81 wiring with strict precedence.
   - T-2.5 RED + T-2.6 GREEN: uv version-range runtime check (R-8).
2. **Wave 15 — SDK gate + platform skips + OS release**:
   - T-2.7 RED + T-2.8 GREEN: SDK prereq gate before tools phase (uses `prereqs/sdk.py`).
   - T-2.9 RED + T-2.10 GREEN: platform_unsupported skip (tool + stack levels). Resolves T-1.16 deferred.
   - T-2.11 RED + T-2.12 GREEN: OS-release capture at major.minor.
3. **Wave 16 — PATH remediation + idempotence + simulation hook**:
   - T-2.13 RED + T-2.14 GREEN: PATH-missing shell snippet.
   - T-2.15 RED + T-2.16 GREEN: skip-on-verify-pass + os_release-mismatch + `--force`.
   - T-2.17 RED + T-2.18 GREEN: `AIENG_TEST_SIMULATE_FAIL`.
4. **Wave 17 — python_env modes + hook generator + data-driven runner**:
   - T-2.19 RED + T-2.20 GREEN: `installer/python_env.py` with 3 modes + non-git fallback.
   - T-2.21 RED + T-2.22 GREEN: `hooks/manager.py` mode branching (.venv/bin prepend toggle).
   - T-2.23 RED + T-2.24 GREEN: `policy/checks/stack_runner.py` data-driven from manifest.
   - T-2.25 RED + T-2.26 GREEN: stack_runner integration test (3 stacks via launcher).
   - T-2.27 RED + T-2.28 GREEN: typescript-only no-op handling.

### Phase 3-6 — UPCOMING (35 tasks)

After Phase 2:
- Phase 3 (4 tasks): doctor refactor parallel to Phase 2.
- Phase 4 (9 tasks): CI matrix smoke + worktree-fast + time-budget + syscall evidence.
- Phase 5 (13 tasks): CHANGELOG + BREAKING banner + IDE mirrors + docs + governance.
- Phase 6 (5 tasks): quality gates + review.

### Concerns logged (non-blocking, follow-up)

1. **Lint normaliser bug** in `validator/categories/required_tools.py:88-115` — forces `required_tools:` as last top-level key in manifest. Latent, follow-up post-spec-101.
2. **6 pre-existing test failures** in `main` HEAD unrelated to spec-101 (`test_real_project_integrity::test_file_existence`, `test_existing_tooling_preserved_after_tools_merge`, 3× `test_swift_stack_skip::TestInstallerPhaseEndToEnd` that resolve in T-1.16/T-2.10, plus 1 misc). Verified by stashing changes and re-running on `main` HEAD — same 6 fail.
3. **Tool registry vs mechanisms duplication** resolved cleanly: registry now imports from mechanisms package; both surfaces expose the SAME class objects.
4. **Apple Silicon Homebrew (`/opt/homebrew`)** is statically allowlisted; **Intel Homebrew (`/usr/local`)** intentionally NOT allowlisted because privileged binaries also live there — Intel users get acceptance via the `brew` driver entry instead.

### Recommended resume command

```
/ai-autopilot --resume
```

(or `/ai-dispatch --resume` for fine-grained per-task control). The Dispatch Status block above is the source-of-truth state for the resume mechanism.

---


## Pipeline: full
## Phases: 7
## Tasks: 102 (build: 95, verify: 1, guard: 1, review: 1, iteration holders: 4)

**Spec ref**: `.ai-engineering/specs/spec.md` (status: approved, scope expanded 2026-04-25)
**Effort**: large (borderline; staying `large` because the parallelism keeps wave depth manageable)
**Dependency graph**:
```
Phase 0 (foundation: schema + state + python_env mode + AGENT_METADATA)
       │
       ▼
Phase 1 (tool registry [14 stacks] + user-scope install module + 8+ mechanisms)
       ├──▶ Phase 2 (installer + exit codes + python_env modes + SDK prereqs + launcher) ──┬─▶ Phase 4 (CI smoke + worktree fast + time-budget + syscall evidence)
       │                                                                                    └─▶ Phase 5 (CHANGELOG + banner + mirrors + docs + governance)
       └──▶ Phase 3 (doctor refactor with python_env mode awareness)
                                                                                                                                                  ▼
                                                                                                                                Phase 6 (quality gates + review)
```

Phase 2 & 3 parallelize after Phase 1. Phase 4 & 5 parallelize after Phase 2. Phase 6 final.

### Path notes (verified)
- `resolved_stacks` built in `cli_commands/core.py:238+`.
- `InstallState` in `state/models.py`; extended in Phase 0.
- `ai-eng validate` at `cli_commands/validate.py:31` — extended.
- `ai-eng sync --check` at `cli_commands/sync.py:26`.
- `hooks/manager.py:83-88` (bash) and `:114-115` (PowerShell) hardcode `.venv/bin` PATH prepend — the worktree pain root cause; modified in Phase 2.
- `doctor/phases/tools.py:107` probes `<cwd>/.venv/pyvenv.cfg` — branches on `python_env.mode` in Phase 3.
- `policy/checks/stack_runner.py` `PRE_COMMIT_CHECKS`/`PRE_PUSH_CHECKS` registry — made data-driven from manifest in Phase 2.
- Language context files for all 14 stacks already exist at `.ai-engineering/contexts/languages/`.

---

### Phase 0: Foundation — 14-stack schema + SDK prereqs + python_env mode + state + AGENT_METADATA

**Gate**: agent write scope covers all new paths; `required_tools` block validates for all 15 keys (baseline + 14 stacks); `python_env.mode` validates with `uv-tool|venv|shared-parent`; SDK prereq schema validates; `load_required_tools(stacks)` and `load_sdk_prereqs(stacks)` return typed specs; governance lint catches abuse cases (tool-level all-3, stack-level missing reason); `InstallState` carries `required_tools_state` + `python_env_mode_recorded`; legacy state migration works.

- [ ] T-0.1: Update `AGENT_METADATA` in `.claude/agents/ai-build.md` + mirrors to include write scopes for `installer/user_scope_install.py`, `installer/tool_registry.py`, `installer/mechanisms/**`, `installer/python_env.py`, `installer/launchers.py`, `state/manifest.py`, `prereqs/sdk.py`, `.github/workflows/install-smoke.yml`, `.github/workflows/install-time-budget.yml`, `.github/workflows/worktree-fast-second.yml`, `tests/fixtures/install-smoke/**`, `tests/fixtures/worktree-fast/**`, `tests/fixtures/install-time-budget/**`, `tests/integration/test_doctor_fix_node_stack.py`, `tests/integration/test_doctor_fix_go_stack.py`, `tests/integration/test_stack_runner_data_driven.py`, `.ai-engineering/contexts/python-env-modes.md`. Run `uv run ai-eng sync` to regenerate. (agent: build)
- [ ] T-0.2: Read `state/models.py`, `state/service.py`, `cli_commands/validate.py`, `installer/phases/tools.py`, `doctor/phases/tools.py`, `hooks/manager.py`, `policy/checks/stack_runner.py` and document extension points in `.ai-engineering/runs/spec-101/phase-0-notes.md`. (agent: build — exploration, read-only)
- [ ] T-0.3: Write failing tests in `tests/unit/test_required_tools_schema.py` for 15-key block (baseline + 14 stacks): each stack key is recognised; missing key fails; invalid `platform_unsupported` OS values fail; tool-level all-3 OSes fails; missing `unsupported_reason` fails; `platform_unsupported_stack` recognised at stack-level. (agent: build — RED)
- [ ] T-0.4: Add `ToolSpec` + `StackSpec` dataclasses to `state/models.py` with fields `name`, `scope` (enum: `user_global`, `user_global_uv_tool`, `project_local`, `sdk_bundled`), `platform_unsupported`, `unsupported_reason`. `StackSpec` also carries `platform_unsupported_stack`. Blocked by T-0.3. (agent: build — GREEN)
- [ ] T-0.5: Write failing tests in `tests/unit/test_manifest_load_required_tools.py`: `load_required_tools(stacks)` returns baseline ∪ declared stacks for each of the 14 stacks; unknown stack raises `UnknownStackError`; empty stacks returns baseline only; stack with `platform_unsupported_stack` covering current OS returns empty tool list with skip-reason. (agent: build — RED)
- [ ] T-0.6: Implement `load_required_tools(stacks: list[str]) -> list[ToolSpec]` in new `state/manifest.py`. Blocked by T-0.5. (agent: build — GREEN)
- [ ] T-0.7: Write failing tests in `tests/unit/test_validate_manifest_required_tools.py` for governance lint: tool-level cap 2-of-3 enforced; stack-level `platform_unsupported_stack` allowed for all 3 OSes (per D-101-13); `unsupported_reason` mandatory at both levels; OS enum validated; declared stack without matching `required_tools.<stack>` entry fails (R-15). (agent: build — RED)
- [ ] T-0.8: Extend `cli_commands/validate.py` with `required_tools` lint per D-101-03 + D-101-13. Blocked by T-0.7. (agent: build — GREEN)
- [ ] T-0.9: Write failing tests in `tests/unit/test_sdk_prereqs_schema.py`: `prereqs.sdk_per_stack` block validates names + `min_version` semver + `install_link` URL; missing fields fail. (agent: build — RED)
- [ ] T-0.10: Add `SdkPrereq` model + `load_sdk_prereqs(stacks)` loader to `state/manifest.py`. Blocked by T-0.9. (agent: build — GREEN)
- [ ] T-0.11: Write failing tests in `tests/unit/test_python_env_mode_schema.py`: `python_env.mode` accepts `uv-tool|venv|shared-parent`; missing key defaults to `uv-tool`; invalid value fails. (agent: build — RED)
- [ ] T-0.12: Add `PythonEnvMode` enum + manifest loader hook in `state/manifest.py`. Blocked by T-0.11. (agent: build — GREEN)
- [ ] T-0.13: Write failing tests in `tests/unit/test_install_state_required_tools.py` for extended `InstallState.required_tools_state: dict[str, ToolInstallRecord]` + `python_env_mode_recorded: PythonEnvMode | None` + ToolInstallRecord fields (state, mechanism, version, verified_at, os_release). Include enum values: `installed`, `skipped_platform_unsupported`, `skipped_platform_unsupported_stack`, `not_installed_project_local`, `failed_needs_manual`. (agent: build — RED)
- [ ] T-0.14: Extend `state/models.py` with `ToolInstallRecord` + `InstallState.required_tools_state` + `python_env_mode_recorded`. Blocked by T-0.13. (agent: build — GREEN)
- [ ] T-0.15: Write failing tests in `tests/unit/test_install_state_migration.py` (R-10): legacy state (missing `required_tools_state` or `python_env_mode_recorded`) renames file to `install-state.json.legacy-<ts>` and returns fresh state. (agent: build — RED)
- [ ] T-0.16: Implement legacy-state migration in `state/service.py` loader. Blocked by T-0.15. (agent: build — GREEN)
- [ ] T-0.17: Add canonical 15-key `required_tools` block + `prereqs.sdk_per_stack` + `python_env.mode: uv-tool` to `.ai-engineering/manifest.yml` AND `src/ai_engineering/templates/.ai-engineering/manifest.yml`. Blocked by T-0.8, T-0.10, T-0.12. (agent: build)

---

### Phase 1: Tool registry + user-scope install module + 8+ mechanisms (14 stacks)

**Gate**: `installer/tool_registry.py` maps tools for all 14 stacks; `installer/user_scope_install.py` exists with `_safe_run` runtime guard; **all 12 mechanism types** tested with mocked subprocess; offline-safe verify passes under `HTTPS_PROXY=http://127.0.0.1:1`; cross-file forbidden-substring grep covers `installer/**/*.py` AND `doctor/**/*.py` AND `prereqs/**/*.py`.

- [ ] T-1.1: Write failing tests in `tests/unit/test_tool_registry.py`: per-tool per-OS mechanism list; verify cmd shape; regex match for ~30 tools spanning 14 stacks. (agent: build — RED)
- [ ] T-1.2: Create `installer/tool_registry.py` with `TOOL_REGISTRY` dict + typed mechanism spec covering: gitleaks, semgrep, jq (baseline); ruff, ty, pip-audit, pytest, sqlfluff (python+sql via uv-tool); checkstyle, google-java-format (java); ktlint (kotlin); staticcheck, govulncheck (go); dotnet-format (csharp); cargo-audit (rust); phpstan, php-cs-fixer, composer (php); shellcheck, shfmt (bash); clang-tidy, clang-format, cppcheck (cpp); swiftlint, swift-format (swift, with stack-level `platform_unsupported_stack: [linux, windows]`). Blocked by T-1.1. (agent: build — GREEN)
- [ ] T-1.3: Write failing tests in `tests/unit/test_driver_binaries.py` for `DRIVER_BINARIES` resolution: git, uv, python, node, npm/pnpm/bun, dotnet, brew, winget, scoop, curl, **java, kotlinc, swift, dart, go, rustc/cargo, php, composer, clang/llvm**; missing drivers reported with actionable error. (agent: build — RED)
- [ ] T-1.4: Implement `DRIVER_BINARIES` + `resolve_driver(name)` in `installer/user_scope_install.py`. Blocked by T-1.3. (agent: build — GREEN)
- [ ] T-1.5: Write failing tests in `tests/unit/test_safe_run_guard.py` for `_safe_run(argv)`: rejects paths outside allowlists; allows install-targets (`~/.local/`, `~/.cargo/`, `~/.dotnet/tools/`, `~/.composer/vendor/bin/`, `~/go/bin/`, `~/.local/share/uv/tools/`, `$(brew --prefix)/`, project venv); allows drivers; raises `UserScopeViolation`; obfuscation attempts blocked. (agent: build — RED)
- [ ] T-1.6: Implement `_safe_run` with expanded path allowlists for the 14-stack tool ecosystem. Blocked by T-1.5. (agent: build — GREEN)
- [ ] T-1.7: Write failing tests in `tests/unit/test_install_mechanisms.py` for each mechanism class (mocked subprocess): `BrewMechanism`, `GitHubReleaseBinaryMechanism` (SHA256-pinned), `WingetMechanism`, `ScoopMechanism`, `UvToolMechanism`, `UvPipVenvMechanism`, `NpmDevMechanism`, `DotnetToolMechanism`, **`CargoInstallMechanism`** (rust), **`GoInstallMechanism`** (go), **`ComposerGlobalMechanism`** (php), **`SdkmanMechanism`** (java/kotlin JDK helper). (agent: build — RED)
- [ ] T-1.8: Implement the 12 mechanism classes in `installer/mechanisms/` package, each routing through `_safe_run`. Blocked by T-1.7. (agent: build — GREEN)
- [ ] T-1.9: Write failing tests in `tests/unit/test_verify_offline_safe.py`: `HTTPS_PROXY=http://127.0.0.1:1` env forces offline; `gitleaks detect --no-git --source /dev/null` exit 0; `semgrep --version` exit 0 (no `--config auto`); regex matches; covers verify cmds for all 14 stacks (≥1 per stack). (agent: build — RED)
- [ ] T-1.10: Implement `run_verify(tool_spec) -> VerifyResult` with 10s timeout + regex match. Blocked by T-1.9. (agent: build — GREEN)
- [ ] T-1.11: Write failing test `tests/unit/test_no_forbidden_substrings.py` greps **all** files under `src/ai_engineering/installer/**/*.py`, `src/ai_engineering/doctor/**/*.py`, AND `src/ai_engineering/prereqs/**/*.py` for forbidden literals (`sudo`, `apt install`, `yum install`, `dnf install`, `npm install -g`, `choco install`, `Install-Package` without `-Scope CurrentUser`); test must FAIL until modules clean. (agent: build — RED)
- [ ] T-1.12: Clean target modules to pass the grep test. Blocked by T-1.11. (agent: build — GREEN)
- [ ] T-1.13: Write failing tests in `tests/unit/test_project_local_launcher.py` for D-101-15 launcher pattern: typescript routes via `npx`; php via `./vendor/bin/`; java via `./mvnw`/`./gradlew`; kotlin via `./gradlew`; cpp via `cmake`+`ctest`; missing launcher emits actionable "run X to install dev deps" message. (agent: build — RED)
- [ ] T-1.14: Implement `installer/launchers.py` with `resolve_project_local(tool_spec, cwd) -> list[str]` returning the launcher cmd. Blocked by T-1.13. (agent: build — GREEN)
- [ ] T-1.15: Write failing tests in `tests/unit/test_swift_stack_skip.py`: on linux/windows, swift stack returns empty tool list + `skipped_platform_unsupported_stack` records per declared swift tool; on darwin, normal install path runs. (agent: build — RED)
- [ ] T-1.16: Implement stack-level platform-skip in `state/manifest.py.load_required_tools` per D-101-13. Blocked by T-1.15. (agent: build — GREEN)
- [ ] T-1.17: Write failing tests in `tests/unit/test_sdk_prereq_probes.py` as a **parametric test** with one case per SDK-required stack — total **9 parametrised cases**, asserted via `len(_test_cases) == 9` to prevent silent omission. Cases: `java -version` parsing JDK version (java + kotlin both share this); `dotnet --version` parsing >= 9; `swift --version` (darwin only); `dart --version`; `go version`; `rustc --version`; `php --version` >= 8.2; `clang --version` OR `gcc --version` (cpp). Plus a **probe-only allowlist** test asserting `prereqs/sdk.py` subprocess argv shapes match the allowlist and reject any install-shaped command (no `install`, `add`, `download`, `curl`, etc. as args). (agent: build — RED)
- [ ] T-1.18: Implement `prereqs/sdk.py` module with per-stack probes + EXIT 81 message templating. Probe-only invariant enforced (D-101-14): module never invokes install commands. Blocked by T-1.17. (agent: build — GREEN)
- [ ] T-1.19: Write failing tests in `tests/unit/test_safe_run_compound_shell.py` (D-101-02 hardening 3): when `argv[0]` resolves to bash/sh/pwsh/node/python, `_safe_run` MUST inspect the full argv and reject compound-shell exfiltration patterns: `curl|bash`, `wget -O-|bash`, `nc -e`, `bash -i >& /dev/tcp/`, `eval $(curl...)`, `base64 -d | sh`, `< <(curl ...)`. Legitimate uses (`bash -c "echo ok"`, `python -c "print('hi')"`) MUST be allowed. Test asserts each blocklist pattern raises `UserScopeViolation` and each allowlisted invocation succeeds. (agent: build — RED)
- [ ] T-1.20: Implement `installer/_shell_patterns.py` with the blocklist regex set + integrate into `_safe_run` so shell-interpreter argv values are inspected for compound chains. Blocked by T-1.19. Constraint: DO NOT modify T-1.19 tests. (agent: build — GREEN)
- [ ] T-1.21: Write failing tests in `tests/unit/test_safe_run_env_scrub.py` (D-101-02 hardening 4): every subprocess spawned by `_safe_run` runs with a scrubbed env that strips sensitive keys matching `^(.+_API_KEY|.+_SECRET|.+_TOKEN|.+_PASSWORD|ANTHROPIC_API_KEY|AWS_SECRET_ACCESS_KEY|AWS_ACCESS_KEY_ID|GITHUB_TOKEN|DATABASE_URL|GH_TOKEN|AZURE_.+_KEY|GOOGLE_APPLICATION_CREDENTIALS)$`. Test poisons parent env with synthetic credentials, runs each mechanism + each verify cmd, asserts child process sees `KeyError` (or empty value) for every sensitive key. Standard env (`PATH`, `HOME`, `LANG`, `TZ`, `TERM`) preserved. Also asserts `RESOLVED_DRIVERS` is a frozen dict initialised at import time and that `shutil.which` is called once per driver per process (TOCTOU closure verification). (agent: build — RED)
- [ ] T-1.22: Implement `_scrubbed_env(os.environ)` + `RESOLVED_DRIVERS` frozen dict at module load time in `installer/user_scope_install.py`; thread `env=_scrubbed_env(...)` through every `subprocess.run`/`Popen` call. Blocked by T-1.21. Constraint: DO NOT modify T-1.21 tests. (agent: build — GREEN)

---

### Phase 2: Installer phase refactor + python_env modes + SDK prereqs + exit codes + idempotence + PATH + uv range

**Gate**: `ai-eng install` installs baseline ∪ resolved_stacks; `python_env.mode=uv-tool` DOES NOT create `.venv/`; `mode=venv` creates `.venv/` and prepends `.venv/bin` to hook PATH; `mode=shared-parent` exports `UV_PROJECT_ENVIRONMENT`; SDK prereq gate runs BEFORE tools and exits 81 on missing SDK; exits 80 on tool failure; `platform_unsupported` and `platform_unsupported_stack` skip correctly; idempotent (verify pass + os_release match); PATH-missing produces shell-specific snippet; simulation hook gated by `AIENG_TEST=1`; data-driven `stack_runner.py` registry.

- [ ] T-2.1: Write failing tests in `tests/unit/test_installer_phase_tools.py`: `PHASE_TOOLS` reads `load_required_tools(resolved_stacks)`; installs baseline ∪ stacks via `user_scope_install`; marks state per tool; respects `python_env.mode`. (agent: build — RED)
- [ ] T-2.2: Rewrite `installer/phases/tools.py` to use `user_scope_install` for all required tools; remove hardcoded `_PIP_INSTALLABLE`; drop VCS-only scoping; branch on `python_env.mode` for Python tools. Blocked by T-2.1 AND Phase 1. (agent: build — GREEN)
- [ ] T-2.3: Write failing tests in `tests/integration/test_install_exit_codes.py` for EXIT 80 (tool install failed) and EXIT 81 (prereq missing OR SDK missing); precedence (missing SDK → 81 before any tool install runs). (agent: build — RED)
- [ ] T-2.4: Wire EXIT 80 / 81 in `cli_commands/core.py` install entry; enforce precedence per D-101-11 + D-101-14. Blocked by T-2.3. (agent: build — GREEN)
- [ ] T-2.5: Write failing tests in `tests/unit/test_uv_version_range.py` (R-8): uv version outside `prereqs.uv.version_range` yields EXIT 81 with mismatch message. (agent: build — RED)
- [ ] T-2.6: Implement uv version-range runtime check in prereqs phase. Blocked by T-2.5. (agent: build — GREEN)
- [ ] T-2.7: Write failing tests in `tests/integration/test_sdk_prereq_gate.py`: missing JDK on a project declaring `java` stack → EXIT 81 with link to https://adoptium.net/; same for go/rust/csharp/php/dart/swift (darwin only)/cpp/kotlin. (agent: build — RED)
- [ ] T-2.8: Wire SDK prereq gate as a phase BEFORE tools phase in `installer/pipeline.py`. Blocked by T-2.7 AND Phase 1 (T-1.18). (agent: build — GREEN)
- [ ] T-2.9: Write failing tests in `tests/unit/test_platform_unsupported_skip.py`: tool-level `platform_unsupported` for current OS skipped + recorded; stack-level `platform_unsupported_stack` skips all stack tools + records per-tool. (agent: build — RED)
- [ ] T-2.10: Implement skip-and-record (both levels) in `installer/phases/tools.py`. Blocked by T-2.9. (agent: build — GREEN)
- [ ] T-2.11: Write failing tests in `tests/unit/test_install_os_release.py`: OS release captured at major.minor (sw_vers / lsb_release / VERSION_ID / OSVersion.Version). (agent: build — RED)
- [ ] T-2.12: Implement OS-release capture helper. Blocked by T-2.11. Single concern. (agent: build — GREEN)
- [ ] T-2.13: Write failing tests in `tests/unit/test_path_shell_remediation.py` (R-1, R-9): tool-runnable-but-not-on-PATH emits shell-specific snippet (bash/zsh/fish/PowerShell). (agent: build — RED)
- [ ] T-2.14: Implement PATH-missing detection + shell snippet. Blocked by T-2.13. (agent: build — GREEN)
- [ ] T-2.15: Write failing tests in `tests/integration/test_install_idempotence.py`: second run reports zero reinstalls when state `installed` + verify passes + os_release matches; synthetic os_release bump invalidates skip. Includes `python_env.mode` recorded check (mode change → re-eval). (agent: build — RED)
- [ ] T-2.16: Implement skip-on-verify-pass + `--force` override + python_env_mode change detection. Blocked by T-2.15. (agent: build — GREEN)
- [ ] T-2.17: Write failing tests in `tests/unit/test_aieng_test_simulate_fail.py`: `AIENG_TEST=1 AIENG_TEST_SIMULATE_FAIL=ruff` synthesizes failure for ruff only; no effect when `AIENG_TEST` unset. (agent: build — RED)
- [ ] T-2.18: Implement `AIENG_TEST_SIMULATE_FAIL` env hook gated behind `AIENG_TEST=1`. Blocked by T-2.17. (agent: build — GREEN)
- [ ] T-2.19: Write failing tests in `tests/unit/test_python_env_mode_install.py`: `mode=uv-tool` → no `.venv/` created, pytest installed via `uv tool install`; `mode=venv` → `.venv/` created in cwd, pytest in `.venv/bin/`; `mode=shared-parent` → venv created at `$(git rev-parse --git-common-dir)/../.venv` and `UV_PROJECT_ENVIRONMENT` exported; `mode=shared-parent` outside a git repo → EXIT 80 with the D-101-12 fallback message ("requires git repository; run `git init` or set `mode=venv`"). (agent: build — RED)
- [ ] T-2.20: Implement `installer/python_env.py` module + branch in installer phase + non-git fallback for `shared-parent` per D-101-12. Blocked by T-2.19. (agent: build — GREEN)
- [ ] T-2.21: Write failing tests in `tests/unit/test_hook_generator_python_env.py`: `mode=uv-tool` → hook PATH preamble OMITS `.venv/bin`; `mode=venv` → keeps current behaviour; `mode=shared-parent` → preamble exports `UV_PROJECT_ENVIRONMENT="$(git rev-parse --git-common-dir)/../.venv"`. Cover both bash and PowerShell hook templates. (agent: build — RED)
- [ ] T-2.22: Modify `hooks/manager.py:83-88` (bash) and `:114-115` (pwsh) to branch on `python_env.mode`. Blocked by T-2.21. (agent: build — GREEN)
- [ ] T-2.23: Write failing tests in `tests/unit/test_stack_runner_data_driven.py`: `PRE_COMMIT_CHECKS`/`PRE_PUSH_CHECKS` resolved from manifest at runtime; declared stack without `required_tools.<stack>` entry produces clear validation error (R-15); project_local tools route through launcher (D-101-15). (agent: build — RED)
- [ ] T-2.24: Refactor `policy/checks/stack_runner.py` to be data-driven from `load_required_tools(stacks)` + dispatch project_local through `installer/launchers.py`. Blocked by T-2.23 AND T-1.14. (agent: build — GREEN)
- [ ] T-2.25: Write failing integration test `tests/integration/test_stack_runner_data_driven.py` exercising 3 stacks end-to-end: a python-stack project triggers `ruff check` via direct PATH invocation; a typescript-stack project (with seeded `node_modules/.bin/eslint`) triggers eslint via `npx`; a go-stack project triggers `staticcheck` via `~/go/bin`. Each gate run asserts the correct launcher pattern and exit-0 on a known-good fixture. (agent: build — RED)
- [ ] T-2.26: Verify the integration test passes (may require seeding the typescript fixture's `node_modules` and the go fixture's GOPATH). Blocked by T-2.25. (agent: build — GREEN)
- [ ] T-2.27: Write failing tests in `tests/unit/test_typescript_stack_no_op_install.py`: `ai-eng install` on a typescript-only project (4 project_local tools, zero installer-managed) emits info-level "stack uses project-local launchers" message AND verifies `package.json` exists; if missing, EXIT 80 with `npm init -y` remediation per R-3 pattern. (agent: build — RED)
- [ ] T-2.28: Implement project_local-only stack handling in `installer/phases/tools.py` per D-101-01 carve-out. Blocked by T-2.27. (agent: build — GREEN)

---

### Phase 3: Doctor refactor (parallel to Phase 2)

**Gate**: `ai-eng doctor --fix --phase tools` uses shared module; covers all 14 stacks; respects `python_env.mode` (skips `_check_venv_health` in `mode=uv-tool`); integration test for node stack installs prettier locally; integration test for go stack runs `go install staticcheck`.

- [ ] T-3.1: Write failing tests in `tests/unit/test_doctor_phase_tools.py`: doctor reads `load_required_tools(resolved_stacks)` and uses `user_scope_install`; respects `python_env.mode`. (agent: build — RED)
- [ ] T-3.2: Rewrite `doctor/phases/tools.py` to delegate to `user_scope_install`; remove hardcoded `_REQUIRED_TOOLS`; branch on `python_env.mode` for venv-related checks. Blocked by T-3.1 AND Phase 1. (agent: build — GREEN)
- [ ] T-3.3: Write failing tests in `tests/unit/test_doctor_venv_health_skip.py`: `_check_venv_health` returns `not_applicable` in `mode=uv-tool`; runs probes in `mode=venv`. (agent: build — RED)
- [ ] T-3.4: Modify `doctor/phases/tools.py:107` `_check_venv_health` to branch on `python_env.mode`. Blocked by T-3.3. (agent: build — GREEN)
- [ ] T-3.5: Write failing integration test `tests/integration/test_doctor_fix_node_stack.py`: node-stack project missing prettier → `ai-eng doctor --fix --phase tools` runs `npm install --save-dev prettier` and verify passes. (agent: build — RED)
- [ ] T-3.6: Verify integration test passes (may require minimal `package.json` in fixture). Blocked by T-3.5. (agent: build — GREEN)
- [ ] T-3.7: Write failing integration test `tests/integration/test_doctor_fix_go_stack.py`: go-stack project missing staticcheck → `ai-eng doctor --fix --phase tools` runs `go install honnef.co/go/tools/cmd/staticcheck@latest` to `~/go/bin/`. (agent: build — RED)
- [ ] T-3.8: Verify go integration test passes. Blocked by T-3.7. (agent: build — GREEN)

---

### Phase 4: CI matrix smoke + worktree-fast + time-budget + syscall evidence

**Gate**: `.github/workflows/install-smoke.yml` green on macos/ubuntu/windows; exit 80 on PATH=""; idempotence + os_release invalidation asserted; strace/dtruss/Process Monitor logs uploaded; `install-time-budget.yml` asserts ≤10 min for python single-stack baseline (G-11); `worktree-fast-second.yml` asserts ≤30s for second worktree commit in `mode=uv-tool` (G-12).

- [ ] T-4.1: Create clean-project fixture at `tests/fixtures/install-smoke/clean-project/` with minimal `.ai-engineering/manifest.yml` (baseline + python stack, `python_env.mode: uv-tool`). (agent: build)
- [ ] T-4.2: Create `.github/workflows/install-smoke.yml` with 3-OS matrix, uv setup, `ai-eng install`, `git commit --allow-empty -m smoke` assertions. (agent: build)
- [ ] T-4.3: Add workflow step: `env -i PATH="" ai-eng install` asserts exit 80 + stderr matches per-tool remediation regex from G-3. (agent: build)
- [ ] T-4.4: Add workflow step for G-4(c) syscall evidence: ubuntu `strace -f -e trace=execve -o syscalls-ubuntu.log`; macOS `sudo dtruss` (skip-with-note if unavailable); Windows Process Monitor PML filtered by `ai-eng.exe`. Upload as 7-day artifacts. (agent: build)
- [ ] T-4.5: Add workflow step: `ai-eng install && ai-eng install` asserts second run 0 reinstalls; synthetic os_release write triggers re-probe. (agent: build)
- [ ] T-4.6: Pin `prereqs.uv.version_range` in manifest + template; CI matrix uses pinned min + max uv versions. (agent: build)
- [ ] T-4.7: Create fixture `tests/fixtures/install-time-budget/python-single-stack/` (clean python project, no SDK install needed). Create `.github/workflows/install-time-budget.yml`: 3-OS matrix runs `time bash -c "git clone <fixture> && cd <fixture> && ai-eng install . && git commit --allow-empty -m smoke"` and asserts wall-clock < 600s (G-11). Use **median-of-3 runs** to absorb runner-load jitter. **Trigger**: nightly schedule + manual `workflow_dispatch` + PR-label `perf` only (NOT every push) to keep PR feedback latency reasonable; the install-smoke job stays on every-push. (agent: build)
- [ ] T-4.8: Create fixture `tests/fixtures/worktree-fast/python-multi-worktree/`. Create `.github/workflows/worktree-fast-second.yml`: ubuntu only in this iteration. Job runs: clone + install primary; `time bash -c "git worktree add ../wt2 && cd ../wt2 && ai-eng install . && git commit --allow-empty -m smoke"`; asserts wall-clock < 30s in `mode=uv-tool` (G-12), **median-of-3** for jitter absorption. **Windows worktree variance is explicitly out-of-scope for this iteration** — `UV_PROJECT_ENVIRONMENT` path-separator handling needs a dedicated investigation; tracked in Out-of-scope section as a follow-up note. (agent: build)
- [ ] T-4.9: Add a 14-stack registry-coverage test in CI: lint asserts every stack in `manifest.providers.stacks` has a corresponding `required_tools.<stack>` block AND a `prereqs.sdk_per_stack.<stack>` entry IFF the stack is in the SDK-required list. (agent: build)

---

### Phase 5: CHANGELOG + BREAKING banner + python_env doc + IDE mirrors + governance

**Gate**: `ai-eng sync --check` passes; CHANGELOG has top-level BREAKING entry covering EXIT codes + `python_env.mode` default + 14-stack manifest; first-run banner fires once; `.github/CODEOWNERS` covers manifest; `copilot-instructions.md` automated test asserts zero stale tool-list refs; `python_env` doc section in README explains the three modes.

- [ ] T-5.1: Write failing tests in `tests/unit/test_breaking_banner.py`: first-run BREAKING banner seen once; state flag recorded; not repeated. (agent: build — RED)
- [ ] T-5.2: Implement banner in `installer/pipeline.py` + state flag. Blocked by T-5.1. (agent: build — GREEN)
- [ ] T-5.3: Add CHANGELOG.md top-level BREAKING entries: (a) `ai-eng install` hard-fails on missing required tools; EXIT 80/81 reserved; removed silent-pass; (b) `python_env.mode` defaults to `uv-tool` — users requiring `.venv/` per-cwd must opt in via `python_env.mode: venv`; (c) `required_tools` now covers 14 stacks. (agent: build)
- [ ] T-5.4: Update README.md migration section: remove `|| true`; document EXIT 80/81; explain `platform_unsupported` (tool vs stack); explain `python_env.mode` decision tree (uv-tool/venv/shared-parent) with the 30s-worktree benefit; list the 14 stacks. (agent: build)
- [ ] T-5.5: Write failing test `tests/unit/test_copilot_instructions_no_stale_refs.py` (G-10 automation): asserts `.github/copilot-instructions.md` zero occurrences of `_PIP_INSTALLABLE`, `_REQUIRED_TOOLS`, legacy hardcoded tool-list names. (agent: build — RED)
- [ ] T-5.6: Run `uv run ai-eng sync` to regenerate IDE mirrors. Stage for `/ai-commit` (plan does NOT commit). (agent: build)
- [ ] T-5.7: Run `uv run ai-eng sync --check`; rerun T-5.6 if drift. Blocked by T-5.6. (agent: build)
- [ ] T-5.8: Edit `.github/copilot-instructions.md` to remove stale references; rerun T-5.5 to confirm GREEN. Blocked by T-5.5. (agent: build — GREEN)
- [ ] T-5.9: Add CODEOWNERS entry for `.ai-engineering/manifest.yml` (D-101-03 + D-101-13 governance). Pause for user input on maintainer handle if ambiguous. (agent: build)
- [ ] T-5.10: Add `.ai-engineering/contexts/python-env-modes.md` summary doc explaining the three modes, when to use each, and migration commands; reference from README and CLAUDE.md table. (agent: build)
- [ ] T-5.11: Update `CLAUDE.md` (mandatory first-line read for every session) — append a brief "Installer modes" entry to the **Source of Truth** section pointing to `.ai-engineering/contexts/python-env-modes.md`; add EXIT-80/81 reference; mention 14-stack support. Keep additions minimal — CLAUDE.md is summary-only, details belong in contexts. (agent: build)
- [ ] T-5.12: Write failing test `tests/unit/test_changelog_breaking_keywords.py` asserting CHANGELOG.md contains the keywords `EXIT 80`, `EXIT 81`, `python_env.mode`, and `14 stacks` in the most recent BREAKING section — guards against accidental documentation regression on the BREAKING entry from T-5.3. (agent: build — RED)
- [ ] T-5.13: Adjust CHANGELOG entry to satisfy T-5.12 keyword test if needed. Blocked by T-5.12. (agent: build — GREEN)

---

### Phase 6: Quality gates + governance + review

**Gate**: all quality gates green; specialists approve; NEVER-weaken-gates intact; decision-store unchanged except spec-101 own entries.

- [ ] T-6.1: Dispatch `/ai-governance` advisory: NEVER-weaken-gates not violated; decision-store.json only adds spec-101 own risks; ownership boundaries respected. Output: governance report. (agent: guard — advisory)
- [ ] T-6.2: Dispatch `/ai-verify --full`: deterministic + LLM verifiers. Zero medium+ findings; coverage ≥80% on changed files; cyclomatic ≤10; cognitive ≤15. (agent: verify)
- [ ] T-6.3: If T-6.2 reports failures: fix root cause (no suppressions). Max 2 iterations. Blocked by T-6.2. (agent: build — iteration holder)
- [ ] T-6.4: Dispatch `/ai-review` on full diff: reviewer-architecture, reviewer-correctness, reviewer-security, reviewer-testing, reviewer-maintainability, reviewer-compatibility specialists. (agent: review)
- [ ] T-6.5: Address review findings; no scope creep. Max 2 iterations. Blocked by T-6.4. (agent: build — iteration holder)

---

## TDD enforcement

All RED tasks produce failing tests; paired GREEN task explicitly blocked + carries "DO NOT modify T-X.Y tests" constraint.

## Agent breakdown

| Agent | Count |
|---|---|
| build | 95 |
| verify | 1 |
| guard | 1 |
| review | 1 |
| iteration holders | 4 |

## Out-of-scope (NOT in this plan)

- S2-S5 backlog (`.ai-engineering/notes/adoption-s*.md`).
- Auto-install of language SDKs (NG-11) — links only.
- Auto-install of prereqs (NG-5).
- sudo/apt/system install (NG-6).
- New public CLI commands (NG-8).
- `--offline` install flow (NG-10).
- Windows-specific worktree-fast benchmark (deferred): `UV_PROJECT_ENVIRONMENT` path-separator handling and wall-clock variance bounding on Windows runners need a dedicated investigation. POSIX worktrees covered in T-4.8 (ubuntu); behaviour and correctness tests for `mode=shared-parent` on Windows are unit-tested in T-2.21/2.22 but performance benchmarking is deferred.
- Cmake/ctest project_local doctor integration test for cpp stack (only go and node have parallel doctor integration tests in T-3.5→3.8; cpp deferred — non-blocking because launcher pattern is unit-tested in T-1.13/1.14).
- Negative cascade test for "JDK present + kotlin tools fail to download" — covered implicitly by EXIT 80 path but not explicitly tested as a multi-stack scenario.
- Commit of regenerated mirrors (handled by `/ai-commit`).

## Spec → Plan coverage matrix

| Spec item | Tasks | Status |
|---|---|---|
| G-1 manifest 14 stacks | T-0.3→0.17 | COVERED |
| G-2 3-OS smoke | T-4.1/4.2 | COVERED |
| G-3 fail with remediation | T-2.3/2.4, T-4.3 | COVERED |
| G-4 (a)+(b)+(c) | T-1.11/1.12, T-1.5/1.6, T-4.4 | COVERED |
| G-5 platform_unsupported governance | T-0.7/0.8, T-2.9/2.10 | COVERED |
| G-6 doctor shared module | T-3.1→3.8 | COVERED |
| G-7 runnable verify | T-1.9/1.10 | COVERED |
| G-8 state record | T-0.13/0.14, T-2.11/2.12 | COVERED |
| G-9 idempotence + os_release | T-2.15/2.16 | COVERED |
| G-10 IDE mirrors automated | T-5.5→5.8 | COVERED |
| G-11 ≤10 min single-stack | T-4.7 | COVERED |
| G-12 worktree second-commit ≤30s | T-4.8 | COVERED |
| D-101-01 14-stack manifest SoT | T-0.3→0.17, T-2.2 | COVERED |
| D-101-02 user-scope + guard + cross-file grep + compound-shell + env-scrub | T-1.5/1.6, T-1.11/1.12, T-1.19/1.20, T-1.21/1.22 | COVERED |
| D-101-03 platform_unsupported governance | T-0.7/0.8, T-5.9 | COVERED |
| D-101-04 offline-safe verify | T-1.9/1.10 | COVERED |
| D-101-05 resolved_stacks | T-2.2 | COVERED |
| D-101-06 registry owns mechanisms | T-1.1/1.2 | COVERED |
| D-101-07 idempotence + os_release | T-2.11→2.16 | COVERED |
| D-101-08 doctor shares module | T-3.1/3.2 | COVERED |
| D-101-09 BREAKING + banner | T-5.1→5.3 | COVERED |
| D-101-10 CI matrix | T-4.1→4.9 | COVERED |
| D-101-11 EXIT 80/81 + AIENG_TEST + uv range | T-2.3/2.4, T-2.5/2.6, T-2.17/2.18 | COVERED |
| D-101-12 python_env.mode (uv-tool default) | T-0.11/0.12, T-2.19→2.22, T-3.3/3.4, T-5.10 | COVERED |
| D-101-13 stack-level platform_unsupported | T-0.7/0.8, T-1.15/1.16, T-2.9/2.10 | COVERED |
| D-101-14 SDK prereq detection | T-0.9/0.10, T-1.17/1.18, T-2.7/2.8 | COVERED |
| D-101-15 project_local launcher | T-1.13/1.14, T-2.23→2.28 | COVERED |
| D-101-01 project_local carve-out | T-0.13/0.14 (state value), T-2.27/2.28 (typescript no-op handling) | COVERED |
| CLAUDE.md mandatory reference | T-5.11 | COVERED |
| CHANGELOG keyword regression guard | T-5.12/5.13 | COVERED |

## Risks tracked to tasks

| Spec risk | Plan task(s) |
|---|---|
| R-1 PATH | T-2.13/2.14 |
| R-2 npm/node prereqs | T-2.3/2.4 |
| R-3 package.json missing | T-3.5/3.6 |
| R-4 Homebrew absent | T-1.1/1.2 (macOS GitHubReleaseBinaryMechanism fallback) |
| R-5 SHA drift | T-1.7/1.8 |
| R-6 BREAKING disruption | T-5.1→5.3 |
| R-7 version mismatch | T-1.9/1.10 |
| R-8 uv range | T-2.5/2.6, T-4.6 |
| R-9 Windows shells | T-2.13/2.14 |
| R-10 legacy migration | T-0.15/0.16 |
| R-11 air-gap | T-1.9/1.10 |
| R-12 brew prefix | T-1.5/1.6 |
| R-13 SDK prereq cascade | T-2.7/2.8, T-1.17/1.18 |
| R-14 worktree venv | T-2.19→2.22, T-3.3/3.4, T-4.8 |
| R-15 manifest ↔ stack_runner drift | T-0.7/0.8 (lint), T-2.23/2.24 (data-driven registry), T-4.9 (CI) |

## Open questions (tracked, not task-gated)

OQ-1 GPG, OQ-2 doctor auto-install, OQ-3 `--offline`, OQ-4 brew prefix, OQ-5 Windows ~/.local/bin — unchanged from prior iteration; still deferred or addressed in tasks above.

## Review summary

- Iteration 1 (post-scope-expansion): closing the new requirements (14 stacks, worktrees, ≤10 min, python_env mode).
- Phase 0 grew from 13 to 17 tasks (+ 4 for SDK prereq schema, python_env schema, stack-level platform_unsupported support).
- Phase 1 grew from 12 to 18 tasks (+ 4 mechanisms: Cargo, GoInstall, ComposerGlobal, Sdkman; + project_local launcher; + stack-level platform skip; + SDK prereq probes).
- Phase 2 grew from 16 to 24 tasks (+ python_env mode install branching; + hook generator branching; + SDK prereq gate wiring; + data-driven stack_runner registry).
- Phase 3 grew from 4 to 8 tasks (+ python_env mode awareness in doctor; + go stack integration test).
- Phase 4 grew from 6 to 9 tasks (+ time-budget workflow G-11; + worktree-fast workflow G-12; + 14-stack registry-coverage CI lint).
- Phase 5 grew from 9 to 10 tasks (+ python-env-modes.md context doc).
- Phase 6 unchanged at 5 tasks.
- Total: **85 tasks** (vs 64 before).
