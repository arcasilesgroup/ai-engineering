---
spec: spec-193
title: Personal Host Security and Zero-Third-Party-MCP Cutover
status: in-progress
effort: large
summary: "Eliminate third-party MCP from personal agent hosts and harden audited credentials and CLI provenance without losing verified access or vendor-native capabilities."
---

# Personal Host Security and Zero-Third-Party-MCP Cutover

## Summary

Personal agent hosts contain connected or residual third-party MCP configuration, disabled integrations that still inject instructions, duplicated MCP-first skills, literal credentials, permissive local file modes and ambiguous executable ownership. Remove every configured, injected, recommended or auto-invoked third-party MCP path in the closed personal discovery surface and harden the audited secrets and CLI provenance before building the private expert-skill fleet, while preserving the three approved Codex capabilities, inert historical evidence and verified direct-CLI access.

## Goals

- Close the inspected universe over Claude Code, Codex, OpenCode, Pi, Cursor, GitHub Copilot, Gemini/Antigravity, Kiro, `ai-engineering` project-local configuration and every shared personal discovery root those hosts load.
- Produce a sanitized manifest covering `N/N` declared surfaces with host, sanitized path/pattern, class, loader, `surface_state`, active/reachable state, owner, mode/ACL, content hash, component identity and runtime/package version; no secret or account identity may enter agent context or captured stdout.
- Reduce configured, injected, recommended and auto-invoked third-party MCP paths to zero after a cold restart and fresh-session discovery on every declared host.
- Preserve only the exact Codex vendor exceptions `node_repl`, OpenAI-bundled Sites design picker and OpenAI-curated GitHub, identified in the manifest by host component ID, publisher, installation channel, version/hash and pre/post identity; every other host has an empty MCP allowlist.
- Keep dormant MCP-related subcommands and signed/versioned CLI-native help in otherwise approved binaries outside the forbidden-path denominator, while ensuring no agent-owned configuration, alias, rule, skill, hook, plugin or instruction invokes or recommends them.
- Remove all reachable personal copies of `context7-mcp`, `notebooklm-mcp` and the MCP-first `use-railway` skill without deleting unrelated skills, canonical caches or the CLI-driven NotebookLM research workflow.
- Preserve authenticated, direct read-only operation of `engram`, `railway`, `notebooklm` and `ctx7` before removing the final prior integration path; explicitly prohibit `ctx7 setup` and every MCP setup command in continuity probes.
- Build a credential ledger for the audited Claude auth token, two OpenCode provider keys, Railway session/token material, Engram cloud token and any secret-bearing backup discovered in the closed surface, using logical aliases and key names only.
- Contain every exposed credential source immediately, then migrate each credential through a resumable provider-specific state machine with two explicit operator checkpoints, verified new authentication and terminal evidence that the exposed prior credential is revoked, invalidated or expired.
- Store credentials only in an official operating-system credential manager, an official CLI-native store with private ACLs, or a governed process-local environment; block the provider migration when none is supported.
- Enforce correct owner, non-symlink destination, private parent traversal and ACLs equivalent to `0700` directories and `0600` secret/state files; prove Engram DB/WAL/SHM privacy after fresh processes recreate state.
- Resolve Railway and Claudeline to one intentional installed owner each; resolve Copilot's receipt/runtime drift to one declared vendor-managed or package-manager-managed ownership model rather than treating it as a duplicate binary.
- Sanitize or remove secret-bearing backups, logs and stale general configuration after successful rotation; historical-preservation rules never protect plaintext credentials.
- Deliver a sanitized handoff artifact for the next spec containing CLI aliases, executed version, winning origin, authentication class, bounded read-only smoke result, risk class and MCP status.

## Non-Goals

- Creating the private `agent-cli-skills` repository, authoring CLI leaves or benchmarking the lazy router; those are the next spec.
- Reducing root instructions, memories, progressive-disclosure hooks, framework skill mirrors or general review fan-out; those are separate context-diet and review-routing specs.
- Editing project files across the remaining repository fleet; the final propagation spec consumes the proven pilot and generator.
- Removing dormant MCP-named subcommands or their signed/versioned native help from third-party CLI binaries; this spec removes agent-owned configuration, reachability, recommendation and automatic invocation.
- Removing audit reports, lifecycle events, decisions or historical specifications that are unreachable from all autoload/instruction/plugin/skill surfaces and contain no credential value.
- Preserving historical logs, backups or artifacts that contain plaintext credentials or secret-derived reusable values.
- Removing the three exact Codex components in the closed allowlist, or changing non-MCP tools built into a host executable.
- Broadly changing Bash/Edit/Write approval policies or turning CLI skills into an authorization system.
- Rotating credentials outside the closed credential ledger, rotating without both explicit checkpoints, or performing unattended revocation.
- Deleting Engram memories/databases, Railway projects, cloud resources, email, documents or provider data.
- Normalizing every system/package-manager PATH difference; this P0 resolves only Railway, Claudeline and the Copilot ownership drift required by the next work.

## Decisions

### D-193-01 — Executable P0 boundary

**Rationale**: Splitting security, private skills, context diet, review routing and fleet propagation keeps each independently risky program verifiable and recoverable.

Limit this spec to the closed personal host/discovery surface, audited credential storage and three CLI-ownership findings. The operator approved a five-spec sequence because the original umbrella combined independently risky security, skill, context, review and propagation programs that could not be planned, verified or recovered safely as one unit.

### D-193-02 — Closed host allowlist

**Rationale**: An identity-pinned allowlist removes analogy-based exceptions while preserving only the three host-vendor capabilities the operator approved.

Apply this exact MCP policy:

| Host/surface | Permitted MCP components | Required removal |
|---|---|---|
| Claude Code | none | Tavily, SVGIcons, Context7, NotebookLM, Todoist, audited Caveman test server and any unclassified registration/residue |
| Codex | `node_repl`; OpenAI-bundled Sites design picker; OpenAI-curated GitHub | Engram model/prompt injection and any component not matching the three manifest identities |
| OpenCode | none | `brand-mcp`, Exa, Pencil, Engram per-call injection, forced Context7 and any unclassified registration/residue |
| Pi | none | any MCP found by final discovery |
| Cursor | none | Context7, Railway and any unclassified registration/residue |
| Copilot CLI | none | Railway and any unclassified registration/residue in standalone CLI loaders |
| VS Code Copilot | none | Engram, Tavily and any unclassified registration/residue in VS Code user/workspace/Copilot loaders |
| Gemini/Antigravity | none | Context7, Exa, Pencil and any unclassified registration/residue |
| Kiro | none | every third-party MCP registration/residue discovered in the closed surface |
| Shared personal skill/config roots | none | reachable MCP-first skills, rules, plugins, aliases and generated projections |

Host-internal non-MCP tools are outside this table. An unknown or identity-mismatched integration blocks the cutover pending human classification; it is never retained by analogy.

### D-193-03 — Discovery closure and residue definition

**Rationale**: Registrations alone miss generated, injected and shared execution paths, so compliance must close over every effective loader and resident process.

Build the closure from host declarations, effective configuration, permissions, hooks, plugins, rules, instruction/model files, skills, shared roots, aliases/functions, shell startup files, environment exports, LaunchAgents/services, host state databases, symlinks, package-manager projections and resident processes. Treat Copilot CLI and VS Code Copilot as separate loaders and manifest rows. “Zero MCP” means zero configured, injected, recommended or auto-invoked third-party path in agent-owned surfaces; dormant subcommands and signed/versioned native help inside preserved CLI binaries may remain but cannot be selected by an agent workflow.

### D-193-04 — Reachability-based historical classification

**Rationale**: Reachability, not the word “historical,” determines whether a file can still change agent behavior, while inert audit evidence remains valuable.

Classify each MCP mention as: autoload/executable; prescriptive documentation loaded on demand; inert historical evidence; or unknown. Remove/replace the first, add an explicit zero-MCP warning or isolate the second, preserve only allowlisted inert audit/research/lifecycle/spec/decision roots, and block on unknown reachability. Content called “historical” is still operational when a bootstrap, memory, hook, plugin, rule, instruction or skill loads it.

### D-193-05 — Complete hard cut, not disable-only

**Rationale**: The audit proved disabled integrations can still inject instructions or regenerate state, so the owning operational path must be removed.

Remove third-party registrations and their owning operational paths rather than toggling servers off or deleting only generated config. The audit proved that disabled Engram and Context7 integrations still inject context or misroute agents; the owning plugin, rule, skill, hook or instruction must be removed and fresh-session discovery must remain clean after the host writes configuration again.

### D-193-06 — Credential ledger and disposition matrix

**Rationale**: Provider-specific lifecycle and future-consumer decisions are required before rotation so the cutover neither preserves unused secrets nor revokes access without recovery.

Create a values-free ledger with these mandatory columns: logical credential ID, provider/account alias, sanitized source path and key name, approved future consumer, disposition (`replace+revoke`, `re-login+invalidate`, `revoke+delete` or `blocked`), supported destination, redacted read-only probe, invalidation evidence and safe re-authentication path. The initial rows cover Claude auth, both OpenCode providers, Railway and Engram; newly found MCP-only credentials default to `revoke+delete` unless a separately approved direct-CLI consumer exists.

The initial capability result is fixed before mutation:

| Logical credential | Issuer/lifecycle capability | Replacement and probe | Invalidation evidence | Gate status |
|---|---|---|---|---|
| Claude configured-gateway auth (`ANTHROPIC_AUTH_TOKEN` and any non-empty `ANTHROPIC_API_KEY`) | A configured non-default gateway, not necessarily Claude's native account session; `claude auth logout` alone does not revoke a gateway token | Issue through the gateway control plane; bounded Claude/gateway auth probe with output suppressed | Prior token rejected by the gateway (`401`/`403`) or issuer revocation receipt | Blocked until checkpoint one confirms issuer/control-plane access |
| OpenCode OpenRouter key | OpenRouter supports create, disable/delete and metadata APIs | Create replacement, store through OpenCode native auth or governed environment, run a bounded provider probe | Key hash disabled/deleted and old-key request rejected | Supported when management/dashboard access is confirmed |
| OpenCode `nan-builders` key | Provider-specific lifecycle; no revocation mechanism was established by the local CLI audit | Provider control-plane replacement and bounded probe | Provider revocation receipt plus old-key rejection | Blocked until checkpoint one records the issuer and invalidation mechanism |
| Railway session/token set | Official CLI login/logout manages local credentials; account/project tokens are managed by Railway settings | Official browser/device login or new scoped token; `whoami`-class probe with stdout discarded | Old account/project token deleted or old session rejected; local `railway logout` alone is not server revocation evidence | Supported when account settings access and token class are confirmed |
| Engram cloud token | v1.20 supports a legacy static server bearer token and managed tokens; legacy rotation affects every client using the server token | Replace server `ENGRAM_CLOUD_TOKEN` and restart/cut over all clients, or issue a managed token where configured; `cloud status`-class probe suppressed | Old sync token returns `401`, or managed-token revoke evidence; record server-wide blast radius | Blocked unless the operator controls the Engram server/token lifecycle |

A `blocked` row may be approved as scope, but P0 cannot complete or mutate that provider until the stated capability becomes `supported` with evidence.

### D-193-07 — Resumable credential state machine and two checkpoints

**Rationale**: An explicit monotonic state machine with two human approvals prevents partial migration, unintended revocation and silent reuse of an exposed credential.

Persist only sanitized states per credential:

`DISCOVERED → SOURCE_CONTAINED → TARGET_READY → NEW_AUTH_OK → CONFIG_CUTOVER → OLD_INVALID → POSTCHECK`.

Containment immediately removes unsafe permissions, log/backup propagation and agent/MCP reachability while preserving the credential's semantic validity until replacement is proven. Checkpoint one occurs before creating or migrating the replacement; checkpoint two occurs after `NEW_AUTH_OK` and before invalidating the old credential. Do not advance to another provider after a failure. Before `NEW_AUTH_OK`, retain access only inside the contained source; after `CONFIG_CUTOVER`, never restore the exposed credential or public permissions. If invalidation cannot be proven, remain contained, mark the provider blocked and escalate rather than accepting implicit risk.

### D-193-08 — Secret destination, receipts and local privacy

**Rationale**: Restricting destinations and receipt fields keeps provider access usable without copying secret material into general configuration, logs or agent context.

Use the provider's official login and, in preference order, an OS credential manager, official CLI-native store with private ACLs, or process-local environment created by the governed launcher. Prohibit secrets in shell profiles, launch agents, argv, logs, temp files and general JSON/YAML settings. Receipts contain only credential alias, provider, CLI version, probe ID, exit code, timestamp, redacted-field count and invalidation evidence reference—never raw stdout, identity/workspace fields or values.

### D-193-09 — Direct-CLI continuity contract

**Rationale**: Preserving a binary is insufficient; authenticated read-only continuity must be proven before the last prior integration path is permanently removed.

Contain the final integration path immediately so it cannot execute, then—before irreversible deletion—record for `engram`, `railway`, `notebooklm` and `ctx7`: resolved executable/origin, version, bounded help check, authenticated read-only operation with captured output discarded/redacted, absence of MCP writes, data-integrity check and re-authentication path. A binary passing `--version` alone is not continuity. `ctx7 setup` and every `mcp`, `setup agent` or equivalent branch are forbidden in probes. A failed continuity test leaves the old integration contained, never reactivated.

### D-193-10 — Durable ACL verification

**Rationale**: One-time chmod does not prove durable privacy when CLIs can recreate files and sidecars with broader modes.

Verify ownership, symlink targets, extended ACLs, parent traversal and effective file modes. Exercise Engram through two fresh CLI processes so DB sidecars are closed and recreated naturally, then require private DB/WAL/SHM state whenever those files exist. Use a deterministic `umask 077` launch boundary only when compatible; if the tool still recreates public state, block P0 and record the upstream limitation instead of claiming success based solely on a private parent directory.

### D-193-11 — One intentional executable ownership model

**Rationale**: A single declared owner aligns the executed binary, update channel, package receipt and recovery command, eliminating PATH and self-update ambiguity.

For Railway and Claudeline, inventory all executable paths and package receipts, smoke-test the chosen current/reproducible owner, then remove the losing installation. For Copilot, choose either package-manager-managed reinstall with self-update controlled or vendor-managed ownership with the stale cask removed. Verify with all-path resolution, realpath, runtime version, owner query, consumer scan and an exact reinstall/recovery command.

### D-193-12 — Deletion manifest and recovery classes

**Rationale**: Owner-aware preview, survivor verification and class-specific recovery prevent broad cleanup from deleting unrelated skills, caches, data or access.

Preview every removal with sanitized path/pattern, class, owner/generator, symlink target, content hash, uninstall mechanism and expected survivor. Use the owning uninstaller when available and prove unrelated skills/caches remain. Recovery is class-specific: credentials re-authenticate without old tokens; MCP host configuration recovers without reactivating third parties; non-secret config uses an inverse patch or encrypted TTL backup; packages use reproducible reinstall commands.

### D-193-13 — Cold-restart verification and fail-closed receipts

**Rationale**: Only a normal state rewrite after a true restart can prove the owning integration will not regenerate forbidden configuration or unsafe state.

Classify each manifest row as `installed+runnable`, `installed+broken`, `residual-only` or `shared-root`. For `installed+runnable`, cold-restart, open a fresh session and let the host write state. `installed+broken` blocks until repaired or uninstalled. For `residual-only`—including Kiro when no executable/app/package is present—prove absence of binary, package, process, service and launcher, remove reachable configuration and rescan after login/shell reload; it does not enter the fresh-session denominator. Verify a `shared-root` from every active consumer. Then rerun effective-config/native listings, process checks, discovery-root scans, physical skill/hash scans and provider-specific secret-presence/entropy checks with all values suppressed. Completion reports `N/N` total surfaces plus denominators by `surface_state`, exact allowed Codex identities and zero forbidden reachable paths. Unknown integrations, failed auth/invalidation, unsafe ACLs, leaked output or regenerated residue block completion.

### D-193-14 — Sanitized handoff and sequential follow-ups

**Rationale**: A structured values-free handoff lets later specs consume proven CLI/auth/path facts without repeating the audit or reintroducing MCP assumptions.

Write the final handoff under `.ai-engineering/runtime/audits/` with the D-193-13 manifest plus CLI alias, executed version, winning origin, auth class, read-only smoke result, risk class and MCP status. The remaining specs follow in order: private CLI-skill pilot; `ai-engineering` context diet; risk-selected review fan-out; fleet propagation. No follow-up may restore MCP fallback or assume a CLI/auth/path that the handoff did not verify.

## Risks

- **Provider lockout during migration.** Use the D-193-07 state machine, two confirmations, read-only proof before invalidation and a provider-specific re-authentication path.
- **Partial failure leaves mixed security state.** Persist the sanitized state after each transition, stop the provider lane immediately and resume idempotently from the last proven state.
- **Accidental disclosure through logs, probes or backups.** Suppress raw output, avoid shell tracing, capture only the D-193-08 receipt schema and sanitize/delete secret-bearing history outside the preservation carve-out.
- **Vendor capability is misclassified.** Require an exact manifest identity for the three Codex exceptions; isolate and escalate every unknown rather than deleting or retaining it speculatively.
- **A historical file remains behaviorally active.** Prove reachability from loaders, not textual intent, and treat every autoloaded historical document as operational.
- **Generated MCP configuration reappears.** Remove the owning plugin/skill/rule/installer, cold-restart, allow a normal state write and rerun the complete closure scan.
- **Engram state permissions regress.** Exercise fresh processes and sidecar creation; block on recreated public state instead of accepting a one-time `chmod`.
- **Direct CLI access is silently lost.** Require authenticated read-only continuity before removing the last integration and stop when no supported direct path exists.
- **Deleting a copied skill removes unrelated content or a canonical cache.** Require the D-193-12 deletion manifest, owner-aware uninstall and survivor/hash verification.
- **Executable ownership change breaks hooks.** Scan consumers, switch and smoke-test before uninstalling, and retain an exact reinstall command without silently restoring the duplicate.
- **Pre-existing worktree changes are overwritten.** Compare every `ai-engineering` mutation with the baseline diff and stop on conflicting ownership.

## References

- research: .ai-engineering/runtime/research/llm-council-personal-cli-skills-2026-07-23.md
- research: .ai-engineering/runtime/research/personal-cli-skills-architecture-2026-07-23.md
- doc: .ai-engineering/runtime/audits/cli-first-context-audit-2026-07-23.md
- doc: .ai-engineering/runtime/audits/personal-cli-inventory-2026-07-23.md
- doc: docs/persistence-doctrine.md
- doc: https://openrouter.ai/docs/cookbook/administration/api-key-rotation
- doc: https://docs.railway.com/cli/login
- doc: https://docs.railway.com/cli/logout
- doc: https://github.com/Gentleman-Programming/engram/blob/763a6ba432713725d6ce82a2416eec6cbd9ec94e/docs/engram-cloud/troubleshooting.md
