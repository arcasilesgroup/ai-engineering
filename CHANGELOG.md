# Changelog — ai-engineering

## 2.4.0

### Minor Changes

- [`d5fe006`](https://github.com/arcasilesgroup/ai-engineering/commit/d5fe006a2ee2f883b7a6446039be6a7108308659) Thanks [@soydachi](https://github.com/soydachi)! - Block direct pushes to main via pre-push hook, security fixes (ReDoS, Snyk taint chain), and cognitive complexity refactors across doctor/init/uninstall/commands

## 2.3.0

### Minor Changes

- [`83b942f`](https://github.com/arcasilesgroup/ai-engineering/commit/83b942fbe86d6f39852df4a9c75924115946ba60) Thanks [@soydachi](https://github.com/soydachi)! - Governance by observability, not by more stoppers (research/001 R1+R2). `doctor`'s receipts line is no longer four numbers: it names the top denier guard/tool, the ledger's repeat count, and WARNs when the last 7 days of denies pass 3x the prior week. The gc that already collects receipts now merges a 90-day daily series into `summary.json` instead of overwriting it, and prunes the new `receipts/denies.json` ledger (age + newest-500) instead of deleting it. The ledger is the cross-session memory OWASP ASI01/ASI06 need: when a guard denies a call this exact machine already denied, the human message says `· this exact call has been denied N times before`. Signal only — no verdict, no new config, no dependency; deny receipts finally carry their real tool instead of `unknown`.

- [`57efe8e`](https://github.com/arcasilesgroup/ai-engineering/commit/57efe8ea66aedd7ed46296d371a6faa9669c02a5) Thanks [@soydachi](https://github.com/soydachi)! - Session handoff improvements (research 006 R1/R2/R3). `ai-eng briefing` generates a session handoff briefing with spec gates, plan step, recent denies, and receipt summary — closing the "rebuild state from scratch" gap (20/90 sessions needed manual "continua"). Receipts now carry `session_id` and `summarizeBySession()` groups them for per-session queries. Research cache (`research-cache/`) persists findings between sessions with doctor reporting and gc auto-prune for entries >30d.

### Patch Changes

- [`83b942f`](https://github.com/arcasilesgroup/ai-engineering/commit/83b942fbe86d6f39852df4a9c75924115946ba60) Thanks [@soydachi](https://github.com/soydachi)! - Docs, comments and specs now describe the product as it is, not as it was. The canon carried ghosts of the v1 Python era and the deleted ai-rtk skill: `ai-verify`'s eval harness claimed "Python 3.8+" while running on Bun, `ai-explore`'s example diagram cited a `chain.py` that does not exist, `ai-write` cited "spec 039/033" from the dead v1 spec-number registry, `ai-visual-recap` routed readers to the out-of-canon visual-plan skill, and `blueprint.html`/`recap.html` still listed ai-rtk in the canon trees, lineage and lifecycle tables and pinned version 0.13.0. Root docs drifted too: `AGENTS.md` pinned 2.2.0 and the retired `tsc --noEmit`, `THIRD-PARTY-NOTICES.md` listed dependencies package.json does not carry, `brand/README.md` documented a nonexistent `brand.ts legacy` subcommand, and `NOTICE.md` omitted the shipping ai-stress-test. Source comments narrating past bugs ("used to…", "no longer…") were rewritten to state the present rule; blueprint stamps now read 2.2.3, and ai-stress-test is listed where the canon is enumerated. No behavior changed — every diff is prose, verified against the tree.

## 2.2.3

### Patch Changes

- [#727](https://github.com/arcasilesgroup/ai-engineering/pull/727) [`7504041`](https://github.com/arcasilesgroup/ai-engineering/commit/75040413fc3e0877fba4948d8a4ce77ac07779e5) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng` crashed on startup under Bun 1.3.x: the banner frame painted the brand hex `#00ED64` through `styleText` (node:util), whose runtime validation accepts only named formats — strict runtimes threw `ERR_INVALID_ARG_VALUE` on the first render, and lenient ones (Bun 1.4, Node ≥ 24.1) silently dropped the colour, so the banner shipped unpainted there. The banner now emits the truecolor SGR sequence for the declared hex itself, degrading to plain text under `NO_COLOR` or a non-TTY stdout — the same rule the rest of the frame follows. `BANNER_META` keeps its named format through `styleText`.

## 2.2.2

### Patch Changes

- [`c46c261`](https://github.com/arcasilesgroup/ai-engineering/commit/c46c26132bb2336a41e65ec1c82c5d97d134ecb3) Thanks [@soydachi](https://github.com/soydachi)! - npm install -g ai-engineering@2.2.1 was broken: `src/assets.ts` imports seven fixture scripts with `with { type: "file" }` from `scripts/.embed/`, but the npm `files` whitelist did not include it, so the tarball shipped without them and `ai-eng` aborted on first run ("Cannot find module '../scripts/.embed/..."). The whitelist now ships `scripts/.embed`; verified by installing the packed tarball and running `ai-eng --version` + `doctor`.

## 2.2.1

### Patch Changes

- [#724](https://github.com/arcasilesgroup/ai-engineering/pull/724) [`a045fa9`](https://github.com/arcasilesgroup/ai-engineering/commit/a045fa9cf172b3edc05d54ca70ad60cd7ea05f16) Thanks [@soydachi](https://github.com/soydachi)! - `ai-security` findings now say where they stand, not only that they were real. A confirmed finding carried `verdict: "confirmed"` and nothing else, so one fixed in the same session kept reading as a live vulnerability: the next audit re-derived it, `REPORT.md` was the only artifact that said "fixed", and the milestone CHECK "zero open HIGH findings" had nothing in the machine-readable half to evaluate.
  
  Every confirmed finding now carries a `disposition` — `{"status": "open"}` while the vulnerability is in the tree, or `{"status": "fixed", "landed_in": "<sha>"}` once the fix has landed. The schema refuses `fixed` without the commit that carries it, so no report can claim a fix nobody can resolve. Phase 5 requires the field, and the prior-run ledger reads it: a `fixed` finding is closed ground, an `open` one is where the next run digs.
  
  A `findings.json` written before this change is refused by `validate-findings.cjs` until it is stamped, which is the point — the two runs this repository keeps were stamped with the commits that carry their fixes.

- [#724](https://github.com/arcasilesgroup/ai-engineering/pull/724) [`a045fa9`](https://github.com/arcasilesgroup/ai-engineering/commit/a045fa9cf172b3edc05d54ca70ad60cd7ea05f16) Thanks [@soydachi](https://github.com/soydachi)! - The session can write its own artifacts again: `self-protect` was denying the session everything under `.ai-engineering/`.
  
  That protection was a plain directory literal, so it covered every child of the directory — the four milestone slots (`spec.html`, `plan.html`, `brainstorm.md`, `recap.html`), the receipts, the cache, and the artifacts the canon's own nodes promise in their `Writes:`: `ai-research` writes `research/NNN-{name}.html`, `ai-security` writes `security/run-N/findings.json` and `REPORT.md`, `ai-design` writes `design/direction.html`. Nothing else writes those files, so the guard denied the only writer there is — a `brainstorm.md` came back as "this file governs you", and a research or security node could not leave the artifact its own contract requires. It also shadowed the pin check: an approved contract is frozen by the sha256 in the lock, and that check was never reached while the directory literal answered first.
  
  The fence is now the machinery and only the machinery: the four files the chain itself reads (`config.toml`, `overrides.toml`, `ai-eng.lock`, `arch.rules.json`), the git floor, the machine-side canon and carriers, and `spec.html` once its sha256 is in the lock. Everything else under the directory is the session's own material. The directory itself is matched as a terminal segment, never a prefix — `rm -rf .ai-engineering` names the machinery in one word and stays denied, while `.ai-engineering/research/002.html` is not the directory and is a write like any other.
  
  The four slot names still live in one place, `src/shared-slots.ts`, because `spec` sweeps them at `spec close`; the guard no longer needs the list, since it no longer carves an exemption out of a directory literal.

- [#724](https://github.com/arcasilesgroup/ai-engineering/pull/724) [`a045fa9`](https://github.com/arcasilesgroup/ai-engineering/commit/a045fa9cf172b3edc05d54ca70ad60cd7ea05f16) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng update` reports both halves it owns, and a no-op is no longer printed as a write. The machine half was visible only when something was wrong: a healthy canon, an unchanged git floor and a carrier already at the binary's bytes printed nothing, so a run that verified everything looked exactly like a run that never looked — and the module carriers were rewritten and counted every time, which is how "all 7 assets current — nothing to sync" arrived with a line claiming the machine side was the work.
  
  The repo and the machine now each report as one block, every part named with its outcome: `Repo assets` lists the files it holds when there is nothing to write, `Machine side` names the canon, each declared surface's carrier, the git floor and the machine ledger, and the closing line says whether anything was written at all. Identical bytes are skipped rather than rewritten, so `written` means a change.
  
  What an existing install will notice: the second `ai-eng update` in a row now ends in "Nothing written — the repo and the machine already match ai-eng <version>" instead of the counts of a run that looked like it had done something.

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
