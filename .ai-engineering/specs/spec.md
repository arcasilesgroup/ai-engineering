---
spec: spec-179
title: Exclude sha-pinned hook scripts from framework formatters
status: in-progress
effort: medium
summary: Skip the sha-pinned `.ai-engineering/scripts/` tree in every framework formatter (gate + PostToolUse auto-format), plus a safe `ai-eng doctor --fix` that re-pins only benign reflow drift — so consumer installs stop bricking all hooks on first commit.
---

# spec-179 — Exclude sha-pinned hook scripts from framework formatters

## Summary

The framework runs `ruff format` over staged Python in two paths — the
`ai-eng gate pre-commit` Wave-1 formatter (`cli_commands/gate.py` staged
partition) and the `auto-format.py` PostToolUse hook. Both will reformat
files under `.ai-engineering/scripts/` — the exact files whose sha256 is
pinned in `.ai-engineering/state/hooks-manifest.json` for integrity. The
canonical scripts are authored at `line-length = 100`. Any consumer repo
whose ruff config differs (a JS/Astro project carries none → ruff's
default 88) reflows those scripts on the first commit, every hook's live
sha drifts from its pin, and `AIENG_HOOK_INTEGRITY_MODE=enforce` then
refuses to run all hooks. Greenfield `ai-eng init` masks this by shipping
a `ruff.toml`; installing onto an already-developed project (where the
installer will not clobber existing config) ships no exclusion, so the
break is guaranteed. Reproduced in `ai-engineering-web`: all 76 hooks
mismatched (100→88 reflow), Stop hooks blocked. The pinned directory must
be byte-stable against every formatter the framework itself runs.

## Goals

- No framework-run formatter ever rewrites a file under
  `.ai-engineering/scripts/` (pre-commit gate path AND PostToolUse
  auto-format path).
- A consumer repo with a non-100 ruff width can stage, format, and commit
  without any hook-manifest sha drift — verified by a regression test that
  formats with an 88-col config and asserts the manifest still verifies.
- The exclusion lands identically in the canonical hook script and its
  `src/ai_engineering/templates/` twin (installer copy), with a test that
  asserts both copies carry the guard.
- `ai-eng doctor` detects formatter-induced pin drift and, under `--fix`,
  re-pins ONLY when the on-disk script is logically identical to the
  framework's bundled reference (pure reflow); substantive or unprovable
  drift is reported and left for the operator.
- Existing broken installs (the `ai-engineering-web` class) recover with a
  single `ai-eng doctor --fix`, no manual incantation.

## Non-Goals

- Shipping or merging a `ruff.toml` into consumer repos (rejected: ruff-only,
  intrusive to consumer config, nothing to merge into for non-Python repos).
- Changing the hooks-manifest schema or the integrity hashing algorithm.
- Weakening `enforce` mode, or normalizing/canonicalizing bytes before
  hashing (would mask real tampering).
- Rewording the integrity mismatch error message (separate concern).
- Auto-formatting hook scripts to the consumer's width — they remain
  framework-authored at 100-col.
- Covering pinned paths outside `.ai-engineering/scripts/` (none exist today).

## Decisions

### D-179-01 — Path-prefix exclusion in both formatter runtime paths

Skip any file whose normalized path contains the `.ai-engineering/scripts/`
segment, in both `cli_commands/gate.py` (staged-file partition) and
`auto-format.py` (PostToolUse). Match on a posix-normalized path so
relative/absolute/Windows separators all resolve.

**Rationale**: `.ai-engineering/scripts/` is exactly the byte-stable,
sha-pinned boundary. A path-prefix test needs no manifest parse on the
formatter hot path and naturally covers the `_lib/` helpers (also pinned).
The manifest-derived alternative is more precise but pays a hot-path parse
+ cache; shipping a `ruff.toml` only covers ruff and intrudes on consumer
config. Path-prefix is the smallest correct mechanism. Over-broad matches
(a non-pinned `.py` added under `scripts/`) are acceptable — everything
there is framework-owned and meant to be byte-stable.

### D-179-02 — Scope is prevention PLUS doctor self-heal

Ship both the formatter exclusion (prevention) and an `ai-eng doctor`
self-heal that recovers already-broken installs.

**Rationale**: the exclusion stops *future* breaks but does nothing for
repos already bricked by an earlier commit (e.g. `ai-engineering-web`).
Operators should not need to know the `regenerate-hooks-manifest.py`
incantation; `ai-eng doctor --fix` is the established recovery surface and
gives zero-touch recovery.

### D-179-03 — doctor self-heal is safe-by-default (fail-closed)

`ai-eng doctor --fix` re-pins (or restores) a drifted pinned script ONLY
when the on-disk content is AST-equivalent to the framework's bundled
package reference — i.e. the drift is pure reflow. Substantive or
unprovable drift (no bundled reference available, or AST differs) is
reported and NOT auto-pinned.

**Rationale**: integrity is a fail-closed security boundary
(`reference/gate-policy.md`). Aggressively re-pinning any drift would
auto-bless a tampered hook and silently trust it. Gating on
AST-equivalence to a trusted reference distinguishes benign reflow from a
real byte change, preserving the integrity guarantee while still
recovering the common case.

### D-179-04 — Template-twin parity is part of the change

The exclusion is applied to the canonical
`.ai-engineering/scripts/hooks/auto-format.py` AND its twin
`src/ai_engineering/templates/.ai-engineering/scripts/hooks/auto-format.py`
in the same change, with a regression test asserting both carry the guard.

**Rationale**: the installer copies the template into new projects; drift
between canonical and template would ship the unfixed formatter to every
fresh install. There is no existing CI guard for this particular twin, so
the parity assertion must be authored here.

### D-179-05 — Integrity stays strictly fail-closed

No change to `enforce` semantics or the hashing path. The fix removes the
formatter *cause*; the check itself is unchanged.

**Rationale**: the correct fix is to stop touching pinned bytes, not to
relax the detector. Keeping the check strict means genuine tampering still
blocks.

## Risks

- **R1 — framework's own dev loses auto-format on hook scripts.** Excluding
  `.ai-engineering/scripts/` means framework developers no longer get those
  files auto-formatted by the gate/hook. *Mitigation:* the framework repo's
  own CI `ruff format --check .` (pyproject `line-length = 100`) still
  enforces formatting; in-repo the exclusion is a no-op because on-disk
  bytes already match the 100-col pins.
- **R2 — bundled reference may be absent for the AST compare.** doctor's
  safe-heal needs the framework's shipped script copy to compare against;
  if the installed package lacks it, benign drift can't be proven.
  *Mitigation:* fall back to report-only (fail-closed) — never auto-pin
  without a reference.
- **R3 — template-twin parity has no CI guard (known repo gap).** The
  exclusion could regress in one copy. *Mitigation:* regression test loads
  BOTH copies and asserts the guard text/behavior in each.
- **R4 — path matching across separators.** A naive substring match could
  miss Windows separators or relative paths. *Mitigation:* normalize to a
  posix path and match the `.ai-engineering/scripts/` segment; cover with a
  unit test over absolute/relative/Windows inputs.

## References

- doc: .ai-engineering/reference/gate-policy.md
- doc: .ai-engineering/scripts/hooks/auto-format.py
- doc: src/ai_engineering/cli_commands/gate.py
- doc: .ai-engineering/state/hooks-manifest.json
