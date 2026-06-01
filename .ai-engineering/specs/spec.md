---
spec: spec-158
title: Public-install hardening — hook-command migration + operator-anonymity gate
status: approved
effort: small
summary: Two public-install correctness bugs in one spec. (A) spec-154 routed Claude Code hook commands through _lib/run-hook.sh (≥3.11 interpreter resolver) so hosts with python3 < 3.11 stop tracebacking on every tool call; fresh installs are born correct, but existing installs that run `ai-eng update` never get the fix because .claude/settings.json is ownership-protected, so its `python3 ".../X.py"` hook commands are never rewritten — the resolver lands unused. This spec adds a surgical, idempotent migrator that rewrites ONLY exact-shape framework-owned hook command strings inside the protected settings.json, with backup, dry-run visibility, and a skip report. (B) Shipped framework content leaks the operator's machine path/name (`/Users/soydachi/...` in transcript_usage.py docstrings — canonical + template, with template drift), violating Hard Rule 4 (anonymous content) on a public framework every company can install. This spec genericizes the leaks, syncs template↔canonical, and adds a name-agnostic CI gate that flags any `/Users/<name>` or `/home/<name>` operator path in shipped surfaces so no operator identity ever reships.
---

# spec-158 — Migrate hook commands in protected `.claude/settings.json`

## Summary

spec-154 (PR #554) introduced `_lib/run-hook.sh` — a wrapper that resolves a
Python ≥3.11 interpreter before dispatching each hook — and rewired the template
`.claude/settings.json` so every hook command runs through it. This removed
`ImportError: cannot import name 'UTC' from 'datetime'` on hosts whose default
`python3` is < 3.11 (e.g. macOS system `python3` = 3.9). **Fresh installs are
born correct.** Existing installs are not.

When an existing user runs `ai-eng update`, the updater ships `run-hook.sh` and
`resolve-python.sh` as net-new files (no ownership conflict), but
`.claude/settings.json` is **ownership-protected** so update preserves it
verbatim — its hook commands stay `python3 "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/X.py"`.
Result: the resolver arrives but is never invoked, and every Bash/Workflow tool
call keeps tracebacking on < 3.11 hosts. The upgrade path silently fails to
deliver the spec-154 fix.

This spec adds a **surgical, idempotent settings.json hook-command migrator** to
the updater: it rewrites only the exact-shape framework-owned command strings to
route through `run-hook.sh`, leaves every user customization untouched, reports
non-canonical commands as skipped, and is visible in dry-run with a pre-mutation
backup.

## Current State (boundary evidence)

- **The gap.** `updater/service.py::_migrate_hooks_dir` (line ~1181) migrates only
  the hook **directory location** (`scripts/hooks/` → `.ai-engineering/scripts/hooks/`).
  No function rewrites the **command strings** inside `.claude/settings.json`.
  `grep -n "run-hook\|settings.json" updater/service.py` returns only the
  directory-migrator name and an ownership comment — no command migrator.
- **Why update can't touch it.** `.claude/settings.json` carries an ownership
  **deny** rule (`updater/service.py:~599` comment: "`.claude/settings.json` deny
  match before broad `.claude/**` allow"). `FileChange.status` resolves to
  `"protected"` (`updater/service.py:96`), so the reconciler in
  `_UpdateAdapter.plan` (`updater/service.py:231`) never overwrites it.
- **Target post-state (proven, from the template).**
  `templates/project/.claude/settings.json` already ships the correct form:
  `"command": "bash \"$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/_lib/run-hook.sh\" \"$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/telemetry-skill.py\""`.
- **Resolver present after update.** `run-hook.sh` exists in both the canonical
  tree and `templates/.ai-engineering/scripts/hooks/_lib/run-hook.sh`, and update
  already ships it — so the only missing link is the settings.json rewrite.
- **Empirical proof (copilotline, a real pre-spec-154 install).** Before fix,
  every hook tracebacked `ImportError: ... 'UTC'` under `python3`=3.9; after a
  manual settings.json rewrite to `run-hook.sh`, the resolver picked
  `/opt/homebrew/bin/python3.13` and hooks ran clean. The framework must do this
  rewrite automatically on `update`.
- **Scope is narrow.** `.codex/hooks.json` is NOT ownership-protected (update
  overwrites it → already self-heals to `run-hook.sh`); `.github/hooks/hooks.json`
  uses `.sh`/`.ps1`, no `python3`-direct wiring. **`.claude/settings.json` is the
  only stranded surface.**

**Concern B — operator-name leak (boundary evidence):**
- A repo-wide `git grep` for `/(Users|home)/<name>` across shipped surfaces
  (`src/**`, `.ai-engineering/scripts/**`, `docs/**`, root `*.md`) finds the
  operator's machine path in exactly THREE lines, all `soydachi`, all in
  `transcript_usage.py` docstrings:
  `.ai-engineering/scripts/hooks/_lib/transcript_usage.py:9` (canonical),
  `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/transcript_usage.py:9`
  and `:67` (template). `/home/linuxbrew/.linuxbrew` is a legitimate default, not
  an operator path.
- **Template drift**: the canonical copy's `_project_slug` docstring (`:67`) was
  already genericized to `/Users/.../ai-engineering`, but the **template** (the
  copy that actually ships to installs) still carries `soydachi` at `:9` AND
  `:67`. The template is what a company installs — so installed users receive the
  leak (a copilotline contributor manually patched their installed copy).
- **No anonymity gate exists.** `tests/unit/test_no_forbidden_substrings.py`
  scans only `installer/`, `doctor/`, `prereqs/` for install-command literals —
  it has no machine-path/operator-name rule and does not scan the hooks tree or
  templates. Total blind spot for this bug class.

## Goals

- An existing install receives the spec-154 hook-resolver wiring with a plain
  `ai-eng update` — no manual settings.json edit.
- Zero `ImportError: UTC` tracebacks on < 3.11 hosts after `update`.
- User customizations in `settings.json` (added hooks, matchers, timeouts, deny
  rules, key order, formatting) are preserved byte-for-byte outside the rewritten
  command values.
- The migration is idempotent, visible in dry-run, backed up before mutation, and
  reports anything it declines to touch.
- Zero operator-name / machine-home-path leaks in any shipped surface; a CI gate
  prevents re-introduction by ANY operator (name-agnostic).

## Non-Goals

- Touching `.codex/hooks.json` or `.github/hooks/hooks.json` (update already
  overwrites / they have no `python3`-direct wiring).
- A generic versioned settings-migration framework (YAGNI — one targeted rewrite).
- Changing the ownership / protected model for full-file overwrites
  (settings.json stays protected for whole-file replacement).
- Auto-installing a ≥3.11 interpreter (`run-hook.sh` already degrades with one
  stderr line + exit 0 when none is found).
- Re-deriving the resolver design (spec-154; proven).
- Scrubbing operator paths from non-shipped surfaces (tests, runtime, specs) — the
  gate scopes to what installs / publishes; test fixtures may use synthetic paths.
- A general PII/secrets redactor (already covered by `security/redactor.py`); this
  gate is specifically operator-home-path leakage in shipped content.

## Decisions

- **D-158-01 — Surgical migrator in the updater, not a registry.** Add a function
  that scans `.claude/settings.json` `hooks[*].hooks[*].command` and rewrites only
  framework-owned commands. No versioned migration registry, no ownership-model
  split.
  **Rationale**: §10.1 KISS / §10.2 YAGNI — one bug, one targeted fix; the
  surface is a single known file and a single known command shape.

- **D-158-02 — Exact-shape detection only; report skips.** Match exactly
  `python3 "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/<file>.py"[ <args>]`
  and rewrite to
  `bash "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/_lib/run-hook.sh" "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/<file>.py"[ <args>]`.
  Any command pointing into the framework hooks dir that does NOT match the exact
  shape (different interpreter, absolute path, extra flags, custom wrapper) is
  **left untouched and reported as skipped** for manual review.
  **Rationale**: §10.7 Clean Code / safety — never guess at a user's customized
  command inside a protected file; fail visible, not silent.

- **D-158-03 — Auto on `update`, dry-run visible, backup before mutate.** The
  migrator runs as part of `ai-eng update`; it appears in the dry-run plan as a
  distinct change (e.g. `migrate-hooks: N commands`); it applies only under
  `--apply`; it writes a timestamped `settings.json` backup before mutating; the
  summary reports `migrated` + `skipped` counts.
  **Rationale**: §10.5 reversibility — a mutation of a protected, user-owned file
  must be previewable and recoverable.

- **D-158-04 — Framework-owned field migration is exempt from the protected-file
  overwrite block.** Introduce the narrow notion of a framework-owned **field**
  migration that may edit specific values inside an ownership-protected file,
  strictly bounded to exact-shape framework hook command strings. Whole-file
  overwrite of `settings.json` stays denied.
  **Rationale**: ownership protects user intent; a framework command string the
  framework itself authored is framework intent — migrating it forward is not a
  user-content overwrite.

- **D-158-05 — Idempotent.** Commands already routed through `run-hook.sh` are
  detected and skipped; a second `update` reports `migrated: 0`.
  **Rationale**: update is run repeatedly; re-runs must be no-ops.

- **D-158-06 — Minimum-diff rewrite (preserve structure).** Rewrite only the
  `command` string value via targeted edit; preserve matchers, timeouts, sibling
  keys, array order, and JSON validity. No full round-trip reformat.
  **Rationale**: §10.7 Clean Code — the diff must read as "21 command strings
  rewired", nothing else; a reformat would bury intent and churn the user's file.

- **D-158-07 — Scope-agnostic, single target.** Operate on the resolved target's
  `.claude/settings.json` (the `update` target root); no cross-scope traversal.
  **Rationale**: matches the updater's existing single-target contract.

- **D-158-08 — Genericize the operator-name leaks + sync template↔canonical.**
  Rewrite the three `soydachi` docstring examples in `transcript_usage.py` to
  generic placeholders (`${HOME}/.claude/projects/<project-slug>/<session-id>.jsonl`
  and `/Users/.../ai-engineering` → `-Users-...-ai-engineering`), matching the
  already-genericized canonical `_project_slug` style, then make the template
  copy byte-identical to the canonical copy so the drift cannot recur.
  **Rationale**: Hard Rule 4 (anonymous content) — no operator name / machine path
  in committed, shipped files; §10.4 DRY — one canonical source, template mirrors.

- **D-158-09 — Add a name-agnostic operator-path gate.** New test scanning shipped
  surfaces (`src/ai_engineering/**` incl. templates, `.ai-engineering/scripts/**`,
  `docs/**/*.md`, root `*.md`/`CONSTITUTION.md`) for `/(Users|home)/<segment>`
  (and `\Users\<segment>`) where `<segment>` is NOT in a small generic allowlist
  (`user`, `you`, `runner`, `linuxbrew`, `root`, `test`, `example`, `name`,
  `project`, `app`, `ci`, `build`, `home`). It flags ANY operator name — not a
  `soydachi` denylist — so a future operator's path is caught automatically. Tests,
  `runtime/`, `specs/`, `observations/` are out of scope (not shipped).
  **Rationale**: durable prevention over one-off scrub; a public framework must
  never reship operator identity. The existing install-command guard
  (`test_no_forbidden_substrings.py`) is the precedent pattern.

## Risks

- **Mutating a protected, user-owned file.** Mitigation: exact-shape match only
  (D-158-02) + pre-mutation backup + dry-run visibility (D-158-03) + skip report.
- **JSON formatting churn / corruption.** Mitigation: targeted value rewrite
  preserving structure (D-158-06); test asserts minimum diff + JSON validity +
  preserved deny rules.
- **A user's custom command happens to match the exact framework shape.**
  Mitigation: the matched path is framework-specific
  (`.ai-engineering/scripts/hooks/<file>.py`); the canonical shape is what the
  framework itself authored, so rewriting it forward is correct. Low residual
  risk accepted.
- **Double-run / concurrent update.** Mitigation: idempotency (D-158-05).
- **`run-hook.sh` absent on a very old install that skips the file ship.**
  Mitigation: update ships `run-hook.sh` in the same pass; if absent at migrate
  time, skip the rewrite and report (do not wire to a missing wrapper).

## Acceptance

- [ ] AC1 — A settings.json with `python3 ".../hooks/X.py"` commands becomes
      `bash ".../run-hook.sh" ".../hooks/X.py"` after `ai-eng update --apply`.
- [ ] AC2 — User-added hooks, matchers, timeouts, and deny rules are preserved
      unchanged.
- [ ] AC3 — Idempotent: a second `update` reports `migrated: 0`.
- [ ] AC4 — A framework-hooks-dir command that is NOT exact-shape (custom
      interpreter / flags / wrapper) is left untouched and reported as `skipped`.
- [ ] AC5 — Dry-run shows `migrate-hooks: N`; `--apply` writes a backup; the
      summary reports `migrated` + `skipped` counts.
- [ ] AC6 — `settings.json` remains valid JSON; user `deny` rules survive.
- [ ] AC7 — Regression (copilotline shape): after `update`, hooks dispatch via
      the resolver with no `ImportError: UTC` traceback.
- [ ] AC8 — If `run-hook.sh` is absent at migrate time, the rewrite is skipped and
      reported (no wiring to a missing wrapper).
- [ ] AC9 — Full test suite green; `hooks-manifest.json` consistent (note: the
      `transcript_usage.py` docstring fix DOES change canonical hook bytes →
      `hooks-manifest.json` MUST be regenerated and committed).
- [ ] AC10 — Zero `soydachi` (or any operator name) in shipped surfaces; the three
      `transcript_usage.py` docstring leaks are genericized; template copy is
      byte-identical to canonical.
- [ ] AC11 — New name-agnostic gate flags any `/Users/<name>` or `/home/<name>`
      operator path in shipped surfaces (allowlist of generic segments only);
      proven by a fixture that the gate catches a planted operator path and passes
      on `/home/linuxbrew` + `/Users/you`.

## References

- spec-154 (PR #554) — hook interpreter resolver `_lib/run-hook.sh`.
- `src/ai_engineering/updater/service.py` — `_migrate_hooks_dir` (~1181),
  `FileChange.status` (96), `_UpdateAdapter.plan` (231), ownership comment (~599).
- `src/ai_engineering/templates/project/.claude/settings.json` — target command
  shape.
