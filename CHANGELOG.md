# Changelog

## 3.2.4

### Patch Changes

- [#812](https://github.com/arcasilesgroup/ai-engineering/pull/812) [`2bd6853`](https://github.com/arcasilesgroup/ai-engineering/commit/2bd68532f5d7aebabc73d33486529bd251df2369) Thanks [@soydachi](https://github.com/soydachi)! - One design system for every HTML artifact, with the gates that keep it honest.
  
  `brand/components.css` and `brand/components.js` now carry the component layer —
  diagrams, tabs, copy blocks, filters, steps, checklists, callouts, category chips,
  verdict and terminal cards — beside `brand/tokens.json`. `bun scripts/brand.ts gen`
  inlines them between markers into all eight templates and into `brand/gallery.html`,
  the gallery that shows every part live with the markup that makes it, and `parity`
  fails on a hand edit. Every colour pair a component uses is declared in
  `tokens.json` and measured by `brand.ts contrast`; prose is left-aligned, and code
  wells moved onto `--surface` where a comment clears 4.5:1.
  
  Two gates protect the result. `tests/artifact-a11y.spec.ts` runs a static
  accessibility gate inside `bun test` — language, one rendered `h1`, heading order,
  table captions and header scope, SVG names, resolvable and unique ids, no external
  request, no inline handler, zoom, and the forced-colours, reduced-motion and print
  layers — with one failing fixture per rule. `bun run a11y` opens all nine pages in
  the system Chrome at 320, 390, 768 and 1440px and under forced colours, runs
  axe-core's WCAG 2.0, 2.1 and 2.2 A and AA rules, walks every tab set with the
  keyboard, and proves 320px reflow and the no-script reading. It runs as its own CI
  job so the unit suite still passes without Chrome.
  
  The templates also ship ready slots — a diagram with a text version, decisions with
  expand all, a stats row and options in tabs — and the page templates now install
  beside the skills.

- [#817](https://github.com/arcasilesgroup/ai-engineering/pull/817) [`30c2f93`](https://github.com/arcasilesgroup/ai-engineering/commit/30c2f93d7c0786e91d0313b95b3a9f2ceaa286f8) Thanks [@soydachi](https://github.com/soydachi)! - The Version Packages PR now carries the CI template pin: `bun run version-packages`
  runs `changeset version` and then `scripts/sync-ci-template-pins.ts`, which rewrites
  `AI_ENG_VERSION` in `templates/ci.yml.tpl` and `templates/azure-pipelines.yml.tpl`
  from `package.json`. A bump can no longer leave the templates pinning the previous
  release, and a template that loses its pin fails the release loudly instead of
  shipping without one.

## 3.2.3

### Patch Changes

- [#809](https://github.com/arcasilesgroup/ai-engineering/pull/809) [`263249e`](https://github.com/arcasilesgroup/ai-engineering/commit/263249ec67b4fcbfb8d4bfe40e7c2c4c7c98de98) Thanks [@soydachi](https://github.com/soydachi)! - `/ai-orchestrator` now resumes one builder for tests, implementation, and verify, then one reviewer reads the diff. A blocker gets one fix. A second failure stops. A passed checkpoint is one commit and the end of the turn.

- [#811](https://github.com/arcasilesgroup/ai-engineering/pull/811) [`4031008`](https://github.com/arcasilesgroup/ai-engineering/commit/4031008756f007d4ecf39c8f4335ddef08f2201a) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng work tidy` and `/ai-pr` now say to run tidy from another checkout while the feature folder is still on its branch, so closing a landed lane removes the folder as well as the branch.

## 3.2.2

### Patch Changes

- [#806](https://github.com/arcasilesgroup/ai-engineering/pull/806) [`3ad5cf4`](https://github.com/arcasilesgroup/ai-engineering/commit/3ad5cf43ef33967672cd366830fe0fda42f88bc6) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng config` no longer ends its summary with "model tiers: .ai-engineering/config.toml": the config template has carried no model tiers for a while, so the line sent you to look for a table that is not there.

## 3.2.1

### Patch Changes

- [#803](https://github.com/arcasilesgroup/ai-engineering/pull/803) [`faac0cb`](https://github.com/arcasilesgroup/ai-engineering/commit/faac0cb65a5e5a8dce7068368f24ad8ea2ddf9b8) Thanks [@soydachi](https://github.com/soydachi)! - Every check that a file is still the one ai-eng read before writing or removing it — project files, machine settings, the machine record and its lock, skill links in the canon — now reads file ids as exact bigints and compares times in nanoseconds. On Windows an NTFS file id passes 2^53, where a JavaScript number drops its low bits, so a file swapped in a moment later could have passed for the one that was judged.

- [#800](https://github.com/arcasilesgroup/ai-engineering/pull/800) [`ecec5f1`](https://github.com/arcasilesgroup/ai-engineering/commit/ecec5f1fe19e5fa576bbcdb2c986ac224b9dc8f4) Thanks [@soydachi](https://github.com/soydachi)! - The command-scope policy no longer blocks `git add` of a file whose name contains "token", "secret" or "credential" (a design-token `tokens.json`, a `secrets-handling.md` page). `git add` copies files into the repository's index; it does not write the files it names, so those paths are now judged as reads, the way `git commit` already judged its message. A real write to such a path is still refused, and a secret staged by mistake is still stopped by the gitleaks commit floor.

- [#801](https://github.com/arcasilesgroup/ai-engineering/pull/801) [`c835dfe`](https://github.com/arcasilesgroup/ai-engineering/commit/c835dfed446cd8eb97dfcf3f1a8b7de3bcc51c16) Thanks [@soydachi](https://github.com/soydachi)! - The self-protect guard no longer carries a rule for `ai-eng adapt apply`: the `adapt` verb was removed in 3.2.0, so the rule guarded a command that no longer exists. `uninstall`, `wrap` and `config --remove` stay refused from inside a governed session.

- [#799](https://github.com/arcasilesgroup/ai-engineering/pull/799) [`06acd8a`](https://github.com/arcasilesgroup/ai-engineering/commit/06acd8a79d990a8be52db8e6c0c201ae2d89ef47) Thanks [@soydachi](https://github.com/soydachi)! - The gitleaks install hint the commit floor prints now leads with what works without administrator rights. On Windows it suggested `choco install`, which needs an administrator; it now suggests `winget install --id Gitleaks.Gitleaks -e`, or putting `gitleaks.exe` from the releases page in a folder on your user PATH. On Linux it suggested `apt install`, which needs sudo; it now suggests the release binary in `~/.local/bin` first. The README gains a short section on installing Bun, ai-eng and gitleaks on a managed PC with no administrator rights.

- [#798](https://github.com/arcasilesgroup/ai-engineering/pull/798) [`24f5084`](https://github.com/arcasilesgroup/ai-engineering/commit/24f50845cb02c31caaf1b4a20fce04909d3de854) Thanks [@soydachi](https://github.com/soydachi)! - On Windows, `ai-eng uninstall` (and the carrier install) sometimes refused to touch `~/.copilot/hooks/ai-eng.json`, saying it "changed while ai-eng was removing its entries, or it is a hard link with a second name". The check that the settings file is not the machine record under a second name compared file ids as JavaScript numbers; an NTFS file id is 64 bits, and past 2^53 two files created a moment apart rounded to the same id. The ids are now compared as exact bigints, so only a real hard link is refused. The checkpoint guard, which finds the checkpoint file a write really lands on by the same id, compares them the same way.

## 3.2.0

### Minor Changes

- [#787](https://github.com/arcasilesgroup/ai-engineering/pull/787) [`556c24e`](https://github.com/arcasilesgroup/ai-engineering/commit/556c24e8d90ddb2307f43c9cb681c86c73f886b4) Thanks [@soydachi](https://github.com/soydachi)! - `/ai-agents-md` and `/ai-config-to-project` are now one skill, `/ai-refresh-project`, run by name. It brings a governed repository back in line with its tree in five steps: `AGENTS.md` and the PRD, the `docs/` folder, stale artifacts (`ai-eng doctor --gc`), orphan branches and worktrees (`ai-eng work`), and the governance files (layer rules, config, overrides), which it proposes on a page for you to apply. The `ai-eng adapt` verb is gone: `ai-eng adapt apply` always refused, because a hash an agent writes cannot prove a person approved the change.

- [#791](https://github.com/arcasilesgroup/ai-engineering/pull/791) [`3e3f358`](https://github.com/arcasilesgroup/ai-engineering/commit/3e3f358b8fd10502e94ccbb8346cb30d0a3e7375) Thanks [@soydachi](https://github.com/soydachi)! - Landed lanes now close on their own. When a session opens, every branch whose landing is proven (its PR merged, `ai-eng worktree merge` recorded it, or a merge brought it into the base) is removed without asking: its tip is kept first in `refs/archive/<branch>`, its folder goes only when it holds no uncommitted work, and a folder another session is writing in, or the branch checked out where the session opens, is left alone. The session is told in one line, with the command that brings a branch back. `ai-eng work tidy` keeps each tip in `refs/archive/` the same way, and fast-forwards the base checked out here when it is clean and behind its upstream.

- [#789](https://github.com/arcasilesgroup/ai-engineering/pull/789) [`74abaa8`](https://github.com/arcasilesgroup/ai-engineering/commit/74abaa8ec8a19cc012b1be7c797833899510ca10) Thanks [@soydachi](https://github.com/soydachi)! - The twelve verification skills `ai-verify` routes to (verify-feature, spec-extract, feature-verify, second-opinion, review-router, code-audit, security-audit, a11y-audit, perf-audit, design-check, build-check and full-review) now live inside `ai-verify` as files in `skills/ai-verify/lanes/`, with their scripts in `skills/ai-verify/scripts/`. None of them changed; they no longer appear as twelve separate skills in your agent's list, and `ai-eng update` removes the old folders. The lanes now read their shared conventions from `ai-verify/references/review/CONVENTIONS.md`, which ships with the skill, instead of a `.claude/review/CONVENTIONS.md` that no project had.

### Patch Changes

- [#792](https://github.com/arcasilesgroup/ai-engineering/pull/792) [`6aba93a`](https://github.com/arcasilesgroup/ai-engineering/commit/6aba93add26e0d4fa1e306edfed617aeb3185863) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng work` now asks Azure DevOps for merged pull requests when the repository's `origin` is an Azure DevOps remote (`dev.azure.com`, `ssh.dev.azure.com` or `*.visualstudio.com`), through `az repos pr list`. A completed PR whose last source commit is the branch tip counts as landed, the same way a merged GitHub PR does through `gh`. Without `az`, or signed out, the board says so and still proves landings from git alone.

- [#793](https://github.com/arcasilesgroup/ai-engineering/pull/793) [`84f3a37`](https://github.com/arcasilesgroup/ai-engineering/commit/84f3a373a80e6a47aa288a62746b04faa83e0271) Thanks [@soydachi](https://github.com/soydachi)! - The `config.toml` that `ai-eng init` writes now tells the truth about itself: the surface list names `copilot-cli` (the id `ai-eng config` accepts), the `[gc]` comment names the folders `doctor --gc` really collects and documents `older_than` and `keep_runs`, and the new-version opt-out reads `[notices] enabled = false`, the key ai-eng reads. The old `notices = false` line, uncommented, landed inside `[gc]` and turned nothing off.

- [#790](https://github.com/arcasilesgroup/ai-engineering/pull/790) [`65b7d61`](https://github.com/arcasilesgroup/ai-engineering/commit/65b7d612a4974537cb5281ab9ade6f618f5e2173) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng doctor --gc` now also clears what piled up unseen: verdict-cache files in `.ai-engineering/cache/verdicts/` untouched for a week, receipt-retention markers from earlier days, and the files under `.ai-engineering/workflow/` (checkpoints, feature pages, test plans) that git already holds and that are older than `[gc] older_than`. As in the other folders, a file cited by DECISIONS.md, NOTICE or the layer rules stays, and a file git does not hold is never deleted.

- [#788](https://github.com/arcasilesgroup/ai-engineering/pull/788) [`5c1e250`](https://github.com/arcasilesgroup/ai-engineering/commit/5c1e2501ecfbbded38325b8d996d4db8e07f1e15) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng work` and `ai-eng work tidy` now see a branch as landed without asking the forge when git can prove it: the branch was merged into the base by a merge commit, its whole change was squash-merged into the base, or `ai-eng worktree merge` recorded merging it. Both commands also run `git fetch --prune` first (best effort, ten seconds at most), so a branch the forge deleted on merge reads as gone. A branch created on the base with nothing of its own still does not count as landed.

- [#786](https://github.com/arcasilesgroup/ai-engineering/pull/786) [`ecd0c3f`](https://github.com/arcasilesgroup/ai-engineering/commit/ecd0c3f0ea9f008380df868897d3de9a9cbefd18) Thanks [@soydachi](https://github.com/soydachi)! - The one-folder-one-writer lease now judges a write in the folder it lands in. When another session held the main checkout, the lease sent you to a worktree and then blocked your `git -C <worktree> commit` or `cd <worktree> && git add` there, because it only looked at where the session started. A git command aimed at a worktree now takes that worktree's lease; one aimed back at the held checkout is still stopped, and a `cd` the shell may not have run first (after `||`, in a subshell or pipeline, or into a folder that does not exist) is not believed. A worktree nested inside the checkout counts as its own folder too.

- [#784](https://github.com/arcasilesgroup/ai-engineering/pull/784) [`edee406`](https://github.com/arcasilesgroup/ai-engineering/commit/edee406dec5fa857f5e8412082867dceabf0342c) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng update` works inside a linked git worktree. It failed there with `ENOTDIR` while writing `.git/hooks`, because in a worktree `.git` is a file and the hooks live in the repository's shared git folder. Update now leaves those shared hooks to the main checkout and keeps them in the lock, so a lock committed from a worktree matches one from the main checkout. `ai-eng doctor` reads the hooks from where git actually runs them.

## 3.1.0

### Minor Changes

- [#780](https://github.com/arcasilesgroup/ai-engineering/pull/780) [`ee5d69b`](https://github.com/arcasilesgroup/ai-engineering/commit/ee5d69bbf909b853d3c89d2fdaec31a3236c3b70) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng init` now asks where the project's CI runs: GitHub Actions, Azure Pipelines, or none. The origin remote preselects the answer, and `--ci github-actions|azure-pipelines|none` skips the question. Azure Pipelines projects receive `.azure-pipelines/ai-eng-check.yml`, which verifies the governor's provenance without a GitHub token, and init names the two portal steps (create the pipeline, add the Build validation branch policy). The choice is stored as `[ci].provider` in `.ai-engineering/config.toml`. `ai-eng config` now changes it too: run it with no flags and pick "CI provider", or pass `--ci <provider>`; it rewrites only that key, writes the new gate and removes the old one. Repositories governed before this release have no `[ci]` block and keep their GitHub workflow.

- [#780](https://github.com/arcasilesgroup/ai-engineering/pull/780) [`ee5d69b`](https://github.com/arcasilesgroup/ai-engineering/commit/ee5d69bbf909b853d3c89d2fdaec31a3236c3b70) Thanks [@soydachi](https://github.com/soydachi)! - New `ai-eng work`: one board for every lane in the repo — each branch with its folder and PR, every stash, and every worktree whose folder is gone — computed from git and the forge each time, never stored. A lane leaves by one of three doors: `ai-eng work tidy` removes what provably landed (the forge merged that exact tip, or the base holds it and its remote branch is gone), `ai-eng work park <branch> "<reason>" [--until YYYY-MM-DD]` records why it waits, and `ai-eng work drop <branch>` keeps the tip in `refs/archive/` before the branch goes. A session start in Claude Code or Codex now adds one line about the lanes that need a decision.
  
  `ai-eng worktree new` refuses a fourth active lane (`[work] max_active`, default 3), a new `no-stash` guard denies creating a stash (reading and restoring one still work), `/ai-pr` closes the lane once the PR is merged, and `AGENTS.md`'s "Where to work" is now seven numbered rules. The `ai-git-cleanup` skill is removed: its merged-branch test missed squash and rebase merges, and `ai-eng work tidy` replaces it.

- [#780](https://github.com/arcasilesgroup/ai-engineering/pull/780) [`ee5d69b`](https://github.com/arcasilesgroup/ai-engineering/commit/ee5d69bbf909b853d3c89d2fdaec31a3236c3b70) Thanks [@soydachi](https://github.com/soydachi)! - New `lease` guard: one folder, one writer. The first session that writes in a folder (a file edit, or a git command that writes the index, a ref or the tree) holds it; another session's write there is denied and sent to a worktree. The hold lives in the folder's git directory, lapses after 15 minutes without a write (`[work] lease_minutes`), ends at once with Claude Code's `SessionEnd`, and `ai-eng work release` frees it by hand. Reading, testing and building are never held, and a host that sends no session id is never judged.

- [#780](https://github.com/arcasilesgroup/ai-engineering/pull/780) [`ee5d69b`](https://github.com/arcasilesgroup/ai-engineering/commit/ee5d69bbf909b853d3c89d2fdaec31a3236c3b70) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng update` now brings you up to date in one command. It reads the registry once (3 s); when a newer ai-eng exists it shows the version and the release notes, asks, installs it with the package manager that installed ai-eng (`bun add -g` or `npm install -g`), checks that the `ai-eng` on PATH is the new one, and runs it to sync the machine and the repo. With no terminal and no `--yes` it installs nothing and prints the command. Offline, it syncs exactly as before. Outside a repo it updates the machine side only.
  
  Every human command now ends with up to two lines: a newer ai-eng on the registry, and a repo installed by an older ai-eng than the one running. The registry is read at most once a day, and a failed read is remembered too, so a bad network costs one 3 s wait a day instead of up to 30 s on every command. Claude Code and Codex get the same two lines at session start through a new `SessionStart` hook, read from the cache with no network. `AI_ENG_NO_UPDATE_NOTICES=1` or `[notices] enabled = false` still turns all of it off.

### Patch Changes

- [#782](https://github.com/arcasilesgroup/ai-engineering/pull/782) [`2b6f946`](https://github.com/arcasilesgroup/ai-engineering/commit/2b6f946dcb283e76f4807cfbf4ea8005efeb8b13) Thanks [@soydachi](https://github.com/soydachi)! - An agent can now finish an `ai-eng update` on its own: the self-protect guard lets it `git add` and `git commit` the files ai-eng wrote (the lock, the carriers), while every command that changes their bytes — an edit, a redirect, `git checkout` or `git restore` over them — stays denied. Before, naming the lock in `git add` was refused even though `git add -A` staged it anyway, so updating every project agentically needed a person for each commit.
  
  The one-writer lease now holds only writes into the leased folder: a second session writing a temp file or a file in another checkout is no longer stopped. Failed or killed mutation runs no longer leave `.stryker-tmp` behind, and the CLI proof hands hooks a native path on Windows.

- [#780](https://github.com/arcasilesgroup/ai-engineering/pull/780) [`ee5d69b`](https://github.com/arcasilesgroup/ai-engineering/commit/ee5d69bbf909b853d3c89d2fdaec31a3236c3b70) Thanks [@soydachi](https://github.com/soydachi)! - The generated CI workflow no longer fails while installing ai-eng: it verified the release's provenance against the tag, but releases are built from main, so the check never passed.

- [#780](https://github.com/arcasilesgroup/ai-engineering/pull/780) [`ee5d69b`](https://github.com/arcasilesgroup/ai-engineering/commit/ee5d69bbf909b853d3c89d2fdaec31a3236c3b70) Thanks [@soydachi](https://github.com/soydachi)! - The CLI now speaks one visual language. Every file row names what happened to it in a fixed column (`installed`, `updated`, `removed`, `unchanged`), while the mark and the colour keep saying how it went. `init`, `doctor`, `config`, `update` and `uninstall` open with the same `verb · folder · ai-eng version` title and close on one next command. `doctor`, `work` and the registry check in `update` show what they are doing while they work. The new-version notice no longer waits on the network at the end of a command: it reads the cache and refreshes it in the background, in blue when a newer ai-eng exists and in yellow when this repo is behind its binary. `--help` gives every verb one line, and `work` colours each lane by the decision it needs.

- [#782](https://github.com/arcasilesgroup/ai-engineering/pull/782) [`2b6f946`](https://github.com/arcasilesgroup/ai-engineering/commit/2b6f946dcb283e76f4807cfbf4ea8005efeb8b13) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng init` no longer asks before installing the global skill canon or adding ai-eng's guard hook to the settings your tools read from your home folder (Claude Code, Pi, Codex, Copilot, OpenCode). A "no" to either left a repo that called itself governed with no guards running, and `update` and `config` already wrote the same files without asking. Your own settings in those files are kept, and running `init` again never adds the hook twice. `init` still asks before creating a git repository and before overwriting an AGENTS.md that is already there.

- [#782](https://github.com/arcasilesgroup/ai-engineering/pull/782) [`2b6f946`](https://github.com/arcasilesgroup/ai-engineering/commit/2b6f946dcb283e76f4807cfbf4ea8005efeb8b13) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng init` no longer writes an empty `.ai-engineering/arch.rules.json` that nothing outside ai-engineering read. Layer rules now belong to your language's own tool (dependency-cruiser, import-linter, or depguard in golangci-lint), and `/ai-config-to-project` proposes them from your code's real imports and your stack's guidelines for you to review and apply. `ai-eng doctor` recognises those tools, no longer warns about a repo with no code yet, and points a repo with code and no rules at the skill. `ai-eng update` removes the old empty file and keeps one you edited.

- [#782](https://github.com/arcasilesgroup/ai-engineering/pull/782) [`2b6f946`](https://github.com/arcasilesgroup/ai-engineering/commit/2b6f946dcb283e76f4807cfbf4ea8005efeb8b13) Thanks [@soydachi](https://github.com/soydachi)! - The binary now carries its skills, agents and templates as plain folders (`bun build --compile --asset`) and reads them by path, so the repository no longer commits a generated asset registry, text copies of skill scripts or the compiled chain bundle. The chain bundle the Oh My Pi, Pi and OpenCode plugins import is built fresh by every build, test run and npm pack. What gets installed is unchanged.

- [#780](https://github.com/arcasilesgroup/ai-engineering/pull/780) [`ee5d69b`](https://github.com/arcasilesgroup/ai-engineering/commit/ee5d69bbf909b853d3c89d2fdaec31a3236c3b70) Thanks [@soydachi](https://github.com/soydachi)! - The pre-push hook now scans for secrets only in the commits the push sends. It used to scan every ref in the clone, so a leak parked on a local `refs/archive/*` ref or in the stash blocked a push that never sent it. A ref the remote already has is measured from its old tip; a new ref is measured from the remote's base branch (`[git] base`, or the remote default), and when that branch is not in the clone the push is refused with the fetch to run. Deletions send nothing and several refs are one scan. The hook also stops naming a `.gitleaksrc.toml` the project does not have, which made gitleaks exit before scanning and was reported as a secret.

## 3.0.8

### Patch Changes

- [#778](https://github.com/arcasilesgroup/ai-engineering/pull/778) [`2666ea5`](https://github.com/arcasilesgroup/ai-engineering/commit/2666ea5929c9e3d840e7f84da4decf98021f5fea) Thanks [@soydachi](https://github.com/soydachi)! - The generated AGENTS.md now says to push only your own feature branch to origin, never the base or integration branch, and to leave opening the PR to a person unless asked.

## 3.0.7

### Patch Changes

- [#771](https://github.com/arcasilesgroup/ai-engineering/pull/771) [`842116f`](https://github.com/arcasilesgroup/ai-engineering/commit/842116f6239bbd7dcaf00b4f291ce5aa79ed972b) Thanks [@soydachi](https://github.com/soydachi)! - The 2025-11-14 review lands: releases gate on green checks (ci-gate polls the dispatched SHA's check runs, platforms runs on v* tags, the version-packages pull request wakes its own CI, SonarCloud waits retry through infrastructure failures), the policy guard reads Windows paths and PowerShell verbs and stops reading commit-message prose as shell, the secrets gate scans the allowlist editor without exemptions and doctor compares the live allowlist against a versioned baseline, skill mirrors fall back to junction and byte-verified copies on Windows, the identity ledger hashes line-ending-normalized text, doctor keeps the newest audits and survives directories, the injection guard never opens a network share, local-rules patterns with catastrophic backtracking shapes die at load, and a long tail of portability, documentation and simplicity fixes (adapters split by job, one path predicate, the learnings log archived).

## 3.0.6

### Patch Changes

- [#768](https://github.com/arcasilesgroup/ai-engineering/pull/768) [`b5a96fa`](https://github.com/arcasilesgroup/ai-engineering/commit/b5a96fa4872f7e7b85388b5a70660a814a9f59cd) Thanks [@soydachi](https://github.com/soydachi)! - opencode: the carrier follows the host's plugin API and stays out of its plugin scan. OpenCode imports every file in `~/.config/opencode/plugins` as a plugin ENTRY, so the chain bundle 3.0.x wrote beside the entry was refused as an invalid plugin and took the provider config hook down with it (`Plugin export is not a function`, then `undefined is not an object (evaluating 'R.config')`). The bundle now lives in `~/.config/opencode/ai-eng/`, imported from there. The entry is written for the installed major: 2.x gets the default `{ id, setup }` definition and gates tool calls by wrapping `tool.execute` (deny = throw, rewrite = args mutation); 1.x gets the `"tool.execute.before"`/`"tool.execute.after"` hooks. `update` retires a scanned bundle a recorded install left behind, and OpenCode's lowercase tool names (`shell`, `read`, `write`, …) now reach the guards under their canonical names instead of being skipped.

## 3.0.5

### Patch Changes

- [#766](https://github.com/arcasilesgroup/ai-engineering/pull/766) [`f447189`](https://github.com/arcasilesgroup/ai-engineering/commit/f4471894d592ef63601bc229036fd592904b6bfd) Thanks [@soydachi](https://github.com/soydachi)! - Every ai-eng question now shows only the titles of its options, without a description beside them:
  
  - **Surface picker (`init` and `config`):** only the surface names (Claude Code, Cursor, GitHub Copilot (CLI + VS Code)…). The capability notes, which ran to six lines for Copilot, are gone. `ai-eng doctor` still shows them, and `init` still warns after the pick when a surface cannot block tool calls.
  - **Re-running `init` on a governed repo:** the choices read "Update ai-eng's files", "Change agent surfaces" and "Exit".
  - **`uninstall`:** the choices read "This project", "Everything" and "Cancel". The block above the question still explains what each scope removes.

## 3.0.4

### Patch Changes

- [#763](https://github.com/arcasilesgroup/ai-engineering/pull/763) [`461bdd9`](https://github.com/arcasilesgroup/ai-engineering/commit/461bdd9dd3a42144c92838de7a1710b6d0fd7fc2) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng update` now moves the lock to the installed version even when every file is already current. Before, after upgrading the binary, `ai-eng doctor` kept saying "files installed by 3.0.2 → ai-eng update", and `ai-eng update` kept answering "nothing to sync" without moving the version. The warning never went away.

## 3.0.3

### Patch Changes

- [#761](https://github.com/arcasilesgroup/ai-engineering/pull/761) [`c5c7825`](https://github.com/arcasilesgroup/ai-engineering/commit/c5c7825eba0a4556c028b8aa85d06dd930fd3695) Thanks [@soydachi](https://github.com/soydachi)! - The guards stop blocking everyday agent commands for reasons that were not true.
  
  - The word `ai-engineering` (the repo slug, a checkout folder, the npm package) no longer counts as the `ai-eng` binary. It still counts when it is the command itself, or when a runner such as `npx`, `bunx` or `bun` starts it.
  - `2>&1` is no longer read as a write to a file.
  - `git -C <repo>` is a working folder, like `cd`.
  - The text of `gh pr`, `gh issue` and `gh release` (titles, bodies, comments) is prose, not code.
  - The command-scope policy no longer reads `/usr/bin/git` or a `NAME=value` prefix as a system write.
  
  What the guards protected before is still protected, and some gaps are closed too:
  
  - `npx ai-engineering@<version> uninstall` is blocked.
  - So is the package fed to a runner through `xargs`.
  - So is a command stored in `gh config set editor|pager|browser` or in `GH_BROWSER`, `GH_EDITOR` or `GH_PAGER`.
  - So is a write hidden after a `$(…)`, a shell keyword or a redirect glued to `2>&1`.
  
  A heredoc's lines are still judged as commands, whoever reads them. To pass a commit message or a PR body that names system paths, write it to a file first (`git commit -F <file>`, `gh pr create --body-file <file>`).

- [#758](https://github.com/arcasilesgroup/ai-engineering/pull/758) [`43db82c`](https://github.com/arcasilesgroup/ai-engineering/commit/43db82c1d564304f610e41c4f5cbc0229affad71) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng update`'s plan now reads the way it acts:
  
  - A shared settings file, such as `.cursor/hooks.json`, says "ai-eng's entries refreshed, your keys kept". It no longer says "overwritten", because it is merged by marker and your keys stay.
  - Each `↳` list of paths now sits under its own heading ("already current", "yours"). Before, it sat under the row above, so the current files seemed to be the ones updated.

## 3.0.2

### Patch Changes

- [#755](https://github.com/arcasilesgroup/ai-engineering/pull/755) [`49a3236`](https://github.com/arcasilesgroup/ai-engineering/commit/49a3236de69caa8069e464c88db8d4bc455f0087) Thanks [@soydachi](https://github.com/soydachi)! - What ai-eng wrote is ai-eng's, and `init`, `update`, `config` and `uninstall` now treat it that way every time — no more half-updated installs.
  
  - A skill folder ai-eng ships is ai-eng's whole. An edited page in it is rewritten to the installed version, and any file it does not ship is removed (names starting with a dot, such as `.DS_Store`, are left alone) — including the pages older releases left behind that 3.0.1 reported as "cannot prove it wrote" and never deleted. Keep your own skills in a folder with a name of your own: those are never touched.
  - A skill, agent or script ai-eng stops shipping is removed on the next `init` or `update`, with its mirror links in `~/.claude/skills`, `~/.agents/skills` and `~/.config/opencode/skill` and its OpenCode slash command.
  - The slash command of an ai-eng skill, an ai-eng agent copied into `~/.claude/agents`, and a machine carrier module (OpenCode, OMP, Pi) always hold ai-eng's bytes, even after an edit. A link of yours at those names is still never written through.
  - In the repo, `update` no longer asks "What wins?": a file ai-eng wrote (CI workflow, git hook shims, carriers) is rewritten even when edited — an edit you committed stays in git; an uncommitted one (a hook shim is never committed) is overwritten, so copy it first — and `uninstall` removes it. One that ai-eng stops shipping is removed on the next `update`. A git hook shim is the one exception on the way out: `uninstall` removes it only while it still carries the ai-eng shim marker. A file ai-eng never wrote stays yours, and `init` no longer records as ai-eng's a file already there whose bytes differ from ai-eng's.
  - Seeded config is the exception: `.ai-engineering/config.toml`, `overrides.toml` and `arch.rules.json` follow ai-eng while untouched and become yours on your first edit.
  - `doctor` drops the "canon unproven" row: every extra in a shipped skill folder is counted as stale, and `ai-eng update` sweeps it.

## 3.0.1

### Patch Changes

- [#752](https://github.com/arcasilesgroup/ai-engineering/pull/752) [`4ba4aa5`](https://github.com/arcasilesgroup/ai-engineering/commit/4ba4aa50ebfa3ebeb034a15f7f143bbecec53e8c) Thanks [@soydachi](https://github.com/soydachi)! - First install works on Windows, and for anyone who already had a settings file.
  
  - `ai-eng init` now merges its hooks into an existing `~/.claude/settings.json`, `~/.codex/hooks.json` or `~/.copilot/hooks/ai-eng.json`. 3.0.0 refused to touch any existing settings file, so every person who already used the host got no hooks at all, and `uninstall` could not take them back out.
  - A denial on Claude Code no longer ends the whole turn. The deny carried `continue: false`, which Claude Code reads even on exit 2 and which stops the agent entirely; it now exits 2 with the reason on stderr, so the agent reads why and goes on. On `Stop` this also makes the checkpoint gate keep the turn going instead of ending it.
  - On Windows, hook lines call `ai-eng.cmd` (npm) or `ai-eng.exe` (bun) instead of a bare `ai-eng`, which PowerShell resolves to `ai-eng.ps1` and the default Restricted execution policy refuses to run. Claude's lines also carry the exit status through PowerShell, which otherwise turned a denial into an allow.
  - On Windows, `init` and `update` remove npm's `ai-eng.ps1` for this package, so a bare `ai-eng` works in PowerShell too: for Cursor, whose shared repo hook has no per-OS line, and for a person typing `ai-eng init`.
  - The Copilot hook file gains a `powershell` line beside the POSIX one: the old guard was POSIX-only, and Copilot fails closed, so every tool call was denied on Windows. The same guarded file now serves the repo and the machine scope.
  - VS Code Copilot is covered by the Copilot surface (it reads the same hook files): pick "GitHub Copilot (CLI + VS Code)", or pass `--surface vscode`.
  - New `first-install` CI job: installs the package, inits each surface and runs every written hook line in PowerShell 5.1 (also under the Restricted policy), pwsh, cmd and Git Bash on Windows, Linux and macOS.

## 3.0.0

### Major Changes

- [#749](https://github.com/arcasilesgroup/ai-engineering/pull/749) [`9932b24`](https://github.com/arcasilesgroup/ai-engineering/commit/9932b2494b62c6ccb6be47a7686cedf17cbc23c0) Thanks [@soydachi](https://github.com/soydachi)! - Prepare the 3.0 release with the breaking CLI and checkpoint workflow changes.

### Minor Changes

- [#749](https://github.com/arcasilesgroup/ai-engineering/pull/749) [`9932b24`](https://github.com/arcasilesgroup/ai-engineering/commit/9932b2494b62c6ccb6be47a7686cedf17cbc23c0) Thanks [@soydachi](https://github.com/soydachi)! - Add the human-reviewed `ai-eng worktree merge <slug>` command for managed feature worktrees.
  
  Add the local workspace hub with governed project discovery, evidence-backed worktree filters and history, and persisted search-root settings with native folder selection.

- [#749](https://github.com/arcasilesgroup/ai-engineering/pull/749) [`9932b24`](https://github.com/arcasilesgroup/ai-engineering/commit/9932b2494b62c6ccb6be47a7686cedf17cbc23c0) Thanks [@soydachi](https://github.com/soydachi)! - Add local worktree lifecycle tracking and remove the checkpoint-plan approval stop.

- [#749](https://github.com/arcasilesgroup/ai-engineering/pull/749) [`9932b24`](https://github.com/arcasilesgroup/ai-engineering/commit/9932b2494b62c6ccb6be47a7686cedf17cbc23c0) Thanks [@soydachi](https://github.com/soydachi)! - Production readiness: the installed command starts with Bun (no Node needed) and a smoke test installs the real packed tarball; the full test suite runs on Linux, macOS and Windows; a release verifies the exact dispatched commit, packs once, publishes that same tarball and ships a runtime-only CycloneDX SBOM; publication requires an annotated tag signed by an allowlisted key and verified redistribution rights. Windows fixes close fail-open paths in the hook chain and self-protect, and the guards now deny shell text they cannot read.
- Floating core keeps the guard floor and orchestration ceremony in core, using the
  user's existing Git, host, and forge for the rest of the workflow.
- The command-scope policy now defaults to `4667` for every install and new project
  (was `0467`): system read and external write are allowed; system write and execute
  stay denied. Set `guards.policy_mode` in `.ai-engineering/config.toml` to narrow it.
- `ai-eng init` installs every skill and its resources by default, with no pack prompt
  or selection; a fresh init writes no `[canon].packs`, and a legacy value is ignored
  with its config bytes preserved.
- `ai-eng init` and `update` create the machine-level Claude, Codex and Copilot carriers when
  they are missing.
- Cleanup and uninstall delete only files ai-eng can prove it wrote, by exact bytes or a
  recorded hash; edited, user-added, linked and unproven files are kept and named. A
  settings file that cannot be changed safely is refused with a warning and left as it was.
- `ai-eng config` changes only `surfaces.enabled` and keeps every other byte, comments and
  line endings included; a layout it cannot edit safely is refused with the file unchanged.
- The checkpoint viewer opens the new current checkpoint during live updates and keeps its
  findings visible, linked from the status banner.
- The pre-push hook denies a direct push to the detected base, and denies when no base can
  be detected.
- Worktree merge and review commits use your own Git identity, and
  `ai-eng worktree rm --force` no longer needs a detected base.
- Automatic receipt retention refuses a linked or escaping `.ai-engineering/receipts`
  folder, deletes only receipt files it wrote, keeps at least one day of history, and never
  changes the host's working directory. Receipt retention opens each receipt only once.
- The checkpoint guard judges where a write lands, so case, link, `cd` and `json.tool -`
  aliases no longer reach the checkpoint file.
- Windows fixes: hooks no longer fail open, because the chain reads stdin before it exits;
  self-protect matches governed paths written with either slash; network-share paths are
  never opened; `AI_ENG_HOME` must stay inside its home; and protected home folders stay
  protected when reached through `..`.
- The shell guards read redirects and quoting, ANSI-C quoting (`$'...'`) and heredoc
  delimiters the way the shell does, and find `git` behind shell keywords and prefix
  commands. Shell text a guard cannot read is denied, and a malformed hook payload is
  denied instead of crashing the chain.
- `ai-eng wrap` keeps a run's evidence when the command's output overflows.
- The README now states the security boundary: what the guards stop and where they end.
- Worktree lifecycle awareness now reads pre-worktree approval from the exact fresh
  brainstorm artifact only when no local feature branch exists, without writing a
  second state store. Existing worktree checkpoints remain authoritative;
  `request-changes` uses the full pending checkpoint-only commit SHA as a
  compare-and-swap token before clearing review pins.
- Worktree creation starts from the invoking checkout's current `HEAD` and accepts
  a branch name only; it does not accept file hints or create a hint manifest. The
  detected base is recorded for integration, not used as the starting commit.
- Worktree cleanup now removes terminal control characters from ignored filenames in
  its output, and a `constructor` slug no longer blocks later worktree creation.
- Azure triage now validates source-linked claims and explains Recommendation and
  Why now alongside dates, discussion, parent/sprint context and evidence coverage.
  Current commitments and blockers can change recommendation order without
  changing native Priority/Severity; critical risk stays first. Partial chronology
  cannot establish current work. Existing inventory-only and GitHub behavior stays
  intact, and invalid evidence preserves the previous report.
- Add a memory-only synthetic preview for complete, limited and empty Azure
  reports; no live tenant or private report is used.

### 3.0 migration guide

The 3.0 major release removes the `workspace`, `briefing`, `upgrade` and `spec`
CLI verbs and the `worktree rebase` subcommand. Use `ai-eng worktree new`,
`list`, `merge` and `rm` for worktree operations; use the `ai-orchestrator`
skill and `.ai-engineering/workflow/checkpoints/<slug>.json` for feature
checkpoints; use native `git rebase <detected base>` when a feature needs
synchronization. Upgrade the installed package with
`bun add -g ai-engineering@latest`, then run `ai-eng update` to reconcile packaged assets.

Checkpoint lifecycle data now uses `reviewed_base` instead of `reviewed_main`.
The reader accepts the legacy field and normalizes it; new plans and writes use
`reviewed_base`. Every shipped skill now comes from `skills/` and is installed by
`ai-eng init` and `ai-eng update`. Existing `[canon].packs` values are legacy settings:
update preserves their config bytes and ignores their values.

`init` and `update` leave their file changes for review; they do not commit.
Only the explicitly approved worktree merge flow creates its reviewed merge
commit, and the feature checkout remains available afterward. Verify the
migrated installation with `ai-eng doctor`.

## Unreleased

<!-- Nothing pending. List a change here only when it has not shipped in a tagged release. -->

## 2.6.0

### Minor Changes

- [#743](https://github.com/arcasilesgroup/ai-engineering/pull/743) [`3e3bd00`](https://github.com/arcasilesgroup/ai-engineering/commit/3e3bd0099483c31cfd4450fc2fbd60355bcc7cb1) Thanks [@soydachi](https://github.com/soydachi)! - New `ai-github-triage` skill: reads every open issue and pull request of a repository into one ranked page at `.ai-engineering/triage.html` — what to start on first, what is already answered, what to close, each claim pinned to a permalink at a commit SHA — read-only on GitHub.

- [#743](https://github.com/arcasilesgroup/ai-engineering/pull/743) [`3e3bd00`](https://github.com/arcasilesgroup/ai-engineering/commit/3e3bd0099483c31cfd4450fc2fbd60355bcc7cb1) Thanks [@soydachi](https://github.com/soydachi)! - One worktree per feature: a session that writes code works in `<repo>.worktrees/<slug>`, merges into the local `main` when it closes, and never pushes, while the new `ai-eng worktree new|rm|list` verb manages those copies and the human decides the pull request against `origin/main`.

### Patch Changes

- [#742](https://github.com/arcasilesgroup/ai-engineering/pull/742) [`3986acb`](https://github.com/arcasilesgroup/ai-engineering/commit/3986acbb3ff5c84d2de5fc796879fcb10bd7a45c) Thanks [@soydachi](https://github.com/soydachi)! - Fix artifact HTML alignment drift at the source: the artifact design system now
  carries one CSS block instead of two drifted copies, the skills say to copy the
  whole block verbatim (copying only the tokens left each writer inventing layout),
  and a new layout gate (tests/artifact-layout.spec.ts) rejects centered or 68ch-capped
  body text, missing `.container` wrappers, and unaligned notes — the defect that
  shipped research 007-014 and the audit page. The gate also caught two template
  defects: `--radius-lg` was used 12× but never declared (border-radius computed
  to 0px — square corners — in every verbatim copier) and the shipped carriers
  were missing 18 canonical rules (`.sr`, `.pipe`, `.tiers`, `nav::after`).
  Both templates now carry the canonical block whole. Research gains the same
  guarantee it never had: `templates/research.html.tpl` (carrier nº3, gated by
  the layout and scroll-spy tests) and ai-research now starts from it instead of
  hand-writing a `<style>` block per report.

- [#744](https://github.com/arcasilesgroup/ai-engineering/pull/744) [`cb0e947`](https://github.com/arcasilesgroup/ai-engineering/commit/cb0e947ed78233b2b5ae622c1060d637109e72a8) Thanks [@soydachi](https://github.com/soydachi)! - Briefing: an ungoverned root reads no foreign receipt store. `summarizeReceipts`
  now takes a tri-state `dir` — `undefined` resolves the caller's repository,
  `null` means this root has no store at all, a string means that store — so a
  temp-root briefing stops resolving the process's nearest governed repo and
  scanning the host checkout's receipts (5 s per call → 0 ms).

- [#744](https://github.com/arcasilesgroup/ai-engineering/pull/744) [`cb0e947`](https://github.com/arcasilesgroup/ai-engineering/commit/cb0e947ed78233b2b5ae622c1060d637109e72a8) Thanks [@soydachi](https://github.com/soydachi)! - `ai-git-cleanup`: the pass learns what a squash merge looks like, so a branch a
  squash-merged pull request left behind is no longer stranded as "unmerged"
  forever. A branch (not the current one, not checked out anywhere) whose tree is
  byte-identical to a fetched `origin/main` has provably landed: tag
  `archive/<branch>` as the receipt that its history stays reachable, then delete
  it. It is the pass's only force-delete, earned by the whole-tree comparison; a
  branch whose tree differs is parked and reported, never merged or re-opened on
  the pass's initiative, and without a fetched `origin/main` the step refuses.

- [#740](https://github.com/arcasilesgroup/ai-engineering/pull/740) [`2fda7ea`](https://github.com/arcasilesgroup/ai-engineering/commit/2fda7ea5c991615b8cb08a1d2567ad7c219b00ba) Thanks [@soydachi](https://github.com/soydachi)! - npm: drop the eight `ai-engineering-<target>` platform packages. They never
  existed on the registry — OIDC trusted publishing cannot create a package
  (npm: "Package must exist"), so every release died at their publish with
  ENEEDAUTH while `ai-engineering` itself published fine. The launcher now runs
  `src/` under the bun that `engines` already requires (the v0.13.0
  `requires-python` contract, in npm terms), and the GitHub release keeps
  shipping the eight compiled binaries for the client's CI.

## 2.5.0

### Minor Changes

- [#734](https://github.com/arcasilesgroup/ai-engineering/pull/734) [`5da899e`](https://github.com/arcasilesgroup/ai-engineering/commit/5da899e45e4b4d26adbc77aebf73ddd39616bd21) Thanks [@soydachi](https://github.com/soydachi)! - skills: ai-git-cleanup v3 — action-first cleanup: phase 0 automatically makes the checkout safe to move (auto-stash a dirty tree, switch to the default branch, ff-only pull pinned to that branch as destination with HEAD already there, WARN-and-continue), phase 1 classifies every local branch deterministically in code with protection filtered before triage and named evidence on every batch entry, phase 2 asks exactly once per delete batch (delete all, pick, or stop — never zero confirmations), and phase 3 executes the batch then prints the per-branch report (previous branch, stash state, and action/reason/upstream/ahead/behind rows) — local git only: no push, no remote deletion, no reflog GC, no CI.

All notable changes, written for someone reading what changed, not how. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Historical notes (unreleased at the time)

These entries preserve earlier release history. Current 3.0 behavior is described
in the migration guide above.

### Added

- Earlier worktree lifecycle flow used a managed rebase to sync a clean feature with local `main`, then removed the reviewed feature checkout after merge. 3.0 removes that managed rebase step: synchronization uses native `git rebase <detected base>`, and `worktree merge` checks the reviewed feature and `reviewed_base` against the detected base while retaining the feature checkout.
- `ai-git-cleanup` skill: list finished local branches and worktrees with the evidence behind each recommendation, then remove only what a person approves at two confirmation gates — local git only.
- `ai-git-cleanup` v2: the two gates become one — a single view shows the full analysis table with its per-row command plan, the `fetchStatus` of the initial best-effort fetch, and the `postSync` post-cleanup sync (`git worktree prune` only when a worktree removal is queued, `git pull --ff-only` on the default branch only when it is behind its upstream, the ahead count reported — never pushed), and that one approval covers deletions and sync alike — local git only, still never zero confirmations.
- `ai-git-cleanup` v3: the flow turns action-first — phase 0 migrates to the default branch automatically and reversibly (auto-stash a dirty tree, `git switch` to the default, `git pull --ff-only` pinned to the default branch as destination with HEAD already there, WARN-and-continue), phase 1 classifies branches deterministically in code with protection filtered before every category, phase 2 asks exactly once per delete batch (delete all, pick, or stop — never zero confirmations), and phase 3 executes the batch then prints the per-branch report: default branch, previous (pre-migration) branch, stash state, and an action/reason/upstream/ahead/behind row for every branch — local git only; the analysis-first two-gate flow and `references/merge-evidence.md` are…
- Earlier Git worktree guidance required feature branches to start from local `main`, required clean design slots, and described merge-time checkout removal. The 3.0 contract starts `worktree new` from the invoking checkout's `HEAD`, reports dirty design files while leaving them in the source checkout, and merges to the detected base without deleting the feature checkout. The `ai-git-cleanup` and `ai-pr` notes that follow preserve the earlier flow's other behavior: `ai-git-cleanup` was rewritten into one automatic pass that removes dead worktrees and branches already merged into local `main`, keeps anything unmerged, unprovable, detached or dirty, force-deletes nothing and asks no question or name; `ai-pr` replaced `ai-pr-loop-fix`, cutting the pull-request branch from local `main` without a worktree, pushing, opening the pull request against `main`, watching CI and review comments, fixing only obvious failures in bounded iterations and merging with a merge commit (auto-merge on by default and switched off on request — "open the pull request" stops before the merge). `ai-audit-code` gained a `## Findings` block (every finding cites its `file:line` or a path, verify before deleting, a test that only asserted a symbol is not a consumer) and `ai-security` stated that CRITICAL through LOW take no severity without an attack path, with the validator never the author of the proof-of-concept it judges.
- `ai-triage` replaces `ai-github-triage` as the single public backlog skill for GitHub and Azure DevOps Services. It preserves complete, read-only GitHub issue and pull-request triage and adds one explicitly scoped Azure DevOps backlog per report; ambiguous scope stops before reads, and Azure access uses the already-authenticated `az` CLI with its Azure DevOps extension without writing credentials.

### Changed

### Fixed

- Checkpoint viewer: a missing or broken plan now shows the empty drop with an offline badge and an “Open a feature plan” h1; the journey row fits at 320px without sideways scroll; Technical details clears a 44px tap target; template and planted viewer stay byte-identical.

### Removed

- `ai-eng spec run` and the `ai-proof` skill. Checkpoints run the feature. `spec open`, `spec approve` and `spec close` stay.

## [2.4.0]

### Changed

- [`d5fe006`](https://github.com/arcasilesgroup/ai-engineering/commit/d5fe006a2ee2f883b7a6446039be6a7108308659) Thanks [@soydachi](https://github.com/soydachi)! - Block direct pushes to main via pre-push hook, security fixes (ReDoS, Snyk taint chain), and cognitive complexity refactors across doctor/init/uninstall/commands

## [2.3.0]

### Changed

- [`83b942f`](https://github.com/arcasilesgroup/ai-engineering/commit/83b942fbe86d6f39852df4a9c75924115946ba60) Thanks [@soydachi](https://github.com/soydachi)! - Governance by observability, not by more stoppers (research/001 R1+R2). `doctor`'s receipts line is no longer four numbers: it names the top denier guard/tool, the ledger's repeat count, and WARNs when the last 7 days of denies pass 3x the prior week. The gc that already collects receipts now merges a 90-day daily series into `summary.json` instead of overwriting it, and prunes the new `receipts/denies.json` ledger (age + newest-500) instead of deleting it. The ledger is the cross-session memory OWASP ASI01/ASI06 need: when a guard denies a call this exact machine already denied, the human message says `· this exact call has been denied N times before`. Signal only — no verdict, no new config, no dependency; deny receipts finally carry their real tool instead of `unknown`.

- [`57efe8e`](https://github.com/arcasilesgroup/ai-engineering/commit/57efe8ea66aedd7ed46296d371a6faa9669c02a5) Thanks [@soydachi](https://github.com/soydachi)! - Session handoff improvements (research 006 R1/R2/R3). `ai-eng briefing` generates a session handoff briefing with spec gates, plan step, recent denies, and receipt summary — closing the "rebuild state from scratch" gap (20/90 sessions needed manual "continua"). Receipts now carry `session_id` and `summarizeBySession()` groups them for per-session queries. Research cache (`research-cache/`) persists findings between sessions with doctor reporting and gc auto-prune for entries >30d.

### Fixed

- [`83b942f`](https://github.com/arcasilesgroup/ai-engineering/commit/83b942fbe86d6f39852df4a9c75924115946ba60) Thanks [@soydachi](https://github.com/soydachi)! - Docs, comments and specs now describe the product as it is, not as it was. The canon carried ghosts of the v1 Python era and the deleted ai-rtk skill: `ai-verify`'s eval harness claimed "Python 3.8+" while running on Bun, `ai-explore`'s example diagram cited a `chain.py` that does not exist, `ai-write` cited "spec 039/033" from the dead v1 spec-number registry, `ai-visual-recap` routed readers to the out-of-canon visual-plan skill, and `blueprint.html`/`recap.html` still listed ai-rtk in the canon trees, lineage and lifecycle tables and pinned version 0.13.0. Root docs drifted too: `AGENTS.md` pinned 2.2.0 and the retired `tsc --noEmit`, `THIRD-PARTY-NOTICES.md` listed dependencies package.json does not carry, `brand/README.md` documented a nonexistent `brand.ts legacy` subcommand, and `NOTICE.md` omitted the shipping ai-stress-test. Source comments narrating past bugs ("used to…", "no longer…") were rewritten to state the present rule; blueprint stamps now read 2.2.3, and ai-stress-test is listed where the canon is enumerated. No behavior changed — every diff is prose, verified against the tree.

## [2.2.3]

### Fixed

- [#727](https://github.com/arcasilesgroup/ai-engineering/pull/727) [`7504041`](https://github.com/arcasilesgroup/ai-engineering/commit/75040413fc3e0877fba4948d8a4ce77ac07779e5) Thanks [@soydachi](https://github.com/soydachi)! - `ai-eng` crashed on startup under Bun 1.3.x: the banner frame painted the brand hex `#00ED64` through `styleText` (node:util), whose runtime validation accepts only named formats — strict runtimes threw `ERR_INVALID_ARG_VALUE` on the first render, and lenient ones (Bun 1.4, Node ≥ 24.1) silently dropped the colour, so the banner shipped unpainted there. The banner now emits the truecolor SGR sequence for the declared hex itself, degrading to plain text under `NO_COLOR` or a non-TTY stdout — the same rule the rest of the frame follows. `BANNER_META` keeps its named format through `styleText`.

## [2.2.2]

### Fixed

- [`c46c261`](https://github.com/arcasilesgroup/ai-engineering/commit/c46c26132bb2336a41e65ec1c82c5d97d134ecb3) Thanks [@soydachi](https://github.com/soydachi)! - npm install -g ai-engineering@2.2.1 was broken: `src/assets.ts` imports seven fixture scripts with `with { type: "file" }` from `scripts/.embed/`, but the npm `files` whitelist did not include it, so the tarball shipped without them and `ai-eng` aborted on first run ("Cannot find module '../scripts/.embed/..."). The whitelist now ships `scripts/.embed`; verified by installing the packed tarball and running `ai-eng --version` + `doctor`.

## [2.2.1]

### Fixed

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

## [2.2.0]

### Changed

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - A gate whose check prints nothing is no longer ticked: `test -f X` and `ls X >/dev/null` exit 0 while saying nothing, so the box rested on an exit code and the ledger carried the silence as evidence. The executor now leaves such a gate UNMET and writes the remedy into its `EVIDENCE` line, and `templates/spec.html.tpl` + the ai-proof canon teach the alternative in place of the existence probe they used to show.
  
  What an existing install will notice: a milestone that already had gates of this shape reports them UNMET on the next `ai-eng spec run`. The fix is one line per gate — make the check print what it found (`test -f X && echo "X $(wc -c < X) bytes"`), or assert its output with `EXPECT: <text|/regex/>`. Nothing is unticked by the tool: the box stays as its author set it and the evidence is what stops counting, which is the same rule the executor already applied to a check that fails.

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - The carrier moves to where each host reads it, and the repo declares itself: `.ai-engineering/config.toml` existing, parsing and naming its surfaces is the single gate every verb asks. A governed repo keeps two carriers — Cursor's and Copilot's, whose cloud readers only see the checkout — while Claude Code, Oh My Pi, OpenCode, Codex and Pi are written once per machine, at the path that host actually loads (the OMP carrier lived in `.agents/hooks/`, which no OMP code path reads, and doctor called it green).
  
  Files the user also owns are merged by marker and never written whole; a settings file this installer would have to reformat is refused and named instead of rewritten. `init.templateDir` makes every new clone be born with the git floor, the shim asks the same gate, a foreign `templateDir` keeps its own hooks, and `uninstall` restores what was there. `doctor` separates the machine carrier, the repo declaration and the version state, and names a downgrade and Codex's `/hooks` re-approval instead of assuming green.
  
  What an existing install will notice: `ai-eng update` moves the carriers out of the repo, sweeps the ones that used to live there, writes the machine side, and records which version wrote what in `~/.ai-engineering/machine.json`.
  
  `AI_ENG_HOME` also redirects the one setting the floor writes outside a home: with it set, the global `init.templateDir` lives inside the override instead of the developer's git config, unless the caller already chose a `GIT_CONFIG_GLOBAL` of its own.

### Fixed

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - ai-goal finds the milestone on its own: Step 0 reads the spec slot from `ai-eng doctor`, then spec.html's context chain, plan.html, the handshake doc at `.ai-engineering/brainstorm.md` and the `[budget]` section, so a fresh session is launched as `/ai-goal` with no briefing prompt. ai-plan says where its working file lives: the slot, never a `.wayfinder/` map beside it.

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - init offers the global canon instead of installing it in silence: inside a repo on a machine that has no canon, the machine side is asked for before anything outside the repo is written, and a no leaves it untouched. §14.5b path 2.

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - The CI workflow `init` installs no longer reddens a project between milestones. Its spec-run step called `ai-eng spec run` unconditionally, and the binary is right to exit 2 when there is no `spec.html` — so a project with no live contract, which is the normal state after a contract closes, had a failing gate for a state that is not a failure. The step distinguishes the two now: no `spec.html` and no pin in the lock is "nothing to enforce between milestones" (exit 0), while a lock that still pins an approved contract whose `spec.html` has vanished fails and names the reason, because that is a contract someone deleted. A live contract still runs, and a check that cannot run is still a FAIL — the guard is about the state, never about a check.

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - The surface picker stops promising what the measurements contradict: its group headers stated a capability that neither row under them had ("experimental — rewrite may be partial" for a Cursor with no output rewrite and a Codex that replaces the whole input), and the row that matters carries its own measured degradation, with the source. The registry gains the state it was missing — `deny: "host-only"` — for a host like Zed, which denies through its own `agent.tool_permissions` and its `always_deny` regexes while offering no hook for the chain to run in; the picker used to print "can't block tool calls" about a host that can, and now says which of the two facts it means. `doctor` prints that caveat from the one place it is written instead of guessing it from a substring.

- [#720](https://github.com/arcasilesgroup/ai-engineering/pull/720) [`793714f`](https://github.com/arcasilesgroup/ai-engineering/commit/793714fba0956ea0bdba29dba746e721b3c6c88a) Thanks [@soydachi](https://github.com/soydachi)! - `update` now reaches the machine half even when the repo is already current. A repo whose assets all match the binary returned from the sync plan before the declared surfaces' carriers and the git template dir were touched — so a machine that had lost its carrier, which is exactly the state `doctor` answers with "→ ai-eng update", could not be repaired by the verb it named: the remedy ran, printed "all N assets current — nothing to sync", and changed nothing. The machine-side work moved into its own step, and both paths run it.
  
  What an existing install will notice: on a machine that lost a carrier (a wiped home, or `uninstall` at machine scope), `ai-eng update` now rewrites it and says which file it wrote, instead of reporting that nothing needed doing.

## [2.1.0]

### Changed

- [`f2e5ee1`](https://github.com/arcasilesgroup/ai-engineering/commit/f2e5ee196ad65ede7339477d619afe64f25cd678) Thanks [@soydachi](https://github.com/soydachi)! - skills: ai-agents-md gains the audit path. A repo that already ships an AGENTS.md set is
  inspected before anything is written: a rule the code already states, a child that repeats its
  parent, a command that no longer runs, a zone an agent must work in with no route. The findings
  and the target set are proposed first, and only an answer earns the edit. The written set is
  mirrored per directory (a sibling `CLAUDE.md` to each `AGENTS.md`), ai-write now routes to its
  README, CONTRIBUTING and SECURITY references instead of shipping them unread, and the
  unreferenced `agents-md-writer` reference is gone.

### Fixed

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

## [2.0.0] - 2026-09-01

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
