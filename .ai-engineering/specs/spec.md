---
spec: spec-124
title: Post-Install UX + Doctor Provisioning + Security Visibility
status: approved
effort: medium
---

# Spec 124 — Post-Install UX + Doctor Provisioning + Security Visibility

## Summary

Spec-123 closed the framework cleanup Phase 1. Fresh `ai-eng install` test on a new project surfaced 8 follow-up concerns: an Engram setup bug (agent name mismatch), a "What's new" banner the user wants removed, tool-installation header truncation + duplication, hooks count always 0 in Install Complete, missing spacing before the Install Complete box, doctor warnings on fresh installs (ownership-coverage + opa-bundle-load + opa-bundle-signature), and lack of visibility into the secrets-gate that already exists. Plus an internal IDE-key rename to align with hyphenated vendor-product convention (`claude-code`, `gemini-cli`, `codex`, `github-copilot`).

This spec delivers targeted polish: install UX bugs fixed, doctor probes provisioned, OPA bundle generated per-install with regulated-grade keypair, secrets-gate surfaced via doctor + documentation, semgrep update model documented, and the 5 already-migrated state/ JSON fallbacks deleted.

## Goals

- Internal IDE keys renamed to single canonical hyphenated form: `claude-code`, `gemini-cli`, `codex`, `github-copilot`. Both old `copilot` and `github_copilot` collapse to `github-copilot`.
- Engram setup invocation passes the canonical hyphenated name directly (no mapping needed); `github-copilot` skipped with notice (Engram doesn't support it).
- "What's new" banner removed from `ai-eng install` output entirely.
- Tool installation phase shows per-tool progress (current tool name + status spinner) during long waits.
- Tool header text fits without truncation; phase number not duplicated.
- Hooks count in Install Complete reflects actual installed hooks, not always 0.
- Spacing inserted between "Open your AI assistant..." line and the Install Complete panel.
- `ownership-coverage` doctor warning resolved by seeding default ownership patterns at install time.
- `opa-bundle-load` + `opa-bundle-signature` doctor warnings resolved by per-install OPA keygen + sign at install time. Bundle directory + `.signatures.json` + `.manifest` present on every fresh install.
- New `ai-eng doctor` probe surfaces secrets-gate status (gitleaks, semgrep, configs, hooks).
- CONSTITUTION.md gains a documentation block on the secrets-gate (gitleaks pre-commit, semgrep pre-push, BLOCK by default).
- `.ai-engineering/contexts/semgrep-update-model.md` documents the manual quarterly bump model.
- 5 migrated state/ JSON fallbacks deleted (`decision-store.json`, `gate-findings.json`, `ownership-map.json`, `install-state.json`, `framework-capabilities.json`); CI guard `tests/unit/specs/test_state_canonical.py` enforces canonical layout.
- Local untracked `keys/opa-bundle-signing-dev.pub.pem` cleaned up; install-output path documented.
- All changes pass full pytest + ruff + gitleaks + doctor on clean state.

## Non-Goals

- Cache cleanup of user's local repo (`.pytest_cache`, `.ruff_cache`, `.venv`, `*.swp`) — out of framework scope; user responsibility.
- New secret-scanning enforcement — gates already exist + already block; this spec only surfaces them.
- New `ai-eng` subcommands beyond what's needed for OPA per-install bundle generation.
- Backwards-compat alias for old underscore IDE keys at the Python type level (manifest read shim only, single-release courtesy).
- Refactoring the gate engine — secrets-gate visibility is a probe + doc fix, not a restructure.
- Multi-host state.db sync, encryption-at-rest, or Phase 2 v2 cutover work.

## Decisions

### Theme A — Install UX bugs

**D-124-01: Rename internal IDE keys to single canonical hyphenated form**

| Old name(s) | Canonical new name | Notes |
|-------------|--------------------|-------|
| `claude_code` | `claude-code` | Anthropic Claude Code |
| `gemini` | `gemini-cli` | Google Gemini CLI |
| `codex` | `codex` | OpenAI Codex (already a single word) |
| `copilot`, `github_copilot` | `github-copilot` | GitHub Copilot — both old forms collapse here |

Scope: `IdeName` Literal type, `detect_ide()` returns, manifest schema enum, CLI flags, all Python call sites, tests, docs.

Rationale: more descriptive, matches Engram's convention (`claude-code`, `gemini-cli`), aligns with shell-flag style. Hard cutover (no Python BC alias) — internal keys are not a published API. Manifest read shim auto-translates old values on load (single-release courtesy) with WARN log; remove shim in spec-125.

**D-124-02: Remove "What's new" banner**

Delete `_BREAKING_BANNER` constant + `_maybe_emit_breaking_banner()` function + call site at `installer/phases/pipeline.py:43-66, 91-112, 312`. Drop `breaking_banner_seen` field from `InstallState` model.

Rationale: noise without ongoing value.

**D-124-03: Per-tool progress UX during install**

Tool installer phase + git-hooks phase emit `tool_started/tool_finished` events. UI layer renders Rich Status spinner with current tool name + duration. Reference: `.ai-engineering/contexts/cli-ux.md` color semantics.

Rationale: long install waits feel unresponsive; per-tool surface improves UX.

**D-124-04: Fix tool header truncation + [N/M] duplication**

Shorten helper text to `(✓ means tool found on PATH)`. Investigate `core.py:604` phase callback for double-emit; fix to single emit.

**D-124-05: Fix Hooks count always 0**

Trace hooks phase execution; ensure each hook filename written goes into `result.hooks.installed`. Verify post-install: `len(result.hooks.installed) > 0`.

**D-124-06: Spacing between Next-steps and Install Complete**

Insert `console.print()` blank line between `suggest_next()` output and Install Complete panel render.

### Theme B — Doctor-warning provisioning

**D-124-07: Seed default ownership map at install time**

State install phase invokes `default_ownership_map()` and writes seeded map on first install. Doctor `ownership-coverage` probe → 0 warnings.

**D-124-08: Per-install OPA keygen + sign (regulated-grade)**

Install template ships `.rego` + `.manifest` (public). Install runs `opa build` → bundle. Install generates ephemeral RS256 keypair if not present (private at `~/.config/ai-engineering/opa-signing-key.pem` mode 0600; public at `keys/opa-bundle-signing-dev.pub.pem` gitignored). Install runs `opa sign` → `.signatures.json`. Each install has its own root of trust.

Rationale: regulated-industry target. Per-install keygen wins on security: no shared dev key in source repo, per-install signature attestation, rotation supported. Trade-off (~5-10 sec install) acceptable.

### Theme C — Security-gate visibility

**D-124-09: ai-eng doctor secrets-gate probe**

New `src/ai_engineering/doctor/runtime/secrets_gate.py` probe checks: gitleaks binary, gitleaks version, semgrep binary, .semgrep.yml, .gitleaks.toml + .gitleaksignore, pre-commit hook, pre-push hook.

**D-124-10: Document secrets-gate in CONSTITUTION + README**

Short paragraph: pre-commit gate runs gitleaks + ruff format + ruff check + spec verify (sub-1s p95); pre-push gate runs semgrep + pip-audit + pytest + ty; CI re-runs all + extras; findings BLOCK at CRITICAL/HIGH/MEDIUM, WARN at LOW; risk-accept workflow at `ai-eng risk accept --finding <hash>`.

**D-124-11: Trace + clean keys/ file origin**

Identify which test or install step generated `keys/opa-bundle-signing-dev.pub.pem`. Either ensure tearDown cleans up OR redirect output to `~/.config/ai-engineering/`. D-124-08 per-install keygen makes the source-repo `keys/` redundant.

### Theme D — state/ JSON cleanup

**D-124-12: Delete 5 migrated state/ JSON fallbacks + CI guard**

Delete `decision-store.json`, `gate-findings.json`, `ownership-map.json`, `install-state.json`, `framework-capabilities.json`. Update consumers to read from state.db. Add startup migration assertion. NEW `tests/unit/specs/test_state_canonical.py` asserts state/ canonical entries.

### Theme E — Documentation

**D-124-13: New context file `.ai-engineering/contexts/semgrep-update-model.md`**

Documents: registry-fetch behavior, custom-rule merge, CVE limitation, quarterly bump cadence, how-to. Linked from CONSTITUTION.md + install README.

## Risks

- **IDE rename breaks external scripts** hardcoding old keys. Mitigation: manifest read shim with WARN; CLI flag rejection with actionable error; CHANGELOG entry.
- **Per-install OPA keygen fails on locked-down machines**. Mitigation: catch failure; fall back to "ship pre-signed" for that install; doctor surfaces fallback.
- **Hooks count fix exposes other assumption mismatches**. Mitigation: targeted tests + verify multiple fresh installs.
- **Per-tool progress UX degrades terminal performance**. Mitigation: Rich Status throttle 100ms.
- **state/ JSON deletion strands a consumer**. Mitigation: pre-deletion grep + migrate any laggard in same commit. Startup assertion catches runtime.
- **secrets-gate probe false positives** on locked-down PATH. Mitigation: advisory only (WARN); actionable message.

## References

- doc: `/Users/soydachi/.claude/plans/ahora-bien-users-soydachi-repos-ai-engin-typed-dongarra.md` (approved plan)
- pr: arcasilesgroup/ai-engineering#505 (spec-122 + spec-123 delivery, predecessor)
- ext: https://github.com/Gentleman-Programming/engram (Engram supported agents: opencode, claude-code, gemini-cli, codex)
- ext: https://www.openpolicyagent.org/docs/ (OPA bundle build + sign)
- ext: https://semgrep.dev/changelog (semgrep rule pack updates)
