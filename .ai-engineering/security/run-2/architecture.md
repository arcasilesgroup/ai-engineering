# Architecture and audit map

## Product and execution model

`ai-engineering` is a local CLI that installs repository governance files and machine-level AI-agent hooks. The npm package ships a Node-compatible launcher and TypeScript source; the launcher runs the CLI through Bun. The release workflow also builds compiled binaries for multiple OS/architecture targets.

## Security-relevant flow

1. A host invokes `ai-eng chain` with an event name, payload, and surface identifier.
2. `src/payload.ts` normalizes host-specific payload fields.
3. `src/env.ts` resolves the repository root from the reported working directory.
4. `src/chain/mod.ts` evaluates guards and returns allow, deny, or rewrite.
5. Host carriers and the CLI apply the result. Rewrite-capable surfaces may invoke `ai-eng wrap`.
6. `src/commands/adapt.ts` can write selected governance files from an adaptation proposal.

Trust boundaries include host event schemas, the hook-reported `cwd`, shell parsing before and after rewrites, files writable by the governed agent, and machine-level carrier installation.

## Prior-run context

`run-1` covers other issues and is not duplicated here. Its report says some findings were fixed in a worktree, while its `findings.json` still marks them open and has no landed commit SHAs. Reconcile that ledger against the actual merged revision before treating those findings as closed.

## Evidence and limits

The four findings in this run were reproduced locally in temporary governed repositories and independently validated. One finding depends on the Copilot documented camelCase payload; another depends on the host reporting a changed `cwd`. Neither was exercised inside a live Copilot CLI or Claude Code session. No Windows VM or Linux container install was available: Docker Hub returned 403, and npm inside the cached Linux image could not validate the registry certificate. This audit therefore makes no cross-platform pass claim.
