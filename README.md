# {ai} Engineering

**Plant. Guard. Prove.** — governance floor for AI coding agents.

[![npm version](https://img.shields.io/npm/v/ai-engineering.svg)](https://www.npmjs.com/package/ai-engineering)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![readme style](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=flat-square)](https://github.com/RichardLitt/standard-readme)

One binary (`ai-eng`, compiled with Bun) that puts a governance floor under your
AI coding agent: guards that deny destructive tool calls, git hooks that fire
even when the agent is not involved, an executable contract per milestone, and
a receipt for every run. The creative work stays with your agent in its IDE;
`ai-eng` makes its failures expensive and its successes provable.

## Table of Contents

- [Background](#background)
- [Install](#install)
- [Usage](#usage)
- [Core concepts](#core-concepts)
- [Security](#security)
- [Development](#development)
- [Maintainers](#maintainers)
- [Contributing](#contributing)
- [License](#license)

## Background

AI agents write code at machine speed and break things at the same speed:
bypassed git hooks, silenced linters, contracts nobody approved, green checks
that never ran. Existing tooling reviews the output; `ai-engineering` governs
the run itself.

The product spec — `docs/blueprint.html` (v17, §-numbered) — defines every
behavior cited below. The triad:

1. **Plant** — `ai-eng init` writes the contract files and hook shims.
2. **Guard** — `ai-eng chain` denies destructive tool calls, fail-closed.
3. **Prove** — receipts and `spec run` make "done" a checkable claim, not a promise.

Unlike linters or CI-only gates, the floor is under the agent's feet during the
run: a guard denial happens before the destructive call executes, and editing a
markdown file switches nothing off — the only bypass is
`.ai-engineering/overrides.toml` with a written reason and an expiry date.

## Install

Requires [Bun](https://bun.sh) ≥ 1.4 (or any npm-compatible runtime):

```bash
bun add -g ai-engineering   # → ai-eng in PATH
```

Or download a standalone binary from
[GitHub Releases](https://github.com/arcasilesgroup/ai-engineering/releases)
(Linux, macOS, Windows × x64, arm64 — SBOM included).

## Usage

```bash
cd my-project && ai-eng init   # plants the contract (creates the repo if needed)
ai-eng doctor                  # 12 checks + one real adversarial probe
```

`init` is idempotent and interactive: outside a git repo it offers to create
one; in an already-governed repo it offers to re-plant assets or exit. CI and
scripts pass `--yes --surface <id>` for zero prompts.

Human verbs:

| Verb | Does |
|---|---|
| `init` | plant governance: machine canon (global) + repo contract |
| `doctor` | 12 health checks + live adversarial probe + receipt stats (`--gc` collects) |
| `config` | add/remove agent surfaces (Claude Code, OpenCode, oh-my-pi, …) |
| `update` | re-plant binary assets into the repo — zero network |
| `upgrade` | show changelog, confirm, delegate install to bun/npm |
| `uninstall` | revert ours, keep yours: AGENTS.md, DECISIONS.md, spec/plan stay |

Machine verbs (called by hooks and CI, no human UX): `chain` (guard dispatcher),
`git` (pre-commit/commit-msg/pre-push floor), `wrap test -- <cmd>` (test-output
filter), `spec run|open|approve|close` (executable contract).

`ai-eng tab` installs shell completion (zsh/bash/fish).

## Core concepts

- **Five guards** — no-verify, self-protect, injection, loop, wrap. Compiled
  into the binary; each denial writes a receipt with the reason verbatim.
- **The git floor** — `core.hooksPath` shims running gitleaks, the DECISIONS.md
  gate, and the `Receipt-Id` trailer, even when the agent is not involved.
- **The executable contract** — `.ai-engineering/spec.html` (WHAT) +
  `plan.html` (HOW) per milestone. A contract nobody approved refuses to run
  (its sha256 must be pinned in `ai-eng.lock`); a check that cannot execute is
  red, never silently green.
- **Proof > promise** — one receipt per execution; `doctor` runs a real
  adversarial payload and measures real latency.
- **The skill canon** — 20 `ai-*` skills installed once per machine in
  `~/.ai-engineering/skills/`, symlinked per surface. Attribution: NOTICE.md.

## Security

The product is a security boundary; treat attacks on it as vulnerabilities.
Report via the policy: [SECURITY.md](SECURITY.md). Guard bypasses are critical
by definition. Overrides require `reason` + `until`; expired exceptions re-arm
the guard; `update` never touches the network (it re-plants from the binary you
already installed).

## Development

```bash
bun install
bun run build              # compile dist/ai-eng (skills/templates embedded)
bun test                   # unit + adversarial (oracle) + gates + arch
bun run lint               # oxlint
bun run typecheck          # tsgolint
bun scripts/gen-assets.ts  # regenerate src/assets.ts after skills/ or templates/ changes
bun link                   # expose local ai-eng for testing in other repos
```

Versioning and changelog: [changesets](.changeset/README.md). Merge to `main`
runs the version workflow (npm publish); tags `v*` build the 8 cross-compiled
binaries + SBOM.

## Maintainers

[Arcasiles Group](https://github.com/arcasilesgroup).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) — repo rules, commit conventions, and
the changeset requirement. This project follows its
[Code of Conduct](CODE_OF_CONDUCT.md).

## License

[Apache-2.0](LICENSE) © Arcasiles Group — see [NOTICE.md](NOTICE.md) and
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for third-party attribution.
