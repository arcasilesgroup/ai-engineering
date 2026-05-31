---
title: "Global Install Work-Plane — Read-Only Global Brain + Per-Repo Work-Plane (Auto-Init Hybrid)"
status: draft
audience: framework-dev
branch: feat/global-install-work-plane
length_estimate: L
authoring_style: brief
principles_required: ["§10.1", "§10.2", "§10.4", "§10.5", "§10.8"]
delivery_mode: standard
mantra: "Global is a read-only brain; the work-plane is always local."
---

# Global Install Work-Plane — Read-Only Global Brain + Per-Repo Work-Plane (Auto-Init Hybrid)

> Design hardened across two passes. Pass 1 (design+critique) resolved four
> must-fix blockers (resolver-predicate contradiction, allowlist-vs-structural
> "governed", commit/release state routing, no-shims migration). Pass 2 (a
> strategy judge-panel, 8 agents) confirmed the model: support a global
> install, but as a **read-only brain** with **no global work-plane, ever** —
> the dominant git/terraform/npm pattern (global tooling + cache, per-repo
> state). The panel's default was fail-loud explicit `ai-eng init`; the
> operator chose **auto-init**, reconciled here as the **hybrid**: auto-create
> the local plane on first governed write, anchored at the git root, announced
> on stderr, never silent, never at `$HOME`. The hooks exit-127 defect (global
> `~/.claude` hook wiring crashes in any repo without `.ai-engineering`) is
> carved into its own brief — `global-hook-surface-resilience-brief.md` — and
> is OUT of scope here. Remaining genuine choices live in Section 9.

## 1. Vision

A global install (`ai-eng install --global`) makes the **brain** — skills,
agents, hooks, policies, overrides, reference — available in every directory of
the machine, exactly as `npm -g`, `~/.cargo/bin`, and `uv tool` make tooling
ubiquitous without owning any project's state. The **work-plane** (specs, plans,
decisions, audit chain, runtime) is never global: it is local to each repo and
materializes lazily, anchored at the repo root, the first time a governed write
needs it. After this change, `ai-eng install --global` followed by work in any
uninitialized repo "just works": skills run everywhere, and each project gets
its own isolated `.ai-engineering` on first governed write — no cross-project
collision, no silent leakage into `$HOME`.

## 2. Scope Boundary

**In scope**

- A single unified work-plane root resolver with an unconditional `$HOME` /
  filesystem ceiling, so walk-up never adopts the global brain as a work-plane.
- A **structural** write-intent chokepoint (not a hand-maintained command list)
  that triggers auto-bootstrap of a minimal local work-plane at the repo root.
- A brain-READ fallback: brain assets resolve from the global plane when absent
  locally; work-plane writes only ever target the resolved local plane.
- Collapse of the five divergent root resolvers (two in `paths.py`, three
  private `_resolve_project_root` variants) into the one resolver.
- Definitive hook behavior: hooks never write outside a resolved local plane,
  never bootstrap on the hot path, and never create a markerless plane.
- Fix the misleading `Installed to: <cwd>` human line and the JSON envelope
  `root` value under global scope.

**Explicitly NOT in scope**

- Relocation tooling for users who accumulated work-plane state inside a
  pre-existing global `~/.ai-engineering` (an advisory is in scope; the
  relocation command is deferred — Section 9).
- Wizard UX redesign and `doctor scope_status` overhaul beyond one advisory.
- Branch-policy-in-global automation.
- Any backwards-compat shim for the renamed resolvers (CONSTITUTION.md §3 —
  hard rename + hard delete, documented in CHANGELOG).

## 3. Diagnostic Snapshot

A global install **does** install the brain correctly to `$HOME`, but work-plane
resolution silently routes project state into that global plane, producing
cross-project collisions. The codebase already proves this is a single-seam
defect, not an architectural one.

- Five resolvers disagree on "what the project is." `find_project_root()` walks
  up to the nearest `.ai-engineering` ancestor with **no upper-bound sentinel**
  (`src/ai_engineering/paths.py:57`, walk at `src/ai_engineering/paths.py:64`);
  `resolve_project_root()` is cwd/target-only with no walk-up
  (`src/ai_engineering/paths.py:12`); and three private cwd-only copies exist
  precisely to dodge the walk-up's global-bleed hazard:
  `src/ai_engineering/cli_commands/risk_cmd.py:74` and
  `src/ai_engineering/cli_commands/audit_cmd.py:51` (the docstrings explicitly
  cite "stale ancestor `.ai-engineering` directories" as the reason).
- Work-plane and governance-state commands use the **walk-up** resolver:
  `spec_cmd.py:153`, `plan_cmd.py:219`, `decisions_cmd.py:39`,
  `ownership_cmd.py:133` (paths under
  `src/ai_engineering/cli_commands/`). With no ceiling, from an uninitialized
  repo under `$HOME` the walk climbs past the repo and binds to
  `$HOME/.ai-engineering` (`src/ai_engineering/paths.py:64`).
- Every work-plane / state artifact derives purely from the passed root:
  `resolve_active_work_plane` (`src/ai_engineering/state/work_plane.py:168`),
  `DurableStateRepository` paths (`src/ai_engineering/state/repository.py:88`),
  `StateService` dir (`src/ai_engineering/state/service.py:34`), and
  `resolve_state_plane_artifact_path`
  (`src/ai_engineering/state/control_plane.py:349`). A wrong root transparently
  redirects specs, plan, decision-store, framework-events, and ownership-map;
  there is no per-artifact safeguard (`src/ai_engineering/state/work_plane.py:174`).
- The brain/work-plane split is **already encoded** by `brain_root()` —
  "`Path.home()` if scope==GLOBAL else target" — at
  `src/ai_engineering/installer/.../scope.py:152` and honored by every install
  phase (governance/scripts/hooks → brain; state-init → work-plane,
  `src/ai_engineering/cli_commands/core.py:795`). Runtime resolution simply
  fails to honor the same split.
- Hooks resolve root from cwd / `CLAUDE_PROJECT_DIR`
  (`.ai-engineering/scripts/hooks/runtime-session-start.py:82`,
  `memory-session-start.py:114`) and **lazily mkdir** `.ai-engineering/state`
  under that root before any CLI runs (`runtime-compact.py:87`); a second
  divergent walk-up lives in the formatter
  (`.ai-engineering/scripts/hooks/auto-format.py:103`). No hook writes a marker,
  so a hook can leave a **markerless** `.ai-engineering/state/` that later traps
  the resolver (Section 4, Section 11).
- The post-install summary prints the raw cwd/target root, not the resolved
  global home, so a `--global` run inside a repo misreports the location in both
  the human line (`src/ai_engineering/cli_commands/core.py:842`) and the JSON
  envelope `root` key (`src/ai_engineering/cli_commands/core.py:803`).
- `src/ai_engineering/doctor/runtime/scope_status.py:22` already detects
  local-vs-global scope (collapsing to global when repo == home) — the natural
  surface for one advisory.

Corroboration from the reported run: branch-policy apply failed with `not a git
repository` because the global install ran from `$HOME` (not a git repo),
confirming global scope decouples from the cwd repo as designed — while the
work-plane resolver still wrongly climbs to `$HOME`.

## 4. Architecture

One resolver, one structural chokepoint, one seeding routine.

**Discriminator (must-fix #1 — single rule, applied consistently).** A directory
is the **global brain** iff `dir.resolve() == Path.home().resolve()`. That is the
only test. The walk-up ceiling is **unconditional**: the walk stops at (and never
returns) `$HOME` and the filesystem root, regardless of any marker. The
contradictory "`specs/` OR `state/` present" heuristic is removed — it produced a
false positive on the brain itself (the template seeds inert empty
`specs/spec.md` + `plan.md` into the brain) and added failure modes. Work-plane
classification is **marker-only**: a non-`$HOME` `.ai-engineering` counts as a
local plane only when it carries a well-formed `state/install-state.json`;
anything else is "markerless" and handled by repair (below), never silently
adopted.

**Resolution algorithm** (`resolve_work_plane_root(intent: read | write)`):

1. Honor an explicit override env first (e.g. `AIENG_WORKPLANE_ROOT`, plus the
   IDE root already honored at
   `.ai-engineering/scripts/hooks/codex-hook-bridge.py:147`). The override is
   validated and may **not** equal `$HOME` (honors Locked Decision #1).
2. `brain_root = Path.home() / ".ai-engineering"` — brain-only, never a
   work-plane root.
3. Walk up `[cwd.resolve(), *cwd.resolve().parents]` — `resolve()` applied to the
   start AND every ancestor uniformly (symlink-safe) — testing each for a
   marker-bearing local plane, bounded by the unconditional `$HOME` / fs-root
   ceiling (adds the missing sentinel to `src/ai_engineering/paths.py:64`).
4. First marker-bearing hit before the ceiling → that is `project_root`; all
   `work_plane.py` / `control_plane.py` / `repository.py` artifacts resolve under
   it.
5. A markerless `.ai-engineering` encountered mid-walk → **fail loud** with a
   heal hint (`ai-eng init --here` to write the marker), never silent adoption.
6. No local plane found and `intent == write` → bootstrap anchor = git toplevel
   (`git rev-parse --show-toplevel`) when present, else cwd; **never `$HOME`**.
   Then bootstrap and proceed.
7. No local plane and `intent == read` → return `source = ephemeral` (no writes);
   readers return a clear "no local work-plane yet" result rather than reading
   the brain's specs/decisions.
8. **Brain-READ fallback** (the operator's primary requirement): brain assets
   (skills, agents, hooks, policies, overrides, reference) resolve from
   `brain_root` when absent locally, so skills/agents work in any directory.
   Work-plane WRITES only ever target the resolved local `project_root`.

**Structural "governed" (must-fix #2).** There is no enumerated command list.
Every work-plane mutation routes through the write APIs in `work_plane.py` /
`control_plane.py` / `repository.py`, and **those APIs** call
`resolve_work_plane_root(write)` by construction. A new mutator cannot bypass the
chokepoint without bypassing the only write path, so the bleed-through cannot
resurrect by someone forgetting a flag.

**Resolver unification (must-fix #3, §10.4 DRY).** The unconditional `$HOME`
ceiling makes walk-up safe — which is the exact hazard the three private cwd-only
resolvers were created to dodge (`risk_cmd.py:74`, `audit_cmd.py:51`). So
`find_project_root`, `resolve_project_root`, and the three private variants are
**hard-deleted** (Section 10) and replaced by the one resolver. `commit` and
`release`, which mutate work-plane state (`decision-store.json`,
`framework-events.ndjson`), route through write-intent resolution — fixing the
cwd-anchored subdir-fragmentation they have today
(`src/ai_engineering/cli_commands/commit.py:21`,
`src/ai_engineering/cli_commands/release.py:34`). Pure install/config that
legitimately needs an explicit target keeps a target parameter, but resolution
is one function.

**Bootstrap.** Creates a minimal local plane at the anchor:
`.ai-engineering/specs/` (stub `spec.md` / `plan.md`), `.ai-engineering/state/`
(`decision-store.json`, genesis `framework-events.ndjson`, `ownership-map.json`,
`install-state.json` marker with `bootstrapped: true`). It REFUSES when the
anchor is `$HOME`. Seeding reuses the **single** installer State-initialization
routine under a file lock (`.ai-engineering/state/locks/`) so the audit
hash-chain is byte-identical and race-safe (`ai-eng audit verify` passes).
Idempotent: per-artifact check-then-create; **heals** a markerless plane by
writing only the missing marker/files. The "initialized local work-plane at
<root>" notice goes to **stderr** (so `--json` stdout stays clean). CI:
non-interactive; `AIENG_NO_BOOTSTRAP=1` disables it (governed writes then fail
loud instead of creating a plane).

**Hooks (must-fix interaction).** Hooks resolve root from cwd /
`CLAUDE_PROJECT_DIR` (`hook_context`), never `$HOME`; they NEVER bootstrap on the
hot path and NEVER write a markerless plane. The hook lazy-mkdir
(`.ai-engineering/scripts/hooks/runtime-compact.py:87`) is gated: if the resolved
root is `$HOME`, hooks pass through writing nothing; otherwise they write only
runtime/ under an already-resolved local root, and the CLI bootstrap later adopts
that same directory idempotently. The formatter's private walk-up
(`.ai-engineering/scripts/hooks/auto-format.py:103`) adopts the same ceiling.
This preserves the `<1s` session-start / pre-commit budget.

## 5. Evidence Catalog

| Claim | Evidence |
|-------|----------|
| Walk-up resolver, no ceiling | `src/ai_engineering/paths.py:57`, `paths.py:64` |
| Cwd/target-only resolver | `src/ai_engineering/paths.py:12` |
| Private cwd-only resolver (test-isolation reason) | `cli_commands/risk_cmd.py:74`, `audit_cmd.py:51` |
| Work-plane cmds use walk-up | `cli_commands/spec_cmd.py:153`, `plan_cmd.py:219` |
| Governance cmds use walk-up | `cli_commands/decisions_cmd.py:39`, `ownership_cmd.py:133` |
| commit/release cwd-anchored (fragmentation) | `cli_commands/commit.py:21`, `release.py:34` |
| Work-plane derives from root | `state/work_plane.py:168`, `work_plane.py:174` |
| State repo paths derive from root | `state/repository.py:88`, `service.py:34` |
| State-plane artifact resolver | `state/control_plane.py:349` |
| Brain/work-plane split already encoded | `installer/.../scope.py:152`, `core.py:795` |
| Hooks resolve from cwd; lazy mkdir state | `scripts/hooks/runtime-session-start.py:82`, `runtime-compact.py:87` |
| Divergent formatter walk-up | `scripts/hooks/auto-format.py:103` |
| Codex bridge env-first root | `scripts/hooks/codex-hook-bridge.py:147` |
| Install scope flags / global=home | `cli_commands/core.py:568`, `core.py:265` |
| Misleading human summary line | `cli_commands/core.py:842` |
| Misleading JSON envelope root | `cli_commands/core.py:803` |
| Scope detector surface for advisory | `doctor/runtime/scope_status.py:22` |
| Resolver-mock tests to sweep | `tests/unit/test_cli_decisions.py:50` |

## 6. Roadmap

- **M1 — Unified resolver + ceiling.** Introduce `resolve_work_plane_root` with
  the unconditional `$HOME`/realpath ceiling and marker-only classification;
  hard-delete all five legacy resolvers; route commit/release/risk/audit through
  it. Gate: walk-up from an uninitialized repo under `$HOME` never returns
  `$HOME`; symlinked-home, nested, monorepo, submodule, worktree tests pass; the
  three deleted private resolvers' isolation tests pass via the new override env.
- **M2 — Structural write chokepoint + lazy bootstrap.** Work-plane write APIs
  call the resolver; bootstrap a minimal plane via the shared installer routine
  under a lock; refuse at `$HOME`; announce on stderr. Gate: a governed write in
  a fresh repo creates a local plane at the git root; `ai-eng audit verify`
  passes on the seeded chain; idempotent + markerless-heal re-run is safe.
- **M3 — Brain-READ fallback.** Brain assets read from global when absent
  locally. Gate: skills/agents resolve in an uninitialized repo with zero
  work-plane writes.
- **M4 — Hooks alignment.** `hook_context` + `auto-format` adopt the ceiling;
  hooks no-op-until-init; `$HOME` guard added; never write a markerless plane.
  Gate: session start in an uninitialized repo writes nothing under `$HOME`; hot
  path SLO honored.
- **M5 — Installer message + advisory.** Correct the human line and JSON
  envelope under global scope; one `scope_status` advisory when a repo runs
  brain-only; legacy-data advisory on first governed write. Gate: a `--global`
  run inside a repo reports the home brain target in both human and JSON output.

## 7. Definition of Done

- From any uninitialized directory under `$HOME` (not `$HOME` itself), a
  work-plane read never resolves to `$HOME`; a work-plane write bootstraps a
  local plane at the git/cwd root.
- Two unrelated uninitialized projects under `$HOME` get independent local
  planes; no shared specs/state/audit chain.
- Skills and agents are usable in an uninitialized repo with zero work-plane
  writes (brain-READ fallback).
- A new work-plane mutator cannot bleed to `$HOME` without bypassing the only
  write API (structural guarantee, not an allowlist).
- commit/release/risk/audit resolve the same repo-root plane from any subdir
  (no fragmentation), bounded by the ceiling (no global bleed).
- Markerless or malformed planes fail loud with a heal hint; bootstrap heals on
  adopt; `.ai-engineering`-as-a-file fails loud (not an opaque mkdir error).
- `ai-eng audit verify` passes on a bootstrapped plane (single lock-protected
  genesis routine).
- `--global` install human line AND JSON `root` report the home brain target,
  with `scope` + `brain_root` keys added; the bootstrap notice is on stderr.
- All five legacy resolvers are gone (hard delete); resolver-mock tests updated;
  CHANGELOG documents the behavior change.

## 8. Quality Stamps

- **§10.1 KISS** — one resolver, one structural chokepoint, one seeding routine;
  the enumerated "governed command" notion is eliminated.
- **§10.2 YAGNI** — no global work-plane namespacing; global is brain-only.
- **§10.4 DRY** — five resolvers and the divergent formatter walk-up collapse
  into the shared resolver; bootstrap reuses the installer seeding.
- **§10.5 TDD** — resolver-mock and chdir-isolation tests are a named M1 task,
  not a footnote; ceiling/symlink/submodule/worktree cases are RED-first.
- **§10.8 Hexagonal** — root resolution is the single port; state/work-plane
  adapters consume the resolved `project_root` unchanged.
- Contracts honored: CONSTITUTION.md §3 (hard rename + hard delete, no shims);
  Hard Rule 7 (one canonical writable store per datum — the work-plane has
  exactly one local store); hot-path SLOs (`<1s` pre-commit, `<5s` pre-push).

## 9. Open Decisions

1. Minimal bootstrap fileset: seed stub `spec.md` + `plan.md` (so
   `ensure_work_plane_artifacts`, `state/work_plane.py:77`, is satisfied) vs
   create only empty `specs/` + `state/` and let the first `/ai-brainstorm`
   write `spec.md`.
2. Bootstrap anchor for submodules and linked git worktrees: a submodule's
   `.git` file would otherwise bootstrap inside the submodule (committed to the
   wrong repo) and two worktrees would get two planes. Pick the anchor rule
   (superproject root? per-worktree? explicit refusal + hint?).
3. Override env name and precedence (`AIENG_WORKPLANE_ROOT`?): does it override a
   discovered local marker; behavior when it points at a nonexistent/unwritable
   path (bootstrap-at-override vs fail loud).
4. `AIENG_NO_BOOTSTRAP` exact fail-loud UX and message wording for the
   "ephemeral / governed-at-`$HOME`" path.
5. `HOME`-unset / non-POSIX fallback for the ceiling (CI/containers where `HOME`
   may be `/root` or absent; Windows cross-drive where the `$HOME` sentinel is
   never on the ancestor chain).
6. Whether `scope_status` emits a doctor advisory when a repo runs brain-only.
7. Relocation tool for legacy global work-plane state: name/scope (the advisory
   is in scope; the mover is deferred).

## 10. Migration

Hard behavior change, no shims (CONSTITUTION.md §3). `find_project_root`,
`resolve_project_root`, and the three private `_resolve_project_root` variants
are hard-deleted into `resolve_work_plane_root`; callers and resolver-mock tests
(e.g. `tests/unit/test_cli_decisions.py:50`) are updated in the same change. The
two non-work-plane callers of the old walk-up are audited first to confirm none
rely on the no-ceiling behavior.

Legacy global-only users (decided, not open): work-plane data that wrongly
accumulated under `$HOME/.ai-engineering/state` and `specs/` is **orphaned in
place** — never read as a work-plane, never deleted. On the first post-upgrade
governed write in a real repo, a fresh local plane is bootstrapped; if legacy
data is detected in the brain, a one-time advisory points to the (deferred)
relocation command. A read in an un-bootstrapped repo also surfaces the advisory,
so a suddenly-empty `spec list` is never mistaken for data loss. CHANGELOG
documents the breakage and the new global = brain-only model.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ceiling still climbs to `$HOME` on symlinked/cross-OS homes | Medium | High | `resolve()` on start AND every ancestor; compare vs `Path.home().resolve()`; explicit symlink/nested/monorepo/cross-drive tests; `HOME`-unset fallback (Section 9.5) |
| Markerless-plane trap: a hook created `state/` before first CLI write | High | High | marker-only classification + fail-loud-with-heal (Section 4.5); bootstrap heals on adopt; hook `$HOME` guard |
| Auto-bootstrap writes `.ai-engineering` into a repo the user only meant to read | Medium | Medium | write-intent only (reads never bootstrap); anchor at git root; refuse at `$HOME`; stderr notice; `AIENG_NO_BOOTSTRAP=1` |
| Submodule / worktree anchor creates wrong/duplicate planes | Medium | High | explicit anchor rule (Section 9.2) with tests before M2 ships |
| Resolver-mock + chdir tests break on the rename | High | Medium | named M1 task; override env gives deterministic anchors; `$HOME` ceiling actually improves `/private/var` isolation |
| Hot-path hooks blow the `<1s` budget after adding the `$HOME` guard | Low | Medium | guard is one `resolve()`+compare; no walk-up on the hook path; cache resolved root per process |
| Genesis `framework-events.ndjson` seeded inconsistently vs installer | Medium | High | single shared seeding routine + lock; `ai-eng audit verify` in the bootstrap test |
| Concurrent CLI/hook bootstrap race on one anchor | Medium | High | bootstrap under `state/locks/`; atomic check-then-create; hooks never write the marker |
| `.ai-engineering` exists as a FILE, or read-only FS (EROFS) | Low | Medium | detect and fail loud with an actionable message, not a raw `mkdir` traceback |
| JSON envelope reshape (`root` value change + new keys) breaks consumers | Low | Medium | additive `scope`/`brain_root` keys; the corrected `root` for `--global` was a bug; document in CHANGELOG |

## 12. References

- git config + repository discovery (global vs local,
  `GIT_CEILING_DIRECTORIES`, `GIT_DISCOVERY_ACROSS_FILESYSTEM`, worktree/`.git`
  file semantics): git-scm.com/docs/git-config, git-scm.com/docs/git-worktree,
  git-scm.com/docs/githooks.
- Layered config precedence + nearest-config discovery: Ruff
  (docs.astral.sh/ruff/configuration), ESLint flat config
  (eslint.org/docs/latest/use/configure/configuration-files).
- Global tooling vs per-project state: npm folders
  (docs.npmjs.com/cli/configuring-npm/folders), Cargo workspaces
  (doc.rust-lang.org/cargo), uv tools (docs.astral.sh/uv).
- Lazy/explicit local-state init: direnv (direnv.net), pre-commit
  (pre-commit.com), `git init` (git-scm.com/docs/git-init), `terraform init`
  (developer.hashicorp.com/terraform/cli/commands/init).

## 13. Glossary

- **Brain** — machine-wide, content-identical, template-regenerated assets:
  skills, agents, hook scripts, overrides, reference, policies, security,
  runbooks, manifest framework-defaults. Hosted once at `$HOME` under global
  scope (`scope.py:152`).
- **Work-plane** — per-repo active spec contract: `specs/spec.md`,
  `specs/plan.md`, `_history.md` (`state/work_plane.py:168`).
- **Control / state plane** — per-repo governance state: `decision-store.json`,
  `framework-events.ndjson`, `state/specs/`, `ownership-map.json`, runtime,
  observations, constitution context.
- **Marker** — `state/install-state.json`; its presence (well-formed) is the
  ONLY signal that a `.ai-engineering` directory is a real local work-plane.
- **Markerless plane** — a `.ai-engineering` (often a hook-created `state/`) with
  no valid marker; fails loud, heals on bootstrap, never silently adopted.
- **Write-intent chokepoint** — the single resolver call inside the work-plane
  write APIs whose UNINITIALIZED result triggers bootstrap; replaces any
  enumerated command list.
- **Brain-READ fallback** — resolving brain assets from the global plane when
  absent locally, so skills/agents work without a local plane.
- **Bootstrap anchor** — where a new local plane is created (git toplevel, else
  cwd; never `$HOME`).

## 14. Acceptance

- [ ] Walk-up never returns `$HOME` as a work-plane root (unconditional ceiling;
      symlink/nested/monorepo/submodule/worktree/cross-drive tests pass).
- [ ] Write-intent in a fresh repo bootstraps a local plane at the git/cwd root;
      refuses at `$HOME`.
- [ ] Two uninitialized projects under `$HOME` get independent planes.
- [ ] Skills/agents usable in an uninitialized repo with zero work-plane writes.
- [ ] A new mutator cannot bleed to `$HOME` without bypassing the write API.
- [ ] commit/release/risk/audit resolve the same repo-root plane from any subdir.
- [ ] Markerless/malformed/file/EROFS cases fail loud with actionable messages;
      bootstrap heals markerless on adopt.
- [ ] Bootstrapped plane passes `ai-eng audit verify`; bootstrap notice on
      stderr; concurrent bootstrap is lock-safe.
- [ ] `--global` install human line AND JSON `root` report the home brain target
      (+ `scope`, `brain_root` keys).
- [ ] All five legacy resolvers hard-deleted; tests updated; CHANGELOG entry.
