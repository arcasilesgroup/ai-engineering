# Changelog — ai-engineering

## 2.2.0

### Minor Changes

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - A gate whose check prints nothing is no longer ticked: `test -f X` and `ls X >/dev/null` exit 0 while saying nothing, so the box rested on an exit code and the ledger carried the silence as evidence. The executor now leaves such a gate UNMET and writes the remedy into its `EVIDENCE` line, and `templates/spec.html.tpl` + the ai-proof canon teach the alternative in place of the existence probe they used to show.
  
  What an existing install will notice: a milestone that already had gates of this shape reports them UNMET on the next `ai-eng spec run`. The fix is one line per gate — make the check print what it found (`test -f X && echo "X $(wc -c < X) bytes"`), or assert its output with `EXPECT: <text|/regex/>`. Nothing is unticked by the tool: the box stays as its author set it and the evidence is what stops counting, which is the same rule the executor already applied to a check that fails.

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - The carrier moves to where each host reads it, and the repo declares itself: `.ai-engineering/config.toml` existing, parsing and naming its surfaces is the single gate every verb asks. A governed repo keeps two carriers — Cursor's and Copilot's, whose cloud readers only see the checkout — while Claude Code, Oh My Pi, OpenCode, Codex and Pi are written once per machine, at the path that host actually loads (the OMP carrier lived in `.agents/hooks/`, which no OMP code path reads, and doctor called it green).
  
  Files the user also owns are merged by marker and never written whole; a settings file this installer would have to reformat is refused and named instead of rewritten. `init.templateDir` makes every new clone be born with the git floor, the shim asks the same gate, a foreign `templateDir` keeps its own hooks, and `uninstall` restores what was there. `doctor` separates the machine carrier, the repo declaration and the version state, and names a downgrade and Codex's `/hooks` re-approval instead of assuming green.
  
  What an existing install will notice: `ai-eng update` moves the carriers out of the repo, sweeps the ones that used to live there, writes the machine side, and records which version wrote what in `~/.ai-engineering/machine.json`.
  
  `AI_ENG_HOME` also redirects the one setting the floor writes outside a home: with it set, the global `init.templateDir` lives inside the override instead of the developer's git config, unless the caller already chose a `GIT_CONFIG_GLOBAL` of its own.

### Patch Changes

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - ai-goal finds the milestone on its own: Step 0 reads the spec slot from `ai-eng doctor`, then spec.html's context chain, plan.html, the handshake doc at `.ai-engineering/brainstorm.md` and the `[budget]` section, so a fresh session is launched as `/ai-goal` with no briefing prompt. ai-plan says where its working file lives: the slot, never a `.wayfinder/` map beside it.

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - init offers the global canon instead of installing it in silence: inside a repo on a machine that has no canon, the machine side is asked for before anything outside the repo is written, and a no leaves it untouched. §14.5b path 2.

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - The CI workflow `init` installs no longer reddens a project between milestones. Its spec-run step called `ai-eng spec run` unconditionally, and the binary is right to exit 2 when there is no `spec.html` — so a project with no live contract, which is the normal state after a contract closes, had a failing gate for a state that is not a failure. The step distinguishes the two now: no `spec.html` and no pin in the lock is "nothing to enforce between milestones" (exit 0), while a lock that still pins an approved contract whose `spec.html` has vanished fails and names the reason, because that is a contract someone deleted. A live contract still runs, and a check that cannot run is still a FAIL — the guard is about the state, never about a check.

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - The surface picker stops promising what the measurements contradict: its group headers stated a capability that neither row under them had ("experimental — rewrite may be partial" for a Cursor with no output rewrite and a Codex that replaces the whole input), and the row that matters carries its own measured degradation, with the source. The registry gains the state it was missing — `deny: "host-only"` — for a host like Zed, which denies through its own `agent.tool_permissions` and its `always_deny` regexes while offering no hook for the chain to run in; the picker used to print "can't block tool calls" about a host that can, and now says which of the two facts it means. `doctor` prints that caveat from the one place it is written instead of guessing it from a substring.

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - `update` now reaches the machine half even when the repo is already current. A repo whose assets all match the binary returned from the sync plan before the declared surfaces' carriers and the git template dir were touched — so a machine that had lost its carrier, which is exactly the state `doctor` answers with "→ ai-eng update", could not be repaired by the verb it named: the remedy ran, printed "all N assets current — nothing to sync", and changed nothing. The machine-side work moved into its own step, and both paths run it.
  
  What an existing install will notice: on a machine that lost a carrier (a wiped home, or `uninstall` at machine scope), `ai-eng update` now rewrites it and says which file it wrote, instead of reporting that nothing needed doing.

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
