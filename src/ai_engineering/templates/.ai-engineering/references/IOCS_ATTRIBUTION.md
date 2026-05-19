# IOC Catalog Attribution

This file documents the provenance of the vendored Indicators of
Compromise (IOC) catalog used by the prompt-injection sentinel for
runtime matching. The catalog itself lives at
`.ai-engineering/security/iocs/iocs.json` once the framework is
installed; this attribution file preserves upstream credit and licence
posture so consumers can audit the chain of custody.

## Source

- **Upstream project**: `claude-mcp-sentinel`
- **Upstream path**: `references/iocs.json`
- **Schema version**: 1.0 (preserved verbatim from upstream)

Consumers should treat the on-disk catalog at
`.ai-engineering/security/iocs/iocs.json` as authoritative; refresh
guidance is documented at `.ai-engineering/contexts/sentinel-iocs-update.md`
once `/ai-branch-cleanup` or `/ai-mcp-audit` lands the next vendor cycle.

## Attribution

The upstream `claude-mcp-sentinel` project is the canonical source of
the IOC catalogue shape and content. Redistribution within
`ai-engineering` is permitted under the upstream licence (MIT). When
publishing this framework downstream, retain this attribution and
mirror upstream attribution in any derivative `iocs.json` distribution.

## License

MIT (inherited from `claude-mcp-sentinel`).
