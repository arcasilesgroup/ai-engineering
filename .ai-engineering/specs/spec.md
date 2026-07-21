---
spec: spec-191
title: "Injection Guard: read-side coverage + risk-accumulator precision"
status: approved
effort: large
summary: "Close the guard's read-side blind spot (PostToolUse scan of fetched web/file content, warn + flag-untrusted, no block) and wire the dead allowlist so known-good hosts/paths stop driving false-positive deny/risk. Two verified-live gaps; four already-fixed items fenced out."
---

Run /ai-brainstorm to start one.
# Injection Guard: read-side coverage + risk-accumulator precision

## Summary

The Prompt-Injection Guard (`prompt-injection-guard.py`, PreToolUse) only inspects
**tool inputs** for Bash/Write/Edit/MultiEdit. Content that arrives back *from* a tool —
a `Read` of a fetched file, a `WebFetch`/`WebSearch` result, or `exa`/`tavily` MCP output —
is delivered into context with **zero inspection**, so an injected instruction or malicious
domain embedded in fetched content has no guard coverage at all. Separately, the guard's IOC
layer carries a dead `allowlist` block in `iocs.json` (`allowlist.domains` /
`allowlist.paths`) that it never consults, so a legitimate citation of `github.com`,
`raw.githubusercontent.com`, or a `pastebin_style` host in fetched content drives a `deny` /
risk escalation. Both are verified-live findings from the fleet telemetry deck (claude.ai
artifact 216ac1f9), ground-truthed against current `main` on 2026-07-21. This spec closes the
read-side gap (warn + flag-untrusted, never block) and wires the allowlist for precision.
Four other B2 sub-claims were already fixed in `main` and are fenced under Non-Goals.

## Goals

- A `PostToolUse` read-side scan inspects `tool_response` for the external-content tools
  `Read`, `WebFetch`, `WebSearch`, and the `exa`/`tavily` MCP tools, evaluating the fetched
  text against the IOC catalog (host/domain/TLD + suspicious patterns) and the
  prompt-injection phrase set.
- On a read-side match the hook **does not block** (the content is already in context) — it
  emits a `content_untrusted` `control_outcome` (`outcome=warning`) plus a visible
  `additionalContext` banner so the operator/agent treats the content cautiously ("flag as
  untrusted").
- Known-good hosts in `iocs.json` `allowlist.domains` (e.g. `api.anthropic.com`,
  `github.com`, `raw.githubusercontent.com`, `pypi.org`) and paths in `allowlist.paths`
  (`/tmp/`, `/var/tmp/`) no longer produce a `deny` verdict or accumulate risk score.
- The IOC evaluation core shared by the write-side and read-side guards lives in one module
  (no duplicated logic, no hidden drift).
- Every change holds the framework's own invariants: byte-twin parity, regenerated
  hooks-manifest, stdlib-only hot path, additive-only telemetry.

## Non-Goals

- Re-tightening the host-IOC boundary regex so a short TLD no longer matches a benign dotted
  identifier / member access. **Already shipped** in spec-177 (PR #603, 2026-06-25) — the
  regex is boundary-anchored (`(?i)[A-Za-z0-9-]+\.{tld}(?![A-Za-z0-9-])`), so the gap is
  closed. Do not reopen.
- Replacing the risk-accumulator's TTL decay. Decay (`DECAY_PER_MINUTE = 0.95`, ~13.5 min
  half-life) has been present since spec-128/129 and is correct; this spec is *precision*
  (the dead allowlist), not a decay rewrite.
- Blocking read-side results. `PostToolUse` fires after the content is delivered to context;
  Claude Code offers no deny path there. The fix is warn + flag-untrusted, not block.
- Extending `PreToolUse` coverage. `Bash`/`Write`/`Edit`/`MultiEdit` are already scanned
  (spec-105/107); this spec adds the read side only.
- Removing the cumulative-same-IOC `force_stop` ladder. Decay already mitigates runaway
  escalation; this spec reduces false positives via the allowlist, not by relaxing `force_stop`.
- `B3` — running `ruff --fix` before consuming a ralph retry. Separate follow-on spec.
- Scanning `Agent` sub-agent responses or non-external tools. The external-content list
  (Read/WebFetch/WebSearch/exa/tavily) is the operator-confirmed scope.

## Decisions

### D-191-01 — Read-side PostToolUse scan: external content only, warn + flag-untrusted

Add a `PostToolUse` hook (`injection-read-guard.py`) that extracts `tool_response` for the
external-content tools (`Read`, `WebFetch`, `WebSearch`, `exa`, `tavily`), evaluates it with
the shared IOC core (host/domain/TLD + suspicious patterns) **and** the prompt-injection
phrase set, and on any match emits `control_outcome` `category=security`,
`control=content_untrusted`, `outcome=warning` plus a one-line `additionalContext` banner
(exit 0). It never exits 2. The Agent tool and non-external tools pass through untouched.

**Rationale**: The guard is write/exec-only today (`_GUARDED_TOOLS` = Bash/Write/Edit/MultiEdit),
so a malicious domain or an embedded directive payload in a fetched web
page or file enters context with no inspection — a genuine injection gap, and the highest-value
security item in the deck. `PostToolUse` cannot deny (content already delivered), so "flag as
untrusted" is realized as a warn `control_outcome` + visible banner the agent can heed. Scope
is operator-confirmed to external content: `Bash` output stays under the existing PreToolUse
command scan, and scanning every tool response would add latency with little signal.

### D-191-02 — Wire the dead `allowlist` into IOC evaluation

Load the `allowlist` block from `iocs.json` once (reusing the existing IOC mtime-LRU cache)
and consult it inside the shared IOC core: a host/TLD match whose domain is in
`allowlist.domains`, or a path match rooted at an `allowlist.paths` entry, is marked
`allowlisted=True` and dropped from the `deny`/`warn` verdict (and never fed to the risk
accumulator). Absent/malformed allowlist fails open to current behavior (match stands).

**Rationale**: `allowlist.domains`/`allowlist.paths` exist in `iocs.json` but the guard never
reads them (grep-confirmed dead across `.ai-engineering/scripts/hooks/`). Consequently a
legitimate README that cites `raw.githubusercontent.com` or mentions a `pastebin_style` host,
or a `/tmp/` scratch read, drives a `deny` and risk escalation — exactly the false-positive
class the telemetry deck flagged under "risk accumulator still escalates". Wiring the allowlist
is the precision fix the deck asked for; it is additive (a new drop path) and fails open.

### D-191-03 — Extract the IOC core into `_lib/ioc_eval.py` (single source)

Move `evaluate_against_iocs`, `_host_ioc_regex`, `_category_patterns`, and `_match_pattern`
out of `prompt-injection-guard.py` into `_lib/ioc_eval.py` (byte-twinned to the template),
and import them from both the write-side guard and the new read-side guard. The move is a
refactor only — identical logic, identical `finding_id`/telemetry — plus the D-191-02
allowlist drop.

**Rationale**: Those four functions live *inside* the write-side hook script, so a second
read-side hook would either duplicate them (drift risk — the exact 3-copy pain spec-190 hit)
or import a hook script with `main()` side effects. Extracting to `_lib` gives one source of
truth with a single byte-twin, and the allowlist wiring lands in exactly one place. The
risk-accumulator decay is untouched.

### D-191-04 — Hold the framework's own invariants

The new read-side hook and every guard edit are copied byte-identical to their
`src/ai_engineering/templates/.ai-engineering/scripts/hooks/**` twins; any hook byte change
regenerates `.ai-engineering/state/hooks-manifest.json`; hooks stay stdlib-only on the hot
path with pre-commit under 1s; new telemetry fields are additive.

**Rationale**: This spec touches the security plane itself; byte-twin parity, manifest
integrity, and the hot-path budget are the invariants that keep installs from breaking (the
same class of pain the deck measured). A fix to the guard must not regress the guard's own
guarantees.

## Risks

- **Read-side latency per fetched result.** Mitigation: reuse the mtime-LRU IOC cache; bound
  scanned text to `_MAX_CONTENT_LEN`; only external tools; always exit 0 (warn-only, never
  blocks the host).
- **New read-side false positives on benign fetched content.** Mitigation: warn-only (no
  block), the D-191-02 allowlist applies symmetrically, and the scan fails open on parse error.
- **Extraction changes write-side behavior.** Mitigation: refactor-only (logic identical),
  byte-twin parity + the existing write-side guard test suite must stay green before the
  read-side hook is added.
- **Manifest staleness self-disables hooks** if a twin `cp`/regen is skipped. Mitigation:
  regen per hook edit + the spec-190 byte-parity guard (now green) + a per-task regen gate.

## References

- doc: claude.ai artifact 216ac1f9 — fleet telemetry analysis (B2 = "guard blind to read-side" + "risk accumulator still escalates" live findings)
- doc: 16-agent ground-truth (this session, 2026-07-21) — read-side absent, allowlist dead, host-IOC boundary regex already anchored (spec-177), decay present (spec-128/129)
- doc: `.ai-engineering/scripts/hooks/prompt-injection-guard.py` — `evaluate_against_iocs` :930, `_host_ioc_regex` :813, `_match_pattern` :897, `_GUARDED_TOOLS` :203, `_IOC_CATEGORIES` :210
- doc: `.ai-engineering/scripts/hooks/_lib/risk_accumulator.py` — `DECAY_PER_MINUTE = 0.95` :91 (decay already present)
- doc: `.ai-engineering/security/iocs/iocs.json` — `allowlist.domains`/`allowlist.paths` :120-135 (dead config)

## Open Questions

- Should the read-side hook scan **both** the IOC host/domain set **and** the
  `prompt_injection_phrases` category, or IOC only? (Recommend: both — the phrase set catches
  instruction-style injection in fetched content, the strongest read-side signal.)
- Banner verbosity, and whether `content_untrusted` should also persist a per-session
  "untrusted sources" marker for downstream hooks to read.
- Should repeated `content_untrusted` on the same source coalesce via the spec-190 dedup
  sidecar (reuse `framework_error_storm` shape) rather than emit per result?
