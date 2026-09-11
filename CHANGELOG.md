# Changelog — ai-engineering

## 2.1.0

### Minor Changes

- [`f2e5ee1`](https://github.com/arcasilesgroup/ai-engineering/commit/f2e5ee196ad65ede7339477d619afe64f25cd678) Thanks [@soydachi](https://github.com/soydachi)! - skills: ai-agents-md gains the audit path. A repo that already ships an AGENTS.md set is
  inspected before anything is written: a rule the code already states, a child that repeats its
  parent, a command that no longer runs, a zone an agent must work in with no route. The findings
  and the target set are proposed first, and only an answer earns the edit. The written set is
  mirrored per directory (a sibling `CLAUDE.md` to each `AGENTS.md`), ai-write now routes to its
  README, CONTRIBUTING and SECURITY references instead of shipping them unread, and the
  unreferenced `agents-md-writer` reference is gone.

### Patch Changes

- [`1f862ef`](https://github.com/arcasilesgroup/ai-engineering/commit/1f862ef3c43cb5d5d65e0c88bbf6ac13167cfb29) Thanks [@soydachi](https://github.com/soydachi)! - fix(chain): overrides.toml now loads — the only guard-off switch had never worked
  
  `readOverrides` looked up the literal TOML key `guard.off`, but `[[guard.off]]`
  parses as `{ guard: { off: [...] } }`: a dotted key nests, and the literal never
  exists. Every file returned an empty list, so §09.1's sole mechanism for turning a
  guard off was inert — a written exception with a reason and an end date changed
  nothing, and the guard kept denying.
  
  Doctor now also dates what it reads: an override renders as `expires in 3d`, an
  entry with no `until` is named as never-expiring, and an entry whose date has
  passed is reported with the removal it needs, so dead config stops hiding behind
  `none active`.
  
  `doctor` now answers the question existence cannot: for every surface that runs the
  guard in-process, the planted `ai-eng-chain.ts` is compared byte for byte against
  the chain this binary ships. A stale or hand-patched bundle reports `is NOT the
  chain this binary ships → ai-eng update` instead of passing as present.
  
  `ai-eng <typo>` no longer answers with a bare `unknown verb`: the nearest verb is
  named, or the help line that follows it (§14.5b).

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
