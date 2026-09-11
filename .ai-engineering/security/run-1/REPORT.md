# Security audit — run 1

**Target:** `arcasilesgroup/ai-engineering` at `da9aa4bf` (branch `main`, formerly `v2`).
**Scope:** the CI/CD and release surface the `ci-gate` milestone changed. Fired by the
repo's own `security` trigger (`.github/workflows/**`, `package.json`).
**Date:** 2026-09-11 · **Tools:** source reading plus executed reproductions
(`bun 1.4.2`, `git 2.50.1`, `gh 2.100.0`, `gitleaks 8.30.0`), and the live GitHub API
for the server-side state (action policy, branch protection, rulesets, environment,
the published release and its attestation certificate).

## Method

Six phases: reconnaissance (`architecture.md`), four parallel hunters by attack class
(supply chain · injection · privileges · business logic + wildcard), adversarial
validation by an agent that found none of the findings and was asked to **disprove**
them, then this report and `findings.json` (validated against
`references/report-schema.json` with the skill's own checker).

Of twenty-four candidates from the hunting pass, the ten most consequential went to
validation: **eight confirmed with an executed reproduction, two refuted.**

## Confirmed

| # | What | Severity | Reproduced as |
|---|---|---|---|
| LOGIC-001 | `ai-eng spec run` reports `ALL MET` **without executing a CHECK** when a committed `spec.html` has its boxes hand-ticked with typed evidence — the runner never passes `--recheck` | high | hand-ticked contract → `ALL MET (2 met)` exit 0, marker file never created; `--recheck` on the same file ran the check and created it |
| LOGIC-003 | A repository-committed `.env` sets `AI_ENG_HOME`, which selects the **gate executor** the governor runs — arbitrary code as the governor inside a client's CI | high | `.env` pointing at `.evil/` → `HIJACKED EXECUTOR ran` and `ALL MET` exit 0; the real `~/.ai-engineering` is denied by self-protect, the override is not covered |
| LOGIC-002 | A contract with **zero gates** is `ALL MET` for `spec run` (exit 0) and "not a contract" for `spec close` (exit 2) | medium | same file, same run, two verbs, opposite verdicts |
| AI-ENG-INJ-001 | The lock's `base_sha` is validated where it is **written** but not where it is **read**, so a PR can make `git diff` treat it as an option (`--output=<path>`) and overwrite an arbitrary file | medium | 28-byte canary became 8 bytes; `spec close` still exit 0; `--end-of-options` refuses it (exit 128, canary intact) |
| SC-01 | The client's `gh attestation verify … --repo` pins neither the **signer workflow** nor the **ref**, and release assets are replaceable (`immutable: false`) | medium | on the real release: `--repo` exit 0, `--signer-workflow …/check.yml` exit 1, `--source-ref refs/heads/main` exit 1 |
| OPEN-01 | Nothing binds a **published release** to the revision under review: the tag (or the dispatch ref) decides the bytes, and the required checks never see that commit | medium | live API: required checks gate merges to `main`, the environment gates the job, neither is compared with the released commit |
| FLOOR-01 | The pre-commit secret scan reads the **working tree**, not the staged blobs | low | staged private key + overwritten worktree → `pre-commit ✓` exit 0 and the key in the commit (the pre-push hook blocks the push) |
| PORT-01 | The planted workflow names `oven-sh/setup-bun`, an action **this project's own policy cannot run** — the documented cause of ten days of blind CI here | low | policy read live: GitHub-owned + ten patterns, no `oven-sh/*` |

## Refuted

- **macOS signing secrets inside the un-gated build job** — the secrets are scoped to
  the codesign step's environment, no untrusted code runs between them, and the material
  is worthless without the Apple account. Kept as a hardening note.
- **The git floor resolves `ai-eng`/`gitleaks` through `PATH`** — measured: git injects
  no repository-controlled directory into a hook's `PATH`, and the shims are not
  versioned, so a repository alone cannot shadow the governor. A hostile effective
  `PATH` is the developer's own configuration, not this repository's defect.

## Hardening notes (not findings)

`attestation-verify.log` proves the verifier ran, in a job that also publishes — it is
evidence of a step, not of provenance (the verifier is now pinned, see below).
`minimumReleaseAge` in `bunfig.toml` governs no CI install line: `--frozen-lockfile`
selects nothing, and the toolchain is installed by name. `npm install -g npm@11` in
`version.yml` floats a major inside a job that can publish. `version.yml` grants
`contents: write` to every step rather than to the one that needs it. The build matrix
holds `id-token: write` and `attestations: write` while running third-party build code;
a minimal attesting job would be tighter. Codesign deserves its own minimal job.

## What changed because of this run

The confirmed findings are fixed in the same session (see the commit that follows),
each with the smallest change that stops the reproduction:

- `spec run` passes `--recheck`; an empty gates block is refused with the closer's
  wording; `base_sha` is validated on read and `--end-of-options` precedes the revision.
- An `AI_ENG_HOME` that resolves inside the governed repository is ignored.
- The client's verify pins the signer workflow, the source ref and hosted runners.
- The planted workflow installs Bun from npm, so it names no third-party action.
- The publish job refuses a revision that is not an ancestor of `main`.
- The pre-commit scan reads the staged blobs.

## Coverage, honestly

One run does not find everything — the skill's own experience is roughly half of the
total across runs. **The guard chain (`src/chain/**`, `src/guards/**`) was out of scope
for this run** and deserves its own. Server-side state was read through the API but is
not versioned in this repository, so it can drift from what is written here.
