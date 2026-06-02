---
spec: spec-160
title: "Harden Sentinel IOC runtime: fail-closed + doc-context + path-equivalence"
status: approved
effort: medium
summary: "Harden the Sentinel IOC runtime: opt-in fail-closed on missing/corrupt iocs.json (default off), a doc-extension bypass relaxing only credential-path/env IOC literals on Write/Edit, and a real path-equivalence matcher covering $HOME/absolute-home/Windows forms."
---

# spec-160 — Harden Sentinel IOC runtime

## Summary

The hot-path runtime guard `.ai-engineering/scripts/hooks/prompt-injection-guard.py`
is the real Sentinel enforcement surface. It correctly returns
`allow`/`deny`/`warn` against the canonical IOC catalog today, but three
production-readiness gaps from GitHub issue #549 remain **open and verified
present** (no commit has touched the guard since the issue was filed
2026-05-25; the focused slice still reports `44 passed`):

1. **Fail-open catalog.** `load_iocs()` returns `{}` on a missing or corrupt
   `iocs.json`, and `evaluate_against_iocs()` short-circuits to `verdict=allow`
   on an empty catalog (`prompt-injection-guard.py:509-526`, `:763-765`). Two
   tests actively *pin* this (`test_hook_fail_open_when_catalog_missing`,
   `test_hook_exposes_load_iocs_fail_open`). A missing/corrupt catalog silently
   disables ALL IOC enforcement.
2. **Documentation false-positives.** The only `Write`/`Edit`/`MultiEdit`
   bypass is `_is_test_fixture_target()` (`tests/`/`fixtures/` paths only,
   `:417-439`). A security doc that legitimately *cites* a credential-path or
   env-var literal is denied (`sys.exit(2)`). Confirmed in practice.
3. **Path-equivalence blind spots.** `_expand_user_path()` is an identity stub
   — its docstring promises `$HOME` expansion, its body is `return pattern`
   (`:654-662`) — so matching collapses to naive substring against the
   catalog's `~/` forms. `$HOME/…`, `${HOME}/…`, absolute-home
   (`/Users/<u>/…`, `/home/<u>/…`), and Windows (`C:\Users\<u>\…`) all evade.

This spec hardens all three without changing the safe default-bootstrap
posture, and keeps the separate Layer-2 prompt-injection scan
(`_lib/injection_patterns`) fully active in every code path.

## Goals

- **G1 (fail-closed, opt-in).** With `security.iocs.fail_closed: true` (manifest
  or env override), a **missing OR corrupt** `iocs.json` produces a
  deterministic exit-2 deny with a distinct audit event. With the flag **off**
  (default), behavior is byte-identical to today (`allow`).
- **G2 (recovery survives lockout).** When fail-closed denies, the pre-IOC
  bypass lanes (`ai-eng risk accept*` Bash whitelist; trusted hash-pinned
  scripts) still function, so an operator can always recover. The deny message
  names the recovery path.
- **G3 (doc-context relax, scoped).** A `Write`/`Edit`/`MultiEdit` to a
  doc-extension target (`*.md`, `*.mdx`, `*.markdown`, `*.rst`, `*.txt`) that
  contains a literal credential-path or sensitive env-var name is **allowed**;
  the identical content written to a non-doc target (e.g. `*.py`/`*.yml`/`*.sh`)
  or supplied via `Bash` is still **denied**.
- **G4 (doc relax does not weaken the rest).** On a doc target, the
  `malicious_domains` and `shell_patterns`/`dangerous_commands` IOC categories
  AND the Layer-2 `_lib/injection_patterns` scan remain fully active. A doc that
  contains a live malicious domain or an injection phrase is still denied.
- **G5 (auditable bypass).** Every doc-context bypass emits a distinct audit
  event (parallel to the existing `ioc-scan-test-fixture-bypass`).
- **G6 (path equivalence, POSIX + Windows).** Each `~/X` catalog pattern also
  matches `$HOME/X`, `${HOME}/X`, `/Users/<u>/X`, `/home/<u>/X`, and the
  Windows `C:\Users\<u>\X` form (backslash-normalized, drive-letter aware,
  case-insensitive on Windows-shaped paths) — when the target is not a doc.
- **G7 (battery stays green + new coverage).** The existing Sentinel test
  battery passes; new tests cover fail-closed (flag on AND off), doc-target
  bypass (allow case + still-deny cases), and path-equivalence (all forms).

## Non-Goals

- **Changing the default posture.** Fail-closed stays opt-in; the shipped
  default remains fail-open so fresh installs and bootstrap never lock out.
- **Expanding detection content.** No new `iocs.json` entries, no new
  injection patterns; this is enforcement-plumbing hardening only.
- **Touching Layer-2.** The `_lib/injection_patterns` rule set is unchanged.
- **A Write-to-iocs.json escape hatch.** Recovery is via the existing
  risk-accept lane, not a new write exemption to the catalog file.
- **Bash doc-context handling.** `Bash` never receives the doc bypass.
- **Per-category doc-relax toggles.** The relaxed set (`sensitive_paths` +
  `sensitive_env_vars`) is fixed in code, not manifest-configurable.
- **Fixing the spec-lifecycle numbering/labeling bug** discovered while minting
  this spec (archive dir `spec-159-installer-parity` vs ledger id `spec-158`;
  `_next_spec_number` ignores archive dirs). Tracked separately.

## Decisions

- **D-160-01 — Fail-closed is opt-in (manifest + env), default off.**
  Add `security.iocs.fail_closed` (default `false`) plus an
  `AIENG_IOC_FAIL_CLOSED` env override (env wins, matching the repo's
  established escape-hatch pattern).
  *Rationale*: a hard fail-closed default creates a chicken-and-egg lockout —
  you cannot restore `iocs.json` via the guarded `Write` tool once the catalog
  is gone. Default-off preserves the bootstrap-safe contract; regulated
  environments opt in deliberately.
- **D-160-02 — Missing and corrupt are treated identically under fail-closed.**
  When the flag is on, both a missing file and an unparseable/non-dict catalog
  produce exit-2 deny with audit evidence.
  *Rationale*: from an enforcement standpoint an absent catalog disables the
  guard exactly as a corrupt one does; both are equally dangerous, so both must
  block.
- **D-160-03 — Recovery reuses the existing pre-IOC bypass lanes.** No new
  escape hatch. `ai-eng risk accept*` (Bash whitelist) and trusted
  hash-pinned scripts already evaluate before the IOC layer, so they remain
  usable during a fail-closed lockout.
  *Rationale*: reuse the already-audited bypass surface; avoid introducing a
  Write-to-catalog hole that an attacker could leverage.
- **D-160-04 — Doc targets are classified by a non-executable extension
  allowlist.** `*.md`, `*.mdx`, `*.markdown`, `*.rst`, `*.txt` on
  `Write`/`Edit`/`MultiEdit` only.
  *Rationale*: an extension allowlist is the simplest classifier that is hard to
  abuse (the formats are non-runnable) and it automatically covers `spec.md`,
  `CHANGELOG.md`, `README.md`, `CONSTITUTION.md`, and `docs/**/*.md` without a
  path-glob registry.
- **D-160-05 — The doc bypass relaxes only `sensitive_paths` +
  `sensitive_env_vars`.** `malicious_domains`, `shell_patterns`/
  `dangerous_commands`, and the Layer-2 injection scan stay active on doc
  targets.
  *Rationale*: only credential-path and env-var literals legitimately appear in
  security documentation; a live malicious domain or an injection phrase in
  prose is still worth denying.
- **D-160-06 — Every doc bypass emits a distinct audit event.** Mirror the
  existing `ioc-scan-test-fixture-bypass` with an `ioc-scan-doc-context-bypass`
  `control_outcome` event.
  *Rationale*: regulated environments must be able to see every relaxation in
  the audit trail.
- **D-160-07 — `_expand_user_path()` gets a real implementation.** For each
  `~/X` pattern it yields the equivalence set `~/X`, `$HOME/X`, `${HOME}/X`,
  and anchored regex forms for `/Users/<u>/X` and `/home/<u>/X`.
  *Rationale*: the identity stub is the literal bug; `$HOME` and absolute-home
  are trivial one-keystroke evasions of credential-path detection today.
- **D-160-08 — Windows path forms are in scope.** Backslash↔slash
  normalization, `C:\Users\<u>\…` drive-letter handling, and case-insensitive
  compare for Windows-shaped paths.
  *Rationale*: Claude Code runs on Windows; a POSIX-only matcher leaves the
  whole platform unguarded. Windows normalization is gated behind path-shape
  detection so it never perturbs POSIX matching.
- **D-160-09 — Fail-open test pins are made flag-aware, not deleted.** The
  default-off path keeps asserting `allow` on a missing catalog; new tests
  assert `deny` under the flag.
  *Rationale*: the bootstrap-safe default is a real, documented contract worth
  keeping under test — we are adding a strict mode, not removing the safe one.

## Risks

- **R1 — Operator enables `fail_closed`, then hits a corrupt catalog
  mid-session → repo-wide deny.** *Mitigation:* risk-accept lane stays usable
  (D-160-03); `AIENG_IOC_FAIL_CLOSED=0` instantly reverts; the deny message
  names both recovery paths.
- **R2 — Doc-extension allowlist abused by naming a payload `evil.md`.**
  *Mitigation:* the bypass relaxes only `sensitive_paths`/`sensitive_env_vars`
  literals (D-160-05); domains, shell patterns, and the Layer-2 injection scan
  still fire; `.md` content is non-executable; `Bash` is never bypassed.
- **R3 — Windows path normalization regresses POSIX matching** (e.g. a legit
  backslash in a POSIX filename). *Mitigation:* gate Windows normalization
  behind drive-letter/backslash shape detection; leave the POSIX path unchanged;
  test both platforms.
- **R4 — Absolute-home regex over-broadens** and false-positives on unrelated
  content containing a home prefix. *Mitigation:* anchor each regex to the
  catalog's specific suffix (e.g. the AWS credentials dotfile suffix), never to
  a bare home directory.
- **R5 — Hot-path budget.** Extra expansion + regex per pattern runs on every
  guarded `Write`/`Bash`. *Mitigation:* precompile the expanded regex set once
  at catalog load; the catalog holds ~15 path patterns, so per-call cost stays
  far under the <1s pre-commit / hook budget.

## References

- work-item: arcasilesgroup/ai-engineering#549
- doc: .ai-engineering/scripts/hooks/prompt-injection-guard.py
- doc: tests/integration/test_sentinel_runtime_iocs.py
- doc: .ai-engineering/security/iocs/iocs.json

## Open Questions

- Audit event field shapes: does `ioc-scan-doc-context-bypass` need to carry the
  matched-but-bypassed pattern names, or just the target path + category? (Lean:
  include category + path; omit the literal to avoid re-introducing the
  credential string into the audit log.) Resolve in `/ai-plan`.
