# Sentinel IOC Refresh Cadence (spec-107 D-107-05)

The IOC catalog vendored at `.ai-engineering/security/iocs/iocs.json`
is maintained as a static snapshot from the upstream
`claude-mcp-sentinel` project. This document describes the manual
refresh cadence and the out-of-band hot-security flow.

## Quarterly review windows

Refresh is performed manually by the framework owner via Pull Request
on a quarterly cadence:

| Quarter | Review window  | Default reviewer       |
|---------|----------------|------------------------|
| Q1      | January 1-15   | framework owner        |
| Q2      | April 1-15     | framework owner        |
| Q3      | July 1-15      | framework owner        |
| Q4      | October 1-15   | framework owner        |

A reminder issue is opened on the first day of each window.

## Refresh process (per quarter)

1. Fetch latest upstream snapshot:
   ```bash
   git -C $REPOS_DIR/claude-mcp-sentinel pull --ff-only
   ```
2. Diff vs vendored copy:
   ```bash
   diff $REPOS_DIR/claude-mcp-sentinel/references/iocs.json \
        .ai-engineering/security/iocs/iocs.json
   ```
3. If non-empty diff:
   - Copy upstream over vendored: `cp $REPOS_DIR/claude-mcp-sentinel/references/iocs.json .ai-engineering/security/iocs/iocs.json`
   - Re-add canonical aliases (`malicious_domains` → `suspicious_network`, `shell_patterns` → `dangerous_commands`) — see `IOCS_ATTRIBUTION.md`
   - Update `IOCS_ATTRIBUTION.md` vendor commit hash and vendor date
   - Append a CHANGELOG.md entry with the human-readable diff summary
   - Mirror to `src/ai_engineering/templates/.ai-engineering/security/iocs/iocs.json`
4. Run targeted tests:
   ```bash
   uv run pytest tests/integration/test_sentinel_runtime_iocs.py -q
   uv run pytest tests/integration/test_sentinel_risk_accept.py -q
   ```
5. Open PR with title `chore(sentinel): quarterly IOC refresh — <YYYY-Q#>`.
6. Merge after review.

## Hot security fixes (out-of-band)

When a new MCP supply-chain incident is disclosed publicly between
quarterly windows, refresh out-of-band:

1. Apply steps 1-4 from the quarterly process.
2. Open PR with `security:` commit prefix, e.g.:
   `security(sentinel): add <domain> to malicious_domains (incident <ref>)`
3. Request expedited review (target: same-day merge for confirmed
   incidents).
4. After merge, monitor `framework-events.ndjson` for
   `category="mcp-sentinel"` `control="ioc-match-deny"` events to
   confirm coverage in production projects.

## Maintainer responsibility

- The framework owner is the primary reviewer for IOC PRs.
- Contributors may submit PRs to add IOCs; they require sign-off from
  the framework owner because IOC drift can cause false positives that
  block legitimate work.
- Incident references must include a public URL (research blog, CVE
  link, or vendor advisory).

## What this process does NOT do

- Automatic upstream polling (no scheduled GitHub Action) — refresh is
  intentionally manual to retain reviewer judgment over false-positive
  risk.
- Cryptographic verification of upstream provenance — the upstream
  project is not signed; trust derives from human review of the diff.
- Forward-publishing to the upstream project — the vendored copy is
  read-only from this framework's perspective.
