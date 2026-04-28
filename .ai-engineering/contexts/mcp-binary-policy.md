# MCP Binary Allowlist Policy

**Spec**: spec-107 D-107-01
**Owner**: `.ai-engineering/scripts/hooks/mcp-health.py` (`_ALLOWED_MCP_BINARIES`)

## Why an allowlist

The MCP-health hook reads `AIE_MCP_CMD_<SERVER>` and `AIE_MCP_RECONNECT_<SERVER>`
from the environment, then spawns the resulting argv vector via
`subprocess.run`. Without a binary allowlist, a compromised environment
(stolen `.envrc`, hijacked CI variable, malicious dotfile) can pivot to
arbitrary code execution every time Claude Code starts a session.

The allowlist closes that surface. Only the eight runtimes that are
typically managed by package managers (and therefore audit-able) are
permitted by default. Anything else must be consciously accepted via the
spec-105 risk-acceptance machinery, leaving an auditable trail.

## Canonical 8 binaries

| Binary    | Rationale                                                                     |
|-----------|-------------------------------------------------------------------------------|
| `npx`     | Node.js package runner; covers the bulk of npm-distributed MCP servers.       |
| `node`    | Direct Node.js entrypoint for pinned/local MCP server scripts.                |
| `python3` | Direct Python entrypoint for `pip install`'d MCP servers.                     |
| `bunx`    | Bun package runner, equivalent of `npx` in the Bun ecosystem.                 |
| `deno`    | Deno runtime, used by some MCP servers distributed as TypeScript modules.    |
| `cargo`   | Rust toolchain runner for Rust-implemented MCP servers (`cargo run`).         |
| `go`      | Go toolchain entrypoint (`go run`) for Go-implemented MCP servers.            |
| `dotnet`  | .NET CLI for C#/F# MCP servers distributed as NuGet tools.                    |

These eight cover the supported-stack matrix (Python, Node, Bun, Deno,
.NET, Go, Rust). Shells (`bash`, `sh`, `zsh`, `pwsh`), network clients
(`curl`, `wget`), and unmanaged interpreters (bare `python` without `3`)
are intentionally excluded — they are common payload-delivery primitives
in MCP supply-chain attacks.

## Extending the allowlist (escape hatch)

When a legitimate workflow requires a binary outside the canonical set
(e.g. `mvn` for a Java-backed MCP server), the maintainer accepts the
risk explicitly:

```bash
ai-eng risk accept \
  --finding-id mcp-binary-mvn \
  --severity low \
  --justification "Java-backed MCP server (atlassian-mcp) shipped via Maven" \
  --spec spec-107 \
  --follow-up "Migrate to npx-based wrapper by 2026-Q4"
```

The hook then:

1. Detects that `mvn` is outside `_ALLOWED_MCP_BINARIES`.
2. Looks up `find_active_risk_acceptance(finding_id="mcp-binary-mvn")`
   in `.ai-engineering/state/decision-store.json`.
3. Permits the invocation when an active acceptance is found.
4. Emits a `control_outcome` event with `category="mcp-sentinel"` and
   `control="binary-allowed-via-dec"` so the bypass remains auditable.

When the acceptance expires or is revoked, the hook reverts to the
default deny path and surfaces the canonical remediation hint on stderr.

List active exceptions with:

```bash
ai-eng risk list --filter "mcp-binary-*"
```

## Boundaries (NEVER)

- The allowlist must not be widened by direct code edit — every
  exception flows through `ai-eng risk accept` so the audit log is
  intact.
- The hook never validates the *content* of a binary; the allowlist is
  a name check only. Supply-chain attacks against an allowed binary
  (compromised `npx` package) are covered by separate controls
  (rug-pull detection, SHA256 spec hashing — spec-107 D-107-09).
- The hook is fail-closed. If the decision-store cannot be parsed, the
  binary is treated as unaccepted and the probe is rejected.
