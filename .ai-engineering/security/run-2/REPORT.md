# Security audit — run 2

**Target:** `arcasilesgroup/ai-engineering`, HEAD `8cf4983` (`chore(ai-eng): assets → 2.1.0`) **plus the uncommitted
working tree** — the global-carriers change set (`src/env.ts`, `src/chain/**`, `src/guards/**`, `src/surfaces/**`,
`src/floor/**`, `src/commands/**`, `src/install.ts`, `templates/**`, `skills/.chain-bundle/**`).
**Fired by:** the repo's own `security` trigger, for the global-carriers milestone.
**Date:** 2026-09-14 · **Technique:** read-only static audit — no product code was run, no payload was crafted, no network call was made.

## Method

Line-by-line source reading, with the harness's `read` / `grep` / `glob` tools only, against the repo's own milestone
spec (`.ai-engineering/spec.html`, work points 01-07, gates G1-G20), the previous audit
(`.ai-engineering/security/run-1`) and the repository's own fixtures (`tests/adversarial/**`, `scripts/proof-*.sh`).

**Nothing was executed against the product.** The audit ran no command on it, crafted no payload and made no network call, so every finding is a static derivation over
`path.join` / `readFileSync` / `writeFileSync` semantics, environment-variable precedence and the product's own tests;
`execution.instructions` in `findings.json` carries the exact reproduction a maintainer runs, and
`execution.expected_result` states what that reproduction would show before and after the fix. Each verdict is
`confirmed` on the strength of the code, not of a run.

**Line numbers** in `findings.json` are those of the audited revision (HEAD plus the working tree as it stood when the
findings were reported). The fixes below landed after the report, so a few of those lines have moved in the current
tree; where the fix is quoted, the quoted code was read back from the working tree before this report was written.

## Confirmed — 8 findings, with disposition

| # | rule_id | What it was | Severity | Disposition |
|---|---|---|---|---|
| 1 | `SEC-CARRIER-PATH-001` | The host-supplied session id reached the loop-guard state filename unvalidated: an id containing `../` made the first guarded call overwrite the user's own `~/.claude/settings.json` (or `~/.codex/hooks.json`, the machine carrier) with loop-state JSON | high | **fixed** — `stateFile()` in `src/guards/loop.ts` derives a sha256 filename, and `skills/.chain-bundle/ai-eng-chain.ts` is regenerated |
| 2 | `SEC-CARRIER-DESTROY-002` | `shimState()` reported `empty` for a template dir holding someone else's hooks, so `installTemplateDir` force-overwrote a person's `pre-commit` / `commit-msg` / `pre-push` | high | **fixed** — `src/floor/template.ts` now returns `theirs` for a present hook without our marker, so `writeShims` runs with `force=false` |
| 3 | `SEC-CARRIER-DESTROY-003` | `config --remove` (and unticking a surface) unlinked a **merged** settings carrier whole — `.cursor/hooks.json`, `.github/hooks/ai-eng.json` — taking the user's own entries with it, while printing that only ai-eng entries were removed | medium | **fixed** — `removeSurfaceFiles()` in `src/commands/config.ts` strips by marker and deletes only when nothing is left |
| 4 | `SEC-CARRIER-STATE-004` | The verdict cache landed in `<repo>/cache/verdicts` — unowned, not gitignored, holding guard messages with absolute machine paths, and staged by our own `git add -A`; `uninstall` never removed it | low | **fixed** — moved to `<repo>/.ai-engineering/cache/verdicts/`, and `.gitignore` now ignores `.ai-engineering/cache/` |
| 5 | `SEC-CARRIER-CONFIG-005` | `restoreTemplateDir` unset a global `init.templateDir` the user owned (when it had moved since init) and reported it as restored | low | **fixed** — `src/floor/template.ts` writes the recorded value back instead of unsetting |
| 6 | `SEC-CARRIER-WIRING-006` | `config --add` declared a surface in `config.toml` without writing any carrier, and reported the adapter as written: a governed repo silently unguarded on that host | low | **fixed** — `installSurfaceFiles()` in `src/commands/config.ts` writes the machine and repo carriers through the same functions `init` uses |
| 7 | `SEC-CARRIER-PATH-007` | The OMP and Pi machine carriers were installed at the hardcoded `~/.omp/agent` / `~/.pi/agent` while the hosts resolve their agent dir from `PI_CODING_AGENT_DIR`; `doctor` checked the same fixed path | low | **fixed** — `agentDirEnv` on the two registry rows, resolved by `carrierBase()` / `carrierPath()` in `src/surfaces/adapters.ts`, and `doctor` resolves through the same `carrierPath()` |
| 8 | `SEC-CARRIER-STRIP-008` | A user's own `$comment` string that merely contained the word `ai-eng` was deleted by `stripValue` on update or uninstall | low | **fixed** — `src/install.ts` matches our banner exactly (`value.startsWith(...)`) |

Every finding's full record — trace, conditions, execution, remediation, severity, confidence — is in
`findings.json`, validated against `references/report-schema.json` by the skill's own checker (`PASS: 8 findings valid`, exit 0).

**Where the disposition is recorded.** `report-schema.json` declares `remediation` with
`additionalProperties: false`, so a separate `fix` key is rejected by the validator the skill ships and by this
task's acceptance criterion. The disposition is therefore the first sentence of `remediation.strategy` on each
finding, in the form `SEC-CARRIER-... — FIXED. Disposition: ...`, followed by the code change that closed it and the
name of the regression test that holds it. The checker was not weakened to make room for the field.

## Fixed, in detail

- **`SEC-CARRIER-PATH-001`** — `stateFile()` in `src/guards/loop.ts` now derives the filename with
  `createHash("sha256").update(sessionId()).digest("hex").slice(0, 32)`, and `skills/.chain-bundle/ai-eng-chain.ts`
  (the in-process carrier that runs inside OMP / OpenCode / Pi) is regenerated with the same derivation — bundle line 730.
  Regression test: `tests/adversarial/governance-gate.test.ts`, *the session id cannot walk out of the state directory
  the guard writes to*.
- **`SEC-CARRIER-DESTROY-002`** — `shimState()` in `src/floor/template.ts` returns `theirs` for a present hook that
  lacks our marker, so `writeShims` runs with `force=false`, keeps the person's file and writes only our missing shims
  (status `joined`). Regression test: `tests/adversarial/carrier-merge.test.ts`, *a template dir the user already had
  keeps its own hooks, and gets ours beside them*.
- **`SEC-CARRIER-DESTROY-003`** — `removeSurfaceFiles()` in `src/commands/config.ts` strips by marker with
  `stripSharedText`, deletes the file only when nothing is left in it, and warns when the file cannot be rewritten.
  Regression test: `tests/adversarial/carrier-merge.test.ts`, *config --remove takes our entries out of a shared file
  and keeps the user's*.
- **`SEC-CARRIER-STATE-004`** — the cache path in `src/chain/mod.ts` is now
  `<repo>/.ai-engineering/cache/verdicts/<sha256>.json`, and `.gitignore` ignores `.ai-engineering/cache/` beside
  `.ai-engineering/receipts/`, so our own `git add -A` no longer stages it. Asserted by the *debt closed* test in
  `tests/adversarial/governance-gate.test.ts`.
- **`SEC-CARRIER-CONFIG-005`** — the recorded value is written back (`gitConfig(["init.templateDir", previous])`)
  instead of being unset, so the report and the action agree.
- **`SEC-CARRIER-WIRING-006`** — `installSurfaceFiles()` writes the machine carrier (and the repo carrier) for an
  added surface through the same functions `init` uses, so *adapter + skill mirror written* is now true.
- **`SEC-CARRIER-PATH-007`** — the `oh-my-pi` and `pi` rows carry `agentDirEnv: "PI_CODING_AGENT_DIR"`, and
  `carrierBase()` / `carrierPath()` resolve the carrier through it (stripping the `.omp/agent` / `.pi/agent` prefix when
  the host's agent dir already is that directory); `doctor` verifies the same resolution.
- **`SEC-CARRIER-STRIP-008`** — `stripValue` matches our banner with `value.startsWith("Generated by ai-eng")`
  instead of a substring test on the word, and its comment records why.

## Accepted, with reason

Two behaviours were left as they are, deliberately, and are **not** findings:

**(a) Our template's top-level scalars are not removed by the strip.** A merged settings file keeps the `version`,
`failClosed` and description values our template declares, because removing a key whose value happens to equal ours
would delete a key the user wrote themselves — a `version` their host requires, which is a broken file rather than a
restored one — and telling the two apart would need a ledger of what each merge added. The reasoning is written into
`stripValue`'s comment in `src/install.ts`; the entries are what matter, and those are exact.

**(b) The merge refuses a file it cannot reproduce byte-for-byte.** `shapeOf()` in `src/install.ts` accepts a file's
indentation, line endings and trailing newline only when this code can regenerate the file's bytes exactly with them
(`serialize(parsed, shape) === text`); compact one-liners, CRLF and anything else it cannot reproduce byte-for-byte is
refused rather than reformatted, and the refusal is surfaced to the user with a warning. This is the milestone's own
rule — nothing foreign is touched, and nothing foreign is reformatted — so it is correct behaviour, not a defect.

## Checked and found clean

Read-only source audit of the global-carriers change set (HEAD = 8cf4983 "chore(ai-eng): assets → 2.1.0" plus the uncommitted working tree, identified from .git/logs/HEAD and file mtimes: src/env.ts, src/chain/**, src/guards/**, src/surfaces/**, src/floor/**, src/commands/**, src/install.ts, templates/**) against the repo's own milestone spec (.ai-engineering/spec.html work points 01-07, gates G1-G20) and the previous audit (.ai-engineering/security/run-1). Technique: line-by-line source reading with `read`/`grep`/`glob` only — this session has no shell tool, so no command was executed; every claim below is a static derivation from the code plus the repo's own fixtures, and each finding states the reproduction a maintainer can run. 8 findings: 1 high (unvalidated session id reaching a loop-state filename), 1 high (a pre-existing init.templateDir's own hooks are force-overwritten), 3 medium/low (config --remove deletes a shared settings carrier whole; the verdict cache lands in an unowned, un-swept, git-committable path; restoreTemplateDir unsets a user's global init.templateDir), 3 low (config --add declares a surface without writing its carrier; the OMP/Pi carrier path ignores PI_CODING_AGENT_DIR; a user $comment containing "ai-eng" is deleted). Deliberately NOT reported, and why: a repository-scope hook file (.claude/settings.json, .cursor/hooks.json) that runs arbitrary commands is code execution by the host's own design, not an ai-eng defect; an empty stdin payload allowing (src/chain/mod.ts chainMain) is only reachable by the host that writes the payload; a hostile repo can switch guards off through .ai-engineering/overrides.toml by design (readOverrides); `[surfaces] enabled = []` is governed-but-guardless by the spec's own F2 semantics and is not reachable through any verb (the picker is required:true); a corrupt/absent/symlinked config.toml fails to the intended fail-open (declaration() catches, readFileSync follows symlinks and the gate stays the parsed declaration); cachedVerdict poisoning is not reachable because the fingerprint includes a host-generated tool_use_id and, without it, dedup is disabled; the JSON round trip refuses anything shapeOf cannot reproduce byte-for-byte, including duplicate keys, comments, compact and CRLF forms.

*(The paragraph above is quoted verbatim from the audit's own coverage summary, written in the read-only session that produced the findings. The only commands this run executed are the two that write and check these artifacts — a node build script and the skill's own validate-findings.cjs — and both touch nothing outside .ai-engineering/security/run-2/.)*

## Reviewed paths

- `src/env.ts`
- `src/chain/mod.ts`
- `src/chain/payload.ts`
- `src/chain/dialect.ts`
- `src/guards/loop.ts`
- `src/guards/self-protect.ts`
- `src/guards/injection.ts`
- `src/install.ts`
- `src/surfaces/adapters.ts`
- `src/surfaces/surfaces.json`
- `src/floor/template.ts`
- `src/floor/entry.ts`
- `src/commands/init.ts`
- `src/commands/update.ts`
- `src/commands/uninstall.ts`
- `src/commands/config.ts`
- `src/commands/doctor.ts`
- `src/commands/init-shared.ts`
- `src/cli.ts`
- `src/receipts.ts`
- `skills/.chain-bundle/ai-eng-chain.ts`
- `templates/git-pre-commit.tpl`
- `templates/git-commit-msg.tpl`
- `templates/git-pre-push.tpl`
- `templates/settings.claude.json.tpl`
- `templates/settings.codex.json.tpl`
- `templates/settings.copilot.json.tpl`
- `templates/settings.copilot.cli.json.tpl`
- `templates/settings.cursor.json.tpl`
- `templates/plugin.omp.ts.tpl`
- `templates/plugin.opencode.ts.tpl`
- `templates/plugin.pi.ts.tpl`
- `scripts/proof-carriers.sh`
- `scripts/proof-cli-ux.sh`
- `tests/adversarial/governance-gate.test.ts`
- `tests/adversarial/carrier-merge.test.ts`
- `.ai-engineering/spec.html`
- `.ai-engineering/security/run-1/findings.json`
- `.ai-engineering/security/run-1/REPORT.md`
- `docs/global-carriers.md`
- `.gitignore`
- `.git/logs/HEAD`

## What this run did not do

- **Nothing was executed.** No reproductions were run, no payloads were crafted, no bytes were written outside the two
  artefact files. Two consequences are recorded in `findings.json`'s `deferred` list of the audit itself: the two
  path-traversal writes (`SEC-CARRIER-PATH-001`) and the template-dir overwrite (`SEC-CARRIER-DESTROY-002`) were
  derived from `path.join` / `writeFileSync` semantics and the repo's own fixtures rather than observed, and the
  per-host breadth of the `AI_ENG_SESSION` route was not measured.
- **Server-side state was out of scope** for this run: the audit covers the diff of HEAD plus the working tree in this
  repository, not the GitHub configuration around it (run 1 covered that surface).
- **`PI_CODING_AGENT_DIR` behaviour was read from the repo's own carrier table and proof script**, not measured against
  an installed OMP or Pi, which is why `SEC-CARRIER-PATH-007` carries `confidence: medium`.
- **Reachability of the `AI_ENG_SESSION` route depends on each host merging a repository `.env` into its own process**
  — proved for the `ai-eng` binary itself by run 1's `LOGIC-003`, not verified per host here.
