---
total: 109
completed: 14
spec: spec-193
title: "Personal Host Security and Zero-Third-Party-MCP Cutover — execution plan"
status: approved
pipeline: full
phases: 10
execution_route:
  version: 1
  spec: spec-193
  executor: build
  automation: hitl
  concern_count: 8
  estimated_files: 70
  reason: "Safety override: the large surface normally meets /ai-autopilot thresholds, but per-credential human checkpoints, irreversible revocation, strictly serial provider lanes, dirty-worktree reconciliation, and restarting the active host match /ai-autopilot's explicit manual-checkpoint exclusion. Execute through supervised /ai-build only."
  safe_next_command: "/ai-build"
---

# Plan — spec-193: Personal Host Security and Zero-Third-Party-MCP Cutover

Pipeline classification: **full**. Execution is deliberately **supervised and
serial**. `/ai-autopilot` is not safe for this migration even though the file
and concern counts exceed its normal threshold: the workflow requires human
review between credential states and must interrupt the active agent host.

## Findings

### Known

- The approved lifecycle sidecar is `spec-193`; the working spec is approved.
- Claude Code, Codex, OpenCode, Pi, Cursor, Copilot CLI, VS Code/Copilot, and
  Antigravity are installed and runnable. Gemini and Kiro are residual-only;
  Gemini configuration is shared with Antigravity.
- Third-party MCP is reachable or prescribed through host configuration,
  hooks, plugins, rules, skills, memories, generated mirrors, project docs,
  and the canonical `ai-research`/`ai-media` workflows.
- Codex may retain only the exact identities for `node_repl`, the
  OpenAI-bundled Sites design picker, and OpenAI-curated GitHub.
- Credential/state ACLs are unsafe under Engram, Railway, OpenCode, Cursor,
  and Gemini. Context7 credentials in Cursor and Gemini extend the initial
  credential ledger and must be classified without assuming shared values or
  ownership. Native private `opencode-go` auth is out of the rotation set
  unless discovery proves actual exposure, in which case execution stops for
  re-plan.
- Railway resolves to a vendor binary while a newer Homebrew binary exists;
  Claudeline has npm plus an untrusted Homebrew tap; Copilot's cask receipt and
  self-updated runtime disagree.
- The repository worktree already contains extensive unrelated changes.
  `.claude/settings.json`, OpenCode mirrors, and the untracked Cursor surface
  overlap this scope and must be reconciled, never overwritten.
- `python` is absent from normal PATH; all Python tasks use `uv run python`.

### Assumed

- None. Issuer access, token class, daemon ownership, and revocation support
  are readiness gates recorded as evidence, not assumptions.

### Known execution blockers

- The owner and full consumer set of the Engram process listening on
  `127.0.0.1:7437` are not yet attributed.
- Claude gateway, `nan-builders`, and Engram lifecycle control are not yet
  proven.
- A neutral terminal must be available to restart and verify the active host.

Any unresolved blocker stops before the first credential replacement. It is
not accepted as residual risk and does not permit a partial-success verdict.

## Design

Design intent is captured at
`.ai-engineering/specs/spec-193/design-intent.md`. The conservative router
matched `component`, `dashboard`, `form`, and `ui`; the applicable design is
the fail-loud terminal interaction for two per-credential checkpoints, not a
graphical interface.

## Architecture

**Ports and Adapters with an explicit local state machine.** A one-shot,
non-autoloaded runner under `.ai-engineering/scripts/spec-193/` owns pure
schema/FSM/redaction logic. Host configuration, filesystem, process, CLI, and
provider operations are adapters. Synthetic fixtures exercise adapters without
real credentials or home-directory writes.

The canonical private bundle is
`STATE_ROOT=${XDG_STATE_HOME:-$HOME/.local/state}/agent-cli/spec-193`:

- `manifest.json` — the only mutable structured truth for surfaces,
  credentials, deletions, CLI ownership, checkpoints, and current states;
- `receipts.ndjson` — append-only evidence whose records use exactly the
  D-193-08 allowlist, never a second state store;
- `runbook.md` — values-free human projection generated from this approved
  plan.

The directory is owner-only `0700`, files are `0600`, and no destination may
be a symlink. `.ai-engineering/runtime/audits/spec-193-handoff.json` is a
sanitized, rebuildable projection; runtime is never the primary witness.

Every receipt record contains exactly these D-193-08 fields: credential alias,
provider, CLI version, probe ID, exit code, timestamp, redacted-field count, and
invalidation-evidence reference. The probe ID encodes the checkpoint/transition
kind; manifest state maps it to the credential row. Raw stdout/stderr,
operation/result fields, manifest references, chain pointers, account/workspace
IDs, endpoints, secret values, prefixes/suffixes, argv secrets, and
secret-derived hashes are forbidden.

Transition commit order is fixed under one lock: validate expected state and
postcondition; append and `fsync` the exact-schema transition receipt;
atomically compare-and-swap `manifest.json` with the receipt byte offset/hash,
ordered hash index, and row mapping kept only in manifest state; release the
lock. A crash after receipt append but before manifest rename leaves an orphan
line. Resume must verify the real postcondition and either index that exact line
or append a schema-valid reconciliation probe receipt; it never repeats an
irreversible provider action automatically.

When an old credential is needed for a negative probe, the runner reads it
from the privately contained source or OS credential quarantine into a locked
one-shot memory buffer before writing secret-free config. A quarantine move is
a recoverable two-phase transfer under the same lock: create and verify a
`pending` credential-manager item through a non-echoing prompt/native channel,
atomically remove the source field, then mark the item active. Resume detects
the temporary both-present state and completes source removal; no successful
terminal state may retain two durable copies. After checkpoint two the runner
performs the provider revocation and bounded rejection probe from that buffer
without shell, argv, stdout, temp, or persistence, then releases it
best-effort. A semantically verified issuer revocation receipt may replace the
negative request where D-193-06 allows it.

## Dependencies Discovered

- Repository canonical changes precede targeted mirror generation. Never edit
  generated mirrors first and never run global sync over an unreviewed dirty
  OpenCode/Cursor diff.
- Direct `engram`, `railway`, `notebooklm`, and `ctx7` continuity must pass
  after reachability containment and before permanent integration deletion.
- All checkpoint-one capability rows must pass before any replacement is
  created, preventing an early provider success followed by a permanently
  blocked lane.
- Provider lanes run one at a time in this fixed order: Claude gateway,
  OpenRouter, `nan-builders`, Railway, Engram, Cursor Context7, then Gemini
  Context7. Native private `opencode-go` auth is preserved unless discovery
  proves exposure; a newly exposed lifecycle requires re-plan before mutation.
- Railway ownership is resolved before its new-auth probe. Engram process
  ownership is resolved before DB/WAL/SHM validation.
- The active agent host is restarted last from a neutral terminal and resumes
  only from the persisted manifest/receipt index.

## Scope guard for the next spec

This plan MUST NOT create `agent-cli-skills`, a skill router/registry/resolver,
CLI leaf skills, benchmarks, or any new `SKILL.md`; invoke `skills add`/`skills
use`; or propagate the future private skill fleet. Phase 4 may edit existing
canonical operational skills only to remove their MCP dependency. It may
remove only the allowlisted MCP-first families `context7-mcp`,
`notebooklm-mcp`, and `use-railway`. The `skills` binary, NotebookLM CLI
workflow, unrelated skills, and the three Codex vendor components must survive.

## Decision coverage

| Decisions | Plan phases |
|---|---|
| D-193-01, D-193-02, D-193-03 | 0, 1, 4, 5, 8 |
| D-193-04, D-193-05 | 1, 3, 4, 5, 8 |
| D-193-06, D-193-07, D-193-08 | 0, 1, 2, 3, 6, 9 |
| D-193-09 | 1, 3, 5, 8 |
| D-193-10 | 0, 1, 3, 6, 8, 9 |
| D-193-11 | 1, 3, 7 |
| D-193-12 | 0, 1, 3, 4, 5, 7 |
| D-193-13 | 0, 1, 5, 6, 8, 9 |
| D-193-14 | 8, 9 |

## Phase 0 — RED/GREEN safety harness

- [x] T-0.0 — Freeze the dirty-worktree baseline before any repository edit — DONE (209-entry values-free external baseline validated; HEAD advanced through three approved checkpoint commits with 0 unowned overlaps and 0 candidate overwrites; preserve the original baseline until T-4.9; never recapture it)
  - Agent: guard
  - Files: `$STATE_ROOT/manifest.json`; path-only/hash metadata for the current worktree and generated surfaces
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Procedure (judgment-bound): before creating tests, runner code, documentation, or any other repository edit, create the owner-only external state root with `umask 077`; record path-only hashes, canonical/generated ownership, pre-existing untracked paths, and the exact candidate-overwrite set without file content or secret-bearing diffs. This minimal manifest is upgraded in T-1.1 without replacing the baseline.
  - Gate: the operator approves the exact owner/overwrite set; any unowned overlap blocks repository work and every unrelated dirty hash becomes an immutable postcondition.

- [x] T-0.1 — RED: pin values-free manifest and receipt schemas — DONE (15 focused contract tests fail only because the isolated runner does not yet exist; static checks and no-suppression pass)
  - Agent: build
  - Files: `tests/unit/scripts/test_spec_193_security_cutover.py` (new)
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Implementation (judgment-bound): add failing synthetic tests requiring exactly credential alias, provider, CLI version, probe ID, exit code, timestamp, redacted-field count, and invalidation-evidence reference; reject every extra field, absolute personal path, account/workspace/endpoint field, secret canary, secret-derived hash, and raw stream.
  - Gate: `uv run pytest tests/unit/scripts/test_spec_193_security_cutover.py -k 'schema or redaction' -q` fails RED because the runner does not exist.

- [x] T-0.2 — GREEN: implement private-store schema, sanitizer, and durable writers — DONE (manifest-specific validation, lock-held receipt fsync→offset/hash→CAS, and fail-closed no-follow parent traversal are GREEN: 20 focused tests, Ruff, Ty, and no-suppression pass)
  - Agent: build
  - Files: `.ai-engineering/scripts/spec-193/security_cutover.py` (new)
  - Principles applied: §10.1 KISS, §10.4 DRY, §10.8 Hexagonal Architecture
  - Implementation (judgment-bound): implement stdlib-only dataclasses/validators, `$HOME` path normalization, exact-schema receipts, `fcntl` locking, manifest-owned receipt offset/hash indexing, `umask 077`, `fsync` plus atomic rename, `lstat` owner/symlink checks, and no logging of input values.
  - Gate: T-0.1 is GREEN; synthetic canaries do not appear in captured output or files.

- [x] T-0.3 — RED: pin the exact credential FSM and serial-lane lock — DONE (15 focused FSM contracts now RED only because the T-0.4 API/state machine is absent; Ruff passes)
  - Agent: build
  - Files: `tests/unit/scripts/test_spec_193_security_cutover.py`
  - Principles applied: §10.5 TDD, §10.3 SOLID
  - Implementation (judgment-bound): add failing tests for every legal next state, skipped transitions, blocked rows, missing checkpoint IDs, stale config hashes, concurrent provider mutation, idempotent resume, receipt-first crash/orphan reconciliation, interrupted source-to-quarantine transfers, one-shot old-witness buffers, semantic issuer receipts, and `revoke+delete` rows with no future consumer.
  - Gate: focused FSM tests fail RED until transition enforcement exists.

- [x] T-0.4 — GREEN: enforce state transitions, checkpoints, and fail-stop resume — DONE (exact FSM, checkpoint/config-hash gates, serial provider guard, blocked-lane stop, idempotent resume, orphan reconciliation, quarantine recovery, and one-shot witness are GREEN: 36 focused tests)
  - Agent: build
  - Files: `.ai-engineering/scripts/spec-193/security_cutover.py`
  - Principles applied: §10.3 SOLID, §10.7 Clean Code
  - Implementation (judgment-bound): enforce `DISCOVERED → SOURCE_CONTAINED → TARGET_READY → NEW_AUTH_OK → CONFIG_CUTOVER → OLD_INVALID → POSTCHECK`, one global provider lock, expected-state/config-hash compare-and-swap, dry-run default, and `--apply --checkpoint-id` for mutation.
  - Gate: T-0.3 is GREEN; a failed row prevents selection of the next provider.

- [x] T-0.5 — RED: pin safe subprocess, command-policy, ACL, and timeout behavior — DONE (13 synthetic policy contracts are RED because bounded probe and ACL APIs are absent; Ruff passes)
  - Agent: build
  - Files: `tests/unit/scripts/test_spec_193_security_cutover.py`
  - Principles applied: §10.5 TDD, §10.2 YAGNI
  - Implementation (judgment-bound): add fake CLIs and credential-manager adapters that leak canaries to streams/argv, exceed 64 KiB, time out, spawn children, fail between quarantine create/source removal, or request `ctx7 setup`, `mcp`, `setup agent`, shell execution, env dumps, or secret argv.
  - Gate: runner-policy tests fail RED.

- [x] T-0.6 — GREEN: implement bounded no-shell probes and ACL validation — DONE (explicit executable allowlist, shell/MCP/env/secret-argv denial, DEVNULL output discard, process-group timeout kill, 64 KiB cap, and fail-closed ACL inspection with bounded native macOS fallback: 62 focused tests GREEN)
  - Agent: build
  - Files: `.ai-engineering/scripts/spec-193/security_cutover.py`
  - Principles applied: §10.1 KISS, §10.8 Hexagonal Architecture
  - Implementation (judgment-bound): use argument arrays with `shell=False`, bounded in-memory parsing or `DEVNULL`, process-group timeout/kill, no argv secrets, command denylist, owner/no-symlink/parent-traversal/extended-ACL checks, non-echoing OS credential-manager prompt/native adapters, best-effort locked one-shot buffers, and explicit result booleans only.
  - Gate: T-0.5 is GREEN; no fake secret survives in output, receipts, temp files, or process argv.

- [x] T-0.7 — RED: pin host closure, survivor, restart, and handoff contracts — DONE (5 synthetic integration contracts are RED because discovery/preview/restart/export adapters are absent; Ruff passes)
  - Agent: build
  - Files: `tests/integration/test_spec_193_security_cutover.py` (new)
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Implementation (judgment-bound): build fixture trees for every declared host state, shared roots, symlinks, generated residue, Codex identity mismatches, dirty-worktree overlaps, skill survivors, crash/resume, and regenerated MCP after simulated restart.
  - Gate: integration tests fail RED until discovery/export adapters exist.

- [x] T-0.8 — GREEN: implement discovery, preview, recovery, and derived export adapters — DONE (bounded synthetic closure scan, exact Codex identities, no-write deletion preview, restart-regeneration detection, and terminal values-free handoff export are GREEN: 56 focused tests)
  - Agent: build
  - Files: `.ai-engineering/scripts/spec-193/security_cutover.py`
  - Principles applied: §10.3 SOLID, §10.8 Hexagonal Architecture
  - Implementation (judgment-bound): add read-only host/config/package/process scanners, deletion preview with expected survivors, class-specific recovery IDs, restart evidence epochs, exact Codex identity matching, and handoff export allowed only from terminal manifest states.
  - Gate: T-0.7 is GREEN; unknown integrations and incomplete rows block export.

- [x] T-0.9 — Prove the one-shot runner is unreachable from agent autoload — DONE (2 architecture assertions pass: no autoload surface references runner/state root and no runner SKILL.md/CLI registration exists)
  - Agent: verify
  - Files: `tests/architecture/test_spec_193_cutover_isolation.py` (new), `.ai-engineering/scripts/spec-193/`
  - Principles applied: §10.2 YAGNI, §10.4 DRY
  - Procedure (read-only): assert no bootstrap, hook, skill, plugin, template, mirror generator, CLI entry point, package manifest, or install surface references the runner or private state root.
  - Gate: targeted architecture test passes and `find` reports no new `SKILL.md`.

- [x] T-0.10 — Declare the external private canonical store and tracking boundary — DONE (persistence doctrine now defines the external values-free SoT and derived handoff; 4 isolation/status assertions pass)
  - Agent: build
  - Files: `docs/persistence-doctrine.md`, `tests/architecture/test_spec_193_cutover_isolation.py`
  - Principles applied: §10.6 SDD, §10.4 DRY
  - Implementation (judgment-bound): document the external per-operator bundle as the canonical values-free migration witness and the runtime handoff as a derived rebuildable projection; assert the external state root can never become a repository install/template/autoload path.
  - Gate: doctrine names one writable store per datum; `git status --short` never lists private receipts or manifests.

- [x] T-0.11 — Run the preflight code-quality gate before real discovery — DONE (60 focused tests, Ruff, Ty, Semgrep, Gitleaks, synthetic-canary containment, and governed gate are GREEN with 0 findings)
  - Agent: verify
  - Files: `.ai-engineering/scripts/spec-193/security_cutover.py`, `tests/unit/scripts/test_spec_193_security_cutover.py`, `tests/integration/test_spec_193_security_cutover.py`
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Procedure (read-only): none; run targeted pytest, Ruff, Ty, Semgrep, gitleaks, and a synthetic canary sweep.
  - Gate: all targeted checks pass; any leak or suppression marker blocks Phase 1.

## Phase 1 — Closed discovery, deletion preview, and baseline RED

- [x] T-1.1 — Upgrade and validate the canonical private bundle — DONE (immutable baseline preserved; private bundle upgrade and fresh-process validation pass)
  - Agent: build
  - Files: `${XDG_STATE_HOME:-$HOME/.local/state}/agent-cli/spec-193/{manifest.json,receipts.ndjson,runbook.md}`
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Implementation (judgment-bound): validate the minimal bundle created by T-0.0 with `lstat`, preserve its immutable dirty-worktree baseline, then atomically upgrade the manifest schema and seed approved host/credential enums plus runner hash without values or personal identity; create missing `receipts.ndjson`/`runbook.md` only under the existing safe root.
  - Gate: T-0.0 hashes are unchanged, root is `0700`, files `0600`, parent traversal is safe, and store validation passes from a fresh process.

- [x] T-1.2 — Manifest Claude, Codex, OpenCode, and Pi surfaces — DONE (11 values-free user/project/shared/generated loader rows; unknown generated rows remain blocking)
  - Agent: build
  - Files: `$STATE_ROOT/manifest.json`; `$HOME/.claude/**`; `$HOME/.codex/**`; `$HOME/.config/opencode/**`; `$HOME/.pi/**`; `$REPO/.mcp.json`; `$REPO/.claude/settings.json`
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): read-only discovery records sanitized path/pattern, loader, owner, mode/ACL, hash of redacted structure, component/version, state, reachability, and proposed action.
  - Gate: all four declared rows exist; generated state and project/user/shared loaders are distinct.

- [ ] T-1.3 — Manifest Cursor, Copilot CLI, VS Code/Copilot, and shared roots
  - Agent: build
  - Files: `$STATE_ROOT/manifest.json`; `$HOME/.cursor/**`; `$HOME/.copilot/**`; `$HOME/Library/Application Support/Code/User/**`; `$HOME/.agents/**`
  - Principles applied: §10.6 SDD, §10.4 DRY
  - Implementation (judgment-bound): inventory each loader separately and record every physical `context7-mcp`, `notebooklm-mcp`, and `use-railway` bundle plus unrelated-skill survivor hashes.
  - Gate: Copilot CLI and VS Code/Copilot are separate rows; shared-root consumers include Pi and every active host.

- [ ] T-1.4 — Manifest Antigravity, Gemini, Kiro, shell, service, and process surfaces
  - Agent: build
  - Files: `$STATE_ROOT/manifest.json`; `$HOME/.gemini/**`; `$HOME/.kiro/**`; shell startup files; LaunchAgents/services; resident-process metadata
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Implementation (judgment-bound): classify Antigravity runnable, Gemini residual/shared, Kiro residual-only, and every alias/export/service/process without printing command lines containing values.
  - Gate: every declared surface has one of `installed+runnable`, `installed+broken`, `residual-only`, or `shared-root`; unknown ownership blocks.

- [ ] T-1.5 — Pin the exact Codex exception identities
  - Agent: build
  - Files: `$STATE_ROOT/manifest.json`; `$HOME/.codex/config.toml`; Codex plugin/app metadata
  - Principles applied: §10.6 SDD, §10.2 YAGNI
  - Implementation (judgment-bound): record component ID, publisher, channel, version/hash, and pre-cutover identity for `node_repl`, OpenAI-bundled Sites, and OpenAI-curated GitHub; classify disabled `computer-use` as forbidden.
  - Gate: exactly three exception rows match; name-only or identity-mismatched components block.

- [ ] T-1.6 — Build the values-free credential and disposition ledger
  - Agent: build
  - Files: `$STATE_ROOT/manifest.json`; audited config/auth/log/backup patterns
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Implementation (judgment-bound): create exactly seven planned rows for Claude gateway, OpenRouter, `nan-builders`, Railway, Engram, Cursor Context7, and Gemini Context7; classify native private `opencode-go` as preserve-only metadata, not a credential lane; add newly found rows only by alias/key/presence and stop for re-plan if any newly exposed lifecycle is outside this plan.
  - Gate: every planned source has mode/owner/symlink metadata, future consumer, disposition, destination class, recovery ID, and no value/digest/identity; exposed `opencode-go` or any eighth lifecycle blocks.

- [ ] T-1.7 — Build the deletion manifest, inverse patches, and survivor set
  - Agent: build
  - Files: `$STATE_ROOT/manifest.json`; all proposed config/plugin/skill/package removals
  - Principles applied: §10.1 KISS, §10.4 DRY
  - Implementation (judgment-bound): preview sanitized path/pattern, class, owner/generator, symlink target, redacted-structure hash, owner-native uninstall, expected survivor, inverse patch for non-secret config, and exact reinstall/recovery command.
  - Gate: no secret-bearing backup is created; unrelated skills/caches and the `skills` binary appear in the required survivor set.

- [ ] T-1.8 — Inventory direct CLIs and executable ownership before mutation
  - Agent: build
  - Files: `$STATE_ROOT/manifest.json`; executable/package metadata for `engram`, `railway`, `notebooklm`, `ctx7`, Claudeline, and Copilot
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Implementation (judgment-bound): record all paths, realpaths, runtime/package versions, owners, consumers, auth class, feature/help capability, and exact recovery command; no package receipt may masquerade as the executed binary.
  - Gate: Railway dual paths, Claudeline npm/untrusted-tap conflict, and Copilot receipt/runtime drift are explicit rows.

- [ ] T-1.9 — Record the real baseline as an expected RED gate
  - Agent: verify
  - Files: `$STATE_ROOT/manifest.json`
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Procedure (read-only): run the full read-only closure/ACL/secret-key-presence/CLI ownership validator; persist counts and row references only.
  - Gate: baseline fails for the known MCP, ACL, literal-key, duplicate-owner, and injection findings; any unclassified row is marked blocking for Phase 2, while T-1.10…T-1.18 still perform fail-closed containment.

- [ ] T-1.10 — Immediately contain Claude gateway credentials and consumers
  - Agent: build
  - Files: `$HOME/.claude/settings.json`, Claude gateway quarantine item, Claude process/loader rows, `$STATE_ROOT/{manifest.json,receipts.ndjson}`
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): under the provider lock, stop Claude consumers, harden the source, move each exposed gateway value through the recoverable two-phase OS-credential quarantine channel, atomically remove only its literal config field, and apply values-free inverse patches that detach every Claude/MCP loader capable of using it. Do not create or revoke a credential.
  - Gate: `claude.gateway.primary` reaches `SOURCE_CONTAINED` only when one private old witness remains, the source is secret-free, no Claude agent/MCP consumer can use it, and recovery metadata is durable.

- [ ] T-1.11 — Immediately contain the OpenRouter credential and consumer paths
  - Agent: build
  - Files: `$HOME/.config/opencode/opencode.json`, `$HOME/.local/share/opencode/auth.json`, OpenRouter quarantine item, OpenCode process/loader rows, `$STATE_ROOT/{manifest.json,receipts.ndjson}`
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): stop OpenCode consumers; transfer only the exposed OpenRouter literal into its owner-only quarantine item; remove only its literal `options.apiKey` field; detach MCP/plugin/autoload access through values-free inverse patches; preserve the `nan-builders` source for T-1.12 and all unrelated native auth including `opencode-go`.
  - Gate: `opencode.openrouter.primary` reaches `SOURCE_CONTAINED` with one witness, no OpenRouter literal in general config, zero agent/MCP use, and unchanged non-OpenRouter auth hashes.

- [ ] T-1.12 — Immediately contain the `nan-builders` credential and consumer paths
  - Agent: build
  - Files: `$HOME/.config/opencode/opencode.json`, `$HOME/.local/share/opencode/auth.json`, `nan-builders` quarantine item, OpenCode process/loader rows, `$STATE_ROOT/{manifest.json,receipts.ndjson}`
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): with OpenCode still stopped, transfer only the exposed `nan-builders` literal into its distinct owner-only quarantine item, remove only that literal `options.apiKey` field, and verify the T-1.11 inverse patches still prevent plugin/MCP/autoload access; preserve every unrelated auth row.
  - Gate: `opencode.nan-builders.primary` reaches `SOURCE_CONTAINED` with one witness, no provider literal in general config, zero agent/MCP use, and unrelated auth hashes unchanged.

- [ ] T-1.13 — Immediately contain Railway credentials and consumers
  - Agent: build
  - Files: `$HOME/.railway`, shell/service/agent loader rows, `$STATE_ROOT/{manifest.json,receipts.ndjson}`
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): stop agent/MCP Railway consumers, remove secret propagation and reversible autoload reachability, harden the official native root/files to owner-only modes, and retain the still-valid old material only in that contained source for the direct-CLI continuity probe.
  - Gate: `railway.primary` reaches `SOURCE_CONTAINED` only when the official CLI is the sole permitted consumer, no agent/MCP loader can use the source, and no backup/log/shell copy is reachable.

- [ ] T-1.14 — Immediately contain Engram auth/state and every agent integration
  - Agent: build
  - Files: `$HOME/.engram`, Engram service/client/plugin/model-instruction rows, `$STATE_ROOT/{manifest.json,receipts.ndjson}`
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): attribute and stop every MCP/plugin client, detach Engram agent injection/autoload with values-free inverse patches, remove propagation, and harden auth plus DB/WAL/SHM roots/files without deleting data; retain the still-valid old auth only for the bounded direct-CLI probe.
  - Gate: `engram.cloud.primary` reaches `SOURCE_CONTAINED` only when no agent/MCP path can use it, the direct CLI is the sole permitted client, and every existing auth/database sidecar is private.

- [ ] T-1.15 — Immediately contain Cursor Context7 auth and loaders
  - Agent: build
  - Files: `$HOME/.cursor/mcp.json`, Cursor rules/skills/process rows, Cursor Context7 quarantine item, `$STATE_ROOT/{manifest.json,receipts.ndjson}`
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): stop Cursor, move its Context7 value through the recoverable two-phase OS quarantine channel, remove the source field, and detach Cursor Context7/Railway MCP autoload through values-free inverse patches; do not assume equality with Gemini.
  - Gate: `context7.cursor.primary` reaches `SOURCE_CONTAINED` with one private witness, zero Cursor/agent/MCP use, and an exact inverse patch.

- [ ] T-1.16 — Immediately contain Gemini Context7 auth and shared Antigravity loaders
  - Agent: build
  - Files: `$HOME/.gemini/{settings.json,config/mcp_config.json}`, Antigravity/Gemini process/rule/skill rows, Gemini Context7 quarantine item, `$STATE_ROOT/{manifest.json,receipts.ndjson}`
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): stop Antigravity/Gemini consumers, independently move the Context7 value through the recoverable two-phase OS quarantine channel, remove its source field, and detach Context7/Exa/Pencil autoload through values-free inverse patches.
  - Gate: `context7.gemini.primary` reaches `SOURCE_CONTAINED` with one private witness, zero shared-host/agent/MCP use, and no reused Cursor evidence.

- [ ] T-1.17 — Close every remaining third-party MCP execution path reversibly
  - Agent: build
  - Files: exact host registrations, plugins, hooks, rules, skills, aliases, services, and resident-process rows in the deletion manifest
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): for each exact classified integration, stop its process/service and apply the previewed values-free inverse patch or owner-native disable so registration, autoload, auto-invoke, recommendation, and agent reachability are all zero. Unknown or identity-mismatched entries STOP for classification/re-plan; no permanent deletion occurs here.
  - Gate: effective scans over every declared loader find zero reachable third-party MCP and zero unknown row; no credential becomes usable by an agent through fallback.

- [ ] T-1.18 — Enforce the immediate-containment barrier
  - Agent: verify
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`; seven credential rows and all host reachability rows
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Procedure (read-only): reconcile interrupted quarantine transfers and inverse patches, then recompute source ownership/ACL, secondary-copy, process/service, effective loader, and consumer reachability denominators without exposing values.
  - Gate: exactly `7/7 SOURCE_CONTAINED`, one old witness per row, zero secret propagation, zero agent/MCP use, zero reachable third-party MCP, and zero unknown identity before T-2.1.

## Phase 2 — Checkpoint one: prove every lifecycle before migration

- [ ] T-2.1 — Confirm Claude gateway issuer, replacement, and revocation control
  - Agent: guard
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): operator records the issuer/control-plane alias, safe re-auth path, bounded probe class, and old-token rejection evidence; never enters a value in chat or the manifest.
  - Gate: exact checkpoint-one phrase for `claude.gateway.primary`; native `claude auth logout` is explicitly insufficient.

- [ ] T-2.2 — Confirm OpenRouter management access, destination branch, and invalidation evidence
  - Agent: guard
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): operator confirms create/disable-delete capability, approved model/probe, and old-key rejection evidence; persist exactly one destination branch: (A) OpenCode private native auth store, which removes `options.apiKey` while retaining the replacement under owner-only native storage, or (B) governed Keychain/env launcher, which writes `{env:VARIABLE}` and never a value to provider config.
  - Gate: exact checkpoint-one phrase for `opencode.openrouter.primary`; the selected branch, consumer patch, and recovery are immutable inputs to T-6.4/T-6.6.

- [ ] T-2.3 — Confirm `nan-builders` issuer, destination branch, and revocation mechanism
  - Agent: guard
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): operator records provider lifecycle, a reproducible rejection proof, and exactly one destination branch: (A) OpenCode private native auth with `options.apiKey` removed or (B) a governed Keychain/env launcher with `{env:VARIABLE}` in config; absence or ambiguity keeps the row blocked.
  - Gate: exact checkpoint-one phrase for `opencode.nan-builders.primary`; local logout is not invalidation and T-6.7/T-6.9 must use the recorded branch.

- [ ] T-2.4 — Confirm Railway token class and select a parallel destination branch
  - Agent: guard
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): operator classifies account/project/session material, server-side deletion, and direct-login recovery, then selects exactly one parallel-staging branch: (A) an official isolated Railway profile/private store that retains the replacement fields at `0600` and later switches profiles, or (B) a scoped token in Keychain/governed env whose launcher later removes old user-token fields. Never overwrite the sole working credential before checkpoint two.
  - Gate: exact checkpoint-one phrase for `railway.primary`; if neither branch supports parallel new-auth proof, the row stays blocked, and `railway logout` alone is rejected.

- [ ] T-2.5 — Confirm Engram ownership and a genuinely parallel auth target
  - Agent: guard
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`; process/service metadata
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): attribute the listener and every client; distinguish legacy server-wide bearer from managed token; require managed dual-token coexistence, explicit dual-token server support, or an isolated blue/green target on which the replacement can reach `NEW_AUTH_OK` while the old path remains recoverable. Record client restart/cutover, durable `umask 077` boundaries, and old-token rejection evidence.
  - Gate: exact checkpoint-one phrase for `engram.cloud.primary`; unknown ownership/client set or a single replace-in-place bearer without isolated parallel proof leaves the row blocked.

- [ ] T-2.6 — Confirm Cursor Context7 disposition and lifecycle
  - Agent: guard
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.2 YAGNI, §10.6 SDD
  - Procedure (judgment-bound): operator chooses direct-CLI consumer or `revoke+delete` and records issuer invalidation; never assumes equality with another Context7 row.
  - Gate: exact checkpoint-one phrase for `context7.cursor.primary`.

- [ ] T-2.7 — Confirm Gemini Context7 disposition and lifecycle
  - Agent: guard
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.2 YAGNI, §10.6 SDD
  - Procedure (judgment-bound): operator independently classifies the shared Antigravity/Gemini credential and its invalidation route.
  - Gate: exact checkpoint-one phrase for `context7.gemini.primary`.

- [ ] T-2.9 — Enforce the all-provider readiness barrier
  - Agent: verify
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): none; verify seven distinct checkpoint-one receipts, one exact supported lifecycle/destination branch per row, neutral-terminal availability, and zero unknown or newly exposed rows.
  - Gate: no credential replacement, host deletion, or ownership mutation starts unless all seven rows pass.

## Phase 3 — Reversible containment and direct-CLI continuity

- [ ] T-3.1 — Revalidate precise ACL containment without recursive chmod
  - Agent: build
  - Files: `$HOME/.claude`, `$HOME/.config/opencode`, `$HOME/.local/share/opencode`, `$HOME/.local/state/opencode`, `$HOME/.railway`, `$HOME/.engram`, `$HOME/.cursor`, `$HOME/.gemini`
  - Principles applied: §10.1 KISS, §10.7 Clean Code
  - Implementation (judgment-bound): idempotently confirm T-1.10…T-1.16 set credential roots to `0700` and exact secret/config/log/DB/WAL/SHM files to `0600`; preserve executables and sockets. After preview, remove only manifest-approved extended ACL grants (`chmod -N` on macOS or equivalent), treating ACLs separately from xattrs.
  - Gate: effective ACL validator passes; an external symlink, wrong owner, unsafe ancestor, unapproved grant, or broad recursive mutation blocks.

- [ ] T-3.2 — Quarantine and revalidate propagation sources without premature deletion
  - Agent: build
  - Files: audited backup/log/session-env/history/shell/LaunchAgent patterns; OS credential quarantine; `$STATE_ROOT/manifest.json`
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): structured scanner emits key/presence/count only; confirm T-1.10…T-1.16 removed propagation and moved each necessary old rejection witness into its linked owner-only quarantine item. Disable access to linked secret-bearing backup/log artifacts, but do not destroy a provider's last old-token witness until that row reaches `POSTCHECK`.
  - Gate: no reachable secondary source remains, every retained witness has one ledger link and private ACL, and no raw `rg`, `cat`, `env`, `printenv`, or `set -x` is used.

- [ ] T-3.3 — Revalidate reversible third-party MCP containment and recovery metadata
  - Agent: build
  - Files: host registrations, plugins, hooks, rules, skills, aliases, and processes listed in the manifest
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Implementation (judgment-bound): idempotently confirm T-1.10…T-1.17 stopped consumers and removed autoload/auto-invoke/recommendation reachability; complete only missing values-free inverse-patch metadata after owner-native disable preview, without copying secret-bearing config.
  - Gate: effective reachability and credential use remain zero before probes; unknown identity stops for re-plan, while Phase 5 still hard-deletes only classified manifest-approved residue.

- [ ] T-3.4 — Prove direct Engram continuity without MCP setup
  - Agent: verify
  - Files: `engram` executable/origin row, Engram data metadata, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): run bounded version/help plus authenticated read-only cloud/doctor operation with output parsed in memory and discarded; record data-integrity and re-auth path.
  - Gate: auth and transport are separately true; no `engram mcp` or `setup agent` branch executes.

- [ ] T-3.5 — Prove direct Railway continuity with the absolute Homebrew candidate
  - Agent: verify
  - Files: Railway executable/origin row, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): smoke the absolute Homebrew binary, then a bounded authenticated `whoami`-class operation parsed without persisting identity; leave current PATH untouched on failure.
  - Gate: candidate version/features/auth pass and no MCP setup branch runs.

- [ ] T-3.6 — Prove NotebookLM CLI continuity and notebook-data integrity
  - Agent: verify
  - Files: `notebooklm` executable/origin row and NotebookLM CLI proof metadata in `$STATE_ROOT/manifest.json`
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): run bounded doctor/status/read-only notebook metadata probe with output discarded; distinguish CLI data from obsolete NotebookLM-MCP app state.
  - Gate: authenticated CLI works, notebook count/integrity boolean is preserved, and no browser/MCP fallback is invoked.

- [ ] T-3.7 — Prove `ctx7` CLI continuity while prohibiting setup
  - Agent: verify
  - Files: `ctx7` executable/origin row, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): run bounded help and approved read-only docs query with output discarded and command policy active.
  - Gate: direct read succeeds; `ctx7 setup`, `mcp`, and every agent-setup path are rejected before execution.

- [ ] T-3.8 — Verify containment and direct-CLI continuity without changing credential state
  - Agent: verify
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.6 SDD, §10.4 DRY
  - Procedure (read-only): verify all seven credential rows already reached `SOURCE_CONTAINED` in T-1.10…T-1.16, sources/quarantines remain private, MCP reachability is zero, propagation is closed, and four direct-CLI proof rows pass; only credential-scoped probes write exact-schema receipts. Mark continuity as the hard prerequisite for Phase 5 permanent integration deletion; do not perform a state transition here.
  - Gate: failed continuity leaves the old integration contained, never reactivated, and blocks Phase 5.

- [ ] T-3.9 — Select the definitive Railway executable owner before auth migration
  - Agent: build
  - Files: `$HOME/.zshrc`, `$HOME/.railway/bin/railway`, `/opt/homebrew/opt/railway/bin/railway`, Railway ownership row
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): after T-3.5 proves the absolute Homebrew candidate, preview the exact vendor PATH-prepend removal and validate fresh-shell resolution, Homebrew realpath/version/receipt, bounded auth smoke, consumer scan, and `brew reinstall railway` recovery before deleting anything. Then remove the PATH line and losing vendor binary/directory if empty; rerun all gates. After deletion, recovery may reinstall/repair only the Homebrew winner—never restore a PATH entry to the deleted vendor binary.
  - Gate: every pre-delete gate passes before unlink; post-delete resolution/auth pass with one Homebrew owner, or exact Homebrew recovery runs and the lane blocks.

## Phase 4 — Repository operational zero-MCP cutover

- [ ] T-4.1 — RED: pin zero-MCP closure and retained research/media behavior
  - Agent: build
  - Files: `tests/conformance/test_zero_third_party_mcp.py` (new), `tests/integration/test_ai_research_tier*.py`, existing research/media/hook/settings/template tests
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Implementation (judgment-bound): add failing tests across autoload/project config, canonical skills, active docs, hooks, policies, templates, and generated surfaces; explicitly allow inert audit/spec/history roots and defensive vocabulary. Before any GREEN patch, pin retained native-web citations/domain filters, existing `gh` behavior, NotebookLM CLI Tier 3, media native-host paths, fail-loud degradation, timeout/output bounds, recovery, and survivor behavior.
  - Gate: tests fail RED on `.mcp.json`, MCP-health wiring, research/media fallbacks, policy remnants, and missing retained-behavior contracts.

- [ ] T-4.2 — Remove project MCP declarations, permissions, hooks, and binary policy
  - Agent: build
  - Files: `.mcp.json` (delete), `.claude/settings.json`, `.github/hooks/hooks.json`, `.ai-engineering/scripts/hooks/{mcp-health.py,copilot-mcp-health.sh,copilot-mcp-health.ps1}`, `.ai-engineering/reference/mcp-binary-policy.md`, template twins, hook manifest, suppression allowlist
  - Principles applied: §10.1 KISS, §10.4 DRY
  - Patch (deterministic): apply only this exact deletion matrix: delete `.mcp.json`; in both `.claude/settings.json` and `src/ai_engineering/templates/project/.claude/settings.json`, remove from `/permissions/allow` the values `mcp__context7__*`, the six listed `mcp__notebooklm__*` entries, and `mcp__tavily__*`, then remove `/hooks/PreToolUse` and `/hooks/PostToolUseFailure` objects whose matcher is `mcp__` and command target is `mcp-health.py`; in both `.github/hooks/hooks.json` and `src/ai_engineering/templates/project/.github/hooks/hooks.json`, remove the `/hooks/preToolUse` object whose bash/PowerShell targets are `copilot-mcp-health.sh`/`.ps1`; delete the three canonical health scripts and their three exact template twins; delete `.ai-engineering/reference/mcp-binary-policy.md` and its template twin; remove the three exact canonical-script keys from the hook manifest and only suppression-allowlist entries whose path is the deleted canonical `mcp-health.py`. Preserve every nonmatching array element, pre-existing timeout, and runtime-hook change; regenerate the manifest.
  - Gate: settings parse, hook parity/integrity pass, and no project MCP registration or health hook remains.

- [ ] T-4.3 — Rewrite `ai-research` Tier 1 around existing `gh` and native web
  - Agent: build
  - Files: `.claude/skills/ai-research/SKILL.md`, `handlers/classify-query.md`, hard-rename `handlers/tier1-free-mcps.md` → `handlers/tier1-native-sources.md`, `handlers/tier0-local.md`
  - Principles applied: §10.1 KISS, §10.4 DRY, §10.6 SDD
  - Implementation (judgment-bound): remove Context7/MS-Learn MCP callables; retain only the existing governed `gh search` path and route library/Microsoft official documentation through bounded native web. Fail loud/degraded when those retained sources are unavailable; do not embed new `ctx7` CLI expertise, add a CLI leaf, or keep a compatibility shim in this P0 spec.
  - Gate: T-4.1 Tier-1 tests pass for `gh`/native web, timeout/output caps, and setup/MCP-fallback prohibition.

- [ ] T-4.4 — Rewrite `ai-research` Tier 2 around native web only
  - Agent: build
  - Files: `.claude/skills/ai-research/handlers/tier2-web.md`, classifier/synthesizer references, research integration helpers/tests
  - Principles applied: §10.1 KISS, §10.2 YAGNI
  - Implementation (judgment-bound): remove Tavily/Exa MCP callables, setup instructions, availability flags, and tie-break semantics; retain bounded native WebSearch/WebFetch, domain filters, URL dedup, citations, and NotebookLM CLI Tier 3.
  - Gate: T-4.1 research resilience tests stay green with native web + existing `gh` + NotebookLM; zero Context7/Tavily/Exa MCP or new `ctx7` integration remains in the active workflow.

- [ ] T-4.5 — Remove MCP execution/fallback from other canonical skills
  - Agent: build
  - Files: `.claude/skills/ai-media/**`, `.claude/skills/ai-skill-improve/SKILL.md`, `.claude/skills/ai-fundraising/handlers/market-research.md`, any other manifest-classified operational canonical skill
  - Principles applied: §10.1 KISS, §10.2 YAGNI
  - Implementation (judgment-bound): remove `requires.mcp`, setup commands, `/ai-memory` MCP, Fal/Exa/other MCP fallbacks; retain native host tools or direct installed CLIs only when already governed, otherwise fail loud until the private-skill spec.
  - Gate: zero-MCP conformance passes for canonical skills without creating a new leaf or weakening outcome gates.

- [ ] T-4.6 — Keep `ai-mcp-audit` defensive and remove enablement semantics
  - Agent: build
  - Files: `.claude/skills/ai-mcp-audit/SKILL.md`, related handlers/tests
  - Principles applied: §10.2 YAGNI, §10.7 Clean Code
  - Implementation (judgment-bound): retain read-only detection of prohibited third-party MCP in imported skills/plugins, delete binary allowlist/install/risk-accept enablement, and make remediation always removal or host-vendor classification.
  - Gate: the skill cannot register, recommend, approve, or execute a third-party MCP.

- [ ] T-4.7 — Rewrite active framework documentation to zero-MCP posture
  - Agent: build
  - Files: `README.md`, `src/ai_engineering/templates/project/CANONICAL.md`, `.ai-engineering/reference/gate-policy.md`, installer/doctor remediation prose, active runbook index entries found by the manifest
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Implementation (judgment-bound): remove operational MCP setup/recommendations; document host-vendor exceptions, direct CLI/native-web paths, defensive auditing, and the dormant-native-help carveout; leave inert history untouched.
  - Gate: every active mention classifies as prohibition, exact Codex exception, defensive audit, or dormant-binary carveout.

- [ ] T-4.8 — Remove obsolete MCP-era tests and complete the pre-seeded GREEN suite
  - Agent: build
  - Files: `tests/integration/test_ai_research_tier*.py`, research helpers, MCP binary/risk tests, hook/settings/template tests, `tests/conformance/test_zero_third_party_mcp.py`
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Implementation (judgment-bound): delete only assertions for removed enablement and update fixtures/names to the direct-source contract already pinned RED in T-4.1; add no new behavioral requirement after implementation.
  - Gate: the complete T-4.1 suite turns GREEN, including native-web/`gh`/NotebookLM, media fail-loud, no-fallback, output-bound, timeout, recovery, and survivor assertions.

- [ ] T-4.9 — Reconcile canonical ownership against the frozen pre-mutation baseline
  - Agent: guard
  - Files: `.opencode/**` changed paths, untracked `.cursor/**`, `.claude/**` canonical diff, generated templates/mirrors, T-0.0 baseline
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Procedure (judgment-bound): compare every candidate against T-0.0, move valid compacted intent into canonical files, review the exact overwrite allowlist, and stop on an unowned or hash-drifted overlap; never recapture a post-edit baseline.
  - Gate: operator re-approves the exact allowlist and every unrelated dirty hash still matches T-0.0.

- [ ] T-4.10 — Regenerate in a clean worktree and apply only allowlisted outputs
  - Agent: build
  - Files: generated `.codex/`, `.agents/`, `.github/`, `.opencode/`, `.cursor/`, Antigravity surfaces and `src/ai_engineering/templates/project/**` selected by T-4.9
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Implementation (judgment-bound): create a temporary clean worktree at the same reviewed base, apply only the reviewed canonical patch there, run the full canonical `ai-eng dev sync`, and compare the generated diff with T-0.0/T-4.9's path+hash allowlist. Copy/apply only approved generated paths back to the dirty working tree; never run global sync directly over that dirty tree; remove the temporary worktree after evidence is recorded.
  - Gate: unexpected generated paths or baseline drift block application; surface parity, install-clean, research, hook, zero-MCP conformance, `ai-eng check`, and unrelated-hash comparison pass.

## Phase 5 — Hard-delete host registrations, injections, and MCP-first skills

Every deletion below is limited to an exact identity already classified and
operator-approved in the manifest. A newly found, unknown, or identity-mismatched
component STOPs for classification and re-plan; no task may delete it generically.

- [ ] T-5.1 — Hard-cut Claude project MCP and project hook/permission residue
  - Agent: build
  - Files: `$REPO/.mcp.json`; `$REPO/.claude/settings.json`; Claude effective project state
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): apply the approved repo deletion and remove every manifest-confirmed project registration for Tavily, SVGIcons, Context7, NotebookLM, Todoist, the audited Caveman test server, Exa, Engram, and only exact additional third-party identities classified and operator-approved in the manifest; remove linked residual permissions/hooks while preserving unrelated settings.
  - Gate: fresh effective config has an empty Claude third-party MCP allowlist and no unknown server survives.

- [ ] T-5.2 — Hard-cut Claude user plugins, rules, skills, memories, and state
  - Agent: build
  - Files: `$HOME/.claude/{settings.json,settings.local.json,rules/context7.md,skills/**,plugins/**,projects/**/memory/**,.claude.json}`
  - Principles applied: §10.1 KISS, §10.4 DRY
  - Implementation (judgment-bound): use owner-native uninstall for manifest-confirmed Tavily, SVGIcons, Context7, NotebookLM, Todoist, the audited Caveman test server, Exa, Engram, and only exact additional third-party identities classified and operator-approved in the manifest; remove forced rules/MCP-first skills and detach reachable MCP memories. Edit generated state only after uninstall leaves a proven orphan; preserve source-only Caveman marketplace code only when reachability is definitively false.
  - Gate: plugin/effective-config scan is empty, no autoload memory prescribes MCP, no unclassified server remains, and unrelated plugins survive.

- [ ] T-5.3 — Hard-cut Codex Engram injection and every classified non-allowlisted component
  - Agent: build
  - Files: `$HOME/.codex/config.toml`, `$HOME/.codex/{engram-instructions.md,engram-compact-prompt.md,mcp-oauth-locks/**}`, classified Codex component rows
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): owner-native remove Engram, `computer-use`, and each exact manifest identity already classified outside the three approved vendor IDs; delete instruction/compact pointers and files; remove orphan state/locks only after identity check. An unknown or identity mismatch stops for classification/re-plan and is never deleted generically.
  - Gate: prompt-input inspection contains no Engram, unknown/unclassified count is zero, and exactly three total MCP-backed component identities survive: Node REPL, OpenAI-bundled Sites, and OpenAI-curated GitHub.

- [ ] T-5.4 — Hard-cut OpenCode MCP, Engram injection, and forced Context7
  - Agent: build
  - Files: `$HOME/.config/opencode/{opencode.json,plugins/engram.ts,AGENTS.md,skills/use-railway}`
  - Principles applied: §10.1 KISS, §10.7 Clean Code
  - Implementation (judgment-bound): remove the manifest-confirmed `brand-mcp`, Exa, and Pencil registrations plus exact additional third-party identities classified and operator-approved in the manifest, the Engram plugin, forced Context7 instructions, and MCP-first Railway skill while preserving provider config for the credential lane and unrelated auth entries; delete the MCP object only when empty.
  - Gate: `opencode mcp list` is empty, no unknown server survives, and a fresh model request receives no Engram/Context7 injected text.

- [ ] T-5.5 — Hard-cut Cursor Context7/Railway configuration and skills
  - Agent: build
  - Files: `$HOME/.cursor/{mcp.json,rules/context7.mdc,skills/context7-mcp,skills/use-railway}`; Cursor Context7 quarantine receipt
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): remove the manifest-confirmed Context7 and Railway registrations plus exact additional third-party identities classified and operator-approved in the manifest, config/rule/bundles only after T-1.15 proves the old Context7 witness moved to owner-only OS credential quarantine and left source config; preserve non-MCP Cursor settings and unrelated skills.
  - Gate: source config is secret-free, quarantine receipt is linked, full Cursor relaunch discovers zero MCP or unknown server, and survivor hashes match.

- [ ] T-5.6 — Hard-cut Copilot CLI Railway MCP and MCP-first skill
  - Agent: build
  - Files: `$HOME/.copilot/{mcp-config.json,skills/use-railway}`
  - Principles applied: §10.1 KISS, §10.7 Clean Code
  - Implementation (judgment-bound): use owner-native removal for the manifest-confirmed Railway registration plus exact additional third-party identities classified and operator-approved in the manifest, delete the config only when empty, and preserve unrelated Copilot config/auth.
  - Gate: fresh `copilot mcp list` is empty with no unknown server; runtime ownership remains unchanged until Phase 7.

- [ ] T-5.7 — Hard-cut VS Code/Copilot MCP without deleting global storage wholesale
  - Agent: build
  - Files: `$HOME/Library/Application Support/Code/User/mcp.json`, Copilot globalStorage rows named in the deletion manifest
  - Principles applied: §10.1 KISS, §10.2 YAGNI
  - Implementation (judgment-bound): remove manifest-confirmed Engram, Tavily, Exa, and Railway entries plus exact additional third-party identities classified and operator-approved in the manifest; delete an empty config and remove only MCP cache/state that regenerates and remains reachable after restart.
  - Gate: empty-workspace then `$REPO` relaunch discovers zero MCP and no unknown server; unrelated Copilot state survives.

- [ ] T-5.8 — Hard-cut Antigravity/Gemini shared Context7/Exa/Pencil residue
  - Agent: build
  - Files: `$HOME/.gemini/{settings.json,config/mcp_config.json,GEMINI.md,skills/context7-mcp}`, Antigravity effective state, Gemini Context7 quarantine receipt
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): remove the manifest-confirmed Context7, Exa, and Pencil registrations plus exact additional third-party identities classified and operator-approved in the manifest, empty residue, forced instruction, and skill only after T-1.16 proves the Gemini Context7 old-token witness is in its independent owner-only OS quarantine and absent from source config.
  - Gate: quarantine linkage passes, fresh `agy` scan has zero third-party or unknown MCP, and Gemini remains correctly classified residual/shared rather than falsely runnable.

- [ ] T-5.9 — Remove Kiro residual and verify Pi's negative contract
  - Agent: build
  - Files: `$HOME/.kiro/settings/mcp.json`, `$HOME/.pi/agent/settings.json`, shared discovery rows
  - Principles applied: §10.1 KISS, §10.2 YAGNI
  - Implementation (judgment-bound): delete Kiro's Pencil residue after proving no app/package/process/service/launcher; do not edit Pi settings.
  - Gate: Kiro residual rescan and Pi fresh session both report zero MCP.

- [ ] T-5.10 — Remove shared MCP-first skill families owner-aware
  - Agent: build
  - Files: global skill-lock/list state and physical `context7-mcp`, `notebooklm-mcp`, `use-railway` directories across declared roots
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Implementation (judgment-bound): preview `skills list -g --json`, use `skills remove -g` for owned common entries, manually delete only the manifest-approved orphan NotebookLM bundle, and never touch plugin caches or unrelated skills.
  - Gate: physical/name scan returns zero targeted bundles; survivor hashes and `skills --version` are unchanged.

- [ ] T-5.11 — Verify the hard cut before any credential replacement
  - Agent: verify
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`; all host effective configs/processes
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): run effective-config/native listings, process/service scan, discovery-root scan, operational-document reachability scan, and exact Codex identity check.
  - Gate: zero reachable forbidden path, zero unknown integration, four direct CLIs still functional; otherwise stop and never restore MCP.

## Phase 6 — Secure credential destinations and serial provider migrations

For every task below, the operator enters new values only in the provider UI,
OS credential manager, or official login prompt—never chat. A Keychain-backed
launcher is permitted only when the provider lacks a compatible private native
store. It uses `set +x`, unsets inherited secret variables, retrieves into the
process without argv exposure, exports, and `exec`s an absolute binary. Shell
profiles/LaunchAgents may contain only the non-secret launcher PATH.
Every provider lane uses the one-shot old-witness protocol above. `OLD_INVALID`
requires a bounded old-auth `401/403` (or equivalent explicit rejection) or a
semantically verified issuer revocation receipt; local logout and inferred
expiry never qualify. Only after that row reaches `POSTCHECK` may the runner
destroy its linked quarantine item and any disabled backup/log copy.

- [ ] T-6.1 — Migrate Claude gateway to new auth through `NEW_AUTH_OK`
  - Agent: build
  - Files: OS credential manager/secure launcher, `$HOME/.claude/settings.json`, Claude ledger row
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Implementation (judgment-bound): operator issues/stores the replacement; runner proves the agreed gateway auth semantically with output suppressed; remove neither old value nor source key yet.
  - Gate: row reaches `NEW_AUTH_OK`; native Claude OAuth status is not accepted as gateway proof.

- [ ] T-6.2 — Checkpoint two: authorize invalidation of the old Claude gateway token
  - Agent: guard
  - Files: Claude ledger row and manifest-owned receipt index
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): display impact, new-auth proof ID, configuration patch, recovery path, and old-token rejection method; accept only the exact per-row invalidation phrase.
  - Gate: checkpoint-two receipt exists and still contains no value or identity.

- [ ] T-6.3 — Cut over, revoke, reject, and postcheck Claude gateway auth
  - Agent: build
  - Files: `$HOME/.claude/settings.json`, secure launcher/store, Claude ledger row, linked old-witness quarantine/source
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): atomically remove literal auth/API keys while preserving non-secret base/model, switch consumer, invalidate through the issuer, prove old rejection from the one-shot buffer, and run a cold bounded Claude request; destroy the linked old witness only after `POSTCHECK`.
  - Gate: row reaches `POSTCHECK` with old `401/403` or a semantically verified issuer revocation receipt; after cutover recovery may reissue only, never restore the old token.

- [ ] T-6.4 — Migrate OpenRouter through `NEW_AUTH_OK` on the selected branch
  - Agent: build
  - Files: selected OpenCode native store or governed launcher/Keychain, `$HOME/.config/opencode/opencode.json`, OpenRouter ledger row
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Implementation (judgment-bound): use only T-2.2's branch: native stores the replacement in OpenCode's private auth store and removes `options.apiKey` at cutover, while governed-env stores it in Keychain and prepares `{env:VARIABLE}` plus the launcher. Run bounded `opencode run --pure` with the approved model, discard output, and keep the contained old witness until checkpoint two.
  - Gate: row reaches `NEW_AUTH_OK`, destination ACL/launcher policy passes, and no MCP/plugin path participates.

- [ ] T-6.5 — Checkpoint two: authorize old OpenRouter key invalidation
  - Agent: guard
  - Files: OpenRouter ledger row and manifest-owned receipt index
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): present new-auth proof, literal-to-secure-reference patch, delete/disable route, rejection probe, and reissue recovery.
  - Gate: exact per-row invalidation confirmation is recorded.

- [ ] T-6.6 — Cut over, invalidate, reject, and postcheck OpenRouter
  - Agent: build
  - Files: `$HOME/.config/opencode/opencode.json`, `$HOME/.local/share/opencode/auth.json` selected row only, selected destination, ledger row, linked old witness
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): apply exactly T-2.2's branch—native removes `options.apiKey` but retains the replacement in owner-only OpenCode auth; governed-env writes only `{env:VARIABLE}` and uses the secure launcher. Remove only the duplicate old auth entry, invalidate server-side, prove rejection, repeat a fresh `--pure` request, then destroy the linked old witness after `POSTCHECK`.
  - Gate: row reaches `POSTCHECK`; unrelated `auth.json` providers survive and the chosen branch does not drift.

- [ ] T-6.7 — Migrate `nan-builders` through `NEW_AUTH_OK` on the selected branch
  - Agent: build
  - Files: selected OpenCode native store or governed launcher/Keychain, `$HOME/.config/opencode/opencode.json`, `nan-builders` ledger row
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Implementation (judgment-bound): use exactly T-2.3's native-auth or governed-env branch, store the replacement only in that secure destination, and run the approved bounded provider/model probe with no output; keep the contained old witness until checkpoint two.
  - Gate: row reaches `NEW_AUTH_OK`; destination/launcher validation or lifecycle drift stops the entire phase.

- [ ] T-6.8 — Checkpoint two: authorize old `nan-builders` invalidation
  - Agent: guard
  - Files: `nan-builders` ledger row and manifest-owned receipt index
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): show proof, patch, provider-specific revoke/rejection, and recovery; accept only the exact row phrase.
  - Gate: checkpoint-two receipt exists.

- [ ] T-6.9 — Cut over, invalidate, reject, and postcheck `nan-builders`
  - Agent: build
  - Files: `$HOME/.config/opencode/opencode.json`, selected destination, ledger row, linked old witness
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): apply exactly T-2.3's branch—native removes `options.apiKey` and keeps replacement auth private; governed-env writes only `{env:VARIABLE}` and uses the launcher—then revoke with provider evidence, prove old rejection, rerun the fresh bounded model probe, and destroy the old witness after `POSTCHECK`.
  - Gate: row reaches `POSTCHECK`; logout/local deletion alone cannot pass and destination branch cannot drift.

- [ ] T-6.10 — Migrate Railway through `NEW_AUTH_OK` using the definitive winner
  - Agent: build
  - Files: T-2.4 selected native profile/store or Keychain launcher, `$HOME/.railway/config.json`, Railway ledger/ownership rows
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Implementation (judgment-bound): use T-3.9's persisted Homebrew winner and exactly T-2.4's parallel-staging branch. Native creates/logs into an isolated official profile/private store while the old profile remains recoverable; governed-env stores a scoped replacement in Keychain and stages the launcher without removing old user-token fields. Run bounded authenticated `whoami` semantics with identity discarded.
  - Gate: row reaches `NEW_AUTH_OK` on the parallel target, token class matches checkpoint one, and the sole old credential was not overwritten.

- [ ] T-6.11 — Checkpoint two: authorize old Railway credential invalidation
  - Agent: guard
  - Files: Railway ledger row and manifest-owned receipt index
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): show server-side invalidation, config-key removal, winner path, negative probe, and re-login recovery.
  - Gate: exact per-row invalidation confirmation is recorded.

- [ ] T-6.12 — Cut over, invalidate, reject, and postcheck Railway
  - Agent: build
  - Files: `$HOME/.railway/config.json`, selected destination/profile, Railway ledger row, linked old witness
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): apply exactly T-2.4's branch: native atomically switches to the isolated official profile and retains replacement fields at `0600`; governed-env switches to the launcher and removes only old access/refresh/session fields while preserving link metadata. Delete/revoke the old server-side credential, prove rejection, run a fresh authenticated read-only smoke, and destroy the old witness after `POSTCHECK`.
  - Gate: row reaches `POSTCHECK`; local logout alone never satisfies `OLD_INVALID`, and the Homebrew owner remains T-3.9's winner.

- [ ] T-6.13 — Prove Engram replacement on a parallel target through `NEW_AUTH_OK`
  - Agent: build
  - Files: Engram parallel server/client secure stores, `$HOME/.engram/cloud.json`, process manifest, Engram ledger row, client launchers/services
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Implementation (judgment-bound): gracefully stop attributed consumers, create the T-2.5 managed dual token or isolated blue/green target without replacing the old path, install a durable service/launcher boundary with `umask 077` for every server/client that may create DB/WAL/SHM or auth files, then prove replacement auth and transport using a bounded fresh process against the parallel target.
  - Gate: row reaches `NEW_AUTH_OK` while the old target remains recoverable; every client/blast-radius row and durable permission boundary is proven. A single replace-in-place bearer blocks.

- [ ] T-6.14 — Checkpoint two: authorize old Engram token invalidation
  - Agent: guard
  - Files: Engram ledger row and manifest-owned receipt index
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): show server-wide impact, client cutover order, restart, old-token rejection, DB non-deletion guarantee, and reissue recovery.
  - Gate: exact per-row invalidation confirmation is recorded.

- [ ] T-6.15 — Cut over every Engram client, invalidate old auth, and postcheck
  - Agent: build
  - Files: `$HOME/.engram/cloud.json`, selected native or Keychain-backed secure stores, client launchers/services, Engram ledger/client rows, linked old witness
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): after checkpoint two, atomically point every client to the proven parallel target; native keeps the replacement only in the owner-only Engram store, while Keychain mode removes the token from general config and uses the governed launcher. Restart controlled services under durable `umask 077`, invalidate the old target/token, prove old sync rejection or semantic managed-revoke receipt, postcheck every client, then destroy the old witness.
  - Gate: row reaches `POSTCHECK`; no client remains on old auth and no observation/database is deleted or restored.

- [ ] T-6.16 — Migrate or revoke quarantined Cursor Context7 through `NEW_AUTH_OK`
  - Agent: build
  - Files: Context7 secure destination or revoke plan, Cursor Context7 quarantine item and ledger row
  - Principles applied: §10.2 YAGNI, §10.6 SDD
  - Implementation (judgment-bound): follow the approved disposition using the old witness already moved in T-1.10; for `revoke+delete`, prove no future consumer and use an explicit not-applicable replacement receipt without creating a credential.
  - Gate: row reaches `NEW_AUTH_OK` under the disposition-specific schema and the quarantine item remains private for the terminal rejection proof.

- [ ] T-6.17 — Checkpoint two: authorize Cursor Context7 invalidation
  - Agent: guard
  - Files: Cursor Context7 ledger row, manifest-owned receipt index, and linked OS quarantine item
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): show the exact disposition, quarantine witness, issuer revoke/delete operation, rejection method, direct-CLI impact, and reissue recovery; accept only the exact row phrase, append the exact-schema checkpoint probe receipt, `fsync`, then CAS the manifest before returning control.
  - Gate: a durable checkpoint-two receipt/index entry exists before T-6.18; a crash after approval cannot authorize a different config hash or row.

- [ ] T-6.18 — Invalidate Cursor Context7 and complete terminal postcheck
  - Agent: build
  - Files: Cursor Context7 ledger row, manifest-owned receipt index, linked OS quarantine item, approved direct consumer if any
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): require T-6.17's fsynced checkpoint ID and expected config hash, perform the server-side revoke/delete, prove rejection from the one-shot witness or semantic issuer receipt, postcheck direct `ctx7` only if approved, and delete the quarantine item only after `POSTCHECK`; crash resume verifies remote state before any retry.
  - Gate: row reaches `POSTCHECK`, crash-injection between remote revoke and terminal receipt is idempotently reconciled, the old witness is gone, and no Cursor MCP config returns.

- [ ] T-6.19 — Migrate or revoke quarantined Gemini Context7 through `NEW_AUTH_OK`
  - Agent: build
  - Files: Context7 secure destination or revoke plan, Gemini Context7 quarantine item and ledger row
  - Principles applied: §10.2 YAGNI, §10.6 SDD
  - Implementation (judgment-bound): independently apply the approved disposition using the T-1.16 witness; do not reuse Cursor evidence or assume the same secret, and keep the private quarantine item only until terminal rejection proof.
  - Gate: row reaches `NEW_AUTH_OK` with an independent proof and quarantine linkage.

- [ ] T-6.20 — Checkpoint two: authorize Gemini Context7 invalidation
  - Agent: guard
  - Files: Gemini Context7 ledger row, manifest-owned receipt index, and linked OS quarantine item
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): show the independent disposition, quarantine witness, issuer revoke/delete operation, rejection method, shared Antigravity impact, and recovery; accept only the exact row phrase, append the exact-schema checkpoint probe receipt, `fsync`, then CAS the manifest before returning control.
  - Gate: a durable checkpoint-two receipt/index entry exists before T-6.21; stale config hash or reused Cursor evidence blocks.

- [ ] T-6.21 — Invalidate Gemini Context7 and complete terminal postcheck
  - Agent: build
  - Files: Gemini Context7 ledger row, manifest-owned receipt index, linked OS quarantine item, approved direct consumer if any
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): require T-6.20's fsynced checkpoint ID and expected config hash, revoke/delete server-side, prove rejection from the one-shot witness or semantic issuer receipt, postcheck any approved direct consumer, and delete the quarantine item only after `POSTCHECK`; crash resume verifies remote state before retry.
  - Gate: row reaches `POSTCHECK`, crash-injection between remote revoke and terminal receipt reconciles idempotently, the old witness is gone, and shared Antigravity config stays MCP-free.

- [ ] T-6.22 — Prove the complete credential ledger terminal
  - Agent: verify
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Procedure (read-only): verify every receipt has exactly the eight D-193-08 fields; validate the manifest-owned ordered offset/hash index over immutable receipt bytes, seven checkpoint-one and seven checkpoint-two probe IDs, strict transition order, exact destination branches, new-auth proof, old invalidation, postcheck, and old-witness destruction for every row.
  - Gate: `7/7 POSTCHECK`; `blocked`, implicit expiry, local logout, unproven rejection, or a surviving quarantine/source witness is not success.

## Phase 7 — Resolve executable ownership and PATH provenance

- [ ] T-7.1 — Reverify the already-selected Railway owner after credential cutover
  - Agent: verify
  - Files: `$HOME/.zshrc`, Railway winner path/receipt, ownership manifest
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Procedure (read-only): make no ownership mutation; repeat a fresh login-shell resolution, realpath/package receipt check, consumer scan, and authenticated read-only smoke against T-3.9's Homebrew winner after T-6.12.
  - Gate: one Homebrew-owned realpath/version remains, no vendor shadow or PATH prepend returned, auth works, and `brew reinstall railway` recovery is still exact.

- [ ] T-7.2 — Select npm Claudeline and remove the untrusted Homebrew owner
  - Agent: build
  - Files: Homebrew Claudeline receipt/link, npm global `@arcasilesgroup/claudeline@0.4.4`, ownership manifest
  - Principles applied: §10.1 KISS, §10.7 Clean Code
  - Implementation (judgment-bound): record receipts, uninstall the untrusted tap formula without auto-trusting it, reinstall the exact npm package to repair the shared-prefix link, and scan consumers.
  - Gate: one npm-owned realpath/version remains; recovery is exact npm reinstall; no `brew trust` occurs automatically.

- [ ] T-7.3 — Select package-manager Copilot and disable self-update by its documented mechanism
  - Agent: build
  - Files: Homebrew cask receipt/binary, version-specific official Copilot configuration surface, ownership manifest
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Implementation (judgment-bound): first verify the installed version's official configuration reference and persist exactly one supported branch—documented `autoUpdate: false` or a documented governed environment control—then refresh cask metadata, require a non-downgrading reproducible version, reinstall, and apply that branch without touching auth. Never invent a config key; if unsupported or the cask stays stale, block for re-plan instead of orphaning/copying the binary.
  - Gate: config introspection proves the control effective, two cold launches keep receipt/runtime/hash aligned, consumers bypass no package-managed path, and recovery is `brew reinstall --cask copilot-cli`.

- [ ] T-7.4 — Verify one intentional owner and recovery contract for all three CLIs
  - Agent: verify
  - Files: ownership rows, shell/agent consumers, package receipts
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): none; repeat all-path resolution in a fresh login shell and validate the exact reinstall commands without executing destructive recovery.
  - Gate: Railway, Claudeline, and Copilot each have one winner, no shadow, matching runtime provenance, and a tested read-only smoke.

## Phase 8 — Cold-restart packets and regenerated-state verification

- [ ] T-8.1 — Establish a neutral-terminal restart epoch and process census
  - Agent: guard
  - Files: restart epoch/process rows in `$STATE_ROOT/manifest.json`
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): operator opens an external neutral terminal, records only a monotonic restart epoch/process identity class, and confirms the current host will be last.
  - Gate: the same agent process cannot attest its own cold restart.

- [ ] T-8.2 — Cold-restart and rescan Claude Code
  - Agent: verify
  - Files: Claude manifest rows and effective generated state
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): close CLI/app, relaunch, open `$REPO`, allow normal state write, then rescan plugins, MCP, permissions, hooks, rules, skills, and reachable memory.
  - Gate: `installed+runnable` denominator passes with empty third-party allowlist and no regenerated secret/residue.

- [ ] T-8.3 — Cold-restart and rescan OpenCode
  - Agent: verify
  - Files: OpenCode manifest rows and generated state
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): terminate, relaunch fresh, permit normal writes, and inspect MCP/plugin/instruction/auth-reference state with values suppressed.
  - Gate: zero MCP/injection, credential rows remain `POSTCHECK`, and CLI is functional.

- [ ] T-8.4 — Cold-restart and rescan Cursor
  - Agent: verify
  - Files: Cursor manifest rows and generated state
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): fully quit/relaunch, open a new window then `$REPO`, allow state writes, and scan config/rules/skills.
  - Gate: empty MCP discovery and unchanged unrelated-skill survivors.

- [ ] T-8.5 — Cold-restart and rescan Copilot CLI and VS Code/Copilot separately
  - Agent: verify
  - Files: Copilot CLI rows, VS Code/Copilot rows, generated storage/config
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): fresh Copilot invocation, then full Code quit/relaunch with empty workspace followed by `$REPO`; inspect each loader independently.
  - Gate: both `installed+runnable` rows pass with empty third-party MCP and stable package-managed Copilot runtime.

- [ ] T-8.6 — Cold-restart Antigravity and verify Gemini residual/shared state
  - Agent: verify
  - Files: Antigravity/Gemini manifest rows and shared configuration
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): terminate/relaunch `agy`, permit state writes, rescan; separately prove no Gemini executable/package/process while shared config stays clean.
  - Gate: Antigravity runnable row passes and Gemini stays out of the fresh-session denominator.

- [ ] T-8.7 — Verify Pi, Kiro residual, and every shared-root consumer
  - Agent: verify
  - Files: Pi/Kiro/shared-root manifest rows
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Procedure (read-only): start fresh Pi, rescan all consumers of `$HOME/.agents`, and after login/shell reload prove Kiro has no binary/package/process/service/launcher/config.
  - Gate: Pi passes; Kiro is `residual-only`; targeted skill families are absent everywhere.

- [ ] T-8.8 — Validate Engram DB/WAL/SHM across two independent fresh processes
  - Agent: verify
  - Files: `$HOME/.engram/{engram.db,engram.db-wal,engram.db-shm}`, Engram process/ACL rows
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): prove no uncontrolled handles; run SQLite `quick_check` and `PRAGMA wal_checkpoint(TRUNCATE)` through the supported Engram/SQLite maintenance path, require `busy=0`, and close. Never unlink, delete, restore, or rename the DB/WAL/SHM. Start fresh bounded process 1 under T-6.13's durable `umask 077`, record which sidecars exist naturally and validate owner/no-symlink/`0600`; close/checkpoint, then repeat independently with process 2. Sidecar absence is valid and is not called recreation.
  - Gate: DB integrity and `busy=0` pass, no uncontrolled handle exists, every naturally existing sidecar is private after both processes, and no state file was deleted; any public sidecar blocks P0.

- [ ] T-8.9 — Cold-restart Codex last and verify the exact vendor set
  - Agent: verify
  - Files: Codex manifest rows, config/plugin/app/generated prompt state
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): from the neutral terminal, terminate the active Codex host, relaunch/resume from canonical state, allow writes, inspect effective MCP/plugins and prompt input.
  - Gate: only exact Node REPL/Sites/GitHub identities survive; zero Engram/non-allowlisted content; previous process cannot supply evidence.

- [ ] T-8.10 — Run the final closed-surface denominator gate
  - Agent: verify
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Procedure (read-only): compute `N/N` total plus denominators by state, exact Codex exception count, zero forbidden reachable paths, zero unsafe ACL, zero unknown owner, and survivor integrity.
  - Gate: all denominators pass; installed-broken, unknown, regenerated residue, or leaked output blocks completion.

## Phase 9 — Terminal security gates, handoff, and self-review

- [ ] T-9.1 — Run terminal secret-presence and artifact-leak scans
  - Agent: verify
  - Files: closed config/shell/service/log/backup surface; private bundle; runtime handoff candidate
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (read-only): structured key-presence/entropy scan with suppressed values checks literals, argv, temp/log/backup artifacts, ACLs, and receipt schema; official private native stores/Keychain are the only allowed destinations.
  - Gate: zero literal reusable secrets outside approved stores and zero secret-derived content in artifacts/output.

- [ ] T-9.2 — Run full repository and one-shot-runner verification
  - Agent: verify
  - Files: full changed repository set and spec-193 runner/tests
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Procedure (read-only): none; run targeted/full tests, Ruff, Ty, Semgrep, pip-audit, gitleaks, spec lint, mirror/template parity, install-clean, zero-MCP conformance, and audit-chain verification.
  - Gate: all applicable checks pass; pre-existing unrelated failures are evidenced and cannot mask changed-surface failures.

- [ ] T-9.3 — Export the sanitized next-spec handoff
  - Agent: build
  - Files: `.ai-engineering/runtime/audits/spec-193-handoff.json`, `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Implementation (judgment-bound): derive CLI alias, executed version, winning origin, auth class, bounded read-only smoke result, risk class, MCP status, state denominators, exact Codex identities, and rebuild command; include no personal absolute path or identity.
  - Gate: export is byte-stable from terminal canonical state and refuses any non-`POSTCHECK`/failed denominator.

- [ ] T-9.4 — Adversarially review decision coverage and irreversible recovery
  - Agent: guard
  - Files: approved spec, this plan, private manifest schema, final handoff
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Procedure (judgment-bound): map every goal and D-193-01…14 to evidence; verify every mutation had preview/checkpoint/postcondition/recovery, every provider stayed serial, and no private-skill work entered scope.
  - Gate: zero blocker/critical/high review findings after at most two self-review iterations.

- [ ] T-9.5 — Seal the terminal receipt index and preserve resumable evidence
  - Agent: build
  - Files: `$STATE_ROOT/manifest.json`, `$STATE_ROOT/receipts.ndjson`, framework audit chain
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Implementation (judgment-bound): without inventing a non-credential receipt, atomically seal the manifest's ordered receipt offset/hash index against the validated handoff hash and emit a framework operation without copying provider evidence or duplicating manifest state.
  - Gate: exact receipt schemas, manifest-owned index integrity, and `ai-eng audit verify` pass; runtime handoff can be deleted and rebuilt from canonical state.

## Risks Identified

- **Lockout:** mitigated by all-provider checkpoint-one readiness, real new-auth
  proof, per-row checkpoint two, server-side invalidation evidence, and reissue
  rather than old-token rollback.
- **Partial migration:** the global readiness barrier and provider lock stop the
  run on the first failed row; no parallel provider mutations are allowed.
- **Secret disclosure:** values stay in provider UI/official prompt/OS store;
  runner output and receipts use a fail-closed allowlist and canary tests.
- **Generated residue:** every runnable host is allowed to write state after a
  cold restart and is rescanned; residual-only hosts use package/process/login
  proof instead of a fake fresh session.
- **Engram corruption or public sidecars:** no DB delete/restore; no open handles;
  internal integrity/checkpoint before natural two-process recreation tests.
- **Worktree loss:** path/hash baseline plus target-specific reconciliation;
  any ownership overlap stops before mirror generation.
- **Scope creep:** an architecture test forbids autoload/distribution and a
  scope guard forbids private skill/router work.

## Recommendations

- Approve this plan only if the operator accepts a supervised, interruptible
  `/ai-build`; never run it with `--no-hitl`.
- Perform provider UI/Keychain input personally from a neutral terminal. Do not
  paste any token into the agent conversation.
- Treat every `BLOCKED`, unknown owner, failed old-key rejection, unsafe ACL,
  regenerated residue, or cold-restart ambiguity as a hard stop and re-plan.

Safe next command after explicit plan approval: `/ai-build`
