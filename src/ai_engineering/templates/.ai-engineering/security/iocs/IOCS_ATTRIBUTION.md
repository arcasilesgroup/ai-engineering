# IOC Catalog Attribution (spec-107 D-107-05)

This file documents the provenance of the vendored Indicators of
Compromise (IOC) catalog used by `prompt-injection-guard.py` for
runtime sentinel matching.

## Source

- **Upstream project**: `claude-mcp-sentinel`
- **Upstream path**: `references/iocs.json`
- **Vendor commit hash**: `7677eca5e0313198daf39d2e3929760c80602ef8`
- **Vendor date**: 2026-04-28
- **Schema version**: 1.0 (preserved verbatim from upstream)
- **Upstream snapshot date** (`last_updated`): 2026-05-05

## License

The upstream `claude-mcp-sentinel` project is licensed under the **MIT
License** (`Copyright (c) 2026 Rafael Tunon Sanchez`). The vendored
catalog inherits the same MIT terms. Redistribution within
`ai-engineering` is permitted under the upstream license.

When publishing this framework downstream, retain this attribution and
mirror upstream attribution in any derivative `iocs.json` distribution.

## Schema

The vendored file preserves the upstream four primary IOC categories
verbatim and additionally exposes the canonical aliases required by
spec-107 contracts:

| Canonical (spec-107)   | Upstream alias         |
|------------------------|------------------------|
| `sensitive_paths`      | (same)                 |
| `sensitive_env_vars`   | (same)                 |
| `malicious_domains`    | `suspicious_network`   |
| `shell_patterns`       | `dangerous_commands`   |

**spec-122-a (D-122-04): pointer-map dedupe.** The on-disk catalog
stores each canonical category exactly once. Alias keys
(`malicious_domains`, `shell_patterns`) are listed in a
`spec107_aliases` block (`alias -> canonical_key` pointers). The
loader in `prompt-injection-guard.py` dereferences the alias map at
load time so callers that index by the alias name still receive the
canonical payload — without ~30 LOC of duplicated body in the JSON.

## Refresh process

See `.ai-engineering/contexts/sentinel-iocs-update.md` for the
quarterly manual PR refresh cadence and the out-of-band hot-security
fix flow.

## Known incidents indexed

The catalog references confirmed incidents (e.g. the Postmark MCP
backdoor, `giftshop.club` exfiltration, Sept 2025 disclosure). When
adding new incidents during a refresh, append to
`suspicious_network.known_malicious_domains[]` with `domain`,
`incident`, and `reference` fields preserved.
