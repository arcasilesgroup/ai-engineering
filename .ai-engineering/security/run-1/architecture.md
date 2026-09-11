# Phase 1 — architecture, trust boundaries and input surfaces

Target: `arcasilesgroup/ai-engineering` at `da9aa4bf` (branch `main`, formerly `v2`).
Scope of this run: the CI/CD and release surface the `ci-gate` milestone changed. The
guard chain (`src/chain/**`, `src/guards/**`) is **out of scope for this run** and is
said so in the report; coverage improves with further runs.

## What the system is

A single Bun-compiled binary (`ai-eng`) that **plants** governance into a repository
(`init`), **enforces** it through hooks (`chain`, called by agent surfaces and by the
git floor), and **proves** it with receipts and contract gates (`spec run`). The binary
carries every skill and template inside itself; the product's own repository is
governed by the same binary (dogfooding).

## Components in scope

| Component | Path | Role |
|---|---|---|
| Our CI | `.github/workflows/{check,platforms,planted-e2e,release,version}.yml` | quality, 3-OS e2e, ephemeral proof, release, npm publish |
| The planted CI | `templates/ci.yml.tpl` | what a client repository receives as its merge gate |
| Toolchain installer | `scripts/toolchain.sh` | trivy/gitleaks/actionlint by download + publisher sha256 |
| Release path | `release.yml` (`build` → `publish`), `scripts/build.ts`, `scripts/release-flags.ts` | 8 cross-compiled binaries, checksums, SBOM, provenance attestations |
| Install path | `src/commands/{init,update,config,uninstall}.ts`, `src/install.ts`, `src/embed.ts` | writing files into a repository, the lock as ownership ledger |
| Contract | `src/spec/index.ts`, `src/spec/triggers.ts` | sha256-pinned `spec.html`, gates executed by `gate-check.mjs` |
| Git floor | `src/floor/{index,entry}.ts` + `.git/hooks/*` shims | commit-time checks on a developer machine |

## Trust boundaries

1. **The registry and the release page are not trusted.** The client's workflow
   downloads the governor from a pinned GitHub release, checks `sha256sum -c` against
   a manifest **from the same release**, then runs `gh attestation verify` against the
   repository's attestation store. The checksum alone is circular by construction; the
   attestation is the independent root.
2. **The repository's action policy is an input to "does this workflow run at all".**
   `allowed_actions: selected` = GitHub-owned plus ten patterns. A workflow naming
   anything else never starts (startup_failure, no logs) — this was the root cause of
   10 days of blind CI on `v2`.
3. **The lock file is untrusted input.** `.ai-engineering/ai-eng.lock` travels in the
   repository and is read by `install`/`update`/`uninstall`; it also carries the
   contract's pin (`spec_sha256`, `base_sha`) which installers must not drop.
4. **`spec.html` is trusted by design** — it is the human's approval, pinned by sha256
   at STOP 1, and its CHECK lines are shell the governor executes. The reviewed party
   is the same party who writes it; that is the product's trust model, not a defect,
   and any finding here must name the actor it escalates against.
5. **The git floor runs with the developer's credentials** on their machine, from
   `.git/hooks/*` shims that live outside version control (`git clone` does not carry
   them; `init`/`update` install them).
6. **The release environment is the human press**: one required reviewer,
   `can_admins_bypass: true`; the token in the CI jobs is scoped per job.

## Input surfaces

- Workflow inputs and contexts that reach a shell: `github.ref_name`, `github.base_ref`,
  `inputs.version`, matrix values (all moved to `env:` this milestone).
- `scripts/toolchain.sh` arguments (tool names) and the versions/checksums it embeds.
- The client's `AI_ENG_VERSION` (a workflow `env:`), and the release assets it resolves.
- `package.json` (`packageManager`, `repository`, `bin`, `files`), `bunfig.toml`.
- Files a repository can carry that the binary reads: `config.toml`, `overrides.toml`,
  `ai-eng.lock`, `arch.rules.json`, `spec.html`, `plan.html`, `AGENTS.md`, `.agents/**`.
- `AI_ENG_HOME` and the executable's own location (where the canon and the gate runner
  are looked up from).

## Prior runs

None: `.ai-engineering/security/` did not exist before this run. Two adversarial reviews
of the same milestone were commissioned earlier in the session (a simplicity review and
a supply-chain parity review against the v0.13.0 release); their output informed the
changes under audit, so **this run must not treat them as findings** — the validator in
Phase 3 is a different agent than the hunters, and any finding they share has to be
re-derived here from the code.
