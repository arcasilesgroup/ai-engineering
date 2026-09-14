<div align="center">
  <a href="https://github.com/arcasilesgroup/ai-engineering">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-light.svg">
      <img src="https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/.github/assets/banner-light.svg" alt="{ai} engineering" width="760">
    </picture>
  </a>

  <p><strong>Install. Guard. Prove.</strong> — the governance floor under your AI coding agent.</p>

  <p>
    <a href="https://github.com/arcasilesgroup/ai-engineering/releases"><picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/badge/release-v2.0.0--rc.1.svg?variant=secondary&amp;font=geist-mono&amp;size=sm&amp;mode=dark">
      <img alt="release v2.0.0-rc.1" src="https://shieldcn.dev/badge/release-v2.0.0--rc.1.svg?variant=secondary&amp;font=geist-mono&amp;size=sm&amp;mode=light">
    </picture></a>
    <a href="https://github.com/arcasilesgroup/ai-engineering/actions/workflows/check.yml"><picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/github/ci/arcasilesgroup/ai-engineering.svg?workflow=check.yml&amp;branch=main&amp;variant=secondary&amp;font=geist-mono&amp;size=sm&amp;mode=dark">
      <img alt="CI status" src="https://shieldcn.dev/github/ci/arcasilesgroup/ai-engineering.svg?workflow=check.yml&amp;branch=main&amp;variant=secondary&amp;font=geist-mono&amp;size=sm&amp;mode=light">
    </picture></a>
    <a href="LICENSE"><picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/badge/license-Apache--2.0.svg?variant=secondary&amp;font=geist-mono&amp;size=sm&amp;mode=dark">
      <img alt="license Apache-2.0" src="https://shieldcn.dev/badge/license-Apache--2.0.svg?variant=secondary&amp;font=geist-mono&amp;size=sm&amp;mode=light">
    </picture></a>
    <a href="https://github.com/arcasilesgroup/ai-engineering/stargazers"><picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/github/stars/arcasilesgroup/ai-engineering.svg?variant=secondary&amp;font=geist-mono&amp;size=sm&amp;mode=dark">
      <img alt="GitHub stars" src="https://shieldcn.dev/github/stars/arcasilesgroup/ai-engineering.svg?variant=secondary&amp;font=geist-mono&amp;size=sm&amp;mode=light">
    </picture></a>
    <a href="https://bun.sh"><img alt="runtime Bun 1.4+" src="https://shieldcn.dev/badge/runtime-Bun%201.4%2B-00D4AA.svg?variant=secondary&amp;font=geist-mono&amp;size=sm"></a>
  </p>

  <p>
    <a href="skills/"><img alt="20 canon skills" src="https://shieldcn.dev/badge/canon%20skills-20-00D4AA.svg?variant=secondary&amp;font=geist-mono&amp;size=sm"></a>
    <a href="#the-five-guards"><img alt="5 guards" src="https://shieldcn.dev/badge/guards-5-00D4AA.svg?variant=secondary&amp;font=geist-mono&amp;size=sm"></a>
    <a href="#surfaces"><img alt="8 agent surfaces" src="https://shieldcn.dev/badge/surfaces-8-00D4AA.svg?variant=secondary&amp;font=geist-mono&amp;size=sm"></a>
    <a href="#usage"><img alt="10 verbs" src="https://shieldcn.dev/badge/verbs-10-00D4AA.svg?variant=secondary&amp;font=geist-mono&amp;size=sm"></a>
  </p>
</div>

One binary — `ai-eng`, compiled with Bun — puts a governance floor under your AI coding agent: guards that deny a destructive tool call before it runs, a git floor that fires even when the agent is not involved, an executable contract per milestone, and a receipt for every execution. Your agent keeps writing the code in whatever editor it already runs in; `ai-eng` makes its failures expensive and its successes provable.

The floor is not a review of the output. It is a constraint on the run. A guard denial happens before the call executes, the contract refuses to execute until a human approves it, and a check that cannot run is red rather than silently green. Editing a markdown file turns none of it off: the only bypass is an override with a written reason and an expiry date.

Nothing is hosted: the payload is the binary, and the state is versioned files in your repository and in `~/.ai-engineering/`. The one outbound read is a daily anonymous registry version check, cached for 24 hours, silent when offline, and off with `notices = false` in `config.toml` or `AI_ENG_NO_UPDATE_NOTICES=1`.

## Table of Contents

- [Why](#why)
- [Install](#install)
- [Usage](#usage)
- [Surfaces](#surfaces)
- [The five guards](#the-five-guards)
- [The executable contract](#the-executable-contract)
- [The skill canon](#the-skill-canon)
- [Security](#security)
- [Development](#development)
- [Maintainers](#maintainers)
- [Contributing](#contributing)
- [Contributors](#contributors)
- [License](#license)

## Why

AI agents write code at machine speed and break things at the same speed: bypassed git hooks, silenced linters, contracts nobody approved, green checks that never ran. Tooling that reviews the output arrives after the damage; the floor sits under the agent's feet while it works.

Three verbs carry the product:

1. **Install** — `ai-eng init` writes the machine canon and the repository contract: `AGENTS.md`, `DECISIONS.md`, `config.toml`, `spec.html`, `plan.html`, and the git-hook shims.
2. **Guard** — `ai-eng chain` screens each tool call and denies the destructive ones, fail-closed.
3. **Prove** — one receipt per execution and a contract that must execute to pass turn "done" into a checkable claim.

Two documents carry the detail. [docs/recap.html](docs/recap.html) is the product as it stands — the repository, the guards, the executable contract, the skill canon, the surfaces, CI and the lifecycle, section by section. [docs/blueprint.html](docs/blueprint.html) is the original design document this line was built from.

Where each host reads its guard, and how a repo declares itself, is in [docs/global-carriers.md](docs/global-carriers.md).

Every artifact ai-engineering generates — `spec.html`, `plan.html`, a recap, a research page, an issue report, a design audit — renders in one design system: [skills/ai-design/references/artifact-design.md](skills/ai-design/references/artifact-design.md). The tokens are pinned by `bun test`, so a drifted artifact fails the build instead of shipping in its own palette.

## Install

The released binary needs no runtime and no package manager. Download the asset for your platform from [Releases](https://github.com/arcasilesgroup/ai-engineering/releases), then verify it before it runs:

```bash
AI_ENG_VERSION=v2.0.0-rc.1
base="https://github.com/arcasilesgroup/ai-engineering/releases/download/${AI_ENG_VERSION}"

curl -sSfL -o ai-eng "$base/ai-eng-darwin-arm64"        # linux-x64 · linux-arm64
curl -sSfL -o CHECKSUMS-SHA256.txt "$base/CHECKSUMS-SHA256.txt"   # darwin-x64 · windows-x64.exe · …

awk '$2=="ai-eng-darwin-arm64"{print $1"  ai-eng"}' CHECKSUMS-SHA256.txt | shasum -a 256 -c -

gh attestation verify ai-eng \
  --repo arcasilesgroup/ai-engineering \
  --signer-workflow arcasilesgroup/ai-engineering/.github/workflows/release.yml \
  --source-ref "refs/tags/${AI_ENG_VERSION}" \
  --deny-self-hosted-runners

install -m 0755 ai-eng "$HOME/.local/bin/ai-eng"
```

The checksum and the binary travel together, so the checksum alone proves nothing. `gh attestation verify` is what binds those bytes to the commit and the workflow that built them.

Built assets ship for `linux-x64`, `linux-arm64`, `linux-musl-x64`, `linux-musl-arm64`, `darwin-x64`, `darwin-arm64`, `windows-x64`, `windows-arm64`, each with an SBOM and a build-provenance attestation.

<details>
<summary>Building from source</summary>

Requires [Bun](https://bun.sh) ≥ 1.4.

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git
cd ai-engineering
bun install
bun run build        # → dist/ai-eng, skills and templates embedded
bun link             # expose ai-eng in PATH for testing in other repos
```

</details>

## Usage

```bash
cd my-project
ai-eng init          # installs the contract; creates a repo if you are outside one
ai-eng doctor        # health checks, plus a real adversarial payload fired at the guard chain
```

`init` is idempotent and interactive: outside a git repository it offers to create one; in an already-governed repository it offers to reinstall assets or exit. CI and scripts pass `--yes --surface <id>` for zero prompts.

Human verbs:

| Verb | Does |
|---|---|
| `init` | install governance: the machine canon and the repository contract |
| `doctor` | run the health checks, fire one adversarial payload, report receipt stats (`--gc` collects) |
| `config` | add or remove agent surfaces, and regenerate their adapters and mirrors |
| `update` | rewrite ai-eng's files from the installed binary — zero network |
| `upgrade` | show the changelog, confirm, hand the install to bun/npm |
| `uninstall` | revert ai-eng's files, keep yours: `AGENTS.md`, `DECISIONS.md`, spec and plan stay |

Machine verbs — called by hooks and CI, no human interface:

| Verb | Does |
|---|---|
| `chain <event>` | the guard dispatcher; reads the surface payload on stdin |
| `git <hook>` | the pre-commit, commit-msg and pre-push floor |
| `wrap test -- <cmd>` | test-output filter: failures grouped, noise dropped |
| `spec run\|open\|approve\|close` | the executable contract |

`ai-eng complete <shell>` serves shell completion for zsh, bash and fish through [tab](https://github.com/bombshell-dev/tab).

## Surfaces

One canonical payload is mirrored into every enabled surface. A surface's loop capability is measured, and the claim carries its evidence.

| Surface | Tier | Loop |
|---|---|---|
| Claude Code | core | native |
| Oh My Pi | core | native |
| OpenCode | core | native |
| Cursor | experimental | native |
| Codex | experimental | native |
| GitHub Copilot | best-effort | native |
| Pi | core | none |
| Zed | skills-only | none |

`ai-eng config --add <id>` enables a surface; `--remove <id>` disables it. The registry lives in `src/surfaces/surfaces.json`.

## The five guards

Each guard is compiled into the binary and writes a receipt on every denial, carrying the reason verbatim.

| Guard | Denies |
|---|---|
| `no-verify` | `--no-verify`, `git commit -n`, `HUSKY=0`, deleting `.git/hooks/`, repointing `core.hooksPath` — and silencing a check: `eslint-disable`, `@ts-ignore`, `# noqa`, `# nosec`, `NOLINTNEXTLINE` |
| `self-protect` | writes against anything that governs the agent: `.ai-engineering/`, the surface settings, the git hooks, the global canon, and `spec.html` once its sha256 is pinned |
| `injection` | reading a file whose text carries an instruction payload — denied before the model sees it — and acting on a fetched page that carries one |
| `loop` | the same call repeated, the same edit reverted, the same failure retried with the arguments tweaked; the thresholds live in `config.toml` |
| `wrap` | nothing: `wrap` rewrites a test command before it runs, so the filter prints the failures and drops the rest |

The only way to turn a guard off is an entry in `.ai-engineering/overrides.toml` with a `reason` and an `until` date. `doctor` reports every active override with the time it has left, and an expired entry re-arms the guard.

## The executable contract

`ai-eng init` writes two HTML files per milestone, and `ai-eng.lock` pins them:

- `spec.html` — **what** must hold: requirements, data contracts and acceptance gates.
- `plan.html` — **how** it gets there: ordered steps, their dependencies, and the risk points.

A contract nobody approved refuses to run: its sha256 must be pinned in `ai-eng.lock` by `ai-eng spec approve`. `ai-eng spec run` executes every gate and refuses an empty gate list, so a tick in a box is never evidence. `ai-eng spec close` re-runs what the artifact claims and closes the milestone.

## The skill canon

Twenty `ai-*` skills ship inside the binary and install once per machine into `~/.ai-engineering/skills/`, symlinked into each surface. They cover the delivery loop end to end — plan, build, verify, document, research — and every skill follows one contract: one `SKILL.md` per folder, English only, no machine paths.

Attribution for every upstream skill travels with the payload: [NOTICE.md](NOTICE.md) and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

## Security

The product is a security boundary, so an attack on it is a vulnerability. Report through the policy in [SECURITY.md](SECURITY.md); a guard bypass is critical by definition.

Two properties hold by construction: `update` never touches the network — it reinstalls what the binary you already installed carries — and the release assets are verified by attestation, not only by a checksum fetched from the same origin.

## Development

```bash
bun install
bun run build              # compile dist/ai-eng (skills and templates embedded)
bun test                   # unit + adversarial (oracle) + gates + arch
bun run lint               # oxlint
bun run typecheck          # oxlint --type-aware --type-check, the single type gate
bun scripts/gen-assets.ts  # regenerate src/assets.ts after touching skills/ or templates/
bun link                   # expose the local ai-eng for testing in other repos
```

`bun scripts/gen-assets.ts` is not optional after a payload change: the binary carries `src/assets.ts`, and a file that is not in it does not ship.

Versioning runs on [changesets](.changeset/README.md). Release is a dispatched workflow with two channels: `integration` ships a prerelease and the npm `next` dist-tag, `production` ships the latest release and the npm `latest` tag. Both channels build the eight cross-compiled binaries, the SBOM and the attestations.

## Maintainers

[Arcasiles Group](https://github.com/arcasilesgroup).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the repo rules, commit conventions and the changeset requirement. This project follows its [Code of Conduct](CODE_OF_CONDUCT.md).

## Contributors

<a href="https://github.com/arcasilesgroup/ai-engineering/graphs/contributors"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/contributors/arcasilesgroup/ai-engineering.svg?title=false&preset=transparent&border=false&mode=dark">
  <img alt="contributors" src="https://shieldcn.dev/contributors/arcasilesgroup/ai-engineering.svg?title=false&preset=transparent&border=false&mode=light">
</picture></a>

## License

[Apache-2.0](LICENSE) © Arcasiles Group — see [NOTICE.md](NOTICE.md) and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for third-party attribution.
