# Changelog — ai-engineering

All notable versions land here. The only notification channel for versions: no
push, no auto-update (§07). Versioning and changelog automation: changesets
(see [.changeset/README.md](.changeset/README.md)).

## 2.0.0 — 2026-09-01

First v2 stable line (blueprint v17). Version bumps and the changelog now flow
through changesets; tag pushes still build the 8 cross-compiled binaries + SBOM.

### Changed
- Version line jumps to 2.0.0 (the 0.x experiment is over; the surface is stable).
- Single version source: `src/version.ts` reads package.json — no drift.
### Added
- `ai-eng chain` — the guard dispatcher: no-verify, self-protect, injection, loop, wrap.
  Fail-closed on any guard crash; verdict cache keyed on one physical tool call.
- `ai-eng git` — the surface-independent floor: pre-commit (diff --check, gitleaks dir
  over staged files, DECISIONS.md gate), commit-msg (convention + Receipt-Id trailer +
  override reason), pre-push (gitleaks over history).
- `ai-eng wrap test -- <cmd>` — deterministic test-output filter (failures grouped, one line).
- `ai-eng spec run|open|approve|close` — executable contract slots; a spec whose sha256
  is not pinned in ai-eng.lock refuses to run (no approval, no execution, §9.3).
- `ai-eng init` (two phases: machine canon + repo contract), `doctor` (12 checks + real
  adversarial probe + p95 latency), `config`, `update` (zero network re-plant),
  `upgrade` (delegates to bun/npm), `uninstall` (keeps the user's four contracts).
- Global canon of 19 ai-* skills (10 core + 9 on demand) integrated per §11 with
  NOTICE.md attribution and machine-global symlinks per surface.
- 4 contract files per repo: AGENTS.md, DECISIONS.md, .ai-engineering/spec.html +
  plan.html; overrides.toml is the only guard-off switch (reason + until required).
- CI in three tiers: pre-commit floor, PR fast lane, merge gate (§17); SBOM on release.
